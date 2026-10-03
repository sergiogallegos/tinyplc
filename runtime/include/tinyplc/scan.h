/* Project-owned scan transaction. See docs/scan-runtime.md and references.md. */
#ifndef TINYPLC_SCAN_H
#define TINYPLC_SCAN_H
#include "tinyplc/native_abi.h"
#define TINYPLC_SCAN_BAD_LAYOUT 256u
#define TINYPLC_SCAN_BAD_STATE 257u
#define TINYPLC_SCAN_OVERRUN 258u
/* Trusted callbacks must return promptly. All buffers are caller-owned, static,
 * disjoint, and at least count cells. Only the scan owner may use this object.
 * This API is NOT a native-code sandbox. */
typedef struct {
    uint32_t count, fault;
    uint8_t types[64], classes[64];
    uint32_t committed[64];
} tinyplc_scan_state;
typedef uint32_t (*tinyplc_cycle_clock)(void);
typedef void (*tinyplc_output_commit)(const uint32_t *cells);
uint32_t tinyplc_scan_init(tinyplc_scan_state *state, uint32_t count,
                           const uint8_t *types, const uint8_t *classes);
/* start is sampled BEFORE physical input acquisition. budget is in cycles,
 * nonzero and < 2^31. Unsigned elapsed subtraction tolerates one clock wrap.
 * A fault latches until reinitialization/reset; VAR state survives failed scans.
 * The output hook receives all-zero OUTPUT cells on every faulted scan. */
uint32_t tinyplc_scan_step(tinyplc_scan_state *state, const uint32_t *inputs,
                           uint32_t *working,
                           tinyplc_native_diagnostic *diagnostic,
                           tinyplc_native_entry entry,
                           tinyplc_cycle_clock clock,
                           tinyplc_output_commit output, uint32_t start,
                           uint32_t budget);
#endif
