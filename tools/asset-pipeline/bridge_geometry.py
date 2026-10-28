"""Concrete arch and steel truss bridges for the structural pipeline (art only).

Kept out of structural_geometry.py until its owner's current edits settle;
registration is an additive patch (see BRIDGE_SIZES / register notes below):
  structural_geometry.MODELS.update(bridge_geometry.MODELS)
  structural_layouts.SIZES.update(bridge_geometry.BRIDGE_SIZES) (before LAYOUTS),
  LAYOUTS[name]['supportLayer'] = 1 for every bridge (the deck is layer 1),
  render_reference_studies.STRUCTURAL_CAMERA_SCALE.update(CAMERA_SCALE).

Art space as in structural_geometry: X across, Y along the span, Z up; one
unit = one tile / one layer; the 32-slot civic palette (native slots only:
BaseWood_DarkBrown 0, BaseMetal 2, Details 7, Plaster_White 27,
IrregularPlanks_MetalForged 29). The walkable deck top is exactly z = 1.0.

ConcreteArchBridge<n> (n = 3..6), size [1, n, 1]: abutment end cells (solid to
the ground), a segmental concrete arch ring over the n-2 middle cells with
recessed spandrel walls, per-cell deck slabs with 12 mm seams, riveted steel
edge channels and steel-and-timber railings on both sides. The railings stand
in the walking layer above the 1-layer module (as rails on native platforms
do); validate_bridge_sources checks they stay outside the walking strip.

SteelTrussBridge<n> (n = 6, 8, 10), size [2, n, 2]: concrete abutments in the
end cells of layer 0, cross girders and stringers under riveted steel deck
plates (top z = 1.0), two Warren trusses (layer 1) with gusset plates, top
lateral struts above z 1.85, a timber handrail inside each truss. The walking
layer between the trusses is clear from z 1.0 to 1.8 for x 0.3..1.7.
"""
import math

from frontier_architecture import WOOD, IRON, BRASS
from reference_materials import CIVIC_CONCRETE as CONCRETE, CIVIC_FORGED_PANEL as FORGED
from walkway_geometry import RailAssembly

ARCH_SPANS = (3, 4, 5, 6)
TRUSS_SPANS = (6, 8, 10)
DECK_TOP = 1.0
RAIL_TOP = 1.66          # arch bridge railing top (walking layer above the module)
TRUSS_CLEAR = 1.8        # clear headroom between the trusses


def _blk(g, x0, y0, z0, x1, y1, z1, mat):
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError(f'Degenerate bridge block {x0, y0, z0, x1, y1, z1}')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat)


def _prism_x(g, profile, x0, x1, mat):
    """Prism of a (y, z) profile (counter-clockwise, y to the right) along X."""
    from lategame_kit import extrude_profile
    extrude_profile(g, profile, x0, x1, mat, axis='X')


# ---------------------------------------------------------------- arch bridge

