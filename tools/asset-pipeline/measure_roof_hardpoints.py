"""Measure what stands over the top cells of every Deep Frontier building model.

Roof hardpoints (docs/platforms-design.md, slice 3 "D1"): a steel column may
stand on the top-most occupied cell of any column of a building, also where
the roof there is pitched, gabled, curved or otherwise not flat, so a deck
can sit over existing buildings with its legs entering the roof. The flat
roofs are already platformable (measure_connection_faces.py records their
'roof' fields and tools/roof_deck_content.mjs makes them stackable); this
measures the same three things for every top cell, flat or not, with the same
probes and thresholds:

- blocked: static geometry in the middle of the cell above (the inner box,
  0.31 in from every cell edge, from ROOF_LIP over the top of the cell up to
  one layer, probed along all three axes): a stack, mast, tank or frame
  standing there. A pitched roof lies inside its own top cell and never
  blocks it.
- covered: static geometry anywhere above the inner box (an overhang or an
  upper storey); the column would be built into it.
- animated: animated geometry in the inner box of the top cell or of the cell
  above (a fan, crane, hoist or rotor the column would cut through).

A top cell is one with an occupied block (any occupation) and nothing
occupied above it in the blueprint. tools/roof_hardpoint_content.mjs adds the
exterior, access, emitter and prop rules and lists the hardpoints.

  python measure_roof_hardpoints.py --data <generated Data root> [--only A,B] [--out DIR]

validate_roof_hardpoint_exports.py re-measures and compares (validate_all exports-roof_hardpoint).
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
from measure_connection_faces import (ROOF_LIP, ROOT, SAMPLES, AxisHits, buildings,  # noqa: E402
                                      relative, sha256, triangles)

OUT = ROOT / 'outputs/roof-hardpoints'
# Structural pieces are supports or paths themselves and get no hardpoints (roof_hardpoint_content.mjs STRUCTURES).
_STRUCTURAL = json.loads((ROOT / 'tools/structural_content.json').read_text(encoding='utf-8'))
STRUCTURES = {b['id'] for b in _STRUCTURAL['buildings'] + _STRUCTURAL['legDecks']['tools']}
INNER = slice(SAMPLES // 4, SAMPLES - SAMPLES // 4)   # samples 0.31..0.69, as measure_connection_faces
RULE = (f'Top cells (occupied, nothing occupied above in the blueprint); inner box = samples {SAMPLES // 4}..{SAMPLES - SAMPLES // 4 - 1} '
        f'of {SAMPLES} per axis; blocked = static geometry from {ROOF_LIP} over the cell top up one layer (vertical and horizontal '
        f'rays); covered = static geometry anywhere above that; animated = animated geometry in the top cell or the cell above')


def top_cells(blueprint):
    spec = blueprint['BlockObjectSpec']
    w, h, layers = spec['Size']['X'], spec['Size']['Y'], spec['Size']['Z']
    blocks = spec['Blocks']
    occupied = lambda x, y, z: blocks[(z * h + y) * w + x]['Occupations'] != 'None'
    cells = []
    for y in range(h):
        for x in range(w):
            for z in range(layers - 1, -1, -1):
                if occupied(x, y, z):
                    cells.append((x, y, z))
                    break
    cells.sort(key=lambda c: (c[2], c[1], c[0]))
    return cells


def inner_ids(hits, cells):
    n = len(cells)
    return hits.sample_ids(cells).reshape(n, SAMPLES, SAMPLES)[:, INNER, INNER].reshape(n, -1)


def measure(path, size, base_z, cells):
    kinds = triangles(path, base_z)
    size = tuple(size)
    cells = np.array(cells, dtype=np.int64).reshape(-1, 3)
    if not len(cells):
        return []
    solid_tris = np.concatenate([kinds['opaque'], kinds['glass'], kinds['lamp']])
    solid = [AxisHits(solid_tris, a, size, 0) for a in range(3)]
    moving = [AxisHits(kinds['animated'], a, size, 0) for a in range(3)]
    top = (cells[:, 2] + 1).astype(np.float64)
    vertical = inner_ids(solid[2], cells)
    blocked = solid[2].any_between(vertical, top + ROOF_LIP, top + 1.).any(1)
    covered = solid[2].any_between(vertical, top + ROOF_LIP, np.full(len(top), 55.)).any(1)
    animated = moving[2].any_between(inner_ids(moving[2], cells), top - 1., top + 1.).any(1)
    over = cells + np.array([0, 0, 1])
    inside = over[:, 2] < size[2]          # horizontal rays exist inside the Size only
    for a in (0, 1):
        if not inside.any():
            break
        lo, hi = over[inside, a] + 2.5 / SAMPLES, over[inside, a] + 1 - 2.5 / SAMPLES   # the band the vertical samples cover
        blocked[inside] |= solid[a].any_between(inner_ids(solid[a], over[inside]), lo, hi).any(1)
        for rows in (cells, over):
            band_lo, band_hi = rows[inside, a] + 2.5 / SAMPLES, rows[inside, a] + 1 - 2.5 / SAMPLES
            animated[inside] |= moving[a].any_between(inner_ids(moving[a], rows[inside]), band_lo, band_hi).any(1)
    return [{'cell': [int(v) for v in c], 'blocked': bool(b), 'covered': bool(k), 'animated': bool(m)}
            for c, b, k, m in zip(cells, blocked, covered, animated)]


def record(ident, blueprint, finished, export, size, base_z):
    return {'template': ident, 'model': finished, 'export': relative(export), 'exportSha256': sha256(export),
            'size': size, 'baseZ': base_z,
            'coordinateSystem': 'Native grid XYZ, Z up, blueprint block indices; the cell is the top cell, a column stands in the cell above',
            'rule': RULE, 'cells': measure(export, size, base_z, top_cells(blueprint))}


def measured(data, only):
    """buildings() of measure_connection_faces without the structural pieces."""
    if only and only & STRUCTURES:
        raise ValueError('Structural pieces get no hardpoints: ' + ', '.join(sorted(only & STRUCTURES)))
    return [row for row in buildings(data, only) if row[0] not in STRUCTURES]


def dump(value):
    return json.dumps(value, separators=(',', ':')).replace('},{', '},\n{') + '\n'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, required=True, help='generated Data root whose blueprints give Size/BaseZ/model')
    parser.add_argument('--only', help='comma-separated templates')
    parser.add_argument('--out', type=Path, default=OUT)
    cli = parser.parse_args()
    only = set(cli.only.split(',')) if cli.only else None
    cli.out.mkdir(parents=True, exist_ok=True)
    for ident, blueprint, finished, export, size, base_z in measured(cli.data, only):
        fresh = record(ident, blueprint, finished, export, size, base_z)
        (cli.out / f'{ident}.json').write_text(dump(fresh), encoding='utf-8')
        clear = sum(not (c['blocked'] or c['covered'] or c['animated']) for c in fresh['cells'])
        print('ROOF TOPS', ident, len(fresh['cells']), 'clear', clear, flush=True)


if __name__ == '__main__':
    main()
