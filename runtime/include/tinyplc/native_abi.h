/* tinyplc target call ABI draft 2, revision 1. Project-owned contract.
 * See docs/native-abi.md; compiler --abi 2 implements this call shape.
 * Arm calling-convention source: https://github.com/ARM-software/abi-aa
 * Related-work credits: docs/references.md. No upstream code incorporated.
 */
#ifndef TINYPLC_NATIVE_ABI_H
#define TINYPLC_NATIVE_ABI_H
#include <stddef.h>
#include <stdint.h>

#define TINYPLC_NATIVE_ABI_VERSION UINT32_C(2)
#define TINYPLC_NATIVE_MAX_TAGS UINT32_C(64)
#define TINYPLC_NATIVE_NAME_BYTES 32u
#define TINYPLC_NATIVE_OK UINT32_C(0)
#define TINYPLC_NATIVE_BAD_COUNT UINT32_C(4)
#define TINYPLC_NATIVE_DIV_ZERO UINT32_C(5)
#define TINYPLC_NATIVE_BAD_BOOL UINT32_C(8)
#define TINYPLC_NATIVE_TYPE_BOOL 1u
#define TINYPLC_NATIVE_TYPE_DINT 2u
#define TINYPLC_NATIVE_INPUT 1u
#define TINYPLC_NATIVE_OUTPUT 2u
#define TINYPLC_NATIVE_VAR 3u

/* Diagnostic data is untrusted application output, never a supervisor pointer. */
typedef struct {
    uint32_t line;
    uint32_t column;
} tinyplc_native_diagnostic;

/* Both arrays have count cells in declaration order; only INPUT indices in
 * inputs and OUTPUT/VAR indices in working are meaningful. All three memory
 * ranges are disjoint. The supervisor owns separate committed state.
 * Const documents the contract; actual read-only enforcement needs the MPU.
 */
typedef uint32_t (*tinyplc_native_entry)(const uint32_t *inputs,
                                      uint32_t *working, uint32_t count,
                                      tinyplc_native_diagnostic *diagnostic);

_Static_assert(sizeof(uint32_t) == 4, "ABI requires 32-bit cells");
_Static_assert(sizeof(tinyplc_native_diagnostic) == 8, "diagnostic size");
_Static_assert(_Alignof(tinyplc_native_diagnostic) == 4, "diagnostic alignment");
_Static_assert(offsetof(tinyplc_native_diagnostic, column) == 4, "column offset");
#endif