def arch_bridge_for(n):
    if n not in ARCH_SPANS:
        raise ValueError(f'Unsupported arch bridge length {n}')
    soffit = .86                     # deck slab underside
    zs = .12                         # springing
    span = n - 2
    crown = .62 if span == 1 else .7
    rise = crown - zs
    R = ((span / 2) ** 2 + rise ** 2) / (2 * rise)
    yc, zc = n / 2, crown - R

    def intrados(y):
        return zc + math.sqrt(max(0.0, R * R - (y - yc) ** 2))

    def build(g, parts):
        # Abutments: solid to the ground, with a proud plinth course and a
        # recessed panel on each side face.
        for a, b in ((0.0, 1.0), (n - 1.0, float(n))):
            _blk(g, .03, a, 0, .97, b, soffit, CONCRETE)
            # Plinth course proud of the side faces; its bottom sits 1 cm up,
            # so only the abutment core owns the ground plane.
            _blk(g, .015, a + .04, .01, .985, b - .04, .16, CONCRETE)
        # Arch ring and spandrels (prisms along X).
        k = 24
        ys = [1 + span * i / k for i in range(k + 1)]
        def extrados(y):
            return min(soffit - .02, intrados(y) + .12)
        # Ring: intrados left to right, extrados back (counter-clockwise).
        ring = [(y, intrados(y)) for y in ys] + [(y, extrados(y)) for y in reversed(ys)]
        _prism_x(g, _ccw(ring), .035, .965, CONCRETE)
        # Spandrel walls 3 cm behind the ring faces, seated 2 cm into it.
        spandrel = [(y, extrados(y) - .02) for y in ys] + [(n - 1.0, soffit), (1.0, soffit)]
        _prism_x(g, _ccw(spandrel), .09, .91, CONCRETE)
        # Keystone proud of the ring on both faces.
        kz = intrados(yc)
        _blk(g, .025, yc - .09, kz - .02, .975, yc + .09, min(soffit - .005, kz + .17), CONCRETE)
        # Deck slabs, one per cell with 12 mm seams; top exactly DECK_TOP.
        for y in range(n):
            _blk(g, .03, y + .006, soffit, .97, y + .994, DECK_TOP, CONCRETE)
        # Riveted steel edge channels: web plus bottom flange, below the deck top.
        for side in (0, 1):
            x0, x1 = (.008, .03) if side == 0 else (.97, .992)
            _blk(g, x0, .0, .74, x1, float(n), .99, IRON)
            # Flange seated 1 cm into the web: no face on the abutment planes.
            f0, f1 = (.02, .07) if side == 0 else (.93, .98)
            _blk(g, f0, .0, .75, f1, float(n), .775, IRON)
            # Rivet heads 6 mm proud of the web, inside the module.
            xr = .006 if side == 0 else .994
            for i in range(2 * n):
                y = .25 + i * .5
                for z in (.8, .93):
                    g.cylinder((xr, y, z), .02, .008, BRASS, 'X', 8)
        # Railings: steel posts on the deck edge, steel mid rail, timber cap.
        for side in (0, 1):
            xc = .05 if side == 0 else .95
            for i in range(2 * n + 1):
                y = min(n - .03, max(.03, i * .5))
                _blk(g, xc - .02, y - .02, DECK_TOP - .01, xc + .02, y + .02, RAIL_TOP - .05, IRON)
            _blk(g, xc - .012, .03, 1.28, xc + .012, n - .03, 1.3, IRON)
            _blk(g, xc - .03, .0, RAIL_TOP - .05, xc + .03, float(n), RAIL_TOP, WOOD)
        return RailAssembly('StructureRails')
    return build


def _ccw(profile):
    """Return the (u, z) polygon wound counter-clockwise (shoelace > 0)."""
    area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(profile, profile[1:] + profile[:1]))
    return profile if area > 0 else list(reversed(profile))


# ---------------------------------------------------------------- truss bridge

def truss_bridge_for(n):
    if n not in TRUSS_SPANS:
        raise ValueError(f'Unsupported truss bridge length {n}')
    plate = .1                       # deck plate thickness
    ABUT_TOP = .78                   # bearing shelf; stringers and bearings sit on it

    def build(g, parts):
        # Concrete abutments in the end cells of layer 0, with bearing shelves.
        for a, b in ((0.0, 1.0), (n - 1.0, float(n))):
            _blk(g, .0, a, 0, 2.0, b, ABUT_TOP, CONCRETE)
        for a in (0.0, n - 1.0):
            inner = 1.0 if a == 0 else n - 1.0
            # Back wall face course toward the gap (proud 2 cm).
            y0, y1 = (inner, inner + .035) if a == 0 else (inner - .035, inner)
            _blk(g, .04, y0, .05, 1.96, y1, .72, CONCRETE)
        # Floor system: cross girders at every inner cell boundary, stringers.
        for y in range(1, n):
            _blk(g, .06, y - .07, .6, 1.94, y + .07, .63, IRON)            # bottom flange
            _blk(g, .06, y - .02, .63, 1.94, y + .02, .845, IRON)          # web
            _blk(g, .06, y - .06, .845, 1.94, y + .06, .876, IRON)          # top flange
        for x in (.55, 1.45):
            _blk(g, x - .05, .5, .78, x + .05, n - .5, DECK_TOP - plate, IRON)
        # Riveted deck plates, one per cell, 12 mm seams; top exactly DECK_TOP.
        for y in range(n):
            for x in range(2):
                xa = .09 if x == 0 else 1.006
                xb = .994 if x == 0 else 1.91
                _blk(g, xa, y + .006, DECK_TOP - plate, xb, y + .994, DECK_TOP, IRON)
        # Warren trusses on both sides.
        for side in (0, 1):
            _truss(g, n, side)
        # Top lateral struts between the top chords (above the clear height).
        for k in range(n - 1):
            y = 1.0 + k
            _blk(g, .085, y - .035, 1.87, 1.915, y + .035, 1.93, IRON)
        for k in range(n - 2):
            a, b = 1.0 + k, 2.0 + k
            p, q = ((.09, a, 1.9), (1.91, b, 1.9)) if k % 2 == 0 else ((1.91, a, 1.9), (.09, b, 1.9))
            g.beam(p, q, .035, .03, IRON)
        # Portal knee braces at the two end panels, outside the clear strip.
        for y in (1.0, n - 1.0):
            for x0, x1 in ((.085, .28), (1.915, 1.72)):
                g.beam((x0, y, 1.62), (x1, y, 1.9), .045, .04, IRON)
        return RailAssembly('StructureRails')
    return build


