"""RadioactiveWasteExport: ships radioactive sludge and contaminated water off

the map (docs/radiation.md; must touch the map edge, MapEdgeSiteSpec).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the spare casks on the dock.

Compacted 2026-10-30 (light touch, outputs/compaction/BRIEF.md): 6x5x4 ->
6x5x3. One layer per floor: the fill house is a concrete ground storey
(layer 0, the hauler door) and one lead-clad storey (layer 1) under a flat
roof whose top is layer 2, an open platform edge to edge.

Shrunk again 2026-11-01 (user: "we need to shrink the buildings down even
more"): 6x5x3 -> 4x3x3, inside the old footprint with the same origin, door
(x 1.5) and native entrance (1,-1); the back (map-edge) side stays 'Up'. The
fill house is two tiles deep (tiles 0..3 x 0..2), the track runs in the
right column out through the dispatch gate on the back row, and the Timber
Pipes socket moves from the old front-right manifold (cell 5,0) to the fill
house front right of the door (cell 2,0, facing Down); the separate manifold
block and the kerb sign post are gone.

HERO: a lead-lined cask car on rails that runs from a steel filling gantry
out through a hazard-striped dispatch gate on the back (map-edge) side.
ROOF: flat open roof (no parapet) on the lead-lined fill house; open steel
gantry and gate.

Accents: the late-game palette has no yellow-green (or yellow) native material;
brass renders silver-grey. Hazard bands, cask bands and trefoil discs use
native orange plaster, as on the rest of the nuclear chain, sparingly.

Animated: cask car (SLIDE_Y) out to the gate and back, filling nozzle
(PISTON_Z), gate beacon (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN, LAYER_GAP
import lategame_industry_parts as P
import lategame_civic_parts as C
from lategame_civic_parts import blk
from lategame_nuclear_parts import Facer, prism
from industrial_facades import building_portal
from native_window_atlas import atlas_window
import lategame_mining_parts as M

IDENT = 'RadioactiveWasteExport'
FOOTPRINT = (4, 3)
HEIGHT = 3
FRAME_END = 121
HERO = ('Lead-lined cask car on rails running from a steel filling gantry out through a hazard-striped '
        'dispatch gate on the map-edge side.')

# The back edge (+Y, 'Up') is the side that must touch the map edge.
MAP_EDGE = 'Up'
# Timber Pipes inlet for RadioactiveSludge / ContaminatedWater on the fill
# house's front face, right of the door (local block coordinates; Down = -Y).
PIPE_INLET = {'cell': [2, 0, 0], 'direction': 'Down', 'state': 'OpenIn',
              'goods': ['RadioactiveSludge', 'ContaminatedWater'], 'socket': [2.5, .16, .55]}

DOOR_X = 1.5
TRACK_X = 3.5
FILL_Y = .85
CAR_TRAVEL = 1.6
RAIL_TOP = .27
HOUSE = (0.0, .15, 2.95, 2.0)   # fill house; the dock row y 2..3 behind it


def rad_sign(g, x, y, z, face='front', r=.22):
    """Trefoil sign: dark plate, brass disc, dark blades."""
    f = Facer(x, y, z, face)
    s = 2 * r + .1
    f.box(g, 0, 0, .02, s, s, .04, IRON)
    segs = 12
    prism(g, f, [(math.cos(i * 2 * math.pi / segs) * r, math.sin(i * 2 * math.pi / segs) * r)
                 for i in range(segs)], .03, .06, ORANGE)
    ri, ro = r * .26, r * .86
    for k in range(3):
        a0 = math.pi / 2 + k * 2 * math.pi / 3 - math.pi / 6
        a1 = a0 + math.pi / 3
        outer = [(math.cos(a0 + (a1 - a0) * i / 5) * ro, math.sin(a0 + (a1 - a0) * i / 5) * ro) for i in range(6)]
        inner = [(math.cos(a1 - (a1 - a0) * i / 5) * ri, math.sin(a1 - (a1 - a0) * i / 5) * ri) for i in range(6)]
        prism(g, f, outer + inner, .05, .075, IRON)
    prism(g, f, [(math.cos(i * math.pi / 5) * r * .16, math.sin(i * math.pi / 5) * r * .16) for i in range(10)],
          .05, .075, IRON)


def stripes_x(g, x0, x1, y0, y1, z0, z1, n):
    """Alternating brass / dark hazard blocks along X (dark blocks recessed)."""
    w = (x1 - x0) / n
    for i in range(n):
        a = x0 + i * w
        if i % 2 == 0:
            blk(g, a, y0, z0, a + w, y1, z1, ORANGE)
        else:
            blk(g, a + .002, y0 + .006, z0 + .006, a + w - .002, y1 - .006, z1 - .006, IRON)


# ---------------------------------------------------------------- ground

def ground(g):
    blk(g, 3.0, 0.0, -.02, 4.0, 3.0, .2, CONCRETE)        # track bed
    blk(g, 0.0, 2.05, -.02, 3.0, 3.0, .2, CONCRETE)       # cask dock on the map-edge row


# ---------------------------------------------------------------- fill house

def fill_house(g, parts):
    x0, y0, x1, y1 = HOUSE
    # Concrete ground storey: solid core with a proud course, notched for the door.
    M.plinth_course(g, x0 + .05, x1 - .05, y0 + .12, y1 - .05, 0, 1.0, CONCRETE, [DOOR_X])
    M.portal(g, DOOR_X, y0 + .12, 0, ident='HaulerDoor')
    top = 1.0
    K.lamp(g, DOOR_X - .62, y0 + .07, .75, face='front')
    bx0, by0, bx1, by1 = x0 + .1, y0 + .1, x1 - .1, y1 - .1
    z1 = 1.84
    C.framed_block(g, bx0, by0, bx1, by1, top + .012, z1, infill=FORGED, frame=CONCRETE, pitch=.9, corner=.2,
                   sink=.03, windows={'left': [(1.05, 1.42, .45, 'factory')]})
    for x in (.62, 2.33):
        atlas_window(g, x, by0, 1.42, .2, 'front', 'slit')
    atlas_window(g, bx1, .6, 1.42, .2, 'right', 'slit')
    atlas_window(g, bx1, 1.5, 1.42, .2, 'right', 'slit')
    rad_sign(g, DOOR_X, by0 - .055, 1.42, 'front', .2)
    stripes_x(g, bx0 + .12, bx1 - .12, by0 - .085, by0 - .055, 1.06, 1.16, 9)
    K.flat_roof(g, bx0, by0, bx1, by1, z1, thickness=.16, overhang=.1)
    # Shielded hatch toward the track: heavy sliding plate on rails.
    blk(g, bx1 + .055, .55, top + .1, bx1 + .14, 1.45, top + .7, IRON)
    for z in (top + .14, top + .66):
        blk(g, bx1 + .14, .45, z - .03, bx1 + .18, 1.55, z + .03, PAINTED)


# ---------------------------------------------------------------- inlet, gantry, track

def manifold(g):
    """Timber Pipes socket on the house front, its riser and the feed to the filling hood."""
    sx, sy, sz = PIPE_INLET['socket']
    blk(g, sx - .25, sy + .04, sz - .25, sx + .25, .32, sz + .2, PAINTED)
    g.cylinder((sx, sy + .02, sz), .15, .08, IRON, 'Y', 16)
    P.hoop(g, (sx, sy - .03, sz), .2, .05, .04, BRASS, axis='Y', segments=16)
    K.bolt_row(g, (sx - .16, sy - .06, sz + .14), (sx + .16, sy - .06, sz + .14), 3, r=.016)
    P.pipe(g, [(sx, .05, sz + .2), (sx, .05, 2.2), (3.3, .05, 2.2), (3.3, FILL_Y - .24, 2.2)], .06, flanges=False)
    P.valve(g, (sx, .05, 1.3), 'front', .1)
    P.gauge(g, sx + .3, .15, .45, 'front', .06)


def gantry(g, parts):
    y = FILL_Y
    for x in (3.06, 3.94):
        P.pier(g, x, y, .17, .45, .12)
        blk(g, x - .055, y - .06, .5, x + .055, y + .06, 2.5, IRON)
    blk(g, 3.0, y - .1, 2.5, 4.0, y + .1, 2.7, IRON)
    stripes_x(g, 3.15, 3.85, y - .13, y - .1, 2.53, 2.67, 5)
    # Filling hood and its moving nozzle.
    blk(g, TRACK_X - .26, y - .24, 1.95, TRACK_X + .26, y + .24, 2.5, FORGED)
    for z in (2.0, 2.44):
        blk(g, TRACK_X - .28, y - .26, z - .03, TRACK_X + .28, y + .26, z + .03, IRON)
    n = Geometry('RadioactiveWasteExport.Nozzle', (TRACK_X, y, 1.75))
    n.cylinder((TRACK_X, y, 1.85), .08, .6, IRON, 'Z', 12)
    P.hoop(n, (TRACK_X, y, 1.66), .12, .04, .06, BRASS, segments=12)
    n.cylinder((TRACK_X, y, 1.55), .055, .06, IRON, 'Z', 10)
    parts.append((n, 'PISTON_Z', -.3))


def track(g):
    for s in (-1, 1):
        blk(g, TRACK_X + s * .25 - .03, .25, .2, TRACK_X + s * .25 + .03, 2.98, RAIL_TOP, IRON)
    for k in range(7):
        y = .45 + k * .36
        blk(g, TRACK_X - .36, y - .06, .19, TRACK_X + .36, y + .06, .225, WOOD)
    # Buffer at the house end.
    blk(g, TRACK_X - .33, .2, .2, TRACK_X + .33, .32, .6, IRON)
    blk(g, TRACK_X - .28, .32, .43, TRACK_X + .28, .36, .53, ORANGE)


def cask_car(g, parts):
    y = FILL_Y
    c = Geometry('RadioactiveWasteExport.CaskCar', (TRACK_X, y, .5))
    blk(c, TRACK_X - .3, y - .4, .34, TRACK_X + .3, y + .4, .46, PAINTED)
    for dy in (-.25, .25):
        for s in (-1, 1):
            c.cylinder((TRACK_X + s * .25, y + dy, RAIL_TOP + .1), .1, .05, IRON, 'X', 12)
    for dy in (-.44, .44):
        blk(c, TRACK_X - .26, y + dy - .04, .36, TRACK_X + .26, y + dy + .04, .44, IRON)
    # Lead-lined cask in its cradle: finned body, hazard band, bolted lid.
    z0 = .46
    blk(c, TRACK_X - .3, y - .18, z0, TRACK_X + .3, y + .18, z0 + .12, IRON)
    P.lathe(c, (TRACK_X, y, z0 + .05), [(.3, 0), (.32, .07), (.32, .74), (.28, .8)], IRON, segments=12)
    for k in range(12):
        a = k * math.pi / 6
        c.box((TRACK_X + math.cos(a) * .34, y + math.sin(a) * .34, z0 + .42), (.045, .045, .54), IRON)
    K.band(c, (TRACK_X, y, 0), .32, z0 + .42, .09, ORANGE, segments=12, proud=.035)
    c.cylinder((TRACK_X, y, z0 + .87), .22, .04, PAINTED, 'Z', 16)
    for k in range(8):
        a = k * math.pi / 4
        c.cylinder((TRACK_X + math.cos(a) * .17, y + math.sin(a) * .17, z0 + .905), .022, .03, BRASS, 'Z', 6)
    c.box((TRACK_X, y, z0 + .95), (.26, .05, .05), IRON)
    parts.append((c, 'SLIDE_Y', CAR_TRAVEL))


def dock(g, parts):
    # Striped quay kerb on the map edge, open where the track runs out.
    for xa, xb in ((0.02, 2.92), (3.92, 3.98)):
        blk(g, xa, 2.8, .17, xb, 2.98, .3, CONCRETE)
        if xb - xa > .3:
            stripes_x(g, xa + .02, xb - .02, 2.82, 2.96, .3, .36, max(2, round((xb - xa) / .22)))
    # Dispatch gate astride the track.
    gy = 2.6
    for x in (3.06, 3.94):
        P.pier(g, x, gy, .17, .42, .12)
        blk(g, x - .055, gy - .06, .45, x + .055, gy + .06, 2.15, IRON)
    blk(g, 3.0, gy - .09, 2.15, 4.0, gy + .09, 2.36, IRON)
    stripes_x(g, 3.15, 3.85, gy - .12, gy - .09, 2.18, 2.33, 5)
    rad_sign(g, 3.5, gy - .09, 1.85, 'front', .15)
    pivot = K.beacon(g, 3.5, gy, 2.36)
    parts.append((K.beacon_shutter(*pivot, 'RadioactiveWasteExport.Beacon'), 'SPIN_Z', 2))
    # Trefoil on the fill house's back wall over the dock.
    rad_sign(g, 1.5, HOUSE[3] - .05, 1.42, 'back', .18)


def build(g, parts):
    ground(g)
    fill_house(g, parts)
    manifold(g)
    gantry(g, parts)
    track(g)
    cask_car(g, parts)
    dock(g, parts)
