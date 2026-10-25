#!/usr/bin/env python3
"""A1 picture-led assembly booklet; hardware status stays visible on every page."""
import json
from publication import Page,ROOT,INK,MUTED,ACCENT,PALE,bundle
OUT=ROOT/'mechanical/drawings';meta=json.loads((ROOT/'renders/projections.json').read_text());pages=[]

def save(p,name):pages.append(p.save(OUT/'assembly-pages'/name))
def step(n,title,img,parts,instruction,check,future=False):
    p=Page(f'{n:02}  {title}','ASSEMBLY / A1 / '+('AFTER ROUTED PCB RELEASE + BRING-UP' if future else 'PROTOTYPE FIT / POWER DISCONNECTED'),len(pages)+1)
    p.rect(14,47,68,125,PALE,3);p.text(19,57,'PARTS / TOOLS',2.8,ACCENT,True)
    yy=p.para(19,67,parts,58,3.4,bold=True)
    p.para(19,yy+9,instruction,58,3.2)
    p.image(img,92,39,190,137.2222)
    for a,b in meta.get(img,{}).get('arrows',[]):
        x1,y1=92+a[0]*190,39+a[1]*137.2222;x2,y2=92+b[0]*190,39+b[1]*137.2222
        p.line(x1,y1,x2,y2,'white',2);p.line(x1,y1,x2,y2,ACCENT,.9,True)
    p.rect(14,178,269,15,'#eaf3ef',2);p.text(19,187,'CHECK  /  '+check,3.1,ACCENT,True)
    save(p,f'{len(pages)+1:02}-step-{n:02}')

p=Page('Build the A1 enclosure.','tinyPLC / VISUAL ASSEMBLY GUIDE',1)
p.image('hero-white',93,43,193,139.4)
p.text(14,53,'WHITE SHELL.',6.3,INK,True);p.text(14,63,'VISIBLE STATUS.',6.3,INK,True)
p.para(14,78,'A picture-led sequence for the switch, custom controller, OLED, light guides and concealed fasteners.',75,3.6)
p.para(14,120,'Start now: print and card fit checks. Board installation follows a routed, reviewed release and staged electrical bring-up.',75,3.4)
p.para(14,164,'All pictures are CAD renders. The display says DEMO because its A1 firmware integration is still pending.',75,3.1,MUTED)
save(p,'01-cover')

p=Page('Lay out the parts.','INVENTORY / USE THE MATCHING A1 BOM',2)
items=[('Printed parts','1 base + 1 lid + 1 fit coupon. Print STLs already have bed orientation.'),
       ('Board retention','4 × M3 × 6 screws; 4 × M3 washers, nominal 0.5 mm thick.'),
       ('Case retention','4 × M3 × 10 screws from below; 4 adhesive feet, nominal 8 × 2 mm.'),
       ('Status optics','1 lens, 64 × 32 × 1; reverse black mask; 2 clear Ø3 × 24.6 rods.'),
       ('OLED module','1 Adafruit 326 QT; 4 × M2 × 6 screws; 4 × M2 washers; 1 four-wire harness.'),
       ('Power switch','1 C&K D102J12S215HQA candidate; 2 insulated leads with matching quick-connects.')]
