"""SteelMill: electric steelworks making Flux, HighGradeSteel and Alloy.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the slag strip with its slag pot car and heap, and the post lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; one layer per floor, flat roofs): 12x10x15 -> 8x6x8, inside the old
footprint with the same origin, door and native entrance. Removed: the open
crane bay and its travelling ladle crane, the bunkers, the cooling bed, the
gable roofs and the 14-layer flue.

Second shrink 2026-11-01 (a YouTuber called the late-game buildings
"massive"; user: "we need to shrink the buildings down even more"):
8x6x8 -> 5x4x6, inside the old footprint with the same origin, door tile and
native entrance (1, -1). Saved mills stay valid: every new block is a block
the old mill occupied (the front three rows stay two layers high, as before;
only the back row, the old melt shop's front row, rises higher), and the
layer-2 and layer-4 roofs sit where the old roof decks were, so paths and
platforms on them keep their support. The reheat furnace is a small box at
the head of the line, the stand motors and pinion boxes are gone, the three
stands are 0.8 scale and the electrodes stand in one row on a one-tile
penthouse.

HERO: an electric-arc furnace bay whose three graphite electrodes rise on
mast arms through a forged roof penthouse, its fume duct into a riveted
steel flue.
ROOFS: flat open roofs, no parapets (user 2026-10-31: "I want it to be like an
actual platform where roads can connect"): the pulpit-and-hall block
(riveted steel plate) and the rolling-line and teeming-bay canopy (painted
metal sheet) form one deck on layer 2 over the front three rows; the furnace
bay's riveted steel-plate roof is on layer 4. Roof variety, user 2026-10-30.

Plan (5 x 4 tiles): the two-storey pulpit and melt hall on tiles 0..2 x 0..3
(door front, tap hole on its right wall); the rolling line along the front
right (2..5 x 0..1: reheat furnace, roller table, three two-high mill
stands); the teeming bay behind it (2..5 x 1..3: a tilting teeming ladle
pouring into ingot moulds on a car); the four-layer furnace bay across the
back row (0..5 x 3..4) with the electrode penthouse on tile 1 and the flue
rising from the ground through its roof on tile 2.

Distinct from DeepProcessor (blast-furnace tower, skip hoist): no shaft
furnace, no skip; the electrodes, the duct and the open roll line carry the
silhouette.

Animated (13, names unchanged): electrode masts (PISTON_Z), teeming ladle
rocking on its trunnions (SWAY_X), pour stream (PULSE), six mill rolls
(SPIN_Y), hot bar running through the stands (CUSTOM_LOOP_X), tap-hole and
reheat-furnace glow (PULSE), the pulpit beacon (SPIN_Z, now on the penthouse
cap).

No pipe port: none of the mill's recipes uses a liquid.
Smoke: the flue (a kit stack) from the ground through the furnace bay roof.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
import lategame_mining_parts as M
import compact_industry_parts as Q
from lategame_roofdeck_parts import deck_slab
from native_window_atlas import atlas_window

IDENT = 'SteelMill'
FOOTPRINT = (5, 4)
HEIGHT = 6
FRAME_END = 121
HERO = ('Electric-arc melt shop whose three graphite electrodes rise on mast arms through a forged roof '
        'penthouse, with a fume duct over the flat roof into a riveted steel flue.')

DOOR_X = 1.5
HALL = (0.0, 0.0, 2.0, 3.0)           # control pulpit and melt hall: two one-layer storeys, roof on layer 2
BAY = (0.0, 3.1, 5.0, 4.0)            # back furnace bay plinth (.1 behind the hall's back face: feet clear)
BAY_TOP = 1.0
EAVE = 3.84                            # furnace bay wall top; flat roof slab above, its top on layer 4
ROOF_TOP = EAVE + .16
PENT = (1.05, 3.2, 1.95, 3.95)         # electrode penthouse plan (x0, y0, x1, y1), on tile 1 of the back row
PENT_TOP = 4.85
CAP = PENT_TOP + .12
ELECTRODES = ((1.2, 3.42), (1.5, 3.42), (1.8, 3.42))
ELECTRODE_R = .12
ARM_Z = (5.35, 5.35, 5.48)
ETOP = 5.72
MAST_Y = 3.82
STACK = (2.5, 3.55)                    # flue from the ground through the bay roof on tile 2 of the back row
LADLE = (3.6, 2.2, 1.2)                # teeming ladle trunnion axis
LADLE_TILT = .45                       # authored forward tilt (radians)
LADLE_SWAY = .08
ROLL_LINE_Y = .55
STANDS = (2.98, 3.68, 4.38)
STAND_SCALE = .8
BAR_Z = (.55, .61)
DECK = 2.0                             # hall, canopy and teeming-bay roofs (layer 2)


def animate(obj, kind, value, frame_end):
    C.animate(obj, kind, value, frame_end)


def centres(a, b, n):
    return [a + (b - a) * (k + .5) / n for k in range(n)]


def room(g, x0, y0, x1, y1, bottom, top, *, infill, post, post_w=.16, windows=None, style='factory',
         scale=.8, bays=None):
    """Four framed walls meeting at closed corners (front/back walls run past
    the side walls, side walls butt into them)."""
    windows = windows or {}
    for name, axis, plane, start, end, out in (
            ('front', 'X', y0, x0 - .05, x1 + .05, -1), ('back', 'X', y1, x0 - .05, x1 + .05, 1),
            ('left', 'Y', x0, y0 + .05, y1 - .05, -1), ('right', 'Y', x1, y0 + .05, y1 - .05, 1)):
        K.frame_wall(g, axis, plane, start, end, bottom, top, outward=out, infill=infill, post=post,
                     post_w=post_w, windows=windows.get(name), window_style=style, window_scale=scale,
                     bays=(bays or {}).get(name))


def copy_rotated_x(dst, src, pivot, angle):
    """Copy every face of `src` (built about the artwork origin) into `dst`,
    rotated about the X-parallel axis through `pivot`."""
    verts = [C.rot_x((-x, -y, z), pivot, angle) for x, y, z in src.vertices]
    for face, mat in zip(src.faces, src.materials):
        dst.add([verts[i] for i in face], [tuple(range(len(face)))], mat)


# ---------------------------------------------------------------- ground

def ground(g):
    """Concrete yard slabs (one owner of the ground per spot)."""
    blk(g, 2.0, 0.0, -.02, 5.0, 3.0, .2, CONCRETE)             # rolling line and teeming bay


# ---------------------------------------------------------------- control pulpit and melt hall

def hall(g, parts):
    """Steel-framed two-storey block on tiles 0..2 x 0..3 (one layer per
    storey): the control pulpit at the front with the door, the melt hall
    behind it with the tap hole on its right wall. Its flat riveted-plate
    roof on layer 2 is an open platform level with the canopy beside it."""
    x0, y0, x1, y1 = HALL
    Q.storey_block(g, x0, y0, x1, y1, 2, infill=FORGED, frame=IRON, door=DOOR_X, door_id='Door0',
                   roof_mat=FORGED, slab_mat=IRON, roof_boards=True,
                   ground_windows={'left': [(.5, .55, 'factory'), (2.5, .55, 'factory')]},
                   windows={'front': [(.5, 1.5, .5, 'factory'), (1.5, 1.5, .5, 'factory')],
                            'left': [(y + .5, 1.5, .5, 'factory') for y in range(3)],
                            'right': [(1.5, 1.5, .5, 'factory')]})
    K.lamp(g, .8, y0 - .01, .8, face='front')
    # Tap hole on the hall's right wall: dark iron frame, glowing throat, spout.
    wx = x1 + .005
    ty, tz = LADLE[1], 1.55
    blk(g, wx, ty - .26, tz - .24, wx + .09, ty + .26, tz + .24, IRON)
    blk(g, wx + .09, ty - .17, tz - .15, wx + .11, ty + .17, tz + .15, CONCRETE)
    glow = Geometry('SteelMill.TapGlow', (wx + .13, ty, tz))
    glow.box((wx + .13, ty, tz), (.04, .22, .19), GLOW)
    parts.append((glow, 'PULSE', .08))
    g.beam((wx + .11, ty, tz - .22), (wx + .4, ty, tz - .3), .12, .08, IRON)


# ---------------------------------------------------------------- furnace bay

def furnace_bay(g, parts):
    """The tall back row (tiles 0..5 x 3..4): brick podium, steel-framed walls
    and a flat steel-plate roof on layer 4, the electrode penthouse on tile 1."""
    x0, y0, x1, y1 = BAY
    top = P.plinth(g, x0, y0, x1, y1, BAY_TOP, wall=K.BRICK)   # brick podium (2026-10-31)
    wx0, wy0, wx1, wy1 = x0 + .1, y0 + .1, x1 - .1, y1 - .1
    bottom = top + .01
    # Solid core behind the framed walls: the bay's cells register as building
    # (thin frame walls alone leave its inside layers free).
    blk(g, wx0 + .1, wy0 + .1, bottom, wx1 - .1, wy1 - .1, EAVE - .01, FORGED)
    xs = centres(wx0 - .05, wx1 + .05, 5)
    room(g, wx0, wy0, wx1, wy1, bottom, EAVE + .03, infill=FORGED, post=IRON, post_w=.18, style='factory',
         scale=.5,
         windows={'front': [(x, 3.0) for x in xs[3:]],
                  'back': [(x, 2.4) for x in (xs[0], xs[3], xs[4])],
                  'left': [(3.55, 2.4)], 'right': [(3.55, 2.4)]},
         bays={'front': 5, 'back': 5, 'left': 1, 'right': 1})
    for x in (.5, 3.5, 4.5):
        atlas_window(g, x, y1, .52, .34, 'back', 'grid9', reveal=IRON)
    # Riveted steel plate roof deck (roof variety, user 2026-10-30).
    M.flat_roof(g, wx0, wx1, wy0, wy1, EAVE, overhang=.1, deck='forged')
    penthouse(g, parts)


def penthouse(g, parts):
    px0, py0, px1, py1 = PENT
    blk(g, px0, py0, ROOF_TOP, px1, py1, PENT_TOP, FORGED)
    for x in (px0, px1):
        for y in (py0, py1):
            blk(g, x - .06, y - .06, ROOF_TOP, x + .06, y + .06, PENT_TOP - .01, IRON)
    blk(g, px0 + .06, py0 - .03, 4.5, px1 - .06, py0 + .002, 4.58, IRON)
    P.louvre(g, 'X', py0, px0 + .15, px1 - .15, 4.12, 4.42, -1)
    blk(g, px0 - .06, py0 - .05, PENT_TOP, px1 + .05, py1 + .04, CAP, IRON)
    # The pulpit's warning beacon on the cap's front-right corner.
    pivot = K.beacon(g, px1 - .08, py0 + .07, CAP)
    parts.append((K.beacon_shutter(*pivot, 'SteelMill.PulpitBeacon'), 'SPIN_Z', 2))
    # Mast guide sleeves.
    for ex, _ in ELECTRODES:
        blk(g, ex - .09, MAST_Y - .09, CAP - .02, ex + .09, MAST_Y + .09, CAP + .22, IRON)
        blk(g, ex - .11, MAST_Y - .11, CAP + .22, ex + .11, MAST_Y + .11, CAP + .27, PAINTED)
    # Moving assembly: electrodes, clamps, arms and mast heads.
    m = Geometry('SteelMill.Electrodes', (1.5, 3.6, CAP))
    ebot = CAP - .3
    for i, (ex, ey) in enumerate(ELECTRODES):
        az = ARM_Z[i]
        m.cylinder((ex, ey, (ebot + ETOP) / 2), ELECTRODE_R, ETOP - ebot, IRON, 'Z', 16)
        m.cylinder((ex, ey, ETOP + .015), ELECTRODE_R * .75, .03, IRON, 'Z', 16)
        P.hoop(m, (ex, ey, ETOP - .2), ELECTRODE_R + .025, .04, .05, BRASS, segments=16)
        blk(m, ex - .135, ey - .14, az - .1, ex + .135, ey + .14, az + .1, PAINTED)
        blk(m, ex - .05, ey + .14, az - .06, ex + .05, MAST_Y - .05, az + .06, IRON)
        blk(m, ex - .05, MAST_Y - .05, CAP - .25, ex + .05, MAST_Y + .05, az + .14, IRON)
        blk(m, ex - .07, MAST_Y - .07, az + .14, ex + .07, MAST_Y + .07, az + .2, PAINTED)
        m.beam((ex, ey + .15, az - .08), (ex, MAST_Y - .08, az - .26), .04, mat=BRASS)
    parts.append((m, 'PISTON_Z', .22))
    # Fume duct from the penthouse into the flue.
    P.pipe(g, [(px1 - .05, STACK[1], 4.45), (STACK[0] - .1, STACK[1], 4.45)], .14, IRON, flanges=False,
           segments=16)
    P.hoop(g, (2.08, STACK[1], 4.45), .165, .04, .07, PAINTED, axis='X', segments=16)


def flue(g):
    """Riveted flue from the ground up through the bay roof (smoke)."""
    sx, sy = STACK
    K.stack(g, sx, sy, .2, 5.7, emits='smoke', r=.27, taper=.8, mat=IRON, bands=4)


# ---------------------------------------------------------------- canopy

def decks(g):
    """One flat painted-sheet deck on layer 2 over the rolling line and the
    teeming bay (tiles 2..5 x 0..3), on corner posts, the hall wall and the
    furnace bay's front wall."""
    for x, y in ((4.84, .16), (4.84, 2.84)):
        P.pier(g, x, y, .17, .4, .22)
        blk(g, x - .07, y - .07, .45, x + .07, y + .07, DECK - .28, IRON)
    blk(g, 2.0, .06, DECK - .28, 4.94, .22, DECK - .16, IRON)       # front beam off the hall wall
    blk(g, 4.78, .22, DECK - .28, 4.94, 3.0, DECK - .16, IRON)
    deck_slab(g, 2.06, 0.0, 5.0, 3.0, DECK, 'painted', base=IRON)   # meets the hall roof's eave


