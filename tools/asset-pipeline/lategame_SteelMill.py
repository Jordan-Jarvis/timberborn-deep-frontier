"""SteelMill: electric steelworks making Flux, HighGradeSteel and Alloy.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the slag strip with its slag pot car and heap, and the post lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; one layer per floor, flat roofs): 12x10x15 -> 8x6x8, inside the old
footprint with the same origin, door and native entrance. Removed: the open
crane bay (runway columns, knee braces, girders and the travelling ladle
crane), the scrap/coal/ore bunkers, the cooling bed, the melt shop's gable
roof and monitor lantern, the rolling line's gable canopy and the 14-layer
flue (now 7.6 high).

HERO: an electric-arc melt shop whose three graphite electrodes rise on mast
arms through a forged roof penthouse, with a fume duct over the flat roof
into a riveted steel flue.
ROOFS: flat parapet roofs on the control pulpit (beacon, concrete) and the
melt shop (riveted steel plate); flat open canopies over the rolling line and
the teeming bay (painted metal sheet). Roof variety, user 2026-10-30.

Plan (8 x 6 tiles): control pulpit front-left with the door; the melt shop
behind it; the open rolling line along the front right (reheat furnace,
roller table, three two-high mill stands); the teeming bay at the back right
(tap hole glow on the melt-shop wall, a tilting teeming ladle pouring into
ingot moulds on a car) with the flue in its corner.

Distinct from DeepProcessor (blast-furnace tower, skip hoist): no shaft
furnace, no skip; the electrodes, the duct and the open roll line carry the
silhouette.

Animated (13): electrode masts (PISTON_Z), teeming ladle rocking on its
trunnions (SWAY_X), pour stream (PULSE), six mill rolls (SPIN_Y), hot bar
running through the stands (CUSTOM_LOOP_X), tap-hole and reheat-furnace glow
(PULSE), pulpit beacon (SPIN_Z). The ladle crane went with the crane bay.

No pipe port: none of the mill's recipes uses a liquid.
Smoke: the melt shop flue (a kit stack). The reheat stovepipe went so the canopy roof stays
buildable (user, 2026-10-30: no clutter on buildable space).
"""
import math
import random

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_mining_parts import ore_heap
import lategame_mining_parts as M
from lategame_roofdeck_parts import deck_slab
from industrial_facades import building_portal
from native_window_atlas import atlas_window

IDENT = 'SteelMill'
FOOTPRINT = (8, 6)
HEIGHT = 8
FRAME_END = 121
HERO = ('Electric-arc melt shop whose three graphite electrodes rise on mast arms through a forged roof '
        'penthouse, with a fume duct over the flat roof into a riveted steel flue.')

DOOR_X = 1.5
MELT = (0.0, 3.05, 5.0, 6.0)          # melt shop plinth (front .05 behind the pulpit's back plinth)
MELT_TOP = 1.0
EAVE = 3.5                             # melt shop wall top; flat roof slab above
ROOF_TOP = EAVE + .16
PENT = (1.0, 3.7, 3.0, 5.5)            # electrode penthouse plan (x0, y0, x1, y1)
PENT_TOP = 5.0
DZ = PENT_TOP - 9.1                    # electrode assembly keeps its 2026-10-22 shapes, lowered by this
ELECTRODES = ((1.55, 4.1), (2.45, 4.1), (2.0, 4.7))
MAST_Y = 5.2
STACK = (5.65, 5.4)
LADLE = (6.8, 4.2, 1.6)                # teeming ladle trunnion axis
LADLE_TILT = .45                       # authored forward tilt (radians)
LADLE_SWAY = .08
ROLL_LINE_Y = 1.5
STANDS = (5.0, 6.05, 7.1)
BAR_Z = (.63, .71)
CANOPY = 2.0                           # rolling-line canopy roof top (layer 2)
BAY_ROOF = 3.0                         # teeming-bay roof top (layer 3)


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
    blk(g, 3.0, 0.0, -.02, 8.0, 3.0, .2, CONCRETE)             # rolling line
    blk(g, 5.0, 3.0, -.02, 8.0, 6.0, .2, CONCRETE)             # teeming bay


