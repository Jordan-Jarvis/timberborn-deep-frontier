"""industrial_budget.py helpers as the industrial family uses them.

CementKiln, ConcreteMixer, StoneCrusher, MineralQuarry and the two pits import
their detail kit from here (the first four take the lean_* variants at the end
of this file). Everything else is industrial_budget.py; the fastener
helpers carry FASTENERS_INDUSTRIAL (see there): longer heads and diagonal
square heads, because these models have no bevel modifier. Other families
import industrial_budget.py directly and keep FASTENERS_SHARED.
"""
import industrial_budget as _b
from industrial_budget import (MODELS, BEVEL, open_box, prism, band, open_beam, rock, rock_heap, cask, round_pipe,
                               cage_lamp, machinery_shell, wheel, gauge)

_F = _b.FASTENERS_INDUSTRIAL


def bolt(g, p, axis='Y', r=.022, outward=None, n=6):
    _b.bolt(g, p, axis, r, outward, n, fasteners=_F)


def steel_bolt(g, p, axis='Y', r=.022):
    _b.steel_bolt(g, p, axis, r, fasteners=_F)


def square_nut(g, p, axis, r, outward):
    _b.square_nut(g, p, axis, r, outward, fasteners=_F)


def bracket(g, x, y, z, w=.22):
    _b.bracket(g, x, y, z, w, fasteners=_F)


def timber_column(g, x, y, bottom, top, w=.19):
    _b.timber_column(g, x, y, bottom, top, w, fasteners=_F)


def beam_joint(g, a, b, w=.18, depth=.18):
    _b.beam_joint(g, a, b, w, depth, fasteners=_F)


def sheet_roof(g, x0, y0, x1, y1, z0, z1, seed):
    _b.sheet_roof(g, x0, y0, x1, y1, z0, z1, seed, fasteners=_F)


def bin(g, p, size, stone=None, seed=0, *, proud_rivets=False):
    _b.bin(g, p, size, stone, seed, proud_rivets=proud_rivets, fasteners=_F)


# Lean style: the 12,000-triangle workshop cap (2026-10-29).
# CementKiln, ConcreteMixer, StoneCrusher and MineralQuarry import the lean_*
# helpers below under the kit names; the two pits keep the helpers above, so
# their generators still build their saved scenes. Same silhouettes, by
# construction rather than by later repair:
# - no collar, plate or roof fasteners (5 cm heads, 2-3 px at normal zoom);
# - no faces that only face down (the game camera always looks down on them)
#   on small parts that rest on something, and no roof-panel sides that touch
#   the next panel or lie inside the edge beams. Posts, footings and masonry
#   stay closed boxes: a closed primitive is a cull volume (enclosed_cull.py)
#   for the beam ends, wall ends and trim buried in it;
# - 6-8 sides on small round parts (pipes keep industrial_budget.round_pipe's
#   8, whose facets meet at elbows without coplanar overlaps), 12-16 on drums
#   and tyres, fewer and simpler rocks.
LEAN_MODELS = ('CementKiln', 'ConcreteMixer', 'StoneCrusher', 'MineralQuarry')

import math as _math
import random as _random
from mathutils import Vector as _Vector
from frontier_architecture import WOOD as _WOOD, PLANK as _PLANK, IRON as _IRON, ROOF as _ROOF, BRASS as _BRASS


def lean_bracket(g, x, y, z, w=.22):
    """bracket's four collar plates (same sizes and places), no nuts."""
    for dx in (-1, 1):
        open_box(g, (x + dx * (w / 2 + .012), y, z), (.028, w + .052, .23), _IRON, ('-x' if dx > 0 else '+x', '-z'))
    for dy in (-1, 1):
        open_box(g, (x, y + dy * (w / 2 + .012), z), (w - .004, .028, .23), _IRON, ('-y' if dy > 0 else '+y', '-x', '+x', '-z'))


def lean_timber_column(g, x, y, bottom, top, w=.19, top_collar_only=False):
    """timber_column with lean collars. top_collar_only: a tall post keeps
    only its head collar."""
    g.box((x, y, (bottom + top) / 2), (w, w, top - bottom), _WOOD)
    collar_levels = ((bottom + top) / 2,) if top - bottom < .46 else (bottom + .115, top - .115)
    if top_collar_only:
        collar_levels = collar_levels[-1:]
    for level in collar_levels:
        lean_bracket(g, x, y, level, w)


