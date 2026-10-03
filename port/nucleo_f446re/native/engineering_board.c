/* Original register driver; ST RM0390 USART/RCC/GPIO and UM1724 VCP wiring.
 * docs/engineering-transport.md records sources, ownership and test limits. */
#define MPU_WRAPPERS_INCLUDED_FROM_API_FILE
#include "FreeRTOS.h"
#include "task.h"
#include "engineering_board.h"
#include <string.h>
#define R(a) (*(volatile uint32_t *)(a))
static tinyplc_loader loader;
static tinyplc_snapshots snapshots;
static tinyplc_update update;
extern uint32_t tinyplc_scan(const uint32_t *, uint32_t *, uint32_t,
                             tinyplc_native_diagnostic *);
extern const uint8_t tinyplc_tag_names[][32], tinyplc_tag_types[],
    tinyplc_tag_classes[];
static tinyplc_engine engine;
static tinyplc_framer framer;
static StaticTask_t comms_tcb;
__attribute__((aligned(4096))) static StackType_t comms_stack[1024];
static TaskHandle_t comms_handle;
static uint8_t rx[1024], response[256], tx[TPLC_FRAME_BYTES_MAX],
    status_image[TPLC_GET_STATUS_RESPONSE_BYTES];
static uint32_t rx_time[1024]; /* Arrival time, not delayed comms-drain time. */
static volatile uint32_t head, tail, overflow;
volatile uint32_t uart_rx_errors, uart_frames, comms_stack_free_words;

static MemoryRegion_t comms_regions[3] = {
    {(void *)TPLC_SLOT_A_BASE, 32768,
     portMPU_REGION_READ_ONLY | portMPU_REGION_EXECUTE_NEVER},
    {0, 0, 0},
    {0, 0, 0}};
