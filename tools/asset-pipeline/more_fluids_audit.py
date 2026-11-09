"""Z-fighting and mesh-cost audits of the saved More Fluids source scenes.

Runs the repository's own checks on src/MoreFluids/Art/Source/<Id>-ReferenceStudy.blend:
  - zfight_audit.audit (near-coplanar overlapping triangles, exterior
    visibility rays), on frames 1 and 51 so animated parts are checked at
    two poses; fails on any visible conflict;
  - the audit_mesh_budget.py measurement (evaluated triangles, vertices,
    materials per object).
The hidden-geometry audit runs through its own client:
  blender -b --python-exit-code 1 --python audit_hidden_geometry.py --
      --models <Id> --blend-dir src/MoreFluids/Art/Source --terrain-z 0 --out outputs/more-fluids-art/hidden

Writes outputs/more-fluids-art/audit/<Id>.json.

Run: blender -b --factory-startup --python-exit-code 1 --python more_fluids_audit.py -- --models A,B
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy

sys.path.insert(0, str(Path(__file__).parent))
import zfight_audit  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'src/MoreFluids/Art/Source'
OUT = ROOT / 'outputs/more-fluids-art/audit'


def mesh_cost(objects):
    deps = bpy.context.evaluated_depsgraph_get()
    rows = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        evaluated = obj.evaluated_get(deps)
        mesh = evaluated.to_mesh()
        try:
            mesh.calc_loop_triangles()
            rows.append({'name': obj.name, 'triangles': len(mesh.loop_triangles), 'vertices': len(mesh.vertices),
                         'materials': len({p.material_index for p in mesh.polygons})})
        finally:
            evaluated.to_mesh_clear()
    return {'triangles': sum(r['triangles'] for r in rows), 'vertices': sum(r['vertices'] for r in rows),
            'meshObjects': len(rows), 'objects': rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    parser.add_argument('--frames', default='1,51')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    OUT.mkdir(parents=True, exist_ok=True)
    failed = []
    for ident in cli.models.split(','):
        path = SOURCE / f'{ident}-ReferenceStudy.blend'
        report = {'model': ident, 'sourceScene': path.relative_to(ROOT).as_posix(),
                  'sourceSha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'frames': {}}
        for frame in [int(f) for f in cli.frames.split(',')]:
            bpy.ops.wm.open_mainfile(filepath=str(path))
            bpy.context.scene.frame_set(frame)
            bpy.context.view_layer.update()
            objects = list(bpy.data.collections[ident + '.ReferenceStudy'].all_objects)
            z = zfight_audit.audit(objects, .0005, .0005)
            report['frames'][frame] = {'visibleConflicts': z['visibleConflicts'], 'occludedConflicts': z['occludedConflicts'],
                                       'examples': [c for c in z['conflicts'] if c['visible']][:5]}
            if frame == 1:
                report['meshCost'] = mesh_cost(objects)
            if z['visibleConflicts']:
                failed.append(f'{ident} frame {frame}: {z["visibleConflicts"]} visible conflicts')
        (OUT / f'{ident}.json').write_text(json.dumps(report, indent=1, default=str) + '\n')
        print('MORE FLUIDS AUDIT', ident, json.dumps({f: {k: v for k, v in r.items() if k != 'examples'}
                                                      for f, r in report['frames'].items()}),
              'triangles', report['meshCost']['triangles'], flush=True)
    if failed:
        raise SystemExit('Visible depth conflicts:\n  ' + '\n  '.join(failed))


if __name__ == '__main__':
    main()
