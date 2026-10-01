/* M0 scheduling demonstration. M1 replaces the placeholder with the C VM;
 * M3 adds TCP. Absolute deadlines avoid adding work time to every period. */
#include <errno.h>
#include <stdio.h>
#include <time.h>
#include "toyplc/limits.h"

int main(void)
{
    struct timespec deadline;
    if (clock_gettime(CLOCK_MONOTONIC, &deadline) != 0) {
        perror("clock_gettime");
        return 1;
    }
    unsigned output = 0;
    for (unsigned scan = 0; scan < 5; ++scan) {
        unsigned input = scan & 1u; /* Read simulated input image. */
        output = !input;           /* Placeholder for VM execution. */
        /* Output publication will go here once core state exists. */
        deadline.tv_nsec += (long)PLC_SCAN_PERIOD_MS * 1000000L;
        if (deadline.tv_nsec >= 1000000000L) {
            deadline.tv_nsec -= 1000000000L;
            ++deadline.tv_sec;
        }
        for (;;) {
            struct timespec now, delay;
            if (clock_gettime(CLOCK_MONOTONIC, &now) != 0) {
                perror("clock_gettime");
                return 1;
            }
            delay.tv_sec = deadline.tv_sec - now.tv_sec;
            delay.tv_nsec = deadline.tv_nsec - now.tv_nsec;
            if (delay.tv_nsec < 0) { --delay.tv_sec; delay.tv_nsec += 1000000000L; }
            if (delay.tv_sec < 0) break;
            if (nanosleep(&delay, NULL) == 0) break;
            if (errno != EINTR) { perror("nanosleep"); return 1; }
        }
    }
    printf("M0 scans=5 period_ms=%u output=%u\n", PLC_SCAN_PERIOD_MS, output);
    return 0;
}
