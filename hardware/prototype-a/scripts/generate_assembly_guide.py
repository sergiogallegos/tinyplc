#!/usr/bin/env python3
"""Build a visual A4 assembly booklet from CAD-derived Blender illustrations.

Run render_assembly.py first. SVG pages retain embedded images and editable
vector text/arrows; PDFs are generated with rsvg-convert and pdfunite.
The detailed electrical procedures remain in technical-assembly-reference.pdf.
"""
import base64
import html
import json
from pathlib import Path
import subprocess
import textwrap

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "renders" / "assembly"
OUT = ROOT / "mechanical" / "drawings"
PAGES = OUT / "assembly-pages"
PAGES.mkdir(exist_ok=True)
META = json.loads((IMAGES / "projections.json").read_text())
INK = "#172f46"
BLUE = "#146bcc"
ORANGE = "#ea682b"
TEAL = "#117e77"
FILES = []


class Page:
    def __init__(self, title, tag="CASE FIT / CAN BE TRIED NOW", step=None):
        self.num = len(FILES)+1
        self.s = ['<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="297mm" height="210mm" viewBox="0 0 297 210">',
                  '<defs><marker id="arrow" markerWidth="7" markerHeight="7" refX="5" refY="3.5" orient="auto"><path d="M0,0 L6,3.5 L0,7 Z" fill="#146bcc"/></marker></defs>',
                  '<rect width="297" height="210" fill="white"/>',
                  '<style>text{font-family:DejaVu Sans,sans-serif;fill:#172f46} .bold{font-weight:bold}</style>']
        self.rect(0,0,297,3,BLUE)
        self.text(12,12,"tinyPLC  /  A0 VISUAL ASSEMBLY",3,BLUE,True)
        self.text(165,12,tag,2.65,TEAL if "NOW" in tag else ORANGE,True)
        if step is not None:
            self.circle(17,25,6,BLUE)
            self.text(17,27,str(step).zfill(2),4,"white",True,"middle")
        self.text(29 if step is not None else 12,28,title,6,INK,True)
        self.line(12,199,285,199,"#dae3eb",0.3)
        self.text(12,204,"A0 • CAD illustrations, not assembly photos • physical fit untested • images not to scale",2.4,"#52677b")
        self.text(285,204,f"{self.num:02d}",3,INK,True,"end")

    def text(self,x,y,body,size=3.3,color=INK,bold=False,anchor="start"):
        self.s.append(f'<text x="{x}" y="{y}" font-size="{size}" style="fill:{color}" font-weight="{"bold" if bold else "normal"}" text-anchor="{anchor}">{html.escape(body)}</text>')

    def paragraph(self,x,y,body,width=65,size=3.2,color=INK,bold=False):
        lines = textwrap.wrap(body,width=max(12,int(width/(size*0.53))))
        for i,line in enumerate(lines):
            self.text(x,y+i*size*1.5,line,size,color,bold)
        return y+len(lines)*size*1.5

    def rect(self,x,y,w,h,color,rx=0):
        self.s.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{color}" rx="{rx}"/>')

    def circle(self,x,y,r,color):
        self.s.append(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{color}"/>')

    def line(self,x1,y1,x2,y2,color=BLUE,width=0.7,arrow=False):
        self.s.append(f'<path d="M{x1},{y1} L{x2},{y2}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linecap="round" {"marker-end="+chr(34)+"url(#arrow)"+chr(34) if arrow else ""}/>')

    def image(self,name,x,y,w,h):
        data = base64.b64encode((IMAGES/(name+".png")).read_bytes()).decode()
        self.s.append(f'<image x="{x}" y="{y}" width="{w}" height="{h}" xlink:href="data:image/png;base64,{data}"/>')

    def main(self,name,callouts=False):
        x,y,w,h = 85,43,202,151.5
        self.image(name,x,y,w,h)
        for a,b in META[name]["arrows"]:
            self.line(x+w*a[0],y+h*a[1],x+w*b[0],y+h*b[1],"white",2.2)
            self.line(x+w*a[0],y+h*a[1],x+w*b[0],y+h*b[1],BLUE,0.85,True)
        if callouts:
            for i,(label,p) in enumerate(META[name]["points"].items()):
                xx,yy=x+w*p[0],y+h*p[1]
                self.circle(xx,yy,3.3,"white")
                self.circle(xx,yy,2.7,BLUE)
                self.text(xx,yy+1.05,label if label.isdigit() else chr(65+i),2.8,"white",True,"middle")

    def panel(self,label="ADD THESE PARTS"):
        self.rect(12,47,66,126,"#f1f6fa",3)
        self.text(17,56,label,2.8,BLUE,True)

    def check(self,body):
        self.rect(12,178,66,17,"#e8f5ef",2)
        self.text(16,184,"CHECK",2.5,TEAL,True)
        self.paragraph(16,189,body,58,2.65)

    def hardware(self,kind,x,y,label,qty=1):
        if kind=="screw":
            self.rect(x+8,y+8,3,15,"#e7ad27")
            for n in range(5): self.line(x+8,y+10+n*2.5,x+11,y+8+n*2.5,"#aa791b",0.45)
            self.rect(x+5,y+5,9,4,"#f2bb3f",1.2)
            self.line(x+7,y+6.2,x+12,y+6.2,INK,0.5)
        elif kind=="washer":
            self.circle(x+10,y+13,6,"#e7ad27")
            self.circle(x+10,y+13,3,"#f1f6fa")
        else:
            self.s.append(f'<path d="M{x+4},{y+9} L{x+10},{y+6} L{x+16},{y+9} L{x+16},{y+16} L{x+10},{y+19} L{x+4},{y+16} Z" fill="#e7ad27"/>')
            self.circle(x+10,y+12.5,2.5,"#f1f6fa")
        self.text(x+22,y+12,f"{qty} ×",4,INK,True)
        self.text(x+22,y+18,label,3)

    def save(self,slug):
        self.s.append("</svg>")
        path = PAGES/f"{self.num:02d}-{slug}.svg"
        path.write_text("\n".join(self.s)+"\n")
        pdf = path.with_suffix(".pdf")
        subprocess.run(["rsvg-convert","--format=pdf","--output",str(pdf),str(path)],check=True)
        FILES.append(pdf)


p=Page("Build it. See every step.","PROTOTYPE / ILLUSTRATED MECHANICAL GUIDE")
p.text(12,49,"YOUR FIRST",6,BLUE,True)
p.text(12,60,"tinyPLC CASE",8,INK,True)
p.paragraph(12,74,"A picture-led guide to printing, checking and assembling the A0 enclosure.",80,4)
p.image("00-overview",104,33,180,135)
p.rect(12,107,78,50,"#edf5fc",3)
p.text(17,116,"PRINT + FIT NOW",3,TEAL,True)
p.paragraph(17,123,"Start with the coupon, printed case and card board template.",67,3.2)
p.text(17,140,"PCB INSTALLATION LATER",3,ORANGE,True)
p.paragraph(17,147,"The A0 PCB is unrouted. Board steps show the intended future assembly.",67,3)
p.paragraph(12,171,"Blue base • pale lid • orange blank • green PCB • yellow hardware",268,3.5,bold=True)
p.paragraph(12,183,"Colors identify parts. Hardware and electronic packages are simplified; screws are candidate sizes. Keep the detailed electrical procedure beside this booklet.",270,3)
p.save("cover")

p=Page("Lay out the large parts", "INVENTORY / MATCH THE A0 REVISION")
cards=[("part-base","A  BASE","1 × base-print.stl","Blue shell; integral PCB posts."),
       ("part-lid","B  LID","1 × lid-print.stl","Pale lid; locating lip underneath."),
       ("part-blank","C  DISPLAY BLANK","1 × display-blank-print.stl","Orange cover; no display installed."),
       ("part-template","D  CARD TEMPLATE","1 × drawing 03 at 100%","Use this for the first case fit."),
       ("part-board","E  FUTURE PCB","1 × reviewed, tested board","Shown for planning; not ready to order."),
       ("01-coupon","F  FIT COUPON","1 × fit-coupon-print.stl","Check printer and pilot holes first.")]
for i,(img,title,qty,note) in enumerate(cards):
    x=12+(i%3)*93; y=40+(i//3)*78
    p.rect(x,y,87,73,"#f1f6fa",3)
    p.text(x+4,y+8,title,3,BLUE,True)
    p.image(img,x+9,y+8,68,43)
    p.text(x+4,y+56,qty,2.9,INK,True)
    p.paragraph(x+4,y+63,note,79,2.8)
p.save("large-parts")

p=Page("Sort the screws before you start", "INVENTORY / NOMINAL HARDWARE")
hardware=[("screw","M3 × 6",4,"PCB mounting","With 4 M3 washers, about 0.5 mm thick."),
          ("screw","M3 × 8",4,"Lid mounting","Head diameter at most 6 mm."),
          ("screw","M2.5 × 8",2,"Display blank","Pass through blank and lid."),
          ("washer","M3",4,"Under PCB screw heads","Seat on the board, not below it."),
          ("washer","M2.5",2,"Under the lid","Between lid underside and blank nuts."),
          ("nut","M2.5",2,"Display blank retention","Hold while tightening the two screws.")]
for i,(kind,label,qty,title,note) in enumerate(hardware):
    x=12+(i%3)*93; y=41+(i//3)*66
    p.rect(x,y,87,61,"#f1f6fa",3)
    p.hardware(kind,x+5,y+1,label,qty)
    p.text(x+5,y+33,title,3.2,INK,True)
    p.paragraph(x+5,y+41,note,77,3)
p.paragraph(12,181,"Tools: ruler, deburring tool, M3 × 0.5 hand tap, suitable hand screwdriver and a small nut driver. Confirm actual screw drawings and fit on the coupon; no tightening torque is qualified.",270,3.2)
p.save("hardware")

p=Page("Prove the fit on the small coupon",step=1)
p.panel("USE FIRST")
p.image("01-coupon",15,60,60,45)
p.text(17,111,"1 × fit coupon",3.7,INK,True)
p.paragraph(17,120,"Print before the full case. Check the 50 × 24 mm outline with a ruler.",56,3.2)
p.paragraph(17,145,"A: 2.5 mm pilot — try M3 tap. B: 3.2 mm clearance. C: 3.4 mm clearance.",56,3.1)
p.main("01-coupon",True)
p.check("No splitting, binding or stripping.")
p.save("coupon")

p=Page("Print with the right face on the bed",step=2)
for i,(img,title,filename,note) in enumerate([
    ("part-base","BASE: FLOOR DOWN","base-print.stl","Open cavity faces up."),
    ("part-lid","LID: OUTSIDE FACE DOWN","lid-print.stl","Locating lip faces up."),
    ("part-blank","BLANK: FLAT","display-blank-print.stl","Both mounting holes remain clear.")]):
    x=12+i*93
    p.rect(x,44,87,117,"#f1f6fa",3)
    p.text(x+4,54,title,3,BLUE,True)
    p.image(img,x+6,57,75,56)
    p.text(x+4,119,filename,2.8,INK,True)
    p.paragraph(x+4,127,note,78,3)
    # Section-style orientation icon, explicitly separate from the part portrait.
    p.line(x+19,153,x+68,153,"#6f8293",0.7)
    p.rect(x+27,149,33,3,BLUE if i==0 else "#b9c5d0" if i==1 else ORANGE)
    if i<2:
        p.rect(x+27,142 if i==0 else 146,2,7 if i==0 else 3,BLUE if i==0 else "#b9c5d0")
        p.rect(x+58,142 if i==0 else 146,2,7 if i==0 else 3,BLUE if i==0 else "#b9c5d0")
p.paragraph(12,174,"Use the supplied print STLs in millimeters: their print orientations are already applied. The pictures above identify parts; the small sections show bed orientation. Use the coupon settings that passed the previous step.",270,3.3)
p.paragraph(12,189,"Starting proposal: PETG, 0.4 mm nozzle, 0.2 mm layers. Review bridges/supports in the slicer and record your actual profile.",270,3)
p.save("print-orientation")

p=Page("Clean and prepare the blue base",step=3)
p.panel("USE THESE PARTS")
p.image("part-base",15,59,60,45)
p.text(17,108,"1 × base",3.7,INK,True)
p.paragraph(17,118,"Remove supports and strings. Try the empty lid; it must seat without screws pulling it flat.",56,3.1)
p.paragraph(17,143,"A: four PCB posts. B: four lid towers. Tap their pilots only after the coupon passes.",56,3.1)
p.main("02-base",True)
p.text(96,191,"C: DI wire openings    D: USB service opening",3,BLUE,True)
p.check("Pilots clear. Floor and lid flat.")
p.save("base")

p=Page("Try the card board template",step=4)
p.panel()
p.image("part-template",15,59,60,45)
p.text(17,109,"1 × card template",3.6,INK,True)
p.paragraph(17,119,"Print drawing 03 at 100%. Check its 100 mm scale bar, cut the outline and punch four holes.",56,3.1)
p.paragraph(17,146,"Lower onto the posts. DI edge faces the four front openings. Check USB and terminal positions.",56,3.1)
p.main("03-template")
p.check("All four holes align freely.")
p.save("card-fit")

p=Page("Lower the tested board into the base","FUTURE STEP / AFTER PCB RELEASE + BRING-UP",5)
p.panel()
p.image("part-board",15,59,60,45)
p.text(17,109,"1 × tested PCB",3.6,INK,True)
p.paragraph(17,119,"First finish routing, fabrication review and the electrical bring-up in the technical reference.",56,3.1)
p.paragraph(17,146,"Power off. Remove cables. Inspect underside leads, then lower the board onto all four posts.",56,3.1)
p.main("04-board")
p.text(97,191,"DI terminals face the four front openings; USB faces its side port.",2.9,BLUE,True)
p.check("Board flat; no lead touches case.")
p.save("install-board")

p=Page("Secure the board with four screws","FUTURE STEP / BOARD INSTALLED, POWER OFF",6)
p.panel()
p.hardware("screw",17,62,"M3 × 6",4)
p.hardware("washer",17,93,"M3 washer",4)
p.paragraph(17,130,"Washer goes under each screw head, on top of the PCB. Tighten gently by hand in opposite corners.",56,3.1)
p.main("05-board-screws")
p.check("No bowing or screw bottoming.")
p.save("board-fasteners")

p=Page("Attach the orange blank to the lid",step=7)
p.panel()
p.text(17,65,"1 × lid + 1 × blank",3.6,INK,True)
p.hardware("screw",17,71,"M2.5 × 8",2)
p.hardware("washer",17,97,"M2.5 washer",2)
p.hardware("nut",17,123,"M2.5 nut",2)
p.paragraph(17,156,"Screw → blank → lid → washer → nut.",56,3.1,bold=True)
p.main("06-blank")
p.text(96,191,"Washers and nuts go underneath: see the detail on the next page.",3,BLUE,True)
p.check("Blank covers the entire opening.")
p.save("blank-fasteners")

p=Page("The blank fastener stack, from both sides", "DETAIL / DISPLAY BLANK HARDWARE")
p.text(17,45,"SIDE SECTION / ONE FASTENER",3.2,BLUE,True)
# An explanatory cross-section, not a manufacturing drawing.
p.rect(35,69,8,80,"#e7ad27")
p.rect(27,66,24,8,"#f2bb3f",2)
p.rect(15,78,20,10,ORANGE)
p.rect(43,78,28,10,ORANGE)
p.rect(15,95,20,12,"#b9c5d0")
p.rect(43,95,28,12,"#b9c5d0")
p.rect(26,114,9,4,"#e7ad27")
p.rect(43,114,9,4,"#e7ad27")
p.rect(27,125,8,10,"#d59a1b")
p.rect(43,125,8,10,"#d59a1b")
for yy,label in [(71,"Screw head"),(84,"Blank"),(102,"Lid"),(117,"Washer"),(131,"Nut")]:
    p.line(57,yy,76,yy,"#6f8293",0.4)
    p.text(78,yy+1,label,3.2)
p.text(17,158,"M2.5 × 8: length below the head",3.1,INK,True)
p.paragraph(17,166,"Section is illustrative; gaps are exaggerated to show the order. Washers belong below the lid.",96,3.1)
p.image("06-under-lid",113,45,176,132)
p.text(153,184,"UNDERSIDE VIEW / two nuts + two washers",3.1,BLUE,True)
p.save("blank-stack-detail")

p=Page("Check the completed lid",step=8)
p.panel("COMPLETED SUBASSEMBLY")
p.image("part-blank",19,64,52,39)
p.paragraph(17,113,"Hold each nut while tightening its screw. The blank should sit flat with no movement.",56,3.2)
p.paragraph(17,143,"Check underneath: both washers and nuts are present. Keep them clear of future wiring.",56,3.1)
p.main("07-lid-ready")
p.text(96,191,"Lid lettering is a separate applied label; it is not embossed in the STL.",2.9,BLUE,True)
p.check("Two screws, two washers, two nuts.")
p.save("completed-lid")

p=Page("Inspect the open assembly and wiring","FUTURE STEP / POWER OFF DURING ASSEMBLY",9)
p.panel("CHECK BEFORE CLOSING")
for i,t in enumerate(["A  All 4 board screws seated.","B  DI1–DI4 at the front.","C  Q1–Q4 at the rear.","D  24 V supply connector.","E  USB service opening."]):
    p.paragraph(17,67+i*17,t,56,3.1)
p.paragraph(17,153,"Use schematic pin numbers for polarity, never this picture alone.",56,2.9,bold=True)
p.main("08-inspect",True)
p.check("No loose hardware or clipped leads.")
p.save("inspect")

p=Page("Seat the lid without trapping wires","CASE FIT NOW / OR FUTURE TESTED ASSEMBLY",10)
p.panel()
p.image("07-lid-ready",15,60,60,45)
p.text(17,112,"1 × completed lid",3.6,INK,True)
p.paragraph(17,122,"If wired: label each wire, use the terminal maker’s strip length and provide external strain relief.",56,3)
p.paragraph(17,147,"Keep wires away from the lip and blank nuts. Lower the lid until the lip sits inside the case.",56,3)
p.main("09-close")
p.check("Lid sits flush before screws go in.")
p.save("close-lid")

p=Page("Fit the four lid screws","CASE FIT NOW / OR FUTURE TESTED ASSEMBLY",11)
p.panel()
p.hardware("screw",17,65,"M3 × 8",4)
p.paragraph(17,103,"Start all four screws by hand. Seat them lightly in the illustrated order: 1 → 2 → 3 → 4.",56,3.2)
p.paragraph(17,136,"Heads must fit the counterbores. Stop if a screw bottoms out or the plastic starts to distort.",56,3.1)
p.main("10-lid-screws",True)
p.check("Even seam; no forced lid bending.")
p.save("lid-fasteners")

p=Page("Record the fit. Plan the next revision.","COMPLETE / MECHANICAL PROTOTYPE")
p.image("11-complete",89,37,196,147)
p.rect(12,44,68,130,"#edf5fc",3)
p.text(17,55,"FINAL CHECK",3.4,TEAL,True)
for i,t in enumerate(["Case seam is even.","Blank is secure.","Ports stay accessible.","No trapped wiring.","Labels match the schematic."]):
    p.rect(17,63+i*12,3,3,"white")
    p.text(23,66+i*12,t,2.9)
p.paragraph(17,132,"Record print settings, fit issues and measurements. Revise CAD and regenerate matching files.",58,3.1)
p.text(12,184,"Next: electrical bring-up and measured testing",3.6,ORANGE,True)
p.paragraph(12,191,"Follow technical-assembly-reference.pdf for staged soldering, power checks, SWD, I/O and firmware. A closed case does not establish a working controller.",271,2.9)
p.save("complete")

subprocess.run(["pdfunite",*[str(f) for f in FILES],str(OUT/"assembly-guide.pdf")],check=True)
manifest={"pages":len(FILES),"page_format":"A4 landscape","source":"FreeCAD-derived meshes rendered in Blender; vector annotations",
          "status":"Illustrated intended mechanical sequence; no physical assembly validation",
          "hardware":"Nominal candidate screw, washer and nut geometry; colors for identification",
          "pdf":"assembly-guide.pdf","page_sources":[f.name.replace('.pdf','.svg') for f in FILES]}
(PAGES/"manifest.json").write_text(json.dumps(manifest,indent=2)+"\n")
print(f"Created {len(FILES)} illustrated pages: {OUT/'assembly-guide.pdf'}")
