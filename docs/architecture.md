# Native PLC runtime architecture

Current decision: **ST → Rust frontend → typed PLC IR → LLVM IR → AOT native
code on the PC → native image → C/FreeRTOS runtime on the MCU**. The earlier
bytecode/Python design is historical. There is no planned VM fallback in the
product architecture. Existing interpreters remain independent test oracles.

R1 implements the Rust compiler and verifies host-native execution and ARM
object generation. This document describes the target supervisor, loader, and
monitoring design. R2.5 implements the basic GPIO scan transaction; isolation,
loading and monitoring remain to be built. The current statically linked test ABI is
in [compiler/README.md](../compiler/README.md); package/target work is detailed
in [native-roadmap.md](native-roadmap.md). The [R2.1 call ABI draft](native-abi.md)
defines separate input/working buffers, now emitted with `--abi 2` and exercised
in the [R2.4 privileged board experiment](R2.4-report.md).

## Ownership boundaries

The Rust frontend resolves declarations into typed expressions and numeric tag
indices. LLVM IR uses a caller-supplied state base, not privileged absolute
addresses. LLVM produces target object code on the PC; the host then needs a
link/package step against a versioned native ABI. LLVM does not provide PLC
semantics, a loader, I/O, tag monitoring, or update transactions.

The privileged C runtime owns the scheduler interface, active generation,
physical I/O, committed state, diagnostics, and update lifecycle. User code
receives only permitted input/working state and bounded services. The
communications task owns transport buffers, its snapshot, and an explicitly
reserved staging region. It cannot mutate active code or live state.

## Scan and tag database

Target period defaults to 10 ms, subject to actual board timing acceptance:

1. Record start/interval and sample GPIO into the input image.
2. Construct the working state from committed internal state and frozen inputs.
3. Arm an independent deadline guard and enter the native user context.
4. On trusted completion, validate outcome and elapsed time; commit permitted
   state only on success. On a contained fault, discard working changes.
5. Apply physical output values; enforce FALSE for the experimental fault state.
6. Publish coherent tags, status, diagnostics, scan sequence and generation.
7. Apply accepted generation-checked requests at the boundary, account for all
   boundary work in the deadline, and wait for the next absolute release.

After an overrun, avoid a burst of overdue scans. A late overrun must force
outputs FALSE and publish corrected status; it cannot undo an earlier physical
pulse. DWT measures cycles and jitter but is not itself a preemptive guard.
An interrupt-driven deadline guard and watchdog recovery are separate mechanisms.

The initial compiler ABI uses one 32-bit cell per tag, with canonical uppercase
names, type/class metadata, and offset `4 * index`. This is a prototype layout,
not the finalized native package contract. New types need size, alignment and
migration rules. Input values and output proposals must not grant user code
access to physical GPIO. Timers will use a defined scan clock and runtime-owned
service semantics; they are not implemented in R1.

R1's generated function already stages tag changes privately and commits on
success. It clears output cells on division/type faults and reports source
line/column. It does not implement input sampling, fault latching, deadline
interruption, physical outputs, snapshots, privilege transitions, or recovery.
Those responsibilities remain in the target C supervisor.

## FreeRTOS, MPU, and services

Use static allocation for task stacks, queues, slot/state storage, and
snapshots. The scan supervisor has the highest application priority; comms has
lower priority. No scan-path allocation or waiting for transport/readers.
Bound UART IRQ work and keep frame parsing in the comms task. DMA is a port
choice, not an initial requirement.

Native execution requires a reviewed MPU-aware FreeRTOS port and context
switch handling. The earlier ordinary ARM_CM4F plan is insufficient by itself.
Use unprivileged execution, protected supervisor memory/stack, non-executable
working data, and immutable executable user code after staging. Budget MPU
regions with the RTOS. Restrict peripheral/DMA control and check aliases.

A function-pointer service table alone cannot cross privilege boundaries.
Use a controlled gateway coordinated with SVC handling, with service IDs,
validated pointers/ranges, bounded execution and a specified ABI. Services may
read the input image and propose outputs; only the supervisor drives pins.

Arm the guard before entering user code. A native infinite loop must not
prevent fault handling. Returning to the faulting instruction is not recovery:
the supervisor needs a controlled abort path and a valid protected context.
Contained user faults should leave comms available. Privileged corruption,
exception-stacking failures and unrecoverable faults may require reset instead.
Feed a watchdog only while the controller makes bounded progress, including
responsive FAULT cycles holding outputs FALSE; user-logic success alone is not
the appropriate health criterion.

## Snapshot publication

Use three statically allocated buffers: producer-owned, consumer-owned, and an
exchange buffer with an atomic index/dirty flag. A release/acquire exchange
hands off completed data; neither party reads the other's private buffer.
Require the selected atomic operation to be lock-free on the target. A slow
consumer can miss updates but cannot delay the scan.

Copy tag names, types, values, scan ID, generation and diagnostics into the
snapshot. No pointers into reusable image/state slots. During paginated reads,
comms pins one snapshot through completion or timeout; subsequent requests
must identify that scan and generation. This is a consistency boundary between
monitoring and execution, not merely shared RAM exposed over UART.

## Download and activation

The native artifact needs its own versioned contract: target features, ABI,
segments, state schema, entry offsets, imports, stack/capacity needs, integrity
and authenticity policy, and permitted relocation records. An ELF `.o` from
R1 is an intermediate artifact, not accepted controller input. Never execute a
partially received, incompatible, or unvalidated image.

Slots follow reserved staging → validated READY → PENDING → ACTIVE. Every
activation request identifies a generation. An accepted response acknowledges
a queued request, not completed execution. The scan owner prepares state,
installs protection/context, and activates only at a boundary. Both old and
new contexts remain reserved through the candidate's first scan.

Future migration copies compatible internal variables by name/type/layout.
Inputs are sampled again; outputs are recomputed. Do not copy raw pointers.
Freeze the old context/state for rollback. If the candidate fails its first
scan, enforce outputs FALSE, retain its diagnostic, and restore old execution
at the next scheduled release if recovery is possible. Explicit rollback
restores saved old state, not the candidate's newest values. Starting another
download retires old rollback storage; two slots cannot hold three versions.

## Acceptance evidence

The host can verify compilation, arithmetic, branches, ABI calls, metadata,
and transactional results. Target tests must additionally verify memory/MPU
layout, gateway behavior, stack limits, relocations, interruption/abort,
physical output behavior, whole-scan timing and recovery. New CPU targets need
new port/ABI/protection evidence even if the language frontend is reusable.
See [R1-report.md](R1-report.md) for current evidence and
[native-roadmap.md](native-roadmap.md) for subsequent gates.

## Reference implementations

The [educational design study](education.md) compares Rusty/matiec frontend stages and
OpenPLC Runtime process images, lifecycle and generated-code interfaces with
our choices. Linux dynamic loading and synchronization are references for
responsibilities, not implementations to transplant into FreeRTOS.

See [references and acknowledgments](references.md) for related work and official
technology documentation, and [tasks](tasks.md) for implementation status.

R2.2 selects the [GCC Cortex-M4 MPU port](target-toolchain.md). Its default
peripheral permissions require hardening before this isolation policy holds;
selection alone is not evidence of isolation.

R2.5 update: the privileged board scan now uses physical GPIO, separate working/
committed state, latched faults and measured release timing. See the
[scan design](scan-runtime.md) and [hardware report](R2.5-report.md). R2.6
isolation and deadline abort remain unimplemented.
