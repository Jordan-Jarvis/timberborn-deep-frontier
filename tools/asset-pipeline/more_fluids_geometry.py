"""Authoring kit for the More Fluids models (Blender bmesh/mathutils, no bpy scene work).

Style: Timberborn's own faction building language (docs/more-fluids-design.md,
"Art"; user decision 2026-11-09): Folktails in brown/light timber, plank walls,
thatch and brass-coloured metal; Iron Teeth in dark timber, grey planks,
riveted plank-metal, plank roofs and blue painted metal. Map objects are
faction-neutral and use MaterialCollection.Common plus the three native
materials More Fluids registers into Common (REGISTERED_COMMON).

Units are tiles: x across, y back (0 = front, the entrance side), z up in
height layers from the building's base (BaseZ). The builder converts to the
exporter's source coordinates (-x, -y, z). Every face gets an explicit UV
island inside the atlas tile of its native material (the native atlases mix
unrelated sheets); no bevel, the native atlases paint the edges.
"""
import math
import random

import bmesh
from mathutils import Vector

# ---------------------------------------------------------------- palettes
# Atlas rectangles (u0, v0, u1, v1), measured on the shipped textures
# (outputs/more-fluids-art/native-renders/atlases-*.png, more_fluids_native_refs.py).
WOOD_STRIPS = [(k / 16 + .004, .012, (k + 1) / 16 - .004, .488) for k in range(8)] + \
              [(.5 + k / 16 + .004, .505, .5 + (k + 1) / 16 - .004, .995) for k in range(4)]
WOOD_END = (.632, .132, .743, .243)        # BaseWood solid end-grain rings
WOOD_HOLE = (.505, .132, .62, .245)        # BaseWood hollow ring (pipe or bore end)
WOOD_PLAIN = (.76, .01, .99, .24)          # BaseWood plain stained board area
PLANK_SHEET = (.01, .01, .99, .99)         # IrregularPlanks: eight vertical planks
METAL_PLATE = (.02, .52, .48, .98)         # BaseMetal plain plate
METAL_RIB = (.01, .13, .37, .49)           # BaseMetal ribbed bars
METAL_RING = (.757, .507, .993, .743)      # BaseMetal round hatch ring (mapped whole)
PAINT_STRIPS = [(k / 8 + .034, .02, k / 8 + .09, .98) for k in range(8)]
GLASS = (.77, .02, .98, .23)               # WindowsAtlas plain glass (glows at night)
PORTHOLE = (.755, .255, .995, .495)        # WindowsAtlas round glass in a metal rim
DARK = (.03, .03, .47, .47)                # WindowsAtlas dark interior (doorways)
PLASTER = (.02, .02, .98, .98)
TEAL_FOLK = (.012, .905, .088, .985)       # Details.Folktails plain teal corner
FORGED = (.01, .01, .99, .99)              # PlanksWithMetal: planks with metal straps
CORE_PANEL = (.02, .52, .48, .98)          # UnstableCore plain bronze panel
CRACKED = (.51, .51, .99, .99)             # Blockage cracked dry crust
BLOCK_GREY = (.01, .51, .49, .99)          # Blockage grey stone
DIRT = None                                # explicit fade UVs (DirtURP: v 0 at the rim)

