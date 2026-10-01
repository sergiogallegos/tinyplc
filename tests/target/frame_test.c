#include "exception_frame.h"
#include <assert.h>
#include <stdio.h>
int main(void)
{
    assert(plc_frame_address_valid(0x20018820, 0xfffffffd, 1));
    assert(plc_frame_address_valid(0x20018fd8, 0xfffffffd, 1));
    assert(!plc_frame_address_valid(0x20018818, 0xfffffffd, 1));
    assert(!plc_frame_address_valid(0x20018fe0, 0xfffffffd, 1));
    assert(!plc_frame_address_valid(0x20018824, 0xfffffffd, 1));
    assert(!plc_frame_address_valid(0x20018200, 0xfffffffd, 1));
    assert(!plc_frame_address_valid(UINTPTR_MAX, 0xfffffffd, 1));
    assert(!plc_frame_address_valid(0x20018fd8, 0xfffffff9, 1));
    assert(!plc_frame_address_valid(0x20018fd8, 0xffffffed, 5));
    assert(!plc_frame_address_valid(0x20018fd8, 0xfffffffd, 0));
    assert(!plc_frame_address_valid(0x20018fd8, 0xfffffffd, 5));
    assert(plc_frame_xpsr_valid(0x41000000));
    assert(plc_frame_xpsr_valid(0x01000200));
    assert(!plc_frame_xpsr_valid(0x0100000b));
    assert(!plc_frame_xpsr_valid(0));
    puts("exception frame: stack bounds, alignment, privilege, PSP, FP and xPSR passed");
}
