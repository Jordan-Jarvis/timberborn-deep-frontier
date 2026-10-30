"""PrecisionMachineWorks: precision parts and components (6 workers, 2200 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose yard stock and barrels.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings"): 11x9x14 -> 9x5x7, inside the old
footprint with the same origin, door and native entrance (cell 8, -1).
Removed: the crane yard's six steel columns and knee braces, the braced
steel frame under the air receiver, the separate forge lean-to and the
13-layer chimney. The travelling crane now runs on a solid concrete runway
wall and a bracket beam on the shop wall; the square brick chimney is six
layers on its firebox.

HERO: a long north-light sawtooth machine hall with an open belt bay, a
      travelling crane over its yard and a square brick chimney bound with
      iron bands.
ROOF: the north-light sawtooth (three teal plank teeth with glazed north
      faces) stays: it is this building's defining silhouette and the only
      sawtooth among the late-game works. Flat concrete roof with a low curb
      on the two-storey gate office.

Plan (9 x 5 tiles): the machine shop on the left with the belt bay in its
front wall (line shaft, belts, three lathes); the gate office front-right
with the door, the compressed-air receiver on its roof; the crane yard
behind it with the steam hammer, the roll lathe and the chimney.

Animated (7, names unchanged): line shaft, three lathe chucks, crane bridge
(slides along Y), steam-hammer ram, yard lathe roll.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYPLANK, GLOW
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
import compact_industry_parts as Q
from architectural_windows import window

IDENT = 'PrecisionMachineWorks'
FOOTPRINT = (9, 5)
HEIGHT = 7
FRAME_END = 121
HERO = ('Long north-light sawtooth machine hall with an open belt bay and a travelling crane over its yard, '
        'with a square brick chimney bound in iron.')

SHOP = (0.0, 0.0, 6.0, 5.0)    # whole tiles
SHOP_EAVE = 2.0
BAY = (1.0, 5.0, .9, .95)      # open belt bay: x0, x1, head height, depth
OFFICE = (6.0, 0.0, 9.0, 2.0)  # gate office on whole tiles; door face on y = 0
DOOR_X = 8.5
RUNWAY_Z = 2.2                 # crane rail top
CRANE_Y = 2.55                 # crane bridge at frame 1; slides back by CRANE_TRAVEL
CRANE_TRAVEL = 1.0


# ---------------------------------------------------------------- machine shop

def sawtooth(g, x0, y0, x1, y1, base, teeth=3, rise=.8):
    d = (y1 - y0) / teeth
    for i in range(teeth):
        ya, yb = y0 + i * d, y0 + (i + 1) * d
        last = i == teeth - 1
        wall_back = y1 + .07 if last else yb   # clear of the back wall's posts (.055 proud)
        wall_front = y1 - .05 if last else yb - .06
        wc = (wall_back + wall_front) / 2
        P.plank_slope(g, 'X', ya - (0 if i == 0 else .03), wc, base, base + rise, x0, x1,
                      overhang=.2 if i == 0 else .0, end_overhang=.0, plank=.3, fascia=i == 0)
        # Glazed north-light face.
        g.box(((x0 + x1) / 2, wc, base + rise / 2 + .01), (x1 - x0 + .06, wall_back - wall_front, rise + .06), FORGED)
        for k in range(5):
            x = x0 + .6 + k * (x1 - x0 - 1.2) / 4
            window(g, x, wall_back, base + rise / 2 + .02, .62, 'back', 'factory')
        g.box(((x0 + x1) / 2, wc, base + rise + .12), (x1 - x0 + .3, .14, .06), IRON)
        for plane, out in ((x0, -1), (x1, 1)):
            prof = [(ya + (.0 if i == 0 else -.02), base - .01), (wall_front, base - .01),
                    (wall_front, base + rise * (wall_front - ya) / (wc - ya + 1e-9) - .07)]
            P.end_prism(g, 'X', plane, out, prof, ORANGE)


def shop(g, parts):
    x0, y0, x1, y1 = SHOP
    bx0, bx1, bz, bd = BAY
    # Concrete ground storey around the open belt bay, one coping ring over
    # all of it (the coping is the bay head), one foot course.
    blk(g, x0, y0, 0, bx0, y1, .97, CONCRETE)
    blk(g, bx1, y0, 0, x1, y1, .97, CONCRETE)
    blk(g, bx0, y0 + bd, 0, bx1, y1, .97, CONCRETE)
    # The office's own foot and coping take over along x = 6 in front of y = 2.
    oy = OFFICE[3]
    blk(g, x0 - .03, y0 - .03, -.03, x1 - .03, y1 + .03, .14, CONCRETE)
    blk(g, x1 - .03, oy + .03, -.03, x1 + .03, y1 + .03, .14, CONCRETE)
    blk(g, x0 - .05, y0 - .05, bz, x1 - .05, y1 + .05, 1.0, CONCRETE)
    blk(g, x1 - .05, oy + .05, bz, x1 + .05, y1 + .05, 1.0, CONCRETE)
    for x in (.5,):
        C.native_window(g, x, y0, .52, .55, 'front', 'factory')
    for y in (1.5, 3.5):
        C.native_window(g, x0, y, .52, .6, 'left', 'factory')
    for x in (1.5, 3.0, 4.5):
        C.native_window(g, x, y1, .52, .6, 'back', 'factory')
    C.native_window(g, x1, 3.5, .52, .6, 'right', 'factory')
    # Framed upper storey (one layer) under the sawtooth.
    # The right face stands .14 in from x = 6 so its corner posts clear the
    # gate office's (whose core starts at 6.05).
    C.framed_block(g, x0 + .05, y0 + .05, x1 - .14, y1 - .05, 1.0, SHOP_EAVE + .03, infill=FORGED, frame=IRON,
                   windows={'front': [(x + .5, 1.5, .55, 'factory') for x in range(6)],
                            'left': [(y + .5, 1.5, .55, 'factory') for y in range(5)],
                            'back': [(x + .5, 1.5, .55, 'factory') for x in range(6)],
                            'right': [(y + .5, 1.5, .55, 'factory') for y in (2, 3, 4)]})
    sawtooth(g, x0 + .05, y0 + .05, x1 - .14, y1 - .05, SHOP_EAVE, teeth=3, rise=.8)
    belt_bay(g, parts)


def belt_bay(g, parts):
    bx0, bx1, bz, bd = BAY
    floor = .14
    back = bd
    # Bay lining: steel back plate, timber posts, plank side cheeks.
    blk(g, bx0 + .02, back - .03, floor, bx1 - .02, back, bz - .02, IRON)
    for x in (bx0 + .03, bx1 - .03):
        blk(g, x - .03, 0, floor, x + .03, back - .03, bz - .02, GREYPLANK)
    # Line shaft with pulleys (one spinning part) on hangers from the head.
    sy, sz = .62, .74
    for x in (bx0 + .35, (bx0 + bx1) / 2, bx1 - .35):
        blk(g, x - .025, sy - .025, sz + .05, x + .025, sy + .025, bz, IRON)
        blk(g, x - .05, sy - .06, sz - .05, x + .05, sy + .06, sz + .05, PAINTED)
    shaft = Geometry('PrecisionMachineWorks.LineShaft', ((bx0 + bx1) / 2, sy, sz))
    P.tube(shaft, (bx0 + .1, sy, sz), (bx1 - .1, sy, sz), .03, IRON, segments=10)
    lathes = (1.85, 2.85, 3.85)
    for x in lathes:
        P.pulley(shaft, (x - .4, sy, sz), .11, .08, 'X', PAINTED)
    P.pulley(shaft, (4.55, sy, sz), .16, .1, 'X', IRON)
    parts.append((shaft, 'SPIN_X', 2))
    # Drive motor at the right end, belted up to the big pulley.
    blk(g, 4.35, .45, floor, 4.75, .8, floor + .14, CONCRETE)
    P.motor(g, (4.55, .62, floor + .3), .12, .3, axis='X')
    for dy in (-.1, .1):
        g.beam((4.55, .62 + dy * .5, floor + .3), (4.55, sy + dy, sz), .07, .015, WOOD)
    # Three lathes with spinning chucks, belted up to the shaft.
    for i, x in enumerate(lathes):
        ly, lz = .42, floor + .42
        for dx in (-.3, .3):
            blk(g, x + dx - .05, ly - .09, floor, x + dx + .05, ly + .09, floor + .3, IRON)
        blk(g, x - .38, ly - .08, floor + .3, x + .38, ly + .08, floor + .36, IRON)
        blk(g, x - .4, ly - .09, floor + .36, x - .2, ly + .09, floor + .55, PAINTED)
        blk(g, x + .2, ly - .06, floor + .36, x + .3, ly + .06, floor + .48, IRON)
        c = Geometry(f'PrecisionMachineWorks.Chuck{i + 1}', (x - .14, ly, lz))
        P.lathe(c, (x - .14, ly, lz), [(.07, -.03), (.07, .03)], IRON, axis='X', segments=12)
        for k in range(3):
            a = k * 2 * math.pi / 3
            c.box((x - .14, ly + math.cos(a) * .06, lz + math.sin(a) * .06), (.07, .035, .035), BRASS)
        P.tube(c, (x - .11, ly, lz), (x + .05, ly, lz), .03, CONCRETE, segments=8)
        P.pulley(c, (x - .4, ly, lz + .05), .07, .05, 'X', PAINTED)
        parts.append((c, 'SPIN_X', 6))
        for dy in (-1, 1):
            g.beam((x - .4, ly + dy * .06, lz + .05), (x - .4, sy + dy * .1, sz), .05, .015, WOOD)
    for x in (1.35, 3.35):
        K.lamp(g, x, back - .03, .62, face='front')


# ---------------------------------------------------------------- gate office

def gate_office(g, parts):
    """Two-storey works office at the gate; the compressed-air receiver for
    the shop's pneumatic tools lies on saddles on its flat roof."""
    x0, y0, x1, y1 = OFFICE
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, door=DOOR_X, door_id='Entrance',
                         ground_windows={'front': [(6.75, .55, 'grand')], 'right': [(1.0, .55, 'grand')]},
                         windows={'front': [(6.5, 1.5, .52, 'grand'), (7.5, 1.5, .52, 'grand'),
                                            (8.5, 1.5, .52, 'grand')],
                                  'right': [(.5, 1.5, .52, 'grand'), (1.5, 1.5, .52, 'grand')],
                                  'back': [(7.5, 1.5, .52, 'grand')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    # Riveted air receiver along X on two concrete saddles, kept to the back
    # row of the roof so its front row stays open (platformable).
    ty, tz, tr = 1.55, top + .42, .26
    for x in (6.95, 8.05):
        blk(g, x - .1, ty - .2, top, x + .1, ty + .2, tz - .15, CONCRETE)
    P.lathe(g, (7.5, ty, tz), [(0, -.85), (.18, -.83), (.23, -.77), (tr, -.66), (tr, .66), (.23, .77),
                               (.18, .83), (0, .85)], PAINTED, axis='X', segments=16)
    for x in (7.0, 7.5, 8.0):
        P.hoop(g, (x, ty, tz), tr + .02, .03, .045, IRON, axis='X', segments=16)
    g.cylinder((7.25, ty, tz + tr + .045), .07, .09, IRON, 'Z', 12)
    g.cylinder((7.25, ty, tz + tr + .1), .1, .03, BRASS, 'Z', 12)
    g.cylinder((7.8, ty, tz + tr + .07), .03, .14, BRASS, 'Z', 8)
    P.gauge(g, 7.75, ty - tr - .005, tz, 'front', .06)


# ---------------------------------------------------------------- crane yard

def crane_yard(g, parts):
    # Solid concrete runway wall on tile column 8 (y 2..4), the chimney's
    # firebox behind it, and a steel runway beam on corbels along the shop's
    # right wall; low concrete yard paving under the lathe.
    xr = 8.0
    # Both start .15 behind the office so they clear its roof curb.
    C.podium(g, xr, 2.15, 9.0, 4.0, RUNWAY_Z - .1, joints=False)
    blk(g, xr - .02, 2.15, RUNWAY_Z - .1, 9.0, 4.0, RUNWAY_Z, IRON)
    blk(g, 6.0, 2.0, -.02, 8.0, 4.0, .1, CONCRETE)
    xl = 6.1   # clear of the sawtooth planks' end overhang
    for y in (2.3, 4.0):
        blk(g, 6.0, y - .08, RUNWAY_Z - .45, xl + .18, y + .08, RUNWAY_Z - .12, IRON)
    blk(g, xl, 2.15, RUNWAY_Z - .12, xl + .18, 4.0, RUNWAY_Z, PAINTED)
    # Travelling bridge with trolley and hook block (one sliding part).
    y = CRANE_Y
    bz = RUNWAY_Z
    xa, xb = xl + .1, xr + .4
    br = Geometry('PrecisionMachineWorks.CraneBridge', ((xa + xb) / 2, y, bz))
    for dy in (-.18, .18):
        br.box(((xa + xb) / 2, y + dy, bz + .2), (xb - xa - .1, .12, .3), PAINTED)
    for x in (xa + .05, xb - .05):
        br.box((x, y, bz + .08), (.2, .7, .16), IRON)
    tx = 7.3
    br.box((tx, y, bz + .43), (.5, .5, .16), IRON)
    P.lathe(br, (tx, y, bz + .57), [(.11, -.18), (.11, .18)], PAINTED, axis='X', segments=12)
    for dy in (-.05, .05):
        br.box((tx + .08, y + dy, bz - .3), (.02, .02, .64), IRON)
    br.box((tx + .08, y, bz - .66), (.16, .18, .18), PAINTED)
    P.hoop(br, (tx + .08, y, bz - .82), .08, .025, .035, IRON, axis='Y', segments=12)
    parts.append((br, 'SLIDE_Y', CRANE_TRAVEL))
    # Steam hammer at the back of the yard.
    hx, hy = 7.0, 4.5
    top = .25
    C.podium(g, 6.0, 4.0, 8.0, 5.0, top, joints=False, foot=False)
    for dx in (-.42, .42):
        blk(g, hx + dx - .1, hy - .18, top, hx + dx + .1, hy + .18, top + 1.45, PAINTED)
    blk(g, hx - .58, hy - .2, top + 1.45, hx + .58, hy + .2, top + 1.65, PAINTED)
    P.lathe(g, (hx, hy, top + 1.65), [(.2, 0), (.2, .5), (.16, .56)], IRON, segments=16)
    K.band(g, (hx, hy, 0), .2, top + 1.95, .05, BRASS, segments=16)
    blk(g, hx - .22, hy - .22, top, hx + .22, hy + .22, top + .45, IRON)
    blk(g, hx - .15, hy - .13, top + .45, hx + .15, hy + .13, top + .52, IRON)
    ram = Geometry('PrecisionMachineWorks.HammerRam', (hx, hy, top + .9))
    ram.box((hx, hy, top + .72), (.3, .26, .3), IRON)
    P.tube(ram, (hx, hy, top + .87), (hx, hy, top + 1.6), .045, IRON, segments=8)
    parts.append((ram, 'PISTON_Z', .18))
    P.pipe(g, [(hx + .2, hy, top + 2.0), (hx + .5, hy, top + 2.0), (hx + .5, hy, top + 2.5)], .04, flanges=False)
    # Big roll lathe in the yard under the crane, turning a long shaft.
    ly, lz = 2.55, .72
    for x in (6.45, 7.05, 7.7):
        blk(g, x - .1, ly - .16, .1, x + .1, ly + .16, .45, IRON)
    blk(g, 6.25, ly - .19, .45, 7.9, ly + .19, .55, IRON)
    blk(g, 6.25, ly - .24, .55, 6.7, ly + .24, 1.0, PAINTED)
    P.motor(g, (6.47, ly + .05, 1.12), .12, .34, axis='X')
    blk(g, 7.6, ly - .15, .55, 7.88, ly + .15, .85, PAINTED)
    blk(g, 7.15, ly - .22, .55, 7.45, ly - .02, .68, IRON)
    roll = Geometry('PrecisionMachineWorks.YardLatheRoll', (7.15, ly, lz))
    P.lathe(roll, (7.15, ly, lz), [(.15, -.45), (.15, -.4), (.11, -.4), (.11, .32), (.08, .32), (.08, .45)],
            IRON, axis='X', segments=16)
    for k in range(4):
        a = k * math.pi / 2
        roll.box((6.73, ly + math.cos(a) * .13, lz + math.sin(a) * .13), (.07, .05, .05), BRASS)
    parts.append((roll, 'SPIN_X', 2))
    chimney(g)


def chimney(g):
    """Square tapered brick chimney (orange plaster reads as brick) on its
    firebox in the yard's back-right corner, bound with iron bands."""
    cx, cy = 8.5, 4.5
    blk(g, 8.0, 4.0, 0, 9.0, 5.0, .9, CONCRETE)
    blk(g, 7.97, 3.97, .9, 9.03, 5.03, .98, CONCRETE)
    # Firebox door with a glowing slot, facing the yard.
    blk(g, 9.0, 4.3, .25, 9.04, 4.7, .6, IRON)
    blk(g, 9.04, 4.38, .38, 9.06, 4.62, .44, GLOW)
    base_r, top, taper = .42, 6.5, .3

    def r_at(z):
        return base_r * (1 - taper * (z - .98) / (top - .98))
    P.lathe(g, (cx, cy, 0), [(r_at(.98 + (top - .98) * k / 8), .98 + (top - .98) * k / 8) for k in range(9)],
            ORANGE, segments=4, phase=math.pi / 4, cap_start=False)
    for z in (2.0, 3.4, 4.8, 6.0):
        P.lathe(g, (cx, cy, 0), [(r_at(z) + .03, z - .05), (r_at(z) + .03, z + .05)], IRON, segments=4,
                phase=math.pi / 4)
    rt = r_at(top)
    P.lathe(g, (cx, cy, 0), [(rt + .05, top - .12), (rt + .05, top + .12)], IRON, segments=4, phase=math.pi / 4)
    g.box((cx, cy, top + .13), (rt * .9, rt * .9, .02), IRON)
    K.emitter(g, 'smoke', cx, cy, top + .14, rt * .45)


def build(g, parts):
    shop(g, parts)
    gate_office(g, parts)
    crane_yard(g, parts)
