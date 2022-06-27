# Copyright 2022 Variscite LTD 
#
# This example was copied and modified respecting the MIT license terms from
# the below project. (06/26/2022)
#  
## Free FFT and Convolution (C++)
##  
## Copyright 2021 Project Nayuki (MIT License)
## https://www.nayuki.io/page/free-small-fft-in-multiple-languages
 
CXX ?= /usr/bin/aarch64-linux-gnu-g++
CXXFLAGS := -Wall -pedantic-errors -Wextra -O3

OUT_NAME := fft

all: main

main: source/main.cpp source/fft.cpp source/fft.hpp Makefile
		$(CXX) $(CXXFLAGS) source/main.cpp source/fft.cpp -o $(OUT_NAME)

clean:
		$(RM) $(OUT_NAME)
