"""Inspect the candidate's exact model, recipes, sockets and door graph."""
import hashlib,json,struct,sys,zlib
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv
folder=root/'outputs/research-integration/Data/Buildings/Science/MaterialsLaboratory'
bp=json.loads((folder/'MaterialsLaboratory.IronTeeth.blueprint.json').read_text())
layout=json.loads((root/'tools/research-layouts.json').read_text())['MaterialsLaboratory']
recipe=json.loads((root/'outputs/research-integration/Data/Recipes/Recipe.MaterialsResearch.blueprint.json').read_text())['RecipeSpec']
payload=(folder/'MaterialsLaboratory.IronTeeth.Model.timbermesh').read_bytes()
assert payload==(folder/'MaterialsLaboratory.IronTeeth.ConstructionStage0.Model.timbermesh').read_bytes()
model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
names=[n.name for n in model.nodes];assert len(names)==len(set(names))
tracks=[(n.name,len(a.frames)) for n in model.nodes for a in n.nodeAnimations]
assert sorted(tracks)==[(f'#MaterialsLaboratory.{n}',121) for n in ('Flywheel','PressScrew','TestRam')]
assert (folder/'Icon.png').stat().st_size>100
assert bp['BuildingSpec']['ScienceCost']==12000
assert bp['WorkplaceSpec']['MaxWorkers']==4
# 6,500 hp: the late-game power rule's floor at 12,000 science (authored 600).
assert bp['MechanicalNodeSpec']=={'PowerInput':6500,'PowerOutput':0,'IsShaft':False}
assert recipe['ProducedSciencePoints']==800 and recipe['CycleDurationInHours']==2 and recipe['Products']==[]
assert recipe['Ingredients']==[{'Id':'Gear','Amount':4},{'Id':'Concrete','Amount':2},{'Id':'MetalBlock','Amount':1},{'Id':'Water','Amount':1}]
# Any-face Timber Pipes connection: recipe Water is the liquid; no port restriction.
assert 'BuildingPipeTargetPortsSpec' not in bp
# The lab's recipe list is authored in tools/research_content.json (buildings[].recipes).
research=json.loads((root/'tools/research_content.json').read_text(encoding='utf-8'))
lab=next(b for b in research['buildings'] if b['id']=='MaterialsLaboratory')
assert bp['ManufactorySpec']['ProductionRecipeIds']==lab['recipes'], bp['ManufactorySpec']['ProductionRecipeIds']
assert 'WorkshopRandomNeedApplierSpec' not in bp
# The donor Smelter's own effects are gone, and since the roof flues went (no
# roof vents, user 2026-10-30) the lab registers no smoke: no attachments, no
# particle controller and no smog emitter.
smoke=json.loads((root/'outputs/research-integration/MaterialsLaboratory-smoke-registration.json').read_text())['smokeEmitters']
assert smoke==[]
for spec in ('TemplateAttachmentsSpec','WorkshopParticleControllerSpec','SmogEmitterSpec'):
    assert spec not in bp, spec
def cell(d):return tuple(d[k] for k in ('X','Y','Z'))
# 10x8 since the outdoor shelves and planters went (2026-10-22); 5 high
# since the one-layer storeys (2026-10-30).
assert cell(bp['BlockObjectSpec']['Size'])==(10,8,5)
blocks=bp['BlockObjectSpec']['Blocks'];assert len(blocks)==400
def block(c):
    x,y,z=c;return blocks[(z*8+y)*10+x]
routes={tuple(n['cell']) for n in layout['nodes']};graph={c:set() for c in routes}
for a,b in layout['edges']:
    a,b=tuple(a),tuple(b);assert a in routes and b in routes
    assert sum(abs(x-y) for x,y in zip(a,b))==1
    graph[a].add(b);graph[b].add(a)
visited=set();pending=[tuple(layout['entrance'])]
while pending:
    c=pending.pop()
    if c in visited:continue
    visited.add(c);pending.extend(graph[c]-visited)
assert visited==routes and {tuple(c) for c in layout['doorNodes']}<=visited
# Player-path terrace deck since 2026-10-30 (every flat roof tile placeable):
# the terrace cells are free over stackable slabs, the rails open on player
# paths, the records office door is the deck door link.
assert layout['deckMode']=='PlayerPlacedPaths' and 'BuildingWalkwaySpec' not in bp
interior={tuple(c) for c in layout['interiorCells']}
for n in layout['nodes']:
    c=tuple(n['cell'])
    if c in interior:continue
    assert block(c)['Occupations']=='None',c
    assert block((c[0],c[1],c[2]-1))['Stackable']=='BlockObject',c
deck=bp['PlatformDeckSpec']
assert deck['Doors']==[{k:dict(zip('XYZ',v)) for k,v in d.items()} for d in layout['doorLinks']]
assert len(deck['Openings'])==len(layout['ports'])
for p in deck['Openings']:
    assert not p['ShownNodes'],p['Id']
    for name in p['HiddenNodes']:assert names.count(name)==1,name
assert bp['BlockObjectNavMeshSettingsSpec']['GenerateFloorsOnStackable']
for socket in bp['TransputProviderSpec']['Transputs']:assert block(cell(socket['Coordinates']))['Occupations']=='All'
for i in range(4):assert names.count(f'#Slot#Entrance{i}')==1
uv_count=0
for node in model.nodes:
    if not node.meshes:continue
    uv=list(struct.iter_unpack('<ff',next(p.data for p in node.vertexProperties if p.name=='uv0')))
    for mesh in node.meshes:
        if mesh.material.endswith('.IronTeeth'):
            for i in set(mesh.indices):
                assert valid_native_uv(mesh.material,uv[i])
                if mesh.material=='Details.IronTeeth':
                    u,v=uv[i];assert .6199<=u<=.8801 and .3289<=v<=.3481
                uv_count+=1
report={'scope':'Candidate export checks; actual native operation remains to test',
    'modelSha256':hashlib.sha256(payload).hexdigest(),'nodes':len(names),'animationTracks':tracks,
    'nativeUvVertices':uv_count,'connectedRouteCells':len(routes),'railOpenings':len(bp['PlatformDeckSpec']['Openings']),
    'terraceSupportCells':sum(b['Stackable']=='BlockObject' for b in blocks),'scienceUnlock':12000,
    'sciencePerBatch':800,'powerDemandHp':6500,'powerOutputHp':0}
(root/'outputs/research-integration/export-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
