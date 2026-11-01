"""DeepDrill: late-game deep-ore drilling rig (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the gate post lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size"): 11x9x16 -> 7x6x8, inside the
old footprint with the same origin, door and native entrance. Removed: the
open lattice derrick (diagonals, Lambda brace, monkey board, racked pipe
setback), the pier-and-I-beam substructure with its cellar BOP stack, the
V-door ramp and catwalk, the pipe rack and the separate power house. The
derrick is now a short boarded tower; the engine room is the solid concrete
base under the drill floor.

Shrunk again 2026-11-01 (user: "we need to shrink the buildings down even
more"; the finite Deep Ore Source is gathered nearby like scrap metal, so
the drill does not sit on it): 7x6x8 -> 4x4x7, inside the old footprint with
the same origin, door and native entrance (cell 1, -1). The brick pump house
with the door keeps the front-left 2x2 under a flat riveted steel roof deck
(its doghouse went); the engine room is one layer on the right column pair,
its roof the drill floor (layer 1, was 2) carrying the boarded tower (crown
deck at 5.5, was 7), the rotary table and the drawworks; the triplex mud
pump stands on its bed on the back-left 2x2. The hoist stroke is 0.45 (was
0.95) and the kelly is shorter, so the tower stays one layer lower than
before over a floor one layer lower.

HERO: a boarded, tapered drilling tower (five layers above the drill floor)
on a solid engine room, open at the front so the hoist shows, with crown
block, gin pole and beacon. Roofs: a riveted steel plate roof deck on the
pump house beside the steel drill floor on the engine room (roof variety,
user 2026-10-30). No roof vents:
the two smoke stacks rise up the engine room's back wall and the doghouse stove
pipe is gone.

Parts: brick pump house (the entrance) under a flat steel roof deck;
one-layer engine room (tiles 2..4 x 0..4) carrying the steel drill floor,
rotary table, drawworks and the two smoke stacks, with the radiator fan on
its right wall; triplex mud pump on its bed. No clutter on buildable space
(user, 2026-10-30): the mud tanks and the pipe joints on the pump-house roof
are gone and the back-left tiles are open ground.

Animated (9, unchanged names and kinds except the radiator fan, which now
turns on the engine room's right wall): travelling block and hook (hoist), its drill
lines (stretch), kelly (descends while turning), rotary table, drawworks
drum, mud-pump pistons and bull wheel, radiator fan, crown beacon.
"""
import math

from mathutils import Quaternion

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK
import lategame_mining_parts as P
from lategame_mining_parts import bx
from lategame_roofdeck_parts import deck_slab

IDENT = 'DeepDrill'
FOOTPRINT = (4, 4)
HEIGHT = 7
HERO = 'Boarded, tapered drilling tower on a solid concrete engine room, crowned by a crown block and beacon'
FRAME_END = 121

FLOOR = 1.0                   # drill floor layer (the engine room's roof)
ON = FLOOR + .012             # top of the floor grating bars
PUMP_ROOF = 2.0               # pump-house roof deck layer
WELL = (3.0, 1.0)             # well centre
BASE = (2.3, 3.7, .3, 1.7)    # tower leg footprint at the floor (x0, x1, y0, y1)
TOP = (2.75, 3.25, .75, 1.25)
ZT = 5.5                      # crown deck
STROKE = .45                  # hoist travel per loop (kelly collar stops above the bushing)
BLOCK_TOP = ZT - 1.25         # travelling block top at its highest
HOIST = BLOCK_TOP - 9.25      # hoist parts keep the 2026-10-22 shapes, lowered by this
GIRTS = (2.0, 3.0, 4.0)
LINE_X = (-.15, -.05, .05, .15)   # crown sheaves / drill lines across the well
FRONT_BOARDS = 4.1            # the open front (V-door) reaches up to here


def frame_at(z):
    t = (z - FLOOR) / (ZT - FLOOR)
    return tuple(BASE[i] + (TOP[i] - BASE[i]) * t for i in range(4))


# ------------------------------------------------------------------ tower

