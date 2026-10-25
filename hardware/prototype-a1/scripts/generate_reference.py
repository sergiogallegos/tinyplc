#!/usr/bin/env python3
"""Mechanical/harness purchasing register, per-item circuit guide and print text."""
import csv
import html
import json
from pathlib import Path
import re
import subprocess
import textwrap
from publication import ROOT,bundle

REPO=ROOT.parents[1]
parts=json.loads((ROOT/'bom/components.json').read_text())
external=json.loads((ROOT/'bom/external-circuits.json').read_text())
fields=['ref','quantity','specification','purpose','official_reference','status']
rows=[]
def row(ref,qty,spec,purpose,url,status='candidate; verify exact drawing, fit and availability'):
    rows.append(dict(zip(fields,[ref,qty,spec,purpose,url,status])))
cad='../mechanical/tinyplc-a1.FCStd'
row('CASE-BASE',1,'base-print.stl; white PETG','Protect board; support PCB and side switch',cad,'custom print; physical fit untested')
row('CASE-LID',1,'lid-print.stl; white PETG','Conceal fasteners; retain OLED and optical guides',cad,'custom print; physical fit untested')
row('COUPON',1,'fit-coupon-print.stl','Trial switch aperture, M3/M2 pilots and rod bore',cad,'print before full enclosure')
row('PCB-SCREW',4,'M3 x 6 pan head','Secure controller to support posts','https://www.bossard.com/','exact supplier SKU pending')
row('PCB-WASHER',4,'M3; nominal 0.5 mm thickness','Spread force and set screw engagement','https://www.bossard.com/','exact supplier SKU pending')
row('CASE-SCREW',4,'M3 x 10; head OD <=6.4 mm','Underside access keeps top visually clean','https://www.bossard.com/','exact head height and SKU pending; verify counterbore')
row('OLED-SCREW',4,'M2 x 6 pan head','Secure OLED from rear into integral posts','https://www.bossard.com/','exact supplier SKU pending')
row('OLED-WASHER',4,'M2; nominal 0.5 mm thickness','Protect module mounting tabs','https://www.bossard.com/','exact supplier SKU pending')
row('LENS',1,'Clear nonconductive sheet 64 x 32 x 1 mm; R2 corners','Protect status window and capture rods','https://www.plexiglas.de/en','material family only; exact sheet grade and supplier pending')
row('LENS-MASK',1,'lens-mask-front.svg; reverse black mask','Hide module edges while keeping optical windows clear','../mechanical/drawings/lens-mask-front.svg','custom artwork; mirror for reverse-side printing')
row('LENS-ADHESIVE',1,'Perimeter adhesive; 0.2 mm thickness allowance','Retain lens without loading screen','../mechanical/drawings/02-lid-and-optics.pdf','exact nonconductive adhesive and optical compatibility pending')
row('LIGHT-ROD',2,'Clear PMMA rod diameter 3 mm; cut/polish length 24.6 mm','Bring power and RUN LED light to lens','https://www.plexiglas.de/en','material family only; exact stock and optical fit pending')
row('FEET',4,'Nominal diameter 8 x 2 mm; compare 3M SJ5302 (7.93 x 2.16)','Keep underside screws clear of desk','https://multimedia.3m.com/mws/media/175691O/3m-tm-bumpon-tm-protective-products.pdf','render uses nominal 8 x 2; selected part and final height pending')
row('LABELS',1,'05-applied-labels.pdf; suitable transfer/decal medium','Identify supply polarity, I/O, service port and power','../mechanical/drawings/05-applied-labels.pdf','custom artwork; verify labels against nets before applying')
row('FINISH',1,'Optional narrow silver cosmetic paint stripe','Subtle seam accent without conductive metal enclosure','../README.md','optional finish; mask mating faces and electrical parts')
for p in external:row(p['ref'],1,p['mpn'],p['purpose'],p['official_document'])
row('OLED-CABLE',1,'Adafruit 4397; QT to premium female sockets; 150 mm','Connect J16 male header to DS1; map by signal not position','https://www.adafruit.com/product/4397','candidate; dress service loop and verify color-to-pin continuity')
row('SWITCH-LEADS',2,'Insulated wire suitable for fused 24 V circuit','Carry fused positive feed to/from panel switch','https://www.ckswitches.com/media/1439/d.pdf','wire gauge and insulation grade pending; match crimp range')
row('SWITCH-RECEPTACLE',2,'Insulated female quick-connect 4.75 x 0.8 mm','Cover SW3 terminals; removable service harness','https://www.ckswitches.com/media/1439/d.pdf','exact receptacle/boot and crimp tool pending; check space physically')
with (ROOT/'bom/mechanical-and-harness.csv').open('w',newline='') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)
with (ROOT/'bom/harness.csv').open('w',newline='') as f:
    w=csv.writer(f);w.writerow(['from','to','signal','identification'])
    w.writerows([['J17.1','SW3.1','VIN_FUSED','Positive supply; not GND'],['SW3.1A','J17.2','VIN_SWITCHED','Positive return; not GND'],['J16.1','DS1 QT.2','+3V3','Red'],['J16.2','DS1 QT.1','GND','Black'],['J16.3','DS1 QT.4','I2C_SCL','Yellow'],['J16.4','DS1 QT.3','I2C_SDA','Blue']])