void plc_uart_handler(void)
{
    uint32_t sr = R(0x40004400);
    if (sr & 0x2f) {
        uint8_t byte =
            (uint8_t)R(0x40004404); /* SR then DR clears RX/error status. */
        uint32_t next = (head + 1) & 1023;
        if ((sr & 15) || next == tail) {
            ++uart_rx_errors;
            overflow = 1;
            return;
        }
        __asm volatile(
            "dmb" ::
                : "memory"); /* Acquire the consumer tail before reusing a cell. */
        rx[head] = byte;
        rx_time[head] = xTaskGetTickCountFromISR();
        __asm volatile("dmb" ::: "memory");
        head = next;
    }
}
static void mapping(void *unused, unsigned slot, bool write)
{
    (void)unused;
    comms_regions[1] = (MemoryRegion_t){
        write ? (void *)(slot ? TPLC_SLOT_B_BASE : TPLC_SLOT_A_BASE) : NULL,
        write ? TPLC_CODE_CAPACITY : 0,
        portMPU_REGION_PRIVILEGED_READ_WRITE | portMPU_REGION_EXECUTE_NEVER};
    vTaskAllocateMPURegions(NULL, comms_regions);
    /* The API updates the TCB; PendSV installs it even when selecting this task again. */
    taskYIELD();
    __asm volatile("dsb\nisb" ::: "memory");
}
static void critical(bool enter)
{
    if (enter) {
        taskENTER_CRITICAL();
    } else {
        taskEXIT_CRITICAL();
    }
}
static void status(void *unused, uint8_t *r)
{
    (void)unused;
    taskENTER_CRITICAL();
    memcpy(r, status_image, sizeof status_image);
    /* Accepted request fields can advance between scan publications. */
    r[TPLC_GET_STATUS_RESPONSE_OUTCOME_OFFSET] = (uint8_t)update.outcome;
    tinyplc_put32(r, TPLC_GET_STATUS_RESPONSE_REQUESTED_GENERATION_OFFSET,
                  update.requested);
    tinyplc_put32(r, TPLC_GET_STATUS_RESPONSE_PENDING_GENERATION_OFFSET,
                  update.pending);
    taskEXIT_CRITICAL();
}
static void frame(void *unused, uint8_t cmd, const uint8_t *p, uint16_t n)
{
    (void)unused;
    ++uart_frames;
    size_t size = tinyplc_engine_request(&engine, cmd, p, n,
                                         xTaskGetTickCount(), response);
    if (!size)
        return;
    size = tinyplc_frame_encode(cmd | TPLC_RESPONSE_BIT, response, size, tx);
    TickType_t start = xTaskGetTickCount();
    for (size_t i = 0; i < size; ++i) {
        while (!(R(0x40004400) & (1u << 7)))
            if ((TickType_t)(xTaskGetTickCount() - start) > 1000)
                return;
        R(0x40004404) = tx[i]; /* Preemptible low-priority TX; no scan lock. */
    }
}
static void comms(void *unused)
{
    (void)unused;
    for (;;) {
        if (overflow) {
            taskENTER_CRITICAL();
            tail = head;
            overflow = 0;
            taskEXIT_CRITICAL();
            framer.used = 0;
        }
        /* One bounded ring drain, then allow scheduler/idle progress. */
        for (unsigned i = 0; i < 1024 && tail != head; ++i) {
            __asm volatile(
                "dmb" ::
                    : "memory"); /* Acquire published bytes after observing head. */
            uint8_t byte = rx[tail];
            uint32_t arrival = rx_time[tail];
            __asm volatile("dmb" ::: "memory");
            tail = (tail + 1) & 1023;
            tinyplc_frame_feed(&framer, byte, arrival, frame, NULL);
        }
        tinyplc_frame_expire(&framer, xTaskGetTickCount());
        tinyplc_loader_expire(&loader, xTaskGetTickCount());
        comms_stack_free_words = uxTaskGetStackHighWaterMark(NULL);
        vTaskDelay(1);
    }
}
void engineering_init(void)
{
    tinyplc_snapshots_init(&snapshots);
    configASSERT(tinyplc_loader_init(&loader, (uint8_t *)TPLC_SLOT_A_BASE,
                                     (uint8_t *)TPLC_SLOT_B_BASE, 0,
                                     TINYPLC_ALLOW_UNSIGNED_LAB != 0));
    /* Register boot metadata before its code/constants can ever be overwritten. */
    tinyplc_slot *boot = &loader.slots[0];
    boot->entry = (uint32_t)tinyplc_scan;
    boot->tag_count = 3;
    for (unsigned i = 0; i < 3; ++i) {
        uint8_t *tag = boot->tags + i * TPLC_TAG_BYTES;
        memcpy(tag, tinyplc_tag_names[i], 32);
        tag[32] = tinyplc_tag_types[i];
        tag[33] = tinyplc_tag_classes[i];
        tag[34] = i == 0   ? TPLC_BINDING_BTN_PC13
                  : i == 1 ? TPLC_BINDING_LED_PA5
                           : TPLC_BINDING_NONE;
    }
    boot->schema_crc = tplc_crc32(boot->tags, 3 * TPLC_TAG_BYTES, 0, 0);
    tinyplc_update_init(&update, &loader, 0);
    engine = (tinyplc_engine){.loader = &loader,
                              .status = status,
                              .mapping = mapping,
                              .snapshots = &snapshots,
                              .update = &update,
                              .critical = critical};
    R(0x40023830) |= 1;
    R(0x40023840) |= 1u << 17;
    (void)R(0x40023840);
    R(0x40020000) = (R(0x40020000) & ~(15u << 4)) |
                    (10u << 4); /* PA2/3 alternate function. */
    R(0x40020020) =
        (R(0x40020020) & ~(255u << 8)) | (0x77u << 8); /* AF7 USART2. */
    R(0x4002000c) =
        (R(0x4002000c) & ~(3u << 6)) | (1u << 6); /* RX idle pull-up. */
    R(0x4000440c) = 0;
    R(0x40004408) = 139; /* HSI/APB1 16 MHz / 115200, OVER8=0. */
    R(0x40004410) = 0;
    R(0x40004414) = 0;
    R(0x4000440c) = (1u << 13) | (1u << 5) | (1u << 3) | (1u << 2);
    *(volatile uint8_t *)0xE000E426 = 6u << 4;
    R(0xE000E104) = 1u << 6; /* IRQ38. */
    TaskParameters_t task = {
        .pvTaskCode = comms,
        .pcName = "comms",
        .usStackDepth = 1024,
        .pvParameters = NULL,
        .uxPriority = 1 | portPRIVILEGE_BIT,
        .puxStackBuffer = comms_stack,
        .pxTaskBuffer = &comms_tcb,
        .xRegions = {comms_regions[0], comms_regions[1], comms_regions[2]}};
    configASSERT(xTaskCreateRestrictedStatic(&task, &comms_handle) == pdPASS);
}
const tinyplc_slot *engineering_prepare(tinyplc_scan_state *state,
                                        uint64_t scan)
{
    if (!tinyplc_update_prepare(&update, state, scan))
        return NULL;
    return &loader.slots[update.active];
}
void engineering_discard(tinyplc_scan_state *state)
{
    tinyplc_update_discard(&update, state);
}
void engineering_finish(tinyplc_scan_state *state,
                        const tinyplc_native_diagnostic *diagnostic,
                        uint64_t scan)
{
    tinyplc_update_finish(&update, state, diagnostic, scan);
}
void engineering_publish(uint64_t scan, uint32_t fault, uint32_t elapsed,
                         uint32_t maximum, int32_t jitter, uint64_t misses)
{
    uint32_t generation = loader.slots[update.active].generation;
    status_image[0] = 0;
    tinyplc_put32(status_image,
                  TPLC_GET_STATUS_RESPONSE_ACTIVE_GENERATION_OFFSET,
                  generation);
    tinyplc_put64(status_image, TPLC_GET_STATUS_RESPONSE_SCAN_OFFSET, scan);
    status_image[TPLC_GET_STATUS_RESPONSE_EXECUTION_OFFSET] =
        fault ? TPLC_EXEC_FAULT : TPLC_EXEC_RUNNING;
    status_image[TPLC_GET_STATUS_RESPONSE_OUTCOME_OFFSET] =
        (uint8_t)update.outcome;
    tinyplc_put32(status_image, TPLC_GET_STATUS_RESPONSE_FAULT_OFFSET, fault);
    tinyplc_put32(status_image, TPLC_GET_STATUS_RESPONSE_LAST_SCAN_US_OFFSET,
                  elapsed / 16 + (elapsed % 16 != 0));
    tinyplc_put32(status_image, TPLC_GET_STATUS_RESPONSE_MAX_SCAN_US_OFFSET,
                  maximum / 16 + (maximum % 16 != 0));
    int32_t us = (int32_t)(jitter >= 0 ? ((int64_t)jitter + 15) / 16
                                       : -((-(int64_t)jitter + 15) / 16));
    tinyplc_put32(status_image,
                  TPLC_GET_STATUS_RESPONSE_RELEASE_JITTER_US_OFFSET,
                  (uint32_t)us);
    tinyplc_put64(status_image, TPLC_GET_STATUS_RESPONSE_MISSED_RELEASES_OFFSET,
                  misses);
}

void engineering_snapshot(uint64_t scan, unsigned count, const uint32_t *cells,
                          const uint32_t *inputs)
{
    const tinyplc_slot *s = &loader.slots[update.active];
    const uint8_t *tags = s->tags;
    static uint32_t
        observed[TPLC_TAG_LIMIT]; /* Scan-owner scratch, never borrowed. */
    for (unsigned i = 0; i < count; ++i)
        observed[i] =
            tags[i * TPLC_TAG_BYTES + TPLC_TAG_CLASS_OFFSET] == TPLC_CLASS_INPUT
                ? inputs[i]
                : cells[i];
    tinyplc_snapshot_publish(&snapshots, s->generation, scan, count, tags,
                             observed);
}
