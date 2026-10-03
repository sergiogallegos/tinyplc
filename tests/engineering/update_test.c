#include "tinyplc/engineering.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static tinyplc_loader l;
static tinyplc_update u;
static tinyplc_scan_state s;
static uint8_t code[2][TPLC_CODE_CAPACITY];
static tinyplc_native_diagnostic diagnostic={7,9};
static void tag(unsigned slot,unsigned index,const char *name,unsigned type,unsigned cls) {
    uint8_t *t=l.slots[slot].tags+index*40;memset(t,0,40);memcpy(t,name,strlen(name));t[32]=(uint8_t)type;t[33]=(uint8_t)cls;
}
static void setup(void) {
    assert(tinyplc_loader_init(&l,code[0],code[1],0,true));
    l.slots[0].entry=TPLC_SLOT_A_BASE|1;l.slots[0].tag_count=3;
    l.slots[1].entry=TPLC_SLOT_B_BASE|1;l.slots[1].tag_count=4;l.slots[1].state=TPLC_SLOT_READY;l.slots[1].generation=2;
    tag(0,0,"N",2,3);tag(0,1,"FLAG",1,3);tag(0,2,"LED",1,2);
    tag(1,0,"FLAG",1,3);tag(1,1,"NEW",2,3);tag(1,2,"N",2,3);tag(1,3,"LED",1,2);
    uint8_t types[]={2,1,1},classes[]={3,3,2};assert(!tinyplc_scan_init(&s,3,types,classes));
    s.committed[0]=41;s.committed[1]=1;s.committed[2]=1;tinyplc_update_init(&u,&l,0);
}
static void request(uint32_t kind,uint32_t generation) {
    assert(!tinyplc_update_reserve(&u,kind,generation));
    assert(tinyplc_update_busy(&u));
    assert(!tinyplc_update_prepare(&u,&s,99)); /* Cannot consume half-built map. */
    tinyplc_update_plan(&u);tinyplc_update_arm(&u);
}
static void finish(uint32_t fault,uint64_t scan) {s.fault=fault;tinyplc_update_finish(&u,&s,&diagnostic,scan);}
static void begin(bool expected) {
    uint8_t p[4],r[256];tinyplc_put32(p,0,204);
    tinyplc_engine e={.loader=&l,.update=&u};
    size_t n=tinyplc_engine_request(&e,TPLC_CMD_DOWNLOAD_BEGIN,p,4,0,r);
    assert(expected?(n==17 && r[0]==0):(n==1 && r[0]==TPLC_STATUS_BUSY));
}
int main(void) {
    setup();request(TPLC_UPDATE_ACTIVATE,2);begin(false);
    s.committed[0]=42; /* Boundary value, not the request-time value. */
    assert(tinyplc_update_prepare(&u,&s,100));
    assert(s.committed[0]==1 && s.committed[1]==0 && s.committed[2]==42 && s.committed[3]==0);
    begin(false);s.committed[2]=900;finish(0,100);
    assert(u.outcome==TPLC_OUTCOME_RUNNING && !tinyplc_update_busy(&u));
    assert(u.saved[0]==42 && u.saved[2]==0);
    request(TPLC_UPDATE_ROLLBACK,0);begin(false);assert(tinyplc_update_prepare(&u,&s,101));
    assert(s.committed[0]==42 && s.committed[1]==1 && s.committed[2]==0);
    ++s.committed[0];finish(0,101);assert(s.committed[0]==43 && u.outcome==TPLC_OUTCOME_RUNNING && !u.saved_generation);
    assert(l.slots[1].state==TPLC_SLOT_EMPTY && !l.slots[1].generation);
    assert(tinyplc_update_reserve(&u,TPLC_UPDATE_ROLLBACK,0)==TPLC_STATUS_NO_PROGRAM);
    /* First-scan fault, old state recovery, retained fault separate from execution. */
    setup();request(1,2);assert(tinyplc_update_prepare(&u,&s,10));s.committed[2]=999;
    finish(5,10);assert(s.committed[2]==41 && u.pending==1 && u.first_fault==5 && u.phase==3);
    begin(false);assert(tinyplc_update_prepare(&u,&s,11));assert(!s.fault && s.committed[0]==41);
    ++s.committed[0];finish(0,11);assert(u.outcome==4 && u.requested==2 && !u.pending && s.committed[0]==42);
    uint8_t r[256];tinyplc_update_status(&u,r);uint32_t value;uint64_t scan;
    assert(tplc_read_u32(r,53,17,&value) && value==5);assert(tplc_read_u64(r,53,33,&scan)&&scan==10);
    assert(r[1]==1 && r[2]==5 && r[3]==4);
    /* Late trusted-work overrun must undo VAR writes before fault publication,
     * but must not release either slot until the next boundary. */
    setup();request(1,2);assert(tinyplc_update_prepare(&u,&s,10));s.committed[2]=999;s.fault=258;
    tinyplc_update_discard(&u,&s);assert(s.committed[2]==41 && u.phase==TPLC_UPDATE_TRIAL);begin(false);
    finish(258,10);assert(u.phase==TPLC_UPDATE_RECOVERY_QUEUED);
    /* Recovery fault never bounces back to failed candidate. */
    setup();request(1,2);assert(tinyplc_update_prepare(&u,&s,10));finish(258,10);
    assert(tinyplc_update_prepare(&u,&s,11));s.committed[0]=999;finish(5,11);
    assert(u.first_fault==258 && u.recovery_fault==5 && s.committed[0]==41 && s.fault==5 && !u.saved_generation && !u.pending && u.outcome==3);
    assert(!tinyplc_update_prepare(&u,&s,12));
    /* Explicit rollback failure consumes checkpoint too. */
    setup();request(1,2);assert(tinyplc_update_prepare(&u,&s,1));finish(0,1);request(2,0);
    assert(tinyplc_update_prepare(&u,&s,2));finish(259,2);assert(u.first_fault==259 && !u.recovery_fault && !u.saved_generation && u.outcome==3);
    /* Later faults do not auto-recover; faulted-source ACTIVATE is cold. */
    setup();request(1,2);assert(tinyplc_update_prepare(&u,&s,1));finish(0,1);finish(5,2);
    assert(u.outcome==2 && !u.pending && s.fault==5);
    setup();s.fault=5;request(1,2);assert(tinyplc_update_prepare(&u,&s,1));assert(!s.committed[0]&&!s.committed[2]&&!u.saved_generation);
    finish(5,1);assert(u.outcome==3 && !u.pending && u.active==1);
    /* Type/class mismatch initializes zero, never converts/migrates I/O. */
    setup();tag(1,0,"FLAG",2,3);tag(1,2,"N",2,1);request(1,2);assert(tinyplc_update_prepare(&u,&s,1));
    for(unsigned i=0;i<4;++i)assert(!s.committed[i]);
    setup();s.committed[1]=2;request(1,2);assert(!tinyplc_update_prepare(&u,&s,1));assert(s.fault==257 && u.outcome==3 && !u.pending && u.active==0);
    setup();request(1,2);l.slots[1].generation=3;assert(!tinyplc_update_prepare(&u,&s,1));assert(s.fault==257);
    setup();request(1,2);l.slots[1].state=TPLC_SLOT_READY;assert(!tinyplc_update_prepare(&u,&s,1));assert(s.fault==257);
    setup();request(1,2);u.map[2]=63;assert(!tinyplc_update_prepare(&u,&s,1));assert(s.fault==257);
    /* BEGIN failure preserves checkpoint; success retires even if expired. */
    setup();request(1,2);assert(tinyplc_update_prepare(&u,&s,1));finish(0,1);
    uint8_t bad[4]={0};tinyplc_engine e={.loader=&l,.update=&u};
    assert(tinyplc_engine_request(&e,2,bad,4,0,r)==1 && r[0]==1 && u.saved_generation==1);
    begin(true);assert(!u.saved_generation);tinyplc_loader_expire(&l,30000);
    assert(tinyplc_update_reserve(&u,2,0)==TPLC_STATUS_NO_PROGRAM);
    /* TIME scalars migrate, TON cells restart even with identical names/types.
     * Explicit rollback and failed-trial recovery also restart TON. */
    for(unsigned failure=0;failure<2;++failure) {
        setup();tag(0,0,"PT",3,3);tag(1,2,"PT",3,3);s.types[0]=3;
        tag(0,1,"__T_DELAY_Q",1,4);tag(1,0,"__T_DELAY_Q",1,4);s.classes[1]=4;
        request(1,2);assert(tinyplc_update_prepare(&u,&s,1));
        assert(s.committed[0]==0 && s.committed[2]==41 && u.saved[1]==0);
        s.committed[0]=1;finish(failure?5:0,1);
        if(!failure)request(2,0);
        assert(tinyplc_update_prepare(&u,&s,2));
        assert(s.committed[0]==41 && s.committed[1]==0);finish(0,2);
    }
    /* Full 64-tag permutation, signed extrema and BOOL canonicality. */
    setup();l.slots[0].tag_count=64;l.slots[1].tag_count=64;s.count=64;
    for(unsigned i=0;i<64;++i) {
        char name[32];snprintf(name,sizeof name,"LONG_COMMON_PREFIX_%02u",i);
        tag(0,i,name,2,3);tag(1,63-i,name,2,3);s.types[i]=2;s.classes[i]=3;s.committed[i]=0x80000000u+i;
    }
    request(1,2);assert(tinyplc_update_prepare(&u,&s,1));
    for(unsigned i=0;i<64;++i)assert(s.committed[i]==0x80000000u+63-i);
    /* Enumerate short serialized ownership schedules across trial and recovery. */
    for(unsigned i=0;i<4000;++i) {
        setup();request(1,2);
        assert(tinyplc_update_reserve(&u,1,2)==3);assert(tinyplc_update_reserve(&u,2,0)==3);begin(false);
        assert(tinyplc_update_prepare(&u,&s,1));begin(false);finish((i&1)?5:0,1);
        if(i&1){begin(false);assert(tinyplc_update_prepare(&u,&s,2));finish((i&2)?259:0,2);}
        assert(!tinyplc_update_busy(&u));begin(true);
    }
    printf("migration/trial/rollback/retirement and 4000 interleavings passed; update=%zu bytes\n",sizeof u);
}
