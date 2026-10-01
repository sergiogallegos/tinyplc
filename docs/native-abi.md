# R2.1: native call ABI draft 2, revision 1

This freezes the first target **call contract** for R2 experiments. It is not
an image format, an implemented native loader, or a board acceptance result.
The compiler implements ABI 2 with `--abi 2`; default emission remains ABI 1
for existing host examples. R2.4 verifies ABI 2 on the board.
Changes to this contract require a new draft revision and fixture updates;
a deployed incompatible contract must receive a new ABI version.

## Target profile and calling convention

Profile: STM32F446RE, little-endian ARMv7E-M Thumb, Cortex-M4, base AAPCS32,
soft-float calling convention. Use `--target=thumbv7em-none-eabi -mcpu=cortex-m4
-mthumb -mfloat-abi=soft -ffreestanding`; no floating-point user operations,
variadics, exceptions, TLS, writable globals or runtime allocation. Compiler
helper calls and unresolved imports are forbidden for the initial leaf-function
experiment and must be checked in the final linked artifact.

On the target, pointers and cells are 32 bits. Follow AAPCS32 register
preservation and maintain an 8-byte-aligned stack at public call boundaries.
The four arguments use r0–r3 and the u32 result uses r0. A callable Thumb entry
has bit 0 set; validate its underlying instruction address against executable
code before constructing the call context. A host function pointer is native
host-sized, never serialized as an MCU pointer.
[Arm AAPCS32](https://github.com/ARM-software/abi-aa/blob/main/aapcs32/aapcs32.rst),
[Clang target selection](https://clang.llvm.org/docs/CrossCompilation.html).

## Entry and layout

The C11 declaration lives in
[native_abi.h](../runtime/include/tinyplc/native_abi.h):

```c
uint32_t scan(const uint32_t *inputs, uint32_t *working, uint32_t count,
              tinyplc_native_diagnostic *diagnostic);
```

The loader/supervisor chooses the validated entry; `scan` is illustrative,
not a required dynamic symbol lookup. There is one entry invocation per scan,
no initialization callback, and no user-created tasks. First activation starts
internal state at zero until R4 defines migration. Outputs begin each scan at
the previous committed values (zero on first activation), preserving R1's
behavior for unassigned outputs. The runtime drives fault outputs separately.

Both arrays contain exactly the module's tag count, 0..64. All objects are
valid, aligned to at least 4 bytes and disjoint for the call lifetime. Even for
an empty program, the supervisor supplies valid backing storage. Diagnostic
storage is always present. `count` must equal the validated schema count;
on mismatch, return 4 and zero the diagnostic without accessing either array.

Tag index is declaration order, offset `4 * index` in either array. BOOL cells
are canonical 0/1; DINT cells hold the 32-bit two's-complement bit pattern.
Names remain unique uppercase ASCII identifiers, up to 31 bytes plus NUL in a
32-byte zero-padded field. Type/class IDs retain R1 values: BOOL=1, DINT=2;
INPUT=1, OUTPUT=2, VAR=3. No embedded pointers, packed C enums or native-size
integers in metadata. Package encoding is a separate R2.7/R3 contract.

| Storage | Before entry | User permissions | After return |
| --- | --- | --- | --- |
| Input array | INPUT indices sampled; all other indices zero | Read-only, non-executable | Remains frozen for the whole scan |
| Working array | OUTPUT/VAR from committed state; INPUT indices zero | Read/write, non-executable | Candidate values only; never physical I/O |
| Diagnostic | Cleared by supervisor | Read/write, non-executable | Untrusted line/column report |
| Committed state | Previous successful state | Inaccessible | Supervisor alone commits accepted changes |
| Code/constants | Fully loaded and validated | Read/execute code; immutable constants | No modification during execution |

Generated INPUT loads use the input base; OUTPUT/VAR loads and stores use the
working base. Working INPUT cells are reserved zero and must stay zero. The
supervisor checks those cells and all candidate BOOL values on successful
return before committing only OUTPUT/VAR indices. C `const` is not protection:
the board port must enforce memory permissions and keep committed state private.
Disjoint logical buffers do not imply one MPU region per buffer; alignment and
placement are determined by the R2.3 memory budget.

## Results, faults and control transfer

Return 0 for success, 4 for count mismatch, 5 for division by zero, 8 for an
invalid BOOL in a relevant input/working cell. Report one-based source line
and column for 5/8; report zero/zero for success/count mismatch. Unknown return
codes are application faults. Diagnostics are bounded numeric data, never
trusted addresses. The initial profile exposes **no runtime service imports**:
I/O is represented by buffers, and timers are outside the language subset.

On any failure, working state and diagnostic contents may have been modified;
the supervisor discards candidate state, preserves committed internal values,
forces the experimental physical outputs FALSE, and latches a diagnostic.
User code cannot clear that latch or feed the watchdog. A deadline or CPU fault
is a supervisor event, not a normal return code or a promise of user cleanup.

Success is necessary but insufficient for commit: the trusted supervisor must
also confirm the deadline, intact context, generation and canonical outputs.
The guard is armed before entry. Normal return reaches a controlled
unprivileged trampoline; a reviewed RTOS exception/gateway path returns to the
supervisor. Do not call unprivileged code on a privileged supervisor stack or
assume a C function return restores privilege. The R2.6 STM32 experiment now implements these mechanics in a separate
worker, checked SVC gateway and timer/fault handlers. See
[native-isolation.md](native-isolation.md); this portable header alone does not
implement isolation. The fixed three-tag board trampoline is not a generic loader.

## Change from research ABI 1

| ABI 1, implemented R1 | ABI 2, implemented with --abi 2 |
| --- | --- |
| One mixed mutable cell array | Separate frozen input and writable candidate arrays |
| Generated function stages locally and rolls back internal values on fault | Supervisor owns transaction; candidate may be dirty on failure |
| Generated function clears output cells on fault | Supervisor enforces physical output policy regardless of candidate contents |
| Count at least schema size | Exact schema count |
| Diagnostic and tag metadata | Same scalar meanings; version 2 distinguishes the call shape |

Do not cast an ABI 1 function pointer to ABI 2. Versioned emission now runs the full semantic corpus for both ABIs, including
fault/discard cases. R1's call behavior and golden fixture remain unchanged.

## Acceptance and limits

`make test-abi` compiles a handwritten LLVM fixture against this C header and
runs a C caller at O0/O2. The fixture covers separate bases, argument order,
diagnostic layout, repeated state, guarded division, count mismatch and
supervisor discard of a deliberately dirty failed candidate. The same caller
and LLVM fixture cross-compile to Cortex-M ELF objects, with target-only
pointer-size assertions. These are contract fixtures, not a generated ST
program or a production supervisor. They establish no MPU, stack-budget,
register-preservation-on-hardware or timing evidence.

The R2.1 fixture stage did not flash a board. Subsequent [R2.4 evidence](R2.4-report.md)
records ABI 2 compiled ST running in RAM on the F446. Related work and official references are in
[references.md](references.md).
