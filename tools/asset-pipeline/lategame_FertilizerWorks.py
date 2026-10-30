"""FertilizerWorks: composting and nitrate works (2 workers, 80 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the bagging lean-to with its sack conveyor, forecourt barrels,
planting and post lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings"): 9x6x13 -> 7x5x7, inside the old
footprint with the same origin, door and native entrance (cell 2, -1).
Removed: the elevator's open lattice tower (the bucket elevator is now a
closed boarded leg with its buckets running up an open front slot), the
silo-top inspection walk and silo ladders, the steam main along the back
and the hall's barrel vault. The silos are four layers lower.

HERO: a battery of three hooped timber-stave silos with teal cone caps, fed
by a closed bucket elevator and a covered gallery over the silo caps.
ROOF: flat timber-plank roof with a timber curb on the two-storey
composting hall (one layer per storey), all eight cells placeable; hipped
teal cap on the elevator head house; teal cone caps on the silos. No roof
vents or roof stacks.
NO CONCRETE (user, 2026-10-30: the works unlocks at 350 science, before
concrete exists, so none may show): boarded grey-timber ground storeys on
timber sole plates and head beams, riveted steel silo drums, timber
cribbing under the drier, a riveted steel firebox.

Parts: timber-and-orange composting hall;
three hooped stave silos on riveted steel drums; boarded bucket elevator
with boot house and head house; covered gallery over the silo caps with
chutes; rotary drier drum on timber cribbing with a firebox, draught fan and
stack.

Animated (5, names unchanged): drier drum (SPIN_X), bucket chain
(CUSTOM_LOOP_Z), elevator head pulley (SPIN_Y), elevator beacon (SPIN_Z),
firebox draught fan (SPIN_Y).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import ORANGE, FORGED, PAINTED, GREYPLANK
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401  (animate used by the harness)
import compact_industry_parts as Q

IDENT = 'FertilizerWorks'
# Artwork keeps its original coordinates (hall front y = 1); GRID_ORIGIN is
# the footprint's (0, 0) corner.
FOOTPRINT = (7, 5)
GRID_ORIGIN = (0, 1)
HEIGHT = 7
HERO = 'Battery of three hooped timber-stave silos with teal cone caps, fed by a closed bucket elevator and a covered gallery.'
FRAME_END = 121

HALL = (0.0, 1.0, 4.0, 3.0)
DOOR_X = 2.5
SILO_X = (.66, 1.98, 3.3)   # footings (apothem .64) clear each other and the boot house
SILO_Y = 4.3
SILO_R = .55
SILO_BASE, SILO_H, SILO_CONE = 1.0, 3.3, .5
ELEV = (5.0, 5.0)                # elevator leg centre
GALLERY = (.3, 5.3, 4.05, 4.55, 5.1, 5.45)   # x0, x1, y0, y1, z0, z1


def hall(g):
    x0, y0, x1, y1 = HALL
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, door=DOOR_X, door_id='Door0',
                         roof_mat=PLANK, curb_mat=WOOD, ground_mat=GREYPLANK, roof_boards=True,
                         ground_windows={'front': [(.75, .6, 'factory'), (3.5, .6, 'factory')],
                                         'left': [(2.0, .6, 'factory')]},
                         windows={'front': [(x + .5, 1.5, .55, 'grand') for x in range(4)],
                                  'left': [(1.5, 1.5, .55, 'grand'), (2.5, 1.5, .55, 'grand')],
                                  'back': [(.5, 1.5, .55, 'grand'), (3.5, 1.5, .55, 'grand')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    K.lamp(g, DOOR_X + .66, y0 - .01, .8, face='front')
    # (No ventilators on the roof: every flat roof cell is a placeable area.)


def silos(g):
    for x in SILO_X:
        Q.stave_silo(g, x, SILO_Y, 0, SILO_R, SILO_H, base_h=SILO_BASE, cone=SILO_CONE, hoops=4)
        K.band(g, (x, SILO_Y, 0), SILO_R + .07, SILO_BASE - .1, .1, IRON, segments=12, proud=.04,
               phase=math.pi / 12)
        # Inspection hatch on the front of each drum.
        blk(g, x - .16, SILO_Y - SILO_R - .12, .25, x + .16, SILO_Y - SILO_R + .15, .75, IRON)


def elevator(g, parts):
    cx, cy = ELEV
    # Boot house on 2 x 2 tiles.
    Q.timber_podium(g, 4.0, 4.0, 6.0, 6.0, 1.0)
    # Closed boarded leg; the up-leg runs in an open slot on its front.
    lx0, lx1, ly0, ly1 = cx - .4, cx + .4, cy - .3, cy + .4
    blk(g, lx0, ly0 + .12, 1.0 - .02, lx1, ly1, 5.5, PLANK)
    for k in range(4):
        z = 1.6 + k * 1.05
        blk(g, lx0 - .03, ly0 + .09, z, lx1 + .03, ly1 + .03, z + .07, IRON)
    for x in (lx0 + .03, lx1 - .03):
        blk(g, x - .03, ly0, 1.0, x + .03, ly0 + .12, 5.5, IRON)
    blk(g, lx0 + .06, ly0 + .02, 1.0, lx1 - .06, ly0 + .06, 5.5, IRON)
    chain = Geometry('BucketChain', (cx, ly0 + .09, 3.0))
    pitch = .4
    for k in range(-1, 12):
        z = 1.1 + k * pitch
        blk(chain, cx - .14, ly0 + .065, z, cx + .14, ly0 + .12, z + .12, PAINTED)
        blk(chain, cx - .12, ly0 + .045, z + .09, cx + .12, ly0 + .07, z + .13, IRON)
    parts.append((chain, 'CUSTOM_LOOP_Z', pitch))
    # Head house with a hipped cap.
    hx0, hy0, hx1, hy1 = cx - .62, cy - .55, cx + .62, cy + .6
    P.framed_block(g, hx0, hy0, hx1, hy1, 5.5, 6.15, infill=FORGED, frame=IRON, pitch=.6, sink=.0,
                   windows={'right': [(cy, 5.85, .45, 'factory')]})
    blk(g, hx0 - .05, hy0 - .05, 5.38, hx1 + .05, hy1 + .05, 5.5, IRON)
    P.hip_roof(g, hx0, hy0, hx1, hy1, 6.15, .38, overhang=.08)
    K.beacon(g, cx, cy, 6.55)
    parts.append((K.beacon_shutter(cx, cy, 6.69, 'ElevatorBeacon'), 'SPIN_Z', 2))
    # Head pulley drive on the front of the head house.
    wheel = Geometry('HeadPulley', (cx - .3, hy0 - .14, 5.85))
    K.wheel(wheel, (cx - .3, hy0 - .14, 5.85), .22, 'Y')
    parts.append((wheel, 'SPIN_Y', 1))
    blk(g, cx - .35, hy0 - .07, 5.8, cx - .25, hy0, 5.9, IRON)
    blk(g, cx + .05, hy0 - .16, 5.55, cx + .4, hy0, 5.8, PAINTED)
    K.ladder(g, cx + .4, cy + .1, 1.0, 5.38, face='right', width=.3, cage=False)


def gallery(g):
    x0, x1, y0, y1, z0, z1 = GALLERY
    blk(g, x0, y0, z0, x1, y1, z1, FORGED)
    for y, s in ((y0, -1), (y1, 1)):
        for za, zb in ((z0 - .01, z0 + .08), (z1 - .08, z1 + .01)):
            blk(g, x0 + .03, min(y, y + s * .04), za, x1 - .03, max(y, y + s * .04), zb, IRON)
        for k in range(6):
            x = x0 + .3 + k * (x1 - x0 - .6) / 5
            blk(g, x - .035, min(y, y + s * .035), z0 + .08, x + .035, max(y, y + s * .035), z1 - .08, IRON)
    # Flat steel roof with a low curb.
    blk(g, x0 - .05, y0 - .05, z1, x1 + .02, y1 + .05, z1 + .06, IRON)
    for x in SILO_X:
        g.cylinder((x, SILO_Y, (SILO_BASE + SILO_H + SILO_CONE - .08 + z0) / 2), .08,
                   z0 - (SILO_BASE + SILO_H + SILO_CONE - .08) + .02, IRON, 'Z', 12)
        g.ring((x, SILO_Y, z0 - .1), .12, .04, .05, BRASS, 'Z', 12)
    # Hanger struts from the gallery onto the silo cone shoulders.
    for x in SILO_X[:2]:
        for s in (-1, 1):
            g.beam((x + s * .45, SILO_Y, SILO_BASE + SILO_H + .08), (x + s * .2, SILO_Y, z0 - .005), .06, mat=IRON)


def drier(g, parts):
    cy, cz, r = 2.0, 1.15, .45
    xa, xb = 4.45, 6.0
    P.podium(g, 4.0, 1.0, 7.0, 3.0, .22, mat=WOOD, joints=False, foot=False)   # timber drier bed on tiles 4..7 x 1..3
    # Timber-crib trunnion piers with rollers under the riding rings.
    for x in (4.8, 5.7):
        blk(g, x - .18, 1.6, .15, x + .18, 2.4, .5, PLANK)
        blk(g, x - .21, 1.57, .5, x + .21, 2.43, .55, IRON)
        for s in (-1, 1):
            g.cylinder((x, cy + s * .32, .62), .09, .16, IRON, 'X', 12)
            blk(g, x - .11, cy + s * .32 - .06, .55, x - .08, cy + s * .32 + .06, .65, IRON)
            blk(g, x + .08, cy + s * .32 - .06, .55, x + .11, cy + s * .32 + .06, .65, IRON)
    # Pinion and motor driving the girth gear.
    blk(g, 5.1, 1.3, .15, 5.4, 1.55, .45, PLANK)
    blk(g, 5.12, 1.33, .45, 5.38, 1.55, .66, PAINTED)
    g.cylinder((5.25, 1.44, .66), .06, .3, IRON, 'X', 10)
    # Firebox and stack at the feed end.
    P.podium(g, 6.0, 1.5, 7.0, 2.5, 1.6, mat=FORGED, joints=False, foot=False, base=.22)   # riveted steel firebox
    blk(g, 5.97, 1.7, .55, 6.0, 2.3, 1.0, IRON)
    blk(g, 6.2, 1.43, .4, 6.8, 1.5, .85, IRON)
    K.stack(g, 6.5, 2.0, 1.6, 3.2, emits='smoke', r=.18)
    # Draught fan housing on the firebox's back with a spinning impeller.
    g.cylinder((6.5, 2.62, 1.0), .26, .14, IRON, 'Y', 12)
    g.ring((6.5, 2.71, 1.0), .27, .045, .045, BRASS, 'Y', 12)
    fan = K.fan('DraughtFan', 6.5, 2.73, 1.0, .22, axis='Y', blades=6)
    parts.append((fan, 'SPIN_Y', 3))
    # Discharge hood at the hall end (no vapour stack on it: no roof stacks).
    blk(g, 4.08, 1.6, .15, 4.45, 2.4, 1.75, FORGED)
    blk(g, 4.05, 1.57, 1.75, 4.48, 2.43, 1.82, IRON)
    blk(g, 4.05, 1.57, .7, 4.48, 2.43, .75, IRON)
    # Rotating drum: riveted shell, riding rings, girth gear, strakes.
    drum = Geometry('DrierDrum', ((xa + xb) / 2, cy, cz))
    drum.cylinder(((xa + xb) / 2, cy, cz), r, xb - xa, IRON, 'X', 12)
    for x in (4.8, 5.7):
        drum.ring((x, cy, cz), .55, .1, .13, PAINTED, 'X', 12)
        drum.cylinder((x, cy, cz), .46, .12, IRON, 'X', 12)
    drum.ring((5.25, cy, cz), .56, .11, .1, BRASS, 'X', 12)
    for i in range(12):
        a = i * 2 * math.pi / 12
        drum.box((5.25, cy + math.cos(a) * .58, cz + math.sin(a) * .58), (.08, .04, .04), IRON)
    for i in range(6):
        a = i * math.pi / 3 + .2
        for xs, xe in ((xa + .04, 4.68), (4.92, 5.13), (5.37, 5.58), (5.82, xb - .04)):
            p0 = (xs, cy + math.cos(a) * (r + .012), cz + math.sin(a) * (r + .012))
            p1 = (xe, cy + math.cos(a) * (r + .012), cz + math.sin(a) * (r + .012))
            drum.beam(p0, p1, .05, .025, PAINTED)
    parts.append((drum, 'SPIN_X', .5))
    # Feed throat from the firebox into the drum mouth.
    g.cylinder((6.0, cy, cz), .26, .1, FORGED, 'X', 12)


def build(g, parts):
    hall(g)
    silos(g)
    elevator(g, parts)
    gallery(g)
    drier(g, parts)
