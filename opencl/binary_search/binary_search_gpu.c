/* Binary Search Example for GPU Using OpenCL
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
#define ARR_SIZE 1000000

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <CL/opencl.h>


char* OpenCLSource = \
    "int _binary_search(long *arr, long n, int min, int max) {    \n" \
    "    int mid;                                                 \n" \
    "    while (min <= max) {                                     \n" \
    "        mid = min + (max - min) / 2;                         \n" \
    "                                                             \n" \
    "        if (arr[mid] == n)                                   \n" \
    "            return mid;                                      \n" \
    "                                                             \n" \
    "        if (arr[mid] < n) {                                  \n" \
    "            min = mid + 1;                                   \n" \
    "        } else {                                             \n" \
    "            max = mid - 1;                                   \n" \
    "        }                                                    \n" \
    "    }                                                        \n" \
    "                                                             \n" \
    "    return -1;                                               \n" \
    "}                                                            \n" \
    "                                                             \n" \
    "kernel void binary_search(                                   \n" \
    "    global long *a, global int *l,                           \n" \
    "    global int *h, global long *r, global long **arr) {      \n" \
    "    unsigned int id = get_global_id(0);                      \n" \
    "    r[id] = _binary_search(arr, a[id], l[id], h[id]);        \n" \
    "}                                                            \n" \
    "";


int main(int argc, char *argv[]) {
    static long arr[ARR_SIZE];
    int i;

    if (argc != 2) {
        fprintf(stderr, "usage of %s: [number]\n", argv[0]);
        return EXIT_FAILURE;
    }

    srand(time(NULL));
    arr[0] = rand() % 10;

    for (i = 1; i < ARR_SIZE; i++)
        arr[i] = arr[i - 1] + (rand() % 10);

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

    cl_kernel kernel = clCreateKernel(program, "binary_search", NULL);

    long a[] = { (long)n };
    long r[] = { 0 };
    int l[] = { 0 };
    int h[] = { ARR_SIZE - 1 };

    cl_mem ma = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE, sizeof(a), NULL, NULL);
    cl_mem mr = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE, sizeof(r), NULL, NULL);
    cl_mem ml = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE, sizeof(l), NULL, NULL);
    cl_mem mh = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE, sizeof(h), NULL, NULL);
    cl_mem gpu_arr = clCreateBuffer(gpu_context, CL_MEM_READ_ONLY | CL_MEM_COPY_HOST_PTR, sizeof(long) * ARR_SIZE, arr, NULL);

    clEnqueueWriteBuffer(command_queue, ma, CL_TRUE, 0, sizeof(a), a, 0, NULL, NULL);
    clEnqueueWriteBuffer(command_queue, mr, CL_TRUE, 0, sizeof(r), r, 0, NULL, NULL);
    clEnqueueWriteBuffer(command_queue, ml, CL_TRUE, 0, sizeof(l), l, 0, NULL, NULL);
    clEnqueueWriteBuffer(command_queue, mh, CL_TRUE, 0, sizeof(h), h, 0, NULL, NULL);
    clEnqueueWriteBuffer(command_queue, gpu_arr, CL_TRUE, 0, sizeof(arr), arr, 0, NULL, NULL);

    clSetKernelArg(kernel, 0, sizeof(ma), (void *)&ma);
    clSetKernelArg(kernel, 3, sizeof(mr), (void *)&mr);
    clSetKernelArg(kernel, 1, sizeof(ml), (void *)&ml);
    clSetKernelArg(kernel, 2, sizeof(mh), (void *)&mh);
    clSetKernelArg(kernel, 4, sizeof(gpu_arr), (void*)&gpu_arr);

    cl_event event = clCreateUserEvent(gpu_context, NULL);

    size_t work[] = { 1, 0, 0 };
    clEnqueueNDRangeKernel(command_queue, kernel, 1, NULL, work, NULL, 0, NULL, &event);
    clEnqueueReadBuffer(command_queue, mr, CL_TRUE, 0, sizeof(r), r, 0, NULL, NULL);

    clFlush(command_queue);
    clReleaseKernel(kernel);
    clReleaseProgram(program);
    clReleaseCommandQueue(command_queue);
    clReleaseContext(gpu_context);
    clReleaseMemObject(ma);
    clReleaseMemObject(mr);
    clReleaseMemObject(ml);
    clReleaseMemObject(mh);
    clReleaseMemObject(gpu_arr);
    clWaitForEvents(1, &event);

    cl_ulong start = 0, stop = 0;

    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_START, sizeof(cl_ulong), &start, NULL);
    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_END, sizeof(cl_ulong), &stop, NULL);

    if (r[0] >= 0)
        printf("[Result] >> %d found at index %ld of the array\n", n, (long)r[0]);
    else
        printf("[Result] >> %d not found in the array\n", n);
    printf("[Execution Time] >> %lf seconds.\n", (stop - start) / 1000000000.0);

    return EXIT_SUCCESS;
}
