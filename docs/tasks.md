# Implementation tasks and readiness

The architecture and educational scope are ready to guide development. R1 and R2 are complete with linked host and hardware evidence. R3.1 freezes the download
wire format with cross-language fixtures; R3.2 implements the packager and
portable validation/staging. R3.3 adds board download/activation. R3.4 adds owned tag monitoring. R3.5 verifies the complete board workflow and timing under mixed traffic. R4 implements online migration and rollback with host and hardware evidence.
The software sections track the [native roadmap](native-roadmap.md), whose stages
supersede historical M3–M5. The A1 section tracks the
[hardware roadmap](hardware-roadmap.md). Update checkboxes only with linked evidence.

## A1 prototype completion

This is the consolidated TODO list for completing the custom controller, its
BOM, enclosure and firmware. The Nucleo software results below do not close A1
hardware or firmware tasks. Unchecked items remain open; CAD checks establish
connectivity and geometry, not a working physical prototype.

Work order: freeze requirements and purchasing choices, review electronics and
physical fit, prepare fabrication, then assemble and integrate. Firmware work
and interface experiments on the Nucleo can proceed alongside design review.
Record completion evidence against each task: reviewed files, measurements,
test reports or photographs, with the matching hardware/firmware revision.

### Completed design baseline

- [x] Create the custom A1 schematic and route its two-layer PCB, including the
  switch loop, display header and power/RUN indicators. Correct DI1 and the
  input-capacitor footprint. Evidence: [routing decisions](hardware/prototype-a1-routing.md).
- [x] Pass native ERC, DRC, schematic parity and independent pin checks with
  zero unrouted connections. Evidence: [CAD verification](../hardware/prototype-a1/reports/verification.md).
- [x] Create the FreeCAD enclosure, print files, construction drawings,
  illustrated assembly guide and Blender product views. Evidence:
  [A1 package](../hardware/prototype-a1/README.md) and
  [publication/CAD checks](../hardware/prototype-a1/reports/publication-checks.json).

### Requirements and scope — before design approval

- [ ] A1-SCOPE-01: Freeze the bench operating specification: supply range,
  input thresholds/filtering, output polarity, per-channel/total current,
  supported loads, ambient conditions and startup/fault behavior.
- [ ] A1-SCOPE-02: Record assembly method, available tools/programmer, prototype
  quantity and budget including shipping, fabrication, printing and rework.
- [ ] A1-SCOPE-03: Decide the first-build Ethernet scope and program-storage
  behavior. Explicitly document any deferred feature and its user-visible limit.

### BOM and sourcing — before ordering

- [ ] A1-BOM-01: Replace every capacitor family placeholder with an exact MPN;
  check package, voltage derating, DC bias, tolerance and VCAP ESR requirements.
- [ ] A1-BOM-02: Resolve exact fastener, washer, lens, light-rod, adhesive, feet,
  wire and crimp-terminal SKUs; confirm the OLED module revision and switch.
- [ ] A1-BOM-03: Audit every electrical footprint/pinout and mechanical mating
  dimension against the exact purchased part's official documentation.
- [ ] A1-BOM-04: Complete a dated purchasing list with quantities, supplier/order
  links, availability, unit/total costs, spares and reviewed alternatives.
- [ ] A1-BOM-05: Include the external 24 V supply, SWD programmer, engineering
  cable/adapter, assembly consumables and test loads in the build budget.

### Electrical design and fabrication

- [ ] A1-ELEC-01: Independently review the schematic, power budget, regulator,
  fuse/switch/diode path, reverse polarity, transient protection and backfeed.
- [ ] A1-ELEC-02: Review input thresholds and resistor dissipation, output-driver
  limits and clamp paths, shared ground, and outputs during reset/faults against
  A1-SCOPE-01. Prove representative interfaces on the Nucleo where practical.
- [ ] A1-ELEC-03: Review clock loading/startup, decoupling, ground returns,
  current-carrying traces/vias and USB routing/damping against component guidance.
- [ ] A1-ELEC-04: Select the board supplier and fabrication stackup, copper
  weight, finish, drill/clearance and USB requirements; update layout if needed.
