/* Independent hand-built wire fixtures. No compiler or test framework needed. */
#include "tinyplc/core.h"
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(expr)                                                            \
    do {                                                                       \
        if (!(expr)) {                                                         \
            fprintf(stderr, "%s:%d: %s\n", __FILE__, __LINE__, #expr);         \
            exit(1);                                                           \
        }                                                                      \
    } while (0)
typedef struct {
    uint8_t bytes[PLC_MAX_IMAGE_BYTES];
    size_t length;
} fixture;
static plc_program program;
static plc_workspace work;
static plc_runtime runtime;
static plc_diagnostic diag;
static const plc_binding bindings[] = {{"BTN", PLC_BOOL, PLC_INPUT},
                                       {"LED", PLC_BOOL, PLC_OUTPUT}};
static const plc_profile profile = {bindings, 2};
static unsigned groups;

static void u16(uint8_t *p, unsigned v)
{
    p[0] = (uint8_t)v;
    p[1] = (uint8_t)(v >> 8);
}
static void u32(uint8_t *p, uint32_t v)
{
    for (unsigned j = 0; j < 4; ++j)
        p[j] = (uint8_t)(v >> (8 * j));
}
static void seal(fixture *f)
{
    u32(f->bytes + 20, plc_image_crc32(f->bytes, f->length));
}
static fixture build_tags(const uint8_t *code, unsigned size, unsigned stack,
                          unsigned tags)
{
    fixture f = {{0}, PLC_HEADER_BYTES + tags * PLC_TAG_BYTES + size};
    CHECK(f.length <= sizeof f.bytes);
    memcpy(f.bytes, "TPLC", 4);
    u16(f.bytes + 4, 1);
    u16(f.bytes + 6, PLC_HEADER_BYTES);
    u16(f.bytes + 8, size);
    u16(f.bytes + 10, tags);
    u16(f.bytes + 12, stack);
    u32(f.bytes + 16, (uint32_t)f.length);
    for (unsigned j = 0; j < tags; ++j) {
        uint8_t *t = f.bytes + PLC_HEADER_BYTES + j * PLC_TAG_BYTES;
        const char *names[] = {"BTN", "LED", "N", "B"};
        t[0] = j == 0 || j == 1 || j == 3 ? PLC_BOOL : PLC_DINT;
        t[1] = j == 0 ? PLC_INPUT : j == 1 ? PLC_OUTPUT : PLC_VAR;
        if (j < 4)
            memcpy(t + 4, names[j], strlen(names[j]));
        else
            (void)snprintf((char *)t + 4, 32, "V%u", j);
    }
    if (size)
        memcpy(f.bytes + PLC_HEADER_BYTES + tags * PLC_TAG_BYTES, code, size);
    seal(&f);
    return f;
}
static fixture build(const uint8_t *code, unsigned size, unsigned stack)
{
    return build_tags(code, size, stack, 4);
}
static void valid(fixture *f)
{
    CHECK(plc_validate(&program, f->bytes, f->length, &profile, &work, &diag) ==
          PLC_FAULT_NONE);
    CHECK(program.valid);
}
static void invalid(fixture *f)
{
    CHECK(plc_validate(&program, f->bytes, f->length, &profile, &work, &diag) !=
          PLC_FAULT_NONE);
    CHECK(!program.valid);
}
static void push(uint8_t *code, unsigned type, uint32_t value)
{
    code[0] = PLC_PUSH;
    code[1] = (uint8_t)type;
    u32(code + 2, value);
}
static plc_fault run(fixture *f, plc_values *values)
{
    valid(f);
    return plc_vm_run(&program, values, PLC_INSTRUCTION_BUDGET, &diag);
}

static void test_header_and_tags(void)
{
    CHECK(plc_crc32((const uint8_t *)"123456789", 9) == UINT32_C(0xcbf43926));
    CHECK(plc_crc32(NULL, 0) == 0);
    uint8_t code[] = {PLC_HALT};
    fixture base = build(code, sizeof code, 0), f;
    valid(&base);
    CHECK(plc_tag_find(&program, "btn") == 0);
    CHECK(plc_tag_find(&program, "N") == 2);
    CHECK(plc_tag_find(&program, "missing") == -1);
    plc_tag t;
    CHECK(!plc_tag_at(&program, 64, &t));
    plc_values v = {{0}};
    CHECK(plc_tag_write(&program, &v, 0, 1) == PLC_NOT_WRITABLE);
    CHECK(plc_tag_write(&program, &v, 1, 1) == PLC_NOT_WRITABLE);
    CHECK(plc_tag_write(&program, &v, 2, UINT32_MAX) == PLC_OK);
    CHECK(plc_tag_write(&program, &v, 3, 2) == PLC_INVALID);
    CHECK(plc_tag_write(&program, &v, 4, 1) == PLC_NOT_FOUND);
    CHECK(plc_input_set(&program, &v, 0, 1) == PLC_OK);
    CHECK(plc_input_set(&program, &v, 0, 2) == PLC_INVALID);
    CHECK(plc_input_set(&program, &v, 2, 0) == PLC_NOT_WRITABLE);
    v.cell[1] = 1;
    plc_outputs_clear(&program, &v);
    CHECK(v.cell[1] == 0 && v.cell[0] == 1 && v.cell[2] == UINT32_MAX);
    for (size_t n = 0; n < base.length; ++n)
        CHECK(plc_validate(&program, base.bytes, n, &profile, &work, &diag) !=
              PLC_FAULT_NONE);
    CHECK(plc_validate(&program, NULL, 1, &profile, &work, &diag) ==
          PLC_FAULT_IMAGE);
    unsigned offsets[] = {0, 4, 6, 8, 10, 12, 14, 16};
    for (unsigned j = 0; j < sizeof offsets / sizeof offsets[0]; ++j) {
        f = base;
        f.bytes[offsets[j]] = 255;
        seal(&f);
        invalid(&f);
    }
    f = base;
    f.bytes[20] ^= 1;
    invalid(&f);
    f = base;
    ++f.length;
    u32(f.bytes + 16, (uint32_t)f.length);
    seal(&f);
    invalid(&f);
    unsigned descriptor_offsets[] = {24, 25, 26, 27, 28};
    for (unsigned j = 0;
         j < sizeof descriptor_offsets / sizeof descriptor_offsets[0]; ++j) {
        f = base;
        f.bytes[descriptor_offsets[j]] = 255;
        seal(&f);
        invalid(&f);
    }
    f = base;
    memset(f.bytes + 28, 'X', 32);
    seal(&f);
    invalid(&f);
    f = base;
    f.bytes[28] = 0;
    seal(&f);
    invalid(&f);
    f = base;
    f.bytes[32] = 'X';
    seal(&f);
    invalid(&f); /* Nonzero name padding. */
    f = base;
    memcpy(f.bytes + 28 + PLC_TAG_BYTES, f.bytes + 28, 32);
    seal(&f);
    invalid(&f);
    f = base;
    memcpy(f.bytes + 28, "BAD", 3);
    seal(&f);
    invalid(&f);
    CHECK(plc_validate(&program, base.bytes, base.length, NULL, &work, &diag) !=
          PLC_FAULT_NONE);
    f = build_tags(code, sizeof code, 0, 0);
    CHECK(plc_validate(&program, f.bytes, f.length, NULL, &work, &diag) ==
          PLC_FAULT_NONE);
    ++groups;
}

static void binary(unsigned op, unsigned type, uint32_t a, uint32_t b,
                   uint32_t expected, bool boolean)
{
    uint8_t code[16];
    push(code, type, a);
    push(code + 6, type, b);
    code[12] = (uint8_t)op;
    code[13] = PLC_STORE;
    code[14] = boolean ? 3 : 2;
    code[15] = PLC_HALT;
    fixture f = build(code, sizeof code, 2);
    plc_values v = {{0}};
    CHECK(run(&f, &v) == PLC_FAULT_NONE);
    CHECK(v.cell[boolean ? 3 : 2] == expected);
}
static void test_operators(void)
{
    binary(PLC_ADD, PLC_DINT, INT32_MAX, 1, UINT32_C(0x80000000), false);
    binary(PLC_ADD, PLC_DINT, UINT32_MAX, 1, 0, false);
    binary(PLC_SUB, PLC_DINT, 0, 1, UINT32_MAX, false);
    binary(PLC_MUL, PLC_DINT, UINT32_C(0x80000000), 2, 0, false);
    binary(PLC_MUL, PLC_DINT, 7, 9, 63, false);
    binary(PLC_DIV, PLC_DINT, UINT32_C(0xfffffff9), 3, UINT32_C(0xfffffffe),
           false);
    binary(PLC_DIV, PLC_DINT, UINT32_C(0x80000000), UINT32_MAX,
           UINT32_C(0x80000000), false);
    binary(PLC_EQ, PLC_DINT, UINT32_MAX, UINT32_MAX, 1, true);
    binary(PLC_NE, PLC_DINT, 0, UINT32_MAX, 1, true);
    binary(PLC_LT, PLC_DINT, UINT32_MAX, 0, 1, true);
    binary(PLC_GT, PLC_DINT, 0, UINT32_MAX, 1, true);
    binary(PLC_LE, PLC_DINT, UINT32_C(0x80000000), UINT32_C(0x80000000), 1,
           true);
    binary(PLC_GE, PLC_DINT, UINT32_MAX, 0, 0, true);
    for (unsigned a = 0; a < 2; ++a)
        for (unsigned b = 0; b < 2; ++b) {
            binary(PLC_AND, PLC_BOOL, a, b, a && b, true);
            binary(PLC_OR, PLC_BOOL, a, b, a || b, true);
            binary(PLC_XOR, PLC_BOOL, a, b, a != b, true);
            binary(PLC_EQ, PLC_BOOL, a, b, a == b, true);
            binary(PLC_NE, PLC_BOOL, a, b, a != b, true);
        }
    uint8_t code[10];
    push(code, PLC_DINT, UINT32_C(0x80000000));
    code[6] = PLC_NEG;
    code[7] = PLC_STORE;
    code[8] = 2;
    code[9] = PLC_HALT;
    fixture f = build(code, sizeof code, 1);
    plc_values v = {{0}};
    CHECK(run(&f, &v) == PLC_FAULT_NONE && v.cell[2] == UINT32_C(0x80000000));
    push(code, PLC_BOOL, 0);
    code[6] = PLC_NOT;
    code[8] = 3;
    f = build(code, sizeof code, 1);
    CHECK(run(&f, &v) == PLC_FAULT_NONE && v.cell[3] == 1);
    CHECK(plc_signed(UINT32_MAX) == -1 &&
          plc_signed(UINT32_C(0x80000000)) == INT32_MIN);
    ++groups;
}

static void test_control_flow(void)
{
    const uint8_t code[] = {
        PLC_LOAD, 0, PLC_JZ,  16,        0, PLC_LOAD, 2,         PLC_PUSH,
        PLC_DINT, 1, 0,       0,         0, PLC_ADD,  PLC_STORE, 2,
        PLC_LOAD, 0, PLC_NOT, PLC_STORE, 1, PLC_HALT};
    fixture f = build(code, sizeof code, 2);
    plc_values v = {{0}};
    CHECK(run(&f, &v) == PLC_FAULT_NONE && v.cell[2] == 0 && v.cell[1] == 1);
    v.cell[0] = 1;
    CHECK(plc_vm_run(&program, &v, 10, &diag) == PLC_FAULT_NONE);
    CHECK(v.cell[2] == 1 && v.cell[1] == 0);
    CHECK(plc_vm_run(&program, &v, 9, &diag) == PLC_FAULT_BUDGET);
    CHECK(plc_vm_run(&program, &v, 0, &diag) == PLC_FAULT_BUDGET);
    /* Both branches supply one DINT; validator must merge their stack types. */
    uint8_t branches[27] = {0};
    push(branches, PLC_BOOL, 0);
    branches[6] = PLC_JZ;
    branches[7] = 18;
    push(branches + 9, PLC_DINT, 11);
    branches[15] = PLC_JMP;
    branches[16] = 24;
    push(branches + 18, PLC_DINT, 22);
    branches[24] = PLC_STORE;
    branches[25] = 2;
    branches[26] = PLC_HALT;
    f = build(branches, sizeof branches, 1);
    CHECK(run(&f, &v) == PLC_FAULT_NONE && v.cell[2] == 22);
    branches[2] = 1;
    f = build(branches, sizeof branches, 1);
    CHECK(run(&f, &v) == PLC_FAULT_NONE && v.cell[2] == 11);
    push(branches + 18, PLC_BOOL, 1);
    f = build(branches, sizeof branches, 1);
    invalid(&f);
    ++groups;
}

static void bad_code(const uint8_t *code, unsigned length, unsigned stack)
{
    fixture f = build(code, length, stack);
    invalid(&f);
}
static void test_rejections_and_limits(void)
{
    const uint8_t bad[][8] = {{0x99},
                              {PLC_LOAD},
                              {PLC_STORE, 0, PLC_HALT},
                              {PLC_LOAD, 64, PLC_HALT},
                              {PLC_JMP, 0, 0, PLC_HALT},
                              {PLC_JMP, 255, 0, PLC_HALT},
                              {PLC_JMP, 4, 0, PLC_LOAD, 0, PLC_HALT},
                              {PLC_ADD, PLC_HALT},
                              {PLC_LOAD, 0, PLC_HALT},
                              {PLC_LOAD, 0, PLC_STORE, 3},
                              {PLC_LOAD, 0, PLC_NEG, PLC_STORE, 2, PLC_HALT},
                              {PLC_LOAD, 2, PLC_JZ, 5, 0, PLC_HALT},
                              {PLC_JMP, 5, 0, PLC_LOAD, 64, PLC_HALT}};
    unsigned sizes[] = {1, 1, 3, 3, 4, 4, 6, 2, 3, 4, 6, 6, 6};
    for (unsigned j = 0; j < sizeof sizes / sizeof sizes[0]; ++j)
        bad_code(bad[j], sizes[j], 1);
    uint8_t push_code[9];
    push(push_code, PLC_BOOL, 2);
    push_code[6] = PLC_STORE;
    push_code[7] = 3;
    push_code[8] = PLC_HALT;
    bad_code(push_code, sizeof push_code, 1);
    push(push_code, 3, 0);
    bad_code(push_code, sizeof push_code, 1);
    push(push_code, PLC_DINT, 0);
    bad_code(push_code, sizeof push_code, 1); /* DINT into BOOL. */
    uint8_t maxcode[PLC_MAX_CODE_BYTES];
    unsigned pos = 0;
    for (unsigned j = 0; j < 64; ++j) {
        push(maxcode + pos, PLC_DINT, j);
        pos += 6;
    }
    for (unsigned j = 0; j < 64; ++j) {
        maxcode[pos++] = PLC_STORE;
        maxcode[pos++] = 2;
    }
    maxcode[pos++] = PLC_HALT;
    fixture f = build(maxcode, pos, 64);
    plc_values v = {{0}};
    CHECK(run(&f, &v) == PLC_FAULT_NONE && v.cell[2] == 0);
    pos = 0;
    for (unsigned j = 0; j < 65; ++j) {
        push(maxcode + pos, PLC_DINT, j);
        pos += 6;
    }
    maxcode[pos++] = PLC_HALT;
    bad_code(maxcode, pos, 64);
    /* Maximum-size image and highest tag index. */
    push(maxcode, PLC_DINT, 123);
    maxcode[6] = PLC_STORE;
    maxcode[7] = 63;
    memset(maxcode + 8, PLC_HALT, sizeof maxcode - 8);
    f = build_tags(maxcode, sizeof maxcode, 1, 64);
    CHECK(f.length == PLC_MAX_IMAGE_BYTES);
    CHECK(run(&f, &v) == PLC_FAULT_NONE && v.cell[63] == 123);
    u16(f.bytes + 12, 2);
    seal(&f);
    invalid(&f); /* Declared maximum must match. */
    ++groups;
}

static void test_runtime_faults(void)
{
    uint8_t code[24];
    push(code, PLC_DINT, 77);
    code[6] = PLC_STORE;
    code[7] = 2;
    push(code + 8, PLC_DINT, 1);
    push(code + 14, PLC_DINT, 0);
    code[20] = PLC_DIV;
    code[21] = PLC_STORE;
    code[22] = 2;
    code[23] = PLC_HALT;
    fixture f = build(code, sizeof code, 2);
    uint32_t generation;
    plc_runtime_init(&runtime);
    CHECK(plc_runtime_lock_free(&runtime));
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work,
                            &generation, &diag) == PLC_OK);
    CHECK(plc_runtime_activate(&runtime, generation) == PLC_OK);
    CHECK(plc_runtime_boundary(&runtime));
    plc_slot *s = atomic_load(&runtime.active);
    s->values.cell[2] = 9;
    s->values.cell[1] = 1;
    plc_values inputs = {{1}};
    CHECK(plc_runtime_scan(&runtime, &inputs, 100) == PLC_FAULT_DIV_ZERO);
    CHECK(runtime.faulted && runtime.diagnostic.pc == 20 &&
          runtime.diagnostic.opcode == PLC_DIV);
    CHECK(s->values.cell[2] == 9 && s->values.cell[1] == 0 &&
          s->values.cell[0] == 1); /* Discard partial N=77. */
    inputs.cell[0] = 0;
    CHECK(plc_runtime_scan(&runtime, &inputs, 100) == PLC_FAULT_DIV_ZERO);
    CHECK(s->values.cell[0] == 0 &&
          s->values.cell[2] == 9); /* Inputs still sampled while faulted. */
    uint8_t halt[] = {PLC_HALT};
    f = build(halt, 1, 0);
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work,
                            &generation, &diag) == PLC_OK);
    CHECK(plc_runtime_activate(&runtime, generation) == PLC_OK &&
          plc_runtime_boundary(&runtime));
    CHECK(!runtime.faulted && runtime.diagnostic.fault == PLC_FAULT_DIV_ZERO);
    CHECK(plc_runtime_scan(&runtime, &inputs, 1) == PLC_FAULT_NONE);
    /* Runtime repeats dynamic checks even when an image had passed validation. */
    valid(&f);
    plc_values v = {{0}};
    v.cell[0] = 2;
    CHECK(plc_vm_run(&program, &v, 10, &diag) == PLC_FAULT_TYPE);
    v.cell[0] = 0;
    program.image[program.code_offset] = PLC_ADD;
    CHECK(plc_vm_run(&program, &v, 10, &diag) == PLC_FAULT_STACK);
    program.image[program.code_offset] = 0x99;
    CHECK(plc_vm_run(&program, &v, 10, &diag) == PLC_FAULT_OPCODE);
    program.valid = false;
    CHECK(plc_vm_run(&program, &v, 10, &diag) == PLC_FAULT_IMAGE);
    ++groups;
}

