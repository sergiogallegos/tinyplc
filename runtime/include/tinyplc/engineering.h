/* Bounded engineering frames and request dispatch. Single task owner. */
#ifndef TINYPLC_ENGINEERING_H
#define TINYPLC_ENGINEERING_H
#include "tinyplc/loader.h"
#include "tinyplc/snapshot.h"
#include "tinyplc/update.h"
typedef struct {uint8_t bytes[TPLC_FRAME_BYTES_MAX];uint16_t used;uint32_t last_ms;} tinyplc_framer;
typedef void (*tinyplc_frame_fn)(void *,uint8_t,const uint8_t *,uint16_t);
void tinyplc_frame_feed(tinyplc_framer *,uint8_t,uint32_t,tinyplc_frame_fn,void *);
void tinyplc_frame_expire(tinyplc_framer *,uint32_t);
size_t tinyplc_frame_encode(uint8_t command,const uint8_t *payload,size_t size,uint8_t *out);
void tinyplc_put16(uint8_t *,size_t,uint16_t);
void tinyplc_put32(uint8_t *,size_t,uint32_t);
void tinyplc_put64(uint8_t *,size_t,uint64_t);
typedef struct {
    tinyplc_loader *loader;
    void *context;
    uint32_t (*activate)(void *,uint32_t);
    void (*status)(void *,uint8_t *); /* Writes success response, 49 bytes. */
    void (*mapping)(void *,unsigned,bool); /* Current comms map: inactive RW/XN during END only. */
    tinyplc_snapshots *snapshots;
    tinyplc_update *update;
    void (*critical)(bool); /* Short reservation/status copies only. */
} tinyplc_engine;
/* Output is response payload (status included), max 256 bytes. No allocation.
 * Caller serializes INFO against scan-boundary slot ownership transitions. */
size_t tinyplc_engine_request(tinyplc_engine *,uint8_t,const uint8_t *,size_t,uint32_t,uint8_t *);
#endif
