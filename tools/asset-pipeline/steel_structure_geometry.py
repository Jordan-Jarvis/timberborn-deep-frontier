"""Riveted steel structures: cantilevers, truss bridges, columns and decks.

Late-game steel (docs/art/lategame-style.md): bare structural steel (IRON,
BaseMetal) in riveted trusses and trestles and in the deck sheets (all
BaseMetal, like the vanilla metal platform), brass rivet heads (BRASS, Details) at the
gusset plates, and cast concrete (CIVIC_CONCRETE, Plaster_White) only where
a piece bears on the ground: cantilever anchor piers and bridge abutment
piers. No bevel (structural pieces build as culled shells).

Art space as in structural_geometry.py: X across, Y along, Z up, one unit per
tile and layer; geometry stays inside its native block grid (bridges also
hang below their layer, into the open cell under the span, like the vanilla
suspension bridge). Grid contracts per family, in structural_layouts.py and
tools/structural_building_content.mjs:

SteelCantilever<N>x1 (N = 10, 12, 15; anchors A = 1, 2, 3), size [1, N, 1]:
  a deck of riveted plates (top exactly 1.0) on two Warren trusses under its
  side edges. The trusses are full depth over the A anchor tiles, where they
  stand on concrete piers, and taper to a shallow tip. Below the plates the
  strip x 0.2..0.8 is clear up to 0.84, as under the concrete overhang.
SteelBridge<N>x1 (N = 8, 10, 12, 15 span tiles), size [1, N+1, 1]: the
  near tile y 0..1 is the supported abutment (two concrete piers carrying
  the portal posts); a riveted deck plate (top 0.03, the vanilla suspension
  bridge's plank height) runs y 0..N+1 on cross girders and stringers that
  hang into the open cell below, between two pony Warren trusses whose top
  chords are the hand rails. The walking strip x 0.17..0.83 is clear from
  the deck to 0.95 over the whole length.
SteelColumnH<H> (H = 1..6), size [1, 1, H]: a four-post riveted steel
  trestle in the cell corners (native Corners occupation), joined by ties and
  knee braces high in every layer, with a riveted cap plate whose top is
  exactly H (the stackable top). Each layer is open below 0.84 for paths.
SteelDeck<n>x<n> (n = 3, 5), size [n, n, 1]: riveted deck plates (top
  exactly 1.0) on perimeter girders and seam joists, carried by a one-layer
  corner trestle in each of the four corner cells (the native foundations).
"""
import math

from frontier_architecture import IRON, BRASS
from reference_materials import CIVIC_CONCRETE as CONCRETE
from walkway_geometry import RailAssembly
from steel_structure_grid import (CANTILEVERS, BRIDGE_SPANS, COLUMN_HEIGHTS, DECK_SPANS,
                                  cantilever_ident, bridge_ident, column_ident, deck_ident)

BRIDGE_DECK_TOP = .03
BRIDGE_UNDERSIDE = -.22      # lowest bridge steel, inside the open cell below the span
BRIDGE_RAIL_TOP = .80
CLEAR_BELOW_DECK = .84       # cantilever, column and deck layers are open below this


def _blk(g, x0, y0, z0, x1, y1, z1, mat):
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError(f'Degenerate steel block {(x0, y0, z0, x1, y1, z1)}')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat)


def rivet(g, p, axis):
    """Brass rivet head: a six-sided prism half buried in its plate."""
    g.cylinder(p, .021, .022, BRASS, axis, 6)


def gusset(g, x_face, outward, y, z, half_y=.11, half_z=.08):
    """Riveted gusset plate on the outer face of a truss node. `x_face` is the
    plate's outer face; the plate reaches 28 mm back into the truss members.
    Two rivet heads stand on the outer face."""
    if outward < 0:
        _blk(g, x_face, y - half_y, z - half_z, x_face + .028, y + half_y, z + half_z, IRON)
    else:
        _blk(g, x_face - .028, y - half_y, z - half_z, x_face, y + half_y, z + half_z, IRON)
    for dy in (-half_y * .55, half_y * .55):
        rivet(g, (x_face, y + dy, z), 'X')


def deck_plate(g, x0, y0, x1, y1, top, thickness):
    """One riveted deck sheet; neighbouring sheets keep a 12 mm seam."""
    _blk(g, x0, y0, top - thickness, x1, y1, top, IRON)


