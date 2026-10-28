"""Re-measure every building's flat exterior faces and compare with the records.

outputs/connection-faces/<Template>.json (measure_connection_faces.py) feed the
shaft transputs and pipe ports that tools/connection_content.mjs generates.
This check:
- re-measures each owning export over the generated blueprint's Size/BaseZ
  and fails when a record no longer matches (export bytes, model, Size,
  BaseZ, rule, faces or curved faces);
- re-checks every recorded face on its own (glass counts as a surface): one wall plane (depth band 0.05)
  covers >= 60% of it and no covering surface is curved, faceted or sloped
  (every covering normal within 5 degrees of the face axis and 1 degree of the
  covering mean);
- holds three curved surfaces as explicit test cases (user: "The reactor has
  curved edges on it; we don't want to be able to connect to the curved
  edges, just the flat ones"): the reactor's curved edge, the round tank of
  the Cryogenic Tank Farm and the barrel-vaulted hall of the Oil Power Plant.
  Each listed face is covered (>= 60% of it within reach) by a curved or
  sloped surface (a covering normal more than 5 degrees off the face axis or
  1 degree off the covering mean) and must not be a connection face.
Static evidence only.

  python validate_connection_exports.py [--data <generated Data root>]
"""
import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import measure_connection_faces as M  # noqa: E402

KEYS = ('model', 'export', 'exportSha256', 'size', 'baseZ', 'rule', 'faces', 'curvedFaces', 'roof')
# Faces covered by curved surfaces (found 2026-10-23 on the exported models).
CURVED_CASES = {
    # Rounded edge of the turbine hall front (y 2, z 5) and the rounded corner pier.
    'NuclearReactor': [[x, 2, 5, 'Up'] for x in range(6, 15)] + [[0, 0, 0, 'Left'], [0, 0, 0, 'Right']],
    # The round LOX tank: its cylinder wall on three sides and its dome; a hydrogen bullet.
    'CryogenicTankFarm': [[9, 6, z, 'Right'] for z in range(6)] + [[7, 4, z, 'Down'] for z in range(6)]
    + [[7, 8, z, 'Up'] for z in range(6)] + [[7, 5, 6, 'Top'], [8, 6, 6, 'Top'], [0, 1, 2, 'Left'], [1, 1, 3, 'Top']],
    # The barrel-vaulted turbine hall roof.
    'OilPowerPlant': [[x, y, 4, 'Top'] for y in (1, 2) for x in range(6)],
}


def curved_cases(ident, export, size, base_z, flat):
    """Each test face is covered by a curved or sloped surface and is not a connection face."""
    failures = []
    kinds = M.triangles(export, base_z)
    axes = {name: (axis, sign) for name, axis, sign in M.DIRECTIONS}
    for f in CURVED_CASES[ident]:
        axis, sign = axes[f[3]]
        c = M.covering(M.AxisHits(np.concatenate([kinds['opaque'], kinds['glass']]), axis, tuple(size), sign), np.array([f[:3]], dtype=np.int64), axis, sign)
        if c['share'][0] < M.COVER or (c['axisAngle'][0] <= M.AXIS_ANGLE and c['normalSpread'][0] <= M.NORMAL_SPREAD):
            failures.append(f'{ident}: test face {f} is no longer covered by a curved or sloped surface; update CURVED_CASES')
        if tuple(f) in flat:
            failures.append(f'{ident}: curved test face {f} is a connection face')
    return failures


def recheck(ident, export, size, base_z, faces):
    """Every recorded face, measured alone, is one uncurved plane."""
    failures = []
    kinds = M.triangles(export, base_z)
    solid = np.concatenate([kinds['opaque'], kinds['glass']])
    hits = {(a, s): (M.AxisHits(solid, a, tuple(size), s), M.AxisHits(kinds['opaque'], a, tuple(size), s)) for a in range(3) for s in (-1, 1)}
    axes = {name: (axis, sign) for name, axis, sign in M.DIRECTIONS}
    for f in faces:
        axis, sign = axes[f[3]]
        c = M.face_test(*hits[(axis, sign)], np.array([f[:3]], dtype=np.int64), axis, sign)
        if c['axisAngle'][0] > M.AXIS_ANGLE or c['normalSpread'][0] > M.NORMAL_SPREAD:
            failures.append(f'{ident}: face {f} sits on a curved, faceted or sloped surface '
                            f'({c["axisAngle"][0]:.1f} deg off the axis, {c["normalSpread"][0]:.1f} deg spread)')
        elif c['planeShare'][0] < M.COVER:
            failures.append(f'{ident}: face {f} has no single plane over {M.COVER:.0%} of it ({c["planeShare"][0]:.0%})')
    return failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', type=Path, default=M.ROOT / 'src/DeepFrontier/Data')
    cli = parser.parse_args()
    failures, checked, total = [], 0, 0
    seen = set()
    for ident, _, finished, export, size, base_z in M.buildings(cli.data, None):
        target = M.OUT / f'{ident}.json'
        if not target.is_file():
            failures.append(f'{ident}: no record {target.relative_to(M.ROOT)}; run measure_connection_faces.py')
            continue
        old = json.loads(target.read_text(encoding='utf-8'))
        fresh = M.record(ident, finished, export, size, base_z)
        for key in KEYS:
            if old.get(key) != fresh[key]:
                failures.append(f'{ident}: recorded {key} differs from a fresh measurement; run measure_connection_faces.py')
        failures += recheck(ident, export, size, base_z, fresh['faces'])
        if ident in CURVED_CASES:
            seen.add(ident)
            failures += curved_cases(ident, export, size, base_z, {tuple(f) for f in fresh['faces']})
        checked += 1
        total += len(fresh['faces'])
    for ident in sorted(set(CURVED_CASES) - seen):
        failures.append(f'{ident}: curved test case building was not measured')
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'Connection face records are stale or not flat ({len(failures)})')
    print(f'Connection face records match fresh measurements: {checked} models, {total} flat faces; '
          f'every face is one uncurved plane; {sum(len(v) for v in CURVED_CASES.values())} curved test faces excluded')


if __name__ == '__main__':
    main()
