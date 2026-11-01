"""Bathhouse: late-game steam baths heated by an engine-driven boiler.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the colonnaded portico, the planter with shrubs and the lamp standard;
the plunge-pool court stays.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale): 9x7x11 -> 7x5x5 (3 x 3 vaulted hall, one-layer changing wing and
boiler room, open engine yard).

Second shrink 2026-11-01 (a YouTuber called the late buildings "massive" and
did not like this one's look; user: "shrink the buildings down even more"):
7x5x5 -> 4x4x3, inside the old footprint with the same origin, door (3.5, 2)
and native entrance cell (3, 1, 0), so a saved bathhouse keeps its path. It
now reads as one building instead of a hall with loose annexes: a brick bath
house with stone dressings round its pool court. The 2 x 2 vaulted bath hall
stands behind the open plunge pool (unchanged, six bathers); the boiler house
beside it is one layer of the same brick under a timber roof deck, its
chimney rising from the ground in the back wall with the safety valve on it;
the engine yard's flywheel and laundry drum now turn in an engine bay in the
boiler house's side wall. The free front-right tiles stay the door's
approach (the entrance cell and the tile before it).

HERO (kept as the silhouette): a cross-vaulted (groin-vaulted) bath hall:
four teal plank barrel quarters meeting in valley groins, each ending in an
iron-banded arch over a semicircular thermal window, with a brass finial at
the crossing.
ROOF: groin vault in teal roof planks (its silhouette); the boiler house's
flat roof is an open timber deck on layer 1, edge to edge (no parapets).

Plan (4 x 4 tiles; front y = 0):
  x 0..3, y 0..2  plunge-pool court (unchanged): cast basin with native water,
                  bronze spout stele, six bathers.
  x 3, y 0..2     the door's approach: (3, 1) is the native entrance cell.
  x 2..4, y 2..4  bath hall: rusticated concrete ground storey (top layer 1)
                  with the door centred on x = 3.5, face on the y = 2 tile
                  edge, brick band with stone dressings, cornice, groin vault.
  x 0..2, y 2..4  boiler house (brick, one layer, timber roof deck): engine
                  bay in its left wall (flywheel and laundry drum), chimney in
                  its back wall on tile (1, 3) with the safety valve, Water
                  pipe socket in a recess at its back (cell (1, 3, 0), Up).

Animated (unchanged names): flywheel and laundry drum (now SPIN_X: their
shafts run into the bay's back wall), safety-valve weighted lever (SWAY_Y).
Emitters: steam at the chimney mouth and off the pool.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, WATER, LAYER_GAP, BRICK
import lategame_civic_parts as P
from lategame_civic_parts import blk, obox
import lategame_industry_parts as I
import native_window_atlas as A
import native_building_assets as N
import civic_wellbeing_parts as W
from lategame_roofdeck_parts import deck_slab
from civic_wellbeing_parts import animate  # noqa: F401  (CUSTOM_ kinds)

IDENT = 'Bathhouse'
FOOTPRINT = (4, 4)
HEIGHT = 3
FRAME_END = 121
HERO = ('Cross-vaulted bath hall: four teal plank barrel quarters meeting in groins, iron-banded arches over '
        'semicircular thermal windows, and a brass finial at the crossing.')

# Bath water arrives by Timber Pipes at the boiler house's back recess
# (same record shape as the NuclearReactor coolant inlet).
PIPE_INLET = {'cell': [1, 3, 0], 'direction': 'Up', 'state': 'OpenIn', 'good': 'Water',
              'socket': [1.2, 3.84, .45]}

HALL = (2.0, 2.0, 4.0, 4.0)          # ground storey on whole tiles
PT = 1.0                              # ground storey top: one layer
HW = (2.06, 2.06, 3.94, 3.94)         # brick band, set back 0.06
WT = 1.34                             # band top
CX, CY = 3.0, 3.0
SPRING, RISE, HALF = 1.46, .68, .94   # springing on the cornice top
DOOR_X = 3.5
SIDE_TOP = 1.0                        # boiler house roof deck, layer 1
SLAB = .16

# Visitor seats (export_lategame_models.bathhouse_slots writes them as native
# '#Slot#Spot<i>' empties; Sitting animation as on the vanilla MudBath).
# Native FixedSlotManager needs a slot per visitor (capacity 12): the six pool
# seats first, the other six inside the closed hall, unseen, as before.
POOL_WATER = .38                      # plunge-pool water surface (pool_court)
BATH_SEATS = [(.75, 1.58, .08, 0, -1), (1.5, 1.58, .08, 0, -1), (2.25, 1.58, .08, 0, -1),
              (.75, .42, .08, 0, 1), (1.5, .42, .08, 0, 1), (2.25, .42, .08, 0, 1)]
HALL_SEATS = [(x, y, PT, 0, 1) for y in (2.9, 3.5) for x in (2.4, 3.0, 3.6)]


# ---------------------------------------------------------------- bath hall

def hall(g, parts):
    x0, y0, x1, y1 = HALL
    P.podium(g, x0, y0, x1, y1, PT, skip=[(DOOR_X - .5, DOOR_X + .5)])
    P.door(g, DOOR_X, y0, 0, 'Door0')
    # One lamp: the door stands on the hall's right half, at its corner.
    K.lamp(g, DOOR_X - .64, y0, .5, face='front')
    P.native_window(g, 2.42, y0, .47, .45, 'front', 'factory')
    for x in (2.5, 3.5):
        P.native_window(g, x, y1, .47, .45, 'back', 'factory')
    for y in (2.5, 3.5):
        P.native_window(g, x1, y, .47, .45, 'right', 'factory')
    hx0, hy0, hx1, hy1 = HW
    P.framed_block(g, hx0, hy0, hx1, hy1, PT, WT, infill=BRICK, frame=CONCRETE, pitch=(hx1 - hx0) / 2,
                   corner=.2, post=.11)
    # Cornice slab capping the band; the vault springs from its top.
    blk(g, hx0 - .05, hy0 - .05, WT - .06, hx1 + .05, hy1 + .05, SPRING, CONCRETE)
    hi, ri = W.groin_vault(g, CX, CY, HALF, SPRING, RISE, overhang=.06, t=.07, segments=16)
    # Lunette infills (orange plaster) with a thermal window in each.
    for face, axis, plane, centre, out in (('front', 'Y', hy0, CX, -1), ('back', 'Y', hy1, CX, 1),
                                           ('left', 'X', hx0, CY, -1), ('right', 'X', hx1, CY, 1)):
        K.arch_infill(g, axis, plane, centre, hi + .03, SPRING, ri + .04, out, ORANGE, segments=16)
        wx, wy = (centre, plane) if axis == 'Y' else (plane, centre)
        W.thermal_window(g, face, wx, wy, SPRING + .05, .48)
    # Corner pinnacles hide the vault's springing corners.
    for x in (hx0, hx1):
        for y in (hy0, hy1):
            blk(g, x - .13, y - .13, WT - .1, x + .13, y + .13, 1.80, CONCRETE)
            blk(g, x - .15, y - .15, 1.80, x + .15, y + .15, 1.85, IRON)
            I.sphere(g, (x, y, 1.93), .06, BRASS, segments=10, rings=6)
            g.cylinder((x, y, 1.86), .022, .022, IRON, 'Z', 8)
    finial(g)


def finial(g):
    """Brass finial at the vault's crossing."""
    z0 = SPRING + RISE - .08
    K.revolve(g, (CX, CY, z0), [(.13, 0), (.13, .07), (.08, .12), (.08, .19), (.035, .26), (.035, .42)], BRASS,
              segments=12)
    I.sphere(g, (CX, CY, z0 + .48), .06, BRASS, segments=10, rings=6)


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


