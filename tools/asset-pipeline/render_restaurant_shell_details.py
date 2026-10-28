"""Render angled close-ups of the saved source without changing its geometry."""
import hashlib
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'src/DeepFrontier/Art/Source/Restaurant-ReferenceStudy.blend'
if Path(bpy.data.filepath)!=source:raise ValueError('Open the exact Restaurant source scene')
digest=hashlib.sha256(source.read_bytes()).hexdigest()
out=ROOT/'docs/art/reviews/2026-10-21-exterior-repair'
scene=bpy.context.scene;scene.frame_set(1)
scene.render.resolution_x=1600;scene.render.resolution_y=1200
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
devices=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(devices)!=1:raise RuntimeError('Required RTX 2060 device unavailable')
for device in prefs.devices:device.use=device in devices
views=[('terrace-door',(-6.65,-4.25,7.0),(-7,5,4.5),5.1),
       ('wall-junction',(-2.9,-6.3,2.1),(7,-9,3.3),5.6)]
for label,target,direction,scale in views:
    target=Vector(target)
    scene.camera.location=target+Vector(direction)
    scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    scene.camera.data.ortho_scale=scale
    scene.render.filepath=str(out/f'Restaurant-{label}.png')
    bpy.ops.render.render(write_still=True)
    print('SAVED SCENE DETAIL RENDERED',label,flush=True)
if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Source changed during review')
print('SOURCE SCENE HASH PRESERVED',digest,flush=True)