def teeming(g, parts):
    lx, ly, lz = LADLE
    base = .2
    for s in (-1, 1):
        x = lx + s * .72
        blk(g, x - .17, ly - .4, base - .03, x + .17, ly + .4, lz - .25, CONCRETE)
        blk(g, x - .2, ly - .43, base - .03, x + .2, ly + .43, base + .12, CONCRETE)
        blk(g, x - .14, ly - .16, lz - .25, x + .14, ly + .16, lz - .06, IRON)
    # Tilting ladle, authored upright then tilted forward on its trunnions.
    src = Geometry('ladle source')
    z0, z1 = lz - .65, lz + .45
    P.lathe(src, (lx, ly, z0), [(.45, 0), (.55, z1 - z0), (.6, z1 - z0), (.6, z1 - z0 + .06)], IRON, segments=12)
    for z in (z0 + .22, z0 + .78):
        K.band(src, (lx, ly, 0), .45 + .1 * (z - z0) / (z1 - z0), z, .07, PAINTED, segments=12)
    src.cylinder((lx, ly, z1 + .07), .52, .02, IRON, 'Z', 12)
    src.cylinder((lx, ly, z1 + .0875), .3, .015, GLOW, 'Z', 12)
    blk(src, lx - .12, ly - .72, z1 - .06, lx + .12, ly - .5, z1 + .02, IRON)      # pouring nose
    for s in (-1, 1):
        src.cylinder((lx + s * .6, ly, lz), .09, .14, IRON, 'X', 12)
        src.cylinder((lx + s * .55, ly, lz), .14, .05, PAINTED, 'X', 12)
    ladle = Geometry('SteelMill.TeemingLadle', (lx, ly, lz))
    copy_rotated_x(ladle, src, (lx, ly, lz), LADLE_TILT)
    parts.append((ladle, 'SWAY_X', LADLE_SWAY))
    # Pour stream from the nose into the mould below.
    nose = C.rot_x((lx, ly - .66, z1 - .02), (lx, ly, lz), LADLE_TILT)
    mould_top = .78
    stream = Geometry('SteelMill.PourStream', (lx, nose[1], nose[2]))
    K.revolve(stream, (lx, nose[1], mould_top - .1), [(.06, 0), (.055, .3), (.045, nose[2] + .06 - mould_top + .1)],
              GLOW, segments=8)
    parts.append((stream, 'PULSE', .06))
    # Ingot moulds on a car running along the bay front.
    track_y = nose[1]
    for s in (-1, 1):
        blk(g, 2.75, track_y + s * .2 - .03, base, 4.45, track_y + s * .2 + .03, base + .07, IRON)
    for k in range(3):
        x = 2.95 + k * .6
        blk(g, x - .05, track_y - .32, base - .01, x + .05, track_y + .32, base + .025, WOOD)
    for k, x in enumerate((lx - .52, lx, lx + .52)):
        blk(g, x - .24, track_y - .22, base + .16, x + .24, track_y + .22, base + .24, IRON)
        for sx in (-.16, .16):
            for sy in (-1, 1):
                g.cylinder((x + sx, track_y + sy * .19, base + .12), .06, .04, IRON, 'Y', 10)
        K.revolve(g, (x, track_y, base + .24), [(.17, 0), (.15, mould_top - base - .24)], PAINTED, segments=4,
                  phase=math.pi / 4)
        if k == 1:
            blk(g, x - .08, track_y - .08, mould_top - .02, x + .08, track_y + .08, mould_top + .012, GLOW)


