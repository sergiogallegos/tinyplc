#include "tinyplc/loader.h"
#include <string.h>
static bool separate(const void *a, size_t an, const void *b, size_t bn)
{
    uintptr_t x = (uintptr_t)a, y = (uintptr_t)b;
    return x <= UINTPTR_MAX - an && y <= UINTPTR_MAX - bn &&
           (x + an <= y || y + bn <= x);
}
bool tinyplc_loader_init(tinyplc_loader *l, uint8_t *a, uint8_t *b, int active,
                         bool allowed)
{
    if (!l || !a || !b || active < -1 || active > 1 ||
        !separate(a, TPLC_CODE_CAPACITY, b, TPLC_CODE_CAPACITY) ||
        !separate(l, sizeof *l, a, TPLC_CODE_CAPACITY) ||
        !separate(l, sizeof *l, b, TPLC_CODE_CAPACITY))
        return false;
    memset(l, 0, sizeof *l);
    l->code[0] = a;
    l->code[1] = b;
    l->allow_unsigned = allowed;
    l->next_transfer = 1;
    l->next_generation = active < 0 ? 1 : 2;
    if (active >= 0) {
        l->slots[active].state = TPLC_SLOT_ACTIVE;
        l->slots[active].generation = 1;
    }
    return true;
}
static void discard(tinyplc_loader *l)
{
    memset(&l->slots[l->receiving], 0, sizeof l->slots[0]);
    l->transfer_id = 0;
    l->total = 0;
    l->next_offset = 0;
    l->last_bytes = 0;
}
void tinyplc_loader_expire(tinyplc_loader *l, uint32_t now)
{
    if (l->transfer_id &&
        (uint32_t)(now - l->last_ms) >= TPLC_TRANSFER_TIMEOUT_MS)
        discard(l);
}
uint32_t tinyplc_loader_begin(tinyplc_loader *l, uint32_t total, uint32_t now,
                              uint32_t *id, uint32_t *base)
{
    tinyplc_loader_expire(l, now);
    if (total < TPLC_PACKAGE_BYTES + 4 + TPLC_TAG_BYTES ||
        total > TPLC_PACKAGE_BYTES_MAX)
        return TPLC_STATUS_BAD_REQUEST;
    if (!l->allow_unsigned)
        return TPLC_STATUS_UNSUPPORTED;
    if (l->transfer_id || !l->next_transfer || !l->next_generation ||
        l->slots[0].state == TPLC_SLOT_PENDING ||
        l->slots[1].state == TPLC_SLOT_PENDING)
        return TPLC_STATUS_BUSY;
    unsigned slot = 2;
    for (unsigned i = 0; i < 2; ++i) {
        if (l->slots[i].state == TPLC_SLOT_EMPTY) {
            slot = i;
            break;
        }
        if (l->slots[i].state == TPLC_SLOT_READY ||
            l->slots[i].state == TPLC_SLOT_PREVIOUS)
            slot = i;
    }
    if (slot == 2)
        return TPLC_STATUS_BUSY;
    memset(&l->slots[slot], 0, sizeof l->slots[slot]);
    l->slots[slot].state = TPLC_SLOT_RECEIVING;
    l->receiving = slot;
    l->total = total;
    l->next_offset = 0;
    l->last_bytes = 0;
    l->transfer_id = l->next_transfer++;
    l->last_ms = now;
    *id = l->transfer_id;
    *base = slot == 0 ? TPLC_SLOT_A_BASE : TPLC_SLOT_B_BASE;
    return TPLC_STATUS_OK;
}
uint32_t tinyplc_loader_chunk(tinyplc_loader *l, uint32_t id, uint32_t offset,
                              const uint8_t *bytes, uint32_t count,
                              uint32_t now, uint32_t *next)
{
    tinyplc_loader_expire(l, now);
    if (!id || id != l->transfer_id || !bytes || !count ||
        count > TPLC_CHUNK_BYTES_MAX || !tplc_range(l->total, offset, count))
        return TPLC_STATUS_BAD_REQUEST;
    if (l->last_bytes && offset == l->last_offset && count == l->last_bytes &&
        memcmp(l->staging + offset, bytes, count) == 0) {
        l->last_ms = now;
        *next = l->next_offset;
        return TPLC_STATUS_OK;
    }
    if (offset != l->next_offset)
        return TPLC_STATUS_BAD_REQUEST;
    /* memmove also permits trusted adapters to pass an overlapping staging view. */
    memmove(l->staging + offset, bytes, count);
    l->next_offset += count;
    l->last_offset = offset;
    l->last_bytes = count;
    l->last_ms = now;
    *next = l->next_offset;
    return TPLC_STATUS_OK;
}
uint32_t tinyplc_loader_end(tinyplc_loader *l, uint32_t id, uint32_t now,
                            uint32_t *generation)
{
    tinyplc_loader_expire(l, now);
    if (!id || id != l->transfer_id || l->next_offset != l->total)
        return TPLC_STATUS_BAD_REQUEST;
    tinyplc_package p;
    uint32_t status = tinyplc_package_validate(
        l->staging, l->total,
        l->receiving == 0 ? TPLC_SLOT_A_BASE : TPLC_SLOT_B_BASE,
        l->allow_unsigned, &p);
    if (status != TPLC_STATUS_OK) {
        discard(l);
        return status;
    }
    if (!l->next_generation) {
        discard(l);
        return TPLC_STATUS_BUSY;
    }
    tinyplc_slot *s = &l->slots[l->receiving];
    /* Only now touch inactive executable storage. The board adapter must map it
     * writable/XN here, keep it inaccessible to the worker, then seal it. */
    memset(l->code[l->receiving], 0, TPLC_CODE_CAPACITY);
    memcpy(l->code[l->receiving], p.payload, p.payload_bytes);
    memcpy(s->tags, p.tags, p.tag_count * TPLC_TAG_BYTES);
    s->payload_bytes = p.payload_bytes;
    s->entry = p.entry;
    s->schema_crc = p.schema_crc;
    s->tag_count = p.tag_count;
    s->generation = l->next_generation++;
    s->state = TPLC_SLOT_READY;
    *generation = s->generation;
    l->transfer_id = 0;
    l->total = 0;
    l->next_offset = 0;
    l->last_bytes = 0;
    return TPLC_STATUS_OK;
}
