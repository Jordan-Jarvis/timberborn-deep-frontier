"""Check explicit Mixer/Hydro/Quarry casing joints without rebuilding scenes."""
import json
import sys
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from industrial_door_components import DOORS,LEGACY_POSITIONS,recipe,legacy_door,hydro_workshop_door
from hydro_isometric_geometry import append_powerhouse
from frontier_architecture import Geometry,WOOD


def check_mount(model,ident,wall,old_anchor):
    definition=DOORS[model][ident]
    g=recipe(model,'Door.'+ident)
    old=legacy_door(model,'Door.'+ident)
    nx,ny=definition['outward']
    axis=0 if nx else 1
    wall_key='wallPlaneX' if nx else 'wallPlaneY'
    outward=Vector((-nx,-ny,0))
    anchor=Vector((-definition['position'][0],-definition['position'][1],definition['position'][2]))
    assert LEGACY_POSITIONS[(model,ident)]==old_anchor
    expected_faces=39 if definition['returnOwnership']=='quarry-outer-bay' else 37
    assert len(g.faces)==expected_faces and len(old.faces)==41
    assert definition['panelDepth']==.04 and abs(definition[wall_key]-wall)<1e-12
    assert abs(definition['position'][axis]+.04-wall)<1e-12
    assert g.face_uvs[:34]==old.face_uvs[:34]
    assert g.materials[:34]==old.materials[:34]
    delta=Vector((old_anchor[0]-definition['position'][0],old_anchor[1]-definition['position'][1],0))
    for face,legacy in zip(g.faces[:34],old.faces[:34],strict=True):
        assert len(face)==len(legacy)
        for i,j in zip(face,legacy,strict=True):
            assert (Vector(g.vertices[i])-Vector(old.vertices[j])-delta).length<2e-6
    for face in g.faces[34:37]:
        assert all(abs(-g.vertices[i][axis]-wall)<2e-6 for i in face)

    tree=BVHTree.FromPolygons(g.vertices,g.faces,all_triangles=False)
    visible={}
    depth_bounds={}
    for part,start,end in (('jamb',0,16),('lintel',16,32)):
        depths=[-(Vector(g.vertices[i])-anchor).dot(outward) for face in g.faces[start:end] for i in face]
        assert min(depths)<.04<max(depths),'Casing must cross its actual wall plane'
        depth_bounds[part]=[min(depths),max(depths)]
        samples=0
        for face in g.faces[start:end]:
            p=[Vector(g.vertices[i]) for i in face]
            center=sum(p,Vector())/len(p)
            normal=(p[1]-p[0]).cross(p[2]-p[0]).normalized()
            if normal.dot(outward)<=.4 or -(center-anchor).dot(outward)>=.04-1e-5:continue
            hit,_,index,_=tree.ray_cast(center+outward*.5,-outward,.51)
            assert hit is not None and g.materials[index]==WOOD,'Infill hides native casing'
            samples+=1
        assert samples>0,'No outward native trim surface verified: '+part
        visible[part]=samples
    # Sample the outer casing projection, excluding the dark rectangular
    # opening. Centroids alone miss the long tapered native timber faces.
    tangent=Vector((ny,-nx,0))
    outer_samples=outer_visible=0
    for xi in range(121):
        x=-.372452736+(xi+.5)*.744905472/121
        for zi in range(121):
            z=(zi+.5)*.733830702/121
            if abs(x)<.301463544 and z<.683321666:continue
            start=anchor+tangent*x+Vector((0,0,z))+outward*.5
            hit,_,index,_=tree.ray_cast(start,-outward,.85)
            outer_samples+=1
            outer_visible+=hit is not None and g.materials[index]==WOOD
    assert outer_visible>0,'Opaque wall completely conceals outer native casing'
    return {'model':model,'component':'Door.'+ident,'currentAnchor':definition['position'],
            'legacyAnchor':old_anchor,wall_key:wall,'panelDepth':.04,
            'nativeFacesPreserved':34,'visibleNativeTrimSamples':visible,'nativeDepthBounds':depth_bounds,
            'outerTrimProjectionSamples':outer_samples,'outerTrimWoodVisible':outer_visible}


def check_powerhouse_mount():
    local=hydro_workshop_door()
    local.doorways.append({'name':'HydroWorkshopDoor','position':[5.5,2.0,2]})
    placed=Geometry('Placement check')
    append_powerhouse(placed,local,sideways=1,downstream=4)
    final=recipe('ReinforcedHydroTurbine','Door.HydroWorkshopDoor')
    assert placed.vertices==final.vertices and placed.faces==final.faces
    assert placed.face_uvs==final.face_uvs
    assert placed.doorways==[{'name':'HydroWorkshopDoor','position':[6.5,6.0,2]}]


def main():
    rows=[check_mount('ConcreteMixer','MixerOperatorDoor',.16,(1.65,.50,0)),
          check_mount('ReinforcedHydroTurbine','HydroWorkshopDoor',6.04,(6.35,6.24,2)),
          check_mount('MineralQuarry','GroundDoor',1.18,(1.37,1.35,0))]
    check_powerhouse_mount()
    report={'scope':'Only individual portal recipes; no source-scene generation/save/export/render.',
            'hydroSourceLocalPlacementAndIdlePoint':'passed','doors':rows}
    output=ROOT/'outputs/component-inventory/industrial-door-mounting.json'
    output.write_text(json.dumps(report,indent=2)+'\n')
    print('PASS explicit industrial casing mounts: native shape/UVs, facade plane, visible trim and original migration anchors')


if __name__=='__main__':main()
