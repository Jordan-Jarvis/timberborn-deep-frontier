"""Read-only geometry evidence for the exact-grid rail metadata migration."""
import hashlib,json,sys
from pathlib import Path
import bpy
ROOT=Path(__file__).resolve().parents[2]
folder=ROOT/'outputs/hatchery-platform-candidate'
before=folder/'FishHatchery-ReferenceStudy.blend1';after=folder/'FishHatchery-ReferenceStudy.blend'
if hashlib.sha256(before.read_bytes()).hexdigest()!='a0e772dc6c3d9a428a7138f9eb53258f5c2b23d9b5ac821ead659fe9a117a171':
    raise ValueError('Expected exact pre-grid-rail candidate backup')
def capture(path):
    bpy.ops.wm.open_mainfile(filepath=str(path));result={}
    for obj in bpy.data.collections['FishHatchery.ReferenceStudy'].objects:
        if not obj.name.startswith('WalkwayRail.FishHatchery.'):continue
        mesh=obj.data
        result[obj.name]={'vertices':[tuple(v.co) for v in mesh.vertices],
          'faces':[(tuple(f.vertices),f.material_index) for f in mesh.polygons],
          'materials':[m.name for m in mesh.materials],
          'uv':[tuple(v.uv) for v in mesh.uv_layers.active.data]}
    return result
a=capture(before);b=capture(after)
if set(a)!=set(b) or len(a)!=41:raise ValueError('Rail inventory differs')
delta=0.;uv_delta=0.;count=0
for name,old in a.items():
    new=b[name]
    if old['faces']!=new['faces'] or old['materials']!=new['materials']:raise ValueError('Rail topology/material differs: '+name)
    for p,q in zip(old['vertices'],new['vertices'],strict=True):
        delta=max(delta,max(abs(x-y) for x,y in zip(p,q,strict=True)));count+=1
    for p,q in zip(old['uv'],new['uv'],strict=True):uv_delta=max(uv_delta,max(abs(x-y) for x,y in zip(p,q,strict=True)))
if delta>2e-6 or uv_delta>2e-6:raise ValueError('Grid authoring changed more than floating-point representation')
report={'beforeSourceSha256':hashlib.sha256(before.read_bytes()).hexdigest(),'afterSourceSha256':hashlib.sha256(after.read_bytes()).hexdigest(),
        'railObjects':41,'vertexSamples':count,'maximumVertexDelta':delta,'maximumUvDelta':uv_delta,
        'sameTopologyAndMaterials':True,'scope':'Precision-only grid metadata correction; pre-migration saved-scene review appearance remains representative'}
(folder/'grid-rail-geometry-comparison.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report))
