"""TechnicalSchool: academy for applied engineering (4 workers, 300 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the front garden with the armillary sphere, shrubs, dandelions and
post lamps; the engine yard sits behind the tower front.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings"): 11x5x14 -> 8x4x7, inside the old
footprint with the same origin, door and native entrance. Storeys are one
layer each; the central block and the engine house have flat roof decks. The
right lecture-hall wing is gone, the left wing became the engine house behind
the demonstration yard, the hipped roofs, ventilator cupolas, skylight and
yard guard rail were removed, and the clock tower lost half its height.
Roof variety (user, 2026-10-30: "some buildings can have actual roofs"): the
central block has a teal gabled roof in the native roof planks instead of the
flat deck; the engine house keeps a flat roof deck, in timber decking.

HERO (kept as the silhouette): the clock tower on the entrance axis:
concrete-framed orange shaft, four-faced clock stage with moving hands,
lancet belfry and a teal pyramid spire with a turning weathervane.
ROOF: teal gabled roof of separate native roof planks (boarded gable ends) on
the central block; timber-decked flat roof deck on layer 1 on the engine house, open
edge to edge (no parapet: user 2026-10-31, "I want it to be like an actual
platform where roads can connect"); the
pyramid spire on the tower.

Plan (8 x 4 tiles; front y = 0; one layer per storey):
  - tower x 4.75..6.25, y 0..1.5, door centred on x = 5.5 with its face on the
    y = 0 tile edge; shaft to layer 3, clock stage, belfry, spire;
  - central block x 3..8, y 1..4: rusticated concrete ground storey, orange
    plaster upper storey with grand windows, gabled roof along x (no
    chimneys or roof vents);
  - demonstration yard x 0..3, y 0..2: beam engine, flywheel, flyball
    governor and vertical boiler on a low concrete bed;
  - engine house x 0..3, y 2..4: one storey, timber roof deck on layer 1.

Animated (unchanged names): six clock hands on three faces (SPIN_Y /
SPIN_X), weathervane (SPIN_Z), engine flywheel (SPIN_X), rocking beam
(SWAY_Y since 2026-11-01: it now rocks along the front row), governor (SPIN_Z).

Second shrink 2026-11-01 (user: "shrink the buildings down even more"):
8x4x7 -> 4x3x5, inside the old footprint with the same origin. The engine
house is gone; the central block is the whole back two rows (two one-layer
storeys of brick with stone dressings under the teal plank gable); the clock
tower is one tile wide on the front-right corner with the door, shorter
(clock stage from layer 2.6, spire top 4.55); the demonstration engine stands
on a bed along the rest of the front row, its flywheel, rocking beam and
governor scaled to one tile's depth. The door moves to x = 3.5 (Entrance
(3,-1,0), was (5,-1,0)).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, BRICK
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N
from lategame_roofdeck_parts import deck_slab
from lategame_mining_parts import plank_gable

IDENT = 'TechnicalSchool'
FOOTPRINT = (4, 3)
HEIGHT = 5
HERO = ('Clock tower on the entrance axis with a four-faced clock stage, lancet belfry and teal pyramid spire '
        'with a weathervane.')
FRAME_END = 121

TX, TY0, TY1 = 3.5, 0.0, 1.25          # tower axis x, front/back y
TW = .46                                # tower half width (was .75); clear of the block's right face
CB = (0.0, 1.0, 4.0, 3.0)               # central block
SLAB = .16


def central(g):
    x0, y0, x1, y1 = CB
    # Brick ground storey, open around the windows and where the tower stands.
    P.podium(g, x0, y0, x1, y1, 1.0, joints=False)
    front = [.5, 1.5, 2.5]
    features = [((TX - TW, TY0, 0), (TX + TW, TY1, 1.0))]
    box = lambda fn: features.append(P.authored_box(g, fn))
    for x in front:
        box(lambda g, x=x: P.native_window(g, x, y0, .47, .52, 'front', 'factory'))
    for x in (.5, 1.5, 2.5, 3.5):
        box(lambda g, x=x: P.native_window(g, x, y1, .47, .52, 'back', 'factory'))
    box(lambda g: P.native_window(g, x1, 2.0, .47, .52, 'right', 'factory'))
    box(lambda g: P.native_window(g, x0, 2.0, .47, .52, 'left', 'factory'))
    P.brick_skin(g, x0, y0, x1, y1, .14, .9, faces=('front', 'back', 'left', 'right'), features=features)
    u0, u1, v0, v1 = x0 + .05, y0 + .05, x1 - .05, y1 - .05
    P.framed_block(g, u0, u1, v0, v1, 1.0, 2.0, infill=BRICK, frame=CONCRETE,   # brick walls, stone dressings (2026-10-31)
                   pitch=(v0 - u0) / 4, corner=.2, post=.12, skip={'front': [(TX - TW - .1, TX + TW + .1)]},
                   windows={'front': [(x, 1.42, .5, 'grand') for x in front],
                            'back': [(x, 1.42, .5, 'grand') for x in (.5, 1.5, 2.5, 3.5)],
                            'left': [(2.0, 1.42, .5, 'grand')],
                            'right': [(2.0, 1.42, .5, 'grand')]})
    plank_gable(g, u0, v0, u1, v1, 2.0, 2.7, ridge_axis='X', overhang=.15, gable_mat=PLANK, seed=3)


def tower(g, parts):
    x0, x1 = TX - TW, TX + TW
    # Brick tower base, open around the door and lamp; its back stands inside
    # the central block.
    P.podium(g, x0, TY0, x1, TY1, 1.0, skip=[(3.0, 4.0)], foot=False, joints=False)
    features = [(CB[:2] + (0,), CB[2:] + (1.0,))]
    box = lambda fn: features.append(P.authored_box(g, fn))
    box(lambda g: P.door(g, TX, TY0, 0, 'Door0'))
    box(lambda g: K.lamp(g, 2.92, TY0, .5, face='front'))
    P.brick_skin(g, x0, TY0, x1, TY1, .03, .9, faces=('front', 'left', 'right'), features=features)
    sx0, sy0, sx1, sy1 = x0 + .05, TY0 + .05, x1 - .05, TY1 - .05
    P.framed_block(g, sx0, sy0, sx1, sy1, 1.0, 2.6, infill=BRICK, frame=CONCRETE, pitch=1.4, floors=(2.0,),
                   corner=.2,
                   windows={'front': [(TX, 1.45, .45, 'grand'), (TX, 2.3, .4, 'lancet')],
                            'left': [(.6, 2.3, .38, 'lancet')],
                            'right': [(.6, 2.3, .38, 'lancet')]})
    # Clock stage.
    blk(g, x0 - .07, TY0 - .07, 2.56, x1 + .07, TY1 + .07, 2.64, CONCRETE)
    cx0, cy0, cx1, cy1 = x0 - .03, TY0 - .03, x1 + .03, TY1 + .03
    P.framed_block(g, cx0, cy0, cx1, cy1, 2.64, 3.44, infill=CONCRETE, frame=WOOD, pitch=3.0, corner=.18,
                   top_rail=False)   # the dial bezels reach the head
    blk(g, cx0 - .06, cy0 - .06, 3.44, cx1 + .06, cy1 + .06, 3.51, CONCRETE)
    cz = 3.08
    faces = [('front', (TX, cy0, cz), 'Y', -1, 1), ('back', (TX, cy1, cz), 'Y', 1, None),
             ('left', (cx0, (TY0 + TY1) / 2, cz), 'X', -1, 1), ('right', (cx1, (TY0 + TY1) / 2, cz), 'X', 1, -1)]
    for name, c, axis, s, spin in faces:
        clock_face(g, parts, name, c, axis, s, spin, k=.58)
    # Belfry with lancets and the pyramid spire.
    bx0, by0, bx1, by1 = x0 + .08, TY0 + .08, x1 - .08, TY1 - .08
    P.framed_block(g, bx0, by0, bx1, by1, 3.51, 3.95, infill=BRICK, frame=WOOD, pitch=2.0, corner=.16,
                   windows={f: [((bx0 + bx1) / 2 if f in ('front', 'back') else (by0 + by1) / 2, 3.73, .36, 'lancet')]
                            for f in ('front', 'back', 'left', 'right')})
    P.pyramid_roof(g, TX, (TY0 + TY1) / 2, .55, 3.95, .6, overhang=.12)
    top = 3.95 + .6
    cy = (TY0 + TY1) / 2
    K.revolve(g, (TX, cy, top - .03), [(.06, 0), (.06, .08), (.09, .12), (.09, .18), (0, .22), (.025, .23), (.025, .31)],
              BRASS, segments=8)
    vz = top + .31
    vane = Geometry('Weathervane', (TX, cy, vz))
    vane.cylinder((TX, cy, vz - .01), .035, .05, BRASS, 'Z', 8)
    vane.beam((TX - .26, cy, vz), (TX + .24, cy, vz), .025, mat=IRON)
    for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
        vane.add([(TX - .26, cy, vz - .035), (TX - .1, cy, vz - .035), (TX - .1, cy, vz + .08), (TX - .26, cy, vz + .045)],
                 [order], IRON)
    for order in ((0, 1, 2), (2, 1, 0)):
        vane.add([(TX + .24, cy - .045, vz), (TX + .33, cy, vz), (TX + .24, cy + .045, vz)], [order], BRASS)
    parts.append((vane, 'SPIN_Z', 1))


def clock_face(g, parts, name, c, axis, s, spin, k=1.0):
    """Plaster dial, steel bezel and hour marks (scaled by k); animated hands
    on the faces seen from the front views."""
    def at(off, u, v):
        # off along the outward normal, u horizontal, v vertical.
        if axis == 'Y':
            return (c[0] + u, c[1] + s * off, c[2] + v)
        return (c[0] + s * off, c[1] + u, c[2] + v)
    g.cylinder(at(.02, 0, 0), .5 * k, .04, CONCRETE, axis, 24)
    g.ring(at(.03, 0, 0), .55 * k, .07 * k, .06, IRON, axis, 24)
    for i in range(12):
        a = i * math.pi / 6
        p = at(.0475, math.cos(a) * .41 * k, math.sin(a) * .41 * k)
        size = (.05 * k, .015, .1 * k) if axis == 'Y' else (.015, .05 * k, .1 * k)
        if i % 3:
            size = (size[0] * .6, size[1], size[2] * .6) if axis == 'Y' else (size[0], size[1] * .6, size[2] * .6)
        g.box(p, size, IRON)
    if spin is None:
        g.box(at(.06, 0, .14 * k), (.04, .01, .28 * k) if axis == 'Y' else (.01, .04, .28 * k), IRON)
        return
    for hand, length, width, off, turns in (('Hour', .26, .055, .062, spin / 12), ('Minute', .38, .035, .078, spin)):
        length, width = length * k, width * k
        h = Geometry(f'Clock{hand}{name.title()}', at(0, 0, 0))
        h.box(at(off, 0, length / 2 - .05 * k), (width, .012, length) if axis == 'Y' else (.012, width, length), IRON)
        h.cylinder(at(off + .006, 0, 0), .04 * k, .012, BRASS, axis, 10)
        parts.append((h, 'SPIN_Y' if axis == 'Y' else 'SPIN_X', turns))


def engine_yard(g, parts):
    """The demonstration beam engine on a low concrete bed along the front row
    (x 0..2.95, y 0..1, beside the tower): rocking beam, flywheel and flyball
    governor in one tile's depth (2026-11-01; the engine house is gone)."""
    blk(g, 0.0, 0.02, 0.0, TX - TW - .05, .98, .15, CONCRETE)
    blk(g, .15, .15, .1, 1.95, .85, .45, CONCRETE)              # engine bed
    # Flywheel in the y-z plane on the bed's right end.
    fx, fy, fz, fr = 2.45, .5, .62, .42
    for x in (2.3, 2.6):
        blk(g, x - .04, .42, .15, x + .04, .58, .58, PAINTED)
        g.cylinder((x, fy, fz), .06, .09, IRON, 'X', 10)
    wheel = Geometry('Flywheel', (fx, fy, fz))
    wheel.ring((fx, fy, fz), fr, .07, .1, IRON, 'X', 16)
    wheel.ring((fx, fy, fz), fr - .07, .025, .07, BRASS, 'X', 16)
    wheel.cylinder((fx, fy, fz), .09, .16, IRON, 'X', 12)
    wheel.cylinder((fx, fy, fz), .035, .36, IRON, 'X', 8)
    for i in range(6):
        a = i * math.pi / 3
        wheel.beam((fx, fy, fz), (fx, fy + math.cos(a) * (fr - .06), fz + math.sin(a) * (fr - .06)), .05, mat=IRON)
    parts.append((wheel, 'SPIN_X', 1))
    # Cast-iron columns and the rocking beam (along x, rocking in the x-z plane).
    px, py, pz = 1.05, .5, 1.45
    for y in (py - .12, py + .12):
        blk(g, px - .04, y - .04, .45, px + .04, y + .04, pz - .05, PAINTED)
        g.beam((px - .32, y, .46), (px - .03, y, pz - .08), .04, mat=PAINTED)
        g.beam((px + .32, y, .46), (px + .03, y, pz - .08), .04, mat=PAINTED)
    blk(g, px - .06, py - .17, pz - .08, px + .06, py + .17, pz - .03, IRON)
    beam = Geometry('RockingBeam', (px, py, pz))
    beam.box((px, py, pz), (1.1, .06, .11), IRON)
    beam.box((px, py, pz), (.22, .09, .18), PAINTED)
    beam.cylinder((px, py, pz), .04, .3, BRASS, 'Y', 8)
    beam.box((px - .48, py, pz - .3), (.03, .03, .52), IRON)
    beam.box((px + .5, py, pz - .27), (.04, .04, .46), IRON)
    parts.append((beam, 'SWAY_Y', .1))
    # Steam cylinder under the left end of the beam.
    g.cylinder((px - .48, py, .7), .15, .5, PAINTED, 'Z', 14)
    for z in (.48, .92):
        g.ring((px - .48, py, z), .17, .03, .04, BRASS, 'Z', 14)
    g.cylinder((px - .48, py, .975), .08, .04, IRON, 'Z', 10)
    # Flyball governor beside the flywheel.
    blk(g, 1.93, .27, .45, 1.97, .31, 1.1, IRON)
    gov = Geometry('Governor', (1.95, .29, 1.1))
    gov.cylinder((1.95, .29, 1.12), .025, .12, BRASS, 'Z', 8)
    for a in (0, math.pi):
        b = (1.95 + math.cos(a) * .12, .29 + math.sin(a) * .12, 1.0)
        gov.beam((1.95, .29, 1.16), b, .012, mat=IRON)
        K.revolve(gov, (b[0], b[1], b[2] - .04), [(.001, 0), (.04, .015), (.04, .06), (.001, .075)], BRASS, segments=10)
    parts.append((gov, 'SPIN_Z', 3))
    P.gauge(g, .35, .15, .7, 'front')


def build(g, parts):
    central(g)
    tower(g, parts)
    engine_yard(g, parts)
