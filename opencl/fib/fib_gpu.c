/* Fibonacci Example for GPU Using OpenCL
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

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <CL/opencl.h>

char* OpenCLSource = \
    "float _fib(float n) {                  \n" \
    "  if(n <= 0) return 0;                 \n" \
    "  if(n > 0 && n < 3) return 1;         \n" \
    "  float r = 0, n1 = 1, n2 = 1;         \n" \
    "  for (int i = 2; i < n; i++) {        \n" \
    "    r = n1 + n2;                       \n" \
    "    n1 = n2;                           \n" \
    "    n2 = r;                            \n" \
    "  }                                    \n" \
    "  return r;                            \n" \
    "}                                      \n" \
    "                                       \n" \
    "kernel void fib(                       \n" \
    "    global const float *a,             \n" \
    "    global float *r) {                 \n" \
    "  unsigned int id = get_global_id(0);  \n" \
    "  r[id] = _fib(a[id]);                 \n" \
    "}                                      \n" \
    "";

int main(int argc, char *argv[])
{
    if (argc != 2) {
	    fprintf(stderr, "usage of %s: [number]\n", argv[0]);
	    return EXIT_FAILURE;
    }

    int n = atoi(argv[1]);
    size_t source_size = strlen(OpenCLSource);

	char device_message[100];
	char driver_message[100];

	cl_platform_id platform_id = NULL;

    clGetPlatformIDs(1, &platform_id, NULL);

    cl_device_id device_id = NULL;
    clGetDeviceIDs(platform_id, CL_DEVICE_TYPE_GPU, 1, &device_id, NULL);

	clGetDeviceInfo(device_id , CL_DEVICE_NAME, sizeof(device_message), &device_message, NULL);
	fprintf(stdout, "CL_DEVICE_NAME:\t\t%s\n", device_message);

	clGetDeviceInfo(device_id, CL_DRIVER_VERSION, sizeof(driver_message), &driver_message, NULL);
	fprintf(stdout, "CL_DRIVER_VERSION:\t%s\n\n", driver_message);

    cl_context gpu_context = clCreateContextFromType(0, CL_DEVICE_TYPE_GPU, NULL, NULL, NULL);

    cl_command_queue command_queue = clCreateCommandQueue(gpu_context, device_id, CL_QUEUE_PROFILING_ENABLE, NULL);

    cl_program program = clCreateProgramWithSource(gpu_context, 1, (const char **)&OpenCLSource, (const size_t *)&source_size, NULL);

    clBuildProgram(program, 0, NULL, NULL, NULL, NULL);

    clGetProgramBuildInfo(program, device_id, CL_PROGRAM_BUILD_LOG, 0, NULL, NULL);
    clGetProgramBuildInfo(program, device_id, CL_PROGRAM_BUILD_LOG, NULL, NULL, NULL);

    cl_kernel kernel = clCreateKernel(program, "fib", NULL);

    float a[1] = { (float)n };
    float r[1] = { 0 };

    cl_mem ma = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE, sizeof(a), NULL, NULL);

    cl_mem mr = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE, sizeof(r), NULL, NULL);

    clEnqueueWriteBuffer(command_queue, ma, CL_TRUE, 0, sizeof(a), a, 0, NULL, NULL);

    clEnqueueWriteBuffer(command_queue, mr, CL_TRUE, 0, sizeof(r), r, 0, NULL, NULL);

    clSetKernelArg(kernel, 0, sizeof(ma), (void *)&ma);

    clSetKernelArg(kernel, 1, sizeof(mr), (void *)&mr);

    cl_event event = clCreateUserEvent(gpu_context, NULL);

    size_t work[2] = { 1, 0 };
    clEnqueueNDRangeKernel(command_queue, kernel, 1, NULL, work, work, 0, NULL, &event);
    clEnqueueReadBuffer(command_queue, mr, CL_TRUE, 0, sizeof(r), r, 0, NULL, NULL);

    clFlush(command_queue);
    clReleaseKernel(kernel);
    clReleaseProgram(program);
    clReleaseCommandQueue(command_queue);
    clReleaseContext(gpu_context);
    clReleaseMemObject(ma);
    clReleaseMemObject(mr);
    clWaitForEvents(1, &event);

    cl_ulong start = 0, stop = 0;

    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_START, sizeof(cl_ulong), &start, NULL);
    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_END, sizeof(cl_ulong), &stop, NULL);

    printf("[Result] >> %ld\n", (long)r[0]);
    printf("[Execution Time] >> %lf seconds.\n", (stop - start) / 1000000000.0);  

    return EXIT_SUCCESS;
}
