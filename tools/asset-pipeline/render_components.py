"""Preview selected saved Blender assets without generating any geometry."""
import argparse
import hashlib
from pathlib import Path
import sys
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--model',required=True)
parser.add_argument('--components',required=True)
parser.add_argument('--output',type=Path,required=True)
parser.add_argument('--context',action='store_true',help='Show surrounding saved geometry in the same close-up')
parser.add_argument('--view',choices=('front-left','front-right','rear-left','rear-right'),default='front-left')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
if not args.output.is_absolute():raise ValueError('Component preview output must be an absolute path')
source=ROOT/'src/DeepFrontier/Art/Source'/f'{args.model}-ReferenceStudy.blend'
digest=hashlib.sha256(source.read_bytes()).hexdigest()
bpy.ops.wm.open_mainfile(filepath=str(source))
names=[args.model+'.'+key for key in args.components.split(',')]
if len(names)!=len(set(names)):raise ValueError('Duplicate preview component')
selected=[bpy.data.objects[name] for name in names]
if any(obj['df_component']!=obj.name for obj in selected):raise ValueError('Expected named authored components')
scene=bpy.context.scene;scene.frame_set(1);bpy.context.view_layer.update()
points=[obj.matrix_world@Vector(corner) for obj in selected for corner in obj.bound_box]
low=Vector(tuple(min(v[a] for v in points) for a in range(3)))
high=Vector(tuple(max(v[a] for v in points) for a in range(3)))
focus=(low+high)/2
if not args.context:
    for obj in bpy.data.objects:
        if obj.type=='MESH':obj.hide_render=obj not in selected
directions={'front-left':(3,5,2.5),'front-right':(-3,5,2.5),
            'rear-left':(3,-5,2.5),'rear-right':(-3,-5,2.5)}
scene.camera.location=focus+Vector(directions[args.view])
scene.camera.rotation_euler=(focus-scene.camera.location).to_track_quat('-Z','Y').to_euler()
scene.camera.data.ortho_scale=max(high-low)*(2.4 if args.context else 1.65)
scene.render.resolution_x=900;scene.render.resolution_y=900;scene.render.resolution_percentage=100
scene.cycles.samples=32;scene.cycles.use_denoising=True
args.output.parent.mkdir(parents=True,exist_ok=True)
scene.render.filepath=str(args.output)
bpy.ops.render.render(write_still=True)
if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:raise RuntimeError('Preview changed saved geometry')
print('SELECTED SAVED ASSET PREVIEW',names,'source unchanged',digest,flush=True)
