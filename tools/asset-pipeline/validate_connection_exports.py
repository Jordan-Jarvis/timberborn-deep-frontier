"""Re-measure every building's flat exterior faces and compare with the records.

outputs/connection-faces/<Template>.json (measure_connection_faces.py) feed the
shaft transputs and pipe ports that tools/connection_content.mjs generates.
This check:
- re-measures each owning export over the generated blueprint's Size/BaseZ
  and fails when a record no longer matches (export bytes, model, Size,
  BaseZ, rule, faces, curved faces, roof or eave faces);
- re-checks every recorded face on its own (glass counts as a surface): one wall plane (depth band 0.05)
  covers >= 60% of it and no covering surface is curved, faceted or sloped
  (every covering normal within 5 degrees of the face axis and 1 degree of the
  covering mean), apart from an eave sloping up from a side wall in the top
  quarter of the face;
- holds three curved surfaces as explicit test cases (user: "The reactor has
  curved edges on it; we don't want to be able to connect to the curved
  edges, just the flat ones"): the reactor's curved edge, the round tank of
  the Cryogenic Tank Farm and the barrel-vaulted hall of the Oil Power Plant.
  Each listed face is covered (>= 60% of it within reach) by a curved or
  sloped surface (a covering normal more than 5 degrees off the face axis or
  1 degree off the covering mean) and must not be a connection face;
- holds the eave rule's test cases (measure_connection_faces EAVE_BAND): the
  Deep Mine's lamp-house wall under its eave, which the user tried to power
  on 2026-11-03 ("it didn't take the connection where it obviously should
  have"), must be a connection face recorded as an eave face; a roof slope
  reaching below the top quarter (the Oil Power Plant), a downward-facing
  slope and a sideways-turned surface in the top band (the Deep Mine's ore
  chute, the Rocket Assembly Hangar) and a slope at the foot of a wall (the
  Sandstone Pit) must still exclude their faces;
- holds walls whose relief is exactly the 0.05 plane band (the Deep Mine's
  back walls, brick panels 0.05 behind their pilasters, stored as
  0.050000191): one plane at float32 precision, so connection faces;
- holds the moving-part rule's test cases (user, 2026-11-03: no connection
  face in front of a moving part): faces with a moving part in their outward
  cell in some pose are not flat faces (the Fertilizer Works' drier drum, the
  Fishery Works' swinging sign, the Greenhouse's gable fan, the Radioactive
  Waste Refinery's spent-fuel cask, which only passes there while moving,
  and the Launch Pad's pump flywheel, 0.02 into the cell above a roof).
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

KEYS = ('model', 'export', 'exportSha256', 'size', 'baseZ', 'rule', 'faces', 'curvedFaces', 'roof', 'eaveFaces')
# Flat walls whose top band is the roof's edge: connection faces (found 2026-11-03).
EAVE_CASES = {
    # The brick lamp house's left wall on layer 2: grand windows under the front-gabled roof's eave at 0.84 of the layer.
    'DeepMine': [[0, 0, 1, 'Left'], [0, 1, 1, 'Left']],
}
# Walls whose relief is exactly PLANE_SPREAD deep: one plane at float32 precision (found 2026-11-03).
RELIEF_CASES = {
    # The back walls: brick panels set 0.05 behind the concrete pilasters and base course (exported as 0.050000191).
    'DeepMine': [[1, 4, 0, 'Up'], [2, 4, 0, 'Up']],
}
# Flat faces with a moving part in their outward cell in some pose: never flat faces (found 2026-11-03).
MOVING_CASES = {
    'FertilizerWorks': [[2, 1, 1, 'Right']],       # the drier drum
    'FisheryWorks': [[5, 0, 0, 'Down']],           # the swinging carved sign
    'Greenhouse': [[5, 1, 0, 'Right']],            # the gable fan's blades, across the top of the wall below it
    'RadioactiveWasteRefinery': [[2, 0, 1, 'Top']],  # the spent-fuel cask, over this roof only while it moves
    'LaunchPad': [[2, 1, 0, 'Top']],               # the pump flywheel's rim, 0.02 into the cell above
}
# Slopes the eave rule must not excuse: never connection faces (found 2026-11-03).
# Each one passes under one loosened rule (a wider band, any tilt, any turn, the foot of the wall).
SLOPE_CASES = {
    # A roof slope reaching down to 0.63 of the layer, where a shaft's frame stands.
    'OilPowerPlant': [[2, 1, 2, 'Up']],
    # The ore chute's underside, facing down, across the headframe plating's top band.
    'DeepMine': [[2, 1, 1, 'Left']],
    # A surface in the top band turned 75 degrees sideways, not sloping up from the wall.
    'RocketAssemblyHangar': [[0, 5, 1, 'Left']],
    # A 45-degree slope at the foot of its left wall's corner (the bottom quarter).
    'SandstonePit': [[0, 1, 0, 'Left']],
}
# Faces covered by curved surfaces (found 2026-10-23 on the exported models).
CURVED_CASES = {
    # The arched turbine-hall door portal and the containment drum (2026-10-30 compaction:
    # the barrel-vaulted hall and the corner pier are gone).
    'NuclearReactor': [[10, 0, 0, 'Left'], [10, 0, 0, 'Right'], [10, 0, 0, 'Top'], [6, 4, 0, 'Down'], [7, 4, 0, 'Down']],
    # The round LOX tank's dome (4x4 study, 2026-11-01).
    'CryogenicTankFarm': [[3, 2, 2, 'Top'], [2, 3, 2, 'Top'], [3, 3, 2, 'Top']],
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


def eave_cases(ident, fresh):
    """Each test wall is a connection face that passes because of its eave."""
    failures = []
    flat, eaves = {tuple(f) for f in fresh['faces']}, {tuple(f) for f in fresh['eaveFaces']}
    for f in EAVE_CASES[ident]:
        if tuple(f) not in flat:
            failures.append(f'{ident}: wall {f} under an eave is not a connection face')
        elif tuple(f) not in eaves:
            failures.append(f'{ident}: test wall {f} no longer has an eave over its top band; update EAVE_CASES')
    return failures


def relief_cases(ident, export, size, base_z, flat):
    """Each test wall's relief is PLANE_SPREAD deep (to float32 precision) and the wall is a flat face."""
    failures = []
    kinds = M.triangles(export, base_z)
    axes = {name: (axis, sign) for name, axis, sign in M.DIRECTIONS}
    for f in RELIEF_CASES[ident]:
        axis, sign = axes[f[3]]
        c = M.face_test(M.AxisHits(np.concatenate([kinds['opaque'], kinds['glass']]), axis, tuple(size), sign),
                        M.AxisHits(kinds['opaque'], axis, tuple(size), sign), np.array([f[:3]], dtype=np.int64), axis, sign)
        if not M.PLANE_SPREAD < c['depthSpread'][0] <= M.PLANE_SPREAD + M.PRECISION:
            failures.append(f'{ident}: test wall {f} relief is {c["depthSpread"][0]:.9f}, not the plane band rounded up; update RELIEF_CASES')
        if tuple(f) not in flat:
            failures.append(f'{ident}: wall {f} with relief within the plane band is not a connection face')
    return failures


