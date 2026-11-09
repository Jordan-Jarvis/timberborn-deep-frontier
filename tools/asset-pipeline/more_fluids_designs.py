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
