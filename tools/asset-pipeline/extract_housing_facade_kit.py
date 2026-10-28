"""Extract explicit shipped Barrack facade parts, retaining native geometry/UVs."""
import hashlib,json,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
source=ROOT/'outputs/native-civic-assets/LargeBarrack.IronTeeth.timbermesh'
model=model_pb2.Model();model.ParseFromString(zlib.decompress(source.read_bytes()))
assert len(model.nodes)==1 and model.nodes[0].name=='LargeBarrack.IronTeeth'
node=model.nodes[0]
props={p.name:list(struct.iter_unpack('<'+'f'*p.scalarTypeDimension,p.data)) for p in node.vertexProperties}
groups=[]
for sub in node.meshes:
    points=props['position'];parent=list(range(len(points)));by_position={}
    def root(i):
        while parent[i]!=i:i=parent[i]
        return i
    triangles=[list(sub.indices[i:i+3]) for i in range(0,len(sub.indices),3)]
    for face in triangles:
        for i in face:
            if points[i] in by_position:parent[root(i)]=root(by_position[points[i]])
            else:by_position[points[i]]=i
        for i in face[1:]:parent[root(i)]=root(face[0])
    components={}
    for face in triangles:components.setdefault(root(face[0]),[]).append(face)
    groups.extend((sub.material,faces) for faces in components.values())
kit={'source':'Buildings/Housing/LargeBarrack/LargeBarrack.IronTeeth.Model',
     'gameVersion':'1.1.2.8','sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest(),'parts':{}}
for name,index,expected_material,count in (
        ('window',20,'WindowsAtlas.IronTeeth',34),
        ('doorJamb',8,'BaseWood_DarkBrown.IronTeeth',16),
        ('doorLintel',9,'BaseWood_DarkBrown.IronTeeth',16),
        ('doorRecess',12,'WindowsAtlas.IronTeeth',2)):
    material,faces=groups[index]
    assert material==expected_material and len(faces)==count,(name,material,len(faces))
    ids=sorted({i for face in faces for i in face});mapping={old:new for new,old in enumerate(ids)}
    kit['parts'][name]={'vertices':[props['position'][i] for i in ids],
        'uv':[props['uv0'][i] for i in ids],
        'faces':[[mapping[i] for i in reversed(face)] for face in faces],'material':material}
styles=ROOT/'outputs/native-civic-assets/NewStylesDistrictCenter.IronTeeth.timbermesh'
model=model_pb2.Model();model.ParseFromString(zlib.decompress(styles.read_bytes()))
node=model.nodes[0];assert node.name=='Dcenter_IT'
props={p.name:list(struct.iter_unpack('<'+'f'*p.scalarTypeDimension,p.data)) for p in node.vertexProperties}
parts=json.loads((ROOT/'outputs/native-civic-assets/NewStylesDistrictCenter.IronTeeth-parts.json').read_text())
kit['grandWindowSource']={'dependency':'Redic.NewStyles','version':'0.1',
    'resource':'Buildings/DistrictManagement/DistrictCenter/DistrictCenter.Ironteeth.Model',
    'sourceSha256':hashlib.sha256(styles.read_bytes()).hexdigest()}
for name,index,material,count in (('grandWindowSill',133,'BaseWood_DarkBrown.IronTeeth',8),
        ('grandWindowCrown',134,'BaseWood_DarkBrown.IronTeeth',34),
        ('grandWindowPanes',225,'WindowsAtlas.IronTeeth',4)):
    part=parts[index];assert part['node']==0 and part['material']==material and len(part['faces'])==count
    ids=sorted({i for face in part['faces'] for i in face});mapping={old:new for new,old in enumerate(ids)}
    kit['parts'][name]={'vertices':[props['position'][i] for i in ids],
        'uv':[props['uv0'][i] for i in ids],
        'faces':[[mapping[i] for i in reversed(face)] for face in part['faces']],'material':material}
kit['windowAssemblies']={
    'grand':{'parts':['grandWindowSill','grandWindowCrown','grandWindowPanes'],
             'origin':[.50344,.824725,.01613277569413185],'tangent':[1,0,0],'outward':[0,0,-1]},
    'lancet':{'parts':['lancetLeft','lancetRight','lancetSill','lancetCrown','lancetPanes'],
              'origin':[.60895,.584925,0],'tangent':[1,0,0],'outward':[0,0,-1]},
    'diamond':{'parts':['diamondFrame','diamondPanes'],
               'origin':[1.5,1.537325,0],'tangent':[1,0,0],'outward':[0,0,-1]},
    'factory':{'parts':['factoryGrid'],'origin':[.1,.64158,.827115],
               'tangent':[0,0,-1],'outward':[-1,0,0]},
}
for cache,resource,selections in (
    ('NewStylesFlat.IronTeeth','Buildings/Flats/Flat.IronTeeth',[
        ('lancetLeft',15,'BaseWood_DarkBrown.IronTeeth',6),
        ('lancetRight',16,'BaseWood_DarkBrown.IronTeeth',6),
        ('lancetSill',17,'BaseWood_DarkBrown.IronTeeth',8),
        ('lancetCrown',96,'WindowsAtlas.IronTeeth',16),
        ('lancetPanes',97,'WindowsAtlas.IronTeeth',4),
        ('diamondFrame',132,'WindowsAtlas.IronTeeth',24),
        ('diamondPanes',133,'WindowsAtlas.IronTeeth',2)]),
    ('NewStylesFoodplant.IronTeeth','Buildings/Food/Foodplant.IronTeeth',[
        ('factoryGrid',68,'WindowsAtlas.IronTeeth',16)])):
    source=ROOT/f'outputs/native-civic-assets/{cache}.timbermesh'
    model=model_pb2.Model();model.ParseFromString(zlib.decompress(source.read_bytes()))
    parts=json.loads((ROOT/f'outputs/native-civic-assets/{cache}-parts.json').read_text())
    kit[cache+'Source']={'dependency':'Redic.NewStyles','version':'0.1','resource':resource,
                        'sourceSha256':hashlib.sha256(source.read_bytes()).hexdigest()}
    for name,index,material,count in selections:
        part=parts[index];assert part['material']==material and len(part['faces'])==count
        node=model.nodes[part['node']]
        props={p.name:list(struct.iter_unpack('<'+'f'*p.scalarTypeDimension,p.data)) for p in node.vertexProperties}
        ids=sorted({i for face in part['faces'] for i in face});mapping={old:new for new,old in enumerate(ids)}
        kit['parts'][name]={'vertices':[props['position'][i] for i in ids],
            'uv':[props['uv0'][i] for i in ids],
            'faces':[[mapping[i] for i in reversed(face)] for face in part['faces']],'material':material}
(ROOT/'tools/asset-pipeline/housing-facade.json').write_text(json.dumps(kit,indent=2)+'\n')
print('Extracted native door and four explicit New Styles window assemblies; original meshes and UVs retained')
