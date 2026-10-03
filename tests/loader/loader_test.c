#include "tinyplc/loader.h"
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static tinyplc_loader loader;
static uint8_t a[TPLC_CODE_CAPACITY], b[TPLC_CODE_CAPACITY];
static uint8_t image[TPLC_PACKAGE_BYTES_MAX + 1],
    mutation[TPLC_PACKAGE_BYTES_MAX + 1];
static size_t length;
static void pristine(void)
{
    memset(a, 0xa7, sizeof a);
    memset(b, 0xb8, sizeof b);
    assert(tinyplc_loader_init(&loader, a, b, 0, true));
}
static void active_intact(void)
{
    for (size_t i = 0; i < sizeof a; ++i)
        assert(a[i] == 0xa7);
    assert(loader.slots[0].state == TPLC_SLOT_ACTIVE &&
           loader.slots[0].generation == 1);
}
static void inactive_intact(void)
{
    for (size_t i = 0; i < sizeof b; ++i)
        assert(b[i] == 0xb8);
}
static uint32_t begin(uint32_t now)
{
    uint32_t id = 0, base = 0;
    assert(tinyplc_loader_begin(&loader, (uint32_t)length, now, &id, &base) ==
           TPLC_STATUS_OK);
    assert(id && base == TPLC_SLOT_B_BASE);
    return id;
}
static void feed(uint32_t id, uint32_t now, const uint8_t *data)
{
    uint32_t offset = 0, next = 0;
    while (offset < length) {
        uint32_t count = (uint32_t)length - offset;
        if (count > TPLC_CHUNK_BYTES_MAX)
            count = TPLC_CHUNK_BYTES_MAX;
        assert(tinyplc_loader_chunk(&loader, id, offset, data + offset, count,
                                    now, &next) == TPLC_STATUS_OK);
        assert(next == offset + count);
        offset = next;
    }
}
static void crc_fix(uint8_t *data)
{
    uint32_t crc = tplc_crc32(data, length, TPLC_PACKAGE_PACKAGE_CRC_OFFSET,
                              TPLC_PACKAGE_PACKAGE_CRC_OFFSET + 4);
    for (unsigned i = 0; i < 4; ++i)
        data[TPLC_PACKAGE_PACKAGE_CRC_OFFSET + i] = (uint8_t)(crc >> (8 * i));
}
static void exercise(void)
{
    assert(!tinyplc_loader_init(&loader, a, a, -1, true));
    assert(!tinyplc_loader_init(&loader, a, a + 1, -1, true));
    assert(!tinyplc_loader_init(&loader, (uint8_t *)&loader, b, -1, true));
    assert(!tinyplc_loader_init(&loader, a, b, 2, true));
    pristine();
    uint32_t id = begin(UINT32_MAX - 10), next = 999, other = 999, gen = 999;
    assert(tinyplc_loader_begin(&loader, (uint32_t)length, 0, &other, &next) ==
               TPLC_STATUS_BUSY &&
           other == 999 && next == 999);
    assert(tinyplc_loader_end(&loader, id, 0, &gen) ==
               TPLC_STATUS_BAD_REQUEST &&
           gen == 999);
    assert(tinyplc_loader_chunk(&loader, id, UINT32_MAX, image, 2, 0, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    assert(tinyplc_loader_chunk(&loader, id, 0, image, 0, 0, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    assert(tinyplc_loader_chunk(&loader, id, 0, image, 241, 0, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    assert(tinyplc_loader_chunk(&loader, id, 1, image, 1, 0, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    assert(tinyplc_loader_chunk(&loader, id + 1, 0, image, 1, 0, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    assert(tinyplc_loader_chunk(&loader, id, 0, image, 4, 5, &next) ==
               TPLC_STATUS_OK &&
           next == 4);
    assert(tinyplc_loader_chunk(&loader, id, 0, image, 4, 6, &next) ==
               TPLC_STATUS_OK &&
           next == 4);
    memcpy(mutation, image, length);
    mutation[0] ^= 1;
    assert(tinyplc_loader_chunk(&loader, id, 0, mutation, 4, 7, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    assert(loader.last_ms == 6 && loader.next_offset == 4);
    assert(tinyplc_loader_chunk(&loader, id, 4, image + 4, 4, 8, &next) ==
           TPLC_STATUS_OK);
    assert(tinyplc_loader_chunk(&loader, id, 0, image, 4, 9, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    tinyplc_loader_expire(&loader, 8 + TPLC_TRANSFER_TIMEOUT_MS - 1);
    assert(loader.transfer_id == id);
    tinyplc_loader_expire(&loader, 8 + TPLC_TRANSFER_TIMEOUT_MS);
    assert(loader.transfer_id == 0);
    assert(tinyplc_loader_chunk(&loader, id, 8, image + 8, 4, 40000, &next) ==
           TPLC_STATUS_BAD_REQUEST);
    active_intact();
    inactive_intact();
    id = begin(40000);
    feed(id, 40001, image);
    inactive_intact();
    assert(tinyplc_loader_end(&loader, id, 40002, &gen) == TPLC_STATUS_OK &&
           gen == 2);
    tinyplc_package p;
    assert(tinyplc_package_validate(image, length, TPLC_SLOT_B_BASE, true,
                                    &p) == 0);
    assert(loader.slots[1].state == TPLC_SLOT_READY &&
           loader.slots[1].generation == 2);
    assert(memcmp(b, p.payload, p.payload_bytes) == 0 &&
           memcmp(loader.slots[1].tags, p.tags, p.tag_count * TPLC_TAG_BYTES) ==
               0);
    for (size_t i = p.payload_bytes; i < sizeof b; ++i)
        assert(b[i] == 0);
    assert(tinyplc_loader_end(&loader, id, 40003, &gen) ==
           TPLC_STATUS_BAD_REQUEST);
    active_intact();
    /* A new reservation explicitly retires the old READY candidate. */
    id = begin(40004);
    assert(loader.slots[1].generation == 0);
    memcpy(mutation, image, length);
    mutation[80] ^= 1;
    feed(id, 40005, mutation);
    assert(tinyplc_loader_end(&loader, id, 40006, &gen) ==
           TPLC_STATUS_CRC_ERROR);
    assert(loader.slots[1].state == TPLC_SLOT_EMPTY && !loader.transfer_id);
    active_intact();
    pristine();
    id = begin(0);
    memcpy(mutation, image, length);
    mutation[TPLC_PACKAGE_LINK_BASE_OFFSET + 1] ^= 0x40;
    crc_fix(mutation);
    feed(id, 1, mutation);
    assert(tinyplc_loader_end(&loader, id, 2, &gen) ==
           TPLC_STATUS_INVALID_IMAGE);
    active_intact();
    inactive_intact();
    pristine();
    loader.slots[1].state = TPLC_SLOT_PENDING;
    assert(tinyplc_loader_begin(&loader, (uint32_t)length, 0, &id, &next) ==
           TPLC_STATUS_BUSY);
    pristine();
    loader.next_transfer = UINT32_MAX;
    id = begin(0);
    assert(id == UINT32_MAX);
    tinyplc_loader_expire(&loader, TPLC_TRANSFER_TIMEOUT_MS);
    assert(tinyplc_loader_begin(&loader, (uint32_t)length,
                                TPLC_TRANSFER_TIMEOUT_MS, &id,
                                &next) == TPLC_STATUS_BUSY);
    pristine();
    loader.next_generation = UINT32_MAX;
    id = begin(0);
    feed(id, 1, image);
    assert(tinyplc_loader_end(&loader, id, 2, &gen) == TPLC_STATUS_OK &&
           gen == UINT32_MAX);
    assert(tinyplc_loader_begin(&loader, (uint32_t)length, 3, &id, &next) ==
           TPLC_STATUS_BUSY);
    pristine();
    loader.allow_unsigned = false;
    assert(tinyplc_loader_begin(&loader, (uint32_t)length, 0, &id, &next) ==
           TPLC_STATUS_UNSUPPORTED);
    /* Seeded mutations stress all parser paths, including re-CRC'd metadata. */
    uint32_t seed = 12345;
    for (unsigned i = 0; i < 4000; ++i) {
        memcpy(mutation, image, length);
        seed = seed * 1664525u + 1013904223u;
        mutation[seed % length] ^= (uint8_t)(1u << (seed % 8));
        if (i & 1)
            crc_fix(mutation);
        tinyplc_package before;
        memset(&before, 0x55, sizeof before);
        p = before;
        uint32_t status = tinyplc_package_validate(mutation, length,
                                                   TPLC_SLOT_B_BASE, true, &p);
        if (status)
            assert(memcmp(&p, &before, sizeof p) == 0);
        else {
            assert(p.payload_bytes <= TPLC_CODE_CAPACITY && p.tag_count <= 64);
        }
    }
    printf(
        "loader staging, retries, expiry, protection, rejection and 4000 mutations passed; state=%zu bytes\n",
        sizeof loader);
}
int main(int argc, char **argv)
{
    assert(argc == 3 || argc == 5);
    FILE *f = fopen(argv[2], "rb");
    assert(f);
    length = fread(image, 1, sizeof image, f);
    assert(!ferror(f));
    fclose(f);
    if (strcmp(argv[1], "validate") == 0) {
        assert(argc == 5);
        tinyplc_package p;
        uint32_t status = tinyplc_package_validate(
            image, length, (uint32_t)strtoul(argv[3], NULL, 0),
            atoi(argv[4]) != 0, &p);
        printf("%u\n", (unsigned)status);
        return 0;
    }
    if (strcmp(argv[1], "maximum") == 0) {
        pristine();
        uint32_t id = begin(0), gen = 0;
        feed(id, 1, image);
        inactive_intact();
        assert(tinyplc_loader_end(&loader, id, 2, &gen) == TPLC_STATUS_OK);
        active_intact();
        tinyplc_package p;
        assert(tinyplc_package_validate(image, length, TPLC_SLOT_B_BASE, true,
                                        &p) == 0);
        assert(p.payload_bytes == TPLC_CODE_CAPACITY &&
               p.tag_count == TPLC_TAG_LIMIT);
        assert(memcmp(b, p.payload, p.payload_bytes) == 0);
        assert(memcmp(loader.slots[1].tags, p.tags,
                      p.tag_count * TPLC_TAG_BYTES) == 0);
        return 0;
    }
    exercise();
    return 0;
}
