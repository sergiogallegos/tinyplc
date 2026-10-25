#!/usr/bin/env python3
"""Generate native FreeCAD solids, print meshes, assembly STEP and inspection data.

Run with system Python, using the installed FreeCAD libraries. Case dimensions
are in a native spreadsheet and solids remain editable Boolean feature trees.
"""
import json
import math
import re
from pathlib import Path
import sys

sys.path.append("/usr/lib/freecad/lib")
import FreeCAD as App
import Part
import MeshPart

ROOT = Path(__file__).resolve().parents[1]
P = json.loads((ROOT / "parameters.json").read_text())
OUT = ROOT / "mechanical"
OUT.mkdir(exist_ok=True)
DOC = App.newDocument("tinyPLC_A0")
S = DOC.addObject("Spreadsheet::Sheet", "Dimensions")
for row,(name,value) in enumerate({"CaseWidth":132,"CaseDepth":102,"BaseHeight":30,"Wall":2.4,"Floor":2.4,"LidThickness":2.4,"BoardWidth":120,"BoardDepth":90,"BoardThickness":1.6,"BoardBottom":8,"BoardOffset":6,"PostDiameter":7,"PilotDiameter":2.5,"LidFitGap":0.3}.items(),1):
    S.set(f"A{row}",name)
    S.set(f"B{row}",f"{value} mm")
    S.setAlias(f"B{row}",name)
S.set("A17","Edit spreadsheet dimensions; regenerate drawings after edits")


def expr(obj, key, val):
    if isinstance(val,str):
        obj.setExpression(key,val)
    else:
        setattr(obj,key,val)


def box(name,size,pos):
    o=DOC.addObject("Part::Box",name)
    for key,val in zip(["Length","Width","Height"],size):
        expr(o,key,val)
    for key,val in zip(["x","y","z"],pos):
        if isinstance(val,str):
            o.setExpression("Placement.Base."+key,val)
        else:
            setattr(o.Placement.Base,key,val)
    return o


def cylinder(name,radius,height,pos):
    o=DOC.addObject("Part::Cylinder",name)
    expr(o,"Radius",radius)
    expr(o,"Height",height)
    o.Placement.Base=App.Vector(*pos)
    return o


def cut(name,base,tool):
    o=DOC.addObject("Part::Cut",name)
    o.Base=base
    o.Tool=tool
    o.Refine=True
    base.Visibility=False
    tool.Visibility=False
    return o


def union(name,objects):
    o=DOC.addObject("Part::MultiFuse",name)
    o.Shapes=objects
    o.Refine=True
    for ob in objects:
        ob.Visibility=False
    return o


base=cut("Hollow_shell",box("Outside",["Dimensions.CaseWidth","Dimensions.CaseDepth","Dimensions.BaseHeight"],[0,0,0]),box("Cavity",["Dimensions.CaseWidth-2*Dimensions.Wall","Dimensions.CaseDepth-2*Dimensions.Wall","Dimensions.BaseHeight"],["Dimensions.Wall","Dimensions.Wall","Dimensions.Floor"]))
posts=[]
for i,(x,y) in enumerate(P["pcb"]["holes"],1):
    x,y=x+6,y+6
    post=cylinder(f"PCB_post_{i}","Dimensions.PostDiameter/2","Dimensions.BoardBottom-Dimensions.Floor",[x,y,2.4])
    # Pilot continues down to floor; M3x6 must not bottom out.
    post=cut(f"PCB_post_pilot_{i}",post,cylinder(f"PCB_pilot_tool_{i}","Dimensions.PilotDiameter/2",8,[x,y,1]))
    posts.append(post)
base=union("Base_with_PCB_posts",[base]+posts)
# Four lid screw towers separated from board supports.
lid_xy=[(3.5,3.5),(128.5,3.5),(3.5,98.5),(128.5,98.5)]
towers=[]
for i,(x,y) in enumerate(lid_xy,1):
    tower=cylinder(f"Lid_tower_{i}",3.1,27.6,[x,y,2.4])
    tower=cut(f"Lid_tower_pilot_{i}",tower,cylinder(f"Lid_pilot_tool_{i}",1.25,10,[x,y,22]))
    towers.append(tower)
base=union("Base_with_lid_towers",[base]+towers)
# Terminal openings align to shared PCB placement coordinates. Full height band
# gives horizontal wire entry; lid-off access is used for terminal screws.
for i,x in enumerate([12,28,44,60],1):
    # Top row terminals are rotated 180 degrees; pin-1 anchoring changes center.
    base=cut(f"DI{i}_opening",base,box(f"DI{i}_cut_tool",[12,9,16],[6+x+4+(2 if i==1 else 0)-2.54-6,-1,9]))
    base=cut(f"Q{i}_opening",base,box(f"Q{i}_cut_tool",[12,9,16],[6+x+2.54-6,94,9]))
