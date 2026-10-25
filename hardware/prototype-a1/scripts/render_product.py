"""blender --background -noaudio --threads 6 --python .../render_product.py

CAD-derived product and assembly photography. OLED content is a UI proposal,
not a capture from working hardware. Optional -- frame names re-render a subset.
"""
import json
import math
from pathlib import Path
import sys
import bpy
import bmesh
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'renders';OUT.mkdir(exist_ok=True)
P=json.loads((ROOT/'parameters.json').read_text())
G=json.loads((ROOT/'mechanical/render-geometry.json').read_text())
ONLY=set(sys.argv[sys.argv.index('--')+1:]) if '--' in sys.argv else set()
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene
scene.unit_settings.system='METRIC';scene.unit_settings.scale_length=0.001

def material(name,color,metallic=0,rough=0.4,emit=0):
    m=bpy.data.materials.new(name);m.diffuse_color=(*color,1);m.use_nodes=True
    s=m.node_tree.nodes.get('Principled BSDF');s.inputs['Base Color'].default_value=(*color,1)
    s.inputs['Metallic'].default_value=metallic;s.inputs['Roughness'].default_value=rough
    if emit:s.inputs['Emission Color'].default_value=(*color,1);s.inputs['Emission Strength'].default_value=emit
    return m

mats={'base':material('Warm matte white polymer',(0.84,0.86,0.86),0,0.31),
      'lid':material('Porcelain white polymer',(0.91,0.92,0.91),0,0.27),
      'lens':material('Reverse-masked clear lens',(0.009,0.013,0.018),0.15,0.19),
      'pcb':material('Dark green solder mask',(0.012,0.105,0.064),0,0.5),
      'oled_pcb':material('OLED module black PCB',(0.018,0.022,0.027)),
      'oled_glass':material('OLED glass',(0.005,0.008,0.009),0.15,0.18),
      'rod_run':material('Clear light guide',(0.55,0.75,0.70),0,0.2),
      'switch':material('Switch nylon',(0.018,0.021,0.025),0,0.42),
      'metal':material('Satin hardware',(0.45,0.49,0.52),0.75,0.25),
      'trim':material('Silver finish accent / cosmetic',(0.46,0.5,0.53),0.6,0.26),
      'ink':material('Applied graphite labels',(0.13,0.17,0.20),0,0.7),
      'light_ink':material('Soft white markings',(0.6,0.66,0.69),0,0.65),
      'chip':material('IC packages',(0.025,0.032,0.036)),
      'terminal':material('Terminal block green',(0.04,0.26,0.13)),
      'gold':material('Connector metal',(0.6,0.38,0.10),0.6),
      'passive':material('Ceramic',(0.25,0.19,0.13)),
      'pwr':material('PWR green light',(0.08,0.8,0.35),0,0.35,1.5),
      'run':material('RUN green light',(0.08,0.8,0.35),0,0.35,1.1),
      'floor':material('Studio grey',(0.68,0.71,0.73),0,0.65)}
mats['rod_pwr']=mats['rod_run']
groups={};parts={}
def register(ob,group):groups.setdefault(group,[]).append(ob);return ob
for part in G['parts']:
    mesh=bpy.data.meshes.new(part['name']);mesh.from_pydata(part['vertices'],[],part['faces']);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh);bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=0.00001);bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    ob=bpy.data.objects.new(part['name'],mesh);scene.collection.objects.link(ob);ob.data.materials.append(mats[part['name']]);parts[part['name']]=register(ob,part['name'])

def cube(name,center,size,mat,group,bevel=0.15):
    bpy.ops.mesh.primitive_cube_add(size=1,location=center);ob=bpy.context.object;ob.name=name;ob.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True);ob.data.materials.append(mat)
    if bevel:
        mod=ob.modifiers.new('Soft manufactured edges','BEVEL');mod.width=bevel;mod.segments=3
    return register(ob,group)

def cylinder(name,center,r,h,mat,group):
    bpy.ops.mesh.primitive_cylinder_add(vertices=40,radius=r,depth=h,location=center)
    ob=bpy.context.object;ob.name=name;ob.data.materials.append(mat);return register(ob,group)

def text(body,pos,size,mat,group,align='CENTER',rotation=(0,0,0)):
    data=bpy.data.curves.new(body,'FONT');data.body=body;data.size=size;data.align_x=align;data.extrude=0.004
    ob=bpy.data.objects.new(body,data);scene.collection.objects.link(ob);ob.location=pos;ob.rotation_euler=rotation;ob.data.materials.append(mat);return register(ob,group)

