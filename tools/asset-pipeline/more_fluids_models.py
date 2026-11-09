"""Build, check, save and export the More Fluids models.

For each selected id of more_fluids_designs.MODELS this script authors the
geometry into a fresh scene, checks it against its contract (every vertex
inside the blueprint's occupied cells, height, triangle ceiling, only
materials the model's faction collection loads, UV islands inside their
atlas tiles, animation nodes), saves the source scene
src/MoreFluids/Art/Source/<Id>-ReferenceStudy.blend (collection
<Id>.ReferenceStudy; textures are never packed) and exports it with the
official Timbermesh exporter to src/MoreFluids/Data/<resource>.timbermesh.

Animated parts are '#<Name>Animated' nodes with one looping 'Default' clip of
100 frames at 24 fps, as the vanilla pumps ship. The worker slot is
'#Slot#Entrance' (TransformSlotInitializerSpec SlotKeyword 'Entrance').

Run (real repository only; scenes and exports are written there):
  blender -b --factory-startup --python-exit-code 1 --python more_fluids_models.py -- --models all
  ... -- --models MoreFluidsFluidExtractor.Folktails --no-export
"""
import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import map_object_preview as preview  # noqa: E402
import more_fluids_designs as designs  # noqa: E402
from more_fluids_geometry import REGISTERED_COMMON  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PLUGIN = ROOT / 'tools/asset-pipeline/timbermesh-plugin'
sys.path[:0] = [str(PLUGIN), str(PLUGIN / 'timbermesh_blender_plugin')]
from timbermesh_blender_plugin import timbermesh_exporter  # noqa: E402

NATIVE = ROOT / 'outputs/more-fluids-art/native'
for _name, _record in json.loads((NATIVE / 'materials.json').read_text()).items():
    preview._records.setdefault(_name, (NATIVE, _record))

SOURCE = ROOT / 'src/MoreFluids/Art/Source'
DATA = ROOT / 'src/MoreFluids/Data'
REPORTS = ROOT / 'outputs/more-fluids-art/reports'
COLLECTIONS = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/MaterialCollections'
FRAMES = 100
FPS = 24
WORLD_KINDS = {'world', 'explicit'}


def collection_materials(name):
    data = json.loads((COLLECTIONS / f'MaterialCollection.{name}.blueprint.json').read_text(encoding='utf-8-sig'))
    return {path.rsplit('/', 1)[1] for path in data['MaterialCollectionSpec']['Materials']}


def allowed_materials(faction):
    common = collection_materials('Common')
    if faction is None:
        return common | set(REGISTERED_COMMON)
    return common | collection_materials(faction)


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.fps = FPS
    scene.frame_start, scene.frame_end = 1, FRAMES
    return scene


def make_object(part, collection):
    mesh = bpy.data.meshes.new(part.name)
    verts = [(-v.x, -v.y, v.z) for v in part.vertices]
    mesh.from_pydata(verts, [], part.faces)
    mesh.update()
    names = list(dict.fromkeys(part.materials))
    for name in names:
        mesh.materials.append(preview.material(name))
    uv = mesh.uv_layers.new(name='UVMap')
    for poly, material, uvs, smooth in zip(mesh.polygons, part.materials, part.uvs, part.smooth):
        poly.material_index = names.index(material)
        poly.use_smooth = smooth
        for loop, coord in zip(poly.loop_indices, uvs, strict=True):
            uv.data[loop].uv = coord
    # Weld coincident corners so smooth faces share normals; flat faces stay flat.
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(part.name, mesh)
    collection.objects.link(obj)
    obj.location = (-part.pivot.x, -part.pivot.y, part.pivot.z)
    return obj


