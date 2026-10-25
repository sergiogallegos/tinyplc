# A0 print drawings

Four A4 landscape sheets, supplied as editable SVG and printable PDF:

1. `01-base.pdf`: base plan, support locations, walls and opening dimensions.
2. `02-lid-and-blank.pdf`: lid, aperture, screw pattern and detachable blank.
3. `03-pcb-fit-template.pdf`: 1:1 board outline, holes and connector envelopes.
4. `04-print-coupon-and-stack.pdf`: fit coupon, print orientation and Z stack.

`tinyplc-a0-drawings.pdf` combines the four dimensioned sheets.

`assembly-guide.pdf` is the visual assembly booklet: colored CAD-based renders,
part quantities, insertion arrows, fastener details and sequential mechanical
assembly steps. The booklet uses A4 landscape pages; its illustrations are not
scale drawings. `assembly-pages/` contains editable SVGs and individual PDFs.

`technical-assembly-reference.pdf` retains the detailed printing, soldering,
electrical bring-up and testing instructions from the repository assembly guide.
Use it alongside the visual booklet for the future electronic build.

Print the dimensioned drawings at actual size / 100%. Disable fit-to-page and measure the 100 mm scale
bar. These are dimensioned prototype construction drawings, not PCB copper
artwork. Use the KiCad file for pad locations and FreeCAD for full case geometry.

Use `../*-print.stl` for 3D printing, importing STL units as millimeters. The
lid STL has its print orientation applied; assembly STEP retains assembly
coordinates. See the [assembly guide](../../../../docs/hardware/prototype-a-assembly.md).

The [Blender exploded view](../../renders/tinyplc-a0-exploded.png) supplements
these drawings. Component bodies are approximate envelopes. Fit checks are
digital; no physical printer, screws or parts have been tested.