# ------------------------------------------------------------- cantilevers

def cantilever_for(length):
    if length not in CANTILEVERS:
        raise ValueError(f'Unsupported steel cantilever length {length}')
    anchors = CANTILEVERS[length]
    top = 1.0
    plate = .09
    chord_top = top - plate + .02            # top chord buried 2 cm in the plates
    deep, shallow = .24, .66                 # bottom chord centre: anchors, tip

    def bottom_z(y):
        if y <= anchors:
            return deep
        return deep + (shallow - deep) * (y - anchors) / (length - anchors)

    def build(g, parts):
        # Deck sheets, one per tile.
        for y in range(length):
            deck_plate(g, .015, y + .006, .985, y + .994, top, plate)
        # Transverse floor beams under every seam and both ends, tops buried
        # in the sheets, all above the clear strip below.
        for k in range(length + 1):
            y0, y1 = (k - .035, k + .035) if 0 < k < length else ((.02, .09) if k == 0 else (length - .09, length - .02))
            _blk(g, .15, y0, CLEAR_BELOW_DECK + .018, .85, y1, top - plate + .015, IRON)
        for side in (0, 1):
            xc = .11 if side == 0 else .89
            sx = -1 if side == 0 else 1          # outward
            # Top chord (one member, full length).
            _blk(g, xc - .05, .03, chord_top - .08, xc + .05, length - .025, chord_top, IRON)
            # Bottom chord: full depth along the anchors, then rising to the tip.
            nodes = [(float(k), bottom_z(k)) for k in range(length + 1)]
            nodes[0] = (.06, deep)
            nodes[-1] = (length - .06, shallow)
            # Neighbouring segments overlap at the nodes, so they alternate
            # 8 mm in width and 7 mm in depth: no shared side or soffit plane.
            for k, ((ya, za), (yb, zb)) in enumerate(zip(nodes, nodes[1:])):
                g.beam((xc, ya - (.03 if ya > .06 else 0), za), (xc, yb + (.03 if yb < length - .06 else 0), zb),
                       .09 if k % 2 == 0 else .082, .075 if k % 2 == 0 else .068, IRON)
            # Verticals at every tile boundary, heavier over the anchors.
            for k, (y, z) in enumerate(nodes):
                width = .075 if k <= anchors else .06
                g.beam((xc, y, z - .03), (xc, y, chord_top - .04), width, width, IRON)
            # Diagonals, one per panel, alternating (Warren).
            for k, ((ya, za), (yb, zb)) in enumerate(zip(nodes, nodes[1:])):
                if k % 2 == 0:
                    g.beam((xc, ya, za), (xc, yb, chord_top - .05), .05, .05, IRON)
                else:
                    g.beam((xc, ya, chord_top - .05), (xc, yb, zb), .05, .05, IRON)
            # Gussets at the bottom nodes (riveted, outer face).
            face = xc + sx * .068
            for y, z in nodes:
                y = min(length - .13, max(.13, y))
                gusset(g, face, sx, y, z + .025)
            # Concrete anchor piers under the full-depth trusses, with a
            # buried steel bearing plate.
            for a in range(anchors):
                _blk(g, xc - .09, a + .1, 0, xc + .09, a + .9, deep - .05, CONCRETE)
                _blk(g, xc - .104, a + .08, deep - .06, xc + .104, a + .92, deep - .025, IRON)
        # Lateral struts between the trusses along the anchors.
        for a in range(anchors + 1):
            y = min(anchors - .04, max(.04, float(a)))
            _blk(g, .14, y - .03, deep - .025, .86, y + .03, deep + .025, IRON)
        # Tip fascia under the last sheet.
        _blk(g, .03, length - .03, top - plate - .1, .97, length - .01, top - plate + .02, IRON)
        return RailAssembly('StructureRails')
    return build


# ------------------------------------------------------------- bridges

