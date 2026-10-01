/* Project-owned R2.6 execution boundary. See docs/native-isolation.md. */
#ifndef TINYPLC_GUARD_H
#define TINYPLC_GUARD_H
#include "FreeRTOS.h"
#include "task.h"
#include "tinyplc/native_abi.h"
#define GUARD_MEMORY_FAULT 259u
#define GUARD_BAD_GATEWAY 260u
#define GUARD_RESET_FAULT 261u
void guard_init(TaskHandle_t owner, TaskHandle_t worker);
void guard_heartbeat(void);
void guard_set_worker(TaskHandle_t worker);
uint32_t guard_invoke(const uint32_t *, uint32_t *, uint32_t, tinyplc_native_diagnostic *);
extern uint32_t guard_scan_start;
extern volatile uint32_t guard_boot_fault, guard_entries, guard_returns;
void plc_worker(void *unused);
void plc_svc_handler(void);
void plc_fault_handler(void);
void plc_timer_handler(void);
#endif
