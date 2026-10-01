# Design review, 2026-09-30

> Historical M0–M2 record. The selected architecture is now the
> [Rust frontend → LLVM AOT → C/RTOS runtime](../README.md).
> Bytecode/Python remain independent test references, not the product path.

## Verdict

The proposed direction is sound for learning PLC internals: small ST subset → explicit bytecode contract → portable C VM → shared native/MCU scan semantics. The F446RE has ample memory for the stated limits. FreeRTOS provides scheduling without hiding the execution engine. A handwritten compiler and standard-library TCP client keep the important parts visible. Proceed incrementally, with target timing acceptance separate from host correctness.

This is a design review, not proof that the future runtime is correct. M0 contains a finite scheduling demo and unbuilt blink sources; the full PLC remains to be implemented.

## Issues corrected before M1

| Issue | Decision |
| --- | --- |
| M3 promises activation before M5 supplies safe swapping | M1 provides slot ownership/boundary API; M3 proves basic activation/snapshots; M5 adds full migration/rollback. |
| Two slots cannot preserve three program versions | Starting a new download explicitly retires old rollback; reserve both slots until candidate's first scan completes. |
| Atomic active pointer is insufficient to stop slot reuse races | Add explicit atomic slot reservations, generation checks, and BUSY handling. |
| Paginated reads could mix scans | Pin the comms-owned snapshot across the enumeration and identify continuation pages by generation/scan sequence. |
| VM fault can leave partially updated internal state | Run with a fixed working-value array and commit persistent values only on scan success. |
| Fault snapshots could report an output that was never applied | Force physical output and published output tags FALSE; preserve failed PC/opcode separately. |
| Deadline accounting could omit swap/publication work | Measure full scan work; rebase overdue releases instead of catch-up bursts. |
| Auto-rollback can retain a fault while execution recovers | Separate retained diagnostic cause from execution state and expose rejected generation. |
| VAR matching does not guarantee output continuity | Document and test internal-state continuity separately from physical-output behavior. |

## Acceptance gates

- **M1:** Native VM/table/CRC tests, malformed images, typed stack branch merges, arithmetic boundaries, input-store rejection, instruction budget, and slot transitions. Run with host sanitizers where supported. Keep native tests dependency-free.
- **M2:** Define operator precedence/associativity and unary semantics before parser code. Verify diagnostic positions, golden bytecode, random well-typed ASTs, independent Python/C execution, and separately malformed-image rejection. Use fixed random seeds for reproducibility.
- **M3:** Lock every response field and units with golden binary fixtures; test fragmented/coalesced frames, resynchronization, transfer errors, transport timeout uncertainty, queue-full behavior, coherent pagination, and pending activation under an active scan loop.
- **M4:** Pin and checksum actual target inputs before fetching; verify linker/stack budgets, IRQ priorities, static allocation, serial ring overflow behavior, GPIO polarity, cycle-counter conversion, and real measured deadlines. No claim of hardware acceptance from a host simulation.
- **M5:** Stress download/activate/rollback/write interleavings, first-scan faults, old-slot reservation, migration rules, preserved diagnostics, and slow monitor readers. Show actual DWT timing in monitor.

## Scope choices to retain

Keep BOOL/DINT, forward-only bytecode jumps, fixed capacities, and one host connection in v1. A/B RAM images disappear on power loss; flash persistence is a later feature with separate wear/power-loss semantics. Modbus and TON should follow a correct scan/VM/compiler path. An external watchdog and hard deadline isolation are beyond the current design; instruction limits and post-execution timing checks alone do not recover a hung CPU.

## Remaining qualifications

Hardware pin mappings are supported by ST documentation, but BTN polarity still needs confirmation against the actual board revision. Selected tool versions are recorded; the ARM build and physical blink remain unverified because GNU Arm GCC/OpenOCD are absent. M0 should therefore be reported as host scaffold ready, with board acceptance pending, rather than fully completed hardware acceptance.

## Review of the mini PLC proposal after M2

