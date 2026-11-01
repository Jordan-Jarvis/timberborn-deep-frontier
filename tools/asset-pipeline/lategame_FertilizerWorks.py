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

Shrunk again 2026-11-01 (a YouTuber's first look: "why is it so massive?";
user: "we need to shrink the buildings down even more"): 7x5x7 -> 4x3x5,
inside the old footprint with the same origin, door and native entrance
(cell 2, -1). The composting hall keeps its two one-layer storeys on the
front 3x2 tiles; the three silos (thinner, one layer lower) stand in a row
on the back tiles; the drier now runs front to back in the right column
from its firebox at the front into the elevator boot at the back, and the
elevator rises in the back-right corner. Nothing stands on open ground.

HERO: a battery of three hooped timber-stave silos with teal cone caps, fed
by a closed bucket elevator and a covered gallery over the silo caps.
ROOF: flat timber-plank roof, open edge to edge, on the two-storey
composting hall (one layer per storey), all six cells placeable; hipped
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

Animated (5, names unchanged): drier drum (SPIN_Y since 2026-11-01, it
runs front to back), bucket chain (CUSTOM_LOOP_Z), elevator head pulley
(SPIN_Y), elevator beacon (SPIN_Z), firebox draught fan (SPIN_X on the
firebox's right side).
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
FOOTPRINT = (4, 3)
GRID_ORIGIN = (0, 1)
HEIGHT = 5
HERO = 'Battery of three hooped timber-stave silos with teal cone caps, fed by a closed bucket elevator and a covered gallery.'
FRAME_END = 121

HALL = (0.0, 1.0, 3.0, 3.0)
DOOR_X = 2.5
SILO_X = (.5, 1.5, 2.5)     # footings (r + .11) clear each other by .06
SILO_Y = 3.5
SILO_R = .36
SILO_BASE, SILO_H, SILO_CONE = .55, 2.25, .4
ELEV = (3.5, 3.5)           # elevator leg centre, over its 1x1 boot house
BOOT_TOP = .8
HEAD_Z = (3.4, 3.95)        # head house walls
GALLERY = (.15, 3.08, 3.3, 3.7, 3.36, 3.62)   # x0, x1, y0, y1, z0, z1
DRIER = (3.45, 1.85, 3.0, .64, .3)            # x centre, y0, y1, z centre, radius
FIREBOX = (3.04, 1.04, 3.74, 1.78, 1.32)      # x0, y0, x1, y1, top


def hall(g):
    x0, y0, x1, y1 = HALL
    Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, door=DOOR_X, door_id='Door0',
                   roof_mat=PLANK, slab_mat=WOOD, ground_mat=GREYPLANK, roof_boards=True,
                   ground_windows={'front': [(.85, .6, 'factory')],
                                   'left': [(2.0, .6, 'factory')]},
                   windows={'front': [(x + .5, 1.5, .55, 'grand') for x in range(3)],
                            'left': [(1.5, 1.5, .55, 'grand'), (2.5, 1.5, .55, 'grand')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    # (No ventilators on the roof: every flat roof cell is a placeable area.)


def silos(g):
    for x in SILO_X:
        Q.stave_silo(g, x, SILO_Y, 0, SILO_R, SILO_H, base_h=SILO_BASE, cone=SILO_CONE, hoops=3)
        K.band(g, (x, SILO_Y, 0), SILO_R + .07, SILO_BASE - .1, .1, IRON, segments=12, proud=.04,
               phase=math.pi / 12)


def elevator(g, parts):
    cx, cy = ELEV
    # Boot house on the back-right tile; the drier discharges into its front.
    Q.timber_podium(g, 3.06, 3.06, 4.0, 4.0, BOOT_TOP)
    # Closed boarded leg; the up-leg runs in an open slot on its front.
    lx0, lx1, ly0, ly1 = cx - .32, cx + .32, cy - .26, cy + .3
    blk(g, lx0, ly0 + .12, BOOT_TOP - .02, lx1, ly1, HEAD_Z[0], PLANK)
    for k in range(3):
        z = 1.3 + k * .75
        blk(g, lx0 - .03, ly0 + .09, z, lx1 + .03, ly1 + .03, z + .07, IRON)
    for x in (lx0 + .03, lx1 - .03):
        blk(g, x - .03, ly0, BOOT_TOP, x + .03, ly0 + .12, HEAD_Z[0], IRON)
    blk(g, lx0 + .06, ly0 + .02, BOOT_TOP, lx1 - .06, ly0 + .06, HEAD_Z[0], IRON)
    chain = Geometry('BucketChain', (cx, ly0 + .09, 2.1))
    pitch = .4
    for k in range(-1, 7):
        z = BOOT_TOP + .1 + k * pitch
        blk(chain, cx - .12, ly0 + .065, z, cx + .12, ly0 + .12, z + .11, PAINTED)
        blk(chain, cx - .1, ly0 + .045, z + .08, cx + .1, ly0 + .07, z + .12, IRON)
    parts.append((chain, 'CUSTOM_LOOP_Z', pitch))
    # Head house with a hipped cap.
    hx0, hy0, hx1, hy1 = cx - .44, cy - .44, cx + .44, cy + .44
    z0, z1 = HEAD_Z
    P.framed_block(g, hx0, hy0, hx1, hy1, z0, z1, infill=FORGED, frame=IRON, pitch=.6, sink=.0,
                   windows={'right': [(cy, z1 - .27, .38, 'factory')]})
    blk(g, hx0 - .04, hy0 - .04, z0 - .1, hx1 + .04, hy1 + .04, z0, IRON)
    P.hip_roof(g, hx0, hy0, hx1, hy1, z1, .3, overhang=.1)
    K.beacon(g, cx, cy, z1 + .3)
    parts.append((K.beacon_shutter(cx, cy, z1 + .44, 'ElevatorBeacon'), 'SPIN_Z', 2))
    # Head pulley drive on the front of the head house.
    wheel = Geometry('HeadPulley', (cx - .2, hy0 - .12, z0 + .3))
    K.wheel(wheel, (cx - .2, hy0 - .12, z0 + .3), .17, 'Y')
    parts.append((wheel, 'SPIN_Y', 1))
    blk(g, cx - .24, hy0 - .06, z0 + .26, cx - .16, hy0, z0 + .34, IRON)
    blk(g, cx + .06, hy0 - .14, z0 + .06, cx + .34, hy0, z0 + .28, PAINTED)
    K.ladder(g, lx1, cy + .05, BOOT_TOP, z0 - .1, face='right', width=.26, cage=False)


def gallery(g):
    x0, x1, y0, y1, z0, z1 = GALLERY
    blk(g, x0, y0, z0, x1, y1, z1, FORGED)
    for y, s in ((y0, -1), (y1, 1)):
        for za, zb in ((z0 - .01, z0 + .07), (z1 - .07, z1 + .01)):
            blk(g, x0 + .03, min(y, y + s * .04), za, x1 - .03, max(y, y + s * .04), zb, IRON)
        for k in range(5):
            x = x0 + .25 + k * (x1 - x0 - .5) / 4
            blk(g, x - .035, min(y, y + s * .035), z0 + .07, x + .035, max(y, y + s * .035), z1 - .07, IRON)
    # Flat steel roof slab.
    blk(g, x0 - .05, y0 - .05, z1, x1, y1 + .05, z1 + .06, IRON)
    top = SILO_BASE + SILO_H + SILO_CONE
    for x in SILO_X:
        g.cylinder((x, SILO_Y, (top - .08 + z0) / 2), .07, z0 - (top - .08) + .02, IRON, 'Z', 12)
        g.ring((x, SILO_Y, z0 - .06), .1, .035, .04, BRASS, 'Z', 12)


def drier(g, parts):
    cx, ya, yb, cz, r = DRIER
    # Timber drier bed under the right column's front two tiles.
    P.podium(g, 3.0, 1.0, 4.0, 3.0, .2, mat=WOOD, joints=False, foot=False)
    # Timber-crib trunnion piers with rollers under the riding rings.
    for y in (2.15, 2.72):
        blk(g, cx - .32, y - .13, .15, cx + .32, y + .13, .26, PLANK)
        blk(g, cx - .35, y - .16, .26, cx + .35, y + .16, .3, IRON)
        for s in (-1, 1):
            g.cylinder((cx + s * .26, y, .36), .07, .14, IRON, 'Y', 12)
    # Pinion and motor on the right driving the girth gear.
    blk(g, 3.8, 2.33, .15, 3.95, 2.6, .42, PLANK)
    blk(g, 3.8, 2.36, .42, 3.95, 2.57, .6, PAINTED)
    # Firebox and stack at the feed end (front).
    x0, y0, x1, y1, top = FIREBOX
    P.podium(g, x0, y0, x1, y1, top, mat=FORGED, joints=False, foot=False, base=.18)
    blk(g, x0 + .1, y0 - .03, .45, x1 - .1, y0, .85, IRON)       # fire door
    K.stack(g, (x0 + x1) / 2, (y0 + y1) / 2, top, 1.7, emits='smoke', r=.14)
    # Draught fan housing on the firebox's right side with a spinning impeller.
    fy, fz = (y0 + y1) / 2, .78
    g.cylinder((x1 + .07, fy, fz), .22, .14, IRON, 'X', 12)
    g.ring((x1 + .15, fy, fz), .23, .04, .04, BRASS, 'X', 12)
    fan = K.fan('DraughtFan', x1 + .17, fy, fz, .19, axis='X', blades=6)
    parts.append((fan, 'SPIN_X', 3))
    # Discharge hood at the boot-house end (no vapour stack: no roof stacks).
    blk(g, cx - .32, 2.92, .15, cx + .32, 3.0, 1.15, FORGED)
    blk(g, cx - .35, 2.88, .62, cx + .35, 3.0, .66, IRON)
    # Rotating drum: riveted shell, riding rings, girth gear, strakes.
    drum = Geometry('DrierDrum', (cx, (ya + yb) / 2, cz))
    drum.cylinder((cx, (ya + yb) / 2, cz), r, yb - ya - .1, IRON, 'Y', 12)
    for y in (2.15, 2.72):
        drum.ring((cx, y, cz), .37, .08, .11, PAINTED, 'Y', 12)
        drum.cylinder((cx, y, cz), .305, .1, IRON, 'Y', 12)
    drum.ring((cx, 2.44, cz), .38, .09, .09, BRASS, 'Y', 12)
    for i in range(12):
        a = i * 2 * math.pi / 12
        drum.box((cx + math.cos(a) * .4, 2.44, cz + math.sin(a) * .4), (.035, .07, .035), IRON)
    for i in range(6):
        a = i * math.pi / 3 + .2
        for ys, ye in ((ya + .06, 2.07), (2.23, 2.37), (2.51, 2.64), (2.8, yb - .1)):
            p0 = (cx + math.cos(a) * (r + .012), ys, cz + math.sin(a) * (r + .012))
            p1 = (cx + math.cos(a) * (r + .012), ye, cz + math.sin(a) * (r + .012))
            drum.beam(p0, p1, .045, .022, PAINTED)
    parts.append((drum, 'SPIN_Y', .5))
    # Feed throat from the firebox into the drum mouth.
    g.cylinder((cx, y1 + .03, cz), .2, .08, FORGED, 'Y', 12)


def build(g, parts):
    hall(g)
    silos(g)
    elevator(g, parts)
    gallery(g)
    drier(g, parts)
