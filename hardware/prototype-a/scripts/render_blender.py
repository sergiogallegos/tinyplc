"""blender --background --python hardware/prototype-a/scripts/render_blender.py

Uses tessellated FreeCAD case geometry and documented package envelopes.
Creates a native .blend and two renders; no downloaded meshes or textures.
"""
import json
import math
from pathlib import Path

import bpy
import bmesh
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[1]
P=json.loads((ROOT/"parameters.json").read_text())
G=json.loads((ROOT/"mechanical"/"render-geometry.json").read_text())
OUT=ROOT/"renders"
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system="METRIC"
scene.unit_settings.scale_length=0.001


def material(name,color,metallic=0,roughness=0.4):
    m=bpy.data.materials.new(name)
    m.diffuse_color=(*color,1)
    m.use_nodes=True
    p=m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value=(*color,1)
    p.inputs["Metallic"].default_value=metallic
    p.inputs["Roughness"].default_value=roughness
    return m


mats={"base":material("PETG - graphite",(0.055,0.072,0.092)),"lid":material("PETG - stone",(0.66,0.70,0.73)),"display_blank":material("Blank plate - orange",(0.95,0.24,0.045)),"pcb":material("PCB solder mask",(0.018,0.18,0.13)),"ic":material("IC packages",(0.025,0.03,0.035)),"terminal":material("Terminal green",(0.06,0.39,0.22)),"metal":material("Metal",(0.46,0.5,0.53),0.8,0.23),"label":material("Ink",(0.055,0.07,0.09)),"white":material("Silkscreen",(0.82,0.87,0.85)),"cap":material("Passives",(0.25,0.17,0.085)),"gold":material("Header / pads",(0.73,0.45,0.10),0.7),"floor":material("Backdrop",(0.135,0.16,0.19))}
parts={}
for p in G["parts"]:
    me=bpy.data.meshes.new(p["name"])
    me.from_pydata(p["vertices"],[],p["faces"])
    me.update()
    bm=bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00001)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces))
    bm.to_mesh(me)
    bm.free()
    me.update()
    ob=bpy.data.objects.new(p["name"],me)
    scene.collection.objects.link(ob)
    ob.data.materials.append(mats[p["name"]])
    # Keep tessellated CAD faces unchanged. Beveling their triangulation can
    # introduce seams on planar faces with holes; the source CAD has sharp edges.
    parts[p["name"]]=ob


def cube(name,center,size,mat,bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center)
    ob=bpy.context.object
    ob.name=name
    ob.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    ob.data.materials.append(mat)
    if bevel:
        m=ob.modifiers.new("Package edge","BEVEL")
        m.limit_method="ANGLE"
        m.width=bevel
        m.segments=2
    return ob


for p in G["envelopes"]:
    ref=p["ref"]
    mat=mats["terminal"] if ref in ["J1"]+[f"J{x}" for x in range(5,13)] else mats["ic"] if ref.startswith(("U","D","SW")) else mats["metal"] if ref in ["Y1","J13"] else mats["gold"] if ref.startswith("J") else mats["cap"]
    cube(ref+" - envelope",p["center"],p["size"],mat)
    if mat==mats["terminal"]:
        x,y,z=p["center"]
        for dx in [-2.54,2.54]:
            bpy.ops.mesh.primitive_cylinder_add(vertices=20,radius=1.4,depth=0.25,location=(x+dx,y,z+p["size"][2]/2+0.1))
            bpy.context.object.data.materials.append(mats["metal"])


def text(name,body,location,size,mat,align="LEFT"):
    cu=bpy.data.curves.new(name,"FONT")
    cu.body=body
    cu.size=size
    cu.extrude=0.012
    cu.align_x=align
    ob=bpy.data.objects.new(name,cu)
    scene.collection.objects.link(ob)
    ob.location=location
    ob.data.materials.append(mat)
    return ob


labels=[]
labels.append(text("Lid branding","tinyPLC",(18,76,32.43),6,mats["label"]))
labels.append(text("Lid revision","A0 / PROTOTYPE",(18,69,32.43),2.6,mats["label"]))
labels.append(text("Blank label","DISPLAY BLANK",(82,50,34.43),2.6,mats["label"],"CENTER"))
for i,x in enumerate([12,28,44,60],1):
    labels.append(text(f"DI label {i}",f"DI{i}",(x+8,13,32.43),2.3,mats["label"],"CENTER"))
    labels.append(text(f"Q label {i}",f"Q{i}",(x+8,86,32.43),2.3,mats["label"],"CENTER"))
text("PCB status","A0 / UNROUTED",(68,91,9.64),2.5,mats["white"])

cube("Ground",(66,51,-1.8),(2000,2000,3),mats["floor"],0)
world=scene.world
world.use_nodes=True
world.node_tree.nodes["Background"].inputs[0].default_value=(0.16,0.19,0.24,1)
world.node_tree.nodes["Background"].inputs[1].default_value=0.5
for name,loc,power,size in [("Key",(20,-80,220),1800000,170),("Fill",(220,140,180),1200000,150),("Rim",(-90,150,130),1700000,100)]:
    data=bpy.data.lights.new(name,"AREA")
    data.energy=power*0.35
    data.shape="DISK"
    data.size=size
    ob=bpy.data.objects.new(name,data)
    scene.collection.objects.link(ob)
    ob.location=loc
    ob.rotation_euler=(Vector((66,51,20))-ob.location).to_track_quat("-Z","Y").to_euler()
bpy.ops.object.camera_add(location=(245,-210,230))
camera=bpy.context.object
camera.rotation_euler=(Vector((66,51,22))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.type="ORTHO"
camera.data.ortho_scale=200
scene.camera=camera
scene.render.engine="CYCLES"
scene.cycles.device="CPU"
scene.cycles.samples=P["render"]["samples"]
scene.render.resolution_x=P["render"]["width"]
scene.render.resolution_y=P["render"]["height"]
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.view_settings.view_transform="AgX"
scene.render.filepath=str(OUT/"tinyplc-a0-assembled.png")
if hasattr(bpy.context.preferences.filepaths,"save_preview_images"):
    bpy.context.preferences.filepaths.save_preview_images=False
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"tinyplc-a0.blend"))
bpy.ops.render.render(write_still=True)
# Explode vertically; all positions derive from the same FreeCAD assembly.
for name in ["lid","display_blank"]:
    parts[name].location.z+=48
for ob in labels:
    ob.location.z+=48
camera.location=(255,-235,270)
camera.rotation_euler=(Vector((66,51,45))-camera.location).to_track_quat("-Z","Y").to_euler()
camera.data.ortho_scale=220
scene.render.filepath=str(OUT/"tinyplc-a0-exploded.png")
bpy.ops.render.render(write_still=True)
print("Saved native Blender assembly and two geometry-based previews.")
