"""Read actual Timbermesh output and its pit blueprint bindings."""
import collections
import json
from pathlib import Path
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv

# Registered sizes (tools/pit-layouts.json, written by pit_layouts.py).
LAYOUTS=json.loads((ROOT/'tools/pit-layouts.json').read_text())
reports=[]
for ident in ('SandstonePit','LimestonePit'):
    folder=ROOT/'src/DeepFrontier/Data/Buildings/Metal'/ident
    blueprint=json.loads((folder/(ident+'.IronTeeth.blueprint.json')).read_text())
    payload=(folder/(ident+'.IronTeeth.Model.timbermesh')).read_bytes()
    model=model_pb2.Model();model.ParseFromString(zlib.decompress(payload))
    names=collections.Counter(n.name for n in model.nodes)
    assert all(n==1 for n in names.values()),ident
    assert names['#Slot#Entrance0']==1,ident
    assert not any(n.startswith('NativeBarrel') for n in names), 'Native barrel must stay an external reference'
    materials={mesh.material for node in model.nodes for mesh in node.meshes}
    native={'BaseWood_DarkBrown.IronTeeth','IrregularPlanks_DarkBrown.IronTeeth',
            'RoofPlanks.IronTeeth','BaseMetal.IronTeeth'}
    assert native<=materials,ident
    count=0
    for node in model.nodes:
        meshes=[m for m in node.meshes if m.material in native]
        if not meshes:continue
        uv=list(struct.iter_unpack('<ff',next(p.data for p in node.vertexProperties if p.name=='uv0')))
        for mesh in meshes:
            for index in set(mesh.indices):
                assert valid_native_uv(mesh.material,uv[index]),(ident,node.name)
                count+=1
    tracks=[(n.name,a) for n in model.nodes for a in n.nodeAnimations]
    assert {name for name,_ in tracks}=={'#Pit.Winch','#Pit.HoistedBasket','#Pit.HoistCable'},ident
    assert len(tracks)==3 and all(len(a.frames)==121 for _,a in tracks),ident
    assert payload==(folder/(ident+'.IronTeeth.ConstructionStage0.Model.timbermesh')).read_bytes()
    # 2026-10-22: footprints end at the walls. The sandstone pit keeps its
    # front row (hoist and sorting grate) with the native path cell (1,0,0)
    # in front of its set-back door; the limestone pit's door is on the
    # footprint edge (doorstep (1,0,0) occupied, entrance outside).
    size=blueprint['BlockObjectSpec']['Size']
    assert size==dict(zip(('X','Y','Z'),LAYOUTS[ident]['size'])),(ident,size)
    blocks=blueprint['BlockObjectSpec']['Blocks']
    assert len(blocks)==size['X']*size['Y']*size['Z']
    assert blueprint['BlockObjectSpec']['Entrance']['Coordinates']=={'X':1,'Y':-1,'Z':0}
    if ident=='SandstonePit':
        assert blocks[1]['Occupations']=='Floor','Doorway floor must leave native player paths available'
        assert blueprint['BuildingAccessibleSpec']['LocalAccess']=={'X':1.5,'Y':0,'Z':.98}
    else:
        assert blocks[1]['Occupations']=='All','Doorstep must be occupied'
        access=blueprint['BuildingAccessibleSpec']['LocalAccess']
        assert access['X']==1.5 and access['Y']==0 and abs(access['Z']+.02)<1e-9,access
        # The free front-right cell: no occupation or matter rule at any layer.
        free=[blocks[(z*size['Y']+0)*size['X']+4] for z in range(size['Z'])]
        assert all(b['Occupations']=='None' and b['MatterBelow']=='Any' for b in free),'Free cell (4,0) is blocked'
    assert blueprint['PathModelTypeEnforcerSpec']=={'PathModelType':'Roof'},'Raised apron would hide a native DirtPath'
    assert blocks[1+size['X']*size['Y']]['Occupations']=='All','Door canopy must be occupied'
    # The one-storey flat roof (2026-10-30) is a platformable roof deck: its
    # stackable blocks are exactly the cells tools/roof_decks.json lists.
    decks=json.loads((ROOT/'tools/roof_decks.json').read_text())['buildings'].get(ident,{}).get('platformable',[])
    stackable={(i%size['X'],(i//size['X'])%size['Y'],i//(size['X']*size['Y'])) for i,b in enumerate(blocks) if b['Stackable']!='None'}
    assert stackable=={tuple(c) for c in decks},(ident,'Stackable roof cells differ from the roof deck plan')
    assert 'MechanicalNodeSpec' not in blueprint,'Hand-operated pit should consume no hp'
    # No loose props: the pits' barrels were removed (2026-10-22).
    assert not blueprint.get('NativeBuildingPropsSpec',{}).get('Props'),'Pits carry no native props'
    assert not any('Barrel' in k for k in blueprint['Children']['#Finished'].get('Children',{})),'Pits carry no native barrel'
    assert 'WorkshopReservoirSpec' not in blueprint,'Pits show no reservoir'
    assert 'MineralPitAnimationSpec' in blueprint
    good=blueprint['MineralPitSpec']['GoodId']
    source=json.loads((ROOT/f'src/DeepFrontier/Data/MapEditor/Objects/{good}Outcrop/{good}Outcrop.blueprint.json').read_text())
    assert source['MineralDepositSpec']['Yielder']['Yield']=={'Id':good,'Amount':600}
    reports.append({'building':ident,'size':size,'nodes':len(model.nodes),
        'animationTracks':len(tracks),'frames':121,'nativeUvVerticesChecked':count,
        'emptyCells':sum(b['Occupations']=='None' for b in blocks)})

report={'scope':'Export/data validation; native gathering, appearance and reload remain to test',
        'buildings':reports}
(ROOT/'outputs/industrial-integration/pit-static-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
