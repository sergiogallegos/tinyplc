# A0 prototype printing, assembly and first power-up

This guide accompanies [A0 CAD and BOM](../../hardware/prototype-a/README.md).
For the picture-led mechanical sequence, use the [visual assembly booklet](../../hardware/prototype-a/mechanical/drawings/assembly-guide.pdf).
It shows colored parts, quantities, insertion arrows and the screw/washer/nut
stack using CAD renders. This document remains the detailed technical procedure;
its printable copy is [technical-assembly-reference.pdf](../../hardware/prototype-a/mechanical/drawings/technical-assembly-reference.pdf).
**The electronic PCB is currently unrouted and has no manufacturing release.**
You can print the case and try a card template now. Steps involving an actual
PCB describe the intended assembly procedure after routing and review; they
have not been performed. Do not order the current PCB as though it were complete.

## 1. Prepare the revision and parts

Record the hardware revision and source commit in a build log. Use the matching
KiCad project, FreeCAD file, BOM and drawing set; do not mix case and board
revisions. Read the electrical and mechanical decision documents first.

Open `bom/electronics.csv`: resolve every capacitor ordering code, check all
candidate packages, voltage/current ratings and active part identities, and
confirm the connector drawing against the actual supplier item. The optional
OLED and Ethernet module are not part of the required A0 assembly. Candidate
tools and mechanical items are in `bom/mechanical.csv`.

For later electrical assembly, prepare a magnifier/microscope, temperature
controlled iron, flux, fine solder, wick, multimeter, current-limited bench
supply, 3.3 V SWD programmer, 3.3 V UART adapter, insulated leads and a scope
or logic analyzer for timing/output checks. The LQFP64 and USB-C pads require
fine-pitch assembly skills; plan stencil/reflow or assembly help if needed.

## 2. Print the drawings and check scale

Print the four A4 PDFs from `mechanical/drawings/` at **100% / actual size**.
Check that each 100 mm scale bar measures 100 mm with a ruler. The 1:1 PCB
template is a mechanical outline, not a PCB etching image. Cut it from card,
mark the DI/Q edges and punch its four mounting holes.

## 3. Print the fit coupon

Load `fit-coupon-print.stl` in millimeters. Print it flat using the intended
printer/filament/profile. Check the 50 × 24 mm dimensions and the 3.2/3.4 mm
clearance holes. Carefully try an M3 tap in the 2.5 mm pilot and assemble the
chosen screw. Adjust the printer compensation/pilot dimension if it splits,
binds or strips. No torque specification is established.

## 4. Print the base, lid and blank

Use `base-print.stl`, `lid-print.stl` and `display-blank-print.stl`. Their print
orientations are already applied. The base floor faces the bed; lid outside
face faces the bed; blank is flat. Use the material guidance and initial slicer
assumptions in the mechanical design document. Review support and bridge paths
around every terminal opening. Save the actual slicer profile and measurements.

Remove supports, strings and brim. Deburr openings without enlarging load-bearing
features arbitrarily. Check for delamination, warped floor, blocked pilots and
sharp edges. Test the empty lid fit; it should sit flat without being pulled
into place by screws. The 0.3 mm lip clearance is a starting assumption.

## 5. Fit the card PCB and blank

Lay the card template on the four posts, DI edge toward the four DI openings.
Check hole alignment, terminal positions and the USB opening. For a useful
height test, tape card blocks representing the 13.8 mm terminals above the
template and fit the lid. This is a mechanical experiment, not electrical proof.

Fit the blank over the lid opening using two M2.5 × 8 screws, washers and nuts.
Keep nuts clear of the future board and wiring. The blank covers the display
opening; there is no display-specific bracket to assemble yet.

## 6. Finish the electronics release before PCB assembly

Review exact footprints and pin numbering, input/output behavior, clock/power
design and the BOM. Complete routing and ground return design, set rules from
the selected fabricator, and resolve DRC errors including all unrouted nets.
Inspect Gerbers, drills, assembly orientation and electrical-to-mechanical
consistency independently. Record the release revision. Only this reviewed
future package should be ordered. Current A0 is not that package.

## 7. Inspect a received bare PCB

Confirm revision, outline, thickness, holes, connector pitches and package pads
against drawings and actual components. Inspect for shorts, damaged pads and
fabrication defects. Measure ground-to-V24 and ground-to-3V3 resistance and
record readings. Capacitors may charge during resistance checks; do not use
an unexplained continuity beep as the sole acceptance criterion.

## 8. Assemble and test the power section first

Populate J1, F1, D1, U2 and C1–C3, leaving MCU and field drivers unpopulated
where practical. On D1 the cathode faces V24; C1 positive faces V24 and negative
faces GND. Check U2 orientation: pin 1 VIN, 2 GND, 3 VOUT. Inspect every joint.

With power off, check for shorts. Connect the bench source with correct
polarity, initially set to 24 V and a 100 mA limit for the power-only test.
If the source current-limits unexpectedly, switch off and investigate rather
than raising the limit. Measure J1, protected V24 and regulated 3V3 at test
pads. Confirm the regulator datasheet's acceptable output range before loading.
Record no-load input current and temperatures. Do not perform a destructive
reverse-polarity or surge test on the first assembly.

## 9. Assemble the logic section

