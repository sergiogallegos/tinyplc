# Future plan: buildable tinyPLC hardware

**Status: deferred proposal, recorded 2026-10-04.** This document preserves a
future project idea. Hardware development has not started, the specifications
below are candidates, and no design is ready to manufacture. There is no
schedule or purchasing commitment.

## Purpose

Build a standalone educational tinyPLC with a custom PCB, a 3D-printed
enclosure, USB, Ethernet, and a small status display. Publish enough source
files and instructions that another person can order the board and enclosure,
buy the components, assemble the controller, install the firmware, and run a
Structured Text program.

The learning path should connect all layers: a signal at an input terminal,
the conditioning electronics, the firmware input image, compiled ST logic,
the output driver, and the physical load. PCB design, mechanical design,
manufacturing, debugging, and software are all part of the project.

Use KiCad and FreeCAD manually. Future assistance can provide step-by-step
instructions, calculations, reviews, and troubleshooting. MCP integration is
not a prerequisite or a planned deliverable.

The existing educational/research scope remains: this is not qualified for
real-machine control or safety functions. A custom PCB and enclosure do not
establish industrial, EMC, environmental, or safety certification.

## Starting point and gaps

The current [project overview](../README.md) describes native ST execution on
the NUCLEO-F446RE, a 10 ms scan, fault handling, program download/activation,
monitoring, online state migration, and TON timers. Recheck that baseline when
this project resumes; these observations describe the repository today.

The standalone board needs additional work:

- The existing physical demonstration uses a button and LED. Field terminals
  need input conditioning, output drivers, protection, and new I/O bindings.
- The engineering connection uses USART2 through the Nucleo's ST-LINK virtual
  COM port. Removing the Nucleo removes that USB bridge and onboard debugger.
- Downloaded programs and state are RAM-only. Power loss restores the
  firmware's boot program. Persistent application storage and startup recovery
  must be designed; retaining variable values is a separate decision.
- Ethernet and display support require hardware and firmware integration.
- Power regulation, clocking, reset, boot configuration, decoupling, and debug
  access currently supplied by the development board need their own design.

## Candidate first version

These are starting proposals, not frozen requirements or selected BOM items.

| Area | Candidate direction | Decide before schematic/layout approval |
| --- | --- | --- |
| MCU | STM32F446, preserving the current software investment | Exact part/package, memory budget, pin allocation, clock design |
| Supply | External 24 V DC source; onboard logic rails | Allowed voltage range, total power, reverse-polarity/transient protection, fusing and thermal budget |
| Digital inputs | Four protected nominal 24 V channels | Thresholds, filtering, polarity, common wiring, isolation requirements |
| Digital outputs | Four protected transistor channels | Sourcing or sinking, per-channel and total current, supported loads, inductive-load protection, fault feedback |
| USB | USB-C engineering connection | USB-to-UART bridge versus native USB; ESD protection, power roles, backfeed prevention |
| Ethernet | SPI Ethernet controller or module, with W5500 as a candidate | Module versus integrated circuit, magnetics/connector, pin budget, driver and protocol |
| Display | Small OLED with status and I/O view | Exact module, interface, mounting, readability, update rate |
| Controls | RUN/STOP control and navigation button | Startup state, restart behavior, debounce; this is not an emergency stop |
| Debug/recovery | SWD header, reset and boot access | Connector, external programmer, recovery instructions |
| Program storage | Persistent validated application | Internal versus external flash, capacity, endurance, interrupted-write recovery |
| Enclosure | Screw-assembled printed case; optional DIN-rail mounting | Size, material, clearances, terminal access, ventilation and mounting strength |

Keep analog I/O, relay outputs, touchscreens, and additional communication
buses as possible later extensions. Prefer a small, reproducible first build.
Ethernet connectivity alone does not provide an industrial protocol: choose
the initial engineering transport explicitly, with Modbus TCP as a possible
later feature. Define network exposure and access expectations before enabling
remote programming.

## Design principles

- Design for assembly and repair. Prefer accessible packages, practical
  passive sizes, clear polarity markings, labeled test points, and replaceable
  modules where useful. Decide which parts need reflow or factory assembly
  before promising a fully hand-soldered build.