def lean_beam_joint(g, a, b, w=.18, depth=.18):
    """beam_joint: the same beam and fish plates, no nuts."""
    g.beam(a, b, w, depth, _WOOD)
    span = _math.dist(a, b)
    plate_stations = () if span < .30 else ((.5,) if span < .60 else (.12, .88))
    for t in plate_stations:
        p = tuple(a[i] + (b[i] - a[i]) * t for i in range(3))
        if abs(b[0] - a[0]) >= abs(b[1] - a[1]):
            g.box((p[0], p[1] - .12, p[2]), (.27, .035, depth + .06), _IRON)
        else:
            g.box((p[0] - .12, p[1], p[2]), (.035, .27, depth + .06), _IRON)


def _beam_faces(g, a, b, width, depth, mat, keep):
    """Geometry.beam's corners; keep(normal) selects which of its six faces exist."""
    a, b = _Vector(a), _Vector(b)
    direction = b - a
    if direction.length < .00001:
        raise ValueError('Zero-length authored beam')
    rotation = direction.to_track_quat('Z', 'Y')
    corners = [a + rotation @ _Vector((x * width / 2, y * depth / 2, z * direction.length)) for z in (0, 1) for y in (-1, 1) for x in (-1, 1)]
    faces = [(2, 3, 1, 0), (5, 7, 6, 4), (1, 5, 4, 0), (6, 7, 3, 2), (4, 6, 2, 0), (3, 7, 5, 1)]
    chosen = []
    for f in faces:
        p0, p1, p2 = (corners[i] for i in f[:3])
        if keep((p1 - p0).cross(p2 - p0).normalized()):
            chosen.append(f)
    g.add(corners, chosen, mat)


def lean_sheet_roof(g, x0, y0, x1, y1, z0, z1, seed, corner_collars=False):
    """sheet_roof's panels, edging, straps and corner shoes. Panels have no
    underside and no sides: those touch the next panel, and the outer ones
    lie on the centre planes of the x0/x1 edge beams. No bolts, and corner
    collars (lean) only with corner_collars, where they close a registered
    face."""
    count = _math.ceil((x1 - x0) / .28)
    width = (x1 - x0) / count
    for i in range(count):
        x = x0 + (i + .5) * width
        _beam_faces(g, (x, y0, z0), (x, y1, z1), width, .045, _ROOF, lambda n: n.z >= -.5 and abs(n.x) <= .5)
    for x in (x0, x1):
        g.beam((x, y0, z0 - .035), (x, y1, z1 - .035), .13, .14, _WOOD)
    for y, z in ((y0, z0), (y1, z1)):
        g.beam((x0, y, z - .055), (x1, y, z - .055), .15, .16, _WOOD)
        for x in (x0, x1):
            if corner_collars:
                lean_bracket(g, x, y, z - .07, .16)
            open_box(g, (x, y, z + .050), (.22, .22, .025), _IRON, ('-z',))
    for t in (.35, .72):
        y = y0 + (y1 - y0) * t
        z = z0 + (z1 - z0) * t + .03
        g.beam((x0, y, z), (x1, y, z), .06, .018, _IRON)
    del seed


def lean_rock(g, p, size, mat, seed, n=5):
    """Chunky cobble: an n-sided lower and middle ring and a top point, no
    underside (it rests on a load or a bed). Planar triangles."""
    rng = _random.Random(seed)
    v = []
    for z, factor in ((-.45, .78), (.05, 1)):
        for i in range(n):
            a = 2 * _math.pi * (i + rng.uniform(-.12, .12)) / n
            jitter = rng.uniform(.86, 1.08)
            v.append((p[0] + _math.cos(a) * size[0] * factor * jitter / 2,
                      p[1] + _math.sin(a) * size[1] * factor * jitter / 2, p[2] + z * size[2]))
    v.append((p[0] + rng.uniform(-.08, .08) * size[0], p[1] + rng.uniform(-.08, .08) * size[1], p[2] + .45 * size[2]))
    f = []
    for i in range(n):
        a, b = i, (i + 1) % n
        f.extend([(a, b, b + n), (a, b + n, a + n), (a + n, b + n, 2 * n)])
    g.add(v, f, mat)