for env in G['envelopes']:
    ref=env['ref']
    m=mats['terminal'] if ref=='J1' or ref=='J17' or ref in [f'J{i}' for i in range(5,13)] else mats['chip'] if ref.startswith(('U','D','SW')) else mats['metal'] if ref in ['J13','Y1'] else mats['gold'] if ref.startswith('J') else mats['passive']
    cube(ref+' package',env['center'],env['size'],m,'pcb')
    if m==mats['terminal']:
        x,y,z=env['center']
        for dx in [-2.54,2.54]:cylinder(ref+' screw',(x+dx,y,z+env['size'][2]/2+0.12),1.3,0.24,mats['metal'],'pcb')
text('A1 / PROTOTYPE',(78,96,9.65),2.1,mats['light_ink'],'pcb')

# Cosmetic silver seam follows the real rounded perimeter, with no metal chassis claim.
verts=[]
for z,w,d,r in [(33.2,140.08,110.08,7.04),(33.8,140.08,110.08,7.04),(33.2,139.96,109.96,6.98),(33.8,139.96,109.96,6.98)]:
    for cx,cy,start in [(w/2-r,d/2-r,0),(-w/2+r,d/2-r,90),(-w/2+r,-d/2+r,180),(w/2-r,-d/2+r,270)]:
        for i in range(12):
            a=math.radians(start+i*90/12);verts.append((70+cx+r*math.cos(a),55+cy+r*math.sin(a),z))
faces=[];n=48
for i in range(n):
    j=(i+1)%n
    faces.extend([(i,j,n+j,n+i),(n+i,n+j,3*n+j,3*n+i),(2*n+j,2*n+i,3*n+i,3*n+j),(j,i,2*n+i,2*n+j)])
me=bpy.data.meshes.new('Silver seam');me.from_pydata(verts,[],faces);me.update();ob=bpy.data.objects.new('Cosmetic silver seam',me);scene.collection.objects.link(ob);ob.data.materials.append(mats['trim']);register(ob,'base')

# Real interface locations; lettering is an applied label set supplied as SVG.
text('tinyPLC',(70,84,37.03),4.3,mats['ink'],'lid')
text('A1  /  RESEARCH CONTROLLER',(70,79.5,37.03),1.25,mats['ink'],'lid')
text('PWR',(52,56.3,37.04),1.25,mats['light_ink'],'lens',align='LEFT')
text('RUN',(52,52.3,37.04),1.25,mats['light_ink'],'lens',align='LEFT')
for y,g in [(57,'pwr'),(53,'run')]:cylinder(g+' optical spot',(49,y,37.025),0.8,0.035,mats[g],'lens')
for env in G['envelopes']:
    ref=env['ref'];x,y,z=env['center']
    if ref in [f'J{i}' for i in range(5,9)]:
        ch=int(ref[1:])-4;text('DI'+str(ch),(x,7.0,37.03),2.1,mats['ink'],'lid')
        # Rotated input terminal: pad 1 is right (+ input), pad 2 left (0V).
        text('0V  +',(x,3.7,37.03),1.3,mats['ink'],'lid')
    elif ref in [f'J{i}' for i in range(9,13)]:
        ch=int(ref[1:])-8;text('Q'+str(ch),(x,103,37.03),2.1,mats['ink'],'lid',rotation=(0,0,math.pi))
        text('Q  +24',(x,106.3,37.03),1.25,mats['ink'],'lid',rotation=(0,0,math.pi))
text('24 V DC',(106.54,101,37.03),2.4,mats['ink'],'lid',rotation=(0,0,math.pi))
text('+',(104,105,37.03),2,mats['ink'],'lid',rotation=(0,0,math.pi))
text('-',(109.08,105,37.03),2,mats['ink'],'lid',rotation=(0,0,math.pi))
text('- 0V/GND  |  +24V',(106.54,110.025,5.1),1.7,mats['ink'],'base',rotation=(math.pi/2,0,math.pi))
text('24 V DC INPUT',(106.54,110.025,28.3),2,mats['ink'],'base',rotation=(math.pi/2,0,math.pi))
text('USB / SERVICE',(140.025,53,27.5),1.8,mats['ink'],'base',rotation=(math.pi/2,0,math.pi/2))
text('POWER',(0-0.025,49,7.5),1.7,mats['ink'],'base',rotation=(math.pi/2,0,-math.pi/2))
cube('SW3 external bezel',(-1,49,22),(2,15,20.83),mats['switch'],'switch',0.8)
cube('SW3 rocker',(-2.3,49,22),(2.5,9.9,14.76),mats['switch'],'switch',0.8)
text('I',(-3.6,49,26),2.8,mats['light_ink'],'switch',rotation=(math.pi/2,0,-math.pi/2))
text('O',(-3.6,49,17),2.4,mats['light_ink'],'switch',rotation=(math.pi/2,0,-math.pi/2))

