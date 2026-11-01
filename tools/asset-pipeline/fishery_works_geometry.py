"""Fishery Works, second shrink pass (2026-11-01): 11x8x4 -> 6x5x3.

A YouTuber's first look called the buildings "massive"; the user: "we need to
shrink the buildings down even more". The waterfront works keeps what makes it
a fishery: the processing hall under its long gabled roof (the works'
defining silhouette), the water wheel, header, cascade and basins, the crane
lowering its net into a basin, the carved fish sign and the two water tanks
that are the Timber Pipes inlet.

Authored in native grid coordinates (layout origin [0, 0, 0]; until this pass
the art had its own source frame, origin [1.25, -1.30]). X runs across the
front, Y back, Z up; one unit is one tile and one layer.

  Water wing      x 0..2, y 0..5 (on the left; the hall needs the door cell
                  (3,0,0) clear of its corner post): the long and small basins,
                  the native compact wheel under the header basin, the
                  cascade, and the crane over the small basin. The basins may
                  overhang a lower bank on adaptive piles
                  (tools/waterside_sites.json).
  Lower hall      x 2..6, y 0..4, one storey (0..1); ground door x 3.5 on the
                  front, door cell (3,0,0) as before. Its flat timber roof at
                  layer 1 is an open deck (no rails).
  Upper hall      x 2.25..4.75, y 2.1..4.9, one storey (1..2) under the long
                  gabled roof (ridge along Y, top 2.85); its door x 3.5 opens
                  onto the front deck (3,1,1).
  Undercroft      x 2..5, y 4..5 under the upper hall: the two water tanks
                  (pipe inlet, cell (3,4,0) Up) and a drying net.
"""
import math

from frontier_architecture import Geometry, WOOD, IRON, SAND, BRASS, deck
from reference_materials import WATER, CLOTH, CIVIC_FORGED_PANEL
from brick_courses import BRICK
from industrial_budget import round_pipe
from native_building_assets import water_barrel, prop
from walkway_geometry import RailAssembly
from civic_isometric_geometry import (CIVIC_ACCESS, CIVIC_TERRACES, framed_room, component_doorway_storey,
                                      roof_bearing, gabled_roof, glazing, hanging_board_storey, fishing_net,
                                      basin, timber_column, beam_joint)

FOOTPRINT = (6, 5)
UPPER = (2.25, 2.10, 4.75, 4.90)   # upper hall frame (x0, y0, x1, y1)

# The civic study contracts (render_reference_studies / civic_validation) for
# this model are defined with its art: no galleries (balconyLayers []); the
# front deck on the lower hall's roof is the terrace, reached through the
# upper hall door at layer 1.
CIVIC_ACCESS['FisheryWorks'] = {'entrance': [3.5, .09, 0], 'balconyLayers': [], 'headroom': .85,
                                'routes': [], 'stairBays': []}
CIVIC_TERRACES['FisheryWorks'] = {'bounds': [2.0, 0.0, 6.0, 2.0], 'layer': 1,
                                  'clearArea': [2.20, .20, 5.70, 1.65]}


