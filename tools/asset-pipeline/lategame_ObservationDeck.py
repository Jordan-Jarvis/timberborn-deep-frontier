"""ObservationDeck: late-game public viewing tower (wellbeing).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the paved apron, corner planters and post lamps.

HERO: a tapering riveted steel tube column wrapped by an open helical stair,
carrying a broad square deck on eight radial cantilever trusses, with a
glazed railing all round, a brass telescope on the front rail and a beacon
mast on the stairhead. Distinct from the launch gantries (no lattice) and
from MissionControl's glazed cab (the deck is open, the glazing is only a
waist-high railing).
ROOF: open deck; teal pyramid roof on the stairhead; conical cap on the beacon.

Plan (6 x 6 tiles; front y = 0):
  - Ground: ticket kiosk on tiles x 2..4, y 0..1 (door centred on x = 2.5,
    face on the y = 0 tile edge; ticket window at x = 3.5); concrete footing
    ring and the flared foot of the tube at (3, 3); corner planters; lamps.
  - Helical stair: 48 riveted treads, 20 degrees and 0.1875 layers apart,
    from the ground to a grated landing at exactly layer 9 round the tube.
  - Capital drum (layers 9..12) houses the upper stair and roots the trusses.
  - Deck: 6 x 6 concrete slab, top exactly layer 12. The slab is 0.2 thick so
    it claims layer 11 (the support layer) under every deck cell; layer-12
    cells stay free except the 2 x 2 stairhead. Railings, posts and the
    telescope stand within 0.15 of the tile edges, so no deck cell is claimed.
  - Stairhead (x 2..4, y 2..4) with the deck door centred on x = 2.5, face on
    the y = 2 tile edge, at layer 12.

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
FOOTPRINT = (6, 6)
HEIGHT = 16
FRAME_END = 121
HERO = ('Tapering riveted steel tube wrapped by an open helical stair, carrying a broad square deck on eight radial '
        'cantilever trusses, with a glazed railing, a brass telescope and a beacon mast.')

CX, CY = 3.0, 3.0
LANDING = 9            # whole layer: top of the stair, round the tube
DECK = 12              # whole layer: walking surface of the deck
SLAB = .2
DRUM_R = .95
STAIR_OUT = 1.44
TREADS = 48
STEP = math.radians(20)
THETA0 = math.radians(-60)
DOOR_X = 2.5
STAIRHEAD = (2.0, 2.0, 4.0, 4.0)
# Roof-terrace registration: the free deck cells at layer 12; their support
# is the slab, which occupies the layer-11 cell below each of them.
TERRACE = {'layer': DECK, 'supportLayer': DECK - 1,
           'cells': [[x, y, DECK] for y in range(6) for x in range(6)
                     if not (STAIRHEAD[0] <= x < STAIRHEAD[2] and STAIRHEAD[1] <= y < STAIRHEAD[3])],
           'door': 'DeckDoor'}

TUBE = [(.25, 1.0), (.85, .8), (1.45, .7), (LANDING, .55)]


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
    for z in [.55] + [1.5 + k for k in range(8)]:
        K.band(g, (CX, CY, 0), tube_r(z), z, .07, IRON, segments=16, proud=.025)
    # Capital drum (upper stair housing) with hoops and the truss roots.
    z0, z1 = LANDING, DECK - SLAB
    K.revolve(g, (CX, CY, z0 - .02), [(DRUM_R, 0), (DRUM_R, z1 - z0 - .3), (DRUM_R + .2, z1 - z0 - .02),
                                      (DRUM_R + .2, z1 - z0 + .02)], FORGED, segments=16)
    for z in (z0 + .45, z0 + 1.35, z0 + 2.2):
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
    # Grated landing at layer 9 with a ring rail (open where the stair arrives).
    I.annulus(g, (CX, CY), tube_r(LANDING) - .02, STAIR_OUT + .05, LANDING - .08, LANDING, IRON, segments=16)
    th_end = THETA0 + (TREADS - 1) * STEP
    a0 = (th_end - math.radians(15)) % (2 * math.pi)
    a1 = (th_end + math.radians(45)) % (2 * math.pi)
    gap = (a0, a1) if a0 < a1 else (a0 - 2 * math.pi, a1)
    I.ring_rail(g, (CX, CY), STAIR_OUT + .02, LANDING, height=.55, posts=16, gap=gap)
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
    blk(g, 0, 0, z - SLAB, 6, 6, z - .02, CONCRETE)
    # Deck flags, one per cell with 12 mm seams; top exactly layer 12.
    for x in range(6):
        for y in range(6):
            if STAIRHEAD[0] <= x < STAIRHEAD[2] and STAIRHEAD[1] <= y < STAIRHEAD[3]:
                continue
            blk(g, x + .006, y + .006, z - .025, x + .994, y + .994, z, CONCRETE)
    # Iron fascia channel round the slab edge (non-overlapping corners).
    f, zb, zt = .03, z - SLAB - .1, z - .03
    blk(g, -f, -f, zb, 6 + f, 0, zt, IRON)
    blk(g, -f, 6, zb, 6 + f, 6 + f, zt, IRON)
    blk(g, -f, 0, zb, 0, 6, zt, IRON)
    blk(g, 6, 0, zb, 6 + f, 6, zt, IRON)
    # Edge girders under the slab, set in from the edge.
    gb, gt = z - SLAB - .32, z - SLAB - .01
    blk(g, .1, .1, gb, 5.9, .32, gt, IRON)
    blk(g, .1, 5.68, gb, 5.9, 5.9, gt, IRON)
    blk(g, .1, .32, gb, .32, 5.68, gt, IRON)
    blk(g, 5.68, .32, gb, 5.9, 5.68, gt, IRON)
    # Eight radial cantilever trusses from the drum to the girders.
    root_lo, root_hi = LANDING + .75, z - SLAB - .03
    for k in range(8):
        a = k * math.pi / 4
        c, s = math.cos(a), math.sin(a)
        reach = (2.79 if k % 2 == 0 else 2.79 * math.sqrt(2) - .05)
        p0 = (CX + c * DRUM_R, CY + s * DRUM_R)
        p1 = (CX + c * reach, CY + s * reach)
        top = root_hi - .07
        g.beam((p0[0], p0[1], top), (p1[0], p1[1], top), .12, .12, IRON)               # top chord
        bot0 = (p0[0], p0[1], root_lo)
        bot1 = (p1[0], p1[1], gb + .05)
        g.beam(bot0, bot1, .12, .1, IRON)                                              # bottom chord
        n = 4
        for j in range(1, n):
            t = j / n
            bx = (bot0[0] + (bot1[0] - bot0[0]) * t, bot0[1] + (bot1[1] - bot0[1]) * t,
                  bot0[2] + (bot1[2] - bot0[2]) * t)
            tx = (p0[0] + (p1[0] - p0[0]) * t, p0[1] + (p1[1] - p0[1]) * t, top)
            g.beam(bx, tx, .07, .07, IRON)                                             # vertical
            t2 = (j + 1) / n
            tx2 = (p0[0] + (p1[0] - p0[0]) * t2, p0[1] + (p1[1] - p0[1]) * t2, top)
            g.beam(bx, tx2, .06, .06, IRON)                                            # diagonal
        g.beam(bot0, (p0[0] + (p1[0] - p0[0]) / n, p0[1] + (p1[1] - p0[1]) / n, top), .06, .06, IRON)
    railing(g, parts)
    stairhead(g, parts)


def _glass(g, a, b, z0, z1, normal):
    """Two-sided native glass pane between plan points a, b (12 mm apart)."""
    u0, u1, v0, v1 = A.cell_rect('glass')
    nx, ny = normal
    for side in (1, -1):
        o = .006 * side
        pts = [(a[0] + nx * o, a[1] + ny * o, z0), (b[0] + nx * o, b[1] + ny * o, z0),
               (b[0] + nx * o, b[1] + ny * o, z1), (a[0] + nx * o, a[1] + ny * o, z1)]
        uvs = [(u0, v0), (u1, v0), (u1, v1), (u0, v1)]
        n = W._newell(pts)
        if (n[0] * nx + n[1] * ny) * side < 0:
            pts.reverse()
            uvs.reverse()
        g.native_piece(pts, [(0, 1, 2, 3)], uvs, WINDOW)


def railing(g, parts):
    z = DECK
    e = .06                       # rail line inset from the deck edge
    hgt = .82
    lines = [((e, e), (6 - e, e), (0, -1)), ((6 - e, e), (6 - e, 6 - e), (1, 0)),
             ((6 - e, 6 - e), (e, 6 - e), (0, 1)), ((e, 6 - e), (e, e), (-1, 0))]
    for (ax_, ay_), (bx_, by_), nrm in lines:
        L = math.hypot(bx_ - ax_, by_ - ay_)
        dx, dy = (bx_ - ax_) / L, (by_ - ay_) / L
        # Posts at the run start (its corner) and at every whole-tile station.
        k0 = ax_ if dx else ay_
        posts = [0.0] + sorted(abs(k - k0) for k in range(1, 6))
        for t in posts:
            g.box((ax_ + dx * t, ay_ + dy * t, z + hgt / 2), (.07, .07, hgt), IRON)
        stations = posts + [L]
        for t0, t1 in zip(stations, stations[1:]):
            a = (ax_ + dx * (t0 + .045), ay_ + dy * (t0 + .045))
            b = (ax_ + dx * (t1 - .045), ay_ + dy * (t1 - .045))
            _glass(g, a, b, z + .1, z + hgt - .08, nrm)
        # Top rails: front/back runs span the corners, side runs stop between
        # them (no overlapping tops). Bottom rails stop short of the corners.
        cxr, cyr = (ax_ + bx_) / 2, (ay_ + by_) / 2
        span = L + .03 if nrm[1] else L - .1
        g.box((cxr, cyr, z + hgt + .025), (abs(dx) * span + abs(nrm[0]) * .09, abs(dy) * span + abs(nrm[1]) * .09, .05),
              IRON)
        g.box((cxr, cyr, z + .06), (abs(dx) * (L - .08) + abs(nrm[0]) * .045, abs(dy) * (L - .08) + abs(nrm[1]) * .045,
                                     .06), IRON)
    # Lamp standards on the four railing corners (top-rail level).
    for cx_, cy_ in ((e, e), (6 - e, e), (6 - e, 6 - e), (e, 6 - e)):
        W.lamp_standard(g, cx_, cy_, z + hgt + .05, .62)
    # Brass telescope on the front rail's middle post (x = 3 grid line).
    tx, ty, tz = 3.0, e, z + hgt + .05
    g.cylinder((tx, ty, tz + .06), .05, .12, IRON, 'Z', 10)
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
    P.framed_block(g, x0, y0, x1, y1, z, z + 1.25, infill=ORANGE, frame=WOOD, pitch=2.0, corner=.16,
                   skip={'front': [(DOOR_X - .5, DOOR_X + .5)]},
                   windows={'left': [(3.0, z + .62, .55, 'lancet')], 'right': [(3.0, z + .62, .55, 'lancet')],
                            'back': [(2.5, z + .62, .55, 'lancet'), (3.5, z + .62, .55, 'lancet')]})
    # The portal's recess floor would lie on the deck top: seat it on a 12 mm
    # iron sill instead; the door is still registered at layer 12.
    from industrial_facades import building_portal
    blk(g, DOOR_X - .5, y0 - .14, z - .03, DOOR_X + .5, y0 + .02, z + .005, IRON)
    building_portal(g, DOOR_X, y0 - .135, z + .012)
    g.doorways.append({'id': 'DeckDoor', 'position': [DOOR_X, y0, z], 'outward': [0, -1]})
    A.atlas_window(g, 3.5, y0, z + .55, .34, 'front', 'porthole')
    blk(g, x0 - .08, y0 - .08, z + 1.25, x1 + .08, y1 + .08, z + 1.33, CONCRETE)
    P.pyramid_roof(g, (x0 + x1) / 2, (y0 + y1) / 2, 1.0, z + 1.33, .95, overhang=.14)
    # Beacon mast with an anemometer arm.
    mz0 = z + 2.1
    K.revolve(g, (CX, CY, mz0), [(.09, 0), (.07, .2), (.05, 1.05)], IRON, segments=10)
    pivot = K.beacon(g, CX, CY, mz0 + 1.05)
    parts.append((K.beacon_shutter(*pivot, 'ObservationDeck.BeaconShutter'), 'SPIN_Z', 2))
    g.beam((CX, CY, mz0 + .6), (CX + .38, CY, mz0 + .6), .03, mat=IRON)
    g.cylinder((CX + .38, CY, mz0 + .66), .02, .12, IRON, 'Z', 8)
    an = Geometry('ObservationDeck.Anemometer', (CX + .38, CY, mz0 + .74))
    an.cylinder((CX + .38, CY, mz0 + .73), .035, .05, BRASS, 'Z', 8)
    for i in range(3):
        a = i * 2 * math.pi / 3
        tip = (CX + .38 + math.cos(a) * .2, CY + math.sin(a) * .2, mz0 + .745)
        an.beam((CX + .38, CY, mz0 + .74), (tip[0], tip[1], mz0 + .74), .02, mat=IRON)   # tops clear of the hub top
        K.revolve(an, (tip[0], tip[1], tip[2] - .04), [(.001, 0), (.055, .03), (.055, .07), (.001, .085)], BRASS,
                  segments=8)
    parts.append((an, 'SPIN_Z', 2))


# ---------------------------------------------------------------- ground

def kiosk(g):
    x0, y0, x1, y1 = 2.0, 0.0, 4.0, 1.0
    P.podium(g, x0, y0, x1, y1, .3, joints=False, skip=[(DOOR_X - .5, DOOR_X + .5)])
    P.framed_block(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, .3, 1.6, infill=ORANGE, frame=WOOD, pitch=1.0,
                   corner=.14, skip={'front': [(DOOR_X - .5, DOOR_X + .5)]},
                   windows={'left': [(.5, 1.0, .5, 'lancet')], 'right': [(.5, 1.0, .5, 'lancet')]})
    P.door(g, DOOR_X, y0, 0, 'Door0')
    # Ticket window with a counter and an iron awning.
    A.atlas_window(g, 3.5, y0 + .05, 1.05, .46, 'front', 'cross')
    blk(g, 3.2, y0 - .12, .72, 3.8, y0 + .05, .78, WOOD)
    for x in (3.24, 3.76):
        g.beam((x, y0 + .05, 1.38), (x, y0 - .2, 1.42), .03, mat=IRON)
    obox(g, (3.5, y0 - .08, 1.43), (1, 0, 0), (0, math.cos(.35), math.sin(.35)), (0, -math.sin(.35), math.cos(.35)),
         .32, .16, .015, FORGED)
    plank_gable(g, x0 + .05, x1 - .05, y0 + .05, y1 - .05, 1.6, 2.15, ridge_axis='X', overhang=.12, seed=4)
    K.lamp(g, 3.1, y0 + .05, 1.1, face='front')


def build(g, parts):
    tower(g)
    stair(g)
    deck(g, parts)
    kiosk(g)
