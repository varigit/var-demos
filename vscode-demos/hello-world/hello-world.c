/* Copyright 2023 Variscite Ltd */

/* Include the standard input/output library. This library provides us with
 * functions like printf() and scanf().
 */
#include <stdio.h>

/* Include the standard library. This library provides us with functions like
 * exit() and malloc(). Here, it provides the EXIT_SUCCESS macro.
 */
#include <stdlib.h>

/* Main function. The operating system runs this function when the program
 * starts. The void in the parentheses means this function takes no arguments.
 */
int main(void)
{
    /* Call the printf function from the stdio library to print the string
     * "Hello, World!" to the console. The '\n' is a special character that
     * represents a newline, so the cursor will move to the next line after
     * printing the string.
     */
    printf("Hello, World!\n");

    /* Return the EXIT_SUCCESS macro (which is typically defined to be 0) to
     * the operating system, indicating that the program has successfully
     * completed. This is a convention in C programming.
     */
    return EXIT_SUCCESS;
}
