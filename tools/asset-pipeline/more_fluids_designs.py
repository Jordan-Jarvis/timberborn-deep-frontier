"""The More Fluids models, authored with more_fluids_geometry.Kit.

Footprints, entrances and water inputs come from docs/more-fluids-design.md
("Objects") and the blueprints under src/MoreFluids/Data. Tile coordinates:
x across, y back (0 = entrance side), z up from the building's base (BaseZ),
so the water-side layer of a pump lies below z = 0.

Each building has a Folktails and an Iron Teeth model from one layout: the
faction changes materials and a few faction details (thatch or plank roofs,
plank or riveted walls, brass or blue-painted metal), as vanilla pumps do.
"""
import math
import random

from more_fluids_geometry import Kit, faction_palette, COMMON_PALETTE, rock_points

FOLK, IRON = 'Folktails', 'IronTeeth'


# ---------------------------------------------------------------- shared parts

def plank_house(k, x0, x1, y0, y1, h, faction, skip=()):
    """Timber-framed hut walls: sill, corner posts, plank infill (Iron Teeth:
    riveted plank-metal lower course)."""
    k.box((x0 - .03, y0 - .03, 0), (x1 + .03, y1 + .03, .08), 'frame', skip=('-z',))
    if faction == IRON:
        k.box((x0, y0, .08), (x1, y1, .42), 'planks2', skip=('-z', '+z') + tuple(skip))
        k.box((x0 + .01, y0 + .01, .42), (x1 - .01, y1 - .01, h), 'planks', skip=('-z', '+z') + tuple(skip))
    else:
        k.box((x0, y0, .08), (x1, y1, h), 'planks2', skip=('-z', '+z') + tuple(skip))
    for x in (x0, x1):
        for y in (y0, y1):
            k.box((x - .07, y - .07, .08), (x + .07, y + .07, h + .04), 'frame', skip=('-z',), top='end')
    # Wall plate under the eaves.
    k.box((x0 - .05, y0 - .05, h - .07), (x1 + .05, y0 + .02, h), 'trim', skip=('-z',))
    k.box((x0 - .05, y1 - .02, h - .07), (x1 + .05, y1 + .05, h), 'trim', skip=('-z',))


def door(k, x, y, width=.42, height=.7, outward=-1):
    """Dark doorway with a timber frame on a wall facing -y (outward=-1)."""
    d = .012 * outward
    k.poly([(x - width / 2, y + d, .08), (x + width / 2, y + d, .08), (x + width / 2, y + d, height),
            (x - width / 2, y + d, height)], 'dark', (0, outward, 0))
    for sx in (x - width / 2 - .05, x + width / 2):
        k.box((sx, y + outward * .05 if outward < 0 else y, .08), (sx + .05, y if outward < 0 else y + .05, height + .02),
              'trim', skip=('-z',))
    k.box((x - width / 2 - .07, y + outward * .06 if outward < 0 else y, height),
          (x + width / 2 + .07, y if outward < 0 else y + .06, height + .08), 'trim')


def gable_ends(k, x0, x1, y0, y1, z_eave, z_ridge, key):
    """Triangular gable infill at both x ends (ridge along x)."""
    ym = (y0 + y1) / 2
    k.poly([(x0, y0, z_eave), (x0, y1, z_eave), (x0, ym, z_ridge)], key, (-1, 0, 0))
    k.poly([(x1, y0, z_eave), (x1, y1, z_eave), (x1, ym, z_ridge)], key, (1, 0, 0))


def gable_ends_y(k, x0, x1, y0, y1, z_eave, z_ridge, key):
    """Triangular gable infill at both y ends (ridge along y)."""
    xm = (x0 + x1) / 2
    k.poly([(x0, y0, z_eave), (x1, y0, z_eave), (xm, y0, z_ridge)], key, (0, -1, 0))
    k.poly([(x0, y1, z_eave), (x1, y1, z_eave), (xm, y1, z_ridge)], key, (0, 1, 0))


