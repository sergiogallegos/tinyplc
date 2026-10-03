# Implementation tasks and readiness

The architecture and educational scope are ready to guide development. R1 and R2 are complete with linked host and hardware evidence. R3.1 freezes the download
wire format with cross-language fixtures; R3.2 implements the packager and
portable validation/staging. R3.3 adds board download/activation. R3.4 adds owned tag monitoring. R3.5 verifies the complete board workflow and timing under mixed traffic. R4 implements online migration and rollback with host and hardware evidence.
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
  R2.3/R2.4 built and exercised the selected integration; full isolation remains R2.6.
- [x] R2.3: Measure firmware RAM/flash/stack needs; define linker regions with
  assertions for supervisor, user stack/state and executable RAM. Budget MPU
  regions and verify code fetch on the actual F446 board.
  Build/layout and board RAM-fetch/stack observations passed; [R2.3 evidence](R2.3-report.md).
- [x] R2.4: Link one tiny native function for a reserved RAM address; audit
  relocations/helper calls and execute it under C supervision on hardware.
  This experiment precedes a downloadable loader.
  ABI 2 semantic regression and ST-generated board execution passed; [R2.4 evidence](R2.4-report.md).
- [x] R2.5: Establish static FreeRTOS tasks, frozen input/working state, GPIO
  commit, boot/fault output policy and a measured 10 ms scan release schedule.
  Host fault tests and board GPIO/fault/timing checks passed; [R2.5 evidence](R2.5-report.md).
- [x] R2.6: Implement user privilege/MPU boundaries, checked service gateway,
  protected return/abort, independent deadline guard and watchdog fallback.
  Inject illegal access, infinite execution and stack faults; measure output
  response and recovery, including cases requiring reset.
  All 19 final board cases passed; [R2.6 evidence](R2.6-report.md).
- [x] R2.7: Finalize package requirements and select placement/relocation and
  lab authenticity policies. Reserve trusted trampoline storage outside
  downloadable payload ownership. Write the R2 report with reproducible commands,
  memory/timing measurements and remaining limitations.
  Evidence: [package requirements](native-package.md), [R2 report](R2-report.md).

The R2 research gate is closed: protected native execution, fixed-slot host
linking and unsigned-lab package requirements are established. Exact package encoding is complete in R3.1; dynamic loading remains R3 work.
Upload/status/activation are implemented in R3.3; R3.4 adds snapshots. R4 adds migration and rollback.

## R3 — upload, acceptance and monitoring

- [x] R3.1: Specify exact package and frame layouts, compatibility/version rules and
  golden fixtures; complete the [protocol contract](protocol.md).
  Evidence: [R3.1 report](R3.1-report.md), `make test-wire`.
- [x] R3.2: Implement bounded loader checks, staging reservations, integrity checks,
  exact slot placement and rejection tests for corrupt/incompatible artifacts.
  Evidence: [R3.2 report](R3.2-report.md), `make test-loader loader-target-check`.
- [x] R3.3: Implement UART engineering transport and host download/activate/status
  commands, including retries, interrupted transfer and uncertain outcomes.
  Evidence: [R3.3 report](R3.3-report.md), `make test-engineering`, explicit board matrix.
- [x] R3.4: Implement owned snapshots with generation/scan IDs and bounded monitor
  reads; prove a stalled reader does not delay scans or reference retired data.
  Evidence: [R3.4 report](R3.4-report.md), `make test-engineering`, concurrent
  sanitizer stress and target build/layout checks. Hardware timing remains R3.5.
- [x] R3.5: Demonstrate edit → build → upload → accept → monitor on the board; report
  measured whole-scan timing while downloads and monitoring are active.
  Evidence: [R3.5 report](R3.5-report.md), [board results](evidence/R3.5-board.json),
  11 downloads and 20 complete 64-tag snapshots with zero missed releases.

## R4 — online state changes

- [x] R4.1: Define compatible migration, new-variable initialization and rollback
  state semantics; preserve frozen inputs and recompute outputs.
  Evidence: [normative state contract](online-state.md), [R4.1 review](R4.1-report.md).
  Implemented in R4.2; historical R4.1 evidence records the design decision.
- [x] R4.2: Implement reserved first-scan trial, explicit rollback and contained-fault
  rollback, with generation/slot lifetime checks and concurrency tests.
  Evidence: [R4.2 report](R4.2-report.md), `make test-engineering test-update-thread`,
  2,000 concurrent activation/rollback pairs under ThreadSanitizer.
- [x] R4.3: Demonstrate state transfer and failed-update recovery on hardware.
  Evidence: [R4.3 report](R4.3-report.md), [board matrix](evidence/R4.3-board.json)
  and [mixed traffic](evidence/R4.3-monitor.json), including failed restoration.

## R5 — deliberate extensions

- [x] R5.1: Add the requested TON on-delay timer with TIME, a frozen millisecond
  clock, reset-on-update behavior, resource limits and host/board acceptance.
  Evidence: [TON contract](ton.md), [R5.1 report](R5.1-report.md).
- [ ] Select subsequent extensions from a documented need, with their own
  semantics, resource budget and acceptance tests.

IDE, broad IEC coverage, industrial networking and product assurance remain
future scope. The R1–R4 educational pipeline now has host and board evidence;
future extensions require their own defined need and acceptance gates.
