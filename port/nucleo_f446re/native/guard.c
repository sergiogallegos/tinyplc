/* Original STM32 execution supervisor; official sources and design in
 * docs/native-isolation.md. All mutable state below is privileged memory. */
#define MPU_WRAPPERS_INCLUDED_FROM_API_FILE
#include "guard.h"
#include "exception_frame.h"
#include "tinyplc/scan.h"
#define R(a) (*(volatile uint32_t *)(a))
#define TIM_CR1 R(0x40000000)
#define TIM_DIER R(0x4000000c)
#define TIM_SR R(0x40000010)
#define TIM_EGR R(0x40000014)
#define TIM_CNT R(0x40000024)
#define TIM_PSC R(0x40000028)
#define TIM_ARR R(0x4000002c)
#define TIM_IRQ (1u << 28)
#define RETAIN_MAGIC 0x504c4336u
extern char plc_return_svc[], plc_abort_loop[];
static TaskHandle_t owner_task, worker_task;
static volatile uint32_t active, ready, result;
uint32_t guard_scan_start;
volatile uint32_t guard_boot_fault, guard_entries, guard_returns, guard_control;
volatile uint32_t guard_fault_cfsr, guard_fault_address, guard_fault_pc;
volatile uint32_t guard_fault_sp, guard_fault_exc, guard_fault_control;
volatile uint32_t guard_fault_cycles, guard_safe_cycles, guard_deadlines,
    guard_reset_flags, guard_last_elapsed;
/* Only interpreted after an IWDG reset, with a magic/complement pair. This is
 * diagnostic SRAM, not durable program state and not trusted across power loss. */