def roof_y(k, x0, x1, y0, y1, z_eave, z_ridge, faction, courses=2, thickness=.06):
    """Gable roof with the ridge along y: author the x-ridge roof in a
    rotated frame by swapping coordinates face by face."""
    xm = (x0 + x1) / 2
    for side, (xa, xb) in (('left', (x0, xm)), ('right', (x1, xm))):
        for c in range(courses):
            t0, t1 = c / courses, (c + 1) / courses
            xl, xh = xa + (xb - xa) * t0, xa + (xb - xa) * t1
            zl, zh = z_eave + (z_ridge - z_eave) * t0, z_eave + (z_ridge - z_eave) * t1
            if side == 'left':
                quad = [(xl, y1, zl), (xl, y0, zl), (xh, y0, zh), (xh, y1, zh)]
            else:
                quad = [(xl, y0, zl), (xl, y1, zl), (xh, y1, zh), (xh, y0, zh)]
            k.roof_course(quad, 'roof', c)
        if side == 'left':
            under = [(xa, y0, z_eave - thickness), (xb, y0, z_ridge - thickness), (xb, y1, z_ridge - thickness), (xa, y1, z_eave - thickness)]
            edge = [(xa, y1, z_eave - thickness), (xa, y0, z_eave - thickness), (xa, y0, z_eave), (xa, y1, z_eave)]
        else:
            under = [(xa, y1, z_eave - thickness), (xb, y1, z_ridge - thickness), (xb, y0, z_ridge - thickness), (xa, y0, z_eave - thickness)]
            edge = [(xa, y0, z_eave - thickness), (xa, y1, z_eave - thickness), (xa, y1, z_eave), (xa, y0, z_eave)]
        k.face(under, 'board')
        k.face(edge, 'trim')
    k.box((xm - .05, y0 - .02, z_ridge - .03), (xm + .05, y1 + .02, z_ridge + .05), 'metal' if faction == IRON else 'frame')


def roof_x(k, x0, x1, y0, y1, z_eave, z_ridge, faction, courses=2):
    k.roof_gable(x0, x1, y0, y1, z_eave, z_ridge, 'roof', gable_key='board', courses=courses)
    ym = (y0 + y1) / 2
    k.box((x0 - .02, ym - .05, z_ridge - .03), (x1 + .02, ym + .05, z_ridge + .05), 'metal' if faction == IRON else 'frame')


def hoop(k, center, radius, z, key, height=.05, sides=12):
    k.cylinder((center[0], center[1], 0), radius, z, z + height, key, sides=sides, caps=(False, False))
    # Ledges so the band reads as a strap standing proud of the staves.
    k.revolve(center, [(radius - .02, z), (radius, z)], key, sides=sides)
    k.revolve(center, [(radius, z + height), (radius - .02, z + height)], key, sides=sides)


def flywheel(k, name, center, radius, faction, axis='x', thickness=.06, spokes=4):
    """Spoked wheel animated about its axle (axis 'x' or 'y')."""
    cx, cy, cz = center
    k.begin(name, center, ('rotate', axis, 1))
    rim_key = 'trim' if faction == FOLK else 'metal'
    if axis == 'x':
        k.cylinder((cx, cy, cz), radius, cx - thickness / 2, cx + thickness / 2, rim_key, sides=12, axis='x', caps=(True, True))
        k.cylinder((cx, cy, cz), radius * .2, cx - thickness, cx + thickness, 'metal', sides=8, axis='x')
        for s in range(spokes):
            a = math.pi * s / spokes
            dy, dz = math.cos(a) * radius * .95, math.sin(a) * radius * .95
            k.beam((cx, cy - dy, cz - dz), (cx, cy + dy, cz + dz), .04, .04, 'frame', caps=False)
    else:
        k.cylinder((cx, cy, cz), radius, cy - thickness / 2, cy + thickness / 2, rim_key, sides=12, axis='y', caps=(True, True))
        k.cylinder((cx, cy, cz), radius * .2, cy - thickness, cy + thickness, 'metal', sides=8, axis='y')
        for s in range(spokes):
            a = math.pi * s / spokes
            dx, dz = math.cos(a) * radius * .95, math.sin(a) * radius * .95
            k.beam((cx - dx, cy, cz - dz), (cx + dx, cy, cz + dz), .04, .04, 'frame', caps=False)
    k.end()


def pipe_run(k, points, radius, key, sides=8):
    """Straight pipe segments with cube joints at the bends."""
    for a, b in zip(points, points[1:]):
        axis = max(range(3), key=lambda i: abs(b[i] - a[i]))
        name = 'xyz'[axis]
        lo, hi = sorted((a[axis], b[axis]))
        c = list(a)
        if name == 'z':
            k.cylinder((c[0], c[1], 0), radius, lo, hi, key, sides=sides, caps=(False, False))
        elif name == 'x':
            k.cylinder((0, c[1], c[2]), radius, lo, hi, key, sides=sides, axis='x', caps=(False, False))
        else:
            k.cylinder((c[0], 0, c[2]), radius, lo, hi, key, sides=sides, axis='y', caps=(False, False))
    for p in points:
        r = radius * 1.35
        k.box((p[0] - r, p[1] - r, p[2] - r), (p[0] + r, p[1] + r, p[2] + r), 'metal')


