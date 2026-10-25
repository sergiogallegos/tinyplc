# tinyPLC A0 prototype

Started 2026-10-24 at the user's request. This is an editable standalone STM32
engineering prototype draft, with a matching printable enclosure and assembly
documentation. A0 is a starting revision for review and iteration.

**The PCB is placed and electrically connected in the design database, but is
unrouted. It cannot be fabricated as a working controller yet.** No Gerbers or
order package are supplied. The BOM contains candidate parts and explicitly
unselected capacitor SKUs; it is not an approved purchasing list. The case can
be printed for a fit experiment now. No physical assembly has been tested.

## Open and inspect

| File | Purpose |
| --- | --- |
| [KiCad project](electronics/tinyplc-a0.kicad_pro) | Open in KiCad 10; schematic and placed PCB share pin-level nets |
| [Schematic PDF](electronics/tinyplc-a0-schematic.pdf) | Printable circuit atlas; equal net labels connect electrically |
| [PCB placement drawing](electronics/tinyplc-a0-placement.svg) | Actual KiCad footprint placement; no routed copper yet |
| [FreeCAD assembly](mechanical/tinyplc-a0.FCStd) | Editable spreadsheet, primitive and Boolean feature trees, board and package envelopes |
| [Assembly STEP](mechanical/tinyplc-a0-assembly.step) | Neutral-format enclosure, board and approximate packages |
| [Blender scene](renders/tinyplc-a0.blend) | Native assembled scene; render script also creates an exploded view |
| [Assembled preview](renders/tinyplc-a0-assembled.png) | CAD-based appearance preview |
| [Exploded preview](renders/tinyplc-a0-exploded.png) | Case, board and lid relationship |
| [Electronic BOM](bom/electronics.csv) | Reference, quantity, candidate MPN, purpose, official documentation and status |
| [Mechanical BOM](bom/mechanical.csv) | Printed parts, fasteners, wiring and external equipment |
| [Drawing package](mechanical/drawings/README.md) | Dimensioned A4 PDF/SVG drawings and a PCB fit template |
| [Combined drawing PDF](mechanical/drawings/tinyplc-a0-drawings.pdf) | Four sheets, retaining true-size A4 dimensions |
| [Visual assembly booklet](mechanical/drawings/assembly-guide.pdf) | Color CAD renders, parts inventory, assembly arrows and one action per step |
| [Technical assembly reference](mechanical/drawings/technical-assembly-reference.pdf) | Detailed printing, staged electronic assembly and electrical bring-up instructions |
| [Illustration scene](renders/assembly/assembly-illustrations.blend) | Editable Blender assembly illustrations, including nominal fasteners |
| [Assembly guide](../../docs/hardware/prototype-a-assembly.md) | Step-by-step print, assembly and bring-up sequence |

Start reading with the [electrical explanation](../../docs/hardware/prototype-a-electronics.md),
[component-by-component register](../../docs/hardware/prototype-a-components.md),
and [mechanical decisions](../../docs/hardware/prototype-a-mechanics.md).

## Agreed direction and explicit assumptions

The user authorized creating an initial PCB and case, using KiCad/FreeCAD, with
an optional Blender render; documenting decisions, every component and official
references; and supplying printable drawings and a step-by-step assembly guide.
No purchases or manufacturing orders were authorized or made.

The standalone board option was used to start work, following the existing
hardware roadmap. No user reply choosing a Nucleo carrier has been received.
Budget, printer, soldering equipment and final electrical ratings remain open.
All dimensions and component selections below are revisable assumptions.

- STM32F446RET6 in LQFP64; 120 × 90 × 1.6 mm PCB.
- Clean regulated 24 V bench supply, initially 21.6–26.4 V only.
- Four active-low input stages with optocouplers, sharing ground with the MCU.
- Four sinking outputs; initial test target 50 mA per channel, 200 mA total,
  resistive loads only. These are test targets, not verified ratings.
- On-board 3.3 V converter. No USB-to-board power path.
- Native USB-C circuitry reserved for new USB device firmware. The existing
  serial engineering protocol will first use a separate 3.3 V UART adapter.
- Optional display and Ethernet use cabled expansion headers. There is no
  selected direct-plug Ethernet footprint, RJ45 aperture, or display mounting
  adapter. Rendered lid opening has a real removable blank, not a fake screen.
- Case 132 × 102 × 32.4 mm, plus 2 mm display blank; screwed lid, no DIN clip.

## Revision and verification

[verification.md](reports/verification.md) records tool versions and measured CAD
checks. ERC is an electrical connectivity/rules check; it cannot establish
correct resistor calculations, circuit performance, fabrication readiness or
firmware operation. DRC reports preserve the unrouted connections.

The next electrical revision must finish BOM selection, review the schematic
and footprints, complete routing, select fabrication constraints and verify
clearances/current paths. Prototype the I/O stages on the Nucleo in parallel.
Then generate a separate manufacturing release with measured bring-up results.

## Regeneration and editing

Generated CAD can be edited directly in its native application. **Regeneration
replaces CAD and BOM outputs. Save manual changes under a new revision before
running generators.** There is no automatic bidirectional synchronization from
native CAD back to Python/JSON.

```sh
python3 hardware/prototype-a/scripts/generate_electronics.py
python3 hardware/prototype-a/scripts/generate_mechanics.py
python3 hardware/prototype-a/scripts/generate_drawings.py
blender --background --threads 6 --python hardware/prototype-a/scripts/render_blender.py
blender --background --threads 6 --python hardware/prototype-a/scripts/render_assembly.py
python3 hardware/prototype-a/scripts/generate_assembly_guide.py
python3 hardware/prototype-a/scripts/verify.py
```

The installed system Python provides KiCad's `pcbnew`; FreeCAD libraries are
loaded from `/usr/lib/freecad/lib`. No dependency downloads are performed.
The drawing script invokes `rsvg-convert` and `pdfunite` for PDF export. Changing layout needs
coordinated updates to the PCB generator, case openings and drawing generator;
`parameters.json` records the overall envelope, not a universal enclosure solver.

The visual booklet is generated separately from the technical text reference.
Its editable, self-contained SVG pages and individual PDFs are in
`mechanical/drawings/assembly-pages/`; source renders and camera-projected arrow
coordinates are in `renders/assembly/`. The illustrations use actual exported
case/board meshes, simplified package envelopes and nominal hardware. Colors
identify parts; they do not specify filament or hardware finishes. The case
geometry is unchanged. Lid text shown in renders represents separately applied
labels, not embossed print geometry.

Third-party KiCad library assets retain their [library license](electronics/THIRD_PARTY.md).
Original prototype scripts and documentation follow the repository license.
Hardware licensing for a future published manufacturing release remains open.
