"""Read exact shipped DirtPath meshes before authoring bank apron clearance."""
import hashlib,json,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/unitypy'))
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import UnityPy,model_pb2
env=UnityPy.load('C:/Program Files (x86)/Steam/steamapps/common/Timberborn/Timberborn_Data/resources.assets')
objects={o.path_id:o for o in env.objects};reports=[]
paths=json.loads((ROOT/'outputs/native-civic-assets/resource-paths.json').read_text())['m_Container']
expected={f'buildings/paths/path/{kind}{variant}.model' for kind in ('dirtpath','roofpath') for variant in ('0000','0010','0011','0111','1010','1111')}
selected=[(name,pointer['m_PathID']) for name,pointer in paths if name in expected]
if {name for name,_ in selected}!=expected:raise ValueError('Native path resource set changed')
for name,ident in selected:
    root=objects[ident].parse_as_dict();models=[]
    for entry in root['m_Component']:
        obj=objects[entry['component']['m_PathID']]
        if obj.type.name!='MonoBehaviour':continue
        header=obj.read_typetree(check_read=False)
        if header['m_Script']!={'m_FileID':1,'m_PathID':4746}:continue # Inspected native BinaryData script.
        raw=obj.get_raw_data();length=struct.unpack_from('<I',raw,32)[0]
        if len(raw)!=36+length+(4-length%4)%4:raise ValueError('Unexpected native BinaryData layout')
        payload=raw[36:36+length];model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
        for node in model.nodes:
            if node.parent!=-1 or node.nodeAnimations or node.scale.x!=1 or node.scale.y!=1 or node.scale.z!=1:
                raise ValueError('Path height inspection requires static unscaled root nodes')
            prop=next(p for p in node.vertexProperties if p.name=='position')
            positions=list(struct.iter_unpack('<fff',prop.data))
            heights=[p[1]+node.position.y for p in positions]
            normal_prop=next(p for p in node.vertexProperties if p.name=='normal')
            normals=list(struct.iter_unpack('<fff',normal_prop.data))
            upward=[]
            for mesh in node.meshes:
                for i in range(0,len(mesh.indices),3):
                    triangle=mesh.indices[i:i+3]
                    if all(normals[j][1]>.9 for j in triangle):upward.extend(heights[j] for j in triangle)
            if not upward:raise ValueError('Native path has no upward surface')
            models.append({'node':node.name,'minimumHeight':min(heights),'maximumHeight':max(heights),
                           'heights':sorted(set(heights)),'upwardMinimumHeight':min(upward),
                           'upwardSurfaceSamples':len(upward),'sourcePayloadSha256':hashlib.sha256(payload).hexdigest()})
    if len(models)!=1:raise ValueError('Expected one native path model')
    reports.append({'name':name,'nativePrefabName':root['m_Name'],'models':models})
folder=ROOT/'outputs/hatchery-platform-candidate'
(folder/'native-path-heights.json').write_text(json.dumps(reports,indent=2)+'\n');print(json.dumps(reports))
