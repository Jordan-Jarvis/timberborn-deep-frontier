"""Re-measure every building's roof tops and compare with the records.

outputs/roof-hardpoints/<Template>.json (measure_roof_hardpoints.py) feed the
roof hardpoints that tools/roof_hardpoint_content.mjs lists. This check
re-measures each owning export over the generated blueprint's Size/BaseZ and
top cells and fails when a record no longer matches (export bytes, model,
Size, BaseZ, rule or any cell's blocked/covered/animated flags), when a
building has no record, or when a record names a template that is gone or is
a structural piece. Static evidence only.

  python validate_roof_hardpoint_exports.py [--data <generated Data root>]
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import measure_connection_faces as C  # noqa: E402
import measure_roof_hardpoints as M  # noqa: E402

KEYS = ('model', 'export', 'exportSha256', 'size', 'baseZ', 'rule', 'cells')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=C.ROOT / 'src/DeepFrontier/Data')
    cli = parser.parse_args()
    failures, checked, cells = [], 0, 0
    seen = set()
    for ident, blueprint, finished, export, size, base_z in M.measured(cli.data, None):
        seen.add(ident)
        target = M.OUT / f'{ident}.json'
        if not target.is_file():
            failures.append(f'{ident}: no record {target.relative_to(C.ROOT)}; run measure_roof_hardpoints.py')
            continue
        old = json.loads(target.read_text(encoding='utf-8'))
        fresh = M.record(ident, blueprint, finished, export, size, base_z)
        for key in KEYS:
            if old.get(key) != fresh[key]:
                failures.append(f'{ident}: recorded {key} differs from a fresh measurement; run measure_roof_hardpoints.py')
        checked += 1
        cells += len(fresh['cells'])
    for path in sorted(M.OUT.glob('*.json')):
        if path.stem not in seen:
            failures.append(f'{path.stem}: record for a template that is gone, owns no model or is a structural piece')
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'Roof top records are stale ({len(failures)})')
    print(f'Roof top records match fresh measurements: {checked} models, {cells} top cells')


if __name__ == '__main__':
    main()
