#include "internal.h"

bool plc_tag_at(const plc_program *p, unsigned index, plc_tag *out)
{
    if (index >= p->tag_count || index >= PLC_MAX_TAGS) return false;
    const uint8_t *t = p->image + PLC_HEADER_BYTES + index * PLC_TAG_BYTES;
    *out = (plc_tag){(const char *)(t + 4), t[0], t[1]};
    return true;
}

static unsigned upper(unsigned c) { return c >= 'a' && c <= 'z' ? c - ('a' - 'A') : c; }

int plc_tag_find(const plc_program *p, const char *name)
{
    if (!p->valid || !name) return -1;
    for (unsigned i = 0; i < p->tag_count; ++i) {
        plc_tag t;
        if (!plc_tag_at(p, i, &t)) return -1;
        unsigned j = 0;
        while (j < 32 && name[j] && t.name[j] && upper((unsigned char)name[j]) == (unsigned char)t.name[j]) ++j;
        if (j < 32 && name[j] == 0 && t.name[j] == 0) return (int)i;
    }
    return -1;
}

static plc_result set(const plc_program *p, plc_values *v, unsigned index, uint32_t value, unsigned kind)
{
    plc_tag t;
    if (!p->valid || !plc_tag_at(p, index, &t)) return PLC_NOT_FOUND;
    if (t.kind != kind) return PLC_NOT_WRITABLE;
    if (t.type == PLC_BOOL && value > 1) return PLC_INVALID;
    v->cell[index] = value;
    return PLC_OK;
}
plc_result plc_tag_write(const plc_program *p, plc_values *v, unsigned index, uint32_t value) { return set(p, v, index, value, PLC_VAR); }
plc_result plc_input_set(const plc_program *p, plc_values *v, unsigned index, uint32_t value) { return set(p, v, index, value, PLC_INPUT); }
void plc_outputs_clear(const plc_program *p, plc_values *v)
{
    for (unsigned i = 0; i < p->tag_count && i < PLC_MAX_TAGS; ++i) {
        plc_tag t;
        if (plc_tag_at(p, i, &t) && t.kind == PLC_OUTPUT) v->cell[i] = 0;
    }
}
int64_t plc_signed(uint32_t bits) { return bits <= INT32_MAX ? (int64_t)bits : (int64_t)bits - INT64_C(4294967296); }