def crane(g, parts, x, y, reach):
    """Small timber crane: a mast on a brick foot, a jib along -X and the
    swaying rope net (`FisheryWorks.CraneNet`) over the small basin."""
    timber_column(g, x, y, 0, 2.62, .22, foot=BRICK)
    beam_joint(g, (x - reach - .05, y, 2.58), (x, y, 2.58), .18, .20)
    g.beam((x, y, 1.80), (x - reach * .62, y, 2.58), .12, mat=WOOD)
    g.cylinder((x, y, 1.20), .20, .40, IRON, 'Y', 20)
    g.ring((x, y - .22, 1.20), .24, .040, .05, BRASS, 'Y', 20)
    nx = x - reach
    load = Geometry('FisheryWorks.CraneNet', (nx, y, 2.50))
    load.beam((nx, y, 2.50), (nx, y, 1.30), .02, mat=CLOTH)
    for i in range(8):
        a = i * math.pi / 4
        load.beam((nx, y, 1.36), (nx + math.cos(a) * .25, y + math.sin(a) * .25, .98), .016, mat=CLOTH)
        load.beam((nx + math.cos(a) * .25, y + math.sin(a) * .25, .98), (nx, y, .84), .016, mat=CLOTH)
    for z, rr in ((.92, .15), (1.01, .24), (1.11, .18)):
        load.ring((nx, y, z), rr, .010, .015, CLOTH, 'Z', 16)
    for i in range(6):
        load.rock((nx - .13 + (i % 3) * .13, y - .06 + (i // 3) * .12, 1.03), (.15, .15, .12), SAND, 500 + i)
    parts.append((load, 'SWAY', .025))


def fishery(g, parts):
    r = RailAssembly('WalkwayRail.FisheryWorks')
    # Lower processing hall, one storey; the front wall stands .25 in so the
    # door casing stays inside the front row.
    framed_room(g, 2.10, .25, 5.90, 3.90, 0, .95, 4, (3.5, 1.0, 1.0), wall_style='storey')
    component_doorway_storey(g, 'FisheryWorks', 'Door1')
    # Its flat roof: one open timber deck at layer 1, edge to edge (the front
    # strip is the canopy over the door), continued behind the hall as the
    # undercroft's ceiling under the upper hall.
    deck(g, 2.0, 0.0, 5.0, 5.0, .93)
    deck(g, 5.0, 0.0, 5.985, 3.90, .93)   # 15 mm inside the hall's side beam face
    for x in (2.12, 4.88):
        timber_column(g, x, 4.88, 0, .86, .20, foot=BRICK)
    # Upper hall under the long gabled roof (the works' silhouette).
    x0, y0, x1, y1 = UPPER
    framed_room(g, x0, y0, x1, y1, 1, 1.95, 3, (3.5, 1.0, 1.0), infill=CIVIC_FORGED_PANEL, wall_style='storey')
    component_doorway_storey(g, 'FisheryWorks', 'Door0')
    roof_bearing(g, x0, y0, x1, y1, 1.95, 2.05)
    gabled_roof(g, x0 - .22, y0 - .20, x1 + .22, y1 + .08, 2.05, 2.85, 310)
    glazing(g, 3.5, y0 - .245, 2.42, .42, style='diamond')
    # Windows: factory panes on the lower hall, lancets at the back above.
    for x in (2.62, 4.45):
        glazing(g, x, .19, .48, .50, style='factory')
    for y in (1.30, 2.80):
        glazing(g, 5.96, y, .48, .50, 'right', 'factory')
    for y in (2.95, 4.05):
        glazing(g, x0 - .06, y, 1.48, .46, 'left', 'factory')
        glazing(g, x1 + .06, y, 1.48, .46, 'right', 'factory')
    for x in (2.90, 4.10):
        glazing(g, x, y1 + .06, 1.48, .46, 'back', 'lancet')
    # Carved fish sign under the deck's front edge, right of the door.
    hanging_board_storey(g, parts, 'FisheryWorks', 5.25, .12, .50, .80)
    # Undercroft: the two water tanks (the Timber Pipes inlet, cell (3,4,0))
    # and a drying net on the lower hall's back wall.
    for i, x in enumerate((3.62, 4.38)):
        water_barrel(g, 'FisheryWaterBarrel' + str(i), (x, 4.48, 0), .62)
    fishing_net(g, 2.70, 4.02, .84, .80, .62)
    # Water wing: the native compact wheel under the header basin, the long
    # and small basins, and the cascade between them.
    prop(g, 'FisheryNativeWheel', 'CompactWaterWheel.IronTeeth', (0.60, 4.80, .03), 1, 90)
    basin(g, .20, 1.95, 1.65, 4.95)
    basin(g, .20, .05, 1.65, 1.80)
    # The header basin sits just above the native wheel (1.69 tall).
    basin(g, .73, 3.50, 1.47, 4.95, 1.72)
    flow = Geometry('FisheryCascade')
    flow.add([(.85, 3.50, 2.16), (1.35, 3.50, 2.16), (.83, 3.07, 1.90), (1.37, 3.07, 1.90),
              (.81, 2.10, .64), (1.39, 2.10, .64)], [(0, 1, 3, 2), (2, 3, 5, 4)], WATER)
    parts.append((flow, 'STATIC', 0))
    # Feed from the header down to the tanks in the undercroft.
    round_pipe(g, [(1.10, 4.70, 2.16), (1.10, 4.86, 2.16), (1.10, 4.86, .55), (3.25, 4.86, .55)], .10)
    crane(g, parts, 1.84, .32, 1.30)
    return r
