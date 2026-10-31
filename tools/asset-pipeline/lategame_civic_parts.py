"""Shared parts for the food-industry and civic-science late-game studies.

Owned by the FertilizerWorks / FoodPackagingWorks / Greenhouse /
TechnicalSchool / PublicHealthLab modules. Artwork coordinates: X across,
Y back, Z up; one unit is one tile and one height layer.

Every helper keeps same-facing parallel surfaces at least LAYER_GAP apart or
buries one inside a solid. Bottom faces never share a plane: cores sink a
little into whatever they stand on, so their bottoms are buried.
"""
import math

from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS
import lategame_kit as K
from lategame_kit import (CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK, WINDOW,
                          LAYER_GAP, GLOW, CYAN)

SQ2 = math.sqrt(2)


# ---------------------------------------------------------------- basics

def blk(g, x0, y0, z0, x1, y1, z1, mat):
    """Box by bounds."""
    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError(f'Degenerate block {x0, y0, z0, x1, y1, z1}')
    g.box(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), (x1 - x0, y1 - y0, z1 - z0), mat)


def door(g, x, wall_y, bottom, ident):
    """Native one-tile Barrack portal standing .015 proud of a solid front
    face at wall_y (its orange surround never shares the wall plane)."""
    from industrial_facades import building_portal
    if abs((x % 1) - .5) > 1e-6 or bottom != int(bottom):
        raise ValueError('Doors are centred on a tile at a whole layer')
    building_portal(g, x, wall_y - .135, bottom)
    g.doorways.append({'id': ident, 'position': [x, wall_y, bottom], 'outward': [0, -1]})


def podium(g, x0, y0, x1, y1, top, *, mat=CONCRETE, joints=True, foot=True, skip=(), base=0.0):
    """Cast concrete podium whose walking surface is exactly z=top.

    The foot sinks 30 mm below `base` so no bottom face shares the ground
    plane with another; the core top is buried in the proud coping.
    """
    blk(g, x0, y0, base, x1, y1, top - .03, mat)
    if foot:
        blk(g, x0 - .03, y0 - .03, base - .03, x1 + .03, y1 + .03, base + .14, mat)
    blk(g, x0 - .05, y0 - .05, top - .10, x1 + .05, y1 + .05, top, mat)
    if not joints:
        return
    lo, hi = base + (.14 if foot else .02), top - .10
    if hi - lo < .15:
        return
    for x in _stations(x0, x1, 1.0):
        for y, s in ((y0, -1), (y1, 1)):
            if s < 0 and any(a - .08 < x < b + .08 for a, b in skip):
                continue
            blk(g, x - .05, min(y, y + s * .025), lo, x + .05, max(y, y + s * .025), hi, mat)
    for y in _stations(y0, y1, 1.0):
        for x, s in ((x0, -1), (x1, 1)):
            blk(g, min(x, x + s * .025), y - .05, lo, max(x, x + s * .025), y + .05, hi, mat)


def pier(g, x, y, bottom, top, w=.3):
    """Concrete pier with a sunk foot and a steel bearing cap."""
    blk(g, x - w / 2, y - w / 2, bottom, x + w / 2, y + w / 2, top, CONCRETE)
    blk(g, x - w / 2 - .04, y - w / 2 - .04, bottom - .03, x + w / 2 + .04, y + w / 2 + .04, bottom + .1, CONCRETE)
    blk(g, x - w / 2 - .025, y - w / 2 - .025, top, x + w / 2 + .025, y + w / 2 + .025, top + .05, IRON)


def rail(g, a, b, z, *, height=.62, pitch=.6, skip_start=False, skip_end=False, mat=IRON):
    """Handrail: .07 posts, .04 top and mid rails (no shared face planes)."""
    ax, ay = a
    bx, by = b
    length = math.hypot(bx - ax, by - ay)
    count = max(1, math.ceil(length / pitch))
    for i in range(count + 1):
        if (i == 0 and skip_start) or (i == count and skip_end):
            continue
        px, py = ax + (bx - ax) * i / count, ay + (by - ay) * i / count
        g.box((px, py, z + height / 2 - .01), (.07, .07, height - .02), mat)
    for h in (height, height * .5):
        g.beam((ax, ay, z + h), (bx, by, z + h), .04, mat=mat)


