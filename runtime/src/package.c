#include "tinyplc/package.h"
#include <string.h>
static uint32_t word(const uint8_t *b, size_t at) {
    uint32_t v = 0; (void)tplc_read_u32(b, TPLC_PACKAGE_BYTES, at, &v); return v;
}
static uint16_t half(const uint8_t *b, size_t at) {
    uint16_t v = 0; (void)tplc_read_u16(b, TPLC_PACKAGE_BYTES, at, &v); return v;
}
static bool zeros(const uint8_t *b, size_t n) {
    for (size_t i=0; i<n; ++i) if (b[i]) return false;
    return true;
}
static bool name_valid(const uint8_t *b) {
    size_t n=0;
    while (n<32 && b[n]) {
        bool letter=(b[n]>='A' && b[n]<='Z') || b[n]=='_';
        bool digit=n && b[n]>='0' && b[n]<='9';
        if (!letter && !digit) return false;
        ++n;
    }
    return n>0 && n<32 && zeros(b+n,32-n);
}
uint32_t tinyplc_package_validate(const uint8_t *b, size_t n, uint32_t base,
                                  bool allow_unsigned, tinyplc_package *out) {
    if (!b || !out || n<TPLC_PACKAGE_BYTES || n>TPLC_PACKAGE_BYTES_MAX || !allow_unsigned ||
        (base!=TPLC_SLOT_A_BASE && base!=TPLC_SLOT_B_BASE)) return TPLC_STATUS_INVALID_IMAGE;
    if (word(b,TPLC_PACKAGE_MAGIC_OFFSET)!=TPLC_PACKAGE_MAGIC ||
        half(b,TPLC_PACKAGE_VERSION_OFFSET)!=TPLC_PACKAGE_VERSION ||
        half(b,TPLC_PACKAGE_HEADER_BYTES_OFFSET)!=TPLC_PACKAGE_BYTES ||
        word(b,TPLC_PACKAGE_TOTAL_BYTES_OFFSET)!=n ||
        half(b,TPLC_PACKAGE_KIND_OFFSET)!=TPLC_IMAGE_NATIVE ||
        half(b,TPLC_PACKAGE_TARGET_OFFSET)!=TPLC_TARGET_F446 ||
        half(b,TPLC_PACKAGE_NATIVE_ABI_OFFSET)!=TPLC_NATIVE_ABI ||
        half(b,TPLC_PACKAGE_RUNTIME_CONTRACT_OFFSET)!=TPLC_RUNTIME_CONTRACT ||
        half(b,TPLC_PACKAGE_AUTH_OFFSET)!=TPLC_AUTH_UNSIGNED_LAB ||
        half(b,TPLC_PACKAGE_FLAGS_OFFSET)!=0 ||
        word(b,TPLC_PACKAGE_LINK_BASE_OFFSET)!=base ||
        half(b,TPLC_PACKAGE_CELL_BYTES_OFFSET)!=TPLC_CELL_BYTES ||
        half(b,TPLC_PACKAGE_STACK_BYTES_OFFSET)!=TPLC_WORKER_STACK_BYTES ||
        !zeros(b+TPLC_PACKAGE_RESERVED_OFFSET,TPLC_PACKAGE_BYTES-TPLC_PACKAGE_RESERVED_OFFSET))
        return TPLC_STATUS_INVALID_IMAGE;
    uint32_t po=word(b,TPLC_PACKAGE_PAYLOAD_OFFSET_OFFSET), pl=word(b,TPLC_PACKAGE_PAYLOAD_BYTES_OFFSET);
    uint32_t to=word(b,TPLC_PACKAGE_TEXT_OFFSET_OFFSET), tl=word(b,TPLC_PACKAGE_TEXT_BYTES_OFFSET);
    uint32_t en=word(b,TPLC_PACKAGE_ENTRY_OFFSET_OFFSET), tags=word(b,TPLC_PACKAGE_TAGS_OFFSET_OFFSET);
    uint16_t count=half(b,TPLC_PACKAGE_TAG_COUNT_OFFSET);
    if (po!=TPLC_PACKAGE_BYTES || pl<4 || pl>TPLC_CODE_CAPACITY || (pl&3) || !tplc_range(n,po,pl) ||
        count<1 || count>TPLC_TAG_LIMIT || half(b,TPLC_PACKAGE_TAG_RECORD_BYTES_OFFSET)!=TPLC_TAG_BYTES ||
        tags!=po+pl || !tplc_range(n,tags,count*TPLC_TAG_BYTES) || tags+count*TPLC_TAG_BYTES!=n ||
        (to&1) || (tl&1) || (en&1) || tl<2 || !tplc_range(pl,to,tl) || en<to || en-to>tl-2)
        return TPLC_STATUS_INVALID_IMAGE;
    if (word(b,TPLC_PACKAGE_PACKAGE_CRC_OFFSET)!=tplc_crc32(b,n,TPLC_PACKAGE_PACKAGE_CRC_OFFSET,TPLC_PACKAGE_PACKAGE_CRC_OFFSET+4))
        return TPLC_STATUS_CRC_ERROR;
    uint32_t schema=tplc_crc32(b+tags,n-tags,0,0);
    if (word(b,TPLC_PACKAGE_SCHEMA_CRC_OFFSET)!=schema) return TPLC_STATUS_INVALID_IMAGE;
    unsigned bindings=0;
    for (uint16_t i=0; i<count; ++i) {
        const uint8_t *tag=b+tags+i*TPLC_TAG_BYTES;
        uint16_t binding=0;
        (void)tplc_read_u16(tag,TPLC_TAG_BYTES,TPLC_TAG_BINDING_OFFSET,&binding);
        if (!name_valid(tag) || !zeros(tag+TPLC_TAG_RESERVED_OFFSET,4)) return TPLC_STATUS_INVALID_IMAGE;
        for (uint16_t j=0; j<i; ++j)
            if (memcmp(tag,b+tags+j*TPLC_TAG_BYTES,32)==0) return TPLC_STATUS_INVALID_IMAGE;
        uint8_t type=tag[TPLC_TAG_TYPE_OFFSET], kind=tag[TPLC_TAG_CLASS_OFFSET];
        if (type!=TPLC_TYPE_BOOL && type!=TPLC_TYPE_DINT && type!=TPLC_TYPE_TIME) return TPLC_STATUS_INVALID_IMAGE;
        if (kind==TPLC_CLASS_VAR || kind==TPLC_CLASS_TIMER) {
            if (binding!=TPLC_BINDING_NONE) return TPLC_STATUS_INVALID_IMAGE;
        } else {
            if (!((kind==TPLC_CLASS_INPUT && type==TPLC_TYPE_BOOL && binding==TPLC_BINDING_BTN_PC13) ||
                (kind==TPLC_CLASS_OUTPUT && type==TPLC_TYPE_BOOL && binding==TPLC_BINDING_LED_PA5) ||
                (kind==TPLC_CLASS_INPUT && type==TPLC_TYPE_DINT && binding==TPLC_BINDING_CLOCK_MS)))
                return TPLC_STATUS_INVALID_IMAGE;
            if (bindings & (1u<<binding)) return TPLC_STATUS_INVALID_IMAGE;
            bindings |= 1u<<binding;
        }
    }
    tinyplc_package result={base,pl,(base+en)|1u,to,tl,schema,count,b+po,b+tags};
    *out=result;
    return TPLC_STATUS_OK;
}
