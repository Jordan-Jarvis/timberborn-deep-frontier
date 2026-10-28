"""Geometric z-fighting risk audit of evaluated Blender meshes.

No geometry repair, depth bias, deduplication or export modification. The audit
compares actual near-coplanar overlapping triangles, including their UV maps,
and ray-tests sampled overlap points for exterior visibility. GPU depth-buffer
precision and shader-specific effects still require native camera inspection.
"""
import argparse,hashlib,itertools,json,math,sys,time
from pathlib import Path
import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT=Path(__file__).resolve().parents[2]


def cross2(a,b):return a[0]*b[1]-a[1]*b[0]


def clip_triangle(subject,clip):
    """Convex clipping in the first triangle's orthonormal plane."""
    result=list(subject)
    sign=1 if cross2(clip[1]-clip[0],clip[2]-clip[0])>0 else -1
    for a,b in zip(clip,clip[1:]+clip[:1]):
        output=[]
        for p,q in zip(result,result[1:]+result[:1]):
            dp=sign*cross2(b-a,p-a);dq=sign*cross2(b-a,q-a)
            if dp>=-1e-10:output.append(p)
            if (dp>=0)!=(dq>=0):output.append(p+(q-p)*(dp/(dp-dq)))
        result=output
        if len(result)<3:return []
    return result


def polygon_area(points):
    return abs(sum(cross2(a,b) for a,b in zip(points,points[1:]+points[:1])))/2


def interpolate_uv(p,triangle):
    a,b,c=triangle['v'];v0=b-a;v1=c-a;v2=p-a
    d00=v0.dot(v0);d01=v0.dot(v1);d11=v1.dot(v1)
    denominator=d00*d11-d01*d01
    if abs(denominator)<1e-16:raise ValueError('Degenerate UV interpolation triangle')
    s=(d11*v2.dot(v0)-d01*v2.dot(v1))/denominator
    t=(d00*v2.dot(v1)-d01*v2.dot(v0))/denominator
    u=triangle['uv']
    return u[0]*(1-s-t)+u[1]*s+u[2]*t


def collect(objects,min_area):
    triangles=[];vertices=[];indices=[]
    graph=bpy.context.evaluated_depsgraph_get()
    for obj in objects:
        if obj.type!='MESH' or obj.hide_render:continue
        evaluated=obj.evaluated_get(graph);mesh=evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            if not mesh.uv_layers.active:raise ValueError('Mesh has no authored UVs: '+obj.name)
            uv=mesh.uv_layers.active.data
            tagged='df_source' in mesh.attributes
            if tagged:source_locations=json.loads(obj['df_source_locations'])
            for tri in mesh.loop_triangles:
                points=[evaluated.matrix_world@mesh.vertices[i].co for i in tri.vertices]
                raw=(points[1]-points[0]).cross(points[2]-points[0])
                area=raw.length/2
                # Retain small triangles in the occlusion tree even when their
                # own overlap could never reach the configured report area.
                if area<1e-12:continue
                normal=raw.normalized()
                material=mesh.materials[tri.material_index]
                if material is None:raise ValueError('Unbound material: '+obj.name)
                record={'object':obj.name,'face':tri.polygon_index,'v':points,
                        'n':normal,'uv':[uv[i].uv.copy() for i in tri.loops],
                        'material':material.name,'area':area}
                if tagged:record['source']=source_locations[mesh.attributes['df_source'].data[tri.polygon_index].value]
                triangles.append(record)
                start=len(vertices);vertices.extend(points);indices.append((start,start+1,start+2))
        finally:evaluated.to_mesh_clear()
    if not triangles:raise ValueError('No evaluated model triangles')
    return triangles,vertices,indices


def candidate_pairs(triangles,epsilon,min_area,angle_degrees):
    """AABB/normal spatial index, including exactly coincident flat faces.

    Blender BVHTree.overlap omits coplanar triangles even with epsilon. It is
    suitable for visibility rays here, not for the candidate intersection test.
    Bucket coordinates index geometry only; vertex positions are never changed.
    """
    bucket_size=.5;normal_step=.02
    normal_delta=2*math.sin(math.radians(angle_degrees)/2)+1e-6
    buckets={};eligible=[]
    def cells(bounds):
        return itertools.product(*(range(math.floor((bounds[0][a]-epsilon)/bucket_size),
                                         math.floor((bounds[1][a]+epsilon)/bucket_size)+1) for a in range(3)))
    for i,t in enumerate(triangles):
        if t['area']<min_area:continue
        bounds=([min(p[a] for p in t['v']) for a in range(3)],
                [max(p[a] for p in t['v']) for a in range(3)])
        t['bounds']=bounds;eligible.append(i)
        normal_key=tuple(math.floor(v/normal_step) for v in t['n'])
        group=buckets.setdefault(normal_key,{})
        for cell in cells(bounds):group.setdefault(cell,[]).append(i)
    print('ZFIGHT index:',len(eligible),'area-eligible triangles;',len(buckets),'normal bins',flush=True)
    for i in eligible:
        t=triangles[i];near=set()
        keys=itertools.product(*(range(math.floor((v-normal_delta)/normal_step),
                                       math.floor((v+normal_delta)/normal_step)+1) for v in t['n']))
        for key in keys:
            if key not in buckets:continue
            group=buckets[key]
            for cell in cells(t['bounds']):
                if cell in group:near.update(group[cell])
        for j in near:
            if j<=i:continue
            b=triangles[j]
            if t['object']==b['object'] and t['face']==b['face']:continue
            if any(t['bounds'][1][a]+epsilon<b['bounds'][0][a] or b['bounds'][1][a]+epsilon<t['bounds'][0][a] for a in range(3)):continue
            yield i,j


