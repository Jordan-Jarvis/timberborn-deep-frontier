"""List disconnected native timber pieces without changing source coordinates."""
from pathlib import Path
import json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
model=model_pb2.Model();model.ParseFromString(zlib.decompress((ROOT/'outputs/native-civic-assets/DoubleLodge.Folktails.timbermesh').read_bytes()))
node=model.nodes[0]
props={p.name:list(struct.iter_unpack('<'+'f'*p.scalarTypeDimension,p.data)) for p in node.vertexProperties}
points=props['position'];sub=node.meshes[0];assert sub.material=='BaseWood_Brown.Folktails'
triangles=[list(sub.indices[i:i+3]) for i in range(0,len(sub.indices),3)]
parent=list(range(len(points)))
def root(i):
    while parent[i]!=i:i=parent[i]
    return i
by_position={}
for i,p in enumerate(points):
    if p in by_position:parent[root(i)]=root(by_position[p])
    else:by_position[p]=i
for tri in triangles:
    for i in tri[1:]:parent[root(i)]=root(tri[0])
groups={}
for tri in triangles:groups.setdefault(root(tri[0]),[]).append(tri)
report=[]
for faces in groups.values():
    ids=sorted({i for f in faces for i in f});vs=[points[i] for i in ids]
    report.append({'id':len(report),'faces':faces,'bounds':[[min(p[a] for p in vs),max(p[a] for p in vs)] for a in range(3)]})
(ROOT/'outputs/native-civic-assets/lodge-timber-parts.json').write_text(json.dumps(report,indent=2))
print(json.dumps([{**{k:v for k,v in p.items() if k!='faces'},'triangles':len(p['faces'])} for p in report],indent=2))
kit={'source':'Buildings/Housing/DoubleLodge/DoubleLodge.Folktails.Model','gameVersion':'1.1.2.8','material':sub.material,'parts':{}}
for name,index in [('post',8),('handrail',9)]:
    part=report[index];ids=sorted({i for f in part['faces'] for i in f});mapping={old:new for new,old in enumerate(ids)}
    kit['parts'][name]={'vertices':[points[i] for i in ids],'uv':[props['uv0'][i] for i in ids],
        'faces':[[mapping[i] for i in reversed(f)] for f in part['faces']],'bounds':part['bounds']}
(ROOT/'tools/asset-pipeline/housing-railing.json').write_text(json.dumps(kit,indent=2)+'\n')
