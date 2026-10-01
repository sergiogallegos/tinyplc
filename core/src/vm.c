#include "internal.h"

plc_fault plc_vm_run(const plc_program *p, plc_values *v, unsigned budget, plc_diagnostic *d)
{
    if (!p->valid || !p->code_length || p->code_length > PLC_MAX_CODE_BYTES || p->tag_count > PLC_MAX_TAGS ||
        p->code_offset != PLC_HEADER_BYTES + p->tag_count * PLC_TAG_BYTES)
        return plc_error(d, PLC_FAULT_IMAGE, PLC_NO_PC, 0, "unvalidated program");
    for (unsigned j = 0; j < p->tag_count; ++j) {
        plc_tag t;
        (void)plc_tag_at(p, j, &t);
        if ((t.type != PLC_BOOL && t.type != PLC_DINT) || (t.type == PLC_BOOL && v->cell[j] > 1))
            return plc_error(d, PLC_FAULT_TYPE, PLC_NO_PC, 0, "invalid tag value/type");
    }
    uint32_t stack[PLC_MAX_STACK];
    uint64_t types = 0;
    unsigned depth = 0, pc = 0;
    for (unsigned executed = 0; executed < budget; ++executed) {
        plc_instruction i;
        if (!plc_boundary(p, pc)) return plc_error(d, PLC_FAULT_IMAGE, pc, 0, "invalid PC boundary");
        plc_fault f = plc_decode(p, pc, &i, d);
        if (f) return f;
        unsigned before = depth;
        f = plc_stack_effect(p, &i, pc, &depth, &types, d);
        if (f) return f;
        if (depth > p->max_stack) return plc_error(d, PLC_FAULT_STACK, pc, i.op, "declared stack exceeded");
        /* Types/bounds checked before any stack reads. */
        uint32_t a = before >= 2 ? stack[before - 2] : 0;
        uint32_t b = before >= 1 ? stack[before - 1] : 0;
        uint32_t result = 0;
        bool binary = false;
        unsigned next = pc + i.width;
        switch (i.op) {
        case PLC_PUSH: stack[before] = i.value; break;
        case PLC_LOAD: stack[before] = v->cell[i.tag]; break;
        case PLC_STORE: v->cell[i.tag] = b; break;
        case PLC_NEG: stack[before - 1] = 0u - b; break;
        case PLC_NOT: stack[before - 1] = !b; break;
        case PLC_ADD: result = a + b; binary = true; break;
        case PLC_SUB: result = a - b; binary = true; break;
        case PLC_MUL: result = a * b; binary = true; break;
        case PLC_DIV:
            if (!b) return plc_error(d, PLC_FAULT_DIV_ZERO, pc, i.op, "division by zero");
            /* int64_t represents the INT32_MIN/-1 quotient without UB. */
            result = (uint32_t)(plc_signed(a) / plc_signed(b)); binary = true; break;
        case PLC_AND: result = a & b; binary = true; break;
        case PLC_OR: result = a | b; binary = true; break;
        case PLC_XOR: result = a ^ b; binary = true; break;
        case PLC_EQ: result = a == b; binary = true; break;
        case PLC_NE: result = a != b; binary = true; break;
        case PLC_LT: result = plc_signed(a) < plc_signed(b); binary = true; break;
        case PLC_GT: result = plc_signed(a) > plc_signed(b); binary = true; break;
        case PLC_LE: result = plc_signed(a) <= plc_signed(b); binary = true; break;
        case PLC_GE: result = plc_signed(a) >= plc_signed(b); binary = true; break;
        case PLC_JMP: next = i.target; break;
        case PLC_JZ: if (!b) next = i.target; break;
        case PLC_HALT: return plc_error(d, PLC_FAULT_NONE, pc, i.op, "ok");
        default: return plc_error(d, PLC_FAULT_OPCODE, pc, i.op, "unknown opcode");
        }
        if (binary) stack[before - 2] = result;
        pc = next;
    }
    return plc_error(d, PLC_FAULT_BUDGET, pc, pc < p->code_length ? p->image[p->code_offset + pc] : 0, "instruction budget exhausted");
}
