"""Authored geometry of the Fisher Flag (1x1x2 Food workplace, 2026-11-02).

A sibling of the vanilla Iron Teeth Gatherer Flag (1x1x2, 466 triangles): a
small plank landing inside four roped posts, a pole with a hanging lantern and
a cloth banner, and the fishing gear that tells it apart: a net hung on the
back rope with red floats, two rods leaning in the corner, a tub of catch and
a crate. The banner is a blue Iron Teeth cloth with a swallowtail and a
stitched fish on both faces; it swings from its bar (the ambient animation).

Only native materials of the Iron Teeth collection, as the vanilla flag:

  WOOD   BaseWood_DarkBrown.IronTeeth  posts, pole, bars, rods, tub staves
  CLOTH  Details.IronTeeth             deck planks, crates, rope, net, banner
                                       cloth, fish and floats (atlas tiles)
  GLASS  WindowsAtlas.IronTeeth        the lantern panes

Every face gets one UV island inside its atlas tile (TILES, measured on the
shipped textures, UV origin bottom-left), the grain along the axis given per
part. Units are tiles: x across, y back (0 = the entrance side), z up in
layers. Geometry stores the exporter's source coordinates. No bevel: the native
atlases paint the edges. Nothing is resized to fit.
"""
import math
import sys
from pathlib import Path

from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from frontier_architecture import Geometry  # noqa: E402

IDENT = 'FisherFlag'
SIZE = (1, 1, 2)
MATERIALS = ['BaseWood_DarkBrown.IronTeeth', 'Details.IronTeeth', 'WindowsAtlas.IronTeeth']
WOOD, CLOTH, GLASS = range(3)

# (material, (u0, v0, u1, v1)). Measured on Details_D.IronTeeth,
# BaseWood_1K_D_Grey (BaseWood_DarkBrown) and WindowsAtlas_D.IronTeeth.
TILES = {
    # BaseWood lower half: eight single boards, 1/16 wide each (as frontier_architecture WOOD).
    **{f'board{k}': (WOOD, (k / 16 + .006, .015, (k + 1) / 16 - .006, .485)) for k in range(8)},
    'endgrain': (WOOD, (.637, .137, .743, .243)),        # log end rings
    'planks': (CLOTH, (.258, .008, .497, .243)),         # horizontal crate planks (five rows)
    **{f'plank{k}': (CLOTH, (.26, .010 + k * .047, .495, .010 + (k + 1) * .047 - .004)) for k in range(5)},
    'crate': (CLOTH, (.005, .265, .245, .495)),          # crate side with its cross brace
    'rope': (CLOTH, (.755, .51, .808, .99)),             # twisted rope strip, twist across V; also the
                                                         # fish: its light bands read as scales
    'cloth': (CLOTH, (.004, .52, .085, .99)),            # plain blue banner cloth (mean rgb 52,64,85)
    'red': (CLOTH, (.87, .835, .95, .865)),              # plain red banner band: floats
    'pane': (GLASS, (.262, .752, .49, .998)),            # framed square window pane
}

POLE = (.5, .58)          # pole axis (x, y)
BAR_Z = 1.66              # banner bar
HINGE = (.5, .535, 1.64)  # the cloth swings about the bar (x axis)
SWING = .07               # radians each way
DECK = .04                # landing top
SEAT = (.5, .17, DECK)    # the idle fisher sits at the front, facing out (vanilla seat .5/.17)


