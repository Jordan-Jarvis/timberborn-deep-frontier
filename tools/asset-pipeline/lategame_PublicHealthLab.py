"""PublicHealthLab: civic water and sanitation laboratory (3 workers, 100 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the water-testing forecourt (basin, fountain, sampling hoist, dosing
tanks), planting and post lamp.

HERO: a tall square concrete ventilation tower, steel-banded and louvred,
crowned by a ring of turning ventilator cowls.
ROOF: steep teal mansard with lancet dormers on the pale plaster lab wing,
topped by an octagonal glazed observation lantern.

Parts: two-layer cast-concrete podium with factory windows and the native
door; pale plaster lab wing in a dark timber frame with two rows of lancet
windows; mansard with dormers and observation lantern with anemometer;
ventilation tower with louvres, duct bridge, platform rail and ladder;
water-testing basin with a fountain (native water) and a sampling hoist;
two dosing tanks with a dosing pump; raised header tank on the podium roof.

Animated: five tower cowls (SPIN_Z), anemometer (SPIN_Z), sampling bucket
(PISTON_Z), dosing-pump flywheel (SPIN_X).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N

IDENT = 'PublicHealthLab'
# Footprint ends at the podium face (y = 2); GRID_ORIGIN is its (0, 0)
# corner in the artwork coordinates used below.
FOOTPRINT = (8, 6)
GRID_ORIGIN = (0, 2)
HEIGHT = 12
HERO = 'Tall square concrete ventilation tower, steel-banded and louvred, crowned by a ring of turning ventilator cowls.'
FRAME_END = 121

PODIUM = (0.0, 2.0, 8.0, 8.0)   # whole tiles to the footprint edges
PTOP = 2.0
WING = (.2, 2.45, 5.2, 7.6)
WTOP = 4.6
TOWER = (5.85, 3.65, 7.15, 4.95)
TTOP = 10.0


def podium(g):
    x0, y0, x1, y1 = PODIUM
    P.podium(g, x0, y0, x1, y1, PTOP, skip=[(4.0, 5.0)])
    P.door(g, 4.5, y0, 0, 'Door0')
    for x in (1.0, 2.0, 3.0, 6.0, 7.0):
        P.native_window(g, x, y0, .75, .8, 'front', 'factory')
        P.native_window(g, x, y0, 1.5, .6, 'front', 'factory')
    for y in (3.0, 4.5, 6.0):
        P.native_window(g, x0, y, 1.1, .8, 'left', 'factory')
        P.native_window(g, x1, y, 1.1, .8, 'right', 'factory')
    for x in (1.5, 3.5, 5.5):
        P.native_window(g, x, y1, 1.1, .8, 'back', 'factory')
    K.lamp(g, 3.88, y0, 1.05, face='front')
    K.lamp(g, 5.12, y0, 1.05, face='front')
    # Low parapet on the exposed podium roof edges (right and back strips).
    blk(g, 5.2, y0 + .05, PTOP, x1 - .05, y0 + .19, PTOP + .3, CONCRETE)
    blk(g, x1 - .19, y0 + .19, PTOP, x1 - .05, y1 - .05, PTOP + .3, CONCRETE)
    blk(g, x0 + .05, y1 - .19, PTOP, x1 - .19, y1 - .05, PTOP + .3, CONCRETE)
    blk(g, 5.18, y0 + .03, PTOP + .3, x1 - .03, y0 + .21, PTOP + .34, IRON)
    blk(g, x1 - .21, y0 + .21, PTOP + .3, x1 - .03, y1 - .03, PTOP + .34, IRON)
    blk(g, x0 + .03, y1 - .21, PTOP + .3, x1 - .21, y1 - .03, PTOP + .34, IRON)


def lab_wing(g, parts):
    x0, y0, x1, y1 = WING
    xs = [x0 + (x1 - x0) * (i + .5) / 5 for i in range(5)]
    ys = [y0 + (y1 - y0) * (i + .5) / 5 for i in range(5)]
    rows = (2.72, 3.95)
    P.framed_block(g, x0, y0, x1, y1, PTOP, WTOP, infill=CONCRETE, frame=GREYWOOD, pitch=99,
                   floors=(3.33,),
                   windows={'front': [(x, z, 1.0, 'lancet') for x in xs for z in rows],
                            'back': [(x, z, 1.0, 'lancet') for x in xs for z in rows],
                            'left': [(y, z, 1.0, 'lancet') for y in ys for z in rows],
                            'right': [(y, 3.95, 1.0, 'lancet') for y in (ys[0], ys[4])]})
    # Mansard with lancet dormers.
    inset, h = .5, 1.35
    deck = P.mansard(g, x0, y0, x1, y1, WTOP, h, inset)
    for xd in (xs[0], xs[2], xs[4]):
        yf, yb = y0 - .03, y0 + .5
        blk(g, xd - .28, yf, WTOP + .05, xd + .28, yb, WTOP + .98, CONCRETE)
        for xx in (xd - .28, xd + .23):
            blk(g, xx, yf - .04, WTOP + .2, xx + .05, yf, WTOP + .98, GREYWOOD)
        P.native_window(g, xd, yf, WTOP + .62, .7, 'front', 'lancet')
        K.gable_roof(g, xd - .28, yf, xd + .28, yb, WTOP + .98, WTOP + 1.28, ridge_axis='Y', overhang=.09)
    # Observation lantern on the deck.
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    blk(g, cx - 1.0, cy - 1.0, deck, cx + 1.0, cy + 1.0, deck + .12, CONCRETE)
    z0, z1 = deck + .12, deck + .95
    P.octagon_frustum(g, cx, cy, z0, z1, .58, .58, IRON)
    for a, b in (((cx - .92, cy - .92), (cx + .92, cy - .92)), ((cx - .92, cy + .92), (cx + .92, cy + .92))):
        P.rail(g, a, b, deck + .12, height=.45)
    for a, b in (((cx - .92, cy - .92), (cx - .92, cy + .92)), ((cx + .92, cy - .92), (cx + .92, cy + .92))):
        P.rail(g, a, b, deck + .12, height=.45, skip_start=True, skip_end=True)
    k = 1 / math.cos(math.pi / 8)
    for i in range(8):
        P.facet_window(g, cx, cy, 45 * i, .58, z0, .58, z1, .5, .78, 'lancet')
        a = math.radians(22.5 + 45 * i)
        g.box((cx + math.cos(a) * (.58 * k + .005), cy + math.sin(a) * (.58 * k + .005), (z0 + z1) / 2), (.07, .07, z1 - z0), WOOD)
    K.revolve(g, (cx, cy, z1), [(.7 * k, 0), (.7 * k, .06), (.62 * k, .12), (.3, .42), (0, .55)], ROOF, segments=8, phase=math.pi / 8)
    K.revolve(g, (cx, cy, z1 + .5), [(.04, 0), (.04, .45)], IRON, segments=8)
    an = Geometry('Anemometer', (cx, cy, z1 + 1.0))
    an.cylinder((cx, cy, z1 + .97), .05, .08, BRASS, 'Z', 8)
    for i in range(3):
        a = i * 2 * math.pi / 3
        tip = (cx + math.cos(a) * .3, cy + math.sin(a) * .3, z1 + .99)
        an.beam((cx, cy, z1 + .99), tip, .025, mat=IRON)
        K.revolve(an, (tip[0], tip[1], tip[2] - .06), [(.001, 0), (.08, .04), (.08, .1), (.001, .12)], BRASS, segments=8)
    parts.append((an, 'SPIN_Z', 2))
    # Chimney flue for the fume cupboards.
    blk(g, x0 + .5, y1 - .7, deck - .2, x0 + .85, y1 - .35, deck + .9, CONCRETE)
    blk(g, x0 + .46, y1 - .74, deck + .9, x0 + .89, y1 - .31, deck + 1.0, IRON)
    K.emitter(g, 'steam', x0 + .675, y1 - .525, deck + 1.0, .175)   # fume vapour


def vent_tower(g, parts):
    x0, y0, x1, y1 = TOWER
    P.framed_block(g, x0, y0, x1, y1, PTOP, TTOP, infill=CONCRETE, frame=IRON, pitch=5.0, corner=.2,
                   floors=(3.5, 5.0, 6.5, 8.0), sink=.04)
    # Louvre panels near the top on three faces.
    for face in ('front', 'left', 'right', 'back'):
        for k in range(8):
            z = 8.35 + k * .17
            if face == 'front':
                blk(g, x0 + .2, y0 - .07, z, x1 - .2, y0, z + .09, FORGED)
            elif face == 'back':
                blk(g, x0 + .2, y1, z, x1 - .2, y1 + .07, z + .09, FORGED)
            elif face == 'left':
                blk(g, x0 - .07, y0 + .2, z, x0, y1 - .2, z + .09, FORGED)
            else:
                blk(g, x1, y0 + .2, z, x1 + .07, y1 - .2, z + .09, FORGED)
    # Small lancet slits up the shaft front.
    for z in (4.25, 5.75, 7.25):
        P.native_window(g, (x0 + x1) / 2, y0, z, .6, 'front', 'lancet')
        P.native_window(g, x1, (y0 + y1) / 2, z, .6, 'right', 'lancet')
    # Cap, platform and cowls.
    blk(g, x0 - .12, y0 - .12, TTOP - .02, x1 + .12, y1 + .12, TTOP + .12, CONCRETE)
    blk(g, x0 - .16, y0 - .16, TTOP + .12, x1 + .16, y1 + .16, TTOP + .18, IRON)
    top = TTOP + .18
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    P.rail(g, (x0 - .1, y0 - .1), (x1 + .1, y0 - .1), top, height=.45)
    P.rail(g, (x0 - .1, y1 + .1), (x1 + .1, y1 + .1), top, height=.45)
    P.rail(g, (x0 - .1, y0 - .1), (x0 - .1, y1 + .1), top, height=.45, skip_start=True, skip_end=True)
    P.rail(g, (x1 + .1, y0 - .1), (x1 + .1, y1 + .1), top, height=.45, skip_start=True, skip_end=True)
    corners = [(x0 + .3, y0 + .3), (x1 - .3, y0 + .3), (x1 - .3, y1 - .3), (x0 + .3, y1 - .3)]
    for i, (x, y) in enumerate(corners):
        g.cylinder((x, y, top + .1), .15, .2, IRON, 'Z', 12)
        c = P.cowl(f'TowerCowl{i}', x, y, top + .2, r=.19, h=.45, facing=i * math.pi / 2)
        parts.append((c, 'SPIN_Z', .5 if i % 2 else -.5))
    g.cylinder((cx, cy, top + .4), .22, .8, FORGED, 'Z', 14)
    g.ring((cx, cy, top + .72), .25, .05, .06, BRASS, 'Z', 14)
    big = P.cowl('TowerCowlMain', cx, cy, top + .8, r=.3, h=.62, facing=0)
    parts.append((big, 'SPIN_Z', .25))
    K.ladder(g, x1 - .35, y1, PTOP + .3, TTOP + .1, face='back')
    # Duct bridge from the lab wing.
    blk(g, WING[2], 4.0, 3.55, x0, 4.55, 4.1, FORGED)
    for x in (5.4, 5.65):
        blk(g, x - .04, 3.96, 3.51, x + .04, 4.59, 4.14, IRON)


def roof_tank(g, parts):
    # Header tank on the podium roof, piped into the lab wing. (The
    # water-testing forecourt, dosing tanks, planting and post lamp in front
    # of the podium were removed: the footprint ends at the podium face.)
    P.raised_tank(g, 6.6, 2.85, .5, 1.1, stand=.9, base=PTOP)
    P.flanged_pipe(g, [(6.12, 2.85, 3.35), (WING[2], 2.85, 3.35)], .05)


def build(g, parts):
    podium(g)
    lab_wing(g, parts)
    vent_tower(g, parts)
    roof_tank(g, parts)
