#include "tinyplc/scan.h"
#include <assert.h>
#include <stdio.h>
static tinyplc_scan_state s;
static const uint8_t types[] = {1, 1, 2}, classes[] = {1, 2, 3};
static uint32_t in[3], work[3], now, calls, pin, output_cost, mode;
static tinyplc_native_diagnostic diag;
static uint32_t clock_cycles(void) { return now; }
static void output(const uint32_t *cells) { pin = cells[1]; now += output_cost; }
static uint32_t program(const uint32_t *inputs, uint32_t *working, uint32_t count,
                        tinyplc_native_diagnostic *d)
{
    assert(count == 3); ++calls;
    working[1] = !inputs[0]; working[2] += 1;
    if (mode == 1) { d->line = 7; return 5; }
    if (mode == 2) working[1] = 2;
    if (mode == 3) working[0] = 1;
    if (mode == 4) now += 100;
    return mode == 5 ? 999 : 0;
}
static void reset(void)
{
    assert(!tinyplc_scan_init(&s, 3, types, classes));
    now = calls = pin = output_cost = mode = 0;
    in[0] = in[1] = in[2] = 0;
}
static uint32_t step(uint32_t start)
{ return tinyplc_scan_step(&s, in, work, &diag, program, clock_cycles, output, start, 100); }
int main(void)
{
    reset(); assert(!step(0) && pin == 1 && s.committed[2] == 1);
    in[0] = 1; assert(!step(0) && pin == 0 && s.committed[2] == 2);
    for (mode = 1; mode <= 5; ++mode) {
        uint32_t test = mode;
        reset(); assert(!step(0)); mode = test;
        uint32_t expected[] = {0, 5, TINYPLC_SCAN_BAD_STATE, TINYPLC_SCAN_BAD_STATE,
                              TINYPLC_SCAN_OVERRUN, 999};
        assert(step(0) == expected[test] && pin == 0 && s.committed[2] == 1);
        assert(calls == 2); mode = 0;
        assert(step(0) == expected[test] && calls == 2 && pin == 0);
        mode = test;
    }
    reset(); in[0] = 2; assert(step(0) == 8 && calls == 0 && pin == 0);
    reset(); output_cost = 100;
    assert(step(0) == TINYPLC_SCAN_OVERRUN && s.committed[2] == 0 && pin == 0);
    reset(); now = 5; assert(!step(UINT32_MAX - 10)); /* counter wrap */
    reset(); now = 100; assert(step(0) == TINYPLC_SCAN_OVERRUN && pin == 0);
    reset(); assert(tinyplc_scan_step(&s, in, work, &diag, program, clock_cycles,
                                    output, 0, 0) == TINYPLC_SCAN_OVERRUN && calls == 0);
    assert(tinyplc_scan_init(&s, 65, types, classes) == TINYPLC_SCAN_BAD_LAYOUT);
    assert(s.count == 0);
    uint8_t bad[] = {1, 9, 2};
    assert(tinyplc_scan_init(&s, 3, bad, classes) == TINYPLC_SCAN_BAD_LAYOUT);
    assert(tinyplc_scan_init(&s, 3, types, bad) == TINYPLC_SCAN_BAD_LAYOUT);
    reset(); assert(!step(0));
    puts("scan transaction: success, dirty faults, latch/reset, input/state checks, deadline and wrap passed");
}
