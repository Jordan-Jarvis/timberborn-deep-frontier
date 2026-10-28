"""FertilizerWorks: composting and nitrate works (2 workers, 80 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the bagging lean-to with its sack conveyor, forecourt barrels,
planting and post lamp.

HERO: a battery of three tall timber-stave silos with teal cone caps, fed by a
lattice bucket elevator and a roof-top conveyor gallery.
ROOF: ribbed teal barrel vault over the composting hall.

Parts: concrete-and-orange composting hall with a barrel vault and roof
ventilators; three hooped stave silos on concrete drums; open lattice bucket
elevator with a forged down-leg, boot and head house; covered gallery over the
silo caps with chutes; rotary drier drum on trunnion piers with a firebox and
stack; bagging lean-to with a sack conveyor.

Animated: drier drum (SPIN_X), bucket chain (CUSTOM_LOOP_Z), elevator head
pulley (SPIN_Y), sack conveyor (CUSTOM_LOOP_X), firebox draught fan (SPIN_Y).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401  (animate used by the harness)
import native_building_assets as N

IDENT = 'FertilizerWorks'
# Footprint ends at the walls (hall front y = 1, silo row back): the bagging
# lean-to, forecourt props and decoration in front were removed. Artwork keeps
# its original coordinates; GRID_ORIGIN is the footprint's (0, 0) corner.
FOOTPRINT = (9, 6)
GRID_ORIGIN = (0, 1)
HEIGHT = 13
HERO = 'Battery of three tall hooped timber-stave silos with teal cone caps, fed by a lattice bucket elevator and a roof-top gallery.'
FRAME_END = 121

SILO_X = (1.2, 3.1, 5.0)
SILO_Y = 6.1
SILO_R = .85


def hall(g):
    x0, y0, x1, y1 = 0.0, 1.0, 5.0, 4.0   # whole tiles; door face on y = 1
    P.podium(g, x0, y0, x1, y1, 1.5, skip=[(2.0, 3.0), (3.9, 4.6)])
    P.door(g, 2.5, y0, 0, 'Door0')
    # Bagging hatch in the podium face (dark recess) feeding the sack belt.
    blk(g, 4.0, y0 - .03, .55, 4.5, y0 + .002, .95, IRON)
    blk(g, 3.95, y0 - .05, .95, 4.55, y0 + .002, 1.03, WOOD)
    # Upper storey: orange plaster in a dark timber frame, tall grand windows.
    xs = [x0 + .05 + (x1 - x0 - .1) * (i + .5) / 5 for i in range(5)]
    P.framed_block(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, 1.5, 3.7, infill=ORANGE, pitch=.94,
                   windows={'front': [(x, 2.55, 1.15, 'grand') for x in xs],
                            'back': [(x, 2.55, 1.15, 'grand') for x in xs[1::2]],
                            'left': [(1.9, 2.55, 1.0, 'grand'), (3.3, 2.55, 1.0, 'grand')]})
    # Podium windows (factory grids) on the long front either side of the door.
    for x in (1.0, 3.5):
        P.native_window(g, x, y0, .75, .8, 'front', 'factory')
    P.native_window(g, x0, 2.6, .8, .8, 'left', 'factory')
    # Barrel vault along X with closed lunette ends.
    spring, rise = 3.7, 1.25
    ya, yb = y0 + .05, y1 - .05
    K.barrel_roof(g, x0 + .05, ya, x1 - .05, yb, spring, rise, axis='X', ribs=5)
    half_in = (yb - ya) / 2 + .12 - .08
    cy = (ya + yb) / 2
    for plane, out in ((x0 + .05, -1), (x1 - .05, 1)):
        pts = []
        n = 14
        wall_half = (yb - ya) / 2
        for k in range(n + 1):
            u = -wall_half + 2 * wall_half * k / n
            z = spring + (rise - .08) * math.sqrt(max(0.0, 1 - (u / half_in) ** 2)) - .01
            pts.append((plane, cy + u, z))
        pts = [(plane, cy + wall_half, spring)] + pts[::-1] + [(plane, cy - wall_half, spring)]
        K.oriented_polygon(g, pts, (out, 0, 0), PLANK)
        # Timber lunette frame and a native window in the end wall.
        blk(g, plane + (-.05 if out < 0 else 0), cy - .06, spring, plane + (0 if out < 0 else .05), cy + .06, spring + rise - .14, WOOD)
        P.native_window(g, plane, cy - .62, spring + .45, .62, 'left' if out < 0 else 'right', 'lancet')
        P.native_window(g, plane, cy + .62, spring + .45, .62, 'left' if out < 0 else 'right', 'lancet')
    # Ridge ventilators: louvered timber boxes with pyramid caps.
    for x in (1.6, 4.0):
        top = spring + rise + .12
        blk(g, x - .3, cy - .3, top - .25, x + .3, cy + .3, top + .45, FORGED)
        for k in range(4):
            z = top - .05 + k * .12
            blk(g, x - .32, cy - .32, z, x + .32, cy + .32, z + .035, WOOD)
        P.pyramid_roof(g, x, cy, .3, top + .45, .4, overhang=.1)
    # Steam main along the back wall from the drier firebox.
    P.flanged_pipe(g, [(8.45, 3.75, 1.3), (x1 + .02, 3.75, 1.3)], .07)
    K.valve_wheel(g, 5.7, 3.62, 1.3, face='front', r=.13)
    P.gauge(g, 6.2, 3.68, 1.3, 'front')


def silos(g):
    for x in SILO_X:
        P.silo(g, x, SILO_Y, 0, SILO_R, 6.8, base_h=2.6, cone=.9, hoops=5)
        K.band(g, (x, SILO_Y, 0), SILO_R + .07, 2.5, .12, CONCRETE, segments=12, proud=.04, phase=math.pi / 12)
        # Inspection hatch and ladder on the front of each drum.
        blk(g, x - .2, SILO_Y - SILO_R - .14, .3, x + .2, SILO_Y - SILO_R + .2, .95, IRON)
        K.ladder(g, x + .45, SILO_Y - SILO_R - .02, 1.4, 9.3, face='front')
    # Silo-top inspection walk joining the silo ladders to the elevator.
    P.walk(g, .55, 4.92, 6.6, 5.27, 9, rails=('front', 'left'))
    for x in (.75, 2.25, 4.15, 6.1):
        g.beam((x, 5.27, 8.3), (x, 4.98, 8.9), .07, mat=IRON)
        blk(g, x - .05, 5.2, 8.2, x + .05, 5.32, 8.96, IRON)


def elevator(g, parts):
    cx, cy = 7.1, 6.1
    # Boot house.
    P.podium(g, 6.0, 5.0, 8.0, 7.0, 1.0, joints=False)   # boot house on 2 x 2 tiles
    # Lattice tower.
    K.lattice_tower(g, 6.6, 5.6, 7.6, 6.6, 1.0, 10.6, bays=8)
    # Down leg: closed forged casing; up leg: belt with moving buckets.
    blk(g, 7.22, 5.96, 1.0, 7.48, 6.22, 10.6, FORGED)
    for k in range(9):
        z = 1.6 + k * 1.1
        blk(g, 7.2, 5.94, z, 7.5, 6.24, z + .06, IRON)
    blk(g, 6.78, 6.04, 1.0, 6.96, 6.08, 10.6, IRON)
    chain = Geometry('BucketChain', (6.87, 6.0, 5.0))
    pitch = .5
    for k in range(-1, 21):
        z = 1.17 + k * pitch
        blk(chain, 6.76, 5.83, z, 6.98, 6.04, z + .13, PAINTED)
        blk(chain, 6.78, 5.81, z + .1, 6.96, 5.85, z + .15, IRON)
    parts.append((chain, 'CUSTOM_LOOP_Z', pitch))
    # Head house with hipped cap.
    P.framed_block(g, 6.35, 5.35, 7.85, 6.85, 10.6, 11.7, infill=FORGED, frame=IRON, pitch=.75, sink=.0,
                   windows={'front': [(7.4, 11.15, .55, 'factory')]})
    blk(g, 6.3, 5.3, 10.45, 7.9, 6.9, 10.6, IRON)
    P.hip_roof(g, 6.35, 5.35, 7.85, 6.85, 11.7, .6, overhang=.1)
    K.beacon(g, 7.1, 6.1, 12.34)
    parts.append((K.beacon_shutter(7.1, 6.1, 12.48, 'ElevatorBeacon'), 'SPIN_Z', 2))
    # Head pulley drive on the front of the head house.
    wheel = Geometry('HeadPulley', (6.78, 5.2, 11.1))
    wheel.wheel((6.78, 5.2, 11.1), .3, 'Y', IRON, BRASS)
    parts.append((wheel, 'SPIN_Y', 1))
    blk(g, 6.72, 5.28, 11.05, 6.84, 5.35, 11.15, IRON)
    blk(g, 7.2, 5.15, 10.62, 7.6, 5.35, 10.95, PAINTED)
    g.cylinder((7.4, 5.13, 10.78), .1, .05, IRON, 'Y', 12)
    K.ladder(g, 7.7, 6.6, 1.0, 10.45, face='right')


def gallery(g):
    x0, x1, y0, y1, z0, z1 = .8, 6.4, 5.82, 6.38, 10.55, 11.1
    blk(g, x0, y0, z0, x1, y1, z1, FORGED)
    for y, s in ((y0, -1), (y1, 1)):
        for za, zb in ((z0 - .01, z0 + .1), (z1 - .1, z1 + .01)):
            blk(g, x0 + .03, min(y, y + s * .05), za, x1 - .03, max(y, y + s * .05), zb, IRON)
        for k in range(8):
            x = x0 + .35 + k * (x1 - x0 - .7) / 7
            blk(g, x - .04, min(y, y + s * .04), z0 + .1, x + .04, max(y, y + s * .04), z1 - .1, IRON)
    K.gable_roof(g, x0, y0, x1, y1, z1, z1 + .35, ridge_axis='X', overhang=.08, gable_mat=FORGED)
    for x in SILO_X:
        g.cylinder((x, SILO_Y, 10.3), .1, .55, IRON, 'Z', 12)
        g.ring((x, SILO_Y, 10.48), .15, .05, .06, BRASS, 'Z', 12)
        for s in (-1, 1):
            g.beam((x + s * .75, SILO_Y, 9.45), (x + s * .35, SILO_Y, z0 - .005), .08, mat=IRON)


def drier(g, parts):
    cy, cz, r = 2.5, 1.55, .6
    xa, xb = 5.95, 8.05
    P.podium(g, 5.0, 1.0, 9.0, 4.0, .22, joints=False, foot=False)   # drier bed on tiles 5..9 x 1..4
    # Trunnion piers with rollers under the riding rings.
    for x in (6.35, 7.65):
        blk(g, x - .24, 1.95, .15, x + .24, 3.05, .72, CONCRETE)
        blk(g, x - .28, 1.91, .72, x + .28, 3.09, .78, IRON)
        for s in (-1, 1):
            g.cylinder((x, cy + s * .42, .85), .12, .2, IRON, 'X', 12)
            blk(g, x - .14, cy + s * .42 - .08, .78, x - .1, cy + s * .42 + .08, .9, IRON)
            blk(g, x + .1, cy + s * .42 - .08, .78, x + .14, cy + s * .42 + .08, .9, IRON)
    # Pinion and motor driving the girth gear.
    blk(g, 6.85, 1.55, .15, 7.25, 1.95, .62, CONCRETE)
    blk(g, 6.88, 1.6, .62, 7.22, 1.92, .9, PAINTED)
    g.cylinder((7.05, 1.75, .9), .08, .4, IRON, 'X', 10)
    # Firebox and stack at the feed end.
    P.podium(g, 8.0, 2.0, 9.0, 3.0, 2.2, joints=False, foot=False, base=.22)   # one-tile firebox on the bed
    blk(g, 7.97, 2.2, .7, 8.0, 2.8, 1.3, IRON)
    blk(g, 8.2, 1.93, .45, 8.8, 2.0, 1.0, IRON)
    for x in (8.3, 8.5, 8.7):
        K.stud(g, (x, 1.91, .9), 'Y', .025)
    K.stack(g, 8.5, 2.5, 2.2, 6.2, emits='smoke', r=.22)
    # Draught fan housing on the firebox side with a spinning impeller.
    g.cylinder((8.5, 3.13, 1.3), .32, .16, IRON, 'Y', 16)
    g.ring((8.5, 3.23, 1.3), .33, .05, .05, BRASS, 'Y', 16)
    fan = K.fan('DraughtFan', 8.5, 3.25, 1.3, .27, axis='Y', blades=6)
    parts.append((fan, 'SPIN_Y', 3))
    # Discharge hood at the hall end with a chute.
    blk(g, 5.5, 1.95, .15, 5.95, 3.05, 2.25, FORGED)
    blk(g, 5.47, 1.92, 2.25, 5.98, 3.08, 2.33, IRON)
    blk(g, 5.47, 1.92, .9, 5.98, 3.08, .96, IRON)
    K.stack(g, 5.72, 2.5, 2.33, 1.0, emits='steam', r=.12, bands=2)   # drier vapour
    # Rotating drum: riveted shell, riding rings, girth gear, strakes.
    drum = Geometry('DrierDrum', ((xa + xb) / 2, cy, cz))
    drum.cylinder(((xa + xb) / 2, cy, cz), r, xb - xa, IRON, 'X', 12)
    for x in (6.35, 7.65):
        drum.ring((x, cy, cz), .72, .12, .16, PAINTED, 'X', 12)
        drum.cylinder((x, cy, cz), .62 + .0, .001 + .15, IRON, 'X', 12)
    drum.ring((7.05, cy, cz), .74, .14, .12, BRASS, 'X', 16)
    for i in range(24):
        a = i * 2 * math.pi / 24
        p = (7.05, cy + math.cos(a) * .76, cz + math.sin(a) * .76)
        drum.box(p, (.1, .05, .05), IRON)
    for i in range(6):
        a = i * math.pi / 3 + .2
        for xs, xe in ((xa + .05, 6.2), (6.5, 6.9), (7.2, 7.5), (7.8, xb - .05)):
            p0 = (xs, cy + math.cos(a) * (r + .015), cz + math.sin(a) * (r + .015))
            p1 = (xe, cy + math.cos(a) * (r + .015), cz + math.sin(a) * (r + .015))
            drum.beam(p0, p1, .06, .03, PAINTED)
    parts.append((drum, 'SPIN_X', .5))
    # Feed pipe from firebox into the drum mouth.
    g.cylinder((8.0, cy, cz), .34, .14, FORGED, 'X', 16)


def door_lamps(g):
    # Wall lamps either side of the door (no forecourt props or planting).
    K.lamp(g, 1.9, 1.0, 1.15, face='front')
    K.lamp(g, 3.1, 1.0, 1.15, face='front')


def build(g, parts):
    hall(g)
    silos(g)
    elevator(g, parts)
    gallery(g)
    drier(g, parts)
    door_lamps(g)