class Kit:
    """Faces with one explicit atlas island each, into a frontier_architecture Geometry."""

    def __init__(self, name, origin=(0, 0, 0)):
        self.g = Geometry(name, origin)
        self.board = 0

    def next_board(self):
        self.board = (self.board + 3) % 8
        return f'board{self.board}'

    def face(self, points, tile, along=(0, 0, 1)):
        material, (u0, v0, u1, v1) = TILES[tile]
        pts = [Vector(p) for p in points]
        normal = Vector((0, 0, 0))
        for i in range(1, len(pts) - 1):
            normal += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0])
        if normal.length < 1e-12:
            raise ValueError(f'{self.g.name}: degenerate face {points}')
        normal.normalize()
        a = Vector(along)
        a = a - normal * a.dot(normal)
        if a.length < 1e-6:
            # The grain axis is the face normal (an end face): grain along x, else y.
            a = Vector((1, 0, 0)) - normal * normal.x
            if a.length < 1e-6:
                a = Vector((0, 1, 0)) - normal * normal.y
        a.normalize()
        across = normal.cross(a)
        coords = [(p.dot(across), p.dot(a)) for p in pts]
        lo = [min(c[i] for c in coords) for i in range(2)]
        span = [max(c[i] for c in coords) - lo[i] for i in range(2)]
        if min(span) < 1e-9:
            raise ValueError(f'{self.g.name}: face without area in its tile {points}')
        uvs = [(u0 + (c[0] - lo[0]) / span[0] * (u1 - u0), v0 + (c[1] - lo[1]) / span[1] * (v1 - v0)) for c in coords]
        self.g.native_piece([tuple(p) for p in pts], [tuple(range(len(pts)))], uvs, material)

    def box(self, lo, hi, tile, along=(0, 0, 1), skip=(), tiles=None):
        x0, y0, z0 = lo
        x1, y1, z1 = hi
        faces = {
            'bottom': [(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)],
            'top': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
            'front': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            'right': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            'back': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
            'left': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
        }
        for name, pts in faces.items():
            if name not in skip:
                self.face(pts, (tiles or {}).get(name, tile), along)

    def beam(self, a, b, width, depth, tile, up=(0, 0, 1), caps=True):
        """A square-section bar from a to b, its grain along the bar."""
        a, b = Vector(a), Vector(b)
        axis = (b - a).normalized()
        side = axis.cross(Vector(up))
        if side.length < 1e-6:
            side = axis.cross(Vector((1, 0, 0)))
        side.normalize()
        normal = side.cross(axis).normalized()
        w, d = side * width / 2, normal * depth / 2
        ring = [-w - d, w - d, w + d, -w + d]
        lo = [a + r for r in ring]
        hi = [b + r for r in ring]
        for i in range(4):
            j = (i + 1) % 4
            self.face([lo[i], lo[j], hi[j], hi[i]], tile, axis)
        if caps:
            self.face(list(reversed(lo)), tile, side)
            self.face(hi, tile, side)

    def cylinder(self, center, radius, z0, z1, segments, tile, top=None, bottom=False, radius_top=None):
        cx, cy = center
        rt = radius if radius_top is None else radius_top
        lo = [(cx + radius * math.cos(i * math.tau / segments), cy + radius * math.sin(i * math.tau / segments), z0) for i in range(segments)]
        hi = [(cx + rt * math.cos(i * math.tau / segments), cy + rt * math.sin(i * math.tau / segments), z1) for i in range(segments)]
        for i in range(segments):
            j = (i + 1) % segments
            self.face([lo[i], lo[j], hi[j], hi[i]], tile if isinstance(tile, str) else tile(i))
        if top:
            self.face(hi, top)
        if bottom:
            self.face(list(reversed(lo)), top or (tile if isinstance(tile, str) else tile(0)))

    def slab(self, pieces, plane_y, thickness, tile, along=(0, 0, 1), front=True, back=True):
        """A thin slab in the x/z plane, from plane_y back by thickness. pieces:
        convex polygons (x, z), counter-clockwise seen from the front (-y), that
        tile the slab and share their inner edges exactly; the edge faces run
        round the outer boundary only, so no two faces coincide. front/back False
        leave out a face that lies against another surface."""
        for piece in pieces:
            if front:
                self.face([(x, plane_y, z) for x, z in piece], tile, along)
            if back:
                self.face([(x, plane_y + thickness, z) for x, z in reversed(piece)], tile, along)
        edges = {}
        for piece in pieces:
            for i, a in enumerate(piece):
                b = piece[(i + 1) % len(piece)]
                key = (round(a[0], 6), round(a[1], 6), round(b[0], 6), round(b[1], 6))
                twin = (key[2], key[3], key[0], key[1])
                if twin in edges:
                    del edges[twin]
                else:
                    edges[key] = (a, b)
        for a, b in edges.values():
            self.face([(b[0], plane_y, b[1]), (a[0], plane_y, a[1]), (a[0], plane_y + thickness, a[1]), (b[0], plane_y + thickness, b[1])], tile, along)


def fish_pieces(cx, cz, length, height, facing=1):
    """A fish seen from the side, nose toward +x (facing 1) or -x: a convex body
    and a convex tail sharing the body's rear chord, counter-clockwise from the front."""
    ring = []
    for k in range(10):
        t = math.tau * k / 10
        ring.append((cx + facing * (math.cos(t) * length * .34 + length * .08), cz + math.sin(t) * height * .5 * (1 + .12 * math.cos(t))))
    # Vertices 4 and 6 bound the rear chord; vertex 5 (the rear point) gives way to the tail.
    body = ring[:5] + ring[6:]
    upper, lower = ring[4], ring[6]
    tip = cx - facing * length * .5
    tail = [upper, (tip, cz + height * .48), (tip, cz - height * .48), lower]
    if facing < 0:
        body.reverse()
        tail.reverse()
    return [body, tail]