def walk(g, x0, y0, x1, y1, z, rails=('front',)):
    """Steel grating walkway at whole layer z with handrails on chosen edges."""
    K.catwalk(g, x0, y0, x1, y1, z, rails=(), brackets=None)
    i = .045
    lines = {'front': ((x0 + i, y0 + i), (x1 - i, y0 + i)), 'back': ((x0 + i, y1 - i), (x1 - i, y1 - i)),
             'left': ((x0 + i, y0 + i), (x0 + i, y1 - i)), 'right': ((x1 - i, y0 + i), (x1 - i, y1 - i))}
    for name in rails:
        a, b = lines[name]
        side = name in ('left', 'right')
        rail(g, a, b, z, skip_start=side and 'front' in rails, skip_end=side and 'back' in rails)


def _stations(a, b, pitch):
    count = max(1, round((b - a) / pitch))
    return [a + (b - a) * i / count for i in range(1, count)]


# ---------------------------------------------------------------- framed walls

FACES = {'front': ((0, -1), 'X'), 'back': ((0, 1), 'X'), 'left': ((-1, 0), 'Y'), 'right': ((1, 0), 'Y')}


def framed_block(g, x0, y0, x1, y1, z0, z1, *, infill=ORANGE, frame=WOOD, pitch=1.0,
                 faces=('front', 'back', 'left', 'right'), corner=.17, post=.11,
                 floors=(), windows=None, sink=.02, top_rail=True, skip=None):
    """Solid core (infill) with a proud dark frame: corner posts, bay posts,
    sill and eave rails and optional floor bands at absolute heights `floors`.

    `windows` maps a face name to (u, z, scale, style) tuples, u along the
    face (x for front/back, y for left/right). `skip` maps a face to a list
    of (u0, u1) ranges kept free of bay posts (portals, bays).
    """
    blk(g, x0, y0, z0 - sink, x1, y1, z1, infill)
    c = corner / 2
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        blk(g, x - c, y - c, z0, x + c, y + c, z1 - .02, frame)
    skip = skip or {}
    for face in faces:
        (nx, ny), along = FACES[face]
        a, b = (x0, x1) if along == 'X' else (y0, y1)
        plane = {'front': y0, 'back': y1, 'left': x0, 'right': x1}[face]
        def slab(u0, u1, za, zb, proud):
            if along == 'X':
                ya, yb = sorted((plane, plane + ny * proud))
                blk(g, u0, ya, za, u1, yb, zb, frame)
            else:
                xa, xb = sorted((plane, plane + nx * proud))
                blk(g, xa, u0, za, xb, u1, zb, frame)
        for u in _stations(a, b, pitch):
            if any(lo - post / 2 < u < hi + post / 2 for lo, hi in skip.get(face, ())):
                continue
            slab(u - post / 2, u + post / 2, z0, z1 - .02, .055)
        rails = [(z0 + .015, z0 + .115)]
        if top_rail:
            rails.append((z1 - .13, z1 - .03))
        rails += [(z - .05, z + .05) for z in floors]
        for za, zb in rails:
            slab(a + c, b - c, za, zb, .04)
    if windows:
        from architectural_windows import window
        for face, items in windows.items():
            plane = {'front': y0, 'back': y1, 'left': x0, 'right': x1}[face]
            for u, z, scale, style in items:
                if face in ('front', 'back'):
                    window(g, u, plane, z, scale, face, style)
                else:
                    window(g, plane, u, z, scale, face, style)


def native_window(g, x, y, z, scale, face, style):
    from architectural_windows import window
    window(g, x, y, z, scale, face, style)


