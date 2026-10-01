/* M0 board bring-up only. STM32F446 reset uses the internal 16 MHz HSI.
 * Register offsets: ST RM0390, RCC/GPIO/SysTick. No HAL or library required. */
#include <stdint.h>
#define REG32(address) (*(volatile uint32_t *)(uintptr_t)(address))
#define RCC_AHB1ENR REG32(0x40023830u)
#define GPIOA_MODER REG32(0x40020000u)
#define GPIOA_BSRR REG32(0x40020018u)
#define SYST_CSR REG32(0xE000E010u)
#define SYST_RVR REG32(0xE000E014u)
#define SYST_CVR REG32(0xE000E018u)

static void delay_ms(unsigned milliseconds)
{
    for (unsigned i = 0; i < milliseconds; ++i) {
        while ((SYST_CSR & (1u << 16)) == 0u) { }
    }
}

int main(void)
{
    RCC_AHB1ENR |= 1u;
    (void)RCC_AHB1ENR; /* Allow the peripheral clock enable to take effect. */
    GPIOA_BSRR = 1u << 21; /* PA5 LOW before enabling output. */
    GPIOA_MODER = (GPIOA_MODER & ~(3u << 10)) | (1u << 10);
    SYST_RVR = 16000u - 1u;
    SYST_CVR = 0u;
    SYST_CSR = 5u; /* CPU clock, counter enabled, interrupt disabled. */
    for (;;) {
        GPIOA_BSRR = 1u << 5;
        delay_ms(500);
        GPIOA_BSRR = 1u << 21;
        delay_ms(500);
    }
}
