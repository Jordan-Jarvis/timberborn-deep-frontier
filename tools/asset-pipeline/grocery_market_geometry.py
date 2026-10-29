"""Deep Frontier Grocery Market: art study after docs/art/concepts/Grocery Store.png.

Reference: the four isometric views and the detail panels of the approved
concept sheet. The top-down view and its printed tile counts are not used.

Hero element: a long, low two-storey timber market hall whose teal gable
roof carries a raised, warmly lit clerestory monitor along its ridge.
Roof type: long gable along X with a central monitor, a front cross-gable,
dormers, and low pent roofs over the market arcade, the left stall wing and
the rear loading dock.

Authored coordinates: one unit is one tile across and one layer up. X runs
across the front, Y runs back, Z is up; the market front faces -Y.

Grid contract (for gameplay integration):
  FOOTPRINT       9 x 6 tiles, x 0..9, y 0..6 (the rear dock and water tower
                  were removed 2026-10-22: no forced decoration beyond walls).
  Ground door     x 4.5 on the y = 2 cell boundary, layer 0, opening -Y.
  Balcony door    x 6.5 on the y = 2 cell boundary, layer 2, opening -Y.
  Balcony deck    x 6..9, y 1..2, top at layer 2.
  Hall frame      outer post faces on x = 1, x = 8, y = 2, y = 6.
  Post lines      arcade front y = 0; stall wing x = 0 (y 1..6).
  Stair bay       x 8..9, y 2..4: clear for two player-built native stairs
                  rising toward -Y onto the open balcony edge at y = 2.
"""
import math
import random
from mathutils import Vector, Quaternion

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from reference_materials import GLOW, CIVIC_CONCRETE as CONCRETE, CIVIC_FORGED_PANEL as FORGED
from architectural_windows import window as native_window
from native_window_atlas import atlas_window
from native_building_assets import barrel, water_barrel, plant
from walkway_geometry import RailAssembly
from lategame_kit import emitter, extrude_profile, revolve

FOOTPRINT = (9, 6)
CREAM = 27        # Plaster_White.IronTeeth: cream awning stripes, painted sign
ORANGE = 28       # Plaster_Orange.IronTeeth: oranges, carrots, pumpkins
LIGHTWOOD = 31    # BaseWood_Brown.Folktails: wicker baskets
DETAILS = BRASS   # Details.IronTeeth: crates, sacks, red/green/purple banner cloth

# Explicit atlas islands (u0, u1, v0, v1) on the shipped textures.
RED = (.862, .952, .842, .878)        # Details: solid red banner cloth
GREEN = (.862, .952, .682, .708)      # Details: solid green banner cloth
PURPLE = (.862, .952, .522, .556)     # Details: solid blueberry banner cloth
SACK = (.507, .743, .512, .988)       # Details: drawn grain sack
CRATE_SIDE = (.004, .246, .004, .246)     # Details: framed crate side
CRATE_BRACE = (.004, .246, .254, .496)    # Details: braced crate side
CRATE_TOP = (.254, .496, .004, .246)      # Details: crate lid planks
WHOLE = (.03, .97, .03, .97)               # Plaster sheets
WICKER = (.512, .742, .515, .985)          # BaseWood_Brown: narrow boards
# MetalForged board islands (pixel columns of the 1024 px sheet, outline
# included), cut between the iron bands: warm boards without the grey gaps.
BOARD_PX = ((10, 118), (161, 238), (271, 353), (405, 478), (528, 620), (667, 735), (798, 864), (920, 994))
BOARD_W = .18      # one native board per 0.18 tile of wall
BARREL = (.505, .995, .005, .495)          # Details: banded barrel staves
METAL_PLATE = (.02, .48, .52, .98)         # BaseMetal: plain plate tile
BLUE = (.012, .075, .56, .98)              # Details: solid blue banner cloth (tin labels)
HUSK = (.77, .99, .02, .22)                # BaseWood_Brown: plain tan sheet (corn husk)

# Stock shown on the displays: the six foods of frontier_progression.json
# groceryStore.stock. Each food has three cumulative fill stages, separate
# objects GroceryStock.<Food>.<1|2|3>, switched by GroceryStockDisplay.cs.
STOCK_FOODS = ('CannedFish', 'PackagedFood', 'AlgaeRation', 'CornRation', 'FermentedCassava', 'FermentedSoybean')
STOCK_STAGES = 3

TILE_WALL = 1.5    # one MetalForged board sheet (8 boards) per 1.5 tiles
TILE_PLANK = 1.5   # one IrregularPlanks sheet per 1.5 tiles (soffits)
TILE_ROOF = 3.5    # one RoofPlanks sheet (16 boards, 4 courses) per 3.5 tiles
SLAB = .08         # roof sheet thickness, normal to the slope

# Main hall and roof. Walls stand on lines set in from the tile edges by
# half a corner post, so every corner post's outer face is on a tile edge:
# x = 1 and 8, y = 2 and 6. The base course is flush with those edges.
EDGE_X0, EDGE_X1, EDGE_Y0, EDGE_Y1 = 1.0, 8.0, 2.0, 6.0
HX0, HX1, HY0, HY1 = EDGE_X0 + .12, EDGE_X1 - .12, EDGE_Y0 + .12, EDGE_Y1 - .12
K = .85                           # main and cross-gable pitch (rise per run)
VT = SLAB * math.sqrt(1 + K * K)  # vertical slab thickness
WALL_TOP = 3.9                    # roof top surface above the eave wall lines
RIDGE_Y = (HY0 + HY1) / 2
RIDGE_TOP = WALL_TOP + K * (RIDGE_Y - HY0)
EAVE_OH, GABLE_OH = .30, .105  # gable slab ends 15 mm inside the frame edges; barges reach the edge
POST_C, POST_M = .24, .20         # corner and bay posts
GIRT_D = .16                      # girt depth across the wall
FLOOR_GIRT, TOP_PLATE = (1.90, .14), (3.73, .14)
MON_X0, MON_X1, MON_Y0, MON_Y1 = 3.0, 6.0, 3.5, 4.5

ACCESS = {
    'footprint': list(FOOTPRINT),
    'doors': [{'id': 'MainDoor', 'cell': [4, 1], 'position': [4.5, 2.0, 0], 'outward': [0, -1]},
              {'id': 'BalconyDoor', 'cell': [6, 1], 'position': [6.5, 2.0, 2], 'outward': [0, -1]}],
    'balcony': {'layer': 2, 'bounds': [6.0, 1.0, 9.0, 2.0],
                'openEdges': [{'from': [8.0, 2.0], 'to': [9.0, 2.0], 'for': 'player stairs'}]},
    'stairBay': {'bounds': [8, 2, 9, 4], 'rise': 'two native stairs: layer 0 entered from y=4..5, layer 2 at y=2'},
    'groundWalk': {'mainDoorApproach': [4.0, 0.0, 5.0, 2.0], 'stairApproach': [8.0, 4.0, 9.0, 5.0]},
    'internalStairs': False,
    'frameEdges': {'x': [EDGE_X0, EDGE_X1], 'y': [EDGE_Y0, EDGE_Y1]},
}


# ------------------------------------------------------------------ primitives

def _newell(points):
    n = Vector((0, 0, 0))
    for a, b in zip(points, points[1:] + points[:1]):
        n.x += (a.y - b.y) * (a.z + b.z)
        n.y += (a.z - b.z) * (a.x + b.x)
        n.z += (a.x - b.x) * (a.y + b.y)
    return n


def face(g, points, normal, mat, uvs=None):
    """One planar polygon wound to face `normal` (outward)."""
    points = [Vector(p) for p in points]
    d = _newell(points).dot(Vector(normal))
    if d == 0:
        raise ValueError('Degenerate or edge-on authored face')
    if d < 0:
        points.reverse()
        uvs = list(reversed(uvs)) if uvs is not None else None
    g.add([tuple(p) for p in points], [tuple(range(len(points)))], mat)
    if uvs is not None:
        g.face_uvs[-1] = [tuple(u) for u in uvs]


def _clip(poly, axis, value, keep_ge):
    out = []
    for i, p in enumerate(poly):
        q = poly[(i + 1) % len(poly)]
        pin = p[axis] >= value - 1e-9 if keep_ge else p[axis] <= value + 1e-9
        qin = q[axis] >= value - 1e-9 if keep_ge else q[axis] <= value + 1e-9
        if pin:
            out.append(p)
        if pin != qin:
            t = (value - p[axis]) / (q[axis] - p[axis])
            out.append((p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t))
    return out


def _area2(poly):
    return abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1]))) / 2


def tiled(g, frame, poly, normal, mat, tile, rect=(0, 1, 0, 1)):
    """A convex polygon in a surface frame, cut on a tile grid. Each cell
    addresses one whole texture island, so UVs stay inside the material.
    `tile` may be (u, v); `rect` may be a function of the cell (i, j)."""
    tu, tv = tile if isinstance(tile, tuple) else (tile, tile)
    us = [p[0] for p in poly]
    vs = [p[1] for p in poly]
    for i in range(math.floor(min(us) / tu + 1e-7), math.ceil(max(us) / tu - 1e-7)):
        for j in range(math.floor(min(vs) / tv + 1e-7), math.ceil(max(vs) / tv - 1e-7)):
            c = poly
            for axis, value, ge in ((0, i * tu, True), (0, (i + 1) * tu, False),
                                    (1, j * tv, True), (1, (j + 1) * tv, False)):
                c = _clip(c, axis, value, ge)
                if len(c) < 3:
                    break
            clean = []
            for p in c:
                if not clean or abs(p[0] - clean[-1][0]) + abs(p[1] - clean[-1][1]) > 1e-7:
                    clean.append(p)
            if len(clean) > 1 and abs(clean[0][0] - clean[-1][0]) + abs(clean[0][1] - clean[-1][1]) < 1e-7:
                clean.pop()
            if len(clean) < 3 or _area2(clean) < 1e-6:
                continue
            r = rect(i, j) if callable(rect) else rect
            uvs = [(r[0] + (u / tu - i) * (r[1] - r[0]),
                    r[2] + (v / tv - j) * (r[3] - r[2])) for u, v in clean]
            face(g, [frame(u, v) for u, v in clean], normal, mat, uvs)


