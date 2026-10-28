"""Grid registration and native props for the Grocery Market study.

Runs the authored geometry (grocery_market_geometry.py) without building a
scene and applies the late-game registration rules (render_lategame_studies.
registration): occupied cells from the authored parts, and per ground door the
doorstep, native Entrance path cell and face offset. Writes
  outputs/lategame-studies/GroceryMarket-registration.json
  outputs/reference-studies/GroceryMarket-native-assembly.json
(named after the study, so the outgoing GroceryStore data stays intact until
the generator switches over)
for export_lategame_models.py and grocery_building_content.mjs. The access
contract (balcony, stair bay, door walk) is carried through and checked here.

Run: blender -b --python-exit-code 1 --python register_grocery_market.py
"""
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from frontier_architecture import Geometry
from render_lategame_studies import record_extents, registration, smoke_emitters
import grocery_market_geometry as source
from render_grocery_market_study import FRAMES, FPS, IDENT as STUDY

IDENT = 'GroceryStore'
HEIGHT = 8   # chimney cap at 7.2


def art_hash():
    here = Path(__file__).parent
    digest = hashlib.sha256()
    for name in ('grocery_market_geometry.py', 'frontier_architecture.py', 'architectural_windows.py',
                 'native_window_atlas.py', 'native_building_assets.py', 'industrial_facades.py'):
        digest.update(name.encode() + b'|' + (here / name).read_bytes())
    return digest.hexdigest()


def main():
    static = Geometry(STUDY + '.Architecture')
    parts = []
    original = record_extents()
    try:
        rails = source.grocery_market(static, parts)
    finally:
        Geometry.add = original
    module = SimpleNamespace(IDENT=IDENT, FOOTPRINT=source.FOOTPRINT, HEIGHT=HEIGHT)
    geometries = [static] + list(rails.meshes) + [geo for geo, _, _ in parts]
    reg = registration(module, geometries, static.doorways)
    reg['smokeEmitters'] = smoke_emitters(module, static, parts)
    access = source.ACCESS
    occupied = {tuple(c) for c in reg['occupied']}
    # The access contract is part of the design: the door walk and the stair
    # bay must stay clear for player paths and native stairs.
    x0, y0, x1, y1 = access['groundWalk']['mainDoorApproach']
    walk = {(x, y, z) for x in range(int(x0), int(x1)) for y in range(int(y0), int(y1)) for z in (0, 1)}
    bx0, by0, bx1, by1 = access['stairBay']['bounds']
    bay = {(x, y, z) for x in range(bx0, bx1) for y in range(by0, by1) for z in (0, 1)}
    for name, cells in (('main door walk', walk), ('stair bay', bay)):
        blocked = sorted(cells & occupied)
        if blocked:
            raise ValueError(f'{IDENT}: {name} cells occupied by the art: {blocked}')
    animated = [geo.name for geo, kind, _ in parts]
    out = dict(reg, ident=IDENT, study=STUDY, frameEnd=FRAMES, fps=FPS, animatedParts=animated,
               access=access, artHash=art_hash())
    (ROOT / f'outputs/lategame-studies/{STUDY}-registration.json').write_text(json.dumps(out, indent=1) + '\n')
    (ROOT / f'outputs/reference-studies/{STUDY}-native-assembly.json').write_text(json.dumps({
        'scope': 'Grocery Market study; runtime references the original shipped resources',
        'props': static.native_props, 'liquids': []}, indent=2) + '\n')
    print('GROCERY REGISTRATION', reg['footprint'], len(occupied), 'cells', reg['doors'], flush=True)


if __name__ == '__main__':
    main()
