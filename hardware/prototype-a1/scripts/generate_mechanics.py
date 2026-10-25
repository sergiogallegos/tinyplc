#!/usr/bin/env python3
"""A1 enclosure: native FreeCAD Boolean tree, print meshes and CAD checks."""
import json
import math
from pathlib import Path
import sys

sys.path.append('/usr/lib/freecad/lib')
import FreeCAD as App
import Part
import MeshPart

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/'parameters.json').read_text())
OUT=ROOT/'mechanical'
DOC=App.newDocument('tinyPLC_A1')
S=DOC.addObject('Spreadsheet::Sheet','DesignDimensions')
for i,(name,value) in enumerate({'Width':140,'Depth':110,'BaseHeight':34,'LidTop':37,'Wall':2.4,'CornerRadius':7,'BoardBottom':8,'BoardOffset':10,'LensThickness':1,'OpticalRodLength':24.6}.items(),1):
    S.set(f'A{i}',name); S.set(f'B{i}',f'{value} mm'); S.setAlias(f'B{i}',name)
S.set('A13','Parameters and scripts govern coordinated regeneration; save manual edits separately.')

def box(name,size,pos):
    o=DOC.addObject('Part::Box',name)
    for k,v in zip(['Length','Width','Height'],size): setattr(o,k,v)
    o.Placement.Base=App.Vector(*pos)
    return o

def cyl(name,r,h,pos):
    o=DOC.addObject('Part::Cylinder',name);o.Radius=r;o.Height=h;o.Placement.Base=App.Vector(*pos)
    return o

def fuse(name,obs):
    o=DOC.addObject('Part::MultiFuse',name);o.Shapes=obs;o.Refine=True
    for x in obs:x.Visibility=False
    return o

def cut(name,a,b):
    o=DOC.addObject('Part::Cut',name);o.Base=a;o.Tool=b;o.Refine=True
    a.Visibility=False;b.Visibility=False
    return o

def rounded(name,w,d,h,r,pos):
    x,y,z=pos
    obs=[box(name+'CoreX',(w-2*r,d,h),(x+r,y,z)),box(name+'CoreY',(w,d-2*r,h),(x,y+r,z))]
    for i,(xx,yy) in enumerate([(r,r),(w-r,r),(r,d-r),(w-r,d-r)]):
        obs.append(cyl(name+f'Corner{i}',r,h,(x+xx,y+yy,z)))
    return fuse(name,obs)

base=cut('HollowWhiteBase',rounded('Outside',140,110,34,7,(0,0,0)),rounded('Inside',135.2,105.2,35,4.6,(2.4,2.4,2.4)))
posts=[]
board_holes=[(x+10,y+10) for x,y in P['pcb']['holes']]
for i,(x,y) in enumerate(board_holes):
    posts.append(cut(f'BoardSupport{i}',cyl(f'BoardPost{i}',3.5,5.6,(x,y,2.4)),cyl(f'BoardPilot{i}',1.25,6,(x,y,2.4))))
base=fuse('BaseWithBoardSupports',[base]+posts)
lid_holes=[(7,7),(133,7),(7,103),(133,103)]
for i,(x,y) in enumerate(lid_holes):
    base=fuse(f'BaseBoss{i}',[base,cyl(f'BottomScrewBoss{i}',4.2,4,(x,y,0))])
    base=cut(f'BottomClearance{i}',base,cyl(f'BottomScrewHole{i}',1.7,5,(x,y,-0.5)))
    base=cut(f'BottomCounterbore{i}',base,cyl(f'BottomHeadTool{i}',3.2,1.5,(x,y,0)))