def board_course(g, face, za, zb):
    fa, fb = frame_at(za), frame_at(zb)
    if face == 'left':
        pts = [(fa[0] + .05, fa[3] - .06, za), (fa[0] + .05, fa[2] + .06, za),
               (fb[0] + .05, fb[2] + .06, zb), (fb[0] + .05, fb[3] - .06, zb)]
        normal = (-1, 0, (TOP[0] - BASE[0]) / (ZT - FLOOR))
    elif face == 'right':
        pts = [(fa[1] - .05, fa[2] + .06, za), (fa[1] - .05, fa[3] - .06, za),
               (fb[1] - .05, fb[3] - .06, zb), (fb[1] - .05, fb[2] + .06, zb)]
        normal = (1, 0, (BASE[1] - TOP[1]) / (ZT - FLOOR))
    elif face == 'back':
        pts = [(fa[1] - .06, fa[3] - .05, za), (fa[0] + .06, fa[3] - .05, za),
               (fb[0] + .06, fb[3] - .05, zb), (fb[1] - .06, fb[3] - .05, zb)]
        normal = (0, 1, (BASE[3] - TOP[3]) / (ZT - FLOOR))
    else:
        pts = [(fa[0] + .06, fa[2] + .05, za), (fa[1] - .06, fa[2] + .05, za),
               (fb[1] - .06, fb[2] + .05, zb), (fb[0] + .06, fb[2] + .05, zb)]
        normal = (0, -1, (TOP[2] - BASE[2]) / (ZT - FLOOR))
    P.slab_quad(g, pts, normal, .05, PLANK)


def tower(g):
    corners = lambda z: (lambda f: [(f[0], f[2]), (f[1], f[2]), (f[1], f[3]), (f[0], f[3])])(frame_at(z))
    # Leg shoes and legs.
    for (x, y), (xt, yt) in zip(corners(FLOOR), corners(ZT)):
        bx(g, x - .17, x + .17, y - .17, y + .17, ON, ON + .16, IRON)
        bx(g, x - .12, x + .12, y - .12, y + .12, ON + .16, ON + .2, PAINTED)
        g.beam((x, y, ON + .1), (xt, yt, ZT - .04), .18, mat=IRON)
    # Timber boarding inside the legs: closed on the left, right and back up
    # to the crown; the front is open below FRONT_BOARDS (the V-door).
    courses = 10
    z0, z1 = ON + .2, ZT - .1
    zs = [z0 + (z1 - z0) * i / courses for i in range(courses + 1)]
    for face in ('left', 'right', 'back'):
        for za, zb in zip(zs, zs[1:]):
            board_course(g, face, za, zb)
    for za, zb in ((FRONT_BOARDS, (FRONT_BOARDS + z1) / 2), ((FRONT_BOARDS + z1) / 2, z1)):
        board_course(g, 'front', za, zb)
    # Steel girts 30 mm proud of the boarding; left/right raised 30 mm so
    # corners never coincide. The front gets only the V-door lintel.
    for z in GIRTS:
        x0, x1, y0, y1 = frame_at(z)
        bx(g, x0 + .07, x1 - .07, y1 - .02, y1 + .08, z - .05, z + .05, IRON)
        bx(g, x0 - .08, x0 + .02, y0 + .07, y1 - .07, z - .02, z + .08, IRON)
        bx(g, x1 - .02, x1 + .08, y0 + .07, y1 - .07, z - .02, z + .08, IRON)
    x0, x1, y0, y1 = frame_at(FRONT_BOARDS)
    bx(g, x0 + .07, x1 - .07, y0 - .08, y0 + .02, FRONT_BOARDS - .05, FRONT_BOARDS + .05, IRON)
    # Work lamp on the inner back boarding, seen through the V-door.
    zl = 2.4
    K.lamp(g, WELL[0] + .3, frame_at(zl + .14)[3] - .1, zl, face='front')
    # Crown deck, crown block and gin pole with beacon.
    cx, cy = WELL
    P.deck(g, TOP[0] - .25, TOP[1] + .25, TOP[2] - .25, TOP[3] + .25, ZT)   # open (user, 2026-10-31)
    zc = ZT + .012
    bx(g, cx - .4, cx + .4, cy - .3, cy + .3, zc, zc + .1, IRON)
    for x in (cx - .36, cx + .26):
        bx(g, x, x + .1, cy - .3, cy + .3, zc + .1, zc + .66, PAINTED)
    g.cylinder((cx, cy, zc + .4), .06, .84, IRON, 'X', 12)
    for dx in LINE_X:
        g.ring((cx + dx, cy, zc + .4), .24, .04, .07, IRON, 'X', 12)
        g.ring((cx + dx, cy, zc + .4), .18, .025, .05, BRASS, 'X', 16)
    gx = cx - .5
    for y in (cy - .55, cy + .55):
        g.beam((gx, y, zc), (gx, cy, ZT + .52), .07, mat=IRON)
    bx(g, gx - .08, gx + .08, cy - .12, cy + .12, ZT + .45, ZT + .58, PAINTED)
    K.beacon(g, gx, cy, ZT + .58)
    # Ladder up the right face to the crown deck.
    ladder_face(g, cy, ON, ZT - .1)


