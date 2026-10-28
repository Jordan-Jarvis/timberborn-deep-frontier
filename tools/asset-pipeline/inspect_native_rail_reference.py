"""Read the shipped Iron Teeth rooftop terrace as the deck-railing reference."""
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
root=objects[3425].parse_as_dict()
assert root['m_Name']=='RooftopTerrace.IronTeeth.Model',root['m_Name']
components=[]
for c in root['m_Component']:
    o=objects[c['component']['m_PathID']]
    if o.type.name!='MonoBehaviour':continue
    header=o.read_typetree(check_read=False)
    components.append({'id':o.path_id,'header':header,'bytes':o.byte_size})
    (out/f'rail-reference-{o.path_id}.bin').write_bytes(o.get_raw_data())
(out/'rail-reference-components.json').write_text(json.dumps(components,indent=2))
print(json.dumps(components))
for name,ident in [('Platform.Full.IronTeeth',4510),('MetalFence1010.IronTeeth',4115),('WoodFence1010.IronTeeth',4012)]:
    root=objects[ident].parse_as_dict();assert root['m_Name']==name+'.Model',root['m_Name']
    binary=[]
    for c in root['m_Component']:
        o=objects[c['component']['m_PathID']]
        if o.type.name!='MonoBehaviour':continue
        h=o.read_typetree(check_read=False)
        if h['m_Script']!={'m_FileID':1,'m_PathID':4746}:continue
        binary.append(o.get_raw_data())
    assert len(binary)==1,name
    data=binary[0];length=struct.unpack_from('<I',data,32)[0]
    assert len(data)==36+length+(4-length%4)%4
    payload=data[36:36+length];m=model_pb2.Model();m.ParseFromString(zlib.decompress(payload))
    (out/(name+'.timbermesh')).write_bytes(payload)
    print(name,[(n.name,[s.material for s in n.meshes]) for n in m.nodes])
