#!/usr/bin/env python3
"""A1 dimensioned construction, lens-mask and label sheets at true scale."""
import json
from pathlib import Path
from publication import Page,ROOT,INK,MUTED,ACCENT,bundle
OUT=ROOT/'mechanical/drawings'
P=json.loads((ROOT/'parameters.json').read_text())
C=json.loads((ROOT/'bom/components.json').read_text())
pdfs=[]

def sheet(title,n):
    p=Page(title,'CONSTRUCTION / A1 / mm / ACTUAL SIZE A4 / CAD FIT ONLY',n)
    p.line(180,187,280,187,MUTED,.4)
    for x in [180,280]:p.line(x,185,x,189,MUTED,.4)
    p.text(230,183,'100 mm — verify printed scale',2.7,MUTED,anchor='middle')
    return p

p=sheet('01  Base and concealed fastening',1);x,y=25,49
p.rect(x,y,140,110,'none',7,INK);p.rect(x+2.4,y+2.4,135.2,105.2,'none',4.6,MUTED)
for hx,hy in [(15,15),(125,15),(15,95),(125,95)]:
    p.circle(x+hx,y+hy,3.5);p.circle(x+hx,y+hy,1.25)
for hx,hy in P['case']['lid_screw_centers']:
    p.circle(x+hx,y+hy,3.2);p.circle(x+hx,y+hy,1.7)
for c in C:
    if c['ref'] in ['J1']+[f'J{i}' for i in range(5,13)]:
        xx=c['xy'][0]+10+(-2.54 if c['angle']==180 else 2.54)
        yy=0 if c['angle']==180 else 107.6
        p.rect(x+xx-6,y+yy,12,2.4,'none',0,INK)
p.hdim(x,x+140,42,'140');p.vdim(18,y,y+110,'110')
p.para(179,49,'Base H 34; floor/wall 2.4. Corner R7. PCB underside Z8; PCB thickness 1.6.',102,3.3)
p.para(179,75,'PCB posts: Ø7 / pilot Ø2.5. Centers (15,15), (125,15), (15,95), (125,95). M3 × 6 + 0.5 washer.',102,3.2)
p.para(179,106,'Lid screws enter from below: M3 × 10. Centers (7,7), (133,7), (7,103), (133,103). Ø3.4 clearance; Ø6.4 × 1.5 counterbore.',102,3.2)
p.para(179,143,'Ports: 12 W × 16 H; bottom Z9. Right USB port: Y43.5–62.5, Z7–17. Switch detail: sheet 04.',102,3.2)
p.para(25,172,'Plan uses the numeric board/case XY datum. DI edge Y=0; supply/Q edge Y=110. All tolerances are prototype starting assumptions.',140,2.8)
pdfs.append(p.save(OUT/'01-base'))

p=sheet('02  Lid, optics and display mounting',2);x,y=25,49
p.rect(x,y,140,110,'none',7,INK)
p.rect(x+38.8,y+38.8,64.4,32.4,'none',2.2,INK)
p.rect(x+60.75,y+48,24.5,14,'none',.7,INK)
for yy in [53,57]:p.circle(x+49,y+yy,1.6)
for hx,hy in P['case']['lid_screw_centers']:p.circle(x+hx,y+hy,3.3,stroke=MUTED)
for hx,hy in P['display']['holes']:
    p.circle(x+58.395+hx,y+35.599+hy,2);p.circle(x+58.395+hx,y+35.599+hy,.8)
p.hdim(x,x+140,42,'140');p.vdim(18,y,y+110,'110')
notes=['Plate Z34–37; top-edge fillet R0.7. Locating lip Z32.2–34; gap 0.3/side.',
       'Lid columns Ø6.6, Z4.3–34. Blind M3 pilots Ø2.5, 10 deep from underside.',
       'Lens 64 × 32 × 1, R2. Pocket 64.4 × 32.4 × 1.2; 0.2 adhesive allowance.',
       'OLED PCB origin (58.395,35.599,27). Hole pitch 24.13 × 26.67. Posts Ø4; M2 pilots Ø1.6.',
       'Glass top Z33.2; nominal lid gap 0.8. Rods Ø3 × 24.6, Z11.2–35.8. Physical fit must be checked.']
yy=49
for note in notes:yy=p.para(179,yy,note,102,3.1)+7
p.para(25,174,'OLED and column circles are underside features; no top screw holes. Top lettering is applied separately. Rods must clear LED packages.',140,2.8)
pdfs.append(p.save(OUT/'02-lid-and-optics'))

p=sheet('03  Custom PCB card fit template',3);x,y=25,50
p.rect(x,y,120,90,'none',0,INK)
for hx,hy in P['pcb']['holes']:p.circle(x+hx,y+hy,1.6)
for c in C:
    if c['ref'] in ['J1','J17']+[f'J{i}' for i in range(5,13)]:
        xx=c['xy'][0]+(-2.54 if c['angle']==180 else 2.54);yy=c['xy'][1]+(.3 if c['angle']==180 else -.3)
        p.rect(x+xx-5.1,y+yy-4.9,10.2,9.8,'none',0,INK)
        p.text(x+xx,y+yy+1,c['ref'],2.3,anchor='middle')
    elif c['ref'] in ['D2','D3']:
        p.circle(x+c['xy'][0],y+c['xy'][1],1)
