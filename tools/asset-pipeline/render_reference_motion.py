"""Check and preview the saved, explicitly selected reference-study animation."""
import argparse
import json
from pathlib import Path
import sys
import bpy

ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--model',required=True,choices=['StoneCrusher','CementKiln','MineralQuarry','Hospital','Restaurant','GroceryStore','FisheryWorks'])
parser.add_argument('--check-only',action='store_true',help='Validate the saved scene without rendering a preview')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
ident=args.model;output=ROOT/'outputs/reference-studies'
metadata=json.loads((output/(ident+'-study.json')).read_text())
scene=bpy.context.scene;end=metadata['animationFrames']
if scene.frame_end!=end:raise ValueError('Saved scene timeline differs from its study metadata')
model=bpy.data.collections[ident+'.ReferenceStudy']
expected=metadata['animatedParts']
animated=[o.name for o in model.objects if o.animation_data and o.animation_data.action]
if set(animated)!=set(expected):raise ValueError('Saved animation nodes differ from their study metadata')
report={'scope':'Blender scene only; no game playback verification','parts':[],
        'sourceTimelineFrames':end,'sourceFps':scene.render.fps}
scene.frame_set(1);bpy.context.view_layer.update()
initial={name:model.objects[name].matrix_world.copy() for name in expected}
movements={name:0 for name in expected};loop_errors={}
check_frames=range(2,end+1) if ident=='MineralQuarry' else (5,11,16,1+(end-1)//4,1+(end-1)//2,end)
for frame in check_frames:
    scene.frame_set(frame);bpy.context.view_layer.update()
    for name in expected:
        pose=model.objects[name].matrix_world
        difference=max(abs(initial[name][i][j]-pose[i][j]) for i in range(4) for j in range(4))
        if frame==end:loop_errors[name]=difference
        else:movements[name]=max(movements[name],difference)
for name in expected:
    movement=movements[name];loop_error=loop_errors[name]
    minimum=.005 if name=='Quarry.SortingSieve' else .02
    if movement<minimum:raise ValueError('Static animated part: '+name)
    if loop_error>.00001:raise ValueError('Animation loop does not close: '+name)
    report['parts'].append({'name':name,'loopMatrixError':loop_error,'sampleMatrixDifference':movement})
for obj in model.objects:
    if obj.type=='EMPTY' and 'native_resource' in obj:continue
    if obj.type!='MESH':raise ValueError('Unexpected model object: '+obj.name)
    if not obj.data.uv_layers:raise ValueError('Missing UVs: '+obj.name)
    if any(slot.material is None for slot in obj.material_slots):raise ValueError('Empty material slot: '+obj.name)
report['sourceVertices']=sum(len(o.data.vertices) for o in model.objects if o.type=='MESH')
report['sourcePolygons']=sum(len(o.data.polygons) for o in model.objects if o.type=='MESH')
if ident in ('StoneCrusher','CementKiln','MineralQuarry','Hospital','Restaurant','GroceryStore','FisheryWorks'):
    rails=json.loads((output/(ident+'-rail-manifest.json')).read_text())
    expected_rails=set(rails['nodes'])
    actual_rails={o.name for o in model.objects if o.name.startswith('WalkwayRail.')}
    if actual_rails!=expected_rails:raise ValueError('Separate rail nodes differ from the authored manifest')
    for run in rails['runs']:
        for panel in run['panels']:
            for key in ('node','startPost','endPost'):
                if panel[key] not in actual_rails:raise ValueError('Missing rail assembly node: '+panel[key])
    report['separateRailNodes']=len(actual_rails);report['railRuns']=len(rails['runs'])
    report['navigationStatus']='Rail nodes checked in Blender; native pathing and adaptive connections not implemented'
    heights=json.loads((output/(ident+'-height-manifest.json')).read_text())
    for run in rails['runs']:
        for panel in run['panels']:
            for endpoint in ('start','end'):
                z=panel[endpoint][2]
                if z not in heights['walkableDeckLayers']:
                    raise ValueError('Rail floor is not an authored whole grid layer: '+panel['node'])
    report['authoredHeightLayers']=heights
if ident=='MineralQuarry':
    sys.path.insert(0,str(Path(__file__).parent))
    from quarry_validation import validate_quarry
    report['quarryKinematicsAndAccess']=validate_quarry(model,scene)
elif ident in ('StoneCrusher','CementKiln'):
    # No walkways or balconies since 2026-10-21: there is no walk to check;
    # the rail manifest above must be empty.
    if report.get('separateRailNodes'):raise ValueError(ident+' must not carry walkway rails')
    report['walkways']='None (ground door only)'
else:
    sys.path.insert(0,str(Path(__file__).parent))
    from civic_validation import validate_civic_walks
    report['civicWalkClearance']=validate_civic_walks(ident,model,scene)
if args.check_only:
    (output/(ident+'-geometry-check.json')).write_text(json.dumps(report,indent=2)+'\n')
    print('REFERENCE GEOMETRY AND MOTION VALIDATED',ident,flush=True)
    raise SystemExit(0)
step={'StoneCrusher':2,'CementKiln':4,'MineralQuarry':4,'Hospital':2,'Restaurant':2,'GroceryStore':2,'FisheryWorks':2}[ident]
scene.frame_start=1;scene.frame_end=end-1;scene.frame_step=step;scene.frame_set(1)
source_fps=scene.render.fps;scene.render.fps_base=step
scene.render.resolution_x=640;scene.render.resolution_y=640;scene.cycles.samples=16
scene.render.use_persistent_data=True;scene.cycles.denoiser='OPTIX'
if ident=='MineralQuarry':
    scene.cycles.samples=32
    # The process-side isometric shows tipping and screening together.
    from mathutils import Vector
    center=(Vector(metadata['boundsMin'])+Vector(metadata['boundsMax']))/2
    target=Vector((center.x,center.y,center.z*.85))
    scene.camera.location=target+Vector((-7,9,6.2))
    scene.camera.rotation_euler=(target-scene.camera.location).to_track_quat('-Z','Y').to_euler()
    report['previewView']='front-right isometric'
prefs=bpy.context.preferences.addons['cycles'].preferences;prefs.compute_device_type='OPTIX';prefs.get_devices()
required=[d for d in prefs.devices if d.type=='OPTIX' and d.name=='NVIDIA GeForce RTX 2060']
if len(required)!=1:raise RuntimeError('Required RTX 2060 OptiX render device is unavailable')
for device in prefs.devices:device.use=device in required
scene.cycles.device='GPU'
scene.render.image_settings.file_format='FFMPEG';scene.render.ffmpeg.format='MPEG4';scene.render.ffmpeg.codec='H264'
scene.render.ffmpeg.constant_rate_factor='HIGH';scene.render.filepath=str(output/(ident+'-motion.mp4'))
bpy.ops.render.render(animation=True)
report['previewFps']=source_fps/step;report['previewFrames']=(end-1)//step
(output/(ident+'-motion-check.json')).write_text(json.dumps(report,indent=2)+'\n')
print('REFERENCE MOTION CHECKED AND RENDERED',ident,flush=True)
