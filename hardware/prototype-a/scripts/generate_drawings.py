#!/usr/bin/env python3
"""Dimensioned A4 SVG/PDF drawings, print coupon and per-item documentation."""
import csv
import html
import json
import re
from pathlib import Path
import subprocess
import sys
import tempfile
import textwrap

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/"parameters.json").read_text())
PARTS=json.loads((ROOT/"bom"/"components.json").read_text())
OUT=ROOT/"mechanical"/"drawings"
OUT.mkdir(exist_ok=True)


class Sheet:
    def __init__(self,title,number):
        self.s=['<svg xmlns="http://www.w3.org/2000/svg" width="297mm" height="210mm" viewBox="0 0 297 210">', '<style>text{font-family:DejaVu Sans,sans-serif;font-size:2.6px;fill:#152431} .line{stroke:#152431;stroke-width:.25;fill:none}.hidden{stroke:#70828d;stroke-width:.2;stroke-dasharray:1.5 1;fill:none}.dim{stroke:#405f73;stroke-width:.18;fill:none}</style>', '<rect width="297" height="210" fill="white"/>']
        self.rect(7,7,283,196)
        self.text(12,15,"tinyPLC A0 / "+title,4.5)
        self.text(12,21,"ENGINEERING DRAFT - mm - scale 1:1 at actual-size A4 printing - NOT A PCB FABRICATION RELEASE",2.4)
        self.line(7,186,290,186)
        self.text(12,193,"Rev A0 / 2026-10-24 / Sheet "+number+" / CAD fit only; physical tolerances unverified")
        self.text(12,199,"Check the scale bar. Print at 100%; disable fit-to-page. Native FreeCAD and parameters govern geometry.",2.5)
        self.line(175,196,275,196)
        self.line(175,194,175,198)
        self.line(275,194,275,198)
        self.text(215,193,"100 mm")

    def text(self,x,y,s,size=2.6):
        self.s.append(f'<text x="{x}" y="{y}" style="font-size:{size}px">{html.escape(s)}</text>')

    def rect(self,x,y,w,h,css="line",radius=0):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" class="{css}"/>')

    def line(self,x1,y1,x2,y2,css="line"):
        self.s.append(f'<path d="M {x1},{y1} L {x2},{y2}" class="{css}"/>')

    def circle(self,x,y,r,css="line"):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" class="{css}"/>')

    def hdim(self,x1,x2,y,label):
        self.line(x1,y,x2,y,"dim")
        for x in [x1,x2]:
            self.line(x,y-2,x,y+2,"dim")
        self.text((x1+x2)/2-5,y-1.5,label)

    def vdim(self,x,y1,y2,label):
        self.line(x,y1,x,y2,"dim")
        for y in [y1,y2]:
            self.line(x-2,y,x+2,y,"dim")
        self.text(x+1.5,(y1+y2)/2,label)

    def save(self,name):
        path=OUT/(name+".svg")
        path.write_text("\n".join(self.s+["</svg>"])+"\n")
        subprocess.run(["rsvg-convert","--format=pdf","--output",str(OUT/(name+".pdf")),str(path)],check=True)


s=Sheet("BASE / TOP AND SIDE VIEWS","1 of 4")
x,y=23,43
s.rect(x,y,132,102)
s.rect(x+2.4,y+2.4,127.2,97.2,"hidden")
for hx,hy in P["pcb"]["holes"]:
    s.circle(x+hx+6,y+hy+6,3.5)
    s.circle(x+hx+6,y+hy+6,1.25)
for hx,hy in [(3.5,3.5),(128.5,3.5),(3.5,98.5),(128.5,98.5)]:
    s.circle(x+hx,y+hy,3.1)
    s.circle(x+hx,y+hy,1.25)
