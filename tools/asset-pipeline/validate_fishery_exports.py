"""Check authored fishery geometry/data contracts before native acceptance."""
import collections,hashlib,json,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def require(value,detail):
    if not value:raise ValueError(detail)
layout=read('tools/civic-layouts.json')['FisheryWorks']
blueprint=read('src/DeepFrontier/Data/Buildings/Food/FisheryWorks/FisheryWorks.IronTeeth.blueprint.json')
payload=(ROOT/'src/DeepFrontier/Data/Buildings/Food/FisheryWorks/FisheryWorks.IronTeeth.Model.timbermesh').read_bytes()
model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
names=collections.Counter(n.name for n in model.nodes)
xyz_=lambda c:{'X':c[0],'Y':c[1],'Z':c[2]}
blocks_=None
require(all(n==1 for n in names.values()),'Duplicate fishery mesh nodes')
# 6x5x3 since the second shrink pass (2026-11-01; 11x8x4 before, 11x8x7
# before the 2026-10-30 compaction, 12x10 before 2026-10-22).
W,D,H=6,5,3
require([blueprint['BlockObjectSpec']['Size'][axis] for axis in ('X','Y','Z')]==[W,D,H],'Waterfront Fishery registration changed')
require(len(blueprint['BlockObjectSpec']['Blocks'])==W*D*H,'Incomplete occupied-cell specification')
blocks_=blueprint['BlockObjectSpec']['Blocks']
cells={tuple(n['cell']) for n in layout['nodes']};graph={n:set() for n in cells}
for a,b in layout['edges']:
    a,b=tuple(a),tuple(b)
    require(a in cells and b in cells and sum(abs(a[i]-b[i]) for i in range(3))==1,'Invalid civic edge')
    graph[a].add(b);graph[b].add(a)
visited=set();queue=[tuple(layout['entrance'])]
while queue:
    cell=queue.pop()
    if cell in visited:continue
    visited.add(cell);queue.extend(graph[cell]-visited)
require(visited==cells,'Disconnected fishery routes')
require(len(layout['doorNodes'])==2 and {c[2] for c in layout['doorNodes']}=={0,1},'Waterfront doorway contract changed')
# Player-placed-path decks since 2026-10-30 (every flat roof tile placeable):
# no built-in walkway; the upper hall door is the deck door link. No rails
# since the 2026-10-31 roof pass.
require(layout['deckMode']=='PlayerPlacedPaths' and 'BuildingWalkwaySpec' not in blueprint,'Fishery decks must be player-path decks')
deck=blueprint['PlatformDeckSpec']
require(deck['Openings']==[] and layout['ports']==[],'The Fishery decks have no rails (2026-10-31 roof pass)')
require(not any(n.startswith(('WalkwayRail','WalkwayGroup')) for n in names),'Railing node exported')
require(deck['Doors']==[{k:xyz_(v) for k,v in d.items()} for d in layout['doorLinks']],'Deck doors differ from the layout door links')
interior={tuple(c) for c in layout['interiorCells']}
for n in layout['nodes']:
    c=tuple(n['cell'])
    if c in interior or c[2]==0:continue
    require(blocks_[(c[2]*D+c[1])*W+c[0]]['Occupations'] in ('None','Corners'),'Deck cell is occupied: '+str(c))
    require(blocks_[((c[2]-1)*D+c[1])*W+c[0]]['Stackable']=='BlockObject','Deck slab is not stackable: '+str(c))
require(blueprint['BlockObjectNavMeshSettingsSpec']['GenerateFloorsOnStackable'],'Deck floors need GenerateFloorsOnStackable')
site=read('tools/waterside_sites.json')['FisheryWorks']
xyz=lambda c:{'X':c[0],'Y':c[1],'Z':c[2]}
require(site['workCells'] is None and 'WaterDepthWorkCellsSpec' not in blueprint and 'TickableWaterBuildingSpec' not in blueprint,'Fishery must not gain a site water requirement')
require(blueprint['AdaptiveSupportsSpec']=={'Columns':[xyz(c) for c in site['supports']['columns']],'MaxDepth':site['supports']['maxDepth'],
    'SegmentNodeName':'#SupportSegment','FootNodeName':'#SupportFoot'},'Wing piles differ from the waterside contract')
