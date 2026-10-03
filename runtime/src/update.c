#include "tinyplc/update.h"
#include "tinyplc/engineering.h"
#include <string.h>
void tinyplc_update_init(tinyplc_update *u,tinyplc_loader *l,unsigned active) {
    memset(u,0,sizeof *u);u->loader=l;u->active=active;
}
bool tinyplc_update_busy(const tinyplc_update *u) {
    return u->phase!=TPLC_UPDATE_IDLE && u->phase!=TPLC_UPDATE_COMPLETE;
}
uint32_t tinyplc_update_reserve(tinyplc_update *u,uint32_t kind,uint32_t generation) {
    tinyplc_loader *l=u->loader;
    if(tinyplc_update_busy(u)||l->transfer_id)return TPLC_STATUS_BUSY;
    unsigned target=1-u->active;
    tinyplc_slot *s=&l->slots[target];
    if(kind==TPLC_UPDATE_ACTIVATE) {
        if(!generation || s->generation!=generation || s->state!=TPLC_SLOT_READY)return TPLC_STATUS_BAD_REQUEST;
    } else if(kind==TPLC_UPDATE_ROLLBACK) {
        if(!u->saved_generation || s->state!=TPLC_SLOT_PREVIOUS || s->generation!=u->saved_generation || target!=u->saved_slot)
            return TPLC_STATUS_NO_PROGRAM;
        generation=s->generation;
    } else return TPLC_STATUS_BAD_REQUEST;
    u->source=u->active;u->target=target;u->source_generation=l->slots[u->active].generation;
    u->requested=generation;u->pending=generation;u->kind=kind;
    u->outcome=TPLC_OUTCOME_PENDING;u->phase=TINYPLC_UPDATE_PLANNING;
    u->failed_generation=0;u->first_fault=0;u->recovery_fault=0;u->line=0;u->column=0;
    u->failed_scan=0;u->completed_scan=0;u->completed_generation=0;
    s->state=TPLC_SLOT_PENDING;return 0;
}
void tinyplc_update_plan(tinyplc_update *u) {
    /* No state reads or long critical section. Both immutable schemas are pinned
     * in PLANNING; scan_prepare must not consume this partially constructed map. */
    if(u->phase!=TINYPLC_UPDATE_PLANNING)return;
    memset(u->map,TINYPLC_UPDATE_NO_MATCH,sizeof u->map);
    const tinyplc_slot *a=&u->loader->slots[u->source],*b=&u->loader->slots[u->target];
    if(a->tag_count>64 || b->tag_count>64)return;
    if(u->kind==TPLC_UPDATE_ACTIVATE)for(unsigned i=0;i<b->tag_count;++i) {
        const uint8_t *bt=b->tags+i*TPLC_TAG_BYTES;
        if(bt[TPLC_TAG_CLASS_OFFSET]!=TPLC_CLASS_VAR)continue;
        for(unsigned j=0;j<a->tag_count;++j) {
            const uint8_t *at=a->tags+j*TPLC_TAG_BYTES;
            if(at[TPLC_TAG_CLASS_OFFSET]==TPLC_CLASS_VAR && at[TPLC_TAG_TYPE_OFFSET]==bt[TPLC_TAG_TYPE_OFFSET] && !memcmp(at,bt,32)) {
                u->map[i]=(uint8_t)j;break;
            }
        }
    }
}
void tinyplc_update_arm(tinyplc_update *u) {if(u->phase==TINYPLC_UPDATE_PLANNING)u->phase=TPLC_UPDATE_QUEUED;}
void tinyplc_update_retire(tinyplc_update *u,unsigned slot) {
    if(u->saved_generation && u->saved_slot==slot)u->saved_generation=0;
}
static bool layout(const tinyplc_slot *s,unsigned slot) {
    uint32_t base=slot?TPLC_SLOT_B_BASE:TPLC_SLOT_A_BASE;
    if(!s->generation || !s->tag_count || s->tag_count>64 || !(s->entry&1) || s->entry<base || s->entry>=base+TPLC_CODE_CAPACITY)return false;
    for(unsigned i=0;i<s->tag_count;++i) {
        const uint8_t *t=s->tags+i*TPLC_TAG_BYTES;
        if((t[32]!=TPLC_TYPE_BOOL && t[32]!=TPLC_TYPE_DINT) || t[33]<TPLC_CLASS_INPUT || t[33]>TPLC_CLASS_VAR)return false;
    }
    return true;
}
static void complete(tinyplc_update *u,uint64_t scan,uint32_t outcome) {
    u->pending=0;u->completed_scan=scan;u->completed_generation=u->loader->slots[u->active].generation;
    u->outcome=outcome;u->phase=TPLC_UPDATE_COMPLETE;
}
static void initial_cells(tinyplc_update *u,tinyplc_scan_state *s,bool restore) {
    for(unsigned i=0;i<s->count;++i) {
        s->committed[i]=0;
        if(s->classes[i]==TPLC_CLASS_VAR && u->saved_generation) {
            unsigned j=restore?i:u->map[i];
            if(j<u->saved_count)s->committed[i]=u->saved[j];
        }
    }
}
bool tinyplc_update_prepare(tinyplc_update *u,tinyplc_scan_state *state,uint64_t scan) {
    bool recovery=u->phase==TPLC_UPDATE_RECOVERY_QUEUED;
    if(!recovery && u->phase!=TPLC_UPDATE_QUEUED)return false;
    bool restore=recovery || u->kind==TPLC_UPDATE_ROLLBACK;
    tinyplc_slot *a=&u->loader->slots[u->active],*b=&u->loader->slots[u->target];
    bool valid=u->target!=u->active && a->state==TPLC_SLOT_ACTIVE &&
        b->state==(recovery?TPLC_SLOT_PREVIOUS:TPLC_SLOT_PENDING) &&
        layout(a,u->active) && layout(b,u->target) && b->generation==u->pending;
    if(!recovery)valid=valid && u->active==u->source && a->generation==u->source_generation;
    if(restore)valid=valid && u->saved_generation==b->generation && u->saved_slot==u->target &&
        u->saved_count==b->tag_count && u->saved_entry==b->entry && u->saved_schema==b->schema_crc;
    else {
        valid=valid && state->count==a->tag_count;
        for(unsigned i=0;valid && i<state->count;++i) {
            const uint8_t *t=a->tags+i*TPLC_TAG_BYTES;
            valid=state->types[i]==t[32] && state->classes[i]==t[33] &&
                (t[32]!=TPLC_TYPE_BOOL || state->committed[i]<=1);
        }
    }
    if(!restore)for(unsigned i=0;valid && i<b->tag_count;++i) {
        unsigned j=u->map[i];
        if(j==TINYPLC_UPDATE_NO_MATCH)continue;
        const uint8_t *bt=b->tags+i*TPLC_TAG_BYTES;
        if(j>=a->tag_count){valid=false;break;}
        const uint8_t *at=a->tags+j*TPLC_TAG_BYTES;
        if(bt[33]!=TPLC_CLASS_VAR || at[33]!=TPLC_CLASS_VAR || bt[32]!=at[32] || memcmp(bt,at,32))valid=false;
    }
    if(restore)for(unsigned i=0;valid && i<b->tag_count;++i)
        if(b->tags[i*TPLC_TAG_BYTES+32]==TPLC_TYPE_BOOL && u->saved[i]>1)valid=false;
    if(!valid) {
        state->fault=TINYPLC_SCAN_BAD_STATE;u->saved_generation=0;
        if(recovery)u->recovery_fault=TINYPLC_SCAN_BAD_STATE;
        if(b!=a){b->state=TPLC_SLOT_EMPTY;b->generation=0;}
        complete(u,scan,TPLC_OUTCOME_REJECTED);return false;
    }
    if(!restore) {
        u->saved_generation=state->fault?0:a->generation;
        u->saved_slot=u->active;u->saved_count=state->count;u->saved_entry=a->entry;u->saved_schema=a->schema_crc;
        for(unsigned i=0;i<state->count;++i)u->saved[i]=state->classes[i]==TPLC_CLASS_VAR?state->committed[i]:0;
    }
    memset(state,0,sizeof *state);state->count=b->tag_count;
    for(unsigned i=0;i<state->count;++i){state->types[i]=b->tags[i*TPLC_TAG_BYTES+32];state->classes[i]=b->tags[i*TPLC_TAG_BYTES+33];}
    initial_cells(u,state,restore);
    a->state=(!restore && u->saved_generation)?TPLC_SLOT_PREVIOUS:TPLC_SLOT_EMPTY;
    if(a->state==TPLC_SLOT_EMPTY)a->generation=0;
    b->state=TPLC_SLOT_ACTIVE;u->active=u->target;
    u->phase=recovery?TPLC_UPDATE_RECOVERY_TRIAL:TPLC_UPDATE_TRIAL;
    return true;
}
void tinyplc_update_discard(tinyplc_update *u,tinyplc_scan_state *state) {
    if(state->fault && (u->phase==TPLC_UPDATE_TRIAL || u->phase==TPLC_UPDATE_RECOVERY_TRIAL))
        initial_cells(u,state,u->phase==TPLC_UPDATE_RECOVERY_TRIAL || u->kind==TPLC_UPDATE_ROLLBACK);
}
void tinyplc_update_finish(tinyplc_update *u,tinyplc_scan_state *state,const tinyplc_native_diagnostic *d,uint64_t scan) {
    bool recovery=u->phase==TPLC_UPDATE_RECOVERY_TRIAL;
    if(!recovery && u->phase!=TPLC_UPDATE_TRIAL)return;
    bool restore=recovery || u->kind==TPLC_UPDATE_ROLLBACK;
    if(state->fault) {
        /* Also undo successful user work if trusted post-entry work ran late. */
        initial_cells(u,state,restore);
        if(recovery)u->recovery_fault=state->fault;
        else {
            u->failed_generation=u->loader->slots[u->active].generation;u->first_fault=state->fault;
            u->failed_scan=scan;u->line=d->line;u->column=d->column;
        }
        if(!restore && u->saved_generation) {
            u->target=u->saved_slot;u->pending=u->saved_generation;
            u->phase=TPLC_UPDATE_RECOVERY_QUEUED;return;
        }
    }
    if(restore) {
        tinyplc_slot *departed=&u->loader->slots[1-u->active];
        departed->state=TPLC_SLOT_EMPTY;departed->generation=0;u->saved_generation=0;
    }
    complete(u,scan,state->fault?TPLC_OUTCOME_REJECTED:recovery?TPLC_OUTCOME_ROLLED_BACK:TPLC_OUTCOME_RUNNING);
}
void tinyplc_update_status(const tinyplc_update *u,uint8_t *r) {
    memset(r,0,TPLC_GET_UPDATE_STATUS_RESPONSE_BYTES);
    r[1]=(uint8_t)u->kind;r[2]=(uint8_t)(u->phase==TINYPLC_UPDATE_PLANNING?TPLC_UPDATE_QUEUED:u->phase);r[3]=(uint8_t)u->outcome;
    tinyplc_put32(r,5,u->source_generation);tinyplc_put32(r,9,u->requested);tinyplc_put32(r,13,u->failed_generation);
    tinyplc_put32(r,17,u->first_fault);tinyplc_put32(r,21,u->recovery_fault);tinyplc_put32(r,25,u->line);tinyplc_put32(r,29,u->column);
    tinyplc_put64(r,33,u->failed_scan);tinyplc_put32(r,41,u->completed_generation);tinyplc_put64(r,45,u->completed_scan);
}
