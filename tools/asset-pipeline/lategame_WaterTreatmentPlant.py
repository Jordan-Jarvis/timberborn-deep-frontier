"""WaterTreatmentPlant: badwater treatment (4 workers, 500 hp).

HERO: an elevated riveted water tower on a braced steel trestle, with a
      railed balcony and a lapped teal cone roof, rising over two round
      clarifiers whose scraper bridges sweep slowly round the water.
ROOF: a teal barrel vault on the filter house, a small gable on the open
      pump shed, a cone on the water tower.

Plan (12 x 11 tiles): two round clarifier basins with native water on the
left; a stepped aeration cascade between them and the filter house; the
filter house with the door at the centre-right; the open pump shed with two
flywheel pumps at the front; the chlorine contact tower beside it; the water
tower front-right; a sludge digester at the back.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, CYAN, GLOW, LAYER_GAP
import lategame_industry_parts as P
from industrial_facades import building_portal
from architectural_windows import window

IDENT = 'WaterTreatmentPlant'
FOOTPRINT = (12, 11)
HEIGHT = 13
FRAME_END = 121
HERO = ('An elevated riveted water tower on a braced steel trestle with a railed balcony and a teal cone roof, '
        'over two round clarifiers whose scraper bridges sweep round the water.')

CLARIFIERS = ((2.5, 2.5), (2.5, 8.5))   # rims tangent to tiles 0..5 x 0..5 and 0..5 x 6..11
RIM_OUT, RIM_IN, RIM_TOP = 2.5, 1.6, 1.0
FILTER = (7.1, 4.3, 11.9, 8.9)          # plinth (walls + .1) on tiles 7..12 x 4..9; door face .2
DOOR_X = 8.5
TOWER = (10.35, 1.75)


def frame(g, axis, plane, start, end, bottom, top, out, **kw):
    K.frame_wall(g, axis, plane, start, end, bottom, top, outward=out, **kw)


# ---------------------------------------------------------------- clarifiers

def clarifier(g, parts, idx, cx, cy):
    # Concrete basin: broad walkway rim (hides the square water's corners).
    K.hollow_revolve(g, (cx, cy, 0), [(RIM_OUT, 0), (RIM_OUT, RIM_TOP)], RIM_OUT - RIM_IN, CONCRETE, segments=20)
    P.hoop(g, (cx, cy, RIM_TOP - .1), RIM_OUT + .03, .06, .12, CONCRETE, segments=20)
    K.revolve(g, (cx, cy, 0), [(RIM_IN - .02, 0), (RIM_IN - .02, .2)], CONCRETE, segments=20)
    # Effluent launder round the inside of the wall, feed well and centre pier.
    K.hollow_revolve(g, (cx, cy, 0), [(RIM_IN, .72), (RIM_IN, .93)], .16, CONCRETE, segments=20)
    K.hollow_revolve(g, (cx, cy, 0), [(.72, .55), (.72, 1.08)], .05, IRON, segments=12)
    K.revolve(g, (cx, cy, .2), [(.3, 0), (.3, .9), (.36, .96), (.36, 1.08)], CONCRETE, segments=16)
    K.revolve(g, (cx, cy, 1.28), [(.26, 0), (.26, .26), (.12, .34)], PAINTED, segments=16)
    g.liquid_surfaces.append(dict(name=f'Clarifier{idx}', shape='Rectangle', center=[cx, cy], bottom=.2, top=.84,
                                  scale=[2 * RIM_IN, 2 * RIM_IN], flowOnly=False))
    # Walkway handrail on the outer rim, open where the access path meets it.
    P.ring_rail(g, (cx, cy), RIM_OUT - .1, RIM_TOP, height=.6, posts=20)
    # Rotating full-diameter scraper bridge on the centre turntable.
    z = 1.72
    b = Geometry(f'WaterTreatmentPlant.ScraperBridge{idx}', (cx, cy, z))
    r1 = RIM_OUT - .28
    for dy in (-.2, .2):
        b.box((cx, cy + dy, z), (2 * r1, .08, .16), IRON)
    for k in range(9):
        x = cx - r1 + .15 + k * (2 * r1 - .3) / 8
        b.box((x, cy, z - .05), (.06, .36, .06), IRON)
    b.box((cx, cy, z + .1), (2 * r1 - .04, .32, .04), FORGED)
    for dy in (-.2, .2):
        P.rail(b, [(cx - r1 + .05, cy + dy), (cx + r1 - .05, cy + dy)], z + .12, height=.5, pitch=.5)
    P.lathe(b, (cx, cy, 0), [(.3, 1.63), (.3, 1.69), (.2, 1.71)], PAINTED, segments=16)
    for side in (-1, 1):
        ex = cx + side * (RIM_OUT - .38)
        # End carriage: legs down to a wheel on the rim, drive motor.
        b.box((ex, cy, z - .14), (.3, .5, .12), PAINTED)
        for dy in (-.17, .17):
            b.box((ex, cy + dy, (RIM_TOP + .14 + z - .2) / 2), (.08, .08, z - .2 - RIM_TOP - .14), IRON)
        b.box((ex, cy, RIM_TOP + .12), (.22, .44, .06), IRON)   # faces clear of the leg faces
        b.cylinder((ex, cy, RIM_TOP + .075), .075, .08, IRON, 'Y', 12)
        b.box((ex - side * .02, cy + .32, z - .1), (.22, .14, .18), IRON)
        # Scraper arm and blade sweeping the basin floor.
        b.beam((cx + side * .85, cy, z - .08), (cx + side * 1.2, cy, .42), .06, mat=IRON)
        b.beam((cx + side * 1.5, cy, z - .08), (cx + side * 1.2, cy, .42), .06, mat=IRON)
        b.box((cx + side * 1.0, cy + side * .03, .36), (1.0, .05, .12), PAINTED)
    parts.append((b, 'SPIN_Z', 1 if idx == 1 else -1))


# ---------------------------------------------------------------- aeration cascade

def cascade(g):
    x0, x1 = 5.0, 6.0   # one tile wide, y 5..10
    steps = [(9.86, 8.645, 2.0), (8.645, 7.43, 1.55), (7.43, 6.215, 1.1), (6.215, 5.0, .65)]
    for k, (yb, ya, floor) in enumerate(steps):
        # Solid stepped body, its side walls, and the weir lip at the low end.
        g.box(((x0 + x1) / 2, (ya + yb) / 2, floor / 2), (x1 - x0 - .3, yb - ya, floor), CONCRETE)
        for x in (x0 + .075, x1 - .075):
            g.box((x, (ya + yb) / 2, (floor + .45) / 2 + .0 + k * .0), (.15, yb - ya, floor + .45), CONCRETE)
        g.box(((x0 + x1) / 2, ya + .06, floor + .15), (x1 - x0 - .3, .12, .3), CONCRETE)
        g.box(((x0 + x1) / 2, ya + .06, floor + .31), (x1 - x0 - .3 - .02, .14, .02), BRASS)
        g.liquid_surfaces.append(dict(name=f'Cascade{k + 1}', shape='Rectangle',
                                      center=[(x0 + x1) / 2, (ya + .12 + yb) / 2], bottom=floor,
                                      top=floor + .24, scale=[x1 - x0 - .3, yb - ya - .12], flowOnly=False))
    # Back head wall.
    g.box(((x0 + x1) / 2, steps[0][0] + .07, (2.45 + 0) / 2), (x1 - x0, .14, 2.45), CONCRETE)
    # Feed pipe from clarifier B over the head wall.
    P.pipe(g, [(CLARIFIERS[1][0] + RIM_OUT - .2, 9.6, RIM_TOP + .25), (x0 + .4, 9.6, RIM_TOP + .25),
               (x0 + .4, 9.6, 2.35)], .08)
    # Aerator paddle wheel on the top step is animated in build().


def aerator(parts):
    x0, x1 = 5.0, 6.0
    cy, cz = 9.2, 2.0 + .26
    a = Geometry('WaterTreatmentPlant.AeratorRotor', ((x0 + x1) / 2, cy, cz))
    P.tube(a, (x0 + .18, cy, cz), (x1 - .18, cy, cz), .045, IRON, segments=10)
    for k in range(6):
        ang = k * math.pi / 3
        for x in (x0 + .3, x1 - .3):   # two paddles across the one-tile channel
            a.box((x, cy + math.cos(ang) * .2, cz + math.sin(ang) * .2),
                  (.22, .03 + .19 * abs(math.sin(ang)), .03 + .19 * abs(math.cos(ang))), PAINTED)   # neighbours clear
    parts.append((a, 'SPIN_X', 3))


# ---------------------------------------------------------------- filter house

def filter_house(g):
    x0, y0, x1, y1 = FILTER
    top = P.plinth(g, x0 - .1, y0 - .1, x1 + .1, y1 + .1, 1.2, door=(DOOR_X, 1.0, 1.0))
    building_portal(g, DOOR_X, y0 - .1 - .12, 0)
    g.doorways.append({'id': 'Entrance', 'position': [DOOR_X, y0 - .1, 0], 'outward': [0, -1]})
    for dx in (-.62, .62):
        K.lamp(g, DOOR_X + dx, y0 - .14, 1.05, face='front')
    spring = 4.5
    fw = dict(infill=ORANGE, post=WOOD, post_w=.16, window_style='grand', window_scale=.95)
    bays = [x0 - .05 + (k + .5) * (x1 - x0 + .1) / 5 for k in range(5)]
    frame(g, 'X', y0, x0 - .05, x1 + .05, top, spring + .03, -1, bays=5,
          windows=[(u, 2.9) for u in bays], **fw)
    frame(g, 'X', y1, x0 - .05, x1 + .05, top, spring + .03, 1, bays=5,
          windows=[(u, 2.9) for u in bays], **fw)
    frame(g, 'Y', x0, y0 + .05, y1 - .05, top, spring + .03, -1, bays=4,
          windows=[(5.0, 2.9), (7.95, 2.9)], **fw)
    frame(g, 'Y', x1, y0 + .05, y1 - .05, top, spring + .03, 1, bays=4,
          windows=[(5.0, 2.9), (6.1, 2.9), (7.0, 2.9), (7.95, 2.9)], **fw)
    # Barrel vault along X with steel ribs; arched plaster end walls.
    half = (y1 - y0) / 2
    rise = 1.45
    P.plank_vault(g, x0, y0, x1, y1, spring + .02, rise, overhang=.16, plank=.34, segments=14, ribs=5)
    pts = [(y0 + half + math.cos(math.pi * k / 14) * (half + .04), spring + .02 + math.sin(math.pi * k / 14) * (rise - .1))
           for k in range(15)]
    prof = [(y0 - .04, spring - .01), (y1 + .04, spring - .01)] + pts[1:-1]
    for plane, out in ((x0, -1), (x1, 1)):
        P.end_prism(g, 'X', plane, out, prof, ORANGE)
        window(g, plane + out * .025, (y0 + y1) / 2, spring + .62, .7, 'left' if out < 0 else 'right', 'diamond')
    # Roof ventilator lantern on the crown.
    crown = spring + .02 + rise + .08
    for x in (8.0, 10.3):
        g.box((x, (y0 + y1) / 2, crown + .1), (.5, .5, .32), FORGED)
        g.box((x, (y0 + y1) / 2, crown + .3), (.62, .62, .08), IRON)
    # Pipe gallery: cascade outfall into the left end wall.
    P.pipe(g, [(5.9, 5.3, .9), (x0 - .2, 5.3, .9), (x0 - .2, 5.3, 1.6), (x0 - .06, 5.3, 1.6)], .1)
    P.gauge(g, x0 - .16, 6.4, 1.8, 'left', .09)
    P.valve(g, (x0 - .2, 5.3, 1.25), 'left', .13)


# ---------------------------------------------------------------- pump shed

def pump_shed(g, parts):
    x0, y0, x1, y1 = 5.1, .1, 7.9, 2.9   # plinth (walls + .1) on tiles 5..8 x 0..3
    top = P.plinth(g, x0 - .1, y0 - .1, x1 + .1, y1 + .1, .4, pilasters=False)
    eave = 3.0
    fw = dict(infill=FORGED, post=IRON, post_w=.16)
    frame(g, 'X', y1, x0 - .05, x1 + .05, top, eave + .03, 1, bays=3, **fw)
    frame(g, 'Y', x0, y0 - .05, y1 - .05, top, eave + .03, -1, bays=2, windows=[(1.5, 2.0)], window_style='factory',
          window_scale=.8, **fw)
    frame(g, 'Y', x1, y0 - .05, y1 - .05, top, eave + .03, 1, bays=2, **fw)
    for x in (x0 + .06, (x0 + x1) / 2, x1 - .06):
        g.box((x, y0 - .02, (top + eave) / 2), (.16, .16, eave - top), IRON)
    g.box(((x0 + x1) / 2, y0 - .02, eave + .02), (x1 - x0 + .26, .2, .12), IRON)
    for x, s in ((x0 + .14, 1), (x1 - .14, -1)):
        g.beam((x, y0 - .02, eave - .5), (x + s * .45, y0 - .02, eave - .04), .07, mat=IRON)
    P.plank_roof(g, x0, y0, x1, y1, eave, eave + .95, ridge_axis='X', overhang=.22, plank=.3, gable_mat=PLANK)
    # Two flywheel pumps.
    for i, x in enumerate((6.0, 7.2)):
        py = 1.5
        g.box((x, py, top + .15), (.9, .8, .3), CONCRETE)
        P.lathe(g, (x + .05, py, top + .75), [(0, -.16), (.36, -.14), (.4, -.06), (.4, .06), (.36, .14), (0, .16)],
                PAINTED, axis='X', segments=18)
        P.motor(g, (x - .3, py, top + .65), .17, .36, axis='X')
        P.pipe(g, [(x + .05, py, top + 1.13), (x + .05, py, 2.3), (x + .05, y1 + .2, 2.3)], .09)
        P.pipe(g, [(x + .22, py - .2, top + .75), (x + .22, y0 + .1, top + .75)], .08, flanges=False)
        P.gauge(g, x + .05, py - .2, top + 1.25, 'front', .07)
        fw_ = P.flywheel(f'WaterTreatmentPlant.PumpFlywheel{i + 1}', (x - .58, py, top + .72), .42, axis='X', spokes=6)
        parts.append((fw_, 'SPIN_X', 2 if i == 0 else -2))
        g.box((x - .58, py, top + .13), (.08, .2, .26), IRON)
    K.lamp(g, (x0 + x1) / 2, y1 - .05, 2.4, face='front')


# ---------------------------------------------------------------- chlorine tower

def chlorine_tower(g):
    cx, cy = 5.75, 3.65
    K.revolve(g, (cx, cy, 0), [(.6, 0), (.6, .3)], CONCRETE, segments=16)
    K.revolve(g, (cx, cy, .3), [(.42, 0), (.42, 5.2)], IRON, segments=12)
    for z in (1.2, 2.4, 3.6, 4.8):
        K.band(g, (cx, cy, 0), .42, z, .07, PAINTED, segments=12)
    K.revolve(g, (cx, cy, 5.5), [(.46, 0), (.46, .06), (.1, .42), (0, .45)], ROOF, segments=12)
    g.cylinder((cx, cy, 6.05), .06, .2, IRON, 'Z', 8)
    K.ladder(g, cx, cy - .42, .3, 5.5, face='front', cage=True)
    P.gauge(g, cx - .25, cy - .41, 1.6, 'front', .07)
    # Chlorine gas cylinders in a rack, and the dosing line to the filters.
    for x in (5.4, 6.1):
        g.box((x, 4.58, .1), (.1, .56, .2), CONCRETE)
    for k, y in enumerate((4.4, 4.62, 4.84)):
        z = .3 if k != 1 else .32
        P.lathe(g, (5.75, y, z), [(0, -.5), (.1, -.47), (.1, .42), (.06, .48), (0, .5)],
                PAINTED, axis='X', segments=12)
        g.cylinder((6.3 if k != 1 else 6.31, y, z), .03, .07, BRASS, 'X', 6)
    P.pipe(g, [(cx + .42, cy, 3.8), (6.35, cy, 3.8), (6.35, 4.75, 3.8), (FILTER[0] - .06, 4.75, 3.8)], .05)


# ---------------------------------------------------------------- water tower

def water_tower(g, parts):
    cx, cy = TOWER
    leg = 1.05
    top = 7.6
    P.lattice_tower(g, cx - leg, cy - leg, cx + leg, cy + leg, 0, top, bays=6, w=.14)
    g.box((cx, cy, top + .06), (2 * leg + .2, 2 * leg + .2, .12), IRON)
    # Dished bottom, riveted shell, balcony at the whole layer 8.
    R = 1.22
    P.lathe(g, (cx, cy, 0), [(0, top + .12), (R * .7, top + .2), (R, top + .42)], IRON, segments=16)
    K.revolve(g, (cx, cy, top + .42), [(R, 0), (R, 2.6)], IRON, segments=16, cap_bottom=False, cap_top=False)
    for z in (top + .9, top + 1.6, top + 2.3):
        K.band(g, (cx, cy, 0), R, z, .08, PAINTED, segments=16)
    P.annulus(g, (cx, cy), R - .1, R + .42, 7.92, 8, IRON, segments=16)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        g.beam((cx + math.cos(a) * R, cy + math.sin(a) * R, 7.55),
               (cx + math.cos(a) * (R + .36), cy + math.sin(a) * (R + .36), 7.9), .06, mat=IRON)
    P.ring_rail(g, (cx, cy), R + .37, 8, height=.6, posts=16, gap=(math.pi * 1.1, math.pi * 1.25))
    # Lapped cone roof of teal boards with a finial and beacon.
    rz = top + .42 + 2.6
    K.revolve(g, (cx, cy, rz - .06), [(R + .1, 0), (R + .1, .1)], WOOD, segments=16)
    P.lathe(g, (cx, cy, 0), [(R + .2, rz), (R * .55, rz + .7)], ROOF, segments=16)
    P.lathe(g, (cx, cy, 0), [(R * .55 + .07, rz + .7), (0, rz + 1.45)], ROOF, segments=16)
    pivot = K.beacon(g, cx, cy, rz + 1.42)
    parts.append((K.beacon_shutter(*pivot, 'WaterTreatmentPlant.Beacon'), 'SPIN_Z', 2))
    # Riser main up the trestle centre and the ladder to the balcony.
    P.pipe(g, [(cx, cy, .1), (cx, cy, top + .14)], .17)
    K.revolve(g, (cx, cy, 0), [(.32, 0), (.32, .25)], CONCRETE, segments=16)
    P.pipe(g, [(FILTER[0] + 3.2, FILTER[1] - .06, 2.0), (FILTER[0] + 3.2, cy + .5, 2.0), (cx, cy + .5, 2.0),
               (cx, cy + .2, 2.0)], .1)
    # Treated-water outlet: a flanged socket on the right-hand face of the
    # site for the Timber Pipes OpenOut port (game data: right side, front).
    oz = .55
    P.pipe(g, [(cx + .05, cy, oz), (11.62, cy, oz)], .1)
    P.lathe(g, (11.78, cy, oz), [(.13, -.16), (.17, -.12), (.17, .1), (.21, .1), (.21, .16)], IRON, axis='X',
            segments=16)
    for k in range(8):
        a = k * math.pi / 4
        K.stud(g, (11.947, cy + math.cos(a) * .18, oz + math.sin(a) * .18), 'X', .018)
    g.cylinder((11.946, cy, oz), .11, .012, IRON, 'X', 16)
    P.pier(g, 11.75, cy, 0, oz - .22, .26)
    P.valve(g, (11.3, cy, oz), 'up', .12)
    K.ladder(g, cx - leg - .02, cy - .6, 0, 8, face='left', cage=True)
    P.gauge(g, cx - .18, cy - .17, 1.5, 'front', .07)
    K.lamp(g, cx - R - .02, cy, 8.9, face='left')


# ---------------------------------------------------------------- digester

def digester(g):
    K.tank(g, 10.4, 10.05, 0, .9, 2.0, mat=IRON, bands=3, roof='dome', segments=16)
    K.tank(g, 8.4, 10.05, 0, .6, 1.6, mat=PAINTED, bands=2, roof='cone', segments=12)
    P.pipe(g, [(9.5, 9.95, 1.6), (9.0, 9.95, 1.6), (9.0, FILTER[3] + .06, 1.6)], .08)
    P.pipe(g, [(10.4, 10.05, 3.0), (10.4, 10.05, 3.35), (11.3, 10.05, 3.35)], .05, flanges=False)
    P.valve(g, (9.0, 9.4, 1.6), 'left', .12)


def build(g, parts):
    for i, (cx, cy) in enumerate(CLARIFIERS):
        clarifier(g, parts, i + 1, cx, cy)
    cascade(g)
    aerator(parts)
    filter_house(g)
    pump_shed(g, parts)
    chlorine_tower(g)
    water_tower(g, parts)
    digester(g)
