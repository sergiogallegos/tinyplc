/* R2.3 build scaffold; see docs/memory-layout.md. Not a timing-qualified port. */
#ifndef FREERTOS_CONFIG_H
#define FREERTOS_CONFIG_H
#include <stdint.h>
void tinyplc_assert_failed(void);
#define configASSERT(x) do { if (!(x)) tinyplc_assert_failed(); } while (0)
#define configCPU_CLOCK_HZ 16000000UL
#define configTICK_RATE_HZ 1000
#define configUSE_PREEMPTION 1
#define configUSE_TIME_SLICING 0
#define configMAX_PRIORITIES 4
#define configMINIMAL_STACK_SIZE 256
#define configMAX_TASK_NAME_LEN 16
#define configTICK_TYPE_WIDTH_IN_BITS TICK_TYPE_WIDTH_32_BITS
#define configIDLE_SHOULD_YIELD 0
#define configUSE_IDLE_HOOK 0
#define configUSE_TICK_HOOK 0
#define configUSE_TIMERS 0
#define configUSE_EVENT_GROUPS 0
#define configUSE_STREAM_BUFFERS 0
#define configUSE_MUTEXES 0
#define configUSE_RECURSIVE_MUTEXES 0
#define configUSE_COUNTING_SEMAPHORES 0
#define configUSE_TASK_NOTIFICATIONS 1
#define configUSE_TRACE_FACILITY 0
#define configSUPPORT_STATIC_ALLOCATION 1
#define configSUPPORT_DYNAMIC_ALLOCATION 0
#define configCHECK_FOR_STACK_OVERFLOW 2
#define configUSE_MPU_WRAPPERS_V1 0
#define configENFORCE_SYSTEM_CALLS_FROM_KERNEL_ONLY 1
#define configENABLE_ACCESS_CONTROL_LIST 1
#define configALLOW_UNPRIVILEGED_CRITICAL_SECTIONS 0
#define configTOTAL_MPU_REGIONS 8
#define configSYSTEM_CALL_STACK_SIZE 256
#define configPROTECTED_KERNEL_OBJECT_POOL_SIZE 8
#define configKERNEL_INTERRUPT_PRIORITY (15U << 4)
#define configMAX_SYSCALL_INTERRUPT_PRIORITY (5U << 4)
#define configCHECK_HANDLER_INSTALLATION 1
#define INCLUDE_vTaskDelay 1
#define INCLUDE_xTaskDelayUntil 1
#define INCLUDE_uxTaskGetStackHighWaterMark 1
#define INCLUDE_vTaskSuspend 0
#define INCLUDE_vTaskDelete 0
#endif