# ---------------------------------------------------------------- control pulpit

def pulpit(g, parts):
    """Steel-framed control pulpit on tiles 0..3 x 0..3. The core front at .12
    puts the native portal's face on the tile edge y = 0; its back stops short of
    the melt shop's plinth. The flat roof stays
    clear: the beacon stands on the parapet corner."""
    M.hall(g, .05, 2.95, .12, 2.9, 1.84, plinth=.5, doors=[DOOR_X], pitch=1.0, infill=FORGED, frame=IRON,
           posts=('front', 'left', 'right'), style='factory',
           windows={'front': [(.45, 1.15, 'factory', .5), (2.55, 1.15, 'factory', .5)],
                    'left': [(.59, 1.15, 'factory', .5), (1.535, 1.15, 'factory', .5), (2.48, 1.15, 'factory', .5)],
                    'right': [(.59, 1.15, 'factory', .5), (1.535, 1.15, 'factory', .5), (2.48, 1.15, 'factory', .5)]})
    zc = M.flat_roof(g, .05, 2.95, .12, 2.9, 1.84, overhang=.05, parapet=.25) + .25 + .05
    pivot = K.beacon(g, 2.93, 2.88, zc)
    parts.append((K.beacon_shutter(*pivot, 'SteelMill.PulpitBeacon'), 'SPIN_Z', 2))
    K.lamp(g, DOOR_X - .72, .12, 1.15, face='front')
    K.lamp(g, DOOR_X + .72, .12, 1.15, face='front')


# ---------------------------------------------------------------- melt shop

def melt_shop(g, parts):
    x0, y0, x1, y1 = MELT
    top = P.plinth(g, x0, y0, x1, y1, MELT_TOP)
    wx0, wy0, wx1, wy1 = x0 + .1, y0 + .1, x1 - .1, y1 - .1
    bottom = top + .01
    xs = centres(wx0 - .05, wx1 + .05, 5)
    ys = centres(wy0 + .05, wy1 - .05, 3)
    room(g, wx0, wy0, wx1, wy1, bottom, EAVE + .03, infill=FORGED, post=IRON, post_w=.18, style='factory',
         scale=.8,
         windows={'front': [(x, 2.85) for x in xs[3:]],
                  'back': [(x, 2.25) for x in xs[::2]],
                  'left': [(y, 2.25) for y in ys],
                  'right': [(ys[0], 2.6), (ys[2], 2.6)]},
         bays={'front': 5, 'back': 5, 'left': 3, 'right': 3})
    # Plinth windows (factory grids).
    for y in (3.75, 5.25):
        atlas_window(g, x0, y, .52, .34, 'left', 'grid9', reveal=IRON)
    for x in (1.25, 3.75):
        atlas_window(g, x, y1, .52, .34, 'back', 'grid9', reveal=IRON)
    # Tap hole on the bay wall: dark iron frame, glowing throat, spout.
    ty, tz = ys[1], 1.75
    blk(g, wx1 + .05, ty - .3, tz - .28, wx1 + .14, ty + .3, tz + .28, IRON)
    blk(g, wx1 + .14, ty - .2, tz - .18, wx1 + .16, ty + .2, tz + .18, CONCRETE)
    glow = Geometry('SteelMill.TapGlow', (wx1 + .18, ty, tz))
    glow.box((wx1 + .18, ty, tz), (.04, .26, .22), GLOW)
    parts.append((glow, 'PULSE', .08))
    g.beam((wx1 + .16, ty, tz - .26), (wx1 + .7, ty, tz - .42), .14, .09, IRON)
    # Riveted steel plate roof deck (roof variety, user 2026-10-30).
    M.flat_roof(g, wx0, wx1, wy0, wy1, EAVE, overhang=.1, parapet=.25, deck='forged')
    penthouse(g, parts)


