"""Render sequential assembly illustrations from the existing CAD-based scene.

blender --background --threads 6 --python hardware/prototype-a/scripts/render_assembly.py
Fasteners are nominal instructional geometry, not supplier CAD. All case/PCB
meshes come from the FreeCAD export used by tinyplc-a0.blend.
"""
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders" / "assembly"
OUT.mkdir(exist_ok=True)
ONLY = set(sys.argv[sys.argv.index("--")+1:]) if "--" in sys.argv else set()
bpy.ops.wm.open_mainfile(filepath=str(ROOT / "renders" / "tinyplc-a0.blend"))
scene = bpy.context.scene
scene.render.resolution_x = 1400
scene.render.resolution_y = 1050
scene.render.resolution_percentage = 100
scene.render.film_transparent = True
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.image_settings.color_mode = "RGBA"
scene.view_settings.view_transform = "AgX"
# Illuminate underside details without changing the source product scene.
light_data = bpy.data.lights.new("Instruction underside fill", "AREA")
light_data.energy = 420000
light_data.size = 160
light = bpy.data.objects.new("Instruction underside fill", light_data)
scene.collection.objects.link(light)
light.location = (66, 0, -180)
light.rotation_euler = (Vector((66,51,30))-light.location).to_track_quat("-Z","Y").to_euler()

def mat(name, color, metallic=0):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = 0.35
    return m

blue = mat("Instruction blue / base", (0.025, 0.28, 0.7))
gold = mat("Instruction yellow / hardware", (0.95, 0.52, 0.025), 0.3)
card = mat("Card template", (0.8, 0.63, 0.36))
dark = mat("Driver slot", (0.045, 0.055, 0.07))
teal = mat("Fit coupon", (0.015, 0.55, 0.5))

base = bpy.data.objects["base"]
lid = bpy.data.objects["lid"]
blank = bpy.data.objects["display_blank"]
board = bpy.data.objects["pcb"]
base.data.materials.clear()
base.data.materials.append(blue)
bpy.data.objects["Ground"].hide_render = True
lid_labels = [o for o in scene.objects if o.type == "FONT" and o.name != "PCB status" and o.name != "Blank label"]
blank_group = [blank, bpy.data.objects["Blank label"]]
board_group = [o for o in scene.objects if o.type in {"MESH", "FONT"} and o not in [base, lid, *blank_group, *lid_labels, bpy.data.objects["Ground"]]]
groups = {"base": [base], "lid": [lid, *lid_labels], "blank": blank_group, "board": board_group}

template = board.copy()
template.data = board.data.copy()
template.name = "Card PCB fit template"
scene.collection.objects.link(template)
template.data.materials.clear()
template.data.materials.append(card)
groups["template"] = [template]

def ring(name, x, y, z, outer, inner, height, material, sides=40):
    verts = []
    for zz, rr in [(z, outer), (z+height, outer), (z, inner), (z+height, inner)]:
        verts.extend([(x+rr*math.cos(i*math.tau/sides), y+rr*math.sin(i*math.tau/sides), zz) for i in range(sides)])
    faces = []
    for i in range(sides):
        j = (i+1) % sides
        faces.extend([(i,j,sides+j,sides+i), (2*sides+j,2*sides+i,3*sides+i,3*sides+j),
                      (sides+i,sides+j,3*sides+j,3*sides+i), (j,i,2*sides+i,2*sides+j)])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    ob = bpy.data.objects.new(name, mesh)
    scene.collection.objects.link(ob)
    ob.data.materials.append(material)
    return ob

def cyl(name, pos, radius, depth, material):
    bpy.ops.mesh.primitive_cylinder_add(vertices=40, radius=radius, depth=depth, location=pos)
    ob = bpy.context.object
    ob.name = name
    ob.data.materials.append(material)
    return ob

