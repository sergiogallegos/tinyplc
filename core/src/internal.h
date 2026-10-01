#ifndef TINYPLC_INTERNAL_H
#define TINYPLC_INTERNAL_H
#include "tinyplc/core.h"
#include <string.h>

static inline uint16_t plc_u16(const uint8_t *b) { return (uint16_t)(b[0] | (uint16_t)b[1] << 8); }
static inline uint32_t plc_u32(const uint8_t *b) {
    return (uint32_t)b[0] | (uint32_t)b[1] << 8 | (uint32_t)b[2] << 16 | (uint32_t)b[3] << 24;
}
static inline plc_fault plc_error(plc_diagnostic *d, plc_fault fault, unsigned pc, unsigned op, const char *why) {
    if (d) *d = (plc_diagnostic){fault, (uint16_t)pc, (uint8_t)op, why};
    return fault;
}
static inline bool plc_boundary(const plc_program *p, unsigned pc) {
    return pc < p->code_length && (p->boundaries[pc / 8] & (1u << (pc % 8))) != 0;
}
typedef struct { uint8_t op, width, type, tag; uint16_t target; uint32_t value; } plc_instruction;
plc_fault plc_decode(const plc_program *p, unsigned pc, plc_instruction *i, plc_diagnostic *d);
/* Shared typing rules ensure STORE/input and operator checks agree. */
plc_fault plc_stack_effect(const plc_program *p, const plc_instruction *i, unsigned pc,
                           unsigned *depth, uint64_t *types, plc_diagnostic *d);
#endif