for p in PARTS:
    if p["ref"] in [f"J{i}" for i in range(5,9)]:
        c=p["xy"][0]+6-2.54
        s.rect(x+c-6,y,12,2.4,"hidden")
    if p["ref"] in ["J1"]+[f"J{i}" for i in range(9,13)]:
        c=p["xy"][0]+6+2.54
        s.rect(x+c-6,y+99.6,12,2.4,"hidden")
s.rect(x+129.6,y+39.5,2.4,19,"hidden")
s.hdim(x,x+132,36,"132")
s.vdim(14,y,y+102,"102")
s.text(25,151,"TOP: XY datum = outside corner at left/top; Z datum = outside floor")
s.text(170,40,"SIDE / SECTION HEIGHTS",3.2)
s.rect(170,53,102,30)
s.line(170,80.6,272,80.6,"hidden")
s.line(170,75,272,75,"hidden")
s.line(170,73.4,272,73.4,"hidden")
s.vdim(279,53,83,"30")
for k,t in enumerate(["Floor: 2.4; walls: 2.4", "PCB underside Z=8; top Z=9.6", "PCB support: OD 7; pilot 2.5", "Support centers: (11,11), (121,11),", "(11,91), (121,91)", "Lid towers: OD 6.2; pilot 2.5", "Terminal windows: 12 W x 16 H", "Window bottom Z=9; top Z=25", "USB: 19 W x 10 H; bottom Z=7", "USB Y span: 39.5 to 58.5", "Pilot sizes require printer coupon."]):
    s.text(170,94+6*k,t)
s.text(23,164,"CUTOUTS: 4 DI windows on Y=0 edge; 4 Q + power windows on Y=102 edge")
s.text(23,171,"See component placement/template for terminal centers. M3 pilots are tapped, not heat-set-insert sockets.")
s.save("01-base")

s=Sheet("LID AND DISPLAY BLANK","2 of 4")
x,y=23,43
s.rect(x,y,132,102)
s.rect(x+2.7,y+2.7,126.6,96.6,"hidden")
for hx,hy in [(3.5,3.5),(128.5,3.5),(3.5,98.5),(128.5,98.5)]:
    s.circle(x+hx,y+hy,1.7)
    s.circle(x+hx,y+hy,3.1)
s.rect(x+67,y+42,30,18)
for hx in [62.5,101.5]:
    s.circle(x+hx,y+51,1.4)
s.hdim(x,x+132,36,"132")
s.vdim(14,y,y+102,"102")
s.text(26,151,"TOP VIEW. Window center: X=82, Y=51. Window: 30 x 18.")
s.text(170,43,"DISPLAY BLANK",3.2)
s.rect(173,54,46,26)
for hx in [3.5,42.5]:
    s.circle(173+hx,67,1.4)
s.hdim(173,219,49,"46")
s.hdim(176.5,215.5,87,"39 hole pitch")
s.vdim(225,54,80,"26")
for k,t in enumerate(["Lid plate: 2.4 thick", "Locating lip: 1.8 below lid", "Lip outer: 126.6 x 96.6", "Lip wall: 1.6 nominal", "Lip clearance: 0.3 per side", "4 holes: dia 3.4 through", "Counterbores: dia 6.2 x 1 deep", "Blank: 2 thick, 2 holes dia 2.8", "2 lid/blank holes: dia 2.8", "Blank fasteners: M2.5 x 8 + nuts"]):
    s.text(170,99+6*k,t)
s.text(23,165,"Lid screw centers: (3.5,3.5), (128.5,3.5), (3.5,98.5), (128.5,98.5). M3 x 8 candidate screws.")
s.text(23,172,"Display blank is a cover; no OLED bracket is defined. Lip has local tower clearances; inspect STEP/FreeCAD.")
s.save("02-lid-and-blank")

s=Sheet("PCB FIT TEMPLATE / COMPONENT PLACEMENT","3 of 4")
x,y=25,47
s.rect(x,y,120,90)
for hx,hy in P["pcb"]["holes"]:
    s.circle(x+hx,y+hy,1.6)
    s.line(x+hx-3,y+hy,x+hx+3,y+hy,"dim")
    s.line(x+hx,y+hy-3,x+hx,y+hy+3,"dim")
