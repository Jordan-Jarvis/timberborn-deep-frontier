"""Build, check, save and export the Deep Frontier map-object and pile-good models.

For each selected model of tools/map_objects.json this script authors the
geometry (map_objects_geometry.py) into a fresh scene, checks it against the
contract (footprint bounds, height band, triangle ceiling, native material
set, UV islands inside their atlas tiles, glow node), saves the source scene
src/DeepFrontier/Art/Source/<Id>-ReferenceStudy.blend (collection
<Id>.ReferenceStudy, export child <Id>.Model) and exports it with the official
Timbermesh exporter into the candidate tree outputs/mapobjects-integration
(Data/<resource>.timbermesh for map objects, AssetBundles/Resources/<mesh>
.timbermesh for pile goods). Promotion into src/DeepFrontier is separate.

Run (real repository only; scenes and exports are written there):
  blender -b --factory-startup --python-exit-code 1 --python build_map_objects.py -- --models all
  ... -- --models DeepOreVein,HumanRecordCache --no-export
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
import map_objects_geometry as geometry  # noqa: E402
import map_object_preview as preview  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
CONTRACT = json.loads((ROOT / 'tools/map_objects.json').read_text(encoding='utf-8'))
PLUGIN = ROOT / 'tools/asset-pipeline/timbermesh-plugin'
sys.path[:0] = [str(PLUGIN), str(PLUGIN / 'timbermesh_blender_plugin')]
from timbermesh_blender_plugin import timbermesh_exporter  # noqa: E402

SOURCE = ROOT / 'src/DeepFrontier/Art/Source'
EXPORT = ROOT / CONTRACT['exportRoot']
SEAMLESS = {'WaterSource', 'UndergroundRuinsCliff'}


def good_entries():
    """(scene id, mesh name, resource, triangle ceiling) for every pile mesh."""
    out = []
    for good, spec in CONTRACT['goods'].items():
        if good == 'note':
            continue
        for resource, ceiling in zip((spec['primary'], spec['secondary']), spec['triangles']):
            mesh = resource.rsplit('/', 1)[1]
            out.append((f'StockpileGood{mesh}', mesh, resource, ceiling, spec))
    return out


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.frame_start, scene.frame_end = 1, 1
    scene.render.fps = 30
    return scene


def study_collections(scene, ident):
    study = bpy.data.collections.new(f'{ident}.ReferenceStudy')
    scene.collection.children.link(study)
    model = bpy.data.collections.new(f'{ident}.Model')
    study.children.link(model)
    return study, model


def build_builders(builders, collection):
    objects = []
    for builder in builders:
        g, names = builder.geometry()
        materials = [preview.material(name) for name in names]
        objects.append(g.build(collection, materials, bevel=0, uv_profile='civic-native'))
    return objects


def measure(objects):
    graph = bpy.context.evaluated_depsgraph_get()
    lo = Vector((1e9, 1e9, 1e9))
    hi = -lo
    triangles, materials, uv_errors = 0, {}, []
    for obj in objects:
        evaluated = obj.evaluated_get(graph)
        mesh = evaluated.to_mesh()
        mesh.calc_loop_triangles()
        triangles += len(mesh.loop_triangles)
        uv = mesh.uv_layers.active.data
        for poly in mesh.polygons:
            name = mesh.materials[poly.material_index].name
            materials[name] = materials.get(name, 0) + len(poly.vertices) - 2
            if name in SEAMLESS:
                continue
            for li in poly.loop_indices:
                u, v = uv[li].uv
                if not (-1e-6 <= u <= 1 + 1e-6 and -1e-6 <= v <= 1 + 1e-6):
                    uv_errors.append(f'{obj.name}/{poly.index} {name} uv {u:.3f},{v:.3f}')
        for vertex in mesh.vertices:
            w = obj.matrix_world @ vertex.co
            lo = Vector(map(min, lo, w))
            hi = Vector(map(max, hi, w))
        evaluated.to_mesh_clear()
    # Source coordinates are the exporter's: x and y negated tile units.
    tile_lo = (-hi.x, -hi.y, lo.z)
    tile_hi = (-lo.x, -lo.y, hi.z)
    return {'triangles': triangles, 'materials': materials, 'boundsMin': [round(v, 4) for v in tile_lo],
            'boundsMax': [round(v, 4) for v in tile_hi], 'uvErrors': uv_errors[:20], 'uvErrorCount': len(uv_errors)}


def allowed_materials():
    common = json.loads((ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/MaterialCollections/MaterialCollection.Common.blueprint.json')
                        .read_text(encoding='utf-8-sig'))['MaterialCollectionSpec']['Materials']
    names = {path.rsplit('/', 1)[1] for path in common}
    names |= {'BaseMetal.IronTeeth', 'PaintedMetal.IronTeeth', 'Plaster_Orange.IronTeeth', 'Plaster_White.IronTeeth'}
    return names


def check(ident, report, spec, *, footprint, height, min_z, ceiling, allowed):
    problems = []
    lo, hi = report['boundsMin'], report['boundsMax']
    if footprint is not None:
        w, d = footprint
        if lo[0] < -1e-4 or lo[1] < -1e-4 or hi[0] > w + 1e-4 or hi[1] > d + 1e-4:
            problems.append(f'{ident}: bounds {lo}..{hi} leave the {w}x{d} footprint')
    if hi[2] > height + 1e-4:
        problems.append(f'{ident}: top {hi[2]} above the declared maxHeight {height}')
    if lo[2] < min_z - 1e-4:
        problems.append(f'{ident}: bottom {lo[2]} below the declared minZ {min_z}')
    if report['triangles'] > ceiling:
        problems.append(f'{ident}: {report["triangles"]} triangles exceed the ceiling {ceiling}')
    extra = sorted(set(report['materials']) - allowed)
    if extra:
        problems.append(f'{ident}: materials outside MaterialCollection.Common and DeepFrontierMapResources: {extra}')
    if report['uvErrorCount']:
        problems.append(f'{ident}: {report["uvErrorCount"]} atlas UVs outside 0..1, e.g. {report["uvErrors"][:3]}')
    return problems


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def export(collection, path, merge):
    path.parent.mkdir(parents=True, exist_ok=True)
    settings = timbermesh_exporter.ExportSettings(bpy.context, merge, True, False)
    timbermesh_exporter.Exporter.export_collection(collection, str(path), settings)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True, help="comma-separated ids from tools/map_objects.json, 'goods', or 'all'")
    parser.add_argument('--no-export', action='store_true')
    parser.add_argument('--no-save', action='store_true')
    parser.add_argument('--export-root', help='write exports and the report here instead (scratch previews)')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    global EXPORT
    if cli.export_root:
        EXPORT = Path(cli.export_root)
    names = cli.models.split(',')
    models = list(CONTRACT['models']) if 'all' in names else [n for n in names if n in CONTRACT['models']]
    goods = good_entries() if ('all' in names or 'goods' in names) else [e for e in good_entries() if e[0] in names]
    unknown = set(names) - set(CONTRACT['models']) - {e[0] for e in good_entries()} - {'all', 'goods'}
    if unknown:
        raise SystemExit(f'Unknown model ids: {sorted(unknown)}')
    allowed = allowed_materials()
    problems, reports = [], {}
    for ident in models:
        spec = CONTRACT['models'][ident]
        scene = reset_scene()
        study, model = study_collections(scene, ident)
        built = geometry.MODELS[ident]()
        builders = built if isinstance(built, tuple) else (built,)
        objects = build_builders(builders, model)
        report = measure(objects)
        report['objects'] = [o.name for o in objects]
        if spec.get('glowNode') and spec['glowNode'] not in report['objects']:
            problems.append(f'{ident}: glow node {spec["glowNode"]} missing')
        w, d, _ = spec['size']
        problems += check(ident, report, spec, footprint=(w, d), height=spec['maxHeight'], min_z=spec['minZ'],
                          ceiling=spec['triangles'], allowed=allowed)
        scene_path = SOURCE / f'{ident}-ReferenceStudy.blend'
        if not cli.no_save:
            bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
            report['sourceScene'] = str(scene_path.relative_to(ROOT)).replace('\\', '/')
            report['sourceSha256'] = sha(scene_path)
        if not cli.no_export:
            path = EXPORT / 'Data' / (spec['resource'] + '.timbermesh')
            export(model, path, merge=not spec.get('glowNode'))
            report['export'] = path.as_posix()
            report['exportSha256'] = sha(path)
        reports[ident] = report
        print('MAP OBJECT', ident, json.dumps({k: report[k] for k in ('triangles', 'materials', 'boundsMin', 'boundsMax')}), flush=True)
    good_builders = geometry.good_models()
    for scene_id, mesh, resource, ceiling, spec in goods:
        scene = reset_scene()
        study, model = study_collections(scene, scene_id)
        objects = build_builders((good_builders[mesh],), model)
        report = measure(objects)
        lo, hi = report['boundsMin'], report['boundsMax']
        half = spec['itemLength'] / 2
        # Centred on the origin across the cell and hanging below it by one level.
        if lo[0] < -half - 1e-3 or hi[0] > half + 1e-3 or hi[2] > 1e-4 or lo[2] < -spec['levelHeight'] - 1e-4:
            problems.append(f'{scene_id}: bounds {lo}..{hi} do not hang one level below the origin within the item length')
        if report['triangles'] > ceiling:
            problems.append(f'{scene_id}: {report["triangles"]} triangles exceed {ceiling}')
        if set(report['materials']) != {'BeaverCarryingModels'}:
            problems.append(f'{scene_id}: pile meshes use only the native goods atlas, not {sorted(report["materials"])}')
        if report['uvErrorCount']:
            problems.append(f'{scene_id}: atlas UVs outside 0..1')
        if any(o.location.length > 1e-9 or o.rotation_euler.to_quaternion().angle > 1e-9 for o in objects):
            problems.append(f'{scene_id}: pile mesh objects must sit untransformed at the origin (the Unity Mesh asset drops node transforms)')
        scene_path = SOURCE / f'{scene_id}-ReferenceStudy.blend'
        if not cli.no_save:
            bpy.ops.wm.save_as_mainfile(filepath=str(scene_path))
            report['sourceScene'] = str(scene_path.relative_to(ROOT)).replace('\\', '/')
            report['sourceSha256'] = sha(scene_path)
        if not cli.no_export:
            path = EXPORT / 'AssetBundles/Resources' / (resource + '.timbermesh')
            export(model, path, merge=True)
            report['export'] = path.as_posix()
            report['exportSha256'] = sha(path)
        reports[scene_id] = report
        print('PILE GOOD', scene_id, json.dumps({k: report[k] for k in ('triangles', 'boundsMin', 'boundsMax')}), flush=True)
    EXPORT.mkdir(parents=True, exist_ok=True)
    record = EXPORT / 'build-report.json'
    previous = json.loads(record.read_text()) if record.is_file() else {}
    previous.update(reports)
    record.write_text(json.dumps(previous, indent=1) + '\n')
    if problems:
        print('\n'.join('FAIL ' + p for p in problems))
        raise SystemExit(f'Map object build failed ({len(problems)})')
    print('MAP OBJECTS BUILT', len(reports), flush=True)


if __name__ == '__main__':
    main()
