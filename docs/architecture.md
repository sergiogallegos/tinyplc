# Runtime architecture (planned v1)

M0 provides scheduling and blink scaffolds only. This document describes the runtime to build in M1–M5; it is not a claim that those features work already.

## State owned by the scan

The portable core contains fixed arrays for program bytes, tag descriptors/values, VM stack, faults, and status. The port supplies time and physical I/O. `core/` accepts values, never a GPIO register, RTOS task handle, or socket. A program image is immutable once validated. Mutable tag state belongs to its slot. The VM receives a validated image and its state explicitly, making a native test independent of hardware.

The scan executes these phases:

1. Record start timestamp and interval from the previous start.
2. Sample physical inputs once into input tags; apply board-profile inversion.
3. Copy persistent values to a fixed working tag array, reset PC and operand stack, and execute within the instruction budget. Commit working values only after a successful scan; faults must not persist partial internal assignments.
4. Check fault and elapsed time before committing output values. On failure discard proposed outputs and write FALSE to every physical output.
5. Publish a coherent copy of tags and status; apply queued internal-tag writes and pending activation at the boundary before the next input read.
6. Wait for the next fixed release time. If late, count an overrun and avoid a rapid catch-up burst.

Output writes and boundary work contribute to the full scan execution time too. A deadline exceeded after output commit must immediately force outputs FALSE, set output tags FALSE in the published snapshot, and restore pre-scan persistent values. Fault policy is fail-closed for this experiment; it does not guarantee physical safety or replace electrical protection. Retain the failed PC/opcode separately for diagnostics rather than presenting proposed outputs as applied outputs.

## FreeRTOS target

Use FreeRTOS-Kernel ARM_CM4F with `configTICK_RATE_HZ=1000`, `configSUPPORT_STATIC_ALLOCATION=1`, `configSUPPORT_DYNAMIC_ALLOCATION=0`, `configCHECK_FOR_STACK_OVERFLOW=2`, and `configASSERT` enabled. Supply static task stacks, idle-task storage, and queues. Do not link a heap implementation. M4 must measure stack high-water marks rather than guessing final sizes.

The scan is the highest application priority task, scheduled with `vTaskDelayUntil`. Comms has lower priority. UART IRQs copy bytes into a bounded ring and never parse frames or run the VM. Comms can block on its own UART/event queue, while the scan never waits for comms, transport availability, download completion, or monitor readers. Requests use bounded mailboxes; a full mailbox returns BUSY. No mutex protects execution of a scan.

Configure period as an integer number of ticks (default 10, permitted 1..1000 ms) at startup; reject zero or unrepresentable values. No live period-change protocol is promised in v1. On overrun, rebase the next `vTaskDelayUntil` release to a future tick instead of repeatedly running overdue scans. An instruction budget bounds instruction count, not wall-clock time: IRQ duration, snapshot copies, migration of up to 64 names, and GPIO work belong in timing acceptance. A deadlocked runtime or hung instruction cannot be recovered by an elapsed-time check that never runs; watchdog coverage is a separate later extension.

DWT CYCCNT supplies cycle measurements. Unsigned subtraction handles one 32-bit wrap; task intervals must remain below the wrap duration. Convert cycles using the actual configured CPU clock. Define period jitter as `(current_start - previous_start) - configured_period`; retain signed minimum and maximum after the first measured interval. GET_STATUS reports scan count, last/max execution time, jitter min/max, overrun count, active generation, and fault. M0 uses 16 MHz HSI for blink; M4 will choose/document its clock and FPU/interrupt configuration explicitly.

## Snapshot publication without blocking

Use three statically allocated snapshot buffers: one owned by the scan producer, one by the comms consumer, and one exchange buffer. An atomic integer packs the exchange-buffer index and a dirty flag. Producer fills only its private buffer, then release/acquire exchanges its index with the middle index and sets dirty. It takes ownership of the previous middle buffer. Consumer swaps its own buffer with the middle only when dirty, clearing dirty, then reads its privately owned buffer.

This is a single-producer/single-consumer latest-value mailbox. Slow consumers may miss scans; snapshots include scan sequence and program generation. Neither side accesses the other's owned buffer; repeated publication reuses only producer/middle buffers. Comms serializes monitor requests through one consumer. C11 atomics provide ordering; `volatile` does not provide ownership or race protection. The target build must assert that the chosen atomic word operation is lock-free. M5 must exercise interrupted exchanges and slow readers. READ_TAGS must copy names/types/generation into the snapshot too, rather than retaining pointers to reusable program slots.