components=json.loads((ROOT/'bom/components.json').read_text())
envelopes=[]; envdata=[]
for p in components:
    ref=p['ref']; fp=p['original_footprint']
    if ref.startswith(('TP','H')):continue
    if 'TerminalBlock' in fp:sx,sy,sz,dx,dy=10.2,9.8,13.8,2.54,-0.3
    elif ref=='U1':sx,sy,sz,dx,dy=12.5,12.5,1.6,0,0
    elif ref=='U2':sx,sy,sz,dx,dy=11.7,7.5,10.6,2.54,-1.75
    elif ref=='U3':sx,sy,sz,dx,dy=6.2,10.2,1.8,0,0
    elif 'DIP-4' in fp:sx,sy,sz,dx,dy=10.2,5,4.6,3.81,1.27
    elif ref=='J13':sx,sy,sz,dx,dy=9.2,7.35,3.4,0,1.5
    elif ref.startswith('J'):
        import re
        n=int(re.search(r'1x(\d+)',fp).group(1))
        sx,sy,sz,dx,dy=2.6,n*2.54,8.5,0,(n-1)*1.27
    elif ref.startswith('SW'):sx,sy,sz,dx,dy=6.5,6.5,5,3.25,2.25
    elif ref=='F1':sx,sy,sz,dx,dy=10.3,3.6,12,2.54,0
    elif ref=='C1':sx,sy,sz,dx,dy=5.5,5.5,12.5,1,0
    elif ref=='Y1':sx,sy,sz,dx,dy=5,3.2,1.3,0,0
    elif ref=='D1':sx,sy,sz,dx,dy=5.2,2.8,2.2,0,0
    elif ref=='U8':sx,sy,sz,dx,dy=3.1,3,1.2,0,0
    else:sx,sy,sz,dx,dy=2.1,1.4,1,0,0
    theta=math.radians(p['angle'])
    x=p['xy'][0]+10+dx*math.cos(theta)+dy*math.sin(theta)
    y=p['xy'][1]+10-dx*math.sin(theta)+dy*math.cos(theta)
    if p['angle'] in [90,270]:sx,sy=sy,sx
    ob=box('Package_'+ref,(sx,sy,sz),(x-sx/2,y-sy/2,9.6))
    ob.Label=ref+': '+p['value']+' (package envelope)'
    envelopes.append(ob);envdata.append(dict(ref=ref,center=[x,y,9.6+sz/2],size=[sx,sy,sz]))
    if ref in [f'J{i}' for i in range(5,9)]:
        base=cut(ref+'FrontPort',base,box(ref+'PortTool',(12,8,16),(x-6,-1,9)))
    elif ref in ['J1']+[f'J{i}' for i in range(9,13)]:
        base=cut(ref+'RearPort',base,box(ref+'PortTool',(12,8,16),(x-6,104,9)))
base=cut('USBServicePort',base,box('USBPortTool',(8,19,10),(134,43.5,7)))
# D102 S2: 12.90 x 19.81 cutout for 2.01--3.00 mm panel (vendor page 4).
base=cut('PowerSwitchCutout',base,box('SwitchCutTool',(7,12.9,19.81),(-1,42.55,12.095)))
base.Label='01 / matte white base / switch left, 24 V rear'

lid=rounded('LidPlate',140,110,3,7,(0,0,34))
DOC.recompute()
# Native fillet feature keeps a real softened outer edge in the printed part.
edge_ids=[(i+1,0.7,0.7) for i,e in enumerate(lid.Shape.Edges) if all(abs(v.Point.z-37)<1e-6 for v in e.Vertexes)]
fillet=DOC.addObject('Part::Fillet','SoftTopPerimeter');fillet.Base=lid;fillet.Edges=edge_ids;lid.Visibility=False;lid=fillet
lip=cut('LocatingLip',rounded('LipOutside',134.6,104.6,1.8,4.3,(2.7,2.7,32.2)),rounded('LipInside',131.4,101.4,3,2.7,(4.3,4.3,31.8)))
for i,(x,y) in enumerate(lid_holes):
    lip=cut(f'LipTowerClearance{i}',lip,cyl(f'LipTowerTool{i}',3.7,3,(x,y,32)))
lid=fuse('LidWithLip',[lid,lip])
for i,(x,y) in enumerate(lid_holes):
    tower=cut(f'BlindLidTower{i}',cyl(f'LidTower{i}',3.3,29.7,(x,y,4.3)),cyl(f'LidPilot{i}',1.25,10,(x,y,4.3)))
    lid=fuse(f'LidWithTower{i}',[lid,tower])

# Recessed clear lens with black reverse mask; 0.2 mm adhesive allowance.
lid=cut('LensPocket',lid,rounded('LensPocketTool',64.4,32.4,1.3,2.2,(38.8,38.8,35.8)))
lid=cut('OLEDViewingWindow',lid,rounded('OLEDWindowTool',24.5,14,6,0.7,(60.75,48,32)))
ox,oy,oz=P['display']['board_origin']
oled=box('OLEDModuleEnvelope',(29.21,31.75,1.6),(ox,oy,oz))
for i,(hx,hy) in enumerate(P['display']['holes']):
    x,y=ox+hx,oy+hy
    oled=cut(f'OLEDHole{i}',oled,cyl(f'OLEDHoleTool{i}',1.25,2,(x,y,26.8)))
    post=cut(f'OLEDPost{i}',cyl(f'OLEDPostOuter{i}',2.0,5.4,(x,y,28.6)),cyl(f'OLEDPilot{i}',0.8,6,(x,y,28.6)))
    lid=fuse(f'LidWithOLEDPost{i}',[lid,post])