def framed_window(g, center, n, up, scale, style):
    """Native window assembly seated on an arbitrary plane.

    `center` lies on the opaque host plane; `n` is the outward normal and
    `up` the window's up direction (orthonormal to n). Native UVs are kept.
    """
    from architectural_windows import window
    t = _cross(up, n)
    tmp = Geometry('window source')
    window(tmp, 0, 0, 0, scale, 'front', style)
    pts = []
    for vx, vy, vz in tmp.vertices:
        px, py, pz = -vx, -vy, vz           # back to artwork coordinates
        pts.append(tuple(center[i] + px * t[i] - py * n[i] + pz * up[i] for i in range(3)))
    for face, mat, uv, src in zip(tmp.faces, tmp.materials, tmp.face_uvs, tmp.face_sources, strict=True):
        g.add([pts[i] for i in face], [tuple(range(len(face)))], mat)
        g.face_uvs[-1] = uv
        g.face_sources[-1] = src


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm(v):
    m = math.sqrt(sum(c * c for c in v))
    return tuple(c / m for c in v)


# ---------------------------------------------------------------- roofs

def pyramid_roof(g, cx, cy, half, z, h, *, mat=ROOF, overhang=.12, t=.06):
    """Square pyramid (spire or tower cap) with a thin eave band."""
    r = (half + overhang) * SQ2
    K.revolve(g, (cx, cy, z), [(r, 0), (r, t), (0, h)], mat, segments=4, phase=math.pi / 4)


def hip_roof(g, x0, y0, x1, y1, z, h, *, mat=ROOF, overhang=.14, t=.07, fascia=True):
    """Hipped roof solid; ridge along the longer side."""
    xa, ya, xb, yb = x0 - overhang, y0 - overhang, x1 + overhang, y1 + overhang
    w, d = xb - xa, yb - ya
    zt = z + t
    if w >= d:
        inset = d / 2
        r0, r1 = (xa + inset, (ya + yb) / 2, zt + h), (xb - inset, (ya + yb) / 2, zt + h)
    else:
        inset = w / 2
        r0, r1 = ((xa + xb) / 2, ya + inset, zt + h), ((xa + xb) / 2, yb - inset, zt + h)
    base = [(xa, ya, zt), (xb, ya, zt), (xb, yb, zt), (xa, yb, zt)]
    low = [(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)]
    # Eave band (vertical faces) and underside.
    for i in range(4):
        j = (i + 1) % 4
        mid = ((low[i][0] + low[j][0]) / 2, (low[i][1] + low[j][1]) / 2)
        cx, cy = (xa + xb) / 2, (ya + yb) / 2
        K.oriented_polygon(g, [low[i], low[j], base[j], base[i]], (mid[0] - cx, mid[1] - cy, 0), mat)
    K.oriented_polygon(g, low, (0, 0, -1), mat)
    if w >= d:
        K.oriented_polygon(g, [base[0], base[1], r1, r0], (0, -1, 1), mat)
        K.oriented_polygon(g, [base[2], base[3], r0, r1], (0, 1, 1), mat)
        K.oriented_polygon(g, [base[3], base[0], r0], (-1, 0, 1), mat)
        K.oriented_polygon(g, [base[1], base[2], r1], (1, 0, 1), mat)
    else:
        K.oriented_polygon(g, [base[0], base[1], r0], (0, -1, 1), mat)
        K.oriented_polygon(g, [base[2], base[3], r1], (0, 1, 1), mat)
        K.oriented_polygon(g, [base[3], base[0], r0, r1], (-1, 0, 1), mat)
        K.oriented_polygon(g, [base[1], base[2], r1, r0], (1, 0, 1), mat)
    if fascia:
        blk(g, x0 - overhang + .05, y0 - overhang + .05, z - .09, x1 + overhang - .05, y1 + overhang - .05, z + .002, WOOD)
    # Steel ridge cap.
    if abs(r1[0] - r0[0]) + abs(r1[1] - r0[1]) > .05:
        g.beam((r0[0], r0[1], r0[2] + .02), (r1[0], r1[1], r1[2] + .02), .1, .06, IRON)