def screw(name,x,y,seat,length,diam,group,up=False):
    sign=1 if up else -1
    cylinder(name+' shaft',(x,y,seat+sign*length/2),diam/2,length,mats['metal'],group)
    cylinder(name+' head',(x,y,seat-sign*0.85),diam,1.7,mats['metal'],group)
    for rot in [0,math.pi/2]:
        ob=cube(name+' drive',(x,y,seat-sign*1.71),(diam*1.2,0.4,0.03),mats['chip'],group,0);ob.rotation_euler.z=rot
for i,(x,y) in enumerate([(15,15),(125,15),(15,95),(125,95)]):
    cylinder('PCB washer',(x,y,9.85),3.2,0.5,mats['metal'],'pcb_screws');screw('PCB M3x6',x,y,10.1,6,3,'pcb_screws')
for x,y in [(7,7),(133,7),(7,103),(133,103)]:screw('Lid M3x10',x,y,1.5,10,3,'bottom_screws',True)
for hx,hy in P['display']['holes']:
    x,y=58.395+hx,35.599+hy
    cylinder('OLED M2 washer',(x,y,26.75),2.2,0.5,mats['metal'],'oled_screws');screw('OLED M2x6',x,y,26.5,6,2,'oled_screws',True)
for x,y in [(20,6),(120,6),(20,104),(120,104)]:cylinder('Adhesive foot',(x,y,-1),4,2,mats['switch'],'feet')

# Actual 128x64 pixel artwork generated by make_status_art.py.
screen_mat=bpy.data.materials.new('OLED UI / illustrative demo');screen_mat.use_nodes=True
nodes=screen_mat.node_tree.nodes;nodes.clear();out=nodes.new('ShaderNodeOutputMaterial');em=nodes.new('ShaderNodeEmission');em.inputs['Strength'].default_value=1.1
tex=nodes.new('ShaderNodeTexImage');tex.image=bpy.data.images.load(str(OUT/'status-run.png'));tex.interpolation='Closest'
screen_mat.node_tree.links.new(tex.outputs['Color'],em.inputs['Color']);screen_mat.node_tree.links.new(em.outputs[0],out.inputs[0])
bpy.ops.mesh.primitive_plane_add(size=1,location=(73,55,37.035));screen=bpy.context.object;screen.name='128x64 status demo';screen.dimensions=(21.744,10.864,1);screen.data.materials.append(screen_mat);register(screen,'lens')
screen.rotation_euler.z=0

floor=cube('Studio floor',(70,55,-3.1),(2000,2000,2),mats['floor'],'floor',0)
world=scene.world;world.use_nodes=True;world.node_tree.nodes['Background'].inputs[0].default_value=(0.74,0.80,0.87,1);world.node_tree.nodes['Background'].inputs[1].default_value=0.32
for name,loc,power,size in [('Key',(30,-90,230),350000,180),('Fill',(230,120,180),180000,170),('Edge',(-120,180,140),260000,100),('Under',(60,-40,-180),180000,160)]:
    data=bpy.data.lights.new(name,'AREA');data.energy=power;data.shape='DISK';data.size=size
    ob=bpy.data.objects.new(name,data);scene.collection.objects.link(ob);ob.location=loc;ob.rotation_euler=(Vector((70,55,20))-ob.location).to_track_quat('-Z','Y').to_euler()
    if name=='Under':under=ob
bpy.ops.object.camera_add(location=(260,-210,240));camera=bpy.context.object;camera.data.type='ORTHO';scene.camera=camera
scene.render.engine='CYCLES';scene.cycles.samples=40;scene.cycles.use_denoising=True
scene.render.resolution_x=1800;scene.render.resolution_y=1300;scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.render.image_settings.color_mode='RGBA'
scene.view_settings.view_transform='AgX'
original={o.name:o.location.copy() for obs in groups.values() for o in obs}
meta={}
if (OUT/'projections.json').exists():meta=json.loads((OUT/'projections.json').read_text())
all_groups=list(groups)
top=['lid','lens','oled_pcb','oled_glass','rod_run','rod_pwr','oled_screws']

