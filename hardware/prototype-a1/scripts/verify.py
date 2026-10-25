#!/usr/bin/env python3
"""Run the native CAD checks and independent cross-file consistency checks.

Unrouted connections are reported, never suppressed or treated as a release.
This command does not generate fabrication files or test electrical hardware.
"""
from collections import Counter
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET

import pcbnew as pcb

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
E=ROOT/"electronics"
R=ROOT/"reports"
PARTS=json.loads((ROOT/"bom"/"components.json").read_text())
P=json.loads((ROOT/"parameters.json").read_text())


def run(*args):
    p=subprocess.run(args,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,check=True)
    return p.stdout


run("kicad-cli","sch","export","pdf","-o",str(E/"tinyplc-a1-schematic.pdf"),str(E/"tinyplc-a1.kicad_sch"))
run("kicad-cli","sch","export","netlist","--format","kicadxml","-o",str(R/"netlist.xml"),str(E/"tinyplc-a1.kicad_sch"))
run("kicad-cli","sch","erc","--format","json","-o",str(R/"erc.json"),str(E/"tinyplc-a1.kicad_sch"))
run("kicad-cli","pcb","drc","--format","json","--schematic-parity","-o",str(R/"drc.json"),str(E/"tinyplc-a1.kicad_pcb"))
run("kicad-cli","pcb","export","svg","--layers","F.Cu,F.SilkS,Edge.Cuts","--page-size-mode","2","-o",str(E/"tinyplc-a1-placement.svg"),str(E/"tinyplc-a1.kicad_pcb"))
erc=json.loads((R/"erc.json").read_text())
drc=json.loads((R/"drc.json").read_text())
ev=[v for s in erc["sheets"] for v in s["violations"]]
assert not ev,ev
assert not drc["schematic_parity"],drc["schematic_parity"]
assert not [v for v in drc["violations"] if v["severity"]=="error"],drc["violations"]
assert not drc["unconnected_items"],drc["unconnected_items"]

# Check the native schematic export, not just the generator's intended records.
xml=ET.parse(R/"netlist.xml")
actual={}
for net in xml.findall("./nets/net"):
    for n in net.findall("node"):
        actual[n.attrib["ref"],n.attrib["pin"]]=net.attrib["name"]
for p in PARTS+json.loads((ROOT/"bom/external-circuits.json").read_text()):
    for pin,net in p["nets"].items():
        if net:
            assert actual[p["ref"],pin]=="/"+net,(p["ref"],pin,actual.get((p["ref"],pin)),net)
board=pcb.LoadBoard(str(E/"tinyplc-a1.kicad_pcb"))
fps={f.GetReference():f for f in board.GetFootprints()}
assert set(fps)=={p["ref"] for p in PARTS}
assert len(board.GetTracks())>0
# Independent pin contract, deliberately not copied from generator output.
expected_mcu={"14":"DI1_N","15":"DI2_N","20":"DI3_N","22":"DI4_N",
    "26":"DO1","27":"DO2","61":"DO3","62":"DO4","21":"STATUS_LED",
    "16":"UART_TX","17":"UART_RX","44":"USB_DM","45":"USB_DP",
    "46":"SWDIO","49":"SWCLK","58":"I2C_SCL","59":"I2C_SDA",
    "30":"VCAP1","13":"VDDA","7":"NRST","60":"BOOT0"}
for pin,net in expected_mcu.items():
    assert actual['U1',pin]=='/'+net,('MCU pin contract',pin,net)
for pin in ['1','19','32','48','64']: assert actual['U1',pin]=='/+3V3'
for pin in ['12','18','31','47','63']: assert actual['U1',pin]=='/GND'
for ref,pin,net in [('J1','1','VIN24'),('J1','2','GND'),('J17','1','VIN_FUSED'),
    ('J17','2','VIN_SWITCHED'),('D1','1','V24'),('D1','2','VIN_SWITCHED'),
    ('U3','8','GND'),('U3','9','V24')]:
    assert actual[ref,pin]=='/'+net,(ref,pin,net)
# Catch duplicated literal dict keys before they silently overwrite a GPIO.
import ast
source=ast.parse((ROOT/'scripts/generate_electronics.py').read_text())
for node in ast.walk(source):
    if isinstance(node,ast.Dict):
        keys=[k.value for k in node.keys if isinstance(k,ast.Constant)]
        assert len(keys)==len(set(keys)),('duplicate source dictionary keys',keys)
tracks=[t for t in board.GetTracks() if isinstance(t,pcb.PCB_TRACK) and not isinstance(t,pcb.PCB_VIA)]
vias=[t for t in board.GetTracks() if isinstance(t,pcb.PCB_VIA)]
assert min(t.GetWidth() for t in tracks)>=pcb.FromMM(.2)
assert all(t.GetWidth()>=pcb.FromMM(.8) for t in tracks if t.GetNetname() in
    ['/VIN24','/VIN_FUSED','/VIN_SWITCHED','/V24'])
assert sum(not z.GetIsRuleArea() for z in board.Zones())==2
# No repeated copper segments after the Specctra round trip.
keys=[]
for t in tracks:
    keys.append((t.GetNetname(),t.GetLayer(),tuple(sorted([
        (t.GetStart().x,t.GetStart().y),(t.GetEnd().x,t.GetEnd().y)])),t.GetWidth()))
