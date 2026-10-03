#include "tinyplc/engineering.h"
#include <assert.h>
#include <stdio.h>
#include <string.h>
static tinyplc_loader l;
static uint8_t a[TPLC_CODE_CAPACITY],b[TPLC_CODE_CAPACITY];
static unsigned frames;
static void got(void *unused,uint8_t cmd,const uint8_t *p,uint16_t n) {(void)unused;assert(cmd==1 && n==0);(void)p;++frames;}
static void feed(tinyplc_framer *f,const uint8_t *b,size_t n,uint32_t now){for(size_t i=0;i<n;++i)tinyplc_frame_feed(f,b[i],now,got,NULL);}
int main(void) {
    tinyplc_framer f={0};uint8_t good[262],outer[262],r[256],p[8]={0};
    size_t n=tinyplc_frame_encode(1,NULL,0,good);assert(n==6);
    for(size_t split=0;split<=n;++split){unsigned before=frames;feed(&f,good,split,0);feed(&f,good+split,n-split,1);assert(frames==before+1);}
    uint8_t noise[]={0,1,2,0xa5,0,0,0xa5,255,255};feed(&f,noise,sizeof noise,2);feed(&f,good,n,2);assert(!f.used);
    size_t out=tinyplc_frame_encode(2,good,n,outer);outer[out-1]^=1;
    unsigned before=frames;feed(&f,outer,out,3);assert(frames==before+1);
    f.used=0;feed(&f,good,3,UINT32_MAX-20);tinyplc_frame_expire(&f,79);assert(f.used==0);
    feed(&f,good,n,80);assert(frames==before+2);
    uint32_t seed=5;for(unsigned i=0;i<10000;++i){seed=seed*1664525+1013904223;tinyplc_frame_feed(&f,(uint8_t)(seed>>24),81+i,got,NULL);assert(f.used<=262);}
    assert(tinyplc_loader_init(&l,a,b,0,true));tinyplc_engine e={.loader=&l};
    size_t size=tinyplc_engine_request(&e,TPLC_CMD_INFO,NULL,0,0,r);assert(size==TPLC_INFO_RESPONSE_BYTES && r[0]==0);
    assert(tinyplc_engine_request(&e,TPLC_CMD_INFO,p,1,0,r)==1 && r[0]==TPLC_STATUS_BAD_REQUEST);
    assert(tinyplc_engine_request(&e,0x81,NULL,0,0,r)==0);
    assert(tinyplc_engine_request(&e,TPLC_CMD_READ_TAGS,NULL,0,0,r)==1 && r[0]==TPLC_STATUS_UNSUPPORTED);
    tinyplc_put32(p,0,204);assert(tinyplc_engine_request(&e,2,p,4,0,r)==17 && r[0]==0);
    uint32_t id;assert(tplc_read_u32(r,17,1,&id));tinyplc_put32(p,0,id);
    assert(tinyplc_engine_request(&e,4,p,4,1,r)==1 && r[0]==TPLC_STATUS_BAD_REQUEST);
    assert(tinyplc_engine_request(&e,3,p,8,1,r)==1 && r[0]==TPLC_STATUS_BAD_REQUEST);
    tinyplc_put32(p,0,204);
    assert(tinyplc_engine_request(&e,2,p,4,1,r)==1 && r[0]==TPLC_STATUS_BUSY);
    puts("engineering framing/replay/expiry and command validation passed");return 0;
}
