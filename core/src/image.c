#include "internal.h"

static uint32_t crc(const uint8_t *data, size_t length, bool image)
{
    uint32_t c = UINT32_MAX;
    for (size_t j = 0; j < length; ++j) {
        c ^= image && j >= 20 && j < 24 ? 0 : data[j];
        for (unsigned b = 0; b < 8; ++b)
            c = (c >> 1) ^ (UINT32_C(0xedb88320) & (0u - (c & 1u)));
    }
    return c ^ UINT32_MAX;
}
uint32_t plc_crc32(const uint8_t *data, size_t length)
{
    return crc(data, length, false);
}
uint32_t plc_image_crc32(const uint8_t *data, size_t length)
{
    return crc(data, length, true);
}

plc_fault plc_decode(const plc_program *p, unsigned pc, plc_instruction *i,
                     plc_diagnostic *d)
{
    if (pc >= p->code_length)
        return plc_error(d, PLC_FAULT_IMAGE, pc, 0, "PC outside code");
    const uint8_t *code = p->image + p->code_offset;
    *i = (plc_instruction){.op = code[pc], .width = 1};
    switch (i->op) {
    case PLC_PUSH:
        i->width = 6;
        break;
    case PLC_LOAD:
    case PLC_STORE:
        i->width = 2;
        break;
    case PLC_JMP:
    case PLC_JZ:
        i->width = 3;
        break;
    case PLC_ADD:
    case PLC_SUB:
    case PLC_MUL:
    case PLC_DIV:
    case PLC_NEG:
    case PLC_AND:
    case PLC_OR:
    case PLC_XOR:
    case PLC_NOT:
    case PLC_EQ:
    case PLC_NE:
    case PLC_LT:
    case PLC_GT:
    case PLC_LE:
    case PLC_GE:
    case PLC_HALT:
        break;
    default:
        return plc_error(d, PLC_FAULT_OPCODE, pc, i->op, "unknown opcode");
    }
    if (i->width > p->code_length - pc)
        return plc_error(d, PLC_FAULT_IMAGE, pc, i->op, "truncated operand");
    if (i->op == PLC_PUSH) {
        i->type = code[pc + 1];
        i->value = plc_u32(code + pc + 2);
        if ((i->type != PLC_BOOL && i->type != PLC_DINT) ||
            (i->type == PLC_BOOL && i->value > 1))
            return plc_error(d, PLC_FAULT_TYPE, pc, i->op,
                             "invalid typed constant");
    }
    if (i->op == PLC_LOAD || i->op == PLC_STORE) {
        plc_tag t;
        i->tag = code[pc + 1];
        if (!plc_tag_at(p, i->tag, &t))
            return plc_error(d, PLC_FAULT_TAG, pc, i->op,
                             "tag index out of range");
        i->type = t.type;
        if (i->op == PLC_STORE && t.kind == PLC_INPUT)
            return plc_error(d, PLC_FAULT_TAG, pc, i->op, "STORE to input");
    }
    if (i->op == PLC_JMP || i->op == PLC_JZ) {
        i->target = plc_u16(code + pc + 1);
        if (i->target <= pc || i->target >= p->code_length)
            return plc_error(d, PLC_FAULT_IMAGE, pc, i->op,
                             "jump must be forward and within code");
    }
    return PLC_FAULT_NONE;
}