def intake_pipe(k, x, y, faction, top=.1):
    """The pipe stub below the overhang: the native pipe segments
    (WaterInputPipeSpec) continue it downwards from z = -1."""
    key = 'planks2' if faction == FOLK else 'metal'
    k.cylinder((x, y, 0), .15, -.27, top, key, sides=10, caps=(True, False), cap_key='hole')
    hoop(k, (x, y), .16, -.2, 'metal' if faction == FOLK else 'paint', .04, sides=10)


# ---------------------------------------------------------------- Fluid Extractor

def fluid_extractor(faction):
    """2 x 3 x 3, BaseZ 1 (vanilla Deep Water Pump layout): pump house on the
    2 x 2 bank, intake over water at (0, 2), separator vessel with a glass
    sight gauge at (1, 1). Animated: the flywheel on the left wall and the
    pump rod over the intake."""
    k = Kit(f'MoreFluidsFluidExtractor.{faction}', faction_palette(faction), seed=11)
    # Pump house on the front of the bank.
    x0, x1, y0, y1, h = .14, 1.86, .14, 1.26, .92
    plank_house(k, x0, x1, y0, y1, h, faction)
    door(k, 1.5, y0, .4, .68)
    k.cylinder((.62, y0, .56), .13, y0 + .01, y0 - .03, 'metal', sides=8, axis='y', caps=(False, True), cap_keys=('port', 'port'))
    gable_ends(k, x0, x1, y0, y1, h, 1.52, 'board')
    if faction == FOLK:
        roof_x(k, .04, 1.96, y0 - .12, y1 + .1, h - .02, 1.6, faction)
    else:
        roof_x(k, .04, 1.96, y0 - .12, y1 + .1, h - .02, 1.56, faction)
    # Flywheel on the left wall, driven from inside (animated).
    k.cylinder((.07, .7, .56), .03, .0, .14, 'metal', sides=6, axis='x')
    flywheel(k, '#FlywheelAnimated', (.075, .7, .56), .27, faction, axis='x', thickness=.05)

    # Separator vessel at the back right: staved (Folktails) or riveted (Iron Teeth) drum.
    vx, vy, vr = 1.42, 1.62, .3
    k.box((1.06, 1.3, 0), (1.86, 1.94, .1), 'frame', skip=('-z',))
    body = 'planks' if faction == FOLK else 'rib'
    k.cylinder((vx, vy, 0), vr, .1, 1.18, body, sides=12, caps=(False, False))
    band = 'metal' if faction == FOLK else 'paint'
    for z in (.22, .62, 1.02):
        hoop(k, (vx, vy), vr + .015, z, band, .06)
    k.revolve((vx, vy), [(vr + .02, 1.18), (vr - .03, 1.3), (.14, 1.4), (.0, 1.43)], 'metal', sides=12)
    k.cylinder((vx, vy, 0), .05, 1.4, 1.55, 'metal', sides=6, caps=(False, True))
    # Glass sight gauge on the vessel's left face, brass/steel fittings.
    gx = vx - vr - .05
    k.box((gx - .03, vy - .07, .24), (gx + .06, vy + .07, .32), 'metal')
    k.box((gx - .03, vy - .07, .96), (gx + .06, vy + .07, 1.04), 'metal')
    k.cylinder((gx, vy, 0), .04, .32, .96, 'glass', sides=6, caps=(False, False), smooth=False)
    k.box((gx + .03, vy - .03, .32), (gx + .06, vy + .03, .96), 'metal')
    # Transfer pipe: intake housing -> vessel, through (0, 1) and (1, 1) only.
    pipe_run(k, [(.5, 2.12, .36), (.5, 1.82, .36), (1.21, 1.82, .36)], .055, 'metal' if faction == FOLK else 'paint')
    # Outlet from the vessel into the house.
    k.cylinder((vx, 0, .7), .05, y1 - .02, vy - vr + .04, 'metal', sides=8, axis='y', caps=(False, False))
    k.cylinder((vx, 0, .7), .075, y1 + .015, y1 + .05, 'metal', sides=8, axis='y', caps=(False, True))

    # Intake over the water at (0, 2): stringers from the bank, housing, pipe.
    for x in (.12, .88):
        k.box((x - .05, 1.55, 0), (x + .05, 2.94, .1), 'frame', skip=('-z',), top='frame')
    k.box((.14, 2.12, .1), (.86, 2.9, .48), 'planks2' if faction == FOLK else 'planks', skip=('-z', '+z'))
    k.cone_roof((.5, 2.51), .52, .47, .7, 'roof', sides=4, courses=1, rim='board')
    for x in (.14, .86):
        for y in (2.12, 2.9):
            k.box((x - .05, y - .05, -.05), (x + .05, y + .05, .52), 'frame', skip=('-z',), top='end')
    intake_pipe(k, .5, 2.51, faction, top=.1)
    # Guide frame and the animated pump rod.
    for x in (.24, .76):
        k.box((x - .04, 2.47, .55), (x + .04, 2.55, .94), 'frame', top='end')
    k.box((.17, 2.45, .88), (.83, 2.57, .95), 'trim')
    k.begin('#PumpRodAnimated', (.5, 2.51, .6), ('bob', 'z', .08))
    k.cylinder((.5, 2.51, 0), .035, .48, .82, 'metal', sides=6, caps=(False, True))
    k.box((.32, 2.47, .7), (.68, 2.55, .76), 'metal')
    k.end()
    k.empty('#Slot#Entrance', (1.42, .36, .04), 180)
    return k


