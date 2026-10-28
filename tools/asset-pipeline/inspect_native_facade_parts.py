"""List exact connected mesh components for selecting native facade assemblies."""
import argparse,json,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
parser=argparse.ArgumentParser();parser.add_argument('--model',required=True);args=parser.parse_args()
model=model_pb2.Model();model.ParseFromString(zlib.decompress((ROOT/f'outputs/native-civic-assets/{args.model}.timbermesh').read_bytes()))
groups=[]
for ni,node in enumerate(model.nodes):
    props={p.name:list(struct.iter_unpack('<'+'f'*p.scalarTypeDimension,p.data)) for p in node.vertexProperties}
    for sub in node.meshes:
        points=props['position'];parent=list(range(len(points)));by={}
        def root(i):
            while parent[i]!=i:i=parent[i]
            return i
        triangles=[list(sub.indices[i:i+3]) for i in range(0,len(sub.indices),3)]
        for face in triangles:
            for i in face:
                if points[i] in by:parent[root(i)]=root(by[points[i]])
                else:by[points[i]]=i
            for i in face[1:]:parent[root(i)]=root(face[0])
        components={}
        for face in triangles:components.setdefault(root(face[0]),[]).append(face)
        for faces in components.values():
            ids=sorted({i for f in faces for i in f});vs=[points[i] for i in ids]
            groups.append(dict(id=len(groups),node=ni,material=sub.material,faces=faces,
                bounds=[[min(p[a] for p in vs),max(p[a] for p in vs)] for a in range(3)]))
(ROOT/f'outputs/native-civic-assets/{args.model}-parts.json').write_text(json.dumps(groups,indent=2))
for part in groups:
    print(part['id'],part['material'],len(part['faces']),[[round(v,5) for v in a] for a in part['bounds']])