def octagon_frustum(g, cx, cy, z0, z1, r0, r1, mat, *, cap_bottom=True, cap_top=True):
    """Eight-sided solid with facets facing 0, 45, 90... degrees. r is the
    apothem (distance to the facet plane)."""
    k = 1 / math.cos(math.pi / 8)
    K.revolve(g, (cx, cy, z0), [(r0 * k, 0), (r1 * k, z1 - z0)], mat, segments=8,
              phase=math.pi / 8, cap_bottom=cap_bottom, cap_top=cap_top)


def facet_window(g, cx, cy, angle_deg, apothem_lo, z_lo, apothem_hi, z_hi, t, scale, style, offset=0.0):
    """Seat a native window on an octagon/square facet plane at fraction t
    up the facet. `offset` slides it sideways along the facet."""
    a = math.radians(angle_deg)
    radial = (math.cos(a), math.sin(a), 0)
    tangent = (-math.sin(a), math.cos(a), 0)
    dr, dz = apothem_hi - apothem_lo, z_hi - z_lo
    L = math.hypot(dr, dz)
    up = _norm((radial[0] * dr / L, radial[1] * dr / L, dz / L))
    n = _norm((radial[0] * dz / L, radial[1] * dz / L, -dr / L))
    ap = apothem_lo + dr * t
    z = z_lo + dz * t
    center = (cx + radial[0] * ap + tangent[0] * offset, cy + radial[1] * ap + tangent[1] * offset, z)
    framed_window(g, center, n, up, scale, style)


# ---------------------------------------------------------------- vessels

def silo(g, x, y, z0, r, h, *, base_h=1.1, cone=.9, hoops=5, body=PLANK, segments=12):
    """Timber-stave silo on a concrete drum, hooped in steel, teal cone cap."""
    K.revolve(g, (x, y, z0), [(r + .07, 0), (r + .07, base_h)], CONCRETE, segments=segments)
    # Footing turned half a side so neighbouring silos' footings meet face to face.
    K.revolve(g, (x, y, z0 - .03), [(r + .11, 0), (r + .11, .19)], CONCRETE, segments=segments, cap_top=True,
              phase=math.pi / segments)
    zb = z0 + base_h
    K.revolve(g, (x, y, zb), [(r, 0), (r, h)], body, segments=segments, cap_bottom=False, cap_top=False)
    for k in range(hoops):
        z = zb + .35 + (h - .6) * k / max(1, hoops - 1)
        K.band(g, (x, y, 0), r, z, .07, IRON, segments=segments)
    top = zb + h
    K.revolve(g, (x, y, top), [(r + .1, 0), (r + .1, .06), (.12, cone), (0, cone + .02)], ROOF, segments=segments)
    K.band(g, (x, y, 0), r, top - .05, .1, FORGED, segments=segments, proud=.035)
    return top + cone


def hopper(g, x, y, z_bot, z_top, half_top, half_bot, mat=FORGED):
    """Inverted square pyramid frustum (bin hopper)."""
    K.revolve(g, (x, y, z_bot), [(half_bot * SQ2, 0), (half_top * SQ2, z_top - z_bot)], mat,
              segments=4, phase=math.pi / 4)


def horizontal_vessel(g, x0, x1, y, z, r, *, mat=IRON, bands=3, axis='X', segments=12, saddles=True):
    """Riveted horizontal pressure vessel with domed ends on concrete saddles."""
    if axis == 'X':
        g.cylinder(((x0 + x1) / 2, y, z), r, x1 - x0, mat, 'X', segments)
        for xe, s in ((x0, -1), (x1, 1)):
            _end_dome(g, (xe, y, z), r, s, 'X', mat, segments)
        for k in range(bands):
            xx = x0 + (x1 - x0) * (k + .5) / bands
            g.cylinder((xx, y, z), r + .025, .07, PAINTED, 'X', segments)
        if saddles:
            for xx in (x0 + .3, x1 - .3):
                blk(g, xx - .12, y - r * .8, 0, xx + .12, y + r * .8, z - r * .55, CONCRETE)
    else:
        y0, y1 = x0, x1
        g.cylinder((y, (y0 + y1) / 2, z), r, y1 - y0, mat, 'Y', segments)
        for ye, s in ((y0, -1), (y1, 1)):
            _end_dome(g, (y, ye, z), r, s, 'Y', mat, segments)
        for k in range(bands):
            yy = y0 + (y1 - y0) * (k + .5) / bands
            g.cylinder((y, yy, z), r + .025, .07, PAINTED, 'Y', segments)
        if saddles:
            for yy in (y0 + .3, y1 - .3):
                blk(g, y - r * .8, yy - .12, 0, y + r * .8, yy + .12, z - r * .55, CONCRETE)