p.hdim(x,x+120,43,'120');p.vdim(18,y,y+90,'90');p.hdim(x+5,x+115,149,'110 hole pitch')
p.para(170,49,'120 × 90 × 1.6 mm custom controller. Four Ø3.2 NPTH holes at (5,5), (115,5), (5,85), (115,85).',110,3.3)
p.para(170,80,'Case offset: +10,+10. DI edge is Y=0. Q and input supply edge is Y=90. J1.1 = +24 V; J1.2 = 0 V/GND (−).',110,3.3)
p.para(170,114,'J17 is the internal switch loop. Both contacts carry positive supply; neither is ground. D2 RUN at (39,43); D3 PWR at (39,47).',110,3.3)
p.para(170,147,'Cut from card for fit checks. This is not a copper/pad image. A1 has no routed tracks and is not ready for fabrication.',110,3.3)
pdfs.append(p.save(OUT/'03-pcb-fit-template'))

p=sheet('04  Switch coupon, lens and optical rods',4)
p.rect(25,52,54,32,'none',0,INK);p.rect(30,58,12.9,19.81,'none',0,INK)
for x,r in [(52,1.25),(61,1.6),(70,.8)]:p.circle(x,68,r)
p.text(25,46,'COUPON 54 × 32 × 2.4',3.2,bold=True)
p.text(25,93,'Switch opening 12.90 × 19.81',3)
p.text(25,100,'Pilots Ø2.5 / rod bore Ø3.2 / pilot Ø1.6',3)
p.rect(25,119,64,32,'none',2,INK);p.rect(46.75,128,24.5,14,'none',.7,INK)
for yy in [133,137]:p.circle(35,yy,1)
p.text(25,114,'LENS CUT 64 × 32 × 1 / R2',3.2,bold=True)
p.text(25,160,'Clear screen + LED windows in a reverse black mask.',2.9)
p.para(170,47,'Switch panel: 2.4 mm. Opening centered at left-face Y49, Z22. C&K D102 S2 nominal dimensions; validate with actual switch.',111,3.3)
p.para(170,84,'Lens front-view mask: screen window centered at (34,16), 24.5 × 14. LED clear spots Ø2 at (10,14) PWR and (10,18) RUN.',111,3.3)
p.para(170,121,'Two clear acrylic rods: Ø3 × 24.6. Polish ends. Lower ledge Z11.2; LED top envelope Z10.6. No contact pressure on LEDs.',111,3.3)
p.para(170,156,'Base print: floor down. Lid print: outside down, columns up. Use the STL orientations; import units as mm.',111,3.1)
pdfs.append(p.save(OUT/'04-coupon-and-lens'))
bundle(pdfs,OUT/'tinyplc-a1-drawings.pdf')

# Physical-size mask, front view. The transparent windows are not black ink.
mask=['<svg xmlns="http://www.w3.org/2000/svg" width="64mm" height="32mm" viewBox="0 0 64 32">',
      '<defs><mask id="m"><rect width="64" height="32" rx="2" fill="white"/><rect x="21.75" y="9" width="24.5" height="14" rx=".7" fill="black"/><circle cx="10" cy="14" r="1" fill="black"/><circle cx="10" cy="18" r="1" fill="black"/></mask></defs>',
      '<rect width="64" height="32" rx="2" fill="#0b1117" mask="url(#m)"/>',
      '<g fill="#d3dcdf" font-family="sans-serif" font-size="1.25"><text x="13" y="14.6">PWR</text><text x="13" y="18.6">RUN</text></g></svg>']
(OUT/'lens-mask-front.svg').write_text('\n'.join(mask)+'\n')
# Full-size label master for transfer/decal printing; no cutting through the case.
p=sheet('05  Applied label master / front-view orientation',5);x,y=25,46
p.rect(x,y,140,110,'none',7,MUTED)
p.text(x+70,y+110-84,'tinyPLC',4.3,anchor='middle')
p.text(x+70,y+110-79.5,'A1 / RESEARCH CONTROLLER',1.25,anchor='middle')
for c in C:
    ref=c['ref']
    if ref in [f'J{i}' for i in range(5,9)]:
        xx=c['xy'][0]+10-2.54
        p.text(x+xx,y+103,'DI'+str(int(ref[1:])-4),2.1,anchor='middle');p.text(x+xx,y+106.3,'0V  +',1.3,anchor='middle')
    elif ref in [f'J{i}' for i in range(9,13)]:
        xx=c['xy'][0]+10+2.54
        p.text(x+xx,y+7,'Q'+str(int(ref[1:])-8),2.1,anchor='middle',rotation=180);p.text(x+xx,y+3.7,'Q  +24',1.25,anchor='middle',rotation=180)
p.text(x+106.54,y+9,'24 V DC',2.4,anchor='middle',rotation=180)
p.text(x+104,y+5,'+',2,anchor='middle',rotation=180);p.text(x+109.08,y+5,'−',2,anchor='middle',rotation=180)
p.para(179,51,'Print at actual size on a suitable decal/transfer medium. Outline is an alignment reference, not part of the label.',102,3.3)
p.para(179,84,'Separate side labels below. No protective-earth symbol: 0 V/GND is the shared DC return, not PE.',102,3.3)
p.text(179,124,'24 V DC INPUT',2.0);p.text(179,130,'− 0V/GND  |  +24V',1.7)
p.text(179,143,'USB / SERVICE',1.8);p.text(179,154,'POWER',1.7)
p.para(25,173,'The lens mask is a separate 64 × 32 mm SVG. Mask artwork is a front view: reverse/mirror for reverse-side printing, keeping viewing windows clear.',140,2.8)
p.save(OUT/'05-applied-labels')
print('Created A1 construction drawings, label master and lens mask.')
