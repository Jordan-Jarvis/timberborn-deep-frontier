"""Read-only scene checks for the selective Hatchery platform migration."""
import argparse,hashlib,json,sys
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(Path(__file__).parent))
from hatchery_structure import deck_cells,source,ROOMS,PENS
from zfight_audit import audit,write_findings
from native_uv_contract import valid_native_uv

def main():
    p=argparse.ArgumentParser();p.add_argument('--directory',required=True)
    args=p.parse_args(sys.argv[sys.argv.index('--')+1:]);folder=Path(args.directory)
    scene=folder/'FishHatchery-ReferenceStudy.blend';digest=hashlib.sha256(scene.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(scene));bpy.context.scene.frame_set(1)
    collection=bpy.data.collections['FishHatchery.ReferenceStudy'];objects=list(collection.all_objects)
    from blender_components import object_digest,surface_digest
    migration=json.loads((folder/'migration-report.json').read_text())
    retained=surface_digest(collection.objects['FishHatchery.Architecture'])
    if retained!=migration['retainedArchitectureSurfaceSha256']:raise ValueError('Retained pen/machine architecture changed')
    untouched=0
    for name,expected in migration['unchangedObjectDigests'].items():
        if name=='NativeBarrel1':continue # The declared barrel root move is validated against the runtime assembly.
        if object_digest(bpy.data.objects[name])!=expected:raise ValueError('Unselected original object changed: '+name)
        untouched+=1
    report=audit(objects,.0005,.0005)
    report.update(model='FishHatchery',frame=1,sourceScene=str(scene),sourceSha256=digest,
                  detectorSha256=hashlib.sha256((Path(__file__).parent/'zfight_audit.py').read_bytes()).hexdigest())
    (folder/'FishHatchery-frame1.json').write_text(json.dumps(report,indent=2)+'\n')
    write_findings(report,folder/'FishHatchery-frame1.md',False)
    from check_hatchery_ground import check_ground
    terrain=check_ground(folder,digest)
    verts=[];polys=[]
    deps=bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type!='MESH' or obj.name.startswith('Studio.'):continue
        evaluated=obj.evaluated_get(deps);mesh=evaluated.to_mesh();start=len(verts)
        verts.extend(evaluated.matrix_world@v.co for v in mesh.vertices)
        polys.extend(tuple(start+i for i in f.vertices) for f in mesh.polygons)
        evaluated.to_mesh_clear()
    tree=BVHTree.FromPolygons(verts,polys)
    def point(native):
        x,y,z=source(native);return Vector((-x,-y,z))
    def hit(native,direction,distance):return tree.ray_cast(point(native),Vector(direction),distance)[0]
    holes=[];floor_probes=0;headroom=[]
    for x,y,z in deck_cells():
        for dx in (.02,.1,.5,.9,.98):
            for dy in (.02,.1,.5,.9,.98):
                floor_probes+=1
                if hit((x+dx,y+dy,z+.03),(0,0,-1),.15) is None:holes.append([x+dx,y+dy,z])
        for dx,dy in ((0,0),(-.20,0),(.20,0),(0,-.20),(0,.20)):
            if hit((x+.5+dx,y+.5+dy,z+.12),(0,0,1),1.1) is not None:headroom.append([x+.5+dx,y+.5+dy,z])
    pen_blocked=[]
    for x0,x1 in ((1.42,2.90),(4.,5.45)):
        for x in (x0+.55,(x0+x1)/2,x1-.25):
            for y in (4.70,5.50,6.40):
                # Probe the retained cage's actual inner aperture. Its rim
                # occupies part of a reserved pen cell, not an added floor.
                found=hit((x,y,1.03),(0,0,-1),.12)
                if found is not None:pen_blocked.append([x,y,1])
    # Read raw roof/shell panels at their opaque fields; source-owned doors
    # intentionally remain one tile wide and open below their native arch.
    shell=bpy.data.objects['FishHatchery.Headhouse.Shell']
    shell_tree=BVHTree.FromObject(shell,deps)
    window_misses=[];window_probes=0
    mounts=json.loads(collection.objects['FishHatchery.Headhouse.Windows']['df_window_mounts'])
    for mount in mounts:
        outward=Vector((-mount['outward'][0],-mount['outward'][1],mount['outward'][2]))
        for edge in mount['rearEdges']:
            a,b=(Vector((-p[0],-p[1],p[2])) for p in edge)
            for t in (0,.25,.5,.75,1):
                p=a.lerp(b,t);window_probes+=1
                if shell_tree.ray_cast(p+outward*.04,-outward,.12)[0] is None:
                    window_misses.append({'anchor':mount['anchor'],'point':list(p)})
    uv_corners=0;uv_errors=[]
    for obj in objects:
        if obj.type!='MESH' or 'native_resource' in obj or 'liquid_surface' in obj:continue
        mesh=obj.data
        for face in mesh.polygons:
            name=mesh.materials[face.material_index].name
            if not (name.endswith('.IronTeeth') or name=='BaseWood_Brown.Folktails'):continue
            for loop in face.loop_indices:
                uv=tuple(mesh.uv_layers.active.data[loop].uv);uv_corners+=1
                if not valid_native_uv(name,uv):uv_errors.append({'object':obj.name,'face':face.index,'material':name,'uv':uv})
    # Shell object has identity transform; test lower and upper wall fields.
    shell_misses=[];shell_probes=0
    for x in [1.01+i*3.98/99 for i in range(100)]:
        for z in [1.01+i*1.98/49 for i in range(50)]:
            for y,normal in ((.8,(0,-1,0)),(3.2,(0,1,0))):
                if y<1 and 2<=x<=3 and z<=2:continue
                shell_probes+=1
                if shell_tree.ray_cast(point((x,y,z)),Vector(normal),.4)[0] is None:shell_misses.append([x,y,z])
    # Actual side skin begins behind the native 14mm exterior timber inset;
    # a ray outside that setback is outside the shell, not a through-hole.
    for y in [1.03+i*1.94/49 for i in range(50)]:
        for z in [1.01+i*1.98/49 for i in range(50)]:
            for x,normal in ((.8,(-1,0,0)),(5.2,(1,0,0))):
                shell_probes+=1
                if shell_tree.ray_cast(point((x,y,z)),Vector(normal),.4)[0] is None:shell_misses.append([x,y,z])
    from hatchery_manifests import write_manifests
    # Validation invocation writes only the same derived JSON manifests; no
    # saved geometry or native prop matrix is modified.
    manifests=write_manifests(folder,collection)
    picking=json.loads((folder/'FishHatchery-structure.json').read_text())
    boxes=[b for p in picking['parts'] for b in p['pickingBoxes']]
    def contained(point):
        return any(all(abs(point[i]-b['center'][i])<b['size'][i]/2 for i in range(3)) for b in boxes)
    picking_probes=[((6.5,5.5,.5),False,'Clear space below dock'),
                    ((6.5,5.5,.95),True,'Physical dock slab'),
                    ((2.5,2.,1.5),True,'Enclosed headhouse'),
                    ((2.5,5.5,.6),False,'Pen water aperture')]
    picking_errors=[{'point':p,'expected':expected,'purpose':purpose} for p,expected,purpose in picking_probes if contained(p)!=expected]
    out={'scope':'Saved selective candidate only; native placement/path tests remain required',
         'sourceSha256':digest,'floorProbes':floor_probes,'floorHoles':holes,
         'headroomObstructions':headroom,'penDeckObstructions':pen_blocked,
         'shellProbes':shell_probes,'shellHoles':shell_misses,
         'windowRearContactProbes':window_probes,'windowMountHoles':window_misses,
         'nativeUvCorners':uv_corners,'nativeUvFailures':uv_errors,
         'pickingProbes':len(picking_probes),'pickingFailures':picking_errors,
         'retainedArchitectureSurfaceSha256':retained,'originalObjectsUnchanged':untouched,
         'bankSurfaceProbes':terrain['surfaceProbes'],'bankTerrainVisibleOverlapPairs':terrain['assembledVisibleOverlapPairs'],
         'roofPathBoardClearance':terrain['roofPathBoardClearance'],
         'visibleOverlapPairs':report['visibleConflicts'],'manifests':manifests}
    (folder/'candidate-checks.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({k:v for k,v in out.items() if k not in ('floorHoles','headroomObstructions','shellHoles')}),flush=True)
    print('FAILURE_COUNTS',len(holes),len(headroom),len(pen_blocked),len(shell_misses),flush=True)
    if hashlib.sha256(scene.read_bytes()).hexdigest()!=digest:raise ValueError('Read-only check changed source scene')
    if report['visibleConflicts'] or holes or headroom or pen_blocked or shell_misses or window_misses or uv_errors or picking_errors:raise ValueError('Candidate geometric validation failed; inspect exact report')

if __name__=='__main__':main()
