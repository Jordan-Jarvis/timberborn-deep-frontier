"""Read-only assembled native-ground and bank-apron surface checks."""
import hashlib,json
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from hatchery_structure import BANK_APRON_SURFACE,PLATFORMS,source
from zfight_audit import audit

def check_ground(folder,source_hash):
    contract=BANK_APRON_SURFACE
    native_path=Path(__file__).resolve().parents[2]/'outputs/native-ground-clearance.json'
    native_ground=json.loads(native_path.read_text())
    actual_terrain=contract['nativeFloor']+native_ground['flatTopHeightMax']
    if actual_terrain>contract['terrainTop']:raise ValueError('Installed terrain exceeds the authored clearance envelope')
    def point(native):
        x,y,z=source(native);return Vector((-x,-y,z))
    # Explicit assembled test fixture, never written into the source scene.
    mesh=bpy.data.meshes.new('Audit.NativeBankPlane')
    mesh.from_pydata([point((x,y,actual_terrain)) for x,y in ((0,0),(8,0),(8,1),(0,1))],[],[(0,1,2,3)])
    mesh.uv_layers.new(name='UVMap')
    for loop,uv in zip(mesh.uv_layers.active.data,((0,0),(8,0),(8,1),(0,1)),strict=True):loop.uv=uv
    material=bpy.data.materials.new('Audit.NativeTerrainSurface');mesh.materials.append(material)
    ground=bpy.data.objects.new('Audit.NativeBankPlane',mesh);bpy.context.scene.collection.objects.link(ground)
    graph=bpy.context.evaluated_depsgraph_get();results=[];failures=[]
    aprons=[bpy.data.objects['FishHatchery.Deck.'+name] for name in ('MainFrontApron','CanopyFrontApron')]
    for obj in aprons:
        ident=obj.name.removeprefix('FishHatchery.Deck.');x0,y0,_,x1,y1,_=PLATFORMS[ident]
        tree=BVHTree.FromObject(obj,graph)
        for x in [x0+.01+(x1-x0-.02)*i/20 for i in range(21)]:
            for y in [y0+.0001,*[y0+i*.2 for i in range(1,5)],y1-.0001]:
                location,_,_,_=tree.ray_cast(point((x,y,1.03)),Vector((0,0,-1)),.10)
                actual=None if location is None else location.z+1
                results.append({'object':obj.name,'nativePoint':[x,y],'surface':'grooveBacking','height':actual})
                if actual is None or abs(actual-contract['backingTop'])>1e-6:failures.append(results[-1])
            for row in range(5):
                y=y0+(row+.5)*.2
                location,_,_,_=tree.ray_cast(point((x,y,1.03)),Vector((0,0,-1)),.10)
                actual=None if location is None else location.z+1
                results.append({'object':obj.name,'nativePoint':[x,y],'surface':'wearingBoard','height':actual})
                if actual is None or abs(actual-contract['wearingTop'])>1e-6:failures.append(results[-1])
    report=audit([ground,*aprons],.0005,.0005)
    bpy.data.objects.remove(ground,do_unlink=True);bpy.data.meshes.remove(mesh);bpy.data.materials.remove(material)
    paths=json.loads((folder/'native-path-heights.json').read_text())
    roof=[p for p in paths if p['name'].split('/')[-1].startswith('roofpath')]
    if len(roof)!=6:raise ValueError('Native roof path inspection must include all six connection variants')
    roof_min=min(model['upwardMinimumHeight'] for p in roof for model in p['models'])
    clearance=roof_min-(contract['wearingTop']-contract['nativeFloor'])
    if clearance<=.0005:raise ValueError('Actual native RoofPath surface does not clear authored apron boards')
    result={'scope':'Saved apron geometry assembled against the maximum measured upward native terrain height; native runtime selection remains to be tested',
            'sourceSha256':source_hash,'surfaceContract':contract,'surfaceProbes':len(results),'surfaceFailures':failures,
            'nativeTerrainModelsInspected':native_ground['terrainModels'],'nativeTerrainMaximumTop':actual_terrain,
            'nativeTerrainEvidenceSha256':hashlib.sha256(native_path.read_bytes()).hexdigest(),
            'backingTerrainClearance':contract['backingTop']-actual_terrain,
            'wearingTerrainClearance':contract['wearingTop']-actual_terrain,
            'roofPathVariants':len(roof),'nativeRoofPathMinimumUpwardSurfaceHeight':roof_min,
            'roofPathBoardClearance':clearance,'nativePathEvidenceSha256':hashlib.sha256((folder/'native-path-heights.json').read_bytes()).hexdigest(),
            'assembledVisibleOverlapPairs':report['visibleConflicts'],'assembledOverlapReport':report}
    (folder/'bank-terrain-checks.json').write_text(json.dumps(result,indent=2)+'\n')
    if failures or report['visibleConflicts']:raise ValueError('Bank apron fails assembled terrain surface audit')
    return result