static void test_slot_lifecycle(void)
{
    uint8_t halt[] = {PLC_HALT};
    fixture f = build(halt, 1, 0);
    uint32_t gen;
    plc_runtime_init(&runtime);
    CHECK(!plc_runtime_boundary(&runtime));
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work, &gen,
                            &diag) == PLC_OK &&
          gen == 1);
    CHECK(atomic_load(&runtime.active) == NULL);
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work, NULL,
                            &diag) == PLC_BUSY);
    CHECK(plc_runtime_activate(&runtime, 99) == PLC_STALE);
    CHECK(plc_runtime_activate(&runtime, gen) == PLC_OK);
    CHECK(plc_runtime_discard(&runtime) == PLC_BUSY);
    CHECK(atomic_load(&runtime.active) == NULL);
    CHECK(plc_runtime_boundary(&runtime));
    plc_slot *old = atomic_load(&runtime.active);
    old->values.cell[2] = 42;
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work, &gen,
                            &diag) == PLC_OK);
    CHECK(plc_runtime_activate(&runtime, gen) == PLC_OK);
    CHECK(atomic_load(&runtime.active) == old && old->values.cell[2] == 42);
    CHECK(plc_runtime_boundary(&runtime));
    CHECK(atomic_load(&runtime.active) != old &&
          atomic_load(&runtime.active)->values.cell[2] == 0);
    f.bytes[0] = 0;
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work, &gen,
                            &diag) == PLC_INVALID);
    CHECK(atomic_load(&runtime.mailbox) == PLC_IDLE);
    f.bytes[0] = 'T';
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work, &gen,
                            &diag) == PLC_OK);
    CHECK(plc_runtime_discard(&runtime) == PLC_OK);
    CHECK(plc_runtime_activate(&runtime, gen) == PLC_BUSY);
    runtime.next_generation = 0;
    CHECK(plc_runtime_stage(&runtime, f.bytes, f.length, &profile, &work, &gen,
                            &diag) == PLC_INVALID);
    ++groups;
}

