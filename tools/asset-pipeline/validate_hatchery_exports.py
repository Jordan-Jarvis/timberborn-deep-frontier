"""Verify submerged registration, native assets and the actual exported payload."""
import collections,hashlib,json,math,struct,sys,zlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv
def read(path):return json.loads((ROOT/path).read_text(encoding='utf-8'))
def require(condition,message):
    if not condition:raise ValueError(message)
layout=read('tools/civic-layouts.json')['FishHatchery']
b=read('src/DeepFrontier/Data/Buildings/Food/FishHatchery/FishHatchery.IronTeeth.blueprint.json')
folder=ROOT/'src/DeepFrontier/Data/Buildings/Food/FishHatchery'
payload=(folder/'FishHatchery.IronTeeth.Model.timbermesh').read_bytes()
model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
names=collections.Counter(n.name for n in model.nodes)
require(all(v==1 for v in names.values()),'Duplicate model nodes')
require(payload==(folder/'FishHatchery.IronTeeth.ConstructionStage0.Model.timbermesh').read_bytes(),'Construction model mismatch')
# Compact early-game footprint since 2026-10-26 (8x8x5 with perimeter docks before).
# 3 high since the one-layer headhouse and canopy (2026-10-30; was 5).
require(list(b['BlockObjectSpec']['Size'].values())==[7,7,3] and b['BlockObjectSpec']['BaseZ']==1,'Submerged registration changed')
W,D=7,7
# Native Entrance = the bank-height path cell in front of the door cell (1,0,1) (tools/native_entrance.mjs).
require(b['BlockObjectSpec']['Entrance']['Coordinates']=={'X':1,'Y':-1,'Z':1},'Entrance is not the bank-height path cell in front of the door')
require(b['BuildingAccessibleSpec']['LocalAccess']=={'X':1.5,'Y':1,'Z':1},'Workshop final access is not centered on the one-tile bank-height arch')
site=read('tools/waterside_sites.json')['FishHatchery']
xyz=lambda c:{'X':c[0],'Y':c[1],'Z':c[2]}
require('TickableWaterBuildingSpec' not in b and 'WaterNeederSpec' not in b,'WaterDepthWorkCells must be the only water-needing component')
work=b['WaterDepthWorkCellsSpec']
require(work=={'WorkCells':[xyz(c) for c in site['workCells']['cells']],'MinDepth':site['workCells']['minDepth'],
               'MaxDepth':site['workCells']['maxDepth'],'Hysteresis':site['workCells']['hysteresis']},'Pen work cells differ from the waterside contract')
require(work['WorkCells'][0]=={'X':1,'Y':5,'Z':0},'Contamination sample is not the verified pen probe')
require(0<work['MinDepth']-work['Hysteresis'] and work['MinDepth']+work['Hysteresis']<work['MaxDepth']-work['Hysteresis'],'Invalid water range')
supports=b['AdaptiveSupportsSpec']
require(len(site['supports']['columns'])==4,'The compact deck stands on four piles')
require(supports=={'Columns':[xyz(c) for c in site['supports']['columns']+site['supports']['bankColumns']],'MaxDepth':site['supports']['maxDepth'],
                   'SegmentNodeName':'#SupportSegment','FootNodeName':'#SupportFoot'},'Pile/bank post columns differ from the waterside contract')
require(names['#SupportSegment']==1 and names['#SupportFoot']==1,'Exported model lacks exactly one support segment/foot template')
require('FishHatchery.Dock.Supports' not in names,'Fixed-length short posts still ship in the model')
require(len(b['BlockObjectSpec']['Blocks'])==W*D*3,'Incomplete occupied-cell data')
require(-1.02<min(v['Center']['Y']-v['Size']['Y']/2 for v in b['Children']['#Finished']['CollidersSpec']['BoxColliders'])<-.8,'Actual submerged cage colliders lost their BaseZ offset')
cells={tuple(n['cell']) for n in layout['nodes']}
require(layout['deckMode']=='PlayerPlacedPaths' and 'BuildingWalkwaySpec' not in b,'Hatchery still owns outdoor path routes')
require(b['BlockObjectNavMeshSettingsSpec']['GenerateFloorsOnStackable'],'Native platform floor generation is disabled')
require(not any('Path' in cell['Occupations'] for cell in b['BlockObjectSpec']['Blocks']),'Deck cells reserve player paths')
require(b['PlatformDeckSpec']['Doors']==[{'Interior':{'X':1,'Y':1,'Z':1},'Exterior':{'X':1,'Y':0,'Z':1}}],'Hatchery native doorway connection changed')
require(b['PathModelTypeEnforcerSpec']=={'PathModelType':'Roof'},'Bank apron does not request native roof path visuals')
# 14 suggested path cells plus the interior door node since the compact deck.
require(len(cells)==15,'Suggested clear deck/door registration mismatch')
for n in layout['nodes']:
    require(n['cell'][2]-1==n['point'][2],'Model/grid height mismatch')
