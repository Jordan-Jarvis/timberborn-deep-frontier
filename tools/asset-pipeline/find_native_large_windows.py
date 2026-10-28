"""Inspect installed Iron Teeth window geometry to choose real large assemblies."""
import json,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path[:0]=[str(ROOT/'tools/asset-pipeline/unitypy'),str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin')]
import UnityPy,model_pb2
env=UnityPy.load(str(dev.resources_assets()))
objects={o.path_id:o for o in env.objects};out=ROOT/'outputs/native-civic-assets'
paths=json.loads((out/'resource-paths.json').read_text())['m_Container'];report=[]
for path,ref in paths:
    if not path.startswith('buildings/') or not path.endswith('.ironteeth.model'):continue
    asset=objects[ref['m_PathID']]
    if asset.type.name!='GameObject':continue
    root=asset.parse_as_dict();binaries=[]
    assert root['m_Name'].lower()==path.rsplit('/',1)[1],(path,root['m_Name'])
    for c in root['m_Component']:
        obj=objects[c['component']['m_PathID']]
        if obj.type.name!='MonoBehaviour':continue
        header=obj.read_typetree(check_read=False)
        if header['m_Script']=={'m_FileID':1,'m_PathID':4746}:binaries.append(obj.get_raw_data())
    assert len(binaries)==1,path
    data=binaries[0];length=struct.unpack_from('<I',data,32)[0]
    assert len(data)==36+length+(4-length%4)%4
    payload=data[36:36+length];m=model_pb2.Model();m.ParseFromString(zlib.decompress(payload));selected=[]
    for ni,node in enumerate(m.nodes):
        for sub in node.meshes:
            if sub.material!='WindowsAtlas.IronTeeth':continue
            prop=next(p for p in node.vertexProperties if p.name=='position')
            points=list(struct.iter_unpack('<fff',prop.data));parent=list(range(len(points)));by={}
            def find(i):
                while parent[i]!=i:i=parent[i]
                return i
            tris=[list(sub.indices[i:i+3]) for i in range(0,len(sub.indices),3)]
            for face in tris:
                for i in face:
                    if points[i] in by:parent[find(i)]=find(by[points[i]])
                    else:by[points[i]]=i
                for i in face[1:]:parent[find(i)]=find(face[0])
            groups={}
            for face in tris:groups.setdefault(find(face[0]),[]).append(face)
            for faces in groups.values():
                vs=[points[i] for i in {i for f in faces for i in f}]
                bounds=[[min(p[a] for p in vs),max(p[a] for p in vs)] for a in range(3)]
                span=[hi-lo for lo,hi in bounds]
                if span[1]>.7 and max(span[0],span[2])>.6:
                    selected.append({'node':ni,'triangles':len(faces),'bounds':bounds})
    if selected:
        name=root['m_Name'].removesuffix('.Model');(out/(name+'.timbermesh')).write_bytes(payload)
        report.append({'model':name,'resource':path,'windows':selected})
        print(name,[(r['node'],r['triangles'],[[round(v,3) for v in a] for a in r['bounds']]) for r in selected],flush=True)
(out/'large-window-candidates.json').write_text(json.dumps(report,indent=2))