def screw(name, x, y, seat, diameter, length):
    # Length is measured below head; the dark cross is an illustrative drive.
    obs = [cyl(name+" shaft", (x,y,seat-length/2), diameter/2, length, gold),
           cyl(name+" head", (x,y,seat+0.9), diameter, 1.8, gold)]
    for angle in [0, math.pi/2]:
        bpy.ops.mesh.primitive_cube_add(size=1, location=(x,y,seat+1.81))
        ob = bpy.context.object
        ob.name = name+" drive"
        ob.dimensions = (diameter*1.45, 0.45, 0.035)
        ob.rotation_euler.z = angle
        ob.data.materials.append(dark)
        obs.append(ob)
    return obs

groups["board_screws"] = []
groups["board_washers"] = []
for i, (x,y) in enumerate([(11,11),(121,11),(11,91),(121,91)], 1):
    groups["board_washers"].append(ring(f"PCB washer {i}",x,y,9.6,3.2,1.6,0.5,gold))
    groups["board_screws"] += screw(f"M3x6 {i}",x,y,10.1,3,6)
groups["lid_screws"] = []
for i,(x,y) in enumerate([(3.5,3.5),(128.5,3.5),(3.5,98.5),(128.5,98.5)],1):
    groups["lid_screws"] += screw(f"M3x8 {i}",x,y,31.4,3,8)
groups["blank_screws"] = []
groups["blank_washers"] = []
groups["blank_nuts"] = []
for i,x in enumerate([62.5,101.5],1):
    groups["blank_screws"] += screw(f"M2.5x8 {i}",x,51,34.4,2.5,8)
    groups["blank_washers"].append(ring(f"Blank washer {i}",x,51,29.5,2.8,1.4,0.5,gold))
    groups["blank_nuts"].append(ring(f"Blank nut {i}",x,51,27.5,2.9,1.25,2,gold,6))

bpy.ops.wm.stl_import(filepath=str(ROOT / "mechanical" / "fit-coupon-print.stl"))
coupon = bpy.context.object
coupon.name = "Fit coupon"
coupon.data.materials.append(teal)
groups["coupon"] = [coupon]

orig = {o.name: o.location.copy() for obs in groups.values() for o in obs}
meta = {}

def render(name, visible, offsets=None, target=(66,51,25), scale=225, direction=(170,-220,270), arrows=None, points=None):
    light.hide_render = name != "06-under-lid"
    for group, objects in groups.items():
        offset = Vector((offsets or {}).get(group, (0,0,0)))
        for ob in objects:
            ob.hide_render = group not in visible
            ob.hide_set(group not in visible)
            ob.location = orig[ob.name]+offset
    cam = scene.camera
    cam.location = Vector(target)+Vector(direction)
    cam.rotation_euler = (Vector(target)-cam.location).to_track_quat("-Z","Y").to_euler()
    cam.data.ortho_scale = scale
    bpy.context.view_layer.update()
    def project(pos):
        co = world_to_camera_view(scene,cam,Vector(pos))
        return [round(co.x,5),round(1-co.y,5)]
    meta[name] = {"arrows": [[project(a),project(b)] for a,b in (arrows or [])],
                  "points": {k:project(p) for k,p in (points or {}).items()}}
    scene.render.filepath = str(OUT/(name+".png"))
    if not ONLY or name in ONLY:
        bpy.ops.render.render(write_still=True)
    print("ASSEMBLY_FRAME", name, flush=True)

case = ["base","board","board_screws","board_washers"]
cover = ["lid","blank","blank_screws","blank_washers","blank_nuts"]
render("00-overview",case+cover+["lid_screws"],
       {"board":(0,0,23),"board_screws":(0,0,23),"board_washers":(0,0,23),
        **{g:(0,0,61) for g in cover},"lid_screws":(0,0,77)},
       target=(66,51,46),scale=300)
render("01-coupon",["coupon"],target=(25,12,2.5),scale=69,
       points={"2.5 mm / tap trial":(7,12,5),"3.2 mm":(24,12,5),"3.4 mm":(41,12,5)})
