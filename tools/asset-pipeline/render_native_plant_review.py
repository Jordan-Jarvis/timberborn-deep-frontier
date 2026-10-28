"""Review exact native plant geometry/materials before placing it in buildings."""
from pathlib import Path
import sys
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from native_building_assets import prop,build_native_assembly

bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.fps=30
collection=bpy.data.collections.new('Original native plants');scene.collection.children.link(collection)
g=Geometry('Native plant review')
for i,model in enumerate(('Shrub.IronTeeth','DandelionMature','CoffeeBushMature','BlueberryBushMature','SunflowerMature')):
    prop(g,model,model,(i*1.6,0,0),1)
build_native_assembly(g,collection,1)
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.05))
ground=bpy.context.object;mat=bpy.data.materials.new('Neutral review ground');mat.diffuse_color=(.13,.14,.16,1)
ground.data.materials.append(mat)
target=Vector((-3.7,-.5,.5))
for position,energy,size in (((-1,3,7),1000,5),((-7,-4,5),700,4)):
    bpy.ops.object.light_add(type='AREA',location=position);light=bpy.context.object
    light.data.energy=energy;light.data.size=size
    light.rotation_euler=(target-light.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add();camera=bpy.context.object;scene.camera=camera;camera.data.type='ORTHO'
camera.data.ortho_scale=9.1;camera.location=target+Vector((1,7,5))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
scene.world.color=(.25,.25,.25);scene.view_settings.view_transform='AgX'
scene.render.engine='CYCLES';scene.cycles.samples=64;scene.cycles.use_denoising=True
scene.cycles.transparent_max_bounces=32
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
required=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(required)!=1:raise RuntimeError('Required RTX 2060 OptiX render device is unavailable')
for device in prefs.devices:device.use=device in required
scene.cycles.device='GPU';scene.render.resolution_x=1800;scene.render.resolution_y=650;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.filepath=str(ROOT/'outputs/reference-studies/NativePlants-original.png')
bpy.ops.render.render(write_still=True)
print('NATIVE PLANT GEOMETRY REVIEW RENDERED',flush=True)