def ladder_face(g, y, z0, z1, w=.32):
    """Ladder following the inclined right face of the tower, standing off
    it, bracketed to the right girts."""
    def xl(z):
        return frame_at(z)[1] + .16
    for s in (-1, 1):
        g.beam((xl(z0), y + s * w / 2, z0), (xl(z1), y + s * w / 2, z1), .045, mat=IRON)
    z = z0 + .2
    while z < z1 - .1:
        g.beam((xl(z), y - w / 2 + .02, z), (xl(z), y + w / 2 - .02, z), .03, mat=IRON)
        z += .3
    for z in (GIRTS[0] + .03, GIRTS[-1] + .03):
        g.beam((xl(z), y, z), (frame_at(z)[1] + .08, y, z), .05, mat=IRON)


def drill_lines():
    """Reeved drill lines from the crown to the travelling block; they stretch."""
    top = ZT + .2
    lines = Geometry('DrillLines', (WELL[0], WELL[1], top))
    for i, dx in enumerate(LINE_X):
        y = WELL[1] - .04 if i % 2 else WELL[1] + .04
        lines.box((WELL[0] + dx, y, (top + BLOCK_TOP - .05) / 2), (.03, .03, top - BLOCK_TOP + .05), IRON)
    return lines


def travelling_block():
    h = HOIST
    blk = Geometry('TravellingBlock', (WELL[0], WELL[1], 8.0 + h))
    x, y = WELL
    bx(blk, x - .28, x + .28, y - .18, y + .18, 8.45 + h, BLOCK_TOP - .12, PAINTED)
    bx(blk, x - .24, x + .24, y - .15, y + .15, BLOCK_TOP - .12, BLOCK_TOP, PAINTED)
    for sx in (-1, 1):
        bx(blk, x + sx * .28 - (.0 if sx > 0 else .025), x + sx * .28 + (.025 if sx > 0 else 0),
           y - .12, y + .12, 8.6 + h, 9.0 + h, BRASS)
    P.bolt_ring(blk, (x, y - .18, 8.85 + h), .16, 6, 'Y', -.008, .02)
    bx(blk, x - .08, x + .08, y - .06, y + .06, 8.3 + h, 8.45 + h, IRON)
    # Hook.
    K.revolve(blk, (x, y, 7.95 + h), [(.07, 0), (.12, .08), (.12, .3), (.08, .4)], IRON, segments=12)
    blk.beam((x, y, 7.98 + h), (x + .16, y, 7.86 + h), .07, mat=IRON)
    blk.beam((x + .16, y, 7.86 + h), (x + .2, y, 8.04 + h), .06, mat=IRON)
    # Swivel and bail.
    K.revolve(blk, (x, y, 7.25 + h), [(.1, 0), (.17, .1), (.2, .3), (.16, .5), (.1, .6)], PAINTED, segments=14)
    for sx in (-1, 1):
        blk.beam((x + sx * .2, y, 7.55 + h), (x + sx * .06, y, 8.0 + h), .04, mat=IRON)
    P.tube(blk, (x, y - .1, 7.7 + h), (x, y - .32, 7.95 + h), .045, BRASS, 8)
    return blk


def kelly():
    h = HOIST
    k = Geometry('Kelly', (WELL[0], WELL[1], 5.0 + h))
    x, y = WELL
    bx(k, x - .08, x + .08, y - .08, y + .08, ON + .2, 7.2 + h, IRON)
    bx(k, x - .12, x + .12, y - .12, y + .12, 6.95 + h, 7.12 + h, BRASS)
    k.cylinder((x, y, 7.19 + h), .11, .12, PAINTED, 'Z', 12)
    return k


def rotary(g, parts):
    x, y = WELL
    bx(g, x - .6, x + .6, y - .6, y + .6, ON, ON + .2, IRON)
    bx(g, x + .6, x + .85, y - .22, y + .22, ON, ON + .14, PAINTED)
    zc = ON + .26
    t = Geometry('RotaryTable', (x, y, zc))
    t.cylinder((x, y, zc), .52, .12, PAINTED, 'Z', 16)
    t.ring((x, y, zc), .55, .05, .07, BRASS, 'Z', 16)
    bx(t, x - .23, x + .23, y - .23, y + .23, zc + .06, zc + .2, IRON)
    for sx in (-1, 1):
        for sy in (-1, 1):
            K.stud(t, (x + sx * .15, y + sy * .15, zc + .209), 'Z', .025)
    bx(t, x + .42, x + .56, y - .05, y + .05, zc + .06, zc + .12, BRASS)
    parts.append((t, 'SPIN_Z', 3))


