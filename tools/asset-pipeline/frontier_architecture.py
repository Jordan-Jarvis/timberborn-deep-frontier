"""Geometry authoring kit for the approved Iron Teeth concept designs.

Dimensions are authored in game tile units, X across, Y back, Z up. Vertex
positions are created in the official exporter's Blender source coordinates.
No bounds repair, runtime scale adjustment, or substitute material is applied.
"""
import math
import random
import json
import sys
from pathlib import Path
import bpy
from mathutils import Vector, Quaternion

PALETTE = [
    ('BaseWood_DarkBrown.IronTeeth', (.22,.105,.045), 0),
    ('IrregularPlanks_DarkBrown.IronTeeth', (.43,.235,.105), 0),
    ('BaseMetal.IronTeeth', (.105,.125,.14), .65),
    ('PaintedMetal.IronTeeth', (.16,.28,.27), .35),
    ('Plaster_Orange.IronTeeth', (.67,.40,.17), 0),
    ('Plaster_White.IronTeeth', (.65,.64,.55), 0),
    ('BaseWood_Grey.IronTeeth', (.32,.31,.27), 0),
    ('Details.IronTeeth', (.55,.48,.31), .4),
]
WOOD, PLANK, IRON, ROOF, SAND, LIME, GREY, BRASS = range(8)

def facade_panel(g,axis,plane,start,end,bottom,top,positive,material):
    """One opaque outward wall face, with no invisible interior/back surface."""
    if axis not in ('X','Y') or end<=start or top<=bottom:
        raise ValueError('Facade panel requires an explicit axis and positive extent')
    if axis=='Y':
        points=[(start,plane,bottom),(end,plane,bottom),(end,plane,top),(start,plane,top)]
        reverse=positive
    else:
        points=[(plane,start,bottom),(plane,end,bottom),(plane,end,top),(plane,start,top)]
        reverse=not positive
    g.add(points,[(3,2,1,0) if reverse else (0,1,2,3)],material)

def create_materials():
    result=[]
    for name,color,metallic in PALETTE:
        m=bpy.data.materials.new(name); m.use_nodes=True
        m.diffuse_color=(*color,1)
        bs=m.node_tree.nodes['Principled BSDF']
        bs.inputs['Base Color'].default_value=(*color,1)
        bs.inputs['Metallic'].default_value=metallic
        bs.inputs['Roughness'].default_value=.68 if metallic==0 else .48
        # Preview grain only. Runtime resolves these exact native material names.
        if name in (PALETTE[WOOD][0], PALETTE[PLANK][0], PALETTE[GREY][0]):
            n=m.node_tree.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value=7
            n.inputs['Detail'].default_value=2
            tex=m.node_tree.nodes.new('ShaderNodeTexCoord')
            mapping=m.node_tree.nodes.new('ShaderNodeVectorMath'); mapping.operation='MULTIPLY'
            mapping.inputs[1].default_value=(3,3,.12)
            m.node_tree.links.new(tex.outputs['Generated'],mapping.inputs[0])
            m.node_tree.links.new(mapping.outputs[0],n.inputs['Vector'])
            ramp=m.node_tree.nodes.new('ShaderNodeValToRGB')
            ramp.color_ramp.elements[0].color=(*(v*.74 for v in color),1)
            ramp.color_ramp.elements[1].color=(*(v*1.18 for v in color),1)
            m.node_tree.links.new(n.outputs['Fac'],ramp.inputs[0]); m.node_tree.links.new(ramp.outputs[0],bs.inputs['Base Color'])
        result.append(m)
    return result