def animate(obj, animation):
    kind, axis, amount = animation
    index = 'xyz'.index(axis)
    obj.rotation_mode = 'XYZ'
    if kind == 'rotate':
        for frame, turn in ((1, 0.0), (FRAMES + 1, amount)):
            value = list(obj.rotation_euler)
            value[index] = 2 * math.pi * turn
            obj.rotation_euler = value
            obj.keyframe_insert('rotation_euler', index=index, frame=frame)
    elif kind in ('bob', 'rock'):
        base = obj.location[index] if kind == 'bob' else 0.0
        for step in range(9):
            frame = 1 + step * FRAMES / 8
            offset = math.sin(2 * math.pi * step / 8) * amount
            if kind == 'bob':
                value = list(obj.location)
                value[index] = base + offset
                obj.location = value
                obj.keyframe_insert('location', index=index, frame=frame)
            else:
                value = list(obj.rotation_euler)
                value[index] = math.radians(offset)
                obj.rotation_euler = value
                obj.keyframe_insert('rotation_euler', index=index, frame=frame)
    else:
        raise ValueError(f'Unknown animation {kind}')
    action = obj.animation_data.action
    curves = action.fcurves if hasattr(action, 'fcurves') else [c for layer in action.layers for strip in layer.strips
                                                                  for bag in strip.channelbags for c in bag.fcurves]
    for curve in curves:
        for point in curve.keyframe_points:
            point.interpolation = 'LINEAR' if kind == 'rotate' else 'BEZIER'
    if kind == 'bob':
        obj.location[index] = base
    else:
        obj.rotation_euler[index] = 0


def build(ident, spec, collection):
    kit = spec['builder']()
    root_part = kit.parts[kit.name]
    root = make_object(root_part, collection)
    objects = [root]
    for name, part in kit.parts.items():
        if part is root_part:
            continue
        if not name.startswith('#') or not name.endswith('Animated'):
            raise ValueError(f'{ident}: extra node {name} must be a #...Animated part')
        obj = make_object(part, collection)
        obj.parent = root
        animate(obj, part.animation)
        objects.append(obj)
    for name, position, yaw in kit.empties:
        empty = bpy.data.objects.new(name, None)
        collection.objects.link(empty)
        empty.parent = root
        empty.location = (-position[0], -position[1], position[2])
        empty.rotation_euler = (0, 0, math.radians(yaw))
    return kit, objects


def inside(point, boxes, tol=1e-4):
    x, y, z = point
    return any(b[0] - tol <= x <= b[3] + tol and b[1] - tol <= y <= b[4] + tol and b[2] - tol <= z <= b[5] + tol
               for b in boxes)


