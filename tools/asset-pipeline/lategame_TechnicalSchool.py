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
the central block; timber-decked flat roof deck on layer 1 on the engine house; the
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

Animated (unchanged names and kinds): six clock hands on three faces
(SPIN_Y / SPIN_X), weathervane (SPIN_Z), engine flywheel (SPIN_X), rocking
beam (SWAY_X), governor (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N
from lategame_roofdeck_parts import deck_slab
from lategame_mining_parts import plank_gable

IDENT = 'TechnicalSchool'
FOOTPRINT = (8, 4)
HEIGHT = 7
HERO = ('Clock tower on the entrance axis with a four-faced clock stage, lancet belfry and teal pyramid spire '
        'with a weathervane.')
FRAME_END = 121

TX, TY0, TY1 = 5.5, 0.0, 1.5           # tower axis x, front/back y
CB = (3.0, 1.0, 8.0, 4.0)               # central block
HOUSE = (0.0, 2.0, 3.0, 4.0)            # engine house
SLAB = .16


def central(g):
    x0, y0, x1, y1 = CB
    # Brick ground storey (2026-10-30, bricks pass; was cast concrete with
    # pilaster joints), open around the windows and where the tower stands.
    P.podium(g, x0, y0, x1, y1, 1.0, joints=False)
    front = [3.5, 4.25, 6.75, 7.5]
    features = [((TX - .75, TY0, 0), (TX + .75, TY1, 1.0))]
    box = lambda fn: features.append(P.authored_box(g, fn))
    for x in front:
        box(lambda g, x=x: P.native_window(g, x, y0, .47, .52, 'front', 'factory'))
    for x in (3.5, 4.5, 5.5, 6.5, 7.5):
        box(lambda g, x=x: P.native_window(g, x, y1, .47, .52, 'back', 'factory'))
    for y in (2.0, 3.0):
        box(lambda g, y=y: P.native_window(g, x1, y, .47, .52, 'right', 'factory'))
    P.brick_skin(g, x0, y0, x1, y1, .14, .9, faces=('front', 'back', 'right'), features=features)
    u0, u1, v0, v1 = x0 + .05, y0 + .05, x1 - .05, y1 - .05
    P.framed_block(g, u0, u1, v0, v1, 1.0, 2.0, infill=ORANGE, frame=CONCRETE,
                   pitch=(v0 - u0) / 5, corner=.2, post=.12, skip={'front': [(4.6, 6.4)]},
                   faces=('front', 'back', 'right'),
                   windows={'front': [(x, 1.42, .5, 'grand') for x in front],
                            'back': [(x, 1.42, .5, 'grand') for x in (3.5, 4.5, 5.5, 6.5, 7.5)],
                            'right': [(y, 1.42, .5, 'grand') for y in (1.75, 3.25)]})
    plank_gable(g, u0, v0, u1, v1, 2.0, 3.05, ridge_axis='X', overhang=.15, gable_mat=PLANK, seed=3)


def tower(g, parts):
    x0, x1 = TX - .75, TX + .75
    # Brick tower base (2026-10-30, bricks pass), open around the door and
    # lamps; its back half stands inside the central block.
    P.podium(g, x0, TY0, x1, TY1, 1.0, skip=[(5.0, 6.0)], foot=False, joints=False)
    features = [(CB[:2] + (0,), CB[2:] + (1.0,))]
    box = lambda fn: features.append(P.authored_box(g, fn))
    box(lambda g: P.door(g, TX, TY0, 0, 'Door0'))
    box(lambda g: K.lamp(g, 4.97, TY0, .5, face='front'))
    box(lambda g: K.lamp(g, 6.03, TY0, .5, face='front'))
    P.brick_skin(g, x0, TY0, x1, TY1, .03, .9, faces=('front', 'left', 'right'), features=features)
    sx0, sy0, sx1, sy1 = x0 + .05, TY0 + .05, x1 - .05, TY1 - .05
    P.framed_block(g, sx0, sy0, sx1, sy1, 1.0, 3.0, infill=ORANGE, frame=CONCRETE, pitch=1.4, floors=(2.0,),
                   corner=.22,
                   windows={'front': [(TX, 1.45, .55, 'grand'), (TX, 2.5, .5, 'lancet')],
                            'left': [(.75, 2.5, .45, 'lancet')],
                            'right': [(.75, 2.5, .45, 'lancet')],
                            'back': [(TX, 2.5, .45, 'lancet')]})
    # Clock stage.
    blk(g, x0 - .08, TY0 - .08, 2.96, x1 + .08, TY1 + .08, 3.04, CONCRETE)
    cx0, cy0, cx1, cy1 = x0 - .04, TY0 - .04, x1 + .04, TY1 + .04
    P.framed_block(g, cx0, cy0, cx1, cy1, 3.04, 4.14, infill=CONCRETE, frame=WOOD, pitch=3.0, corner=.2)
    blk(g, cx0 - .07, cy0 - .07, 4.14, cx1 + .07, cy1 + .07, 4.22, CONCRETE)
    cz = 3.59
    faces = [('front', (TX, cy0, cz), 'Y', -1, 1), ('back', (TX, cy1, cz), 'Y', 1, None),
             ('left', (cx0, (TY0 + TY1) / 2, cz), 'X', -1, 1), ('right', (cx1, (TY0 + TY1) / 2, cz), 'X', 1, -1)]
    for name, c, axis, s, spin in faces:
        clock_face(g, parts, name, c, axis, s, spin, k=.84)
    # Belfry with lancets and the pyramid spire.
    bx0, by0, bx1, by1 = x0 + .1, TY0 + .1, x1 - .1, TY1 - .1
    P.framed_block(g, bx0, by0, bx1, by1, 4.22, 4.92, infill=ORANGE, frame=WOOD, pitch=2.0, corner=.18,
                   windows={f: [((bx0 + bx1) / 2 if f in ('front', 'back') else (by0 + by1) / 2, 4.57, .5, 'lancet')]
                            for f in ('front', 'back', 'left', 'right')})
    P.pyramid_roof(g, TX, (TY0 + TY1) / 2, .65, 4.92, 1.05, overhang=.14)
    top = 4.92 + 1.05
    cy = (TY0 + TY1) / 2
    K.revolve(g, (TX, cy, top - .03), [(.07, 0), (.07, .1), (.11, .15), (.11, .22), (0, .27), (.03, .28), (.03, .38)],
              BRASS, segments=8)
    vz = top + .37
    vane = Geometry('Weathervane', (TX, cy, vz))
    vane.cylinder((TX, cy, vz - .01), .04, .06, BRASS, 'Z', 8)
    vane.beam((TX - .3, cy, vz), (TX + .28, cy, vz), .03, mat=IRON)
    for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
        vane.add([(TX - .3, cy, vz - .04), (TX - .12, cy, vz - .04), (TX - .12, cy, vz + .09), (TX - .3, cy, vz + .05)],
                 [order], IRON)
    for order in ((0, 1, 2), (2, 1, 0)):
        vane.add([(TX + .28, cy - .05, vz), (TX + .38, cy, vz), (TX + .28, cy + .05, vz)], [order], BRASS)
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


def engine_house(g):
    x0, y0, x1, y1 = HOUSE
    # Plinth top 0.25: the wall core's 12 mm edge chamfer then sits between the
    # connection-face measuring rows, so the walls count as flat faces.
    P.podium(g, x0, y0, x1 - .08, y1, .25, joints=False, foot=False)   # coping clears the block's joint strips
    u0, v0, u1, v1 = x0 + .05, y0 + .05, x1 - .02, y1 - .05
    P.framed_block(g, u0, v0, u1, v1, .25, 1.0 - SLAB, infill=ORANGE, frame=WOOD, pitch=(u1 - u0) / 3,
                   faces=('front', 'back', 'left'), corner=.16,
                   windows={'front': [(x, .52, .42, 'factory') for x in (.55, 1.5, 2.45)],
                            'back': [(x, .52, .42, 'factory') for x in (.55, 1.5, 2.45)],
                            'left': [(y, .52, .42, 'factory') for y in (2.55, 3.45)]})
    # Roof slab (layer 1); it stops at the central block's coping (x 2.95).
    deck_slab(g, u0 - .05, v0 - .05, CB[0] - .05, v1 + .05, 1.0, 'timber', thickness=SLAB)
    # Parapet on the three open edges (the back of the central block closes the fourth).
    t, h = .14, .24
    blk(g, x0 - .03, y0 - .03, 1.0, x1 - .03, y0 - .03 + t, 1.0 + h, CONCRETE)
    blk(g, x0 - .03, y1 + .03 - t, 1.0, x1 - .03, y1 + .03, 1.0 + h, CONCRETE)
    blk(g, x0 - .03, y0 - .03 + t, 1.0, x0 - .03 + t, y1 + .03 - t, 1.0 + h, CONCRETE)
    blk(g, x0 - .06, y0 - .06, 1.0 + h, x1 - .03, y0 - .03 + t + .03, 1.0 + h + .05, IRON)
    blk(g, x0 - .06, y1 + .03 - t - .03, 1.0 + h, x1 - .03, y1 + .06, 1.0 + h + .05, IRON)
    blk(g, x0 - .06, y0 - .03 + t + .03, 1.0 + h, x0 - .03 + t + .03, y1 + .03 - t - .03, 1.0 + h + .05, IRON)


def engine_yard(g, parts):
    # Low concrete bed on tiles 0..3 x 0..2 beside the tower front; the
    # 2026-10-22 engine assembly moved over from the old right-hand yard.
    blk(g, 0.0, 0.0, 0.0, 2.95, 2.0, .15, CONCRETE)
    with K.shifted(g, -8.0, -.45):
        engine(g, parts)


def engine(g, parts):
    # Engine bed split around the flywheel pit (2026-10-22 coordinates).
    blk(g, 8.25, .5, .1, 9.72, 2.2, .62, CONCRETE)
    blk(g, 10.1, .9, .1, 10.5, 1.7, .62, CONCRETE)
    fx, fy, fz, fr = 9.91, 1.3, 1.25, .7
    for x in (9.74, 10.08):
        blk(g, x - .05, 1.18, .62, x + .05, 1.42, 1.15, PAINTED)
        g.cylinder((x, fy, 1.25), .08, .12, IRON, 'X', 10)
    wheel = Geometry('Flywheel', (fx, fy, fz))
    wheel.ring((fx, fy, fz), fr, .1, .14, IRON, 'X', 16)
    wheel.ring((fx, fy, fz), fr - .1, .03, .1, BRASS, 'X', 16)
    wheel.cylinder((fx, fy, fz), .12, .22, IRON, 'X', 12)
    wheel.cylinder((fx, fy, fz), .045, .5, IRON, 'X', 8)
    for i in range(6):
        a = i * math.pi / 3
        wheel.beam((fx, fy, fz), (fx, fy + math.cos(a) * (fr - .08), fz + math.sin(a) * (fr - .08)), .07, mat=IRON)
    parts.append((wheel, 'SPIN_X', 1))
    # Cast-iron columns and the rocking beam (in the flywheel plane).
    px, py, pz = 9.15, 1.3, 2.2
    for x in (px - .16, px + .16):
        blk(g, x - .05, py - .05, .62, x + .05, py + .05, pz - .06, PAINTED)
        g.beam((x, py - .45, .63), (x, py - .03, pz - .1), .05, mat=PAINTED)
        g.beam((x, py + .45, .63), (x, py + .03, pz - .1), .05, mat=PAINTED)
    blk(g, px - .22, py - .07, pz - .1, px + .22, py + .07, pz - .04, IRON)
    beam = Geometry('RockingBeam', (px, py, pz))
    beam.box((px, py, pz), (.08, 1.5, .14), IRON)
    beam.box((px, py, pz), (.12, .3, .24), PAINTED)
    beam.cylinder((px, py, pz), .05, .4, BRASS, 'X', 8)
    beam.box((px, py - .66, pz - .43), (.04, .04, .76), IRON)
    beam.box((px, py + .7, pz - .38), (.05, .05, .66), IRON)
    parts.append((beam, 'SWAY_X', .1))
    # Steam cylinder under the front end of the beam.
    g.cylinder((px, py - .66, .97), .2, .7, PAINTED, 'Z', 14)
    for z in (.68, 1.26):
        g.ring((px, py - .66, z), .23, .04, .05, BRASS, 'Z', 14)
    g.cylinder((px, py - .66, 1.345), .1, .05, IRON, 'Z', 10)
    # Crank arm linking the back end down toward the shaft.
    blk(g, px - .04, py + .7, .62, px + .04, py + .82, .7, IRON)
    # Flyball governor.
    blk(g, 8.47, .62, .62, 8.53, .68, 1.5, IRON)
    gov = Geometry('Governor', (8.5, .65, 1.5))
    gov.cylinder((8.5, .65, 1.52), .03, .16, BRASS, 'Z', 8)
    for a in (0, math.pi):
        b = (8.5 + math.cos(a) * .16, .65 + math.sin(a) * .16, 1.38)
        gov.beam((8.5, .65, 1.58), b, .015, mat=IRON)
        K.revolve(gov, (b[0], b[1], b[2] - .05), [(.001, 0), (.05, .02), (.05, .08), (.001, .1)], BRASS, segments=10)
    parts.append((gov, 'SPIN_Z', 3))
    # Vertical demonstration boiler and steam pipe.
    K.tank(g, 10.35, 2.0, .15, .26, 1.0, bands=2, roof='dome')
    # Vent stack without a plume: a steam emitter would bar the engine-house
    # roof cells beside it from the roof deck (BRIEF: no clutter on buildable space).
    K.stack(g, 10.35, 2.0, 1.5, .9, emits=None, r=.08, bands=1)
    P.flanged_pipe(g, [(10.1, 2.0, 1.0), (9.15, 2.0, 1.0), (9.15, .78, 1.0)], .045)
    P.gauge(g, 10.35, 1.72, .9, 'front')


def build(g, parts):
    central(g)
    tower(g, parts)
    engine_house(g)
    engine_yard(g, parts)
