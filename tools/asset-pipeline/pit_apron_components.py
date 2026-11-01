"""Independent mineral-yard aprons with physical timber above native terrain."""
import math
from frontier_architecture import Geometry, WOOD, PLANK, deck

# Current yard floors, inside the 3x3 footprints (2026-11-01; artwork =
# grid - origin). Both end 4 cm inside the side and rear tile edges. The
# sandstone floor covers the whole yard; the limestone floor starts at its
# door's front edge and stops at the hoist column (grid x 2.13), so the free
# front-right cell (2,0) and the ground under the hoisted basket stay bare.
BOUNDS = {
    # (-.50: no board joint falls on the door's centre line, art x .93.)
    'SandstonePit': (-.50, .04, 2.39, 2.96),
    'LimestonePit': (-.53, 1.02, 1.56, 3.96),
}
# The saved scenes' original zero-top decks, for the one-time split only.
LEGACY_BOUNDS = {
    'SandstonePit': (.08, .10, 4.30, 4.12),
    'LimestonePit': (.08, .10, 4.76, 4.12),
}
BOARD_BOTTOM = -.14
BOARD_TOP = .020
JOIST_CENTER = -.14
JOIST_THICKNESS = .14


def recipe(model):
    """Only board height changes; joists and native atlas face order are kept."""
    x0,y0,x1,y1 = BOUNDS[model]
    g = Geometry(model+'.Apron')
    count = math.ceil((x1-x0)/.17)
    width = (x1-x0)/count
    for i in range(count):
        g.box((x0+(i+.5)*width,(y0+y1)/2,(BOARD_BOTTOM+BOARD_TOP)/2),
              (width-.009,y1-y0,BOARD_TOP-BOARD_BOTTOM),PLANK)
    for y in (y0+.07,y1-.07):
        g.box(((x0+x1)/2,y,JOIST_CENTER),
              (x1-x0,.12,JOIST_THICKNESS),WOOD)
    return g


def legacy(model):
    """Exact previous zero-top deck, used only for explicit lossless splitting."""
    g = Geometry(model+'.Apron')
    deck(g,*LEGACY_BOUNDS[model],-.07)
    return g