For a paginated READ_TAGS enumeration, comms keeps ownership of one captured snapshot until all pages are read or the enumeration times out. Each page carries its scan sequence and generation; the host supplies that sequence on continuation requests. Comms does not exchange its consumer buffer mid-enumeration. The scan continues publishing through the other two buffers without waiting. This prevents a tag table assembled from different scans.

## A/B slots and requests

Slots progress through EMPTY → DOWNLOADING → READY → PENDING → ACTIVE, with a preserved previous image marked ROLLBACK. Only comms writes a DOWNLOADING slot; the scan owns ACTIVE state. Validation finishes before READY is exposed using release/acquire ordering. DOWNLOAD_BEGIN refuses a slot that is PENDING or being migrated. Once the user starts another download into the inactive slot, the previous rollback image is explicitly retired; INFO must expose that rollback is then unavailable. Two slots cannot hold active, previous, and a third candidate simultaneously.

Both slots remain reserved from accepted activation until the new program's first scan completes, so comms cannot erase the image needed for automatic rollback. Slot reservations and boundary requests use atomic state transitions with generation checks; a pointer switch alone does not establish ownership of the other slot. Comms never spins waiting for the scan. DOWNLOAD_BEGIN, ACTIVATE, ROLLBACK, and WRITE_TAG must resolve conflicting requests as BUSY and cannot target state owned by a pending operation.

ACTIVATE changes only the pending request. After outputs are written, the scan matches internal VAR names and types, copies their values, zeroes other new state, then switches the active program pointer once with an atomic store. Input tags are overwritten by the next physical sample; output tags are calculated by the next execution. Pending requests carry a slot generation so a stale request cannot activate different bytes. No comms operation mutates live tags; WRITE_TAG enqueues an index/value/generation request, checked again at the boundary.

The old slot's state is frozen after migration. Explicit ROLLBACK restores that saved state and image at a boundary. If the candidate's first execution faults, force outputs FALSE, record the candidate fault, restore the old image, and resume the old program on the next scheduled scan. Avoid recursive rollback or clearing the recorded cause. With no old image, remain faulted with outputs FALSE. Later VM faults latch until explicit valid activation/rollback; exact acknowledgements distinguish accepted requests from completed swaps.

Retained diagnostic cause and current execution state are separate: after successful automatic rollback the old program may run while status still reports the rejected generation/fault. Explicit rollback restores the old frozen VAR state rather than migrating the candidate's latest values; this is deliberate and must be visible to users. In M5, test output continuity separately from VAR continuity: matching VARs alone cannot guarantee unchanged physical outputs after a logic edit.

## Memory and validation

Two 4376-byte maximum images plus two 64-entry value arrays use under 10 KB before snapshot buffers, stacks, and UART storage. Obtain actual totals from the linker map in M4. No casts from image bytes to packed structs: use explicit little-endian reads, bounds checked before advancing.

The extra working-value array is 256 bytes. Three snapshots containing 64 complete descriptors and values cost roughly 8 KB plus metadata. This remains practical within 128 KB, but fixed VM validation workspaces, RTOS stacks, queues, and every static buffer must be included in the map. Check both flash and RAM budgets.

Validation walks all instructions to build an instruction-boundary map, checks every operand (even in unreachable code), rejects backward jumps in v1, and propagates typed stack states through control flow. Branch merges must agree on stack depth and types. All reachable paths must end at HALT with an empty stack. Runtime guards remain independent of validation, including stack bounds, division checks, and instruction count.

## Host simulator and compiler

The native simulator will call the same core scan operations using monotonic POSIX time and simulated GPIO. A TCP server replaces UART framing but uses exactly the same messages. M0 demonstrates absolute deadlines with relative nanosleeps recomputed from CLOCK_MONOTONIC because macOS does not provide every Linux timer API. It does not claim deterministic timing.

Python compilation stages are lexer → AST parser → symbol/type/binding checks → bytecode emitter → image encoder. Parse errors include source line/column. The compiler computes capacity/stack bounds, but the controller repeats validation because transport bytes are untrusted. Python's reference VM masks DINT operations to 32 bits; differential tests compare it with the compiled C VM, including signed limits, every branch, and faults.

## Milestone dependencies

M1 owns slot state and a native scan-boundary API alongside tags/VM/validation. M3 implements and tests basic boundary activation plus coherent snapshots, since its CLI already exposes ACTIVATE and READ_TAGS. M4 ports that proven API to FreeRTOS and checks actual timing. M5 completes state migration, explicit/automatic rollback, race testing, and live-edit monitoring. These foundations cannot all be postponed until M5 without making M3 unsafe or misleading.
