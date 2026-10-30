"""ElectrolysisPlant: splits water into hydrogen and oxygen (5 workers, 6000 hp).

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings", "no clutter on buildable space"): 12x9x12 -> 8x5x6, inside the old
footprint with the same origin. The door moved from the old yard (entrance
cell 6, 3) to the front edge on the same tile column (entrance cell 6, -1),
where a placed plant's access path entered the old footprint; the map sites'
door approach stays where it was. Removed: the bus-bar gantry's
steel portal frames, the open cell gallery, the scrubber drums, the
guide frames' diagonal bracing, their third girt and the monitor roof's
pitched slopes. The holders keep their round guide columns with two girt
rings; the cell hall is one solid two-storey block (one layer per storey).

HERO: twin telescoping gas holders in round steel guide frames - a two-lift
      hydrogen holder and a smaller single-lift oxygen holder (2:1, as the
      cells make them) - whose riveted bells slowly rise and fall.
ROOF: flat concrete roof with a low curb on the cell hall, carrying a
      flat-capped glazed clerestory lantern with the hydrogen vents.

Plan (8 x 5 tiles): the cell hall front-right with the door; the transformer
pad behind it feeding brass bus bars into the hall's back wall; the water
intake channel with its pump between pad and holders; the hydrogen holder
front-left and the oxygen holder behind it.

Animated (7, names unchanged): two transformer fans, pump flywheel,
hydrogen lift, hydrogen bell, oxygen bell, beacon.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, CYAN
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
import compact_industry_parts as Q

IDENT = 'ElectrolysisPlant'
FOOTPRINT = (8, 5)
HEIGHT = 6
FRAME_END = 121
HERO = ('Twin telescoping gas holders in round steel guide frames: a two-lift hydrogen holder and a '
        'smaller oxygen holder whose riveted bells slowly rise and fall.')

HALL = (4.0, 0.0, 8.0, 3.0)     # two storeys on whole tiles
DOOR_X = 6.5                    # entrance cell (6, -1): the old access path's tile column
H2 = (2.35, 1.5, 1.0)           # centre and bell-tank radius
O2 = (1.15, 4.0, .7)
TRANSFORMERS = ((5.0, 4.0), (7.0, 4.0))
INTAKE = (3.0, 3.0, 4.0, 5.0)   # one tile wide, open to the back edge


# ---------------------------------------------------------------- cell hall

def hall(g):
    x0, y0, x1, y1 = HALL
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=IRON, door=DOOR_X, door_id='Entrance',
                         ground_windows={'front': [(7.5, .55, 'factory'), (5.25, .55, 'factory'), (4.5, .55, 'factory')],
                                         'right': [(1.5, .6, 'factory')]},
                         windows={'front': [(x + .5, 1.5, .58, 'factory') for x in range(4, 8)],
                                  'right': [(y + .5, 1.5, .58, 'factory') for y in range(3)],
                                  'left': [(y + .5, 1.5, .58, 'factory') for y in (0, 2)],
                                  'back': [(7.5, 1.5, .58, 'factory'), (4.5, 1.5, .58, 'factory')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    K.lamp(g, DOOR_X + .66, y0 - .01, .8, face='front')
    # Flat-capped glazed clerestory lantern on the roof, with hydrogen vents.
    lx0, ly0, lx1, ly1 = 4.45, .95, 7.55, 2.05
    lz = top + .55
    C.framed_block(g, lx0, ly0, lx1, ly1, top, lz, infill=FORGED, frame=IRON, pitch=.78,
                   faces=('front', 'back'), sink=.02,
                   windows={'front': [(lx0 + .39 + k * .775, top + .28, .38, 'factory') for k in range(4)],
                            'back': [(lx0 + .39 + k * .775, top + .28, .38, 'factory') for k in range(4)]})
    blk(g, lx0 - .08, ly0 - .08, lz - .02, lx1 + .08, ly1 + .08, lz + .08, CONCRETE)
    for x in (6.8, 5.2):
        g.cylinder((x, 1.5, lz + .35), .07, .55, IRON, 'Z', 12)
        K.revolve(g, (x, 1.5, lz + .62), [(.13, 0), (.13, .05), (.04, .16), (0, .18)], IRON, segments=12)
    # Bus-bar wall bushings on the back wall where the DC feed enters.
    blk(g, 4.6, y1 + .01, 1.5, 7.4, y1 + .07, 1.8, PAINTED)


# ---------------------------------------------------------------- transformers

def transformer(g, parts, x, y, idx, top):
    # Tank with corrugated cooling fins on both sides.
    blk(g, x - .45, y - .35, top, x + .45, y + .35, top + 1.0, PAINTED)
    blk(g, x - .49, y - .39, top + 1.0, x + .49, y + .39, top + 1.05, IRON)
    for side in (-1, 1):
        for k in range(5):
            xx = x - .32 + k * .16
            blk(g, xx - .025, y + side * .35 - (.07 if side < 0 else 0), top + .12,
                xx + .025, y + side * .35 + (.07 if side > 0 else 0), top + .9, IRON)
    # Radiator bank and its fan (facing back).
    blk(g, x + .45, y - .28, top + .05, x + .72, y + .28, top + .9, IRON)
    for k in range(4):
        yy = y - .21 + k * .14
        blk(g, x + .44, yy - .015, top + .1, x + .74, yy + .015, top + .85, FORGED)
    fy = y + .4   # its hoop clears the tank's back face (y + .35) and the fins (x <= .345)
    fan = Geometry(f'ElectrolysisPlant.TransformerFan{idx}', (x + .585, fy, top + .48))
    P.lathe(fan, (x + .585, fy, top + .48), [(.04, -.025), (.04, .025)], IRON, axis='Y', segments=10)
    for k in range(4):
        a = k * math.pi / 2 + .3
        fan.beam((x + .585, fy, top + .48), (x + .585 + math.cos(a) * .17, fy, top + .48 + math.sin(a) * .17),
                 .06, .012, IRON)
    parts.append((fan, 'SPIN_Y', 4))
    P.hoop(g, (x + .585, fy, top + .48), .2, .025, .04, PAINTED, axis='Y', segments=12)
    # Conservator drum on brackets.
    zc = top + 1.32
    for dx in (-.28, .28):
        blk(g, x + dx - .03, y - .23 - .03, top + 1.05, x + dx + .03, y - .23 + .03, top + 1.22, IRON)
    P.lathe(g, (x, y - .23, zc), [(0, -.42), (.1, -.4), (.12, -.35), (.12, .35), (.1, .4), (0, .42)],
            PAINTED, axis='X', segments=12)
    # High-voltage bushings, and the two low-voltage (bus) bushings forward.
    for dx in (-.25, 0, .25):
        P.insulator(g, x + dx, y + .15, top + 1.05, height=.45, r=.07, discs=3)
    for dx in (-.09, .09):
        P.insulator(g, x + dx, y - .1, top + 1.05, height=.25, r=.05, discs=2)
    P.gauge(g, x - .22, y + .35, top + .7, 'back', .06)
    # Bus bars: up from the low-voltage bushings and forward into the hall's back wall.
    for dx in (-.09, .09):
        bz = top + 1.35 + (.06 if dx > 0 else 0)
        blk(g, x + dx - .03, y - .13, top + 1.28, x + dx + .03, y - .07, bz + .05, BRASS)   # tops clear of the bar's
        blk(g, x + dx - .025, HALL[3] + .04, bz - .03, x + dx + .025, y - .1, bz + .03, BRASS)   # ends inside the riser


def transformer_pad(g, parts):
    top = .3
    C.podium(g, 4.0, 3.0, 8.0, 5.0, top, joints=False, foot=False)   # the hall's foot course meets it
    for i, (x, y) in enumerate(TRANSFORMERS):
        transformer(g, parts, x, y, i + 1, top)


# ---------------------------------------------------------------- water intake

def intake(g, parts):
    x0, y0, x1, y1 = INTAKE
    w = .16
    # Concrete channel: floor, side walls and head wall, open to the back edge.
    blk(g, x0 + w, y0 + .22, .0, x1 - w, y1 - .02, .2, CONCRETE)
    for xa, xb in ((x0, x0 + w), (x1 - w, x1)):
        blk(g, xa, y0, 0, xb, y1, .8, CONCRETE)
        blk(g, xa - .04, y0 - .02, .8, xb + .04, y1, .86, CONCRETE)
    blk(g, x0 + w, y0, 0, x1 - w, y0 + .22, .8, CONCRETE)
    blk(g, x0 + w + .04, y0 - .02, .8, x1 - w - .04, y0 + .26, .86, CONCRETE)   # between the side copings
    g.liquid_surfaces.append(dict(name='IntakeChannel', shape='Rectangle',
                                  center=[(x0 + x1) / 2, (y0 + .22 + y1) / 2], bottom=.2, top=.62,
                                  scale=[x1 - x0 - 2 * w, y1 - y0 - .22], flowOnly=False))
    # Trash screen across the mouth.
    for k in range(4):
        x = x0 + w + .1 + k * (x1 - x0 - 2 * w - .2) / 3
        blk(g, x - .015, y1 - .4, .25, x + .015, y1 - .35, .9, IRON)
    blk(g, x0 + w, y1 - .41, .9, x1 - w, y1 - .34, .96, IRON)
    # Pump on a steel bridge over the channel, with a flywheel.
    cx, yb = (x0 + x1) / 2, 4.1
    blk(g, x0 - .04, yb - .3, .86, x1 + .04, yb + .3, .94, IRON)
    blk(g, cx - .2, yb - .17, .94, cx + .2, yb + .17, 1.3, PAINTED)
    P.motor(g, (cx + .3, yb, 1.15), .13, .3, axis='X')
    P.pipe(g, [(cx, yb, .86), (cx, yb, .35)], .07, flanges=False)
    fw = P.flywheel('ElectrolysisPlant.PumpFlywheel', (cx - .3, yb, 1.22), .26, axis='X', spokes=6)
    parts.append((fw, 'SPIN_X', 2))
    blk(g, cx - .27, yb - .04, 1.18, cx - .2, yb + .04, 1.26, IRON)
    # Discharge to the hall's left wall, past the hydrogen holder.
    P.pipe(g, [(cx, yb - .12, 1.3), (cx, yb - .12, 1.5), (cx, 2.6, 1.5), (HALL[0], 2.6, 1.5)], .065)
    P.valve(g, (cx, 3.2, 1.5), 'up', .1)


# ---------------------------------------------------------------- gas holders

def guide_frame(g, cx, cy, r, top, columns=8, phase=0.0):
    """Round guide frame: columns on piers and two girt rings (no bracing)."""
    pts = [(cx + math.cos(phase + k * 2 * math.pi / columns) * r, cy + math.sin(phase + k * 2 * math.pi / columns) * r)
           for k in range(columns)]
    for x, y in pts:
        P.pier(g, x, y, 0, .25, .26)
        blk(g, x - .065, y - .065, .3, x + .065, y + .065, top, IRON)
        blk(g, x - .095, y - .095, top, x + .095, y + .095, top + .08, PAINTED)
    for z in ((top + .3) / 2, top - .1):
        for (ax, ay), (bx, by) in zip(pts, pts[1:] + pts[:1]):
            d = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / d, (by - ay) / d
            g.beam((ax + ux * .07, ay + uy * .07, z), (bx - ux * .07, by - uy * .07, z), .1, .13, mat=IRON)
    return pts


def holder_tank(g, cx, cy, R, height):
    """Concrete water tank with coping and pilasters; open top."""
    K.hollow_revolve(g, (cx, cy, 0), [(R + .2, 0), (R + .2, height)], .2, CONCRETE, segments=16)
    K.hollow_revolve(g, (cx, cy, 0), [(R + .25, height - .1), (R + .25, height + .02)], .28, CONCRETE, segments=16)
    for k in range(8):
        a = k * 2 * math.pi / 8
        x, y = cx + math.cos(a) * (R + .215), cy + math.sin(a) * (R + .215)
        P.tube(g, (x, y, .12), (x, y, height - .12), .045, CONCRETE, segments=6)


def bell(name, cx, cy, r, z0, h, *, crown=.25, rollers=8, guide_r=None, phase=0.0):
    """Riveted telescoping bell (closed crown) as an animated part."""
    b = Geometry(name, (cx, cy, z0))
    K.hollow_revolve(b, (cx, cy, 0), [(r, z0), (r, z0 + h)], .05, IRON, segments=16)
    K.dome(b, (cx, cy, z0 + h), r + .02, IRON, segments=16, rings=3, squash=crown / r)
    for k in range(2):
        K.band(b, (cx, cy, 0), r, z0 + .25 + (h - .5) * k, .07, PAINTED, segments=16)
    rr = r * .8
    zr = z0 + h + crown * math.sqrt(max(0, 1 - (rr / (r + .02)) ** 2)) - .02
    P.ring_rail(b, (cx, cy), rr, zr, height=.42, posts=10)
    b.cylinder((cx, cy, z0 + h + crown + .07), .11, .18, IRON, 'Z', 12)
    P.hoop(b, (cx, cy, z0 + h + crown + .17), .16, .05, .04, BRASS)
    if guide_r:
        for k in range(rollers):
            a = phase + k * 2 * math.pi / rollers
            ux, uy = math.cos(a), math.sin(a)
            P.tube(b, (cx + ux * (r - .02), cy + uy * (r - .02), z0 + h - .15),
                   (cx + ux * (guide_r - .12), cy + uy * (guide_r - .12), z0 + h - .15), .04, IRON, segments=8)
            b.box((cx + ux * (guide_r - .12), cy + uy * (guide_r - .12), z0 + h - .15), (.09, .09, .14), PAINTED)
    return b


def lift(name, cx, cy, r, z0, h, *, guide_r=None, rollers=8, phase=0.0):
    """Intermediate open lift with a cup ring, as an animated part."""
    b = Geometry(name, (cx, cy, z0))
    K.hollow_revolve(b, (cx, cy, 0), [(r, z0), (r, z0 + h)], .05, IRON, segments=16)
    K.hollow_revolve(b, (cx, cy, 0), [(r + .06, z0 + h - .12), (r + .06, z0 + h + .02)], .12, PAINTED, segments=16)
    if guide_r:
        for k in range(rollers):
            a = phase + k * 2 * math.pi / rollers
            ux, uy = math.cos(a), math.sin(a)
            P.tube(b, (cx + ux * (r + .04), cy + uy * (r + .04), z0 + h - .05),
                   (cx + ux * (guide_r - .12), cy + uy * (guide_r - .12), z0 + h - .05), .035, IRON, segments=8)
            b.box((cx + ux * (guide_r - .12), cy + uy * (guide_r - .12), z0 + h - .05), (.09, .09, .12), PAINTED)
    return b


def holders(g, parts):
    # Hydrogen: two lifts.
    cx, cy, R = H2
    holder_tank(g, cx, cy, R, 1.2)
    gr = R + .32
    ph = math.pi / 8
    pts = guide_frame(g, cx, cy, gr, 4.6, columns=8, phase=ph)
    parts.append((lift('ElectrolysisPlant.HydrogenLift', cx, cy, R - .1, .4, 1.4, guide_r=gr, phase=ph),
                  'SLIDE_Z', .5))
    parts.append((bell('ElectrolysisPlant.HydrogenBell', cx, cy, R - .25, 1.6, 1.4, guide_r=gr, phase=ph),
                  'SLIDE_Z', 1.0))
    # Ladder up the front-left guide column; beacon on a mast on its cap.
    lx, ly = pts[4]
    K.ladder(g, lx, ly - .065, 0, 4.6, face='front', width=.3, cage=False)
    mx, my = pts[3]
    blk(g, mx - .03, my - .03, 4.68, mx + .03, my + .03, 5.0, IRON)
    pivot = K.beacon(g, mx, my, 5.0)
    parts.append((K.beacon_shutter(*pivot, 'ElectrolysisPlant.Beacon'), 'SPIN_Z', 2))
    # Oxygen: single lift.
    ox, oy, r2 = O2
    holder_tank(g, ox, oy, r2, 1.0)
    gr2 = r2 + .28
    guide_frame(g, ox, oy, gr2, 3.2, columns=6)
    parts.append((bell('ElectrolysisPlant.OxygenBell', ox, oy, r2 - .12, .3, 1.6, guide_r=gr2, rollers=6),
                  'SLIDE_Z', .8))
    # Gas mains from the hall: hydrogen straight into its tank, oxygen round
    # the intake to enter low down.
    P.pipe(g, [(HALL[0], cy, .6), (cx + R + .18, cy, .6)], .08, flanges=False)
    P.valve(g, (3.78, cy, .6), 'up', .1)
    ey = oy - .35
    ex = ox + math.sqrt((r2 + .2) ** 2 - .35 ** 2) - .03
    P.pipe(g, [(HALL[0], 2.9, 1.75), (2.7, 2.9, 1.75), (2.7, ey, 1.75), (2.7, ey, .6), (ex, ey, .6)], .06,
           mat=PAINTED, flanges=False)


def build(g, parts):
    hall(g)
    transformer_pad(g, parts)
    intake(g, parts)
    holders(g, parts)
