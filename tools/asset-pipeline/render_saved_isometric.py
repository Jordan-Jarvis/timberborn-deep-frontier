"""Render the saved civic studio scene without rebuilding or saving its geometry."""
import argparse,json,sys,hashlib
from pathlib import Path
import bpy
from mathutils import Vector
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--model',required=True,choices=['Hospital','Restaurant','GroceryStore','FisheryWorks','FishHatchery'])
parser.add_argument('--views',default='front,front-right,rear')
parser.add_argument('--source-dir',type=Path,default=ROOT/'src/DeepFrontier/Art/Source')
parser.add_argument('--output-dir',type=Path,default=ROOT/'outputs/reference-studies')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if not args.source_dir.is_absolute() or not args.output_dir.is_absolute():
    raise ValueError('Saved scene and output directories must be absolute')
source=args.source_dir/f'{args.model}-ReferenceStudy.blend'
if Path(bpy.data.filepath)!=source:raise ValueError('Open the exact reviewed source scene')
digest=hashlib.sha256(source.read_bytes()).hexdigest()
out=args.output_dir
study=json.loads((out/f'{args.model}-study.json').read_text())
low,high=Vector(study['boundsMin']),Vector(study['boundsMax'])
centre=(low+high)/2;focus=Vector((centre.x,centre.y,centre.z*.85))
directions={'front':(7,9,6.2),'front-right':(-7,9,6.2),'rear':(-7,-9,6.5),'back-left':(7,-9,6.2)}
scene=bpy.context.scene;scene.frame_set(1)
# Saved studio cameras may retain an earlier sheet-layout offset. A single
# building review owns a centered square composition, independently of that
# sheet layout; geometry and the saved source scene remain unchanged.
scene.camera.data.shift_x=0
scene.camera.data.shift_y=0
scene.render.resolution_x=1600
scene.render.resolution_y=1600
scene.render.resolution_percentage=100
scene.camera.data.type='ORTHO'
review_objects=[obj for obj in bpy.data.collections[args.model+'.ReferenceStudy'].all_objects
                if obj.type=='MESH' and not obj.name.startswith('Studio.') and not obj.hide_render]
if not review_objects:raise ValueError('Review collection has no visible model geometry')
points=[obj.matrix_world@v.co for obj in review_objects for v in obj.data.vertices]
framing=[]
prefs=bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type='OPTIX';prefs.get_devices()
devices=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(devices)!=1:raise RuntimeError('Required RTX 2060 render device unavailable')
for device in prefs.devices:device.use=device in devices
for view in args.views.split(','):
    if view not in directions:raise ValueError('Only isometric review views are allowed')
    scene.camera.location=focus+Vector(directions[view])
    scene.camera.rotation_euler=(focus-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    basis=scene.camera.rotation_euler.to_matrix()
    horizontal=basis@Vector((1,0,0));vertical=basis@Vector((0,1,0))
    projected=[((p-focus).dot(horizontal),(p-focus).dot(vertical)) for p in points]
    lo=[min(p[axis] for p in projected) for axis in (0,1)]
    hi=[max(p[axis] for p in projected) for axis in (0,1)]
    centre=focus+horizontal*((lo[0]+hi[0])/2)+vertical*((lo[1]+hi[1])/2)
    scene.camera.location=centre+Vector(directions[view])
    scene.camera.data.ortho_scale=max(hi[0]-lo[0],hi[1]-lo[1])*1.12
    framing.append({'view':view,'focus':list(centre),'orthographicScale':scene.camera.data.ortho_scale,
                    'modelVertexSamples':len(points),'shift':[0,0],'resolution':[1600,1600]})
    scene.render.filepath=str(out/f'{args.model}-{view}.png')
    bpy.ops.render.render(write_still=True)
    print('SAVED SCENE RENDERED',args.model,view,flush=True)
if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise ValueError('Review rendering changed the source scene')
(out/f'{args.model}-review-framing.json').write_text(json.dumps({'sourceSha256':digest,'views':framing},indent=2)+'\n')
print('SOURCE SCENE HASH PRESERVED',digest)
