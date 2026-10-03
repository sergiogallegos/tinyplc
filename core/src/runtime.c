#include "internal.h"

void plc_runtime_init(plc_runtime *r)
{
    memset(r, 0, sizeof *r); /* Initialization must precede either owner. */
    atomic_init(&r->active, NULL);
    atomic_init(&r->mailbox, PLC_IDLE);
    r->next_generation = 1;
    r->diagnostic.pc = PLC_NO_PC;
}
bool plc_runtime_lock_free(const plc_runtime *r)
{
    return atomic_is_lock_free(&r->active) && atomic_is_lock_free(&r->mailbox);
}

plc_result plc_runtime_stage(plc_runtime *r, const uint8_t *bytes,
                             size_t length, const plc_profile *profile,
                             plc_workspace *w, uint32_t *generation,
                             plc_diagnostic *d)
{
    unsigned expected = PLC_IDLE;
    if (!atomic_compare_exchange_strong_explicit(
            &r->mailbox, &expected, PLC_STAGING, memory_order_acq_rel,
            memory_order_acquire))
        return PLC_BUSY;
    if (!r->next_generation) {
        atomic_store_explicit(&r->mailbox, PLC_IDLE, memory_order_release);
        return PLC_INVALID;
    }
    /* While STAGING, the scan cannot swap; active is stable. */
    plc_slot *active = atomic_load_explicit(&r->active, memory_order_acquire);
    r->staged = active == &r->slots[0] ? 1u : 0u;
    plc_slot *s = &r->slots[r->staged];
    plc_fault f = plc_validate(&s->program, bytes, length, profile, w, d);
    if (f) {
        atomic_store_explicit(&r->mailbox, PLC_IDLE, memory_order_release);
        return PLC_INVALID;
    }
    s->generation = r->next_generation++;
    if (generation)
        *generation = s->generation;
    atomic_store_explicit(&r->mailbox, PLC_READY, memory_order_release);
    return PLC_OK;
}
plc_result plc_runtime_activate(plc_runtime *r, uint32_t generation)
{
    if (atomic_load_explicit(&r->mailbox, memory_order_acquire) != PLC_READY)
        return PLC_BUSY;
    if (r->slots[r->staged].generation != generation)
        return PLC_STALE;
    atomic_store_explicit(&r->mailbox, PLC_PENDING, memory_order_release);
    return PLC_OK;
}
plc_result plc_runtime_discard(plc_runtime *r)
{
    unsigned expected = PLC_READY;
    return atomic_compare_exchange_strong_explicit(
               &r->mailbox, &expected, PLC_IDLE, memory_order_acq_rel,
               memory_order_acquire)
               ? PLC_OK
               : PLC_BUSY;
}
bool plc_runtime_boundary(plc_runtime *r)
{
    if (atomic_load_explicit(&r->mailbox, memory_order_acquire) != PLC_PENDING)
        return false;
    plc_slot *s = &r->slots[r->staged];
    memset(&s->values, 0,
           sizeof s->values); /* M5 will add name/type migration. */
    r->faulted = false;
    atomic_store_explicit(&r->active, s, memory_order_release);
    /* Release old slot only AFTER the scan owner has stopped using it. */
    atomic_store_explicit(&r->mailbox, PLC_IDLE, memory_order_release);
    return true;
}
plc_fault plc_runtime_scan(plc_runtime *r, const plc_values *inputs,
                           unsigned budget)
{
    plc_slot *s = atomic_load_explicit(&r->active, memory_order_acquire);
    if (!s)
        return plc_error(&r->diagnostic, PLC_FAULT_IMAGE, PLC_NO_PC, 0,
                         "no active program");
    r->working = s->values;
    for (unsigned j = 0; j < s->program.tag_count; ++j) {
        plc_tag t;
        (void)plc_tag_at(&s->program, j, &t);
        if (t.kind == PLC_INPUT) {
            r->working.cell[j] = inputs->cell[j];
            /* Keep valid sampled inputs visible even if logic later faults.
             * Invalid BOOL samples are rejected here and fault in the VM. */
            (void)plc_input_set(&s->program, &s->values, j, inputs->cell[j]);
        }
    }
    if (r->faulted) {
        plc_outputs_clear(&s->program, &s->values);
        return r->diagnostic.fault;
    }
    plc_diagnostic current;
    plc_fault f = plc_vm_run(&s->program, &r->working, budget, &current);
    if (f) {
        r->faulted = true;
        r->diagnostic = current;
        plc_outputs_clear(&s->program, &s->values);
    } else
        s->values = r->working;
    return f;
}
