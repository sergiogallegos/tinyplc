/* Original tinyPLC native package validator; no native code is executed here. */
#ifndef TINYPLC_PACKAGE_H
#define TINYPLC_PACKAGE_H
#include "wire.h"
typedef struct {
    uint32_t link_base, payload_bytes, entry, text_offset, text_bytes,
        schema_crc;
    uint16_t tag_count;
    const uint8_t *payload,
        *tags; /* Borrowed only while input remains immutable. */
} tinyplc_package;
/* Returns wire status; output is untouched on failure. Input/output must not
 * alias. Caller owns stable input for the duration of validation and use. */
uint32_t tinyplc_package_validate(const uint8_t *bytes, size_t length,
                                  uint32_t reserved_base, bool allow_unsigned,
                                  tinyplc_package *out);
#endif