for p in b['PlatformDeckSpec']['Openings']:
    for name in p['HiddenNodes']+p['ShownNodes']:require(names[name]==1,'Missing rail binding '+name)
require(len(b['PlatformDeckSpec']['Openings'])==3,'Rail opening count changed')
blocks=b['BlockObjectSpec']['Blocks']
cell=lambda x,y,z:blocks[(z*D+y)*W+x]
for x in range(W):
    require(cell(x,0,0)['Occupations']=='None','Bank terrain row is occupied')
    # Door cell on native ground; every other bank apron may overhang a lower
    # shore on the adaptive bank post directly below it.
    if [x,0,1] in site['supports']['groundCells']:
        require(cell(x,0,1)['MatterBelow']=='GroundOrStackable' and [x,0,0] not in site['supports']['bankColumns'],'Door bank cell lost its ground support')
    else:
        require(cell(x,0,1)['MatterBelow']=='Any' and [x,0,0] in site['supports']['bankColumns'],'Bank apron overhang has no adaptive bank post')
for x in (0,1,2,3,4,6):require(cell(x,0,1)['Occupations']=='Floor','Bank apron must reserve its physical floor but leave player paths available')
for x,y,z in site['supports']['columns']:
    require(cell(x,y,0)['MatterBelow']=='Any' and cell(x,y,0)['Occupations']!='None','Pile does not stand under an over-water deck block')
require(site['supports']['groundCells']==[[1,0,1]] and sum(1 for v in blocks if v['MatterBelow']!='Any')==1,'Only the door cell may require ground')
# Cursor anchor: replay native BlockObjectPreviewPicker.ComposeCoordinates for a
# cursor anywhere on the hovered top face at cell (0,0). The CustomPivot is
# rotated but never flipped; Blocks.Transform flips (W-1-x), then rotates. In
# every rotation the hovered cell is the door cell, on native ground, so the
# height comes from the bank; flipped, it is the door's mirror on the bank row.
pivot=b['PlaceableBlockObjectSpec']['CustomPivot']
require(pivot=={'HasCustomPivot':True,'Coordinates':{'X':1.5,'Y':.5,'Z':0}},'Cursor anchor is not the door cell')
def rotate(o,x,y):return {0:(x,y),90:(y,-x),180:(-x,-y),270:(-y,x)}[o]
sign=lambda v:1 if v>=0 else -1   # Mathf.Sign(0) == 1
pick_checks=0
for o in (0,90,180,270):
    for flipped in (False,True):
        cx,cy=rotate(o,pivot['Coordinates']['X'],pivot['Coordinates']['Y'])
        for fx in (.02,.5,.98):
            for fy in (.02,.5,.98):
                origin=(math.floor(fx-cx+.5*sign(cx)),math.floor(fy-cy+.5*sign(cy)))
                hovered=[(lx,ly) for lx in range(W) for ly in range(D)
                         if tuple(a+c for a,c in zip(origin,rotate(o,W-1-lx if flipped else lx,ly)))==(0,0)]
                expected=(W-1-1,0) if flipped else (1,0)
                require(hovered==[expected],f'Cursor cell is not the door (mirror when flipped): {o} {flipped} {hovered}')
                pick_checks+=1
