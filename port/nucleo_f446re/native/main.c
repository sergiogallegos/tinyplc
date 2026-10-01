/* R2.5 physical-I/O experiment: privileged task only, no downloadable loader.
 * Runtime design inspiration and official sources: docs/references.md. */
#define MPU_WRAPPERS_INCLUDED_FROM_API_FILE
#include "FreeRTOS.h"
#include "task.h"
#include "tinyplc/scan.h"
#define REG32(address) (*(volatile uint32_t *)(address))
static StaticTask_t scan_tcb, idle_tcb;
static StackType_t idle_stack[configMINIMAL_STACK_SIZE];
__attribute__((section(".user_stack"), aligned(2048)))
static StackType_t scan_stack[512];
__attribute__((section(".inputs"), aligned(512), used))
static uint32_t inputs[128];
__attribute__((section(".working"), aligned(512), used))
static struct {
    uint32_t cells[64];
    tinyplc_native_diagnostic diagnostic;
    uint32_t padding[62];
} working;
static tinyplc_scan_state supervisor;
volatile uint32_t input_raw, input_pressed, input_transitions;
volatile uint32_t scan_cycles_max, period_cycles_min = UINT32_MAX, period_cycles_max;
volatile uint32_t release_jitter_max, missed_releases;
extern uint32_t tinyplc_scan(const uint32_t *, uint32_t *, uint32_t, tinyplc_native_diagnostic *);
extern const uint32_t tinyplc_abi_version, tinyplc_tag_count;
extern const uint8_t tinyplc_tag_types[], tinyplc_tag_classes[];
volatile uint32_t native_status, native_count, native_output;
/* Debugger-visible evidence fields. Values are not observations until board run. */
volatile uint32_t probe_result, scan_count, stack_free_words, assertion_latched;
__attribute__((section(".ram_probe"), noinline, used))
uint32_t ram_probe(uint32_t value) { return value + 1; }
void tinyplc_assert_failed(void)
{
    __asm volatile("cpsid i" ::: "memory");
    REG32(0x40023830) |= 5;
    (void)REG32(0x40023830);
    REG32(0x40020018) = 1U << (5 + 16);
    assertion_latched = 1;
    for (;;) { }
}
void vApplicationStackOverflowHook(TaskHandle_t task, char *name)
{ (void)task; (void)name; tinyplc_assert_failed(); }
void vApplicationGetIdleTaskMemory(StaticTask_t **tcb, StackType_t **stack,
                                   configSTACK_DEPTH_TYPE *words)
{ *tcb = &idle_tcb; *stack = idle_stack; *words = configMINIMAL_STACK_SIZE; }
static uint32_t cycle_clock(void) { return REG32(0xE0001004); }
static void commit_outputs(const uint32_t *cells)
{
    REG32(0x40020018) = cells[1] ? (1U << 5) : (1U << 21);
    __asm volatile("dsb" ::: "memory");
}
static void scan(void *unused)
{
    (void)unused;
    TickType_t release = xTaskGetTickCount();
    uint32_t previous = 0;
    for (;;) {
        const uint32_t start = cycle_clock();
        if (scan_count) {
            uint32_t period = start - previous;
            if (period < period_cycles_min) period_cycles_min = period;
            if (period > period_cycles_max) period_cycles_max = period;
            uint32_t jitter = period > 160000 ? period - 160000 : 160000 - period;
            if (jitter > release_jitter_max) release_jitter_max = jitter;
        }
        previous = start;
        input_raw = (REG32(0x40020810) >> 13) & 1;
        uint32_t pressed = !input_raw; /* boards/nucleo_f446re.json */
        if (scan_count && input_pressed != pressed) ++input_transitions;
        input_pressed = pressed;
        inputs[0] = pressed;
        native_status = tinyplc_scan_step(&supervisor, inputs, working.cells,
            &working.diagnostic, tinyplc_scan, cycle_clock, commit_outputs, start, 160000);
        native_output = supervisor.committed[1];
        native_count = supervisor.committed[2];
        uint32_t elapsed = cycle_clock() - start;
        if (elapsed > scan_cycles_max) scan_cycles_max = elapsed;
        ++scan_count;
        stack_free_words = uxTaskGetStackHighWaterMark(NULL);
        if (xTaskDelayUntil(&release, pdMS_TO_TICKS(10)) == pdFALSE) {
            ++missed_releases;
            supervisor.fault = TINYPLC_SCAN_OVERRUN;
            supervisor.committed[1] = 0;
            commit_outputs(supervisor.committed);
            /* Skip catch-up bursts after a missed release. */
            vTaskDelay(pdMS_TO_TICKS(10));
            release = xTaskGetTickCount();
        }
    }
}
int main(void)
{
    REG32(0x40023830) |= 5;
    (void)REG32(0x40023830);
    REG32(0x40020018) = 1U << (5 + 16);
    REG32(0x40020000) = (REG32(0x40020000) & ~(3U << 10)) | (1U << 10);
    REG32(0x40020800) &= ~(3U << 26); /* PC13 input, external board pull-up. */
    REG32(0x4002080C) &= ~(3U << 26);
    for (unsigned i = 0; i < 128; ++i) inputs[i] = 0;
    for (unsigned i = 0; i < 64; ++i) working.cells[i] = 0;
    configASSERT(tinyplc_abi_version == 2 && tinyplc_tag_count == 3);
    configASSERT(tinyplc_tag_types[0] == 1 && tinyplc_tag_classes[0] == 1);
    configASSERT(tinyplc_tag_types[1] == 1 && tinyplc_tag_classes[1] == 2);
    configASSERT(tinyplc_tag_types[2] == 2 && tinyplc_tag_classes[2] == 3);
    configASSERT(tinyplc_scan_init(&supervisor, tinyplc_tag_count,
        tinyplc_tag_types, tinyplc_tag_classes) == 0);
    REG32(0xE000EDFC) |= 1U << 24;
    REG32(0xE0001004) = 0;
    REG32(0xE0001000) |= 1;
    probe_result = ram_probe(41);
    configASSERT(probe_result == 42);
    const TaskParameters_t task = {
        .pvTaskCode = scan, .pcName = "scan", .usStackDepth = 512,
        .pvParameters = NULL, .uxPriority = 2 | portPRIVILEGE_BIT,
        .puxStackBuffer = scan_stack, .pxTaskBuffer = &scan_tcb,
        .xRegions = {
            {(void *)0x20010000, 16384, portMPU_REGION_READ_ONLY},
            {inputs, sizeof inputs, portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY | portMPU_REGION_EXECUTE_NEVER},
            {&working, sizeof working, portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER}
        }
    };
    TaskHandle_t handle;
    configASSERT(xTaskCreateRestrictedStatic(&task, &handle) == pdPASS);
    vTaskStartScheduler();
    tinyplc_assert_failed();
    return 0;
}