def lean_rock_heap(g, x0, y0, x1, y1, z, mat, seed, count, size=(.12, .24)):
    rng = _random.Random(seed)
    for i in range(count):
        s = rng.uniform(*size)
        lean_rock(g, (rng.uniform(x0, x1), rng.uniform(y0, y1), z + s * .3), (s, s * .9, s * .8), mat, seed * 100 + i)


def lean_bin(g, p, size, stone=None, seed=0):
    """bin: floor, plank courses about 0.25 high, corner irons (no rivets),
    and a stone load: a bed of the stone just below the rim (it reads as a
    full bin) with a few large stones on it."""
    x, y, z = p
    w, d, h = size
    rows = max(2, _math.ceil(h / .25))
    g.box((x, y, z + .045), (w - .12, d - .12, .09), _WOOD)
    for j in range(rows):
        level = z + (j + .5) * h / rows
        for xx in (x - w / 2 + .03, x + w / 2 - .03):
            g.box((xx, y, level), (.06, d - .12, h / rows - .01), _PLANK)
        for yy in (y - d / 2 + .03, y + d / 2 - .03):
            g.box((x, yy, level), (w, .06, h / rows - .01), _PLANK)
    for xx in (x - w / 2 + .055, x + w / 2 - .055):
        for yy in (y - d / 2 + .055, y + d / 2 - .055):
            g.box((xx, yy, z + h / 2), (.09, .09, h + .03), _IRON)
    if stone is not None:
        open_box(g, (x, y, z + h * .70), (w - .12, d - .12, .06), stone, ('-z',))
        lean_rock_heap(g, x - w * .35, y - d * .32, x + w * .35, y + d * .32, z + h * .76, stone, seed,
                       max(4, int(w * d * 3.5)), (.18, .30))


def lean_cask(g, p, r=.43, h=1.0, water=False):
    """cask: 8 staves bulging at mid-height, two hoops, a lid."""
    from reference_materials import WATER
    x, y, z = p
    n = 8
    levels = [(0, r * .88), (.50 * h, r), (h, r * .88)]
    for i in range(n):
        a0 = (i + .025) * 2 * _math.pi / n
        a1 = (i + .975) * 2 * _math.pi / n
        v = []
        for zz, rr in levels:
            v.extend([(x + _math.cos(a0) * rr, y + _math.sin(a0) * rr, z + zz), (x + _math.cos(a1) * rr, y + _math.sin(a1) * rr, z + zz)])
        g.add(v, [(j * 2, j * 2 + 1, j * 2 + 3, j * 2 + 2) for j in range(len(levels) - 1)], _PLANK)
    for zz in (.22 * h, .78 * h):
        rr = r * (.88 + .12 * (1 - abs(zz / h - .5) * 2))
        band(g, (x, y, z + zz), rr + .015, .032, .075, _IRON, 'Z', n)
    if water:
        prism(g, (x, y, z + h - .07), r * .85, .025, WATER, 'Z', n, (False, True))
    else:
        prism(g, (x, y, z + h - .014), r * .86, .035, _PLANK, 'Z', n, (False, True))


def lean_cage_lamp(g, x, y, z):
    """cage_lamp: bracket arm, 6-sided glass and caps, no cage wires and no
    downward faces (the camera always looks down on a hanging lamp)."""
    from reference_materials import GLOW
    g.beam((x, y + .05, z + .16), (x, y - .13, z + .16), .035, mat=_IRON)
    prism(g, (x, y - .13, z), .06, .19, GLOW, 'Z', 6, (False, True))
    for zz in (z - .12, z + .12):
        prism(g, (x, y - .13, zz), .085, .025, _IRON, 'Z', 6, (False, True))