def penthouse(g, parts):
    px0, py0, px1, py1 = PENT
    blk(g, px0, py0, ROOF_TOP, px1, py1, PENT_TOP, FORGED)
    for x in (px0, px1):
        for y in (py0, py1):
            blk(g, x - .07, y - .07, ROOF_TOP, x + .07, y + .07, PENT_TOP - .01, IRON)
    for z in (4.15, 4.6):
        blk(g, px0 + .07, py0 - .03, z, px1 - .07, py0 + .002, z + .08, IRON)
        blk(g, px0 - .03, py0 + .07, z, px0 + .002, py1 - .07, z + .08, IRON)
    P.louvre(g, 'X', py0, px0 + .25, px1 - .25, 3.82, 4.08, -1)
    P.louvre(g, 'Y', px0, py0 + .3, py1 - .3, 3.82, 4.08, -1)
    cap = PENT_TOP + .12
    blk(g, px0 - .08, py0 - .08, PENT_TOP, px1 + .08, py1 + .08, cap, IRON)
    # Electrode collars (static rings, clear of the moving electrodes).
    for ex, ey in ELECTRODES:
        P.hoop(g, (ex, ey, cap + .06), .29, .08, .12, BRASS, segments=16)
    # Mast guide sleeves.
    for ex, _ in ELECTRODES:
        blk(g, ex - .13, MAST_Y - .13, cap - .02, ex + .13, MAST_Y + .13, 10.35 + DZ, IRON)
        blk(g, ex - .16, MAST_Y - .16, 10.35 + DZ, ex + .16, MAST_Y + .16, 10.43 + DZ, PAINTED)
    # Moving assembly: electrodes, clamps, arms and mast heads.
    m = Geometry('SteelMill.Electrodes', (2.0, 4.4, 10.0 + DZ))
    arm_z = {0: 10.75 + DZ, 1: 10.75 + DZ, 2: 10.95 + DZ}
    etop = 11.8 + DZ
    for i, (ex, ey) in enumerate(ELECTRODES):
        az = arm_z[i]
        m.cylinder((ex, ey, (8.7 + DZ + etop) / 2), .16, etop - 8.7 - DZ, IRON, 'Z', 16)
        m.cylinder((ex, ey, etop + .02), .12, .04, IRON, 'Z', 16)
        for zj in (10.1 + DZ, 11.45 + DZ):
            P.hoop(m, (ex, ey, zj), .185, .05, .07, BRASS, segments=16)
        blk(m, ex - .22, ey - .22, az - .17, ex + .22, ey + .22, az + .17, PAINTED)
        blk(m, ex - .08, ey + .22, az - .1, ex + .08, MAST_Y - .07, az + .1, IRON)
        blk(m, ex - .07, MAST_Y - .07, 9.55 + DZ, ex + .07, MAST_Y + .07, az + .22, IRON)
        blk(m, ex - .1, MAST_Y - .1, az + .22, ex + .1, MAST_Y + .1, az + .3, PAINTED)
        # Flexible cable loops from the clamp to the mast (heavy bus).
        for s in (-1, 1):
            m.beam((ex + s * .1, ey + .25, az - .15), (ex + s * .1, MAST_Y - .12, az - .45), .05, mat=BRASS)
    parts.append((m, 'PISTON_Z', .22))
    # Fume duct over the roof to the flue.
    duct_y, duct_z = 4.9, 4.6
    P.pipe(g, [(px1 - .05, duct_y, duct_z), (STACK[0], duct_y, duct_z), (STACK[0], STACK[1] - .2, duct_z)],
           .22, IRON, flanges=False, elbow_mat=IRON, segments=16)
    for x in (3.5, 4.3):
        P.hoop(g, (x, duct_y, duct_z), .255, .05, .08, PAINTED, axis='X', segments=16)
    for x in (3.9, 4.7):
        blk(g, x - .06, duct_y - .06, ROOF_TOP, x + .06, duct_y + .06, duct_z - .2, IRON)
        blk(g, x - .16, duct_y - .05, duct_z - .24, x + .16, duct_y + .05, duct_z - .2, IRON)


def flue(g):
    sx, sy = STACK
    K.revolve(g, (sx, sy, .17), [(.5, 0), (.5, .45), (.42, .53)], CONCRETE, segments=8, phase=math.pi / 8)
    K.stack(g, sx, sy, .62, 6.85, emits='smoke', r=.32, taper=.78, mat=IRON, bands=4)