def fluid_extractor_stage(faction):
    k = Kit(f'MoreFluidsFluidExtractor.{faction}.ConstructionStage0', faction_palette(faction), seed=12)
    dirt_patch(k, [(0, 0, 2, 2)])
    stage_frame(k, 0, 2, 0, 2, 1.0, metal=True)
    for x in (.3, .7):
        k.box((x - .05, 1.7, 0), (x + .05, 2.94, .085), 'frame', skip=('-z',))
    intake_pipe(k, .5, 2.51, faction, top=0)
    return k


# ---------------------------------------------------------------- construction stages

def dirt_patch(k, rects, outside=.022, rim=.11):
    """Native DirtURP patch over grounded rectangles: v 0 at `outside`
    beyond the edge, 1 from `rim` inside it (vanilla construction bases)."""
    z = .001
    for x0, y0, x1, y1 in rects:
        ox0, oy0, ox1, oy1 = x0 - outside, y0 - outside, x1 + outside, y1 + outside
        ix0, iy0, ix1, iy1 = x0 + rim, y0 + rim, x1 - rim, y1 - rim
        k.face([(ix0, iy0, z), (ix1, iy0, z), (ix1, iy1, z), (ix0, iy1, z)], 'dirt',
               uvs=[(ix0 / 4, 1), (ix1 / 4, 1), (ix1 / 4, 1), (ix0 / 4, 1)])
        ring_o = [(ox0, oy0), (ox1, oy0), (ox1, oy1), (ox0, oy1)]
        ring_i = [(ix0, iy0), (ix1, iy0), (ix1, iy1), (ix0, iy1)]
        for i in range(4):
            j = (i + 1) % 4
            pts = [(*ring_o[i], z), (*ring_o[j], z), (*ring_i[j], z), (*ring_i[i], z)]
            k.face(pts, 'dirt', uvs=[(ring_o[i][0] / 4, 0), (ring_o[j][0] / 4, 0), (ring_i[j][0] / 4, 1), (ring_i[i][0] / 4, 1)])


def stage_frame(k, x0, x1, y0, y1, height, metal):
    """Vanilla-look stage: sills round the outline, corner posts, top girts
    and one brace per long side (metal girders when the cost holds metal)."""
    post = 'metal' if metal else 'frame'
    i = .08
    k.box((x0 + .02, y0 + .02, .001), (x1 - .02, y0 + .14, .1), 'frame', skip=('-z',))
    k.box((x0 + .02, y1 - .14, .001), (x1 - .02, y1 - .02, .1), 'frame', skip=('-z',))
    k.box((x0 + .02, y0 + .14, .001), (x0 + .14, y1 - .14, .1), 'frame', skip=('-z',))
    k.box((x1 - .14, y0 + .14, .001), (x1 - .02, y1 - .14, .1), 'frame', skip=('-z',))
    for x in (x0 + i, x1 - i):
        for y in (y0 + i, y1 - i):
            k.box((x - .06, y - .06, .1), (x + .06, y + .06, height), post, skip=('-z',))
    k.box((x0 + .03, y0 + .04, height - .1), (x1 - .03, y0 + .12, height - .02), post)
    k.box((x0 + .03, y1 - .12, height - .1), (x1 - .03, y1 - .04, height - .02), post)
    k.box((x0 + .04, y0 + .12, height - .2), (x0 + .12, y1 - .12, height - .12), post)
    k.box((x1 - .12, y0 + .12, height - .2), (x1 - .04, y1 - .12, height - .12), post)
    k.beam((x0 + .2, y0 + .08, .12), (x1 - .2, y0 + .08, height - .12), .05, .05, post)


# ---------------------------------------------------------------- registry

MODELS = {}


def _register(ident, builder, resource, allowed, height, ceiling, faction=None, stage_of=None):
    """ident is the scene id: <Id>-ReferenceStudy.blend with collection
    <Id>.ReferenceStudy (Blender names stop at 63 bytes, so construction
    stages are '<Building>.Stage0')."""
    if len(ident + '.ReferenceStudy') > 63:
        raise ValueError(f'{ident}: scene id too long for a Blender collection name')
    MODELS[ident] = {'builder': builder, 'resource': resource, 'allowed': allowed, 'maxHeight': height,
                     'triangles': ceiling, 'faction': faction, 'stageOf': stage_of}


