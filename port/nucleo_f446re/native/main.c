/* R3.3 isolated native scan with bounded UART staging/activation.
 * Runtime design inspiration and official sources: docs/references.md. */
#define MPU_WRAPPERS_INCLUDED_FROM_API_FILE
#include "FreeRTOS.h"
#include "task.h"
#include "tinyplc/scan.h"
#include "guard.h"
#include "engineering_board.h"
#define REG32(address) (*(volatile uint32_t *)(address))
static StaticTask_t scan_tcb, idle_tcb, worker_tcb;
static TaskHandle_t scan_handle, worker_handle;
__attribute__((aligned(2048))) static StackType_t scan_stack[512];
static StackType_t idle_stack[configMINIMAL_STACK_SIZE];
__attribute__((section(".user_stack"), aligned(2048)))
static StackType_t worker_stack[512];
__attribute__((section(".inputs"), aligned(512), used))
static uint32_t inputs[128];
__attribute__((section(".working"), aligned(512), used))
static struct {
    uint32_t cells[64];
    tinyplc_native_diagnostic diagnostic;
    uint32_t padding[62];
} working;
static tinyplc_scan_state supervisor;
static int input_index=0, output_index=1;
static uint64_t scan_sequence, missed_sequence;
static void create_worker(void) {
    const TaskParameters_t user={.pvTaskCode=plc_worker,.pcName="ST",.usStackDepth=512,
        .pvParameters=NULL,.uxPriority=2,.puxStackBuffer=worker_stack,.pxTaskBuffer=&worker_tcb,
        .xRegions={
            {(void *)(inputs[64]&~(TPLC_CODE_CAPACITY-1)),TPLC_CODE_CAPACITY,portMPU_REGION_READ_ONLY},
            {inputs,sizeof inputs,portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY|portMPU_REGION_EXECUTE_NEVER},
            {&working,sizeof working,portMPU_REGION_READ_WRITE|portMPU_REGION_EXECUTE_NEVER}}};
    configASSERT(xTaskCreateRestrictedStatic(&user,&worker_handle)==pdPASS);
    vTaskSuspend(worker_handle);
}
static void activate_boundary(void) {
    const tinyplc_slot *candidate=engineering_candidate();
    if(!candidate)return;
    /* Worker is suspended following every return/fault. Discard its old stack
     * and register context before publishing a new descriptor or slot mapping. */
    vTaskDelete(worker_handle);
    uint8_t types[64],classes[64];input_index=-1;output_index=-1;
    for(unsigned i=0;i<candidate->tag_count;++i) {
        const uint8_t *tag=candidate->tags+i*TPLC_TAG_BYTES;
        types[i]=tag[TPLC_TAG_TYPE_OFFSET];classes[i]=tag[TPLC_TAG_CLASS_OFFSET];
        if(tag[TPLC_TAG_BINDING_OFFSET]==TPLC_BINDING_BTN_PC13)input_index=(int)i;
        if(tag[TPLC_TAG_BINDING_OFFSET]==TPLC_BINDING_LED_PA5)output_index=(int)i;
    }
    configASSERT(tinyplc_scan_init(&supervisor,candidate->tag_count,types,classes)==0);
    for(unsigned i=0;i<64;++i){inputs[i]=0;working.cells[i]=0;}
    inputs[64]=candidate->entry;inputs[65]=candidate->tag_count;inputs[66]=candidate->generation;inputs[67]=0;
    __asm volatile("dsb\nisb":::"memory");
    create_worker();guard_set_worker(worker_handle);engineering_accept();
}

volatile uint32_t input_raw, input_pressed, input_transitions;
volatile uint32_t scan_cycles_max, period_cycles_min = UINT32_MAX, period_cycles_max;
volatile uint32_t release_jitter_max, missed_releases;
extern uint32_t tinyplc_scan(const uint32_t *, uint32_t *, uint32_t, tinyplc_native_diagnostic *);
extern const uint32_t tinyplc_abi_version, tinyplc_tag_count;
extern const uint8_t tinyplc_tag_types[], tinyplc_tag_classes[];
volatile uint32_t native_status, native_count, native_output;
/* Debugger-visible evidence fields. Values are not observations until board run. */
volatile uint32_t scan_count, stack_free_words, assertion_latched, worker_stack_free_words;
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
    REG32(0x40020018) = output_index>=0 && cells[output_index] ? (1U << 5) : (1U << 21);
    __asm volatile("dsb" ::: "memory");
}
/* Measure against the RTOS scheduled tick, not the phase at task startup.
 * BASEPRI protects the software tick sample; pending SysTick is accounted for
 * while its counter continues. The retry covers a hardware rollover in sampling. */
