"""Check actual Timbermesh doorway coverage with native one-sided face winding.

Run in Blender for mathutils BVH. Reads the payload; never modifies geometry.
Door faces are tested independently, then their actual wall joints are tested
as an assembly. Their source/export transform chains are translation-only.

Merged exports (static_mesh_merge.py joins the architecture, doors and other
static parts into StaticMerged plus one StaticMerged.<glass material> node):
pass --game-blend, the <Model>-Game.blend the exporter saved just before that
join. Each door object's evaluated triangles there (world space, the grid-origin
parent applied) are located among the exported merged triangles by exact vertex
positions (2e-5); every one must be found, and the isolated-door probes run on
those exported triangles. The joint probes run on all merged static nodes,
which contain the architecture the door meets.
"""
import argparse
import hashlib
import json
import struct
import sys
import zlib
from pathlib import Path
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2
from building_components import DOOR_LAYOUTS,FACADES,CULLING_CONTEXTS,exported_doors

parser=argparse.ArgumentParser()
parser.add_argument('--building',required=True,choices=DOOR_LAYOUTS)
parser.add_argument('--model',type=Path,required=True)
parser.add_argument('--report',type=Path,required=True)
parser.add_argument('--game-blend',type=Path,help='required when the doors were joined into StaticMerged nodes')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
DOORS=exported_doors(args.building)
payload=args.model.read_bytes()
model=model_pb2.Model()
model.ParseFromString(zlib.decompress(payload))
def read_node(name):
    nodes=[n for n in model.nodes if n.name==name]
    if len(nodes)!=1:raise ValueError('Expected one mesh node: '+name)
    assembly=nodes[0];node=assembly;offset=Vector((0,0,0))
    while True:
        if (node.rotation.x,node.rotation.y,node.rotation.z,node.rotation.w)!=(0,0,0,1):
            raise ValueError('Door component contract requires identity rotation')
        if (node.scale.x,node.scale.y,node.scale.z)!=(1,1,1):
            raise ValueError('Door component contract requires unit scale')
        offset+=Vector((node.position.x,node.position.y,node.position.z))
        if node.parent==-1:break
        node=model.nodes[node.parent]
    position=next(p for p in assembly.vertexProperties if p.name=='position')
    # Invert the official exporter basis to restore Blender winding.
    vertices=[Vector((-x-offset.x,-z-offset.z,y+offset.y))
              for x,y,z in struct.iter_unpack('<fff',position.data)]
    faces=[]
    for mesh in assembly.meshes:
        if len(mesh.indices)%3:raise ValueError('Non-triangular exported mesh')
        # Official node_builder.__update_node_vertices reverses every source
        # triangle for Unity. Undo that reversal alongside the basis change
        # when reconstructing a Blender BVH (not a runtime mesh mutation).
        faces.extend(tuple(reversed(mesh.indices[i:i+3])) for i in range(0,len(mesh.indices),3))
    return vertices,faces


def merge_tree(names):
    points=[];polygons=[]
    for name in names:
        vertices,faces=read_node(name);offset=len(points)
        points.extend(vertices);polygons.extend(tuple(offset+i for i in face) for face in faces)
    return BVHTree.FromPolygons(points,polygons,all_triangles=True)


node_names={n.name for n in model.nodes}
merged_names=sorted(n for n in node_names if n=='StaticMerged' or n.startswith('StaticMerged.'))
door_names=[args.building+'.Door.'+key for key in DOORS]
merged=not set(door_names)<=node_names
door_triangles={}
if merged:
    if set(door_names)&node_names:raise ValueError('Some doors are separate nodes and some are not')
    if not merged_names:raise ValueError('Doors are neither separate nodes nor in StaticMerged nodes')
    if args.game_blend is None or not args.game_blend.is_absolute():
        raise ValueError('Doors were joined by static_mesh_merge.py: pass the absolute --game-blend saved before the join')
    import bpy
    bpy.ops.wm.open_mainfile(filepath=str(args.game_blend))
    exported=[]
    for name in merged_names:
        vertices,faces=read_node(name)
        exported.extend(tuple(vertices[i] for i in face) for face in faces)
    from mathutils.kdtree import KDTree
    centroids=KDTree(len(exported))
    for i,triangle in enumerate(exported):centroids.insert(sum(triangle,Vector())/3,i)
    centroids.balance()
    for name in door_names:
        # The evaluated mesh (modifiers applied) is what the exporter wrote.
        obj=bpy.data.objects[name];evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh=evaluated.to_mesh();mesh.calc_loop_triangles()
        found=[]
        for tri in mesh.loop_triangles:
            corners=[obj.matrix_world@mesh.vertices[v].co for v in tri.vertices]
            hits=[exported[i] for _,i,_ in centroids.find_range(sum(corners,Vector())/3,5e-5)
                  if all(min((p-q).length for q in exported[i])<2e-5 for p in corners)]
            if not hits:raise ValueError(f'{name}: source triangle {tri.index} missing from the merged export')
            found.append(hits[0])
        evaluated.to_mesh_clear()
        door_triangles[name]=found