base=cut("Power_opening",base,box("Power_cut_tool",[12,9,16],[6+94+2.54-6,94,9]))
# Large open service port: permits access to recessed USB connector, boot and UART.
base=cut("USB_service_opening",base,box("USB_cut_tool",[10,19,10],[125,6+43-9.5,7]))
base.Label="01 Base - print floor down; terminals and USB access"

lid=box("Lid_plate",["Dimensions.CaseWidth","Dimensions.CaseDepth","Dimensions.LidThickness"],[0,0,"Dimensions.BaseHeight"])
lip_outer=box("Lip_outside",["Dimensions.CaseWidth-2*(Dimensions.Wall+Dimensions.LidFitGap)","Dimensions.CaseDepth-2*(Dimensions.Wall+Dimensions.LidFitGap)",1.8],["Dimensions.Wall+Dimensions.LidFitGap","Dimensions.Wall+Dimensions.LidFitGap",28.2])
lip_inner=box("Lip_inside",[123.4,93.4,2],[4.3,4.3,28.1])
lip=cut("Locating_lip",lip_outer,lip_inner)
# Clear the lip around screw towers rather than intersecting them.
for i,(x,y) in enumerate(lid_xy,1):
    lip=cut(f"Lip_screw_clearance_{i}",lip,cylinder(f"Lip_clearance_tool_{i}",3.45,3,[x,y,28]))
lid=union("Lid_with_lip",[lid,lip])
for i,(x,y) in enumerate(lid_xy,1):
    lid=cut(f"Lid_through_hole_{i}",lid,cylinder(f"Lid_hole_tool_{i}",1.7,6,[x,y,28]))
    lid=cut(f"Lid_counterbore_{i}",lid,cylinder(f"Counterbore_tool_{i}",3.1,1,[x,y,31.4]))
cx,cy=P["display"]["center"]
lid=cut("Display_aperture",lid,box("Window_tool",[30,18,6],[cx-15,cy-9,28]))
for i,x in enumerate([cx-19.5,cx+19.5],1):
    lid=cut(f"Blank_mount_hole_{i}",lid,cylinder(f"Blank_screw_tool_{i}",1.4,5,[x,cy,29]))
# Sideways vents intentionally omitted until heat measurements; closed lid is printable.
lid.Label="02 Lid - removable; optional display opening with blank"
cover=box("Display_blank",[46,26,2],[cx-23,cy-13,32.4])
for i,x in enumerate([cx-19.5,cx+19.5],1):
    cover=cut(f"Blank_hole_{i}",cover,cylinder(f"Blank_hole_tool_{i}",1.4,4,[x,cy,31.5]))
cover.Label="03 Display blank - remove for a future display adapter"

# PCB and package envelopes: own geometry, not vendor precision STEP models.
board=box("PCB_slab",[120,90,1.6],[6,6,8])
for i,(x,y) in enumerate(P["pcb"]["holes"],1):
    board=cut(f"PCB_hole_{i}",board,cylinder(f"Board_hole_tool_{i}",1.6,3,[x+6,y+6,7.5]))
