#ifndef TINYPLC_CORE_H
#define TINYPLC_CORE_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <stdatomic.h>
#include "tinyplc/limits.h"

#define PLC_HEADER_BYTES 24u
#define PLC_TAG_BYTES 36u
#define PLC_MAX_IMAGE_BYTES (PLC_HEADER_BYTES + PLC_TAG_BYTES * PLC_MAX_TAGS + PLC_MAX_CODE_BYTES)
#define PLC_NO_PC UINT16_MAX

enum plc_type { PLC_BOOL = 1, PLC_DINT = 2 };
enum plc_class { PLC_INPUT = 1, PLC_OUTPUT = 2, PLC_VAR = 3 };
enum plc_opcode {
    PLC_PUSH = 0x01, PLC_LOAD = 0x02, PLC_STORE = 0x03,
    PLC_ADD = 0x10, PLC_SUB, PLC_MUL, PLC_DIV, PLC_NEG,
    PLC_AND = 0x20, PLC_OR, PLC_XOR, PLC_NOT,
    PLC_EQ = 0x30, PLC_NE, PLC_LT, PLC_GT, PLC_LE, PLC_GE,
    PLC_JMP = 0x40, PLC_JZ, PLC_HALT = 0xff
};
typedef enum {
    PLC_FAULT_NONE, PLC_FAULT_IMAGE, PLC_FAULT_STACK, PLC_FAULT_OPCODE,
    PLC_FAULT_TAG, PLC_FAULT_DIV_ZERO, PLC_FAULT_BUDGET,
    PLC_FAULT_OVERRUN, PLC_FAULT_TYPE
} plc_fault;
typedef enum { PLC_OK, PLC_INVALID, PLC_BUSY, PLC_NOT_WRITABLE, PLC_NOT_FOUND, PLC_STALE } plc_result;
typedef struct {
    plc_fault fault;
    uint16_t pc;
    uint8_t opcode;
    const char *reason; /* Static literal: never allocated. */
} plc_diagnostic;
typedef struct { const char *name; uint8_t type, kind; } plc_binding;
typedef struct { const plc_binding *items; size_t count; } plc_profile;
typedef struct { const char *name; uint8_t type, kind; } plc_tag;

/* Immutable after successful validation. Do not construct fields manually. */
typedef struct {
    uint8_t image[PLC_MAX_IMAGE_BYTES];
    uint8_t boundaries[PLC_MAX_CODE_BYTES / 8u];
    uint16_t code_offset, code_length, tag_count, max_stack;
    bool valid;
} plc_program;
typedef struct { uint32_t cell[PLC_MAX_TAGS]; } plc_values;

/* Reusable comms-owned validation workspace (~18 KB), never scan-stack local. */
typedef struct {
    uint64_t types[PLC_MAX_CODE_BYTES];
    uint8_t depth[PLC_MAX_CODE_BYTES]; /* 255 = unreachable */
} plc_workspace;

uint32_t plc_crc32(const uint8_t *data, size_t length);
uint32_t plc_image_crc32(const uint8_t *data, size_t length);
/* out/work/profile are caller-owned; out must never be the active program.
 * Failed validation clears out->valid. Profile names must be canonical ASCII.
 * Object arguments are required unless explicitly documented optional. */
plc_fault plc_validate(plc_program *out, const uint8_t *bytes, size_t length,
                       const plc_profile *profile, plc_workspace *work, plc_diagnostic *diag);
bool plc_tag_at(const plc_program *p, unsigned index, plc_tag *out);
int plc_tag_find(const plc_program *p, const char *name); /* ASCII case-insensitive */
plc_result plc_tag_write(const plc_program *p, plc_values *v, unsigned index, uint32_t value);
plc_result plc_input_set(const plc_program *p, plc_values *v, unsigned index, uint32_t value);
void plc_outputs_clear(const plc_program *p, plc_values *v);
int64_t plc_signed(uint32_t bits); /* Portable signed interpretation, no narrowing cast. */

/* VM mutates working values. Caller must discard them on failure. */
plc_fault plc_vm_run(const plc_program *p, plc_values *working, unsigned budget, plc_diagnostic *diag);

typedef struct { plc_program program; plc_values values; uint32_t generation; } plc_slot;
enum plc_mailbox { PLC_IDLE, PLC_STAGING, PLC_READY, PLC_PENDING };
typedef struct {
    plc_slot slots[2];
    _Atomic(plc_slot *) active;
    atomic_uint mailbox;
    unsigned staged; /* Published by READY/PENDING release stores. */
    uint32_t next_generation; /* Comms owner only. */
    bool faulted; /* Scan owner only, as are working/diagnostic. */
    plc_values working;
    plc_diagnostic diagnostic;
} plc_runtime;

void plc_runtime_init(plc_runtime *r);
bool plc_runtime_lock_free(const plc_runtime *r);
/* One comms producer. Copy/validate only an inactive slot. generation/diag
 * are optional outputs. A failed stage does not alter the active slot. */
plc_result plc_runtime_stage(plc_runtime *r, const uint8_t *bytes, size_t length,
                             const plc_profile *profile, plc_workspace *w,
                             uint32_t *generation, plc_diagnostic *diag);
plc_result plc_runtime_activate(plc_runtime *r, uint32_t generation);
plc_result plc_runtime_discard(plc_runtime *r);
/* One scan owner: boundary only AFTER physical output commit. */
bool plc_runtime_boundary(plc_runtime *r);
/* Inputs are indexed by tag index. Persistent VARs commit only on success.
 * The caller applies active->values outputs, even when this returns a fault. */
plc_fault plc_runtime_scan(plc_runtime *r, const plc_values *inputs, unsigned budget);

#endif