def _end_dome(g, p, r, s, axis, mat, segments, rings=4, squash=.45):
    """Dished head on a horizontal vessel end."""
    x, y, z = p
    verts = []
    for k in range(rings + 1):
        t = k / rings * math.pi / 2
        rr = r * math.cos(t) * (1 - .002 * k)
        d = r * squash * math.sin(t)
        for i in range(segments):
            a = i * 2 * math.pi / segments
            u, v = math.cos(a) * rr, math.sin(a) * rr
            if axis == 'X':
                verts.append((x + s * (d + .001), y + u, z + v))
            else:
                verts.append((x + u, y + s * (d + .001), z + v))
    faces = []
    for k in range(rings):
        for i in range(segments):
            j = (i + 1) % segments
            faces.append((k * segments + i, k * segments + j, (k + 1) * segments + j, (k + 1) * segments + i))
    # Orient outward along s*axis.
    g2 = Geometry('tmp')
    test = verts[faces[0][0]], verts[faces[0][1]], verts[faces[0][2]]
    e1 = [test[1][i] - test[0][i] for i in range(3)]
    e2 = [test[2][i] - test[0][i] for i in range(3)]
    nrm = _cross(e1, e2)
    mid = [sum(c) / 3 for c in zip(*test)]
    outward = [mid[0] - x, mid[1] - y, mid[2] - z]
    if sum(a * b for a, b in zip(nrm, outward)) < 0:
        faces = [tuple(reversed(f)) for f in faces]
    g.add(verts, faces, mat)


def gauge(g, x, y, z, face='front', r=.075):
    """Pressure gauge without glass: brass bezel, plaster dial, iron needle."""
    n = {'front': (0, -1), 'back': (0, 1), 'left': (-1, 0), 'right': (1, 0)}[face]
    axis = 'Y' if n[0] == 0 else 'X'
    g.cylinder((x + n[0] * .03, y + n[1] * .03, z), r, .06, BRASS, axis, 8)
    g.cylinder((x + n[0] * .065, y + n[1] * .065, z), r * .78, .012, CONCRETE, axis, 8)
    g.beam((x + n[0] * .074, y + n[1] * .074, z), (x + n[0] * .074 + (r * .55 if axis == 'Y' else 0),
            y + n[1] * .074 + (r * .55 if axis == 'X' else 0), z + r * .35), .014, .008, IRON)


def flanged_pipe(g, points, r=.06):
    K.pipe_run(g, points, r)


# ---------------------------------------------------------------- animated parts

def cowl(name, x, y, z, r=.16, h=.42, facing=0.0):
    """Rotating ventilator cowl (hood, throat and tail vane), SPIN_Z about (x,y)."""
    c = Geometry(name, (x, y, z))
    K.revolve(c, (x, y, z), [(r * .8, 0), (r * .8, h * .55)], FORGED, segments=12)
    K.band(c, (x, y, 0), r * .8, z + .05, .05, IRON, segments=12)
    a = facing
    dx, dy = math.cos(a), math.sin(a)
    # Hood: a box leaning forward, open face toward (dx, dy).
    hx, hy = x + dx * r * .35, y + dy * r * .35
    c.beam((x - dx * r * .2, y - dy * r * .2, z + h * .55), (hx + dx * r * .5, hy + dy * r * .5, z + h * .55), r * 1.9, r * 1.6, FORGED)
    c.cylinder((x, y, z + h * .55 + r * .85), r * .95, .05, IRON, 'Z', 12)
    c.beam((x - dx * r * .5, y - dy * r * .5, z + h * .6), (x - dx * r * 1.9, y - dy * r * 1.9, z + h * .6), .03, r * 1.2, IRON)
    return c


