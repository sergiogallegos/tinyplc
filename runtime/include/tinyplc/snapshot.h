/* Single producer/single consumer owned mailbox. No pointers into program slots.
 * Initialize before tasks start. Producer and consumer each have one task owner. */
#ifndef TINYPLC_SNAPSHOT_H
#define TINYPLC_SNAPSHOT_H
#include <stdatomic.h>
#include "wire.h"
_Static_assert(ATOMIC_INT_LOCK_FREE == 2, "snapshot indices must be lock-free");
typedef struct {
    uint64_t scan;
    uint32_t generation;
    uint8_t count;
    uint8_t records[TPLC_TAG_LIMIT][TPLC_TAG_VALUE_BYTES];
} tinyplc_snapshot;
typedef struct {
    tinyplc_snapshot buffers[3];
    atomic_uint middle;
    unsigned back, front;
    bool leased;
    uint32_t last_ms;
} tinyplc_snapshots;
void tinyplc_snapshots_init(tinyplc_snapshots *);
/* Stable validated schema and committed cells supplied by the scan owner. */
void tinyplc_snapshot_publish(tinyplc_snapshots *, uint32_t, uint64_t, unsigned,
                              const uint8_t *, const uint32_t *);
size_t tinyplc_snapshot_read(tinyplc_snapshots *, const uint8_t *, size_t,
                             uint32_t, uint8_t *);
#endif
