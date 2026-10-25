# Library asset provenance

Symbols and footprints were copied from the installed KiCad 10 library packages
on 2026-10-24. Original libraries are maintained by the KiCad library team:

- [KiCad symbols](https://gitlab.com/kicad/libraries/kicad-symbols)
- [KiCad footprints](https://gitlab.com/kicad/libraries/kicad-footprints)
- [Official library license](https://www.kicad.org/libraries/license/)

KiCad library assets use CC BY-SA 4.0 with the KiCad library exception. Preserve
that license and exception when redistributing extracted or modified library
assets. The repository MIT license does not relicense third-party library data.

`tinyplc.kicad_sym` snapshots selected library symbols under unique project-local
names; inherited symbols are flattened. The VO617A-3 instance uses a four-pin
LTV-817 graphic with a proposed matching pinout, documented in the electrical
guide. Footprints are retained in `tinyplc.pretty`; board instances remove
system-specific model links because the mechanical assembly uses explicit
project-created envelope geometry. The footprint snapshots retain their
original descriptions, generator information and any embedded model references.

The TSR_1_2433 and TPL7407L symbols and PTC_MF_R050 footprint are project-created
from the linked manufacturer pin tables/dimensions and need final review.
FreeCAD package envelopes and Blender details are project-created approximations,
not downloaded vendor models. Manufacturer datasheets are linked, not copied
into this release. No third-party raster textures or image assets are used.