Remove power. Populate small MCU passives, Y1 and C13/C14, U1, reset/button
parts, status LED and debug/UART headers. Match U1 pin 1 to the footprint mark;
use the selected package's pin-1 dot and datasheet top view. C8 belongs only
between VCAP1 and GND. Verify LED cathode orientation. No BOOT shunt is fitted
for normal operation. Inspect fine-pitch pins for bridges and unsoldered leads.

Apply current-limited power, allowing for the populated logic load after
checking the power budget. Check 3V3, VDDA and VCAP against ST's permitted
conditions. Verify NRST releases high and BOOT0 stays low.

## 10. Connect SWD and establish minimal firmware

Power the target from its bench supply. Connect the programmer's target voltage
reference to J3 pin 1, ground to pin 2, SWDIO to pin 3, SWCLK to pin 4 and NRST
to pin 5. J3 pin 6 is NC. This custom pinout requires a deliberate cable mapping.
Avoid enabling programmer target power at the same time.

Identify the actual MCU, test reset/connect-under-reset and flash a dedicated
minimal board build. Configure the local crystal correctly; the Nucleo's
external ST-LINK clock path is absent. Verify PA5 LED and PC13 button, clocks
and watchdog before introducing native ST execution. A tinyPLC A0 firmware
port does not yet exist; do not treat the existing Nucleo binary as accepted.

## 11. Fit and test one input at a time

Power off and populate R10–R12, U4, D11 and C21. U4 pin 1 is LED anode, pin 2
cathode, pin 3 emitter and pin 4 collector. D11 cathode connects to the LED
anode; it is intentionally opposite the internal LED. Confirm the actual
VO617A-3 package matches this mapping.

Power the board and use a separately current-limited input signal. With input
off, PA0 should be high. At nominal 24 V between J5 pin 1 and GND pin 2, measure
input current (about 5.2 mA calculated) and a low PA0 level. Sweep input levels
within the proposed bench range to record actual switching thresholds; check
release delay and repeated transitions. Add DI2–DI4 and repeat. Logical ST
inputs must invert the raw `_N` signals in the new board port.

## 12. Fit and test one output at a time

Remove power. Populate U3, C30, R51–R54 and J9–J12. Check U3 pin 1, pin 8 GND
and pin 9 COM/V24. Keep unused driver inputs grounded. Firmware must drive
commands low by default.

Connect a 4.7 kΩ resistor of at least 0.25 W between J9 pin 1 and J9 pin 2.
At 24 V this dissipates about 0.123 W and draws about 5.1 mA. Limit the bench
source current appropriately. Command Q1 on/off and measure voltage across
the load; check for off-state leakage and unexpected boot/reset pulses. Repeat
for each output. Then test all four simultaneously. Increase load only within
reviewed limits and after measuring package/supply temperatures. Initial
50 mA/channel is an unverified test target. Do not short the outputs.

## 13. Add USB and optional peripherals separately

Remove power before fitting J13, U8, R60–R65 and C31. Inspect USB-C solder joints
and verify VBUS is not shorted to 3V3/V24. Using a host cable, measure VBUS sense
and confirm power sequencing/unpowered injection before implementing native
USB. There is no working USB CDC firmware supplied by this prototype change.

For the existing engineering protocol, use J4: pin 1 GND; pin 2 board TX to
adapter RX; pin 3 board RX from adapter TX. Use 3.3 V UART levels. Leave the
adapter's power output disconnected. Optional Ethernet/display require
separate module-to-header wiring tables and firmware before connection.

## 14. Mount the tested board in the base

Power off and remove external cables. Trim/inspect underside leads. Tap the
four 2.5 mm PCB support pilots as validated on the coupon. Place the board on
the posts with DI edge correctly oriented, and install four M3 × 6 screws
with nominal 0.5 mm washers. Verify engagement and that screw tips do not
bottom out. Tighten gently by hand, diagonally, until seated. Check that the
board remains flat and no lead touches the floor or screw towers.

## 15. Route and identify the wiring

Pass wires through their matching openings without tension on terminals.
Strip and terminate wires according to the actual terminal manufacturer's
instructions. Label DI1–DI4, Q1–Q4, supply polarity and shared GND. Verify every
connection against the schematic. Check access to terminal screws with lid
removed and clearance for USB cable overmolds. Provide external cable strain
relief for the bench experiment; no internal cable clamp is included in A0.

## 16. Close the enclosure

Inspect for loose solder, clipped leads and tools. Keep wires away from the
lid lip and blank nuts. Seat the lid before installing four candidate M3 × 8
screws. Verify screw head/counterbore fit and the roughly 6.6 mm thread
engagement; do not force screws to flatten a warped lid. The rendered text is
not embossed into the print: apply printed labels separately.

## 17. Run the complete experiment and record changes

After the new board port is implemented and individually verified, compile,
download, activate and monitor an input-to-output example using the UART
engineering connection. Verify inversion and pin bindings at the physical
terminals. Use a TON delay once the basic path passes.

Measure scan timing, power draw and closed-case temperatures with all intended
loads and communication/display traffic. Test reset, power-off, communication
loss and contained program faults, checking physical output behavior. Record
that the current runtime loses downloaded applications on reset.

For each finding, log the symptom, measurement, affected schematic reference or
case feature, proposed correction and required retest. Revise editable source,
then regenerate matching drawings, BOM and print files under a new revision.
Keep A0 artifacts as evidence instead of silently calling changed files A0.