- Keep outputs off during boot, reset, firmware download, and faults through
  an explicit hardware and software design. Verify behavior at the terminals.
- Give the scan priority over communications and display work. Use published
  snapshots for the display, bound communication work, and measure timing
  under simultaneous traffic and display updates.
- Plan the PCB and case together. Establish a common coordinate system,
  mounting holes, connector locations, component heights, and access space.
- Record exact component identities and tested substitutes. Avoid a BOM that
  depends on ambiguous marketplace descriptions.
- Preserve editable source and reproducible exports. Manufacturing and
  printing files must identify the exact hardware revision they represent.

## Work phases and completion gates

### H0 — Revisit and define requirements

When time is available, reread this plan and the current firmware status.
Choose the intended learning experiments, I/O electrical requirements,
available soldering tools, approximate size, prototype budget, and assembly
approach. Include fabrication, shipping, tools, and likely board revisions in
the budget. Recheck component availability and CAD versions at that time.

**Gate:** a short agreed specification, block diagram, initial pin allocation,
power budget, and list of unresolved decisions. No PCB order yet.

### H1 — Prove the new interfaces with the existing Nucleo

Prototype input/output circuitry and candidate Ethernet/display modules with
the current controller. Use suitable protected interface hardware for 24 V
signals; do not connect them directly to MCU pins. Exercise representative
loads within the proposed ratings. Evaluate the USB approach and persistent
program storage strategy.

**Gate:** documented interface tests, demonstrated ST-to-terminal mapping,
measured scan timing under added workloads, and evidence supporting the chosen
components. This prototype is a bridge to the standalone board.

### H2 — Design the schematic and preliminary enclosure

In KiCad, create separate schematic sections for power, MCU/debug, inputs,
outputs, USB, Ethernet, and display/controls. Follow the exact selected parts'
datasheets and reference designs. Review pin conflicts, voltage domains,
protection, startup behavior, power dissipation, and footprint pin numbering.
Resolve electrical-rule-check findings or document justified exceptions.

In FreeCAD, create a parametric enclosure concept with board supports,
connector openings, display window, fasteners, and optional rail mounting.
Account for screwdriver access, plugged-in cables, and assembly order.

**Gate:** reviewed schematic, preliminary BOM, reviewed footprints, and a
mechanical envelope that fits the intended components and connectors.

### H3 — Lay out the PCB and check mechanical fit

Select layer count and fabrication rules from the circuit's needs and the
chosen manufacturer's capabilities. Place critical power/protection and
connector circuitry deliberately; review return paths, trace sizing,
clearances, and interface routing against component guidance.

Export the PCB assembly as STEP and import it into FreeCAD. Verify hole
alignment, tallest components, terminal access, display placement, and cable
clearance. Print a fit prototype or critical sections before committing to
the final enclosure. Record printer/material settings and measured tolerances.

**Gate:** reviewed layout, resolved design-rule-check findings or documented
exceptions, schematic/PCB consistency, and a checked mechanical fit. Passing
CAD checks alone does not prove electrical correctness.

### H4 — Prepare and order a small prototype batch

Create a versioned manufacturing package and independently inspect the
exported fabrication files. Record board thickness, layer stack, copper,
finish, and any special requirements. Confirm footprints against the parts
actually being purchased, including terminal blocks and display modules.

For bare boards, prepare hand-assembly instructions and any stencil needed.
For optional factory assembly, supply the required BOM and placement files
and review the assembler's component substitutions and orientation preview.
Order or print the matching enclosure revision.

**Gate:** fabrication package checked against source, parts sourced, and a
small prototype order placed only when the project reaches this phase.

### H5 — Assemble, bring up, and integrate firmware

Document assembly order with reference designators, polarity checks, photos,
required tools, and inspection points. Start with unpowered continuity checks,
then verify power rails using a current-limited supply before functional
testing. Record expected voltages and acceptable current from the final design.

Establish SWD access, flash the runtime, verify clocks/reset/watchdog, and test
USB, each input/output, display, and Ethernet individually. Add a distinct
board profile and target port as needed while preserving the Nucleo example.
Implement persistent application validation, startup policy, and recovery.