__attribute__((section(".retained"), used)) static volatile struct {
    uint32_t magic, inverse, cfsr, pc, sp, exc, control, fault_cycles,
        safe_cycles;
} retained;
static uint32_t cycles(void) { return R(0xE0001004); }
static void safe_output(void)
{
    R(0x40020018) = 1u << 21;
    __asm volatile("dsb" ::: "memory");
    guard_safe_cycles = cycles();
}
static int valid_frame(uint32_t *frame, uint32_t exc, uint32_t control)
{
    if (!plc_frame_address_valid((uintptr_t)frame, exc, control))
        return 0;
    return plc_frame_xpsr_valid(frame[7]);
}
static void park(uint32_t *frame)
{
    frame[6] = (uint32_t)plc_abort_loop & ~1u;
    frame[7] = 0x01000000; /* Thread mode, Thumb, clear IT/alignment state. */
}
static void reset_fallback(void) __attribute__((noreturn));
static void reset_fallback(void)
{
    safe_output();
    /* A stacking fault can be pending while the higher-priority SVC checker
     * catches the bad PSP first. Read hardware status here too, not only in
     * the CPU fault-handler path. Never dereference that frame. */
    guard_fault_cfsr = R(0xE000ED28);
    retained.cfsr = guard_fault_cfsr;
    retained.pc = guard_fault_pc;
    retained.sp = guard_fault_sp;
    retained.exc = guard_fault_exc;
    retained.control = guard_fault_control;
    retained.fault_cycles = guard_fault_cycles;
    retained.safe_cycles = guard_safe_cycles;
    retained.inverse = ~RETAIN_MAGIC;
    retained.magic = RETAIN_MAGIC;
    __asm volatile("dsb\ncpsid i" ::: "memory");
    /* Do not attempt exception return or RTOS context save with an invalid PSP.
     * IWDG is independent of CPU scheduling and is already running. */
    for (;;) {
    }
}
void guard_svc(uint32_t *frame, uint32_t exc, uint32_t control)
{
    guard_control = control;
    if (!active || !valid_frame(frame, exc, control)) {
        guard_fault_cycles = cycles();
        guard_fault_sp = (uint32_t)frame;
        guard_fault_exc = exc;
        guard_fault_control = control;
        reset_fallback();
    }
    if (frame[6] != (uint32_t)plc_return_svc + 2) {
        guard_fault_cycles = cycles();
        safe_output();
        result = GUARD_BAD_GATEWAY;
        guard_fault_pc = frame[6];
        park(frame);
    } else {
        result = frame[0];
        ++guard_returns;
    }
    if (cycles() - guard_scan_start >= 160000 || (TIM_SR & 1)) {
        result = TINYPLC_SCAN_OVERRUN;
        ++guard_deadlines;
        guard_fault_cycles = cycles();
        safe_output();
        park(frame);
    }
    TIM_CR1 = 0;
    TIM_DIER = 0;
    TIM_SR = 0;
    ready = 1;
    /* SVCall runs above the RTOS API ceiling. Defer notification to TIM2 IRQ. */
    R(0xE000E200) = TIM_IRQ;
    __asm volatile("dsb\nisb" ::: "memory");
}
void guard_fault(uint32_t *frame, uint32_t exc, uint32_t control)
{
    guard_fault_cycles = cycles();
    safe_output();
    guard_fault_cfsr = R(0xE000ED28);
    guard_fault_address =
        (guard_fault_cfsr & 0x80)
            ? R(0xE000ED34)
            : ((guard_fault_cfsr & 0x8000) ? R(0xE000ED38) : 0);
    guard_fault_sp = (uint32_t)frame;
    guard_fault_exc = exc;
    guard_fault_control = control;
    /* Stacking/unstacking/lazy-FP faults or a fault outside the user job require
     * reset. Never read a suspect exception frame in that case. */
    if (!active || (guard_fault_cfsr & 0x3838) ||
        !valid_frame(frame, exc, control))
        reset_fallback();
    guard_fault_pc = frame[6];
    result = GUARD_MEMORY_FAULT;
    park(frame);
    R(0xE000ED28) = guard_fault_cfsr;
    R(0xE000ED2c) = R(0xE000ED2c);
    TIM_CR1 = 0;
    TIM_DIER = 0;
    TIM_SR = 0;
    ready = 1;
    R(0xE000E200) = TIM_IRQ;
    __asm volatile("dsb\nisb" ::: "memory");
}
void guard_timer(uint32_t *frame, uint32_t exc, uint32_t control)
{
    TIM_CR1 = 0;
    TIM_DIER = 0;
    TIM_SR = 0;
    if (!active)
        return;
    if (!ready) {
        guard_fault_cycles = cycles();
        guard_last_elapsed = guard_fault_cycles - guard_scan_start;
        safe_output();
        ++guard_deadlines;
        result = TINYPLC_SCAN_OVERRUN;
        /* A timeout may occur before the supervisor has blocked. Only rewrite
         * a frame when the interrupted thread is the unprivileged worker. */
        if (control & 1) {
            if (!valid_frame(frame, exc, control)) {
                guard_fault_sp = (uint32_t)frame;
                guard_fault_exc = exc;
                guard_fault_control = control;
                reset_fallback();
            }
            park(frame);
        }
        ready = 1;
    }
    BaseType_t wake = pdFALSE;
    vTaskNotifyGiveFromISR(owner_task, &wake);
    portYIELD_FROM_ISR(wake);
}
void guard_init(TaskHandle_t owner, TaskHandle_t worker)
{
    owner_task = owner;
    worker_task = worker;
    /* The port enabled CP10/11 at scheduler start. Deny FP to user code; retain
     * privileged access for the port. Then enable configurable fault handlers. */
    R(0xE000ED88) = (R(0xE000ED88) & ~(15u << 20)) | (5u << 20);
    R(0xE000ED24) |= 7u << 16;
    __asm volatile("dsb\nisb" ::: "memory");
    R(0x40023840) |= 1;
    (void)R(0x40023840); /* TIM2 APB1 clock. */
    TIM_CR1 = 0;
    TIM_DIER = 0;
    TIM_PSC = 0;
    TIM_SR = 0;
    *(volatile uint8_t *)0xE000E41c = configMAX_SYSCALL_INTERRUPT_PRIORITY;
    R(0xE000E280) = TIM_IRQ;
    R(0xE000E100) = TIM_IRQ;
    guard_reset_flags = R(0x40023874);
    if ((guard_reset_flags & (1u << 29)) && retained.magic == RETAIN_MAGIC &&
        retained.inverse == ~RETAIN_MAGIC) {
        guard_boot_fault = GUARD_RESET_FAULT;
        guard_fault_cfsr = retained.cfsr;
        guard_fault_pc = retained.pc;
        guard_fault_sp = retained.sp;
        guard_fault_exc = retained.exc;
        guard_fault_control = retained.control;
        guard_fault_cycles = retained.fault_cycles;
        guard_safe_cycles = retained.safe_cycles;
    } else if (guard_reset_flags & (1u << 29))
        guard_boot_fault = GUARD_RESET_FAULT;
    retained.magic = 0;
    R(0x40023874) |= 1u << 24;
    /* Approximately 0.5 s at nominal 32 kHz LSI: /64, reload 249. Actual LSI
     * tolerance applies. Healthy fault-latched supervision still feeds IWDG. */
    R(0x40003000) = 0xcccc;
    R(0x40003000) = 0x5555;
    R(0x40003004) = 4;
    R(0x40003008) = 249;
    while (R(0x4000300c)) {
    }
    R(0x40003000) = 0xaaaa;
}
void guard_set_worker(TaskHandle_t worker)
{
    configASSERT(!active);
    worker_task = worker;
}
void guard_heartbeat(void) { R(0x40003000) = 0xaaaa; }
uint32_t guard_invoke(const uint32_t *inputs, uint32_t *working, uint32_t count,
                      tinyplc_native_diagnostic *diagnostic)
{
    configASSERT((uintptr_t)inputs == 0x20018000 &&
                 (uintptr_t)working == 0x20018200 && count >= 1 &&
                 count <= 64 && count == inputs[65] &&
                 (uintptr_t)diagnostic == 0x20018300);
    uint32_t elapsed = cycles() - guard_scan_start;
    if (elapsed >= 160000)
        return TINYPLC_SCAN_OVERRUN;
    (void)ulTaskNotifyTake(pdTRUE, 0);
    ready = 0;
    result = GUARD_RESET_FAULT;
    active = 1;
    ++guard_entries;
    TIM_CR1 = 0;
    TIM_ARR = 160000 - elapsed - 1;
    TIM_CNT = 0;
    TIM_EGR = 1;
    while (!(TIM_SR & 1)) {
    } /* Wait for the APB update event before clearing UIF. */
    TIM_SR = 0;
    (void)TIM_SR;
    R(0xE000E280) = TIM_IRQ;
    TIM_DIER = 1;
    TIM_CR1 = 9; /* One-pulse, counter enabled. */
    vTaskResume(worker_task);
    (void)ulTaskNotifyTake(pdTRUE, portMAX_DELAY);
    vTaskSuspend(worker_task);
    active = 0;
    TIM_CR1 = 0;
    TIM_DIER = 0;
    TIM_SR = 0;
    return result;
}
