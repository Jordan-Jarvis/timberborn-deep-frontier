"""DeepMine: late-game deep-ore shaft mine (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the east ore yard (track, ore tubs and stockpile) and the post lamps.

HERO: a monumental riveted steel headframe: a four-post tower over a concrete
shaft collar, raked backstays to the winding house, and twin 2.1-tile sheave
wheels turning in opposite directions under a maintenance gantry. Roofs: the
engine house has a monitor (clerestory) roof; teal plank gables on the bath
house and tipple head-house; a plank lean-to over the winding drum.

Parts: concrete shaft collar and dark shaft; timber skip guides; counterbalanced
skips; winding drum shed between the backstays; engine house with concrete lower
storey, timber-framed upper storey, clerestory and an outside flywheel; raised
timber ore bin with steel hopper, tipple deck and head-house, fed by a chute
from the headframe; mine track with ore tubs and a Deep Ore stockpile; pithead
bath-house with chimney and hot-water tank.

Animated (9): two sheave wheels, two skips, their two hoist ropes (stretch),
winding drum, engine flywheel, an ore tub on the track.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK
import lategame_mining_parts as P
from lategame_mining_parts import bx

IDENT = 'DeepMine'
# Footprint ends at the walls: the east ore yard (track, tubs, stockpile)
# was removed, so the footprint stops at the ore bin and engine house.
FOOTPRINT = (10, 11)
HEIGHT = 16
HERO = 'Monumental riveted steel headframe with raked backstays and twin counter-rotating sheave wheels'
FRAME_END = 121

SHAFT_Y = 3.45
LEGS_X = (3.0, 5.8)
LEGS_Y = (2.45, 4.45)
COLLAR = .6
DECK = 13
WHEEL_R = 1.05
WHEEL_Y = SHAFT_Y + WHEEL_R
WHEEL_Z = 14.2
SKIPS = (3.8, 5.0)
TRAVEL = 7.6
SKIP_LOW = .25
SKIP_H = 1.65                  # skip bottom to rope shackle
DRUM = (4.4, 7.7, 1.6)
LEVELS = [COLLAR + .05, 2.15, 3.7, 5.25, 6.8, 8.35, 9.9, 11.45, DECK - .08]


# ------------------------------------------------------------------ headframe

def collar(g):
    x0, x1, y0, y1 = 2.7, 6.1, 2.1, 4.8
    ox0, ox1, oy0, oy1 = 3.3, 5.5, 2.9, 4.0
    for e, z0, z1 in ((.06, 0, .22), (0, .22, COLLAR)):
        bx(g, x0 - e, x1 + e, y0 - e, oy0, z0, z1, CONCRETE)
        bx(g, x0 - e, x1 + e, oy1, y1 + e, z0, z1, CONCRETE)
        bx(g, x0 - e, ox0, oy0, oy1, z0, z1, CONCRETE)
        bx(g, ox1, x1 + e, oy0, oy1, z0, z1, CONCRETE)
    bx(g, ox0, ox1, oy0, oy1, 0, .05, IRON)


def headframe(g):
    zb = COLLAR
    for x in LEGS_X:
        for y in LEGS_Y:
            P.column(g, x, y, zb, DECK - .3, .28)
    # Girts: X-running at the level, Y-running 40 mm higher.
    for z in LEVELS[1:-1]:
        for y in LEGS_Y:
            bx(g, LEGS_X[0] + .14, LEGS_X[1] - .14, y - .07, y + .07, z - .07, z + .07, IRON)
        for x in LEGS_X:
            bx(g, x - .07, x + .07, LEGS_Y[0] + .14, LEGS_Y[1] - .14, z - .03, z + .11, IRON)
    # Zigzag bracing standing off the legs, alternating stand-off per bay.
    faces = (((LEGS_X[0], LEGS_Y[0]), (LEGS_X[1], LEGS_Y[0]), (0, -1)),
             ((LEGS_X[1], LEGS_Y[1]), (LEGS_X[0], LEGS_Y[1]), (0, 1)),
             ((LEGS_X[0], LEGS_Y[1]), (LEGS_X[0], LEGS_Y[0]), (-1, 0)),
             ((LEGS_X[1], LEGS_Y[0]), (LEGS_X[1], LEGS_Y[1]), (1, 0)))
    for fi, (pa, pb, n) in enumerate(faces):
        for k in range(len(LEVELS) - 1):
            za, zb2 = LEVELS[k] + .1, LEVELS[k + 1] - .08
            off = .17 if k % 2 == 0 else .19
            a, b = (pa, pb) if (k + fi) % 2 else (pb, pa)
            g.beam((a[0] + n[0] * off, a[1] + n[1] * off, za), (b[0] + n[0] * off, b[1] + n[1] * off, zb2),
                   .06, .1, IRON)
        # Bolted gusset plates at the girt joints, front and side faces only.
        if n[1] == -1 or n[0] == -1:
            for z in LEVELS[1:-1]:
                for p in (pa, pb):
                    if n[1]:
                        cy = p[1] - .14
                        bx(g, p[0] - .2, p[0] + .2, cy - .04, cy, z - .17, z + .17, FORGED)
                        for dx in (-.12, .12):
                            K.stud(g, (p[0] + dx, cy - .049, z), 'Y', .024)
                    else:
                        cx = p[0] - .14
                        bx(g, cx - .04, cx, p[1] - .2, p[1] + .2, z - .145, z + .195, FORGED)
                        for dy in (-.12, .12):
                            K.stud(g, (cx - .049, p[1] + dy, z + .025), 'X', .024)
    # Timber skip guides on steel buntons.
    for sx in SKIPS:
        for gx in (sx - .42, sx + .42):
            bx(g, gx - .04, gx + .04, SHAFT_Y - .05, SHAFT_Y + .05, .05, 10.4, WOOD)
            out = -1 if gx < sx else 1
            for z in LEVELS[1:7]:
                ba, bb = sorted((gx + out * .04, gx + out * .1))
                bx(g, ba, bb, LEGS_Y[0] + .07, LEGS_Y[1] - .07, z + .14, z + .24, IRON)
    # Deck girders, sheave deck, backstays.
    for x in LEGS_X:
        P.ibeam(g, 'Y', 2.2, 6.0, x, DECK - .3, DECK - .08, .32)
    for y in (2.3, 4.45, 5.9):
        P.ibeam(g, 'X', LEGS_X[0] + .16, LEGS_X[1] - .16, y, DECK - .3, DECK - .08, .24)
    P.deck(g, 2.8, 6.0, 2.2, 6.0, DECK)
    feet = ((2.7, 7.6), (6.1, 7.6))
    tops = ((LEGS_X[0], 5.9, DECK - .3), (LEGS_X[1], 5.9, DECK - .3))
    for (fx, fy), top in zip(feet, tops):
        P.pier(g, fx, fy, 0, .5, .62, cap=False)
        g.beam((fx, fy, .3), top, .3, .3, PAINTED)
    def stay(i, z):
        (fx, fy), (tx, ty, tz) = feet[i], tops[i]
        t = (z - .3) / (tz - .3)
        return (fx + (tx - fx) * t, fy + (ty - fy) * t, z)
    # Struts from the tower's back legs to the backstays; zigzag between stays.
    for z in (5.25, 9.9):
        for i, x in enumerate(LEGS_X):
            sx, sy, _ = stay(i, z)
            g.beam((x, LEGS_Y[1] + .14, z + .25), (sx, sy - .1, z + .25), .14, mat=IRON)
    zs = [1.2, 3.7, 6.8, 9.9, 12.2]
    for k in range(len(zs) - 1):
        a, b = stay(k % 2, zs[k]), stay((k + 1) % 2, zs[k + 1])
        off = .2 if k % 2 == 0 else .22
        g.beam((a[0], a[1] + off, a[2]), (b[0], b[1] + off, b[2]), .08, .1, IRON)
    for z in zs[1:-1]:
        a, b = stay(0, z), stay(1, z)
        g.beam((a[0] + .15, a[1], z), (b[0] - .15, b[1], z), .12, mat=IRON)
    # Sheave pedestals and bearing caps; maintenance gantry over the wheels.
    zd = DECK + .012
    for sx in SKIPS:
        for px in (sx - .38, sx + .38):
            bx(g, px - .07, px + .07, WHEEL_Y - .22, WHEEL_Y + .22, zd, WHEEL_Z + .1, PAINTED)
            bx(g, px - .09, px + .09, WHEEL_Y - .16, WHEEL_Y + .16, WHEEL_Z + .1, WHEEL_Z + .2, BRASS)
    for x in (2.95, 5.85):
        bx(g, x - .07, x + .07, WHEEL_Y - .07, WHEEL_Y + .07, zd, 15.55, IRON)
    P.ibeam(g, 'X', 2.82, 5.98, WHEEL_Y, 15.55, 15.75, .18)
    bx(g, 4.3, 4.5, WHEEL_Y - .08, WHEEL_Y + .08, 15.3, 15.55, PAINTED)
    # Lamps and a caged ladder up the front-left leg.
    K.ladder(g, LEGS_X[1] + .3, 2.85, 0, DECK, face='right', width=.34, cage=True)
    K.lamp(g, LEGS_X[0] - .07, 3.45, 6.7, face='left')
    K.lamp(g, LEGS_X[1] + .07, 3.75, 6.7, face='right')
    # Dump chute from the skip tipping point to the tipple head-house.
    P.slab_quad(g, [(5.45, 3.15, 9.55), (5.45, 3.75, 9.55), (6.85, 3.75, 8.35), (6.85, 3.15, 8.35)],
                (1.2, 0, 1.4), .06, FORGED)
    for y in (3.1, 3.8):
        P.slab_quad(g, [(5.45, y, 9.5), (6.85, y, 8.3), (6.85, y, 8.6), (5.45, y, 9.8)],
                    (0, -1 if y < 3.4 else 1, 0), .05, PAINTED)


def sheave(name, x, turns):
    w = P.spoked_wheel(name, (x, WHEEL_Y, WHEEL_Z), WHEEL_R, 'X', rim_t=.1, rim_w=.16, spokes=10,
                       hub_r=.15, double=True)
    w.cylinder((x, WHEEL_Y, WHEEL_Z), .07, .84, IRON, 'X', 12)
    return w, 'SPIN_X', turns


def skip(name, x, low):
    bottom = SKIP_LOW if low else SKIP_LOW + TRAVEL
    s = Geometry(name, (x, SHAFT_Y, bottom + .6))
    y = SHAFT_Y
    bx(s, x - .32, x + .32, y - .36, y + .36, bottom, bottom + 1.2, FORGED)
    for z in (bottom + .12, bottom + 1.08):
        bx(s, x - .345, x + .345, y - .385, y + .385, z - .05, z + .05, PAINTED)
    for xa, xb in ((x - .38, x - .32), (x + .32, x + .38)):
        for za, zb in ((.2, .45), (.8, .98)):
            bx(s, xa, xb, y - .05, y + .05, bottom + za, bottom + zb, IRON)
    for sx in (-1, 1):
        s.beam((x + sx * .28, y, bottom + 1.2), (x + sx * .06, y, bottom + SKIP_H - .08), .06, mat=IRON)
    bx(s, x - .1, x + .1, y - .06, y + .06, bottom + SKIP_H - .12, bottom + SKIP_H, PAINTED)
    for i in range(5):
        s.rock((x - .18 + i * .09, y + (-.1 if i % 2 else .12), bottom + 1.2 + .01 * i), (.16 + i * .01, .15, .12),
               IRON, 40 + i)
    return s


def rope(name, x, low):
    top = WHEEL_Z
    bottom = (SKIP_LOW if low else SKIP_LOW + TRAVEL) + SKIP_H
    r = Geometry(name, (x, SHAFT_Y, top))
    bx(r, x - .02, x + .02, SHAFT_Y - .02, SHAFT_Y + .02, bottom - .04, top, IRON)
    r.rope_length = top - bottom + .04
    return r


# ------------------------------------------------------------------ winding

def drum_shed(g, parts):
    cx, cy, cz = DRUM
    for x0 in (3.2, 5.4):
        bx(g, x0 - .05, x0 + .25, cy - .35, cy + .35, 0, .2, CONCRETE)
        bx(g, x0, x0 + .2, cy - .3, cy + .3, .2, 1.72, CONCRETE)
        bx(g, x0 - .02, x0 + .22, cy - .16, cy + .16, 1.72, 1.84, BRASS)
    d = Geometry('WindingDrum', DRUM)
    d.cylinder(DRUM, .8, 1.7, IRON, 'X', 16)
    for x in (3.55, 4.4, 5.25):
        d.cylinder((x, cy, cz), 1.0, .08, PAINTED, 'X', 16)
    for x in (3.8, 5.0):
        for k in range(3):
            d.ring((x - .2 + k * .2, cy, cz), .83, .04, .14, IRON, 'X', 16)
    d.cylinder(DRUM, .12, 2.3, IRON, 'X', 12)
    for x, s in ((3.51, -1), (5.29, 1)):
        P.bolt_ring(d, (x, cy, cz), .9, 10, 'X', s * .008, .025)
        for k in range(4):
            a = k * math.pi / 2
            d.beam((x + s * .012, cy + math.cos(a) * .2, cz + math.sin(a) * .2),
                   (x + s * .012, cy + math.cos(a) * .78, cz + math.sin(a) * .78), .03, .08, BRASS)
    parts.append((d, 'SPIN_X', -1))
    # Lean-to over the drum, posts at the front.
    for x in (3.3, 5.5):
        P.column(g, x, 7.92, 1.72, 3.95, .14, base=False)
    bx(g, 2.95, 5.85, 7.84, 8.0, 3.95, 4.07, WOOD)
    P.lean_to(g, 2.95, 5.85, 7.7, 8.4, 4.0, 4.35, low_side='front', seed=5)
    # Hoist ropes from the drum to the sheaves (A over the top, B from below).
    g.beam((3.8, cy, cz + .84), (3.8, WHEEL_Y + .98, WHEEL_Z + .27), .04, mat=IRON)
    g.beam((5.0, cy - .84, cz), (5.0, WHEEL_Y + .98, WHEEL_Z - .27), .04, mat=IRON)


def engine_house(g, parts):
    # Plinth course (core + .05) on tiles 0..8 x 9..11, clear of the drum.
    x0, x1, y0, y1 = .05, 7.95, 9.05, 10.95
    eave, zc = 4.4, 5.0
    ym0, ym1 = 9.5, 10.5
    pitch = (x1 - x0) / 7
    bays = [x0 + (k + .5) * pitch for k in range(7)]
    front = [(bays[0], 3.2), (bays[1], 3.2), (6.4, 3.2)]
    P.hall(g, x0, x1, y0, y1, eave, plinth=1.4, doors=[7.5], record_doors=False, pitch=pitch,
           rails=[2.4],
           windows={'front': front, 'back': [(u, 3.2) for u in bays],
                    'left': [(9.5, 3.2), (10.5, 3.2)], 'right': [(9.5, 3.2), (10.5, 3.2)]}, wscale=.72,
           lamps=[('front', 6.95, 1.75)])
    for x in (bays[0], bays[1], 6.4):
        P.window(g, x, y0 - .05, .75, 'front', .55, 'factory')
    for y in (9.5, 10.5):
        P.window(g, x1 + .05, y, .75, 'right', .55, 'factory')
        P.window(g, x0 - .05, y, .75, 'left', .55, 'factory')
    # Monitor roof: plaster end infill, lean-to slopes, riveted clerestory, gable cap.
    K.extrude_profile(g, [(y0, eave), (ym0, eave), (ym0, zc)], x0, x1, ORANGE, axis='X')
    K.extrude_profile(g, [(ym1, eave), (y1, eave), (ym1, zc)], x0, x1, ORANGE, axis='X')
    top = 6.2
    bx(g, x0, x1, ym0, ym1, eave, top, FORGED)
    for i in range(1, 7):
        x = x0 + (x1 - x0) * i / 7
        for y, s in ((ym0, -1), (ym1, 1)):
            P.face_member(g, 'front' if s < 0 else 'back', (x0, x1, ym0, ym1), x - .06, x + .06, -.01, .05,
                          zc + .12, top - .02, IRON)
        if i < 7:
            pass
    for k in range(7):
        x = x0 + (x1 - x0) * (k + .5) / 7
        P.window(g, x, ym0, 5.6, 'front', .6, 'factory')
        P.window(g, x, ym1, 5.6, 'back', .6, 'factory')
    P.lean_to(g, x0, x1, y0, ym0, eave, zc, low_side='front', seed=31)
    P.lean_to(g, x0, x1, ym1, y1, eave, zc, low_side='back', seed=37)
    P.plank_gable(g, x0, x1, ym0, ym1, top, top + .55, ridge_axis='X', seed=41, gable_mat=FORGED)
    # Boiler stack at the back-left.
    K.stack(g, 1.3, 10.55, 4.3, 5.2, emits='smoke', r=.24, bands=3)
    # Flywheel outside the right gable on concrete bearing blocks.
    fc = (8.55, 10.0, 1.45)
    for xa, xb in ((8.2, 8.35), (8.75, 8.9)):
        bx(g, xa - .04, xb + .04, 9.66, 10.34, 0, .16, CONCRETE)
        bx(g, xa, xb, 9.7, 10.3, .16, 1.55, CONCRETE)
        bx(g, xa - .01, xb + .01, 9.85, 10.15, 1.55, 1.65, BRASS)
    g.cylinder((8.08, 10.0, 1.45), .1, .26, IRON, 'X', 12)
    fly = P.spoked_wheel('Flywheel', fc, 1.25, 'X', rim_t=.2, rim_w=.28, spokes=6, groove=False,
                         hub_r=.2, mat=IRON, hub_mat=PAINTED)
    parts.append((fly, 'SPIN_X', 2))


# ------------------------------------------------------------------ tipple

def ore_bin(g, parts):
    cols = ((6.7, 1.9), (9.3, 1.9), (9.3, 4.7), (6.7, 4.7))
    for x, y in cols:
        P.pier(g, x, y, 0, .95, .42)
        P.column(g, x, y, 1.0, 6.92, .22)
    core = (6.85, 9.15, 2.05, 4.55)
    bx(g, core[0], core[1], core[2], core[3], 3.0, 6.92, PLANK)
    for face in ('front', 'back', 'left', 'right'):
        P.boards(g, face, core, 3.0, 6.92, width=.26, t=.06, mat=PLANK)
    for z in (3.35, 4.8, 6.25):
        bx(g, core[0] - .06, core[1] + .06, core[2] - .1, core[2] - .06, z - .07, z + .07, IRON)
        bx(g, core[0] - .06, core[1] + .06, core[3] + .06, core[3] + .1, z - .07, z + .07, IRON)
        bx(g, core[0] - .1, core[0] - .06, core[2] - .06, core[3] + .06, z - .05, z + .09, IRON)
        bx(g, core[1] + .06, core[1] + .1, core[2] - .06, core[3] + .06, z - .05, z + .09, IRON)
    P.frustum(g, core, 3.0, (7.75, 8.25, 3.05, 3.55), 2.2, FORGED)
    bx(g, 7.7, 8.3, 3.0, 3.6, 1.85, 2.2, PAINTED)
    g.beam((8.3, 3.3, 2.0), (8.75, 3.3, 2.5), .05, mat=IRON)
    bx(g, 8.72, 8.84, 3.24, 3.36, 2.45, 2.57, BRASS)
    # Bracing under the bin (one diagonal per face).
    for (ax, ay), (bxx, by) in (((6.7, 1.9), (9.3, 1.9)), ((9.3, 4.7), (6.7, 4.7))):
        s = -1 if ay < 3 else 1
        g.beam((ax, ay + s * .14, 1.15), (bxx, by + s * .14, 2.85), .06, .1, IRON)
    for (ax, ay), (bxx, by) in (((6.7, 4.7), (6.7, 1.9)), ((9.3, 1.9), (9.3, 4.7))):
        s = -1 if ax < 8 else 1
        g.beam((ax + s * .14, ay, 1.15), (bxx + s * .14, by, 2.85), .06, .1, IRON)
    # Tipple deck and head-house.
    P.deck(g, 6.5, 9.5, 1.7, 4.9, 7, gaps={'right': [(4.0, 4.6)]})
    P.hall(g, 6.8, 8.4, 2.4, 4.2, 9.0, z0=7.012, plinth=.2, doors=[7.5], record_doors=False, pitch=.8,
           post_skip={'left': [3.3]},
           windows={'right': [(3.3, 8.25, 'grand', .6)], 'back': [(7.6, 8.25, 'grand', .6)]})
    P.plank_gable(g, 6.8, 8.4, 2.4, 4.2, 9.0, 9.85, ridge_axis='X', seed=51)
    K.lamp(g, 8.05, 2.4, 8.4, face='front')
    K.ladder(g, 9.5, 4.3, 0, 7, face='right', width=.34, cage=True)


def bath_house(g):
    # Plinth course on the footprint's left edge and the y = 4 tile edge; its
    # right face stays clear of the shaft collar (x 2.64).
    side = [(.76, 2.0), (1.67, 2.0), (2.59, 2.0), (3.5, 2.0)]
    P.hall(g, .05, 2.5, .3, 3.95, 3.2, plinth=.5, doors=[1.5], pitch=1.0,
           windows={'left': side, 'right': side, 'back': [(.75, 2.0), (1.95, 2.0)]},
           lamps=[('front', .75, 1.35), ('front', 2.25, 1.35)])
    P.plank_gable(g, .05, 2.5, .3, 3.95, 3.2, 4.5, ridge_axis='Y', seed=61)
    K.stack(g, 1.4, 4.62, 0, 5.4, emits='smoke', r=.18, bands=3)
    # Hot-water tank on a steel stand.
    for x in (.75, 1.85):
        for y in (5.05, 6.15):
            P.column(g, x, y, 0, .92, .12, base=True)
    P.deck(g, .6, 2.0, 4.9, 6.3, 1, rails=(), bars=False)
    K.tank(g, 1.3, 5.6, 1.0, .48, 1.3, mat=PAINTED, bands=2, roof='cone')
    K.pipe_run(g, [(1.0, 5.4, 1.3), (1.0, 3.9, 1.3)], .06, flanges=False)
    P.gauge(g, 1.3, 5.12, 2.0, 'front', .08)


def build(g, parts):
    collar(g)
    headframe(g)
    parts.append(sheave('SheaveA', SKIPS[0], 2))
    parts.append(sheave('SheaveB', SKIPS[1], -2))
    parts.append((skip('SkipA', SKIPS[0], True), 'CUSTOM_SKIP', TRAVEL))
    parts.append((skip('SkipB', SKIPS[1], False), 'CUSTOM_SKIP', -TRAVEL))
    parts.append((rope('RopeA', SKIPS[0], True), 'CUSTOM_ROPE', TRAVEL))
    parts.append((rope('RopeB', SKIPS[1], False), 'CUSTOM_ROPE', -TRAVEL))
    drum_shed(g, parts)
    engine_house(g, parts)
    ore_bin(g, parts)
    bath_house(g)


KEYS = ((0.0, 0.0), (.42, 1.0), (.5, 1.0), (.92, 0.0), (1.0, 0.0))


def animate(obj, kind, value, frame_end):
    """Counterbalanced winding: skips and their ropes share one linear timeline."""
    span = frame_end - 1
    if kind == 'CUSTOM_SKIP':
        base = obj.location.z
        for f, t in KEYS:
            obj.location.z = base + value * t
            obj.keyframe_insert(data_path='location', index=2, frame=1 + span * f)
        obj.location.z = base
    elif kind == 'CUSTOM_ROPE':
        name = obj.name
        low = name.endswith('A')
        bottom = (SKIP_LOW if low else SKIP_LOW + TRAVEL) + SKIP_H
        length = WHEEL_Z - bottom + .04
        for f, t in KEYS:
            obj.scale = (1, 1, (length - value * t) / length)
            obj.keyframe_insert(data_path='scale', frame=1 + span * f)
    else:
        raise ValueError('Unknown custom animation ' + kind)
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
