"""Generate, check and export the construction stage of every Deep Frontier building.

For each generated building (construction_stage_massing.buildings(): every
TemplateCollection.Buildings.IronTeeth template with its own finished model,
less tools/construction_stages.json `authored` and `previewOnly`), this script

  1. derives the construction site from the blueprint and the finished model
     (construction_stage_massing.massing: box bays, Dirt cells, frame
     material, the vanilla ConstructionBase that fits, stage colliders);
  2. builds the stage in a fresh scene (construction_stage_geometry.build:
     native timber or metal frame and Dirt patch, explicit atlas islands);
  3. checks it: frame inside the footprint, Dirt at most `outside` beyond it,
     heights inside the block grid, only the three native stage materials,
     every UV inside its tile, the triangle ceiling, and a strict z-fighting
     audit (zfight_audit.audit, no visible conflict);
  4. exports it with the official Timbermesh exporter (merged, one node) to
     <exportRoot>/Data/<stage resource>.timbermesh and records the massing,
     triangles and export hash in the manifest.

The stages are fully generated: the generator, the blueprint and the finished
model are their source, so no Blender scene is saved. Inputs are read from
--data (default src/DeepFrontier/Data, read only); construction_stage_content.mjs
binds the exports during canonical generation.

Run (real repository; exports land in the tracked candidate folder):
  tools/asset-pipeline/blender_low.sh -b --factory-startup --python-exit-code 1 \
      --python tools/asset-pipeline/build_construction_stages.py -- --models all
  ... -- --models StoneCrusher,SteelMill [--data <absolute Data root>] [--export-root <dir>]
"""
import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import build_map_objects as kit  # noqa: E402  (reset_scene, measure, export)
import construction_stage_geometry as geometry  # noqa: E402
import construction_stage_massing as massing_module  # noqa: E402
import map_object_preview as preview  # noqa: E402
import zfight_audit  # noqa: E402

ROOT = kit.ROOT
CONFIG = massing_module.CONFIG


def frame_bounds(g):
    """Bounds of the non-Dirt vertices, in tile units (x, y, height)."""
    used = {v for face, mat in zip(g.faces, g.materials) if mat != geometry.DIRT for v in face}
    pts = [g.vertices[i] for i in used]
    # Geometry stores the exporter's source coordinates: x and y negated.
    xs = [-p[0] for p in pts]
    ys = [-p[1] for p in pts]
    zs = [p[2] for p in pts]
    return [min(xs), min(ys), min(zs)], [max(xs), max(ys), max(zs)]


def check(m, g, report, audit):
    problems = []
    w, d, h = m['size']
    out = CONFIG['dirt']['outside']
    flo, fhi = frame_bounds(g)
    if flo[0] < -1e-4 or flo[1] < -1e-4 or fhi[0] > w + 1e-4 or fhi[1] > d + 1e-4:
        problems.append(f'frame {flo}..{fhi} leaves the {w}x{d} footprint')
    lo, hi = report['boundsMin'], report['boundsMax']
    if lo[0] < -out - 1e-4 or lo[1] < -out - 1e-4 or hi[0] > w + out + 1e-4 or hi[1] > d + out + 1e-4:
        problems.append(f'stage {lo}..{hi} reaches more than {out} beyond the footprint')
    if lo[2] < -m['baseZ'] - 1e-4 or hi[2] > h - m['baseZ'] + 1e-4:
        problems.append(f'heights {lo[2]}..{hi[2]} leave the block grid {-m["baseZ"]}..{h - m["baseZ"]}')
    if report['triangles'] > CONFIG['triangleCeiling']:
        problems.append(f'{report["triangles"]} triangles exceed the ceiling {CONFIG["triangleCeiling"]}')
    extra = sorted(set(report['materials']) - set(CONFIG['materials']))
    if extra:
        problems.append(f'materials outside the native stage set: {extra}')
    if 'Dirt' not in report['materials']:
        problems.append('no Dirt patch')
    if report['uvErrorCount']:
        problems.append(f'{report["uvErrorCount"]} UVs outside 0..1, e.g. {report["uvErrors"][:3]}')
    if audit['visibleConflicts']:
        problems.append(f'{audit["visibleConflicts"]} visible z-fighting candidates, e.g. '
                        f'{[(c["a"]["face"], c["b"]["face"], c["center"]) for c in audit["conflicts"][:3]]}')
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True, help="comma-separated building ids, or 'all'")
    parser.add_argument('--data', default=str(ROOT / 'src/DeepFrontier/Data'), help='Data tree to read blueprints and finished models from')
    parser.add_argument('--export-root', default=str(ROOT / CONFIG['exportRoot']))
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    data = Path(cli.data)
    export_root = Path(cli.export_root)
    if not data.is_absolute() or not data.is_dir():
        raise SystemExit(f'--data must be an existing absolute Data folder: {data}')
    every = massing_module.buildings(data)
    generated = [b for b in every if b['kind'] == 'generated']
    wanted = [b['id'] for b in generated] if cli.models == 'all' else cli.models.split(',')
    by_id = {b['id']: b for b in every}
    unknown = [i for i in wanted if i not in by_id]
    if unknown:
        raise SystemExit(f'Not Deep Frontier buildings in {data}: {unknown}')
    skipped = [i for i in wanted if by_id[i]['kind'] != 'generated']
    if skipped:
        raise SystemExit(f'Not generated here (tools/construction_stages.json authored/previewOnly): {skipped}')
    manifest_path = export_root / Path(CONFIG['manifest']).relative_to(CONFIG['exportRoot'])
    manifest = json.loads(manifest_path.read_text(encoding='utf-8')) if manifest_path.is_file() else {'stages': {}}
    if cli.models == 'all':
        manifest['stages'] = {}
    failures = {}
    started = time.monotonic()
    for ident in wanted:
        m = massing_module.massing(by_id[ident], data)
        scene = kit.reset_scene()
        collection = bpy.data.collections.new(f'{ident}.ConstructionStage0')
        scene.collection.children.link(collection)
        materials = [preview.material(name) for name in geometry.MATERIALS]
        g = geometry.build(m)
        obj = g.build(collection, materials, bevel=0, uv_profile='civic-native')
        report = kit.measure([obj])
        audit = zfight_audit.audit([obj], .0005, .0005)
        problems = check(m, g, report, audit)
        if problems:
            failures[ident] = problems
            print('CONSTRUCTION STAGE FAIL', ident, json.dumps(problems), flush=True)
            continue
        path = export_root / 'Data' / f"{m['stage']}.timbermesh"
        kit.export(collection, path, merge=True)
        manifest['stages'][ident] = {**m, 'triangles': report['triangles'], 'materials': report['materials'],
                                     'export': path.relative_to(export_root).as_posix(),
                                     'exportSha256': hashlib.sha256(path.read_bytes()).hexdigest()}
        print('CONSTRUCTION STAGE', ident, json.dumps({'frame': m['frame'], 'boxes': len(m['boxes']), 'cut': m['cut'],
              'base': m['base']['name'], 'triangles': report['triangles']}), flush=True)
    manifest['generator'] = 'tools/asset-pipeline/build_construction_stages.py'
    manifest['stages'] = dict(sorted(manifest['stages'].items()))
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1) + '\n', encoding='utf-8')
    print('CONSTRUCTION STAGES', json.dumps({'built': len(wanted) - len(failures), 'failed': len(failures),
          'seconds': round(time.monotonic() - started, 1)}), flush=True)
    if failures:
        raise SystemExit(f'Construction stages failed: {sorted(failures)}')


if __name__ == '__main__':
    main()
