/* M2 test adapter, not a transport or PLC scan interface. */
#include "tinyplc/core.h"
#include <errno.h>
#include <inttypes.h>
#include <stdio.h>
#include <stdlib.h>

static plc_program program;
static plc_workspace workspace;
static const plc_binding bindings[] = {
    {"BTN", PLC_BOOL, PLC_INPUT}, {"LED", PLC_BOOL, PLC_OUTPUT}
};

static bool number(const char *text, uint32_t *out)
{
    char *end;
    errno = 0;
    if (!text[0] || text[0] == '-') return false;
    unsigned long value = strtoul(text, &end, 10);
    if (errno || *end || value > UINT32_MAX) return false;
    *out = (uint32_t)value;
    return true;
}

int main(int argc, char **argv)
{
    if (argc < 3) { fprintf(stderr, "usage: vm-runner image budget [u32 cells...]\n"); return 2; }
    uint32_t budget;
    if (!number(argv[2], &budget)) return 2;
    FILE *file = fopen(argv[1], "rb");
    if (!file) { perror(argv[1]); return 2; }
    uint8_t bytes[PLC_MAX_IMAGE_BYTES + 1];
    size_t length = fread(bytes, 1, sizeof bytes, file);
    bool failed = ferror(file) != 0;
    if (fclose(file) || failed) return 2;
    plc_profile profile = {bindings, sizeof bindings / sizeof bindings[0]};
    plc_diagnostic diagnostic;
    plc_fault fault = plc_validate(&program, bytes, length, &profile, &workspace, &diagnostic);
    bool accepted = fault == PLC_FAULT_NONE;
    plc_values values = {{0}};
    if (accepted) {
        if (argc != 3 && argc != 3 + program.tag_count) return 2;
        for (int j = 3; j < argc; ++j)
            if (!number(argv[j], &values.cell[j - 3])) return 2;
        fault = plc_vm_run(&program, &values, budget, &diagnostic);
    }
    printf("{\"accepted\":%s,\"fault\":%u,\"pc\":%u,\"opcode\":%u,\"values\":[",
           accepted ? "true" : "false", (unsigned)fault,
           (unsigned)diagnostic.pc, (unsigned)diagnostic.opcode);
    if (accepted) for (unsigned j = 0; j < program.tag_count; ++j)
        printf("%s%" PRIu32, j ? "," : "", values.cell[j]);
    puts("]}");
    return 0;
}