def _wall_frame(axis, plane, outward):
    if axis == 'X':
        return (lambda u, v: (u, plane, v)), (0, outward, 0)
    return (lambda u, v: (plane, u, v)), (outward, 0, 0)


def wall(g, axis, plane, outward, a, b, z0, z1, holes=()):
    """Single opaque board skin (outward face only) in warm native boards,
    with rectangular holes (u0, u1, z0, z1) that native portals close."""
    frame, normal = _wall_frame(axis, plane, outward)
    us = sorted({a, b, *[c for h in holes for c in h[:2] if a < c < b]})
    zs = sorted({z0, z1, *[c for h in holes for c in h[2:] if z0 < c < z1]})
    for u0, u1 in zip(us, us[1:]):
        for v0, v1 in zip(zs, zs[1:]):
            cu, cv = (u0 + u1) / 2, (v0 + v1) / 2
            if any(h[0] < cu < h[1] and h[2] < cv < h[3] for h in holes):
                continue
            tiled(g, frame, [(u0, v0), (u1, v0), (u1, v1), (u0, v1)], normal, FORGED, (BOARD_W, TILE_WALL), board)


def board(i, j):
    """One whole native board per wall column, varied along the wall."""
    a, b = BOARD_PX[(i * 5 + j * 3) % len(BOARD_PX)]
    return (a / 1024, b / 1024, .41, .59)


def gable(g, axis, plane, outward, poly):
    frame, normal = _wall_frame(axis, plane, outward)
    tiled(g, frame, poly, normal, FORGED, (BOARD_W, TILE_WALL), board)


