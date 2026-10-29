"""Greenhouse: Victorian iron-and-timber glasshouse (1 worker, 35 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the entrance porch (the door is in the pavilion podium face), the
front planting beds with their native plants, shrubs and the path lamp.

HERO: a square glazed palm pavilion crowned by a two-tier faceted octagonal
glass dome, a glazed lantern and a weathervane.
ROOF: steep glazed ridge roofs on the two wings; faceted glass dome on the
pavilion. All glazing is native factory/grand window assemblies seated on an
opaque steel host plane (sloped facets use the same native assemblies,
re-oriented onto the facet plane).

Parts: concrete dwarf walls; painted-steel framed glazed pavilion and wings;
octagonal dome with steel hip ribs, corner pinnacles and lantern; gable-end
circulating fans; hinged ridge vents; entrance porch with the native door;
rear boiler house with stack and heating mains; concrete planting beds with
native sunflowers, blueberry, coffee and dandelions; REDIC cypresses.

Animated: two gable circulating fans (SPIN_X), four ridge vent flap rows
(SWAY_X), weathervane (SPIN_Z), boiler circulating-pump flywheel (SPIN_X).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N

IDENT = 'Greenhouse'
# Footprint ends at the walls: the porch and the planting beds, shrubs and
# path lamp in front were removed; the door is in the pavilion podium face
# (y = 2). GRID_ORIGIN is the footprint's (0, 0) corner in the artwork
# coordinates used below.
FOOTPRINT = (9, 5)
GRID_ORIGIN = (0, 2)
HEIGHT = 9
HERO = 'Square glazed palm pavilion crowned by a two-tier faceted octagonal glass dome, glazed lantern and weathervane.'
FRAME_END = 121

# Podiums stand .05 proud of the walls, so every podium edge is a tile edge.
PCX, PCY = 4.5, 3.5                     # pavilion centre
PX0, PY0, PX1, PY1 = 3.05, 2.05, 5.95, 4.95
WY0, WY1 = 2.15, 3.95                   # wing walls, set back behind the pavilion front
WPY0, WPY1 = 2.06, 4.0                  # wing podium (front .06 behind the pavilion podium's)
WALL_TOP, OVER = 2.4, .06
RIDGE = WALL_TOP + (WY1 - WY0) / 2 + OVER
S45 = math.sqrt(.5)


def pavilion(g):
    P.podium(g, PX0 - .05, PY0 - .05, PX1 + .05, PY1 + .05, .6, joints=False)
    xs = [PX0 + (PX1 - PX0) * (i + .5) / 3 for i in range(3)]
    P.framed_block(g, PX0, PY0, PX1, PY1, .6, 3.4, infill=IRON, frame=PAINTED, pitch=.93, floors=(2.0,),
                   faces=('front', 'back'),
                   windows={'front': [(PX0 + .43, 1.3, 1.0, 'grand'), (PX1 - .43, 1.3, 1.0, 'grand')] +
                                     [(x, 2.7, 1.0, 'grand') for x in xs],
                            # Upper row only: the boiler house stands against the back below 2.5.
                            'back': [(x, 2.92, .9, 'grand') for x in xs]})
    # Side faces above the wing roofs: posts only.
    for x, s in ((PX0, -1), (PX1, 1)):
        for y in (PY0 + .2, PY1 - .2):
            blk(g, min(x, x + s * .055), y - .055, .6, max(x, x + s * .055), y + .055, 3.38, PAINTED)
    # Native door in the pavilion podium face, on the footprint edge.
    P.door(g, 4.5, PY0 - .05, 0, 'Door0')
    K.lamp(g, 3.62, PY0 - .05, .92, face='front')
    # Deck, cornice and the faceted dome.
    blk(g, PX0 - .08, PY0 - .08, 3.38, PX1 + .08, PY1 + .08, 3.48, IRON)
    blk(g, PX0 - .12, PY0 - .12, 3.48, PX1 + .12, PY1 + .12, 3.53, PAINTED)
    k = 1 / math.cos(math.pi / 8)
    levels = [(1.3, 3.53), (.92, 4.5), (.58, 5.2)]
    K.revolve(g, (PCX, PCY, 3.53), [(a * k, z - 3.53) for a, z in levels], IRON, segments=8, phase=math.pi / 8)
    for i in range(8):
        a = math.radians(22.5 + 45 * i)
        pts = [(PCX + math.cos(a) * (r * k + .01), PCY + math.sin(a) * (r * k + .01), z) for r, z in levels]
        for p, q in zip(pts, pts[1:]):
            g.beam(p, q, .08, .06, PAINTED)
    for i in range(8):
        ang = 45 * i
        P.facet_window(g, PCX, PCY, ang, 1.3, 3.53, .92, 4.5, .5, .9, 'factory')
        P.facet_window(g, PCX, PCY, ang, .92, 4.5, .58, 5.2, .5, .6, 'factory')
    # Tier band between the two glazed tiers.
    K.revolve(g, (PCX, PCY, 4.46), [(.94 * k + .03, 0), (.92 * k + .03, .08)], PAINTED, segments=8, phase=math.pi / 8)
    # Lantern, cap, finial.
    P.octagon_frustum(g, PCX, PCY, 5.2, 5.75, .42, .42, IRON)
    for i in range(8):
        P.facet_window(g, PCX, PCY, 45 * i, .42, 5.2, .42, 5.75, .5, .4, 'factory')
    K.revolve(g, (PCX, PCY, 5.75), [(.52 * k, 0), (.52 * k, .06), (.22, .34), (0, .5)], ROOF, segments=8, phase=math.pi / 8)
    K.revolve(g, (PCX, PCY, 6.2), [(.05, 0), (.05, .12), (.09, .17), (.09, .25), (0, .3), (.025, .31), (.025, .55)], BRASS, segments=8)
    vane = Geometry('Weathervane', (PCX, PCY, 6.85))
    vane.cylinder((PCX, PCY, 6.82), .04, .08, BRASS, 'Z', 8)
    vane.beam((PCX - .32, PCY, 6.85), (PCX + .3, PCY, 6.85), .03, mat=IRON)
    vane.add([(PCX - .32, PCY, 6.8), (PCX - .14, PCY, 6.8), (PCX - .14, PCY, 7.0), (PCX - .32, PCY, 6.94)], [(0, 1, 2, 3)], IRON)
    vane.add([(PCX - .32, PCY, 6.8), (PCX - .14, PCY, 6.8), (PCX - .14, PCY, 7.0), (PCX - .32, PCY, 6.94)], [(3, 2, 1, 0)], IRON)
    vane.add([(PCX + .3, PCY - .06, 6.85), (PCX + .42, PCY, 6.85), (PCX + .3, PCY + .06, 6.85)], [(0, 1, 2)], BRASS)
    vane.add([(PCX + .3, PCY - .06, 6.85), (PCX + .42, PCY, 6.85), (PCX + .3, PCY + .06, 6.85)], [(2, 1, 0)], BRASS)
    for x, y in ((PX0 + .02, PY0 + .02), (PX1 - .02, PY0 + .02), (PX1 - .02, PY1 - .02), (PX0 + .02, PY1 - .02)):
        blk(g, x - .07, y - .07, 3.53, x + .07, y + .07, 3.95, PAINTED)
        K.revolve(g, (x, y, 3.95), [(.1, 0), (.1, .04), (.06, .1), (0, .26)], BRASS, segments=8)
    return vane


def wing(g, parts, x0, x1, side):
    """Glazed wing; side -1 for the left (outer end at x0), +1 for the right."""
    outer = x0 if side < 0 else x1
    P.podium(g, x0 - .05 if side < 0 else PX1 + .05, WPY0, PX0 - .05 if side < 0 else x1 + .05, WPY1, .55, foot=False)
    faces = ('front', 'back', 'left' if side < 0 else 'right')
    bays = [x0 + (x1 - x0) * (i + .5) / 3 for i in range(3)]
    end = 'left' if side < 0 else 'right'
    P.framed_block(g, x0, WY0, x1, WY1, .55, WALL_TOP, infill=IRON, frame=PAINTED, pitch=(x1 - x0) / 3,
                   faces=faces, floors=(1.46,),
                   windows={'front': [(x, z, .85, 'factory') for x in bays for z in (1.02, 1.9)],
                            'back': [(x, z, .85, 'factory') for x in bays for z in (1.02, 1.9)],
                            end: [(y, z, .85, 'factory') for y in (WY0 + .45, WY1 - .45) for z in (1.02, 1.9)]})
    # Glazed ridge roof: opaque steel prism, native windows on both slopes.
    ra, rb = (x0 - OVER, x1) if side < 0 else (x0, x1 + OVER)
    ya, yb, ym = WY0 - OVER, WY1 + OVER, (WY0 + WY1) / 2
    K.extrude_profile(g, [(ya, WALL_TOP), (yb, WALL_TOP), (ym, RIDGE)], ra, rb, IRON, axis='X')
    slant = (ym - ya) / S45
    for sgn in (-1, 1):
        n = (0, sgn * S45, S45)
        up = (0, -sgn * S45, S45)
        y_eave = ya if sgn < 0 else yb
        def on_slope(d, lift=0.0):
            return (y_eave - sgn * d * S45 + n[1] * lift, WALL_TOP + d * S45 + n[2] * lift)
        for x in [ra + (rb - ra) * (i + .5) / 3 for i in range(3)]:
            for d in (.4, 1.0):
                yy, zz = on_slope(d)
                P.framed_window(g, (x, yy, zz), n, up, .72, 'factory')
        for i in range(4):
            x = ra + .045 + (rb - ra - .09) * i / 3
            p0, p1 = on_slope(.02, .02), on_slope(slant - .02, .02)
            g.beam((x, p0[0], p0[1]), (x, p1[0], p1[1]), .06, .05, PAINTED)
        # Eave gutter.
        blk(g, ra, y_eave + (-.07 if sgn < 0 else 0), WALL_TOP - .1, rb, y_eave + (0 if sgn < 0 else .07), WALL_TOP + .0, IRON)
        # Hinged ridge vent flaps (pre-opened so the sway stays clear of the roof).
        hinge = (0, ym, RIDGE + .03)
        vent = Geometry(f'RidgeVent{"L" if side < 0 else "R"}{"F" if sgn < 0 else "B"}', ((ra + rb) / 2, ym, RIDGE + .03))
        open_angle = .2
        for x in [ra + (rb - ra) * (i + .5) / 3 for i in range(3)]:
            yy, zz = on_slope(slant - .2, .05)
            c = (x, yy, zz)
            ax = (1, 0, 0)
            ay = (0, up[1], up[2])
            az = n
            # Rotate open about the ridge hinge so the lower edge lifts.
            angle = open_angle * (1 if sgn < 0 else -1)
            cr = P.rot_x(c, hinge, angle)
            ayr = P.rot_x(ay, (0, 0, 0), angle)
            azr = P.rot_x(az, (0, 0, 0), angle)
            P.obox(vent, cr, ax, ayr, azr, .36, .15, .015, FORGED)
            for xx in (x - .3, x + .3):
                vent.beam(P.rot_x((xx, *on_slope(slant - .02, .075)), hinge, angle),
                          P.rot_x((xx, *on_slope(slant - .4, .075)), hinge, angle), .03, mat=IRON)
        parts.append((vent, 'SWAY_X', .12))
    # Ridge cap with cresting.
    blk(g, ra - .03, ym - .07, RIDGE - .04, rb + .03, ym + .07, RIDGE + .03, IRON)
    for i in range(7):
        x = ra + .15 + (rb - ra - .3) * i / 6
        K.revolve(g, (x, ym, RIDGE + .03), [(.04, 0), (.04, .1), (0, .2)], BRASS, segments=6)
    # Gable-end circulating fan.
    fx = outer + side * OVER
    fz = WALL_TOP + .5
    g.ring((fx + side * .04, ym, fz), .42, .07, .08, IRON, 'X', 16)
    g.ring((fx + side * .04, ym, fz), .3, .03, .06, BRASS, 'X', 12)
    g.cylinder((fx + side * .06, ym, fz), .07, .12, IRON, 'X', 10)
    fan = K.fan(f'GableFan{"L" if side < 0 else "R"}', fx + side * .13, ym, fz, .36, axis='X', blades=6)
    parts.append((fan, 'SPIN_X', 2 * side))


def boiler_house(g, parts):
    x0, y0, x1, y1 = 3.0, 5.0, 6.0, 7.0   # whole tiles behind the pavilion
    P.podium(g, x0, y0, x1, y1, 1.0, foot=False)
    # Walls inset .12 at the ends so their corner posts clear the pavilion's.
    P.framed_block(g, x0 + .12, y0 + .05, x1 - .12, y1 - .05, 1.0, 2.5, infill=ORANGE, pitch=.95,
                   windows={'back': [(3.75, 1.75, .9, 'grand'), (5.25, 1.75, .9, 'grand')],
                            'left': [(6.0, 1.75, .9, 'grand')], 'right': [(6.0, 1.75, .9, 'grand')]})
    # Front eave kept clear of the pavilion's back wall (y 4.95).
    K.gable_roof(g, x0 + .05, y0 + .15, x1 - .05, y1 - .05, 2.5, 3.2, ridge_axis='X', overhang=.14)
    K.stack(g, 5.0, 6.15, 2.7, 5.5, emits='smoke', r=.2)
    P.native_window(g, x0, 6.0, .55, .7, 'left', 'factory')
    # Heating mains along the back of each wing.
    for s, xa, xw in ((-1, x0, 1.8), (1, x1, 7.2)):
        P.flanged_pipe(g, [(xa, 5.3, .35), (xw, 5.3, .35), (xw, WY1 + .05, .35)], .06)
        P.flanged_pipe(g, [(xa, 5.55, .62), (xw - s * .3, 5.55, .62), (xw - s * .3, WY1 + .05, .62)], .05)
        K.valve_wheel(g, xa + s * .45, 5.17, .35, face='front', r=.1)
        P.gauge(g, xa + s * .02 + (-.005 if s < 0 else .005), 5.95, 1.35, 'left' if s < 0 else 'right')
    # Circulating pump with flywheel beside the boiler house.
    px, py = 6.5, 6.3
    P.pier(g, px, py, 0, .3, .5)
    g.cylinder((px, py, .62), .16, .5, PAINTED, 'Z', 12)
    g.ring((px, py, .88), .19, .05, .05, BRASS, 'Z', 12)
    g.cylinder((px, py + .22, .62), .05, .22, IRON, 'Y', 8)
    wheel = Geometry('PumpFlywheel', (px + .32, py, .62))
    K.wheel(wheel, (px + .32, py, .62), .26, 'X')
    parts.append((wheel, 'SPIN_X', 1))
    g.cylinder((px + .2, py, .62), .04, .25, IRON, 'X', 8)
    P.flanged_pipe(g, [(px, py, .87), (px, py, 1.2), (x1 + .02, py, 1.2)], .05)
    # Coal bunker, one tile, behind the heating mains.
    blk(g, 2.0, 6.0, 0, 3.0, 7.0, .7, CONCRETE)
    blk(g, 2.04, 6.04, .7, 2.96, 6.96, .76, IRON)
    P.hopper(g, 2.5, 6.5, .76, 1.0, .44, .34)


def build(g, parts):
    vane = pavilion(g)
    parts.append((vane, 'SPIN_Z', 1))
    # Wing walls run .1 into the pavilion so their inner corner posts are buried.
    wing(g, parts, .05, PX0 + .1, -1)
    wing(g, parts, PX1 - .1, 8.95, 1)
    boiler_house(g, parts)
