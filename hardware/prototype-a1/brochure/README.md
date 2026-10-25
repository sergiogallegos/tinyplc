# tinyPLC A1 prototype brochure

[Open the eight-page PDF](tinyplc-a1-brochure.pdf).

The brochure introduces the product appearance, power/ground identification,
physical switch, OLED/LED interface, custom hardware, current software and the
path from repository files to a tested prototype. All product pictures are
Blender renders derived from the A1 CAD. OLED content is a proposed interface,
not a screenshot from a working controller. The PCB is routed and passes native CAD checks; fabrication review and physical testing remain pending.

Editable self-contained SVG pages and individual PDFs are in `pages/`.
Regenerate using `python3 hardware/prototype-a1/scripts/generate_brochure.py`
after the Blender render script. Design/source references are collected in the
[engineering decisions](../../../docs/hardware/prototype-a1-design.md) and the
[package index](../README.md).
