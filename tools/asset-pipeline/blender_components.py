"""Lossless separation of explicitly authored mesh components in Blender."""
import hashlib
import json
import struct
import bmesh
import bpy


def surface_digest(obj,faces=None):
    """Geometry/UV/material/bevel/provenance identity, independent of indices."""
    mesh=obj.data
    indices=range(len(mesh.polygons)) if faces is None else sorted(faces)
    sources=json.loads(obj['df_source_locations'])
    source=mesh.attributes['df_source'];native=mesh.attributes['df_source_uv']
    # A mesh built without a bevel modifier (Geometry.build(bevel=0), the
    # triangle-budget models) has no edge weights: every weight is 0. A beveled
    # mesh must carry its weights.
    weight=mesh.attributes.get('bevel_weight_edge')
    if weight is None and any(m.type=='BEVEL' for m in obj.modifiers):
        raise ValueError('Beveled mesh has no bevel_weight_edge: '+obj.name)
    uv=mesh.uv_layers['UVMap']
    records=[]
    for index in indices:
        polygon=mesh.polygons[index]
        corners=[]
        for li in polygon.loop_indices:
            loop=mesh.loops[li]
            corners.append(struct.pack('<6f',*mesh.vertices[loop.vertex_index].co,
                *uv.data[li].uv,0.0 if weight is None else weight.data[loop.edge_index].value))
        # Preserve winding but allow BMesh to rotate a face's starting corner.
        start=min(range(len(corners)),key=lambda i:b''.join(corners[i:]+corners[:i]))
        corners=corners[start:]+corners[:start]
        record=struct.pack('<I?',polygon.material_index,native.data[index].value)
        record+=sources[source.data[index].value].encode()+b'\0'+b''.join(corners)
        records.append(hashlib.sha256(record).digest())
    return hashlib.sha256(b''.join(sorted(records))).hexdigest()


def object_digest(obj):
    """Watch untouched objects without mutating or evaluating their geometry."""
    def rna_values(block):
        values={}
        for prop in block.bl_rna.properties:
            if prop.identifier in ('rna_type',) or prop.type in ('POINTER','COLLECTION'):continue
            value=getattr(block,prop.identifier)
            values[prop.identifier]=(list(value) if prop.type in ('INT','FLOAT','BOOLEAN') and prop.is_array else value)
        return values
    data={'name':obj.name,'type':obj.type,'matrix':[v for row in obj.matrix_local for v in row],
          'parent':None if obj.parent is None else obj.parent.name,
          'properties':{k:obj[k] for k in obj.keys()},
          'modifiers':[rna_values(m) for m in obj.modifiers]}
    if obj.type=='MESH':
        mesh=obj.data
        # Other scene meshes include native preview props and have no custom
        # source attributes. Their raw datablock digest also catches UV edits.
        records=[struct.pack('<3f',*v.co) for v in mesh.vertices]
        records.extend(struct.pack('<I',p.material_index)+struct.pack('<'+str(len(p.vertices))+'I',*p.vertices)
                       for p in mesh.polygons)
        for layer in mesh.uv_layers:
            records.append(layer.name.encode())
            records.extend(struct.pack('<2f',*item.uv) for item in layer.data)
        data['mesh']=hashlib.sha256(b''.join(records)).hexdigest()
        data['materials']=[m.name for m in mesh.materials]
    if obj.animation_data and obj.animation_data.action:
        action=obj.animation_data.action
        data['animation']=[{'path':c.data_path,'index':c.array_index,
            'keys':[(tuple(k.co),tuple(k.handle_left),tuple(k.handle_right),k.interpolation) for k in c.keyframe_points]}
            for c in action.fcurves]
    return hashlib.sha256(json.dumps(data,sort_keys=True,default=str).encode()).hexdigest()


def retain_faces(mesh,indices):
    bm=bmesh.new()
    try:
        bm.from_mesh(mesh);bm.faces.ensure_lookup_table()
        bmesh.ops.delete(bm,geom=[f for f in bm.faces if f.index not in indices],context='FACES')
        bm.to_mesh(mesh);mesh.update()
    finally:bm.free()


def separate_components(obj,components):
    """Split known face ranges; preserve all stored UVs and bevel weights."""
    claimed=set();names=[]
    for component in components:
        name=component['name'];first,end=component['faceRange']
        if not 0<=first<end<=len(obj.data.polygons) or name in bpy.data.objects:
            raise ValueError('Invalid or already separated component '+name)
        indices=set(range(first,end))
        if claimed.intersection(indices):raise ValueError('Overlapping component ownership')
        claimed.update(indices);names.append(name)
    remaining=set(range(len(obj.data.polygons)))-claimed
    if not remaining:raise ValueError('Architecture must retain its explicit parent mesh')
    before=surface_digest(obj,remaining)
    for component in components:
        name=component['name'];indices=set(range(*component['faceRange']))
        expected=surface_digest(obj,indices)
        part=obj.copy();part.data=obj.data.copy();part.name=name;part.data.name=name
        for collection in obj.users_collection:collection.objects.link(part)
        retain_faces(part.data,indices)
        if surface_digest(part)!=expected:raise RuntimeError('Component separation changed surface data: '+name)
        part['df_component']=name
    retain_faces(obj.data,remaining)
    if surface_digest(obj)!=before:raise RuntimeError('Separation changed retained architecture')
    obj['df_components']=json.dumps(names)
    return {'retainedFaces':len(remaining),'retainedSurfaceSha256':before,
            'separatedFaces':len(claimed),'components':names}
