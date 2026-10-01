/* Project-specific ABI. Related-work reading: OpenPLC's generated-program/image
 * interfaces and matiec's variable access layer. Neither implementation is used
 * here. See docs/education.md and docs/references.md at the repository root.
 * C language reference: WG14 N1570 (public C11 draft), linked in references.md.
 */
#ifndef TINYPLC_LLVM_SCAN_ABI_H
#define TINYPLC_LLVM_SCAN_ABI_H
#include <stdint.h>
/* Research ABI for one statically linked generated module; not a download image.
 * Caller owns execution and supplies disjoint, aligned, valid storage.
 * cells has at least count u32 cells; diagnostic is always required.
 * Initialize cells to zero, then sample INPUT cells before each call.
 * Success commits OUTPUT/VAR cells. Fault 5/8 clears OUTPUTs and preserves VARs.
 * Fault 4 (count too small) leaves all cells untouched. No latching or deadlines.
 */
typedef struct { uint32_t line, column; } tinyplc_diagnostic;
extern const uint32_t tinyplc_abi_version, tinyplc_tag_count;
extern const uint8_t tinyplc_tag_types[], tinyplc_tag_classes[];
extern const char tinyplc_tag_names[][32];
uint32_t tinyplc_scan(uint32_t *cells, uint32_t count, tinyplc_diagnostic *diagnostic);
#endif
