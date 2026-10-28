"""Read-only isometric review of the exact final catalog source scenes.

Strict overlap evidence must match each scene before rendering. The manifest
records scene and image hashes; neither source nor packaged meshes is changed.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parents[2]
MODELS=('GroceryStore','FisheryWorks','FishHatchery','ReinforcedHydroTurbine',
        'MaterialsLaboratory','StoneCrusher','CementKiln','MineralQuarry',
        'ConcreteMixer','SandstonePit','LimestonePit')
parser=argparse.ArgumentParser()
parser.add_argument('--models',default=','.join(MODELS))
parser.add_argument('--resolution',type=int,default=1400)
parser.add_argument('--samples',type=int,default=64)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
out=ROOT/'outputs/catalog-shell-review';out.mkdir(exist_ok=True)
manifest_path=out/'manifest.json'
manifest=json.loads(manifest_path.read_text()) if manifest_path.exists() else []
for model in args.models.split(','):
    if model not in MODELS:raise ValueError('Model not owned by this catalog review: '+model)
    source=ROOT/f'src/DeepFrontier/Art/Source/{model}-ReferenceStudy.blend'
    digest=hashlib.sha256(source.read_bytes()).hexdigest()
    audit=json.loads((ROOT/f'outputs/zfight/{model}-frame1.json').read_text())
    if audit['visibleConflicts'] or audit['sourceSha256']!=digest:
        raise ValueError('Review requires a fresh clean strict source audit: '+model)
    study=json.loads((ROOT/f'outputs/reference-studies/{model}-study.json').read_text())
    bpy.ops.wm.open_mainfile(filepath=str(source));scene=bpy.context.scene;scene.frame_set(1)
    low,high=Vector(study['boundsMin']),Vector(study['boundsMax'])
    center=(low+high)/2;focus=Vector((center.x,center.y,center.z*.85))
    scale={'GroceryStore':1.34,'FisheryWorks':1.34,'FishHatchery':1.55,
           'ReinforcedHydroTurbine':1.55,'MaterialsLaboratory':1.39,
           'StoneCrusher':1.55,'CementKiln':1.31,'MineralQuarry':1.34,
           'ConcreteMixer':1.55,'SandstonePit':1.55,'LimestonePit':1.55}[model]
    scene.camera.data.ortho_scale=max(high-low)*scale
    prefs=bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type='OPTIX';prefs.get_devices()
    devices=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
    if len(devices)!=1:raise RuntimeError('Required RTX 2060 render device unavailable')
    for device in prefs.devices:device.use=device in devices
    scene.cycles.device='GPU';scene.cycles.samples=args.samples
    scene.render.resolution_x=args.resolution;scene.render.resolution_y=args.resolution
    scene.render.resolution_percentage=100
    entry={'model':model,'sourceScene':str(source.relative_to(ROOT)),
           'sourceSha256':digest,'views':[],'visualReview':'pending'}
    for view,direction in (('front',(7,9,6.2)),('rear',(-7,-9,6.5))):
        # The dam tower shadows its entire downstream workshop from the
        # stored studio lamps. A rear-only review lamp makes that facade
        # inspectable; this temporary light never enters a saved source.
        if model=='ReinforcedHydroTurbine' and view=='rear':
            bpy.ops.object.light_add(type='AREA',location=focus+Vector((-7,-7,7)))
            light=bpy.context.object;light.data.energy=1400;light.data.size=6
            light.rotation_euler=(focus-light.location).to_track_quat('-Z','Y').to_euler()
        scene.camera.location=focus+Vector(direction)
        scene.camera.rotation_euler=(focus-scene.camera.location).to_track_quat('-Z','Y').to_euler()
        image=out/f'{model}-{view}.png';scene.render.filepath=str(image)
        bpy.ops.render.render(write_still=True)
        entry['views'].append({'view':view,'image':str(image.relative_to(ROOT)),
                               'sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
        print('CATALOG VIEW RENDERED',model,view,flush=True)
    if hashlib.sha256(source.read_bytes()).hexdigest()!=digest:
        raise ValueError('Review modified canonical source: '+model)
    manifest=[item for item in manifest if item['model']!=model]+[entry]
    manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
print('Catalog review images saved; visual review remains required')
