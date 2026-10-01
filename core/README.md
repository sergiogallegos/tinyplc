# Portable core: learning and API guide

> Historical M0–M2 record. The selected architecture is now the
> [Rust frontend → LLVM AOT → C/RTOS runtime](../README.md).
> Bytecode/Python remain independent test references, not the product path.

Read `src/tags.c`, then `src/image.c`, `src/vm.c`, and `src/runtime.c`. Public types and functions live in `include/tinyplc/core.h`. Only C11 standard headers are used. There are no heap allocations, HAL calls, FreeRTOS headers, sockets, or GPIO references.

## Program construction and execution

A `plc_program` owns serialized bytes and a bitset of instruction boundaries. It becomes usable only when `plc_validate` succeeds. Validation checks the header/CRC and tag descriptors, decodes every instruction, then propagates stack depth/types along forward control flow. One bit per stack position distinguishes BOOL from DINT. Two branches reaching the same instruction must supply identical depth and types. This checks stack correctness without executing the program.

A `plc_values` holds 64 unsigned 32-bit cells. BOOL is 0/1; DINT cells contain a two's-complement bit pattern. `plc_signed` converts it to an int64_t mathematical value for comparisons and division. Arithmetic uses unsigned cells, so overflow is defined. The division intermediate can represent INT32_MIN/-1 before conversion back to 32 bits.

`plc_vm_run` starts with empty stack and PC zero on every call. It repeats opcode/type/bounds/budget checks independently of the validator, but does not recompute CRC on every scan. Program bytes must remain immutable after validation. Its values are working state; a VM fault may leave partial changes there. `plc_runtime_scan` wraps it with a persistent/working-state transaction, retaining persistent VARs and forcing output tags FALSE on failure. Sampled valid inputs remain visible for diagnostics. A fault latches further execution until activation; retained diagnostics survive recovery.

## Two owners, one mailbox

Initialize `plc_runtime` before either owner starts. Verify `plc_runtime_lock_free` on the target. Keep runtime and validation workspace statically allocated. One comms context owns stage/activate/discard; one scan context owns scan/boundary and every live tag-value access. The API does not support multiple producers or concurrent scans.

```text
IDLE --stage reserves inactive slot--> STAGING
STAGING --valid image copied--> READY
STAGING --invalid image--> IDLE
READY --discard--> IDLE
READY --activate matching generation--> PENDING
PENDING --scan boundary zeroes new values and switches pointer--> IDLE
```

Comms never modifies the active slot. Acquire/release operations on the mailbox publish candidate bytes and protect slot reuse. A pending request cannot be discarded or overwritten. The scan boundary performs one atomic active-pointer store and releases the previous slot only after it has stopped accessing it. Initial activation can run at the initial boundary before the first scan; subsequent calls must follow the physical output commit.

An activation acknowledgement means pending, not complete. M1 starts all new tag values at zero. It does not implement migration, snapshots, or rollback yet, and an old slot may be reused after boundary completion. M5 will reserve both slots through a candidate's first-scan trial before adding automatic rollback. `plc_runtime_stage` copies/validates a whole image; M3 adds bounded transport chunk assembly outside this API.

Generation numbers start at one, increase for every successfully staged image (including discarded candidates), and are never reused during a runtime session. Requests with stale generations fail. Generation exhaustion refuses further staging instead of wrapping. Reinitialize only while both owners are stopped.

## Integrating a port

1. Supply the allowed I/O names, types, and classes as a `plc_profile`; the core consumes no JSON. M1 simulator/tests supply BTN/LED matching the JSON board profile. A NULL/empty profile permits internal tags only. M2/M4 must ensure the compiler/target profiles stay consistent.
2. Stage an image and request activation from comms. Keep its `plc_workspace` owned by that context. Pointer/array arguments are caller-owned; do not pass an active program as a validation destination.
3. At a boundary the scan consumes activation. Sample physical inputs with inversion into a `plc_values` array indexed by tag index.
4. Call `plc_runtime_scan`; always apply active output tags, including when it returns a fault. Hardware I/O and deadline enforcement remain the port's responsibility.
5. Finish output writes, then call `plc_runtime_boundary`. Do not retain old-slot pointers beyond this call.

`plc_tag_write` is an owner-only VAR write primitive, not a thread-safe remote write API. M3 must enqueue protocol writes for the scan owner with a generation check. Comms must never use tag lookup/accessors against mutable/reusable live slots; use a captured snapshot once M3 introduces that mechanism. Exposed structs aid learning, but direct mutation bypasses the API's ownership contract.

## Memory and tests

On the verified arm64 Mac ABI: program=4642 bytes, runtime=10104 bytes, reusable validator workspace=18432 bytes. Runtime includes two programs, two persistent value sets, and one working set. Values differ with ABI; target stack/flash/RAM acceptance still requires the ARM linker map. Validation storage is not on the scan stack; VM stack storage is 256 bytes plus locals/call frames. Snapshot buffers and UART/RTOS allocations are future additions.

`make test` checks the wire contract using hand-built fixtures, without the future compiler. `make sanitize` runs address/undefined-behavior checks; `make thread-sanitize` instruments actual concurrent producer/scan activation. Mutations and stress runs exercise defects but do not prove all possible interleavings. Python/C differential execution remains M2.