def obox(g, c, ex, ey, ez, mat):
    """Oriented box from a centre and three half-axis vectors."""
    c, ex, ey, ez = (Vector(v) for v in (c, ex, ey, ez))
    if ex.cross(ey).dot(ez) < 0:
        ez = -ez
    pts = [c + sx * ex + sy * ey + sz * ez for sz in (-1, 1)
           for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    g.add([tuple(p) for p in pts],
          [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)


def member(g, a, b, w, h, mat=WOOD, up=(0, 0, 1)):
    """Timber member from a to b: w across (horizontal), h in the vertical plane."""
    a, b = Vector(a), Vector(b)
    ex = (b - a) / 2
    d = ex.normalized()
    side = d.cross(Vector(up))
    if side.length < 1e-6:
        side = Vector((1, 0, 0))
    side.normalize()
    ez = side.cross(d).normalized()
    if ez.z < 0:
        ez = -ez
    obox(g, (a + b) / 2, ex, side * w / 2, ez * h / 2, mat)


def slab(g, o, U, S, L, W, *, mat=ROOF, under=PLANK, edge=WOOD, tile=TILE_ROOF):
    """Roof sheet: tiled native top, plank soffit, timber edges. `o` is the
    top-surface corner at the eave, U along the eave, S up the slope."""
    o, U, S = Vector(o), Vector(U).normalized(), Vector(S).normalized()
    N = U.cross(S).normalized()
    if N.z < 0:
        N = -N
    tiled(g, lambda u, s: tuple(o + U * u + S * s), [(0, 0), (L, 0), (L, W), (0, W)], N, mat, tile)
    tiled(g, lambda u, s: tuple(o + U * u + S * s - N * SLAB), [(0, 0), (L, 0), (L, W), (0, W)], -N, under, TILE_PLANK)
    t = [o, o + U * L, o + U * L + S * W, o + S * W]
    b = [p - N * SLAB for p in t]
    for i, n in ((0, -S), (1, U), (2, S), (3, -U)):
        j = (i + 1) % 4
        face(g, [t[i], t[j], b[j], b[i]], n, edge)
    return N


def paint(g, first, mat, rect):
    """Assign a bounded native atlas island to every face added since `first`."""
    for i in range(first, len(g.faces)):
        g.materials[i] = mat
        pts = [Vector(g.vertices[k]) for k in g.faces[i]]
        n = _newell(pts)
        axis = max(range(3), key=lambda a: abs(n[a]))
        a, b = [k for k in range(3) if k != axis]
        us = [p[a] for p in pts]
        vs = [p[b] for p in pts]
        su = max(max(us) - min(us), 1e-6)
        sv = max(max(vs) - min(vs), 1e-6)
        g.face_uvs[i] = [(rect[0] + (u - min(us)) / su * (rect[1] - rect[0]),
                          rect[2] + (v - min(vs)) / sv * (rect[3] - rect[2])) for u, v in zip(us, vs)]


def tiled_box(g, c, size, mat, tile=.8, rect=(0, 1, 0, 1)):
    """Axis-aligned solid whose six faces each tile one native island."""
    x, y, z = c
    a, b, h = (s / 2 for s in size)
    for axis, plane, out, lo, hi in (('X', y - b, -1, x - a, x + a), ('X', y + b, 1, x - a, x + a),
                                     ('Y', x - a, -1, y - b, y + b), ('Y', x + a, 1, y - b, y + b)):
        frame, normal = _wall_frame(axis, plane, out)
        tiled(g, frame, [(lo, z - h), (hi, z - h), (hi, z + h), (lo, z + h)], normal, mat, tile, rect)
    for zz, n in ((z - h, -1), (z + h, 1)):
        tiled(g, lambda u, v, zz=zz: (u, v, zz), [(x - a, y - b), (x + a, y - b), (x + a, y + b), (x - a, y + b)],
              (0, 0, n), mat, tile, rect)


# ------------------------------------------------------------------ structure

def footing(g, x, y, w=.20, fx=0, fy=0):
    """Cast footing from the ground (z = 0) with a steel shoe; the post
    starts inside the shoe. fx/fy = -1 or +1 puts the post's outer face on a
    tile edge: the footing is then flush with that face and grows inward,
    and the shoe steps 15 mm back so no two faces share the edge plane."""
    def span(c, f, ext, recess):
        if f < 0:
            return c - w / 2 + recess, c + w / 2 + 2 * ext
        if f > 0:
            return c - w / 2 - 2 * ext, c + w / 2 - recess
        return c - w / 2 - ext, c + w / 2 + ext
    for (ax, bx), (ay, by), z, h, mat in ((span(x, fx, .08, 0), span(y, fy, .08, 0), .09, .18, CONCRETE),
                                          (span(x, fx, .04, .015), span(y, fy, .04, .015), .20, .08, IRON)):
        g.box(((ax + bx) / 2, (ay + by) / 2, z), (bx - ax, by - ay, h), mat)


def free_post(g, x, y, top, w=.20, fx=0, fy=0):
    footing(g, x, y, w, fx, fy)
    g.box((x, y, (.22 + top) / 2), (w, w, top - .22), WOOD)


# Triangle budget, 20k grand cap (2026-10-29): no rivet heads (the civic shell
# family's rule, civic_isometric_geometry.collar); the plates and caps stay.

def corner_plates(g, x, y, z, sx, sy, h=.30):
    """Folded steel corner plate at one real frame joint (corner post, girts)."""
    half = POST_C / 2
    fy, fx = y + sy * half, x + sx * half
    # Plate on the Y-facing side; its end buries into the X-facing plate.
    ya, yb = sorted((fy + sy * .02, fy - sy * .05))
    xa, xb = sorted((x + sx * (half + .008), x - sx * .42))
    g.box(((xa + xb) / 2, (ya + yb) / 2, z), (xb - xa, yb - ya, h), IRON)
    # Plate on the X-facing side; its end buries into the first plate.
    xc, xd = sorted((fx + sx * .02, fx - sx * .05))
    yc, yd = sorted((y + sy * (half + .005), y - sy * .42))
    g.box(((xc + xd) / 2, (yc + yd) / 2, z), (xd - xc, yd - yc, h - .03), IRON)


def frame_wall(g, axis, plane, a, b, posts):
    """Dark structural frame on a wall line: posts, floor girt and top plate.
    `posts` are (u, bottom, top, width) along the wall."""
    for u, bottom, top, w in posts:
        p = (u, plane) if axis == 'X' else (plane, u)
        g.box((p[0], p[1], (bottom + top) / 2), (w, w, top - bottom), WOOD)
    for zc, h in (FLOOR_GIRT, TOP_PLATE):
        lo, hi = a + .09, b - .09
        c = ((lo + hi) / 2, plane) if axis == 'X' else (plane, (lo + hi) / 2)
        size = (hi - lo, GIRT_D, h) if axis == 'X' else (GIRT_D, hi - lo, h)
        g.box((c[0], c[1], zc), size, WOOD)


def course(g, axis, edge, out, a, b, gaps=()):
    """Cast concrete base course under the board skin (late-game plinth),
    its outer face on the tile edge and 19 cm deep inward."""
    runs, start = [], a
    for lo, hi in sorted(gaps):
        runs.append((start, lo))
        start = hi
    runs.append((start, b))
    for lo, hi in runs:
        if hi - lo < .02:
            continue
        c = edge - out * .095
        if axis == 'X':
            g.box(((lo + hi) / 2, c, .15), (hi - lo, .19, .30), CONCRETE)
        else:
            g.box((c, (lo + hi) / 2, .15), (.19, hi - lo, .30), CONCRETE)


def top_main(y):
    return WALL_TOP + K * min(y - HY0, HY1 - y)


def pipe(g, points, w=.07):
    """Square steel pipe run; segments butt into proud elbow blocks."""
    points = [Vector(p) for p in points]
    for i, (a, b) in enumerate(zip(points, points[1:])):
        d = (b - a).normalized()
        a2 = a + d * (w / 2 + .005) if i > 0 else a
        b2 = b - d * (w / 2 + .005) if i < len(points) - 2 else b
        member(g, a2, b2, w, w, IRON)
    for p in points[1:-1]:
        g.box(tuple(p), (w + .03, w + .03, w + .03), IRON)


def lantern(g, x, y, hang, drop=.10):
    """Small hanging lantern under a beam whose underside is at `hang`."""
    g.box((x, y, hang - drop / 2 + .01), (.025, .025, drop + .02), IRON)
    zc = hang - drop - .13
    g.box((x, y, zc + .115), (.17, .17, .03), IRON)
    g.box((x, y, zc), (.10, .10, .20), GLOW)
    for dx in (-1, 1):
        for dy in (-1, 1):
            g.box((x + dx * .06, y + dy * .06, zc), (.022, .022, .20), IRON)
    g.box((x, y, zc - .115), (.14, .14, .03), IRON)
    # Studio-only light positions (the renderer adds preview point lights).
    g.__dict__.setdefault('lamp_points', []).append((x, y, zc))


def post_lamp(g, x, y, z, face_dir):
    """Lantern on a short iron arm bolted to a post face."""
    nx, ny = face_dir
    g.box((x, y, z + .08), (.10 if ny else .03, .03 if ny else .10, .26), IRON)
    tip = (x + nx * .24, y + ny * .24)
    member(g, (x, y, z + .18), (tip[0], tip[1], z + .18), .03, .03, IRON)
    lantern(g, tip[0], tip[1], z + .165, .04)


# ------------------------------------------------------------------ produce

def crate(g, x, y, z, w=.46, d=.36, h=.28, kind='apple', seed=0, brace=False):
    first = len(g.faces)
    g.box((x, y, z + h / 2), (w, d, h), DETAILS)
    cell = CRATE_BRACE if brace else CRATE_SIDE
    for k in range(first, len(g.faces)):
        u0, u1, v0, v1 = CRATE_TOP if k - first in (0, 1) else cell
        g.face_uvs[k] = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
    if kind is not None:
        produce(g, x, y, z + h, w - .06, d - .06, kind, seed)


def produce(g, x, y, z, w, d, kind, seed):
    """A heaped layer of produce, each lump a bounded native colour island.
    Four-sided lumps (triangle budget, 20k grand cap): a fruit is 3-4 px at
    normal zoom; baskets 8 sides, barrels 10, sacks 6."""
    rng = random.Random(seed)
    spec = {'apple': (RED, DETAILS, .085), 'tomato': (RED, DETAILS, .075),
            'orange': (WHOLE, ORANGE, .09), 'cabbage': (GREEN, DETAILS, .13),
            'greens': (GREEN, DETAILS, .10), 'potato': (SACK, DETAILS, .08),
            'onion': (WHOLE, CREAM, .075), 'berry': (PURPLE, DETAILS, .055),
            'pumpkin': (WHOLE, ORANGE, .17), 'carrot': (WHOLE, ORANGE, .05)}
    rect, mat, r = spec[kind]
    r *= 1.2
    if kind == 'carrot':
        for layer in range(2):
            for i in range(int(d / .065)):
                yy = y - d / 2 + .035 + i * .065 + layer * .03
                zz = z + .03 + layer * .055
                first = len(g.faces)
                member(g, (x - w * .44, yy, zz), (x + w * .30, yy, zz + .02), .06, .06, mat)
                paint(g, first, mat, rect)
                first = len(g.faces)
                member(g, (x + w * .30, yy, zz + .02), (x + w * .48, yy + rng.uniform(-.02, .02), zz + .05), .08, .03, DETAILS)
                paint(g, first, DETAILS, GREEN)
        return
    squash = .65 if kind == 'pumpkin' else .85
    nx, ny = max(1, round(w / (r * 1.55))), max(1, round(d / (r * 1.55)))
    for i in range(nx):
        for j in range(ny):
            xx = x - w / 2 + (i + .5) * w / nx + rng.uniform(-.012, .012)
            yy = y - d / 2 + (j + .5) * d / ny + rng.uniform(-.012, .012)
            lift = .016 * ((i + j) % 2)   # neighbours never share a cap plane
            lump(g, (xx, yy, z + r * .40 + lift), r, r * .95, r * squash, mat, rect, seed * 131 + i * 17 + j, seg=4)
    # Heaped courses make every crate read as overflowing from above.
    if kind != 'pumpkin':
        for i in range(max(1, nx - 1)):
            for j in range(max(1, ny - 1)):
                xx = x - w / 2 + (i + (1 if nx > 1 else .5)) * w / nx
                yy = y - d / 2 + (j + (1 if ny > 1 else .5)) * d / ny
                lift = .016 * ((i + j) % 2)
                lump(g, (xx, yy, z + r * 1.10 + lift), r, r, r * squash, mat, rect, seed * 977 + i * 7 + j, seg=4)
        if nx * ny >= 4:
            lump(g, (x, y, z + r * 1.75), r * .95, r * .95, r * squash, mat, rect, seed * 31 + 5, seg=4)


def lump(g, c, rx, ry, rz, mat, rect, seed, seg=5):
    """Low-poly fruit or vegetable: a jittered `seg`-sided ellipsoid
    (pentagonal by default; was hexagonal)."""
    rng = random.Random(seed)
    x, y, z = c
    rings = [(-.78, .60), (-.05, 1.0), (.62, .72)]
    pts = []
    for k, (h, f) in enumerate(rings):
        for i in range(seg):
            a = 2 * math.pi * (i + .5 * k) / seg
            j = rng.uniform(.88, 1.08)
            pts.append(Vector((x + math.cos(a) * rx * f * j, y + math.sin(a) * ry * f * j, z + h * rz)))
    first = len(g.faces)
    centre = Vector(c)
    for k in range(len(rings) - 1):
        for i in range(seg):
            i2 = (i + 1) % seg
            a, b = pts[k * seg + i], pts[k * seg + i2]
            cc, d = pts[(k + 1) * seg + i2], pts[(k + 1) * seg + i]
            for tri in ((a, b, cc), (a, cc, d)):
                face(g, tri, sum(tri, Vector()) / 3 - centre, mat)
    face(g, pts[:seg], (0, 0, -1), mat)
    face(g, pts[-seg:], (0, 0, 1), mat)
    paint(g, first, mat, rect)


def place(g, temp, fn):
    """Copy a temporary assembly into `g` through a rigid transform."""
    if temp.native_props:
        raise ValueError('Transformed assemblies must not carry native props')
    for f, mat, uv, src in zip(temp.faces, temp.materials, temp.face_uvs, temp.face_sources, strict=True):
        pts = [fn(Vector((-temp.vertices[i][0], -temp.vertices[i][1], temp.vertices[i][2]))) for i in f]
        g.add([tuple(q) for q in pts], [tuple(range(len(f)))], mat)
        g.face_uvs[-1] = uv
        g.face_sources[-1] = src


def display_crate(g, x, y, z, w, d, h, kind, seed, *, facing='front', tilt=.30, brace=False):
    """Crate tilted toward the shopper on its front bottom edge, propped on
    a block at the back. (x, y) is the crate's footprint centre before tilt."""
    t = Geometry('display crate')
    crate(t, 0, 0, 0, w, d, h, kind, seed, brace)
    rot = Quaternion((1, 0, 0), tilt)
    pivot = Vector((0, -d / 2, 0))
    yaw = {'front': 0, 'left': -math.pi / 2, 'right': math.pi / 2}[facing]
    turn = Quaternion((0, 0, 1), yaw)
    at = Vector((x, y, z))
    place(g, t, lambda q: at + turn @ (rot @ (q - pivot) + pivot))
    lift = (d - .06) * math.sin(tilt)
    yb = -d / 2 + (d - .06) * math.cos(tilt)
    centre = at + turn @ Vector((0, yb, (lift + .012) / 2))
    size = (w - .10, .06, lift + .012) if yaw == 0 else (.06, w - .10, lift + .012)
    g.box(tuple(centre), size, WOOD)


def lying_sack(g, x, y, z, r, h, seed, along='X'):
    """Sack laid on its side (the drawn tie toward +X or +Y)."""
    t = Geometry('lying sack')
    sack(t, 0, 0, 0, r, h, seed)
    rot = Quaternion((0, 1, 0), math.pi / 2) if along == 'X' else Quaternion((1, 0, 0), -math.pi / 2)
    at = Vector((x, y, z + r * 1.06))
    place(g, t, lambda q: at + rot @ q)


def sack_stack(g, x, y, along, seed, r=.14, h=.44):
    """Three sacks laid side by side with two on top."""
    off = Vector((0, 1, 0)) if along == 'X' else Vector((1, 0, 0))
    base = Vector((x, y, 0)) - (Vector((h / 2, 0, 0)) if along == 'X' else Vector((0, h / 2, 0)))
    for k, (o, zz) in enumerate(((-1, 0), (0, 0), (1, 0), (-.5, 1), (.5, 1))):
        p = base + off * (o * r * 2.08)
        lying_sack(g, p.x, p.y, zz * r * 1.72, r, h, seed + k, along)


def produce_barrel(g, x, y, kind, seed, r=.21, h=.52):
    """Open banded barrel heaped with produce (Details barrel staves)."""
    seg = 10
    rings = [(r * .88, 0), (r, h / 2), (r * .90, h)]
    pts = [[Vector((x + math.cos(2 * math.pi * i / seg) * rr, y + math.sin(2 * math.pi * i / seg) * rr, zz))
            for i in range(seg)] for rr, zz in rings]
    u0, u1, v0, v1 = BARREL
    for k in range(2):
        for i in range(seg):
            i2 = (i + 1) % seg
            quad = [pts[k][i], pts[k][i2], pts[k + 1][i2], pts[k + 1][i]]
            ua, ub = u0 + (i % 7) / 7 * (u1 - u0), u0 + (i % 7 + 1) / 7 * (u1 - u0)
            va, vb = v0 + k / 2 * (v1 - v0), v0 + (k + 1) / 2 * (v1 - v0)
            out = (quad[0] + quad[2]) / 2 - Vector((x, y, (quad[0].z + quad[2].z) / 2))
            face(g, quad, out, DETAILS, [(ua, va), (ub, va), (ub, vb), (ua, vb)])
    face(g, pts[0], (0, 0, -1), DETAILS, [((u0 + u1) / 2, v0 + .01)] * seg)
    face(g, pts[2], (0, 0, 1), DETAILS, [((u0 + u1) / 2, v1 - .01)] * seg)
    # The hoop's top stands 5 mm under the lid: flush, it overlapped the lid
    # wherever the (sparser, four-sided) produce leaves the lid open.
    g.ring((x, y, h - .025), r * .90 + .014, .028, .04, IRON, 'Z', seg)
    produce(g, x, y, h - .01, r * 1.35, r * 1.35, kind, seed)


def sack(g, x, y, z, r=.15, h=.40, seed=0, lean=0.0):
    """Tied grain sack wrapped with the shipped Details sack drawing."""
    rng = random.Random(seed)
    seg = 6
    profile = [(r * .78, 0), (r, h * .16), (r * 1.04, h * .52), (r * .86, h * .78), (r * .40, h * .90), (r * .30, h)]
    verts = []
    for rr, zz in profile:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            j = rng.uniform(.92, 1.06)
            verts.append(Vector((x + math.cos(a) * rr * j + lean * zz, y + math.sin(a) * rr * j, z + zz)))
    u0, u1, v0, v1 = SACK
    def uv(ii, kk):
        t = ii / seg
        t = 2 * t if t <= .5 else 2 - 2 * t
        return (u0 + t * (u1 - u0), v0 + profile[kk][1] / h * (v1 - v0))
    for k in range(len(profile) - 1):
        for i in range(seg):
            i2 = (i + 1) % seg
            quad = [verts[k * seg + i], verts[k * seg + i2], verts[(k + 1) * seg + i2], verts[(k + 1) * seg + i]]
            zm = (profile[k][1] + profile[k + 1][1]) / 2
            out = (quad[0] + quad[2]) / 2 - Vector((x + lean * zm, y, z + zm))
            face(g, quad, out, DETAILS, [uv(i, k), uv(i + 1, k), uv(i + 1, k + 1), uv(i, k + 1)])
    for k, n in ((0, -1), (len(profile) - 1, 1)):
        ring = verts[k * seg:(k + 1) * seg]
        face(g, ring, (0, 0, n), DETAILS, [((u0 + u1) / 2, v0 + .02 if n < 0 else v1 - .02)] * seg)


def basket(g, x, y, z, r=.17, kind='apple', seed=0):
    first = len(g.faces)
    g.cylinder((x, y, z + .07), r, .14, LIGHTWOOD, 'Z', 8, r * 1.12)
    paint(g, first, LIGHTWOOD, WICKER)
    g.ring((x, y, z + .14), r * 1.12 + .012, .03, .03, IRON, 'Z', 8)
    produce(g, x, y, z + .12, r * 1.6, r * 1.6, kind, seed)


def stand(g, x0, x1, y0, y1, top):
    """Trestle display table: plank top on four legs with a stretcher."""
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, top - .03), (x1 - x0, y1 - y0, .06), PLANK)
    for x in (x0 + .06, x1 - .06):
        for y in (y0 + .06, y1 - .06):
            g.box((x, y, (top - .06) / 2), (.07, .07, top - .06), WOOD)
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, .16), (x1 - x0 - .2, .05, .05), WOOD)


