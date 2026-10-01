/* Executable C/LLVM call-contract fixture, not the target supervisor.
 * Credits and AAPCS sources: docs/references.md and docs/native-abi.md. */
#include "tinyplc/native_abi.h"
#if defined(__arm__)
_Static_assert(sizeof(void *) == 4, "target pointers must be 32 bits");
_Static_assert(sizeof(tinyplc_native_entry) == 4, "target function pointer size");
#endif
extern uint32_t fixture_scan(const uint32_t *, uint32_t *, uint32_t,
                             tinyplc_native_diagnostic *);
#define CHECK(condition) do { if (!(condition)) return __LINE__; } while (0)

int main(void)
{
    tinyplc_native_entry entry = fixture_scan;
    uint32_t inputs[3] = {2, 0, 0};
    uint32_t committed[3] = {0, 0, 9};
    uint32_t working[3] = {0, 0, 9};
    tinyplc_native_diagnostic diagnostic = {99, 99};
    CHECK(entry(inputs, working, 3, &diagnostic) == TINYPLC_NATIVE_OK);
    CHECK(working[0] == 0 && working[1] == 5 && working[2] == 10);
    CHECK(inputs[0] == 2 && inputs[1] == 0 && inputs[2] == 0);
    CHECK(diagnostic.line == 0 && diagnostic.column == 0);
    committed[1] = working[1]; committed[2] = working[2];
    CHECK(entry(inputs, working, 3, &diagnostic) == TINYPLC_NATIVE_OK);
    CHECK(working[1] == 5 && working[2] == 11);
    committed[1] = working[1]; committed[2] = working[2];

    /* Failed candidate is dirty. Preserve committed VAR; physical output policy
     * is represented here by a scalar, not a real driver or fault latch. */
    inputs[0] = 0;
    uint32_t status = entry(inputs, working, 3, &diagnostic);
    CHECK(status == TINYPLC_NATIVE_DIV_ZERO);
    CHECK(diagnostic.line == 7 && diagnostic.column == 12);
    CHECK(working[2] == 12 && committed[2] == 11);
    uint32_t physical_output = status == TINYPLC_NATIVE_OK ? working[1] : 0;
    CHECK(physical_output == 0);
    working[1] = committed[1]; working[2] = committed[2];

    /* Both undersized and oversized counts fail without changing either base. */
    CHECK(entry(inputs, working, 2, &diagnostic) == TINYPLC_NATIVE_BAD_COUNT);
    CHECK(diagnostic.line == 0 && diagnostic.column == 0);
    CHECK(entry(inputs, working, 4, &diagnostic) == TINYPLC_NATIVE_BAD_COUNT);
    CHECK(working[0] == 0 && working[1] == 5 && working[2] == 11);
    CHECK(inputs[0] == 0 && inputs[1] == 0 && inputs[2] == 0);

    inputs[0] = UINT32_MAX; working[2] = INT32_MAX;
    CHECK(entry(inputs, working, 3, &diagnostic) == TINYPLC_NATIVE_OK);
    CHECK(working[1] == UINT32_C(0x80000000));
    CHECK(working[2] == UINT32_C(0x80000000));
    return 0;
}