glass=box('OLEDGlassEnvelope',(26.7,19.26,4.6),(59.65,43.272,28.6))
oled.Label='DS1 / Adafruit 326 QT PCB envelope / check received revision'
glass.Label='DS1 screen glass envelope / optical top Z=33.2'
lens=rounded('ClearMaskedLens',64,32,1,2,(39,39,36))
lens.Label='03 / 1 mm clear lens / reverse black mask, clear screen and LED windows'
rodparts=[]
for i,y in enumerate([53,57]):
    sleeve=cyl(f'OpticalSleeve{i}',2.3,22.9,(49,y,11.1))
    sleeve=cut(f'RodBore{i}',sleeve,cyl(f'RodBoreTool{i}',1.6,27,(49,y,11.2)))
    sleeve=cut(f'LightEntrance{i}',sleeve,cyl(f'LightEntranceTool{i}',1.05,1,(49,y,10.8)))
    lid=fuse(f'LidWithLightSleeve{i}',[lid,sleeve])
    lid=cut(f'LensLightPassage{i}',lid,cyl(f'TopLightTool{i}',1.6,3,(49,y,33.5)))
    rodparts.append(cyl(f'ClearRod{i}',1.5,24.6,(49,y,11.2)))
lid.Label='02 / white lid / hidden bottom screws, OLED posts and light guides'

board=box('ControllerPCB',(120,90,1.6),(10,10,8))
for i,(x,y) in enumerate(board_holes):board=cut(f'ControllerHole{i}',board,cyl(f'ControllerHoleTool{i}',1.6,3,(x,y,7.5)))
board.Label='Custom controller PCB / A1 / PROTOTYPE'
# Switch rear volume includes terminals; insulated connector boots need a physical trial.
switch=box('SW3Envelope',(20.45,12.7,18.54),(0,42.65,12.73))
switch.Label='SW3 / nominal internal envelope incl. terminals / verify boots and wiring'

DOC.recompute()
parts={'base':base,'lid':lid,'lens':lens,'pcb':board,'oled_pcb':oled,'oled_glass':glass,'rod_run':rodparts[0],'rod_pwr':rodparts[1],'switch':switch}
checks={'status':'CAD geometry only; wiring bends, printing and physical fit not tested','solids':{},'interferences':[]}
for name,ob in parts.items():
    assert ob.Shape.isValid() and len(ob.Shape.Solids)==1,name
    checks['solids'][name]={'valid':True,'solid_count':1,'volume_mm3':round(ob.Shape.Volume,3)}
for i,(name,ob) in enumerate(parts.items()):
    for name2,ob2 in list(parts.items())[i+1:]:
        # The switch body fills the panel cutout; its flange is represented in Blender.
        vol=ob.Shape.common(ob2.Shape).Volume
        if vol>0.001:checks['interferences'].append({'pair':name+' / '+name2,'volume_mm3':round(vol,5)})
for ob,data in zip(envelopes,envdata):
    for name in ['base','lid','oled_pcb','oled_glass','rod_run','rod_pwr','switch']:
        vol=ob.Shape.common(parts[name].Shape).Volume
        if vol>0.001:checks['interferences'].append({'pair':data['ref']+' / '+name,'volume_mm3':round(vol,5)})

for name in ['base','lid']:
    shape=parts[name].Shape.copy()
    if name=='lid':shape.rotate(App.Vector(0,0,0),App.Vector(1,0,0),180)
    bb=shape.BoundBox;shape.translate(App.Vector(-bb.XMin,-bb.YMin,-bb.ZMin))
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=0.06,AngularDeflection=0.15,Relative=False)
    assert mesh.isSolid(),name
    checks['solids'][name]['print_mesh_closed']=True
    mesh.write(str(OUT/(name+'-print.stl')))
    Part.export([parts[name]],str(OUT/(name+'.step')))
# Critical-fit coupon: pilot, rod bore and switch cutout in a 2.4 mm panel.
coupon=Part.makeBox(54,32,2.4)
coupon=coupon.cut(Part.makeBox(12.9,19.81,4,App.Vector(5,6,-0.5)))
for x,r in [(27,1.25),(36,1.6),(45,0.8)]:coupon=coupon.cut(Part.makeCylinder(r,4,App.Vector(x,16,-0.5)))
MeshPart.meshFromShape(Shape=coupon,LinearDeflection=0.06,AngularDeflection=0.15,Relative=False).write(str(OUT/'fit-coupon-print.stl'))
data=[]
for name,ob in parts.items():
    verts,faces=ob.Shape.tessellate(0.10)
    data.append(dict(name=name,vertices=[[v.x,v.y,v.z] for v in verts],faces=faces))
(OUT/'render-geometry.json').write_text(json.dumps({'parts':data,'envelopes':envdata},separators=(',',':'))+'\n')
Part.export(list(parts.values())+envelopes,str(OUT/'tinyplc-a1-assembly.step'))
DOC.recompute();DOC.saveAs(str(OUT/'tinyplc-a1.FCStd'))
(ROOT/'reports/mechanical-checks.json').write_text(json.dumps(checks,indent=2)+'\n')
print(json.dumps(checks,indent=2))
assert not checks['interferences'],'Resolve the reported CAD intersections before calling this fit-checked.'
