# A0 CAD verification

Generated: 2026-10-24T22:46:43.581246+00:00

| Check | Result |
| --- | --- |
| KiCad version | 10.0.7 |
| Placed footprints | 95 |
| Named signal/power nets | 59 |
| Schematic ERC | 0 violations |
| Schematic/PCB parity | 0 issues |
| Placement DRC errors | 0 (excluding explicitly reported unrouted connections) |
| Placement warnings | {'silk_overlap': 6, 'silk_over_copper': 1} |
| Unrouted connections | **211 — routing unfinished** |
| Tracks | 0 |
| Electronic BOM | 87 individual purchased-item rows, matching CAD |
| Mechanical geometry | Valid single solids, closed case print meshes, no reported intersections |
| PDFs, native files and local document links | Present and checked |

These checks establish CAD consistency, not electrical function or a fabrication
release. Raw [ERC](erc.json), [DRC](drc.json), [native schematic netlist](netlist.xml)
and [mechanical checks](mechanical-checks.json) are preserved. DRC has not been
made clean by suppressing unconnected nets. Silk warnings remain visible for
the next layout revision. No physical test, printer fit, thermal measurement,
component availability approval or new-board firmware validation has occurred.

Tools used for initial generation: KiCad 10.0.7, FreeCAD 1.1.4, Blender 5.2.2 LTS.
Blender and FreeCAD were run headlessly; package geometry is approximate.