def riser(g, x0, x1, y0, y1, top):
    """Low solid display step (closed timber box) for the back row of crates."""
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, top / 2), (x1 - x0, y1 - y0, top), PLANK)


def flower_box(g, x, y, z, width, seed, species=('DandelionMature', 'BlueberryBushMature')):
    g.box((x, y, z + .10), (width, .22, .20), WOOD)
    g.box((x, y, z + .195), (width - .05, .17, .02), PLANK)
    count = max(1, int((width - .06) / .22))
    for i in range(count):
        xx = x - (count - 1) * .11 + i * .22
        plant(g, species[(seed + i) % len(species)], (xx, y, z + .20), .30, ((seed + i) % 4) * 90)


def herb_bunch(g, x, y, top, kind, seed):
    """Drying bunch hung on a cord under an arcade roof."""
    g.box((x, y, top - .07), (.012, .012, .14), WOOD)
    rect = GREEN if kind == 'greens' else WHOLE
    mat = DETAILS if kind == 'greens' else CREAM
    rng = random.Random(seed)
    for k in range(4):
        lump(g, (x + rng.uniform(-.03, .03), y + rng.uniform(-.03, .03), top - .20 - k * .07),
             (.10 - k * .015) / 2, (.09 - k * .012) / 2, .055, mat, rect, seed * 7 + k)


# ------------------------------------------------------------------ building parts

def hall(g):
    """Two-storey timber hall: board skins, concrete course, frame, windows."""
    door, bdoor = (4.0, 5.0, 0, 1), (6.0, 7.0, 2, 3)
    eave_wall = TOP_PLATE[0] + .11
    # Front skin: eave walls either side of the cross-gable bay.
    wall(g, 'X', HY0, -1, HX0, 5.5, 0, eave_wall, [door])
    wall(g, 'X', HY0, -1, 5.5, 7.5, 0, TOP_PLATE[0] + .07, [bdoor])
    wall(g, 'X', HY0, -1, 7.5, HX1, 0, eave_wall)
    wall(g, 'X', HY1, 1, HX0, HX1, 0, eave_wall)
    und = lambda y: top_main(y) - VT + .03
    for x, out in ((HX0, -1), (HX1, 1)):
        gable(g, 'Y', x, out, [(HY0, 0), (HY1, 0), (HY1, und(HY1)), (RIDGE_Y, und(RIDGE_Y)), (HY0, und(HY0))])
    # Timber doorways close the two one-tile door holes.
    timber_door(g, 4.5, 0)
    timber_door(g, 6.5, 2)
    g.doorways.append({'id': 'MainDoor', 'position': [4.5, HY0, 0], 'outward': [0, -1],
                       'width': 1.0, 'internalConnection': 'BuildingInterior'})
    g.doorways.append({'id': 'BalconyDoor', 'position': [6.5, HY0, 2], 'outward': [0, -1],
                       'width': 1.0, 'internalConnection': 'BuildingInterior'})
    # Late-game cast base course; cut at the door recess and the cargo door.
    course(g, 'X', EDGE_Y0, -1, EDGE_X0, EDGE_X1, [(3.98, 5.02)])
    course(g, 'X', EDGE_Y1, 1, EDGE_X0, EDGE_X1, [(2.845, 4.005)])
    for x, out in ((EDGE_X0, -1), (EDGE_X1, 1)):
        course(g, 'Y', x, out, EDGE_Y0 + .19, EDGE_Y1 - .19)
    # Frame. Ground posts flank the door recess with 15 mm of clearance.
    c, m = POST_C, POST_M
    corner_top = TOP_PLATE[0] + .05
    up0, up1 = FLOOR_GIRT[0] + .05, TOP_PLATE[0] - .03
    # Corner posts stand on the course; their outer faces are the tile edges.
    front = [(HX0, .30, corner_top, c), (HX1, .30, corner_top, c)]
    front += [(u, .28, 1.85, m) for u in (2.70, 3.875, 5.125, 6.30, 7.15)]
    front += [(u, up0, up1, m) for u in (2.75, 4.10, 5.52, 7.50)]
    frame_wall(g, 'X', HY0, HX0, HX1, front)
    back = [(HX0, .30, corner_top, c), (HX1, .30, corner_top, c)]
    back += [(u, .28, 1.85, m) for u in (2.75, 4.10, 5.45, 6.80)]
    back += [(u, up0, up1, m) for u in (2.75, 4.10, 5.45, 6.80)]
    frame_wall(g, 'X', HY1, HX0, HX1, back)
    for x in (HX0, HX1):
        frame_wall(g, 'Y', x, HY0, HY1, [(RIDGE_Y, .28, 1.85, m), (RIDGE_Y, up0, up1, m)])
    # Folded plates at the frame corners; the balcony, the stall wing and
    # the tank tower own the other three lower joints.
    for x, sx in ((HX0, -1), (HX1, 1)):
        for y, sy in ((HY0, -1), (HY1, 1)):
            for z in (1.90, 3.45):
                if z < 2 and (sx > 0 or sy < 0):
                    continue
                corner_plates(g, x, y, z, sx, sy)
    # Ground storey: lit shop windows inside the arcade; grids elsewhere.
    for x, w in ((2.05, .62), (3.29, .50), (5.71, .60), (6.72, .50), (7.50, .40)):
        atlas_window(g, x, HY0, 1.0, w, 'front', 'grid9')
    for y in (3.0, 5.0):
        atlas_window(g, HX1, y, 1.0, .60, 'right', 'grid9')
        atlas_window(g, HX0, y, 1.05, .52, 'left', 'single')
    for x in (2.075, 4.775, 7.33):
        atlas_window(g, x, HY1, 1.0, .58, 'back', 'grid9')
    # Upper storey: grand market-room windows with flower boxes at the front,
    # lancets on the sides, triples at the back, slits beside the balcony door.
    for i, x in enumerate((2.075, 3.425, 4.80)):
        native_window(g, x, HY0, 3.05, 1.0, 'front', 'grand')
        for dx in (-.20, .20):
            member(g, (x + dx, HY0 - .005, 2.27), (x + dx, HY0 - .25, 2.27), .04, .05, IRON)
        flower_box(g, x, HY0 - .16, 2.30, .56, 3 + i)
    for x in (5.75, 7.25):
        atlas_window(g, x, HY0, 2.60, .20, 'front', 'slit')
    for y in (3.0, 5.0):
        native_window(g, HX0, y, 2.95, 1.0, 'left', 'lancet')
    for y in (4.45, 5.25):   # right side: clear of the stair bay (y 2..4)
        native_window(g, HX1, y, 2.95, 1.0, 'right', 'lancet')
    for x in (2.075, 3.425, 4.775, 7.33):
        atlas_window(g, x, HY1, 2.95, .34, 'back', 'triple')
    for x, face_name in ((HX0, 'left'), (HX1, 'right')):
        atlas_window(g, x, RIDGE_Y, 4.45, .42, face_name, 'porthole')
    # Door lanterns on the flanking posts, above the door head.
    for x in (3.875, 5.125):
        post_lamp(g, x, HY0 - m / 2, 1.22, (0, -1))


