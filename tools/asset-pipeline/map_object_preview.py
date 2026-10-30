"""Blender preview helpers for map objects and goods (review renders only).

Imports exported Timbermesh files (ours or cached native ones) with preview
copies of the native materials they name. Material records come from
outputs/map-objects/native/materials.json (export_map_object_references.py)
and outputs/native-civic-assets/materials.json. The preview is an
approximation of the game's shaders: albedo x colour, metallic/gloss map and
the unpacked normal map; terrain-shader materials (TerrainURP/SlopeURP) are
box-projected in world space, as the terrain shader projects them. Nothing
here is exported; the game resolves the original native materials by name.
"""
import json
import math
import struct
import sys
import zlib
from pathlib import Path

import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tools/asset-pipeline/timbermesh-plugin/timbermesh_blender_plugin'))
import model_pb2  # noqa: E402

CACHES = [ROOT / 'outputs/map-objects/native', ROOT / 'outputs/native-civic-assets']
_records = {}
for cache in CACHES:
    for name, record in json.loads((cache / 'materials.json').read_text()).items():
        _records.setdefault(name, (cache, record))
TERRAIN_SHADERS = ('Shader Graphs/TerrainURP', 'Shader Graphs/SlopeURP')

# The Radioactive Spring tint (Scripts/Radiation/RadiationMaterials.cs).
SPRING_COLOR = (0.80, 0.87, 0.10)
SPRING_EMISSION = (0.42, 0.52, 0.02)


def srgb_to_linear(c):
    return c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4


def _texture(nodes, links, cache, record, slot, vector, linear=False):
    data = record['textures'][slot]
    image = bpy.data.images.load(str(cache / data['file']), check_existing=True)
    image.colorspace_settings.name = 'Non-Color' if linear else 'sRGB'
    node = nodes.new('ShaderNodeTexImage')
    node.image = image
    links.new(vector, node.inputs['Vector'])
    return node