def loop_belt(name, origin, items):
    """Group of evenly pitched items for a CUSTOM_LOOP_<axis> conveyor."""
    return Geometry(name, origin)


def animate(obj, kind, value, frame_end):
    """CUSTOM_LOOP_<axis>: linear travel of `value` over the loop. Items are
    spaced at exactly `value`, so frame_end looks identical to frame 1."""
    if not kind.startswith('CUSTOM_LOOP_'):
        raise ValueError('Unknown custom animation ' + kind)
    axis = kind[-1]
    index = 'XYZ'.index(axis)
    sign = {'X': -1, 'Y': -1, 'Z': 1}[axis]
    base = obj.location[index]
    for frame, t in ((1, 0.0), (frame_end, 1.0)):
        obj.location[index] = base + sign * value * t
        obj.keyframe_insert(data_path='location', index=index, frame=frame)
    obj.location[index] = base
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def raised_tank(g, x, y, r, height, *, stand=1.0, bands=2, roof='cone', mat=IRON, segments=12, base=0.0):
    """Banded tank on four steel legs standing on sunk-foot piers (the kit's
    legged tank shares its leg and pad bottoms on the ground plane)."""
    for i in range(4):
        a = math.pi / 4 + i * math.pi / 2
        lx, ly = x + math.cos(a) * r * .72, y + math.sin(a) * r * .72
        pier(g, lx, ly, base, base + .2, .18)
        blk(g, lx - .06, ly - .06, base + .25, lx + .06, ly + .06, base + stand + .05, IRON)
    for i in range(4):
        a0 = math.pi / 4 + i * math.pi / 2
        a1 = a0 + math.pi / 2
        p0 = (x + math.cos(a0) * r * .72, y + math.sin(a0) * r * .72)
        p1 = (x + math.cos(a1) * r * .72, y + math.sin(a1) * r * .72)
        g.beam((p0[0], p0[1], base + .35), (p1[0], p1[1], base + stand - .1), .04, mat=IRON)
    K.revolve(g, (x, y, base + stand), [(r, 0), (r, height)], mat, segments=segments)
    for k in range(bands):
        K.band(g, (x, y, 0), r, base + stand + height * (k + .5) / bands, .07, PAINTED, segments=segments)
    top = base + stand + height
    if roof == 'cone':
        K.revolve(g, (x, y, top), [(r + .04, 0), (r + .04, .04), (.08, r * .55), (0, r * .58)], ROOF, segments=segments)
    else:
        K.dome(g, (x, y, top), r + .03, mat, segments=segments, squash=.45)
    return top


def obox(g, c, ax, ay, az, hx, hy, hz, mat):
    """Oriented box: centre c, right-handed orthonormal axes, half sizes."""
    pts = []
    for sx, sy, sz in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                       (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)):
        pts.append(tuple(c[i] + sx * hx * ax[i] + sy * hy * ay[i] + sz * hz * az[i] for i in range(3)))
    g.add(pts, [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)], mat)


def rot_x(p, pivot, angle):
    """Rotate point p about the X-parallel line through pivot."""
    y, z = p[1] - pivot[1], p[2] - pivot[2]
    c, s = math.cos(angle), math.sin(angle)
    return (p[0], pivot[1] + y * c - z * s, pivot[2] + y * s + z * c)


