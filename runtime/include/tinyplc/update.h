/* R4 online transaction. Caller serializes operations; exactly one scan owner.
 * Reserve/arm/observe/retire are short. Plan runs in comms on pinned schemas;
 * prepare/finish run in the scan task. See docs/online-state.md. */
#ifndef TINYPLC_UPDATE_H
#define TINYPLC_UPDATE_H
#include "tinyplc/loader.h"
#include "tinyplc/scan.h"
#define TINYPLC_UPDATE_PLANNING 6u
#define TINYPLC_UPDATE_NO_MATCH 255u
typedef struct {
    tinyplc_loader *loader;
    uint32_t active, source, target, pending, requested;
    uint32_t kind, phase, outcome, source_generation;
    uint32_t saved_slot, saved_generation, saved_count, saved_entry,
        saved_schema;
    uint32_t saved[64];
    uint8_t map[64];
    uint32_t failed_generation, first_fault, recovery_fault, line, column;
    uint64_t failed_scan, completed_scan;
    uint32_t completed_generation;
} tinyplc_update;
_Static_assert(sizeof(tinyplc_update) <= 1024, "R4 static storage budget");
void tinyplc_update_init(tinyplc_update *, tinyplc_loader *, unsigned);
bool tinyplc_update_busy(const tinyplc_update *);
uint32_t tinyplc_update_reserve(tinyplc_update *, uint32_t kind,
                                uint32_t generation);
void tinyplc_update_plan(tinyplc_update *);
void tinyplc_update_arm(tinyplc_update *);
void tinyplc_update_retire(tinyplc_update *, unsigned);
/* True means a new state/descriptor was installed; caller creates fresh worker. */
bool tinyplc_update_prepare(tinyplc_update *, tinyplc_scan_state *, uint64_t);
/* Discard a failed trial before publishing; keep reservations until finish. */
void tinyplc_update_discard(tinyplc_update *, tinyplc_scan_state *);
void tinyplc_update_finish(tinyplc_update *, tinyplc_scan_state *,
                           const tinyplc_native_diagnostic *, uint64_t);
void tinyplc_update_status(const tinyplc_update *, uint8_t *);
#endif
