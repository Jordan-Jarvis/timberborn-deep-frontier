"""Read exact installed terrain meshes; do not alter or redistribute assets."""
from pathlib import Path
import hashlib,json,struct,sys,zlib
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/unitypy'))
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import UnityPy,model_pb2
GAME=Path('C:/Program Files (x86)/Steam/steamapps/common/Timberborn/Timberborn_Data')
manager=next(o for o in UnityPy.load(str(GAME/'globalgamemanagers')).objects if o.type.name=='ResourceManager')
if manager.assets_file.externals[4].path!='resources.assets':raise ValueError('Native resource-file mapping changed')
objects={o.path_id:o for o in UnityPy.load(str(GAME/'resources.assets')).objects}
scripts={o.path_id:o for o in UnityPy.load(str(GAME/'globalgamemanagers.assets')).objects}
records=[]
for resource,pointer in manager.parse_as_dict()['m_Container']:
    if not resource.startswith('environment/land/'):continue
    if resource in ('environment/land/layertoolterraintopprefab','environment/land/terraintileprefab'):continue
    if pointer['m_FileID']!=5:raise ValueError('Terrain resource file changed')
    asset=objects[pointer['m_PathID']]
    if asset.type.name!='GameObject':continue
    root=asset.parse_as_dict();binary=[]
    for component in root['m_Component']:
        obj=objects[component['component']['m_PathID']]
        if obj.type.name!='MonoBehaviour':continue
        header=obj.read_typetree(check_read=False);script=header['m_Script']
        if script['m_FileID']!=1:raise ValueError('Terrain component script mapping changed')
        kind=scripts[script['m_PathID']].parse_as_dict()
        if kind['m_ClassName']=='BinaryData' and kind['m_Namespace']=='Timberborn.AssetSystem':binary.append(obj)
    if len(binary)!=1:raise ValueError('Terrain resource has no unique BinaryData payload: '+resource)
    raw=binary[0].get_raw_data();length=struct.unpack_from('<I',raw,32)[0]
    if len(raw)!=36+length+(4-length%4)%4:raise ValueError('Native BinaryData layout changed')
    payload=raw[36:36+length]
    # TimbermeshReader.ReadFromStream validates78 9c, then reads a raw
    # DeflateStream to source EOF. Shipped terrain payloads use that stream
    # contract; they are not complete Zlib containers with an Adler trailer.
    if payload[:2]!=bytes((120,156)):raise ValueError('Native Timbermesh header changed')
    stream=zlib.decompressobj(-zlib.MAX_WBITS)
    decoded=stream.decompress(payload[2:])+stream.flush()
    if stream.unconsumed_tail:raise ValueError('Native deflate stream was not consumed')
    model=model_pb2.Model();model.ParseFromString(decoded)
    heights=[];surface_heights=[];triangle_count=0
    for node in model.nodes:
        if not node.meshes:continue
        offset=[0.,0.,0.];current=node
        while True:
            if (current.rotation.x,current.rotation.y,current.rotation.z,current.rotation.w)!=(0,0,0,1) or (current.scale.x,current.scale.y,current.scale.z)!=(1,1,1):
                raise ValueError('Terrain native transform requires an explicit new inspection contract')
            offset=[a+b for a,b in zip(offset,(current.position.x,current.position.y,current.position.z),strict=True)]
            if current.parent==-1:break
            current=model.nodes[current.parent]
        points=list(struct.iter_unpack('<fff',next(p.data for p in node.vertexProperties if p.name=='position')))
        normals=list(struct.iter_unpack('<fff',next(p.data for p in node.vertexProperties if p.name=='normal')))
        for mesh in node.meshes:
            surface_heights.extend(points[j][1]+offset[1] for j in mesh.indices)
            for i in range(0,len(mesh.indices),3):
                ids=mesh.indices[i:i+3]
                if len(ids)!=3:raise ValueError('Terrain payload is not triangulated')
                if all(normals[j][1]>.99 for j in ids):
                    triangle_count+=1;heights.extend(points[j][1]+offset[1] for j in ids)
    records.append({'resource':resource,'sha256':hashlib.sha256(payload).hexdigest(),'upwardTriangles':triangle_count,
                    'allSurfaceHeightMin':min(surface_heights),'allSurfaceHeightMax':max(surface_heights),
                    'flatTopHeightMin':min(heights) if heights else None,'flatTopHeightMax':max(heights) if heights else None})
flat=[r for r in records if r['upwardTriangles']]
report={'scope':'Installed native flat terrain faces; model heights before grid translation, not a GPU shader test',
        'terrainModels':len(records),'modelsWithFlatTop':len(flat),'flatTopHeightMin':min(r['flatTopHeightMin'] for r in flat),
        'allSurfaceHeightMax':max(r['allSurfaceHeightMax'] for r in records),
        'flatTopHeightMax':max(r['flatTopHeightMax'] for r in flat),'models':records}
out=ROOT/'outputs/native-ground-clearance.json';out.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k!='models'}))
