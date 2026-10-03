/* Independent fixture consumer, deliberately NOT the production loader. */
#include "wire.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static uint8_t b[TPLC_PACKAGE_BYTES_MAX + 1];
static size_t n;
static uint32_t u32(size_t at)
{
    uint32_t v = 0;
    assert(tplc_read_u32(b, n, at, &v));
    return v;
}
static uint16_t u16(size_t at)
{
    uint16_t v = 0;
    assert(tplc_read_u16(b, n, at, &v));
    return v;
}
static bool package(void)
{
    if (n < TPLC_PACKAGE_BYTES || n > TPLC_PACKAGE_BYTES_MAX)
        return false;
    if (u32(TPLC_PACKAGE_MAGIC_OFFSET) != TPLC_PACKAGE_MAGIC ||
        u16(TPLC_PACKAGE_VERSION_OFFSET) != TPLC_PACKAGE_VERSION ||
        u16(TPLC_PACKAGE_HEADER_BYTES_OFFSET) != TPLC_PACKAGE_BYTES ||
        u32(TPLC_PACKAGE_TOTAL_BYTES_OFFSET) != n)
        return false;
    uint32_t po = u32(TPLC_PACKAGE_PAYLOAD_OFFSET_OFFSET),
             pl = u32(TPLC_PACKAGE_PAYLOAD_BYTES_OFFSET);
    uint32_t to = u32(TPLC_PACKAGE_TEXT_OFFSET_OFFSET),
             tl = u32(TPLC_PACKAGE_TEXT_BYTES_OFFSET),
             en = u32(TPLC_PACKAGE_ENTRY_OFFSET_OFFSET);
    uint32_t tags = u32(TPLC_PACKAGE_TAGS_OFFSET_OFFSET),
             count = u16(TPLC_PACKAGE_TAG_COUNT_OFFSET);
    if (po != TPLC_PACKAGE_BYTES || !pl || pl > TPLC_CODE_CAPACITY ||
        (pl & 3) || !tplc_range(n, po, pl))
        return false;
    if (count < 1 || count > TPLC_TAG_LIMIT ||
        u16(TPLC_PACKAGE_TAG_RECORD_BYTES_OFFSET) != TPLC_TAG_BYTES)
        return false;
    if (tags != po + pl || !tplc_range(n, tags, count * TPLC_TAG_BYTES) ||
        tags + count * TPLC_TAG_BYTES != n)
        return false;
    if ((to & 1) || (tl & 1) || (en & 1) || tl < 2 || !tplc_range(pl, to, tl) ||
        en < to || en - to > tl - 2)
        return false;
    return u32(TPLC_PACKAGE_SCHEMA_CRC_OFFSET) ==
               tplc_crc32(b + tags, n - tags, 0, 0) &&
           u32(TPLC_PACKAGE_PACKAGE_CRC_OFFSET) ==
               tplc_crc32(b, n, TPLC_PACKAGE_PACKAGE_CRC_OFFSET,
                          TPLC_PACKAGE_PACKAGE_CRC_OFFSET + 4);
}
int main(int argc, char **argv)
{
    assert(tplc_crc32((const uint8_t *)"123456789", 9, 0, 0) == 0xcbf43926);
    assert(tplc_crc16((const uint8_t *)"123456789", 9) == 0x29b1);
    assert(!tplc_range(80, UINT32_MAX, 2) && !tplc_range(80, 1, UINT32_MAX));
    uint32_t v;
    uint64_t wide;
    assert(!tplc_read_u32(b, 4, SIZE_MAX, &v));
    assert(!tplc_read_u64(b, 7, 0, &wide));
    if (argc != 3)
        return 2;
    FILE *file = fopen(argv[2], "rb");
    if (!file)
        return 2;
    n = fread(b, 1, sizeof b, file);
    assert(!ferror(file));
    fclose(file);
    bool ok = false;
    if (strcmp(argv[1], "package") == 0)
        ok = package();
    else if (strcmp(argv[1], "dispatch") == 0) {
        if (n == TPLC_DISPATCH_BYTES) {
            uint32_t entry = u32(TPLC_DISPATCH_ENTRY_OFFSET),
                     count = u32(TPLC_DISPATCH_TAG_COUNT_OFFSET);
            uint32_t pc = entry & ~UINT32_C(1);
            ok = (entry & 1) && count >= 1 && count <= TPLC_TAG_LIMIT &&
                 u32(TPLC_DISPATCH_GENERATION_OFFSET) != 0 &&
                 u32(TPLC_DISPATCH_RESERVED_OFFSET) == 0 &&
                 ((pc >= TPLC_SLOT_A_BASE &&
                   pc < TPLC_SLOT_A_BASE + TPLC_CODE_CAPACITY) ||
                  (pc >= TPLC_SLOT_B_BASE &&
                   pc < TPLC_SLOT_B_BASE + TPLC_CODE_CAPACITY));
        }
    } else if (n >= 6 && n <= TPLC_FRAME_BYTES_MAX &&
               b[0] == TPLC_FRAME_START) {
        uint16_t len = u16(TPLC_FRAME_PREFIX_LENGTH_OFFSET);
        ok = len >= TPLC_FRAME_LENGTH_MIN && len <= TPLC_FRAME_LENGTH_MAX &&
             n == (size_t)len + 5 && u16(n - 2) == tplc_crc16(b + 1, n - 3);
    }
    if (!ok)
        return 1;
    printf("%08x\n", (unsigned)tplc_crc32(b, n, 0, 0));
    return 0;
}