# ------------------------------------------------------------------ engine room and drill floor

def engine_room(g):
    """One-layer brick engine room (concrete base course and pilasters) on tiles 2..4 x 0..4; its roof is the drill floor."""
    small = lambda u: (u, .52, 'factory', .4)
    P.concrete_house(g, 2.12, 3.95, .05, 3.95, FLOOR - .16, base=.2, pitch=1.3, record_doors=False, wall=P.BRICK,
                     windows={'front': [small(2.7), small(3.4)],
                              'right': [small(.7), small(1.9)],
                              'back': [small(3.0)]})
    # Roof slab on whole tiles, steel drill floor stacked on it.
    bx(g, 2.1, 4.0, 0.0, 4.0, FLOOR - .16, FLOOR - .08, CONCRETE)
    P.deck(g, 2.1, 4.0, 0.0, 4.0, FLOOR)   # an open platform edge to edge (user, 2026-10-31)
    P.gauge(g, 3.05, .01, .62, 'front', .07)

def drawworks(g, parts):
    x, y = WELL[0], 2.75
    for x0 in (2.2, 3.6):
        bx(g, x0, x0 + .18, y - .45, y + .45, ON, ON + .95, PAINTED)
        bx(g, x0 - .03, x0 + .21, y - .18, y + .18, ON + .95, ON + 1.08, BRASS)
    bx(g, 2.38, 3.6, y - .4, y + .4, ON, ON + .12, IRON)
    c = (x, y, ON + .6)
    d = Geometry('DrawworksDrum', c)
    d.cylinder(c, .32, 1.16, IRON, 'X', 16)
    for fx in (2.47, 3.53):
        d.cylinder((fx, y, c[2]), .46, .08, PAINTED, 'X', 16)
    for fx in (2.75, 3.0, 3.25):
        d.ring((fx, y, c[2]), .35, .035, .12, IRON, 'X', 16)
    d.cylinder(c, .09, 1.5, IRON, 'X', 12)
    for fx in (2.47, 3.53):
        # (The flange bolt circles were sub-pixel; the brass index lug shows the turn.)
        bx(d, fx - .035, fx + .035, y - .05, y + .05, c[2] + .46, c[2] + .54, BRASS)
    parts.append((d, 'SPIN_X', 2))
    # Fast line from the drum over the back of the tower to the crown.
    g.beam((x - .05, y, c[2] + .32), (x, TOP[3] + .02, ZT + .35), .035, mat=IRON)
    # Dead-line anchor beside the drawworks.
    bx(g, 2.2, 2.45, 3.45, 3.7, ON, ON + .25, PAINTED)
    g.beam((2.32, 3.57, ON + .25), (WELL[0] - .3, TOP[3] - .05, ZT + .35), .035, mat=IRON)

STACKS_X = (2.75, 3.25)       # smoke stacks against the engine room's back wall


def back_services(g, parts):
    """Smoke stacks against the engine room's back wall and the radiator fan on its right wall.

    User, 2026-10-30 ("no roof vents"): the stacks rise from the base course up
    the outside of the back wall instead of standing on the drill floor; they
    stay in the deck cells' outer band, so the deck behind the drawworks stays
    platformable."""
    for x in STACKS_X:
        K.wall_stack(g, x, 3.84, .2, ON + 2.6 - .2, emits='smoke', r=.11, bands=3)
    bx(g, 3.95, 4.03, 2.95, 3.75, .22, .78, PAINTED)
    g.ring((4.05, 3.35, .5), .26, .04, .06, IRON, 'X', 16)
    parts.append((P.rotor('RadiatorFan', (4.09, 3.35, .5), .22, 'X', 6), 'SPIN_X', 4))

# ------------------------------------------------------------------ pump house