# Allowed volumes (x0, y0, z0, x1, y1, z1) in tile coordinates; every vertex
# must lie inside one of them (the blueprint's occupied cells).
EXTRACTOR_CELLS = [(0, 0, 0, 2, 2, 1.9), (0, 2, -.3, 1, 3, 1.0)]
for _f in (FOLK, IRON):
    _register(f'MoreFluidsFluidExtractor.{_f}', lambda f=_f: fluid_extractor(f),
              f'Buildings/Water/MoreFluidsFluidExtractor/MoreFluidsFluidExtractor.{_f}.Model',
              EXTRACTOR_CELLS, 1.9, 2600, _f)
    _register(f'MoreFluidsFluidExtractor.{_f}.Stage0', lambda f=_f: fluid_extractor_stage(f),
              f'Buildings/Water/MoreFluidsFluidExtractor/MoreFluidsFluidExtractor.{_f}.ConstructionStage0.Model',
              [(-.03, -.03, -.3, 2.03, 2.03, 1.2), (0, 2, -.3, 1, 3, 1.0)], 1.2, 700, _f,
              stage_of=f'MoreFluidsFluidExtractor.{_f}')


# ---------------------------------------------------------------- Desalinator

def salt_tray(k, x0, x1, y0, y1, z, faction):
    """Shallow evaporation pan on short legs: timber rim, white salt crust."""
    rim = 'trim' if faction == FOLK else 'planks2'
    k.face([(x0 + .04, y0 + .04, z + .04), (x1 - .04, y0 + .04, z + .04), (x1 - .04, y1 - .04, z + .04),
            (x0 + .04, y1 - .04, z + .04)], 'salt')
    k.box((x0, y0, z - .04), (x1, y0 + .05, z + .09), rim)
    k.box((x0, y1 - .05, z - .04), (x1, y1, z + .09), rim)
    k.box((x0, y0 + .05, z - .04), (x0 + .05, y1 - .05, z + .09), rim, skip=('-y', '+y'))
    k.box((x1 - .05, y0 + .05, z - .04), (x1, y1 - .05, z + .09), rim, skip=('-y', '+y'))
    for x in (x0 + .03, x1 - .09):
        for y in (y0 + .03, y1 - .09):
            k.box((x, y, 0), (x + .06, y + .06, z - .04), 'frame', skip=('-z', '+z'))


def lean_to(k, x_wall, x_edge, y0, y1, z_wall, z_edge, faction):
    """Condenser hood: a lean-to roof from the house wall out over the pans,
    on two posts, with a gutter along its low edge."""
    s = 1 if x_edge > x_wall else -1
    for c in range(2):
        t0, t1 = c / 2, (c + 1) / 2
        xa, xb = x_edge + (x_wall - x_edge) * t0, x_edge + (x_wall - x_edge) * t1
        za, zb = z_edge + (z_wall - z_edge) * t0, z_edge + (z_wall - z_edge) * t1
        if s < 0:
            quad = [(xa, y1, za), (xa, y0, za), (xb, y0, zb), (xb, y1, zb)]
        else:
            quad = [(xa, y0, za), (xa, y1, za), (xb, y1, zb), (xb, y0, zb)]
        k.roof_course(quad, 'roof', c)
    t = .05
    k.poly([(x_edge, y0, z_edge - t), (x_wall, y0, z_wall - t), (x_wall, y1, z_wall - t), (x_edge, y1, z_edge - t)],
           'board', (-s * (z_wall - z_edge), 0, -abs(x_wall - x_edge)))
    k.poly([(x_edge, y1, z_edge - t), (x_edge, y0, z_edge - t), (x_edge, y0, z_edge), (x_edge, y1, z_edge)], 'trim', (s, 0, 0))
    for y, ny in ((y0, -1), (y1, 1)):
        k.poly([(x_edge, y, z_edge - t), (x_edge, y, z_edge), (x_wall, y, z_wall), (x_wall, y, z_wall - t)], 'trim', (0, ny, 0))
    px = x_edge - s * .07
    for y in (y0 + .07, y1 - .07):
        k.box((px - .05, y - .05, 0), (px + .05, y + .05, z_edge - .05), 'frame', skip=('-z', '+z'))
    gutter = 'trim' if faction == FOLK else 'paint'
    gx0, gx1 = sorted((x_edge - s * .015, x_edge - s * .11))
    k.box((gx0, y0 - .02, z_edge - .13), (gx1, y1 + .02, z_edge - .06), gutter)