/* One bit per operand: 0=BOOL, 1=DINT. Bits above depth are always zero. */
plc_fault plc_stack_effect(const plc_program *p, const plc_instruction *i,
                           unsigned pc, unsigned *depth, uint64_t *types,
                           plc_diagnostic *d)
{
    (void)p;
    unsigned pop = 0, push = 0, required = 0, result = 0;
    switch (i->op) {
    case PLC_PUSH:
    case PLC_LOAD:
        push = 1;
        result = i->type;
        break;
    case PLC_STORE:
        pop = 1;
        required = i->type;
        break;
    case PLC_NEG:
        pop = push = 1;
        required = result = PLC_DINT;
        break;
    case PLC_NOT:
        pop = push = 1;
        required = result = PLC_BOOL;
        break;
    case PLC_JZ:
        pop = 1;
        required = PLC_BOOL;
        break;
    case PLC_ADD:
    case PLC_SUB:
    case PLC_MUL:
    case PLC_DIV:
        pop = 2;
        push = 1;
        required = result = PLC_DINT;
        break;
    case PLC_AND:
    case PLC_OR:
    case PLC_XOR:
        pop = 2;
        push = 1;
        required = result = PLC_BOOL;
        break;
    case PLC_EQ:
    case PLC_NE:
        pop = 2;
        push = 1;
        result = PLC_BOOL;
        break;
    case PLC_LT:
    case PLC_GT:
    case PLC_LE:
    case PLC_GE:
        pop = 2;
        push = 1;
        required = PLC_DINT;
        result = PLC_BOOL;
        break;
    case PLC_HALT:
        if (*depth)
            return plc_error(d, PLC_FAULT_STACK, pc, i->op,
                             "HALT requires empty stack");
        break;
    case PLC_JMP:
        break;
    default:
        return plc_error(d, PLC_FAULT_OPCODE, pc, i->op, "unknown opcode");
    }
    if (*depth < pop || *depth - pop + push > PLC_MAX_STACK)
        return plc_error(d, PLC_FAULT_STACK, pc, i->op,
                         "stack underflow or overflow");
    for (unsigned n = 0; n < pop; ++n) {
        unsigned type = ((*types >> (*depth - 1)) & 1u) ? PLC_DINT : PLC_BOOL;
        if (!required)
            required = type; /* EQ/NE require two identical types. */
        if (type != required)
            return plc_error(d, PLC_FAULT_TYPE, pc, i->op,
                             "operand type mismatch");
        --*depth;
        *types &= ~(UINT64_C(1) << *depth);
    }
    if (push) {
        if (result == PLC_DINT)
            *types |= UINT64_C(1) << *depth;
        ++*depth;
    }
    return PLC_FAULT_NONE;
}

static bool identifier(const uint8_t *name)
{
    unsigned j = 0;
    for (; j < 32 && name[j]; ++j) {
        bool letter = (name[j] >= 'A' && name[j] <= 'Z') || name[j] == '_';
        if (!letter && !(j && name[j] >= '0' && name[j] <= '9'))
            return false;
    }
    if (j == 0 || j == 32)
        return false;
    for (; j < 32; ++j)
        if (name[j])
            return false;
    return true;
}

static bool merge(plc_workspace *w, unsigned pc, unsigned depth, uint64_t types)
{
    if (w->depth[pc] == UINT8_MAX) {
        w->depth[pc] = (uint8_t)depth;
        w->types[pc] = types;
        return true;
    }
    return w->depth[pc] == depth && w->types[pc] == types;
}