for i,(title,body) in enumerate(items):p.block(14+(i%3)*93,44+(i//3)*65,83,58,title,body)
p.para(14,185,'Prepare a ruler, suitable hand screwdriver, M3/M2 taps, crimp tool and multimeter. Try actual hardware on the coupon before printing the whole case.',269,3.2)
save(p,'02-inventory')

step(1,'Print the coupon, then the shell.','step-base','1 coupon / base / lid. Ruler, switch, taps and rod.',
     'Test the switch snap fit, M3/M2 pilots and rod bore first. Print base floor-down; lid outside-face-down with columns up. Import STLs in mm.',
     'Coupon passes; empty lid seats flush. No cracked pilots or warped mating faces.')
step(2,'Fit the side power switch.','step-switch','1 SW3 switch. Two insulated quick-connect leads.',
     'Snap into the left opening. Check terminal 1–1A continuity in the I position. Fit insulated 4.75 × 0.8 mm connectors with the correct crimp tool.',
     'Switch retained; terminals insulated; space for connector boots and wire bends.')
step(3,'Lower the tested board onto its posts.','step-board','1 reviewed and tested custom A1 controller PCB.',
     'For the first case trial, substitute the card template. For electronics assembly, remove all power and cables. DI edge faces the four front openings.',
     'All four holes align. No lead touches the floor or case.',True)
step(4,'Secure the controller board.','step-board-screws','4 × M3 × 6 screws. 4 × M3 washers.',
     'Place a washer under each head, on the PCB. Start all screws and tighten gently in opposite corners. Keep the board flat.',
     'No board bowing, bottomed screws or loose hardware.',True)

p=Page('05  Wire the positive-side switch loop.','ASSEMBLY / A1 / POWER DISCONNECTED',len(pages)+1)
p.image('step-switch',14,49,130,94)
for x,title,body in [(155,'J17.1','VIN_FUSED'),(218,'SW3.1','Common')]:p.block(x,47,55,27,title,body)
p.line(211,61,217,61,ACCENT,.8,True)
p.block(218,94,55,27,'SW3.1A','ON contact');p.line(245,75,245,92,ACCENT,.8,True)
p.block(155,94,55,27,'J17.2','VIN_SWITCHED');p.line(217,107,212,107,ACCENT,.8,True)
p.para(155,137,'Both J17 contacts are positive power paths. Neither is ground. Verify ON closes the loop and OFF opens it.',122,3.5,bold=True)
p.para(14,172,'J1 supply: pin 1 = +24 V, pin 2 = 0 V/GND (−). Disconnect the source before assembly. OFF does not isolate the input terminal or every external signal.',268,3.4)
save(p,f'{len(pages)+1:02}-switch-wiring')

step(6,'Install the light guides and lens.','step-optics','2 clear Ø3 × 24.6 rods. 1 masked lens + perimeter adhesive.',
     'Insert rods through the top pocket onto their ledges. Align the screen and LED windows in the reverse mask. Bond the lens perimeter after the optical trial.',
     'Rods stay clear of LEDs. Viewing windows remain clear; adhesive stays off the optics.')
step(7,'Mount the OLED beneath the lid.','step-lid','1 Adafruit 326 QT. 4 × M2 × 6 screws + washers.',
     'Glass faces the lid window. Posts touch the module PCB, not the glass. Screws enter from the module rear. Check the received board revision and narrow glass clearance.',
     'No glass/flex clamping; module flat, lens aligned and screws retained.')

p=Page('08  Connect the display harness.','ASSEMBLY / A1 / CUSTOM HEADER ORDER',len(pages)+1)
p.image('step-lid',12,43,145,105)
rows=[('J16.1','+3V3','QT 2 / VIN / red','#cc5d4c'),('J16.2','GND','QT 1 / GND / black','#303a40'),('J16.3','SCL / PB6','QT 4 / yellow','#b99020'),('J16.4','SDA / PB7','QT 3 / blue','#2b729a')]
for i,(pin,net,dest,color) in enumerate(rows):
    yy=51+i*25;p.rect(163,yy,120,20,PALE,2);p.circle(169,yy+10,1.6,color,color)
    p.text(175,yy+8,pin+'  '+net,3.5,INK,True);p.text(175,yy+15,dest,3.1)
p.para(14,160,'Use female sockets at the controller male header and a keyed QT plug at the display. These pin orders are different: verify continuity, then measure 3.3 V before connecting the module.',269,3.4)
p.para(14,183,'Leave a short service loop clear of columns and optical sleeves. Do not pull the display cable when removing the lid.',269,3.2,ACCENT,True)
save(p,f'{len(pages)+1:02}-display-harness')

step(9,'Close the enclosure by hand.','step-close','1 completed lid. Board and wiring inspected.',
     'Remove clipped leads and tools. Check switch boots, the display loop and light-guide alignment. Seat the lip into the base without pinching wires.',
     'The lid is flush before any case screw is installed.',True)
step(10,'Fasten from underneath.','step-bottom-screws','4 × M3 × 10 screws. 4 adhesive feet.',
     'Turn the unpowered assembly over. Start all four screws, then tighten diagonally by hand. Place the feet clear of the screw access holes.',
     'Even seam; no forced bending. The top remains free of visible fasteners.')

p=Page('11  Apply labels and record the build.','ASSEMBLY / A1 / FINAL MECHANICAL CHECK',len(pages)+1)
p.image('rear-power',105,40,176,127.1)
p.para(14,52,'Apply the A1 label master. J1 is the supply input; output terminals are load connections.',74,3.5,bold=True)
p.para(14,83,'Verify +24 V and 0 V/GND (−) against J1 pin numbers. There is no protective-earth connection.',74,3.4)
p.para(14,119,'Record printer settings, screw fit, switch retention, cable clearance and optical alignment. Update CAD under a new revision when needed.',74,3.3)
p.para(14,179,'Electrical operation requires the staged bring-up procedure and an A1 firmware port. Test the actual terminal behavior, switch cycling and temperatures; a lit PWR LED does not prove execution.',269,3.4)
save(p,f'{len(pages)+1:02}-final-check')
bundle(pages,OUT/'assembly-guide.pdf')
(OUT/'assembly-pages/manifest.json').write_text(json.dumps({'pages':len(pages),'revision':'A1','images':'CAD-derived Blender renders','status':'routed PCB; assembly and UI unvalidated physically'},indent=2)+'\n')
print(f'Created {len(pages)}-page A1 visual assembly guide.')
