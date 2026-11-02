"""WarehouseModule: one stackable storage module of the modular warehouse.

Native contract (the parent's generator; not this module): a doorless
storage block that adds capacity to a Modular Warehouse core. Modules stack
on the core, on each other, or stand beside them; nobody enters one
(DOORLESS). Early game and unpowered: timber only, iron as straps and
hardware (no brick, concrete or plaster).

HERO: a slatted timber crib bound with iron corner straps, its crates and
barrels showing between the plank slats, with a little pulley and hook in a
niche on the front.
ROOF: flat plank deck exactly on layer 1, edge to edge, nothing on it: the
bed the next module stacks on.

Stacking rule: everything stays inside the 3x3x1 box. The sole plate and the
deck are flush with the cell faces, the posts stand 12 mm in and only the
iron straps reach the cell faces, so two modules side by side meet flat
planes (and a module on a module meets a flat deck) without clipping.

Animated (in the front niche, behind the cell face): the pulley (SPIN_Y,
turning in the wall plane) and the hook on its rope (SWAY_Y, swinging along
the wall).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON
from lategame_kit import GREYWOOD, GREYPLANK, FOLK_WOOD
from lategame_civic_parts import blk
from lategame_roofdeck_parts import deck_slab

IDENT = 'WarehouseModule'
FOOTPRINT = (3, 3)
HEIGHT = 1
FRAME_END = 121
DOORLESS = True
HERO = ('Slatted timber crib bound with iron corner straps, crates and barrels showing between its plank slats, '
        'with a pulley and hook in a front niche.')

W = 3.0
SOLE_TOP = .1
DECK_BASE = .88           # deck slab underside; posts and beams stop here
POST_FACE = .012          # posts 12 mm in from the cell faces
SLAT = (.02, .06)         # slat plane: front, back
CORE = .1                 # goods core face (crates behind the slats)
CORNER, POST = .14, .1
ROWS = ((.13, .29), (.33, .49), (.65, .78))   # slat rows; a wide gap .49-.65 shows the goods
NICHE = (1 + POST / 2, 2 - POST / 2)          # front middle bay, open for the pulley


def faces():
    """(axis, plane, outward) per side: front, back, left, right."""
    return (('X', 0.0, -1), ('X', W, 1), ('Y', 0.0, -1), ('Y', W, 1))


def box_on(g, axis, plane, out, u0, u1, d0, d1, z0, z1, mat):
    """Box from depth d0 to d1 behind the cell face `plane` (depth measured
    inward), spanning u0..u1 along the face."""
    a, b = sorted((plane - out * d0, plane - out * d1))
    if axis == 'X':
        blk(g, u0, a, z0, u1, b, z1, mat)
    else:
        blk(g, a, u0, z0, b, u1, z1, mat)


def base(g):
    blk(g, 0.0, 0.0, 0.0, W, W, SOLE_TOP, WOOD)                      # sole plate, flush
    blk(g, CORE, CORE, .08, W - CORE, W - CORE, .9, PLANK)           # stacked goods core (dark, reads as shadow)


def frame(g):
    lo, hi = POST_FACE, W - POST_FACE - CORNER
    for x0 in (lo, hi):
        for y0 in (lo, hi):
            blk(g, x0, y0, SOLE_TOP, x0 + CORNER, y0 + CORNER, DECK_BASE, WOOD)
    for axis, plane, out in faces():
        for u in (1.0, 2.0):
            box_on(g, axis, plane, out, u - POST / 2, u + POST / 2, POST_FACE, CORE + .01, SOLE_TOP, DECK_BASE, WOOD)
        # Top beam under the deck, between the corner posts.
        box_on(g, axis, plane, out, CORNER + POST_FACE, W - CORNER - POST_FACE, .025, CORE + .01,
               DECK_BASE - .08, DECK_BASE, WOOD)


def slats(g):
    bays = ((CORNER + POST_FACE, 1 - POST / 2), (1 + POST / 2, 2 - POST / 2), (2 + POST / 2, W - CORNER - POST_FACE))
    for i, (axis, plane, out) in enumerate(faces()):
        for bay in bays:
            if i == 0 and bay[0] == NICHE[0]:
                continue                  # the front niche
            for za, zb in ROWS:
                box_on(g, axis, plane, out, bay[0], bay[1], SLAT[0], SLAT[1], za, zb, GREYPLANK)


def goods(g):
    """Crates against the core, seen through the wide slat gap (front 30 mm
    behind the slat backs, back in the core), each with an iron band."""
    mats = (FOLK_WOOD, GREYWOOD, FOLK_WOOD, GREYPLANK, GREYWOOD)
    k = 0
    for i, (axis, plane, out) in enumerate(faces()):
        for c in (.55, 1.5, 2.45):
            if i == 0 and abs(c - 1.5) < .1:
                continue
            h = .7 if k % 2 else .66
            box_on(g, axis, plane, out, c - .17, c + .17, SLAT[1] + .03, CORE + .02, .44, h, mats[k % len(mats)])
            box_on(g, axis, plane, out, c - .18, c + .18, SLAT[1] + .02, SLAT[1] + .035, .55, .58, IRON)
            k += 1


def straps(g):
    """Iron corner straps: the only parts on the cell faces."""
    for x, y in ((0, 0), (W, 0), (0, W), (W, W)):
        sx, sy = (1 if x == 0 else -1), (1 if y == 0 else -1)
        for z in (.2, .7):
            xa, xb = sorted((x, x + sx * .2))
            ya, yb = sorted((y, y + sy * POST_FACE))
            blk(g, xa, ya, z - .04, xb, yb, z + .04, IRON)
            xa, xb = sorted((x, x + sx * POST_FACE))
            ya, yb = sorted((y + sy * POST_FACE, y + sy * .2))
            blk(g, xa, ya, z - .04, xb, yb, z + .04, IRON)


def niche(g, parts):
    """Front middle bay: a pulley turning in the wall plane and a hook swaying
    on its rope, all behind the cell face."""
    x = 1.5
    blk(g, x - .03, .07, .7, x + .03, CORE + .01, .78, WOOD)          # pulley block on the core
    wheel = Geometry('WarehouseModule.Pulley', (x, .055, .64))
    wheel.cylinder((x, .055, .64), .075, .03, WOOD, 'Y', 12)
    wheel.cylinder((x, .055, .64), .025, .05, IRON, 'Y', 8)
    for k in range(3):
        a = k * math.pi / 3 + math.pi / 6
        wheel.box((x + math.cos(a) * .045, .055, .64 + math.sin(a) * .045), (.02, .036, .02), IRON)
    parts.append((wheel, 'SPIN_Y', 1))
    hx = x + .075
    hook = Geometry('WarehouseModule.Hook', (hx, .055, .64))
    hook.cylinder((hx, .055, .45), .009, .38, FOLK_WOOD, 'Z', 4)
    hook.box((hx, .055, .245), (.04, .02, .05), IRON)
    hook.box((hx - .015, .055, .21), (.03, .02, .02), IRON)
    parts.append((hook, 'SWAY_Y', .15))
    # A sack slumped at the foot of the niche.
    g.cylinder((x - .18, .1, .17), .07, .1, GREYWOOD, 'Y', 8)


def deck(g):
    deck_slab(g, 0.0, 0.0, W, W, 1.0, 'timber', thickness=.12, base=WOOD)


def build(g, parts):
    base(g)
    frame(g)
    slats(g)
    goods(g)
    straps(g)
    niche(g, parts)
    deck(g)