for p in PARTS:
    px,py=p["xy"]
    if p["ref"] in ["J1"]+[f"J{i}" for i in range(5,13)]:
        center=px+(-2.54 if p["angle"]==180 else 2.54)
        s.rect(x+center-5.1,y+py-5.2,10.2,9.8)
        s.text(x+center-3.4,y+py+0.9,p["ref"],2.3)
    elif p["ref"]=="U1":
        s.rect(x+px-5,y+py-5,10,10)
        s.text(x+px-3,y+py+1,"U1")
    elif p["ref"]=="J13":
        s.rect(x+px-3.7,y+py-4.6,7.4,9.2)
        s.text(x+px-10,y+py-7,"USB")
s.hdim(x,x+120,40,"120")
s.vdim(15,y,y+90,"90")
s.hdim(x+5,x+115,145,"110 hole pitch")
s.vdim(153,y+5,y+85,"80")
for k,t in enumerate(["Board: 120 x 90 x 1.6", "Mounting holes: 4 x dia 3.2 NPTH", "Centers relative to board datum:", "(5,5), (115,5), (5,85), (115,85)", "DI edge = Y=0 (top of this view)", "Q/power edge = Y=90 (bottom)", "J5 DI1 / J6 DI2 / J7 DI3 / J8 DI4", "J9 Q1 / J10 Q2 / J11 Q3 / J12 Q4", "J1 power / J13 USB-C", "Board-to-case offset: +6,+6", "Template can be cut from card.", "THIS IS NOT A COPPER/PAD ARTWORK."]):
    s.text(170,47+7*k,t)
s.text(25,163,"TOP VIEW - label side up. A0 footprint placements are provisional; use KiCad for all pads and pin numbers.")
s.text(25,171,"The mounting-hole and terminal envelope template is for mechanical fit only. The electronic PCB is unrouted.")
s.save("03-pcb-fit-template")

s=Sheet("PRINT COUPON AND ASSEMBLY STACK","4 of 4")
s.rect(25,47,50,24)
for hx,r,label in [(32,1.25,"2.5 pilot"),(49,1.6,"3.2"),(66,1.7,"3.4")]:
    s.circle(hx,59,r)
    s.text(hx-4,78,label)
s.text(25,40,"50 x 24 x 5 test coupon",3.2)
s.text(25,88,"Tap pilot and try actual screws before the full print.")
s.text(25,95,"Measure hole size, elephant foot, layer bonding and flatness.")
for k,t in enumerate(["STACK / assembled Z coordinates:", "0.0  outside base bottom", "2.4  inside floor", "8.0  PCB underside", "9.6  PCB component side", "23.4 terminal top (nominal envelope)", "28.2 underside of lid locating lip", "30.0 lid underside / tower top", "32.4 lid outside face", "34.4 blank outside face", "Screw heads may project further."]):
    s.text(173,40+8*k,t,3 if k==0 else 2.6)
s.text(25,120,"PRINT ORIENTATION",3.2)
for k,t in enumerate(["base-print.stl: floor down, open side up", "lid-print.stl: outside face down, lip up", "display-blank-print.stl: flat", "fit-coupon-print.stl: flat", "Import STL units as mm; do not rescale.", "0.4 nozzle / 0.2 layer is a starting proposal.", "Check bridges/supports in the slicer first.", "Material and settings are not physically qualified."]):
    s.text(25,129+6*k,t)
s.save("04-print-coupon-and-stack")

# Bundle the dimensioned sheets, keeping every original page at its true size.
subprocess.run(["pdfunite"]+[str(OUT/(n+".pdf")) for n in ["01-base","02-lid-and-blank","03-pcb-fit-template","04-print-coupon-and-stack"]]+[str(OUT/"tinyplc-a0-drawings.pdf")],check=True)

