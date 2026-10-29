"""ElectrolysisPlant: splits water into hydrogen and oxygen (5 workers, 6000 hp).

HERO: twin telescoping gas holders in round steel guide frames - a large
      two-lift hydrogen holder and a smaller single-lift oxygen holder (2:1,
      as the cells make them) - whose riveted bells slowly rise and fall.
ROOF: a long monitor roof (low teal slopes with a glazed clerestory monitor
      along the ridge) on the cell hall, and an open lean-to over the visible
      cell gallery.

Plan (12 x 9 tiles): transformer yard front-left feeding brass bus bars over a
steel gantry; open cell gallery on the hall's left end with a row of cells;
the cell hall behind with the door; a water-intake channel with a pump in
front of the hall; the hydrogen holder front-right and the oxygen holder
behind it, with gas mains and scrubbers between.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, CYAN, GLOW, LAYER_GAP
import lategame_industry_parts as P
from industrial_facades import building_portal

IDENT = 'ElectrolysisPlant'
FOOTPRINT = (12, 9)
HEIGHT = 12
FRAME_END = 121
HERO = ('Twin telescoping gas holders in round steel guide frames: a two-lift hydrogen holder and a '
        'smaller oxygen holder whose riveted bells slowly rise and fall.')

HALL = (2.1, 4.25, 7.9, 8.9)   # plinth (walls + .1) on tiles 2..8 x 4..9; door face .15 behind y=4
DOOR_X = 6.5
EAVE = 4.4
MON_Y = (5.875, 7.275)         # centred on the hall depth
MON_Z = 5.0
H2 = (9.75, 2.45, 1.7)
BARS = (.91, 1.09, 2.91, 3.09)
TRANSFORMERS = ((1.0, 1.0), (3.0, 1.0))   # centres: 2 x 2 tile plinths on tiles 0..4 x 0..2
O2 = (10.05, 6.95, 1.2)


def room(g, x0, y0, x1, y1, bottom, top, *, infill, post=IRON, post_w=.16, windows=None, style='factory',
         scale=.8, bays=None, skip=()):
    windows = windows or {}
    for name, axis, plane, start, end, out in (
            ('front', 'X', y0, x0 - .05, x1 + .05, -1), ('back', 'X', y1, x0 - .05, x1 + .05, 1),
            ('left', 'Y', x0, y0 + .05, y1 - .05, -1), ('right', 'Y', x1, y0 + .05, y1 - .05, 1)):
        if name in skip:
            continue
        K.frame_wall(g, axis, plane, start, end, bottom, top, outward=out, infill=infill, post=post,
                     post_w=post_w, windows=windows.get(name), window_style=style, window_scale=scale,
                     bays=(bays or {}).get(name))


# ---------------------------------------------------------------- cell hall

def hall(g):
    x0, y0, x1, y1 = HALL
    bay_centres = [x0 - .05 + (k + .5) * (x1 - x0 + .1) / 5 for k in range(5)]
    top = P.plinth(g, x0 - .1, y0 - .1, x1 + .1, y1 + .1, 1.25, door=(DOOR_X, 1.0, 1.0))
    building_portal(g, DOOR_X, y0 - .1 - .12, 0)
    g.doorways.append({'id': 'Entrance', 'position': [DOOR_X, y0 - .1, 0], 'outward': [0, -1]})
    for dx in (-.62, .62):
        K.lamp(g, DOOR_X + dx, y0 - .14, 1.1, face='front')
    room(g, x0, y0, x1, y1, top, EAVE + .03, infill=ORANGE, post=IRON, scale=.95,
         windows={'front': [(u, 2.75) for u in bay_centres],
                  'back': [(u, 2.75) for u in bay_centres],
                  # Centred in bays 2-5; bay 1 carries the hydrogen main.
                  'right': [(y0 + .05 + (k + .5) * (y1 - y0 - .1) / 5, 2.75) for k in range(1, 5)]},
         bays={'front': 5, 'back': 5, 'left': 5, 'right': 5})
    # Low main slopes rising to the monitor walls.
    ya, yb = MON_Y
    for u_low, u_high in ((y0, ya), (y1, yb)):
        P.plank_slope(g, 'X', u_low, u_high, EAVE, MON_Z, x0, x1, overhang=.14, end_overhang=.2, plank=.32)
    # End closures under the slopes, set back from the end walls.
    s = (MON_Z - EAVE) / (ya - y0)
    for plane, out in ((x0, -1), (x1, 1)):
        prof = [(y0 - .04, EAVE - .01), (y1 + .04, EAVE - .01), (yb + .05, MON_Z - .02 - .05 * s),
                (ya - .05, MON_Z - .02 - .05 * s)]
        P.end_prism(g, 'X', plane, out, prof, ORANGE)
    # Clerestory monitor with factory glazing.
    room(g, x0, ya, x1, yb, MON_Z - .03, 5.83, infill=FORGED, post=IRON, post_w=.14, scale=.72,
         windows={'front': [(x0 + (k + .5) * (x1 - x0) / 5, 5.4) for k in range(5)],
                  'back': [(x0 + (k + .5) * (x1 - x0) / 5, 5.4) for k in range(5)]},
         bays={'front': 5, 'back': 5, 'left': 1, 'right': 1})
    ridge = P.plank_roof(g, x0, ya, x1, yb, 5.8, 6.35, ridge_axis='X', overhang=.15, plank=.3,
                         gable_mat=PLANK)
    # Hydrogen vent stacks on the monitor ridge.
    for x in (3.0, 6.2):
        g.cylinder((x, (ya + yb) / 2, ridge + .35), .09, .75, IRON, 'Z', 12)
        K.revolve(g, (x, (ya + yb) / 2, ridge + .72), [(.16, 0), (.16, .06), (.05, .2), (0, .22)], IRON,
                  segments=12)
    # Bus-bar wall bushing panel where the DC feed enters (front wall).
    g.box(((BARS[2] + BARS[3]) / 2, y0 - .14, 3.45), (.9, .06, .55), PAINTED)
    for bx in BARS[2:]:
        P.tube(g, (bx, y0 - .17, 3.45), (bx, 3.585, 3.45), .055, CONCRETE, segments=10)
        for k in range(2):
            P.hoop(g, (bx, y0 - .24 - k * .08, 3.45), .085, .03, .03, CONCRETE, axis='Y', segments=10)
    P.gauge(g, 5.0, y0 - .155, 3.5, 'front', .09)
    P.gauge(g, 5.3, y0 - .155, 3.5, 'front', .07)


# ---------------------------------------------------------------- cell gallery

def gallery(g):
    x0, y0, x1, y1 = 0.0, 4.0, HALL[0] - .05, 9.0
    # Tiles 0..2 x 4..9; the right face stops .05 short so its foot clears the hall plinth's.
    top = P.plinth(g, x0, y0, 1.95, y1, .3, pilasters=False)
    for y in (y0 + .2, 5.9, 7.1, y1 - .2):
        P.pier(g, x0 + .2, y, top, top + .25, .26)
        g.box((x0 + .2, y, (top + .3 + 2.72) / 2), (.14, .14, 2.72 - top - .3), IRON)
        g.beam((x0 + .2, y, 2.2), (x0 + .7, y, 2.66), .07, mat=IRON)
    g.box((x0 + .2, (y0 + y1) / 2, 2.67), (.16, y1 - y0 - .2, .12), IRON)
    P.plank_slope(g, 'Y', x0 + .1, x1 + .05, 2.75, 3.45, y0, y1, overhang=.1, plank=.3)
    # Row of four electrolysis cells: painted tanks, brass bus straps, gas
    # offtakes into twin collector mains, cyan level glasses.
    for i, y in enumerate((4.55, 5.5, 6.45, 7.4)):
        cx = 1.15
        g.box((cx, y + .35, top + .06), (.9, .9, .12), CONCRETE)
        g.box((cx, y + .35, top + .55), (.78, .76, .86), PAINTED)
        for dz in (.25, .75):
            g.box((cx, y + .35, top + .12 + dz), (.82, .8, .06), IRON)
        g.box((cx, y + .35, top + 1.02), (.84, .82, .08), IRON)
        for k in range(3):
            g.box((cx - .31 + k * .31, y + .35, top + 1.1), (.12, .6, .07), BRASS)
        g.box((cx - .4, y + .35, top + .62), (.03, .1, .26), CYAN)
        P.pipe(g, [(cx - .18, y + .2, top + 1.06), (cx - .18, y + .2, 2.2)], .045, flanges=False)
        P.pipe(g, [(cx + .18, y + .5, top + 1.06), (cx + .18, y + .5, 2.0)], .035, flanges=False)
    # Collector mains running into the hall gable.
    P.pipe(g, [(.97, y0 + .3, 2.2), (.97, 8.0, 2.2), (.97, 8.3, 2.2), (x1 + .06, 8.3, 2.2)], .08)
    P.pipe(g, [(1.33, y0 + .4, 2.0), (1.33, 7.9, 2.0), (x1 + .06, 7.9, 2.0)], .06, mat=PAINTED)


# ---------------------------------------------------------------- transformers

def transformer(g, parts, x, y, idx, top):
    # Tank with corrugated cooling fins on both sides.
    g.box((x, y, top + .62), (1.0, .8, 1.24), PAINTED)
    g.box((x, y, top + 1.26), (1.08, .88, .06), IRON)
    for side in (-1, 1):
        for k in range(6):
            g.box((x - .4 + k * .16, y + side * .47, top + .62), (.05, .14, 1.0), IRON)
    # Radiator bank and its fan (facing front).
    g.box((x + .72, y, top + .54), (.3, .62, 1.08), IRON)
    for k in range(5):
        g.box((x + .72, y - .25 + k * .125, top + .58), (.34, .03, .94), FORGED)
    fan = Geometry(f'ElectrolysisPlant.TransformerFan{idx}', (x + .72, y - .36, top + .58))
    P.lathe(fan, (x + .72, y - .36, top + .58), [(.05, -.03), (.05, .03)], IRON, axis='Y', segments=10)
    for k in range(4):
        a = k * math.pi / 2 + .3
        fan.beam((x + .72, y - .36, top + .58),
                 (x + .72 + math.cos(a) * .2, y - .36, top + .58 + math.sin(a) * .2), .07, .012, IRON)
    parts.append((fan, 'SPIN_Y', 4))
    P.hoop(g, (x + .72, y - .36, top + .58), .24, .03, .05, PAINTED, axis='Y', segments=12)
    # Conservator drum on brackets.
    zc = top + 1.62
    for dx in (-.32, .32):
        g.box((x + dx, y + .28, top + 1.42), (.06, .06, .3), IRON)
    P.lathe(g, (x, y + .28, zc), [(0, -.5), (.13, -.48), (.16, -.42), (.16, .42), (.13, .48), (0, .5)],
            PAINTED, axis='X', segments=12)
    # Three high-voltage bushings and two low-voltage (bus) bushings.
    for dx in (-.3, 0, .3):
        P.insulator(g, x + dx, y - .2, top + 1.29, height=.55, r=.08, discs=4)
    for dx in (-.09, .09):
        P.insulator(g, x + dx, y + .15, top + 1.29, height=.3, r=.06, discs=2)
    P.gauge(g, x - .25, y - .4, top + .9, 'front', .07)
    return top + 1.29 + .32


def busbar_gantry(g):
    # Two steel portal frames carry the DC bus north to the cells and hall.
    for y in (2.75, 3.55):
        for x in (.55, 4.35):
            P.pier(g, x, y, 0, .3, .3)
            g.box((x, y, (.35 + 3.25) / 2), (.16, .16, 2.9), IRON)
        g.box((2.45, y, 3.33), (4.0, .18, .16), IRON)
        for x, s in ((.55, 1), (4.35, -1)):
            g.beam((x + s * .08, y, 2.8), (x + s * .5, y, 3.24), .08, mat=IRON)
    # Post insulators on the gantry beams carry two DC bars per transformer.
    for bx in BARS:
        for y in (2.75, 3.55):
            P.insulator(g, bx, y, 3.41, height=.32, r=.07, discs=3)
        # Riser from the low-voltage bushing, then the run north.
        ry = TRANSFORMERS[0][1] + .15
        g.box((bx, ry, (2.02 + 3.82) / 2), (.08, .08, 3.82 - 2.02), BRASS)
        end = 3.65 if bx < 2 else 3.6
        # The run ends 1 cm inside the downcomer (no shared end face).
        g.box((bx, (ry - .02 + end + .03) / 2, 3.79), (.06, end + .03 - ry + .02, .1), BRASS)
    for bx in BARS[:2]:
        # Down to the cell gallery and along the cell tops.
        g.box((bx, 3.65, (1.5 + 3.75) / 2), (.08, .08, 3.75 - 1.5), BRASS)
        g.box((bx, (3.63 + 7.95) / 2, 1.512), (.06, 7.95 - 3.63, .06), BRASS)
    for bx in BARS[2:]:
        # Down to the wall bushings of the hall.
        g.box((bx, 3.6, (3.45 + 3.75) / 2), (.08, .08, .3), BRASS)


# ---------------------------------------------------------------- water intake

def intake(g, parts):
    x0, y0, x1, y1 = 5.0, 0.0, 6.0, 4.0   # one tile wide, front edge to the hall
    w = .18
    # Concrete channel: floor slab and two side walls, open to the front edge.
    g.box(((x0 + x1) / 2, (y0 + .02 + y1 - .1) / 2, .1), (x1 - x0 - .2, y1 - y0 - .12, .2), CONCRETE)
    for x in (x0 + w / 2, x1 - w / 2):
        g.box((x, (y0 + y1) / 2, .5), (w, y1 - y0, .8), CONCRETE)
        g.box((x, (y0 + y1) / 2, .93), (w + .08, y1 - y0 + .04, .06), CONCRETE)
    g.box(((x0 + x1) / 2, y1 - .11, .5), (x1 - x0 - 2 * w, .22, .8), CONCRETE)
    g.box(((x0 + x1) / 2, y1 - .11, .935), (x1 - x0 - 2 * w + .12, .3, .08), CONCRETE)
    g.liquid_surfaces.append(dict(name='IntakeChannel', shape='Rectangle',
                                  center=[(x0 + x1) / 2, (y0 + y1 - .22) / 2], bottom=.2, top=.72,
                                  scale=[x1 - x0 - 2 * w, y1 - y0 - .22], flowOnly=False))
    # Trash screen across the mouth.
    for k in range(5):
        x = x0 + w + .08 + k * (x1 - x0 - 2 * w - .16) / 4
        g.box((x, y0 + .35, .62), (.03, .05, .84), IRON)
    g.box(((x0 + x1) / 2, y0 + .35, 1.06), (x1 - x0 - 2 * w + .02, .08, .08), IRON)
    # Pump on a steel bridge over the channel, with a flywheel.
    yb = 2.6
    g.box(((x0 + x1) / 2, yb, 1.0), (x1 - x0 + .1, .7, .1), IRON)
    P.grating(g, x0 + .05, yb - .33, x1 - .05, yb + .33, 1, along='Y')
    g.box(((x0 + x1) / 2, yb, 1.25), (.5, .4, .5), PAINTED)
    P.motor(g, ((x0 + x1) / 2 + .48, yb, 1.28), .17, .45, axis='X')
    P.pipe(g, [((x0 + x1) / 2, yb, .9), ((x0 + x1) / 2, yb, .35)], .09, flanges=False)
    P.pipe(g, [((x0 + x1) / 2, yb + .15, 1.5), ((x0 + x1) / 2, yb + .15, 2.1),
               ((x0 + x1) / 2, HALL[1] - .15, 2.1)], .08)
    P.valve(g, ((x0 + x1) / 2, 3.2, 2.1), 'up', .12)
    fw = P.flywheel('ElectrolysisPlant.PumpFlywheel', ((x0 + x1) / 2 - .4, yb, 1.4), .36, axis='X', spokes=6)
    parts.append((fw, 'SPIN_X', 2))
    g.box(((x0 + x1) / 2 - .32, yb, 1.4), (.14, .1, .1), IRON)


# ---------------------------------------------------------------- gas holders

def guide_frame(g, cx, cy, r, top, columns=8, levels=3, phase=0.0):
    pts = [(cx + math.cos(phase + k * 2 * math.pi / columns) * r, cy + math.sin(phase + k * 2 * math.pi / columns) * r)
           for k in range(columns)]
    for x, y in pts:
        P.pier(g, x, y, 0, .3, .3)
        g.box((x, y, (.35 + top) / 2), (.16, .16, top - .35), IRON)
        g.box((x, y, top + .05), (.22, .22, .1), PAINTED)
    for lv in range(1, levels + 1):
        z = .35 + (top - .35) * lv / levels - (.1 if lv == levels else 0)
        for k, ((ax, ay), (bx, by)) in enumerate(zip(pts, pts[1:] + pts[:1])):
            d = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / d, (by - ay) / d
            g.beam((ax + ux * .1, ay + uy * .1, z), (bx - ux * .1, by - uy * .1, z), .12, .16, mat=IRON)
    for lv in range(levels):
        za = .35 + (top - .35) * lv / levels + .2
        zb = .35 + (top - .35) * (lv + 1) / levels - .2
        for k, ((ax, ay), (bx, by)) in enumerate(zip(pts, pts[1:] + pts[:1])):
            if (k + lv) % 2:
                continue
            mx, my = (ax + bx) / 2, (ay + by) / 2
            nx, ny = mx - cx, my - cy
            n = math.hypot(nx, ny)
            ox, oy = nx / n * .06, ny / n * .06
            d = math.hypot(bx - ax, by - ay)
            ux, uy = (bx - ax) / d, (by - ay) / d
            g.beam((ax + ux * .1 + ox, ay + uy * .1 + oy, za), (bx - ux * .1 + ox, by - uy * .1 + oy, zb), .06, mat=IRON)
            g.beam((bx - ux * .1 + ox * 1.6, by - uy * .1 + oy * 1.6, za), (ax + ux * .1 + ox * 1.6, ay + uy * .1 + oy * 1.6, zb),
                   .06, mat=IRON)
    return pts


def holder_tank(g, cx, cy, R, height):
    """Concrete water tank with coping and pilasters; open top."""
    K.hollow_revolve(g, (cx, cy, 0), [(R + .22, 0), (R + .22, height)], .22, CONCRETE, segments=16)
    K.hollow_revolve(g, (cx, cy, 0), [(R + .27, height - .1), (R + .27, height + .02)], .3, CONCRETE, segments=16)
    for k in range(8):
        a = k * 2 * math.pi / 8
        x, y = cx + math.cos(a) * (R + .235), cy + math.sin(a) * (R + .235)
        P.tube(g, (x, y, .15), (x, y, height - .12), .05, CONCRETE, segments=6)


def bell(name, cx, cy, r, z0, h, *, crown=.32, mat=IRON, rollers=8, guide_r=None, phase=0.0):
    """Riveted telescoping bell (closed crown) as an animated part."""
    b = Geometry(name, (cx, cy, z0))
    K.hollow_revolve(b, (cx, cy, 0), [(r, z0), (r, z0 + h)], .05, mat, segments=16)
    K.dome(b, (cx, cy, z0 + h), r + .02, mat, segments=16, rings=3, squash=crown / r)
    for k in range(3):
        K.band(b, (cx, cy, 0), r, z0 + .2 + (h - .4) * k / 2, .07, PAINTED, segments=16)
    # Crown inspection rail, vent and grip ring.
    rr = r * .86
    zr = z0 + h + crown * math.sqrt(max(0, 1 - (rr / (r + .02)) ** 2)) - .02
    P.ring_rail(b, (cx, cy), rr, zr, height=.5, posts=12)
    b.cylinder((cx, cy, z0 + h + crown + .08), .14, .2, IRON, 'Z', 12)
    P.hoop(b, (cx, cy, z0 + h + crown + .2), .2, .06, .05, BRASS)
    if guide_r:
        for k in range(rollers):
            a = phase + k * 2 * math.pi / rollers
            ux, uy = math.cos(a), math.sin(a)
            # Roller carriage reaching out to the guide column.
            P.tube(b, (cx + ux * (r - .02), cy + uy * (r - .02), z0 + h - .15),
                   (cx + ux * (guide_r - .14), cy + uy * (guide_r - .14), z0 + h - .15), .045, IRON, segments=8)
            b.box((cx + ux * (guide_r - .14), cy + uy * (guide_r - .14), z0 + h - .15), (.1, .1, .16), PAINTED)
    return b


def lift(name, cx, cy, r, z0, h, *, guide_r=None, rollers=8, phase=0.0):
    """Intermediate open lift with a cup ring, as an animated part."""
    b = Geometry(name, (cx, cy, z0))
    K.hollow_revolve(b, (cx, cy, 0), [(r, z0), (r, z0 + h)], .05, IRON, segments=16)
    K.hollow_revolve(b, (cx, cy, 0), [(r + .06, z0 + h - .14), (r + .06, z0 + h + .02)], .13, PAINTED, segments=16)
    K.band(b, (cx, cy, 0), r, z0 + h * .5, .07, PAINTED, segments=16)
    if guide_r:
        for k in range(rollers):
            a = phase + k * 2 * math.pi / rollers
            ux, uy = math.cos(a), math.sin(a)
            P.tube(b, (cx + ux * (r + .04), cy + uy * (r + .04), z0 + h - .06),
                   (cx + ux * (guide_r - .14), cy + uy * (guide_r - .14), z0 + h - .06), .04, IRON, segments=8)
            b.box((cx + ux * (guide_r - .14), cy + uy * (guide_r - .14), z0 + h - .06), (.1, .1, .14), PAINTED)
    return b


def holders(g, parts):
    # Hydrogen: two lifts.
    cx, cy, R = H2
    tank_h = 2.4
    holder_tank(g, cx, cy, R, tank_h)
    gr = R + .5
    pts = guide_frame(g, cx, cy, gr, 10.2, columns=8, levels=4, phase=math.pi / 8)
    parts.append((lift('ElectrolysisPlant.HydrogenLift', cx, cy, R - .1, .8, 3.6, guide_r=gr, phase=math.pi / 8),
                  'SLIDE_Z', 1.2))
    parts.append((bell('ElectrolysisPlant.HydrogenBell', cx, cy, R - .3, 3.2, 3.0, guide_r=gr, phase=math.pi / 8),
                  'SLIDE_Z', 2.4))
    # Caged ladder up the left guide column to the beacon.
    lx, ly = pts[4]
    K.ladder(g, lx - .08, ly, 0, 10.2, face='left', cage=True)
    # Beacon on a mast on the top girt.
    mx, my = pts[3]
    g.box((mx, my, 10.55), (.07, .07, .5), IRON)
    pivot = K.beacon(g, mx, my, 10.8)
    parts.append((K.beacon_shutter(*pivot, 'ElectrolysisPlant.Beacon'), 'SPIN_Z', 2))
    # Oxygen: single lift.
    ox, oy, r2 = O2
    holder_tank(g, ox, oy, r2, 2.0)
    gr2 = r2 + .42
    guide_frame(g, ox, oy, gr2, 6.9, columns=6, levels=3)
    parts.append((bell('ElectrolysisPlant.OxygenBell', ox, oy, r2 - .12, .3, 3.8, guide_r=gr2, rollers=6),
                  'SLIDE_Z', 1.6))
    # Inlet mains: from the hall to each tank, dropping to enter low down.
    P.pipe(g, [(HALL[2] + .06, 5.0, 3.2), (8.05, 5.0, 3.2), (8.05, 5.0, .55), (8.05, 3.75, .55)], .1)
    P.pipe(g, [(HALL[2] + .06, 6.95, 2.6), (8.3, 6.95, 2.6), (8.3, 6.95, .55), (ox - r2 - .1, 6.95, .55)], .08,
           mat=PAINTED)
    for x, y in ((8.05, 5.0), (8.3, 6.95)):
        P.valve(g, (x, y, 1.4), 'right', .13)
    # Scrubber drums between the hall and the oxygen holder.
    for y in (5.75, 8.15):
        K.tank(g, 8.45, y, 0, .34, 2.1, mat=PAINTED, bands=2, roof='dome', segments=16)
        P.gauge(g, 8.45 - .36, y, 1.5, 'left', .07)


def build(g, parts):
    hall(g)
    gallery(g)
    # One shared yard plinth under both transformers (tiles 0..4 x 0..2).
    top = P.plinth(g, 0.0, 0.0, 4.0, 2.0, .35, pilasters=False)
    for i, (x, y) in enumerate(TRANSFORMERS):
        transformer(g, parts, x, y, i + 1, top)
    busbar_gantry(g)
    intake(g, parts)
    holders(g, parts)