board.Label="PCB envelope - 120 x 90 x 1.6; pads on underside need clearance"
components=json.loads((ROOT/"bom"/"components.json").read_text())
envelopes=[]
envelope_data=[]
for p in components:
    ref=p["ref"]
    if ref.startswith(("TP","H")):
        continue
    footprint=p["original_footprint"]
    # Conservative package bounding boxes with documented simplification.
    if "TerminalBlock" in footprint:
        sx,sy,sz=10.2,9.8,13.8
        dx,dy=2.54,-0.3
    elif ref=="U1":
        sx,sy,sz,dx,dy=12.5,12.5,1.6,0,0
    elif ref=="U2":
        sx,sy,sz,dx,dy=11.7,7.5,10.6,2.54,-1.75
    elif ref=="U3":
        sx,sy,sz,dx,dy=6.2,10.2,1.8,0,0
    elif "DIP-4" in footprint:
        sx,sy,sz,dx,dy=10.2,5.0,4.6,3.81,1.27
    elif ref=="J13":
        sx,sy,sz,dx,dy=9.2,7.35,3.4,0,1.5
    elif ref.startswith("J"):
        n=int(re.search(r"1x(\d+)",footprint).group(1)) if "1x" in footprint else 3
        sx,sy,sz,dx,dy=2.6,n*2.54,8.5,0,(n-1)*1.27
    elif ref.startswith("SW"):
        sx,sy,sz,dx,dy=6.5,6.5,5,3.25,2.25
    elif ref=="F1":
        sx,sy,sz,dx,dy=10.3,3.6,12,2.54,0
    elif ref=="C1":
        sx,sy,sz,dx,dy=6.3,6.3,12,1.25,0
    elif ref=="Y1":
        sx,sy,sz,dx,dy=5,3.2,1.3,0,0
    elif ref=="D1":
        sx,sy,sz,dx,dy=5.2,2.8,2.2,0,0
    elif ref=="U8":
        sx,sy,sz,dx,dy=3.1,3,1.2,0,0
    else:
        sx,sy,sz,dx,dy=2.1,1.4,1,0,0
    theta=math.radians(p["angle"])
    # KiCad xy down, FreeCAD xy here also uses board coordinates (view mirrored by camera).
    x=p["xy"][0]+6+dx*math.cos(theta)+dy*math.sin(theta)
    y=p["xy"][1]+6-dx*math.sin(theta)+dy*math.cos(theta)
    if p["angle"] in [90,270]:
        sx,sy=sy,sx
    envelope=box("Package_"+ref,[sx,sy,sz],[x-sx/2,y-sy/2,9.6])
    envelope.Label=f'{ref}: {p["value"]} (envelope only)'
    envelopes.append(envelope)
    envelope_data.append(dict(ref=ref,center=[x,y,9.6+sz/2],size=[sx,sy,sz],purpose=p["purpose"]))

DOC.recompute()
checks={"units":"mm","status":"CAD checks only; no physical fit test", "solids":{},"interferences":[],"component_count":len(envelopes)}
for name,obj in [("base",base),("lid",lid),("display_blank",cover),("pcb",board)]:
    assert obj.Shape.isValid(), name
    assert len(obj.Shape.Solids)==1,(name,len(obj.Shape.Solids))
    checks["solids"][name]={"valid":True,"volume_mm3":round(obj.Shape.Volume,3),"solid_count":len(obj.Shape.Solids)}
for name,a,b in [("base-pcb",base,board),("base-lid",base,lid),("lid-pcb",lid,board),("lid-blank",lid,cover)]:
    vol=a.Shape.common(b.Shape).Volume
    checks["interferences"].append({"pair":name,"volume_mm3":round(vol,6)})
    assert vol<0.001,(name,vol)
for ob,p in zip(envelopes,envelope_data):
    for name,casepart in [("base",base),("lid",lid)]:
        vol=ob.Shape.common(casepart.Shape).Volume
        if vol>0.001:
            checks["interferences"].append({"pair":p["ref"]+"-"+name,"volume_mm3":round(vol,6)})

# Explicit print transforms: all print meshes rest at Z=0. Lid outside face down.
print_shapes={"base":base.Shape.copy(),"lid":lid.Shape.copy(),"display-blank":cover.Shape.copy()}
print_shapes["lid"].rotate(App.Vector(0,0,0),App.Vector(1,0,0),180)
for name,shape in print_shapes.items():
    bb=shape.BoundBox
    shape.translate(App.Vector(-bb.XMin,-bb.YMin,-bb.ZMin))
    mesh=MeshPart.meshFromShape(Shape=shape,LinearDeflection=0.06,AngularDeflection=0.15,Relative=False)
    mesh.write(str(OUT/(name+"-print.stl")))
    checks["solids"][name.replace("-","_")]["print_mesh_closed"]=mesh.isSolid()
    Part.export([{"base":base,"lid":lid,"display-blank":cover}[name]],str(OUT/(name+".step")))

# Tessellate assembled parts for Blender from actual FreeCAD geometry.
render_meshes=[]
for name,obj in [("base",base),("lid",lid),("display_blank",cover),("pcb",board)]:
    verts,faces=obj.Shape.tessellate(0.12)
    render_meshes.append(dict(name=name,vertices=[[v.x,v.y,v.z] for v in verts],faces=faces))
(OUT/"render-geometry.json").write_text(json.dumps({"parts":render_meshes,"envelopes":envelope_data},separators=(",",":"))+"\n")
Part.export([base,lid,cover,board]+envelopes,str(OUT/"tinyplc-a0-assembly.step"))
DOC.recompute()
DOC.saveAs(str(OUT/"tinyplc-a0.FCStd"))
(ROOT/"reports"/"mechanical-checks.json").write_text(json.dumps(checks,indent=2)+"\n")
print(json.dumps(checks,indent=2))
