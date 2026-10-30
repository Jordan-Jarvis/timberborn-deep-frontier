"""Register the vanilla smoke/steam mouths of the civic, industrial and
research buildings for tools/vanilla_smoke.mjs and the smog module.

The authored geometry records each mouth with lategame_kit.emitter (civic
chimney(emits=...), the kiln's machinery chimney, the laboratory's
stack(emits=...)); emitters add no geometry, so the saved scenes and their
exports are unchanged. This runs the authored geometry without building a
scene (as register_grocery_market.py does), converts each mouth into the
native grid frame of the building registration (layout origin: native =
artwork + origin, Z up; the late-game registration frame) and checks it
against the saved <Model>-ReferenceStudy.blend that the official export
reads: the highest static surface within radius + MOUTH_REACH of the mouth
must lie at the mouth height, on a stack at least STACK_DEPTH tall.

Writes outputs/<pipeline>-integration/<Model>-smoke-registration.json in the
late-game registration shape (footprint, height, smokeEmitters: kind,
position, radius) with the scene's SHA256, so the content generators reject a
record made on a different scene. Never saves a scene.

blender -b --python-exit-code 1 --python register_smoke_emitters.py -- --models Restaurant,Hospital
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import bpy
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from frontier_architecture import Geometry
from lategame_kit import EMITTER_KINDS

MOUTH_REACH = .2      # the top frame/collar stands up to 0.2 outside the mouth radius
HEIGHT_TOLERANCE = .002
STACK_DEPTH = .5
# Buildings whose roof flues were removed (user, 2026-10-30: "no roof vents"):
# they register an empty emitter list, and an emitter recorded on them fails.
# Every other model must still record at least one.
FLUELESS = frozenset({'Restaurant', 'Hospital', 'FisheryWorks', 'MaterialsLaboratory'})


def models():
    from civic_isometric_geometry import restaurant, hospital, fishery
    from kiln_isometric_geometry import kiln
    from materials_laboratory_geometry import laboratory
    civic = ('tools/civic-layouts.json', 'outputs/civic-integration')
    return {'Restaurant': (restaurant, *civic), 'Hospital': (hospital, *civic), 'FisheryWorks': (fishery, *civic),
            'CementKiln': (kiln, 'tools/industrial-layouts.json', 'outputs/industrial-integration'),
            'MaterialsLaboratory': (laboratory, 'tools/research-layouts.json', 'outputs/research-integration')}


def authored_emitters(ident, build):
    static = Geometry(ident + '.Architecture')
    parts = []
    rails = build(static, parts)
    for geo in [geo for geo, _, _ in parts] + list(rails.meshes):
        if geo.__dict__.get('emitters'):
            raise ValueError(f'{ident}: emitter on {geo.name}; record it on the static architecture')
    emitters = static.__dict__.get('emitters', [])
    if ident in FLUELESS:
        if emitters:
            raise ValueError(f'{ident}: has no flue since 2026-10-30, but the art records {len(emitters)} emitter(s)')
        return []
    if not emitters:
        raise ValueError(f'{ident}: the authored art records no smoke/steam emitter')
    for e in emitters:
        if e['kind'] not in EMITTER_KINDS:
            raise ValueError(f'{ident}: unknown emitter kind {e["kind"]}')
    return emitters


def animated(obj):
    while obj is not None:
        if obj.animation_data and obj.animation_data.action:
            return True
        obj = obj.parent
    return False


def scene_points(ident, source, origin):
    """Static, evaluated scene vertices at frame 1 in the native grid frame
    (Blender scene -> native: (-x + ox, -y + oy, z + oz), as the exporter's
    IndustrialGridOrigin places the model)."""
    bpy.ops.wm.open_mainfile(filepath=str(source))
    bpy.context.scene.frame_set(1)
    depsgraph = bpy.context.evaluated_depsgraph_get()
    chunks = []
    for obj in bpy.data.collections[ident + '.ReferenceStudy'].all_objects:
        if obj.type != 'MESH' or animated(obj) or 'native_resource' in obj or 'liquid_surface' in obj:
            continue
        evaluated = obj.evaluated_get(depsgraph)
        mesh = evaluated.to_mesh()
        co = np.empty(len(mesh.vertices) * 3, dtype=np.float64)
        mesh.vertices.foreach_get('co', co)
        co = co.reshape(-1, 3)
        matrix = np.array(evaluated.matrix_world)
        world = co @ matrix[:3, :3].T + matrix[:3, 3]
        chunks.append(world)
        evaluated.to_mesh_clear()
    world = np.concatenate(chunks)
    ox, oy, oz = origin
    return np.column_stack((-world[:, 0] + ox, -world[:, 1] + oy, world[:, 2] + oz))


def register(ident, build, layout_file, folder):
    layout = json.loads((ROOT / layout_file).read_text())[ident]
    if layout['baseZ'] != 0:
        raise ValueError(f'{ident}: BaseZ {layout["baseZ"]}; the model/#Finished frame for a nonzero BaseZ is not established')
    ox, oy, oz = layout['origin']
    w, d, h = layout['size']
    emitters = []
    for e in authored_emitters(ident, build):
        x, y, z = e['position']
        p = [round(x + ox, 4), round(y + oy, 4), round(z + oz, 4)]
        if not (0 <= p[0] <= w and 0 <= p[1] <= d and 0 < p[2] <= h):
            raise ValueError(f'{ident}: {e["kind"]} mouth {p} lies outside the {w}x{d}x{h} registration')
        emitters.append({'kind': e['kind'], 'position': p, 'radius': e['radius']})
    source = ROOT / 'src/DeepFrontier/Art/Source' / f'{ident}-ReferenceStudy.blend'
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    points = scene_points(ident, source, (ox, oy, oz))
    checks = []
    for e in emitters:
        x, y, z = e['position']
        near = points[np.hypot(points[:, 0] - x, points[:, 1] - y) <= e['radius'] + MOUTH_REACH]
        if not len(near):
            raise ValueError(f'{ident}: no saved-scene geometry under the {e["kind"]} mouth {e["position"]}')
        top, bottom = float(near[:, 2].max()), float(near[:, 2].min())
        if abs(top - z) > HEIGHT_TOLERANCE:
            raise ValueError(f'{ident}: saved-scene stack top {top:.4f} differs from the {e["kind"]} mouth {e["position"]}')
        if top - bottom < STACK_DEPTH:
            raise ValueError(f'{ident}: no stack under the {e["kind"]} mouth {e["position"]} in the saved scene')
        checks.append({'position': e['position'], 'stackTop': round(top, 4), 'lowestNearby': round(bottom, 4),
                       'vertices': int(len(near))})
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest:
        raise RuntimeError(f'{ident}: scene changed while registering')
    target = ROOT / folder / f'{ident}-smoke-registration.json'
    target.write_text(json.dumps({
        'ident': ident, 'source': source.relative_to(ROOT).as_posix(), 'sourceSha256': digest, 'frame': 1,
        'layout': layout_file, 'origin': layout['origin'], 'baseZ': layout['baseZ'], 'footprint': [w, d], 'height': h,
        'coordinateSystem': 'Native grid XYZ, Z up: authored artwork + registration origin (the late-game registration frame)',
        'smokeEmitters': emitters,
        'sceneCheck': {'rule': f'highest static surface within radius + {MOUTH_REACH} at the mouth height '
                               f'(+/-{HEIGHT_TOLERANCE}), at least {STACK_DEPTH} above the lowest', 'mouths': checks},
    }, indent=1) + '\n')
    print('SMOKE REGISTRATION', ident, [(e['kind'], e['position'], e['radius']) for e in emitters], target, flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True, help='Comma-separated: ' + ', '.join(models()))
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    table = models()
    selected = cli.models.split(',')
    if len(set(selected)) != len(selected) or any(ident not in table for ident in selected):
        raise ValueError('Choose distinct models from: ' + ', '.join(table))
    for ident in selected:
        register(ident, *table[ident])


if __name__ == '__main__':
    main()
