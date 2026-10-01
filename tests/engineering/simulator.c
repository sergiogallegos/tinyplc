#define _POSIX_C_SOURCE 200809L
#include "tinyplc/engineering.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
static tinyplc_loader l;static tinyplc_framer f;static tinyplc_engine e;
static uint8_t a[TPLC_CODE_CAPACITY],b[TPLC_CODE_CAPACITY],response[256],out[262];
static uint32_t active=1,requested;static uint64_t scans;
static int dropped;
static uint32_t now(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC,&t);return (uint32_t)((uint64_t)t.tv_sec*1000+t.tv_nsec/1000000);}
static uint32_t activate(void *unused,uint32_t gen) {
    (void)unused;
    if(l.transfer_id)return TPLC_STATUS_BUSY;
    for(unsigned i=0;i<2;++i)if(l.slots[i].state==TPLC_SLOT_READY && l.slots[i].generation==gen){
        l.slots[1-i].state=TPLC_SLOT_PREVIOUS;l.slots[i].state=TPLC_SLOT_ACTIVE;active=gen;requested=gen;return 0;
    }
    return TPLC_STATUS_BAD_REQUEST;
}
static void status(void *unused,uint8_t *r){(void)unused;memset(r,0,49);tinyplc_put32(r,1,active);tinyplc_put64(r,5,++scans);r[13]=1;r[14]=requested?2:0;tinyplc_put32(r,17,requested);}
static void frame(void *unused,uint8_t cmd,const uint8_t *p,uint16_t n) {
    (void)unused;size_t len=tinyplc_engine_request(&e,cmd,p,n,now(),response);
    if(!len)return;
    if(cmd==3 && getenv("DROP_CHUNK_ACK") && !dropped){dropped=1;return;}
    len=tinyplc_frame_encode(cmd|128,response,len,out);
    for(size_t i=0;i<len;++i)if(write(1,out+i,1)!=1)exit(2);
}
int main(void) {
    if(!tinyplc_loader_init(&l,a,b,0,true))return 2;
    e=(tinyplc_engine){&l,NULL,activate,status,NULL};
    uint8_t byte;while(read(0,&byte,1)==1)tinyplc_frame_feed(&f,byte,now(),frame,NULL);return 0;
}
