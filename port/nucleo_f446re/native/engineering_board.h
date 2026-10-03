#ifndef TINYPLC_ENGINEERING_BOARD_H
#define TINYPLC_ENGINEERING_BOARD_H
#include "tinyplc/engineering.h"
void engineering_init(void);
void engineering_snapshot(uint64_t,unsigned,const uint32_t *,const uint32_t *);
const tinyplc_slot *engineering_prepare(tinyplc_scan_state *,uint64_t);
void engineering_discard(tinyplc_scan_state *);
void engineering_finish(tinyplc_scan_state *,const tinyplc_native_diagnostic *,uint64_t);
void engineering_publish(uint64_t scan,uint32_t fault,uint32_t last_cycles,uint32_t max_cycles,int32_t jitter_cycles,uint64_t misses);
void plc_uart_handler(void);
#endif