class Geometry:
    def __init__(self,name,origin=(0,0,0)):
        self.name=name; self.origin=Vector(origin); self.vertices=[]; self.faces=[]; self.materials=[]
        self.face_uvs=[]
        self.face_sources=[]
        self.native_props=[]
        self.liquid_surfaces=[]
        self.doorways=[]
        self.visitor_seats=[]
        self.structural_parts=[]
        self.window_mounts=[]
        # Explicit authored assets, kept separate in Blender for targeted edits.
        # Faces remain here during generation so existing geometry validators
        # and native UV assignment keep their original deterministic ordering.
        self.components=[]
        # Every add() call: (first vertex, end vertex, first face, end face).
        # Closed convex calls are solid volumes for the opt-in enclosed-face
        # cull (enclosed_cull.py); hidden_volumes are declared closed spaces
        # (mesh coordinates, with the component group they belong to).
        self.primitives=[]
        self.hidden_volumes=[]
        # Opt-in, default off: other families build exactly as before.
        self.cull_enclosed=False
        # With cull_enclosed: also ray-test small faces (enclosed_cull.small).
        self.cull_small_hidden=False
    def declare_hidden_volume(self,lo,hi,exposed=()):
        """An authored space that no camera can see into: its walls, floor,
        roof and sealed doors close it. Faces whose front lies inside it are
        removed when cull_enclosed is set. `exposed` boxes (door recesses)
        are carved out by splitting the volume around them."""
        boxes=[(tuple(lo),tuple(hi))]
        for elo,ehi in exposed:
            split=[]
            for blo,bhi in boxes:
                if any(ehi[a]<=blo[a] or elo[a]>=bhi[a] for a in range(3)):
                    split.append((blo,bhi));continue
                cur_lo,cur_hi=list(blo),list(bhi)
                for a in range(3):
                    if elo[a]>cur_lo[a]:
                        h=list(cur_hi);h[a]=elo[a];split.append((tuple(cur_lo),tuple(h)));cur_lo[a]=elo[a]
                    if ehi[a]<cur_hi[a]:
                        l=list(cur_lo);l[a]=ehi[a];split.append((tuple(l),tuple(cur_hi)));cur_hi[a]=ehi[a]
            boxes=split
        for blo,bhi in boxes:
            a=Vector(blo)-self.origin;b=Vector(bhi)-self.origin
            self.hidden_volumes.append({'lo':(-b.x,-b.y,a.z),'hi':(-a.x,-a.y,b.z),'group':None})
    def include_component(self,component):
        if tuple(component.origin)!=(0,0,0) or component.components:
            raise ValueError('Included components must use source coordinates without nested components')
        if any(item['name']==component.name for item in self.components):
            raise ValueError('Duplicate authored component: '+component.name)
        first=len(self.faces);offset=len(self.vertices)
        self.primitives.extend((v0+offset,v1+offset,f0+first,f1+first) for v0,v1,f0,f1 in component.primitives)
        group=len(self.components)+1
        self.hidden_volumes.extend({'lo':(v['lo'][0]+self.origin.x,v['lo'][1]+self.origin.y,v['lo'][2]-self.origin.z),
                                    'hi':(v['hi'][0]+self.origin.x,v['hi'][1]+self.origin.y,v['hi'][2]-self.origin.z),
                                    'group':group} for v in component.hidden_volumes)
        self.vertices.extend((x+self.origin.x,y+self.origin.y,z-self.origin.z)
                             for x,y,z in component.vertices)
        self.faces.extend(tuple(offset+i for i in face) for face in component.faces)
        self.materials.extend(component.materials)
        self.face_uvs.extend(component.face_uvs)
        self.face_sources.extend(component.face_sources)
        self.components.append({'name':component.name,'faceRange':[first,len(self.faces)]})
    def add(self,vertices,faces,mat):
        frame=sys._getframe(1);source=[]
        while frame is not None and len(source)<4:
            if frame.f_code.co_filename!=__file__ or frame.f_code.co_name not in ('box','beam','cylinder','ring','native_piece','rivet','plate','rock','wheel'):
                source.append(f'{Path(frame.f_code.co_filename).name}:{frame.f_lineno}:{frame.f_code.co_name}')
            frame=frame.f_back
        self.face_sources.extend([' > '.join(source)]*len(faces))
        base=len(self.vertices)
        for p in vertices:
            p=Vector(p)-self.origin; self.vertices.append((-p.x,-p.y,p.z))
        self.primitives.append((base,len(self.vertices),len(self.faces),len(self.faces)+len(faces)))
        self.faces.extend(tuple(base+i for i in f) for f in faces)
        self.materials.extend([mat]*len(faces))
        self.face_uvs.extend([None]*len(faces))
    def native_piece(self,vertices,faces,uvs,mat):
        self.add(vertices,faces,mat)
        self.face_uvs[-len(faces):]=[[uvs[i] for i in face] for face in faces]
    def box(self,p,size,mat=WOOD):
        x,y,z=p; a,b,c=[v/2 for v in size]
        self.add([(x-a,y-b,z-c),(x+a,y-b,z-c),(x+a,y+b,z-c),(x-a,y+b,z-c),
                  (x-a,y-b,z+c),(x+a,y-b,z+c),(x+a,y+b,z+c),(x-a,y+b,z+c)],
                 [(0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7)],mat)
    def beam(self,a,b,width=.12,depth=None,mat=WOOD):
        if depth is None: depth=width
        a,b=Vector(a),Vector(b); direction=b-a
        if direction.length < .00001: raise ValueError('Zero-length authored beam')
        rotation=direction.to_track_quat('Z','Y')
        corners=[a+rotation@Vector((x*width/2,y*depth/2,z*direction.length)) for z in (0,1) for y in (-1,1) for x in (-1,1)]
        self.add(corners,[(2,3,1,0),(5,7,6,4),(1,5,4,0),(6,7,3,2),(4,6,2,0),(3,7,5,1)],mat)
    def cylinder(self,p,r,length,mat=IRON,axis='Z',segments=16,r2=None):
        if r2 is None: r2=r
        def point(a,b,c):
            return (p[0]+c,p[1]+a,p[2]+b) if axis=='X' else ((p[0]+a,p[1]+c,p[2]+b) if axis=='Y' else (p[0]+a,p[1]+b,p[2]+c))
        v=[point(math.cos(i*2*math.pi/segments)*radius,math.sin(i*2*math.pi/segments)*radius,z) for radius,z in ((r,-length/2),(r2,length/2)) for i in range(segments)]
        f=[tuple(reversed(range(segments))),tuple(range(segments,2*segments))]
        f.extend((i,(i+1)%segments,(i+1)%segments+segments,i+segments) for i in range(segments))
        self.add(v,[tuple(reversed(face)) for face in f] if axis=='Y' else f,mat)
    def ring(self,p,r,t,width,mat=IRON,axis='Z',segments=24):
        def point(a,b,c):
            return (p[0]+c,p[1]+a,p[2]+b) if axis=='X' else ((p[0]+a,p[1]+c,p[2]+b) if axis=='Y' else (p[0]+a,p[1]+b,p[2]+c))
        v=[point(math.cos(i*2*math.pi/segments)*radius,math.sin(i*2*math.pi/segments)*radius,z) for radius,z in ((r,-width/2),(r,width/2),(r-t,-width/2),(r-t,width/2)) for i in range(segments)]
        f=[]
        for i in range(segments):
            j=(i+1)%segments
            f.extend([(i,j,j+segments,i+segments),(i+2*segments,i+3*segments,j+3*segments,j+2*segments),(i,i+2*segments,j+2*segments,j),(i+segments,j+segments,j+3*segments,i+3*segments)])
        self.add(v,[tuple(reversed(face)) for face in f] if axis=='Y' else f,mat)
    def rivet(self,p,axis='Y',r=.025):
        self.cylinder(p,r*1.35,.012,IRON,axis,8)
        self.cylinder(p,r,.025,BRASS,axis,6)
    def plate(self,p,size,axis='Y'):
        self.box(p,size,IRON)
        # Visible pair of structural fasteners.
        if axis=='Y':
            for z in (-.3,.3): self.rivet((p[0],p[1]-size[1]/2-.009,p[2]+z*size[2]))
        else:
            for z in (-.3,.3): self.rivet((p[0]-size[0]/2-.009,p[1],p[2]+z*size[2]),'X')
    def rock(self,p,size,mat,seed):
        rng=random.Random(seed); n=7; v=[]
        for z,factor in ((-.45,.7),(-.12,1),(.34,.78),(.5,.35)):
            for i in range(n):
                a=2*math.pi*i/n; jitter=rng.uniform(.86,1.08)
                v.append((p[0]+math.cos(a)*size[0]*factor*jitter/2,p[1]+math.sin(a)*size[1]*factor*jitter/2,p[2]+z*size[2]))
        f=[tuple(reversed(range(n))),tuple(range(3*n,4*n))]
        for level in range(3):
            for i in range(n): f.append((level*n+i,level*n+(i+1)%n,(level+1)*n+(i+1)%n,(level+1)*n+i))
        self.add(v,f,mat)
    def wheel(self,p,r,axis='X',mat=IRON,accent=BRASS):
        self.ring(p,r,.055,.08,mat,axis)
        self.ring(p,r*.77,.025,.06,accent,axis)
        self.cylinder(p,.09,.17,IRON,axis)
        for i in range(8):
            a=i*math.pi/4
            end=(p[0],p[1]+math.cos(a)*r*.95,p[2]+math.sin(a)*r*.95) if axis=='X' else (p[0]+math.cos(a)*r*.95,p[1],p[2]+math.sin(a)*r*.95)
            self.beam(p,end,.045,mat=mat)
    def _cull_enclosed(self,bevel):
        """Drop faces enclosed by solid or hidden volumes (enclosed_cull.py).
        Returns compacted vertices/faces/attributes, components with their
        face ranges remapped, the original index of every kept face (UV strips
        stay those of the uncut build) and the removed polygons."""
        import enclosed_cull
        group=[0]*len(self.faces)
        for index,component in enumerate(self.components):
            a,b=component['faceRange']
            for i in range(a,b):group[i]=index+1
        owner=[-1]*len(self.faces)
        volumes=[]
        margin=enclosed_cull.MARGIN+1.5*bevel
        see_through={8,9,10,11}  # lamp glass, window glass, foliage, water
        for v0,v1,f0,f1 in self.primitives:
            if f1<=f0:continue
            if len({group[i] for i in range(f0,f1)})!=1:raise ValueError(f'{self.name}: a primitive spans two components')
            # Glass, foliage cards and water are not opaque occluders.
            if any(self.materials[i] in see_through for i in range(f0,f1)):continue
            planes=enclosed_cull.convex_planes(self.vertices,self.faces[f0:f1])
            if planes is None:continue
            for i in range(f0,f1):owner[i]=len(volumes)
            volumes.append(enclosed_cull.Volume(planes,self.vertices[v0:v1],margin,len(volumes),group[f0]))
        for v in self.hidden_volumes:
            lo,hi=v['lo'],v['hi']
            corners=[(x,y,z) for x in (lo[0],hi[0]) for y in (lo[1],hi[1]) for z in (lo[2],hi[2])]
            # Declared rooms grow by 0.1 mm so members flush with their faces count;
            # every removal they propose is ray-verified below.
            volumes.append(enclosed_cull.Volume(enclosed_cull.box_planes(lo,hi),corners,-1e-4,len(volumes),v['group'] or 0,declared=True))
        excluded=see_through|{30}  # and native windows
        # Doors stay complete: a door component and every building_portal
        # face (inline portals too) are the native entrance insert that
        # test_industrial_door_components.py and check_exported_door_culling.py
        # compare face for face with its recipe. They still occlude others.
        door=[False]*len(self.faces)
        for component in self.components:
            if '.Door.' in component['name']:
                a,b=component['faceRange']
                for i in range(a,b):door[i]=True
        for i,source in enumerate(self.face_sources):
            if ':building_portal' in source:door[i]=True
        # Other faces with authored atlas islands (painted goods) may go too:
        # removing a face never changes another face's UVs.
        eligible=lambda i:self.materials[i] not in excluded and not door[i]
        exact,declared=enclosed_cull.cull(self.vertices,self.faces,owner,group,volumes,eligible)
        removed=set(exact)
        small=[]
        if self.cull_small_hidden:
            # Opt-in: small faces (fastener sides, plate edges, lamp cages) that
            # are only partly buried or tucked behind other parts. Proposed
            # here, kept unless the ray test below finds them hidden.
            proposed=removed|set(declared)
            small=[i for i in range(len(self.faces)) if i not in proposed
                   and eligible(i) and enclosed_cull.small([self.vertices[k] for k in self.faces[i]])]
        if declared or small:
            # A declared room can be open somewhere (a roof gap, a doorway):
            # each proposed face must stay unseen from every orbit direction
            # with every proposed face gone. Exact removals are verified too:
            # with a room's inner faces gone, a ray through a solid can
            # continue into the room. Visible faces stay.
            from mathutils import Vector
            from mathutils.bvhtree import BVHTree
            gone=removed|set(declared)|set(small)
            tree=BVHTree.FromPolygons(self.vertices,[f for i,f in enumerate(self.faces) if i not in gone and self.materials[i] not in see_through],epsilon=0.0)
            dirs=[Vector(d) for d in enclosed_cull.directions()]
            restored=[i for i in sorted(gone) if enclosed_cull.visible(tree,[self.vertices[k] for k in self.faces[i]],dirs)]
            removed=gone-set(restored)
            self.cull_report={'exact':len(exact),'declaredCandidates':len(declared),'smallCandidates':len(small),
                              'visibleKept':len(restored),'removed':len(removed)}
        else:
            self.cull_report={'exact':len(exact),'declaredCandidates':0,'smallCandidates':0,'visibleKept':0,'removed':len(removed)}
        keep=[i for i in range(len(self.faces)) if i not in removed]
        used=sorted({v for i in keep for v in self.faces[i]})
        remap={old:new for new,old in enumerate(used)}
        vertices=[self.vertices[v] for v in used]
        faces=[tuple(remap[v] for v in self.faces[i]) for i in keep]
        before=[0]*(len(self.faces)+1)
        for i in range(len(self.faces)):before[i+1]=before[i]+(i not in removed)
        components=[{**c,'faceRange':[before[c['faceRange'][0]],before[c['faceRange'][1]]]} for c in self.components]
        for c in components:
            if c['faceRange'][0]==c['faceRange'][1]:raise ValueError(f"{self.name}: component {c['name']} is entirely enclosed; remove it at source")
        culled=[[[round(x,5) for x in self.vertices[v]] for v in self.faces[i]] for i in sorted(removed)]
        return (vertices,faces,[self.materials[i] for i in keep],[self.face_uvs[i] for i in keep],
                [self.face_sources[i] for i in keep],components,keep,culled)
    def build(self,collection,materials,bevel=.008,uv_profile='industrial-atlas'):
        if uv_profile not in ('industrial-atlas','civic-native','research-native','prototype-native'):raise ValueError('Unknown authored UV profile '+uv_profile)
        if len(self.face_sources)!=len(self.faces):raise ValueError('Missing authored surface provenance: '+self.name)
        vertices,faces,face_materials,face_uvs,face_sources,components=self.vertices,self.faces,self.materials,self.face_uvs,self.face_sources,self.components
        original=range(len(faces));culled=[]
        if self.cull_enclosed:
            vertices,faces,face_materials,face_uvs,face_sources,components,original,culled=self._cull_enclosed(bevel)
        mesh=bpy.data.meshes.new(self.name); mesh.from_pydata(vertices,[],faces); mesh.update()
        obj=bpy.data.objects.new(self.name,mesh); collection.objects.link(obj)
        obj.location=(-self.origin.x,-self.origin.y,self.origin.z)
        for mat in materials: mesh.materials.append(mat)
        for poly,index in zip(mesh.polygons,face_materials): poly.material_index=index
        sources=list(dict.fromkeys(face_sources));source_ids={source:i for i,source in enumerate(sources)}
        attribute=mesh.attributes.new('df_source',type='INT',domain='FACE')
        attribute.data.foreach_set('value',[source_ids[source] for source in face_sources])
        obj['df_source_locations']=json.dumps(sources)
        source_uv=mesh.attributes.new('df_source_uv',type='BOOLEAN',domain='FACE')
        source_uv.data.foreach_set('value',[coords is not None for coords in face_uvs])
        # Native materials address a subrectangle of a shared atlas. Their UVs
        # must stay inside the material tile: world-coordinate tiling spills
        # into windows, signs and emissive atlas regions. Author a face island
        # on one board strip, with the grain along the longest edge.
        uv=mesh.uv_layers.new(name='UVMap')
        for poly in mesh.polygons:
            if uv_profile=='prototype-native':
                from prototype_native_uv import author_face_uv
                if face_uvs[poly.index] is not None:raise ValueError('Prototype primitive UV profile does not import native meshes')
                author_face_uv(mesh,uv,poly,mesh.materials[poly.material_index].name)
                continue
            if face_uvs[poly.index] is not None:
                for loopindex,coord in zip(poly.loop_indices,face_uvs[poly.index],strict=True):uv.data[loopindex].uv=coord
                continue
            if poly.material_index==30:
                points=[mesh.vertices[i].co for i in poly.vertices]
                axis=0 if abs(poly.normal.y)>.5 else 1
                coords=[(p[axis],p.z) for p in points]
                lo=[min(p[a] for p in coords) for a in range(2)]
                span=[max(p[a] for p in coords)-lo[a] for a in range(2)]
                if min(span)<1e-8:raise ValueError('Window must be an upright authored facade quad')
                # Exact native nine-pane square or three-pane vertical window.
                u0,u1,v0,v1=(.502,.623,.752,.998) if span[1]>span[0]*1.3 else (.002,.248,.752,.998)
                for loopindex,(u,v) in zip(poly.loop_indices,coords):uv.data[loopindex].uv=(u0+(u-lo[0])/span[0]*(u1-u0),v0+(v-lo[1])/span[1]*(v1-v0))
                continue
            if uv_profile in ('civic-native','research-native') and poly.material_index in (2,7,27,28,29):
                # Separate bounded face islands address the shipped metal and
                # plaster sheets. Wood keeps the established chunky grain.
                points=[mesh.vertices[i].co for i in poly.vertices]
                along=max((points[(i+1)%len(points)]-p for i,p in enumerate(points)),key=lambda e:e.length_squared).normalized()
                across=poly.normal.cross(along).normalized()
                coords=[(p.dot(across),p.dot(along)) for p in points]
                lo=[min(p[i] for p in coords) for i in range(2)]
                span=[max(p[i] for p in coords)-lo[i] for i in range(2)]
                if min(span)<1e-8:raise ValueError(f'Degenerate civic surface: {self.name}/{poly.index}')
                # BaseMetal has beams, grilles and badges on the same sheet.
                # Flat structural faces use its actual upper-left plate tile.
                u0,u1,v0,v1=(.02,.48,.52,.98) if poly.material_index==2 else (.02,.98,.02,.98)
                # The laboratory's metal bands address the actual metal strip
                # in Details.IronTeeth, not its mixed bags/banners/crate sheet.
                if poly.material_index==7:
                    u0,u1,v0,v1=.62,.88,.329,.348
                for loopindex,(u,v) in zip(poly.loop_indices,coords):
                    uv.data[loopindex].uv=(u0+(u-lo[0])/span[0]*(u1-u0),v0+(v-lo[1])/span[1]*(v1-v0))
                continue
            if poly.material_index in (WOOD,PLANK,ROOF):
                points=[mesh.vertices[i].co for i in poly.vertices]
                edges=[points[(i+1)%len(points)]-p for i,p in enumerate(points)]
                along=max(edges,key=lambda e:e.length_squared).normalized()
                across=poly.normal.cross(along).normalized()
                coords=[(p.dot(across),p.dot(along)) for p in points]
                lo=[min(p[i] for p in coords) for i in range(2)]
                span=[max(p[i] for p in coords)-lo[i] for i in range(2)]
                if min(span)<1e-8:raise ValueError(f'Degenerate UV face: {self.name}/{poly.index}')
                strip=original[poly.index]%8
                if poly.material_index==WOOD:
                    u0,u1=strip/16+.004,(strip+1)/16-.004
                    v0,v1=.012,.488
                elif poly.material_index==ROOF:
                    u0,u1=strip/16+.003,(strip+1)/16-.003
                    row=(original[poly.index]//8)%4
                    v0,v1=row/4+.018,(row+1)/4-.018
                else:
                    u0,u1=strip/8+.008,(strip+1)/8-.008
                    v0,v1=.012,.988
                for loopindex,(u,v) in zip(poly.loop_indices,coords):
                    uv.data[loopindex].uv=(u0+(u-lo[0])/span[0]*(u1-u0),v0+(v-lo[1])/span[1]*(v1-v0))
                continue
            axis=max(range(3),key=lambda i:abs(poly.normal[i])); axes=[i for i in range(3) if i!=axis]
            for loopindex in poly.loop_indices:
                v=mesh.vertices[mesh.loops[loopindex].vertex_index].co
                uv.data[loopindex].uv=(v[axes[0]],v[axes[1]])
        if bevel:
            mod=obj.modifiers.new('Authored softened edges','BEVEL'); mod.width=bevel; mod.segments=1
            mod.affect='EDGES'; mod.limit_method='WEIGHT'
            # Explicit native UV islands carry already finished source meshes.
            # Keep their original edges intact instead of beveling them again.
            native_vertices={v for face,coords in zip(faces,face_uvs,strict=True) if coords is not None for v in face}
            edge_faces={tuple(sorted(edge.vertices)):[] for edge in mesh.edges}
            for poly in mesh.polygons:
                for key in poly.edge_keys:edge_faces[tuple(sorted(key))].append(poly)
            weights=mesh.attributes.new(name='bevel_weight_edge',type='FLOAT',domain='EDGE')
            for edge in mesh.edges:
                faces=edge_faces[tuple(sorted(edge.vertices))]
                if not native_vertices.intersection(edge.vertices) and len(faces)==2 and faces[0].normal.angle(faces[1].normal)>mod.angle_limit:
                    weights.data[edge.index].value=1
        if components:
            from blender_components import separate_components
            separate_components(obj,components)
        if self.cull_enclosed:
            # After separation: components are copies of obj and must not
            # inherit the architecture's cull record.
            obj['df_enclosed_culled']=len(culled)
            obj['df_enclosed_cull_report']=json.dumps(self.cull_report)
            _write_culled(self.name,culled)
        return obj

def _write_culled(name,polygons):
    """Provenance of the enclosed-face cull, read by audit_hidden_geometry.py
    --culled to prove every removed face stays occluded in the saved scene."""
    folder=Path(__file__).resolve().parents[2]/'outputs/triangle-budget/culled'
    folder.mkdir(parents=True,exist_ok=True)
    (folder/(name+'.json')).write_text(json.dumps({'object':name,'polygons':polygons})+'\n',encoding='utf-8')

def deck(g,x0,y0,x1,y1,z=.19):
    count=math.ceil((x1-x0)/.17)
    for i in range(count):
        width=(x1-x0)/count
        g.box((x0+(i+.5)*width,(y0+y1)/2,z),(width-.009,y1-y0,.14),PLANK)
    # Narrow ledges have one joist; two full-width joists would overlap.
    joists=((y0+y1)/2,) if y1-y0<.26 else (y0+.07,y1-.07)
    for y in joists:g.box(((x0+x1)/2,y,z-.07),(x1-x0,.12,.14),WOOD)

def post(g,x,y,h,z=.18):
    g.box((x,y,(z+h)/2),(.14,.14,h-z),WOOD)
    for level in (z+.1,h-.12): g.plate((x,y-.025,level),(.18,.17,.20))

def rail(g,a,b,z):
    a,b=Vector(a),Vector(b); count=math.ceil((b-a).length/.72)
    for i in range(count+1):
        p=a+(b-a)*i/count; g.box((p.x,p.y,z+.27),(.07,.07,.55),WOOD)
        g.rivet((p.x,p.y-.042,z+.46),r=.018)
    for level in (.20,.51):g.beam((a.x,a.y,z+level),(b.x,b.y,z+level),.065,mat=WOOD)

def roof(g,x0,y0,x1,y1,eave,ridge):
    mid=(x0+x1)/2; length=y1-y0; count=math.ceil(length/.26)
    # Each roof plank is a separate sloped structural member.
    for i in range(count):
        y=y0+(i+.5)*length/count
        for x in (x0,x1): g.beam((x,y,eave),(mid,y,ridge),length/count,.055,ROOF)
    for y in (y0+.015,y1-.015):
        for x in (x0,x1):
            g.beam((x,y,eave-.055),(mid,y,ridge-.055),.10,.09,WOOD)
            for t in (.07,.48,.90):g.rivet((x+(mid-x)*t,y-.055,eave+(ridge-eave)*t),r=.022)
    g.beam((mid,y0,ridge),(mid,y1,ridge),.10,.11,IRON)
    for x in (x0,x1):g.beam((x,y0,eave),(x,y1,eave),.11,.12,WOOD)

def shed(g,x0,y0,x1,y1,eave,ridge,back=True):
    for x in (x0+.08,x1-.08):
        for y in (y0+.10,y1-.10):post(g,x,y,eave-.07)
    for y in (y0+.10,y1-.10):g.beam((x0+.08,y,eave-.18),(x1-.08,y,eave-.18),.14,mat=WOOD)
    for x in (x0+.08,x1-.08):
        g.beam((x,y0+.1,eave-.65),(x,y0+.55,eave-.18),.09,mat=WOOD)
        g.beam((x,y1-.1,eave-.65),(x,y1-.55,eave-.18),.09,mat=WOOD)
    if back: wall(g,x0+.13,y1-.10,x1-.13,eave-.2,.22)
    roof(g,x0,y0,x1,y1,eave,ridge)

def wall(g,x0,y,x1,top,bottom=.18):
    n=math.ceil((x1-x0)/.15)
    for i in range(n):
        width=(x1-x0)/n
        g.box((x0+(i+.5)*width,y,(top+bottom)/2),(width,.07,top-bottom),PLANK)
    # Trim terminates inside the cladding ends; its side caps must not share
    # the exposed wall-end plane once the board joints are sealed.
    if x1-x0<=.04:raise ValueError('Plank wall needs space for its inset trim ends')
    for z in (bottom+.07,top-.07):g.box(((x0+x1)/2,y-.035,z),(x1-x0-.04,.12,.10),WOOD)

def bin(g,p,size,stone=None,seed=0,*,proud_rivets=False):
    x,y,z=p; w,d,h=size
    # proud_rivets: the front rivet heads stand 9 mm off the plank face. The
    # original offset left the iron washer 1 mm proud, inside the strict
    # 0.004 overlap tolerance. Kept opt-in so existing scenes regenerate as-is.
    rivet_offset=.058 if proud_rivets else .05
    # The floor fits inside the side planks, whose corner joints butt together.
    g.box((x,y,z+.045),(w-.12,d-.12,.09),WOOD)
    for j in range(max(2,math.ceil(h/.15))):
        level=z+(j+.5)*h/max(2,math.ceil(h/.15))
        for xx in (x-w/2+.03,x+w/2-.03):g.box((xx,y,level),(.06,d-.12,h/max(2,math.ceil(h/.15))-.01),PLANK)
        for yy in (y-d/2+.03,y+d/2-.03):g.box((x,yy,level),(w,.06,h/max(2,math.ceil(h/.15))-.01),PLANK)
    for xx in (x-w/2+.055,x+w/2-.055):
        for yy in (y-d/2+.055,y+d/2-.055):
            g.box((xx,yy,z+h/2),(.09,.09,h+.03),IRON)
            for zz in (z+.08,z+h-.06):g.rivet((xx,yy-rivet_offset,zz),r=.019)
    if stone is not None:
        rng=random.Random(seed)
        for i in range(max(7,int(w*d*18))):
            r=rng.uniform(.12,.24)
            g.rock((x+rng.uniform(-w*.35,w*.35),y+rng.uniform(-d*.32,d*.32),z+h*.88),(r,r*.9,r*.8),stone,seed*100+i)

def barrel(g,p,r=.26,h=.65,water=False):
    x,y,z=p; n=14
    for i in range(n):
        a=i*math.pi*2/n
        g.beam((x+math.cos(a)*r*.89,y+math.sin(a)*r*.89,z+.05),(x+math.cos(a)*r,y+math.sin(a)*r,z+h-.05),.09,.10,PLANK)
    for level in (.12,h-.12):g.ring((x,y,z+level),r+.025,.025,.07,IRON)
    g.cylinder((x,y,z+h-.06),r*.90,.035,ROOF if water else PLANK,segments=20)

def pipe(g,points,r=.055):
    for a,b in zip(points,points[1:]):
        g.beam(a,b,r*1.7,r*1.7,IRON)
    for p in points[1:-1]:g.box(p,(r*2.1,r*2.1,r*2.1),BRASS)

def ladder(g,x,y,z,height,width=.28):
    for xx in (x-width/2,x+width/2):g.beam((xx,y,z),(xx,y+.16,z+height),.045,mat=WOOD)
    for i in range(int(height/.18)+1):
        zz=i*.18; g.beam((x-width/2,y+.16*zz/height,z+zz),(x+width/2,y+.16*zz/height,z+zz),.04,mat=IRON)

def chimney(g,x,y,z,h):
    g.box((x,y,z+h/2),(.23,.25,h),IRON)
    for level in (.1,h*.5,h-.05):
        g.box((x,y,z+level),(.28,.30,.045),GREY)
        g.rivet((x,y-.16,z+level),r=.022)
    # Open rim with dark recess, not an oversized solid cube.
    for xx in (x-.135,x+.135):g.box((xx,y,z+h+.015),(.045,.31,.08),IRON)
    for yy in (y-.135,y+.135):g.box((x,yy,z+h+.015),(.23,.045,.08),IRON)

def spin(obj,axis='X',turns=1,frame_end=61):
    obj.rotation_mode='QUATERNION'
    v={'X':(-1,0,0),'Y':(0,-1,0),'Z':(0,0,1)}[axis]
    for frame in range(1,frame_end+1):
        obj.rotation_quaternion=Quaternion(v,turns*2*math.pi*(frame-1)/(frame_end-1))
        obj.keyframe_insert(data_path='rotation_quaternion',frame=frame)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:key.interpolation='LINEAR'

def sway(obj,angle=.05,frame_end=61):
    obj.rotation_mode='XYZ'
    if (frame_end-1)%60:raise ValueError('Sway requires complete 60-frame cycles')
    for cycle in range((frame_end-1)//60):
        for frame,value in ((1,-angle),(16,0),(31,angle),(46,0),(61,-angle)):
            obj.rotation_euler.y=value;obj.keyframe_insert(data_path='rotation_euler',frame=frame+60*cycle)

def window(g,x,y,z,w=.40,h=.48):
    # Historical eight-slot prototype helper. Reviewed buildings use the
    # explicit 32-slot architectural_windows module instead.
    g.box((x,y,z),(w,.045,h),IRON)
    g.box((x,y-.027,z),(w-.07,.012,h-.07),SAND)
    for xx in (x-w/2,x+w/2,x):g.box((xx,y-.045,z),(.035,.045,h+.05),WOOD)
    for zz in (z-h/2,z+h/2,z):g.box((x,y-.05,zz),(w+.07,.05,.035),WOOD)
    g.box((x,y-.075,z-h/2-.035),(w+.13,.14,.05),WOOD)

def door(g,x,y,z=.18):
    g.box((x,y,z+.36),(.52,.06,.72),IRON)
    for i in range(4):g.box((x-.19+i*.127,y-.04,z+.34),(.12,.035,.67),PLANK)
    for xx in (x-.29,x+.29):g.box((xx,y-.08,z+.39),(.08,.12,.79),WOOD)
    g.box((x,y-.08,z+.79),(.66,.13,.09),WOOD)
    for zz in (.14,.55):g.box((x,y-.07,z+zz),(.48,.025,.04),IRON)
    g.ring((x+.15,y-.11,z+.36),.035,.012,.02,BRASS,'Y',12)

def sign_geometry(g,p,kind):
    x,y,z=p
    g.box((x,y,z),(.48,.07,.42),WOOD)
    g.box((x,y-.045,z),(.42,.022,.36),IRON)
    if kind=='Hospital':
        g.box((x,y-.062,z-.015),(.13,.025,.19),LIME)
        g.box((x,y-.062,z+.11),(.07,.025,.07),LIME)
    elif kind=='Restaurant':
        g.beam((x-.14,y-.07,z+.02),(x-.08,y-.07,z-.08),.04,mat=LIME)
        g.beam((x-.08,y-.07,z-.08),(x+.10,y-.07,z-.08),.04,mat=LIME)
        g.beam((x+.10,y-.07,z-.08),(x+.15,y-.07,z+.02),.04,mat=LIME)
        g.beam((x-.14,y-.07,z+.02),(x+.15,y-.07,z+.02),.03,mat=LIME)
    elif kind=='GroceryStore':
        g.box((x,y-.063,z-.03),(.23,.025,.12),LIME)
        g.ring((x,y-.07,z+.05),.09,.02,.02,LIME,'Y',12)
    elif kind=='FisheryWorks':
        g.rock((x-.025,y-.07,z),(.26,.04,.12),LIME,91)
        g.add([(x+.08,y-.09,z),(x+.19,y-.09,z+.08),(x+.19,y-.09,z-.08)],[(0,1,2)],LIME)
    else:raise ValueError(kind)