# ---------------------------------------------------------------- boiler house

BAY = (.45, 2.16, 3.56)               # engine bay: depth into the left wall, y range


def boiler_house(g, parts):
    """Brick boiler house (x 0..2, y 2..4), one layer under a timber roof deck,
    with the arched engine bay in its left wall and the pipe recess at its back."""
    zt = SIDE_TOP - SLAB
    P.podium(g, 0.0, 2.0, 2.0, 4.0, .2, joints=False, foot=False)
    bd, by0, by1 = BAY
    rx0, rx1, ry = .93, 1.47, 3.70     # pipe recess
    # Brick core in pieces round the engine bay and the pipe recess.
    blk(g, bd, 2.06, .2, 1.99, ry, zt, BRICK)
    blk(g, bd, ry, .2, rx0, 3.94, zt, BRICK)
    blk(g, rx1, ry, .2, 1.99, 3.94, zt, BRICK)
    blk(g, .06, 2.06, .2, bd, by0, zt, BRICK)
    blk(g, .06, by1, .2, bd, 3.94, zt, BRICK)
    # Stone dressings: corner posts and a string course under the deck on the
    # front and back faces (the bay and recess heads are the deck slab).
    for y in (2.06, 3.94):
        blk(g, -.01, y - .07, .2, .13, y + .07, zt - .01, CONCRETE)
    for ya, yb in ((1.99, 2.07), (3.93, 4.0)):
        blk(g, .13, ya, zt - .12, 1.95, yb, zt - .03, CONCRETE)
    deck_slab(g, .02, 2.02, HALL[0] - .05, 3.98, SIDE_TOP, 'timber', thickness=SLAB)   # clear of the hall coping
    # Windows: a porthole over the pool and one at the back.
    A.atlas_window(g, 1.2, 2.06, .66, .26, 'front', 'porthole')
    A.atlas_window(g, .55, 3.94, .52, .26, 'back', 'porthole')
    # Water pipe socket in the back recess.
    sx, sy, sz = PIPE_INLET['socket']
    g.box((sx, sy - .12, sz), (.40, .2, .40), PAINTED)
    g.cylinder((sx, sy + .02, sz), .14, .12, IRON, 'Y', 16)
    g.ring((sx, sy + .075, sz), .18, .05, .035, BRASS, 'Y', 16)
    K.bolt_row(g, (sx - .14, sy + .1, sz + .13), (sx + .14, sy + .1, sz + .13), 3, r=.015)
    engine_bay(g, parts)
    chimney(g, parts)