# Deck objects stand on z=0 slabs below BaseZ and share the hatchery's native
# load layer; StackableBaseLoadOrder.cs loads the hatchery first in it, which is
# valid only while no foundation block lies above BaseZ.
base_z=b['BlockObjectSpec']['BaseZ']
require(any(v['Stackable']!='None' for v in blocks[:base_z*W*D]),'Deck slabs below BaseZ are no longer stackable')
require(all(i//(W*D)<=base_z for i,v in enumerate(blocks) if v['MatterBelow'] in ('Ground','GroundOrStackable','Stackable')),
        'A foundation above BaseZ breaks the deck load order (StackableBaseLoadOrder)')
origin=next(n for n in model.nodes if n.name=='IndustrialGridOrigin').position
for node in (n for n in model.nodes if n.name in ('#SupportSegment','#SupportFoot')):
    require(node.position.y+origin.y<=-2 and 0<=node.position.z+origin.z<=1,'Support template is not parked inside the bank below the front row')
require(cell(1,2,1)['Occupations']=='All','Headroom can be built inside workroom')
require(cell(1,5,1)['Occupations']=='None' and cell(1,5,0)['Stackable']=='None','Nursery pen incorrectly supports paths')
require(cell(4,3,1)['Occupations']=='All' and cell(6,3,1)['Occupations']=='All','Canopy post cells lost reservation')
require(cell(2,6,0)['Occupations']=='Top, Corners' and cell(2,6,1)['Occupations']=='None','Centre dock end lost usable space above or below')
# The perimeter docks are gone: no block beyond the pens' outer edges or behind the canopy.
for x,y in ((5,4),(6,4),(5,6),(6,6)):
    require(all(cell(x,y,z)['Occupations']=='None' for z in range(3)),'Removed dock cell is registered again')
for x,y,z in layout['buildableCells']:
    require(cell(x,y,z-1)['Stackable']=='BlockObject','Clear dock lacks platform support')
require(not any(n.startswith('Studio.') for n in names),'Preview water shipped in mesh')
assembly=read('outputs/reference-studies/FishHatchery-native-assembly.json')
# Only the header tank (the reservoir stock) remains; the two bank barrels went
# with the forced decoration (2026-10-22).
require([p['name'] for p in assembly['props']]==['HatcheryHeaderTank'],'Native tank assembly changed')
for p in assembly['props']:require(not any(p['name'] in n for n in names),'Preview prop duplicated in exported mesh')
reservoir=b['WorkshopReservoirSpec']
require(reservoir['Capacity']==60 and len(reservoir['Surfaces'])==1,'Header tank capacity changed')
require(reservoir['Material']=='Materials/Goods/Water' and not reservoir['FlowNodes'] and not reservoir['WheelNodes'],'Header tank bindings changed')
tracks=[(n.name,len(a.frames)) for n in model.nodes for a in n.nodeAnimations]
require(tracks==[('#FishHatchery.NurserySign',61)],'Sign animation lost')
require({n for n in names if n.startswith('#Slot#Entrance')}=={'#Slot#Entrance0','#Slot#Entrance1'},'Worker doorway slots lost')
require(b['MechanicalNodeSpec']['PowerInput']==55 and b['MechanicalNodeSpec']['PowerOutput']==0,'Demand/output mixed')
native={'BaseWood_DarkBrown.IronTeeth','IrregularPlanks_DarkBrown.IronTeeth','RoofPlanks.IronTeeth','BaseMetal.IronTeeth','Details.IronTeeth','Plaster_White.IronTeeth','Plaster_Orange.IronTeeth','IrregularPlanks_MetalForged.IronTeeth','WindowsAtlas.IronTeeth','BaseWood_Brown.Folktails'}
uv_count=0
for node in model.nodes:
    meshes=[m for m in node.meshes if m.material in native]
    if not meshes:continue
    uv=list(struct.iter_unpack('<ff',next(p for p in node.vertexProperties if p.name=='uv0').data))
    for mesh in meshes:
        for i in set(mesh.indices):
            require(valid_native_uv(mesh.material,uv[i]),'UV outside authored/native contract')
            uv_count+=1
report={'scope':'Source/export only; native results recorded separately','modelSha256':hashlib.sha256(payload).hexdigest(),
 'nodes':len(model.nodes),'nativeUvVertices':uv_count,'suggestedPathCells':len(cells)-1,'openings':3,'baseZ':1,'size':[W,D,3],'cursorPickChecks':pick_checks,
 'nativeProps':1,'tankCapacity':60,'animationTracks':tracks}
(ROOT/'outputs/civic-integration/hatchery-static-checks.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps(report))