def door_tree(name):
    if not merged:return merge_tree([name])
    points=[p for triangle in door_triangles[name] for p in triangle]
    return BVHTree.FromPolygons(points,[(3*i,3*i+1,3*i+2) for i in range(len(door_triangles[name]))],all_triangles=True)


def front_hit(tree,start,end):
    ray=(end-start).normalized();remaining=(end-start).length;cursor=start
    for _ in range(16):
        hit,normal,index,distance=tree.ray_cast(cursor,ray,remaining)
        if hit is None:return False
        if normal.dot(ray)<-1e-6:return True
        step=distance+.00001;cursor+=ray*step;remaining-=step
        if remaining<=0:return False
    raise ValueError('Unexpected layered doorway geometry')


assembled=merge_tree(merged_names if merged else [*CULLING_CONTEXTS[args.building],*door_names])
failures=[];counts={'isolatedDoor':0,'wallSeam':0}
for ident,door in DOORS.items():
    tree=door_tree(args.building+'.Door.'+ident)
    if 'seamCorners' in door:
        if set(door['seamCorners'])!=set(door['seamCornerAcross']):
            raise ValueError('Every authored doorway corner needs an explicit interior ray endpoint')
        if not set(door['seamCorners'])<=set(('left','right')):
            raise ValueError('Unknown authored doorway corner')
    x,y,z=door['position'];nx,ny=door['outward'];tx,ty=-ny,nx
    def point(a,d,h):return Vector((-(x+a*tx-d*nx),-(y+a*ty-d*ny),z+h))
    for i in range(60):
        for j in range(60):
            a=-.5+(i+.5)/60;h=(j+.5)/60
            counts['isolatedDoor']+=1
            if not front_hit(tree,point(a,-.25,h),point(a,.15,h)):
                failures.append({'door':ident,'part':'isolatedDoor','across':a,'height':h})
    # Probe both sides of each vertical joint, including the exact boundary,
    # from both oblique camera directions. Rays stop at the local wall; the
    # far side of the building cannot cover a missing near surface.
    for edge in (-.5,.5):
        for offset in (-.006,0,.006):
            for j in range(60):
                h=(j+.5)/60;a=edge+offset
                for slope in (-.20,.20):
                    counts['wallSeam']+=1
                    # RoofStairhead is only one cell wide: these joints are
                    # room corners, not a longer coplanar wall. Finish inside
                    # its side wall rather than firing wholly outside it.
                    grid=FACADES[args.building]=='grid'
                    end_a=a-(.06 if edge>0 else -.06) if grid and ident=='RoofTerraceDoor' else a
                    corner='right' if edge>0 else 'left'
                    if 'seamCorners' in door and corner in door['seamCorners']:
                        end_a=door['seamCornerAcross'][corner]
                    depth=.06 if grid else .18
                    if not front_hit(assembled,point(a+slope,-.25,h),point(end_a,depth,h)):
                        failures.append({'door':ident,'part':'wallSeam','across':a,'height':h,'slope':slope})
report={'building':args.building,'model':str(args.model),'sha256':hashlib.sha256(payload).hexdigest(),
        'mergedExport':merged,'doorTrianglesFound':{k:len(v) for k,v in door_triangles.items()},
        'scope':'Actual exported isolated door faces and oblique near-wall joints with back-face culling',
        'probes':counts,'failureCount':len(failures),'failures':failures}
args.report.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'probes':counts,'failures':len(failures),'sha256':report['sha256']}),flush=True)
if failures:raise RuntimeError('Export contains missing or back-facing doorway surfaces')
