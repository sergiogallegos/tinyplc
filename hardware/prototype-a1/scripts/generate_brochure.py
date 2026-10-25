#!/usr/bin/env python3
"""An eight-page prototype brochure, using actual Blender render outputs."""
from publication import Page,ROOT,INK,MUTED,ACCENT,PALE,bundle

OUT=ROOT/'brochure';pages=[]
def save(p,name):pages.append(p.save(OUT/'pages'/name))

p=Page('',number=1)
p.image('hero-white',0,-2,297,214.5)
p.text(15,16,'tinyPLC  /  A1 PROTOTYPE',3.1,ACCENT,True)
p.text(15,35,'Small controller.',8.5,INK,True)
p.text(15,46,'Open to exploration.',8.5,INK,True)
p.para(15,58,'Structured Text. Native execution. A physical prototype you can understand and improve.',89,3.6)
p.rect(14,175,269,21,'#f6f8f8',2)
p.text(20,183,'CUSTOM STM32 PCB',3.1,ACCENT,True)
p.text(106,183,'PRINTABLE WHITE ENCLOSURE',3.1,ACCENT,True)
p.text(216,183,'VISIBLE STATUS',3.1,ACCENT,True)
p.text(20,190,'A1 routed PCB prototype',2.8,MUTED);p.text(106,190,'FreeCAD + Blender source',2.8,MUTED);p.text(216,190,'OLED + power / RUN',2.8,MUTED)
p.text(15,205,'Research prototype • render, not a built unit • Routed PCB; fabrication review and display firmware pending',2.5,MUTED)
save(p,'01-cover')

p=Page('A quieter industrial object.','DESIGN / SOFT GEOMETRY, CLEAR PURPOSE',2)
p.para(14,42,'A rounded white shell, a restrained black interface and a narrow silver seam. The prototype is designed to be pleasant on a desk and practical to open.',268,3.7)
p.image('hero-white',10,52,138,100);p.image('hero-silver',149,52,138,100)
p.text(18,155,'MATTE WHITE / PRIMARY DIRECTION',3.2,ACCENT,True)
p.text(157,155,'SILVER / FINISH STUDY',3.2,ACCENT,True)
p.para(18,165,'Printed polymer. 140 × 110 × 37 mm before feet and switch projection. Soft corners and a clean top surface.',123,3.2)
p.para(157,165,'The same geometry with a silver-colored finish. This is not a machined aluminum enclosure or grounded metal chassis.',123,3.2)
save(p,'02-design')

p=Page('Understand the state at a glance.','INTERFACE / SMALL DISPLAY, USEFUL SIGNALS',3)
p.image('status-detail',12,41,168,121.3)
p.block(191,45,92,34,'PWR','A hardware LED follows the 3.3 V rail, independently of firmware.')
p.block(191,84,92,39,'RUN','A proposed heartbeat follows accepted scan progress. A live UI task alone must not assert RUN.')
p.block(191,128,92,43,'OLED','128 × 64 monochrome status: RUN, STOP or FAULT, scan period and an I/O snapshot.')
p.para(14,179,'The screen is deliberately small and non-touch. The displayed DEMO content is a UI proposal; the A1 OLED driver and status integration still need implementation.',269,3.4)
save(p,'03-interface')

p=Page('Power is explicit. Wiring stays legible.','CONNECTIONS / LABELS THAT FOLLOW THE SCHEMATIC',4)
p.image('rear-power',11,40,178,128.6)
p.block(197,43,86,40,'24 V DC INPUT','J1.1: +24 V. J1.2: 0 V / GND (−). GND is the circuit return, not protective earth.')
p.block(197,88,86,39,'PHYSICAL ON / OFF','A maintained side rocker opens the fused positive feed to the controller and output bus.')
p.block(197,132,86,40,'FOUR IN / FOUR OUT','Four conditioned input channels and four sinking output channels. Electrical ratings remain test targets.')
p.para(14,181,'USB is a service/data connection, not the supply. The shared-ground board is not isolated. OFF is not an all-signal disconnect; remove external sources before servicing.',269,3.3)
save(p,'04-power-and-io')

p=Page('One custom board. Clear responsibilities.','HARDWARE / STM32F446 CONTROLLER ARCHITECTURE',5)
for x,title,body in [(14,'24 V INPUT','J1 → F1 → SW3 → D1'),(107,'PROTECTED BUS','V24 → TSR 1-2433'),(200,'3.3 V LOGIC','STM32 + OLED + PWR')]:
    p.block(x,46,83,30,title,body)
    if x<200:p.line(x+84,61,x+91,61,ACCENT,.8,True)