def power_hub(k, x_face, y, z, s, faction):
    """Mechanical connection on a transput face: a bearing post, a short
    shaft and a gear disc at the building edge (s = -1 left, +1 right)."""
    bx0, bx1 = sorted((x_face - s * .16, x_face - s * .06))
    k.box((bx0, y - .06, 0), (bx1, y + .06, z - .06), 'frame', skip=('-z',))
    lo, hi = sorted((x_face - s * .16, x_face - s * .005))
    k.cylinder((0, y, z), .04, lo, hi, 'metal', sides=8, axis='x')
    lo, hi = sorted((x_face - s * .06, x_face - s * .015))
    k.cylinder((0, y, z), .15, lo, hi, 'metal' if faction == FOLK else 'paint', sides=12, axis='x',
               cap_keys=('hatch', 'hatch'))


def desalinator(faction):
    """3 x 4 x 4, BaseZ 1 (vanilla Large Water Pump layout): a narrow
    timber house down the middle (door on the entrance tile), stepped
    evaporation pans with white salt crust on both wings under lean-to
    condenser hoods, and the intake pump house over the water tile (1, 3)
    with a brine spout. Power connects on the left and right faces of the
    middle row (blueprint transputs (0, 1, 1) and (2, 1, 1))."""
    k = Kit(f'MoreFluidsDesalinator.{faction}', faction_palette(faction), seed=21)
    x0, x1, y0, y1, h = .98, 2.02, .14, 2.3, 1.22
    plank_house(k, x0, x1, y0, y1, h, faction)
    door(k, 1.5, y0, .4, .7)
    gable_ends_y(k, x0, x1, y0, y1, h, 1.78, 'board')
    roof_y(k, .9, 2.1, .04, 2.4, h - .02, 1.86, faction)
    k.cylinder((1.5, y0, 1.4), .11, y0 + .01, y0 - .03, 'metal', sides=8, axis='y', caps=(False, True), cap_keys=('port', 'port'))
    # Pans: front tray in the open, two under each hood, stepping up to the back.
    for wx0, wx1 in ((.18, .9), (2.1, 2.82)):
        salt_tray(k, wx0, wx1, .16, .88, .2, faction)
        salt_tray(k, wx0, wx1, .96, 1.86, .34, faction)
        salt_tray(k, wx0, wx1, 1.94, 2.84, .48, faction)
    lean_to(k, x0 - .06, .04, 1.9, 2.92, 1.14, .98, faction)
    lean_to(k, x1 + .06, 2.96, 1.9, 2.92, 1.14, .98, faction)
    # Feed pipes from the house into the back pans.
    key = 'metal' if faction == FOLK else 'paint'
    pipe_run(k, [(1.14, 2.62, .76), (.54, 2.62, .76), (.54, 2.62, .64)], .045, key)
    pipe_run(k, [(1.86, 2.62, .76), (2.46, 2.62, .76), (2.46, 2.62, .64)], .045, key)
    power_hub(k, 0, 1.4, .62, -1, faction)
    power_hub(k, 3, 1.4, .62, 1, faction)

    # Intake pump house over the water at (1, 3).
    px0, px1, py0, py1, ph = 1.16, 1.84, 2.36, 3.84, .9
    plank_house(k, px0, px1, py0, py1, ph, faction)
    gable_ends_y(k, px0, px1, py0, py1, ph, 1.36, 'board')
    roof_y(k, 1.08, 1.92, 2.3, 3.92, ph - .02, 1.44, faction, courses=1)
    intake_pipe(k, 1.5, 3.5, faction, top=.1)
    flywheel(k, '#FlywheelAnimated', (1.92, 3.1, .5), .24, faction, axis='x', thickness=.05)
    k.cylinder((0, 3.1, .5), .03, px1 - .02, 1.95, 'metal', sides=6, axis='x')
    # Pump rod through the ridge.
    k.box((1.42, 3.3, 1.38), (1.58, 3.5, 1.52), 'metal')
    k.begin('#PumpRodAnimated', (1.5, 3.4, 1.6), ('bob', 'z', .07))
    k.cylinder((1.5, 3.4, 0), .035, 1.4, 1.74, 'metal', sides=6, caps=(False, True))
    k.box((1.38, 3.36, 1.66), (1.62, 3.44, 1.72), 'frame')
    k.end()
    # Brine spout out of the back of the pump house, crusted with salt.
    k.beam((1.5, py1 - .05, .5), (1.5, 3.97, .38), .14, .06, 'board')
    k.beam((1.5, py1 - .02, .545), (1.5, 3.95, .43), .08, .02, 'salt', caps=False)
    k.empty('#Slot#Entrance', (1.5, .4, .04), 180)
    return k