def bridge_for(span):
    if span not in BRIDGE_SPANS:
        raise ValueError(f'Unsupported steel bridge span {span}')
    end = span + 1.0                          # far edge of the last span tile
    plate = .05

    def build(g, parts):
        # Abutment: two concrete piers at the sides of the supported tile.
        for x0, x1 in ((.02, .2), (.8, .98)):
            _blk(g, x0, .04, 0, x1, .96, .17, CONCRETE)
        # Deck sheets (top exactly BRIDGE_DECK_TOP), one per tile.
        for y in range(span + 1):
            deck_plate(g, .1, y + .006, .9, y + .994, BRIDGE_DECK_TOP, plate)
        # Floor system under the span: cross girders at the tile boundaries
        # and both ends, two stringers, one lateral brace per panel.
        under = BRIDGE_DECK_TOP - plate
        for k in range(1, span + 2):
            y0, y1 = (k - .035, k + .035) if k <= span else (end - .08, end - .012)
            _blk(g, .05, y0, BRIDGE_UNDERSIDE, .95, y1, under + .01, IRON)
        for x in (.32, .68):
            _blk(g, x - .04, 1.0, under - .15, x + .04, end - .03, under + .008, IRON)
        for k in range(1, span + 1):
            a, b = (.12, .88) if k % 2 else (.88, .12)
            g.beam((a, k + .01, BRIDGE_UNDERSIDE + .06), (b, min(end - .03, k + .99), BRIDGE_UNDERSIDE + .06), .04, .03, IRON)
        for side in (0, 1):
            xc = .07 if side == 0 else .93
            sx = -1 if side == 0 else 1
            # Bottom chord along the deck edge, top chord as the hand rail.
            _blk(g, xc - .04, .86, -.1, xc + .04, end - .02, -.004, IRON)
            _blk(g, xc - .045, .96, BRIDGE_RAIL_TOP - .08, xc + .045, end - .02, BRIDGE_RAIL_TOP, IRON)
            # Portal post on the abutment pier, and the far end post.
            _blk(g, xc - .055, .4, .16, xc + .055, .52, BRIDGE_RAIL_TOP + .06, IRON)
            g.beam((xc, .5, BRIDGE_RAIL_TOP - .04), (xc, 1.1, BRIDGE_RAIL_TOP - .04), .07, .06, IRON)
            g.beam((xc, end - .06, -.08), (xc, end - .06, BRIDGE_RAIL_TOP - .02), .07, .07, IRON)
            # Verticals at the tile boundaries, diagonals per panel.
            for k in range(1, span + 1):
                g.beam((xc, k, -.08), (xc, k, BRIDGE_RAIL_TOP - .03), .055, .05, IRON)
            for k in range(1, span + 1):
                ya, yb = float(k), min(end - .06, k + 1.0)
                if k % 2:
                    g.beam((xc, ya, -.05), (xc, yb, BRIDGE_RAIL_TOP - .05), .045, .04, IRON)
                else:
                    g.beam((xc, ya, BRIDGE_RAIL_TOP - .05), (xc, yb, -.05), .045, .04, IRON)
            # Riveted gussets at the bottom nodes and on the portal knee.
            face = xc + sx * .058
            for k in range(1, span + 2):
                gusset(g, face, sx, min(end - .13, float(k)), -.05, .1, .07)
            gusset(g, face, sx, .66, BRIDGE_RAIL_TOP - .095, .1, .07)
        return RailAssembly('StructureRails')
    return build


# ------------------------------------------------------------- columns and decks

POST = (.12, .88)


def trestle(g, z0, z1, ties_at):
    """Four corner posts from z0 to z1 with base plates, joint collars, and
    ties plus knee braces just below every height in `ties_at`."""
    for x in POST:
        for y in POST:
            _blk(g, x - .1, y - .1, z0, x + .1, y + .1, z0 + .04, IRON)          # base plate
            _blk(g, x - .06, y - .06, z0 + .03, x + .06, y + .06, z1, IRON)       # post
    for zt in ties_at:
        # Collars on the posts at the tie level.
        for x in POST:
            for y in POST:
                _blk(g, x - .075, y - .075, zt - .16, x + .075, y + .075, zt - .06, IRON)
        # Perimeter ties between the posts (their ends buried in the collars).
        for y in POST:
            _blk(g, .17, y - .035, zt - .15, .83, y + .035, zt - .07, IRON)
        for x in POST:
            _blk(g, x - .03, .17, zt - .145, x + .03, .83, zt - .075, IRON)
        # Knee braces from each post up to the tie, on all four faces.
        for y in POST:
            for x, d in ((.12, 1), (.88, -1)):
                g.beam((x, y, zt - .36), (x + d * .26, y, zt - .11), .045, .04, IRON)
        for x in POST:
            for y, d in ((.12, 1), (.88, -1)):
                g.beam((x, y, zt - .36), (x, y + d * .26, zt - .11), .04, .045, IRON)
        # Rivets on the outer collar faces.
        for x in POST:
            for y in POST:
                rivet(g, (x, y - .075 if y < .5 else y + .075, zt - .11), 'Y')


