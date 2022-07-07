# OpenCL Examples

## CPU and GPU

The difference between the Central Processing Unit (CPU) and the Graphics
Processing Unit (GPU) and why the GPU itself is so crucial for developing
graphical applications. The CPU is designed to handle a wide range of tasks
quickly but is limited to the concurrency of tasks that can be executed
simultaneously. Even though the CPU can handle a variety of workloads, it does
not have optimization for multiple tasks. For example, if the solution has
algorithms that require a lot of branching and conditions like “if-else”
statements, then the code runs more efficiently on a CPU than on a GPU.

On the other hand, the GPU is designed with multitasking in mind and generally
supports one type of workload related to graphics processing, such as rendering
high-resolution images and videos. CPUs and GPUs differ in their overall
architecture; while the CPU is narrow and deep, the GPUs are shallow and wide.
Generally, the CPU has a massive memory cache, makes branch prediction, and has
a much higher clock speed than the GPU. The GPU contains several compute units,
which are much simpler than a regular CPU, and execute the exact instructions in
parallel but operate on different data, and it also does not make branch
predictions.

The OpenCL (cross-platform, parallel programming of modern processors) is
defined by Khronos Group:

* [https://www.khronos.org/opencl/](https://www.khronos.org/opencl/).

## Getting Started

To build the examples, please follow the next instructions.

1. Build a Yocto toolchain by following the
[Variscite Wiki](https://variwiki.com/) instructions.

2. Export the toolchain:

```console
$ source /opt/fslc-xwayland/<version>/environment-setup-cortexa53-crypto-fslc-linux
```

3. Search for the OpenCL header file:

```console
$ find / -iname "cl.h" 2> /dev/null
```
Output:

```console
/opt/fslc-xwayland/<version>/sysroots/cortexa53-crypto-fslc-linux/usr/include/CL/cl.h
```

4. Set the enviroment variable:

```console
$ export ROOTFS_DIR=/opt/fslc-xwayland/<version>/sysroots/cortexa53-crypto-fslc-linux
```

5. To compile the exampleS, just run the following command in the respective folder:

```console
$ make
```
6. Copy the examples to the module, and execute them.


## Examples

### Sum Array

|                    | DART-MX8M-PLUS | SPEAR-MX8 |
|--------------------|----------------|-----------|
| CPU Time (seconds) | 0.010300       |   -       |
| GPU Time (seconds) | 0.002497       |   -       |

* [Sum Array Example](https://github.com/varigit/var-demos/tree/master/opencl/sum)

### Square Array

|                    | DART-MX8M-PLUS | SPEAR-MX8 |
|--------------------|----------------|-----------|
| CPU Time (seconds) | 0.011486       |   -       |
| GPU Time (seconds) | 0.002488       |   -       |

* [Square Array Example](https://github.com/varigit/var-demos/tree/master/opencl/square)

### Fibonacci

|                    |  n  | DART-MX8M-PLUS | SPEAR-MX8 |
|--------------------|-----|----------------|-----------|
| CPU Time (seconds) | 30  | 0.000006       |   -       |
| CPU Time (seconds) | 90  | 0.000007       |   -       |
| GPU Time (seconds) | 30  | 0.000085       |   -       |
| GPU Time (seconds) | 92  | 0.000109       |   -       |

* [Fibonacci Example](https://github.com/varigit/var-demos/tree/master/opencl/fib)