def audit(objects,epsilon=.0005,min_area=.0005,angle_degrees=.05):
    started=time.monotonic();triangles,vertices,indices=collect(objects,min_area)
    tree=BVHTree.FromPolygons(vertices,indices,all_triangles=True)
    pairs=candidate_pairs(triangles,epsilon,min_area,angle_degrees)
    print('ZFIGHT geometry:',len(triangles),'evaluated triangles',flush=True)
    cosine=math.cos(math.radians(angle_degrees))
    conflicts=[];same_uv=0;considered=0;pair_count=0
    ray_length=max((max(p[a] for p in vertices)-min(p[a] for p in vertices)) for a in range(3))*3+1
    for i,j in pairs:
        pair_count+=1
        a,b=triangles[i],triangles[j]
        if a['object']==b['object'] and a['face']==b['face']:continue
        if min(a['area'],b['area'])<min_area:continue
        # Opposite faces do not compete under normal back-face culling.
        # These are reported as a scope limitation, not silently repaired.
        if a['n'].dot(b['n'])<cosine:continue
        distances=[abs((p-a['v'][0]).dot(a['n'])) for p in b['v']]
        if max(distances)>epsilon:continue
        considered+=1
        n=a['n'];u=(a['v'][1]-a['v'][0]).normalized();v=n.cross(u);origin=a['v'][0]
        def project(p):return Vector(((p-origin).dot(u),(p-origin).dot(v)))
        clipped=clip_triangle([project(p) for p in a['v']],[project(p) for p in b['v']])
        if len(clipped)<3:continue
        area=polygon_area(clipped)
        if area<min_area:continue
        points=[origin+u*p[0]+v*p[1] for p in clipped]
        center=sum(points,Vector())/len(points)
        if a['material']==b['material'] and all((interpolate_uv(p,a)-interpolate_uv(p,b)).length<1e-5 for p in points):
            same_uv+=1;continue
        visible=False
        for p in [center,*[(center+q)/2 for q in points]]:
            for direction in [n,(n+u*.7).normalized(),(n-u*.7).normalized(),(n+v*.7).normalized(),(n-v*.7).normalized()]:
                if tree.ray_cast(p+direction*(epsilon*8),direction,ray_length)[0] is None:
                    visible=True;break
            if visible:break
        conflicts.append({'a':{key:a[key] for key in ('object','face','material','source') if key in a},
                          'b':{key:b[key] for key in ('object','face','material','source') if key in b},
                          'planeSeparation':max(distances),'overlapArea':area,'visible':visible,
                          'center':list(center),'normal':list(n),'polygon':[list(p) for p in points]})
    # Sorting is report presentation only; geometry and source IDs are unchanged.
    conflicts.sort(key=lambda c:(not c['visible'],-c['overlapArea']))
    return {'scope':'Evaluated modifiers and posed native prop meshes. Same-facing triangles only; five exterior ray directions per sample. Potential depth conflicts, not proof of GPU flicker.',
            'epsilon':epsilon,'minimumOverlapArea':min_area,'parallelAngleDegrees':angle_degrees,
            'triangles':len(triangles),'spatialCandidatePairs':pair_count,'nearPlanePairs':considered,
            'identicalMaterialAndUvPairs':same_uv,'visibleConflicts':sum(c['visible'] for c in conflicts),
            'occludedConflicts':sum(not c['visible'] for c in conflicts),'conflicts':conflicts,
            'seconds':round(time.monotonic()-started,2)}


