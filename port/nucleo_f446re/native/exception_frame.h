/* Pure validation predicates, shared with host boundary tests. */
#ifndef TINYPLC_EXCEPTION_FRAME_H
#define TINYPLC_EXCEPTION_FRAME_H
#include <stdint.h>
static inline int plc_frame_address_valid(uintptr_t p, uint32_t exc,
                                          uint32_t control)
{
    /* SPSEL reads zero in Handler mode. EXC_RETURN proves thread/PSP return;
     * nPRIV must remain set and FPCA must be clear for the integer-only ABI.
     * Require room for a basic frame plus a possible stack-alignment word. */
    return exc == UINT32_C(0xfffffffd) && (control & 5) == 1 && !(p & 7) &&
           p >= UINT32_C(0x20018820) && p <= UINT32_C(0x20019000) - 36;
}
static inline int plc_frame_xpsr_valid(uint32_t xpsr)
{
    return (xpsr & UINT32_C(0x010001ff)) == UINT32_C(0x01000000);
}
#endif
