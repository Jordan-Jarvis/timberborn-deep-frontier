"""Author explicit Iron Teeth atlas islands when creating prototype primitives.

Coordinates match the proven civic-native authoring rectangles in
frontier_architecture.py. Unknown materials and degenerate faces fail; no
default UV rectangle or export-time correction is used.
"""
import math

MATERIALS={
    'BaseMetal.IronTeeth', 'PaintedMetal.IronTeeth',
    'BaseWood_DarkBrown.IronTeeth', 'Plaster_Orange.IronTeeth',
    'Plaster_White.IronTeeth','BaseWood_Grey.IronTeeth',
    'IrregularPlanks_DarkBrown.IronTeeth','Details.IronTeeth',
}


def atlas_rectangle(material,face):
    if material not in MATERIALS:raise ValueError('Unspecified native atlas material: '+material)
    if material=='BaseMetal.IronTeeth':return (.02,.48,.52,.98)
    if material=='PaintedMetal.IronTeeth':
        strip=face%8;row=(face//8)%4
        return (strip/16+.003,(strip+1)/16-.003,row/4+.018,(row+1)/4-.018)
    if material in ('BaseWood_DarkBrown.IronTeeth','BaseWood_Grey.IronTeeth'):
        strip=face%8
        return (strip/16+.004,(strip+1)/16-.004,.012,.488)
    if material=='IrregularPlanks_DarkBrown.IronTeeth':
        strip=face%8
        return (strip/8+.008,(strip+1)/8-.008,.012,.988)
    if material=='Details.IronTeeth':return (.62,.88,.329,.348)
    if material in ('Plaster_Orange.IronTeeth','Plaster_White.IronTeeth'):
        return (.02,.98,.02,.98)
    raise ValueError('Native material has no authored atlas rectangle: '+material)


def author_face_uv(mesh,uv,face,material):
    points=[mesh.vertices[i].co for i in face.vertices]
    edges=[points[(i+1)%len(points)]-p for i,p in enumerate(points)]
    along=max(edges,key=lambda edge:edge.length_squared).normalized()
    across=face.normal.cross(along).normalized()
    coords=[(p.dot(across),p.dot(along)) for p in points]
    low=[min(p[i] for p in coords) for i in range(2)]
    span=[max(p[i] for p in coords)-low[i] for i in range(2)]
    if min(span)<=1e-8 or not all(math.isfinite(v) for v in (*span,*low)):
        raise ValueError(f'Degenerate authored primitive UV face: {mesh.name}/{face.index}')
    u0,u1,v0,v1=atlas_rectangle(material,face.index)
    for loop,(u,v) in zip(face.loop_indices,coords,strict=True):
        uv.data[loop].uv=(u0+(u-low[0])/span[0]*(u1-u0),v0+(v-low[1])/span[1]*(v1-v0))


def author_primitive_uv(obj,material):
    mesh=obj.data
    mesh.update()
    for layer in list(mesh.uv_layers):mesh.uv_layers.remove(layer)
    uv=mesh.uv_layers.new(name='UVMap')
    for face in mesh.polygons:author_face_uv(mesh,uv,face,material)
    obj['df_uv_profile']='prototype-native-v1'