def material(name):
    existing = bpy.data.materials.get(name)
    if existing is not None and existing.get('df_preview'):
        return existing
    if name not in _records:
        raise KeyError(f'No cached native material record for {name}; extend export_map_object_references.py')
    cache, record = _records[name]
    shader = record.get('shader')
    colors = dict(record['properties']['m_Colors'])
    floats = dict(record['properties']['m_Floats'])
    mat = bpy.data.materials.new(name)
    mat['df_preview'] = True
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes['Principled BSDF']
    coords = nodes.new('ShaderNodeTexCoord')
    if shader in TERRAIN_SHADERS:
        # World box projection at one texture repeat per 4 tiles.
        mapping = nodes.new('ShaderNodeMapping')
        mapping.inputs['Scale'].default_value = (.25, .25, .25)
        links.new(coords.outputs['Object'], mapping.inputs['Vector'])
        slot = '_BaseAlbedoTex' if shader == 'Shader Graphs/SlopeURP' else '_SplatAlbedoTex'
        tex = _texture(nodes, links, cache, record, slot, mapping.outputs[0])
        tex.projection = 'BOX'
        tex.projection_blend = .3
        albedo = tex.outputs['Color']
    else:
        tex = _texture(nodes, links, cache, record, '_MainTex', coords.outputs['UV'])
        albedo = tex.outputs['Color']
    tint = colors.get('_Color', {'r': 1, 'g': 1, 'b': 1, 'a': 1})
    rgba = tuple(srgb_to_linear(tint[c]) for c in 'rgb') + (1,)
    multiply = nodes.new('ShaderNodeMixRGB')
    multiply.blend_type = 'MULTIPLY'
    multiply.inputs[0].default_value = 1
    links.new(albedo, multiply.inputs[1])
    multiply.inputs[2].default_value = rgba
    links.new(multiply.outputs[0], bsdf.inputs['Base Color'])
    bsdf.inputs['Metallic'].default_value = floats.get('_Metallic', 0)
    bsdf.inputs['Roughness'].default_value = 1 - floats.get('_Smoothness', floats.get('_Glossiness', .2))
    if '_MetallicGlossMap' in record['textures'] and shader not in TERRAIN_SHADERS and 'Water' not in str(shader):
        metal = _texture(nodes, links, cache, record, '_MetallicGlossMap', coords.outputs['UV'], True)
        split = nodes.new('ShaderNodeSeparateColor')
        links.new(metal.outputs['Color'], split.inputs[0])
        links.new(split.outputs['Red'], bsdf.inputs['Metallic'])
        gloss = nodes.new('ShaderNodeMath')
        gloss.operation = 'MULTIPLY'
        gloss.inputs[1].default_value = floats.get('_GlossMapScale', 1)
        links.new(metal.outputs['Alpha'], gloss.inputs[0])
        rough = nodes.new('ShaderNodeMath')
        rough.operation = 'SUBTRACT'
        rough.inputs[0].default_value = 1
        links.new(gloss.outputs[0], rough.inputs[1])
        links.new(rough.outputs[0], bsdf.inputs['Roughness'])
    if '_BumpMap' in record['textures'] and shader not in TERRAIN_SHADERS:
        normal = _texture(nodes, links, cache, record, '_BumpMap', coords.outputs['UV'], True)
        split = nodes.new('ShaderNodeSeparateColor')
        links.new(normal.outputs['Color'], split.inputs[0])

        def op(kind, a, b=None):
            node = nodes.new('ShaderNodeMath')
            node.operation = kind
            for i, value in enumerate((a, b)):
                if value is None:
                    continue
                if isinstance(value, (int, float)):
                    node.inputs[i].default_value = value
                else:
                    links.new(value, node.inputs[i])
            return node.outputs[0]
        red = op('MULTIPLY', split.outputs['Red'], normal.outputs['Alpha'])
        combine = nodes.new('ShaderNodeCombineColor')
        links.new(red, combine.inputs['Red'])
        links.new(split.outputs['Green'], combine.inputs['Green'])
        combine.inputs['Blue'].default_value = 1
        normal_map = nodes.new('ShaderNodeNormalMap')
        normal_map.inputs['Strength'].default_value = floats.get('_BumpScale', 1)
        links.new(combine.outputs[0], normal_map.inputs['Color'])
        links.new(normal_map.outputs[0], bsdf.inputs['Normal'])
    for emission_slot in ('_LightingMap', '_Emission_Map'):
        if emission_slot in record['textures']:
            emission = _texture(nodes, links, cache, record, emission_slot, coords.outputs['UV'])
            links.new(emission.outputs['Color'], bsdf.inputs['Emission Color'])
            bsdf.inputs['Emission Strength'].default_value = 1.5
    mat.diffuse_color = rgba
    return mat


def spring_material():
    existing = bpy.data.materials.get('DeepFrontierRadioactiveSpring')
    if existing is not None:
        return existing
    mat = bpy.data.materials.new('DeepFrontierRadioactiveSpring')
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Base Color'].default_value = tuple(srgb_to_linear(c) for c in SPRING_COLOR) + (1,)
    bsdf.inputs['Roughness'].default_value = .25
    bsdf.inputs['Emission Color'].default_value = tuple(srgb_to_linear(c) for c in SPRING_EMISSION) + (1,)
    bsdf.inputs['Emission Strength'].default_value = 1
    return mat


def _vectors(prop):
    return list(struct.iter_unpack('<' + 'f' * prop.scalarTypeDimension, prop.data))