plc_fault plc_validate(plc_program *out, const uint8_t *bytes, size_t length,
                       const plc_profile *profile, plc_workspace *w,
                       plc_diagnostic *d)
{
    out->valid = false;
    plc_error(d, PLC_FAULT_NONE, PLC_NO_PC, 0, "ok");
    if (!bytes || !w || length < PLC_HEADER_BYTES ||
        length > PLC_MAX_IMAGE_BYTES)
        return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0, "image size");
    unsigned code_len = plc_u16(bytes + 8), tags = plc_u16(bytes + 10),
             stack = plc_u16(bytes + 12);
    if (memcmp(bytes, "TPLC", 4) || plc_u16(bytes + 4) != 1 ||
        plc_u16(bytes + 6) != PLC_HEADER_BYTES || !code_len ||
        code_len > PLC_MAX_CODE_BYTES || tags > PLC_MAX_TAGS ||
        stack > PLC_MAX_STACK || plc_u16(bytes + 14) ||
        plc_u32(bytes + 16) != length ||
        length != PLC_HEADER_BYTES + tags * PLC_TAG_BYTES + code_len)
        return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0, "invalid header");
    if (plc_u32(bytes + 20) != plc_image_crc32(bytes, length))
        return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0, "CRC32 mismatch");
    memmove(out->image, bytes, length);
    memset(out->boundaries, 0, sizeof out->boundaries);
    out->code_offset = (uint16_t)(PLC_HEADER_BYTES + tags * PLC_TAG_BYTES);
    out->code_length = (uint16_t)code_len;
    out->tag_count = (uint16_t)tags;
    out->max_stack = (uint16_t)stack;
    for (unsigned j = 0; j < tags; ++j) {
        const uint8_t *t = out->image + PLC_HEADER_BYTES + j * PLC_TAG_BYTES;
        if ((t[0] != PLC_BOOL && t[0] != PLC_DINT) || t[1] < PLC_INPUT ||
            t[1] > PLC_VAR || t[2] || t[3] || !identifier(t + 4))
            return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0,
                             "invalid tag descriptor");
        for (unsigned k = 0; k < j; ++k)
            if (strcmp((const char *)t + 4, (const char *)out->image +
                                                PLC_HEADER_BYTES +
                                                k * PLC_TAG_BYTES + 4) == 0)
                return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0,
                                 "duplicate tag name");
        if (t[1] != PLC_VAR) {
            bool found = false;
            if (profile && profile->items)
                for (size_t k = 0; k < profile->count; ++k) {
                    const plc_binding *b = &profile->items[k];
                    if (b->name && b->type == t[0] && b->kind == t[1] &&
                        strcmp(b->name, (const char *)t + 4) == 0)
                        found = true;
                }
            if (!found)
                return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0,
                                 "unsupported I/O binding");
        }
    }
    /* Pass 1 decodes EVERY instruction, including unreachable operands. */
    for (unsigned pc = 0; pc < code_len;) {
        plc_instruction i;
        plc_fault f = plc_decode(out, pc, &i, d);
        if (f)
            return f;
        out->boundaries[pc / 8] |= (uint8_t)(1u << (pc % 8));
        pc += i.width;
    }
    memset(w->depth, UINT8_MAX, sizeof w->depth);
    w->depth[0] = 0;
    w->types[0] = 0;
    unsigned maximum = 0;
    bool halt = false;
    /* Forward-only control flow means predecessors are processed first. */
    for (unsigned pc = 0; pc < code_len;) {
        plc_instruction i;
        plc_fault f = plc_decode(out, pc, &i, d);
        if (f)
            return f;
        unsigned next = pc + i.width;
        if ((i.op == PLC_JMP || i.op == PLC_JZ) && !plc_boundary(out, i.target))
            return plc_error(d, PLC_FAULT_IMAGE, pc, i.op, "jump into operand");
        if (w->depth[pc] != UINT8_MAX) {
            unsigned depth = w->depth[pc];
            uint64_t types = w->types[pc];
            f = plc_stack_effect(out, &i, pc, &depth, &types, d);
            if (f)
                return f;
            if (depth > maximum)
                maximum = depth;
            if (i.op == PLC_HALT)
                halt = true;
            else {
                if ((i.op == PLC_JMP || i.op == PLC_JZ) &&
                    !merge(w, i.target, depth, types))
                    return plc_error(d, PLC_FAULT_STACK, pc, i.op,
                                     "branch stack mismatch");
                if (i.op != PLC_JMP &&
                    (next >= code_len || !merge(w, next, depth, types)))
                    return plc_error(d, PLC_FAULT_STACK, pc, i.op,
                                     "fallthrough or stack merge failure");
            }
        }
        pc = next;
    }
    if (!halt || maximum != stack)
        return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0,
                         "HALT or declared stack mismatch");
    out->valid = true;
    return PLC_FAULT_NONE;
}
