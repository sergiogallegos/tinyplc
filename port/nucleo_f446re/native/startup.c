/* Project-owned startup for the R2.3 experiment. Credits: docs/references.md. */
#include <stdint.h>
extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
extern uint32_t _siuser, _suser, _euser;
extern int main(void);
void Reset_Handler(void);
void tinyplc_assert_failed(void);
void plc_svc_handler(void);
void plc_fault_handler(void);
void plc_timer_handler(void);
void plc_uart_handler(void);
void xPortPendSVHandler(void);
void xPortSysTickHandler(void);
static void Fault_Handler(void) { tinyplc_assert_failed(); }
__attribute__((section(".isr_vector"), used))
void (*const vectors[16 + 96])(void) = {
    [0] = (void (*)(void))(&_estack), [1] = Reset_Handler,
    [2 ... 6] = plc_fault_handler, [7 ... 10] = Fault_Handler, [11] = plc_svc_handler,
    [12 ... 13] = Fault_Handler, [14] = xPortPendSVHandler,
    [15] = xPortSysTickHandler, [16 ... 43] = Fault_Handler,
    [44] = plc_timer_handler, [45 ... 53] = Fault_Handler,
    [54] = plc_uart_handler, [55 ... 111] = Fault_Handler
};
void Reset_Handler(void)
{
    uint32_t *source = &_sidata;
    for (uint32_t *dest = &_sdata; dest < &_edata; ++dest) *dest = *source++;
    for (uint32_t *dest = &_sbss; dest < &_ebss; ++dest) *dest = 0;
    source = &_siuser;
    for (uint32_t *dest = &_suser; dest < &_euser; ++dest) *dest = *source++;
    /* HSI reset clock; CP10/11 enabled for the port's FP context instructions. */
    *(volatile uint32_t *)0xE000ED88 |= 0xFUL << 20;
    *(volatile uint32_t *)0xE000ED08 = (uint32_t)vectors;
    __asm volatile("dsb\nisb" ::: "memory");
    (void)main();
    Fault_Handler();
}