lines=['# A1 component-by-component register','','Each row comes from the A1 schematic/BOM source. The custom controller is','routed; exact purchasing choices and physical performance still require review.','Off-board SW3/DS1 are shown in the schematic but are not fake PCB footprints.','Read the [A1 decisions](prototype-a1-design.md) and the [common circuit explanation](prototype-a-electronics.md).','']
for group in dict.fromkeys(p['group'] for p in parts+external):
    lines += ['## '+group,'','| Ref | Candidate / value | Function and reason | Official reference |','| --- | --- | --- | --- |']
    for p in parts+external:
        if p['group']==group:lines.append(f'| {p["ref"]} | {p["mpn"]}; {p["value"]} | {p["purpose"]} | [Source]({p["official_document"]}) |')
    lines.append('')
lines+=['## Mechanical and harness parts','','See [mechanical-and-harness.csv](../../hardware/prototype-a1/bom/mechanical-and-harness.csv) for quantities, reasons and source references.','Generic supplier/family references do not resolve an exact purchasing SKU.','']
(REPO/'docs/hardware/prototype-a1-components.md').write_text('\n'.join(lines))

# Printable detailed procedure, alongside the visual booklet.
doc=REPO/'docs/hardware/prototype-a1-assembly.md'
chunks=[];page=[];used=0
for para in doc.read_text().split('\n\n'):
    text=' '.join(para.splitlines());text=re.sub(r'\[([^\]]+)\]\([^)]+\)',r'\1',text).replace('**','').replace('`','')
    heading=text.startswith('#');text=text.lstrip('# ')
    wrapped=textwrap.wrap(text,width=94 if not heading else 78);height=len(wrapped)*4.7+5
    if used+height>249 and page:chunks.append(page);page=[];used=0
    page.append((used,wrapped,heading));used+=height
if page:chunks.append(page)
out=ROOT/'mechanical/drawings/technical-pages';out.mkdir(exist_ok=True)
pdfs=[]
for i,page in enumerate(chunks,1):
    svg=['<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297"><rect width="210" height="297" fill="white"/><g font-family="sans-serif" fill="#202c34">',f'<text x="15" y="13" font-size="3">tinyPLC A1 / TECHNICAL ASSEMBLY / {i} of {len(chunks)}</text>']
    for y,wrapped,heading in page:
        for j,line in enumerate(wrapped):svg.append(f'<text x="15" y="{26+y+j*4.7}" font-size="{3.5 if heading else 3}" font-weight="{700 if heading else 400}">{html.escape(line)}</text>')
    svg.append('<text x="15" y="286" font-size="2.5">Routed prototype; physical testing pending. Use matching A1 design, schematic, BOM and illustrated assembly guide.</text></g></svg>')
    path=out/f'{i:02}.svg';path.write_text('\n'.join(svg));pdf=path.with_suffix('.pdf')
    subprocess.run(['rsvg-convert','--format=pdf','--output',str(pdf),str(path)],check=True);pdfs.append(pdf)
bundle(pdfs,ROOT/'mechanical/drawings/technical-assembly-reference.pdf')
print(f'Created purchasing register, harness map, component register and {len(chunks)} technical pages.')
