"""Inspect candidate Timbermesh bytes, blueprint bindings and retaining rules."""
import json
import math
from pathlib import Path
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv
catalog=json.loads((ROOT/'tools/structural_content.json').read_text())
data=ROOT/'outputs/structural-integration/Data'
reports=[]
pick_checks=0
for building in catalog['buildings']:
    ident=building['id']
    folder=data/'Buildings/Platforms'/ident
    bp=json.loads((folder/(ident+'.IronTeeth.blueprint.json')).read_text())
    payload=(folder/(ident+'.IronTeeth.Model.timbermesh')).read_bytes()
    model=model_pb2.Model()
    model.ParseFromString(zlib.decompress(payload))
    assert payload==(folder/(ident+'.IronTeeth.ConstructionStage0.Model.timbermesh')).read_bytes()
    assert len(set(n.name for n in model.nodes))==len(model.nodes), ident
    assert not any(n.nodeAnimations for n in model.nodes), ident
    assert not any(k in bp for k in ('MechanicalNodeSpec','WorkplaceSpec','ManufactorySpec')), ident
    assert bp['BuildingSpec']['ScienceCost']==building['science'], ident
    assert bp['BuildingSpec']['BuildingCost']==[dict(Id=g,Amount=a) for g,a in building['cost']], ident
    assert bp['BlockObjectSpec']['Size']==dict(zip(('X','Y','Z'),building['size'])), ident
    assert (folder/'Icon.png').stat().st_size>100, ident
    uv_count=0
    for node in model.nodes:
        if not node.meshes:
            continue
        uv=list(struct.iter_unpack('<ff',next(p.data for p in node.vertexProperties if p.name=='uv0')))
        for mesh in node.meshes:
            if mesh.material.endswith('.IronTeeth'):
                for index in set(mesh.indices):
                    assert valid_native_uv(mesh.material,uv[index]), (ident,node.name,mesh.material)
                    uv_count+=1
    blocks=bp['BlockObjectSpec']['Blocks']
    support=sum(b['Stackable']=='BlockObject' for b in blocks)
    if building['kind']=='sidedeck':
        # n x n legless deck beside a one-cell anchor row, plus the cleat layer
        # above it. The cleat on the anchor's top is the only foundation block.
        width,depth,layers=building['size']
        n=depth-1
        assert width==(n if n%2 else n+1) and layers==2 and bp['BlockObjectSpec']['BaseZ']==1,ident
        assert bp['BlockObjectSpec']['Flippable'] is True,ident
        assert support==n*n,ident
        anchor=bp['AnchoredDeckSpec']['Anchor']
        assert anchor==dict(X=n//2,Y=n,Z=0) and 2*anchor['X']==width-1,ident
        foundation=[(i,b) for i,b in enumerate(blocks) if b['MatterBelow']!='Any']
        cleat=anchor['X']+(depth+anchor['Y'])*width
        assert [(i,b['MatterBelow'],b['Occupations'],b['Stackable']) for i,b in foundation]==[(cleat,'Stackable','Floor','None')],ident
        pivot=bp['PlaceableBlockObjectSpec']['CustomPivot']
        assert pivot==dict(HasCustomPivot=True,Coordinates=dict(X=anchor['X']+.5,Y=n+.5,Z=0)),ident
        # Replay native picking for a cursor on the anchor's top face at grid
        # cell (0,0): BlockObjectPreviewPicker.ComposeCoordinates rotates the
        # CustomPivot but never flips it; Blocks.Transform flips (W-1-x), then
        # rotates (OrientationExtensions.Transform). Every rotation and both
        # flip states must put the anchor (and the cleat above it) on the
        # hovered block, for intersections anywhere in the hovered cell.
        def rotate(o,x,y):return {0:(x,y),90:(y,-x),180:(-x,-y),270:(-y,x)}[o]
        sign=lambda v:1 if v>=0 else -1          # Mathf.Sign(0) == 1
        for o in (0,90,180,270):
            for flipped in (False,True):
                cx,cy=rotate(o,pivot['Coordinates']['X'],pivot['Coordinates']['Y'])
                for fx in (.02,.5,.98):
                    for fy in (.02,.5,.98):
                        origin=(math.floor(fx-cx+.5*sign(cx)),math.floor(fy-cy+.5*sign(cy)))
                        lx=width-anchor['X']-1 if flipped else anchor['X']
                        wx,wy=rotate(o,lx,anchor['Y'])
                        assert (origin[0]+wx,origin[1]+wy)==(0,0),(ident,'Cleat misses the hovered anchor',o,flipped,fx,fy)
                        pick_checks+=1
    else:
        assert support==building['size'][0]*building['size'][1],ident
    assert ('AnchoredDeckAnchorSpec' in bp)==bool(building.get('deckAnchor')),ident
    if building['kind'] in ('block','dam'):
        expected=1 if building['kind']=='block' else .65
        assert bp['FinishableWaterObstacleSpec']['Height']==expected,ident
    else:
        assert 'WaterObstacleSpec' not in bp and 'FinishableWaterObstacleSpec' not in bp,ident
    reports.append(dict(building=ident,nodes=len(model.nodes),nativeUvVertices=uv_count,supportCells=support))
report=dict(scope='Candidate source/export checks, not native runtime acceptance',buildings=reports,
            sidePlatformPickReplays=pick_checks)
(ROOT/'outputs/structural-integration/export-checks.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
