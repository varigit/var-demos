/* Fibonacci Example for CPU
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

#include <stdio.h>
#include <stdlib.h>
#include <time.h>


long fib(long n)
{
    if (n <= 0)
        return 0;
    if (n > 0 && n < 3)
        return 1;

    long r = 0, n1 = 1, n2 = 1;
    for (long i = 2; i < n; i++) {
        r = n1 + n2;
        n1 = n2;
        n2 = r;
    }
    return r;
}

int main(int argc, char *argv[])
{
    long n, r;
    clock_t start = 0;
    clock_t end = 0;
    double cpu_time = 0.0;

    if (argc != 2) {
        fprintf(stderr, "Usage of %s: [number]\n", argv[0]);
        return EXIT_FAILURE;
    }

    n = atoi(argv[1]);

    start = clock();
    r = fib(n);
    end = clock();

    cpu_time = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("[Result] >> %ld\n", r);
    printf("[Execution Time] >> %lf seconds.\n", cpu_time);

    return EXIT_SUCCESS;
}
