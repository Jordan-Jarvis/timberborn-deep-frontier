"""Check saved selected aprons, their retained UVs, and assembled terrain clearance."""
import hashlib
import json
from pathlib import Path
import struct
import sys
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from pit_apron_components import BOUNDS,BOARD_TOP,BOARD_BOTTOM,recipe
from pit_layouts import LAYOUTS
from native_uv_contract import valid_native_uv
TERRAIN_MAX=.01


def test(model):
    path=ROOT/'src/DeepFrontier/Art/Source'/(model+'-ReferenceStudy.blend')
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.scene.frame_set(1)
    collection=bpy.data.collections[model+'.ReferenceStudy']
    apron=bpy.data.objects[model+'.Apron']
    authored=recipe(model)
    mesh=apron.data
    # 2026-10-22: the yard floors were cut back to the shrunk footprints
    # (pit_apron_components.BOUNDS), so the saved apron is checked against
    # the current recipe rather than the pre-migration deck. The enclosed-face
    # cull may omit only faces it recorded.
    culled=apron.get('df_enclosed_culled',0)
    assert len(mesh.polygons)==len(authored.faces)-culled,(model,len(mesh.polygons),len(authored.faces),culled)
    points=[Vector(v) for v in authored.vertices]
    for vertex in mesh.vertices:
        assert min((vertex.co-q).length for q in points)<2e-6,'Saved component differs from root recipe'
    uv_layer=mesh.uv_layers['UVMap']
    for polygon in mesh.polygons:
        material=mesh.materials[polygon.material_index].name
        assert all(valid_native_uv(material,uv_layer.data[i].uv) for i in polygon.loop_indices),material
    # The pits are triangle-budget models (industrial_budget.py): no bevel
    # modifier; the native atlases paint the edge highlights.
    from industrial_budget import MODELS as BUDGET_MODELS,BEVEL
    assert model in BUDGET_MODELS and BEVEL==0
    assert not any(m.type=='BEVEL' for m in apron.modifiers)
    assert 'bevel_weight_edge' not in mesh.attributes
    # The floor stays inside the registered footprint (artwork = native - origin).
    ox,oy,_=LAYOUTS[model]['origin'];sx,sy,_=LAYOUTS[model]['size']
    x0,y0,x1,y1=BOUNDS[model]
    assert -ox<=x0 and x1<=sx-ox and -oy<=y0 and y1<=sy-oy,(model,'yard floor outside the footprint')
    assert LAYOUTS[model]['baseZ']==0
    assert LAYOUTS[model]['origin'][2]==0
    # All saved objects participate in the visibility test; add an explicit
    # ground plane so a ray that misses the wearing top must hit terrain.
    graph=bpy.context.evaluated_depsgraph_get()
    vertices=[];triangles=[];owners=[];samples=[]
    for obj in collection.all_objects:
        if obj.type!='MESH' or obj.hide_render or 'liquid_surface' in obj:continue
        evaluated=obj.evaluated_get(graph);data=evaluated.to_mesh()
        try:
            data.calc_loop_triangles();offset=len(vertices)
            vertices.extend(evaluated.matrix_world@v.co for v in data.vertices)
            for tri in data.loop_triangles:
                ids=tuple(offset+i for i in tri.vertices)
                a,b,c=[vertices[i] for i in ids]
                normal=(b-a).cross(c-a)
                if normal.length<1e-10:continue
                triangles.append(ids);owners.append(obj.name)
                if obj==apron and normal.normalized().z>.999999 and all(abs(p.z-BOARD_TOP)<2e-6 for p in (a,b,c)):
                    center=(a+b+c)/3
                    samples.extend([center]+[center*.15+p*.85 for p in (a,b,c)])
        finally:evaluated.to_mesh_clear()
    x0,y0,x1,y1=BOUNDS[model]
    start=len(vertices)
    vertices.extend([Vector(p) for p in [(-x1-1,-y1-1,TERRAIN_MAX),(-x0+1,-y1-1,TERRAIN_MAX),(-x0+1,-y0+1,TERRAIN_MAX),(-x1-1,-y0+1,TERRAIN_MAX)]])
    triangles.extend([(start,start+1,start+2),(start,start+2,start+3)])
    owners.extend(['Terrain','Terrain'])
    tree=BVHTree.FromPolygons(vertices,triangles,all_triangles=True)
    assert samples,'No evaluated wearing surface at the authored top'
    terrain_hits=[];height=[];covering=set()
    for sample in samples:
        origin=Vector((sample.x,sample.y,.05))
        location,normal,index,distance=tree.ray_cast(origin,Vector((0,0,-1)),.10)
        assert location is not None,'Assembled ground ray missed both model and terrain'
        if owners[index]=='Terrain' or location.z<BOARD_TOP-2e-6:
            terrain_hits.append({'sample':list(sample),'hit':list(location),'owner':owners[index]})
        height.append(location.z);covering.add(owners[index])
    assert not terrain_hits,terrain_hits
    after=hashlib.sha256(path.read_bytes()).hexdigest()
    assert before==after,'Read-only verification source changed'
    return dict(model=model,sourceSha256=before,sourceUnchanged=True,
                boardBottom=BOARD_BOTTOM,boardTop=BOARD_TOP,nativeBaseZ=0,
                savedEqualsRecipe=True,nativeUvTilesInside=True,enclosedFacesCulled=culled,bevel=None,
                insideFootprint=True,
                terrainPlaneZ=TERRAIN_MAX,terrainEvidence='outputs/native-ground-clearance.json',
                assembledVisibilityRays=len(samples),terrainWonRays=0,
                hitHeightRange=[min(height),max(height)],hitObjects=sorted(covering),
                limitation='Flat support terrain at frame1; native path/depth behavior remains an in-game check.')


reports=[]
for model in BOUNDS:
    result=test(model);reports.append(result);print(json.dumps(result),flush=True)
(ROOT/'outputs/terrain-contact/pit-apron-source-checks.json').write_text(json.dumps(reports,indent=2)+'\n')
