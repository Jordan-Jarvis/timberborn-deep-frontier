"""Report evaluated mesh cost without changing source geometry or guessing FPS."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser();parser.add_argument('--models',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
reports=[]
for ident in args.models.split(','):
    path=ROOT/f'src/DeepFrontier/Art/Source/{ident}-ReferenceStudy.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.scene.frame_set(1)
    deps=bpy.context.evaluated_depsgraph_get();objects=[]
    for obj in bpy.data.collections[ident+'.ReferenceStudy'].all_objects:
        if obj.type!='MESH':continue
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            objects.append({'name':obj.name,'nativeResource':'native_resource' in obj,
                'triangles':len(mesh.loop_triangles),'vertices':len(mesh.vertices),
                'materials':len({p.material_index for p in mesh.polygons})})
        finally:evaluated.to_mesh_clear()
    report={'model':ident,'sourceSha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        'scope':'Blender frame-one evaluated geometry including native preview props; not measured GPU time or runtime draw calls.',
        'triangles':sum(o['triangles'] for o in objects),
        'authoredTriangles':sum(o['triangles'] for o in objects if not o['nativeResource']),
        'nativePreviewTriangles':sum(o['triangles'] for o in objects if o['nativeResource']),
        'meshObjects':len(objects),'objects':sorted(objects,key=lambda o:-o['triangles'])}
    reports.append(report)
    print(json.dumps({k:v for k,v in report.items() if k!='objects'}),flush=True)
folder=ROOT/'outputs/mesh-budget';folder.mkdir(exist_ok=True)
for report in reports:(folder/(report['model']+'.json')).write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
