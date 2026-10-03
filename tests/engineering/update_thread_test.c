#define _POSIX_C_SOURCE 200809L
#include "tinyplc/engineering.h"
#include <assert.h>
#include <pthread.h>
#include <sched.h>
#include <stdio.h>
#include <string.h>
static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
static pthread_cond_t changed = PTHREAD_COND_INITIALIZER;
static tinyplc_loader l;
static tinyplc_update u;
static tinyplc_scan_state state;
static uint8_t code[2][TPLC_CODE_CAPACITY];
static bool stop;
static uint64_t scans;
static void critical(bool enter)
{
    assert(
        !(enter ? pthread_mutex_lock(&mutex) : pthread_mutex_unlock(&mutex)));
}
static void *scan_owner(void *unused)
{
    (void)unused;
    for (;;) {
        critical(true);
        if (stop) {
            critical(false);
            return NULL;
        }
        tinyplc_native_diagnostic d = {0};
        tinyplc_update_finish(&u, &state, &d, scans);
        (void)tinyplc_update_prepare(&u, &state, scans + 1);
        ++state.committed[0];
        ++scans;
        assert(!state.fault);
        pthread_cond_broadcast(&changed);
        critical(false);
        sched_yield();
    }
}
int main(void)
{
    assert(tinyplc_loader_init(&l, code[0], code[1], 0, true));
    uint8_t types[] = {2}, classes[] = {3};
    assert(!tinyplc_scan_init(&state, 1, types, classes));
    for (unsigned slot = 0; slot < 2; ++slot) {
        l.slots[slot].entry = (slot ? TPLC_SLOT_B_BASE : TPLC_SLOT_A_BASE) | 1;
        l.slots[slot].tag_count = 1;
        l.slots[slot].tags[0] = 'N';
        l.slots[slot].tags[32] = 2;
        l.slots[slot].tags[33] = 3;
    }
    tinyplc_update_init(&u, &l, 0);
    tinyplc_engine engine = {.loader = &l, .update = &u, .critical = critical};
    pthread_t worker;
    assert(!pthread_create(&worker, NULL, scan_owner, NULL));
    for (uint32_t gen = 2; gen < 2002; ++gen) {
        critical(true);
        while (tinyplc_update_busy(&u))
            assert(!pthread_cond_wait(&changed, &mutex));
        unsigned target = 1 - u.active;
        /* Stand-in for exclusive END publication; source runs concurrently. */
        l.slots[target].state = TPLC_SLOT_READY;
        l.slots[target].generation = gen;
        uint32_t before = state.committed[0];
        critical(false);
        uint8_t p[4], r[256];
        tinyplc_put32(p, 0, gen);
        assert(tinyplc_engine_request(&engine, TPLC_CMD_ACTIVATE, p, 4, 0, r) ==
                   5 &&
               r[0] == 0);
        assert(tinyplc_engine_request(&engine, TPLC_CMD_GET_UPDATE_STATUS, NULL,
                                      0, 0, r) == 53);
        critical(true);
        while (tinyplc_update_busy(&u))
            assert(!pthread_cond_wait(&changed, &mutex));
        assert(u.outcome == TPLC_OUTCOME_RUNNING &&
               state.committed[0] >= before);
        critical(false);
        assert(tinyplc_engine_request(&engine, TPLC_CMD_ROLLBACK, NULL, 0, 0,
                                      r) == 5 &&
               r[0] == 0);
    }
    critical(true);
    while (tinyplc_update_busy(&u))
        assert(!pthread_cond_wait(&changed, &mutex));
    stop = true;
    critical(false);
    assert(!pthread_join(worker, NULL));
    puts(
        "2000 concurrent activation/rollback pairs and coherent diagnostics passed");
}
