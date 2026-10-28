"""Decode exact BinaryData._bytes payloads using the official Timbermesh schema."""
from pathlib import Path
import json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
out=ROOT/'outputs/native-civic-assets'
models={'CompactWaterWheel.IronTeeth':10491,'LargeWaterWheel.IronTeeth':10557,'SmallTank.IronTeeth':10654,'Barrel':10415,
        'Shrub.IronTeeth':10685,'BlueberryBushMature':10006,'CoffeeBushMature':10634,
        'DandelionMature':10780,'SunflowerMature':10657}
for name,component in models.items():
    data=(out/(str(component)+'-component.bin')).read_bytes()
    length=struct.unpack_from('<I',data,32)[0]
    if len(data)!=36+length+(4-length%4)%4:raise ValueError('BinaryData length does not match Unity byte-array layout')
    payload=data[36:36+length];model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
    (out/(name+'.timbermesh')).write_bytes(payload)
    summary=[]
    for n in model.nodes:
        summary.append({'name':n.name,'fields':[f.name for f,_ in n.ListFields()],
            'meshes':[{'material':m.material,'indices':len(m.indices)} for m in n.meshes],
            'properties':[{'name':p.name,'fields':str(p)[:130]} for p in n.vertexProperties],
            'animations':[{'name':a.name,'frames':len(a.frames)} for a in n.nodeAnimations]})
    (out/(name+'-model.json')).write_text(json.dumps(summary,indent=2))
    print(name,json.dumps(summary),flush=True)