def desalinator_stage(faction):
    k = Kit(f'MoreFluidsDesalinator.{faction}.ConstructionStage0', faction_palette(faction), seed=22)
    dirt_patch(k, [(0, 0, 3, 3)])
    stage_frame(k, 0, 3, 0, 3, 1.1, metal=True)
    for x in (1.3, 1.7):
        k.box((x - .05, 2.7, 0), (x + .05, 3.94, .085), 'frame', skip=('-z',))
    intake_pipe(k, 1.5, 3.5, faction, top=0)
    return k


# ---------------------------------------------------------------- Healing Spring (buildable well)

def healing_well(faction):
    """1 x 1 x 2, BaseZ 0, no entrance: a carved-stone well basin with mint
    mineral stains, a timber frame carrying the faction's pump head, a
    power-driven wheel (animated) and a small roof."""
    k = Kit(f'MoreFluidsHealingWell.{faction}', faction_palette(faction), seed=31)
    c = (.5, .5)
    k.revolve(c, [(.44, 0), (.44, .26), (.47, .28), (.47, .36), (.36, .36), (.36, .2), (0, .2)], 'stone', sides=8)
    # Mint mineral staining down three faces of the basin.
    apothem = .44 * math.cos(math.pi / 8) + .004
    for i in (1, 3, 6):
        a = 2 * math.pi * (i + 1) / 8
        nx, ny = math.cos(a), math.sin(a)
        tx, ty = -ny, nx
        px, py = .5 + nx * apothem, .5 + ny * apothem
        k.poly([(px - tx * .05, py - ty * .05, .03), (px + tx * .05, py + ty * .05, .03),
                (px + tx * .07, py + ty * .07, .25), (px - tx * .07, py - ty * .07, .25)], 'teal', (nx, ny, 0))
    for x in (.1, .9):
        k.box((x - .05, .45, .0), (x + .05, .55, 1.52), 'frame', skip=('-z',), top='end')
    k.box((.02, .44, 1.32), (.98, .56, 1.42), 'trim')
    for x in (.1, .9):
        k.beam((x + (.05 if x < .5 else -.05), .5, .98), ((x + .5) / 2, .5, 1.32), .05, .05, 'frame')
    # Pump head: barrel pump (Folktails) or riveted cylinder (Iron Teeth), standpipe and spout.
    body = 'planks' if faction == FOLK else 'rib'
    band = 'metal' if faction == FOLK else 'paint'
    k.cylinder((.5, .5, 0), .13, .82, 1.2, body, sides=10, cap_keys=('end', 'metal'))
    hoop(k, (.5, .5), .14, .88, band, .04, sides=10)
    hoop(k, (.5, .5), .14, 1.1, band, .04, sides=10)
    k.cylinder((.5, .5, 0), .04, 1.2, 1.32, 'metal', sides=6, caps=(False, False))
    k.cylinder((.5, .5, 0), .05, .2, .82, 'metal', sides=8, caps=(False, False))
    pipe_run(k, [(.62, .5, 1.0), (.72, .5, 1.0), (.72, .5, .56)], .035, band)
    # Power-driven wheel in front of the pump head, on the drive shaft.
    flywheel(k, '#WheelAnimated', (.5, .29, 1.1), .17, faction, axis='y', thickness=.05)
    k.cylinder((.5, 0, 1.1), .03, .26, .38, 'metal', sides=6, axis='y')
    if faction == FOLK:
        k.cone_roof(c, .52, 1.5, 1.96, 'roof', sides=8, courses=2, rim='board')
    else:
        k.cone_roof(c, .6, 1.5, 1.88, 'roof', sides=4, courses=2, rim='board')
        k.cylinder((.5, .5, 0), .04, 1.84, 1.96, 'metal', sides=6, caps=(False, True))
    return k


def healing_well_stage(faction):
    k = Kit(f'MoreFluidsHealingWell.{faction}.ConstructionStage0', faction_palette(faction), seed=32)
    dirt_patch(k, [(0, 0, 1, 1)])
    k.revolve((.5, .5), [(.44, 0), (.44, .14), (.36, .14), (.36, .04), (0, .04)], 'stone', sides=8)
    for x in (.1, .9):
        k.box((x - .05, .45, .0), (x + .05, .55, .86), 'metal', skip=('-z',))
    k.box((.02, .44, .82), (.98, .56, .9), 'metal')
    return k


# ---------------------------------------------------------------- map objects

