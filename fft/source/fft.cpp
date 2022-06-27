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

#include <cstddef>
#include <cstdint>
#include <stdexcept>
#include <utility>

#include "fft.hpp"

using std::complex;
using std::size_t;
using std::uintmax_t;
using std::vector;


static size_t reverseBits(size_t val, int width)
{
	size_t result = 0;
	for (int i = 0; i < width; i++, val >>= 1)
		result = (result << 1) | (val & 1U);
	return result;
}

void FFT::transform(vector<complex<double> > &vec, bool inverse)
{
	size_t n = vec.size();
	if (n == 0)
		return;
	else if ((n & (n - 1)) == 0)
		transformRadix2(vec, inverse);
	else
		throw std::domain_error("Length is not a power of 2");
}

void FFT::transformRadix2(vector<complex<double> > &vec, bool inverse)
{
	size_t n = vec.size();
	int levels = 0;
	for (size_t temp = n; temp > 1U; temp >>= 1)
		levels++;
	if (static_cast<size_t>(1U) << levels != n)
		throw std::domain_error("Length is not a power of 2");

	vector<complex<double> > expTable(n / 2);
	for (size_t i = 0; i < n / 2; i++)
		expTable[i] = std::polar(1.0, (inverse ? 2 : -2) * M_PI * i / n);
	
	for (size_t i = 0; i < n; i++) {
		size_t j = reverseBits(i, levels);
		if (j > i)
			std::swap(vec[i], vec[j]);
	}
	
	for (size_t size = 2; size <= n; size *= 2) {
		size_t halfsize = size / 2;
		size_t tablestep = n / size;
		for (size_t i = 0; i < n; i += size) {
			for (size_t j = i, k = 0; j < i + halfsize; j++, k += tablestep) {
				complex<double> temp = vec[j + halfsize] * expTable[k];
				vec[j + halfsize] = vec[j] - temp;
				vec[j] += temp;
			}
		}
		if (size == n)
			break;
	}
}
