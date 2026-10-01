/* Finite native demonstration of a Rust/LLVM-compiled button_led.st program.
 * This is an ABI exercise, not a scheduler, loader, or hardware port. */
#include "scan_abi.h"
#include <inttypes.h>
#include <stdio.h>
#include <string.h>

int main(void)
{
    if (tinyplc_abi_version != 1 || tinyplc_tag_count > 64) return 1;
    int button = -1, led = -1, counter = -1;
    for (uint32_t i = 0; i < tinyplc_tag_count; ++i) {
        if (!strcmp(tinyplc_tag_names[i], "BTN")) button = (int)i;
        if (!strcmp(tinyplc_tag_names[i], "LED")) led = (int)i;
        if (!strcmp(tinyplc_tag_names[i], "N")) counter = (int)i;
    }
    if (button < 0 || led < 0 || counter < 0) return 1;
    uint32_t cells[64] = {0};
    const uint32_t inputs[] = {0, 1, 1, 0, 0};
    for (unsigned scan = 0; scan < sizeof inputs / sizeof inputs[0]; ++scan) {
        tinyplc_diagnostic diagnostic;
        cells[button] = inputs[scan];
        uint32_t fault = tinyplc_scan(cells, tinyplc_tag_count, &diagnostic);
        if (fault) {
            fprintf(stderr, "fault=%" PRIu32 " at %" PRIu32 ":%" PRIu32 "\n",
                    fault, diagnostic.line, diagnostic.column);
            return 1;
        }
    }
    printf("R1 AOT scans=5 LED=%" PRIu32 " N=%" PRIu32 "\n", cells[led], cells[counter]);
    return cells[led] != 1 || cells[counter] != 2;
}
