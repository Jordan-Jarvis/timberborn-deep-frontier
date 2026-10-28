"""Inspect the exact shipped double-height housing rail nodes and their UVs."""
from pathlib import Path
import json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools'))
import dev_environment as dev
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/unitypy'))
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import UnityPy,model_pb2
env=UnityPy.load(str(dev.resources_assets()))
objects={o.path_id:o for o in env.objects}
out=ROOT/'outputs/native-civic-assets'
report={}
for name,ident in [('DistrictCenter.IronTeeth',3238)]:
    root=objects[ident].parse_as_dict();assert root['m_Name']==name+'.Model',root['m_Name']
    binaries=[]
    for component in root['m_Component']:
        obj=objects[component['component']['m_PathID']]
        if obj.type.name!='MonoBehaviour':continue
        header=obj.read_typetree(check_read=False)
        if header['m_Script']=={'m_FileID':1,'m_PathID':4746}:binaries.append(obj.get_raw_data())
    assert len(binaries)==1,name
    data=binaries[0];length=struct.unpack_from('<I',data,32)[0]
    assert len(data)==36+length+(4-length%4)%4
    payload=data[36:36+length];model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
    (out/(name+'.timbermesh')).write_bytes(payload)
    nodes=[]
    for node in model.nodes:
        positions=next(p for p in node.vertexProperties if p.name=='position')
        points=list(struct.iter_unpack('<fff',positions.data))
        nodes.append({'name':node.name,'parent':node.parent,'position':[node.position.x,node.position.y,node.position.z],
            'bounds':[[min(p[a] for p in points),max(p[a] for p in points)] for a in range(3)] if points else [],
            'materials':[s.material for s in node.meshes], 'vertices':len(points)})
    report[name]=nodes
(out/'district-facade-inspection.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