def check(ident, spec, kit, faction):
    problems = []
    tris = kit.triangles()
    if tris > spec['triangles']:
        problems.append(f'{ident}: {tris} triangles exceed the ceiling {spec["triangles"]}')
    lo, hi = kit.bounds()
    if hi.z > spec['maxHeight'] + 1e-4:
        problems.append(f'{ident}: top {hi.z:.3f} above {spec["maxHeight"]}')
    outside = []
    used = {}
    uv_errors = []
    world_materials = {kit.palette[k][0] for k in kit.palette if kit.palette[k][1] in WORLD_KINDS}
    for part in kit.parts.values():
        swing = 0.0
        if part.animation and part.animation[0] == 'bob':
            swing = part.animation[2]
        for face, material, uvs in zip(part.faces, part.materials, part.uvs):
            used[material] = used.get(material, 0) + len(face) - 2
            for vi in face:
                p = part.vertices[vi] + part.pivot
                for dz in ((-swing, swing) if swing else (0,)):
                    if not inside((p.x, p.y, p.z + dz), spec['allowed']):
                        outside.append((part.name, round(p.x, 3), round(p.y, 3), round(p.z + dz, 3)))
            if material not in world_materials:
                for u, v in uvs:
                    if not (-1e-6 <= u <= 1 + 1e-6 and -1e-6 <= v <= 1 + 1e-6):
                        uv_errors.append((part.name, material, round(u, 3), round(v, 3)))
        if part.animation and part.animation[0] in ('rotate', 'rock'):
            # A rotating part sweeps its whole radius about the pivot.
            axis = 'xyz'.index(part.animation[1])
            radius = max(math.hypot(*[v[i] for i in range(3) if i != axis]) for v in part.vertices)
            p = part.pivot
            for a in range(16):
                ang = 2 * math.pi * a / 16
                d = [0, 0, 0]
                others = [i for i in range(3) if i != axis]
                d[others[0]] = math.cos(ang) * radius
                d[others[1]] = math.sin(ang) * radius
                q = (p.x + d[0], p.y + d[1], p.z + d[2])
                if not inside(q, spec['allowed']):
                    outside.append((part.name + ' sweep', *[round(c, 3) for c in q]))
    if outside:
        problems.append(f'{ident}: {len(outside)} vertices outside the occupied cells, e.g. {outside[:4]}')
    extra = sorted(set(used) - allowed_materials(faction))
    if extra:
        problems.append(f'{ident}: materials the {faction or "Common"} collections do not load: {extra}')
    if uv_errors:
        problems.append(f'{ident}: {len(uv_errors)} atlas UVs outside 0..1, e.g. {uv_errors[:3]}')
    report = {'triangles': tris, 'materials': dict(sorted(used.items())),
              'boundsMin': [round(c, 4) for c in lo], 'boundsMax': [round(c, 4) for c in hi],
              'nodes': [kit.name] + [n for n in kit.parts if n != kit.name] + [e[0] for e in kit.empties]}
    return problems, report


def export(collection, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = timbermesh_exporter.ExportSettings(bpy.context, False, True, False)
    timbermesh_exporter.Exporter.export_collection(collection, str(path), settings)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True, help="comma-separated ids of more_fluids_designs.MODELS, or 'all'")
    parser.add_argument('--no-export', action='store_true')
    parser.add_argument('--no-save', action='store_true')
    parser.add_argument('--export-root', help='write exports here instead of src/MoreFluids/Data (previews)')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    names = list(designs.MODELS) if cli.models == 'all' else cli.models.split(',')
    unknown = [n for n in names if n not in designs.MODELS]
    if unknown:
        raise SystemExit(f'Unknown model ids: {unknown}')
    data = Path(cli.export_root) if cli.export_root else DATA
    REPORTS.mkdir(parents=True, exist_ok=True)
    problems = []
    for ident in names:
        spec = designs.MODELS[ident]
        reset_scene()
        study = bpy.data.collections.new(f'{ident}.ReferenceStudy')
        bpy.context.scene.collection.children.link(study)
        kit, objects = build(ident, spec, study)
        found, report = check(ident, spec, kit, spec['faction'])
        problems += found
        if not cli.no_save:
            SOURCE.mkdir(parents=True, exist_ok=True)
            scene_path = SOURCE / f'{ident}-ReferenceStudy.blend'
            for image in bpy.data.images:
                if image.packed_file:
                    raise SystemExit(f'{ident}: image {image.name} is packed; scenes keep textures external')
            bpy.ops.wm.save_as_mainfile(filepath=str(scene_path), compress=True)
            report['sourceScene'] = scene_path.relative_to(ROOT).as_posix()
            report['sourceSha256'] = sha(scene_path)
        if not cli.no_export and not found:
            path = data / (spec['resource'] + '.timbermesh')
            export(study, path)
            report['export'] = path.as_posix()
            report['exportSha256'] = sha(path)
        (REPORTS / f'{ident}.json').write_text(json.dumps(report, indent=1) + '\n')
        print('MORE FLUIDS MODEL', ident, json.dumps({k: report[k] for k in ('triangles', 'boundsMin', 'boundsMax')}),
              json.dumps(report['materials']), flush=True)
    if problems:
        raise SystemExit('Contract failures:\n  ' + '\n  '.join(problems))


if __name__ == '__main__':
    main()
