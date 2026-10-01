/* Five scans through the actual core VM. M3 adds TCP and program download.
 * Absolute deadlines avoid adding work time to every period. */
#include <errno.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
#include "tinyplc/core.h"

static plc_runtime runtime;
static plc_workspace workspace;
static const plc_binding bindings[] = {{"BTN", PLC_BOOL, PLC_INPUT}, {"LED", PLC_BOOL, PLC_OUTPUT}};
static const plc_profile profile = {bindings, 2};

/* Hand-encoded button_led.st until the M2 compiler exists. */
static const uint8_t demo_code[] = {
    PLC_LOAD, 0, PLC_JZ, 16, 0,
    PLC_LOAD, 2, PLC_PUSH, PLC_DINT, 1, 0, 0, 0, PLC_ADD, PLC_STORE, 2,
    PLC_LOAD, 0, PLC_NOT, PLC_STORE, 1, PLC_HALT
};
static void u32(uint8_t *b, uint32_t v) { for (unsigned j = 0; j < 4; ++j) b[j] = (uint8_t)(v >> (8 * j)); }
static bool load_demo(void)
{
    uint8_t bytes[PLC_HEADER_BYTES + 3 * PLC_TAG_BYTES + sizeof demo_code] = {0};
    memcpy(bytes, "TPLC", 4); bytes[4] = 1; bytes[6] = PLC_HEADER_BYTES;
    bytes[8] = sizeof demo_code; bytes[10] = 3; bytes[12] = 2;
    u32(bytes + 16, sizeof bytes);
    const char *names[] = {"BTN", "LED", "N"};
    for (unsigned j = 0; j < 3; ++j) {
        uint8_t *t = bytes + PLC_HEADER_BYTES + j * PLC_TAG_BYTES;
        t[0] = j == 2 ? PLC_DINT : PLC_BOOL; t[1] = (uint8_t)(j + 1);
        memcpy(t + 4, names[j], strlen(names[j]));
    }
    memcpy(bytes + PLC_HEADER_BYTES + 3 * PLC_TAG_BYTES, demo_code, sizeof demo_code);
    u32(bytes + 20, plc_image_crc32(bytes, sizeof bytes));
    uint32_t generation;
    plc_diagnostic d;
    plc_runtime_init(&runtime);
    if (!plc_runtime_lock_free(&runtime) ||
        plc_runtime_stage(&runtime, bytes, sizeof bytes, &profile, &workspace, &generation, &d) != PLC_OK) return false;
    return plc_runtime_activate(&runtime, generation) == PLC_OK && plc_runtime_boundary(&runtime);
}

int main(void)
{
    if (!load_demo()) { fputs("demo image validation/activation failed\n", stderr); return 1; }
    struct timespec deadline;
    if (clock_gettime(CLOCK_MONOTONIC, &deadline) != 0) {
        perror("clock_gettime");
        return 1;
    }
    for (unsigned scan = 0; scan < 5; ++scan) {
        plc_values inputs = {{0}};
        inputs.cell[0] = scan & 1u;
        if (plc_runtime_scan(&runtime, &inputs, PLC_INSTRUCTION_BUDGET) != PLC_FAULT_NONE) {
            fprintf(stderr, "VM fault: %s\n", runtime.diagnostic.reason); return 1;
        }
        /* A real port writes active values to GPIO here, before boundary. */
        (void)plc_runtime_boundary(&runtime);
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
    plc_slot *active = atomic_load(&runtime.active);
    printf("M1 scans=5 period_ms=%u LED=%u N=%u generation=%u\n",
           PLC_SCAN_PERIOD_MS, (unsigned)active->values.cell[1],
           (unsigned)active->values.cell[2], (unsigned)active->generation);
    return 0;
}