def lean_wheel(g, p, r, axis='X', mat=_IRON, accent=_BRASS, segments=12, spokes=4):
    """wheel: one rim, 6-sided hub, spokes without their buried hub ends."""
    del accent
    band(g, p, r, .055, .08, mat, axis, segments, inner=True)
    prism(g, p, .09, .17, _IRON, axis, 6)
    for i in range(spokes):
        a = i * 2 * _math.pi / spokes
        end = (p[0], p[1] + _math.cos(a) * r * .95, p[2] + _math.sin(a) * r * .95) if axis == 'X' else (p[0] + _math.cos(a) * r * .95, p[1], p[2] + _math.sin(a) * r * .95)
        start = (p[0], p[1] + _math.cos(a) * .08, p[2] + _math.sin(a) * .08) if axis == 'X' else (p[0] + _math.cos(a) * .08, p[1], p[2] + _math.sin(a) * .08)
        open_beam(g, start, end, .045, mat=mat, end=False)


def lean_gauge(g, x, y, z, r=.09, rim_material=_BRASS):
    """gauge: 8-sided case and glass (front caps only) and the needle."""
    from reference_materials import GLASS
    from industrial_facades import CYAN
    prism(g, (x, y, z), r, .045, rim_material, 'Y', 8, (True, False))
    prism(g, (x, y - .03, z), r * .79, .016, GLASS, 'Y', 8, (True, False))
    g.beam((x, y - .046, z), (x + r * .48, y - .046, z + r * .42), .009, mat=CYAN)


def lean_machinery_shell(g, p, profile, axis='Y', segments=16):
    """machinery_shell: the shell of revolution and banded joints, no pins."""
    x, y, z = p

    def point(a, b, c):
        return (x + c, y + a, z + b) if axis == 'X' else (x + a, y + c, z + b)
    verts = [point(_math.cos(i * _math.pi * 2 / segments) * r, _math.sin(i * _math.pi * 2 / segments) * r, t) for t, r in profile for i in range(segments)]
    faces = [tuple(reversed(range(segments))), tuple(range((len(profile) - 1) * segments, len(profile) * segments))]
    for level in range(len(profile) - 1):
        for i in range(segments):
            faces.append((level * segments + i, level * segments + (i + 1) % segments, (level + 1) * segments + (i + 1) % segments, (level + 1) * segments + i))
    if axis == 'Y':
        faces = [tuple(reversed(f)) for f in faces]
    g.add(verts, faces, _IRON)
    # Each joint band's flats clear the shell's corners by 1.2 cm.
    for t, r in profile[1:-1]:
        band(g, point(0, 0, t), r / _math.cos(_math.pi / segments) + .012, .035, .075, _IRON, axis, segments)


def lean_wall(g, x0, y, x1, top, bottom=.18, inner=None):
    """frontier_architecture.wall: the same boards and inset trim; the boards'
    touching sides and their undersides are left out, and with inner ('-y' or
    '+y') the board faces that look into a closed room."""
    if inner not in (None, '-y', '+y'):
        raise ValueError('A wall closes a room on its -y or +y side')
    n = _math.ceil((x1 - x0) / .15)
    width = (x1 - x0) / n
    for i in range(n):
        skip = ['-z'] + (['-x'] if i > 0 else []) + (['+x'] if i < n - 1 else []) + ([inner] if inner else [])
        open_box(g, (x0 + (i + .5) * width, y, (top + bottom) / 2), (width, .07, top - bottom), _PLANK, skip)
    if x1 - x0 <= .04:
        raise ValueError('Plank wall needs space for its inset trim ends')
    for z in (bottom + .07, top - .07):
        g.box(((x0 + x1) / 2, y - .035, z), (x1 - x0 - .04, .12, .10), _WOOD)


def skin_board(g, p, size, axis, index, count, mat, inner):
    """One board of a plank skin of `count` boards along `axis` ('X' or 'Y'):
    the sides it shares with its neighbours, its underside and the face
    `inner` ('+x', '-y', ...) that looks into a closed room are left out."""
    lo, hi = ('-x', '+x') if axis == 'X' else ('-y', '+y')
    skip = ['-z'] + ([lo] if index > 0 else []) + ([hi] if index < count - 1 else []) + ([inner] if inner else [])
    open_box(g, p, size, mat, skip)
