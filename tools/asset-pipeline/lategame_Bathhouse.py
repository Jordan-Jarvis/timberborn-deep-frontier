"""Bathhouse: late-game steam baths heated by an engine-driven boiler plant.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the colonnaded portico, the planter with shrubs and the lamp standard;
the plunge-pool court stays.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor", "make
the roof flat on more of our buildings"): 9x7x11 -> 7x5x5, inside the old
footprint with the same origin, door and native entrance cell. The bath hall
is a 3 x 3 hall (one-layer concrete storey, a short plaster band and the
vault) instead of 5 x 5 with a 1.2-layer podium and three-layer walls; the
changing wing and the boiler room are one layer high with flat roofs (no lean-
to or plank gable); the steam stack is less than half as tall.
Roof variety (user, 2026-10-30: "no roof vents"): the louvred lantern on the
vault became a plain brass finial, the changing-wing roof is a timber deck and
the boiler-room roof riveted metal; the boiler chimney rises from the ground
in the boiler room's back wall instead of standing on its roof.

HERO (kept as the silhouette): a cross-vaulted (groin-vaulted) bath hall:
four teal plank barrel quarters meeting in valley groins, each ending in an
iron-banded arch over a semicircular thermal (Diocletian) window, with a
brass finial at the crossing. No other study has a groin vault or thermal
windows.
ROOF: groin vault in teal roof planks on the hall (kept as its silhouette);
flat roof decks on layer 1 with low parapets: timber decking on the changing
wing, riveted metal on the boiler room.

Plan (7 x 5 tiles; front y = 0):
  x 2..5, y 2..5  bath hall: rusticated concrete ground storey (top layer 1)
                  with the door centred on x = 3.5, face on the y = 2 tile
                  edge (its path cell (3,1,0) stays free), orange plaster band
                  set back 0.06, cornice and the groin vault.
  x 0..2, y 2..5  changing-room wing, grey-plank timber frame, portholes.
  x 0..3, y 0..2  plunge-pool court: cast basin with native water and a
                  bronze spout stele.
  x 4..7, y 1..2  open engine yard along the boiler-room wall: flywheel and a
                  belt-driven laundry drum; the front row y 0..1 stays bare.
  x 5..7, y 2..5  boiler room (concrete); its chimney rises from the ground
                  in the back wall (tile (5,4)) with the safety valve on it, so
                  the rest of its roof is a clear roof deck; the Water pipe
                  socket sits in a recess at its back (cell (6,4,0), Up).

Animated (unchanged names and kinds): flywheel (SPIN_Y), laundry/towel drum
(SPIN_Y), safety-valve weighted lever (SWAY_Y).
Emitters: steam at the chimney mouth and off the pool.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, WATER, LAYER_GAP
import lategame_civic_parts as P
from lategame_civic_parts import blk, obox
import lategame_industry_parts as I
import native_window_atlas as A
import native_building_assets as N
import civic_wellbeing_parts as W
from lategame_roofdeck_parts import deck_slab
from civic_wellbeing_parts import animate  # noqa: F401  (CUSTOM_ kinds)

IDENT = 'Bathhouse'
FOOTPRINT = (7, 5)
HEIGHT = 5
FRAME_END = 121
HERO = ('Cross-vaulted bath hall: four teal plank barrel quarters meeting in groins, iron-banded arches over '
        'semicircular thermal windows, and a brass finial at the crossing.')

# Bath water arrives by Timber Pipes at the boiler room's back recess
# (same record shape as the NuclearReactor coolant inlet).
PIPE_INLET = {'cell': [6, 4, 0], 'direction': 'Up', 'state': 'OpenIn', 'good': 'Water',
              'socket': [6.5, 4.84, .45]}

HALL = (2.0, 2.0, 5.0, 5.0)          # ground storey on whole tiles
PT = 1.0                              # ground storey top: one layer
HW = (2.06, 2.06, 4.94, 4.94)         # plaster band, set back 0.06 (one flat face with the cornice)
WT = 1.38                             # band top
CX, CY = 3.5, 3.5
SPRING, RISE, HALF = 1.5, .95, 1.44    # springing on the cornice top
DOOR_X = 3.5
SIDE_TOP = 1.0                        # changing wing and boiler room roofs, layer 1
SLAB = .16

# Visitor seats (export_lategame_models.bathhouse_slots writes them as native
# '#Slot#Spot<i>' empties; Sitting animation as on the vanilla MudBath, not a
# WaterSlot: the pool water is the model's own surface, not world water).
# Native FixedSlotManager needs a slot per visitor (capacity 12), so the
# bathers fill the six pool seats first and the other six sit inside the
# closed hall, unseen, as before. (x, y, seat z, facing x, facing y).
POOL_WATER = .38                      # plunge-pool water surface (pool_court)
BATH_SEATS = [(.75, 1.58, .08, 0, -1), (1.5, 1.58, .08, 0, -1), (2.25, 1.58, .08, 0, -1),
              (.75, .42, .08, 0, 1), (1.5, .42, .08, 0, 1), (2.25, .42, .08, 0, 1)]
HALL_SEATS = [(x, y, PT, 0, 1) for y in (3.0, 4.0) for x in (2.5, 3.5, 4.5)]


# ---------------------------------------------------------------- bath hall

def hall(g, parts):
    x0, y0, x1, y1 = HALL
    P.podium(g, x0, y0, x1, y1, PT, skip=[(DOOR_X - .5, DOOR_X + .5)])
    P.door(g, DOOR_X, y0, 0, 'Door0')
    K.lamp(g, DOOR_X - .64, y0, .5, face='front')
    K.lamp(g, DOOR_X + .64, y0, .5, face='front')
    for x in (2.45, 4.55):
        P.native_window(g, x, y0, .47, .5, 'front', 'factory')
    for x in (2.5, 3.5, 4.5):
        P.native_window(g, x, y1, .47, .5, 'back', 'factory')
    hx0, hy0, hx1, hy1 = HW
    P.framed_block(g, hx0, hy0, hx1, hy1, PT, WT, infill=ORANGE, frame=CONCRETE, pitch=(hx1 - hx0) / 3,
                   corner=.2, post=.11)
    # Cornice slab capping the band; the vault springs from its top.
    blk(g, hx0 - .05, hy0 - .05, WT - .06, hx1 + .05, hy1 + .05, SPRING, CONCRETE)
    hi, ri = W.groin_vault(g, CX, CY, HALF, SPRING, RISE, overhang=.06, t=.08, segments=16)
    # Lunette infills (orange plaster) with a thermal window in each.
    for face, axis, plane, centre, out in (('front', 'Y', hy0, CX, -1), ('back', 'Y', hy1, CX, 1),
                                           ('left', 'X', hx0, CY, -1), ('right', 'X', hx1, CY, 1)):
        K.arch_infill(g, axis, plane, centre, hi + .03, SPRING, ri + .04, out, ORANGE, segments=16)
        wx, wy = (centre, plane) if axis == 'Y' else (plane, centre)
        W.thermal_window(g, face, wx, wy, SPRING + .06, .74)
    # Corner pinnacles hide the vault's springing corners.
    for x in (hx0, hx1):
        for y in (hy0, hy1):
            blk(g, x - .15, y - .15, WT - .1, x + .15, y + .15, 1.95, CONCRETE)
            blk(g, x - .17, y - .17, 1.95, x + .17, y + .17, 2.0, IRON)
            I.sphere(g, (x, y, 2.09), .07, BRASS, segments=10, rings=6)
            g.cylinder((x, y, 2.01), .025, .025, IRON, 'Z', 8)
    finial(g)


def finial(g):
    """Brass finial at the vault's crossing (the louvred steam lantern, a roof
    vent, was removed on 2026-10-30)."""
    z0 = SPRING + RISE - .1
    K.revolve(g, (CX, CY, z0), [(.16, 0), (.16, .08), (.1, .14), (.1, .22), (.04, .3), (.04, .5)], BRASS,
              segments=12)
    I.sphere(g, (CX, CY, z0 + .56), .07, BRASS, segments=10, rings=6)


# ---------------------------------------------------------------- changing wing

def changing_wing(g):
    P.podium(g, 0.0, 2.0, 2.0, 5.0, .2, joints=False, foot=False)
    zt = SIDE_TOP - SLAB
    P.framed_block(g, .06, 2.06, 1.99, 4.94, .2, zt, infill=GREYPLANK, frame=WOOD, pitch=.96,
                   corner=.14, faces=('front', 'back', 'left'))
    for y in (2.5, 3.5, 4.5):
        A.atlas_window(g, .06, y, .52, .3, 'left', 'porthole')
    A.atlas_window(g, 1.0, 2.06, .52, .3, 'front', 'porthole')
    A.atlas_window(g, 1.0, 4.94, .52, .3, 'back', 'porthole')
    deck_slab(g, .02, 2.02, HALL[0] - .05, 4.98, SIDE_TOP, 'timber', thickness=SLAB)   # clear of the hall coping
    low_parapet(g, 0.0, 2.0, 2.0, 5.0, open_side='right')


def low_parapet(g, x0, y0, x1, y1, *, open_side):
    """Low concrete parapet with an iron cap on three edges of a layer-1 roof;
    `open_side` abuts the hall."""
    t, h, z = .12, .2, SIDE_TOP
    xa = x0 - .02
    xb = x1 + .02 if open_side != 'right' else x1 - .05
    xl = x0 - .02 if open_side != 'left' else x0 + .05
    blk(g, xl, y0 - .02, z, xb, y0 - .02 + t, z + h, CONCRETE)
    blk(g, xl, y1 + .02 - t, z, xb, y1 + .02, z + h, CONCRETE)
    if open_side != 'left':
        blk(g, xa, y0 - .02 + t, z, xa + t, y1 + .02 - t, z + h, CONCRETE)
    if open_side != 'right':
        blk(g, xb - t, y0 - .02 + t, z, xb, y1 + .02 - t, z + h, CONCRETE)
    c = .02
    blk(g, xl - (c if open_side != 'left' else 0), y0 - .02 - c, z + h, xb + (c if open_side != 'right' else 0),
        y0 - .02 + t + c, z + h + .04, IRON)
    blk(g, xl - (c if open_side != 'left' else 0), y1 + .02 - t - c, z + h, xb + (c if open_side != 'right' else 0),
        y1 + .02 + c, z + h + .04, IRON)
    if open_side != 'left':
        blk(g, xa - c, y0 - .02 + t + c, z + h, xa + t + c, y1 + .02 - t - c, z + h + .04, IRON)
    if open_side != 'right':
        blk(g, xb - t - c, y0 - .02 + t + c, z + h, xb + c, y1 + .02 - t - c, z + h + .04, IRON)


# ---------------------------------------------------------------- pool court

def pool_court(g):
    x0, y0, x1, y1 = 0.0, 0.0, 2.95, 2.0     # x1 .05 short: the door portal's side panel stands on x 3
    t, h = .2, .5
    blk(g, x0, y0, 0, x1, y0 + t, h, CONCRETE)
    blk(g, x0, y1 - t, 0, x1, y1, h, CONCRETE)
    blk(g, x0, y0 + t, 0, x0 + t, y1 - t, h, CONCRETE)
    blk(g, x1 - t, y0 + t, 0, x1, y1 - t, h, CONCRETE)
    c = .02     # coping within 0.02 of the wall face: one flat face
    blk(g, x0 - c, y0 - c, h, x1 + c, y0 + t + c, h + .07, CONCRETE)
    blk(g, x0 - c, y1 - t - c, h, x1 + c, y1 + c, h + .07, CONCRETE)
    blk(g, x0 - c, y0 + t + c, h, x0 + t + c, y1 - t - c, h + .07, CONCRETE)
    blk(g, x1 - t - c, y0 + t + c, h, x1 + c, y1 - t - c, h + .07, CONCRETE)
    blk(g, x0 + t, y0 + t, .0, x1 - t, y1 - t, .08, CONCRETE)        # basin floor
    g.liquid_surfaces.append(dict(name='PlungePool', shape='Rectangle', center=[(x0 + x1) / 2, (y0 + y1) / 2],
                                  bottom=.08, top=POOL_WATER, scale=[x1 - x0 - 2 * t, y1 - y0 - 2 * t], flowOnly=False))
    # Iron pool ladder on the inner right wall (beside the entrance path).
    lx = x1 - t - .06
    for y in (.82, 1.18):
        g.box((lx, y, .36), (.04, .04, .62), IRON)
        g.beam((lx, y, .67), (lx + .08, y, .67), .04, mat=IRON)
    for k in range(3):
        g.box((lx, 1.0, .12 + k * .18), (.03, .36, .03), IRON)
    # Spout stele on the left wall with a bronze spout and its falling water.
    sy = 1.0
    blk(g, x0 + .02, sy - .3, h + .07, x0 + t - .02, sy + .3, 1.2, CONCRETE)
    blk(g, x0 - .0, sy - .34, 1.2, x0 + t + .02, sy + .34, 1.27, CONCRETE)
    I.sphere(g, (x0 + t + .01, sy, .95), .09, BRASS, segments=12, rings=6)
    I.tube(g, (x0 + t + .02, sy, .92), (x0 + t + .24, sy, .88), .04, BRASS, segments=10)
    I.tube(g, (x0 + t + .25, sy, .86), (x0 + t + .3, sy, .39), .028, WATER, segments=8)
    # Steam rising off the hot pool (vanilla SteamEngineSmoke; it plays while
    # bathers are in, EnterableParticleController via vanilla_smoke.mjs).
    for ex, ey in ((1.05, .8), (2.0, 1.25)):
        K.emitter(g, 'steam', ex, ey, POOL_WATER + .03, .3)


# ---------------------------------------------------------------- engine yard

def engine_yard(g, parts):
    """Flywheel and laundry drum on a concrete bed along the boiler-room wall
    (tiles x 4..7, y 1..2). The front row y 0..1 stays bare ground: no
    machinery leaves a mostly open tile unbuildable (BRIEF, no clutter)."""
    blk(g, 4.05, 1.0, -.03, 7.0, 1.96, .1, CONCRETE)    # clear of the door portal (x 4) and the hall foot
    fx, fy, fz, fr = 6.3, 1.4, .72, .5
    for y in (1.18, 1.62):
        blk(g, fx - .1, y - .07, .1, fx + .1, y + .07, fz - .09, CONCRETE)
        blk(g, fx - .12, y - .09, fz - .09, fx + .12, y + .09, fz - .04, IRON)
    g.cylinder((fx, 1.6, fz), .045, .92, IRON, 'Y', 10)            # shaft into the boiler room
    wheel = Geometry('Bathhouse.Flywheel', (fx, fy, fz))
    wheel.ring((fx, fy, fz), fr, .085, .12, IRON, 'Y', 16)
    wheel.ring((fx, fy, fz), fr - .085, .025, .09, BRASS, 'Y', 16)
    wheel.cylinder((fx, fy, fz), .1, .2, IRON, 'Y', 12)
    for i in range(6):
        a = i * math.pi / 3
        wheel.beam((fx, fy, fz), (fx + math.cos(a) * (fr - .07), fy, fz + math.sin(a) * (fr - .07)), .06, mat=IRON)
    wheel.ring((fx, 1.85, fz), .17, .045, .07, PAINTED, 'Y', 16)    # belt pulley
    for k in range(3):
        a = k * math.pi / 3
        wheel.beam((fx - math.cos(a) * .13, 1.85, fz - math.sin(a) * .13),
                   (fx + math.cos(a) * .13, 1.85, fz + math.sin(a) * .13), .028, mat=IRON)
    parts.append((wheel, 'SPIN_Y', 1))
    # Laundry (towel) drum on two iron A-frames, belt-driven from the shaft.
    dx, dz, dr = 4.7, .55, .32
    for y in (1.15, 1.72):
        for s in (-1, 1):
            g.beam((dx + s * .3, y, .1), (dx + s * .03, y, dz - .02), .055, mat=IRON)
        blk(g, dx - .055, y - .04, dz - .055, dx + .055, y + .04, dz + .055, IRON)
    g.cylinder((dx, 1.5, dz), .032, .9, IRON, 'Y', 8)
    drum = Geometry('Bathhouse.LaundryDrum', (dx, 1.45, dz))
    drum.cylinder((dx, 1.45, dz), dr, .36, FORGED, 'Y', 12)
    for y in (1.3, 1.45, 1.6):
        drum.ring((dx, y, dz), dr + .02, .035, .04, IRON, 'Y', 12)
    drum.ring((dx + .15, 1.255, dz + .07), .09, .028, .02, BRASS, 'Y', 14)   # loading hatch
    drum.cylinder((dx + .15, 1.255, dz + .07), .068, .01, IRON, 'Y', 12)
    drum.ring((dx, 1.85, dz), .2, .045, .07, PAINTED, 'Y', 16)              # driven pulley
    parts.append((drum, 'SPIN_Y', .5))
    # Belt runs (static) between the pulleys.
    for s in (-1, 1):
        a = (fx, 1.85, fz + s * .17)
        b = (dx, 1.85, dz + s * .2)
        g.beam(a, b, .05, .013, IRON)


# ---------------------------------------------------------------- boiler room

def boiler_room(g, parts):
    # Concrete room (one layer) with a recess for the Water pipe socket in the
    # back face; the roof slab is the lintel over the recess.
    zt = SIDE_TOP - SLAB
    rx0, rx1, ry = 6.15, 6.85, 4.7
    blk(g, 5.0, 2.0, 0, rx0, 5.0, zt, CONCRETE)
    blk(g, rx1, 2.0, 0, 7.0, 5.0, zt, CONCRETE)
    blk(g, rx0, 2.0, 0, rx1, ry, zt, CONCRETE)
    deck_slab(g, HALL[2] + .05, 2.0, 7.0, 5.0, SIDE_TOP, 'forged', thickness=SLAB)    # clear of the hall coping
    blk(g, 4.98, 1.98, zt - .12, 7.02, 5.02, zt - .02, CONCRETE)       # string course
    sx, sy, sz = PIPE_INLET['socket']
    g.box((sx, sy - .12, sz), (.44, .2, .44), PAINTED)
    g.cylinder((sx, sy + .02, sz), .15, .12, IRON, 'Y', 16)
    g.ring((sx, sy + .085, sz), .2, .06, .04, BRASS, 'Y', 16)
    K.bolt_row(g, (sx - .16, sy + .11, sz + .14), (sx + .16, sy + .11, sz + .14), 3, r=.016)
    for y in (2.5, 3.5, 4.5):
        P.native_window(g, 7.0, y, .4, .45, 'right', 'factory')
    P.native_window(g, 5.5, 5.0, .4, .45, 'back', 'factory')
    P.native_window(g, 5.5, 2.0, .4, .45, 'front', 'factory')
    low_parapet(g, 5.0, 2.0, 7.0, 5.0, open_side='left')
    # Boiler chimney rising from the ground in the back wall (tile (5,4)),
    # mouth above 4 so its steam does not bar the roof deck round it.
    cx0, cy0, cx1, cy1 = 5.1, 4.55, 5.5, 4.95
    blk(g, cx0, cy0, -.03, cx1, cy1, 4.3, CONCRETE)
    for z in (1.4, 2.6, 3.7):
        blk(g, cx0 - .03, cy0 - .03, z, cx1 + .03, cy1 + .03, z + .08, IRON)
    blk(g, cx0 - .05, cy0 - .05, 4.3, cx1 + .05, cy1 + .05, 4.42, IRON)
    K.emitter(g, 'steam', (cx0 + cx1) / 2, (cy0 + cy1) / 2, 4.45, .15)
    # Safety valve on a bracket off the chimney's front face (same tile):
    # steam dome, fulcrum and the weighted lever.
    mx, vy = 5.3, 4.3
    base = 1.6
    blk(g, mx - .18, vy - .18, base - .08, mx + .18, vy + .18, base, IRON)
    blk(g, mx - .05, vy + .1, base - .2, mx + .05, cy0 + .02, base - .02, IRON)
    K.revolve(g, (mx, vy, base), [(.17, 0), (.17, .2), (.1, .28), (.05, .3)], IRON, segments=16)
    K.band(g, (mx, vy, 0), .17, base + .14, .045, BRASS, segments=16)
    g.cylinder((mx, vy, base + .39), .04, .18, BRASS, 'Z', 10)
    blk(g, mx - .14, vy - .03, base + .22, mx - .09, vy + .03, base + .54, IRON)
    lever = Geometry('Bathhouse.SafetyValveLever', (mx - .115, vy, base + .5))
    lever.box((mx + .14, vy, base + .5), (.54, .035, .035), IRON)
    I.sphere(lever, (mx + .4, vy, base + .47), .07, BRASS, segments=12, rings=6)
    lever.cylinder((mx - .115, vy, base + .5), .025, .09, IRON, 'Y', 8)
    parts.append((lever, 'SWAY_Y', .1))


# ---------------------------------------------------------------- grounds

def build(g, parts):
    hall(g, parts)
    changing_wing(g)
    pool_court(g)
    engine_yard(g, parts)
    boiler_room(g, parts)