static int32_t release_jitter(TickType_t scheduled, uint32_t start) {
    uint32_t before,after,value;TickType_t tick;
    taskENTER_CRITICAL();
    do {
        tick=xTaskGetTickCount();before=REG32(0xE000ED04)&(1u<<26);
        value=REG32(0xE000E018);after=REG32(0xE000ED04)&(1u<<26);
    } while(before!=after);
    if(after)++tick;
    uint32_t sampled=cycle_clock();taskEXIT_CRITICAL();
    int64_t cycles=(int64_t)(int32_t)(tick-scheduled)*16000+(15999-(int32_t)value)-(uint32_t)(sampled-start);
    if(cycles>INT32_MAX)return INT32_MAX;
    if(cycles<INT32_MIN)return INT32_MIN;
    return (int32_t)cycles;
}
static void scan(void *unused)
{
    (void)unused;
    guard_init(scan_handle, worker_handle);
    supervisor.fault = guard_boot_fault;
    TickType_t release = xTaskGetTickCount();
    uint32_t previous = 0;
    for (;;) {
        const uint32_t start = cycle_clock();
        int32_t signed_jitter=release_jitter(release,start);
        activate_boundary();
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
        if(input_index>=0) inputs[input_index] = pressed;
        guard_scan_start = start;
        native_status = tinyplc_scan_step(&supervisor, inputs, working.cells,
            &working.diagnostic, guard_invoke, cycle_clock, commit_outputs, start, 160000);
        native_output = output_index>=0 ? supervisor.committed[output_index] : 0;
        native_count = supervisor.count>2 ? supervisor.committed[2] : 0;
        uint32_t elapsed = cycle_clock() - start;
        if (elapsed > scan_cycles_max) scan_cycles_max = elapsed;
        if(scan_count!=UINT32_MAX)++scan_count;
        if(scan_sequence!=UINT64_MAX)++scan_sequence;
        engineering_publish(scan_sequence,supervisor.fault,elapsed,scan_cycles_max,signed_jitter,missed_sequence);
        guard_heartbeat();
        stack_free_words = uxTaskGetStackHighWaterMark(NULL);
        worker_stack_free_words = uxTaskGetStackHighWaterMark(worker_handle);
        if (xTaskDelayUntil(&release, pdMS_TO_TICKS(10)) == pdFALSE) {
            if(missed_releases!=UINT32_MAX)++missed_releases;
            if(missed_sequence!=UINT64_MAX)++missed_sequence;
            supervisor.fault = TINYPLC_SCAN_OVERRUN;
            for(unsigned i=0;i<supervisor.count;++i) if(supervisor.classes[i]==TPLC_CLASS_OUTPUT)supervisor.committed[i]=0;
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
    inputs[64]=(uint32_t)tinyplc_scan;inputs[65]=tinyplc_tag_count;inputs[66]=1;
    engineering_init();
    REG32(0xE000EDFC) |= 1U << 24;
    REG32(0xE0001004) = 0;
    REG32(0xE0001000) |= 1;
    const TaskParameters_t task = {
        .pvTaskCode = scan, .pcName = "scan", .usStackDepth = 512,
        .pvParameters = NULL, .uxPriority = 3 | portPRIVILEGE_BIT,
        .puxStackBuffer = scan_stack, .pxTaskBuffer = &scan_tcb,
        .xRegions = {
            {(void *)0x20010000, 32768, portMPU_REGION_READ_ONLY|portMPU_REGION_EXECUTE_NEVER},
            {inputs, sizeof inputs, portMPU_REGION_PRIVILEGED_READ_WRITE_UNPRIV_READ_ONLY | portMPU_REGION_EXECUTE_NEVER},
            {&working, sizeof working, portMPU_REGION_READ_WRITE | portMPU_REGION_EXECUTE_NEVER}
        }
    };
    configASSERT(xTaskCreateRestrictedStatic(&task, &scan_handle) == pdPASS);
    create_worker();
    vTaskStartScheduler();
    tinyplc_assert_failed();
    return 0;
}