def render_review(report,objects,path):
    """Temporary diagnostic scene: grey model with red overlap polygons."""
    scene=bpy.context.scene
    grey=bpy.data.materials.new('AuditGrey');grey.diffuse_color=(.37,.40,.42,1)
    red=bpy.data.materials.new('AuditOverlap');red.diffuse_color=(1,.025,.12,1)
    for obj in objects:
        if obj.type!='MESH':continue
        obj.data=obj.data.copy()
        for slot in obj.material_slots:slot.material=grey
    vertices=[];faces=[]
    for conflict in report['conflicts']:
        if not conflict['visible']:continue
        start=len(vertices);offset=Vector(conflict['normal'])*.008
        vertices.extend(Vector(p)+offset for p in conflict['polygon'])
        faces.append(tuple(range(start,len(vertices))))
    mesh=bpy.data.meshes.new('Visible depth-conflict regions');mesh.from_pydata(vertices,[],faces)
    marker=bpy.data.objects.new('Visible depth-conflict regions',mesh);scene.collection.objects.link(marker)
    marker.data.materials.append(red)
    scene.render.engine='BLENDER_WORKBENCH';scene.display.shading.color_type='MATERIAL'
    scene.display.shading.light='STUDIO';scene.display.shading.show_shadows=False
    scene.display.shading.show_cavity=True;scene.display.shading.show_specular_highlight=False
    scene.render.resolution_x=1400;scene.render.resolution_y=1400;scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG';scene.render.filepath=str(path)
    bpy.ops.render.render(write_still=True)


def write_findings(report,path,rendered):
    groups={}
    for c in report['conflicts']:
        if not c['visible']:continue
        key=(c['a']['object'],c['b']['object'],*sorted((c['a']['material'],c['b']['material'])))
        group=groups.setdefault(key,{'pairs':0,'area':0,'faces':set(),'example':c['center']})
        group['pairs']+=1;group['area']+=c['overlapArea']
        group['faces'].update(((c['a']['object'],c['a']['face']),(c['b']['object'],c['b']['face'])))
    lines=[f'# {report["model"]} depth-conflict review — frame {report["frame"]}','',
           f'{report["visibleConflicts"]} potentially visible triangle overlap pairs; '
           f'{report["occludedConflicts"]} occluded pairs. Pair counts are not counts of distinct visual defects.',
           '',*([f'![Red marks indicate overlapping surfaces]({path.stem}.png)',''] if rendered else []),
           'Positions below are Blender scene coordinates. The JSON includes exact evaluated face IDs, overlap polygons, materials and measured separation.',
           '', '| Object pair | Material pair | Triangle pairs | Unique faces | Example position |',
           '| --- | --- | ---: | ---: | --- |']
    for key,g in sorted(groups.items(),key=lambda item:-item[1]['area']):
        lines.append(f'| {key[0]} / {key[1]} | {key[2]} / {key[3]} | {g["pairs"]} | {len(g["faces"])} | '+', '.join(f'{v:.4f}' for v in g['example'])+' |')
    lines+=['','Limits: same-facing surfaces under normal back-face culling; geometric tolerance is '+str(report['epsilon'])+
            ' model units. This does not prove how a GPU shader will draw them. Added player paths and neighboring buildings require an assembled-scene or native check. Nothing is repaired automatically.']
    path.write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--models',required=True)
    parser.add_argument('--frames',default='1')
    parser.add_argument('--epsilon',type=float,default=.0005)
    parser.add_argument('--min-area',type=float,default=.0005)
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--fail-on-visible',action='store_true')
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    if args.epsilon<=0 or args.min_area<=0:raise ValueError('Positive tolerances required')
    folder=ROOT/'outputs/zfight';folder.mkdir(parents=True,exist_ok=True)
    detector_hash=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    failed=[]
    for model in args.models.split(','):
        for frame in [int(x) for x in args.frames.split(',')]:
            bpy.ops.wm.open_mainfile(filepath=str(ROOT/f'src/DeepFrontier/Art/Source/{model}-ReferenceStudy.blend'))
            bpy.context.scene.frame_set(frame);bpy.context.view_layer.update()
            objects=list(bpy.data.collections[model+'.ReferenceStudy'].all_objects)
            report=audit(objects,args.epsilon,args.min_area)
            scene_path=ROOT/f'src/DeepFrontier/Art/Source/{model}-ReferenceStudy.blend'
            report.update(model=model,frame=frame,sourceScene=str(scene_path.relative_to(ROOT)),
                          sourceSha256=hashlib.sha256(scene_path.read_bytes()).hexdigest(),
                          detectorSha256=detector_hash)
            path=folder/f'{model}-frame{frame}.json'
            path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            print('ZFIGHT REPORT',json.dumps({k:v for k,v in report.items() if k!='conflicts'}),flush=True)
            if args.render:
                image_path=folder/f'{model}-frame{frame}.png'
                render_review(report,objects,image_path)
                report['diagnosticImage']={'path':str(image_path.relative_to(ROOT)),
                                          'sha256':hashlib.sha256(image_path.read_bytes()).hexdigest()}
                path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
            write_findings(report,folder/f'{model}-frame{frame}.md',args.render)
            if report['visibleConflicts']:failed.append(str(path))
    if args.fail_on_visible and failed:raise ValueError('Visible depth-conflict candidates: '+', '.join(failed))


if __name__=='__main__':main()
