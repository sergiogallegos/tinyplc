#include "tinyplc/engineering.h"
#include <string.h>
void tinyplc_put16(uint8_t *b, size_t at, uint16_t v)
{
    b[at] = (uint8_t)v;
    b[at + 1] = (uint8_t)(v >> 8);
}
void tinyplc_put32(uint8_t *b, size_t at, uint32_t v)
{
    for (unsigned i = 0; i < 4; ++i)
        b[at + i] = (uint8_t)(v >> (8 * i));
}
void tinyplc_put64(uint8_t *b, size_t at, uint64_t v)
{
    for (unsigned i = 0; i < 8; ++i)
        b[at + i] = (uint8_t)(v >> (8 * i));
}
static uint32_t get(const uint8_t *b, size_t n, size_t at)
{
    uint32_t v = 0;
    (void)tplc_read_u32(b, n, at, &v);
    return v;
}
void tinyplc_frame_expire(tinyplc_framer *f, uint32_t now)
{
    if (f->used && (uint32_t)(now - f->last_ms) >= TPLC_FRAME_TIMEOUT_MS)
        f->used = 0;
}
void tinyplc_frame_feed(tinyplc_framer *f, uint8_t byte, uint32_t now,
                        tinyplc_frame_fn callback, void *ctx)
{
    tinyplc_frame_expire(f, now);
    f->last_ms = now;
    if (f->used == TPLC_FRAME_BYTES_MAX)
        f->used = 0;
    f->bytes[f->used++] = byte;
    /* On rejection discard just one byte; replay bounded remaining bytes.
     * This preserves a complete embedded frame without recursion/allocation. */
    while (f->used) {
        if (f->bytes[0] != TPLC_FRAME_START)
            goto drop;
        if (f->used < 3)
            return;
        uint16_t length = 0;
        (void)tplc_read_u16(f->bytes, f->used, 1, &length);
        if (length < TPLC_FRAME_LENGTH_MIN || length > TPLC_FRAME_LENGTH_MAX)
            goto drop;
        size_t total = (size_t)length + 5;
        if (f->used < total)
            return;
        uint16_t crc = 0;
        (void)tplc_read_u16(f->bytes, f->used, total - 2, &crc);
        if (crc != tplc_crc16(f->bytes + 1, total - 3))
            goto drop;
        callback(ctx, f->bytes[3], f->bytes + 4, (uint16_t)(length - 1));
        f->used = (uint16_t)(f->used - total);
        memmove(f->bytes, f->bytes + total, f->used);
        continue;
    drop:
        --f->used;
        memmove(f->bytes, f->bytes + 1, f->used);
    }
}
size_t tinyplc_frame_encode(uint8_t cmd, const uint8_t *p, size_t n,
                            uint8_t *out)
{
    if (n > 256)
        return 0;
    out[0] = TPLC_FRAME_START;
    tinyplc_put16(out, 1, (uint16_t)(n + 1));
    out[3] = cmd;
    if (n)
        memcpy(out + 4, p, n);
    tinyplc_put16(out, n + 4, tplc_crc16(out + 1, n + 3));
    return n + 6;
}
static uint32_t request_update(tinyplc_engine *e, uint32_t kind,
                               uint32_t generation)
{
    if (e->critical)
        e->critical(true);
    uint32_t status = tinyplc_update_reserve(e->update, kind, generation);
    if (e->critical)
        e->critical(false);
    if (!status) {
        tinyplc_update_plan(
            e->update); /* Preemptible; schemas reserved, state untouched. */
        if (e->critical)
            e->critical(true);
        tinyplc_update_arm(e->update);
        if (e->critical)
            e->critical(false);
    }
    return status;
}
size_t tinyplc_engine_request(tinyplc_engine *e, uint8_t cmd, const uint8_t *p,
                              size_t n, uint32_t now, uint8_t *r)
{
    if (cmd & TPLC_RESPONSE_BIT)
        return 0;
    tinyplc_loader *l = e->loader;
    tinyplc_loader_expire(l, now);
    memset(r, 0, 256);
    r[0] = TPLC_STATUS_BAD_REQUEST;
    uint32_t value = 0, base = 0, status;
    size_t size = 1;
    switch (cmd) {
    case TPLC_CMD_INFO:
        if (n)
            break;
        tinyplc_put16(r, TPLC_INFO_RESPONSE_PROTOCOL_OFFSET,
                      TPLC_PROTOCOL_VERSION);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_PACKAGE_VERSION_OFFSET,
                      TPLC_PACKAGE_VERSION);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_TARGET_OFFSET, TPLC_TARGET_F446);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_NATIVE_ABI_OFFSET, TPLC_NATIVE_ABI);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_RUNTIME_CONTRACT_OFFSET,
                      TPLC_RUNTIME_CONTRACT);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_AUTH_OFFSET,
                      TPLC_AUTH_UNSIGNED_LAB);
        tinyplc_put32(r, TPLC_INFO_RESPONSE_CAPABILITIES_OFFSET,
                      (l->allow_unsigned ? TPLC_CAP_UNSIGNED_LAB : 0) |
                          (e->update
                               ? (TPLC_CAP_ONLINE_MIGRATION | TPLC_CAP_ROLLBACK)
                               : 0));
        tinyplc_put32(
            r, TPLC_INFO_RESPONSE_COMMAND_MASK_OFFSET,
            0x0f | ((e->activate || e->update) ? 0x10 : 0) |
                (e->status ? 0x100 : 0) | (e->snapshots ? 0x40 : 0) |
                (e->update ? 0x220 : 0)); /* Advertise only wired callbacks. */
        tinyplc_put32(r, TPLC_INFO_RESPONSE_PACKAGE_MAX_OFFSET,
                      TPLC_PACKAGE_BYTES_MAX);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_TAG_LIMIT_OFFSET, TPLC_TAG_LIMIT);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_CELL_BYTES_OFFSET, TPLC_CELL_BYTES);
        tinyplc_put16(r, TPLC_INFO_RESPONSE_STACK_BYTES_OFFSET,
                      TPLC_WORKER_STACK_BYTES);
        tinyplc_put32(r, TPLC_INFO_RESPONSE_TRANSFER_TIMEOUT_MS_OFFSET,
                      TPLC_TRANSFER_TIMEOUT_MS);
        tinyplc_put32(r, TPLC_INFO_RESPONSE_TRANSFER_ID_OFFSET, l->transfer_id);
        tinyplc_put32(r, TPLC_INFO_RESPONSE_NEXT_OFFSET_OFFSET, l->next_offset);
        tinyplc_put32(r, TPLC_INFO_RESPONSE_TRANSFER_REMAINING_MS_OFFSET,
                      l->transfer_id ? TPLC_TRANSFER_TIMEOUT_MS -
                                           (uint32_t)(now - l->last_ms)
                                     : 0);
        if (e->critical)
            e->critical(true);
        for (unsigned i = 0; i < 2; ++i) {
            uint8_t *s = r + (i ? TPLC_INFO_RESPONSE_SLOT_B_OFFSET
                                : TPLC_INFO_RESPONSE_SLOT_A_OFFSET);
            tinyplc_put32(s, TPLC_SLOT_BASE_OFFSET,
                          i ? TPLC_SLOT_B_BASE : TPLC_SLOT_A_BASE);
            tinyplc_put32(s, TPLC_SLOT_CAPACITY_OFFSET, TPLC_CODE_CAPACITY);
            s[TPLC_SLOT_STATE_OFFSET] = (uint8_t)l->slots[i].state;
            tinyplc_put32(s, TPLC_SLOT_GENERATION_OFFSET,
                          l->slots[i].generation);
        }
        if (e->critical)
            e->critical(false);
        r[0] = 0;
        return TPLC_INFO_RESPONSE_BYTES;
    case TPLC_CMD_DOWNLOAD_BEGIN:
        if (n != TPLC_DOWNLOAD_BEGIN_REQUEST_BYTES)
            break;
        if (e->critical)
            e->critical(true);
        bool busy = e->update && tinyplc_update_busy(e->update);
        if (e->critical)
            e->critical(false);
        if (busy) {
            r[0] = TPLC_STATUS_BUSY;
            break;
        }
        status = tinyplc_loader_begin(l, get(p, n, 0), now, &value, &base);
        r[0] = (uint8_t)status;
        if (!status && e->update) {
            if (e->critical)
                e->critical(true);
            tinyplc_update_retire(e->update, l->receiving);
            if (e->critical)
                e->critical(false);
        }
        if (!status) {
            tinyplc_put32(r, 1, value);
            tinyplc_put32(r, 5, base);
            tinyplc_put32(r, 9, TPLC_CODE_CAPACITY);
            tinyplc_put32(r, 13, TPLC_TRANSFER_TIMEOUT_MS);
            size = TPLC_DOWNLOAD_BEGIN_RESPONSE_BYTES;
        }
        break;
    case TPLC_CMD_DOWNLOAD_CHUNK:
        if (n <= TPLC_DOWNLOAD_CHUNK_REQUEST_BYTES ||
            n > TPLC_DOWNLOAD_CHUNK_REQUEST_BYTES + TPLC_CHUNK_BYTES_MAX)
            break;
        status = tinyplc_loader_chunk(l, get(p, n, 0), get(p, n, 4), p + 8,
                                      (uint32_t)n - 8, now, &value);
        r[0] = (uint8_t)status;
        if (!status) {
            tinyplc_put32(r, 1, value);
            size = TPLC_DOWNLOAD_CHUNK_RESPONSE_BYTES;
        }
        break;
    case TPLC_CMD_DOWNLOAD_END:
        if (n != TPLC_DOWNLOAD_END_REQUEST_BYTES)
            break;
        /* Only the reserved inactive slot may become writable, and only during
         * bounded END validation/copy. The adapter seals it on every outcome. */
        if (l->transfer_id && get(p, n, 0) == l->transfer_id && e->mapping)
            e->mapping(e->context, l->receiving, true);
        status = tinyplc_loader_end(l, get(p, n, 0), now, &value);
        if (e->mapping)
            e->mapping(e->context, 0, false);
        r[0] = (uint8_t)status;
        if (!status) {
            tinyplc_put32(r, 1, value);
            size = TPLC_DOWNLOAD_END_RESPONSE_BYTES;
        }
        break;
    case TPLC_CMD_ACTIVATE:
        if (n != TPLC_ACTIVATE_REQUEST_BYTES)
            break;
        value = get(p, n, 0);
        status = e->update     ? request_update(e, TPLC_UPDATE_ACTIVATE, value)
                 : e->activate ? e->activate(e->context, value)
                               : TPLC_STATUS_UNSUPPORTED;
        r[0] = (uint8_t)status;
        if (!status) {
            tinyplc_put32(r, 1, value);
            size = TPLC_ACTIVATE_RESPONSE_BYTES;
        }
        break;
    case TPLC_CMD_ROLLBACK:
        if (n)
            break;
        status = e->update ? request_update(e, TPLC_UPDATE_ROLLBACK, 0)
                           : TPLC_STATUS_UNSUPPORTED;
        r[0] = (uint8_t)status;
        if (!status) {
            tinyplc_put32(r, 1, e->update->requested);
            size = TPLC_ROLLBACK_RESPONSE_BYTES;
        }
        break;
    case TPLC_CMD_GET_UPDATE_STATUS:
        if (n)
            break;
        if (!e->update) {
            r[0] = TPLC_STATUS_UNSUPPORTED;
            break;
        }
        if (e->critical)
            e->critical(true);
        tinyplc_update_status(e->update, r);
        if (e->critical)
            e->critical(false);
        return TPLC_GET_UPDATE_STATUS_RESPONSE_BYTES;
    case TPLC_CMD_READ_TAGS:
        if (e->snapshots)
            return tinyplc_snapshot_read(e->snapshots, p, n, now, r);
        r[0] = TPLC_STATUS_UNSUPPORTED;
        break;
    case TPLC_CMD_GET_STATUS:
        if (n)
            break;
        if (e->status) {
            e->status(e->context, r);
            return TPLC_GET_STATUS_RESPONSE_BYTES;
        }
        r[0] = TPLC_STATUS_UNSUPPORTED;
        break;
    default:
        r[0] = TPLC_STATUS_UNSUPPORTED;
        break;
    }
    return size;
}
