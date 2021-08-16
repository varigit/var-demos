#include <gpiod.h>
#include <stdio.h>
#include <unistd.h>
#include <stdlib.h>
#include <string.h>

#ifndef    CONSUMER
#define    CONSUMER    "Variscite"
#endif

typedef enum
{
    DART_MX8M,
    /* TODO: Add others */
    SOM_UNKNOWN
} som_t;

/**
 * Parse /sys/devices/soc0/machine to determine the current Variscite SoM
 */
som_t detect_som() {
    FILE *fptr;
    som_t som = SOM_UNKNOWN;
    char machine[200];
    int len;
    if ((fptr = fopen("/sys/devices/soc0/machine","r")) == NULL){
           printf("Error: Failed to open /sys/devices/soc0/machine\n");
    } else {
       len = fread(machine, sizeof(char), 200, fptr);
       if(len > 0) {
            if(strstr(machine, " DART-MX8M ")) {
                som = DART_MX8M;
            }
       } else {
            printf("Error: Failed to read /sys/devices/soc0/machine\n");
       }
   }

   return som;
}


int main(int argc, char **argv)
{
    // Make volatile so we can debug
    volatile unsigned int i, ret, val;
    struct gpiod_chip *chip;
    struct gpiod_line *line;
    char * chipname = 0;
    unsigned int line_num;

    // Detect SOM and configure gpiochip and line_num
    switch(detect_som()) {
        case DART_MX8M:
            chipname = "gpiochip6"; // dt8mcustomboard i2c gpio expander
            line_num = 7;            // i2c gpio expander gpio #7
        break;
        /* Todo: Add other SoMs */
        default:
        break;
    }

    if (!chipname) {
        goto end;
    }

    chip = gpiod_chip_open_by_name(chipname);
    if (!chip) {
        perror("Open chip failed\n");
        goto end;
    }

    line = gpiod_chip_get_line(chip, line_num);
    if (!line) {
        perror("Get line failed\n");
        goto close_chip;
    }

    ret = gpiod_line_request_output(line, CONSUMER, 0);
    if (ret < 0) {
        perror("Request line as output failed\n");
        goto release_line;
    }

    /* Blink 5 times */
    val = 0;
    for (i = 0; i < 5; i++) {
        ret = gpiod_line_set_value(line, val);
        if (ret < 0) {
            perror("Set line output failed\n");
            goto release_line;
        }
        printf("Output %u on line #%u\n", val, line_num);
        sleep(1);
        val = !val;
    }

release_line:
    gpiod_line_release(line);
close_chip:
    gpiod_chip_close(chip);
end:
    return 0;
}
