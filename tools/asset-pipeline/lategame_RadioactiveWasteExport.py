"""RadioactiveWasteExport: ships radioactive sludge and contaminated water off

the map (docs/radiation.md; must touch the map edge, MapEdgeSiteSpec).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the spare casks on the dock.

Compacted 2026-10-30 (light touch, outputs/compaction/BRIEF.md): 6x5x4 ->
6x5x3. One layer per floor: the fill house is a concrete ground storey
(layer 0, the hauler door) and one lead-clad storey (layer 1) under a flat
roof whose top is layer 2, with an open parapet ring (the kit parapet's lid
is gone, so the roof is a usable roof deck). The filling gantry and the
dispatch gate are a layer lower. Footprint, door, pipe inlet and the
map-edge side are unchanged.

HERO: a lead-lined cask car on rails that runs from a steel filling gantry
out through a hazard-striped dispatch gate on the back (map-edge) side.
ROOF: flat parapet roof on the lead-lined fill house; open steel gantry and
gate.

Plan (6 x 5 tiles): the fill house front-left (thick concrete, forged lead
cladding, the hauler door, a trefoil sign); the inlet manifold with the
Timber Pipes socket front-right; the filling gantry over the track; the cask
car; spare casks on cradles on the dock behind the house; the dispatch gate
and striped quay kerb on the back edge, which is the side that must face the
map edge.

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
from lategame_roofdeck_parts import parapet_ring
import lategame_mining_parts as M

IDENT = 'RadioactiveWasteExport'
FOOTPRINT = (6, 5)
HEIGHT = 3
FRAME_END = 121
HERO = ('Lead-lined cask car on rails running from a steel filling gantry out through a hazard-striped '
        'dispatch gate on the map-edge side.')

# The back edge (+Y, 'Up') is the side that must touch the map edge.
MAP_EDGE = 'Up'
# Timber Pipes inlet for RadioactiveSludge / ContaminatedWater on the
# manifold's front face (local block coordinates; Down = -Y).
PIPE_INLET = {'cell': [5, 0, 0], 'direction': 'Down', 'state': 'OpenIn',
              'goods': ['RadioactiveSludge', 'ContaminatedWater'], 'socket': [5.5, .16, .55]}

DOOR_X = 1.5
TRACK_X = 4.5
FILL_Y = 1.25
CAR_TRAVEL = 3.0
RAIL_TOP = .27


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
    blk(g, 3.0, 0.0, -.02, 6.0, 5.0, .2, CONCRETE)        # yard and track bed
    blk(g, 0.0, 3.05, -.02, 3.0, 5.0, .2, CONCRETE)       # cask dock


# ---------------------------------------------------------------- fill house

def fill_house(g, parts):
    x0, y0, x1, y1 = 0.0, .15, 2.95, 3.0
    # Concrete ground storey: solid core with a proud course, notched for the door.
    M.plinth_course(g, x0 + .05, x1 - .05, y0 + .12, y1 - .05, 0, 1.0, CONCRETE, [DOOR_X])
    M.portal(g, DOOR_X, y0 + .12, 0, ident='HaulerDoor')
    top = 1.0
    K.lamp(g, DOOR_X - .62, y0 + .07, .75, face='front')
    K.lamp(g, DOOR_X + .62, y0 + .07, .75, face='front')
    bx0, by0, bx1, by1 = x0 + .1, y0 + .1, x1 - .1, y1 - .1
    z1 = 1.84
    C.framed_block(g, bx0, by0, bx1, by1, top + .012, z1, infill=FORGED, frame=CONCRETE, pitch=.9, corner=.2,
                   sink=.03, windows={'left': [(1.5, 1.42, .5, 'factory')]})
    for x in (.62, 2.23):
        atlas_window(g, x, by0, 1.42, .2, 'front', 'slit')
    atlas_window(g, bx1, .69, 1.42, .2, 'right', 'slit')
    atlas_window(g, bx1, 2.31, 1.42, .2, 'right', 'slit')
    rad_sign(g, DOOR_X, by0 - .055, 1.42, 'front', .2)
    stripes_x(g, bx0 + .12, bx1 - .12, by0 - .085, by0 - .055, 1.06, 1.16, 9)
    K.flat_roof(g, bx0, by0, bx1, by1, z1, thickness=.16, overhang=.1)
    parapet_ring(g, bx0 - .1, by0 - .1, bx1 + .1, by1 + .1, z1 + .16, height=.24)
    # Shielded hatch toward the track: heavy sliding plate on rails.
    blk(g, bx1 + .055, .9, top + .1, bx1 + .14, 1.9, top + .7, IRON)
    for z in (top + .14, top + .66):
        blk(g, bx1 + .14, .8, z - .03, bx1 + .18, 2.0, z + .03, PAINTED)


# ---------------------------------------------------------------- inlet, gantry, track

def manifold(g):
    sx, sy, sz = PIPE_INLET['socket']
    blk(g, 5.0, .3, .17, 5.95, 1.0, .95, CONCRETE)
    blk(g, 4.97, .27, .95, 5.98, 1.03, 1.0, IRON)
    blk(g, sx - .25, sy + .04, sz - .25, sx + .25, .32, sz + .2, PAINTED)
    g.cylinder((sx, sy + .02, sz), .15, .08, IRON, 'Y', 16)
    P.hoop(g, (sx, sy - .03, sz), .2, .05, .04, BRASS, axis='Y', segments=16)
    K.bolt_row(g, (sx - .16, sy - .06, sz + .14), (sx + .16, sy - .06, sz + .14), 3, r=.016)
    P.pipe(g, [(sx, .65, 1.0), (sx, .65, 2.15), (TRACK_X, .65, 2.15), (TRACK_X, FILL_Y - .28, 2.15)], .07,
           flanges=False)
    P.valve(g, (sx, .65, 1.6), 'front', .12)
    P.gauge(g, 5.2, .3, .6, 'front', .07)


def gantry(g, parts):
    y = FILL_Y
    for x in (3.6, 5.4):
        P.pier(g, x, y, .17, .5, .3)
        blk(g, x - .09, y - .09, .55, x + .09, y + .09, 2.5, IRON)
    blk(g, 3.45, y - .11, 2.5, 5.55, y + .11, 2.72, IRON)
    stripes_x(g, 3.7, 5.3, y - .14, y - .11, 2.54, 2.68, 7)
    # Filling hood and its moving nozzle.
    blk(g, TRACK_X - .3, y - .28, 1.95, TRACK_X + .3, y + .28, 2.5, FORGED)
    for z in (2.0, 2.44):
        blk(g, TRACK_X - .32, y - .3, z - .03, TRACK_X + .32, y + .3, z + .03, IRON)
    n = Geometry('RadioactiveWasteExport.Nozzle', (TRACK_X, y, 1.75))
    n.cylinder((TRACK_X, y, 1.85), .09, .6, IRON, 'Z', 12)
    P.hoop(n, (TRACK_X, y, 1.66), .13, .04, .06, BRASS, segments=12)
    n.cylinder((TRACK_X, y, 1.55), .06, .06, IRON, 'Z', 10)
    parts.append((n, 'PISTON_Z', -.3))


def track(g):
    for s in (-1, 1):
        blk(g, TRACK_X + s * .25 - .03, .25, .2, TRACK_X + s * .25 + .03, 4.98, RAIL_TOP, IRON)
    for k in range(13):
        y = .45 + k * .36
        blk(g, TRACK_X - .38, y - .06, .19, TRACK_X + .38, y + .06, .225, WOOD)
    # Buffer at the house end.
    blk(g, TRACK_X - .35, .2, .2, TRACK_X + .35, .32, .62, IRON)
    blk(g, TRACK_X - .3, .32, .45, TRACK_X + .3, .36, .55, ORANGE)


def cask_car(g, parts):
    y = FILL_Y
    c = Geometry('RadioactiveWasteExport.CaskCar', (TRACK_X, y, .5))
    blk(c, TRACK_X - .4, y - .5, .34, TRACK_X + .4, y + .5, .46, PAINTED)
    for dy in (-.32, .32):
        for s in (-1, 1):
            c.cylinder((TRACK_X + s * .25, y + dy, RAIL_TOP + .1), .1, .05, IRON, 'X', 12)
    for dy in (-.55, .55):
        blk(c, TRACK_X - .3, y + dy - .05, .36, TRACK_X + .3, y + dy + .05, .44, IRON)
    # Lead-lined cask in its cradle: finned body, brass hazard band, bolted lid.
    z0 = .46
    blk(c, TRACK_X - .42, y - .2, z0, TRACK_X + .42, y + .2, z0 + .14, IRON)
    P.lathe(c, (TRACK_X, y, z0 + .06), [(.36, 0), (.38, .08), (.38, .86), (.33, .94)], IRON, segments=12)
    for k in range(12):
        a = k * math.pi / 6
        c.box((TRACK_X + math.cos(a) * .4, y + math.sin(a) * .4, z0 + .48), (.05, .05, .64), IRON)
    K.band(c, (TRACK_X, y, 0), .38, z0 + .48, .1, ORANGE, segments=12, proud=.04)
    c.cylinder((TRACK_X, y, z0 + 1.02), .26, .04, PAINTED, 'Z', 16)
    for k in range(8):
        a = k * math.pi / 4
        c.cylinder((TRACK_X + math.cos(a) * .2, y + math.sin(a) * .2, z0 + 1.055), .025, .03, BRASS, 'Z', 6)
    c.box((TRACK_X, y, z0 + 1.1), (.3, .06, .06), IRON)
    parts.append((c, 'SLIDE_Y', CAR_TRAVEL))


def dock(g, parts):
    # Striped quay kerb on the map edge, open where the track runs out.
    for xa, xb in ((0.02, 3.92), (5.08, 5.98)):
        blk(g, xa, 4.8, .17, xb, 4.98, .3, CONCRETE)
        stripes_x(g, xa + .02, xb - .02, 4.82, 4.96, .3, .36, max(2, round((xb - xa) / .22)))
    # Dispatch gate astride the track.
    gy = 4.55
    for x in (3.85, 5.15):
        P.pier(g, x, gy, .17, .45, .26)
        blk(g, x - .08, gy - .08, .5, x + .08, gy + .08, 2.2, IRON)
    blk(g, 3.72, gy - .1, 2.2, 5.28, gy + .1, 2.42, IRON)
    stripes_x(g, 3.9, 5.1, gy - .13, gy - .1, 2.23, 2.39, 5)
    rad_sign(g, 4.5, gy - .1, 1.9, 'front', .18)
    for x in (4.38, 4.62):
        blk(g, x - .015, gy - .135, 2.1, x + .015, gy - .105, 2.22, IRON)
    pivot = K.beacon(g, 4.5, gy, 2.42)
    parts.append((K.beacon_shutter(*pivot, 'RadioactiveWasteExport.Beacon'), 'SPIN_Z', 2))
    # Sign post by the kerb.
    blk(g, 5.6, 4.3, .2, 5.66, 4.36, 1.7, IRON)
    rad_sign(g, 5.63, 4.3, 1.5, 'front', .18)


def build(g, parts):
    ground(g)
    fill_house(g, parts)
    manifold(g)
    gantry(g, parts)
    track(g)
    cask_car(g, parts)
    dock(g, parts)
