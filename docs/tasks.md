# Implementation tasks and readiness

The architecture and educational scope are ready to guide development. R1 is
implemented; R2 is ready to start as a sequence of design and hardware
experiments. The final target contracts and board behavior are not yet proven.
This checklist tracks the [native roadmap](native-roadmap.md), whose stages
supersede historical M3–M5. Update checkboxes only with linked evidence.

## Completed baseline

- [x] Choose Rust frontend → typed PLC IR → LLVM IR → PC AOT → C/FreeRTOS.
- [x] Define and implement the small BOOL/DINT ST subset and research C call ABI.
- [x] Verify host AOT semantics at O0/O2 and Cortex-M object generation.
- [x] Document architecture diagrams, state ownership and dependency boundaries.
- [x] Record related work, official technology references and attribution policy.

Evidence: [R1 report](R1-report.md), [compiler ABI](../compiler/README.md),
[education](education.md), [references](references.md).

## R2 — native execution and protected supervision

Execute in this order; each item produces reviewable code/specification and evidence.

- [x] R2.1: Freeze a target ABI draft: Thumb/float convention, entry/return,
  tag layout, input/output permissions, fault result and permitted services.
  Specify how the research ABI changes; add host ABI fixtures.
  Evidence: [ABI draft 2](native-abi.md), `make test-abi`; [R2.1 report](R2.1-report.md).
- [x] R2.2: Select and pin toolchain, FreeRTOS revision and compatible MPU-aware
  port. Record license/provenance, build flags, startup ownership and SVC use.
  Evidence: [selection](target-toolchain.md), [R2.2 report](R2.2-report.md).
  Target build and hardening are still pending; selected GCC/OpenOCD are absent.
- [ ] R2.3: Measure firmware RAM/flash/stack needs; define linker regions with
  assertions for supervisor, user stack/state and executable RAM. Budget MPU
  regions and verify code fetch on the actual F446 board.
- [ ] R2.4: Link one tiny native function for a reserved RAM address; audit
  relocations/helper calls and execute it under C supervision on hardware.
  This experiment precedes a downloadable loader.
- [ ] R2.5: Establish static FreeRTOS tasks, frozen input/working state, GPIO
  commit, boot/fault output policy and a measured 10 ms scan release schedule.
- [ ] R2.6: Implement user privilege/MPU boundaries, checked service gateway,
  protected return/abort, independent deadline guard and watchdog fallback.
  Inject illegal access, infinite execution and stack faults; measure output
  response and recovery, including cases requiring reset.
- [ ] R2.7: Finalize package requirements and select placement/relocation and
  lab authenticity policies. Write the R2 report with reproducible commands,
  memory/timing measurements and remaining limitations.

The call ABI draft is frozen for experiments; target integration is not complete.
The MPU port and versions are selected. Open decisions in R2.3/R2.7 include
memory partitions, code placement, fixups and package encoding. Next: R2.3. ABI 2 compiler emission
and semantic regression checks must precede the R2.4 ST-generated experiment.

## R3 — upload, acceptance and monitoring

- [ ] Specify exact package and frame layouts, compatibility/version rules and
  golden fixtures; complete the [protocol proposal](protocol.md).
- [ ] Implement bounded loader checks, staging reservations, integrity checks,
  permitted fixups and rejection tests for corrupt/incompatible artifacts.
- [ ] Implement UART engineering transport and host download/activate/status
  commands, including retries, interrupted transfer and uncertain outcomes.
- [ ] Implement owned snapshots with generation/scan IDs and bounded monitor
  reads; prove a stalled reader does not delay scans or reference retired data.
- [ ] Demonstrate edit → build → upload → accept → monitor on the board; report
  measured whole-scan timing while downloads and monitoring are active.

## R4 — online state changes

- [ ] Define compatible migration, new-variable initialization and rollback
  state semantics; preserve frozen inputs and recompute outputs.
- [ ] Implement reserved first-scan trial, explicit rollback and contained-fault
  rollback, with generation/slot lifetime checks and concurrency tests.
- [ ] Demonstrate state transfer and failed-update recovery on hardware.

## R5 — deliberate extensions

- [ ] Select each extension from a documented need: timers/function blocks,
  larger types, source debugging, persistence or additional CPU targets.
- [ ] Give each extension its own semantics, resource budget and acceptance tests.

IDE, broad IEC coverage, industrial networking and product assurance remain
future scope. The full educational pipeline is complete only after the R3/R4
board demonstrations, not when the frontend alone passes host tests.