p.block(14,98,73,40,'4 INPUT CHANNELS','Resistor limits + optocouplers. Active-low raw signals; shared GND.')
p.block(108,94,81,49,'STM32F446RET6','Custom 120 × 90 mm PCB. C/FreeRTOS supervisor executes compiled ST logic. SWD and UART for bring-up.','#e2edef')
p.block(210,98,73,40,'4 SINK OUTPUTS','TPL7407L low-side driver. External resistive loads for initial tests.')
p.line(88,117,105,117,ACCENT,.8,True);p.line(191,117,208,117,ACCENT,.8,True)
p.block(14,156,83,30,'ENGINEERING','3.3 V UART first; USB integration later.')
p.block(107,156,83,30,'STATUS','I²C OLED + independent power LED.')
p.block(200,156,83,30,'EXPANSION','SPI headers; Ethernet still optional.')
p.line(148,144,148,153,ACCENT,.8,True)
p.text(14,194,'Block diagram describes the intended A1 hardware. PCB routing is complete; manufacturing release and hardware qualification remain pending.',2.6,MUTED)
save(p,'05-hardware-architecture')

p=Page('Compile on the PC. Execute on the controller.','SOFTWARE / STRUCTURED TEXT TO NATIVE ARM CODE',6)
for i,(title,body) in enumerate([('STRUCTURED TEXT','Write the control program'),('RUST FRONTEND','Parse + type-check'),('LLVM / AOT','Generate ARM code'),('PACKAGE','Validate + stage image'),('C / FREERTOS','Scan + execute + commit')]):
    x=14+i*55
    p.block(x,47,49,38,title,body)
    if i<4:p.line(x+50,66,x+54,66,ACCENT,.7,True)
p.block(14,99,128,56,'IMPLEMENTED ON THE NUCLEO BASELINE','Native execution, serial download and explicit activation; coherent monitoring; compatible state migration, trial and rollback; TON on-delay timers.')
p.block(155,99,128,56,'A1 INTEGRATION STILL TO DO','Standalone clock and pin setup, four-channel I/O validation, OLED driver and heartbeat ownership. Native USB and Ethernet are not ready-to-use A1 features.')
p.para(14,168,'The supervisor owns physical I/O and fault handling. User logic runs in a restricted native worker. The UI must consume snapshots at lower priority, with bounded I²C transactions.',269,3.5)
p.text(14,190,'Target scan period: 10 ms. Existing measured evidence is for NUCLEO-F446RE; A1 timing must be measured separately.',2.9,MUTED)
save(p,'06-software')

p=Page('The files are part of the product.','BUILD / INSPECT, PRINT, ASSEMBLE, ITERATE',7)
p.image('exploded',92,37,192,139)
p.text(14,47,'01 / INSPECT',3.6,ACCENT,True)
p.para(14,56,'KiCad schematic, custom PCB, per-item BOM and design decisions explain the electronics.',74,3.3)
p.text(14,83,'02 / PRINT + FIT',3.6,ACCENT,True)
p.para(14,92,'FreeCAD, STEP and oriented STLs provide the shell, display mount, optical sleeves and fit coupon.',74,3.3)
p.text(14,126,'03 / ASSEMBLE',3.6,ACCENT,True)
p.para(14,135,'Illustrated instructions, dimensioned drawings, label artwork and harness mappings keep the build traceable.',74,3.3)
p.para(14,181,'Every product view in this brochure comes from the editable Blender scene built from the CAD geometry. Package bodies and switch details are simplified envelopes.',269,3.3)
save(p,'07-build-files')

p=Page('A prototype with a clear next step.','READINESS / WHAT YOU CAN CONSTRUCT TODAY',8)
p.block(14,44,85,67,'READY TO EXPLORE','Inspect the custom board and schematic. Print the coupon and case for fit trials. Try the compiler, host simulation and documented Nucleo workflow. Review the proposed OLED interface.')
p.block(106,44,85,67,'BEFORE BOARD ORDER','Review the routed PCB. Resolve exact capacitor and hardware SKUs. Review power, I/O, ground returns and fabrication constraints. Inspect manufacturing outputs independently.')
p.block(198,44,85,67,'BEFORE A WORKING A1','Build and test the board in stages. Port the firmware. Integrate the OLED and status logic. Validate switch wiring, optical alignment, thermal behavior and physical outputs.')
p.image('hero-white',14,117,96,69.3)
p.text(122,131,'Start with hardware/prototype-a1/README.md',4,INK,True)
p.para(122,144,'It links the native CAD, BOM, assembly guide, construction drawings, design rationale and this brochure. A0 remains available for comparison.',159,3.4)
p.para(122,168,'Research and education only. No certified machine-control or safety use. Downloaded programs currently do not persist across reset.',159,3.2,MUTED)
p.text(122,189,'github.com/sergiogallegos/tinyplc',3.2,ACCENT,True)
save(p,'08-next-steps')
bundle(pages,OUT/'tinyplc-a1-brochure.pdf')
(OUT/'README.md').write_text('''# tinyPLC A1 prototype brochure

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
''')
print('Created 8-page prototype product brochure.')
