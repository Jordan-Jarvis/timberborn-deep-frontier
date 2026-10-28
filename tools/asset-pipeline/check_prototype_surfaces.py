"""Strict source overlap and authored atlas checks for all active prototypes."""
import hashlib
import json
import sys
from pathlib import Path
import bpy

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from zfight_audit import audit
from prototype_native_uv import atlas_rectangle

catalog=json.loads((ROOT/'tools/building_asset_catalog.json').read_text())['buildings']
models=[m for m in catalog if m['artStage']=='prototype']
assert len(models)==20
reports=[]
for source in dict.fromkeys(m['sourceScene'] for m in models):
    path=ROOT/source;digest=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path));bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
    for model in [m for m in models if m['sourceScene']==source]:
        objects=list(bpy.data.collections[model['collection']].all_objects)
        uv_count=0
        for obj in objects:
            if obj.type!='MESH':continue
            mesh=obj.data;uv=mesh.uv_layers['UVMap'].data
            for face in mesh.polygons:
                name=mesh.materials[face.material_index].name
                u0,u1,v0,v1=atlas_rectangle(name,face.index)
                for loop in face.loop_indices:
                    u,v=uv[loop].uv
                    if not (u0-1e-6<=u<=u1+1e-6 and v0-1e-6<=v<=v1+1e-6):
                        raise ValueError(f'{model["building"]}/{obj.name}/{face.index}: UV outside authored {name} island')
                    uv_count+=1
        report=audit(objects,.0005,.0005)
        report.update(model=model['model'],frame=1,sourceScene=source,sourceSha256=digest,
            detectorSha256=hashlib.sha256((Path(__file__).parent/'zfight_audit.py').read_bytes()).hexdigest(),
            checkedUvCorners=uv_count,scope='Prototype source surface audit; detailed art/grid migration still pending')
        output=ROOT/'outputs/zfight'/(model['model']+'-frame1.json')
        output.write_text(json.dumps(report,indent=2)+'\n')
        reports.append({k:v for k,v in report.items() if k!='conflicts'})
        print('PROTOTYPE AUDIT',json.dumps(reports[-1]),flush=True)
    assert hashlib.sha256(path.read_bytes()).hexdigest()==digest,'Audit changed source'
(ROOT/'outputs/prototype-surface-summary.json').write_text(json.dumps(reports,indent=2)+'\n')
assert all(not r['visibleConflicts'] for r in reports),'Visible source overlaps; inspect outputs/zfight before export'
print('PASS all20 prototype source overlap and exact native atlas audits')
