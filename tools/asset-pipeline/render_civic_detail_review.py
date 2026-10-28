"""Angled details from saved civic scenes; never changes their source meshes."""
import argparse,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--model',required=True,choices=['Hospital','FisheryWorks'])
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);ident=args.model
scene=bpy.context.scene;scene.frame_set(1);scene.render.resolution_x=1400;scene.render.resolution_y=1100
scene.render.resolution_percentage=100;scene.render.image_settings.file_format='PNG';scene.cycles.samples=64
scene.cycles.transparent_max_bounces=32
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
required=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(required)!=1:raise RuntimeError('Required RTX 2060 OptiX render device is unavailable')
for device in prefs.devices:device.use=device in required
scene.cycles.device='GPU'
out=ROOT/'outputs/reference-studies'
def render(label,focus,direction,scale):
    focus=Vector(focus);camera=scene.camera;camera.data.ortho_scale=scale
    camera.location=focus+Vector(direction);camera.rotation_euler=(focus-camera.location).to_track_quat('-Z','Y').to_euler()
    scene.render.filepath=str(out/f'{ident}-{label}.png');bpy.ops.render.render(write_still=True)

if ident=='Hospital':
    render('planter-detail',(-2.48,-1.45,2.62),(3,5,3.2),2.4)
    render('terrace-detail',(-8.6,-4.5,6.5),(-7,9,6.2),5.3)
else:
    assembly=json.loads((out/'FisheryWorks-native-assembly.json').read_text());states=[]
    for label,fraction in (('full',1),('half',.5),('empty',0)):
        heights={}
        for surface in assembly['liquids']:
            obj=bpy.data.objects[surface['name']]
            obj.location.z=surface['bottom']+(surface['top']-surface['bottom'])*fraction
            obj.hide_render=fraction==0;heights[obj.name]=obj.location.z
        bpy.data.objects['FisheryCascade'].hide_render=fraction==0
        render('water-'+label,(-7.8,-4.1,1.65),(-7,9,6.2),6.2)
        states.append({'label':label,'fill':fraction,'heights':heights})
    (out/'FisheryWorks-water-preview.json').write_text(json.dumps({
        'scope':'Blender fill-state demonstration; runtime fishery integration pending','states':states},indent=2)+'\n')
print('CIVIC DETAILS RENDERED',ident,flush=True)