render("02-base",["base"],target=(66,51,12),scale=240,direction=(60,-80,350),
       points={"PCB posts":(11,11,8),"Lid towers":(128.5,3.5,30),"DI edge":(40,0,16),"USB access":(132,49,15)})
render("03-template",["base","template"],{"template":(0,0,35)},target=(66,51,22),scale=210,
       arrows=[((11,11,42),(11,11,9)),((121,91,42),(121,91,9))])
render("04-board",["base","board"],{"board":(0,0,38)},target=(66,51,30),scale=225,
       arrows=[((11,11,45),(11,11,9)),((121,91,45),(121,91,9))],
       points={"DI row faces front openings":(46,12,62)})
render("05-board-screws",case,{"board_screws":(0,0,26),"board_washers":(0,0,14)},target=(66,51,22),scale=210,
       arrows=[((x,y,28),(x,y,12)) for x,y in [(11,11),(121,11),(11,91),(121,91)]])
render("06-blank",["lid","blank","blank_screws","blank_washers","blank_nuts"],
       {"blank":(0,0,18),"blank_screws":(0,0,32),"blank_washers":(0,0,-13),"blank_nuts":(0,0,-21)},
       target=(66,51,33),scale=200,direction=(150,-220,190),
       arrows=[((62.5,51,55),(62.5,51,35)),((101.5,51,55),(101.5,51,35))],
       points={"Washer below lid":(62.5,51,16.5),"Nut below washer":(101.5,51,7.5)})
render("06-under-lid",cover,target=(66,51,30),scale=185,direction=(50,-120,-250),
       points={"Washer + nut":(62.5,51,27),"Washer + nut ":(101.5,51,27)})
render("07-lid-ready",cover,target=(66,51,30),scale=195,
       points={"Blank closes unused display opening":(82,51,35)})
render("08-inspect",case,target=(66,51,13),scale=230,direction=(50,-100,350),
       points={"4 board screws":(11,11,12),"DI1-DI4":(46,12,24),"Q1-Q4":(46,94,24),"24 V supply":(102,94,24),"USB service port":(132,49,15)})
render("09-close",case+cover,{g:(0,0,35) for g in cover},target=(66,51,33),scale=245,
       arrows=[((3.5,3.5,62),(3.5,3.5,31)),((128.5,98.5,62),(128.5,98.5,31))])
render("10-lid-screws",case+cover+["lid_screws"],{"lid_screws":(0,0,26)},target=(66,51,25),scale=240,
       arrows=[((x,y,52),(x,y,34)) for x,y in [(3.5,3.5),(128.5,3.5),(3.5,98.5),(128.5,98.5)]],
       points={"1":(3.5,3.5,59),"2":(128.5,98.5,59),"3":(128.5,3.5,59),"4":(3.5,98.5,59)})
render("11-complete",case+cover+["lid_screws"],target=(66,51,17),scale=195)

# Per-part pictures for the inventory and the 'add these parts' panels.
for name,visible,target,scale in [
    ("part-base",["base"],(66,51,12),195),
    ("part-lid",["lid"],(66,51,30),195),
    ("part-blank",["blank"],(82,51,34),61),
    ("part-board",["board"],(66,51,12),180),
    ("part-template",["template"],(66,51,8),180),
]:
    render(name,visible,target=target,scale=scale)

(OUT/"projections.json").write_text(json.dumps(meta,indent=2)+"\n")
# Save a separate editable illustration scene, with the final assembly visible.
for group, obs in groups.items():
    for ob in obs:
        ob.location = orig[ob.name]
        ob.hide_render = group in {"template","coupon"}
        ob.hide_set(ob.hide_render)
scene.camera.location = Vector((66,51,17))+Vector((170,-220,270))
scene.camera.rotation_euler = (Vector((66,51,17))-scene.camera.location).to_track_quat("-Z","Y").to_euler()
scene.camera.data.ortho_scale = 195
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"assembly-illustrations.blend"))
print("Assembly illustrations complete.", flush=True)
