/* Binary Search Example for CPU
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

#define ARR_SIZE    1000000

#include <stdio.h>
#include <stdlib.h>
#include <time.h>


int binary_search(long *arr, long n, int min, int max) {
    int mid;

    while (min <= max) {
        mid = min + (max - min) / 2;

        if (arr[mid] == n)
            return mid;

        if (arr[mid] < n) {
            min = mid + 1;
        } else {
            max = mid - 1;
        }
    }

    return -1;
}


void fill_array(long *arr) {
    int i;

    srand(time(NULL));
    arr[0] = rand() % 10;

    for (i = 1; i < ARR_SIZE; i++)
        arr[i] = arr[i - 1] + (rand() % 10);
}


int main(int argc, char *argv[]) {
    int i, result;
    long arr[ARR_SIZE];
    long n;
    double cpu_time = 0.0;
    clock_t start = 0;
    clock_t end = 0;

    if (argc != 2) {
        fprintf(stderr, "Usage of %s: [number]\n", argv[0]);
        return EXIT_FAILURE;
    }

    n = atoi(argv[1]);

    fill_array(arr);

    start = clock();
    result = binary_search(arr, n, 0, ARR_SIZE - 1);
    end = clock();

    cpu_time = ((double)(end - start)) / CLOCKS_PER_SEC;

    if (result >= 0)
        printf("%ld found at index %d of the array\n", n, result);
    else
        printf("%ld not found in the array\n", n);
    printf("[Execution Time] >> %lf seconds.\n", cpu_time);

    return EXIT_SUCCESS;
}