def render(name,visible=None,offsets=None,target=(70,55,18),direction=(180,-235,230),scale=250,arrows=None,transparent=False):
    for group,objects in groups.items():
        for ob in objects:
            ob.location=original[ob.name]+Vector((offsets or {}).get(group,(0,0,0)))
            ob.hide_render=group not in (visible or all_groups) or (transparent and group=='floor')
            ob.hide_set(ob.hide_render)
    under.hide_render=direction[2]>=0
    camera.location=Vector(target)+Vector(direction);camera.rotation_euler=(Vector(target)-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.ortho_scale=scale
    scene.render.film_transparent=transparent;bpy.context.view_layer.update()
    def project(p):
        v=world_to_camera_view(scene,camera,Vector(p));return [v.x,1-v.y]
    meta[name]={'arrows':[[project(a),project(b)] for a,b in (arrows or [])]}
    if not ONLY or name in ONLY:
        scene.render.filepath=str(OUT/(name+'.png'));bpy.ops.render.render(write_still=True)
    print('PRODUCT_FRAME',name,flush=True)

render('hero-white')
render('rear-power',direction=(-180,235,190),scale=245)
render('status-detail',target=(70,55,36),direction=(0,-50,280),scale=100,transparent=True)
render('underside',direction=(160,-200,-240),scale=245,transparent=True)
render('exploded',offsets={**{g:(0,0,65) for g in top},'lens':(0,0,83),'pcb':(0,0,18),'pcb_screws':(0,0,18)},target=(70,55,48),scale=320,transparent=True)
render('step-base',visible=['base','feet'],scale=240,transparent=True,direction=(60,-90,350))
render('step-switch',visible=['base','switch','feet'],scale=240,transparent=True,direction=(-220,-100,240))
render('step-board',visible=['base','switch','pcb','feet'],offsets={'pcb':(0,0,38)},target=(70,55,30),scale=260,transparent=True,
       arrows=[((15,15,45),(15,15,9)),((125,95,45),(125,95,9))])
render('step-board-screws',visible=['base','pcb','pcb_screws','switch'],offsets={'pcb_screws':(0,0,26)},scale=240,transparent=True,
       arrows=[((x,y,31),(x,y,11)) for x,y in [(15,15),(125,15),(15,95),(125,95)]])
render('step-lid',visible=top,target=(70,55,27),direction=(100,-160,-300),scale=230,transparent=True)
render('step-optics',visible=['lid','lens','rod_run','rod_pwr'],offsets={'lens':(0,0,18),'rod_run':(0,0,12),'rod_pwr':(0,0,12)},target=(70,55,28),scale=245,transparent=True,
       arrows=[((49,53,48),(49,53,36)),((49,57,48),(49,57,36))])
render('step-close',offsets={g:(0,0,35) for g in top},target=(70,55,30),scale=280,transparent=True,
       arrows=[((7,7,65),(7,7,35)),((133,103,65),(133,103,35))])
render('step-bottom-screws',offsets={'bottom_screws':(0,0,-22)},target=(70,55,12),direction=(160,-200,-240),scale=270,transparent=True,
       arrows=[((x,y,-19),(x,y,0)) for x,y in [(7,7),(133,7),(7,103),(133,103)]])
# Silver is a finish study of the same polymer case, not an aluminum enclosure.
for name in ['base','lid']:
    bs=mats[name].node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(0.40,0.44,0.48,1);bs.inputs['Metallic'].default_value=0.32
render('hero-silver')
for name,color in [('base',(0.84,0.86,0.86,1)),('lid',(0.91,0.92,0.91,1))]:
    bs=mats[name].node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=color;bs.inputs['Metallic'].default_value=0
tex.image=bpy.data.images.load(str(OUT/'status-off.png'))
for name in ['pwr','run']:
    bs=mats[name].node_tree.nodes.get('Principled BSDF');bs.inputs['Emission Strength'].default_value=0;bs.inputs['Base Color'].default_value=(0.008,0.025,0.012,1)
render('power-off')
tex.image=bpy.data.images.load(str(OUT/'status-fault.png'))
mats['pwr'].node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=1.5
mats['pwr'].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(0.08,0.8,0.35,1)
render('fault-detail',target=(70,55,36),direction=(0,-50,280),scale=100,transparent=True)
tex.image=bpy.data.images.load(str(OUT/'status-run.png'));mats['run'].node_tree.nodes.get('Principled BSDF').inputs['Emission Strength'].default_value=1.1
mats['run'].node_tree.nodes.get('Principled BSDF').inputs['Base Color'].default_value=(0.08,0.8,0.35,1)
# Restore the default opening view without rendering again.
saved=ONLY;ONLY={'__save_only__'};render('hero-white');ONLY=saved
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tinyplc-a1.blend'))
bpy.ops.file.pack_all()
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/'tinyplc-a1.blend'))
(OUT/'projections.json').write_text(json.dumps(meta,indent=2)+'\n')
print('Product scene and views complete.',flush=True)
