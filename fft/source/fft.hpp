/*
 * Copyright 2022 Variscite LTD 
 *
 * This example was copied and modified respecting the MIT license terms from
 * the below project. (06/26/2022)
 * 
 ** Free FFT and Convolution (C++)
 ** 
 ** Copyright 2021 Project Nayuki (MIT License)
 ** https://www.nayuki.io/page/free-small-fft-in-multiple-languages
 ** 
 **/

#pragma once

#include <complex>
#include <vector>


namespace FFT {
	/* 
	 * Computes the discrete Fourier transform (DFT) of the given complex vector
	 * storing the result back into the vector. The vector can have any length.
	 * This is a wrapper function. The inverse transform does not perform
	 * scaling, so it is not a true inverse.
	 */
	void transform(std::vector<std::complex<double> > &vec, bool inverse);
	/* 
	 * Computes the discrete Fourier transform (DFT) of the given complex vector
	 * storing the result back into the vector. The vector's length must be a
	 * power of 2. Uses the Cooley-Tukey decimation-in-time radix-2 algorithm.
	 */
	void transformRadix2(std::vector<std::complex<double> > &vec, bool inverse);	
}
