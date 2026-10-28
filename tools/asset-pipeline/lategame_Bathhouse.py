"""Bathhouse: late-game steam baths heated by an engine-driven boiler plant.

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the colonnaded portico, the planter with shrubs and the lamp standard;
the plunge-pool court stays.

HERO: a cross-vaulted (groin-vaulted) bath hall: four teal plank barrel
quarters meeting in valley groins, each ending in an iron-banded arch over a
semicircular thermal (Diocletian) window, with a louvred steam lantern at the
crossing. No other study has a groin vault or thermal windows.
ROOF: groin vault on the hall; classical plank pediment on the portico;
plank gable on the boiler room; lean-to roofs on the changing wing and the
engine shed.

Plan (9 x 7 tiles; front y = 0):
  x 1..6, y 2..7  bath hall on a rusticated concrete podium (top layer 1.2),
                  orange plaster upper walls set back 0.15, clerestory ribbons
                  above the side wings, thermal windows in all four lunettes.
  x 1..6, y 0..2  colonnaded portico: six concrete columns on the grid lines
                  x = 1..6 and a plank pediment with a gear tympanum. The door
                  is centred on x = 3.5 with its face on the y = 2 tile edge;
                  its path cell (3,1,0) between the columns stays free.
  x 0..1, y 2..7  changing-room wing, grey-plank timber frame, portholes.
  x 6..9, y 0..3  plunge-pool court: cast basin with native water and a
                  bronze spout stele.
  x 6..9, y 3..4  open engine shed: flywheel and a belt-driven laundry drum.
  x 6..9, y 4..7  boiler room (forged sheet in a timber frame) with the steam
                  stack, a safety valve on the ridge and the steam main to
                  the hall; the Water pipe socket sits in a recess at its back.

Animated: flywheel (SPIN_Y), laundry/towel drum (SPIN_Y), safety-valve
weighted lever (SWAY_Y).
Emitters: steam at the stack mouth and at the lantern vent.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, WATER, LAYER_GAP
import lategame_civic_parts as P
from lategame_civic_parts import blk, obox
import lategame_industry_parts as I
from lategame_mining_parts import plank_gable, plank_slope, lean_to
import native_window_atlas as A
import native_building_assets as N
import civic_wellbeing_parts as W
from civic_wellbeing_parts import animate  # noqa: F401  (CUSTOM_ kinds)

IDENT = 'Bathhouse'
FOOTPRINT = (9, 7)
HEIGHT = 11
FRAME_END = 121
HERO = ('Cross-vaulted bath hall: four teal plank barrel quarters meeting in groins, iron-banded arches over '
        'semicircular thermal windows, and a louvred steam lantern at the crossing.')

# Bath water arrives by Timber Pipes at the boiler room's back recess
# (same record shape as the NuclearReactor coolant inlet).
PIPE_INLET = {'cell': [7, 6, 0], 'direction': 'Up', 'state': 'OpenIn', 'good': 'Water',
              'socket': [7.5, 6.84, .45]}

HALL = (1.0, 2.0, 6.0, 7.0)          # podium on whole tiles
PT = 1.2                              # podium top
HW = (1.15, 2.15, 5.85, 6.85)         # upper walls, set back 0.15
WT = 3.9                              # wall top
CX, CY = 3.5, 4.5
SPRING, RISE, HALF = 4.0, 2.0, 2.35    # springing on the cornice top, exactly layer 4
DOOR_X = 3.5

# Visitor seats (export_lategame_models.bathhouse_slots writes them as native
# '#Slot#Spot<i>' empties; Sitting animation as on the vanilla MudBath, not a
# WaterSlot: the pool water is the model's own surface, not world water).
# Native FixedSlotManager needs a slot per visitor (capacity 12), so the
# bathers fill the six pool seats first and the other six sit inside the
# closed hall, unseen, as before. (x, y, seat z, facing x, facing y).
POOL_WATER = .42                      # plunge-pool water surface (pool_court)
BATH_SEATS = [(6.75, 2.42, .08, 0, -1), (7.5, 2.42, .08, 0, -1), (8.25, 2.42, .08, 0, -1),
              (6.58, 1.7, .08, 1, 0), (6.58, 1.0, .08, 1, 0), (8.3, .6, .08, -1, 1)]
HALL_SEATS = [(x, y, PT, 0, 1) for y in (3.8, 5.2) for x in (2.5, 3.5, 4.5)]


# ---------------------------------------------------------------- bath hall

def hall(g, parts):
    x0, y0, x1, y1 = HALL
    P.podium(g, x0, y0, x1, y1, PT, skip=[(DOOR_X - .5, DOOR_X + .5)])
    P.door(g, DOOR_X, y0, 0, 'Door0')
    K.lamp(g, DOOR_X - .66, y0, 1.02, face='front')
    K.lamp(g, DOOR_X + .66, y0, 1.02, face='front')
    for x in (1.55, 2.4, 4.6, 5.45):
        P.native_window(g, x, y0, .62, .62, 'front', 'factory')
    for x in (1.5, 2.5, 3.5, 4.5, 5.5):
        P.native_window(g, x, y1, .62, .7, 'back', 'factory')
    hx0, hy0, hx1, hy1 = HW
    bays = [hx0 + (hx1 - hx0) * (i + .5) / 5 for i in range(5)]
    P.framed_block(g, hx0, hy0, hx1, hy1, PT, WT, infill=ORANGE, frame=CONCRETE, pitch=(hx1 - hx0) / 5,
                   corner=.2, post=.11,
                   windows={'back': [(x, 2.55, 1.05, 'grand') for x in bays]})
    # Clerestory ribbons above the side wings, and the portico's outer bays.
    for y in bays:
        A.atlas_window(g, hx0, y, 3.56, .68, 'left', 'ribbon')
        A.atlas_window(g, hx1, y, 3.56, .68, 'right', 'ribbon')
    for x in (bays[0], bays[4]):
        A.atlas_window(g, x, hy0, 3.56, .68, 'front', 'ribbon')
    # Cornice slab capping the walls; the vault springs from its top.
    blk(g, hx0 - .1, hy0 - .1, WT - .08, hx1 + .1, hy1 + .1, SPRING, CONCRETE)
    hi, ri = W.groin_vault(g, CX, CY, HALF, SPRING, RISE, overhang=.12, t=.1, segments=16)
    # Lunette infills (orange plaster) with a thermal window in each.
    for face, axis, plane, centre, out in (('front', 'Y', hy0, CX, -1), ('back', 'Y', hy1, CX, 1),
                                           ('left', 'X', hx0, CY, -1), ('right', 'X', hx1, CY, 1)):
        K.arch_infill(g, axis, plane, centre, hi + .03, SPRING, ri + .04, out, ORANGE, segments=16)
        wx, wy = (centre, plane) if axis == 'Y' else (plane, centre)
        W.thermal_window(g, face, wx, wy, SPRING + .1, 1.42)
    # Corner pinnacles hide the vault's springing corners.
    for x in (hx0, hx1):
        for y in (hy0, hy1):
            blk(g, x - .17, y - .17, WT - .12, x + .17, y + .17, 4.72, CONCRETE)
            blk(g, x - .19, y - .19, 4.72, x + .19, y + .19, 4.78, IRON)
            I.sphere(g, (x, y, 4.88), .085, BRASS, segments=10, rings=6)
            g.cylinder((x, y, 4.79), .03, .03, IRON, 'Z', 8)
    lantern(g)


def lantern(g):
    """Louvred steam lantern at the crossing (round, never octagonal)."""
    z0 = SPRING + RISE - .15
    K.revolve(g, (CX, CY, z0), [(.4, 0), (.4, .85)], IRON, segments=12)
    for k in range(5):
        K.band(g, (CX, CY, 0), .4, z0 + .25 + k * .11, .05, FORGED, segments=12, proud=.03)
    K.band(g, (CX, CY, 0), .4, z0 + .06, .1, IRON, segments=12, proud=.05)
    top = z0 + .85
    K.revolve(g, (CX, CY, top), [(.56, 0), (.56, .05), (.09, .44), (.09 - .001, .445)], ROOF, segments=12)
    K.revolve(g, (CX, CY, top + .44), [(.07, 0), (.07, .26)], IRON, segments=10)
    g.ring((CX, CY, top + .68), .1, .04, .05, BRASS, 'Z', 10)
    K.emitter(g, 'steam', CX, CY, top + .705, .07)


# ---------------------------------------------------------------- changing wing

def changing_wing(g):
    P.podium(g, 0.0, 2.0, 1.0, 7.0, .5, joints=False, foot=False)
    zt = 2.45
    P.framed_block(g, .06, 2.06, HW[0], 6.94, .5, zt, infill=GREYPLANK, frame=WOOD, pitch=.98,
                   corner=.14, faces=('front', 'back', 'left'))
    ys = [2.06 + (6.94 - 2.06) * (i + .5) / 5 for i in range(5)]
    for y in ys:
        A.atlas_window(g, .06, y, 1.55, .38, 'left', 'porthole')
    A.atlas_window(g, .6, 2.06, 1.55, .34, 'front', 'porthole')
    A.atlas_window(g, .6, 6.94, 1.55, .34, 'back', 'porthole')
    lean_to(g, .06, HW[0] + .06, 2.06, 6.94, zt, 3.12, low_side='left', overhang=.1, seed=5)
    # Gable triangles closing the wedge under the lean-to at both ends.
    slope = (3.12 - zt) / (HW[0] + .06 - .06)
    tri = [(.06, zt), (HW[0], zt), (HW[0], zt + slope * (HW[0] - .06) - .01)]
    K.extrude_profile(g, tri, 2.06, 2.14, PLANK, axis='Y')
    K.extrude_profile(g, tri, 6.86, 6.94, PLANK, axis='Y')


# ---------------------------------------------------------------- pool court

def pool_court(g):
    x0, y0, x1, y1 = 6.0, 0.0, 9.0, 3.0
    t, h = .25, .55
    blk(g, x0, y0, 0, x1, y0 + t, h, CONCRETE)
    blk(g, x0, y1 - t, 0, x1, y1, h, CONCRETE)
    blk(g, x0, y0 + t, 0, x0 + t, y1 - t, h, CONCRETE)
    blk(g, x1 - t, y0 + t, 0, x1, y1 - t, h, CONCRETE)
    c = .03
    blk(g, x0 - c, y0 - c, h, x1 + c, y0 + t + c, h + .07, CONCRETE)
    blk(g, x0 - c, y1 - t - c, h, x1 + c, y1 + c, h + .07, CONCRETE)
    blk(g, x0 - c, y0 + t + c, h, x0 + t + c, y1 - t - c, h + .07, CONCRETE)
    blk(g, x1 - t - c, y0 + t + c, h, x1 + c, y1 - t - c, h + .07, CONCRETE)
    blk(g, x0 + t, y0 + t, .0, x1 - t, y1 - t, .08, CONCRETE)        # basin floor
    g.liquid_surfaces.append(dict(name='PlungePool', shape='Rectangle', center=[(x0 + x1) / 2, (y0 + y1) / 2],
                                  bottom=.08, top=POOL_WATER, scale=[x1 - x0 - 2 * t, y1 - y0 - 2 * t], flowOnly=False))
    # Iron pool ladder on the inner front wall.
    for x in (7.32, 7.68):
        g.box((x, y0 + t + .06, .4), (.04, .04, .7), IRON)
        g.beam((x, y0 + t + .06, .75), (x, y0 + t - .02, .75), .04, mat=IRON)
    for k in range(3):
        g.box((7.5, y0 + t + .06, .12 + k * .2), (.36, .03, .03), IRON)
    # Spout stele on the side wall (clear of the engine yard behind) with a
    # bronze spout and its falling water.
    sy = 1.5
    blk(g, x1 - t + .02, sy - .35, h + .07, x1 - .02, sy + .35, 1.42, CONCRETE)
    blk(g, x1 - t - .02, sy - .39, 1.42, x1 + .0, sy + .39, 1.5, CONCRETE)
    I.sphere(g, (x1 - t - .01, sy, 1.14), .1, BRASS, segments=12, rings=6)
    I.tube(g, (x1 - t - .02, sy, 1.1), (x1 - t - .26, sy, 1.06), .045, BRASS, segments=10)
    I.tube(g, (x1 - t - .27, sy, 1.04), (x1 - t - .33, sy, .43), .03, WATER, segments=8)
    # Steam rising off the hot pool (vanilla SteamEngineSmoke; it plays while
    # bathers are in, EnterableParticleController via vanilla_smoke.mjs).
    for ex, ey in ((7.05, 1.15), (7.95, 1.95)):
        K.emitter(g, 'steam', ex, ey, POOL_WATER + .03, .3)


# ---------------------------------------------------------------- engine shed

def engine_shed(g, parts):
    y0, y1 = 3.0, 4.08
    # Concrete bed and pedestals.
    blk(g, 6.0, 3.0, 0, 9.0, 4.0, .1, CONCRETE)
    fx, fy, fz, fr = 8.2, 3.45, 1.2, .7
    for y in (3.16, 3.74):
        blk(g, fx - .11, y - .08, .1, fx + .11, y + .08, fz - .1, CONCRETE)
        blk(g, fx - .13, y - .1, fz - .1, fx + .13, y + .1, fz - .04, IRON)
    g.cylinder((fx, 3.6, fz), .05, 1.0, IRON, 'Y', 10)           # shaft into the boiler room
    wheel = Geometry('Bathhouse.Flywheel', (fx, fy, fz))
    wheel.ring((fx, fy, fz), fr, .1, .14, IRON, 'Y', 16)
    wheel.ring((fx, fy, fz), fr - .1, .03, .1, BRASS, 'Y', 16)
    wheel.cylinder((fx, fy, fz), .12, .22, IRON, 'Y', 12)
    for i in range(6):
        a = i * math.pi / 3
        wheel.beam((fx, fy, fz), (fx + math.cos(a) * (fr - .08), fy, fz + math.sin(a) * (fr - .08)), .07, mat=IRON)
    wheel.ring((fx, 3.95, fz), .2, .05, .08, PAINTED, 'Y', 16)    # belt pulley
    for k in range(3):
        a = k * math.pi / 3
        wheel.beam((fx - math.cos(a) * .16, 3.95, fz - math.sin(a) * .16),
                   (fx + math.cos(a) * .16, 3.95, fz + math.sin(a) * .16), .03, mat=IRON)
    parts.append((wheel, 'SPIN_Y', 1))
    # Laundry (towel) drum on two iron A-frames, belt-driven from the shaft.
    dx, dz, dr = 6.78, 1.0, .46
    for y in (3.14, 3.84):
        for s in (-1, 1):
            g.beam((dx + s * .42, y, .1), (dx + s * .03, y, dz - .02), .07, mat=IRON)
        blk(g, dx - .07, y - .05, dz - .07, dx + .07, y + .05, dz + .07, IRON)
    g.cylinder((dx, 3.53, dz), .04, .92, IRON, 'Y', 8)
    drum = Geometry('Bathhouse.LaundryDrum', (dx, 3.5, dz))
    drum.cylinder((dx, 3.5, dz), dr, .56, FORGED, 'Y', 12)
    for y in (3.28, 3.5, 3.72):
        drum.ring((dx, y, dz), dr + .025, .05, .05, IRON, 'Y', 12)
    drum.ring((dx + .22, 3.215, dz + .1), .12, .035, .025, BRASS, 'Y', 14)   # loading hatch
    drum.cylinder((dx + .22, 3.215, dz + .1), .09, .012, IRON, 'Y', 12)
    drum.ring((dx, 3.95, dz), .26, .05, .08, PAINTED, 'Y', 16)              # driven pulley
    parts.append((drum, 'SPIN_Y', .5))
    # Belt runs (static) between the pulleys.
    for s in (-1, 1):
        a = (fx, 3.95, fz + s * .2)
        b = (dx, 3.95, dz + s * .26)
        g.beam(a, b, .06, .015, IRON)


# ---------------------------------------------------------------- boiler room

def boiler_room(g, parts):
    # Podium with a recess for the Water pipe socket in the back face.
    zt = .6
    rx0, rx1, ry = 7.15, 7.85, 6.7
    blk(g, 6.0, 4.0, 0, rx0, 7.0, zt - .03, CONCRETE)
    blk(g, rx1, 4.0, 0, 9.0, 7.0, zt - .03, CONCRETE)
    blk(g, rx0, 4.0, 0, rx1, ry, zt - .03, CONCRETE)
    blk(g, 5.98, 3.98, zt - .1, 9.02, 7.02, zt, CONCRETE)        # coping (lintel over the recess)
    sx, sy, sz = PIPE_INLET['socket']
    g.box((sx, sy - .12, sz), (.44, .2, .44), PAINTED)
    g.cylinder((sx, sy + .02, sz), .15, .12, IRON, 'Y', 16)
    g.ring((sx, sy + .085, sz), .2, .06, .04, BRASS, 'Y', 16)
    K.bolt_row(g, (sx - .16, sy + .11, sz + .14), (sx + .16, sy + .11, sz + .14), 3, r=.016)
    # Walls: forged sheet in a dark timber frame; no posts on the hall side.
    bx0, by0, bx1, by1 = HW[2], 4.08, 8.92, 6.92
    top = 3.0
    ys = [by0 + (by1 - by0) * (i + .5) / 3 for i in range(3)]
    P.framed_block(g, bx0, by0, bx1, by1, zt, top, infill=FORGED, frame=WOOD, pitch=(by1 - by0) / 3,
                   corner=.17, faces=('front', 'back', 'right'),
                   windows={'right': [(y, 1.75, .8, 'factory') for y in ys],
                            'front': [(6.36, 2.32, .7, 'factory'), (8.41, 2.32, .7, 'factory')],
                            'back': [(6.36, 1.75, .8, 'factory'), (8.41, 1.75, .8, 'factory')]})
    # Overhang .08: the eave plank ends (x 5.77) clear the hall corner post face (x 5.75).
    plank_gable(g, bx0, bx1, by0, by1, top, 4.0, ridge_axis='Y', overhang=.08, gable=True, seed=8)
    # Steam stack through the roof (flare buried in the wall core).
    K.stack(g, 8.4, 6.4, 2.2, 8.2, emits='steam', r=.3, taper=.75, bands=5)
    # Safety valve on the ridge: steam dome, fulcrum and the weighted lever.
    mx = (bx0 + bx1) / 2
    vy = 5.0
    K.revolve(g, (mx, vy, 3.95), [(.2, 0), (.2, .22), (.12, .32), (.06, .34)], IRON, segments=16)
    K.band(g, (mx, vy, 0), .2, 4.1, .05, BRASS, segments=16)
    g.cylinder((mx, vy, 4.37), .045, .2, BRASS, 'Z', 10)
    blk(g, mx - .16, vy - .03, 4.2, mx - .1, vy + .03, 4.55, IRON)
    lever = Geometry('Bathhouse.SafetyValveLever', (mx - .13, vy, 4.5))
    lever.box((mx + .16, vy, 4.5), (.62, .04, .04), IRON)
    I.sphere(lever, (mx + .46, vy, 4.47), .08, BRASS, segments=12, rings=6)
    lever.cylinder((mx - .13, vy, 4.5), .03, .1, IRON, 'Y', 8)
    parts.append((lever, 'SWAY_Y', .1))
    # Steam main from the boiler room along the hall wall into the hall.
    z = 3.3
    I.pipe(g, [(6.5, 6.55, z), (5.97, 6.55, z), (5.97, 4.35, z), (HW[2] - .05, 4.35, z)], .065)
    I.valve(g, (5.97, 5.4, z), 'up', r=.1, stem=.16)


# ---------------------------------------------------------------- grounds

def build(g, parts):
    hall(g, parts)
    changing_wing(g)
    pool_court(g)
    engine_shed(g, parts)
    boiler_room(g, parts)
