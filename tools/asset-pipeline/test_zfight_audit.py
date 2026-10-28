"""Observable geometry cases for the depth-conflict detector."""
import json,sys
from pathlib import Path
import bpy
from mathutils import Matrix,Vector
sys.path.insert(0,str(Path(__file__).parent))
from zfight_audit import audit

red=bpy.data.materials.new('Red');blue=bpy.data.materials.new('Blue')

def panel(name,material,z=0,offset=0,uv_shift=0,rotation=None):
    points=[Vector((x+offset,y,z)) for x,y in ((0,0),(1,0),(1,1),(0,1))]
    if rotation:points=[rotation@p for p in points]
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(points,[],[(0,1,2,3)])
    obj=bpy.data.objects.new(name,mesh);bpy.context.scene.collection.objects.link(obj)
    mesh.materials.append(material);layer=mesh.uv_layers.new()
    for loop,p in zip(layer.data,((0,0),(1,0),(1,1),(0,1))):loop.uv=(p[0]+uv_shift,p[1])
    return obj

results=[]
def check(name,objects,visible,duplicates=False):
    bpy.context.view_layer.update();r=audit(objects)
    assert bool(r['visibleConflicts'])==visible,(name,r)
    if duplicates:assert r['identicalMaterialAndUvPairs']>0,(name,r)
    results.append({'case':name,'visibleConflicts':r['visibleConflicts'],
                    'occludedConflicts':r['occludedConflicts'],'identicalPairs':r['identicalMaterialAndUvPairs']})

a=panel('Base',red)
check('different materials on coincident faces',[a,panel('SamePlane',blue)],True)
check('same material, different texture mapping',[a,panel('ShiftedUv',red,uv_shift=.2)],True)
check('identical material and UV result',[a,panel('SameUv',red)],False,True)
check('positive near-plane separation',[a,panel('NearPlane',blue,z=.0002)],True)
check('clear depth separation',[a,panel('ClearDepth',blue,z=.01)],False)
check('shared edge only',[a,panel('SharedEdge',blue,offset=1)],False)
check('visible partial overlap',[a,panel('Partial',blue,offset=.4)],True)
rotation=Matrix.Rotation(.45,3,'X')
check('angled roof overlap',[panel('SlopeA',red,rotation=rotation),panel('SlopeB',blue,rotation=rotation)],True)
# A larger opaque plate blocks every outward probe above the overlap. Other
# test objects are omitted explicitly, so they cannot contaminate this case.
cover=panel('OccludingCover',red,z=.2);cover.scale=(4,4,1);cover.location=(-1.5,-1.5,0)
check('buried joint',[a,panel('HiddenPlane',blue),cover],False)
path=Path(__file__).resolve().parents[2]/'outputs/zfight/detector-tests.json'
path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
print('ALL ZFIGHT GEOMETRY CASES PASSED',json.dumps(results),flush=True)