# key -> (material, kind, rect(s), uv-units per tile)
#   kind: 'strip' boards with the grain along the longest edge; 'sheet' one
#   island, grain vertical on walls; 'whole' the face's box mapped onto the
#   rect (discs); 'world' seamless world projection; 'roof' course mapping;
#   'explicit' caller-supplied UVs.
def faction_palette(faction):
    if faction == 'Folktails':
        f = '.Folktails'
        frame, trim, accent = 'BaseWood_Brown' + f, 'BaseWood_LightBrown' + f, 'BaseWood_Yellow' + f
        planks, planks2 = 'IrregularPlanks_Brown' + f, 'IrregularPlanks_LightBrown' + f
        roof, teal = 'ThatchedRoof' + f, ('Details' + f, 'whole', TEAL_FOLK, None)
    elif faction == 'IronTeeth':
        f = '.IronTeeth'
        frame, trim, accent = 'BaseWood_DarkBrown' + f, 'BaseWood_Grey' + f, 'BaseWood_Indigo' + f
        planks, planks2 = 'IrregularPlanks_Grey' + f, 'IrregularPlanks_MetalForged' + f
        roof, teal = 'RoofPlanks' + f, ('PaintedMetal' + f, 'strip', PAINT_STRIPS, .45)
    else:
        raise ValueError(f'Unknown faction {faction}')
    return {
        'frame': (frame, 'strip', WOOD_STRIPS, .30),
        'trim': (trim, 'strip', WOOD_STRIPS, .30),
        'accent': (accent, 'strip', WOOD_STRIPS, .30),
        'end': (frame, 'whole', WOOD_END, None),
        'trimEnd': (trim, 'whole', WOOD_END, None),
        'hole': (frame, 'whole', WOOD_HOLE, None),
        'board': (frame, 'sheet', WOOD_PLAIN, .45),
        'planks': (planks, 'sheet', PLANK_SHEET, .55),
        'planks2': (planks2, 'sheet', FORGED if faction == 'IronTeeth' else PLANK_SHEET, .55),
        'roof': (roof, 'roof', None, None),
        'metal': ('BaseMetal' + f, 'sheet', METAL_PLATE, .75),
        'rib': ('BaseMetal' + f, 'sheet', METAL_RIB, .75),
        'hatch': ('BaseMetal' + f, 'whole', METAL_RING, None),
        'paint': ('PaintedMetal' + f, 'strip', PAINT_STRIPS, .45),
        'glass': ('WindowsAtlas' + f, 'whole', GLASS, None),
        'port': ('WindowsAtlas' + f, 'whole', PORTHOLE, None),
        'dark': ('WindowsAtlas' + f, 'whole', DARK, None),
        'salt': ('Plaster_White' + f, 'sheet', PLASTER, .6),
        'stone': ('Plaster_White' + f, 'sheet', PLASTER, .9),
        'teal': teal,
        'dirt': ('Dirt', 'explicit', DIRT, None),
    }


# Native materials that are not in MaterialCollection.Common but that the
# faction-neutral map objects use: More Fluids must register exactly these
# into CollectionId Common (as Deep Frontier's MaterialCollection.DeepFrontierMapResources does).
REGISTERED_COMMON = {
    'Plaster_White.IronTeeth': 'Materials/UberAtlas/Materials/IronTeeth/Plaster_White.IronTeeth',
    'Plaster_Orange.IronTeeth': 'Materials/UberAtlas/Materials/IronTeeth/Plaster_Orange.IronTeeth',
    'Details.Folktails': 'Materials/UberAtlas/Materials/Folktails/Details.Folktails',
    'Moss.Folktails': 'Materials/UberAtlas/Materials/Folktails/Moss.Folktails',
}
COMMON_PALETTE = {
    'rock': ('WaterSource', 'world', (0, 0, 1, 1), 1 / 1.2),
    'rockDark': ('UndergroundRuinsCliff', 'world', (0, 0, 1, 1), 1 / 1.2),
    'crack': ('Blockage', 'sheet', CRACKED, .55),
    'grey': ('Blockage', 'sheet', BLOCK_GREY, .55),
    'sinter': ('Plaster_White.IronTeeth', 'sheet', PLASTER, .7),
    'ochre': ('Plaster_Orange.IronTeeth', 'sheet', PLASTER, .7),
    'teal': ('Details.Folktails', 'whole', TEAL_FOLK, None),
    'moss': ('Moss.Folktails', 'sheet', PLASTER, .6),
    'dirt': ('Dirt', 'explicit', DIRT, None),
}

# Thatch: four horizontal courses, fringe at the bottom of each (low v).
# RoofPlanks: four rows of sixteen shingle strips.
ROOF_ROWS = [(r / 4 + .006, (r + 1) / 4 - .006) for r in range(4)]


class Part:
    """One exported node: static geometry, or an animated part whose
    vertices are stored relative to its pivot."""

    def __init__(self, name, pivot=(0, 0, 0), animation=None):
        self.name = name
        self.pivot = Vector(pivot)
        self.animation = animation      # ('rotate', axis, turns) | ('bob', axis, amplitude) | ('rock', axis, degrees)
        self.vertices, self.faces, self.uvs, self.materials, self.smooth = [], [], [], [], []


