# OpenCL Examples

To build the examples, please follow the next instructions.

## Build

1. Build a Yocto toolchain by following the [Variscite Wiki](https://variwiki.com/) instructions.

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

## Examples

* [Sum Array](https://github.com/varigit/var-demos/tree/master/opencl/sum)
* [Square Array](https://github.com/varigit/var-demos/tree/master/opencl/square)
* [Fibonacci](https://github.com/varigit/var-demos/tree/master/opencl/fib)

1. To compile the example, just run the following command:

```console
$ make
```
2. Copy the examples to the module, and execute them.