The proposed contract → C runtime → compiler → engineering tools approach is
appropriate for this research controller. The portable core is the primary
artifact: FreeRTOS supplies scheduling, and the port supplies I/O and time.
The compiler and PC tooling must obey the runtime's contracts. This is a
review of the intended architecture, not evidence of a completed RTOS port.
The [README diagrams](../README.md#how-the-pieces-fit-together) distinguish M2
behavior from future integration.

### What the supplied task diagram gets right

The two task lanes make scan ownership and lower-priority communications
clear. Sampling, VM execution, output commit, observation, and boundary
activation are the right phases to expose. A snapshot separates monitoring
from live execution; staging separates download from activation.

The replacement diagrams refine four labels: the VM is C code executing
bytecode data; the download slot is whichever inactive slot is reserved, not
always B; activation needs an owned request and generation, not only a flag;
and comms handles independent commands rather than running download, read,
and activate as a fixed sequence. They also identify planned functionality,
show fault handling, and distinguish an accepted command from a running
program generation.

### Decisions to preserve and refine

1. **FreeRTOS, static allocation, and bounded port work.** Keep this choice for
   the first target. FreeRTOS supports application-supplied task/queue storage
   without its heap implementations; absolute periodic scheduling is the right
   starting point. Neither configuration proves deadlines: interrupts,
   critical sections, output writes, snapshot work, and migration still need
   budgets and on-board measurements. UART DMA can follow a bounded interrupt
   ring if measurements justify it; no parsing belongs in the ISR.
   [Static allocation](https://www.freertos.org/Documentation/02-Kernel/02-Kernel-features/09-Memory-management/03-Static-vs-Dynamic-memory-allocation),
   [periodic scheduling](https://github.com/FreeRTOS/FreeRTOS-Website-Content/blob/main/content/en-us/Documentation/02-Kernel/04-API-references/02-Task-control/03-xTaskDelayUntil.md).

2. **The small stack VM.** Keep validation and runtime guards independent.
   Forward-only control flow bounds a path by the number of decoded
   instructions; code length in bytes is a conservative upper bound, not the
   exact instruction count. A budget also counts HALT. Measure the whole scan
   on the STM32 before claiming 10 ms performance; host tests do not establish
   worst-case execution time. A VM narrows the executable surface but does not
   protect against bugs in its own C implementation or authenticate images.
   The current C/Python differential tests check semantics, not hardware timing.

3. **Separate immutable images from state.** Keep fixed u32 cells and tag
   indices for BOOL/DINT. M2 does not need arbitrary offsets. When structures,
   timers, or function blocks arrive, their state layout and migration policy
   must be specified and versioned. Match only internal VAR names and types
   for M5 migration; resample inputs and recompute outputs. Preserved state is
   useful continuity, but does not prove a bumpless output transition after
   changed logic. With two slots, downloading a third version must explicitly
   retire the existing rollback candidate.

4. **Owned requests and snapshots.** There are two directions of communication,
   each with a defined producer and consumer. Activation, rollback, and writes
   need bounded request payloads, slot reservations, generation checks, BUSY,
   and observable completion. Keep the planned three-buffer snapshot mailbox.
   A sequence counter around ordinary concurrently accessed C fields does not
   make data races legal, and retrying readers need progress analysis. Linux's
   seqlock rules also impose writer serialization and preemption constraints;
   that API is not a portable C11 implementation to copy verbatim. See
   [C11 draft N1570 §5.1.2.4, paragraph 25](https://www.open-std.org/jtc1/sc22/wg14/www/docs/n1570.pdf)
   and [kernel sequence-counter rules](https://www.kernel.org/doc/html/latest/locking/seqlock.html).

5. **Distinguish a user-program fault from a hung controller.** Force outputs
   FALSE, retain diagnostics, and keep a responsive faulted controller
   reachable. Feeding IWDG only after successful user-program execution would
   eventually reset that controller during a latched divide-by-zero fault.
   Proposed future policy: the scan owner may feed after a bounded RUN cycle
   or a bounded FAULT cycle that enforces outputs FALSE; it must not feed if
   the scan stops making progress. A comms task must not hide a stuck scan by
   feeding independently. Define boot behavior, reset-cause reporting, and
   diagnostic retention before enabling IWDG. Reset is not an output-safety
   guarantee. The watchdog remains an extension, not M2 functionality.
   [ST watchdog overview](https://wiki.st.com/stm32mcu/wiki/Getting_started_with_WDG).

6. **Compiler checks and versioned contracts.** Keep semantic type checks and
   the Python reference VM. M2 has a parsed AST and checks expression types
   while emitting; it does not retain a separate fully typed IR. The current
   24-byte image header has format version, lengths/capacities, flags, and
   CRC32. It does not have separate ISA/runtime versions, a layout hash, or a
   signature field. The format version currently selects the instruction
   contract. Introduce future extensions deliberately with a version change.
   A layout hash can classify structural differences but cannot prove changed
   logic is safe to activate. Runtime validation remains authoritative.

7. **Separate engineering from HMI access.** Keep the custom framed engineering
   protocol focused on staging, activation, status, and observation. Define
   idempotent chunk retries and reconcile status after ambiguous timeouts.
   Future Modbus writes must become scan-owned requests too. A separate UART
   for a future HMI link is a reasonable port choice, not a dependency for M3.
   First monitoring means tag values and fault/status information. Source-level
   highlighting needs a source map; an editor is a later interface layer.

8. **Firmware, persistence, and security are distinct contracts.** Keep ST-LINK
   firmware installation separate from RAM program downloads. Program flash
   persistence and A/B firmware updates each need a target-specific memory
   budget and power-loss recovery design; a dedicated sector plus CRC alone
   does not make interrupted updates recoverable. CRC detects accidental
   corruption and is not authentication. A reserved signature field alone
   would not define signing coverage, trusted keys, or replay policy. Keep the
   initial engineering connection local and revisit authentication before
   exposing it to untrusted networks. None of these extensions requires
   silently changing the existing v1 image now.

### What scales

The reusable concepts are a deterministic execution contract, one owner for
mutable execution state, immutable validated programs, bounded cross-owner
requests, coherent observation, and explicit update/fault states. These form a
useful foundation for a larger controller. Additional I/O, scan rates, complex
state, or clients require fresh capacity and scheduling analysis, expanded
migration rules, and stronger operational/security guarantees. This project
is an educational mini PLC, not a reduced-size claim of industrial or safety
certification.

The existing milestone order is still appropriate: M1 portable runtime and
M2 compiler are host-verified; M3 connects the engineering workflow in the
simulator; M4 reuses it on FreeRTOS/STM32; M5 proves migration and rollback.
Early button/LED board bring-up can reduce port risk without claiming those
later features are finished. No implementation milestone advances as a result
of this documentation review.

## Review of the native-code diagrams

The proposed shared front end and parallel bytecode/native paths are useful
research directions. The [native roadmap](native-roadmap.md) adds a corrected
layer comparison, compiler diagram, build/load/run workflow, repository plan,
and gates for experiments on the existing F446RE.

The maturity chart should describe responsibilities rather than require Rust,
LLVM, multiple scan tasks, or Ethernet for every production PLC. The backend
chart needs to distinguish our PLC-to-LLVM lowering from LLVM's existing CPU
backends. The native workflow must arm the timer before entry, include a real
privilege gateway, and qualify fault recovery. Slot ownership and migration
policy can be reused conceptually, while native state layout, MPU context, and
asynchronous abort require new implementation and tests. No native feature is
implemented by adding these diagrams.