def moving_cases(ident, export, size, base_z, fresh):
    """Each test face is one plane, a moving part enters its outward cell in some pose, and it is not a flat face."""
    failures = []
    kinds = M.triangles(export, base_z)
    axes = {name: (axis, sign) for name, axis, sign in M.DIRECTIONS}
    flat = {tuple(f) for f in fresh['faces']}
    for f in MOVING_CASES[ident]:
        axis, sign = axes[f[3]]
        cell = np.array([f[:3]], dtype=np.int64)
        c = M.face_test(M.AxisHits(np.concatenate([kinds['opaque'], kinds['glass']]), axis, tuple(size), sign),
                        M.AxisHits(kinds['opaque'], axis, tuple(size), sign), cell, axis, sign)
        if not (M.planar(c)[0] and M.moving_in_front(kinds['swept'], cell, axis, sign, np.ones(1, bool))[0]):
            failures.append(f'{ident}: test face {f} is no longer a flat face with a moving part in front; update MOVING_CASES')
        if tuple(f) in flat:
            failures.append(f'{ident}: face {f} with a moving part in front is a flat face')
    return failures



def slope_cases(ident, export, size, base_z, flat):
    """Each test face is covered by a slope outside the eave band and is not a connection face."""
    failures = []
    kinds = M.triangles(export, base_z)
    axes = {name: (axis, sign) for name, axis, sign in M.DIRECTIONS}
    for f in SLOPE_CASES[ident]:
        axis, sign = axes[f[3]]
        c = M.face_test(M.AxisHits(np.concatenate([kinds['opaque'], kinds['glass']]), axis, tuple(size), sign),
                        M.AxisHits(kinds['opaque'], axis, tuple(size), sign), np.array([f[:3]], dtype=np.int64), axis, sign)
        if c['axisAngle'][0] <= M.AXIS_ANGLE:
            failures.append(f'{ident}: test face {f} is no longer covered by a slope outside the eave band; update SLOPE_CASES')
        if tuple(f) in flat:
            failures.append(f'{ident}: test face {f} under a slope outside the eave band is a connection face')
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
    failures, checked, total, eaves = [], 0, 0, 0
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
        if ident in EAVE_CASES:
            seen.add(ident)
            failures += eave_cases(ident, fresh)
        if ident in SLOPE_CASES:
            seen.add(ident)
            failures += slope_cases(ident, export, size, base_z, {tuple(f) for f in fresh['faces']})
        if ident in RELIEF_CASES:
            seen.add(ident)
            failures += relief_cases(ident, export, size, base_z, {tuple(f) for f in fresh['faces']})
        if ident in MOVING_CASES:
            seen.add(ident)
            failures += moving_cases(ident, export, size, base_z, fresh)
        checked += 1
        total += len(fresh['faces'])
        eaves += len(fresh['eaveFaces'])
    for ident in sorted((set(CURVED_CASES) | set(EAVE_CASES) | set(SLOPE_CASES) | set(RELIEF_CASES) | set(MOVING_CASES)) - seen):
        failures.append(f'{ident}: test case building was not measured')
    if failures:
        print('\n'.join('FAIL ' + f for f in failures))
        raise SystemExit(f'Connection face records are stale or not flat ({len(failures)})')
    print(f'Connection face records match fresh measurements: {checked} models, {total} flat faces ({eaves} under an eave); '
          f'every face is one uncurved plane; {sum(len(v) for v in CURVED_CASES.values())} curved test faces excluded; '
          f'{sum(len(v) for v in EAVE_CASES.values())} eave and {sum(len(v) for v in RELIEF_CASES.values())} relief test walls kept, '
          f'{sum(len(v) for v in SLOPE_CASES.values())} slope and {sum(len(v) for v in MOVING_CASES.values())} moving-part test faces excluded')


if __name__ == '__main__':
    main()
