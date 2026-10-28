"""Record the ground cells the no-forced-decoration pass freed (2026-10-22).

Compares each late-game registration before the pass (a saved copy, --before
DIR) with the current one (outputs/lategame-studies), taking the module's
GRID_ORIGIN into account, and writes tools/lategame_freed_cells.json:

- footprint before -> after and the grid origin;
- outsideCells: ground cells of the old footprint that now lie outside the
  building (always free for the player);
- insideCells: ground cells inside the new footprint that were occupied before
  and are free now. tools/validate_lategame_freed_cells.mjs checks these
  against the generated blueprints (no occupation at layers 0-1, no collider,
  not a door cell), so a Path or a 1x1 decoration can be placed there.

Run: python record_freed_cells.py --before DIR
"""
import argparse
import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def grid_origin(ident):
    """GRID_ORIGIN literal from the module source (no Blender import needed)."""
    tree = ast.parse((ROOT / f'tools/asset-pipeline/lategame_{ident}.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'GRID_ORIGIN' for t in node.targets):
            return list(ast.literal_eval(node.value))
    return [0, 0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--before', required=True, type=Path)
    cli = parser.parse_args()
    ids = json.loads((ROOT / 'tools/lategame_batches.json').read_text(encoding='utf-8'))['integrated']
    out = {}
    # Buildings integrated after the pass have no earlier registration and
    # freed nothing; they are named, not silently skipped.
    newer = [i for i in ids if not (cli.before / f'{i}-registration.json').is_file()]
    if newer:
        print('integrated after the pass (no earlier registration):', ', '.join(newer))
    for ident in (i for i in ids if i not in newer):
        old = json.loads((cli.before / f'{ident}-registration.json').read_text(encoding='utf-8'))
        new = json.loads((ROOT / f'outputs/lategame-studies/{ident}-registration.json').read_text(encoding='utf-8'))
        dx, dy = grid_origin(ident)
        ow, oh = old['footprint']
        nw, nh = new['footprint']
        old_ground = {(x - dx, y - dy) for x, y, z in old['occupied'] if z == 0}
        new_ground = {(x, y) for x, y, z in new['occupied'] if z == 0}
        outside, inside = [], []
        for y in range(oh):
            for x in range(ow):
                c = (x - dx, y - dy)
                if not (0 <= c[0] < nw and 0 <= c[1] < nh):
                    outside.append(list(c))
                elif c in old_ground and c not in new_ground:
                    inside.append(list(c))
        if outside or inside or [ow, oh] != [nw, nh]:
            out[ident] = {'footprintBefore': [ow, oh, old['height']], 'footprintAfter': [nw, nh, new['height']],
                          'gridOrigin': [dx, dy], 'outsideCells': len(outside), 'insideCells': sorted(inside)}
    record = {'scope': 'Ground cells freed by the no-forced-decoration pass (2026-10-22), in the new footprint '
                       'frame; outside cells left the building entirely.',
              'buildings': out}
    target = ROOT / 'tools/lategame_freed_cells.json'
    target.write_text(json.dumps(record, indent=1) + '\n', encoding='utf-8')
    print(json.dumps({k: [v['footprintBefore'][:2], v['footprintAfter'][:2], v['outsideCells'], len(v['insideCells'])]
                      for k, v in out.items()}))


if __name__ == '__main__':
    main()
