#include <stdint.h>
extern uint32_t _estack, _sidata, _sdata, _edata, _sbss, _ebss;
extern int main(void);
void Reset_Handler(void);
static void Default_Handler(void) { for (;;) { } }

/* Only core exception vectors are needed: blink enables no interrupts. */
__attribute__((section(".isr_vector"), used))
void (*const vectors[16])(void) = {
    (void (*)(void))(&_estack), Reset_Handler,
    Default_Handler, Default_Handler, Default_Handler, Default_Handler,
    Default_Handler, 0, 0, 0, 0, Default_Handler, Default_Handler,
    0, Default_Handler, Default_Handler
};

void Reset_Handler(void)
{
    uint32_t *source = &_sidata;
    for (uint32_t *dest = &_sdata; dest < &_edata; ++dest) *dest = *source++;
    for (uint32_t *dest = &_sbss; dest < &_ebss; ++dest) *dest = 0;
    (void)main();
    Default_Handler();
}
