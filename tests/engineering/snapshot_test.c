#include "tinyplc/engineering.h"
#include <assert.h>
#include <pthread.h>
#include <stdio.h>
#include <string.h>
static tinyplc_snapshots m;
static uint8_t tags[64][TPLC_TAG_BYTES];
static uint32_t cells[64];
static uint32_t get32(const uint8_t *p,size_t at){uint32_t v;assert(tplc_read_u32(p,256,at,&v));return v;}
static uint64_t get64(const uint8_t *p,size_t at){uint64_t v;assert(tplc_read_u64(p,256,at,&v));return v;}
static size_t read_page(uint32_t gen,uint64_t scan,unsigned first,unsigned count,uint32_t now,uint8_t *r) {
    uint8_t p[14];tinyplc_put32(p,0,gen);tinyplc_put64(p,4,scan);p[12]=(uint8_t)first;p[13]=(uint8_t)count;
    return tinyplc_snapshot_read(&m,p,sizeof p,now,r);
}
static void publish(uint32_t gen,uint64_t scan) {
    for(unsigned i=0;i<64;++i){memset(tags[i],0,40);tags[i][0]=(uint8_t)('A'+gen%26);tags[i][32]=2;tags[i][33]=3;cells[i]=(uint32_t)scan+i;}
    tinyplc_snapshot_publish(&m,gen,scan,64,&tags[0][0],cells);
}
static void check(const uint8_t *r,uint32_t gen,uint64_t scan,unsigned first) {
    assert(r[0]==0 && get32(r,1)==gen && get64(r,5)==scan && r[13]==first && r[15]==64);
    for(unsigned i=0;i<r[14];++i){assert(r[16+i*40]=='A'+gen%26);assert(get32(r,16+i*40+36)==(uint32_t)scan+first+i);}
}
static void *producer(void *unused) {
    (void)unused;for(uint32_t i=1;i<=100000;++i)publish(i,i);return NULL;
}
int main(void) {
    uint8_t r[256];tinyplc_snapshots_init(&m);
    assert(read_page(0,0,0,5,0,r)==1 && r[0]==TPLC_STATUS_NO_PROGRAM);
    publish(1,1);
    assert(read_page(0,0,0,0,0,r)==1 && r[0]==TPLC_STATUS_BAD_REQUEST);
    assert(read_page(0,0,1,5,0,r)==1 && r[0]==TPLC_STATUS_BAD_REQUEST);
    assert(read_page(2,0,0,5,0,r)==1 && r[0]==TPLC_STATUS_BUSY);
    assert(read_page(0,0,0,5,UINT32_MAX-10,r)==216);check(r,1,1,0);
    /* Thousands of publications and schema destruction while reader is stalled. */
    for(unsigned i=2;i<10000;++i)publish(i,i);
    memset(tags,0xff,sizeof tags);memset(cells,0xff,sizeof cells);
    assert(read_page(1,1,5,5,20,r)==216);check(r,1,1,5);
    assert(read_page(2,1,5,5,21,r)==1 && r[0]==TPLC_STATUS_BUSY);
    assert(read_page(1,1,64,5,21,r)==1 && r[0]==TPLC_STATUS_BAD_REQUEST);
    assert(read_page(1,1,10,5,2020,r)==1 && r[0]==TPLC_STATUS_BUSY);
    assert(read_page(0,0,0,5,2021,r)==216);check(r,9999,9999,0);
    assert(read_page(9999,9999,60,5,2022,r)==176);check(r,9999,9999,60);
    assert(read_page(9999,9999,5,5,2023,r)==1 && r[0]==TPLC_STATUS_BUSY);
    tinyplc_snapshots_init(&m);publish(1,1);
    pthread_t thread;assert(!pthread_create(&thread,NULL,producer,NULL));
    for(unsigned i=0;i<10000;++i) {
        assert(read_page(0,0,0,5,0,r)==216);
        uint32_t gen=get32(r,1);uint64_t scan=get64(r,5);check(r,gen,scan,0);
        for(unsigned first=5;first<64;first+=5){assert(read_page(gen,scan,first,5,0,r)>1);check(r,gen,scan,first);}
    }
    assert(!pthread_join(thread,NULL));
    puts("snapshot ownership, pagination, expiry and concurrent stress passed");return 0;
}