class Kit:
    def __init__(self, name, palette, seed=1):
        self.name = name
        self.palette = palette
        self.rng = random.Random(seed)
        self.parts = {name: Part(name)}
        self.part = self.parts[name]
        self.empties = []          # (name, position, yaw degrees)
        self.strip_turn = 0

    # ------------------------------------------------------------ parts
    def begin(self, name, pivot, animation):
        if name in self.parts:
            raise ValueError(f'{self.name}: part {name} already exists')
        self.parts[name] = Part(name, pivot, animation)
        self.part = self.parts[name]
        return self.part

    def end(self):
        self.part = self.parts[self.name]

    def empty(self, name, position, yaw):
        self.empties.append((name, tuple(position), yaw))

    # ------------------------------------------------------------ UVs
    def _island(self, points, normal, key, along):
        material, kind, rect, density = self.palette[key]
        if kind == 'strip':
            self.strip_turn += 1
            rect = rect[self.strip_turn % len(rect)]
        n = normal
        if kind == 'world':
            a = Vector((1, 0, 0)) if abs(n.x) < .9 else Vector((0, 1, 0))
            a = (a - n * a.dot(n)).normalized()
            b = n.cross(a).normalized()
            k = density
            return material, [(p.dot(a) * k + .37, p.dot(b) * k + .61) for p in points]
        if along is None:
            if kind == 'sheet' and abs(n.z) < .7:
                along = Vector((0, 0, 1))
            else:
                edges = [points[(i + 1) % len(points)] - p for i, p in enumerate(points)]
                along = max(edges, key=lambda e: e.length_squared)
        along = Vector(along)
        along = along - n * along.dot(n)
        if along.length < 1e-9:
            along = Vector((1, 0, 0)) - n * n.x
            if along.length < 1e-9:
                along = Vector((0, 1, 0)) - n * n.y
        along.normalize()
        across = n.cross(along).normalized()
        coords = [(p.dot(across), p.dot(along)) for p in points]   # u across the grain, v along it
        lo = [min(c[i] for c in coords) for i in range(2)]
        size = [max(c[i] for c in coords) - lo[i] for i in range(2)]
        u0, v0, u1, v1 = rect
        if kind == 'whole':
            return material, [(u0 + (c[0] - lo[0]) / max(size[0], 1e-9) * (u1 - u0),
                               v0 + (c[1] - lo[1]) / max(size[1], 1e-9) * (v1 - v0)) for c in coords]
        k = density
        su, sv = size[0] * k, size[1] * k
        if su > u1 - u0 or sv > v1 - v0:
            shrink = min((u1 - u0) / su if su else 1, (v1 - v0) / sv if sv else 1) * .999
            k *= shrink
            su, sv = su * shrink, sv * shrink
        ou = u0 + self.rng.random() * (u1 - u0 - su)
        ov = v0 + self.rng.random() * (v1 - v0 - sv)
        return material, [(ou + (c[0] - lo[0]) * k, ov + (c[1] - lo[1]) * k) for c in coords]

    # ------------------------------------------------------------ faces
    def face(self, points, key, along=None, smooth=False, uvs=None):
        pts = [Vector(p) for p in points]
        normal = Vector((0, 0, 0))
        for i in range(1, len(pts) - 1):
            normal += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0])
        if normal.length < 1e-10:
            raise ValueError(f'{self.name}: degenerate face {points}')
        normal.normalize()
        if uvs is None:
            material, uvs = self._island(pts, normal, key, along)
        else:
            material = self.palette[key][0]
        part = self.part
        base = len(part.vertices)
        part.vertices.extend(p - part.pivot for p in pts)
        part.faces.append(tuple(range(base, base + len(pts))))
        part.uvs.append([tuple(uv) for uv in uvs])
        part.materials.append(material)
        part.smooth.append(smooth)

    def poly(self, points, key, normal, along=None, smooth=False):
        """Planar polygon wound to face `normal`."""
        pts = [Vector(p) for p in points]
        n = Vector((0, 0, 0))
        for i in range(1, len(pts) - 1):
            n += (pts[i] - pts[0]).cross(pts[i + 1] - pts[0])
        if n.dot(Vector(normal)) < 0:
            pts.reverse()
        self.face(pts, key, along, smooth)

    # ------------------------------------------------------------ solids
    def box(self, lo, hi, key, skip=(), top=None, along=None, keys=None):
        """Axis box from lo to hi. skip: subset of '-x','+x','-y','+y','-z','+z'.
        keys optionally maps a side to another palette key."""
        (x0, y0, z0), (x1, y1, z1) = lo, hi
        if x1 - x0 <= 0 or y1 - y0 <= 0 or z1 - z0 <= 0:
            raise ValueError(f'{self.name}: empty box {lo} {hi}')
        sides = {
            '-x': [(x0, y1, z0), (x0, y0, z0), (x0, y0, z1), (x0, y1, z1)],
            '+x': [(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)],
            '-y': [(x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)],
            '+y': [(x1, y1, z0), (x0, y1, z0), (x0, y1, z1), (x1, y1, z1)],
            '-z': [(x0, y1, z0), (x1, y1, z0), (x1, y0, z0), (x0, y0, z0)],
            '+z': [(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)],
        }
        for side, pts in sides.items():
            if side in skip:
                continue
            k = (keys or {}).get(side, top if side == '+z' and top else key)
            self.face(pts, k, along)

    def beam(self, p0, p1, width, height, key, up=(0, 0, 1), caps=True, cap_key=None):
        """Square-section member from p0 to p1 (centre line)."""
        a, b = Vector(p0), Vector(p1)
        d = (b - a)
        if d.length < 1e-6:
            raise ValueError(f'{self.name}: zero-length beam')
        d.normalize()
        u = Vector(up)
        if abs(u.dot(d)) > .95:
            u = Vector((1, 0, 0)) if abs(d.x) < .9 else Vector((0, 1, 0))
        side = d.cross(u).normalized() * (width / 2)
        upv = side.cross(d).normalized() * (height / 2)
        ring = [side + upv, -side + upv, -side - upv, side - upv]
        ra = [a + r for r in ring]
        rb = [b + r for r in ring]
        for i in range(4):
            j = (i + 1) % 4
            self.face([ra[i], rb[i], rb[j], ra[j]], key, along=d)
        if caps:
            self.poly(ra, cap_key or key, -d)
            self.poly(rb, cap_key or key, d)

    def cylinder(self, center, radius, z0, z1, key, sides=12, caps=(True, True), cap_key=None,
                 axis='z', radius1=None, smooth=True, cap_keys=None):
        """Prism/frustum along an axis. center is the axis point at the base
        (for axis 'x'/'y', z0/z1 are positions along that axis)."""
        r0, r1 = radius, radius if radius1 is None else radius1
        cx, cy, cz = center

        def point(r, t, i):
            ang = 2 * math.pi * (i + .5) / sides
            c, s = math.cos(ang) * r, math.sin(ang) * r
            if axis == 'z':
                return Vector((cx + c, cy + s, t))
            if axis == 'x':
                return Vector((t, cy + c, cz + s))
            return Vector((cx + c, t, cz + s))
        low = [point(r0, z0, i) for i in range(sides)]
        high = [point(r1, z1, i) for i in range(sides)]
        ax = Vector({'z': (0, 0, 1), 'x': (1, 0, 0), 'y': (0, 1, 0)}[axis]) * (1 if z1 > z0 else -1)
        base = point(0, z0, 0)
        for i in range(sides):
            j = (i + 1) % sides
            mid = (low[i] + low[j]) / 2 - base
            outward = mid - ax * mid.dot(ax)
            self.poly([low[i], low[j], high[j], high[i]], key, outward, along=high[i] - low[i],
                      smooth=smooth and sides > 6)
        bottom_key, top_key = cap_keys or (cap_key or key, cap_key or key)
        if caps[0] and r0 > 0:
            self.poly(low, bottom_key, -ax)
        if caps[1] and r1 > 0:
            self.poly(high, top_key, ax)

    def revolve(self, center, profile, key, sides=12, cap_top=None, smooth=True, keys=None, wobble=None):
        """Surface of revolution about a vertical axis through center (x, y):
        profile [(r, z), ...] from bottom to top. Optional per-band keys and
        wobble(ring, i) -> radius factor for natural, irregular forms."""
        cx, cy = center
        rings = []
        for ring, (r, z) in enumerate(profile):
            rings.append([Vector((cx + math.cos(2 * math.pi * (i + .5) / sides) * r * (wobble(ring, i) if wobble else 1),
                                  cy + math.sin(2 * math.pi * (i + .5) / sides) * r * (wobble(ring, i) if wobble else 1), z))
                          for i in range(sides)])
        for band in range(len(profile) - 1):
            k = keys[band] if keys else key
            (r0, z0), (r1, z1) = profile[band], profile[band + 1]
            for i in range(sides):
                j = (i + 1) % sides
                mid = (rings[band][i] + rings[band][j]) / 2
                radial = Vector((mid.x - cx, mid.y - cy, 0)).normalized()
                normal = radial * (z1 - z0) + Vector((0, 0, -(r1 - r0)))
                if r1 < 1e-6:
                    pts = [rings[band][i], rings[band][j], rings[band + 1][i]]
                elif r0 < 1e-6:
                    pts = [rings[band][i], rings[band + 1][j], rings[band + 1][i]]
                else:
                    pts = [rings[band][i], rings[band][j], rings[band + 1][j], rings[band + 1][i]]
                self.poly(pts, k, normal, smooth=smooth and abs(z1 - z0) > 1e-6)
        if cap_top and profile[-1][0] > 1e-6:
            self.poly(rings[-1], cap_top, (0, 0, 1))

    def roof_gable(self, x0, x1, y0, y1, z_eave, z_ridge, key, ridge_axis='x', thickness=.06, gable_key=None,
                   courses=2):
        """Gable roof slabs over [x0,x1]x[y0,y1] with the ridge along ridge_axis,
        mapped course by course onto the roof atlas. Gable triangles in gable_key."""
        if ridge_axis != 'x':
            raise ValueError('roof_gable authors x ridges; rotate the plan instead')
        ym = (y0 + y1) / 2
        for side, (ya, yb) in (('front', (y0, ym)), ('back', (y1, ym))):
            for c in range(courses):
                t0, t1 = c / courses, (c + 1) / courses
                yl, yh = ya + (yb - ya) * t0, ya + (yb - ya) * t1
                zl, zh = z_eave + (z_ridge - z_eave) * t0, z_eave + (z_ridge - z_eave) * t1
                quad = [(x0, yl, zl), (x1, yl, zl), (x1, yh, zh), (x0, yh, zh)]
                if side == 'back':
                    quad = [(x1, yl, zl), (x0, yl, zl), (x0, yh, zh), (x1, yh, zh)]
                self.roof_course(quad, key, c)
            # Underside and eave edge of the slab.
            under = [(x0, ya, z_eave - thickness), (x0, yb, z_ridge - thickness),
                     (x1, yb, z_ridge - thickness), (x1, ya, z_eave - thickness)]
            if side == 'back':
                under = [(x1, ya, z_eave - thickness), (x1, yb, z_ridge - thickness),
                         (x0, yb, z_ridge - thickness), (x0, ya, z_eave - thickness)]
            self.face(under, gable_key or 'frame')
            edge = [(x0, ya, z_eave - thickness), (x1, ya, z_eave - thickness), (x1, ya, z_eave), (x0, ya, z_eave)]
            if side == 'back':
                edge = [(x1, ya, z_eave - thickness), (x0, ya, z_eave - thickness), (x0, ya, z_eave), (x1, ya, z_eave)]
            self.face(edge, gable_key or 'frame')
            # Slab ends at both gables.
            for x, nx in ((x0, -1), (x1, 1)):
                self.poly([(x, ya, z_eave - thickness), (x, ya, z_eave), (x, yb, z_ridge), (x, yb, z_ridge - thickness)],
                          gable_key or 'frame', (nx, 0, 0))

    def roof_course(self, quad, key, row):
        """quad: lower-left, lower-right, upper-right, upper-left (seen from
        outside). Maps one roof course onto one atlas row: the fringe (low v)
        at the lower edge, u along the eave."""
        material, kind = self.palette[key][:2]
        if kind != 'roof':
            raise ValueError(f'{key} is not a roof key')
        p = [Vector(q) for q in quad]
        width = max((p[1] - p[0]).length, (p[2] - p[3]).length)
        v0, v1 = ROOF_ROWS[row % 4]
        span = min(1.0, width * .5)
        u0 = self.rng.random() * (1 - span)
        # Upper edge may be shorter (hip or cone): keep it centred.
        top_w = (p[2] - p[3]).length
        inset = (width - top_w) / 2 / width * span if width else 0
        uvs = [(u0, v0), (u0 + span, v0), (u0 + span - inset, v1), (u0 + inset, v1)]
        if (p[2] - p[3]).length < 1e-6:     # triangle course (cone apex)
            self.face([p[0], p[1], p[2]], key, uvs=[uvs[0], uvs[1], ((uvs[0][0] + uvs[1][0]) / 2, v1)])
            return
        self.face(p, key, uvs=uvs)

    def cone_roof(self, center, radius, z0, z1, key, sides=12, courses=2, rim=None):
        """Conical roof (thatch or plank) in courses, with an optional rim underside."""
        cx, cy = center
        for c in range(courses):
            t0, t1 = c / courses, (c + 1) / courses
            r0, r1 = radius * (1 - t0), radius * (1 - t1)
            za, zb = z0 + (z1 - z0) * t0, z0 + (z1 - z0) * t1
            for i in range(sides):
                a0, a1 = 2 * math.pi * (i + .5) / sides, 2 * math.pi * (i + 1.5) / sides
                q = [(cx + math.cos(a0) * r0, cy + math.sin(a0) * r0, za), (cx + math.cos(a1) * r0, cy + math.sin(a1) * r0, za),
                     (cx + math.cos(a1) * r1, cy + math.sin(a1) * r1, zb), (cx + math.cos(a0) * r1, cy + math.sin(a0) * r1, zb)]
                if r1 < 1e-6:
                    self.roof_course_tri([q[0], q[1], (cx, cy, zb)], key, c)
                else:
                    self.roof_course(q, key, c)
        if rim:
            ring = [(cx + math.cos(2 * math.pi * (i + .5) / sides) * radius,
                     cy + math.sin(2 * math.pi * (i + .5) / sides) * radius, z0 - .002) for i in range(sides)]
            self.face(list(reversed(ring)), rim)

    def roof_course_tri(self, tri, key, row):
        p = [Vector(q) for q in tri]
        width = (p[1] - p[0]).length
        v0, v1 = ROOF_ROWS[row % 4]
        span = min(1.0, width * .5)
        u0 = self.rng.random() * (1 - span)
        self.face(p, key, uvs=[(u0, v0), (u0 + span, v0), (u0 + span / 2, v1)])

    def disc(self, center, radius, z, key, sides=12, down=False):
        cx, cy = center
        ring = [Vector((cx + math.cos(2 * math.pi * (i + .5) / sides) * radius,
                        cy + math.sin(2 * math.pi * (i + .5) / sides) * radius, z)) for i in range(sides)]
        self.face(list(reversed(ring)) if down else ring, key)

    def hull(self, points, key, cut=None, smooth=False):
        """Faceted convex solid through the points (rocks); faces entirely at
        or below z=cut that face down are dropped (they sit in the ground).
        key may be a function (normal, points) -> palette key."""
        bm = bmesh.new()
        verts = [bm.verts.new(Vector(p)) for p in points]
        bmesh.ops.convex_hull(bm, input=verts)
        for v in [v for v in bm.verts if not v.link_faces]:
            bm.verts.remove(v)
        bm.normal_update()
        for f in bm.faces:
            pts = [v.co.copy() for v in f.verts]
            if cut is not None and f.normal.z < -.3 and max(p.z for p in pts) <= cut + 1e-6:
                continue
            k = key(f.normal.copy(), pts) if callable(key) else key
            self.poly(pts, k, f.normal.copy(), smooth=smooth)
        bm.free()

    # ------------------------------------------------------------ checks
    def triangles(self):
        return sum(len(f) - 2 for p in self.parts.values() for f in p.faces)

    def bounds(self):
        pts = [v + p.pivot for p in self.parts.values() for v in p.vertices]
        lo = Vector((min(v.x for v in pts), min(v.y for v in pts), min(v.z for v in pts)))
        hi = Vector((max(v.x for v in pts), max(v.y for v in pts), max(v.z for v in pts)))
        return lo, hi


def rock_points(rng, center, size, count=10, flat_bottom=0.0):
    """Points of a rough rounded boulder: jittered ellipsoid samples."""
    cx, cy, cz = center
    sx, sy, sz = size
    pts = []
    for i in range(count):
        th = 2 * math.pi * (i + rng.uniform(-.3, .3)) / count
        ph = rng.uniform(.1, .75) * math.pi / 2
        r = rng.uniform(.85, 1.0)
        pts.append((cx + math.cos(th) * math.cos(ph) * sx * r, cy + math.sin(th) * math.cos(ph) * sy * r,
                    max(cz + math.sin(ph) * sz * r, flat_bottom)))
    for i in range(5):
        th = 2 * math.pi * i / 5 + rng.uniform(-.3, .3)
        pts.append((cx + math.cos(th) * sx * .95, cy + math.sin(th) * sy * .95, flat_bottom))
    return pts
