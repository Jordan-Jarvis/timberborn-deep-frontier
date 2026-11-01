"""Every ground tile the no-forced-decoration pass freed must take the player's
own path or small decoration (user rule, 2026-10-22).

Rules, from the decompiled Timberborn 1.1.2.8 Timberborn.BlockSystem
(BlockValidator.BlockValid, MatterBelowValidator, BlockOccupations):
- BlockConflictsWithExistingObject: the new block's occupations may not
  intersect the building's non-overridable occupations in that cell.
- BlockConflictsWithBlockAbove: a block occupying Top fails when the object
  whose bottom is in the cell above requires MatterBelow Air there.
- MatterBelow: vanilla Path and Shrub need GroundOrStackable at the bottom;
  a ground-level freed cell stands on terrain, so this holds.
Probe objects are the vanilla blueprints themselves: Path (one block,
Occupations Path), and as the 1x1 decoration Shrub.IronTeeth (two blocks:
Bottom, Top, Path, Middle / Floor, Bottom, Path, Middle) or, where the
building overhangs the cell one layer up, Brazier.IronTeeth (one block:
Bottom, Path, Middle), read from the vendor resources. These are the probes
src/DeepFrontier/Scripts/FreedCellProbe.cs asks the native BlockValidator
about in the acceptance fixtures; a cell needs the Path and one decoration.

FREED lists, per building, each ground cell (new native frame) that the pass
opened inside the building's bounds. Cells freed outside the shrunken bounds
need no check (nothing of the building is there) and are listed in OUTSIDE for
the report. Also no authored collider may reach into the central half of a
freed cell below the accepted decoration's own picking volume, at most 1 m
(Shrub: 1 m; Brazier: its collider top; balcony corner posts keep to the
corners), so a path or decoration there is not hidden inside a picking volume.
These cells are in-game acceptance points (place a path and a shrub).

Run: python validate_freed_cells.py [--data DIR]
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
VANILLA = ROOT / 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources'

# Blueprint path (under Data) -> freed ground cells inside the new bounds.
FREED = {
    'Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint.json': {
        # The rear barrel and supply pile stood under the back balcony's wing
        # ends, at (1,8,0), (10,8,0) and (11,8,0) of the 12x9 frame. The
        # 2026-10-30 compaction removed both ward wings: the 4x9 pavilion is
        # native x 4..7 of that frame (ORIGIN x -4), so all three are now
        # outside its bounds and no freed cell is inside.
        'cells': [],
        'outside': 'the two former front rows (planters, sunflowers, canopy footprint), and the rear barrel and supply pile under the removed wings\' back balcony: now outside the 4x4 bounds (4x9 until 2026-11-01)',
    },
    'Buildings/Science/MaterialsLaboratory/MaterialsLaboratory.IronTeeth.blueprint.json': {
        # Front specimen shelves, rear planters, barrel and crate.
        'cells': [(x, 0, 0) for x in range(3, 8)] + [(0, 7, 0), (2, 7, 0), (8, 7, 0), (9, 7, 0)],
        'outside': 'the former rear row (rear specimen shelves): now outside the 10x8 bounds',
    },
    'Buildings/Food/FisheryWorks/FisheryWorks.IronTeeth.blueprint.json': {
        # The rear supply pile and loose barrel (2026-10-22) are outside the
        # 6x5 bounds of the second shrink pass (2026-11-01).
        'cells': [],
        'outside': 'the two former front rows (fish tables, bins, front basin), the empty right column and the rear supply cells: now outside the 6x5 bounds',
    },
    'Buildings/Food/FishHatchery/FishHatchery.IronTeeth.blueprint.json': {
        # Bank-row barrels and sacks (2026-10-22), in the compact grid
        # (2026-10-26: x moved by -1). The rear dock corners (dock lamps) left
        # the footprint with the perimeter docks; the third barrel cell (6,0,1)
        # with the 5x5 shrink (2026-11-01).
        'cells': [(2, 0, 1), (3, 0, 1)],
        'outside': 'the perimeter docks, the walkway column beside the headhouse, the front walkway row, the outer canopy column and the rear pen rows: now outside the 5x5 bounds',
    },
    'Buildings/Food/GroceryStore/GroceryStore.IronTeeth.blueprint.json': {
        'cells': [],
        'outside': 'the former rear row (loading dock, its goods and barrels, the water tower): now outside the 9x6 bounds',
    },
    'Buildings/Food/Restaurant/Restaurant.IronTeeth.blueprint.json': {
        # Outdoor service counters, awnings and barrel under the dining
        # balcony, and the ground doorstep between the balcony posts. Since
        # the 2026-10-30 compaction the balcony is one layer up (its slab is
        # Top, Corners in these cells), so the decoration here is a Brazier.
        'cells': [(x, 0, 0) for x in range(1, 6)],
        'outside': 'the former empty first row and column: now outside the 9x7 bounds',
    },
}

PATH_BLOCKS = None
# (name, blocks, clear height): each 1x1 decoration probe, in the order
# FreedCellProbe.cs tries them, with the height its picking volume needs clear.
DECORATIONS = None


def flags(text):
    return {f.strip() for f in text.split(',')} - {'None'}


def occupation_set(text):
    names = flags(text)
    if 'All' in names:
        return {'Floor', 'Bottom', 'Top', 'Corners', 'Path', 'Middle'}
    return names


def load_probe(path):
    spec = json.loads(path.read_text(encoding='utf-8-sig'))['BlockObjectSpec']
    if spec['Size'] != {'X': 1, 'Y': 1, 'Z': len(spec['Blocks'])}:
        raise SystemExit(f'{path.name}: expected a 1x1 column probe')
    return spec['Blocks']


def probe_clear_height(path):
    """Top of the probe's finished picking volume, at most one layer."""
    colliders = json.loads(path.read_text(encoding='utf-8-sig'))['Children']['#Finished']['CollidersSpec']['BoxColliders']
    if not colliders:
        raise SystemExit(f'{path.name}: probe has no finished box colliders')
    return min(1.0, max(c['Center']['Y'] + c['Size']['Y'] / 2 for c in colliders))