# ---------------------------------------------------------------- rolling line

def rolling_line(g, parts):
    base = .2
    # Reheat furnace at the head of the line, against the pulpit's side wall.
    fx0, fx1, fy0, fy1 = 2.08, 2.52, .22, .9
    blk(g, fx0, fy0, base - .03, fx1, fy1, 1.15, CONCRETE)
    blk(g, fx0 - .03, fy0 - .03, 1.15, fx1 + .03, fy1 + .03, 1.22, IRON)
    for x in (fx0 + .1, fx1 - .1):
        blk(g, x - .04, fy0 - .03, base + .1, x + .04, fy0, 1.15, IRON)
    blk(g, 2.16, fy0 - .04, .45, 2.44, fy0 - .01, .82, IRON)               # charging door
    blk(g, 2.18, fy0 - .06, .76, 2.42, fy0 - .04, .79, BRASS)
    blk(g, fx1, ROLL_LINE_Y - .24, .45, fx1 + .03, ROLL_LINE_Y + .24, .7, IRON)
    glow = Geometry('SteelMill.ReheatGlow', (fx1 + .04, ROLL_LINE_Y, .58))
    glow.box((fx1 + .04, ROLL_LINE_Y, .58), (.02, .32, .12), GLOW)
    parts.append((glow, 'PULSE', .1))
    # Roller table, interrupted at the stands.
    s = STAND_SCALE
    tx0, tx1 = fx1 + .04, 4.85
    cuts = [tx0] + [v for x in STANDS for v in (x - .3, x + .3)] + [tx1]
    for a, b in zip(cuts[::2], cuts[1::2]):
        for y in (ROLL_LINE_Y - .24, ROLL_LINE_Y + .24):
            blk(g, a, y - .03, .36, b, y + .03, .5, IRON)
    for x in (2.62, 3.33, 4.03, 4.75):
        for y in (ROLL_LINE_Y - .24, ROLL_LINE_Y + .24):
            blk(g, x - .035, y - .035, base - .02, x + .035, y + .035, .36, IRON)
    x = tx0 + .12
    while x < tx1 - .08:
        if all(abs(x - st) > .34 for st in STANDS):
            g.cylinder((x, ROLL_LINE_Y, .465), .055, .43, IRON, 'Y', 10)
        x += .24
    for i, sx in enumerate(STANDS):
        mill_stand(g, parts, i, sx)
    # Hot bar segments travel one pitch per loop through the stands.
    pitch = .65
    bar = Geometry('SteelMill.HotBar', (3.4, ROLL_LINE_Y, BAR_Z[0]))
    for k in range(3):
        xa = 2.6 + k * pitch
        blk(bar, xa, ROLL_LINE_Y - .07, BAR_Z[0] + .003, xa + .45, ROLL_LINE_Y + .07, BAR_Z[1] - .003, GLOW)
    parts.append((bar, 'CUSTOM_LOOP_X', pitch))


