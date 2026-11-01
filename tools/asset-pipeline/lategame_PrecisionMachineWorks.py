"""PrecisionMachineWorks: precision parts and components (6 workers, 2200 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose yard stock and barrels.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings"): 11x9x14 -> 9x5x7, inside the old
footprint with the same origin, door and native entrance (cell 8, -1).
Removed: the crane yard's six steel columns and knee braces, the braced
steel frame and the air receiver it carried, the separate forge lean-to
and the 13-layer chimney. The travelling crane now runs on a solid concrete runway
wall and a bracket beam on the shop wall; the square brick chimney is six
layers on its firebox.

Second shrink 2026-11-01 (a YouTuber called the late-game buildings
"massive"; user: "we need to shrink the buildings down even more"):
9x5x7 -> 5x4x3, inside the old footprint with the same origin. The old door
(tile 8 of the front) lies outside the new footprint, so the door moves to
tile 4 of the front: entrance (8,-1) -> (4,-1); a flipped works keeps its
entrance at (0,-1). At 5x4 the works no longer needs a reserved map site. Every new block is a block the
old works occupied: the old works was three layers high over its whole
machine shop, so the new one stays within three layers (the chimney is
three layers on its firebox, the crane runs on a thin runway wall). The
yard lathe's roll, the crane and the steam hammer share the 2x2 yard.

HERO: a north-light sawtooth machine hall with an open belt bay, a
      travelling crane over its small yard and a square brick chimney bound
      with iron bands.
ROOF: the north-light sawtooth (four teal plank teeth with glazed north
      faces) stays: it is this building's defining silhouette and the only
      sawtooth among the late-game works. Flat timber-plank roof, open edge
      to edge, on the two-storey gate office, every cell placeable.

Plan (5 x 4 tiles): the machine shop on tiles 0..3 x 0..4 with the belt bay
in its front wall (line shaft, belts, three 0.8-scale lathes); the gate
office front-right (3..5 x 0..2) with the door; the crane yard behind it
(3..5 x 2..4) with the roll lathe under the crane, the steam hammer and the
chimney.

Animated (7, names unchanged): line shaft, three lathe chucks, crane bridge
(slides along Y), steam-hammer ram, yard lathe roll.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYPLANK, GLOW, BRICK
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
import compact_industry_parts as Q
from architectural_windows import window

IDENT = 'PrecisionMachineWorks'
FOOTPRINT = (5, 4)
HEIGHT = 3
FRAME_END = 121
HERO = ('North-light sawtooth machine hall with an open belt bay and a travelling crane over its yard, '
        'with a square brick chimney bound in iron.')

SHOP = (0.0, 0.0, 3.0, 4.0)    # whole tiles
SHOP_EAVE = 2.0
BAY = (.15, 2.85, .9, .95)     # open belt bay: x0, x1, head height, depth
OFFICE = (3.0, 0.0, 5.0, 2.0)  # gate office on whole tiles; door face on y = 0
DOOR_X = 4.5
RUNWAY_Z = 2.0                 # crane rail top
CRANE_Y = 2.45                 # crane bridge at frame 1; slides back by CRANE_TRAVEL
CRANE_TRAVEL = .5
LATHE_SCALE = .8
LATHES = (1.2, 1.85, 2.5)


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
        for k in range(3):
            x = x0 + .5 + k * (x1 - x0 - 1.0) / 2
            window(g, x, wall_back, base + rise / 2 + .02, .62, 'back', 'factory')
        g.box(((x0 + x1) / 2, wc, base + rise + .12), (x1 - x0 + .3, .14, .06), IRON)
        for plane, out in ((x0, -1), (x1, 1)):
            prof = [(ya + (.0 if i == 0 else -.02), base - .01), (wall_front, base - .01),
                    (wall_front, base + rise * (wall_front - ya) / (wc - ya + 1e-9) - .07)]
            P.end_prism(g, 'X', plane, out, prof, BRICK)


def shop(g, parts):
    x0, y0, x1, y1 = SHOP
    bx0, bx1, bz, bd = BAY
    # Brick ground storey (2026-10-31; was cast concrete) around the open belt
    # bay, one concrete coping ring over all of it (the coping is the bay head),
    # one foot course.
    blk(g, x0, y0, 0, bx0, y1, .97, BRICK)
    blk(g, bx1, y0, 0, x1, y1, .97, BRICK)
    blk(g, bx0, y0 + bd, 0, bx1, y1, .97, BRICK)
    # The office's own foot and coping take over along x = 6 in front of y = 2.
    oy = OFFICE[3]
    blk(g, x0 - .03, y0 - .03, -.03, x1 - .03, y1 + .03, .14, CONCRETE)
    blk(g, x1 - .03, oy + .03, -.03, x1 + .03, y1 + .03, .14, CONCRETE)
    blk(g, x0 - .05, y0 - .05, bz, x1 - .05, y1 + .05, 1.0, CONCRETE)
    blk(g, x1 - .05, oy + .05, bz, x1 + .05, y1 + .05, 1.0, CONCRETE)
    for y in (1.5, 2.5):
        C.native_window(g, x0, y, .52, .6, 'left', 'factory')
    for x in (.5, 1.5, 2.5):
        C.native_window(g, x, y1, .52, .6, 'back', 'factory')
    # Framed upper storey (one layer) under the sawtooth.
    # The right face stands .14 in from x = 3 so its corner posts clear the
    # gate office's (whose core starts at 3.05).
    C.framed_block(g, x0 + .05, y0 + .05, x1 - .14, y1 - .05, 1.0, SHOP_EAVE + .03, infill=FORGED, frame=IRON,
                   windows={'front': [(x + .5, 1.5, .55, 'factory') for x in range(3)],
                            'left': [(y + .5, 1.5, .55, 'factory') for y in range(4)],
                            'back': [(x + .5, 1.5, .55, 'factory') for x in range(3)],
                            'right': [(y + .5, 1.5, .55, 'factory') for y in (2, 3)]})
    sawtooth(g, x0 + .05, y0 + .05, x1 - .14, y1 - .05, SHOP_EAVE, teeth=4, rise=.75)
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
    k = LATHE_SCALE
    for x in LATHES:
        P.pulley(shaft, (x - .4 * k, sy, sz), .09, .07, 'X', PAINTED)
    P.pulley(shaft, (.42, sy, sz), .14, .09, 'X', IRON)
    parts.append((shaft, 'SPIN_X', 2))
    # Drive motor at the left end, belted up to the big pulley.
    blk(g, .27, .5, floor, .57, .82, floor + .12, CONCRETE)
    P.motor(g, (.42, .66, floor + .26), .1, .26, axis='X')
    for dy in (-.08, .08):
        g.beam((.42, .66 + dy * .5, floor + .26), (.42, sy + dy, sz), .06, .015, WOOD)
    # Three lathes at LATHE_SCALE with spinning chucks, belted up to the shaft.
    for i, x in enumerate(LATHES):
        ly, lz = .42, floor + .42 * k
        for dx in (-.3 * k, .3 * k):
            blk(g, x + dx - .04, ly - .07, floor, x + dx + .04, ly + .07, floor + .3 * k, IRON)
        blk(g, x - .38 * k, ly - .065, floor + .3 * k, x + .38 * k, ly + .065, floor + .36 * k, IRON)
        blk(g, x - .4 * k, ly - .075, floor + .36 * k, x - .2 * k, ly + .075, floor + .55 * k, PAINTED)
        blk(g, x + .2 * k, ly - .05, floor + .36 * k, x + .3 * k, ly + .05, floor + .48 * k, IRON)
        c = Geometry(f'PrecisionMachineWorks.Chuck{i + 1}', (x - .14 * k, ly, lz))
        P.lathe(c, (x - .14 * k, ly, lz), [(.06, -.025), (.06, .025)], IRON, axis='X', segments=12)
        for j in range(3):
            a = j * 2 * math.pi / 3
            c.box((x - .14 * k, ly + math.cos(a) * .05, lz + math.sin(a) * .05), (.06, .03, .03), BRASS)
        P.tube(c, (x - .11 * k, ly, lz), (x + .05 * k, ly, lz), .025, CONCRETE, segments=8)
        P.pulley(c, (x - .4 * k, ly, lz + .04), .06, .045, 'X', PAINTED)
        parts.append((c, 'SPIN_X', 6))
        for dy in (-1, 1):
            g.beam((x - .4 * k, ly + dy * .05, lz + .04), (x - .4 * k, sy + dy * .09, sz), .045, .015, WOOD)
    for x in (.9, 2.2):
        K.lamp(g, x, back - .03, .62, face='front')


# ---------------------------------------------------------------- gate office

def gate_office(g, parts):
    """Two-storey works office at the gate under a flat, placeable roof, the
    door in its front wall."""
    x0, y0, x1, y1 = OFFICE
    top = Q.storey_block(g, x0, y0, x1, y1, 2, infill=ORANGE, frame=WOOD, door=DOOR_X, door_id='Entrance',
                         roof_mat=PLANK, slab_mat=WOOD, roof_boards=True,
                         ground_windows={'front': [(3.5, .55, 'grand')], 'right': [(1.0, .55, 'grand')]},
                         windows={'front': [(3.5, 1.5, .52, 'grand'), (4.5, 1.5, .52, 'grand')],
                                  'right': [(.5, 1.5, .52, 'grand'), (1.5, 1.5, .52, 'grand')]})
    K.lamp(g, DOOR_X - .66, y0 - .01, .8, face='front')
    # (The air receiver that lay on this roof is gone: every flat roof cell is
    # a placeable area, user 2026-10-30.)


# ---------------------------------------------------------------- crane yard

def crane_yard(g, parts):
    # Thin concrete runway wall along the yard's right edge (x 4.8..5, y 2..4)
    # with the chimney at its back end, a steel runway beam on corbels along
    # the shop's right wall, low concrete paving under the lathe and hammer.
    xr = 4.8
    # Both start .15 behind the office, clear of its roof edge.
    blk(g, xr, 2.15, -.03, 5.0, 3.12, RUNWAY_Z - .1, CONCRETE)
    blk(g, xr - .02, 2.15, RUNWAY_Z - .1, 5.0, 3.12, RUNWAY_Z, IRON)
    blk(g, 3.0, 2.0, -.02, xr, 3.2, .1, CONCRETE)
    blk(g, 3.0, 3.2, -.02, 4.2, 4.0, .1, CONCRETE)
    xl = 3.1   # clear of the sawtooth planks' end overhang
    for y in (2.3, 3.7):
        blk(g, 3.0, y - .07, RUNWAY_Z - .4, xl + .16, y + .07, RUNWAY_Z - .12, IRON)
    blk(g, xl, 2.15, RUNWAY_Z - .12, xl + .16, 3.85, RUNWAY_Z, PAINTED)
    # Travelling bridge with trolley and hook block (one sliding part).
    y = CRANE_Y
    bz = RUNWAY_Z
    xa, xb = xl + .08, xr + .1
    br = Geometry('PrecisionMachineWorks.CraneBridge', ((xa + xb) / 2, y, bz))
    for dy in (-.14, .14):
        br.box(((xa + xb) / 2, y + dy, bz + .16), (xb - xa - .08, .1, .24), PAINTED)
    for x in (xa + .05, xb - .05):
        br.box((x, y, bz + .07), (.16, .56, .14), IRON)
    tx = 4.1
    br.box((tx, y, bz + .36), (.4, .4, .12), IRON)
    P.lathe(br, (tx, y, bz + .48), [(.09, -.14), (.09, .14)], PAINTED, axis='X', segments=12)
    for dy in (-.04, .04):
        br.box((tx + .06, y + dy, bz - .25), (.02, .02, .52), IRON)
    br.box((tx + .06, y, bz - .54), (.13, .15, .15), PAINTED)
    P.hoop(br, (tx + .06, y, bz - .67), .07, .02, .03, IRON, axis='Y', segments=12)
    parts.append((br, 'SLIDE_Y', CRANE_TRAVEL))
    # Steam hammer at the back of the yard, clear of the crane's travel.
    hx, hy = 3.7, 3.52
    top = .25
    C.podium(g, 3.12, 3.2, 4.14, 3.85, top, joints=False, foot=False)
    for dx in (-.34, .34):
        blk(g, hx + dx - .08, hy - .15, top, hx + dx + .08, hy + .15, top + 1.2, PAINTED)
    blk(g, hx - .46, hy - .17, top + 1.2, hx + .46, hy + .17, top + 1.36, PAINTED)
    P.lathe(g, (hx, hy, top + 1.36), [(.16, 0), (.16, .4), (.13, .45)], IRON, segments=16)
    K.band(g, (hx, hy, 0), .16, top + 1.6, .04, BRASS, segments=16)
    blk(g, hx - .18, hy - .18, top, hx + .18, hy + .18, top + .36, IRON)
    blk(g, hx - .12, hy - .1, top + .36, hx + .12, hy + .1, top + .42, IRON)
    ram = Geometry('PrecisionMachineWorks.HammerRam', (hx, hy, top + .75))
    ram.box((hx, hy, top + .6), (.24, .2, .25), IRON)
    P.tube(ram, (hx, hy, top + .72), (hx, hy, top + 1.32), .036, IRON, segments=8)
    parts.append((ram, 'PISTON_Z', .14))
    P.pipe(g, [(hx + .16, hy, top + 1.65), (hx + .4, hy, top + 1.65), (hx + .4, hy, top + 2.05)], .035,
           flanges=False)
    # Roll lathe in the yard under the crane, turning a long shaft.
    ly, lz = 2.45, .62
    for x in (3.35, 3.85, 4.4):
        blk(g, x - .08, ly - .13, .1, x + .08, ly + .13, .38, IRON)
    blk(g, 3.2, ly - .16, .38, 4.55, ly + .16, .46, IRON)
    blk(g, 3.2, ly - .2, .46, 3.56, ly + .2, .84, PAINTED)
    P.motor(g, (3.38, ly + .04, .94), .1, .28, axis='X')
    blk(g, 4.3, ly - .12, .46, 4.53, ly + .12, .72, PAINTED)
    blk(g, 3.95, ly - .18, .46, 4.2, ly - .02, .56, IRON)
    roll = Geometry('PrecisionMachineWorks.YardLatheRoll', (3.95, ly, lz))
    P.lathe(roll, (3.95, ly, lz), [(.12, -.37), (.12, -.33), (.09, -.33), (.09, .27), (.065, .27), (.065, .35)],
            IRON, axis='X', segments=16)
    for j in range(4):
        a = j * math.pi / 2
        roll.box((3.6, ly + math.cos(a) * .11, lz + math.sin(a) * .11), (.06, .04, .04), BRASS)
    parts.append((roll, 'SPIN_X', 2))
    chimney(g)


def chimney(g):
    """Square tapered brick chimney (the brick tile since 2026-10-31) on its
    firebox in the yard's back-right corner, bound with iron bands; three
    layers in all."""
    cx, cy = 4.6, 3.6
    blk(g, 4.2, 3.2, 0, 5.0, 4.0, .9, CONCRETE)
    blk(g, 4.17, 3.17, .9, 5.0, 4.0, 1.0, CONCRETE)   # flat top on layer 1
    # Firebox door with a glowing slot, facing the yard.
    blk(g, 4.3, 3.16, .25, 4.62, 3.2, .58, IRON)
    blk(g, 4.38, 3.14, .37, 4.54, 3.16, .43, GLOW)
    base_r, top, taper = .3, 2.85, .25

    def r_at(z):
        return base_r * (1 - taper * (z - 1.0) / (top - 1.0))
    P.lathe(g, (cx, cy, 0), [(r_at(1.0 + (top - 1.0) * k / 4), 1.0 + (top - 1.0) * k / 4) for k in range(5)],
            BRICK, segments=4, phase=math.pi / 4, cap_start=False)
    for z in (1.7, 2.4):
        P.lathe(g, (cx, cy, 0), [(r_at(z) + .03, z - .04), (r_at(z) + .03, z + .04)], IRON, segments=4,
                phase=math.pi / 4)
    rt = r_at(top)
    P.lathe(g, (cx, cy, 0), [(rt + .04, top - .1), (rt + .04, top + .1)], IRON, segments=4, phase=math.pi / 4)
    g.box((cx, cy, top + .11), (rt * .9, rt * .9, .02), IRON)
    K.emitter(g, 'smoke', cx, cy, top + .12, rt * .45)


def build(g, parts):
    shop(g, parts)
    gate_office(g, parts)
    crane_yard(g, parts)
