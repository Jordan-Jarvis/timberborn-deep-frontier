"""Source checks for the bridge studies (bridge_geometry.py) on saved scenes.

Same contracts as validate_structural_sources.py, extended for bridges:
  - meshes stay in their module (arch railings may rise to RAIL_TOP in the
    walking layer above the 1-layer module);
  - flush support: the deck top is exactly z = 1.0 at 25 samples per cell;
  - end-cell support: the end cells are solid down to the ground plane;
  - open middles: nothing below the arch intrados springing band / truss
    floor girders under the middle cells;
  - truss passage: nothing between z 1.01 and TRUSS_CLEAR for x 0.3..1.7.

Run (Blender):
  blender.exe -b --python-exit-code 1 --python tools/asset-pipeline/validate_bridge_sources.py -- \
      --blend-dir <dir with <Ident>-ReferenceStudy.blend> [--models A,B] [--report out.json]
"""
import argparse
import json
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, str(Path(__file__).parent))
from bridge_geometry import BRIDGE_SIZES, DECK_TOP, RAIL_TOP, TRUSS_CLEAR, SUPPORT
from native_uv_contract import valid_native_uv

NATIVE_CHECKED = (0, 1, 2, 3, 7, 27, 28, 29)


def check(ident, blend):
    bpy.ops.wm.open_mainfile(filepath=str(blend))
    w, h, height = BRIDGE_SIZES[ident]
    meshes = [o for o in bpy.data.collections[ident + '.ReferenceStudy'].objects if o.type == 'MESH']
    vertices, faces, uv_corners = [], [], 0
    for obj in meshes:
        assert obj.animation_data is None, (ident, 'Passive structure must be static')
        off = len(vertices)
        vertices.extend(obj.matrix_world @ v.co for v in obj.data.vertices)
        faces.extend(tuple(off + i for i in f.vertices) for f in obj.data.polygons)
        assert len(obj.material_slots) == 32 and obj.data.uv_layers, ident
        used = {f.material_index for f in obj.data.polygons}
        assert used <= set(NATIVE_CHECKED), (ident, 'Non-native material slots', sorted(used - set(NATIVE_CHECKED)))
        for f in obj.data.polygons:
            for i in f.loop_indices:
                assert valid_native_uv(obj.material_slots[f.material_index].material.name,
                                       obj.data.uv_layers.active.data[i].uv), ident
                uv_corners += 1
    tree = BVHTree.FromPolygons(vertices, faces)
    arch = ident.startswith('ConcreteArch')
    top = RAIL_TOP if arch else height
    assert vertices and all(-w - .001 <= v.x <= .001 and -h - .001 <= v.y <= .001 and -.001 <= v.z <= top + .001
                            for v in vertices), (ident, 'Mesh leaves its module')
    # Flush deck support (Blender x, y are the negated art x, y).
    support = 0
    for x in range(w):
        for y in range(h):
            for dx in (.1, .3, .5, .7, .9):
                for dy in (.1, .3, .5, .7, .9):
                    hit = tree.ray_cast(Vector((-x - dx, -y - dy, DECK_TOP + .1)), Vector((0, 0, -1)), .2)[0]
                    assert hit is not None and abs(hit.z - DECK_TOP) < .001, (ident, x, y, dx, dy, 'Missing flush support')
                    support += 1
    # End cells solid to the ground: a ray from below meets the abutment base.
    ground = 0
    for gx, gy, _ in SUPPORT[ident]['groundCells']:
        for dx in (.2, .5, .8):
            for dy in (.2, .5, .8):
                hit = tree.ray_cast(Vector((-gx - dx, -gy - dy, -.05)), Vector((0, 0, 1)), .1)[0]
                assert hit is not None and abs(hit.z) < .002, (ident, gx, gy, 'End cell not founded on the ground')
                ground += 1
    # Open middles: clear under the middle cells.
    open_samples = 0
    clear_below = .2 if arch else .55
    xs = (.5,) if arch else (.25, .5, .75, 1.25, 1.5, 1.75)
    for y in range(1, h - 1):
        for x in xs:
            for dy in (.3, .5, .7):
                hit = tree.ray_cast(Vector((-x, -y - dy, .005)), Vector((0, 0, 1)), clear_below)[0]
                assert hit is None, (ident, x, y + dy, 'Middle cell not open below', hit)
                open_samples += 1
    # Truss walking passage.
    passage = 0
    if not arch:
        for y in range(h):
            for x in (.3, .5, .7, 1.0, 1.3, 1.5, 1.7):
                for dy in (.1, .5, .9):
                    hit = tree.ray_cast(Vector((-x, -y - dy, DECK_TOP + .01)), Vector((0, 0, 1)),
                                        TRUSS_CLEAR - DECK_TOP - .01)[0]
                    assert hit is None, (ident, x, y + dy, 'Obstruction in the truss walkway', hit)
                    passage += 1
    return dict(model=ident, vertices=len(vertices), supportSamples=support, groundSamples=ground,
                openBelowSamples=open_samples, passageSamples=passage, nativeAtlasUvCorners=uv_corners)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--blend-dir', type=Path, required=True)
    parser.add_argument('--models', default=','.join(BRIDGE_SIZES))
    parser.add_argument('--report', type=Path)
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    results = [check(m, cli.blend_dir / f'{m}-ReferenceStudy.blend') for m in cli.models.split(',')]
    report = dict(scope='Saved Blender geometry; native placement and traversal require separate tests',
                  models=results)
    if cli.report:
        cli.report.write_text(json.dumps(report, indent=2) + '\n')
    print('BRIDGE SOURCE CHECKS', json.dumps(report))


if __name__ == '__main__':
    main()