def timber_door(g, cx, z0):
    """Timber doorway matching the hall frame: a 10 cm lined reveal, a
    closed board leaf with iron straps, dark jambs and a head beam."""
    x0, x1, z1, depth = cx - .5, cx + .5, z0 + 1.0, .10
    yb = HY0 + depth
    for x, n in ((x0, 1), (x1, -1)):
        face(g, [(x, HY0, z0), (x, yb, z0), (x, yb, z1), (x, HY0, z1)], (n, 0, 0), WOOD)
    face(g, [(x0, HY0, z1), (x1, HY0, z1), (x1, yb, z1), (x0, yb, z1)], (0, 0, -1), WOOD)
    # Threshold from the tile edge (y = 2): on the ground at layer 0; flush
    # with the deck top at layer 2.
    if z0 == 0:
        g.box((cx, (EDGE_Y0 + yb + .04) / 2, .015), (1.0, yb + .04 - EDGE_Y0, .03), WOOD)
        leaf0 = .03
    else:
        g.box((cx, (EDGE_Y0 + yb + .04) / 2, z0 - .04), (1.0, yb + .04 - EDGE_Y0, .08), WOOD)
        leaf0 = z0
    for i in range(5):
        g.box((x0 + .1 + i * .2, yb + .02, (leaf0 + z1 + .02) / 2), (.2, .04, z1 + .02 - leaf0), PLANK)
    for zz in (z0 + .24, z1 - .24):
        g.box((cx, yb - .01, zz), (.76, .02, .07), IRON)
    g.ring((cx + .26, yb - .025, z0 + .52), .045, .012, .02, IRON, 'Y', 10)
    jamb0 = z0 + .03 if z0 == 0 else z0
    # Head beam front on the tile edge; jambs 12 mm behind it, so the walk
    # in front of the door (y < 2) stays clear.
    for x in (x0, x1):
        g.box((x, (EDGE_Y0 + .012 + EDGE_Y0 + .20) / 2, (jamb0 + z1 + .12) / 2), (.16, .188, z1 + .12 - jamb0), WOOD)
    g.box((cx, (EDGE_Y0 + EDGE_Y0 + .17) / 2, z1 + .09), (1.32, .17, .22), WOOD)


def back_doors(g):
    """Closed timber cargo doors at the dock and a hoist door above."""
    for cx, z0, z1 in ((3.425, 0, 1.25), (6.125, 2.15, 2.95)):
        for dx in (-.255, .255):
            g.box((cx + dx, HY1 + .02, (z0 + z1) / 2), (.49, .06, z1 - z0), PLANK)
            for zz in (z0 + .18, z1 - .18):
                g.box((cx + dx, HY1 + .062, zz), (.42, .025, .07), IRON)
        for xx in (cx - .54, cx + .54):
            # Jambs stand 1 cm proud of the frame posts' rear faces (shared plane
            # once the bevel modifier is gone).
            g.box((xx, HY1 + .045, (z0 + z1) / 2 + .03), (.08, .10, z1 - z0 + .06), WOOD)
        # Lintel 1 cm proud of the frame posts' rear faces (shared plane once
        # the bevel modifier is gone).
        g.box((cx, HY1 + .05, z1 + .08), (1.18, .12, .12), WOOD)


def main_roof(g):
    s = math.sqrt(1 + K * K)
    ye0, ye1 = HY0 - EAVE_OH, HY1 + EAVE_OH
    gx0, gx1 = HX0 - GABLE_OH, HX1 + GABLE_OH
    W = (RIDGE_Y - ye0) * s
    e = top_main(ye0)
    # Front slope in three pieces: the cross-gable owns the middle eave.
    slab(g, (gx0, ye0, e), (1, 0, 0), (0, 1, K), 5.5 - gx0, W)
    slab(g, (5.5, HY0 + .05, top_main(HY0 + .05)), (1, 0, 0), (0, 1, K), 2.0, (RIDGE_Y - HY0 - .05) * s)
    slab(g, (7.5, ye0, e), (1, 0, 0), (0, 1, K), gx1 - 7.5, W)
    slab(g, (gx0, ye1, e), (1, 0, 0), (0, -1, K), gx1 - gx0, W)
    # Barge boards along both gables.
    # Barge boards enclose each slab end; the pair is offset 14 mm so the
    # two boards never share a plane where they meet at the ridge.
    for gx, inward in ((EDGE_X0, 1), (EDGE_X1, -1)):
        for ye, off in ((ye0, .035), (ye1, .021)):
            xx = gx + inward * off
            member(g, (xx, ye, e - SLAB / 2 + .012), (xx, RIDGE_Y, RIDGE_TOP - SLAB / 2 + .012), .08, .20, WOOD)
    # Ridge timber outside the monitor; iron caps where it meets the gables.
    for x0, x1 in ((gx0 - .04, MON_X0 + .05), (MON_X1 - .05, gx1 + .04)):
        g.box(((x0 + x1) / 2, RIDGE_Y, RIDGE_TOP - .02), (x1 - x0, .16, .14), WOOD)
    for x in (EDGE_X0 + .03, EDGE_X1 - .03):
        g.box((x, RIDGE_Y, RIDGE_TOP - .03), (.16, .30, .28), IRON)
    # Eave fascia boards (the cross-gable covers the front middle).
    for y, x0, x1 in ((ye0 - .035, gx0, 5.2), (ye1 + .035, gx0, gx1)):
        g.box(((x0 + x1) / 2, y, e - .085), (x1 - x0, .07, .16), WOOD)
    for x, y in ((EDGE_X0 + .03, ye0 - .03), (EDGE_X0 + .03, ye1 + .03), (EDGE_X1 - .03, ye1 + .03)):
        g.box((x, y, e - .07), (.16, .16, .24), IRON)


def cross_gable(g):
    """Front cross-gable over the balcony bay, valley-jointed into the roof."""
    s = math.sqrt(1 + K * K)
    ridge = WALL_TOP + K * 1.0
    eave = WALL_TOP - K * EAVE_OH
    for x, sdir in ((5.5 - EAVE_OH, 1), (7.5 + EAVE_OH, -1)):
        slab(g, (x, HY0 - EAVE_OH, eave), (0, 1, 0), (sdir, 0, K), 1.35, (1 + EAVE_OH) * s)
    und = lambda x: WALL_TOP + K * (1 - abs(x - 6.5)) - VT + .03
    gable(g, 'X', HY0, -1, [(5.5, TOP_PLATE[0] + .07), (7.5, TOP_PLATE[0] + .07), (7.5, und(7.5)), (6.5, und(6.5)), (5.5, und(5.5))])
    native_window(g, 6.5, HY0, 4.24, .55, 'front', 'diamond')
    ye = HY0 - EAVE_OH - .03
    for xe, off in ((5.5 - EAVE_OH, 0), (7.5 + EAVE_OH, .016)):
        member(g, (xe, ye - off, eave - SLAB / 2 + .012), (6.5, ye - off, ridge - SLAB / 2 + .012), .08, .20, WOOD)
    g.box((6.5, ye + .01, ridge - .03), (.30, .16, .28), IRON)
    g.box((6.5, (ye + 3.02) / 2, ridge - .02), (.16, 3.02 - ye, .14), WOOD)
    # Dark timber valley boards over each roof intersection.
    for x0 in (5.5 - EAVE_OH, 7.5 + EAVE_OH):
        member(g, (x0, HY0 - EAVE_OH, eave + .035), (6.5, HY0 + 1.0, ridge + .035), .16, .05, WOOD)


def monitor(g):
    """Raised clerestory along the ridge with a row of lit windows."""
    x0, x1, y0, y1 = MON_X0, MON_X1, MON_Y0, MON_Y1
    base, top, mk = top_main(y0) - .18, 6.25, .8
    mvt = SLAB * math.sqrt(1 + mk * mk)
    ridge = top + mk * (y1 - y0) / 2
    wall(g, 'X', y0, -1, x0, x1, base, top - .05)
    wall(g, 'X', y1, 1, x0, x1, base, top - .05)
    for x, out in ((x0, -1), (x1, 1)):
        gable(g, 'Y', x, out, [(y0, base), (y1, base), (y1, top - .05), ((y0 + y1) / 2, ridge - mvt + .03), (y0, top - .05)])
    xm = (x0 + x1) / 2
    for x in (x0, xm, x1):
        for y in (y0, y1):
            g.box((x, y, (base + top - .08) / 2), (.16, .16, top - .08 - base), WOOD)
    for y, face_name in ((y0, 'front'), (y1, 'back')):
        for dx in (-1.08, -.42, .42, 1.08):
            atlas_window(g, xm + dx, y, 5.70, .44, face_name, 'grid9')
        g.box((xm, y, top_main(y0) + .12), (x1 - x0 - .16, .12, .20), WOOD)
    s = math.sqrt(1 + mk * mk)
    for y, sdir in ((y0 - .18, 1), (y1 + .18, -1)):
        slab(g, (x0 - .15, y, top - .18 * mk), (1, 0, 0), (0, sdir, mk), x1 - x0 + .3, ((y1 - y0) / 2 + .18) * s)
    for x, out in ((x0 - .17, -1), (x1 + .17, 1)):
        for ye, off in ((y0 - .18, 0), (y1 + .18, .016)):
            member(g, (x + out * off, ye, top - .18 * mk - SLAB / 2 + .01),
                   (x + out * off, (y0 + y1) / 2, ridge - SLAB / 2 + .01), .07, .17, WOOD)
    g.box((xm, (y0 + y1) / 2, ridge - .02), (x1 - x0 + .36, .14, .13), WOOD)
    for x in (x0 - .19, x1 + .19):
        g.box((x, (y0 + y1) / 2, ridge - .03), (.14, .26, .24), IRON)


