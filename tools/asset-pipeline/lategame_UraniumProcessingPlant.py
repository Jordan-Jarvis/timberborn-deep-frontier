"""Uranium Processing Plant: late-game study (Iron Teeth, Deep Frontier).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the loose drums and barrels on the dock.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; outputs/compaction/BRIEF.md): 12x11x14 -> 8x7x8, inside the old
footprint with the same origin, door (x 3.5, face 0.15 behind the front
edge) and native entrance. One layer per floor: the concrete podium is one
storey (layer 0) and the cascade hall one work floor on it (layer 1), under a
flat concrete roof with a flat-roofed clerestory monitor. Removed: the
lattice gantry girder, the layer-4 catwalk and ladder, the two inner
centrifuge rows nobody saw, the stack's work ring and the 13-layer stack.

HERO: the centrifuge cascade, an open-fronted gallery on a concrete podium
where a row of spinning gas centrifuges stands under a solid flat canopy, the
hall behind it lit by a glazed clerestory monitor.
ROOF: flat roofs in varied finishes: concrete on the hall canopy and the
scrubber house, riveted steel plate on the clerestory monitor and the fuel
vault; open parapet rings; no roof vents (roof-variety pass).

Supporting masses: an orange-slurry settling thickener with a rotating rake,
the lead-lined fuel vault, two riveted acid tanks on a concrete bund, and the
scrubber house with a packed scrubber column and its stack. No clutter on
buildable cells (user rule, 2026-10-30): the open drum dock and its jib hoist
are gone, so tiles 6..8 x 2..4 stay free.

Animated: five centrifuge rotor drums (SPIN_Z), thickener rake arms (SPIN_Z),
scrubber roof fan (SPIN_Z), three warning beacons (SPIN_Z).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
from lategame_kit import (stud, CONCRETE, ORANGE, FORGED, PAINTED, CYAN, GLOW, plinth, frame_wall,
                          revolve, band, dome, tank, stack, hollow_revolve, flat_roof,
                          steel_rail, ladder, lamp, beacon, beacon_shutter, fan, valve_wheel)
from lategame_nuclear_parts import (bx, Facer, trefoil, gauge, drum, riveted_panel, straight_pipe,
                                    pipe_path, valve, frustum)
from industrial_facades import building_portal
from architectural_windows import window
from lategame_roofdeck_parts import parapet_ring
from lategame_sheet_roofs import plate_deck
import lategame_mining_parts as M

IDENT = 'UraniumProcessingPlant'
FOOTPRINT = (8, 7)
HEIGHT = 8
HERO = ('Centrifuge cascade: an open-fronted gallery on a concrete podium with a row of spinning '
        'centrifuges under a flat canopy, lit by a glazed clerestory monitor.')
FRAME_END = 121

PX0, PX1 = 0.0, 6.0         # podium on tiles 0..6 x 0..4
PY0, PY1 = .15, 4.0         # front (door) face .15 off the tile edge
DECK = 1.0                  # podium top: the cascade work floor (layer 1)
HYF = 1.75                  # hall front wall behind the open cascade row
ROOF_Z = 3.84               # canopy / hall roof slab bottom; its top is layer 4
ROW_Y = .95
COLS = [.85, 1.95, 3.05, 4.15, 5.25]
CASING = 1.3                # centrifuge casing height above its pedestal
MON = (1.1, 4.9, 2.2, 3.55) # clerestory monitor x0, x1, y0, y1
MON_TOP = 5.0                # monitor roof top on layer 5


def podium(g):
    # One-storey podium: a solid core with a proud concrete course, notched
    # for the native one-tile door (layer 0); its top is the deck (layer 1).
    M.plinth_course(g, PX0 + .05, PX1 - .05, PY0 + .12, PY1 - .05, 0, DECK, CONCRETE, [3.5])
    M.portal(g, 3.5, PY0 + .12, 0, ident='Main')
    lamp(g, 2.85, PY0 + .07, .7, face='front')
    lamp(g, 4.15, PY0 + .07, .7, face='front')
    for x in (1.0, 5.4):
        window(g, x, PY0 + .07, .5, .55, 'front', 'grand')
    for y in (1.0, 2.6):
        window(g, PX0, y, .5, .55, 'left', 'grand')


def column(g, x, y, top):
    bx(g, x - .16, y - .16, DECK + .02, x + .16, y + .16, top, CONCRETE)
    bx(g, x - .2, y - .2, DECK, x + .2, y + .2, DECK + .14, CONCRETE)


def hall(g, parts):
    podium(g)
    # Hall walls on the deck: forged front behind the open row, orange back.
    tier = 2.45
    frame_wall(g, 'X', HYF, PX0 + .12, PX1 - .12, DECK + .012, ROOF_Z, outward=-1, infill=FORGED, bays=5,
               windows=[(x, tier) for x in (1.4, 2.5, 3.6, 4.7)], window_style='factory', window_scale=.62)
    frame_wall(g, 'X', PY1 - .12, PX0 + .12, PX1 - .12, DECK + .012, ROOF_Z, outward=1, infill=ORANGE, bays=5,
               windows=[(x, tier) for x in (.9, 2.3, 3.7, 5.1)], window_style='factory', window_scale=.62)
    for x, out in ((PX0 + .12, -1), (PX1 - .12, 1)):
        frame_wall(g, 'Y', x, HYF + .05, PY1 - .17, DECK + .012, ROOF_Z, outward=out, infill=FORGED, bays=2,
                   windows=[(2.85, tier)], window_style='factory', window_scale=.62)
    # Solid flat canopy over the open row and the hall, on three concrete columns.
    for x in (PX0 + .3, 2.5, PX1 - .3):
        column(g, x, PY0 + .3, ROOF_Z)
    bx(g, PX0 + .1, PY0 + .1, ROOF_Z - .22, PX1 - .1, PY0 + .5, ROOF_Z, CONCRETE)
    flat_roof(g, PX0 + .05, PY0 + .1, PX1 - .05, PY1 - .05, ROOF_Z, overhang=.05)
    roof = ROOF_Z + .16
    parapet_ring(g, PX0, PY0 + .05, PX1, PY1, roof, height=.24, open_sides=('front',))
    # The hall is a solid room (its cells are the building's, not free space).
    bx(g, PX0 + .22, HYF + .07, DECK + .012, PX1 - .22, PY1 - .2, ROOF_Z, IRON)
    # Orange name board on the canopy fascia, lamps under it.
    f = Facer(3.5, PY0 + .1 - .05, 0, 'front')
    riveted_panel(g, f, -.8, .8, ROOF_Z - .2, ROOF_Z + .1, 0, .04, ORANGE)
    trefoil(g, 1.5, PY0 + .02, ROOF_Z - .05, face='front', r=.14)
    # Rails on the open bay's front and ends.
    for a, b in ((PX0 + .5, 2.3), (2.7, PX1 - .5)):
        steel_rail(g, (a, PY0 + .22), (b, PY0 + .22), DECK, pitch=.8)
    for x in (PX0 + .12, PX1 - .12):
        steel_rail(g, (x, PY0 + .5), (x, HYF - .1), DECK, pitch=.8)
    # Clerestory monitor: forged walls with factory windows, flat roof.
    x0, x1, y0, y1 = MON
    for y, out in ((y0, -1), (y1, 1)):
        frame_wall(g, 'X', y, x0, x1, roof, MON_TOP - .16, outward=out, infill=FORGED, bays=4,
                   windows=[(x0 + (i + .5) * (x1 - x0) / 4, roof + .32) for i in range(4)],
                   window_style='factory', window_scale=.5)
    for x, out in ((x0, -1), (x1, 1)):
        bx(g, x - .05 if out < 0 else x - .05, y0 + .05, roof, x + .05, y1 - .05, MON_TOP - .16, FORGED)
    plate_deck(g, x0, y0, x1, y1, MON_TOP, mat=FORGED, overhang=.12)   # riveted steel plate roof
    bx(g, x0 + .1, y0 + .1, roof, x1 - .1, y1 - .1, MON_TOP - .16, IRON)   # solid monitor room
    # Centrifuge cascade: the open-air row of five.
    for i, x in enumerate(COLS):
        centrifuge(g, parts, f'Centrifuge0{i}', x, ROW_Y)
    hz = DECK + .16 + CASING + .12 + .62 + .2
    straight_pipe(g, (PX0 + .4, ROW_Y, hz), (PX1 - .4, ROW_Y, hz), .07, flanges=False)
    for x in COLS:
        g.cylinder((x, ROW_Y, hz - .17), .04, .24, BRASS, 'Z', 8)
    for x in (1.4, 3.6, 4.7):
        bx(g, x - .035, ROW_Y - .035, hz + .06, x + .035, ROW_Y + .035, ROOF_Z - .22, IRON)
    pipe_path(g, [(PX1 - .4, ROW_Y, hz), (PX1 - .4, ROW_Y, DECK + .35), (PX1 - .4, HYF - .1, DECK + .35)], .07)
    valve(g, (PX1 - .4, 1.35, DECK + .35), .07, 'Y', wheel_face='right')
    # Control desk at the left end of the row.
    bx(g, .25, 1.35, DECK, .6, 1.65, DECK + .62, PAINTED)
    gauge(g, .42, 1.35, DECK + .45, face='front', r=.07)
    bx(g, .3, 1.31, DECK + .22, .55, 1.35, DECK + .27, CYAN)


def beacon_part(g, parts, name, x, y, z):
    px, py, pz = beacon(g, x, y, z)
    parts.append((beacon_shutter(px, py, pz, name), 'SPIN_Z', 2))


def centrifuge(g, parts, name, x, y):
    bx(g, x - .27, y - .27, DECK, x + .27, y + .27, DECK + .16, CONCRETE)
    z0 = DECK + .16
    revolve(g, (x, y, z0), [(.24, 0), (.24, CASING), (.27, CASING + .12)], CONCRETE, segments=8)
    band(g, (x, y, 0), .24, z0 + .95, .07, BRASS, segments=8)
    gauge(g, x, y - .24, z0 + .5, face='front', r=.065)
    base = z0 + CASING + .12
    r = Geometry(name, (x, y, base))
    revolve(r, (x, y, base + .012), [(.28, 0), (.28, .46), (0, .58)], IRON, segments=12, cap_bottom=False)
    for k in range(3):
        a = k * 2 * math.pi / 3
        r.box((x + math.cos(a) * .295, y + math.sin(a) * .295, base + .24), (.05, .05, .42), IRON)
    a = math.pi / 6
    r.box((x + math.cos(a) * .295, y + math.sin(a) * .295, base + .24), (.04, .04, .2), ORANGE)
    band(r, (x, y, 0), .28, base + .39, .05, BRASS, segments=12)
    parts.append((r, 'SPIN_Z', 4))


def thickener(g, parts):
    cx, cy = 7.0, 1.0      # tiles 6..8 x 0..2
    hollow_revolve(g, (cx, cy, 0), [(.92, 0), (.92, .9)], .18, CONCRETE, segments=12)
    revolve(g, (cx, cy, .012), [(.98, 0), (.98, .18)], CONCRETE, segments=12)
    g.ring((cx, cy, .8), .945, .045, .08, IRON, 'Z', 12)
    revolve(g, (cx, cy, .03), [(.75, 0), (.75, .72)], ORANGE, segments=12, cap_bottom=False)
    revolve(g, (cx, cy, .72), [(.16, 0), (.16, .32)], CONCRETE, segments=12)
    revolve(g, (cx, cy, 1.04), [(.22, 0), (.22, .16), (.15, .22), (.15, .3)], IRON, segments=12)
    g.box((cx - .25, cy, 1.15), (.22, .16, .14), PAINTED)
    # Fixed worker bridge from the left rim to the drive head.
    bx(g, cx - .92, cy - .2, 1.18, cx - .2, cy + .2, 1.24, IRON)
    for y in (cy - .17, cy + .17):
        steel_rail(g, (cx - .88, y), (cx - .25, y), 1.24, pitch=.4, height=.5)
    rake = Geometry('ThickenerRake', (cx, cy, .82))
    for s in (-1, 1):
        rake.beam((cx, cy, .86), (cx + s * .7, cy, .86), .07, .07, IRON)
        for k in range(3):
            xx = cx + s * (.25 + k * .2)
            rake.beam((xx, cy, .83), (xx, cy, .6), .035, mat=IRON)
            rake.box((xx, cy, .7), (.05, .16, .05), PAINTED)
    rake.ring((cx, cy, .84), .3, .04, .1, IRON, 'Z', 12)
    parts.append((rake, 'SPIN_Z', 1))
    gauge(g, cx + .92, cy - .2, .55, face='right', r=.08)


def fuel_vault(g, parts):
    x0, y0, x1, y1 = 3.03, 4.03, 5.0, 7.0   # fuel vault on tiles 3..5 x 4..7
    bx(g, x0, y0, 0, x1, y1, 2.0, CONCRETE)
    bx(g, x0 - .05, y0 - .05, 1.9, x1 + .05, y1 + .05, 2.012, CONCRETE)
    for x in (x0 + .3, x1 - .3):
        bx(g, x - .08, y1, 0, x + .08, y1 + .06, 1.9, CONCRETE)
    # Lead-lined door on the back face: forged leaves in a steel frame.
    f = Facer(4.0, y1, 0, 'back')
    f.box(g, 0, .865, -.03, 1.0, 1.67, .1, IRON)
    for u in (-.22, .22):
        riveted_panel(g, f, u - .2, u + .2, .15, 1.6, .02, .06, FORGED, rivets=False)
    valve_wheel(g, *f.p(0, .95, .11), face='back', r=.16)
    plate_deck(g, x0 + .1, y0 + .1, x1 - .1, y1 - .1, 2.032, mat=FORGED, t=.04)   # riveted steel plate
    parapet_ring(g, x0 - .05, y0 - .05, x1 + .05, y1 + .05, 2.012, height=.28)


def acid_tanks(g, parts):
    # Concrete tank bund (tiles 0..3 x 4..7, top layer 1) carrying both tanks.
    bx(g, 0.0, 4.0, 0, 3.0, 7.0, .9, CONCRETE)
    bx(g, 0.0, 4.0, .9, 3.02, 7.03, 1.0, CONCRETE)
    for x in (.5, 1.5, 2.5):
        bx(g, x - .05, 7.0, .12, x + .05, 7.04, .8, CONCRETE)
    for x, mat in ((.8, IRON), (2.2, PAINTED)):
        y = 5.55
        tank(g, x, y, 1.0, .55, 1.9, mat=mat, bands=3, roof='cone', segments=12)
        pipe_path(g, [(x, y - .55, 1.55), (x, PY1 + .02, 1.55)], .07)
        valve(g, (x, 4.55, 1.55), .07, 'Y', wheel_face='up')
        gauge(g, x + .32, y - .48, 1.9, face='front', r=.08)
    pipe_path(g, [(1.33, 5.55, 2.8), (1.67, 5.55, 2.8)], .06)


def scrubber(g, parts):
    x0, y0, x1, y1 = 5.03, 4.03, 8.0, 7.0   # scrubber house on tiles 5..8 x 4..7
    bx(g, x0, y0, 0, x1, y1, 1.84, CONCRETE)
    flat_roof(g, x0, y0, x1, y1, 1.84, overhang=.0)
    parapet_ring(g, x0, y0, x1, y1, 2.0, height=.28)
    for x in (5.7, 7.3):
        window(g, x, y1, .9, .55, 'back', 'factory')
    window(g, x1, 5.0, .9, .55, 'right', 'factory')
    window(g, x1, 6.2, .9, .55, 'right', 'factory')
    roof = 2.0
    # Packed scrubber column.
    cx, cy = 5.9, 5.0
    revolve(g, (cx, cy, 0.03), [(.46, 0), (.46, roof + 3.9 - .03)], IRON, segments=12)   # rises from the ground
    revolve(g, (cx, cy, roof), [(.6, 0), (.6, .18), (.46, .22)], IRON, segments=12, cap_top=False)
    for z in (3.0, 4.6):
        band(g, (cx, cy, 0), .46, z, .08, PAINTED, segments=12)
    dome(g, (cx, cy, roof + 3.9), .47, IRON, segments=12, squash=.5)
    for z in (3.4,):
        gauge(g, cx, cy - .46, z, face='front', r=.09)
    beacon_part(g, parts, 'ColumnBeacon', cx, cy, roof + 3.9 + .235)
    # Stack on a cast pedestal, joined to the column by a duct.
    sx, sy = 7.2, 6.15
    bx(g, sx - .5, sy - .5, 0.03, sx + .5, sy + .5, 2.6, CONCRETE)   # pedestal rises from the ground
    bx(g, sx - .55, sy - .55, 2.52, sx + .55, sy + .55, 2.64, CONCRETE)
    stack(g, sx, sy, 2.64, 5.06, emits='steam', r=.32, taper=.82, bands=3)
    pipe_path(g, [(cx, cy + .3, 5.1), (cx, sy, 5.1), (sx - .24, sy, 5.1)], .13, flanges=True)
    bx(g, sx - .05, sy - .37, 6.3, sx + .05, sy - .27, 6.5, IRON)
    beacon_part(g, parts, 'StackBeacon', sx, sy - .32, 6.5)
    # Off-gas duct from the hall's back wall into the scrubber column.
    pipe_path(g, [(5.6, PY1 - .02, 2.9), (5.6, cy - .46, 2.9)], .14)


def build(g, parts):
    hall(g, parts)
    thickener(g, parts)
    fuel_vault(g, parts)
    acid_tanks(g, parts)
    scrubber(g, parts)

