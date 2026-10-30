"""Inspect the turbine's exported bytes, binding graph and authored water seal."""
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path

root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv

folder=root/'outputs/hydro-integration/Data/Buildings/Power/ReinforcedHydroTurbine'
bp=json.loads((folder/'ReinforcedHydroTurbine.IronTeeth.blueprint.json').read_text())
layout=json.loads((root/'tools/hydro-layouts.json').read_text())['ReinforcedHydroTurbine']
payload=(folder/'ReinforcedHydroTurbine.IronTeeth.Model.timbermesh').read_bytes()
assert payload==(folder/'ReinforcedHydroTurbine.IronTeeth.ConstructionStage0.Model.timbermesh').read_bytes()
model=model_pb2.Model()
model.ParseFromString(zlib.decompress(payload))
names=[n.name for n in model.nodes]
assert len(names)==len(set(names))
tracks=[(n.name,len(a.frames)) for n in model.nodes for a in n.nodeAnimations]
assert sorted(tracks)==[('#Hydro.GeneratorCoupling',121),('#Hydro.TurbineRunner',121)]
assert (folder/'Icon.png').stat().st_size>100
assert bp['MechanicalNodeSpec']['PowerInput']==0
assert not any(k in bp for k in ('WaterWheelSpec','WaterPoweredGeneratorSpec','ManufactorySpec','WorkplaceSpec'))
def cell(value):
    return tuple(value[k] for k in ('X','Y','Z'))
# One-storey workshop since the 2026-10-30 compaction (8x10x7 -> 8x10x6).
assert cell(bp['BlockObjectSpec']['Size'])==(8,10,6)
blocks=bp['BlockObjectSpec']['Blocks']
assert len(blocks)==8*10*6
def block(c):
    x,y,z=c
    return blocks[(z*10+y)*8+x]
for x in range(4,8):
    for y in (2,3):
        for z in range(6):
            assert block((x,y,z))['Occupations']=='None','Dam continuation blocked'
routes={tuple(n['cell']) for n in layout['nodes']}
graph={c:set() for c in routes}
for a,b in layout['edges']:
    a,b=tuple(a),tuple(b)
    assert a in routes and b in routes
    assert sum(abs(x-y) for x,y in zip(a,b))==1
    graph[a].add(b);graph[b].add(a)
visited=set()
pending=[tuple(layout['entrance'])]
while pending:
    c=pending.pop()
    if c in visited:continue
    visited.add(c);pending.extend(graph[c]-visited)
assert visited==routes
# Player-path terrace deck since 2026-10-30 (every flat roof tile placeable):
# the lane cells are free over stackable foundation roofs, with no door links.
assert layout['deckMode']=='PlayerPlacedPaths' and 'BuildingWalkwaySpec' not in bp and not layout['doorLinks']
for c in routes:
    assert block(c)['Occupations']=='None',c
    assert block((c[0],c[1],c[2]-1))['Stackable']=='BlockObject',c
assert bp['PlatformDeckSpec']['Doors']==[] and bp['BlockObjectNavMeshSettingsSpec']['EdgeGroups']==[]
for x in range(4):
    for y in (2,3):assert block((x,y,5))['Stackable']=='BlockObject'
assert len(bp['PlatformDeckSpec']['Openings'])==len(layout['ports'])
for opening in bp['PlatformDeckSpec']['Openings']:
    assert not opening['ShownNodes'],opening['Id']
    for name in opening['HiddenNodes']:assert names.count(name)==1,name
hydro=bp['HydroTurbineSpec']
solid={cell(c) for c in hydro['SolidWaterCells']}
closed={cell(c) for c in hydro['ClosedGateCells']}
planes={cell(c) for c in bp['FinishableHorizontalWaterObstacleSpec']['Obstacles']}
assert len(solid)==len(hydro['SolidWaterCells']) and not solid&closed
assert closed=={(1,3,0),(1,3,1),(2,3,0),(2,3,1)}
# Walk both physical lanes and prove every side/floor/roof seal.
assert [cell(c) for c in hydro["Gates"]]==[(1,3,0),(2,3,0)]
assert [cell(c) for c in hydro["Intakes"]]==[(1,-1,0),(2,-1,0)]
assert [cell(c) for c in hydro["Outlets"]]==[(1,5,0),(2,5,0)]
for y in range(6):
    for x in (1,2):
        assert (x,y,0) in planes and (x,y,2) in planes
        for z in range(2):assert (x,y,z) not in solid
    for z in range(2):assert (0,y,z) in solid and (3,y,z) in solid
for socket in bp['TransputProviderSpec']['Transputs']:
    assert block(cell(socket['Coordinates']))['Occupations']=='All'
uv_count=0
for node in model.nodes:
    if not node.meshes:continue
    uv=list(struct.iter_unpack('<ff',next(p.data for p in node.vertexProperties if p.name=='uv0')))
    for mesh in node.meshes:
        assert mesh.material!='Details.IronTeeth','Decorative-label sheet on turbine hardware'
        if mesh.material.endswith('.IronTeeth'):
            for index in set(mesh.indices):
                assert valid_native_uv(mesh.material,uv[index])
                uv_count+=1
report={
    'scope':'Candidate export, grid and water-seal checks; native runtime and pump balance pending',
    'modelSha256':hashlib.sha256(payload).hexdigest(),'nodes':len(names),
    'animationTracks':tracks,'nativeUvVertices':uv_count,'routeCells':len(routes),
    'adaptiveOpenings':len(bp['PlatformDeckSpec']['Openings']),
    'supportCells':sum(b['Stackable']=='BlockObject' for b in blocks),
    'solidWaterCells':len(solid),'horizontalWaterPlanes':len(planes),
    'powerConnections':len(bp['TransputProviderSpec']['Transputs']),
}
(root/'outputs/hydro-integration/export-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