def roof_battens(g):
    """Dark cover battens down the main slopes, as on the concept roof."""
    s = math.sqrt(1 + K * K)
    for x, sdir, y_end in ((3.55, 1, MON_Y0), (4.75, 1, MON_Y0), (1.45, 1, RIDGE_Y),
                           (3.55, -1, MON_Y1), (4.75, -1, MON_Y1), (6.45, -1, RIDGE_Y), (7.62, -1, RIDGE_Y)):
        ye = HY0 - EAVE_OH if sdir > 0 else HY1 + EAVE_OH
        n = Vector((0, -K * sdir, 1)).normalized()
        a = Vector((x, ye, top_main(ye))) + n * .02
        b = Vector((x, y_end, top_main(y_end))) + n * .02
        if abs(y_end - RIDGE_Y) > 1e-6:
            b = b + Vector((0, -.05 * sdir, -.05 * K))
        d = (b - a) / 2
        obox(g, (a + b) / 2, d, (.05, 0, 0), n * .035, WOOD)


def dormer(g, xc, front, sdir):
    """Small gabled dormer on the main roof; sdir=+1 front slope, -1 rear."""
    dk = .8
    yf = front
    rf = top_main(yf)
    top = rf + .52
    ridge = top + .4 * dk
    dvt = SLAB * math.sqrt(1 + dk * dk)
    gable(g, 'X', yf, -sdir, [(xc - .4, rf - .15), (xc + .4, rf - .15), (xc + .4, top - .07),
                              (xc, ridge - dvt + .03), (xc - .4, top - .07)])
    rise = (top + .08 - WALL_TOP) / K
    yb = HY0 + rise if sdir > 0 else HY1 - rise
    for x, out in ((xc - .4, -1), (xc + .4, 1)):
        gable(g, 'Y', x, out, [(yf, rf - .15), (yb, top - .07), (yf, top - .07)])
    for x in (xc - .4, xc + .4):
        g.box((x, yf, (rf - .05 + top - .09) / 2), (.11, .11, top - .09 - rf + .05), WOOD)
    atlas_window(g, xc, yf, rf + .28, .40, 'front' if sdir > 0 else 'back', 'cross')
    s = math.sqrt(1 + dk * dk)
    rise = (ridge + .08 - WALL_TOP) / K
    yend = HY0 + rise if sdir > 0 else HY1 - rise
    y0 = yf - .15 * sdir
    for x, d in ((xc - .52, 1), (xc + .52, -1)):
        slab(g, (x, y0, top - .12 * dk), (0, sdir, 0), (d, 0, dk), abs(yend - y0), .52 * s)
    for x, off in ((xc - .54, 0), (xc + .54, .016)):
        yb2 = y0 - (.02 + off) * sdir
        member(g, (x, yb2, top - .12 * dk - SLAB / 2 + .01), (xc, yb2, ridge - SLAB / 2 + .01), .06, .15, WOOD)
    g.box((xc, y0 - .02 * sdir, ridge - .03), (.20, .14, .20), IRON)


def chimney(g, x, y):
    """Riveted metal flue on a cast base above the rear slope."""
    base = top_main(y) - .30
    tiled_box(g, (x, y, (base + 6.90) / 2), (.42, .42, 6.90 - base), PLANK, 1.5)
    for zz, size, h in ((top_main(y) - .04, .48, .50), (6.05, .46, .06), (6.92, .52, .10)):
        g.box((x, y, zz), (size, size, h), IRON)
    g.cylinder((x, y, 7.08), .11, .22, IRON, 'Z', 12)
    g.cylinder((x, y, 7.20), .16, .03, IRON, 'Z', 12)
    # Vanilla chimney steam above the cap (no geometry; see vanilla_smoke.mjs).
    emitter(g, 'steam', x, y, 7.215, .11)   # steam: smoke-kind means smog


def arcade(g):
    """Front market arcade: a pent roof on a post line whose outer faces are
    on y = 0, the striped awning over the stall beside the entrance walk,
    and a skirt roof in front of the balcony. The walk x 4..5 stays open."""
    k = .33
    s = math.sqrt(1 + k * k)
    pvt = SLAB * s
    def pent_top(y):
        return 2.10 - k * (HY0 - y)
    # Left pent: posts on x = 1, 2.5 and 4 (outer faces on 1 and 4).
    x0, x1 = 1.02, 3.98
    slab(g, (x0, 0.0, pent_top(0.0)), (1, 0, 0), (0, 1, k), x1 - x0, (HY0 + .06) * s)
    beam_top = pent_top(.10) - pvt + .012
    g.box(((x0 + x1) / 2, .10, beam_top - .075), (x1 - x0 - .04, .16, .15), WOOD)
    for x, fx in ((1.10, -1), (2.50, 0), (3.90, 1)):
        free_post(g, x, .10, beam_top - .10, .20, fx, -1)
        for d in (-1, 1):
            if x0 < x + d * .42 < x1:
                member(g, (x, .10, beam_top - .55), (x + d * .42, .10, beam_top - .14), .09, .09, WOOD)
        g.box((x, -.008, beam_top - .34), (.16, .016, .20), IRON)
    g.box(((x0 + x1) / 2, -.02, pent_top(0.0) - .085), (x1 - x0, .04, .16), WOOD)
    for x in (1.80, 3.20):
        lantern(g, x, .10, beam_top - .15)
    for i, x in enumerate((1.60, 2.15, 2.85, 3.40)):
        herb_bunch(g, x, .52, pent_top(.52) - pvt + .01, 'greens' if i % 2 else 'garlic', 40 + i)
    # Skirt pent in front of the balcony: posts on x = 6 and 8, front y = 0.
    def skirt_top(y):
        return 1.78 - k * (1.0 - y)
    sx0, sx1 = 6.02, 7.98
    slab(g, (sx0, 0.0, skirt_top(0.0)), (1, 0, 0), (0, 1, k), sx1 - sx0, 1.06 * s)
    sb = skirt_top(.10) - pvt + .012
    g.box(((sx0 + sx1) / 2, .10, sb - .075), (sx1 - sx0 - .04, .16, .15), WOOD)
    for x, fx in ((6.10, -1), (7.90, 1)):
        free_post(g, x, .10, sb - .10, .20, fx, -1)
        g.box((x, -.008, sb - .34), (.16, .016, .20), IRON)
    g.box(((sx0 + sx1) / 2, -.02, skirt_top(0.0) - .085), (sx1 - sx0, .04, .16), WOOD)
    lantern(g, 7.0, .10, sb - .15)
    striped_awning(g)


def striped_awning(g):
    """Red-and-cream striped awning on iron rods over the stall at x 5..6,
    beside (not over) the entrance walk."""
    x0, x1 = 5.0, 6.0
    top = [(.50, 1.46), (.95, 1.58), (1.45, 1.71), (HY0 - .02, 1.88)]
    t = .025
    prof = [(y, z - t) for y, z in top] + [(y, z) for y, z in reversed(top)]
    n = 4
    for i in range(n):
        a = x0 + i * (x1 - x0) / n
        b = x0 + (i + 1) * (x1 - x0) / n
        mat = DETAILS if i % 2 == 0 else CREAM
        first = len(g.faces)
        extrude_profile(g, prof, a, b, mat, axis='X')
        # Scalloped valance: each stripe ends in a rounded tongue.
        g.box(((a + b) / 2, .497, 1.39), (b - a, .022, .15), mat)
        g.cylinder(((a + b) / 2, .497, 1.315), (b - a) / 2 - .002, .010, mat, 'Y', 10)
        paint(g, first, mat, RED if i % 2 == 0 else WHOLE)
    # Front bar, side rods and tension rods to the wall (real steel joints).
    g.box(((x0 + x1) / 2, .535, 1.42), (x1 - x0 - .02, .04, .04), WOOD)
    # The right tension rod anchors short of the balcony door jamb.
    for x, xa in ((x0 + .032, x0 + .032), (x1 - .032, x1 - .20)):
        member(g, (x, .52, 1.43), (x, HY0 - .01, 1.84), .03, .03, IRON)
        member(g, (x, .54, 1.45), (xa, HY0 - .01, 2.14), .022, .022, IRON)
        g.box((xa, HY0 - .03, 2.14), (.10, .05, .14), IRON)


def balcony(g, rails):
    """Upper-floor balcony, x 6..9, y 1..2, top at layer 2; open to the
    player stairs on its back edge x 8..9."""
    top = 2.0
    rows = [1.0 + i / 6 for i in range(7)]
    for y0, y1 in zip(rows, rows[1:]):
        for xa, xb in ((6.0, 7.5), (7.5, 9.0)):
            g.box(((xa + xb) / 2, (y0 + y1) / 2, top - .05), (xb - xa - .008, y1 - y0 - .008, .10), PLANK)
    # Strip from the deck edge back to the wall skin, beside the door sill.
    g.box(((7.0 + 7.75) / 2, (EDGE_Y0 + HY0) / 2, top - .05), (.75 - .008, HY0 - EDGE_Y0 - .004, .10), PLANK)
    # Rim beam on the front posts; rear beam against the hall frame.
    g.box((7.5, 1.10, 1.83), (2.92, .16, .14), WOOD)
    g.box((7.5, 1.935, 1.83), (2.96, .11, .14), WOOD)
    for x in (6.35, 7.0, 7.75, 8.40):
        g.box((x, 1.525, 1.835), (.10, .71, .13), WOOD)
    for x, y, fx, fy in ((6.10, 1.10, -1, -1), (7.50, 1.10, 0, -1), (8.90, 1.10, 1, -1), (8.90, 1.90, 1, 1)):
        free_post(g, x, y, 1.77, .20, fx, fy)
    for x, d in ((6.10, 1), (7.50, -1), (7.50, 1), (8.90, -1)):
        member(g, (x, 1.10, 1.32), (x + d * .40, 1.10, 1.74), .09, .09, WOOD)
    for x in (6.10, 7.50, 8.90):
        g.box((x, .992, 1.62), (.16, .016, .22), IRON)
    # Rails: native posts (0.14 x 0.16) set in by half a post so their
    # outer faces sit on the deck edges x = 6, x = 9 and y = 1.
    rx0, rx1, ry0 = 6.071, 8.929, 1.081
    rails.run('BalconyFront', (rx0, ry0), (rx1, ry0), 2)
    rails.run('BalconyLeft', (rx0, ry0), (rx0, 1.90), 2)
    rails.run('BalconyRight', (rx1, ry0), (rx1, 1.919), 2)
    # Flower boxes stand inside the front rail, clear of the walking strip.
    for i, x in enumerate((6.45, 7.45, 8.45)):
        g.box((x, 1.30, 2.06), (.56, .16, .12), WOOD)
        flower_box(g, x, 1.30, 2.12, .62, 11 + i, ('DandelionMature', 'BlueberryBushMature', 'DandelionMature'))
    lantern(g, 6.80, 1.10, 1.76)
    lantern(g, 8.20, 1.10, 1.76)


