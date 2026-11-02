"""ModularWarehouse: the hub of the modular warehouse (early game, unpowered).

Native contract (the parent's generator; not this module): a storage core
that haulers and builders enter; Warehouse Modules (lategame_WarehouseModule)
stack on its roof, on each other or stand beside it. Unlocks before bricks
and concrete exist, so it is timber throughout: dark Iron Teeth timber frame,
grey board infill, a plank roof deck, iron only as hardware (no brick,
concrete or plaster anywhere, including the door).

HERO: a two-storey timber storehouse with a rope-and-pulley hoist jutting
over its double plank door and a chalk ledger board beside it.
ROOF: flat plank deck exactly on layer 2, edge to edge, nothing on it: the
bed a Warehouse Module stacks on (and every cell a roof deck).

Stacking rule: everything stays inside the 3x3x2 box (posts and roof edge on
the cell faces, infill 70 mm behind them), so modules beside or on top of it
meet flat faces and never clip trim. Only the hoist and the lantern overhang
the door's own entrance path.

Animated: hoist pulley (SPIN_X), hoisted crate on its rope (PISTON_Z),
lantern beside the door (SWAY_Y, swinging along the wall).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON
import lategame_kit as K
from lategame_kit import GREYWOOD, GREYPLANK, FOLK_WOOD, GLOW
from lategame_civic_parts import blk
from lategame_roofdeck_parts import deck_slab
from native_window_atlas import atlas_window

IDENT = 'ModularWarehouse'
FOOTPRINT = (3, 3)
HEIGHT = 2
FRAME_END = 121
HERO = ('Two-storey timber storehouse with a rope-and-pulley hoist jutting over its double plank door and a chalk '
        'ledger board beside it.')

W = 3.0
INSET = .07           # plank infill plane behind the post faces
RAIL = .03            # rails 40 mm proud of the infill, 30 mm behind the post faces
CORNER, POST = .16, .1
SOLE_TOP = .12
FRAME_TOP = 1.88      # posts and rails stop under the roof slab
ROOF_TOP = 2.0
DOOR = (1.06, 1.94, .86)   # opening x0, x1, head


def sole(g):
    # Timber sole plate on the ground (no masonry footing: pre-concrete).
    blk(g, 0.0, 0.0, -.03, W, W, SOLE_TOP, WOOD)


def infill(g):
    """Dark plank backing 15 mm behind the skin and grey boards laid across
    every bay between the rails (each board its own texture island, so the
    planks read instead of one stretched sheet). The door opening is left to
    the door; everything else on the skin plane (INSET) sits on the boards."""
    b = INSET + .015
    blk(g, b, b, .1, W - b, W - b, 1.94, PLANK)
    bays = ((CORNER, 1 - POST / 2), (1 + POST / 2, 2 - POST / 2), (2 + POST / 2, W - CORNER))
    storeys = ((SOLE_TOP + .09, .95), (1.05, FRAME_TOP - .1))
    for face in ('front', 'back', 'left', 'right'):
        for u0, u1 in bays:
            for za, zb in storeys:
                if face == 'front' and (u0, u1) == bays[1] and za < DOOR[2]:
                    za = DOOR[2] + .09          # above the lintel only
                    if zb - za < .05:
                        continue
                n = max(1, round((zb - za) / .18))
                for k in range(n):
                    z0 = za + (zb - za) * k / n + (.004 if k else 0)
                    z1 = za + (zb - za) * (k + 1) / n - (.004 if k < n - 1 else 0)
                    _board(g, face, u0, u1, z0, z1)


def _board(g, face, u0, u1, z0, z1):
    d0, d1 = INSET, INSET + .02
    if face == 'front':
        blk(g, u0, d0, z0, u1, d1, z1, GREYPLANK)
    elif face == 'back':
        blk(g, u0, W - d1, z0, u1, W - d0, z1, GREYPLANK)
    elif face == 'left':
        blk(g, d0, u0, z0, d1, u1, z1, GREYPLANK)
    else:
        blk(g, W - d1, u0, z0, W - d0, u1, z1, GREYPLANK)


def frame(g):
    z0, z1 = SOLE_TOP, FRAME_TOP
    for x0, y0 in ((0, 0), (W - CORNER, 0), (0, W - CORNER), (W - CORNER, W - CORNER)):
        blk(g, x0, y0, z0, x0 + CORNER, y0 + CORNER, z1, WOOD)
    d = INSET + .025  # post and rail backs buried in the plank backing
    for u in (1.0, 2.0):
        blk(g, u - POST / 2, 0, z0, u + POST / 2, d, z1, WOOD)              # front
        blk(g, u - POST / 2, W - d, z0, u + POST / 2, W, z1, WOOD)          # back
        blk(g, 0, u - POST / 2, z0, d, u + POST / 2, z1, WOOD)              # left
        blk(g, W - d, u - POST / 2, z0, W, u + POST / 2, z1, WOOD)          # right
    # Rails between the posts: sill, floor band on layer 1, head under the roof.
    rails = ((SOLE_TOP, SOLE_TOP + .09), (.95, 1.05), (FRAME_TOP - .1, FRAME_TOP))
    spans = [(CORNER, 1 - POST / 2), (1 + POST / 2, 2 - POST / 2), (2 + POST / 2, W - CORNER)]
    for za, zb in rails:
        for a, b in spans:
            front_door = (a, b) == spans[1] and za < DOOR[2]
            if not front_door:
                blk(g, a, RAIL, za, b, d, zb, WOOD)
            blk(g, a, W - d, za, b, W - RAIL, zb, WOOD)
            blk(g, RAIL, a, za, d, b, zb, WOOD)
            blk(g, W - d, a, za, W - RAIL, b, zb, WOOD)


def door(g):
    """Double plank door (ledged and braced) in the front of tile 1, its face
    on the tile edge; recorded as the haulers' and builders' door."""
    x0, x1, head = DOOR
    blk(g, x0 - .01, RAIL, head, x1 + .01, INSET + .025, .95, WOOD)           # lintel
    blk(g, x0, RAIL + .005, SOLE_TOP, x1, INSET + .025, SOLE_TOP + .03, WOOD) # threshold
    mid = (x0 + x1) / 2
    for a, b in ((x0 + .01, mid - .006), (mid + .006, x1 - .01)):
        blk(g, a, .035, SOLE_TOP + .03, b, INSET + .025, head - .005, PLANK)   # leaf
        for z in (.3, .72):
            blk(g, a + .03, .02, z - .035, b - .03, .035, z + .035, WOOD)       # ledges
        g.beam(((a + b) / 2 - .13, .0315, .34), ((a + b) / 2 + .13, .0315, .68), .05, .007, WOOD)  # brace
        left = a < mid
        for z in (.3, .72):                                                    # strap hinges
            ha, hb = (a, a + .13) if left else (b - .13, b)
            blk(g, ha, .005, z - .02, hb, .02, z + .02, IRON)
    # Iron ring pulls on the meeting stiles.
    for x in (mid - .04, mid + .04):
        g.cylinder((x, .03, .5), .018, .02, IRON, 'Y', 4)
    g.doorways.append({'id': 'Door0', 'position': [1.5, 0.0, 0], 'outward': [0, -1]})


def windows(g):
    # Small cross windows on the upper storey's middle bays.
    atlas_window(g, INSET, 1.5, 1.45, .42, 'left', 'cross')
    atlas_window(g, W - INSET, 1.5, 1.45, .42, 'right', 'cross')
    for x in (.5, 2.5):
        atlas_window(g, x, W - INSET, 1.45, .42, 'back', 'cross')
    atlas_window(g, 2.5, INSET, 1.45, .42, 'front', 'cross')
    # Ground storey: one small grid window on each side.
    atlas_window(g, INSET, .5, .55, .3, 'left', 'grid9')
    atlas_window(g, W - INSET, 2.5, .55, .3, 'right', 'grid9')


def ledger(g):
    """Chalk ledger board on the front, left of the door: tally rows of what
    the store holds."""
    x0, x1, z0, z1 = .26, .9, 1.16, 1.72
    blk(g, x0, .045, z0, x1, INSET + .01, z1, FOLK_WOOD)     # painted board
    for za, zb in ((z0 - .03, z0), (z1, z1 + .03)):
        blk(g, x0 - .03, .035, za, x1 + .03, INSET + .01, zb, WOOD)
    for xa, xb in ((x0 - .03, x0), (x1, x1 + .03)):
        blk(g, xa, .035, z0, xb, INSET + .01, z1, WOOD)
    for i in range(4):
        z = z1 - .1 - i * .12
        blk(g, x0 + .05, .036, z - .012, x0 + .2, .045, z + .012, WOOD)        # good name
        for k in range(3 + i % 2):
            x = x0 + .3 + k * .06
            blk(g, x - .008, .036, z - .03, x + .008, .045, z + .03, WOOD)       # tally stroke


def hoist(g, parts):
    """Cantilevered hoist beam over the door with a turning pulley and a crate
    riding its rope."""
    x, y_end, z = 1.5, -.22, 1.68
    blk(g, x - .06, y_end, z - .06, x + .06, INSET + .03, z + .06, WOOD)
    g.beam((x, INSET, 1.32), (x, -.12, z - .06), .07, .07, WOOD)            # knee brace
    for dx in (-.045, .045):
        blk(g, x + dx - .008, -.2, z - .17, x + dx + .008, -.1, z - .06, IRON)    # pulley fork
    py, pz = -.15, z - .14
    wheel = Geometry('ModularWarehouse.Pulley', (x, py, pz))
    wheel.cylinder((x, py, pz), .07, .05, WOOD, 'X', 12)
    wheel.cylinder((x, py, pz), .025, .09, IRON, 'X', 8)
    for k in range(3):
        a = k * math.pi / 3
        wheel.box((x, py + math.cos(a) * .05, pz + math.sin(a) * .05), (.056, .022, .022), IRON)
    parts.append((wheel, 'SPIN_X', 1))
    ry = py - .07          # rope leaves the pulley on its outer side
    load = Geometry('ModularWarehouse.Load', (x, ry, 1.1))
    load.cylinder((x, ry, 1.35), .01, .38, FOLK_WOOD, 'Z', 4)               # rope
    load.box((x, ry, 1.15), (.03, .02, .05), IRON)                         # hook
    for dx in (-.07, .07):
        load.beam((x, ry, 1.16), (x + dx, ry, 1.08), .012, .012, FOLK_WOOD)   # sling
    load.box((x, ry, .98), (.2, .14, .18), PLANK)                          # crate
    load.box((x, ry, .98), (.212, .152, .03), IRON)                        # crate band
    parts.append((load, 'PISTON_Z', .07))


def lantern(g, parts):
    x, z = 2.5, .62
    blk(g, x - .02, -.12, z + .15, x + .02, INSET + .01, z + .19, WOOD)      # bracket arm
    blk(g, x - .03, INSET - .02, z + .05, x + .03, INSET + .01, z + .22, WOOD)   # wall plate
    lamp = Geometry('ModularWarehouse.Lantern', (x, -.1, z + .15))
    lamp.box((x, -.1, z + .12), (.012, .012, .06), IRON)
    lamp.cylinder((x, -.1, z + .01), .04, .1, GLOW, 'Z', 8)
    lamp.box((x, -.1, z + .075), (.1, .1, .02), IRON)
    lamp.box((x, -.1, z - .05), (.09, .09, .02), IRON)
    parts.append((lamp, 'SWAY_Y', .12))


def roof(g):
    # Plank deck on a timber slab, top exactly on layer 2, flush with the walls.
    deck_slab(g, 0.0, 0.0, W, W, ROOF_TOP, 'timber', thickness=.12, base=WOOD)


def build(g, parts):
    sole(g)
    infill(g)
    frame(g)
    door(g)
    windows(g)
    ledger(g)
    hoist(g, parts)
    lantern(g, parts)
    roof(g)
