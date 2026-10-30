"""Render the actual shipped terrace to measure its railing style, not a guess."""
import sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from native_building_assets import import_prop
bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
scene=bpy.context.scene;scene.render.fps=30
collection=bpy.data.collections.new('Native terrace reference');scene.collection.children.link(collection)
for i,name in enumerate(('DistrictCenter.IronTeeth',)):
    import_prop({'name':name,'model':name,'resource':'ReferenceOnly/'+name,'position':[i*4,0,0],'scale':1,'yaw':0},collection,1)
target=Vector((-1.5,-1.5,2))
for pos,energy,size in (((1,3,6),450,4),((-5,-2,5),250,3)):
    bpy.ops.object.light_add(type='AREA',location=pos);o=bpy.context.object;o.data.energy=energy;o.data.size=size
    o.rotation_euler=(target-o.location).to_track_quat('-Z','Y').to_euler()
bpy.ops.object.camera_add(location=target+Vector((5,7,4)));camera=bpy.context.object;scene.camera=camera
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler();camera.data.type='ORTHO';camera.data.ortho_scale=6.0
scene.world.color=(.18,.18,.18);scene.view_settings.view_transform='AgX'
scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
gpu=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(gpu)!=1:raise RuntimeError('Required RTX 2060 OptiX device unavailable')
for d in prefs.devices:d.use=d in gpu
scene.cycles.device='GPU';scene.render.resolution_x=1100;scene.render.resolution_y=900;scene.render.resolution_percentage=100
# Denoise on the GPU too: OIDN on the CPU used ~85 of the ~95 CPU-seconds of a 1200 px render.
if not prefs.has_oidn_gpu_devices():raise RuntimeError('RTX 2060 OIDN GPU denoising unavailable')
scene.cycles.denoising_use_gpu=True
scene.render.image_settings.file_format='PNG';scene.render.filepath=str(ROOT/'outputs/reference-studies/NativeDistrict-facade-reference.png')
bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/'outputs/native-civic-assets/District-reference.blend'))