def check_cell(blueprint, cell):
    """Problems per probe (Path, then each decoration); the cell passes when
    the Path and at least one decoration have none."""
    spec = blueprint['BlockObjectSpec']
    w, d, h = spec['Size']['X'], spec['Size']['Y'], spec['Size']['Z']
    blocks = spec['Blocks']
    x, y, z = cell
    if not (0 <= x < w and 0 <= y < d and 0 <= z < h):
        return {'bounds': ['not inside the bounds (list it as outside instead)']}

    def block(c):
        cx, cy, cz = c
        if 0 <= cz < h:
            return blocks[(cz * d + cy) * w + cx]
        return None

    def block_problems(name, probe):
        problems = []
        for k, pb in enumerate(probe):
            here = block((x, y, z + k))
            if here is None:
                continue
            clash = occupation_set(here['Occupations']) & occupation_set(pb['Occupations'])
            if clash:
                problems.append(f'{name} block {k} intersects the building occupation {sorted(clash)} at {(x, y, z + k)}')
            if 'Top' in occupation_set(pb['Occupations']):
                above = block((x, y, z + k + 1))
                if above is not None and 'Bottom' in occupation_set(above['Occupations']) and above['MatterBelow'] == 'Air':
                    problems.append(f'{name} block {k} occupies Top under a building block requiring air below')
        return problems

    def collider_problems(name, clear_height):
        problems = []
        for collider in blueprint['Children']['#Finished'].get('CollidersSpec', {}).get('BoxColliders', []):
            c, s = collider['Center'], collider['Size']
            lo = (c['X'] - s['X'] / 2, c['Z'] - s['Z'] / 2, c['Y'] - s['Y'] / 2)
            hi = (c['X'] + s['X'] / 2, c['Z'] + s['Z'] / 2, c['Y'] + s['Y'] / 2)
            # The central half of the tile, where a path or decoration stands;
            # balcony corner posts (Corners occupation) keep to the tile corners.
            cell_lo, cell_hi = (x + .25, y + .25, z), (x + .75, y + .75, z + clear_height)
            if all(lo[a] < cell_hi[a] - 1e-6 and hi[a] > cell_lo[a] + 1e-6 for a in range(3)):
                problems.append(f'{name}: a building collider reaches into the middle of {cell} below {clear_height:.3f} m: {collider}')
        return problems

    result = {'Path': block_problems('Path', PATH_BLOCKS)}
    for name, probe, clear_height in DECORATIONS:
        result[name] = block_problems(name, probe) + collider_problems(name, clear_height)
    return result


def main():
    global PATH_BLOCKS, DECORATIONS
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', default=str(ROOT / 'src/DeepFrontier/Data'))
    data = Path(parser.parse_args().data)
    PATH_BLOCKS = load_probe(VANILLA / 'Buildings/Paths/Path/Path.blueprint.json')
    DECORATIONS = []
    for name, rel in (('Shrub', 'Buildings/Decoration/Shrub/Shrub.IronTeeth.blueprint.json'),
                      ('Brazier', 'Buildings/Decoration/Brazier/Brazier.IronTeeth.blueprint.json')):
        DECORATIONS.append((name, load_probe(VANILLA / rel), probe_clear_height(VANILLA / rel)))
    failures, report = [], {}
    for rel, entry in FREED.items():
        blueprint = json.loads((data / rel).read_text(encoding='utf-8-sig'))
        size = blueprint['BlockObjectSpec']['Size']
        rows = []
        for cell in entry['cells']:
            problems = check_cell(blueprint, cell)
            decoration = next((name for name, _, _ in DECORATIONS if name in problems and not problems[name]), None)
            rows.append({'cell': list(cell), 'path': 'Path' in problems and not problems['Path'],
                         'decoration': decoration, 'problems': problems})
            if 'Path' not in problems or problems['Path'] or decoration is None:
                failures.extend(f'{rel.split("/")[-1]} {cell}: {p}' for found in problems.values() for p in found)
        report[rel.split('/')[-1].split('.')[0]] = {'size': [size['X'], size['Y'], size['Z']],
                                                     'freedInside': rows, 'freedOutside': entry['outside']}
    out = ROOT / 'outputs/triangle-budget/freed-cells.json'
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps({'rules': 'Timberborn 1.1.2.8 BlockValidator; probes: vanilla Path, and Shrub.IronTeeth or Brazier.IronTeeth',
                               'buildings': report}, indent=1) + '\n', encoding='utf-8')
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'Freed-cell validation failed ({len(failures)})')
    print(json.dumps({'status': 'freed-cells-checked', 'buildings': {k: len(v['freedInside']) for k, v in report.items()}}))


if __name__ == '__main__':
    main()
