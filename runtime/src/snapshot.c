#include "tinyplc/snapshot.h"
#include "tinyplc/engineering.h"
#include <string.h>
/* The producer owns back, the consumer owns front, and middle is transferable.
 * Each exchange returns a distinct buffer and transfers ownership with release /
 * acquire ordering. The producer never touches front or waits for the reader.
 * A new enumeration exchanges front only when a newer publication exists.
 * Expiry releases the logical lease; retaining front physically still leaves
 * two buffers for unlimited publication. No shared pointer or refcount exists. */
#define DIRTY 4u
void tinyplc_snapshots_init(tinyplc_snapshots *m)
{
    memset(m, 0, sizeof *m);
    m->back = 0;
    m->front = 2;
    atomic_init(&m->middle, 1);
}
void tinyplc_snapshot_publish(tinyplc_snapshots *m, uint32_t generation,
                              uint64_t scan, unsigned count,
                              const uint8_t *tags, const uint32_t *cells)
{
    if (!generation || !scan || count > TPLC_TAG_LIMIT)
        return;
    tinyplc_snapshot *s = &m->buffers[m->back];
    s->generation = generation;
    s->scan = scan;
    s->count = (uint8_t)count;
    for (unsigned i = 0; i < count; ++i) {
        memcpy(s->records[i], tags + i * TPLC_TAG_BYTES,
               TPLC_TAG_VALUE_VALUE_OFFSET);
        tinyplc_put32(s->records[i], TPLC_TAG_VALUE_VALUE_OFFSET, cells[i]);
    }
    m->back = atomic_exchange_explicit(&m->middle, m->back | DIRTY,
                                       memory_order_acq_rel) &
              3u;
}
size_t tinyplc_snapshot_read(tinyplc_snapshots *m, const uint8_t *p, size_t n,
                             uint32_t now, uint8_t *r)
{
    r[0] = TPLC_STATUS_BAD_REQUEST;
    if (n != TPLC_READ_TAGS_REQUEST_BYTES)
        return 1;
    uint32_t generation = 0;
    uint64_t scan = 0;
    (void)tplc_read_u32(p, n, 0, &generation);
    (void)tplc_read_u64(p, n, 4, &scan);
    unsigned first = p[12], count = p[13];
    if (!count || count > TPLC_TAG_PAGE_LIMIT || (!scan && first))
        return 1;
    if (m->leased && (uint32_t)(now - m->last_ms) >= TPLC_SNAPSHOT_TIMEOUT_MS)
        m->leased = false;
    if (!scan) {
        m->leased = false;
        if (atomic_load_explicit(&m->middle, memory_order_acquire) & DIRTY)
            m->front = atomic_exchange_explicit(&m->middle, m->front,
                                                memory_order_acq_rel) &
                       3u;
        const tinyplc_snapshot *s = &m->buffers[m->front];
        if (!s->generation) {
            r[0] = TPLC_STATUS_NO_PROGRAM;
            return 1;
        }
        if (generation && generation != s->generation) {
            r[0] = TPLC_STATUS_BUSY;
            return 1;
        }
        m->leased = true;
    }
    const tinyplc_snapshot *s = &m->buffers[m->front];
    if (!m->leased ||
        (scan && (scan != s->scan || generation != s->generation))) {
        r[0] = TPLC_STATUS_BUSY;
        return 1;
    }
    if (first >= s->count)
        return 1;
    if (count > s->count - first)
        count = s->count - first;
    r[0] = 0;
    tinyplc_put32(r, 1, s->generation);
    tinyplc_put64(r, 5, s->scan);
    r[13] = (uint8_t)first;
    r[14] = (uint8_t)count;
    r[15] = s->count;
    memcpy(r + TPLC_READ_TAGS_RESPONSE_BYTES, s->records[first],
           count * TPLC_TAG_VALUE_BYTES);
    m->last_ms = now;
    if (first + count == s->count)
        m->leased = false;
    return TPLC_READ_TAGS_RESPONSE_BYTES + count * TPLC_TAG_VALUE_BYTES;
}
