"""Check industrial portal recipes against saved source surfaces read-only.

The only generated meshes are individual doors and two small placement test
boxes. No whole-building generator, saved-scene write, render or export runs.
"""
import hashlib
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from industrial_door_components import DOORS,UV_PROFILES,LEGACY_POSITIONS,recipes,recipe,legacy_door,hydro_workshop_door,kiln_return_strips
from hydro_isometric_geometry import append_powerhouse


def face_points(g,face):
    return [Vector(g.vertices[i]) for i in face]


def check_cavity_normals(g,definition,*,legacy=False,legacy_position=None):
    # A legacy insert sits at its original anchor, not the current one.
    x,y,z=legacy_position if legacy else definition['position']
    nx,ny=definition['outward']
    interior=Vector((-(x-nx*.06),-(y-ny*.06),z+.5))
    count=4 if legacy or definition['returnOwnership']=='complete' else (8 if definition['returnOwnership']=='kiln-shoulder-strips' else 0)
    assert len(g.faces)==37+count
    for face in g.faces[37:37+count]:
        points=face_points(g,face)
        center=sum(points,Vector())/len(points)
        normal=(points[1]-points[0]).cross(points[2]-points[0]).normalized()
        assert normal.dot(interior-center)>.01,'Recess return faces away from cavity: '+g.name
    expected_depth=.12 if legacy else definition['panelDepth']
    for face in g.faces[34:37]:
        for point in face_points(g,face):
            depth=-nx*(-point.x-x)-ny*(-point.y-y)
            assert abs(depth-expected_depth)<2e-6,'Door panel misses authored wall plane: '+g.name


def check_kiln_return_ownership():
    px,py,_=DOORS['CementKiln']['GroundDoor']['position']
    reveals=Geometry('Kiln existing shoulder ends plus owned reveals')
    kiln_return_strips(reveals,(px,py,0))
    # These two boxes are the exact porch shoulders (kiln porch(), relative
    # to the door anchor). No whole building is generated for this seam test.
    for x in (px-.555,px+.555):reveals.box((x,py+.05,.58),(.11,.08,1.00))
    bvh=BVHTree.FromPolygons(reveals.vertices,reveals.faces,all_triangles=False)
    for side,plane in ((1,px-.5),(-1,px+.5)):
        for yi in range(61):
            y=py+(yi+.5)*.12/61
            for zi in range(71):
                z=(zi+.5)/71
                ray=Vector((side,0,0));start=Vector((-px,-y,z))
                point,normal,_,_=bvh.ray_cast(start,ray,.6)
                assert point is not None and abs(point.x+plane)<2e-6
                assert normal.dot(ray)<-.99,'A kiln reveal is culled from its cavity'
    # The new vertical rectangles and the existing shoulder end never share
    # positive area. Boundary contact is intentional joinery.
    for face in reveals.faces[:6]:
        points=face_points(reveals,face)
        ys=[-p.y for p in points];zs=[p.z for p in points]
        overlap_y=min(max(ys),py+.09)-max(min(ys),py+.01)
        overlap_z=min(max(zs),1.0)-max(min(zs),.08)
        assert overlap_y<=2e-7 or overlap_z<=2e-7,'Duplicate shoulder-end area'


def check_hydro_placement():
    architecture=Geometry('Test retained dam')
    architecture.box((0,0,0),(1,1,1))
    retained=(list(architecture.vertices),list(architecture.faces),list(architecture.face_uvs))
    local=Geometry('Test powerhouse')
    local.box((3,3,1),(1,1,1))
    local.include_component(hydro_workshop_door())
    local.doorways.append({'name':'HydroWorkshopDoor','position':[5.5,2.0,2]})
    append_powerhouse(architecture,local,sideways=1,downstream=4)
    assert architecture.vertices[:len(retained[0])]==retained[0]
    assert architecture.faces[:len(retained[1])]==retained[1]
    assert architecture.face_uvs[:len(retained[2])]==retained[2]
    assert architecture.components==[{'name':'ReinforcedHydroTurbine.Door.HydroWorkshopDoor','faceRange':[12,49]}]
    assert architecture.doorways==[{'name':'HydroWorkshopDoor','position':[6.5,6.0,2]}]
    final=recipe('ReinforcedHydroTurbine','Door.HydroWorkshopDoor')
    for index,face in enumerate(final.faces):
        actual=face_points(architecture,architecture.faces[12+index])
        expected=face_points(final,face)
        assert all((a-b).length<2e-12 for a,b in zip(actual,expected,strict=True))
        assert architecture.materials[12+index]==final.materials[index]
        assert architecture.face_uvs[12+index]==final.face_uvs[index]


