# tinyPLC A1 — product design and engineering decisions

A1 develops the original A0 draft into a coherent desktop research controller.
The direction requested by the user is restrained, clean and approachable:
matte white, a small black status panel and a narrow silver accent. This is an
original tinyPLC design; there is no Apple logo, affiliation or certification.
The [A1 package](../../hardware/prototype-a1/README.md) preserves A0 unchanged.

The PCB is now routed. [Routing decisions](prototype-a1-routing.md) document
the corrected DI1 pin, added VBAT bypass, revised local placement, copper rules
and native CAD checks. Exterior dimensions and optical interfaces are preserved.

## Product shape and service access

The white polymer shell is 140 × 110 × 37 mm, excluding the 2 mm adhesive feet
and the side switch projection. A 7 mm plan corner radius softens the silhouette;
the lid has a real 0.7 mm top-edge fillet. Wall/floor thickness is 2.4 mm. The
larger envelope provides room around the unchanged 120 × 90 mm controller board
for the switch, wiring and concealed fasteners. Matte white PETG is a proposed
print material, not a qualified thermal or flame rating. The silver variant in
the brochure is a polymer finish study, not an aluminum chassis. A narrow
silver painted seam is cosmetic; it has no electrical grounding role.

Four underside M3 × 10 screws engage blind columns molded into the lid at
(7,7), (133,7), (7,103), (133,103) mm. This removes exposed screws from the top
while retaining screwdriver service access. The PCB remains secured separately
with four M3 × 6 screws and nominal 0.5 mm washers. Board support positions are
(15,15), (125,15), (15,95), (125,95), with the PCB underside at Z=8. All pilots
must be tried on the coupon before tapping. No torque or repeated-cycle life
is qualified. Large lid columns print upright when the outside face is down.

The terminal ports remain accessible for bench wiring, with screw access after
lid removal. Recessed terminals reduce visual clutter, at the cost of less
finger access and more demanding wire insertion. There is no internal strain
relief, DIN clip, ingress rating or selected Ethernet module. Use external wire
restraint and inspect the actual cable bend space. The lower right-side opening
is a service port for the recessed USB connector; USB does not power this board.

## Supply labels and the physical power switch

J1 pin 1 is **+24 V DC input** (`VIN24`). J1 pin 2 is **0 V / GND (−)**, the
shared circuit return. Printed polarity is tied to physical pad coordinates,
not inferred from the viewing direction of a render. The enclosure has no
protective-earth terminal: **GND here is not PE**. The board is not galvanically
isolated; inputs, outputs, display and logic share this return.