def mansard(g, x0, y0, x1, y1, z, h, inset, *, overhang=.14, deck=IRON):
    """Steep teal mansard (truncated hip) with a flat deck and timber fascia."""
    xa, ya, xb, yb = x0 - overhang, y0 - overhang, x1 + overhang, y1 + overhang
    lo = [(xa, ya, z), (xb, ya, z), (xb, yb, z), (xa, yb, z)]
    hi = [(x0 + inset, y0 + inset, z + h), (x1 - inset, y0 + inset, z + h),
          (x1 - inset, y1 - inset, z + h), (x0 + inset, y1 - inset, z + h)]
    normals = [(0, -1, .6), (1, 0, .6), (0, 1, .6), (-1, 0, .6)]
    for i in range(4):
        j = (i + 1) % 4
        K.oriented_polygon(g, [lo[i], lo[j], hi[j], hi[i]], normals[i], ROOF)
    K.oriented_polygon(g, lo, (0, 0, -1), ROOF)
    K.oriented_polygon(g, hi, (0, 0, 1), deck)
    blk(g, xa + .05, ya + .05, z - .1, xb - .05, yb - .05, z + .002, WOOD)
    return z + h


# ------------------------------------------------------------- brick skins
# Brick skins (2026-10-30, bricks pass): running-bond bricks in the native
# brick-red plaster (Plaster_Orange.IronTeeth) laid 0.02 proud of a solid wall
# whose own surface (Plaster_White here) shows as the mortar joints. Doors,
# windows and lamps on the wall stay clear: each is authored first through
# authored_box, and every course skips its box (plus a margin) on the face it
# stands on. Front and back courses run corner to corner; the side courses
# stop short of them, so no two bricks meet at a corner.
BRICK_REACH = .3      # a feature within this distance of a face plane opens it


def authored_box(g, fn):
    """Run fn(g) and return the artwork bounding box ((x, y, z), (x, y, z))
    of the vertices it added."""
    n0 = len(g.vertices)
    fn(g)
    o = g.origin
    pts = [(-x + o.x, -y + o.y, z + o.z) for x, y, z in g.vertices[n0:]]
    if not pts:
        raise ValueError('authored_box: the feature authored no geometry')
    return (tuple(min(p[i] for p in pts) for i in range(3)), tuple(max(p[i] for p in pts) for i in range(3)))


def brick_skin(g, x0, y0, x1, y1, z0, z1, *, faces=('front', 'back', 'left', 'right'), features=(), margin=.03):
    """Brick courses between z0 and z1 on the named faces of the solid wall
    block x0..x1, y0..y1, leaving the feature boxes (authored_box) open."""
    from lategame_mining_parts import _brick_runs, BRICK_COURSE, BRICK_JOINT, BRICK_PROUD, BRICK_EMBED
    pr, em, j = BRICK_PROUD, BRICK_EMBED, BRICK_JOINT
    planes = {'front': (1, y0, -1), 'back': (1, y1, 1), 'left': (0, x0, -1), 'right': (0, x1, 1)}
    runs = {'front': (x0 - pr, x1 + pr), 'back': (x0 - pr, x1 + pr),
            'left': (y0 + em + j, y1 - em - j), 'right': (y0 + em + j, y1 - em - j)}
    n = max(2, round((z1 - z0) / BRICK_COURSE))
    pitch = (z1 - z0) / n
    for face in faces:
        k, plane, out = planes[face]
        u_axis = 1 - k
        openings = [(lo[u_axis] - margin, hi[u_axis] + margin, lo[2] - margin, hi[2] + margin)
                    for lo, hi in features if lo[k] <= plane + BRICK_REACH and hi[k] >= plane - BRICK_REACH]
        na, nb = (plane - pr, plane + em) if out < 0 else (plane - em, plane + pr)
        for row in range(n):
            za, zb = z0 + row * pitch + j / 2, z0 + (row + 1) * pitch - j / 2
            spans = [runs[face]]
            for ua, ub, oa, ob in openings:
                if ob <= za or oa >= zb:
                    continue
                spans = [piece for a, b in spans for piece in ((a, min(b, ua)), (max(a, ub), b))
                         if piece[1] - piece[0] > .06]
            for a, b in spans:
                for u, v in _brick_runs(a, b, row % 2):
                    u, v = u + j / 2, v - j / 2
                    if k == 1:
                        blk(g, u, na, za, v, nb, zb, ORANGE)
                    else:
                        blk(g, na, u, za, nb, v, zb, ORANGE)