def stall_wing(g, parts):
    """Low lean-to stall wing on x 0..1, y 1..6, with its own pent roof and
    the hanging basket sign. Outer post faces on x = 0, y = 1 and y = 6."""
    k = .40
    s = math.sqrt(1 + k * k)
    lvt = SLAB * s
    y0, y1 = 1.0, 6.0
    def top(x):
        return 2.15 - k * (HX0 - x)
    slab(g, (0.0, y0 - .05, top(0.0)), (0, 1, 0), (1, 0, k), y1 - y0 + .10, (HX0 + .06) * s)
    under = lambda x: top(x) - lvt
    free_post(g, .10, 1.10, under(.10) - .10, .20, -1, -1)
    free_post(g, .10, 3.50, under(.10) - .10, .20, -1, 0)
    free_post(g, .10, 5.90, under(.10) - .10, .20, -1, 1)
    free_post(g, 1.10, 1.10, under(1.10) - .10, .20, 0, -1)
    g.box((.10, (y0 + .02 + y1 - .02) / 2, under(.10) - .068), (.16, y1 - y0 - .04, .14), WOOD)
    g.box((1.10, (y0 + .02 + EDGE_Y0 + .10) / 2, under(1.10) - .068), (.13, EDGE_Y0 + .08 - y0, .14), WOOD)
    for y in (1.10, 5.90):
        member(g, (.05, y, under(.05) - .07), (HX0 + .05, y, under(HX0 + .05) - .07), .12, .13, WOOD)
    g.box((-.02, (y0 + y1) / 2, top(0.0) - .085), (.04, y1 - y0 + .10, .16), WOOD)
    # Rear board wall closes the wing on the hall's back wall line.
    gable(g, 'X', HY1, 1, [(.10, 0), (HX0, 0), (HX0, under(HX0) + .03), (.10, under(.10) + .03)])
    for y in (2.30, 4.70):
        lantern(g, .10, y, under(.10) - .138)
    # Hanging basket sign on an iron arm from the front corner post.
    arm_z = under(.10) - .17
    member(g, (.10, 1.19, arm_z), (.10, .03, arm_z), .05, .06, IRON)
    member(g, (.10, 1.0, arm_z - .32), (.10, .90, arm_z - .03), .04, .04, IRON)
    pivot = (.10, .42, arm_z - .03)
    sign = Geometry('GroceryMarket.BasketSign', pivot)
    basket_sign(sign, *pivot)
    parts.append((sign, 'SWAY', .05))


def basket_sign(m, x, y, hang):
    """Double-faced carved board with a painted basket emblem."""
    s = 1.25
    zc = hang - .50
    for dy in (-.15, .15):
        for i in range(4):
            m.ring((x, y + dy, hang - .040 - i * .048), .024, .008, .012, IRON, 'Y' if i % 2 else 'X', 6)
    boards, width, height = 5, .72, .60
    for i in range(boards):
        yy = y - width / 2 + (i + .5) * width / boards
        m.box((x, yy, zc), (.06, width / boards - .006, height), PLANK)
    for zz in (zc - height / 2 + .03, zc + height / 2 - .03):
        m.box((x, y, zz), (.075, width + .04, .07), WOOD)
    for yy in (y - width / 2 - .005, y + width / 2 + .005):
        m.box((x, yy, zc), (.085, .05, height - .12), IRON)
    for side in (-1, 1):
        # Each stroke family stands at its own relief, so crossings never
        # share a plane (the shallower stroke buries into the deeper one).
        def stroke(a, b, w, relief):
            first = len(m.faces)
            c = x + side * (.03 + relief / 2 - .003)
            member(m, (c, y + a[0] * s, zc + a[1] * s), (c, y + b[0] * s, zc + b[1] * s), relief + .006, w * s, CREAM)
            paint(m, first, CREAM, WHOLE)
        body = [(-.15, .0), (.15, .0), (.11, -.17), (-.11, -.17)]
        for i, (a, b) in enumerate(zip(body, body[1:] + body[:1])):
            stroke(a, b, .03, .010 if i % 2 == 0 else .022)
        for t in (-.06, -.115):
            stroke((-.14 - t * .2, t), (.14 + t * .2, t), .02, .016)
        for u in (-.07, 0, .07):
            stroke((u, .0), (u * .75, -.17), .02, .028)
        arc = [(math.cos(a) * .12, math.sin(a) * .13) for a in [i * math.pi / 6 for i in range(7)]]
        for i, (a, b) in enumerate(zip(arc, arc[1:])):
            stroke(a, b, .028, .034 if i % 2 == 0 else .040)


def dock(g, parts):
    """Rear hoist under the hall's back eave over the cargo doors.

    2026-10-22 (user): no forced decoration beyond the walls. The pent-roofed
    loading dock on its row of posts, its lanterns, sacks, crates and barrels
    and the water tower are gone, and the footprint ends at the hall's back
    wall (9x7 -> 9x6). The hoist stays: it hangs from the eave, 0.17 off the
    wall, and occupies no ground tile."""
    # Hoist beam under the rear eave, a turning pulley and a rising load.
    hx, wheel_z, r = 6.125, 3.08, .12
    wy = HY1 + .17
    member(g, (hx, HY1 - .05, 3.31), (hx, HY1 + EAVE_OH - .01, 3.31), .16, .18, WOOD)
    g.box((hx, HY1 + .03, 3.31), (.24, .04, .32), IRON)
    for dx in (-.06, .06):
        g.box((hx + dx, wy, 3.20), (.02, .12, .22), IRON)
    g.cylinder((hx, wy, wheel_z), .025, .16, IRON, 'X', 8)
    wheel = Geometry('GroceryMarket.HoistPulley', (hx, wy, wheel_z))
    wheel.ring((hx, wy, wheel_z), r, .035, .07, IRON, 'X', 16)
    wheel.cylinder((hx, wy, wheel_z), .045, .09, IRON, 'X', 10)
    for i in range(6):
        a = i * math.pi / 3
        member(wheel, (hx, wy, wheel_z), (hx, wy + math.cos(a) * (r - .03), wheel_z + math.sin(a) * (r - .03)),
               .025, .025, WOOD, up=(1, 0, 0))
    travel, low_top = 1.0, 1.22
    rope = Geometry('GroceryMarket.HoistRope', (hx, wy + r, wheel_z))
    rope.box((hx, wy + r, (wheel_z + low_top + .08) / 2), (.022, .022, wheel_z - low_top - .08), WOOD)
    load = Geometry('GroceryMarket.HoistLoad', (hx, wy + r, low_top))
    for dy in (-.14, .14):
        member(load, (hx, wy + r, low_top + .08), (hx, wy + r + dy, low_top - .02), .016, .016, WOOD, up=(1, 0, 0))
    crate(load, hx, wy + r, low_top - .36, .42, .34, .34, 'cabbage', 77)
    parts.append((wheel, 'HOIST_WHEEL', (travel, r)))
    parts.append((rope, 'HOIST_ROPE', (travel, wheel_z - low_top - .08)))
    parts.append((load, 'HOIST_LOAD', travel))


def stock(g, food, stage):
    """The fill-stage object of one food; created on first use."""
    if food not in STOCK_FOODS or not 1 <= stage <= STOCK_STAGES:
        raise ValueError(f'Unknown grocery stock stage {food}.{stage}')
    table = g.__dict__.setdefault('stock_parts', {})
    if (food, stage) not in table:
        table[(food, stage)] = Geometry(f'GroceryStock.{food}.{stage}')
    return table[(food, stage)]


# Triangle budget, 20k grand cap (2026-10-29): the stock items are the bulk
# of the model (about 20k of 30k triangles, three cumulative fill stages of
# six foods), so each item is drawn with about half its former triangles.

def tin(t, x, y, z, seed=0):
    """CannedFish: a steel tin wrapped in its red cloth label."""
    # One 5-sided tin whose sides carry the label (was a 6-sided steel tin
    # plus a proud label band): a 9 cm tin is about 12 px wide at the closest
    # zoom.
    first = len(t.faces)
    t.cylinder((x, y, z + .0375), .05, .075, IRON, 'Z', 5)
    # Geometry.cylinder: the two caps come first, then the five sides.
    paint(t, first + 2, DETAILS, RED)


def parcel(t, x, y, z, seed=0):
    """PackagedFood: a cream paper parcel tied with crossed twine."""
    sx, sy, sz = .15, .11, .075
    first = len(t.faces)
    t.box((x, y, z + sz / 2), (sx, sy, sz), CREAM)
    paint(t, first, CREAM, WHOLE)
    # One twine band across the short side (was crossed twine).
    t.box((x, y, z + (.014 + sz + .020) / 2), (.022, sy + .040, sz + .006), WOOD)


