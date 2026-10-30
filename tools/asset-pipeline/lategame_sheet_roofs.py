"""Pitched sheet roofs for the compacted late-game power, nuclear and
rocketry buildings (2026-10-30 roof-variety direction: "some metal roofs,
some wood roofs ... steel roofing"). Native materials only:

- PAINTED (PaintedMetal.IronTeeth): corrugated metal sheet; the harness maps
  whole ribs along each slope (render_lategame_studies.author_extra_native_uvs);
- FORGED (IrregularPlanks_MetalForged.IronTeeth): riveted steel plate;
- ROOF (RoofPlanks.IronTeeth): the vanilla teal roof planks.

`sheet_gable` is `lategame_kit.gable_roof` with the slope material as a
parameter and steel instead of timber trim; it adds nothing to the shared kit.
"""
from frontier_architecture import WOOD, PLANK, IRON, ROOF
from lategame_kit import extrude_profile, _check_positive, PAINTED, FORGED


def sheet_gable(g, x0, y0, x1, y1, eave, ridge, *, ridge_axis='Y', overhang=.12, mat=PAINTED,
                gable_mat=FORGED, trim=IRON, t=.06):
    """Gabled roof of one sloped slab per side in `mat`, closed gable ends in
    `gable_mat`, a steel ridge cap and steel fascia."""
    _check_positive(ridge - eave)
    if ridge_axis == 'Y':
        mid = (x0 + x1) / 2
        lo, hi = y0 - overhang, y1 + overhang
        for side in (-1, 1):
            xe = x0 - overhang if side < 0 else x1 + overhang
            prof = [(xe, eave - .02), (mid, ridge), (mid, ridge + t), (xe, eave - .02 + t)]
            if side > 0:
                prof = list(reversed(prof))
            extrude_profile(g, prof, lo, hi, mat, axis='Y')
            g.box((xe - side * .04, (lo + hi) / 2, eave - .05), (.05, hi - lo, .1), trim)
        for y in (y0, y1):
            d = .07 if y == y0 else -.07
            g.add([(x0, y, eave), (x1, y, eave), (mid, y, ridge - .02)], [(0, 1, 2) if y == y0 else (2, 1, 0)], gable_mat)
            g.add([(x0, y + d, eave), (x1, y + d, eave), (mid, y + d, ridge - .02)],
                  [(2, 1, 0) if y == y0 else (0, 1, 2)], gable_mat)
            for k in (0, 1):
                ax = x0 if k == 0 else x1
                vs = [(ax, y, eave), (mid, y, ridge - .02), (mid, y + d, ridge - .02), (ax, y + d, eave)]
                g.add(vs, [(0, 1, 2, 3) if (k == 0) == (y == y0) else (3, 2, 1, 0)], gable_mat)
        g.box((mid, (lo + hi) / 2, ridge + t + .025), (.12, hi - lo + .04, .06), trim)
    elif ridge_axis == 'X':
        mid = (y0 + y1) / 2
        lo, hi = x0 - overhang, x1 + overhang
        for side in (-1, 1):
            ye = y0 - overhang if side < 0 else y1 + overhang
            prof = [(ye, eave - .02), (mid, ridge), (mid, ridge + t), (ye, eave - .02 + t)]
            if side > 0:
                prof = list(reversed(prof))
            extrude_profile(g, prof, lo, hi, mat, axis='X')
            g.box(((lo + hi) / 2, ye - side * .04, eave - .05), (hi - lo, .05, .1), trim)
        for x in (x0, x1):
            d = .07 if x == x0 else -.07
            g.add([(x, y0, eave), (x, y1, eave), (x, mid, ridge - .02)], [(2, 1, 0) if x == x0 else (0, 1, 2)], gable_mat)
            g.add([(x + d, y0, eave), (x + d, y1, eave), (x + d, mid, ridge - .02)],
                  [(0, 1, 2) if x == x0 else (2, 1, 0)], gable_mat)
            for k in (0, 1):
                ay = y0 if k == 0 else y1
                vs = [(x, ay, eave), (x, mid, ridge - .02), (x + d, mid, ridge - .02), (x + d, ay, eave)]
                g.add(vs, [(3, 2, 1, 0) if (k == 0) == (x == x0) else (0, 1, 2, 3)], gable_mat)
        g.box(((lo + hi) / 2, mid, ridge + t + .025), (hi - lo + .04, .12, .06), trim)
    else:
        raise ValueError('ridge_axis must be X or Y')


# Strip width per finish, as lategame_roofdeck_parts.STRIP: each plate or
# board is its own box, so it takes its own native texture island instead of
# one strip stretched over the whole roof.
STRIP = {FORGED: .5, PAINTED: .5, PLANK: .25, WOOD: .25, ROOF: .3, IRON: 1.0}


def plate_deck(g, x0, y0, x1, y1, z, *, mat=FORGED, t=.16, overhang=.0):
    """Flat roof slab whose top is z, finished in `mat` (riveted steel plate,
    timber decking or corrugated sheet instead of concrete), laid as separate
    plates or boards running along the longer side."""
    _check_positive(x1 - x0, y1 - y0)
    a0, b0, a1, b1 = x0 - overhang, y0 - overhang, x1 + overhang, y1 + overhang
    along_x = (a1 - a0) >= (b1 - b0)
    u0, u1 = (b0, b1) if along_x else (a0, a1)
    n = max(1, round((u1 - u0) / STRIP.get(mat, .5)))
    for i in range(n):
        v0, v1 = u0 + (u1 - u0) * i / n, u0 + (u1 - u0) * (i + 1) / n
        if along_x:
            g.box(((a0 + a1) / 2, (v0 + v1) / 2, z - t / 2), (a1 - a0, v1 - v0, t), mat)
        else:
            g.box(((v0 + v1) / 2, (b0 + b1) / 2, z - t / 2), (v1 - v0, b1 - b0, t), mat)
