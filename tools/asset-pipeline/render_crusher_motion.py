"""Inspect the saved crusher scene and render its existing animation to MP4."""
import json
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
scene=bpy.context.scene
model=bpy.data.collections['StoneCrusher.ReferenceStudy']
names=['ReferenceCrusherRoller1','ReferenceCrusherRoller2','ReferenceCrusherFlywheel',
       'ReferenceCrusherDriveSprocket0.61','ReferenceCrusherDriveSprocket1.96']
report={'scope':'Blender scene only; no game playback verification','parts':[]}
for name in names:
    obj=model.objects[name]
    if not obj.animation_data or not obj.animation_data.action:raise ValueError('Missing animation: '+name)
    transforms=[]
    for frame in (1,16,61):
        scene.frame_set(frame);bpy.context.view_layer.update();transforms.append(obj.matrix_world.copy())
    movement=max(abs(transforms[0][i][j]-transforms[1][i][j]) for i in range(4) for j in range(4))
    loop_error=max(abs(transforms[0][i][j]-transforms[2][i][j]) for i in range(4) for j in range(4))
    if movement<.1:raise ValueError('Static animated part: '+name)
    if loop_error>.00001:raise ValueError('Animation loop does not close: '+name)
    report['parts'].append({'name':name,'loopMatrixError':loop_error,'quarterTurnMatrixDifference':movement})
for obj in model.objects:
    if obj.type!='MESH':raise ValueError('Unexpected model object: '+obj.name)
    if not obj.data.uv_layers:raise ValueError('Missing UVs: '+obj.name)
    if any(slot.material is None for slot in obj.material_slots):raise ValueError('Empty material slot: '+obj.name)
report['sourceVertices']=sum(len(o.data.vertices) for o in model.objects)
report['sourcePolygons']=sum(len(o.data.polygons) for o in model.objects)
out=ROOT/'outputs/reference-studies'
(out/'StoneCrusher-motion-check.json').write_text(json.dumps(report,indent=2)+'\n')
scene.frame_start=1;scene.frame_end=60;scene.frame_step=2;scene.frame_set(1)
scene.render.fps=15
scene.render.resolution_x=768;scene.render.resolution_y=768
scene.cycles.samples=16
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
required=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(required)!=1:raise RuntimeError('Required RTX 2060 OptiX render device is unavailable')
for device in prefs.devices:device.use=device in required
scene.cycles.device='GPU'
scene.render.image_settings.file_format='FFMPEG'
scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='HIGH'
scene.render.filepath=str(out/'StoneCrusher-motion.mp4')
bpy.ops.render.render(animation=True)
print('CRUSHER MOTION CHECKED AND RENDERED',flush=True)
