/* Portable, single-owner staging. No activation, MPU changes, or execution. */
#ifndef TINYPLC_LOADER_H
#define TINYPLC_LOADER_H
#include "tinyplc/package.h"
typedef struct {
    uint32_t state, generation, payload_bytes, entry, schema_crc;
    uint16_t tag_count;
    uint8_t tags[TPLC_TAG_LIMIT * TPLC_TAG_BYTES];
} tinyplc_slot;
typedef struct {
    uint8_t staging[TPLC_PACKAGE_BYTES_MAX];
    uint8_t *code[2]; /* Caller-owned disjoint CODE_CAPACITY buffers. */
    tinyplc_slot slots[2];
    uint32_t total, next_offset, transfer_id, next_transfer, next_generation;
    uint32_t last_ms, last_offset, last_bytes;
    unsigned receiving;
    bool allow_unsigned;
} tinyplc_loader;
/* active_slot=-1 means empty; 0/1 protects a pre-existing firmware-linked image
 * as generation 1 (its schema remains unavailable through this staging API).
 * All buffers/loader must be disjoint and alive throughout use. No malloc. */
bool tinyplc_loader_init(tinyplc_loader *l, uint8_t *a, uint8_t *b,
                         int active_slot, bool allow_unsigned);
void tinyplc_loader_expire(tinyplc_loader *l, uint32_t now_ms);
/* Call with a monotonic modulo-u32 ms clock, polling at least every 2^31 ms.
 * All APIs require one serialized owner; no concurrent scan/comms mutation.
 * Output pointers must be valid and disjoint from loader/input storage.
 * Return wire status; output parameters change only on success. */
uint32_t tinyplc_loader_begin(tinyplc_loader *l, uint32_t total, uint32_t now,
                              uint32_t *id, uint32_t *base);
uint32_t tinyplc_loader_chunk(tinyplc_loader *l, uint32_t id, uint32_t offset,
                              const uint8_t *bytes, uint32_t count,
                              uint32_t now, uint32_t *next);
uint32_t tinyplc_loader_end(tinyplc_loader *l, uint32_t id, uint32_t now,
                            uint32_t *generation);
#endif