def pump_house(g):
    # Brick hall on tiles 0..2 x 0..2, its right wall on the tile line the
    # engine room stands beside (from 2.12). The core front at .12 puts the
    # native portal's face on the tile edge y = 0.
    P.hall(g, .05, 2.0, .12, 1.95, PUMP_ROOF - .16, plinth=.5, doors=[1.5], pitch=1.0, plinth_mat=P.BRICK,
           posts=('front', 'back', 'left'),
           windows={'front': [(.5, 1.15, 'grand', .55)],
                    'left': [(.6, 1.15, 'grand', .55), (1.45, 1.15, 'grand', .55)]})
    K.lamp(g, .92, .12, 1.15, face='front')
    # Flat roof of riveted steel plate on whole tiles (a canopy over the door):
    # an open roof deck (the doghouse went, 2026-11-01).
    deck_slab(g, 0.0, 0.0, 2.0, 2.0, PUMP_ROOF, 'forged', base=IRON)

def mud_pump(g, parts):
    bx(g, 0.0, 2.0, 2.0, 4.0, 0, .3, CONCRETE)   # pump bed on the back-left 2x2
    # Fluid end with three valve covers.
    bx(g, .2, .75, 2.4, 3.4, .3, 1.08, IRON)
    for y in (2.6, 2.9, 3.2):
        g.cylinder((.17, y, .76), .1, .08, BRASS, 'X', 12)
        K.stud(g, (.125, y, .76), 'X', .03)
    # Liner frame between fluid and power ends.
    for y in (2.45, 3.35):
        bx(g, .75, 1.1, y - .04, y + .04, .45, .55, IRON)
        bx(g, .75, 1.1, y - .04, y + .04, .98, 1.06, IRON)
    # Power end crankcase with a rounded cover.
    bx(g, 1.1, 1.9, 2.45, 3.35, .3, 1.0, PAINTED)
    g.cylinder((1.5, 2.9, 1.0), .38, .84, PAINTED, 'Y', 18)
    rods = Geometry('MudPumpPistons', (.93, 2.9, .76))
    for y in (2.6, 2.9, 3.2):
        rods.cylinder((.93, y, .76), .04, .55, IRON, 'X', 10)
        bx(rods, .87, 1.0, y - .065, y + .065, .7, .82, BRASS)
    parts.append((rods, 'PISTON_X', .12))
    wheel = P.spoked_wheel('MudPumpBullWheel', (1.5, 3.62, .9), .42, 'Y', rim_t=.07, rim_w=.09,
                           spokes=6, groove=False, hub_r=.1)
    parts.append((wheel, 'SPIN_Y', 2))
    g.cylinder((1.5, 3.45, .9), .05, .3, IRON, 'Y', 10)
    # Discharge up onto the drill floor (standpipe).
    K.pipe_run(g, [(.45, 3.3, 1.08), (.45, 3.3, 1.3), (.45, 3.85, 1.3), (2.5, 3.85, 1.3), (2.5, 3.85, ON + .02)], .07)
    P.gauge(g, .2, 3.6, .9, 'left', .07)

def build(g, parts):
    engine_room(g)
    tower(g)
    rotary(g, parts)
    pump_house(g)
    mud_pump(g, parts)
    back_services(g, parts)
    drawworks(g, parts)
    parts.append((travelling_block(), 'CUSTOM_HOIST', STROKE))
    parts.append((drill_lines(), 'CUSTOM_LINES', STROKE))
    parts.append((kelly(), 'CUSTOM_KELLY', STROKE))
    parts.append((K.beacon_shutter(WELL[0] - .5, WELL[1], ZT + .72, 'CrownBeaconShutter'), 'SPIN_Z', 2))


def animate(obj, kind, value, frame_end):
    """Hoist cycle: slow descent while drilling, quick pull back to the top."""
    span = frame_end - 1
    keys = ((1, 0.0), (1 + span * .78, 1.0), (frame_end, 0.0))
    base_z = obj.location.z
    if kind == 'CUSTOM_LINES':
        length = ZT + .2 - BLOCK_TOP + .05
        for frame, t in keys:
            obj.scale = (1, 1, (length + value * t) / length)
            obj.keyframe_insert(data_path='scale', frame=frame)
    elif kind in ('CUSTOM_HOIST', 'CUSTOM_KELLY'):
        for frame, t in keys:
            obj.location.z = base_z - value * t
            obj.keyframe_insert(data_path='location', index=2, frame=frame)
        if kind == 'CUSTOM_KELLY':
            obj.rotation_mode = 'QUATERNION'
            steps = 48
            for k in range(steps + 1):
                obj.rotation_quaternion = Quaternion((0, 0, 1), 3 * 2 * math.pi * k / steps)
                obj.keyframe_insert(data_path='rotation_quaternion', frame=1 + span * k / steps)
    else:
        raise ValueError('Unknown custom animation ' + kind)
    obj.location.z = base_z
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'