def import_timbermesh(path, collection, location=(0, 0, 0), *, tint_nodes=(), tint_all=False, yaw=0.0):
    """Import every mesh node; returns (objects, stats). Unity (x, y up, z) maps to
    Blender (-x, -z, y), as the official exporter's inverse. Nodes named in
    tint_nodes (or all, with tint_all) get the radioactive spring material,
    as RadioactiveSpringVisual does in game."""
    model = model_pb2.Model()
    model.ParseFromString(zlib.decompress(Path(path).read_bytes()))
    objects, stats = [], {'triangles': 0, 'vertices': 0, 'materials': {}}
    root = bpy.data.objects.new(Path(path).stem, None)
    collection.objects.link(root)
    root.location = location
    root.rotation_euler = (0, 0, math.radians(yaw))
    made = []
    for index, node in enumerate(model.nodes):
        obj_parent = root if node.parent == -1 else made[node.parent]
        if not node.meshes:
            empty = bpy.data.objects.new(node.name, None)
            collection.objects.link(empty)
            empty.parent = obj_parent
            _transform(empty, node)
            made.append(empty)
            continue
        props = {p.name: _vectors(p) for p in node.vertexProperties if p.scalarType == model_pb2.SCALAR_TYPE_FLOAT}
        mesh = bpy.data.meshes.new(node.name)
        faces, slots = [], []
        tinted = tint_all or node.name in tint_nodes
        for slot, sub in enumerate(node.meshes):
            faces.extend(tuple(reversed(sub.indices[i:i + 3])) for i in range(0, len(sub.indices), 3))
            slots.extend([slot] * (len(sub.indices) // 3))
            mesh.materials.append(spring_material() if tinted else material(sub.material))
            stats['materials'][sub.material] = stats['materials'].get(sub.material, 0) + len(sub.indices) // 3
        mesh.from_pydata([(-x, -z, y) for x, y, z in props['position']], [], faces)
        mesh.update()
        for polygon, slot in zip(mesh.polygons, slots):
            polygon.material_index = slot
            polygon.use_smooth = True
        mesh.normals_split_custom_set_from_vertices([(-x, -z, y) for x, y, z in props['normal']])
        if 'uv0' in props:
            uv = mesh.uv_layers.new(name='uv0')
            for loop in mesh.loops:
                uv.data[loop.index].uv = props['uv0'][loop.vertex_index]
        obj = bpy.data.objects.new(node.name, mesh)
        collection.objects.link(obj)
        obj.parent = obj_parent
        _transform(obj, node)
        made.append(obj)
        objects.append(obj)
        stats['triangles'] += len(faces)
        stats['vertices'] += node.vertexCount
        stats['boundsTop'] = max(stats.get('boundsTop', -1e9), max(y for _, y, _ in props['position']) + node.position.y + location[2])
    return objects, stats


def import_native_mesh(name, material_name, collection, location=(0, 0, 0), yaw=0):
    """A cached native Unity mesh (export_map_object_references.py), e.g. a
    stockpile good model, with its native material."""
    data = json.loads((ROOT / 'outputs/map-objects/native/meshes' / f'{name}.json').read_text())
    mesh = bpy.data.meshes.new(name)
    faces = [tuple(reversed(t)) for sub in data['submeshes'] for t in sub]
    mesh.from_pydata([(-x, -z, y) for x, y, z in data['vertices']], [], faces)
    mesh.update()
    mesh.materials.append(material(material_name))
    for polygon in mesh.polygons:
        polygon.use_smooth = True
    if data['normals']:
        mesh.normals_split_custom_set_from_vertices([(-x, -z, y) for x, y, z in data['normals']])
    uv = mesh.uv_layers.new(name='uv0')
    for loop in mesh.loops:
        uv.data[loop.index].uv = data['uv0'][loop.vertex_index]
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (0, 0, math.radians(yaw))
    return obj, {'triangles': len(faces), 'vertices': len(data['vertices']), 'materials': {material_name: len(faces)},
                 'boundsTop': max(y for _, y, _ in data['vertices']) + location[2]}


def _transform(obj, source):
    obj.location = (-source.position.x, -source.position.z, source.position.y)
    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = (source.rotation.w, source.rotation.x, source.rotation.z, -source.rotation.y)
    obj.scale = (source.scale.x, source.scale.z, source.scale.y)


def ground(collection, center, size, name='PreviewGround'):
    """Native grass terrain at height 0 with faint tile lines (grid review)."""
    mesh = bpy.data.meshes.new(name)
    hx, hy = size[0] / 2, size[1] / 2
    cx, cy = center
    mesh.from_pydata([(cx - hx, cy - hy, 0), (cx + hx, cy - hy, 0), (cx + hx, cy + hy, 0), (cx - hx, cy + hy, 0)], [], [(0, 1, 2, 3)])
    obj = bpy.data.objects.new(name, mesh)
    collection.objects.link(obj)
    mat = bpy.data.materials.new(name + 'Material')
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes['Principled BSDF']
    coords = nodes.new('ShaderNodeTexCoord')
    mapping = nodes.new('ShaderNodeMapping')
    mapping.inputs['Scale'].default_value = (.125, .125, .125)
    links.new(coords.outputs['Object'], mapping.inputs['Vector'])
    cache, record = _records['Cliff']
    grass = _texture(nodes, links, cache, record, '_BaseAlbedoTex', mapping.outputs[0])
    # Tile lines: frac(x) or frac(y) within 0.012 of an integer.
    sep = nodes.new('ShaderNodeSeparateXYZ')
    links.new(coords.outputs['Object'], sep.inputs[0])
    lines = []
    for axis in ('X', 'Y'):
        wrap = nodes.new('ShaderNodeMath')
        wrap.operation = 'PINGPONG'
        wrap.inputs[1].default_value = .5
        links.new(sep.outputs[axis], wrap.inputs[0])
        less = nodes.new('ShaderNodeMath')
        less.operation = 'LESS_THAN'
        less.inputs[1].default_value = .012
        links.new(wrap.outputs[0], less.inputs[0])
        lines.append(less.outputs[0])
    either = nodes.new('ShaderNodeMath')
    either.operation = 'MAXIMUM'
    links.new(lines[0], either.inputs[0])
    links.new(lines[1], either.inputs[1])
    shade = nodes.new('ShaderNodeMixRGB')
    shade.blend_type = 'MULTIPLY'
    links.new(either.outputs[0], shade.inputs[0])
    links.new(grass.outputs['Color'], shade.inputs[1])
    shade.inputs[2].default_value = (.55, .55, .55, 1)
    links.new(shade.outputs[0], bsdf.inputs['Base Color'])
    bsdf.inputs['Roughness'].default_value = .95
    mesh.materials.append(mat)
    return obj


def setup_render(scene, resolution):
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 48
    scene.cycles.use_denoising = True
    scene.cycles.seed = 0
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    gpus = [d for d in prefs.devices if d.type == 'OPTIX' and d.name == 'NVIDIA GeForce RTX 2060']
    if len(gpus) != 1:
        raise RuntimeError('RTX 2060 OptiX device required')
    for device in prefs.devices:
        device.use = device in gpus
    scene.cycles.device = 'GPU'
    # Denoise on the GPU too: OIDN on the CPU used ~85 of the ~95 CPU-seconds of a 1200 px render.
    if not prefs.has_oidn_gpu_devices():
        raise RuntimeError('RTX 2060 OIDN GPU denoising unavailable')
    scene.cycles.denoising_use_gpu = True
    scene.render.resolution_x = scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.film_transparent = False
    scene.view_settings.view_transform = 'AgX'
    world = scene.world or bpy.data.worlds.new('PreviewWorld')
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.55, .60, .68, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .9


def rig(collection):
    cam_data = bpy.data.cameras.new('PreviewCamera')
    cam_data.type = 'ORTHO'
    cam_data.clip_start, cam_data.clip_end = .1, 400
    camera = bpy.data.objects.new('PreviewCamera', cam_data)
    collection.objects.link(camera)
    sun_data = bpy.data.lights.new('PreviewSun', 'SUN')
    sun_data.energy = 3.2
    sun_data.angle = math.radians(3)
    sun = bpy.data.objects.new('PreviewSun', sun_data)
    sun.rotation_euler = (math.radians(42), 0, math.radians(35))
    collection.objects.link(sun)
    return camera


def aim(camera, target, scale, azimuth=62, pitch=45):
    """Game-like orthographic view: the front (Blender +Y, the blueprint's
    entrance side) seen from the front-right at the game's 45 degree pitch."""
    a, p = math.radians(azimuth), math.radians(pitch)
    direction = Vector((math.cos(p) * math.cos(a), math.cos(p) * math.sin(a), math.sin(p)))
    camera.location = Vector(target) + direction * 60
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera.data.ortho_scale = scale