# ---------------------------------------------------------------- teeming bay

def teeming_bay(g):
    """Flat roof over the teeming bay on two posts and the melt-shop wall."""
    for y in (5.0, 5.8):
        P.pier(g, 7.75, y, .17, .45, .3)
        blk(g, 7.67, y - .08, .5, 7.83, y + .08, BAY_ROOF - .28, IRON)
    blk(g, 7.62, 3.1, BAY_ROOF - .28, 7.88, 5.9, BAY_ROOF - .16, IRON)
    deck_slab(g, 5.0, 3.0, 8.0, 6.0, BAY_ROOF, 'painted', base=IRON)   # painted metal sheets (roof variety)


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
    mould_top = 1.08
    stream = Geometry('SteelMill.PourStream', (lx, nose[1], nose[2]))
    K.revolve(stream, (lx, nose[1], mould_top - .1), [(.06, 0), (.055, .3), (.045, nose[2] + .06 - mould_top + .1)],
              GLOW, segments=8)
    parts.append((stream, 'PULSE', .06))
    # Ingot moulds on a car running along the bay front.
    track_y = nose[1]
    for s in (-1, 1):
        blk(g, 5.3, track_y + s * .25 - .03, base, 7.55, track_y + s * .25 + .03, base + .07, IRON)
    for k in range(4):
        x = 5.5 + k * .66
        blk(g, x - .05, track_y - .38, base - .01, x + .05, track_y + .38, base + .025, WOOD)
    for k, x in enumerate((lx - .75, lx, lx + .75)):
        blk(g, x - .32, track_y - .3, base + .2, x + .32, track_y + .3, base + .3, IRON)
        for sx in (-.22, .22):
            for sy in (-1, 1):
                g.cylinder((x + sx, track_y + sy * .25, base + .15), .08, .05, IRON, 'Y', 10)
        K.revolve(g, (x, track_y, base + .3), [(.22, 0), (.19, mould_top - base - .3)], PAINTED, segments=4,
                  phase=math.pi / 4)
        if k == 1:
            blk(g, x - .1, track_y - .1, mould_top - .02, x + .1, track_y + .1, mould_top + .012, GLOW)


# ---------------------------------------------------------------- rolling line