static void test_mutations(void)
{
    uint8_t code[9];
    push(code, PLC_DINT, 1);
    code[6] = PLC_STORE;
    code[7] = 2;
    code[8] = PLC_HALT;
    fixture base = build(code, sizeof code, 1);
    uint32_t seed = 12345;
    for (unsigned j = 0; j < 4000; ++j) {
        fixture f = base;
        seed = seed * UINT32_C(1664525) + UINT32_C(1013904223);
        size_t index = seed % f.length;
        f.bytes[index] ^= (uint8_t)(1u << (j % 8));
        if (j % 2)
            seal(&f); /* Explore structural checks past CRC. */
        plc_fault result =
            plc_validate(&program, f.bytes, f.length, &profile, &work, &diag);
        if (!result) {
            plc_values v = {{0}};
            CHECK(plc_vm_run(&program, &v, PLC_INSTRUCTION_BUDGET, &diag) ==
                  PLC_FAULT_NONE);
        } else
            CHECK(!program.valid);
    }
    ++groups;
}

/* A real producer/scan interleaving test of slot publication, not timing. */
static fixture concurrent_image;
static void *producer(void *unused)
{
    (void)unused;
    for (unsigned n = 1; n <= 2000; ++n) {
        uint32_t gen;
        while (atomic_load_explicit(&runtime.mailbox, memory_order_acquire) !=
               PLC_IDLE)
            sched_yield();
        CHECK(plc_runtime_stage(&runtime, concurrent_image.bytes,
                                concurrent_image.length, &profile, &work, &gen,
                                &diag) == PLC_OK);
        CHECK(gen == n && plc_runtime_activate(&runtime, gen) == PLC_OK);
    }
    return NULL;
}
static void test_concurrent_activation(void)
{
    const uint8_t code[] = {PLC_LOAD, 0, PLC_NOT, PLC_STORE, 1, PLC_HALT};
    concurrent_image = build(code, sizeof code, 1);
    plc_runtime_init(&runtime);
    pthread_t thread;
    CHECK(pthread_create(&thread, NULL, producer, NULL) == 0);
    unsigned count = 0;
    while (count < 2000) {
        if (atomic_load_explicit(&runtime.active, memory_order_acquire)) {
            plc_values inputs = {{0}};
            CHECK(plc_runtime_scan(&runtime, &inputs, 20) == PLC_FAULT_NONE);
            CHECK(atomic_load(&runtime.active)->values.cell[1] == 1);
        }
        if (plc_runtime_boundary(&runtime)) {
            ++count;
            CHECK(atomic_load(&runtime.active)->generation == count);
        } else
            sched_yield();
    }
    CHECK(pthread_join(thread, NULL) == 0);
    ++groups;
}

int main(void)
{
    test_header_and_tags();
    test_operators();
    test_control_flow();
    test_rejections_and_limits();
    test_runtime_faults();
    test_slot_lifecycle();
    test_mutations();
    test_concurrent_activation();
    printf(
        "core: %u groups passed (4000 mutations, 2000 concurrent activations)\n",
        groups);
    printf(
        "static sizes: runtime=%zu program=%zu validator_workspace=%zu bytes\n",
        sizeof runtime, sizeof program, sizeof work);
    return 0;
}