def column_for(height):
    if height not in COLUMN_HEIGHTS:
        raise ValueError(f'Unsupported steel column height {height}')
    top = float(height)
    plate = .07

    def build(g, parts):
        trestle(g, 0, top - plate + .02, [k + .0 for k in range(1, height)] + [top - plate + .005])
        # Cap: riveted plate over a perimeter channel (stackable top = H).
        deck_plate(g, .015, .015, .985, .985, top, plate)
        for y in (.05, .95):
            _blk(g, .03, y - .03, top - plate - .07, .97, y + .03, top - plate + .01, IRON)
        for x in (.05, .95):
            _blk(g, x - .025, .07, top - plate - .065, x + .025, .93, top - plate + .012, IRON)
        return RailAssembly('StructureRails')
    return build


def deck_for(n):
    if n not in DECK_SPANS:
        raise ValueError(f'Unsupported steel deck {n}x{n}')
    top = 1.0
    plate = .08
    under = top - plate

    def build(g, parts):
        # Corner trestles (the four native foundation cells).
        for cx in (0, n - 1):
            for cy in (0, n - 1):
                sub = _Offset(g, cx, cy)
                trestle(sub, 0, under + .02, [under + .005])
        # Perimeter girders, tops buried in the plates, bottoms above the
        # clear height of the layer below the deck.
        for y0, y1 in ((.02, .1), (n - .1, n - .02)):
            _blk(g, .02, y0, CLEAR_BELOW_DECK + .005, n - .02, y1, under + .015, IRON)
        for x0, x1 in ((.026, .1), (n - .1, n - .026)):
            _blk(g, x0, .06, CLEAR_BELOW_DECK + .01, x1, n - .06, under + .012, IRON)
        # Joists under every interior seam, both ways (they cross; their tops
        # stand at different depths inside the plates).
        for k in range(1, n):
            _blk(g, k - .03, .08, CLEAR_BELOW_DECK + .02, k + .03, n - .08, under + .01, IRON)
            _blk(g, .08, k - .025, CLEAR_BELOW_DECK + .025, n - .08, k + .025, under + .008, IRON)
        for x in range(n):
            for y in range(n):
                deck_plate(g, x + .006, y + .006, x + .994, y + .994, top, plate)
        # Rivet heads along the girder faces, one per tile.
        for k in range(n):
            for y, axis in ((.02, 'Y'), (n - .02, 'Y')):
                rivet(g, (k + .5, y, CLEAR_BELOW_DECK + .045), axis)
            for x in (.02, n - .02):
                rivet(g, (x, k + .5, CLEAR_BELOW_DECK + .045), 'X')
        return RailAssembly('StructureRails')
    return build


class _Offset:
    """Geometry proxy that shifts box/beam/cylinder calls by whole tiles."""
    def __init__(self, g, dx, dy):
        self.g, self.dx, self.dy = g, dx, dy

    def _p(self, p):
        return (p[0] + self.dx, p[1] + self.dy, p[2])

    def box(self, p, size, mat):
        self.g.box(self._p(p), size, mat)

    def beam(self, a, b, width=.12, depth=None, mat=IRON):
        self.g.beam(self._p(a), self._p(b), width, depth, mat)

    def cylinder(self, p, r, length, mat, axis='Z', segments=16):
        self.g.cylinder(self._p(p), r, length, mat, axis, segments)


# ------------------------------------------------------------- registration

MODELS = {cantilever_ident(n): cantilever_for(n) for n in CANTILEVERS}
MODELS.update({bridge_ident(n): bridge_for(n) for n in BRIDGE_SPANS})
MODELS.update({column_ident(h): column_for(h) for h in COLUMN_HEIGHTS})
MODELS.update({deck_ident(n): deck_for(n) for n in DECK_SPANS})