require(names['#SupportSegment']==1 and names['#SupportFoot']==1,'Exported model lacks exactly one support segment/foot template')
blocks=blueprint['BlockObjectSpec']['Blocks'];cellAt=lambda x,y,z:blocks[(z*D+y)*W+x]
wing={tuple(c) for c in site['supports']['groundOptionalCells']}
for x,y,z in wing:require(z==0 and cellAt(x,y,z)['MatterBelow']=='Any' and cellAt(x,y,z)['Occupations']=='All','Wing cell is not an occupied ground-optional basin cell')
# 29 occupied ground cells since the second shrink pass (2026-11-01): the 10
# wing cells, the 16 of the lower hall and the 3 of the undercroft; cell (5,4)
# behind the hall is free. Less the 9 ground-optional wing cells.
require(sum(1 for b in blocks if b['MatterBelow']=='GroundOrStackable')==29-len(wing),'Fishery ground contract changed outside the wing')
for x,y,z in site['supports']['columns']:require(z==-1 and (x,y,0) in wing,'Pile is not directly below a wing cell')
for cell in ((3,0,0),(1,0,0),(3,4,0)):require(cellAt(*cell)['MatterBelow']=='GroundOrStackable','Door cell, crane mast or water tanks left the land: '+str(cell))
origin=next(n for n in model.nodes if n.name=='IndustrialGridOrigin').position
for node in (n for n in model.nodes if n.name in ('#SupportSegment','#SupportFoot')):
    require(node.position.y+origin.y<=-2,'Support template is not parked underground')
reservoir=blueprint['WorkshopReservoirSpec']
# The small front basin went with the forced front decoration (2026-10-22).
require(reservoir['Capacity']==90 and len(reservoir['Surfaces'])==5,'Water capacity/visible reservoir mismatch')
require(collections.Counter(s['Mesh'] for s in reservoir['Surfaces'])=={
    'Meshes/DeepFrontier/ReservoirRectangle':3,'StockpileGoodModels/SmallLiquidPlane':2},'Water geometry shape bindings')
require(reservoir['WheelNodes']==['FisheryNativeWheel'] and reservoir['FlowNodes']==['FisheryCascade'],'Water mechanism bindings changed')
cascade=next(n for n in model.nodes if n.name=='FisheryCascade')
require({m.material for m in cascade.meshes}=={'Water'},'Cascade must use native animated water material')
assembly=read('outputs/reference-studies/FisheryWorks-native-assembly.json')
for p in assembly['props']:require(not any(p['name'] in name for name in names),'Native prop copy shipped in mesh')
require(any(p['resource']=='Buildings/Power/CompactWaterWheel/CompactWaterWheel.IronTeeth.Model' for p in assembly['props']),'Native wheel reference missing')
require({n for n in names if n.startswith('#Slot#Entrance')}=={'#Slot#Entrance0','#Slot#Entrance1','#Slot#Entrance2'},'Native worker doorway slots')
for i,(point,facing) in enumerate(zip(layout['idle'],layout['idleFacing'],strict=True)):
    marker=next(n for n in model.nodes if n.name==f'#Slot#Entrance{i}')
    require(all(abs(a-b)<1e-5 for a,b in zip((marker.position.x,marker.position.y,marker.position.z),(point[0],point[2],point[1]))),'Worker idle marker moved from its doorway')
    q=marker.rotation
    forward=(2*(q.x*q.z+q.w*q.y),1-2*(q.x*q.x+q.y*q.y))
    require(all(abs(a-b)<1e-5 for a,b in zip(forward,facing)),'Worker idle marker faces into the wall')
tracks=[(n.name,len(a.frames)) for n in model.nodes for a in n.nodeAnimations]
require(tracks==[('#FisheryWorks.CarvedSign',301),('#FisheryWorks.CraneNet',301)],'Fishery source animations changed')
require(blueprint['MechanicalNodeSpec']['PowerInput']==80 and blueprint['MechanicalNodeSpec']['PowerOutput']==0,'Demand/output mixed')
native={'BaseWood_DarkBrown.IronTeeth','IrregularPlanks_DarkBrown.IronTeeth','RoofPlanks.IronTeeth','BaseMetal.IronTeeth','Details.IronTeeth','Plaster_White.IronTeeth','Plaster_Orange.IronTeeth','IrregularPlanks_MetalForged.IronTeeth'}
uv_count=0
for node in model.nodes:
    meshes=[m for m in node.meshes if m.material in native]
    if not meshes:continue
    uv=list(struct.iter_unpack('<ff',next(p for p in node.vertexProperties if p.name=='uv0').data))
    for mesh in meshes:
        for i in set(mesh.indices):
            require(valid_native_uv(mesh.material,uv[i]),'UV outside authored/native contract')
            uv_count+=1
report={'scope':'Source/export and blueprint checks only; runtime results are separate','modelSha256':hashlib.sha256(payload).hexdigest(),
    'nodes':len(model.nodes),'nativeUvVertices':uv_count,'connectedRouteCells':len(cells),'openings':len(layout['ports']),
    'doors':[0,1],'waterSurfaces':5,'waterCapacity':90,'nativeProps':len(assembly['props']),'animationTracks':tracks}
(ROOT/'outputs/civic-integration/fishery-static-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
