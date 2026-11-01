"""ObservationDeck: late-game public viewing tower (wellbeing).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the paved apron, corner planters and post lamps.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "make the roof flat on more of
our buildings"; the tower's height is its purpose, so it stays a lookout):
6x6x16 -> 6x6x10, same footprint, origin, doors and visitor slots. The deck
drops from layer 12 to layer 7 and the stair landing from 9 to 5. The eight
open radial cantilever trusses are replaced by a solid concrete corbel and
four solid web brackets; the stairhead and the ticket kiosk are one layer
high and the beacon mast is shorter. Roof variety (user, 2026-10-30: "some
buildings can have actual roofs"): the stairhead keeps a low teal pyramid
roof in the native roof planks and the kiosk a plank gable.

Second shrink 2026-11-01 (user: "shrink the buildings down even more"):
6x6x10 -> 3x3x8. The same tapering tube and open helical stair (16 treads to
a landing at layer 3) now carry a 3 x 3 open concrete deck at layer 5 on a
smaller corbel and four web brackets; the stairhead is one tile in the
middle of the deck with the deck door on its front, the telescope on the
front edge and the beacon mast on its pyramid. The ticket kiosk became a
one-tile vestibule with the ground door against the tube's foot, under a
small hipped roof. Ground door at x = 1.5 (Entrance (1,-1,0), was (2,-1,0)).
20 visitor places on the deck round the stairhead.

HERO: a tapering riveted steel tube column wrapped by an open helical stair,
carrying a square open deck on a solid concrete corbel (no railing: user,
2026-10-31), a brass telescope on a pedestal at the front edge and a beacon
mast on the stairhead.
ROOF: open concrete deck (a roof terrace); low teal pyramid roof (native roof
planks) on the stairhead; small hipped roof on the vestibule; conical cap on the
beacon.

Plan (3 x 3 tiles; front y = 0):
  - Ground: vestibule on tile x 1, y 0 (door centred on x = 1.5, face on the
    y = 0 tile edge), one layer under a small hipped roof, against the flared foot
    of the tube at (1.5, 1.5) on its concrete footing ring.
  - Helical stair: 15 riveted treads, 22 degrees and 0.19 layers apart, from
    the ground to a grated landing at exactly layer 3 round the tube.
  - Capital drum (layers 3..5) houses the upper stair and carries the corbel.
  - Deck: 3 x 3 concrete slab, top exactly layer 5. The slab is 0.2 thick so
    it claims layer 4 under every deck cell; layer-5 cells stay free except
    the stairhead tile.
  - Stairhead (x 1..2, y 1..2), one layer, with the deck door centred on
    x = 1.5, face on the y = 1 tile edge, at layer 5.

Animated: telescope (CUSTOM_YAW_OSC pan), beacon shutter (SPIN_Z),
anemometer (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, WINDOW, LAYER_GAP
import lategame_civic_parts as P
from lategame_civic_parts import blk, obox
import lategame_industry_parts as I
from lategame_mining_parts import plank_gable
import native_window_atlas as A
import native_building_assets as N
import civic_wellbeing_parts as W
from civic_wellbeing_parts import animate  # noqa: F401  (CUSTOM_ kinds)

IDENT = 'ObservationDeck'
FOOTPRINT = (3, 3)
HEIGHT = 8
N = 3                  # deck size in tiles
FRAME_END = 121
HERO = ('Tapering riveted steel tube wrapped by an open helical stair, carrying a broad open square deck on a '
        'solid concrete corbel, with a brass telescope and a beacon mast.')

CX, CY = 1.5, 1.5
LANDING = 3            # whole layer: top of the stair, round the tube
DECK = 5               # whole layer: walking surface of the deck
SLAB = .2
DRUM_R = .95
STAIR_OUT = 1.44
TREADS = 16
STEP = math.radians(22)
THETA0 = math.radians(-30)
DOOR_X = 1.5
STAIRHEAD = (1.0, 1.0, 2.0, 2.0)
# Roof-terrace registration: the free deck cells at layer 7; their support
# is the slab, which occupies the layer-11 cell below each of them.
TERRACE = {'layer': DECK, 'supportLayer': DECK - 1,
           'cells': [[x, y, DECK] for y in range(N) for x in range(N)
                     if not (STAIRHEAD[0] <= x < STAIRHEAD[2] and STAIRHEAD[1] <= y < STAIRHEAD[3])],
           'door': 'DeckDoor'}

TUBE = [(.25, 1.0), (.85, .8), (1.45, .7), (LANDING, .55)]
# The 20 visitors' places (capacity unchanged): three along the outer edge of
# each side cell round the stairhead (the deck door's step too, by its outer
# edge) and two on each corner cell.
DOOR_STEP = (1, 0)


def _visitor_places():
    places = []
    for x, y, _ in TERRACE['cells']:
        dx, dy = x + .5 - CX, y + .5 - CY
        ox, oy = x + .5 + .25 * (dx > 0) - .25 * (dx < 0), y + .5 + .25 * (dy > 0) - .25 * (dy < 0)
        along = (1, 0) if dy else (0, 1)
        corner = dx and dy
        offsets = (-.2, .2) if corner else (-.28, 0, .28)
        if corner:
            along = (1, 0)
        if (x, y) == DOOR_STEP:
            oy = y + .3
        for o in offsets:
            places.append((ox + along[0] * o, oy + along[1] * o))
    return places


VISITOR_PLACES = _visitor_places()


def tube_r(z):
    for (z0, r0), (z1, r1) in zip(TUBE, TUBE[1:]):
        if z <= z1:
            return r0 + (r1 - r0) * max(0.0, z - z0) / (z1 - z0)
    return TUBE[-1][1]


# ---------------------------------------------------------------- tower

def tower(g):
    K.revolve(g, (CX, CY, .0), [(1.18, 0), (1.18, .18), (1.1, .25)], CONCRETE, segments=16)
    # Tube foot buried 5 cm in the footing ring.
    K.revolve(g, (CX, CY, 0), [(1.0, .2)] + [(r, z) for z, r in TUBE], FORGED, segments=16)
    for z in [.55] + [1.5 + k for k in range(int(LANDING - 1.5) + 1)]:
        K.band(g, (CX, CY, 0), tube_r(z), z, .07, IRON, segments=16, proud=.025)
    # Capital drum (upper stair housing) with hoops and the truss roots.
    z0, z1 = LANDING, DECK - SLAB
    K.revolve(g, (CX, CY, z0 - .02), [(DRUM_R, 0), (DRUM_R, z1 - z0 - .3), (DRUM_R + .2, z1 - z0 - .02),
                                      (DRUM_R + .2, z1 - z0 + .02)], FORGED, segments=16)
    for z in (z0 + .45,):
        K.band(g, (CX, CY, 0), DRUM_R, z, .08, IRON, segments=16, proud=.03)
    # Hatch door on the drum where the stair arrives.
    th = THETA0 + (TREADS - 1) * STEP + STEP * .9
    hx, hy = CX + math.cos(th) * (DRUM_R + .03), CY + math.sin(th) * (DRUM_R + .03)
    ax, ay, az = (-math.sin(th), math.cos(th), 0), (-math.cos(th), -math.sin(th), 0), (0, 0, 1)
    c, s = math.cos(th), math.sin(th)
    obox(g, (CX + c * .975, CY + s * .975, z0 + .43), ax, ay, az, .28, .025, .44, IRON)    # frame, front r 1.0
    obox(g, (CX + c * .995, CY + s * .995, z0 + .42), ax, ay, az, .24, .035, .4, WOOD)     # door, front r 1.03


def stair(g):
    h = LANDING / TREADS
    tops = []
    # The 48th riser lands on the landing itself, so 47 treads are authored.
    for i in range(TREADS - 1):
        th = THETA0 + i * STEP
        z = (i + 1) * h
        r_in = tube_r(z) + .01
        c, s = math.cos(th), math.sin(th)
        rm = (r_in + STAIR_OUT) / 2
        obox(g, (CX + c * rm, CY + s * rm, z - .025), (c, s, 0), (-s, c, 0), (0, 0, 1),
             (STAIR_OUT - r_in) / 2, .15, .025, FORGED)
        tops.append((th, z))
    # Continuous outer stringer and handrail (sweeps), posts on every other tread.
    def helix(r, dz, n_sub=3):
        pts, sides, ups = [], [], []
        for k in range(TREADS * n_sub + 1):
            t = k / n_sub
            th = THETA0 + t * STEP
            z = (t + 1) * h + dz
            pts.append((CX + math.cos(th) * r, CY + math.sin(th) * r, z))
            sides.append((math.cos(th), math.sin(th), 0))
            ups.append((0, 0, 1))
        return pts, sides, ups
    p, s_, u = helix(STAIR_OUT + .03, -.12)
    W.sweep(g, p, s_, u, .025, .08, IRON)
    p, s_, u = helix(STAIR_OUT - .04, .64)
    W.sweep(g, p, s_, u, .025, .025, IRON)
    for i in range(0, TREADS - 1, 2):
        th, z = tops[i]
        r = STAIR_OUT - .04
        g.box((CX + math.cos(th) * r, CY + math.sin(th) * r, z + .31), (.04, .04, .62), IRON)
    # Grated landing at layer 9, open (no ring rail: user, 2026-10-31).
    I.annulus(g, (CX, CY), tube_r(LANDING) - .02, STAIR_OUT + .05, LANDING - .08, LANDING, IRON, segments=16)
    for k in range(8):
        a = k * math.pi / 4 + math.pi / 8
        if 70 <= math.degrees(a) <= 170:      # the top treads pass here
            continue
        g.beam((CX + math.cos(a) * tube_r(LANDING - .7), CY + math.sin(a) * tube_r(LANDING - .7), LANDING - .7),
               (CX + math.cos(a) * (STAIR_OUT - .05), CY + math.sin(a) * (STAIR_OUT - .05), LANDING - .1), .06,
               mat=IRON)


# ---------------------------------------------------------------- deck

def deck(g, parts):
    z = DECK
    blk(g, 0, 0, z - SLAB, N, N, z - .02, CONCRETE)
    # Deck flags, one per cell with 12 mm seams; top exactly the deck layer.
    for x in range(N):
        for y in range(N):
            if STAIRHEAD[0] <= x < STAIRHEAD[2] and STAIRHEAD[1] <= y < STAIRHEAD[3]:
                continue
            blk(g, x + .006, y + .006, z - .025, x + .994, y + .994, z, CONCRETE)
    # Iron fascia channel round the slab edge (non-overlapping corners).
    f, zb, zt = .03, z - SLAB - .1, z - .03
    blk(g, -f, -f, zb, N + f, 0, zt, IRON)
    blk(g, -f, N, zb, N + f, N + f, zt, IRON)
    blk(g, -f, 0, zb, 0, N, zt, IRON)
    blk(g, N, 0, zb, N + f, N, zt, IRON)
    # Edge girders under the slab, set in from the edge.
    gb, gt = z - SLAB - .32, z - SLAB - .01
    blk(g, .1, .1, gb, N - .1, .3, gt, IRON)
    blk(g, .1, N - .3, gb, N - .1, N - .1, gt, IRON)
    blk(g, .1, .3, gb, .3, N - .3, gt, IRON)
    blk(g, N - .3, .3, gb, N - .1, N - .3, gt, IRON)
    # Solid concrete corbel flaring from the drum to an iron ring band under
    # the slab, and four solid web brackets out to the slab corners.
    cz0, cz1 = LANDING + .9, z - SLAB - .02
    K.revolve(g, (CX, CY, cz0), [(DRUM_R - .02, 0), (DRUM_R + .15, .3), (1.3, cz1 - cz0 - .12),
                                  (1.3, cz1 - cz0)], CONCRETE, segments=16)
    K.band(g, (CX, CY, 0), 1.3, cz1 - .12, .1, IRON, segments=16, proud=.03)
    r0, r1 = .9, (N / 2 - .21) * math.sqrt(2) - .12
    prof = [(r0, LANDING + .6), (r1, gb + .02), (r1, gt - .01), (r0, gt - .01)]   # counter-clockwise in (r, z)
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        c, s_ = math.cos(a), math.sin(a)
        n = (-s_, c, 0)

        def at(r, zz, off):
            return (CX + c * r + n[0] * off, CY + s_ * r + n[1] * off, zz)
        for side in (1, -1):
            K.oriented_polygon(g, [at(r, zz, .05 * side) for r, zz in prof], (n[0] * side, n[1] * side, 0), IRON)
        for (ra, za), (rb, zb) in zip(prof, prof[1:] + prof[:1]):
            quad = [at(ra, za, -.05), at(rb, zb, -.05), at(rb, zb, .05), at(ra, za, .05)]
            out = (zb - za, -(rb - ra))       # outward normal of the edge in (r, z)
            K.oriented_polygon(g, quad, (c * out[0], s_ * out[0], out[1]), IRON)
    telescope(g, parts)
    stairhead(g, parts)


def telescope(g, parts):
    """Brass telescope on a steel pedestal standing on the deck's front edge
    at the x = 2 grid line, within the roof cells' outer band (0.31 from
    every cell edge), so both deck cells stay placeable. Its tube swings at
    the same height it had on the old railing."""
    z = DECK
    tx, ty, tz = 2.0, .15, z + .87
    # Base plate and post start 15 mm down in the deck flags (above the slab under them).
    g.cylinder((tx, ty, z + .0125), .11, .055, IRON, 'Z', 10)
    g.cylinder((tx, ty, (z - .015 + tz + .12) / 2), .05, tz + .135 - z, IRON, 'Z', 10)
    tel = Geometry('ObservationDeck.Telescope', (tx, ty, tz + .16))
    tel.cylinder((tx, ty, tz + .14), .04, .08, IRON, 'Z', 8)
    K.revolve(tel, (tx, ty, tz + .16), [(.001, -.02), (.055, 0), (.055, .06), (.001, .08)], BRASS, segments=10)
    I.tube(tel, (tx - .34, ty, tz + .25), (tx + .3, ty, tz + .21), .045, BRASS, segments=12)
    I.tube(tel, (tx + .3, ty, tz + .21), (tx + .38, ty, tz + .205), .06, BRASS, segments=12)
    I.tube(tel, (tx - .42, ty, tz + .255), (tx - .34, ty, tz + .25), .03, IRON, segments=10)
    tel.box((tx, ty, tz + .2), (.08, .06, .06), IRON)
    parts.append((tel, 'CUSTOM_YAW_OSC', (.6, 1)))


def stairhead(g, parts):
    x0, y0, x1, y1 = STAIRHEAD
    z = DECK
    P.framed_block(g, x0, y0, x1, y1, z, z + 1.0, infill=ORANGE, frame=WOOD, pitch=2.0, corner=.12,
                   skip={'front': [(DOOR_X - .5, DOOR_X + .5)]},
                   windows={'left': [(1.5, z + .45, .4, 'lancet')], 'right': [(1.5, z + .45, .4, 'lancet')],
                            'back': [(1.5, z + .45, .4, 'lancet')]})
    # The portal's recess floor would lie on the deck top: seat it on a 12 mm
    # iron sill instead; the door is still registered at layer 12.
    from industrial_facades import building_portal
    blk(g, DOOR_X - .49, y0 - .14, z - .03, DOOR_X + .49, y0 + .02, z + .005, IRON)
    building_portal(g, DOOR_X, y0 - .135, z + .012)
    g.doorways.append({'id': 'DeckDoor', 'position': [DOOR_X, y0, z], 'outward': [0, -1]})
    blk(g, x0 - .06, y0 - .06, z + 1.0, x1 + .06, y1 + .06, z + 1.06, CONCRETE)
    P.pyramid_roof(g, (x0 + x1) / 2, (y0 + y1) / 2, .5, z + 1.06, .4, overhang=.1)
    # Beacon mast with an anemometer arm on the pyramid's apex.
    mz0 = z + 1.06 + .4
    K.revolve(g, (CX, CY, mz0 - .04), [(.07, 0), (.055, .12), (.045, .5)], IRON, segments=10)
    pivot = K.beacon(g, CX, CY, mz0 + .46)
    parts.append((K.beacon_shutter(*pivot, 'ObservationDeck.BeaconShutter'), 'SPIN_Z', 2))
    ar = .32
    g.beam((CX, CY, mz0 + .3), (CX + ar, CY, mz0 + .3), .03, mat=IRON)
    g.cylinder((CX + ar, CY, mz0 + .36), .02, .12, IRON, 'Z', 8)
    an = Geometry('ObservationDeck.Anemometer', (CX + ar, CY, mz0 + .44))
    an.cylinder((CX + ar, CY, mz0 + .43), .035, .05, BRASS, 'Z', 8)
    for i in range(3):
        a = i * 2 * math.pi / 3
        tip = (CX + ar + math.cos(a) * .18, CY + math.sin(a) * .18, mz0 + .445)
        an.beam((CX + ar, CY, mz0 + .44), (tip[0], tip[1], mz0 + .44), .02, mat=IRON)   # tops clear of the hub top
        K.revolve(an, (tip[0], tip[1], tip[2] - .04), [(.001, 0), (.055, .03), (.055, .07), (.001, .085)], BRASS,
                  segments=8)
    parts.append((an, 'SPIN_Z', 2))


# ---------------------------------------------------------------- ground

def kiosk(g):
    """One-tile vestibule with the ground door, against the tube's foot, under
    a small hipped roof (the ticket kiosk until 2026-11-01)."""
    x0, y0, x1, y1 = 1.0, 0.0, 2.0, .62
    P.podium(g, x0, y0, x1, y1, .12, joints=False, foot=False, skip=[(DOOR_X - .5, DOOR_X + .5)], base=-.02)   # underside clear of the footing ring's (z 0)
    P.framed_block(g, x0 + .05, y0 + .05, x1 - .05, y1, .12, 1.0, infill=ORANGE, frame=WOOD, pitch=1.0,
                   corner=.12, faces=('front', 'left', 'right'), skip={'front': [(DOOR_X - .5, DOOR_X + .5)]})
    P.door(g, DOOR_X, y0, 0, 'Door0')
    P.hip_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .02, 1.0, .22, overhang=.06)
    K.lamp(g, .9, y0 + .05, .52, face='front')


def build(g, parts):
    tower(g)
    stair(g)
    deck(g, parts)
    kiosk(g)