def _truss(g, n, side):
    """One Warren truss in the plane x = .05 (or 1.95): bottom chord at deck
    level, top chord at z ~1.9, inclined end posts, diagonals, gussets and a
    timber handrail on its inner face."""
    s = 1 if side == 0 else -1
    X = (lambda x: x) if side == 0 else (lambda x: 2.0 - x)

    def box(x0, x1, y0, y1, z0, z1, mat):
        a, b = sorted((X(x0), X(x1)))
        _blk(g, a, y0, z0, b, y1, z1, mat)

    # Chords: different widths, so no two members share a face plane.
    box(.01, .09, .1, n - .1, .84, .99, IRON)                 # bottom chord
    box(.015, .085, 1.0, n - 1.0, 1.82, 1.95, IRON)           # top chord
    bottom = [(.5 + k, .92) for k in range(n)]
    top = [(1.0 + k, 1.885) for k in range(n - 1)]
    xm = X(.05)
    for k in range(n - 1):
        (yb, zb), (yt, zt) = bottom[k], top[k]
        w = .065 if k in (0,) else .05
        g.beam((xm, yb, zb), (xm, yt, zt), w, w, IRON)
        (yb2, zb2) = bottom[k + 1]
        w = .065 if k == n - 2 else .05
        g.beam((xm, yt, zt), (xm, yb2, zb2), w, w, IRON)
    # Gusset plates on the outer face at every node (x 0..0.012).
    for (y, z) in bottom:
        box(.0, .012, y - .16, y + .16, .82, 1.0, IRON)
    for (y, z) in top:
        box(.0, .012, y - .16, y + .16, 1.76, 1.97, IRON)
    # Bearings under the truss ends on the abutment shelves.
    for y in (.5, n - .5):
        box(.005, .1, y - .14, y + .14, .77, .845, IRON)
    # Timber handrail and its brackets on the inner face.
    for k in range(n + 1):
        y = min(n - .15, max(.15, float(k)))
        box(.09, .13, y - .02, y + .02, 1.5, 1.58, IRON)
    box(.13, .18, .15, n - .15, 1.52, 1.58, WOOD)


# ---------------------------------------------------------------- registration data

def arch_ident(n):
    return f'ConcreteArchBridge{n}'


def truss_ident(n):
    return f'SteelTrussBridge{n}'


MODELS = {arch_ident(n): arch_bridge_for(n) for n in ARCH_SPANS}
MODELS.update({truss_ident(n): truss_bridge_for(n) for n in TRUSS_SPANS})
BRIDGE_SIZES = {arch_ident(n): [1, n, 1] for n in ARCH_SPANS}
BRIDGE_SIZES.update({truss_ident(n): [2, n, 2] for n in TRUSS_SPANS})
CAMERA_SCALE = {name: (1.15 if name.startswith('ConcreteArch') else 1.05) for name in MODELS}
# Native grid contract per bridge: ground (GroundOrStackable) under the end
# cells of layer 0; every middle cell MatterBelow Any; deck support on layer 1
# (the walking layer); the truss layer-1 cells are walkable between trusses.
SUPPORT = {}
for _n in ARCH_SPANS:
    SUPPORT[arch_ident(_n)] = {'groundCells': [[0, 0, 0], [0, _n - 1, 0]], 'deckTop': DECK_TOP,
                               'walkLayer': 1, 'railTop': RAIL_TOP}
for _n in TRUSS_SPANS:
    SUPPORT[truss_ident(_n)] = {'groundCells': [[x, y, 0] for y in (0, _n - 1) for x in (0, 1)],
                                'deckTop': DECK_TOP, 'walkLayer': 1, 'clearHeight': TRUSS_CLEAR}
