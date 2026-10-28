"""Hospital source-only shell and complete player-deck geometry coverage."""
import hashlib,json,math,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from frontier_architecture import Geometry
from hospital_geometry import hospital_room,hospital
from hospital_structure import ROOMS,EXTERIOR_WALLS
from hospital_layout import HOSPITAL

entrances={'CentralLower':'GroundDoor','WestWardUpper':'WestWardDoor','CentralUpper':'RearWardDoor','RoofStairhead':'RoofTerraceDoor'}
checks=0;failures=[]
for name,b in ROOMS.items():
    g=Geometry('Shell probe '+name);hospital_room(g,name,entrances.get(name))
    tree=BVHTree.FromPolygons([Vector(v) for v in g.vertices],g.faces)
    for side,spans in EXTERIOR_WALLS[name].items():
        plane={'front':b[1],'back':b[4],'left':b[0],'right':b[3]}[side]
        normal=Vector({'front':(0,1,0),'back':(0,-1,0),'left':(1,0,0),'right':(-1,0,0)}[side])
        for a,c in spans:
            for i in range(math.ceil((c-a)*40)):
                along=a+.005+(i+.5)/math.ceil((c-a)*40)*(c-a-.01)
                for j in range(80):
                    z=b[2]+(j+.5)/80*(b[5]-b[2])
                    target=Vector((-along,-plane,z) if side in ('front','back') else (-plane,-along,z))
                    hit=tree.ray_cast(target+normal, -normal,1.30)
                    checks+=1
                    if hit[0] is None:failures.append([name,side,along,z])
if failures:
    (ROOT/'outputs/reference-studies/Hospital-shell-failures.json').write_text(json.dumps(failures,indent=2)+'\n')
    raise ValueError('Hospital open shell samples: '+str(len(failures))+' '+str(failures[:15]))

# Every actual mounting perimeter reaches opaque authored building geometry.
# Remove ALL window faces from this tree so the window's own reveal can never
# accidentally serve as evidence that its back touches the wall.
facade=Geometry('Hospital mounting audit');hospital(facade,[])
window_faces={i for mount in facade.window_mounts for i in range(*mount['faceRange'])}
mount_tree=BVHTree.FromPolygons([Vector(v) for v in facade.vertices],
                              [f for i,f in enumerate(facade.faces) if i not in window_faces])
mount_probes=0
for index,mount in enumerate(facade.window_mounts):
    outward=Vector((-mount['outward'][0],-mount['outward'][1],mount['outward'][2]))
    for edge in mount['rearEdges']:
        a,b=[Vector((-p[0],-p[1],p[2])) for p in edge]
        for t in (.1,.3,.5,.7,.9):
            p=a.lerp(b,t)
            hit=mount_tree.ray_cast(p+outward*.002,-outward,.006)
            if hit[0] is None:raise ValueError('Hospital detached window reveal '+str((index,mount['style'],mount['face'],mount['anchor'],list(p))))
            mount_probes+=1

objects=bpy.data.collections['Hospital.ReferenceStudy'].objects
vertices=[];faces=[]
depsgraph=bpy.context.evaluated_depsgraph_get()
for obj in objects:
    if obj.type!='MESH':continue
    evaluated=obj.evaluated_get(depsgraph);mesh=evaluated.to_mesh()
    offset=len(vertices)
    vertices.extend(evaluated.matrix_world@v.co for v in mesh.vertices)
    faces.extend(tuple(offset+i for i in p.vertices) for p in mesh.polygons)
    evaluated.to_mesh_clear()
tree=BVHTree.FromPolygons(vertices,faces)
evaluated_wall_probes=0
for name,b in ROOMS.items():
    for side,spans in EXTERIOR_WALLS[name].items():
        plane={'front':b[1],'back':b[4],'left':b[0],'right':b[3]}[side]
        normal=Vector({'front':(0,1,0),'back':(0,-1,0),'left':(1,0,0),'right':(-1,0,0)}[side])
        for a,c in spans:
            stations=[a+.005,c-.005]+[a+(i+.5)/40 for i in range(math.ceil((c-a)*40))]
            for along in stations:
                for j in range(80):
                    z=b[2]+(j+.5)/80*(b[5]-b[2])
                    # Below the full-span fascia the timber frame has an
                    # authored14mm perimeter inset and12mm bevel. Probe its
                    # physical silhouette, not space outside that silhouette.
                    if z<b[5]-.28 and (along<a+.03 or along>c-.03):continue
                    target=Vector((-along,-plane,z) if side in ('front','back') else (-plane,-along,z))
                    hit=tree.ray_cast(target+normal,-normal,1.30)
                    if hit[0] is None:raise ValueError('Evaluated Hospital wall opening '+str((name,side,along,z)))
                    evaluated_wall_probes+=1
deck_probes=0
for x,y,z in HOSPITAL['suggestedPathCells']:
    if z==0:continue
    for dx,dy in ((0,0),(.2,0),(-.2,0),(0,.2),(0,-.2)):
        p=Vector((-x-.5-dx,-y-.5-dy,z+.03))
        floor=tree.ray_cast(p,Vector((0,0,-1)),.07)
        if floor[0] is None or abs(floor[0].z-z)>.005:raise ValueError('Hospital road lacks physical floor '+str((x,y,z,dx,dy)))
        ceiling=tree.ray_cast(p,Vector((0,0,1)),1.07)
        if ceiling[0] is not None:raise ValueError('Hospital road obstructed '+str((x,y,z,dx,dy,ceiling[0])))
        deck_probes+=1
roof_probes=0
for name,b in ROOMS.items():
    if b[2]!=0:continue
    for i in range((b[3]-b[0])*40):
        for j in range((b[4]-b[1])*40):
            x=b[0]+(i+.5)/40;y=b[1]+(j+.5)/40
            hit=tree.ray_cast(Vector((-x,-y,10)),Vector((0,0,-1)),10)
            if hit[0] is None:raise ValueError('Hospital roof has an open vertical ray '+str((name,x,y)))
            roof_probes+=1
result={'status':'Source shell and suggested-road geometry checks passed; native gameplay is separate',
        'sourceSha256':hashlib.sha256(Path(bpy.data.filepath).read_bytes()).hexdigest(),
        'mountedWindows':len(facade.window_mounts),'windowContactProbes':mount_probes,
        'evaluatedWallProbes':evaluated_wall_probes,'rooms':len(ROOMS),'roofShellProbes':roof_probes,'opaqueWallSamples':checks,'bodyClearanceProbes':deck_probes,
        'doors':len(entrances),'roofClearCells':len(HOSPITAL['buildableCells'])}
(ROOT/'outputs/reference-studies/Hospital-shell-check.json').write_text(json.dumps(result,indent=2)+'\n')
(ROOT/'outputs/reference-studies/Hospital-window-mounts.json').write_text(json.dumps({
    'sourceSha256':result['sourceSha256'],'scope':'Authored native window reveals contact opaque non-window geometry',
    'probes':mount_probes,'mounts':facade.window_mounts},indent=2)+'\n')
print(result)
