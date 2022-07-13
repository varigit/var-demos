/* Matrix Multiplication for GPU Using OpenCL
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

#define N 512

const char *OpenCLSource = \
    "__kernel void matrix_multiplication(__global int* z, __global int* a,__global int* b)\n"
    "{                                                                                    \n"
    "   unsigned int id = get_global_id(0);                                               \n"
    "   int i = 0, j = 0, q = 0;                                                          \n"
    "   for (j = 0; j < id; j++) {                                                         \n"
    "       for (i = 0; i < id; i++) {                                                     \n"
    "           z[j][i] = 0;                                                              \n"
    "           for (q = 0; q < N; q++) {                                                 \n"
    "               z[j][i] += a[j][q]*b[q][i];                                           \n"
    "           }                                                                         \n"
    "        }                                                                            \n"
    "    }                                                                                \n"
    "}                                                                                    \n";

int main(void)
{
    static float a[N][N];
    static float b[N][N];
    static float z[N][N];

    int i, j;

    char device_message[100];
    char driver_message[100];

    for (j = 0; j < N; j++) {
	    for (i = 0; i < N; i++) {
		    a[j][i] = 2 * i - 5 * j;
		    b[j][i] = 3 * i + 10 * j;
	    }
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

    cl_mem gpu_a = clCreateBuffer(gpu_context, CL_MEM_WRITE_ONLY | CL_MEM_COPY_HOST_PTR, sizeof(a), a, NULL);

    cl_mem gpu_b = clCreateBuffer(gpu_context, CL_MEM_WRITE_ONLY | CL_MEM_COPY_HOST_PTR, sizeof(b), b, NULL);

    cl_mem gpu_z = clCreateBuffer(gpu_context, CL_MEM_WRITE_ONLY, sizeof(z), NULL, NULL);

    cl_program matrix_multiplication = clCreateProgramWithSource(gpu_context, 1, (const char **)&OpenCLSource, NULL , NULL);

    clBuildProgram(matrix_multiplication, 0, NULL, NULL, NULL, NULL);

    cl_kernel kernel = clCreateKernel(matrix_multiplication, "matrix_calculation", NULL);

    clSetKernelArg(kernel, 0, sizeof(cl_mem), (void*)&gpu_z);
    clSetKernelArg(kernel, 1, sizeof(cl_mem), (void*)&gpu_a);
    clSetKernelArg(kernel, 2, sizeof(cl_mem), (void*)&gpu_b);

    cl_event event = clCreateUserEvent(gpu_context, NULL);

    size_t work[] = { N };
    clEnqueueNDRangeKernel(command_queue, kernel, 1, NULL, work, NULL, 0, NULL, &event);
    clEnqueueReadBuffer(command_queue, gpu_z, CL_TRUE, 0, sizeof(z), z, 0, NULL, NULL);
    clFlush(command_queue);

    clReleaseKernel(kernel);
    clReleaseProgram(matrix_multiplication);
    clReleaseCommandQueue(command_queue);
    clReleaseContext(gpu_context);
    clReleaseMemObject(gpu_a);
    clReleaseMemObject(gpu_b);
    clReleaseMemObject(gpu_z);
    clWaitForEvents(1, &event);

    cl_ulong start = 0;
    cl_ulong stop = 0;

    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_START, sizeof(cl_ulong), &start, NULL);
    clGetEventProfilingInfo(event, CL_PROFILING_COMMAND_END, sizeof(cl_ulong), &stop, NULL);

    printf("[Execution Time] >> %lf seconds.\n", (stop - start) / 1000000000.0);

    return EXIT_SUCCESS;
}