def algae(t, x, y, z, seed=0):
    """AlgaeRation: a bundle of green ration bars with a band."""
    # One block for the three bars (their 4 mm joints were sub-pixel).
    first = len(t.faces)
    t.box((x, y, z + .02), (.15, .11, .04), DETAILS)
    paint(t, first, DETAILS, GREEN)
    t.box((x, y, z + (.004 + .046) / 2), (.024, .122, .042), WOOD)


def corn(t, x, y, z, seed=0):
    """CornRation: three husked cobs bound at one end."""
    for k, dy in enumerate((-.036, 0, .036)):
        lift = .022 if k == 1 else 0
        lump(t, (x + .01, y + dy, z + .026 + lift), .085, .029, .028, ORANGE, WHOLE, seed * 7 + k, seg=4)
    first = len(t.faces)
    t.box((x - .055, y, z + (.004 + .078) / 2), (.034, .12, .074), LIGHTWOOD)
    paint(t, first, LIGHTWOOD, HUSK)


def crock(t, x, y, z, seed=0):
    """FermentedCassava: a cream stoneware crock with an iron lid."""
    # 6 sides (was 10, then 8) for the crock, its lid and the jar below; no
    # 3 cm lid knob.
    revolve(t, (x, y, z), [(.062, 0), (.087, .07), (.070, .17), (.055, .19)], CREAM, segments=6)
    t.cylinder((x, y, z + .20), .063, .025, IRON, 'Z', 6)


def jar(t, x, y, z, seed=0):
    """FermentedSoybean: a terracotta jar under a cloth cover."""
    revolve(t, (x, y, z), [(.056, 0), (.077, .07), (.052, .17), (.050, .19)], ORANGE, segments=6)
    t.cylinder((x, y, z + .195), .064, .03, CREAM, 'Z', 6)


def heap(t, maker, x0, x1, y0, y1, z, layer, px, py, seed):
    """One stacking layer of `maker` items on an area; each layer above the
    first has one item fewer each way, offset into the gaps (a pyramid)."""
    nx = max(1, int((x1 - x0) / px + 1e-6) - (layer - 1))
    ny = max(1, int((y1 - y0) / py + 1e-6) - (layer - 1))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    for i in range(nx):
        for j in range(ny):
            maker(t, cx - nx * px / 2 + (i + .5) * px, cy - ny * py / 2 + (j + .5) * py, z, seed + i * 7 + j * 3)


# Item pitch and stacking height per heaped food.
HEAP = {'CannedFish': (tin, .11, .11, .075), 'PackagedFood': (parcel, .18, .16, .097),
        'AlgaeRation': (algae, .17, .14, .052), 'CornRation': (corn, .19, .14, .075)}


def stocked_tray(g, food, x0, x1, y0, y1, z, seed):
    """Static shallow tray; stage n adds stacking layer n of the food."""
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, z + .03), (x1 - x0, y1 - y0, .06), PLANK)
    maker, px, py, lh = HEAP[food]
    for n in range(1, STOCK_STAGES + 1):
        heap(stock(g, food, n), maker, x0 + .02, x1 - .02, y0 + .02, y1 - .02, z + .06 + (n - 1) * lh, n, px, py, seed + 100 * n)


def stocked_crate(g, food, x, y, z, w, d, h, seed, *, stages=(1, 2, 3), tilt=.30, brace=False):
    """Static crate tilted toward the shopper (propped at the back); its
    contents are stacking layers in the given fill stages, tilted with it."""
    t = Geometry('stock crate')
    crate(t, 0, 0, 0, w, d, h, None, seed, brace)
    rot = Quaternion((1, 0, 0), tilt)
    pivot = Vector((0, -d / 2, 0))
    at = Vector((x, y, z))
    fn = lambda q: at + rot @ (q - pivot) + pivot
    place(g, t, fn)
    lift = (d - .06) * math.sin(tilt)
    g.box((x, y - d / 2 + (d - .06) * math.cos(tilt), z + (lift + .012) / 2), (w - .10, .06, lift + .012), WOOD)
    maker, px, py, lh = HEAP[food]
    for layer, stage in enumerate(stages, 1):
        t = Geometry('stock layer')
        heap(t, maker, -w / 2 + .03, w / 2 - .03, -d / 2 + .03, d / 2 - .03, h + (layer - 1) * lh, layer, px, py, seed + 100 * layer)
        place(stock(g, food, stage), t, fn)


def crock_shelf(g, food, y0, y1, seed):
    """Two closed timber steps along the stall wing, facing the side street;
    stage 1 fills the ground row in front, stages 2 and 3 the two steps."""
    maker = crock if food == 'FermentedCassava' else jar
    g.box(((.58 + .77) / 2, (y0 + y1) / 2, .14), (.19, y1 - y0, .28), PLANK)
    g.box(((.79 + .98) / 2, (y0 + y1) / 2, .28), (.19, y1 - y0, .56), PLANK)
    count = int((y1 - y0 - .02) / .19)
    for stage, (x, z) in enumerate(((.46, 0.0), (.675, .28), (.885, .56)), 1):
        for i in range(count):
            maker(stock(g, food, stage), x, y0 + .10 + i * .19 + (i % 2) * .004, z, seed + stage * 20 + i)


def check_stock(g):
    """Every declared food must have all of its fill stages, none empty."""
    table = g.__dict__.get('stock_parts', {})
    expected = {(f, n) for f in STOCK_FOODS for n in range(1, STOCK_STAGES + 1)}
    if set(table) != expected or any(not geo.faces for geo in table.values()):
        missing = sorted(expected - {k for k, geo in table.items() if geo.faces})
        raise ValueError(f'Grocery stock stages missing or empty: {missing}')


def front_goods(g):
    """Storefront stock: the six foods the shop sells, each in its own
    display group and three fill stages (see GroceryStockDisplay.cs). Empty
    displays leave their trays, steps and crates bare. A few produce baskets
    and barrels stay as decor. The walk to the main door (x 4..5, y 0..2)
    stays clear."""
    # Left arcade, three steps: canned fish (left), packaged food (right).
    riser(g, 1.30, 3.70, 1.04, 1.44, .28)
    riser(g, 1.30, 3.70, 1.46, 1.96, .56)
    for food, x0, x1, seed in (('CannedFish', 1.34, 2.46, 10), ('PackagedFood', 2.54, 3.66, 30)):
        stocked_tray(g, food, x0, x1, .60, .96, 0.0, seed)
        stocked_tray(g, food, x0, x1, 1.06, 1.42, .28, seed + 3)
        stocked_tray(g, food, x0, x1, 1.50, 1.86, .56, seed + 6)
    # Overflow out in the light in front of the posts at full stock.
    stocked_crate(g, 'CannedFish', 2.00, .20, 0, .40, .28, .22, 120, stages=(3,), brace=True)
    stocked_crate(g, 'PackagedFood', 3.35, .20, 0, .44, .28, .22, 122, stages=(3,))
    basket(g, 1.55, .20, 0, .11, 'apple', 121)
    basket(g, 2.90, .20, 0, .11, 'tomato', 123)
    # Awning stall (x 5..6): algae ration bundles stacked on the table.
    stand(g, 5.10, 5.90, .60, 1.80, .52)
    for n in range(1, STOCK_STAGES + 1):
        heap(stock(g, 'AlgaeRation', n), algae, 5.13, 5.87, .63, 1.77, .52 + (n - 1) * .052, n, .17, .14, 40 + 100 * n)
    produce_barrel(g, 5.22, .24, 'apple', 52, .17, .48)
    basket(g, 5.72, .22, 0, .11, 'berry', 53)
    # Under the skirt roof: corn ration bundles in four tilted crates, with
    # an overflow crate out in front at full stock.
    for i, x in enumerate((6.30, 6.76, 7.22, 7.68)):
        stocked_crate(g, 'CornRation', x, .70, 0, .44, .26, .26, 60 + i, brace=i % 2 == 1)
    stocked_crate(g, 'CornRation', 7.00, .19, 0, .44, .26, .22, 126, stages=(3,), brace=True)
    basket(g, 6.55, .20, 0, .11, 'berry', 125)
    # Under the balcony: decor baskets and a sack stack.
    stand(g, 6.32, 7.25, 1.42, 1.86, .55)
    for i, (x, kind) in enumerate(((6.55, 'apple'), (7.02, 'onion'))):
        basket(g, x, 1.64, .55, .19, kind, 70 + i)
    sack_stack(g, 7.70, 1.68, 'Y', 80, .13, .36)
    # Stall wing: fermented cassava crocks (front) and soybean jars (back)
    # on stepped shelves facing the side street.
    crock_shelf(g, 'FermentedCassava', 1.45, 3.25, 90)
    crock_shelf(g, 'FermentedSoybean', 3.75, 5.55, 95)
    # In front of the stall wing, beside the sign: cassava overflow crate.
    g_crate = (.62, .40, .44, .30, .24)
    crate(g, g_crate[0], g_crate[1], 0, g_crate[2], g_crate[3], g_crate[4], None, 113)
    for i, dx in enumerate((-.10, .10)):
        crock(stock(g, 'FermentedCassava', 3), g_crate[0] + dx, g_crate[1], g_crate[4], 113 + i)
    basket(g, .50, .80, 0, .11, 'orange', 114)
    sack(g, .85, .78, 0, .12, .34, 115)
    check_stock(g)


def grocery_market(g, parts):
    rails = RailAssembly('WalkwayRail.GroceryMarket')
    hall(g)
    back_doors(g)
    main_roof(g)
    cross_gable(g)
    monitor(g)
    roof_battens(g)
    dormer(g, 2.40, 2.50, 1)
    dormer(g, 2.40, 5.50, -1)
    chimney(g, 7.00, 4.75)
    arcade(g)
    balcony(g, rails)
    stall_wing(g, parts)
    dock(g, parts)
    front_goods(g)
    return rails
