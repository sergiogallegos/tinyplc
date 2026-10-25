# A1 printing, assembly and first build

Use the [A1 visual guide](../../hardware/prototype-a1/mechanical/drawings/assembly-guide.pdf)
with the [design decisions](prototype-a1-design.md) and matching A1 BOM/CAD.
A1 now has a routed controller board that passes the configured CAD checks.
Printing and card fit checks can start now. Review the [routing decisions](prototype-a1-routing.md),
resolve remaining purchasing choices and inspect fabrication outputs before ordering.

1. Print the 54 × 32 × 2.4 mm fit coupon first. Try the actual power switch in
   its 12.90 × 19.81 mm opening; try M3 and M2 taps in the 2.5 and 1.6 mm pilots,
   and the 3 mm light rod in the 3.2 mm bore. Reject cracking, loose retention or
   binding. Measure the drawings' 100 mm scale bar before using paper templates.
2. Print the white base floor-down and the white lid outside-face-down using
   the supplied print STLs in mm. The lid's tall columns and optical sleeves
   face upward. Start with a 0.4 mm nozzle, 0.2 mm layers and multiple perimeters;
   review bridge/support paths and record the real profile. Sand or paint only
   external cosmetic surfaces; preserve mating faces and optical bores.
3. Deburr and test the empty lid. Tap the four PCB pilots and four lid-column
   pilots M3; tap the four OLED post pilots M2 after successful coupon trials.
   Cut a card controller template from drawing 03 and check mounting/port alignment.
4. With all supplies removed, snap SW3 into the left-side aperture. Identify
   terminals 1 and 1A by the actual switch marking and continuity test, and
   confirm the I position closes them. Prepare two insulated leads with proper
   4.75 × 0.8 mm female quick-connects and a suitable crimp tool. The connection
   boots and wire bending room require a physical trial.
5. After PCB review and electrical bring-up, lower the board onto
   the posts, DI row toward the four front openings. Inspect underside leads.
   Secure with four M3 × 6 screws and nominal 0.5 mm M3 washers. Tighten gently
   in opposite corners; confirm no bowing, bottoming or contact with the floor.
6. Connect J17.1 to SW3.1 and SW3.1A to J17.2. Both are positive supply paths;
   never connect either to GND. Check OFF opens the loop and ON closes it.
   Route the pair away from optical sleeves, the display and lid columns.
7. Install two clear 3 mm rods, **24.6 mm long**, through the lens pocket into
   their sleeves. Their lower ends rest on the internal ledges. Check they stay
   above the LED packages and do not press on them. Trial-fit the clear lens
   and its reverse black mask; align both clear LED spots and the screen window.
   Bond only the lens perimeter using the nominal 0.2 mm adhesive allowance.
8. With the lid upside down, place the Adafruit 326 QT module on its four
   underside posts, glass facing the viewing aperture. Use four M2 × 6 screws
   and nominal 0.5 mm washers, from the rear of the module. Do not clamp glass
   or flex cable. Compare the received board with the drawing and inspect the
   narrow post-to-glass clearance before tightening.
9. Make the display harness: J16.1 → VIN/red, J16.2 → GND/black,
   J16.3 → SCL/yellow, J16.4 → SDA/blue. The connector orders differ. Verify
   every wire by continuity, leave a short service loop and unplug before
   removing the lid. Measure 3.3 V at the cable before plugging in DS1.
10. Inspect for loose screws, cut leads and trapped wires. Check the switch
    wire boots and display cable clear the lens sleeves and columns. Seat the
    lid flush by hand, turn the unpowered enclosure over and install four
    M3 × 10 screws into the underside counterbores. Tighten diagonally. Do not
    use screws to pull a warped lid into place. Add four nominal 8 × 2 mm feet
    away from the screw heads so later service does not destroy the feet.
11. Apply the labels from the A1 label sheet. Confirm J1.1 is +24 V, J1.2 is
    0 V/GND (−); there is no PE terminal. Input contacts are DI/GND; output
    contacts are protected +24 V/Q sink, not supply input pairs. All lettering
    in the render is a separate applied label, not embossed STL geometry.
12. Record fit, screw engagement, cable paths, lens visibility and any changes.
    Only after staged board bring-up and A1 firmware integration should you
    test with the case closed. Measure temperature, power behavior and physical
    outputs, including boot, OFF/ON and reset. The displayed RUN state must
    reflect actual accepted scans. A working power light alone is not a PLC test.

## Electrical build sequence and A1 changes

The [A0 detailed procedure](prototype-a-assembly.md) remains the reference for
the common MCU, power converter, inputs, outputs, SWD, UART and USB circuits.
Use A1 component placements and nets, not the A0 manufacturing files. First
complete a routed, reviewed release and resolve purchasing placeholders.

For power-only bring-up, populate J1, F1, J17, D1, U2, C1–C3 and D3/R75. Wire
and verify SW3 before applying the current-limited 24 V source. The original
100 mA power-only limit is a starting test setting, not a final board limit.
Measure VIN24, VIN_FUSED, VIN_SWITCHED, V24 and +3V3. Switch off immediately if
the source current-limits unexpectedly. Check PWR independently of MCU firmware;
disconnect the source before adding parts. Do not jumper J17 in the final
prototype: that bypasses the requested power switch.

After logic, SWD and I/O acceptance, add DS1 separately. Verify supply polarity,
the effective I²C pull-ups and selected module address before enabling its
driver. Implement the A1 status ownership and bounded-update policy in the
design document; do not relabel the old Nucleo application LED as a working
heartbeat. Check retained power from external I/O, UART, USB or debugger sources
before treating the power switch as a convenient bench stop. It is not an
emergency-stop or safety disconnect. Applications currently need re-download
after reset; persistence remains future software work.
