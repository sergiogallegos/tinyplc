#ifndef TOYPLC_LIMITS_H
#define TOYPLC_LIMITS_H

/* Fixed capacities shared by both ports. There is no VM yet at M0. */
#define PLC_SCAN_PERIOD_MS 10u
#define PLC_MAX_CODE_BYTES 2048u
#define PLC_MAX_TAGS 64u
#define PLC_MAX_STACK 64u
#define PLC_INSTRUCTION_BUDGET 4096u

#endif