def inspect_saved(model):
    path=ROOT/f'src/DeepFrontier/Art/Source/{model}-ReferenceStudy.blend'
    before=hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    obj=bpy.data.objects[model+'.Architecture'];mesh=obj.data
    locations=json.loads(obj['df_source_locations']);provenance=mesh.attributes['df_source']
    portal_faces={p.index for p in mesh.polygons if ':building_portal' in locations[provenance.data[p.index].value]}
    records=[]
    for component,builder in recipes(model).items():
        current=builder();definition=DOORS[model][component.removeprefix('Door.')]
        check_cavity_normals(current,definition)
        g=legacy_door(model,component)
        check_cavity_normals(g,definition,legacy=True,legacy_position=LEGACY_POSITIONS[(model,component.removeprefix('Door.'))])
        # Facade ownership changes only the custom infill/returns. Native
        # jamb/lintel/recess geometry, UV corners and winding stay untouched.
        # The grid pass (2026-10-21) and the pit door fix (2026-10-22) moved
        # the anchors from LEGACY_POSITIONS: the native insert is the same
        # shape, translated exactly by that move (mesh X/Y are negated source
        # X/Y, Geometry.add).
        position=definition['position'];legacy_position=LEGACY_POSITIONS[(model,component.removeprefix('Door.'))]
        move=Vector((-(position[0]-legacy_position[0]),-(position[1]-legacy_position[1]),position[2]-legacy_position[2]))
        for index in range(34):
            assert current.materials[index]==g.materials[index]
            assert current.face_uvs[index]==g.face_uvs[index]
            moved=[p+move for p in face_points(g,g.faces[index])]
            assert len(moved)==len(current.faces[index]) and all(
                (p-q).length<2e-6 for p,q in zip(face_points(current,current.faces[index]),moved)),(model,component,index)
        # The saved scene holds each door as its own component object (the
        # one-time portal migration split them out of the architecture, and
        # full regeneration builds them that way). Its polygons must be the
        # current recipe's faces: same material, corners within 2e-6 and, on
        # all 34 native faces, the exact native UV of each corner. Models
        # built as shells (enclosed-face cull) may omit only custom,
        # non-native faces enclosed by the door's own solids.
        name=f'{model}.{component}'
        part=bpy.data.objects[name]
        assert part.get('df_component')==name and part.parent is None and tuple(part.location)==(0,0,0),name
        saved=part.data;uv_layer=saved.uv_layers['UVMap']
        recipe_faces=[(face_points(current,face),material,uv) for face,material,uv in zip(current.faces,current.materials,current.face_uvs,strict=True)]
        matched=set();native_faces=0
        for polygon in saved.polygons:
            actual=[saved.vertices[v].co for v in polygon.vertices]
            hits=[i for i,(expected,material,_) in enumerate(recipe_faces) if i not in matched and material==polygon.material_index
                  and len(expected)==len(actual) and all(min((p-q).length for q in actual)<2e-6 for p in expected)]
            assert len(hits)==1,(name,'saved face is not exactly one recipe face',polygon.index,len(hits))
            index=hits[0];matched.add(index)
            expected,_,uv=recipe_faces[index]
            if uv is not None:
                native_faces+=1
                # Match each original UV corner by its actual vertex. This
                # preserves the quarry reflection instead of assuming rotation.
                for point,expected_uv in zip(expected,uv,strict=True):
                    corners=[j for j,q in enumerate(actual) if (point-q).length<2e-6]
                    assert len(corners)==1
                    actual_uv=uv_layer.data[polygon.loop_indices[corners[0]]].uv
                    assert (actual_uv-Vector(expected_uv)).length<2e-6,'Native UV changed: '+name
        missing=[i for i in range(len(recipe_faces)) if i not in matched]
        shell=part.get('df_enclosed_culled') is not None
        assert all(recipe_faces[i][2] is None for i in missing),(name,'native door face missing',missing)
        assert len(missing)==(part['df_enclosed_culled'] if shell else 0),(name,'unaccounted missing faces',len(missing))
        assert native_faces==34,(name,native_faces)
        records.append({'component':component,'legacyFaces':len(g.faces),'currentFaces':len(current.faces),'savedFaces':len(saved.polygons),
                        'enclosedFacesCulled':len(missing),'nativeUvFaces':native_faces,
                        'anchorMoveFromLegacy':[round(v,6) for v in move],'facade':definition['facade'],
                        'panelDepth':definition['panelDepth'],'returnOwnership':definition['returnOwnership']})
    # No building_portal face may remain in the architecture: every portal is
    # an owned component.
    assert not portal_faces,('Unowned portal faces remain in the architecture',model,len(portal_faces))
    assert hashlib.sha256(path.read_bytes()).hexdigest()==before,'Source changed during read-only test'
    return {'model':model,'sourceSha256':before,'sourceUnchanged':True,'uvProfile':UV_PROFILES[model],'components':records}


check_hydro_placement()
check_kiln_return_ownership()
rows=[inspect_saved(model) for model in DOORS]
report={'scope':'Individual door recipes and read-only saved scene equivalence; no whole-building generator, source save, render or export.',
        'hydroComponentPlacementAndRetainedGeometry':'passed',
        'kilnShoulderRevealCoverageSamples':2*61*71,'kilnReturnCoverageAndNoDuplicateEndFaces':'passed','models':rows}
out=ROOT/'outputs/component-inventory/industrial-door-recipe-check.json'
out.parent.mkdir(parents=True,exist_ok=True)
out.write_text(json.dumps(report,indent=2)+'\n')
print('PASS industrial door recipes:',len(rows),'scenes,',sum(len(row['components']) for row in rows),
      'components; exact native UVs, reflected quarry placement and inward returns verified')
