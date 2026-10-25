# A0 enclosure decisions and printing

The [FreeCAD file](../../hardware/prototype-a/mechanical/tinyplc-a0.FCStd) contains
the base, lid, display blank, PCB and package envelopes. Solids are editable
primitive/Boolean feature trees. A native spreadsheet controls core dimensions;
local opening coordinates remain separate features. The
[parameter record](../../hardware/prototype-a/parameters.json) describes the
same initial envelope. Regenerating replaces manual CAD edits.

## M01 — Envelope and coordinate system

The PCB is 120 × 90 × 1.6 mm. Its four 3.2 mm NPTH mounting-hole centers are
(5,5), (115,5), (5,85), (115,85), measured from the PCB outline corner used by
the layout. The case uses the same increasing X/Y directions, with the PCB
origin translated by (6,6) mm. Case Z=0 is its outside bottom.

The base is 132 × 102 × 30 mm; the lid is 2.4 mm thick. The optional display
blank adds 2 mm locally, giving a maximum height of 34.4 mm. These dimensions
prioritize room for probes, accessible packages and board changes. They are
not a compact product envelope or a DIN-rail width standard.

KiCad's Y direction is down in its top view. The FreeCAD construction deliberately
retains the numeric board coordinates instead of silently reflecting them.
The supplied fit template labels the DI and Q edges so the assembly cannot be
inferred solely from an unlabeled drawing orientation.

## M02 — Wall, floor and board supports

Walls and floor are 2.4 mm thick, a starting point for a 0.4 mm nozzle with
multiple perimeters. Print dimensions, rather than this nominal nozzle ratio,
determine actual strength. The inside shell dimensions are 127.2 × 97.2 mm,
leaving nominal 3.6 mm lateral clearance around the board.

Four 7 mm-diameter posts carry the PCB bottom at Z=8 mm. The 5.6 mm space above
the floor accommodates through-hole leads protruding below the 1.6 mm board.
Trim and inspect leads so they do not touch the floor. The posts' 2.5 mm pilots
are provisional for tapped M3 threads. Use an M3 tap carefully or verify a
suitable plastic screw on the test coupon; do not assume an M3 machine screw
will self-form a reliable thread. No heat-set inserts are fitted in A0.

M3 × 6 PCB screws pass through the board and a nominal 0.5 mm washer, leaving
about 3.9 mm engagement. Verify the actual screw, washer and pilot depth before
tightening. Printed threads are for low-cycle prototype access. A later revision
can add inserts once repeated-assembly requirements are known.

## M03 — Lid and screw towers

The lid uses four separate corner towers at case coordinates (3.5,3.5),
(128.5,3.5), (3.5,98.5), (128.5,98.5). Towers are 6.2 mm diameter and have
2.5 mm pilots extending down from Z=30 to 22 mm. They were moved outward after
the initial CAD check found a collision with the board corners.

The lid has 3.4 mm clearance holes and 6.2 mm-diameter, 1 mm-deep counterbores.
Candidate M3 × 8 screws provide about 6.6 mm engagement below the remaining
1.4 mm lid web. A 1 mm counterbore does not fully bury a normal pan head.
Confirm the selected head fits and does not crack the thin outer corner web.
Use gentle hand tightening; no assembly torque has been validated.

A 1.8 mm locating lip aligns the lid with 0.3 mm clearance per side. Local
circular reliefs clear the towers. The lip locates the lid; the screws retain
it. This fit allowance is an untested starting value: measure a coupon and
adjust for the actual printer, filament and shrinkage.

## M04 — Terminal and USB access

Each of the four DI and four Q positions has its own 12 × 16 mm horizontal
wire-entry opening, starting at Z=9 mm. A ninth opening serves the power input.
DI terminal footprints are rotated 180 degrees; their center offsets are
accounted for separately from the Q row. The lid is removed to reach terminal
screws, permitting an uncluttered exterior and direct screwdriver access during
bench work. Label wire functions after fitting the real terminals.

The USB opening is a 19 × 10 mm service opening in the right wall, spanning
Y=39.5–58.5 mm and Z=7–17 mm. It provides room for a recessed connector and
the plug overmold. Actual plug insertion and strain relief still need a fit
test. A connector bounding box does not establish cable access or allowable
connector load. Add a cable clamp before moving a wired prototype regularly.

## M05 — Display blank and deferred features

The lid aperture is 30 × 18 mm centered at (82,51). The 46 × 26 × 2 mm blank
has two 2.8 mm holes 39 mm apart. Two M2.5 × 8 screws, washers and nuts retain
it. This detachable part makes the initial case printable while leaving room
for a later display-specific adapter. It is not a mounting pattern for any
particular OLED. The chosen module's viewing area, PCB, holes and cable bend
must drive a separate adapter revision.

There is no RJ45 hole or DIN-rail clip. Ethernet is an optional off-board
experiment until the module and mounting are selected. Base vents are deferred
until closed-case heat measurements show the airflow required. There is no
gasket, ingress rating or certification implied by the enclosure.

## M06 — Print files, drawings and settings

Use the supplied `*-print.stl` files, not arbitrary assembly exports. STL carries
no unit metadata: import as **millimeters**. Base floor is already at Z=0; the
lid mesh is inverted so its outside face prints down; the blank lies flat.
The STEP and FreeCAD files retain assembly coordinates and are not all bed-ready.

The [drawing package](../../hardware/prototype-a/mechanical/drawings/README.md)
provides A4 PDF/SVG views, dimensions, datums and a 1:1 PCB fit template. Print
PDFs at 100%/actual size and verify the 100 mm scale bar; disable fit-to-page.
Do not infer dimensions from screen pixels. Drawings document the prototype,
not an injection-molding tooling specification.

Initial slicer assumptions: 0.4 mm nozzle, 0.2 mm layers, at least four
perimeters, five top/bottom layers and 20–30% infill. Use the actual filament
manufacturer's temperature and bed guidance. Start with PLA for an unpowered
fit check; PETG is the candidate bench enclosure material. These are proposed
settings, not validated profiles. See the official
[Prusa PETG printing guide](https://help.prusa3d.com/article/petg_2059) and
[Prusament PETG material data](https://prusament.com/wp-content/uploads/2022/10/PETG_Prusament_TDS_2021_10_EN.pdf).

Inspect the slicer preview around the terminal-opening bridges, pilot holes,
lip and counterbores. Local supports or bridge tuning may be needed. Avoid
filling pilots with difficult-to-remove support. Print the coupon first and
measure its 3.2/3.4 mm clearance holes and 2.5 mm pilot. Check the 0.3 mm lip
gap separately on the printed lid and base.

Fastener hole sizes and print allowances are project design assumptions. The
[Bossard plastics fastening guide](https://media.bossard.com/us-en/-/media/bossard-group/website/documents/white-paper/bossard-whitepaper-fastening-solutions-for-composite-and-plastic-materials-en-04-2021.pdf?la=en-us)
explains why material, boss geometry and screw type must be considered together;
it is not approval of this printed joint or an exact screw datasheet.

## M07 — What the CAD check proves

The generator checks solid validity, closed print meshes and Boolean volume
intersections between the board, base and lid. It also checks approximate
component envelopes against the case. The solid geometry used for Blender is
tessellated from the same FreeCAD parts, not recreated as a different case.

Component models are simplified package envelopes, not manufacturer STEP models.
The render's text and terminal screw details are visual annotations, not
embossed or engraved print geometry. No copper routing is depicted. CAD checks
do not prove print accuracy, screw pull-out strength, wiring access, thermal
performance or compatibility with every nominally similar component.
