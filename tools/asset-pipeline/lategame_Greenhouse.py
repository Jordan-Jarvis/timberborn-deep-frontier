"""Greenhouse: Victorian iron-and-timber glasshouse (1 worker, 35 hp).

Revised 2026-10-22 (no forced decoration; footprint ends at the walls):
removed the entrance porch (the door is in the pavilion podium face), the
front planting beds with their native plants, shrubs and the path lamp.

Compacted 2026-10-30 (Workshop feedback: the buildings exceed Timberborn's
scale; user: "it is the scaffolding and size", "one layer per floor"):
9x5x9 -> 9x3x5, inside the old footprint with the same origin, width, door
and native entrance. The boiler house moved from behind the pavilion to the
strip behind the right wing, with the coal bunker beside it and the
circulating pump on its roof; the wings drop from 2.4 to 0.95 layers
at the eaves (one glazed storey, no floor band), the pavilion from 3.4 to 2
and the dome tiers are flatter; the stack is 4.2 instead of 8.3 high.

HERO: a square glazed palm pavilion crowned by a two-tier faceted octagonal
glass dome, a glazed lantern and a weathervane.
ROOF: glazed ridge roofs on the two wings and the faceted glass dome on the
pavilion, kept as the glasshouse's defining silhouette; flat concrete roof on
the boiler house. All glazing is native factory/grand window assemblies
seated on an opaque steel host plane (sloped facets use the same native
assemblies, re-oriented onto the facet plane).

Plan (9 x 3 tiles; front y = 0):
  - pavilion x 3..6, y 0..3 on a concrete podium; the native door centred on
    x = 4.5 with its face on the y = 0 tile edge;
  - glazed wings x 0..3 and 6..9, y 0..2;
  - behind the right wing (y 2..3): boiler house with the smoke stack and the
    circulating pump on its roof (x 6..8) and the coal bunker (x 8..9); the
    strip behind the left wing holds only the heating main on the wing wall,
    so its cells stay free.

Animated (unchanged names and kinds): two gable circulating fans (SPIN_X),
four ridge vent flap rows (SWAY_X), weathervane (SPIN_Z), boiler
circulating-pump flywheel (SPIN_X).
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, GLOW, CYAN
import lategame_civic_parts as P
from lategame_civic_parts import blk, animate  # noqa: F401
import native_building_assets as N

IDENT = 'Greenhouse'
FOOTPRINT = (9, 3)
HEIGHT = 5
HERO = 'Square glazed palm pavilion crowned by a two-tier faceted octagonal glass dome, glazed lantern and weathervane.'
FRAME_END = 121

# Podiums stand .05 proud of the walls, so every podium edge is a tile edge.
PCX, PCY = 4.5, 1.5                     # pavilion centre
PX0, PY0, PX1, PY1 = 3.05, .05, 5.95, 2.95
PTOP = 2.0                              # pavilion wall top
WY0, WY1 = .15, 1.95                    # wing walls, set back behind the pavilion front
WPY0, WPY1 = .06, 2.0                   # wing podium (front .06 behind the pavilion podium's)
WALL_TOP, OVER = .95, .06
RIDGE = WALL_TOP + (WY1 - WY0) / 2 + OVER
S45 = math.sqrt(.5)


def pavilion(g):
    P.podium(g, PX0 - .05, PY0 - .05, PX1 + .05, PY1 + .05, .3, joints=False)
    xs = [PX0 + (PX1 - PX0) * (i + .5) / 3 for i in range(3)]
    P.framed_block(g, PX0, PY0, PX1, PY1, .3, PTOP, infill=IRON, frame=PAINTED, pitch=.93, floors=(1.2,),
                   faces=('front', 'back'),
                   windows={'front': [(PX0 + .43, .7, .5, 'grand'), (PX1 - .43, .7, .5, 'grand')] +
                                     [(x, 1.6, .5, 'grand') for x in xs],
                            'back': [(x, z, .5, 'grand') for x in xs for z in (.7, 1.6)]})
    # Side faces above the wing roofs: posts only.
    for x, s in ((PX0, -1), (PX1, 1)):
        for y in (PY0 + .2, PY1 - .2):
            blk(g, min(x, x + s * .055), y - .055, .3, max(x, x + s * .055), y + .055, PTOP - .02, PAINTED)
    # Native door in the pavilion podium face, on the footprint edge.
    P.door(g, 4.5, PY0 - .05, 0, 'Door0')
    K.lamp(g, 3.62, PY0 - .05, .5, face='front')
    # Deck, cornice and the faceted dome.
    z0 = PTOP - .02
    blk(g, PX0 - .08, PY0 - .08, z0, PX1 + .08, PY1 + .08, z0 + .1, IRON)
    blk(g, PX0 - .12, PY0 - .12, z0 + .1, PX1 + .12, PY1 + .12, z0 + .15, PAINTED)
    zb = z0 + .15
    k = 1 / math.cos(math.pi / 8)
    levels = [(1.3, zb), (.92, zb + .67), (.58, zb + 1.17)]
    K.revolve(g, (PCX, PCY, zb), [(a * k, z - zb) for a, z in levels], IRON, segments=8, phase=math.pi / 8)
    for i in range(8):
        a = math.radians(22.5 + 45 * i)
        pts = [(PCX + math.cos(a) * (r * k + .01), PCY + math.sin(a) * (r * k + .01), z) for r, z in levels]
        for p, q in zip(pts, pts[1:]):
            g.beam(p, q, .07, .05, PAINTED)
    for i in range(8):
        ang = 45 * i
        P.facet_window(g, PCX, PCY, ang, 1.3, levels[0][1], .92, levels[1][1], .5, .62, 'factory')
        P.facet_window(g, PCX, PCY, ang, .92, levels[1][1], .58, levels[2][1], .5, .42, 'factory')
    # Tier band between the two glazed tiers.
    zt = levels[1][1]
    K.revolve(g, (PCX, PCY, zt - .04), [(.94 * k + .03, 0), (.92 * k + .03, .07)], PAINTED, segments=8, phase=math.pi / 8)
    # Lantern, cap, finial.
    zl0, zl1 = levels[2][1], levels[2][1] + .4
    P.octagon_frustum(g, PCX, PCY, zl0, zl1, .42, .42, IRON)
    for i in range(8):
        P.facet_window(g, PCX, PCY, 45 * i, .42, zl0, .42, zl1, .5, .3, 'factory')
    K.revolve(g, (PCX, PCY, zl1), [(.52 * k, 0), (.52 * k, .06), (.22, .28), (0, .4)], ROOF, segments=8, phase=math.pi / 8)
    zf = zl1 + .35
    K.revolve(g, (PCX, PCY, zf), [(.05, 0), (.05, .1), (.08, .14), (.08, .2), (0, .25), (.022, .26), (.022, .45)], BRASS,
              segments=8)
    vz = zf + .55
    vane = Geometry('Weathervane', (PCX, PCY, vz))
    vane.cylinder((PCX, PCY, vz - .03), .04, .08, BRASS, 'Z', 8)
    vane.beam((PCX - .3, PCY, vz), (PCX + .28, PCY, vz), .03, mat=IRON)
    vane.add([(PCX - .3, PCY, vz - .05), (PCX - .13, PCY, vz - .05), (PCX - .13, PCY, vz + .13), (PCX - .3, PCY, vz + .08)], [(0, 1, 2, 3)], IRON)
    vane.add([(PCX - .3, PCY, vz - .05), (PCX - .13, PCY, vz - .05), (PCX - .13, PCY, vz + .13), (PCX - .3, PCY, vz + .08)], [(3, 2, 1, 0)], IRON)
    vane.add([(PCX + .28, PCY - .06, vz), (PCX + .4, PCY, vz), (PCX + .28, PCY + .06, vz)], [(0, 1, 2)], BRASS)
    vane.add([(PCX + .28, PCY - .06, vz), (PCX + .4, PCY, vz), (PCX + .28, PCY + .06, vz)], [(2, 1, 0)], BRASS)
    for x, y in ((PX0 + .02, PY0 + .02), (PX1 - .02, PY0 + .02), (PX1 - .02, PY1 - .02), (PX0 + .02, PY1 - .02)):
        blk(g, x - .06, y - .06, zb, x + .06, y + .06, zb + .3, PAINTED)
        K.revolve(g, (x, y, zb + .3), [(.085, 0), (.085, .035), (.05, .085), (0, .22)], BRASS, segments=8)
    return vane


def wing(g, parts, x0, x1, side):
    """Glazed wing; side -1 for the left (outer end at x0), +1 for the right."""
    outer = x0 if side < 0 else x1
    P.podium(g, x0 - .05 if side < 0 else PX1 + .05, WPY0, PX0 - .05 if side < 0 else x1 + .05, WPY1, .25, foot=False)
    faces = ('front', 'back', 'left' if side < 0 else 'right')
    bays = [x0 + (x1 - x0) * (i + .5) / 3 for i in range(3)]
    end = 'left' if side < 0 else 'right'
    P.framed_block(g, x0, WY0, x1, WY1, .25, WALL_TOP, infill=IRON, frame=PAINTED, pitch=(x1 - x0) / 3,
                   faces=faces,
                   windows={'front': [(x, .6, .45, 'factory') for x in bays],
                            'back': [(x, .6, .45, 'factory') for x in bays],
                            end: [(y, .6, .45, 'factory') for y in (WY0 + .45, WY1 - .45)]})
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
    """Boiler house behind the right wing (x 6..8, y 2..3), one layer with a
    flat roof, the smoke stack and a coal bunker beside it."""
    x0, y0, x1, y1 = 6.0, 2.0, 8.0, 3.0
    P.podium(g, x0, y0, x1, y1, .2, joints=False, foot=False)
    # x0 + .13: its corner posts clear the pavilion's back corner post (x 6.035).
    P.framed_block(g, x0 + .13, y0 + .05, x1 - .05, y1 - .05, .2, .84, infill=ORANGE, pitch=.95,
                   windows={'back': [(6.5, .5, .45, 'factory'), (7.5, .5, .45, 'factory')]})
    K.flat_roof(g, x0 + .05, y0 + .05, x1 - .05, y1 - .05, .84, thickness=.16, overhang=.05)
    K.stack(g, 7.45, 2.5, .9, 3.3, emits='smoke', r=.18)
    # Coal bunker, one tile, beside the boiler house.
    blk(g, 8.0, 2.0, 0, 9.0, 3.0, .5, CONCRETE)
    blk(g, 8.04, 2.04, .5, 8.96, 2.96, .56, IRON)
    P.hopper(g, 8.5, 2.5, .56, .82, .42, .32)
    # Heating main from the boiler house along the right wing's back wall.
    P.flanged_pipe(g, [(x0 + .05, 2.3, .4), (6.2, 2.3, .4), (6.2, 2.07, .4)], .05)


def pump(g, parts):
    """Circulating pump with flywheel on the boiler-house roof (its cells
    already sit beside the stack's smoke, so no roof-deck cell is lost; BRIEF
    "no clutter on buildable space": nothing stands on the open strip behind
    the left wing), and the heating main along that wing's back wall, within
    0.15 of the wall so it claims no cell."""
    px, py, base = 6.5, 2.5, 1.0
    P.pier(g, px, py, base - .03, base + .22, .4)
    g.cylinder((px, py, base + .5), .14, .44, PAINTED, 'Z', 12)
    g.ring((px, py, base + .72), .17, .045, .05, BRASS, 'Z', 12)
    wheel = Geometry('PumpFlywheel', (px + .3, py, base + .5))
    K.wheel(wheel, (px + .3, py, base + .5), .24, 'X')
    parts.append((wheel, 'SPIN_X', 1))
    g.cylinder((px + .19, py, base + .5), .04, .22, IRON, 'X', 8)
    P.flanged_pipe(g, [(px, py - .15, base + .5), (px, 2.12, base + .5), (px, 2.12, base - .02)], .045)
    P.flanged_pipe(g, [(.4, 2.06, .55), (2.95, 2.06, .55)], .05)


def build(g, parts):
    vane = pavilion(g)
    parts.append((vane, 'SPIN_Z', 1))
    # Wing walls run .1 into the pavilion so their inner corner posts are buried.
    wing(g, parts, .05, PX0 + .1, -1)
    wing(g, parts, PX1 - .1, 8.95, 1)
    boiler_house(g, parts)
    pump(g, parts)
