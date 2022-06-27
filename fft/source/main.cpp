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

#include <chrono>
#include <complex>
#include <cstdlib>
#include <iostream>
#include <random>
#include <utility>
#include <vector>
#include "fft.hpp"

using std::complex;
using std::cout;
using std::endl;
using std::vector;


// Private function prototypes
static void testFft(int n);
static vector<complex<double> > randomComplexes(int n);

// Random number generation
std::default_random_engine randGen((std::random_device())());


/*---- Main and test functions ----*/
int main() {
	// Test power-of-2 size FFTs
	for (int i = 4; i <= 16; i++)
		testFft(1 << i);

	return EXIT_SUCCESS;
}


static void testFft(int n) {
	vector<complex<double>> input = randomComplexes(n);
	std::chrono::steady_clock::time_point begin = std::chrono::steady_clock::now();
	FFT::transform(input, false);
	std::chrono::steady_clock::time_point end = std::chrono::steady_clock::now();
	cout << "fftsize = " << n << " ";
    	cout << "elapsed time = " << std::chrono::duration_cast<std::chrono::microseconds>(end - begin).count() << endl;
}


static vector<complex<double> > randomComplexes(int n) {
	std::uniform_real_distribution<double> valueDist(-1.0, 1.0);
	vector<complex<double> > result;
	for (int i = 0; i < n; i++)
		result.push_back(complex<double>(valueDist(randGen), valueDist(randGen)));
	return result;
}
