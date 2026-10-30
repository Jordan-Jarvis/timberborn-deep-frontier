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
    # The arched turbine-hall door portal and the containment drum (2026-10-30 compaction:
    # the barrel-vaulted hall and the corner pier are gone).
    'NuclearReactor': [[10, 0, 0, 'Left'], [10, 0, 0, 'Right'], [10, 0, 0, 'Top'], [6, 4, 0, 'Down'], [7, 4, 0, 'Down']],
    # The round LOX tank's dome and the hydrogen bullets' dished heads (7x6 study, 2026-10-30).
    'CryogenicTankFarm': [[3, 3, 3, 'Top'], [3, 4, 3, 'Top'], [0, 5, 0, 'Up'], [1, 5, 0, 'Up']],
    # The arched door portal (the barrel vault went flat in the 2026-10-30 compaction).
    'OilPowerPlant': [[1, 0, 0, 'Left'], [1, 0, 0, 'Right'], [1, 0, 0, 'Top']],
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
    axes = {name: (axis, sign) for name, axis, sign in M.DIRECTIONS}
    # covering() measures every face (row) on its own, so each direction's
    # faces go through face_test in one call.
    tested = {}
    for axis, sign in sorted({axes[f[3]] for f in faces}):
        rows = [i for i, f in enumerate(faces) if axes[f[3]] == (axis, sign)]
        c = M.face_test(M.AxisHits(solid, axis, tuple(size), sign), M.AxisHits(kinds['opaque'], axis, tuple(size), sign),
                        np.array([faces[i][:3] for i in rows], dtype=np.int64), axis, sign)
        for r, i in enumerate(rows):
            tested[i] = (c['axisAngle'][r], c['normalSpread'][r], c['planeShare'][r])
    for i, f in enumerate(faces):
        axis_angle, spread, plane_share = tested[i]
        if axis_angle > M.AXIS_ANGLE or spread > M.NORMAL_SPREAD:
            failures.append(f'{ident}: face {f} sits on a curved, faceted or sloped surface '
                            f'({axis_angle:.1f} deg off the axis, {spread:.1f} deg spread)')
        elif plane_share < M.COVER:
            failures.append(f'{ident}: face {f} has no single plane over {M.COVER:.0%} of it ({plane_share:.0%})')
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