def healing_spring():
    """Map Healing Spring, 1 x 1 x 1: a low ring of mossy boulders round a
    dark vent, with mint mineral crusts terracing down to the water."""
    k = Kit('MoreFluidsHealingSpring', COMMON_PALETTE, seed=41)
    rng = random.Random(41)

    def mossy(normal, points):
        return 'moss' if normal.z > .62 else 'rock'
    rocks = [((.22, .27, 0), (.17, .15, .26)), ((.77, .3, 0), (.16, .18, .32)), ((.79, .75, 0), (.17, .15, .22)),
             ((.25, .78, 0), (.18, .16, .36)), ((.52, .86, 0), (.11, .09, .17))]
    for center, size in rocks:
        k.hull(rock_points(rng, center, size, 14), mossy, cut=0)
    # Mint crust terraces round the vent, moss at their outer edge.
    jitter = [rng.uniform(.82, 1.12) for _ in range(10)]
    k.revolve((.5, .52), [(.38, .0), (.34, .04), (.29, .05), (.25, .09), (.17, .1), (.12, .07)], None, sides=10,
              keys=['moss', 'moss', 'teal', 'teal', 'teal'], wobble=lambda ring, i: jitter[i] if ring < 4 else 1)
    k.cylinder((.5, .52, 0), .11, -.05, .07, 'rockDark', sides=10, caps=(False, False))
    k.disc((.5, .52), .11, -.05, 'rockDark', sides=10)
    return k


def geyser():
    """Map Geyser, 1 x 1 x 1: a grey-white sinter cone of stepped terraces
    with ochre mineral bands round a dark vent."""
    k = Kit('MoreFluidsGeyser', COMMON_PALETTE, seed=51)
    rng = random.Random(52)
    noise = [rng.uniform(.86, 1.08) for _ in range(12)]
    profile = [(.44, 0), (.4, .06), (.35, .08), (.33, .12), (.27, .14), (.25, .21), (.2, .23), (.18, .32),
               (.14, .35), (.11, .32), (.1, .2)]
    keys = ['crack', 'sinter', 'ochre', 'sinter', 'crack', 'sinter', 'sinter', 'sinter', 'rockDark', 'rockDark']
    k.revolve((.5, .5), profile, None, sides=12, keys=keys,
              wobble=lambda ring, i: (noise[i] * (1 + .06 * math.sin(ring * 1.7 + i))) if ring < 9 else 1)
    k.disc((.5, .5), .1, .2, 'rockDark', sides=12)
    rng = random.Random(51)
    for center, size in (((.17, .2, 0), (.12, .1, .14)), ((.84, .74, 0), (.11, .12, .12))):
        k.hull(rock_points(rng, center, size, 9), 'grey', cut=0)
    return k


MAP_CELL = [(0, 0, -.06, 1, 1, .95)]
DESAL_CELLS = [(0, 0, 0, 3, 3, 2.9), (1, 3, -.3, 2, 4, 2.0)]
WELL_CELL = [(0, 0, 0, 1, 1, 1.98)]
for _f in (FOLK, IRON):
    _register(f'MoreFluidsDesalinator.{_f}', lambda f=_f: desalinator(f),
              f'Buildings/Water/MoreFluidsDesalinator/MoreFluidsDesalinator.{_f}.Model', DESAL_CELLS, 2.9, 4000, _f)
    _register(f'MoreFluidsDesalinator.{_f}.Stage0', lambda f=_f: desalinator_stage(f),
              f'Buildings/Water/MoreFluidsDesalinator/MoreFluidsDesalinator.{_f}.ConstructionStage0.Model',
              [(-.03, -.03, -.3, 3.03, 3.03, 1.3), (1, 3, -.3, 2, 4, 1.0)], 1.3, 800, _f,
              stage_of=f'MoreFluidsDesalinator.{_f}')
    _register(f'MoreFluidsHealingWell.{_f}', lambda f=_f: healing_well(f),
              f'Buildings/Water/MoreFluidsHealingWell/MoreFluidsHealingWell.{_f}.Model', WELL_CELL, 1.98, 2000, _f)
    _register(f'MoreFluidsHealingWell.{_f}.Stage0', lambda f=_f: healing_well_stage(f),
              f'Buildings/Water/MoreFluidsHealingWell/MoreFluidsHealingWell.{_f}.ConstructionStage0.Model',
              [(-.03, -.03, 0, 1.03, 1.03, 1.0)], 1.0, 500, _f, stage_of=f'MoreFluidsHealingWell.{_f}')
_register('MoreFluidsHealingSpring', healing_spring,
          'MapEditor/Objects/MoreFluidsHealingSpring/MoreFluidsHealingSpring.Model', MAP_CELL, .5, 1000)
_register('MoreFluidsGeyser', geyser, 'MapEditor/Objects/MoreFluidsGeyser/MoreFluidsGeyser.Model', MAP_CELL, .6, 1000)