**Gate:** repeatable cold boot, documented program recovery, verified I/O,
and a complete compile/download/run/monitor workflow. Test reset, power loss,
interrupted program updates, communication loss, and output fault behavior.
Measure scan timing and temperature under the declared operating conditions.

### H6 — Publish a reproducible educational release

Fix prototype findings, record errata, and repeat affected checks before
calling the hardware revision verified. Have another builder, where possible,
follow the instructions without relying on undocumented knowledge.

**Gate:** matching CAD sources, manufacturing exports, BOM, firmware revision,
test evidence, assembly guide, and first-program tutorial. Clearly distinguish
tested capabilities from future features and unverified operating limits.

## Proposed repository organization

Create these directories when work begins; this plan does not require empty
placeholder projects now.

```text
hardware/
  electronics/       KiCad project, schematics, PCB, project-local libraries
  mechanical/        FreeCAD source, parameters, assembly model
  bom/               Electronic and mechanical parts, tested alternatives
  manufacturing/     Export instructions and revision manifests
docs/
  hardware-roadmap.md This deferred plan
  hardware/          Requirements, design decisions, electrical limits
  assembly/          Tools, soldering sequence, photos, enclosure assembly
  bringup/           Inspection, power checks, flashing, recovery, I/O tests
boards/              New logical/physical I/O profile alongside the Nucleo
port/                Target-specific firmware integration
```

Keep reusable symbols, footprints, and necessary 3D models available through
project-relative paths, with their attribution and redistribution terms.
Record CAD versions and export steps. Decide how generated release bundles
are distributed, and identify each with a source commit and hardware revision.
Choose and document licensing for original hardware and mechanical designs
before publication; the existing software license does not settle third-party
asset permissions.

## Release contents

| Deliverable | Required contents |
| --- | --- |
| Editable electronics | KiCad schematic, PCB, project settings, local library dependencies |
| PCB fabrication | Gerbers, drill files, fabrication notes, board specification, revision |
| Assembly package | Schematic PDF, assembly drawings, polarity/orientation notes; placement files and stencil data if applicable |
| BOM | Reference designators, quantities, manufacturer and exact part number, package, ratings, supplier references, tested alternatives, optional/DNP status |
| Mechanical BOM | Terminals, screws, inserts, spacers, display mounting parts, rail clip, printed parts |
| Editable mechanics | FreeCAD source, dimensions/parameters, assembly and PCB fit model |
| Printing package | STEP plus STL or 3MF, units, material, orientation, supports, print settings, fit tolerances |
| Firmware | Compatible source revision, build/flash instructions, board profile, recovery procedure |
| Builder documentation | Tools, sourcing notes, assembly sequence, wiring diagrams, troubleshooting, first ST example |
| Verification | Test procedure, measured results, supported limits, errata, hardware/firmware compatibility record |

Treat BOM pricing and supplier availability as dated estimates. Include the
external supply and programmer in the required equipment list even if they
are not part of the assembled controller.

## First learning exercise

The first tutorial should let a builder trace and test one complete path:

1. Assemble and inspect the controller, then verify its power rails.
2. Flash the runtime and confirm status through USB and the display.
3. Connect a documented low-energy input and output demonstration load.
4. Compile and download an ST example, such as an input driving an output
   through a TON delay.
5. Observe the physical output, tag snapshot, and display status together.
6. Power-cycle the controller and verify the documented startup behavior.

Explain why each circuit and firmware boundary exists, with links from the
wiring diagram to schematic sections, board bindings, and runtime behavior.

## References to revisit when starting

- [Current hardware and firmware baseline](../README.md#hardware).
- [Native architecture roadmap](native-roadmap.md).
- [Educational design notes](education.md).
- [STM32F446RE manufacturer information](https://www.st.com/en/microcontrollers-microprocessors/stm32f446re.html).
- [W5500 manufacturer documentation](https://docs.wiznet.io/Product/Chip/Ethernet/W5500)
  for evaluating the Ethernet candidate, not a final component selection.

The next action, whenever this project is resumed, is H0: confirm the needs
and constraints before choosing parts or drawing the production board.
