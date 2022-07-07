# Makefile for Square Array Example CPU/GPU
#
# MIT License
# Copyright 2022 Variscite LTD
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

CPU_EXAMPLE = fib_cpu
GPU_EXAMPLE = fib_gpu

CXX ?= /usr/bin/aarch64-linux-gnu-gcc
DEL_FILE = rm -rf
TARGET_PATH_LIB = $(ROOTFS_DIR)/usr/lib
TARGET_PATH_INCLUDE = $(ROOTFS_DIR)/usr/include

CPU_CFLAGS = -Wall -Wextra -std=c11 -O0
CPU_LFLAGS = 

GPU_CFLAGS = -Wall -Wextra -std=c11 -O0 -fsigned-char -DEGL_API_FB -DGPU_TYPE_VIV -DGL_GLEXT_PROTOTYPES -DENABLE_GPU_RENDER_20 -I../include -I$(TARGET_PATH_INCLUDE)
GPU_LFLAGS = -Wl,--library-path=$(TARGET_PATH_LIB),-rpath-link=$(TARGET_PATH_LIB) -lm -lglib-2.0 -lOpenCL -lCLC -ldl -lpthread

CPU_OBJECTS = $(CPU_EXAMPLE).o
GPU_OBJECTS = $(GPU_EXAMPLE).o

all: $(CPU_EXAMPLE) $(GPU_EXAMPLE)

$(CPU_EXAMPLE): $(CPU_OBJECTS)
	$(CC) $(CPU_LFLAGS) -o $(CPU_EXAMPLE) $(CPU_OBJECTS)
$(CPU_EXAMPLE).o: $(CPU_EXAMPLE).c
	$(CC) $(CPU_CFLAGS) -c -o $(CPU_EXAMPLE).o $(CPU_EXAMPLE).c

$(GPU_EXAMPLE): $(GPU_OBJECTS)
	$(CC) $(GPU_LFLAGS) -o $(GPU_EXAMPLE) $(GPU_OBJECTS)
$(GPU_EXAMPLE).o: $(GPU_EXAMPLE).c
	$(CC) $(GPU_CFLAGS) -c -o $(GPU_EXAMPLE).o $(GPU_EXAMPLE).c

clean:
	rm -rf $(CPU_EXAMPLE) $(CPU_EXAMPLE).o $(GPU_EXAMPLE) $(GPU_EXAMPLE).o
