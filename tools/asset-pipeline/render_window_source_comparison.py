"""Inspect original New Styles facades before selecting window parts."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from native_building_assets import import_prop
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.fps=24
collection=bpy.data.collections.new('Original window source comparison');scene.collection.children.link(collection)
for i,name in enumerate(('NewStylesFlat.IronTeeth','NewStylesFoodplant.IronTeeth')):
    import_prop({'name':name,'model':name,'resource':'ReferenceOnly/'+name,'position':[i*4,0,0],'scale':1,'yaw':0},collection,1,vertex_colors=False)
target=Vector((-3,-1,1.3))
for pos,energy,size in (((1,3,6),600,5),((-5,-2,5),300,4)):
    bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=energy;o.data.size=size
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=target+Vector((4,9,4)));camera=bpy.context.object;scene.camera=camera
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=8
scene.world.color=(.18,.18,.18);scene.view_settings.view_transform='AgX'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
gpu=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(gpu)!=1:raise RuntimeError('Required RTX 2060 OptiX device unavailable')
for d in prefs.devices:d.use=d in gpu
scene.cycles.device='GPU';scene.render.resolution_x=1600;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'outputs/reference-studies/Window-source-comparison.png')
bpy.ops.render.render(write_still=True)