assert len(keys)==len(set(keys)),"duplicate track segments"
c1pads={a.GetNumber():a for a in fps['C1'].Pads()}
assert abs(pcb.ToMM(c1pads['2'].GetPosition().x-c1pads['1'].GetPosition().x)-2)<.001
assert 'D5.0mm_P2.00mm' in str(fps['C1'].GetFPID().GetLibItemName())
# Fixed optical interfaces must still align with the A1 enclosure.
for ref,pos in [('D2',(39,43)),('D3',(39,47))]:
    q=fps[ref].GetPosition()
    assert (round(pcb.ToMM(q.x)-100,3),round(pcb.ToMM(q.y)-100,3))==pos
for p in PARTS:
    fp=fps[p["ref"]]
    x,y=pcb.ToMM(fp.GetPosition().x)-100,pcb.ToMM(fp.GetPosition().y)-100
    assert abs(x-p["xy"][0])<0.001 and abs(y-p["xy"][1])<0.001
    for pad in fp.Pads():
        expected=p["nets"].get(pad.GetNumber())
        if expected:
            assert pad.GetNetname()=="/"+expected
for i,xy in enumerate(P["pcb"]["holes"],1):
    fp=fps[f"H{i}"]
    assert [round(pcb.ToMM(fp.GetPosition().x)-100,3),round(pcb.ToMM(fp.GetPosition().y)-100,3)]==xy
    pad=list(fp.Pads())[0]
    assert abs(pcb.ToMM(pad.GetDrillSize().x)-3.2)<0.001

# A missing/duplicate purchasing row can produce a physically unbuildable board.
bom=list(csv.DictReader((ROOT/"bom"/"electronics.csv").open()))
required=[p for p in PARTS if not p["ref"].startswith(("H","TP"))]
assert Counter(x["ref"] for x in bom)==Counter(p["ref"] for p in required)
assert all(x["official_document"].startswith("https://") and x["purpose"] for x in bom)
mech=json.loads((R/"mechanical-checks.json").read_text())
assert all(x["valid"] and x["solid_count"]==1 for x in mech["solids"].values())
assert all(x["volume_mm3"]<0.001 for x in mech["interferences"])
assert all(mech["solids"][name]["print_mesh_closed"] for name in ["base","lid"])

for name in ["base-print.stl","lid-print.stl","fit-coupon-print.stl","tinyplc-a1.FCStd","tinyplc-a1-assembly.step"]:
    assert (ROOT/"mechanical"/name).stat().st_size>100
for name in ["01-base","02-lid-and-optics","03-pcb-fit-template","04-coupon-and-lens"]:
    assert (ROOT/"mechanical"/"drawings"/(name+".pdf")).read_bytes().startswith(b"%PDF")

counts=Counter(v["type"] for v in drc["violations"])
report={"checked_utc":datetime.now(timezone.utc).isoformat(),"kicad":pcb.GetBuildVersion(),
    "footprints":len(PARTS),"named_signal_and_power_nets":len({n for p in PARTS for n in p["nets"].values() if n}),
    "erc_violations":len(ev),"schematic_parity_issues":len(drc["schematic_parity"]),
    "drc_errors":sum(v['severity']=='error' for v in drc['violations']),
    "drc_warnings":dict(counts),"unrouted_connections":len(drc["unconnected_items"]),
    "tracks":len(tracks),"vias":len(vias),"minimum_track_width_mm":pcb.ToMM(min(t.GetWidth() for t in tracks)),
    "bom_rows":len(bom),"independent_mcu_and_power_pin_contract":"passed",
    "mechanical_checks":"valid solids, closed print meshes, zero reported intersections",
    "status":"routed prototype candidate; independent fabrication review and physical testing pending"}
(R/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
md=["# A1 routed PCB verification", "", "Generated: "+report["checked_utc"], "",
    "| Check | Result |", "| --- | --- |",f"| KiCad | {report['kicad']} |",
    f"| Footprints / BOM rows | {len(PARTS)} / {len(bom)} |",
    "| Schematic ERC / schematic-board parity | 0 / 0 |",
    f"| DRC errors / warning types | {report['drc_errors']} / {dict(counts)} |",
    "| Unrouted connections | **0** |",f"| Copper segments / vias | {len(tracks)} / {len(vias)} |",
    f"| Minimum trace width | {report['minimum_track_width_mm']} mm |",
    "| 24 V supply trace width | 0.8 mm minimum |",
    "| Ground pours | Front and back, disconnected islands removed |",
    "| Independent MCU / power pin contract | Passed |",
    "| Mechanical checks | Valid solids; closed meshes; no reported interference |",
    "", "Raw [ERC](erc.json), [DRC](drc.json), [netlist](netlist.xml), and",
    "[mechanical checks](mechanical-checks.json) are preserved. No unconnected-net",
    "or DRC exclusions are used. See [routing decisions](../../../docs/hardware/prototype-a1-routing.md)",
    "for layer rules, critical routes, reproduction and remaining review gates.", "",
    "This validates CAD connectivity and configured rules. It does not establish",
    "electrical function, USB signal quality, thermal limits, printer fit or firmware",
    "support. The prototype has not been manufactured or physically tested."]
(R/"verification.md").write_text("\n".join(md)+"\n")
# Validate relative links after the report itself exists.
docs=[ROOT/"README.md",ROOT/"mechanical"/"drawings"/"README.md"]+list((REPO/"docs"/"hardware").glob("prototype-a1-*.md"))
for path in docs:
    for target in re.findall(r"\]\(([^)]+)\)",path.read_text()):
        if not re.match(r"https?://|#",target):
            assert (path.parent/target.split("#")[0]).exists(),(path,target)
print(json.dumps(report,indent=2))
