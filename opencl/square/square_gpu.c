/* square Array Example for GPU Using OpenCL
 *
 * MIT License
 * Copyright 2022 Variscite LTD
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
 * SOFTWARE.
 *
 */

#define CL_TARGET_OPENCL_VERSION 120
#define CL_USE_DEPRECATED_OPENCL_1_2_APIS

#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <CL/cl.h>

#define ARRAY_SMALL_SIZE 80
#define ARRAY_LARGE_SIZE 600000

const char *OpenCLSource =
    "__kernel void square(__global int* c, __global int* a,__global int* b)\n"
    "{\n"
    "	unsigned int id = get_global_id(0);\n"
    "	c[id] = a[id] * b[id];\n"
    "}\n";

int main(void)
{
    static volatile int a[ARRAY_SMALL_SIZE];
    static volatile int b[ARRAY_SMALL_SIZE];

    static int m[ARRAY_LARGE_SIZE];
    static int n[ARRAY_LARGE_SIZE];
    static volatile int z[ARRAY_LARGE_SIZE];

    int i = 0;
    cl_ulong start = 0, stop = 0;

    char device_message[100];
    char driver_message[100];

    for (i = 0; i < ARRAY_SMALL_SIZE; i++) {
        a[i] = 2 * i;
        b[i] = 3 * i;
    }

    for (i = 0; i < ARRAY_LARGE_SIZE; i++) {
        m[i] = a[i % ARRAY_SMALL_SIZE];
        n[i] = b[i % ARRAY_SMALL_SIZE];
    }

    cl_device_id device_id = NULL;
    cl_platform_id platform_id = NULL;

    clGetPlatformIDs(1, &platform_id, NULL);
    clGetDeviceIDs(platform_id, CL_DEVICE_TYPE_GPU, 1, &device_id , NULL);

    clGetDeviceInfo(device_id , CL_DEVICE_NAME, sizeof(device_message), &device_message, NULL);
    fprintf(stdout, "CL_DEVICE_NAME:\t\t%s\n", device_message);

    clGetDeviceInfo(device_id, CL_DRIVER_VERSION, sizeof(driver_message), &driver_message, NULL);
    fprintf(stdout, "CL_DRIVER_VERSION:\t%s\n\n", driver_message);

    cl_context gpu_context = clCreateContextFromType(0, CL_DEVICE_TYPE_GPU, NULL, NULL, NULL);

    cl_command_queue command_queue = clCreateCommandQueue(gpu_context, device_id, CL_QUEUE_PROFILING_ENABLE, NULL);

    cl_mem gpu_m = clCreateBuffer(gpu_context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, sizeof(int) * ARRAY_LARGE_SIZE, m, NULL);

    cl_mem gpu_n = clCreateBuffer(gpu_context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, sizeof(int) * ARRAY_LARGE_SIZE, n, NULL);

    cl_mem gpu_z = clCreateBuffer(gpu_context, CL_MEM_WRITE_ONLY, sizeof(int) * ARRAY_LARGE_SIZE, NULL, NULL);

    cl_program square_array_example = clCreateProgramWithSource(gpu_context, 1, (const char **)&OpenCLSource, NULL , NULL);

    clBuildProgram(square_array_example, 0, NULL, NULL, NULL, NULL);

    cl_kernel square_array_example_kernel = clCreateKernel(square_array_example, "square", NULL);

    clSetKernelArg(square_array_example_kernel, 0, sizeof(cl_mem), (void*)&gpu_z);
    clSetKernelArg(square_array_example_kernel, 1, sizeof(cl_mem), (void*)&gpu_m);
    clSetKernelArg(square_array_example_kernel, 2, sizeof(cl_mem), (void*)&gpu_n);

    cl_event event = clCreateUserEvent(gpu_context, NULL);

    size_t work_size[1] = {ARRAY_LARGE_SIZE};
    clEnqueueNDRangeKernel(command_queue, square_array_example_kernel, 1, NULL, work_size, NULL, 0, NULL, &event);
    clEnqueueReadBuffer(command_queue, gpu_z, CL_TRUE, 0, ARRAY_LARGE_SIZE * sizeof(int), z, 0, NULL, NULL);
    clFlush(command_queue);

    clReleaseKernel(square_array_example_kernel);
    clReleaseProgram(square_array_example);
    clReleaseCommandQueue(command_queue);
    clReleaseContext(gpu_context);
    clReleaseMemObject(gpu_m);
    clReleaseMemObject(gpu_n);
    clReleaseMemObject(gpu_z);
    clWaitForEvents(1, &event);

    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_START, sizeof(cl_ulong), &start, NULL);
    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_END, sizeof(cl_ulong), &stop, NULL);

    printf("[Execution Time] >> %lf seconds.\n", (stop - start) / 1000000000.0);

    return EXIT_SUCCESS;
}
