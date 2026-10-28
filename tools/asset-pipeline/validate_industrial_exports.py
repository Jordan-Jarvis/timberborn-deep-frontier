"""Validate exported mesh bindings and authored native graph contracts."""
import collections,json,sys,zlib,struct
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from native_uv_contract import valid_native_uv
report=[]
for ident,frames in [('StoneCrusher',61),('CementKiln',241),('SandstoneQuarry',481),('LimestoneQuarry',481),('ConcreteMixer',121)]:
    folder=ROOT/'src/DeepFrontier/Data/Buildings/Metal'/ident
    bp=json.loads((folder/(ident+'.IronTeeth.blueprint.json')).read_text())
    model=model_pb2.Model();model.ParseFromString(zlib.decompress((folder/(ident+'.IronTeeth.Model.timbermesh')).read_bytes()))
    names=collections.Counter(n.name for n in model.nodes)
    materials={mesh.material for node in model.nodes for mesh in node.meshes}
    assert {'BaseWood_DarkBrown.IronTeeth','IrregularPlanks_DarkBrown.IronTeeth','RoofPlanks.IronTeeth'}<=materials,(ident,materials)
    assert not {'DFIndustrial00','DFIndustrial01','DFIndustrial03'}&materials,(ident,'Custom wood or roof still exported')
    native_uv_vertices=0
    for node in model.nodes:
        native_meshes=[m for m in node.meshes if m.material in {'BaseWood_DarkBrown.IronTeeth','IrregularPlanks_DarkBrown.IronTeeth','RoofPlanks.IronTeeth'}]
        if not native_meshes:continue
        uv=next(p for p in node.vertexProperties if p.name=='uv0')
        coords=list(struct.iter_unpack('<ff',uv.data))
        for mesh in native_meshes:
            for index in set(mesh.indices):
                assert valid_native_uv(mesh.material,coords[index]),(ident,node.name,mesh.material,index,coords[index],'Outside authored/native UV contract')
                native_uv_vertices+=1
    # These machines have no walkable decks, balconies or rails (2026-10-21):
    # no walkway spec, building navigation edges or rail nodes may remain. A
    # navmesh spec may only switch on native floors over platformable roofs
    # (roof_deck_content.mjs: GenerateFloorsOnStackable, no edges).
    nav=bp.get('BlockObjectNavMeshSettingsSpec')
    assert 'BuildingWalkwaySpec' not in bp and (nav is None or not (nav['EdgeGroups'] or nav['UnblockedCoordinates'] or nav['BlockedEdges'])),(ident,'Walkway data remains')
    assert not any('Rail' in n and ('.Post' in n or '.Panel' in n or '.CellPart' in n) for n in names),(ident,'Rail nodes remain')
    assert not any(n.startswith('WalkwayJoin.') for n in names),(ident,'Walkway joins remain')
    tracks=[a for n in model.nodes for a in n.nodeAnimations]
    assert tracks and all(len(a.frames)==frames for a in tracks),(ident,[(a.name,len(a.frames)) for a in tracks])
    for slot in bp['TransformSlotInitializerSpec']['Slots']:
        assert any(n.startswith('#Slot#'+slot['SlotKeyword']) for n in names),(ident,slot)
    if ident.endswith('Quarry'):
        foundations=[b for b in bp['BlockObjectSpec']['Blocks'] if b['Occupations']=='Top']
        assert len(foundations)==25
    report.append(dict(building=ident,nodes=len(model.nodes),animationTracks=len(tracks),frames=frames,walkways='none',nativeUvVerticesChecked=native_uv_vertices))
out=ROOT/'outputs/industrial-integration/static-checks.json'
out.write_text(json.dumps({'scope':'Exported assets and authored graph; runtime tests required','buildings':report},indent=2)+'\n')
print(json.dumps(report))
