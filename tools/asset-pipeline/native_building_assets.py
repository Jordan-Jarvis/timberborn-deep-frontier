"""Local previews of exact shipped assets; runtime uses native resource references.

The cached meshes/textures are never copied into the mod. Placement and prop
scale are authored explicitly, with no fitting to model bounds or tile counts.
"""
import json, math, struct, sys, zlib
from pathlib import Path
import bpy
from mathutils import Vector, Quaternion

ROOT=Path(__file__).resolve().parents[2]
CACHE=ROOT/'outputs/native-civic-assets'
sys.path.insert(0,str(ROOT/'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2

RESOURCES={
    'RooftopTerrace.IronTeeth':'Buildings/Wellbeing/RooftopTerrace/RooftopTerrace.IronTeeth.Model',
    'Barrel':'Environment/Common/Barrel/Barrel',
    'SmallTank.IronTeeth':'Buildings/Storage/SmallTank/SmallTank.IronTeeth.Model',
    'CompactWaterWheel.IronTeeth':'Buildings/Power/CompactWaterWheel/CompactWaterWheel.IronTeeth.Model',
    'Shrub.IronTeeth':'Buildings/Decoration/Shrub/Shrub.IronTeeth.Model',
    'BlueberryBushMature':'NaturalResources/Bushes/Blueberry/BlueberryBushMature',
    'CoffeeBushMature':'NaturalResources/Bushes/Coffee/CoffeeBushMature',
    'DandelionMature':'NaturalResources/Bushes/Dandelion/DandelionMature',
    'SunflowerMature':'NaturalResources/Crops/Sunflower/SunflowerMature',
    'BeaverStatue.IronTeeth':'Buildings/Decoration/BeaverStatue/BeaverStatue.IronTeeth.Model',
    'BeaverBust.IronTeeth':'Buildings/Decoration/BeaverBust/BeaverBust.IronTeeth.Model',
    'FountainOfJoy.Folktails':'Buildings/Monuments/FountainOfJoy/FountainOfJoy.Folktails.Model',
}
PLANT_MATERIALS={'Shrub.IronTeeth','Blueberry','CoffeeBush','Dandelion','Sunflower'}

def prop(g,name,model,position,scale=1,yaw=0):
    if model not in RESOURCES:raise ValueError('Unregistered native prop '+model)
    if any(p['name']==name for p in g.native_props):raise ValueError('Duplicate native prop '+name)
    g.native_props.append(dict(name=name,model=model,resource=RESOURCES[model],
        position=list(position),scale=scale,yaw=yaw))

def barrel(g,p,scale=2.6):
    # Shipped carrying-barrel origin is .1659208 above its base, in native units.
    prop(g,'NativeBarrel'+str(len(g.native_props)),'Barrel',
         (p[0],p[1],p[2]+.1659208*scale),scale)

def water_barrel(g,name,p,scale):
    prop(g,name,'SmallTank.IronTeeth',(p[0]-.5*scale,p[1]-.5*scale,p[2]),scale)
    g.liquid_surfaces.append(dict(name=name+'.Water',shape='SmallLiquidPlane',
        center=[p[0],p[1]],bottom=p[2]+.546*scale,top=p[2]+1.42*scale,
        scale=[scale,scale],flowOnly=False))


def plant(g,model,p,scale,yaw=0):
    """Place a whole native plant about its authored half-tile origin."""
    if model not in ('Shrub.IronTeeth','BlueberryBushMature','CoffeeBushMature','DandelionMature','SunflowerMature'):
        raise ValueError('Expected an explicit registered native plant')
    angle=math.radians(yaw);c,s=math.cos(angle),math.sin(angle)
    position=(p[0]-.5*scale*(c+s),p[1]-.5*scale*(c-s),p[2])
    prop(g,'NativePlant'+str(len(g.native_props)),model,position,scale,yaw)
    if model=='DandelionMature':
        g.native_props[-1]['plantAppearance']='Flowering'

def native_material(name):
    existing=bpy.data.materials.get(name)
    if existing is not None:
        if existing.get('native_preview')!=True:raise ValueError('Material name collision '+name)
        return existing
    record=json.loads((CACHE/'materials.json').read_text())[name]
    floats=dict(record['properties']['m_Floats']);colors=dict(record['properties']['m_Colors'])
    mat=bpy.data.materials.new(name);mat.use_nodes=True;mat['native_preview']=True
    nodes=mat.node_tree.nodes;links=mat.node_tree.links;bs=nodes['Principled BSDF']
    uv=nodes.new('ShaderNodeTexCoord')
    def texture(slot,linear=False):
        data=record['textures'][slot];path=CACHE/data['file']
        image=bpy.data.images.load(str(path),check_existing=False)
        image.colorspace_settings.name='Non-Color' if linear else 'sRGB';image.pack()
        tex=nodes.new('ShaderNodeTexImage');tex.image=image
        links.new(uv.outputs['UV'],tex.inputs['Vector']);return tex
    tex=texture('_MainTex');tint=colors['_Color']
    albedo,alpha=tex.outputs['Color'],tex.outputs['Alpha']
    if name=='Dandelion':
        # Native dandelions put flowers on the third UV channel. The mature
        # ornamental preview explicitly shows that layer; UV0 alone is foliage.
        detail=texture('_DetailMap');detail_uv=nodes.new('ShaderNodeUVMap');detail_uv.uv_map='uv2'
        links.new(detail_uv.outputs['UV'],detail.inputs['Vector'])
        over=nodes.new('ShaderNodeMixRGB');over.blend_type='MIX'
        links.new(detail.outputs['Alpha'],over.inputs[0]);links.new(albedo,over.inputs[1])
        links.new(detail.outputs['Color'],over.inputs[2]);albedo=over.outputs[0]
        coverage=nodes.new('ShaderNodeMath');coverage.operation='MAXIMUM'
        links.new(alpha,coverage.inputs[0]);links.new(detail.outputs['Alpha'],coverage.inputs[1]);alpha=coverage.outputs[0]
    # Unity serializes Color properties in sRGB; Blender socket values are
    # scene-linear. Decode at import, just as the sRGB albedo image is decoded.
    def srgb_to_linear(c):return c/12.92 if c<=.04045 else ((c+.055)/1.055)**2.4
    rgba=tuple(srgb_to_linear(tint[c]) for c in ('r','g','b'))+(tint['a'],)
    mul=nodes.new('ShaderNodeMixRGB');mul.blend_type='MULTIPLY';mul.inputs[0].default_value=1
    links.new(albedo,mul.inputs[1]);mul.inputs[2].default_value=rgba
    links.new(mul.outputs[0],bs.inputs['Base Color']);mat.diffuse_color=rgba
    if name in PLANT_MATERIALS:
        # Native plants are leaf cards with alpha-cut silhouettes and original
        # vertex colours. Opaque cards or missing colour data destroy the shape.
        vertex=nodes.new('ShaderNodeVertexColor');vertex.layer_name='NativeColor'
        foliage=nodes.new('ShaderNodeMixRGB');foliage.blend_type='MULTIPLY';foliage.inputs[0].default_value=1
        links.new(mul.outputs[0],foliage.inputs[1]);links.new(vertex.outputs['Color'],foliage.inputs[2])
        links.new(foliage.outputs[0],bs.inputs['Base Color'])
        cutout=nodes.new('ShaderNodeMath');cutout.operation='GREATER_THAN'
        links.new(alpha,cutout.inputs[0]);cutout.inputs[1].default_value=floats['_Cutoff']
        links.new(cutout.outputs[0],bs.inputs['Alpha'])
        mat.use_backface_culling=False
        mat.surface_render_method='DITHERED'
    bs.inputs['Metallic'].default_value=floats['_Metallic']
    bs.inputs['Roughness'].default_value=1-floats['_Smoothness']
    # The original tank's Paper label declares scalar metallic/smoothness and
    # has no metallic texture. This is its explicit source material contract.
    if name not in ('Water','FountainWater','Paper.IronTeeth','PlasteredWood_White.Folktails') and name not in PLANT_MATERIALS:
        metallic=texture('_MetallicGlossMap',True)
        metal_channels=nodes.new('ShaderNodeSeparateColor');links.new(metallic.outputs['Color'],metal_channels.inputs[0])
        links.new(metal_channels.outputs['Red'],bs.inputs['Metallic'])
        gloss=nodes.new('ShaderNodeMath');gloss.operation='MULTIPLY';gloss.inputs[1].default_value=floats['_GlossMapScale']
        links.new(metallic.outputs['Alpha'],gloss.inputs[0])
        rough=nodes.new('ShaderNodeMath');rough.operation='SUBTRACT';rough.inputs[0].default_value=1
        links.new(gloss.outputs[0],rough.inputs[1]);links.new(rough.outputs[0],bs.inputs['Roughness'])
    normal=texture('_BumpMap1' if name in ('Water','FountainWater') else '_BumpMap',True)   # FountainWater: same layout as Water
    # Unity's UnpackNormalmapRGorAG: X is R*A and Y is G. The extracted
    # DXT5nm texture has R=1; interpreting it as an RGB normal tilts every face.
    normal_color,normal_alpha=normal.outputs['Color'],normal.outputs['Alpha']
    if name=='Dandelion':
        detail_normal=texture('_BumpMap',True);links.new(detail_uv.outputs['UV'],detail_normal.inputs['Vector'])
        blend_normal=nodes.new('ShaderNodeMixRGB');blend_normal.blend_type='MIX'
        links.new(detail.outputs['Alpha'],blend_normal.inputs[0]);links.new(normal_color,blend_normal.inputs[1])
        links.new(detail_normal.outputs['Color'],blend_normal.inputs[2]);normal_color=blend_normal.outputs[0]
        blend_alpha=nodes.new('ShaderNodeMixRGB');blend_alpha.blend_type='MIX'
        links.new(detail.outputs['Alpha'],blend_alpha.inputs[0]);links.new(normal_alpha,blend_alpha.inputs[1])
        links.new(detail_normal.outputs['Alpha'],blend_alpha.inputs[2]);normal_alpha=blend_alpha.outputs[0]
    channels=nodes.new('ShaderNodeSeparateColor');links.new(normal_color,channels.inputs[0])
    def math_node(operation,a,b=None):
        node=nodes.new('ShaderNodeMath');node.operation=operation
        for i,value in enumerate((a,b)):
            if value is None:continue
            if isinstance(value,(int,float)):node.inputs[i].default_value=value
            else:links.new(value,node.inputs[i])
        return node.outputs[0]
    red=math_node('MULTIPLY',channels.outputs['Red'],normal_alpha)
    x=math_node('SUBTRACT',math_node('MULTIPLY',red,2),1)
    y=math_node('SUBTRACT',math_node('MULTIPLY',channels.outputs['Green'],2),1)
    squared=math_node('ADD',math_node('MULTIPLY',x,x),math_node('MULTIPLY',y,y))
    z=math_node('ADD',math_node('MULTIPLY',math_node('SQRT',math_node('MAXIMUM',math_node('SUBTRACT',1,squared),0)),.5),.5)
    rgb=nodes.new('ShaderNodeCombineColor');links.new(red,rgb.inputs['Red'])
    links.new(channels.outputs['Green'],rgb.inputs['Green']);links.new(z,rgb.inputs['Blue'])
    normalmap=nodes.new('ShaderNodeNormalMap');normalmap.inputs['Strength'].default_value=floats['_BumpScale']
    links.new(rgb.outputs[0],normalmap.inputs['Color']);links.new(normalmap.outputs[0],bs.inputs['Normal'])
    if name in ('Water','FountainWater'):
        # Preview only: scroll the original normal map with its original speed.
        # In game the unmodified native Water shader supplies both moving layers.
        mapping=nodes.new('ShaderNodeMapping');links.new(uv.outputs['UV'],mapping.inputs['Vector'])
        links.new(mapping.outputs[0],normal.inputs['Vector'])
        speed=colors['_BumpMap1Speed']
        for axis,key in enumerate(('r','g')):
            d=mapping.inputs['Location'].driver_add('default_value',axis).driver
            d.expression=f'frame/{bpy.context.scene.render.fps}*{speed[key]}'
    return mat

def vectors(prop):
    if prop.scalarType!=model_pb2.SCALAR_TYPE_FLOAT:raise ValueError('Expected native float property')
    return list(struct.iter_unpack('<'+'f'*prop.scalarTypeDimension,prop.data))

def transform(obj,source):
    obj.location=(-source.position.x,-source.position.z,source.position.y)
    obj.rotation_mode='QUATERNION'
    obj.rotation_quaternion=(source.rotation.w,source.rotation.x,source.rotation.z,-source.rotation.y)
    obj.scale=(source.scale.x,source.scale.z,source.scale.y)

def import_prop(definition,collection,frame_end,*,vertex_colors=True):
    name=definition['name'];model=model_pb2.Model()
    model.ParseFromString(zlib.decompress((CACHE/(definition['model']+'.timbermesh')).read_bytes()))
    root=bpy.data.objects.new(name,None);collection.objects.link(root)
    x,y,z=definition['position'];root.location=(-x,-y,z)
    root.rotation_euler=(0,0,-math.radians(definition['yaw']))
    root.scale=(definition['scale'],)*3;root['native_resource']=definition['resource']
    objects=[];animated=[]
    for index,node in enumerate(model.nodes):
        props={p.name:vectors(p) for p in node.vertexProperties}
        mesh=bpy.data.meshes.new(name+'.'+node.name)
        faces=[];indices=[]
        for mi,sub in enumerate(node.meshes):
            if len(sub.indices)%3:raise ValueError('Native triangle indices malformed')
            # Invert the official exporter's reversed triangle order when
            # returning Unity coordinates to Blender's handedness.
            faces.extend(tuple(reversed(sub.indices[i:i+3])) for i in range(0,len(sub.indices),3))
            indices.extend([mi]*(len(sub.indices)//3))
            mesh.materials.append(native_material(sub.material))
        mesh.from_pydata([(-x,-z,y) for x,y,z in props['position']],[],faces);mesh.update()
        for polygon,mi in zip(mesh.polygons,indices):polygon.material_index=mi;polygon.use_smooth=True
        mesh.normals_split_custom_set_from_vertices([(-x,-z,y) for x,y,z in props['normal']])
        if node.meshes and ('color' in props)!=vertex_colors:
            raise ValueError('Model does not match its declared vertex-color schema: '+node.name)
        if node.meshes and vertex_colors:
            color=mesh.color_attributes.new(name='NativeColor',type='FLOAT_COLOR',domain='POINT')
            for vertex,rgba in zip(color.data,props['color'],strict=True):vertex.color=rgba
        for key in ('uv0','uv1','uv2'):
            if key in props:
                uv=mesh.uv_layers.new(name=key)
                for loop in mesh.loops:uv.data[loop.index].uv=props[key][loop.vertex_index]
        obj=bpy.data.objects.new(name+'.'+node.name,mesh);collection.objects.link(obj)
        obj.parent=root if node.parent==-1 else objects[node.parent]
        obj['native_resource']=definition['resource'];obj['native_node_index']=index
        transform(obj,node);objects.append(obj)
        for clip in node.nodeAnimations:
            if clip.name!='Default' or clip.framerate!=bpy.context.scene.render.fps:
                raise ValueError('Native animation requires its original Default clip and frame rate')
            for f in range(1,frame_end+1):
                transform(obj,clip.frames[(f-1)%len(clip.frames)])
                for field in ('location','rotation_quaternion','scale'):obj.keyframe_insert(data_path=field,frame=f)
            for curve in obj.animation_data.action.fcurves:
                for key in curve.keyframe_points:key.interpolation='LINEAR'
            animated.append(obj.name)
    return animated

def surface_mesh(definition,collection,fraction):
    name=definition['name'];mesh=bpy.data.meshes.new(name)
    if definition['shape']=='SmallLiquidPlane':
        source=json.loads((CACHE/'SmallLiquidPlane.json').read_text())
        vertices=[(-x,-z,y) for x,y,z in source['vertices']]
        faces=[tuple(reversed(face)) for face in source['faces']];uvs=source['uv']
    elif definition['shape']=='Rectangle':
        vertices=[(-.5,-.5,0),(.5,-.5,0),(.5,.5,0),(-.5,.5,0)]
        faces=[(0,1,2,3)];uvs=[(0,0),(1,0),(1,1),(0,1)]
    else:raise ValueError('Unknown liquid surface shape '+definition['shape'])
    mesh.from_pydata(vertices,[],faces);mesh.update();mesh.materials.append(native_material('Water'))
    uv=mesh.uv_layers.new(name='uv0')
    for loop in mesh.loops:uv.data[loop.index].uv=uvs[loop.vertex_index]
    obj=bpy.data.objects.new(name,mesh);collection.objects.link(obj)
    x,y=definition['center'];height=definition['bottom']+(definition['top']-definition['bottom'])*fraction
    obj.location=(-x,-y,height);obj.scale=(*definition['scale'],1)
    obj.hide_render=fraction==0;obj['liquid_surface']=True
    return obj

def build_native_assembly(g,collection,frame_end,fraction=1):
    if not 0<=fraction<=1:raise ValueError('Liquid preview fill must be in [0,1]')
    animated=[]
    for definition in g.native_props:animated.extend(import_prop(definition,collection,frame_end))
    for definition in g.liquid_surfaces:surface_mesh(definition,collection,fraction)
    return animated
