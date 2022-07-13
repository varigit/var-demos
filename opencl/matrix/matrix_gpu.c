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

#define DIM 512

const char *OpenCLSource = \
    "__kernel void matrix_multiplication(__global float* z, __global float* a,                 \n"
    "                                    __global float* b, int dim) {                         \n"
    "    int id_x = get_global_id(0);                                                          \n"
    "    int id_y = get_global_id(1);                                                          \n"
    "    float sum = 0.0;                                                                      \n"
    "                                                                                          \n"
    "    for (int i = 0; i < dim; i++)                                                         \n"
    "        sum += a[dim * id_x + i] * b[dim * i +id_y];                                      \n"
    "                                                                                          \n"
    "    z[dim * id_x + id_y] = sum;                                                           \n"
    "}                                                                                         \n";


int main(void)
{
    float a[DIM * DIM];
    float b[DIM * DIM];
    float z[DIM * DIM];
    int dim = DIM;
    int i, j;

    char device_message[100];
    char driver_message[100];

    for (i = 0; i < DIM; i++)
	    for (j = 0; j < DIM; j++) {
		    a[DIM * i + j] = 2 * j - 5 * i;
		    b[DIM * i + j] = 3 * j + 10 * i;
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
    cl_program matrix_multiplication = clCreateProgramWithSource(gpu_context, 1, (const char **)&OpenCLSource, NULL , NULL);
    clBuildProgram(matrix_multiplication, 0, NULL, NULL, NULL, NULL);
    cl_kernel kernel = clCreateKernel(matrix_multiplication, "matrix_multiplication", NULL);

    cl_mem gpu_a = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE | CL_MEM_COPY_HOST_PTR, sizeof(float) * DIM * DIM, a, NULL);
    cl_mem gpu_b = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE | CL_MEM_COPY_HOST_PTR, sizeof(float) * DIM * DIM, b, NULL);
    cl_mem gpu_z = clCreateBuffer(gpu_context, CL_MEM_READ_WRITE, sizeof(float) * DIM * DIM, NULL, NULL);

    clSetKernelArg(kernel, 0, sizeof(cl_mem), (void*)&gpu_z);
    clSetKernelArg(kernel, 1, sizeof(cl_mem), (void*)&gpu_a);
    clSetKernelArg(kernel, 2, sizeof(cl_mem), (void*)&gpu_b);
    clSetKernelArg(kernel, 3, sizeof(int), (void*)&dim);

    cl_event event = clCreateUserEvent(gpu_context, NULL);

    size_t work[] = { DIM, DIM };
    clEnqueueNDRangeKernel(command_queue, kernel, 2, NULL, work, NULL, 0, NULL, &event);
    clEnqueueReadBuffer(command_queue, gpu_z, CL_TRUE, 0, sizeof(float) * DIM * DIM, z, 0, NULL, NULL);

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

    /* Print the resulting matrix
    for (i = 0; i < DIM; i++) {
        for (j = 0; j < DIM; j++)
            printf("%f ", z[DIM * i + j]);

        printf("\n");
    } */

    printf("[Execution Time] >> %lf seconds.\n", (stop - start) / 1000000000.0);

    return EXIT_SUCCESS;
}
