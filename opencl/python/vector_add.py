#!/usr/bin/env python3
# Copyright 2026 Variscite Ltd.
# SPDX-License-Identifier: BSD-3-Clause

import argparse
import ctypes as C
from ctypes.util import find_library
import time


class OpenCL:
    def __init__(self):
        library = find_library('OpenCL')
        if not library:
            raise RuntimeError('libOpenCL is missing from this image')
        self.lib = C.CDLL(library)
        pointer, uint, size = C.c_void_p, C.c_uint, C.c_size_t
        signatures = {
            'clGetPlatformIDs': (C.c_int, [uint, C.POINTER(pointer),
                                          C.POINTER(uint)]),
            'clGetDeviceIDs': (C.c_int, [pointer, C.c_ulong, uint,
                                        C.POINTER(pointer), C.POINTER(uint)]),
            'clGetDeviceInfo': (C.c_int, [pointer, uint, size, pointer,
                                         C.POINTER(size)]),
            'clCreateContext': (pointer, [pointer, uint, C.POINTER(pointer),
                                          pointer, pointer, C.POINTER(C.c_int)]),
            'clCreateCommandQueue': (pointer, [pointer, pointer, C.c_ulong,
                                               C.POINTER(C.c_int)]),
            'clCreateBuffer': (pointer, [pointer, C.c_ulong, size, pointer,
                                         C.POINTER(C.c_int)]),
            'clCreateProgramWithSource': (pointer, [pointer, uint,
                C.POINTER(C.c_char_p), C.POINTER(size), C.POINTER(C.c_int)]),
            'clBuildProgram': (C.c_int, [pointer, uint, C.POINTER(pointer),
                                        C.c_char_p, pointer, pointer]),
            'clGetProgramBuildInfo': (C.c_int, [pointer, pointer, uint, size,
                                               pointer, C.POINTER(size)]),
            'clCreateKernel': (pointer, [pointer, C.c_char_p,
                                         C.POINTER(C.c_int)]),
            'clSetKernelArg': (C.c_int, [pointer, uint, size, pointer]),
            'clEnqueueNDRangeKernel': (C.c_int, [pointer, pointer, uint,
                C.POINTER(size), C.POINTER(size), C.POINTER(size),
                uint, pointer, C.POINTER(pointer)]),
            'clEnqueueReadBuffer': (C.c_int, [pointer, pointer, uint, size,
                size, pointer, uint, pointer, pointer]),
            'clGetEventProfilingInfo': (C.c_int, [pointer, uint, size,
                                                  pointer, C.POINTER(size)]),
        }
        for name, (result, arguments) in signatures.items():
            function = getattr(self.lib, name)
            function.restype = result
            function.argtypes = arguments
        for kind in ('Context', 'CommandQueue', 'MemObject', 'Program',
                     'Kernel', 'Event'):
            function = getattr(self.lib, 'clRelease' + kind)
            function.restype = C.c_int
            function.argtypes = [pointer]
        self.resources = []

    def check(self, status):
        if status != 0:
            raise RuntimeError(f'OpenCL returned error {status}')

    def own(self, handle, status, kind):
        self.check(status.value)
        if not handle:
            raise RuntimeError(f'OpenCL did not create {kind}')
        self.resources.append((kind, handle))
        return handle

    def close(self):
        for kind, handle in reversed(self.resources):
            getattr(self.lib, 'clRelease' + kind)(handle)
        self.resources.clear()

    def gpu(self):
        count = C.c_uint()
        self.check(self.lib.clGetPlatformIDs(0, None, C.byref(count)))
        platforms = (C.c_void_p * count.value)()
        self.check(self.lib.clGetPlatformIDs(count, platforms, None))
        for platform in platforms:
            device = C.c_void_p()
            status = self.lib.clGetDeviceIDs(platform, 4, 1,
                                            C.byref(device), None)
            if status == 0:
                return device
            if status != -1:  # CL_DEVICE_NOT_FOUND
                self.check(status)
        raise RuntimeError('No OpenCL GPU is available; no CPU fallback')

    def run(self, count=262144, check_only=False):
        device = self.gpu()
        name = C.create_string_buffer(256)
        self.check(self.lib.clGetDeviceInfo(device, 0x102B, len(name),
                                            name, None))
        print('GPU:', name.value.decode(errors='replace'), flush=True)
        if check_only:
            return
        error = C.c_int()
        context = self.own(self.lib.clCreateContext(
            None, 1, C.byref(device), None, None, C.byref(error)),
            error, 'Context')
        queue = self.own(self.lib.clCreateCommandQueue(
            context, device, 2, C.byref(error)), error, 'CommandQueue')
        data = (C.c_float * count)(*(index % 100 for index in range(count)))
        output = (C.c_float * count)()
        buffers = []
        for flags, host in ((4 | 32, data), (4 | 32, data), (2, None)):
            buffers.append(self.own(self.lib.clCreateBuffer(
                context, flags, C.sizeof(data), host, C.byref(error)),
                error, 'MemObject'))
        source = C.c_char_p(b'__kernel void add(__global const float *a, '
            b'__global const float *b, __global float *c) {'
            b' size_t i=get_global_id(0); c[i]=a[i]+b[i]; }')
        program = self.own(self.lib.clCreateProgramWithSource(
            context, 1, C.byref(source), None, C.byref(error)),
            error, 'Program')
        status = self.lib.clBuildProgram(program, 1, C.byref(device),
                                         None, None, None)
        if status:
            log = C.create_string_buffer(8192)
            self.lib.clGetProgramBuildInfo(program, device, 0x1183,
                                           len(log), log, None)
            raise RuntimeError(log.value.decode(errors='replace'))
        kernel = self.own(self.lib.clCreateKernel(
            program, b'add', C.byref(error)), error, 'Kernel')
        for index, buffer in enumerate(buffers):
            handle = C.c_void_p(buffer)
            self.check(self.lib.clSetKernelArg(kernel, index,
                C.sizeof(handle), C.byref(handle)))
        event = C.c_void_p()
        size = C.c_size_t(count)
        started = time.monotonic()
        self.check(self.lib.clEnqueueNDRangeKernel(queue, kernel, 1,
            None, C.byref(size), None, 0, None, C.byref(event)))
        self.resources.append(('Event', event))
        self.check(self.lib.clEnqueueReadBuffer(queue, buffers[2], 1,
            0, C.sizeof(output), output, 0, None, None))
        wall_ms = 1000 * (time.monotonic() - started)
        if any(value != 2 * (index % 100)
               for index, value in enumerate(output)):
            raise RuntimeError('GPU result verification failed')
        times = []
        for field in (0x1282, 0x1283):
            stamp = C.c_ulonglong()
            self.check(self.lib.clGetEventProfilingInfo(event, field,
                C.sizeof(stamp), C.byref(stamp), None))
            times.append(stamp.value)
        print(f'Verified {count:,} additions on the GPU.')
        print(f'GPU kernel: {(times[1] - times[0]) / 1e6:.3f} ms')
        print(f'Dispatch and readback: {wall_ms:.3f} ms')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    api = None
    try:
        api = OpenCL()
        api.run(check_only=args.check)
    except (OSError, RuntimeError) as error:
        parser.exit(1, f'{error}\n')
    finally:
        if api is not None:
            api.close()


if __name__ == '__main__':
    main()