def landing(k):
    # Plank landing on four bearers; the boards run across, as on a jetty.
    for i, (y0, y1) in enumerate(((.04, .26), (.26, .48), (.48, .72), (.72, .96))):
        k.box((.05, y0 + .004, 0), (.95, y1 - .004, DECK), f'plank{(i * 2) % 5}', along=(1, 0, 0), skip=('bottom',))


def posts_and_ropes(k):
    corners = ((.1, .1), (.9, .1), (.1, .9), (.9, .9))
    for x, y in corners:
        k.box((x - .035, y - .035, DECK), (x + .035, y + .035, .46), k.next_board(), tiles={'top': 'endgrain'}, skip=('bottom',))
    r = .009
    # Back, left and right ropes at two heights; the front stays open for the entrance.
    for z in (.40, .24):
        k.beam((.135, .9, z), (.865, .9, z), r * 2, r * 2, 'rope', caps=False)
    for x in (.1, .9):
        k.beam((x, .135, .40), (x, .865, .40), r * 2, r * 2, 'rope', caps=False)


def net(k):
    # A diamond-mesh net hung in front of the back ropes. The two strand directions
    # sit at different depths, so no two strands share a plane where they cross.
    x0, x1, z0, z1 = .15, .85, .07, .39
    pitch = .085
    for direction, y in ((1, .880), (-1, .870)):
        c = x0 - (z1 - z0)
        while c < x1 + (z1 - z0):
            # direction 1: x = c + (z - z0); direction -1: x = c + (z1 - z).
            if direction > 0:
                za, zb = max(z0, x0 - c + z0), min(z1, x1 - c + z0)
                x = lambda z: c + (z - z0)
            else:
                za, zb = max(z0, c + z1 - x1), min(z1, c + z1 - x0)
                x = lambda z: c + (z1 - z)
            if zb - za > .04:
                k.beam((x(za), y, za), (x(zb), y, zb), .012, .006, 'rope', up=(0, 1, 0), caps=False)
            c += pitch
    # Head and foot lines, and the floats on the head line.
    k.beam((x0, .869, z1), (x1, .869, z1), .016, .012, 'rope', up=(0, 1, 0), caps=False)
    k.beam((x0, .875, z0), (x1, .875, z0), .012, .008, 'rope', up=(0, 1, 0), caps=False)
    for fx in (.24, .42, .58, .76):
        k.cylinder((fx, .862), .026, z1 - .03, z1 + .03, 6, 'red', top='red', bottom=True)


def pole_and_lantern(k):
    px, py = POLE
    k.cylinder(POLE, .034, DECK, 1.74, 8, 'board1', top='endgrain', radius_top=.028)
    k.box((px - .07, py - .07, DECK), (px + .07, py + .07, DECK + .07), 'board5', tiles={'top': 'endgrain'}, skip=('bottom',))
    # Banner bar across the front of the pole, on a short arm.
    k.beam((px, py - .02, BAR_Z), (px, HINGE[1] - .005, BAR_Z), .03, .03, 'board6')
    k.beam((.25, HINGE[1], BAR_Z), (.75, HINGE[1], BAR_Z), .034, .034, 'board2', up=(0, 1, 0))
    # Lantern on an arm at the front of the pole.
    lx, ly, lz = px, py - .13, .78
    k.beam((px, py - .03, lz + .2), (lx, ly, lz + .2), .022, .022, 'board3')
    k.beam((lx, ly, lz + .2), (lx, ly, lz + .15), .012, .012, 'board4', caps=False)
    s = .045
    for name, pts in (('front', [(lx - s, ly - s, lz), (lx + s, ly - s, lz), (lx + s, ly - s, lz + .1), (lx - s, ly - s, lz + .1)]),
                      ('right', [(lx + s, ly - s, lz), (lx + s, ly + s, lz), (lx + s, ly + s, lz + .1), (lx + s, ly - s, lz + .1)]),
                      ('back', [(lx + s, ly + s, lz), (lx - s, ly + s, lz), (lx - s, ly + s, lz + .1), (lx + s, ly + s, lz + .1)]),
                      ('left', [(lx - s, ly + s, lz), (lx - s, ly - s, lz), (lx - s, ly - s, lz + .1), (lx - s, ly + s, lz + .1)])):
        k.face(pts, 'pane')
    k.box((lx - s - .01, ly - s - .01, lz - .025), (lx + s + .01, ly + s + .01, lz), 'board7')
    c = s + .012
    cap = [(lx - c, ly - c, lz + .1), (lx + c, ly - c, lz + .1), (lx + c, ly + c, lz + .1), (lx - c, ly + c, lz + .1)]
    apex = (lx, ly, lz + .15)
    for i in range(4):
        k.face([cap[i], cap[(i + 1) % 4], apex], 'board0')
    k.face(list(reversed(cap)), 'board0')


