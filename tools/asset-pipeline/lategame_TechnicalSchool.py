"""TechnicalSchool: grand academy for applied engineering (4 workers, 300 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the front garden with the armillary sphere, shrubs, dandelions and
post lamps; the engine yard sits behind the tower front.

HERO: a 14-layer clock tower on the entrance axis: concrete-quoined orange
shaft, four-faced clock stage with moving hands, lancet belfry and a teal
pyramid spire with a turning weathervane.
ROOF: flat parapet roof on the central block, hipped teal roofs on the two
lecture-hall wings, pyramid spire on the tower.

Parts: rusticated concrete ground storey; orange plaster upper storeys framed
by concrete pilasters with tall grand windows; two lecture-hall wings with
tall arched windows and roof ventilator cupolas; front-right demonstration
yard with a beam engine, flywheel, flyball governor and vertical boiler;
front-left garden with an armillary sphere on a pedestal.

Animated: six clock hands on three faces (SPIN_Y / SPIN_X), weathervane
(SPIN_Z), engine flywheel (SPIN_X), rocking beam (SWAY_X), governor (SPIN_Z),
armillary sphere (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N

IDENT = 'TechnicalSchool'
# Footprint ends at the walls (tower front y = 1): the front garden, its
# planting and post lamps were removed and the engine yard moved back behind
# the tower front. GRID_ORIGIN is the footprint's (0, 0) corner.
FOOTPRINT = (11, 5)
GRID_ORIGIN = (0, 1)
HEIGHT = 14
HERO = 'Fourteen-layer clock tower with a four-faced clock stage, lancet belfry and teal pyramid spire with a weathervane.'
FRAME_END = 121

TX, TY0, TY1 = 5.5, 1.0, 2.5           # tower axis x, front/back y
CB = (3.0, 2.0, 8.0, 6.0)               # central block on tiles 3..8 x 2..6 (tower podium 1..2)


def central(g):
    x0, y0, x1, y1 = CB
    P.podium(g, x0, y0, x1, y1, 1.5, skip=[(4.7, 6.3)])
    for x in (3.8, 7.2):
        P.native_window(g, x, y0, .78, .8, 'front', 'factory')
    for x in (3.9, 5.5, 7.1):
        P.native_window(g, x, y1, .78, .8, 'back', 'factory')
    fw = [(3.75, z, 1.1, 'grand') for z in (2.3, 3.75)] + [(7.25, z, 1.1, 'grand') for z in (2.3, 3.75)]
    bw = [(x, z, 1.1, 'grand') for x in (3.85, 4.95, 6.05, 7.15) for z in (2.3, 3.75)]
    P.framed_block(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, 1.5, 4.6, infill=ORANGE, frame=CONCRETE,
                   pitch=1.1, floors=(3.05,), corner=.22, post=.14, skip={'front': [(4.6, 6.4)]},
                   windows={'front': fw, 'back': bw,
                            'left': [(2.6, 3.75, 1.1, 'grand')],
                            'right': [(2.6, 3.75, 1.1, 'grand')]})
    K.flat_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, 4.6, overhang=.12)
    K.parapet(g, x0 - .07, y0 - .07, x1 + .07, y1 + .07, 4.76, .32, CONCRETE)
    # Roof chimneys and a skylight.
    for x in (3.8, 7.2):
        blk(g, x - .17, 4.6, 4.76, x + .17, 4.95, 5.7, CONCRETE)
        blk(g, x - .21, 4.56, 5.7, x + .21, 4.99, 5.8, IRON)
        K.emitter(g, 'steam', x, 4.775, 5.8, .17)   # steam: smoke-kind means smog
    blk(g, 4.4, 3.4, 4.76, 6.6, 4.4, 5.3, IRON)
    for x in (4.85, 5.5, 6.15):
        for y, f in ((3.4, 'front'), (4.4, 'back')):
            P.native_window(g, x, y, 5.03, .42, f, 'factory')
    K.gable_roof(g, 4.4, 3.4, 6.6, 4.4, 5.3, 5.7, ridge_axis='X', overhang=.08, gable_mat=FORGED)


def tower(g, parts):
    x0, x1 = TX - .75, TX + .75
    P.podium(g, x0, TY0, x1, CB[1], 1.55, skip=[(5.0, 6.0)], foot=False)
    P.door(g, 5.5, TY0, 0, 'Door0')
    K.lamp(g, 4.95, TY0, 1.0, face='front')
    K.lamp(g, 6.05, TY0, 1.0, face='front')
    P.framed_block(g, x0 + .05, TY0 + .05, x1 - .05, TY1 - .05, 1.55, 9.3, infill=ORANGE, frame=CONCRETE,
                   pitch=1.4, floors=(4.7, 7.0), corner=.24,
                   windows={'front': [(TX, 3.0, 1.15, 'grand'), (TX, 5.8, 1.0, 'grand'), (TX, 8.15, .8, 'lancet')],
                            'left': [(1.3, 5.8, .7, 'lancet'), (1.3, 8.15, .8, 'lancet')],
                            'right': [(1.3, 5.8, .7, 'lancet'), (1.3, 8.15, .8, 'lancet')],
                            'back': [(TX, 5.8, .9, 'lancet'), (TX, 8.15, .8, 'lancet')]})
    # Clock stage.
    blk(g, x0 - .1, TY0 - .1, 9.22, x1 + .1, TY1 + .1, 9.3, CONCRETE)
    sx0, sy0, sx1, sy1 = x0 - .05, TY0 - .05, x1 + .05, TY1 + .05
    P.framed_block(g, sx0, sy0, sx1, sy1, 9.3, 10.9, infill=CONCRETE, frame=WOOD, pitch=3.0, corner=.2)
    blk(g, sx0 - .08, sy0 - .08, 10.9, sx1 + .08, sy1 + .08, 10.98, CONCRETE)
    cz = 10.1
    faces = [('front', (TX, sy0, cz), 'Y', -1, 1), ('back', (TX, sy1, cz), 'Y', 1, None),
             ('left', (sx0, (TY0 + TY1) / 2, cz), 'X', -1, 1), ('right', (sx1, (TY0 + TY1) / 2, cz), 'X', 1, -1)]
    for name, c, axis, s, spin in faces:
        clock_face(g, parts, name, c, axis, s, spin)
    # Belfry with lancets and the pyramid spire.
    bx0, by0, bx1, by1 = x0 + .1, TY0 + .1, x1 - .1, TY1 - .1
    P.framed_block(g, bx0, by0, bx1, by1, 10.98, 11.98, infill=ORANGE, frame=WOOD, pitch=2.0, corner=.18,
                   windows={f: [((bx0 + bx1) / 2 if f in ('front', 'back') else (by0 + by1) / 2, 11.47, .78, 'lancet')]
                            for f in ('front', 'back', 'left', 'right')})
    P.pyramid_roof(g, TX, (TY0 + TY1) / 2, .65, 11.98, 1.55, overhang=.16)
    K.revolve(g, (TX, (TY0 + TY1) / 2, 13.5), [(.07, 0), (.07, .1), (.11, .15), (.11, .22), (0, .27), (.03, .28), (.03, .38)], BRASS, segments=8)
    cy = (TY0 + TY1) / 2
    vane = Geometry('Weathervane', (TX, cy, 13.9))
    vane.cylinder((TX, cy, 13.89), .04, .06, BRASS, 'Z', 8)
    vane.beam((TX - .3, cy, 13.9), (TX + .28, cy, 13.9), .03, mat=IRON)
    for order in ((0, 1, 2, 3), (3, 2, 1, 0)):
        vane.add([(TX - .3, cy, 13.86), (TX - .12, cy, 13.86), (TX - .12, cy, 13.99), (TX - .3, cy, 13.95)], [order], IRON)
    for order in ((0, 1, 2), (2, 1, 0)):
        vane.add([(TX + .28, cy - .05, 13.9), (TX + .38, cy, 13.9), (TX + .28, cy + .05, 13.9)], [order], BRASS)
    parts.append((vane, 'SPIN_Z', 1))


def clock_face(g, parts, name, c, axis, s, spin):
    """Plaster dial, steel bezel and hour marks; animated hands on the faces
    seen from the front views."""
    def at(off, u, v):
        # off along the outward normal, u horizontal, v vertical.
        if axis == 'Y':
            return (c[0] + u, c[1] + s * off, c[2] + v)
        return (c[0] + s * off, c[1] + u, c[2] + v)
    g.cylinder(at(.02, 0, 0), .5, .04, CONCRETE, axis, 24)
    g.ring(at(.03, 0, 0), .55, .07, .06, IRON, axis, 24)
    for k in range(12):
        a = k * math.pi / 6
        p = at(.0475, math.cos(a) * .41, math.sin(a) * .41)
        size = (.05, .015, .1) if axis == 'Y' else (.015, .05, .1)
        if k % 3:
            size = (size[0] * .6, size[1], size[2] * .6)
        g.box(p, size, IRON)
    if spin is None:
        g.box(at(.06, 0, .14), (.04, .01, .28) if axis == 'Y' else (.01, .04, .28), IRON)
        return
    for hand, length, width, off, turns in (('Hour', .26, .055, .062, spin / 12), ('Minute', .38, .035, .078, spin)):
        h = Geometry(f'Clock{hand}{name.title()}', at(0, 0, 0))
        h.box(at(off, 0, length / 2 - .05), (width, .012, length) if axis == 'Y' else (.012, width, length), IRON)
        h.cylinder(at(off + .006, 0, 0), .04, .012, BRASS, axis, 10)
        parts.append((h, 'SPIN_Y' if axis == 'Y' else 'SPIN_X', turns))


def wing(g, x0, x1, side):
    y0, y1 = 3.0, 6.0   # tiles x0..x1 x 3..6
    # The inner end stops .08 short of the central block so its coping
    # clears the central podium's joint strips.
    P.podium(g, x0 if side < 0 else x0 + .08, y0, x1 - .08 if side < 0 else x1, y1, 1.0, foot=False)
    xs = [x0 + .05 + (x1 - x0 - .1) * (i + .5) / 3 for i in range(3)]
    ys = [y0 + .05 + (y1 - y0 - .1) * (i + .5) / 3 for i in range(3)]
    outer = 'left' if side < 0 else 'right'
    for x in xs:
        P.native_window(g, x, y0, .55, .75, 'front', 'factory')
    P.framed_block(g, x0 + .05 if side < 0 else CB[2] - .12, y0 + .05, CB[0] + .12 if side < 0 else x1 - .05,
                   y1 - .05, 1.0, 3.4, infill=ORANGE, frame=WOOD, pitch=(x1 - x0 - .1) / 3,
                   faces=('front', 'back', outer),
                   windows={'front': [(x, 2.2, 1.3, 'grand') for x in xs],
                            'back': [(x, 2.2, 1.3, 'grand') for x in xs],
                            outer: [(y, 2.2, 1.3, 'grand') for y in ys]})
    P.hip_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, 3.4, 1.15)
    # Ventilator cupola on the hip ridge.
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    blk(g, cx - .22, cy - .22, 4.3, cx + .22, cy + .22, 4.85, WOOD)
    for k in range(4):
        z = 4.42 + k * .1
        blk(g, cx - .24, cy - .24, z, cx + .24, cy + .24, z + .03, IRON)
    P.pyramid_roof(g, cx, cy, .22, 4.85, .35, overhang=.08)


def engine_yard(g, parts):
    # Engine podium on tiles 8..11 x 1..3, level with the tower front; the
    # engine stands on it 0.55 tiles further back than first authored.
    P.podium(g, 8.0, 1.0, 11.0, 3.0, .2, joints=False, foot=False)
    with K.shifted(g, 0, .55):
        engine(g, parts)
    # Guard rail on the front edge of the engine podium.
    P.rail(g, (8.05, 1.08), (10.95, 1.08), .2, height=.5)


def engine(g, parts):
    # Engine bed split around the flywheel pit.
    blk(g, 8.25, .5, .15, 9.72, 2.2, .62, CONCRETE)
    blk(g, 10.1, .9, .15, 10.5, 1.7, .62, CONCRETE)
    fx, fy, fz, fr = 9.91, 1.3, 1.25, .78
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
    px, py, pz = 9.15, 1.3, 2.45
    for x in (px - .16, px + .16):
        blk(g, x - .05, py - .05, .62, x + .05, py + .05, pz - .06, PAINTED)
        g.beam((x, py - .45, .63), (x, py - .03, pz - .1), .05, mat=PAINTED)
        g.beam((x, py + .45, .63), (x, py + .03, pz - .1), .05, mat=PAINTED)
    blk(g, px - .22, py - .07, pz - .1, px + .22, py + .07, pz - .04, IRON)
    beam = Geometry('RockingBeam', (px, py, pz))
    beam.box((px, py, pz), (.08, 1.6, .14), IRON)
    beam.box((px, py, pz), (.12, .3, .24), PAINTED)
    beam.cylinder((px, py, pz), .05, .4, BRASS, 'X', 8)
    beam.box((px, py - .7, pz - .55), (.04, .04, 1.0), IRON)
    beam.box((px, py + .76, pz - .45), (.05, .05, .8), IRON)
    parts.append((beam, 'SWAY_X', .1))
    # Steam cylinder under the front end of the beam.
    g.cylinder((px, py - .7, .97), .2, .7, PAINTED, 'Z', 14)
    for z in (.68, 1.32):
        g.ring((px, py - .7, z), .23, .04, .05, BRASS, 'Z', 14)
    g.cylinder((px, py - .7, 1.38), .1, .05, IRON, 'Z', 10)
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
    K.tank(g, 10.35, 2.0, .2, .26, 1.1, bands=2, roof='dome')
    K.stack(g, 10.35, 2.0, 1.65, 1.1, emits='steam', r=.08, bands=1)
    P.flanged_pipe(g, [(10.1, 2.0, 1.1), (9.15, 2.0, 1.1), (9.15, .74, 1.1)], .045)
    P.gauge(g, 10.35, 1.72, 1.0, 'front')


def build(g, parts):
    central(g)
    tower(g, parts)
    wing(g, 0.0, CB[0], -1)
    wing(g, CB[2], 11.0, 1)
    engine_yard(g, parts)