def mill_stand(g, parts, i, sx):
    """Two-high mill stand at STAND_SCALE: housings either side of the line,
    crosshead with the screw-down wheel, two rolls and their spindles."""
    s = STAND_SCALE
    y = ROLL_LINE_Y
    lo, hi = .2 + .23 * s, .2 + .71 * s
    top = .2 + 1.05 * s
    for side in (-1, 1):
        py = y + side * .42 * s
        for dx in (-.22 * s, .22 * s):
            blk(g, sx + dx - .06, py - .06, .2, sx + dx + .06, py + .06, top, IRON)
        blk(g, sx - .27, py - .075, top, sx + .27, py + .075, top + .12, PAINTED)
        blk(g, sx - .28, py - .08, .17, sx + .28, py + .08, .28, IRON)
        g.cylinder((sx, py, top + .25), .04, .14, IRON, 'Z', 8)
    K.wheel(g, (sx, y - .42 * s, top + .34), .11, 'Y')
    blk(g, sx - .24, y - .35 * s, top + .12, sx + .24, y + .35 * s, top + .17, IRON)
    # Spindles back to the coupling box on the stand's back housing.
    for z in (lo, hi):
        g.cylinder((sx, y + .42 * s + .12, z), .05, .1, IRON, 'Y', 10)
    for z, name, turns in ((lo, 'Lower', 2), (hi, 'Upper', -2)):
        r = Geometry(f'SteelMill.Stand{i + 1}{name}Roll', (sx, y, z))
        r.cylinder((sx, y, z), .16, .72 * s / .8, IRON, 'Y', 16)
        r.cylinder((sx, y, z), .07, .96 * s / .8 * .9, IRON, 'Y', 10)
        for k in range(4):
            a = k * math.pi / 2
            r.box((sx + math.cos(a) * .08, y + .4, z + math.sin(a) * .08), (.04, .04, .04), BRASS)
        parts.append((r, 'SPIN_Y', turns))


def build(g, parts):
    ground(g)
    hall(g, parts)
    furnace_bay(g, parts)
    flue(g)
    decks(g)
    teeming(g, parts)
    rolling_line(g, parts)
