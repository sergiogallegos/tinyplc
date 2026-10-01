#include <assert.h>
#include <stddef.h>
#include <string.h>
void *plc_memset(void *,int,size_t);
void *plc_memcpy(void *,const void *,size_t);
void *plc_memmove(void *,const void *,size_t);
int plc_memcmp(const void *,const void *,size_t);
int main(void) {
    unsigned char a[16],b[16];
    for(size_t n=0;n<=16;++n) {
        for(size_t src=0;src+n<=16;++src) for(size_t dst=0;dst+n<=16;++dst) {
            for(size_t i=0;i<16;++i)a[i]=b[i]=(unsigned char)i;
            memmove(a+dst,a+src,n);assert(plc_memmove(b+dst,b+src,n)==b+dst);
            assert(memcmp(a,b,16)==0);
        }
    }
    assert(plc_memset(a,0xab,16)==a);memset(b,0xab,16);assert(plc_memcmp(a,b,16)==0);
    b[8]=0xac;assert(plc_memcmp(a,b,16)<0 && plc_memcmp(b,a,16)>0);
    assert(plc_memcpy(a,b,16)==a && memcmp(a,b,16)==0);
    assert(plc_memcmp(a,b,0)==0);
    return 0;
}