def engine_bay(g, parts):
    """Flywheel and laundry drum on shafts into the bay's back wall, belted."""
    bd, by0, by1 = BAY
    blk(g, .04, by0, .2, bd, by1, .26, CONCRETE)       # bay floor
    fx, fy, fz, fr = .2, 2.56, .54, .27
    g.cylinder((.32, fy, fz), .035, .26, IRON, 'X', 10)     # shaft into the wall
    wheel = Geometry('Bathhouse.Flywheel', (fx, fy, fz))
    wheel.ring((fx, fy, fz), fr, .07, .09, IRON, 'X', 16)
    wheel.ring((fx, fy, fz), fr - .07, .02, .07, BRASS, 'X', 16)
    wheel.cylinder((fx, fy, fz), .07, .14, IRON, 'X', 12)
    for i in range(6):
        a = i * math.pi / 3
        wheel.beam((fx, fy, fz), (fx, fy + math.cos(a) * (fr - .06), fz + math.sin(a) * (fr - .06)), .05, mat=IRON)
    wheel.ring((.37, fy, fz), .12, .035, .05, PAINTED, 'X', 16)    # belt pulley
    parts.append((wheel, 'SPIN_X', 1))
    dx, dy, dz, dr = .2, 3.2, .48, .21
    g.cylinder((.32, dy, dz), .03, .26, IRON, 'X', 8)
    drum = Geometry('Bathhouse.LaundryDrum', (dx, dy, dz))
    drum.cylinder((dx, dy, dz), dr, .26, FORGED, 'X', 12)
    for x in (.1, .2, .3):
        drum.ring((x, dy, dz), dr + .015, .03, .03, IRON, 'X', 12)
    drum.ring((.37, dy, dz), .15, .035, .05, PAINTED, 'X', 16)     # driven pulley
    parts.append((drum, 'SPIN_X', .5))
    for s in (-1, 1):
        g.beam((.37, fy, fz + s * .12), (.37, dy, dz + s * .15), .012, .04, IRON)


def chimney(g, parts):
    """Boiler chimney rising from the ground in the back wall (tile (1, 3)),
    with the safety valve bracketed off its front face on the same tile."""
    cx0, cy0, cx1, cy1 = 1.52, 3.56, 1.9, 3.94
    blk(g, cx0, cy0, -.03, cx1, cy1, 2.8, BRICK)
    for z in (1.5, 2.2):
        blk(g, cx0 - .03, cy0 - .03, z, cx1 + .03, cy1 + .03, z + .07, IRON)
    blk(g, cx0 - .05, cy0 - .05, 2.8, cx1 + .05, cy1 + .05, 2.9, IRON)
    K.emitter(g, 'steam', (cx0 + cx1) / 2, (cy0 + cy1) / 2, 2.93, .14)
    mx, vy = 1.71, 3.3
    base = 1.38
    blk(g, mx - .15, vy - .15, base - .07, mx + .15, vy + .15, base, IRON)
    blk(g, mx - .05, vy + .1, base - .2, mx + .05, cy0 + .02, base - .02, IRON)
    K.revolve(g, (mx, vy, base), [(.14, 0), (.14, .17), (.08, .24), (.04, .26)], IRON, segments=16)
    K.band(g, (mx, vy, 0), .14, base + .12, .04, BRASS, segments=16)
    g.cylinder((mx, vy, base + .34), .035, .16, BRASS, 'Z', 10)
    blk(g, mx - .12, vy - .03, base + .19, mx - .08, vy + .03, base + .47, IRON)
    lever = Geometry('Bathhouse.SafetyValveLever', (mx - .1, vy, base + .44))
    lever.box((mx + .07, vy, base + .44), (.4, .03, .03), IRON)
    I.sphere(lever, (mx + .25, vy, base + .41), .055, BRASS, segments=12, rings=6)
    lever.cylinder((mx - .1, vy, base + .44), .022, .08, IRON, 'Y', 8)
    parts.append((lever, 'SWAY_Y', .1))


# ---------------------------------------------------------------- grounds

def build(g, parts):
    hall(g, parts)
    boiler_house(g, parts)
    pool_court(g)
