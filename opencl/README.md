# OpenCL Examples

OpenCL:tm: (Open Computing Language) is an open, royalty-free standard for
cross-platform, parallel programming of diverse accelerators found in
supercomputers, cloud servers, personal computers, mobile devices and embedded
platforms.

The OpenCL framework is defined by Khronos Group:

* [https://www.khronos.org/opencl/](https://www.khronos.org/opencl/).

## CPU and GPU Overview

The difference between the Central Processing Unit (CPU) and the Graphics
Processing Unit (GPU) and why the GPU itself is so crucial for developing
graphical applications. The CPU is designed to handle a wide range of tasks
quickly but is limited to the concurrency of tasks that can be executed
simultaneously. Even though the CPU can handle a variety of workloads, it does
not have optimization for multiple tasks. For example, if the solution has
algorithms that require a lot of branching and conditions like **if-else**
statements, then the code runs more efficiently on a CPU than on a GPU.

On the other hand, the GPU is designed with multitasking in mind and generally
supports one type of workload related to graphics processing, such as rendering
high-resolution images and videos. CPUs and GPUs differ in their overall
architecture; while the CPU is **narrow** and **deep**, the GPUs are
**shallow** and **wide**. Generally, the CPU has a massive memory cache, makes
branch prediction, and has a much higher clock speed than the GPU. The GPU
contains several compute units, which are much simpler than a regular CPU, and
execute the exact instructions in parallel but operate on different data, and
it also does not make branch predictions.

## Getting Started

To build the examples, please follow the next instructions.

### Yocto Toolchain

1. Build a Yocto toolchain by following the
[Variscite Wiki](https://variwiki.com/) instructions.

2. Export the toolchain:

```console
$ source /opt/fslc-xwayland/<version>/environment-setup-cortexa53-crypto-fslc-linux
```

### Build the Examples

1. Search for the OpenCL header file:

```console
$ find / -iname "cl.h" 2> /dev/null
```
Output:

```console
/opt/fslc-xwayland/<version>/sysroots/cortexa53-crypto-fslc-linux/usr/include/CL/cl.h
```

2. Set the enviroment variable for the Makefile:

```console
$ export ROOTFS_DIR=/opt/fslc-xwayland/<version>/sysroots/cortexa53-crypto-fslc-linux
```

3. To compile the examples, just run the following command in the respective folder:

```console
$ make
```
4. Copy the examples to the module, and execute them.


## Examples

### Sum Array

* [Sum Array Example](https://github.com/varigit/var-demos/tree/master/opencl/sum)

|                    | Kernel  | CPU@Frequency | Time (seconds)  | GPU@Frequency | Time (seconds) |
|--------------------|---------|---------------|-----------------|---------------|----------------|
| VAR-SOM-MX8        |         |               |                 |               |                |
| VAR-SOM-MX8X       |         |               |                 |               |                |
| VAR-SOM-MX8M-NANO  |         |               |                 |               |                |
| DART-MX8M          |         |               |                 |               |                |
| DART-MX8M-MINI     |         |               |                 |               |                |
| DART-MX8M-PLUS     | 5.10.72 | A53@1200000   | **0.010300**    | GC7000UL@1000 | **0.002497**   |


### Square Array

* [Square Array Example](https://github.com/varigit/var-demos/tree/master/opencl/square)

|                    | Kernel  | CPU@Frequency | Time (seconds)  | GPU@Frequency | Time (seconds) |
|--------------------|---------|---------------|-----------------|---------------|----------------|
| VAR-SOM-MX8        |         |               |                 |               |                |
| VAR-SOM-MX8X       |         |               |                 |               |                |
| VAR-SOM-MX8M-NANO  |         |               |                 |               |                |
| DART-MX8M          |         |               |                 |               |                |
| DART-MX8M-MINI     |         |               |                 |               |                |
| DART-MX8M-PLUS     | 5.10.72 | A53@1200000   | **0.011486**    | GC7000UL@1000 | **0.002488**   |

### Fibonacci

* [Fibonacci Example](https://github.com/varigit/var-demos/tree/master/opencl/fib)

|                    | Kernel  | CPU@Frequency | Time (seconds)  | GPU@Frequency | Time (seconds) |
|--------------------|---------|---------------|-----------------|---------------|----------------|
| VAR-SOM-MX8        |         |               |                 |               |                |
| VAR-SOM-MX8X       |         |               |                 |               |                |
| VAR-SOM-MX8M-NANO  |         |               |                 |               |                |
| DART-MX8M          |         |               |                 |               |                |
| DART-MX8M-MINI     |         |               |                 |               |                |
| DART-MX8M-PLUS     | 5.10.72 | A53@1200000   | **0.000007**    | GC7000UL@1000 | **0.000109**   |
