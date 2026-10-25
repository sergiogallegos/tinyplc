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


run("kicad-cli","sch","export","pdf","-o",str(E/"tinyplc-a0-schematic.pdf"),str(E/"tinyplc-a0.kicad_sch"))
run("kicad-cli","sch","export","netlist","--format","kicadxml","-o",str(R/"netlist.xml"),str(E/"tinyplc-a0.kicad_sch"))
run("kicad-cli","sch","erc","--format","json","-o",str(R/"erc.json"),str(E/"tinyplc-a0.kicad_sch"))
run("kicad-cli","pcb","drc","--format","json","--schematic-parity","-o",str(R/"drc.json"),str(E/"tinyplc-a0.kicad_pcb"))
run("kicad-cli","pcb","export","svg","--layers","F.Cu,F.SilkS,Edge.Cuts","--page-size-mode","2","-o",str(E/"tinyplc-a0-placement.svg"),str(E/"tinyplc-a0.kicad_pcb"))
erc=json.loads((R/"erc.json").read_text())
drc=json.loads((R/"drc.json").read_text())
ev=[v for s in erc["sheets"] for v in s["violations"]]
assert not ev,ev
assert not drc["schematic_parity"],drc["schematic_parity"]
assert not [v for v in drc["violations"] if v["severity"]=="error"],drc["violations"]
assert drc["unconnected_items"],"A0 must clearly preserve its unrouted state"

# Check the native schematic export, not just the generator's intended records.
xml=ET.parse(R/"netlist.xml")
actual={}
for net in xml.findall("./nets/net"):
    for n in net.findall("node"):
        actual[n.attrib["ref"],n.attrib["pin"]]=net.attrib["name"]
for p in PARTS:
    for pin,net in p["nets"].items():
        if net:
            assert actual[p["ref"],pin]=="/"+net,(p["ref"],pin,actual.get((p["ref"],pin)),net)
board=pcb.LoadBoard(str(E/"tinyplc-a0.kicad_pcb"))
fps={f.GetReference():f for f in board.GetFootprints()}
assert set(fps)=={p["ref"] for p in PARTS}
assert len(board.GetTracks())==0
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
assert all(mech["solids"][name]["print_mesh_closed"] for name in ["base","lid","display_blank"])

for name in ["base-print.stl","lid-print.stl","display-blank-print.stl","fit-coupon-print.stl","tinyplc-a0.FCStd","tinyplc-a0-assembly.step"]:
    assert (ROOT/"mechanical"/name).stat().st_size>100
for name in ["01-base","02-lid-and-blank","03-pcb-fit-template","04-print-coupon-and-stack"]:
    assert (ROOT/"mechanical"/"drawings"/(name+".pdf")).read_bytes().startswith(b"%PDF")

counts=Counter(v["type"] for v in drc["violations"])
report={"checked_utc":datetime.now(timezone.utc).isoformat(),"kicad":pcb.GetBuildVersion(),"footprints":len(PARTS),"named_signal_and_power_nets":len({n for p in PARTS for n in p["nets"].values() if n}),"erc_violations":len(ev),"schematic_parity_issues":len(drc["schematic_parity"]),"placement_drc_errors":0,"placement_drc_warnings":dict(counts),"unrouted_connections":len(drc["unconnected_items"]),"tracks":len(board.GetTracks()),"bom_rows":len(bom),"mechanical_checks":"valid solids, closed print meshes, zero reported intersections","status":"draft verified for cross-file CAD consistency only; not manufacturable or hardware tested"}
(R/"verification.json").write_text(json.dumps(report,indent=2)+"\n")
md=["# A0 CAD verification", "", "Generated: "+report["checked_utc"], "", "| Check | Result |", "| --- | --- |", f"| KiCad version | {report['kicad']} |", f"| Placed footprints | {len(PARTS)} |", f"| Named signal/power nets | {report['named_signal_and_power_nets']} |", "| Schematic ERC | 0 violations |", "| Schematic/PCB parity | 0 issues |", "| Placement DRC errors | 0 (excluding explicitly reported unrouted connections) |", f"| Placement warnings | {dict(counts)} |", f"| Unrouted connections | **{report['unrouted_connections']} — routing unfinished** |", "| Tracks | 0 |", f"| Electronic BOM | {len(bom)} individual purchased-item rows, matching CAD |", "| Mechanical geometry | Valid single solids, closed case print meshes, no reported intersections |", "| PDFs, native files and local document links | Present and checked |", "", "These checks establish CAD consistency, not electrical function or a fabrication", "release. Raw [ERC](erc.json), [DRC](drc.json), [native schematic netlist](netlist.xml)", "and [mechanical checks](mechanical-checks.json) are preserved. DRC has not been", "made clean by suppressing unconnected nets. Silk warnings remain visible for", "the next layout revision. No physical test, printer fit, thermal measurement,", "component availability approval or new-board firmware validation has occurred.", "", "Tools used for initial generation: KiCad 10.0.7, FreeCAD 1.1.4, Blender 5.2.2 LTS.", "Blender and FreeCAD were run headlessly; package geometry is approximate."]
(R/"verification.md").write_text("\n".join(md)+"\n")
# Validate relative links after the report itself exists.
docs=[ROOT/"README.md",ROOT/"mechanical"/"drawings"/"README.md"]+list((REPO/"docs"/"hardware").glob("prototype-a-*.md"))
for path in docs:
    for target in re.findall(r"\]\(([^)]+)\)",path.read_text()):
        if not re.match(r"https?://|#",target):
            assert (path.parent/target.split("#")[0]).exists(),(path,target)
print(json.dumps(report,indent=2))
