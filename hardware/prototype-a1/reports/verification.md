# A1 routed PCB verification

Generated: 2026-10-25T00:57:40.960526+00:00

| Check | Result |
| --- | --- |
| KiCad | 10.0.7 |
| Footprints / BOM rows | 99 / 91 |
| Schematic ERC / schematic-board parity | 0 / 0 |
| DRC errors / warning types | 0 / {} |
| Unrouted connections | **0** |
| Copper segments / vias | 830 / 80 |
| Minimum trace width | 0.2 mm |
| 24 V supply trace width | 0.8 mm minimum |
| Ground pours | Front and back, disconnected islands removed |
| Independent MCU / power pin contract | Passed |
| Mechanical checks | Valid solids; closed meshes; no reported interference |

Raw [ERC](erc.json), [DRC](drc.json), [netlist](netlist.xml), and
[mechanical checks](mechanical-checks.json) are preserved. No unconnected-net
or DRC exclusions are used. See [routing decisions](../../../docs/hardware/prototype-a1-routing.md)
for layer rules, critical routes, reproduction and remaining review gates.

This validates CAD connectivity and configured rules. It does not establish
electrical function, USB signal quality, thermal limits, printer fit or firmware
support. The prototype has not been manufactured or physically tested.