def rolling_line(g, parts):
    base = .2
    # Flat open canopy on four steel posts (front and back), level with the pulpit roof.
    for x in (3.2, 7.8):
        for y in (.2, 2.88):
            P.pier(g, x, y, base - .03, base + .3, .26)
            blk(g, x - .07, y - .07, base + .35, x + .07, y + .07, CANOPY - .28, IRON)
    for y in (.2, 2.88):
        blk(g, 3.1, y - .08, CANOPY - .28, 7.9, y + .08, CANOPY - .16, IRON)
    blk(g, 3.0, 0.0, CANOPY - .16, 8.0, 3.0, CANOPY, CONCRETE)
    # Reheat furnace at the head of the line.
    fx0, fx1, fy0, fy1 = 3.35, 4.25, .75, 2.25
    blk(g, fx0, fy0, base - .03, fx1, fy1, 1.4, CONCRETE)
    blk(g, fx0 - .04, fy0 - .04, 1.4, fx1 + .04, fy1 + .04, 1.48, IRON)
    for x in (fx0 + .2, (fx0 + fx1) / 2, fx1 - .2):
        blk(g, x - .05, fy0 - .04, base + .1, x + .05, fy0, 1.4, IRON)
        blk(g, x - .05, fy1, base + .1, x + .05, fy1 + .04, 1.4, IRON)
    blk(g, 3.57, fy0 - .05, .5, 4.03, fy0 - .02, 1.05, IRON)               # charging door
    blk(g, 3.6, fy0 - .07, .95, 4.0, fy0 - .05, .99, BRASS)
    blk(g, fx1, ROLL_LINE_Y - .3, .55, fx1 + .03, ROLL_LINE_Y + .3, .82, IRON)
    glow = Geometry('SteelMill.ReheatGlow', (fx1 + .04, ROLL_LINE_Y, .67))
    glow.box((fx1 + .04, ROLL_LINE_Y, .67), (.02, .4, .16), GLOW)
    parts.append((glow, 'PULSE', .1))
    # Roller table, interrupted at the stands.
    tx0, tx1 = fx1 + .04, 7.6
    cuts = [tx0] + [v for s in STANDS for v in (s - .36, s + .36)] + [tx1]
    for a, b in zip(cuts[::2], cuts[1::2]):
        for y in (ROLL_LINE_Y - .3, ROLL_LINE_Y + .3):
            blk(g, a, y - .035, .42, b, y + .035, .6, IRON)
    for x in (4.6, 5.55, 6.6, 7.55):
        for y in (ROLL_LINE_Y - .3, ROLL_LINE_Y + .3):
            blk(g, x - .04, y - .04, base - .02, x + .04, y + .04, .42, IRON)
    x = tx0 + .2
    while x < tx1 - .1:
        if all(abs(x - s) > .4 for s in STANDS):
            g.cylinder((x, ROLL_LINE_Y, .555), .07, .53, IRON, 'Y', 10)
        x += .3
    for i, sx in enumerate(STANDS):
        mill_stand(g, parts, i, sx)
    # Hot bar segments travel one pitch per loop through the stands.
    pitch = .9
    bar = Geometry('SteelMill.HotBar', (5.6, ROLL_LINE_Y, BAR_Z[0]))
    for k in range(3):
        xa = 4.3 + k * pitch
        blk(bar, xa, ROLL_LINE_Y - .09, BAR_Z[0] + .003, xa + .68, ROLL_LINE_Y + .09, BAR_Z[1] - .003, GLOW)
    parts.append((bar, 'CUSTOM_LOOP_X', pitch))


def mill_stand(g, parts, i, sx):
    y = ROLL_LINE_Y
    lo, hi = .43, .91
    for side in (-1, 1):
        py = y + side * .52
        for dx in (-.22, .22):
            blk(g, sx + dx - .07, py - .07, .2, sx + dx + .07, py + .07, 1.25, IRON)
        blk(g, sx - .32, py - .09, 1.25, sx + .32, py + .09, 1.4, PAINTED)
        blk(g, sx - .34, py - .1, .17, sx + .34, py + .1, .3, IRON)
        # Screw-down column on the crosshead (all under the canopy roof at 1.84).
        g.cylinder((sx, py, 1.48), .05, .16, IRON, 'Z', 8)
    K.wheel(g, (sx, y - .52, 1.6), .14, 'Y')
    blk(g, sx - .3, y - .44, 1.4, sx + .3, y + .44, 1.46, IRON)
    # Spindles back to a pinion box and motor behind the line.
    for z in (lo, hi):
        g.cylinder((sx, y + .69, z), .06, .24, IRON, 'Y', 10)
    blk(g, sx - .25, 2.2, .2, sx + .25, 2.5, 1.15, PAINTED)
    blk(g, sx - .18, 2.5, .2, sx + .18, 2.72, .28, IRON)
    P.motor(g, (sx, 2.49, .48), .2, .32, axis='Y')
    for z, name, turns in ((lo, 'Lower', 2), (hi, 'Upper', -2)):
        r = Geometry(f'SteelMill.Stand{i + 1}{name}Roll', (sx, y, z))
        r.cylinder((sx, y, z), .2, .9, IRON, 'Y', 16)
        r.cylinder((sx, y, z), .085, 1.24, IRON, 'Y', 10)
        for k in range(4):
            a = k * math.pi / 2
            r.box((sx + math.cos(a) * .1, y + .6, z + math.sin(a) * .1), (.05, .05, .05), BRASS)
        parts.append((r, 'SPIN_Y', turns))


def build(g, parts):
    ground(g)
    pulpit(g, parts)
    melt_shop(g, parts)
    flue(g)
    teeming_bay(g)
    teeming(g, parts)
    rolling_line(g, parts)