# A printable guide derived from the repository Markdown; no browser/network needed.
guide=ROOT.parents[1]/"docs"/"hardware"/"prototype-a-assembly.md"
paragraphs=guide.read_text().split("\n\n")
pages=[]
current=[]
used=0
for para in paragraphs:
    text=" ".join(para.splitlines())
    text=re.sub(r"\[([^\]]+)\]\([^)]+\)",r"\1",text)
    text=text.replace("**","").replace("`","")
    heading=text.startswith("#")
    text=text.lstrip("# ") if heading else text
    lines=textwrap.wrap(text,width=87 if heading else 104)
    height=len(lines)*4.6+(4.5 if heading else 3)
    if used+height>245 and current:
        pages.append(current)
        current=[]
        used=0
    current.append((used,lines,heading))
    used+=height
if current:
    pages.append(current)
with tempfile.TemporaryDirectory(prefix="tinyplc-guide-") as tmp:
    pdfs=[]
    for index,paragraphs in enumerate(pages,1):
        svg=['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">','<rect width="210" height="297" fill="white"/>','<style>text{font-family:DejaVu Sans,sans-serif;fill:#152431}</style>',f'<text x="15" y="12" font-size="2.7">tinyPLC A0 / ASSEMBLY GUIDE / draft, not a fabrication release / page {index} of {len(pages)}</text>']
        for yy,lines,heading in paragraphs:
            for j,line in enumerate(lines):
                svg.append(f'<text x="15" y="{24+yy+j*4.6}" font-size="{3.5 if heading else 2.9}" font-weight="{"bold" if heading else "normal"}">{html.escape(line)}</text>')
        svg.append('<text x="15" y="286" font-size="2.5">Source: docs/hardware/prototype-a-assembly.md; refer to CAD, BOM and official component links.</text></svg>')
        src=Path(tmp)/f"page-{index:02}.svg"
        src.write_text("\n".join(svg))
        pdf=src.with_suffix(".pdf")
        subprocess.run(["rsvg-convert","--format=pdf","--output",str(pdf),str(src)],check=True)
        pdfs.append(str(pdf))
    subprocess.run(["pdfunite"]+pdfs+[str(OUT/"technical-assembly-reference.pdf")],check=True)

# A simple closed calibration coupon, using native FreeCAD geometry.
sys.path.append("/usr/lib/freecad/lib")
import FreeCAD as App
import Part
import MeshPart
shape=Part.makeBox(50,24,5)
for x,r in [(7,1.25),(24,1.6),(41,1.7)]:
    shape=shape.cut(Part.makeCylinder(r,7,App.Vector(x,12,-1)))
mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=0.04,AngularDeflection=0.15,Relative=False)
assert mesh.isSolid()
mesh.write(str(ROOT/"mechanical"/"fit-coupon-print.stl"))

# Each reference has its own explanation and official documentation link.
lines=["# A0 component-by-component register", "", "Generated from the same component records as the KiCad draft and BOM.", "Every row identifies an individual item, its function and an official source.", "Candidate MPNs require a final package/availability review. Capacitors list a", "required specification and an official manufacturer family reference while", "their exact ordering codes remain open. A family page is not an exact-part", "approval. See the [circuit explanation](prototype-a-electronics.md) for", "calculations, limits and interactions between these items.", ""]
for g in dict.fromkeys(p["group"] for p in PARTS):
    lines += ["## "+g,"", "| Reference | Value / candidate part | What it does and why it is present | Official reference |", "| --- | --- | --- | --- |"]
    for p in PARTS:
        if p["group"]==g:
            value=p["value"]+"; "+p["mpn"]
            lines.append(f'| {p["ref"]} | {value} | {p["purpose"]} | [Manufacturer / design reference]({p["official_document"]}) |')
    lines.append("")
(ROOT.parents[1]/"docs"/"hardware"/"prototype-a-components.md").write_text("\n".join(lines)+"\n")
print("Created 4 dimensioned SVG/PDF drawings, a print coupon and the component register.")
