/* Bounded byte primitives only. This is not an image validator or loader. */
#ifndef TINYPLC_WIRE_H
#define TINYPLC_WIRE_H
#include <stdbool.h>
#include <stddef.h>
#include "wire_generated.h"
static inline bool tplc_range(size_t total, uint32_t offset, uint32_t length) {
    return (uintmax_t)offset <= total && (uintmax_t)length <= total - (size_t)offset;
}
static inline bool tplc_read_u16(const uint8_t *b, size_t n, size_t at, uint16_t *out) {
    if (at > n || n - at < 2) return false;
    *out = (uint16_t)((uint16_t)b[at] | (uint16_t)((uint16_t)b[at+1] << 8));
    return true;
}
static inline bool tplc_read_u32(const uint8_t *b, size_t n, size_t at, uint32_t *out) {
    if (at > n || n - at < 4) return false;
    *out = (uint32_t)b[at] | (uint32_t)b[at+1] << 8 | (uint32_t)b[at+2] << 16 | (uint32_t)b[at+3] << 24;
    return true;
}
static inline bool tplc_read_u64(const uint8_t *b, size_t n, size_t at, uint64_t *out) {
    if (at > n || n - at < 8) return false;
    uint32_t lo, hi;
    (void)tplc_read_u32(b, n, at, &lo);
    (void)tplc_read_u32(b, n, at+4, &hi);
    *out = (uint64_t)lo | (uint64_t)hi << 32;
    return true;
}
static inline uint32_t tplc_crc32(const uint8_t *b, size_t n, size_t zero_start, size_t zero_end) {
    uint32_t crc = TPLC_CRC32_INIT;
    for (size_t i = 0; i < n; ++i) {
        crc ^= i >= zero_start && i < zero_end ? 0 : b[i];
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (crc >> 1) ^ (TPLC_CRC32_POLY_REFLECTED & (0u - (crc & 1u)));
    }
    return crc ^ TPLC_CRC32_XOROUT;
}
static inline uint16_t tplc_crc16(const uint8_t *b, size_t n) {
    uint16_t crc = (uint16_t)TPLC_CRC16_INIT;
    for (size_t i = 0; i < n; ++i) {
        crc ^= (uint16_t)((uint16_t)b[i] << 8);
        for (unsigned bit = 0; bit < 8; ++bit)
            crc = (uint16_t)((uint16_t)(crc << 1) ^ (crc & 0x8000u ? TPLC_CRC16_POLY : 0u));
    }
    return crc;
}
#endif