def banner(k):
    # The swinging cloth (its own object, origin at the hinge): blue cloth with a
    # swallowtail and a stitched fish on each face, nose toward the right.
    y, t = HINGE[1] + .004, .016
    top, hem, notch = BAR_Z - .015, 1.06, 1.18
    k.slab([[(.28, top), (.28, hem), (.5, notch), (.5, top)], [(.5, top), (.5, notch), (.72, hem), (.72, top)]], y, t, 'cloth')
    fish = fish_pieces(.5, 1.42, .30, .13)
    k.slab(fish, y - .006, .006, 'rope', along=(1, 0, 0), back=False)
    k.slab(fish, y + t, .006, 'rope', along=(1, 0, 0), front=False)
    # Dark battens hemmed into both side edges, as the vanilla banner's frame.
    for x in (.28, .72):
        k.box((x - .012, y - .004, hem + .01), (x + .012, y + t + .004, top), 'board4', tiles={'top': 'endgrain', 'bottom': 'endgrain'})
    # Bead eyes, front and back.
    k.box((.575, y - .010, 1.435), (.595, y - .006, 1.455), 'board1', skip=('back',))
    k.box((.575, y + t + .006, 1.435), (.595, y + t + .010, 1.455), 'board1', skip=('front',))


def gear(k):
    # Two rods leaning in the back-left corner, each with a hanging line.
    for (bx, by), (tx, ty, tz) in (((.2, .8), (.07, .95, 1.18)), ((.27, .82), (.16, .955, 1.05))):
        k.beam((bx, by, DECK + .001), (tx, ty, tz), .016, .016, 'board3', caps=True)
        k.beam((tx, ty, tz), (tx, ty, tz - .32), .005, .005, 'rope', caps=False)
    # A tub of catch at the front right: staves and two fish heads above the rim.
    tub(k, (.76, .3), .1, .11, DECK, DECK + .16)
    for cx, cz, facing in ((.735, DECK + .17, 1), (.79, DECK + .155, -1)):
        k.slab(fish_pieces(cx, cz, .12, .05, facing), .29, .02, 'rope', along=(1, 0, 0))
    # A fish crate on the right, behind the tub.
    k.box((.66, .5, DECK), (.86, .7, DECK + .16), 'crate', along=(0, 0, 1), tiles={'top': 'plank3'}, skip=('bottom',))


def tub(k, center, r0, r1, z0, z1, segments=8):
    """Open stave tub: outer and inner walls, a rim, and the catch level inside."""
    cx, cy = center
    def ring(r, z):
        return [(cx + r * math.cos(i * math.tau / segments), cy + r * math.sin(i * math.tau / segments), z) for i in range(segments)]
    wall = .012
    lo, hi = ring(r0, z0), ring(r1, z1)
    inner_lo, inner_hi = ring(r0 - wall, z1 - .06), ring(r1 - wall, z1)
    for i in range(segments):
        j = (i + 1) % segments
        k.face([lo[i], lo[j], hi[j], hi[i]], f'board{i % 8}')
        k.face([inner_lo[j], inner_lo[i], inner_hi[i], inner_hi[j]], f'board{(i + 4) % 8}')
        k.face([hi[i], hi[j], inner_hi[j], inner_hi[i]], 'endgrain')
    k.face(inner_lo, 'planks')


def build_stage():
    """Construction stage: the landing laid, the post stumps set and the pole
    lying on the boards, waiting to be raised (vanilla flags show a staked
    base at this stage)."""
    k = Kit(f'{IDENT}.ConstructionStage0')
    landing(k)
    for x, y in ((.1, .1), (.9, .1), (.1, .9), (.9, .9)):
        k.box((x - .035, y - .035, DECK), (x + .035, y + .035, DECK + .14), k.next_board(), tiles={'top': 'endgrain'}, skip=('bottom',))
    k.beam((.14, .42, DECK + .025), (.6, .6, DECK + .025), .05, .05, 'board1')
    k.box((.66, .5, DECK), (.86, .7, DECK + .16), 'crate', tiles={'top': 'plank3'}, skip=('bottom',))
    return k.g


def build():
    """(static geometry, banner geometry, seat transform)."""
    static = Kit(f'{IDENT}.Structure')
    landing(static)
    posts_and_ropes(static)
    net(static)
    pole_and_lantern(static)
    gear(static)
    swing = Kit(f'{IDENT}.Banner', HINGE)
    banner(swing)
    return static.g, swing.g, SEAT
