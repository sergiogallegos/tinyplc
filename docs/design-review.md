# Design review, 2026-09-30

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