- [ ] A1-ELEC-05: After approved changes, regenerate matching CAD/BOM and repeat
  ERC, DRC, pin-contract and mechanical checks; record the reviewed revision.
- [ ] A1-ELEC-06: Generate and independently inspect Gerbers, drill files and
  fabrication notes; add placement files, assembly BOM and stencil if required.
- [ ] A1-ELEC-07: Order a small prototype batch after the purchasing, electrical
  review and mechanical-fit tasks pass; record supplier approvals/substitutions.

### Mechanical design and physical fit

- [ ] A1-MECH-01: Print the fit coupon using the intended material/printer;
  measure switch fit, pilots and optical bores, and record print settings.
- [ ] A1-MECH-02: Print the enclosure and check the PCB/card template, mounting
  holes, connector openings, component heights, lid fit and screw engagement.
- [ ] A1-MECH-03: Trial-fit actual switch terminals, crimp boots, display cable
  and external plugs; verify wire bends, strain relief, tool and service access.
- [ ] A1-MECH-04: Verify OLED mounting, lens/adhesive fit, readable markings,
  light-guide alignment, indicator brightness and light leakage.
- [ ] A1-MECH-05: Measure temperatures in the populated, closed enclosure under
  declared loads; review material, ventilation and clearances from the results.
- [ ] A1-MECH-06: Apply fit/thermal findings to CAD and drawings; reprint affected
  parts and record the final dimensions, materials and assembly instructions.

### A1 firmware and software integration

- [ ] A1-SW-01: Add a distinct A1 board target with its standalone clock,
  pin assignments, startup/linker configuration, SWD and recovery instructions;
  retain the working Nucleo target.
- [ ] A1-SW-02: Integrate all four conditioned inputs and four sinking outputs
  with the PLC I/O image, polarity/filtering and defined boot/STOP/fault policy.
- [ ] A1-SW-03: Bring up the UART engineering connection, then native USB;
  verify download, activation and monitoring without the Nucleo ST-LINK bridge.
- [ ] A1-SW-04: Implement the OLED's BOOT/STOP/RUN/FAULT and I/O views from coherent
  supervisor snapshots, with bounded I2C work and graceful display failure.
- [ ] A1-SW-05: Drive the RUN heartbeat from advancing accepted scans; implement
  the chosen user-button behavior and verify power/status indicators physically.
- [ ] A1-SW-06: Design and implement the selected persistent-application policy,
  validation, interrupted-write recovery and startup behavior. Decide retained
  variable state separately; document behavior when no valid application exists.
- [ ] A1-SW-07: If included by A1-SCOPE-03, select and integrate the Ethernet
  module, driver and initial protocol with bounded workload and defined access.
  If deferred, link the scope decision and keep Ethernet out of release claims.
- [ ] A1-SW-08: Repeat target memory/stack and 10 ms scan timing measurements
  under concurrent downloads, monitoring, display updates and enabled networking;
  repeat watchdog, deadline, MPU, migration/rollback and TON acceptance on A1.

### Assembly, validation and reproducible release

- [ ] A1-TEST-01: Assemble and inspect the PCB in stages; record polarity,
  unpowered continuity, current-limited startup, rail voltages and current draw.
- [ ] A1-TEST-02: Establish SWD access and verify clock/reset/watchdog operation;
  measure each input threshold and each output with the declared test loads.
- [ ] A1-TEST-03: Test the physical switch, cold boots, power loss/brownout,
  reset, interrupted updates, communication loss and runtime faults; record
  actual terminal behavior and recovery, including external-cable/backfeed cases.
- [ ] A1-TEST-04: Demonstrate ST compile → download → activate → physical I/O →
  monitor on the assembled A1, with the case and status interface installed.
- [ ] A1-REL-01: Record errata, correct findings and repeat affected checks;
  publish matching CAD, fabrication files, exact BOM, firmware and test evidence.
- [ ] A1-REL-02: Add real assembly photographs and measured bring-up results to
  the guide, plus a first-program tutorial; keep render/demo content identified.
- [ ] A1-REL-03: Reproduce the build from a clean checkout and have another
  builder follow the instructions where possible; document tested operating
  limits and distinguish remaining optional features from supported behavior.

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