The user explicitly selected a physical ON/OFF switch. The candidate SW3 is
**C&K D102J12S215HQA**, maintained SPST, black snap-in body, 4.75 mm quick-connect
terminals, I/O marking. The current [manufacturer D-series datasheet](https://www.ckswitches.com/media/1439/d.pdf)
lists D102 at 4 A, 30 V DC resistive; this is a switch rating, not a controller
output rating. Confirm the exact ordering code and stock before purchase.

Power flows J1+ → F1 → J17 pin 1 → SW3 terminal 1 → SW3 terminal 1A → J17 pin 2
→ D1 → V24 → U2 / output-load supply. Both J17 pins are positive-side power
conductors; **neither is GND**. The two leads need insulated 4.75 × 0.8 mm female
quick-connect receptacles matched to the actual wire, terminal and crimp tool.
No bare push-on terminals should be left near the PCB. Switching the fused
positive feed removes controller and output-bus power; the supply terminal and
fuse input remain live. OFF is not a disconnect for all external signals.
Disconnect power and external signal cables before opening the enclosure.

The 12.90 × 19.81 mm cutout follows the S2 panel drawing for 2.01–3.00 mm wall
thickness; the case wall is 2.4 mm. It is on the left face, centered at Y=49,
Z=22. The CAD uses a 20.45 mm internal switch envelope including terminals.
Connector boots and wire bends still require a physical fit trial. Check which
marked actuator position closes terminals 1–1A before attaching the leads.

## Visible power and RUN indicators

D3 is a new green [Kingbright KP-2012SGC](https://www.kingbrightusa.com/images/catalog/SPEC/KP-2012SGC.pdf)
LED fed directly from +3V3 through R75 (1 kΩ), independent of software. At an
assumed 2.2 V forward drop the current is approximately 1.1 mA, with about
1.21 mW resistor dissipation. This indicates presence of the regulated rail,
not a precision power-good threshold or successful execution. It goes dark
after the rail discharges; an unlit LED alone is not proof of zero voltage.

D2/R6 retain the PA5 LED circuit and become the proposed RUN heartbeat.
The two LEDs move to board coordinates (39,47) and (39,43), below the status
panel. R75 is at (35,47); R6 moves to (35,43). The future A1 firmware must reserve
PA5 for supervisor status; the old Nucleo example binds PA5 as the application
LED, so it must not be reused unchanged.

Two 3 mm clear acrylic rods, nominal length **24.6 mm**, carry light to the lid.
They sit from Z=11.2 to 35.8, leaving a nominal 0.6 mm clearance above the LED
package envelope. Opaque integral sleeves limit light spill; small bottom
ledges retain the rods. The lens captures their tops. Do not use opaque white
filament for these optical parts. Polish cut faces, test brightness and tune
length before closing; the guide geometry is not an optical performance result.

## Display selection and retention

DS1 is the **STEMMA QT revision of Adafruit 326**, a small monochrome SSD1306
128 × 64 OLED. [Official product documentation](https://www.adafruit.com/product/326)
describes I²C, auto-reset, 3 V/5 V operation and a selectable 0x3C/0x3D address.
Use the 3.3 V rail here. The old non-QT module has different mechanical and
configuration details and must not be substituted without checking the mount.

The [official board CAD](https://github.com/adafruit/Adafruit-128x64-Monochrome-OLED-PCB/blob/master/Adafruit%200.96in%20128x64%20OLED%20STEMMA%20QT.brd)
was inspected directly. Its full outline, including mounting tabs, is
29.21 × 31.75 mm, not the shorter height in the web listing. Hole centers are
(2.54,2.54), (26.67,2.54), (2.54,29.21), (26.67,29.21), each 2.5 mm drill.
The CAD active-area rectangle is 21.744 × 10.864 mm. A source URL, SHA-256 and
extraction note are recorded in `sources/oled-reference.json`.

The module board origin is (58.395,35.599,27) mm in the case. Four integral
4 mm-diameter posts contact its front PCB surface at Z=28.6; M2 × 6 screws with
0.5 mm washers insert from the underside. The 1.6 mm pilots must be tapped M2
on a coupon first. These narrow posts leave only about 0.28 mm nominal clearance
to the conservative glass envelope; inspect the received module before printing
the full lid. Do not clamp the glass or flex cable. The module glass is modeled
to Z=33.2; the lid underside is Z=34, giving 0.8 mm nominal clearance.

A 64 × 32 × 1 mm clear lens sits in a 64.4 × 32.4 × 1.2 mm pocket. Allow 0.2 mm
for perimeter adhesive. The supplied SVG mask is black except for the optical
window and the two LED spots. Use a clear, nonconductive sheet with a reverse
mask or a printed overlay; it is not a 3D-printed display. The screen opening
in the lid is 24.5 × 14 mm. Check optical alignment and parallax with the real
module before bonding. The module's OLED board is a purchased breakout; the
main STM32 controller PCB is custom.

## Four-wire display harness

The [manufacturer wiring guide](https://learn.adafruit.com/monochrome-oled-breakouts/wiring-128x64-oleds)
identifies the QT lead functions. A1 J16 keeps its original custom header order:

| Controller header | Net | OLED QT lead / contact |
| --- | --- | --- |
| J16.1 | +3V3 | VIN, red / 2 |
| J16.2 | GND | GND, black / 1 |
| J16.3 | PB6 / I2C_SCL | SCL, yellow / 4 |
| J16.4 | PB7 / I2C_SDA | SDA, blue / 3 |

Use a QT cable ending in female sockets for the controller's male 2.54 mm
header, or an explicitly documented adapter. Do not mate it by position alone:
the two connector orders differ. Verify continuity and voltage before plugging
in the OLED. R73/R74 remain 4.7 kΩ pull-up candidates; the module has additional
pull-ups. Confirm the effective pull-up resistance, rise time and GPIO sink
current with the exact module. Start at 100 kHz and use a short service loop.

## Status behavior and firmware boundary

Rendered screens are marked **DEMO**. They are interface proposals, not captures
from running A1 hardware. The standalone board firmware port, OLED driver and
heartbeat integration are not implemented by this design revision.

| State | Power LED | RUN LED | OLED proposal |
| --- | --- | --- | --- |
| Power removed / rail discharged | Dark | Dark | Dark |
| Boot / no active application | On | Dark | BOOT or STOP |
| Accepted scans progressing | On | 1 Hz heartbeat | RUN, scan period, I/O snapshot |
| Contained runtime fault | On | Dark | FAULT and a diagnostic code |
| Display unavailable | On if rail present | Follows supervisor | Blank; controller must continue |

The future UI should read a coherent supervisor snapshot in a low-priority
task, never block the 10 ms scan on an I²C transaction, use bounded timeouts and
limit refresh to about 2 Hz. A full 1024-byte frame takes about 92 ms at 100 kHz
before overhead; a blocking full-screen transfer in the scan task is unsuitable.
The heartbeat must depend on advancing accepted scans, not merely a live UI
task. Do not display a measured 24 V value: no input-voltage ADC circuit exists.
Dim or blank an idle OLED to reduce long-term uneven aging.

The existing Nucleo software supports ST compilation, native packages,
download/activation, monitoring, update migration/trial/rollback and TON timers.
It does not establish operation on this custom PCB. Downloaded applications
are not persistent across reset; the new physical switch therefore reinforces
the need to document reset and re-download behavior. No certified machinery
or safety use is implied by the product styling.
