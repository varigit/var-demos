/* Sum Array Example for CPU
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

#define ARRAY_SIZE 600000

int main(void)
{
    static int a[ARRAY_SIZE];
    static int b[ARRAY_SIZE];

    static int z[ARRAY_SIZE];
    static volatile int v[ARRAY_SIZE];

    int i = 0;
    clock_t start = 0;
    clock_t end = 0;
    double cpu_time = 0.0;

    for (i = 0; i < ARRAY_SIZE; i++) {
        a[i] = 2 * i;
        b[i] = 3 * i;
    }

    start = clock();
    for (i = 0; i < ARRAY_SIZE; i++) {
        z[i] = a[i] + b[i];
    }
    end = clock();

    for (i = 0; i < ARRAY_SIZE; i++) {
        v[i] = z[i];
    }

    cpu_time = ((double)(end - start)) / CLOCKS_PER_SEC;
    printf("[Execution Time] >> %f seconds.\n", cpu_time);

    return EXIT_SUCCESS;
}
