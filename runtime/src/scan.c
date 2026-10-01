#include "tinyplc/scan.h"
uint32_t tinyplc_scan_init(tinyplc_scan_state *s, uint32_t count,
                          const uint8_t *types, const uint8_t *classes)
{
    *s = (tinyplc_scan_state){0};
    s->fault = TINYPLC_SCAN_BAD_LAYOUT;
    if (!count || count > 64 || !types || !classes) return s->fault;
    for (uint32_t i = 0; i < count; ++i) {
        if ((types[i] != TINYPLC_NATIVE_TYPE_BOOL && types[i] != TINYPLC_NATIVE_TYPE_DINT)
            || classes[i] < TINYPLC_NATIVE_INPUT || classes[i] > TINYPLC_NATIVE_VAR)
            return s->fault;
    }
    s->count = count;
    for (uint32_t i = 0; i < count; ++i) {
        s->types[i] = types[i]; s->classes[i] = classes[i];
    }
    s->fault = 0;
    return 0;
}
uint32_t tinyplc_scan_step(tinyplc_scan_state *s, const uint32_t *inputs,
                          uint32_t *working, tinyplc_native_diagnostic *diagnostic,
                          tinyplc_native_entry entry, tinyplc_cycle_clock clock,
                          tinyplc_output_commit output, uint32_t start, uint32_t budget)
{
    if (!budget || budget >= UINT32_C(0x80000000)) s->fault = TINYPLC_SCAN_OVERRUN;
    if (!s->fault) {
        for (uint32_t i = 0; i < s->count; ++i) {
            working[i] = s->committed[i];
            if (s->classes[i] == TINYPLC_NATIVE_INPUT &&
                s->types[i] == TINYPLC_NATIVE_TYPE_BOOL && inputs[i] > 1)
                s->fault = TINYPLC_NATIVE_BAD_BOOL;
        }
        *diagnostic = (tinyplc_native_diagnostic){0};
        if (!s->fault) s->fault = entry(inputs, working, s->count, diagnostic);
        if (!s->fault) {
            for (uint32_t i = 0; i < s->count; ++i) {
                if ((s->classes[i] == TINYPLC_NATIVE_INPUT && working[i] != 0)
                    || (s->types[i] == TINYPLC_NATIVE_TYPE_BOOL && working[i] > 1))
                    s->fault = TINYPLC_SCAN_BAD_STATE;
            }
        }
        if (!s->fault && clock() - start >= budget) s->fault = TINYPLC_SCAN_OVERRUN;
        if (!s->fault) {
            output(working);
            /* A slow output hook can already have changed pins. Detect it and
             * force safe outputs; no hard deadline containment is claimed. */
            if (clock() - start >= budget) s->fault = TINYPLC_SCAN_OVERRUN;
            else for (uint32_t i = 0; i < s->count; ++i) s->committed[i] = working[i];
        }
    }
    if (s->fault) {
        for (uint32_t i = 0; i < s->count; ++i)
            if (s->classes[i] == TINYPLC_NATIVE_OUTPUT) s->committed[i] = 0;
        output(s->committed);
    }
    return s->fault;
}
