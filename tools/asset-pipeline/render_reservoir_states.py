"""Review authored reservoir heights. These images are not gameplay evidence."""
import json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
ident='FisheryWorks';out=ROOT/'outputs/reference-studies'
assembly=json.loads((out/(ident+'-native-assembly.json')).read_text())
collection=bpy.data.collections[ident+'.ReferenceStudy'];scene=bpy.context.scene
scene.frame_set(1);scene.cycles.samples=64
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
devices=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(devices)!=1:raise RuntimeError('RTX 2060 OptiX device required')
for device in prefs.devices:device.use=device in devices
scene.cycles.device='GPU'
scene.render.resolution_x=1200;scene.render.resolution_y=1200
from mathutils import Vector
target=Vector((-7.5,-3.9,1.9));scene.camera.location=target+Vector((-7,9,6.2))
scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.ortho_scale=6.9
records=[]
for label,fraction in [('full',1),('half',.5),('empty',0)]:
    for surface in assembly['liquids']:
        obj=collection.objects[surface['name']]
        obj.location.z=surface['bottom']+(surface['top']-surface['bottom'])*fraction
        obj.hide_render=fraction==0
    collection.objects['FisheryCascade'].hide_render=fraction==0
    scene.render.filepath=str(out/(ident+'-water-'+label+'.png'))
    bpy.ops.render.render(write_still=True)
    records.append({'label':label,'fill':fraction,'heights':{s['name']:collection.objects[s['name']].location.z for s in assembly['liquids']}})
(out/(ident+'-water-preview.json')).write_text(json.dumps({'scope':'Blender fill-state demonstration; runtime fishery integration pending','states':records},indent=2))
