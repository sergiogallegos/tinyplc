#ifndef TINYPLC_ENGINEERING_BOARD_H
#define TINYPLC_ENGINEERING_BOARD_H
#include "tinyplc/engineering.h"
void engineering_init(void);
const tinyplc_slot *engineering_candidate(void);
void engineering_accept(void);
void engineering_publish(uint64_t scan,uint32_t fault,uint32_t last_cycles,uint32_t max_cycles,int32_t jitter_cycles,uint64_t misses);
void plc_uart_handler(void);
#endif
