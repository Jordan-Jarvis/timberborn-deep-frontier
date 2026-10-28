"""Build, check and render late-game building studies (art only, no game data).

Each building is authored in its own module `lategame_<Ident>.py`, which must
define:

    IDENT        exact template name, e.g. 'NuclearReactor'
    FOOTPRINT    (X, Y) whole tiles; geometry must stay inside 0..X, 0..Y
    HEIGHT       whole-layer vertical envelope; geometry must stay below it
    HERO         one sentence naming the building's unique silhouette element
    FRAME_END    loop length in frames at 30 fps (121 recommended)
    FPS          optional; 24 when using native CompactWaterWheel props (use FRAME_END 301)
    build(g, parts)  author static geometry into `g` and append animated parts
                     as (Geometry, kind, value) tuples; see ANIMATION_KINDS.

Optional: `animate(obj, kind, value, frame_end)` for custom kinds that start
with 'CUSTOM_'.

The scene saves as src/DeepFrontier/Art/Source/<Ident>-ReferenceStudy.blend with
collection <Ident>.ReferenceStudy, so `zfight_audit.py --models <Ident>` checks
it. Renders and metadata go to outputs/lategame-studies/.

Run:
  blender.exe -b --factory-startup --python-exit-code 1 --python \
      tools/asset-pipeline/render_lategame_studies.py -- --models NuclearReactor \
      --views front,front-right,rear
"""
import argparse
import importlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector, Quaternion

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from frontier_architecture import Geometry
from reference_materials import create_reference_materials, civic_native_materials
from industrial_facades import extra_materials
from native_building_assets import build_native_assembly

ANIMATION_KINDS = ('STATIC', 'SPIN_X', 'SPIN_Y', 'SPIN_Z', 'PISTON_X', 'PISTON_Y', 'PISTON_Z',
                   'SLIDE_X', 'SLIDE_Y', 'SLIDE_Z', 'SWAY_X', 'SWAY_Y', 'FLAME', 'PULSE')
VIEWS = {'front': (7, 9, 6.2), 'front-right': (-7, 9, 6.2), 'back-left': (7, -9, 6.2),
         'rear': (-7, -9, 6.5), 'low': (7, 9, 2.6), 'top-angle': (5, 6.5, 11)}


def _linear(obj):
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'LINEAR'


def _smooth(obj):
    for curve in obj.animation_data.action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = 'BEZIER'


def animate(obj, kind, value, frame_end, module):
    """Keyframe one authored part. Loops close exactly at frame_end."""
    span = frame_end - 1
    if kind == 'STATIC':
        return
    if kind.startswith('CUSTOM_'):
        if not hasattr(module, 'animate'):
            raise ValueError(f'{kind} requires module.animate')
        module.animate(obj, kind, value, frame_end)
        return
    axis = kind[-1]
    # Artwork X/Y map to Blender -X/-Y (Geometry.add); Z is unchanged.
    sign = {'X': -1, 'Y': -1, 'Z': 1}.get(axis, 1)
    index = 'XYZ'.index(axis) if axis in 'XYZ' else None
    if kind.startswith('SPIN_'):
        obj.rotation_mode = 'QUATERNION'
        vector = {'X': (-1, 0, 0), 'Y': (0, -1, 0), 'Z': (0, 0, 1)}[axis]
        steps = max(8, int(abs(value) * 16))
        for k in range(steps + 1):
            frame = 1 + span * k / steps
            obj.rotation_quaternion = Quaternion(vector, value * 2 * math.pi * k / steps)
            obj.keyframe_insert(data_path='rotation_quaternion', frame=frame)
        _linear(obj)
    elif kind.startswith('PISTON_'):
        base = obj.location[index]
        for frame, t in ((1, 0), (1 + span * .25, 1), (1 + span * .5, 0), (1 + span * .75, 1), (frame_end, 0)):
            obj.location[index] = base + sign * value * t
            obj.keyframe_insert(data_path='location', index=index, frame=frame)
        _smooth(obj)
    elif kind.startswith('SLIDE_'):
        base = obj.location[index]
        for frame, t in ((1, 0), (1 + span * .4, 1), (1 + span * .5, 1), (1 + span * .9, 0), (frame_end, 0)):
            obj.location[index] = base + sign * value * t
            obj.keyframe_insert(data_path='location', index=index, frame=frame)
        _smooth(obj)
    elif kind.startswith('SWAY_'):
        obj.rotation_mode = 'XYZ'
        i = 'XY'.index(axis)
        for frame, t in ((1, -1), (1 + span * .25, 0), (1 + span * .5, 1), (1 + span * .75, 0), (frame_end, -1)):
            obj.rotation_euler[i] = value * t
            obj.keyframe_insert(data_path='rotation_euler', index=i, frame=frame)
        _smooth(obj)
    elif kind == 'FLAME':
        values = [1, .81, 1.12, .92, 1.05, .87]
        frames = [1 + span * k / 12 for k in range(13)]
        for k, frame in enumerate(frames):
            v = values[(k + int(value)) % 6] if k < 12 else values[int(value) % 6]
            obj.scale = (1 + (1 - v) * .22, 1 + (1 - v) * .16, v)
            obj.keyframe_insert(data_path='scale', frame=frame)
        _linear(obj)
    elif kind == 'PULSE':
        for frame, t in ((1, 0), (1 + span * .5, 1), (frame_end, 0)):
            s = 1 + value * t
            obj.scale = (s, s, s)
            obj.keyframe_insert(data_path='scale', frame=frame)
        _smooth(obj)
    else:
        raise ValueError('Unknown animation kind ' + kind)


EXTRA_NATIVE = ('PaintedMetal.IronTeeth', 'BaseWood_Grey.IronTeeth', 'IrregularPlanks_Grey.IronTeeth')


def palette():
    """32-slot civic/research palette plus three further shipped materials."""
    from native_building_assets import native_material
    materials = create_reference_materials('kiln')
    materials.extend(extra_materials())
    materials = civic_native_materials(materials)
    if len(materials) != 32:
        raise ValueError('Late-game studies require the 32-slot native palette')
    materials.extend(native_material(name) for name in EXTRA_NATIVE)
    return materials


def atlas_rectangle(slot, index):
    """Bounded islands on the shipped atlases for slots 32-34 (same layouts as
    the proven PaintedMetal/BaseWood/IrregularPlanks rectangles)."""
    strip = index % 8
    if slot == 32:
        row = (index // 8) % 4
        return (strip / 16 + .003, (strip + 1) / 16 - .003, row / 4 + .018, (row + 1) / 4 - .018)
    if slot == 33:
        return (strip / 16 + .004, (strip + 1) / 16 - .004, .012, .488)
    if slot == 34:
        return (strip / 8 + .008, (strip + 1) / 8 - .008, .012, .988)
    raise ValueError(f'No late-game atlas rectangle for slot {slot}')


def author_extra_native_uvs(obj):
    mesh = obj.data
    uv = mesh.uv_layers['UVMap']
    for poly in mesh.polygons:
        if poly.material_index < 32:
            continue
        points = [mesh.vertices[i].co for i in poly.vertices]
        edges = [points[(i + 1) % len(points)] - p for i, p in enumerate(points)]
        along = max(edges, key=lambda e: e.length_squared).normalized()
        across = poly.normal.cross(along).normalized()
        coords = [(p.dot(across), p.dot(along)) for p in points]
        lo = [min(c[i] for c in coords) for i in range(2)]
        span = [max(c[i] for c in coords) - lo[i] for i in range(2)]
        if min(span) < 1e-8:
            raise ValueError(f'Degenerate native surface {obj.name}/{poly.index}')
        if poly.material_index == 32:
            # PaintedMetal.IronTeeth is a tileable corrugated sheet (8 rib
            # pairs across the texture). Map whole ribs at ~4 per tile so
            # every panel shows real corrugation, never a lone strip.
            ribs = max(1, round(span[0] / .25))
            u0, u1, v0, v1 = 0, ribs / 8, 0, max(.25, span[1] / 2)
        else:
            u0, u1, v0, v1 = atlas_rectangle(poly.material_index, poly.index)
        for loop, (u, v) in zip(poly.loop_indices, coords, strict=True):
            uv.data[loop].uv = (u0 + (u - lo[0]) / span[0] * (u1 - u0), v0 + (v - lo[1]) / span[1] * (v1 - v0))


BEVEL_MIN_EDGE = .5               # only edges at least this long keep the softened bevel
BEVEL_MIN_FACE = .1               # ...between faces at least this deep
CULL_ENCLOSED = True              # drop faces enclosed by solid primitives
SMOOTH_ANGLE = math.radians(37)   # 10+ sided round parts shade smooth (and are not
                                  # bevelled between facets); boxes stay crisp


def budget_shading(obj):
    """Triangle budget (outputs/triangle-budget/): the game keeps several
    copies of every placement-preview mesh, so geometry pays for itself only
    where it shows at game zoom.

    - The authored 1.2 cm softened-edge bevel stays on long edges (building
      masses, slabs, roof edges), where it catches light. On edges shorter
      than BEVEL_MIN_EDGE (bolts, rungs, small pipes) or along members
      thinner than BEVEL_MIN_FACE (beams, ribs, rails) it is under two
      pixels at the closest zoom and only multiplied the triangles.
    - Faces are smooth-shaded with edges sharper than SMOOTH_ANGLE kept
      sharp, so round parts read as round with half the sides and boxes keep
      flat faces; the bevel marks its own edges sharp so slabs stay flat.
    """
    mesh = obj.data
    weights = mesh.attributes.get('bevel_weight_edge')
    if weights is not None:
        faces = {}
        for poly in mesh.polygons:
            for key in poly.edge_keys:
                faces.setdefault(key, []).append(poly)
        for edge in mesh.edges:
            if not weights.data[edge.index].value:
                continue
            a, b = (mesh.vertices[i].co for i in edge.vertices)
            axis = (b - a).normalized()
            # Depth of each adjoining face away from the edge: thin members
            # (beams, ribs, rails under BEVEL_MIN_FACE) keep crisp edges.
            depth = min(max(((mesh.vertices[i].co - a) - axis * (mesh.vertices[i].co - a).dot(axis)).length
                            for i in poly.vertices) for poly in faces[edge.key])
            pair = faces[edge.key]
            curved = len(pair) == 2 and pair[0].normal.angle(pair[1].normal) < SMOOTH_ANGLE
            if (a - b).length < BEVEL_MIN_EDGE or depth < BEVEL_MIN_FACE or curved:
                weights.data[edge.index].value = 0
    mesh.shade_smooth()
    mesh.set_sharp_from_angle(angle=SMOOTH_ANGLE)
    for modifier in obj.modifiers:
        if modifier.type == 'BEVEL':
            modifier.mark_sharp = True
    return obj


def check_materials(ident, geometries):
    """Surfaces must use shipped game materials; emissive accents stay tiny."""
    from lategame_kit import NATIVE_SLOTS, ACCENT_SLOTS
    used = {}
    for geo in geometries:
        for m in geo.materials:
            used[m] = used.get(m, 0) + 1
    bad = sorted(m for m in used if m not in NATIVE_SLOTS and m not in ACCENT_SLOTS)
    if bad:
        raise ValueError(f'{ident}: non-native material slots used: {bad}. Use lategame_kit NATIVE_SLOTS.')
    total = sum(used.values())
    accent = sum(used.get(m, 0) for m in ACCENT_SLOTS)
    if accent > .04 * total:
        raise ValueError(f'{ident}: emissive accents cover {accent}/{total} faces; keep them under 4%')
    return {NATIVE_SLOTS.get(m, f'accent{m}'): n for m, n in sorted(used.items())}


def clear_scene():
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for c in list(bpy.data.collections):
        bpy.data.collections.remove(c)
    for mesh in list(bpy.data.meshes):
        bpy.data.meshes.remove(mesh)
    for material in list(bpy.data.materials):
        bpy.data.materials.remove(material)
    for action in list(bpy.data.actions):
        bpy.data.actions.remove(action)


def import_redic_props(static, collection, frame_end):
    """Preview REDIC New Building Styles props from the installed dependency."""
    from lategame_kit import REDIC_ROOT
    from native_building_assets import import_prop
    animated = []
    for definition in getattr(static, 'lategame_props', []):
        path = Path(REDIC_ROOT) / definition['resource']
        mesh_file = Path(str(path) + '.timbermesh')
        if not mesh_file.is_file():
            raise FileNotFoundError(mesh_file)
        # import_prop joins its cache with the model path; an absolute path
        # replaces the cache root, so the installed file is read in place.
        local = dict(definition, model=str(path))
        try:
            animated += import_prop(local, collection, frame_end, vertex_colors=True)
        except ValueError as error:
            if 'vertex-color' not in str(error):
                raise
            for obj in [o for o in collection.objects if o.name.startswith(definition['name'])]:
                bpy.data.objects.remove(obj)
            animated += import_prop(local, collection, frame_end, vertex_colors=False)
    return animated



OCCUPANCY_INSET = .15  # a part must reach 15 cm into a cell to occupy it
DOOR_WALL_PROUD = .3   # wall-mounted parts this close to a door face leave its path cell free
WALL_DEPTH = .12       # a wall's skin lies within this of the cell face
WALL_COVER = .6        # share of a cell face the wall must cover


def record_extents():
    """Record each Geometry.add call's artwork-space extent while a module
    builds. Occupancy is derived from these authored parts, so solid interiors
    (tanks, plinths, rooms) count even though they have no inner faces."""
    original = Geometry.add

    def add(self, vertices, faces, mat):
        pts = list(vertices)
        if pts:
            lo = tuple(min(p[i] for p in pts) for i in range(3))
            hi = tuple(max(p[i] for p in pts) for i in range(3))
            self.__dict__.setdefault('_extents', []).append((lo, hi))
        return original(self, vertices, faces, mat)
    Geometry.add = add
    return original


def registration(module, geometries, doorways):
    """Native grid registration derived from the authored art.

    Occupied cells: any authored part reaching OCCUPANCY_INSET into the cell.
    Ground doors: the doorstep is the cell behind the door face and the native
    Entrance is the path cell in front (vanilla convention). A door face more
    than 0.25 tiles from that cell boundary is rejected: the path stub would
    stop visibly short of the door. Parts on the door's own wall standing at
    most DOOR_WALL_PROUD in front of it (the native jamb, wall lamps) overhang
    the path and do not occupy its cell.
    """
    fx, fy = module.FOOTPRINT
    fz = int(math.ceil(module.HEIGHT))
    doors = []
    for d in doorways:
        x, y, z = d['position']
        ox, oy = d.get('outward', [0, -1])
        if z != int(z) or (ox, oy) not in ((0, -1), (0, 1), (-1, 0), (1, 0)):
            raise ValueError(f'{module.IDENT}: door {d.get("id")} is not a whole-layer, axis-aligned door')
        along, across = (x, y) if ox == 0 else (y, x)
        normal = oy if ox == 0 else ox
        if abs(along % 1 - .5) > .01:
            raise ValueError(f'{module.IDENT}: door {d.get("id")} is not centred on a tile ({along})')
        if normal < 0:
            step = math.floor(across + 1e-6); offset = across - step
        else:
            step = math.ceil(across - 1e-6) - 1; offset = step + 1 - across
        cell_along = math.floor(along)
        doorstep = (cell_along, step, int(z)) if ox == 0 else (step, cell_along, int(z))
        entrance = (doorstep[0] + ox, doorstep[1] + oy, int(z))
        doors.append({'id': d.get('id'), 'position': [x, y, z], 'outward': [ox, oy],
                      'doorstep': list(doorstep), 'entrance': list(entrance), 'faceOffset': round(offset, 4)})

    def wall_mounted(cell, lo, hi):
        for d in doors:
            if tuple(d['entrance']) != cell:
                continue
            ox, oy = d['outward']
            axis, normal = (1, oy) if ox == 0 else (0, ox)
            face = d['position'][axis]
            proud = face - lo[axis] if normal < 0 else hi[axis] - face
            if proud <= DOOR_WALL_PROUD:
                return True
        return False

    occupied = set()
    outside = 0
    for geo in geometries:
        for lo, hi in geo.__dict__.get('_extents', []):
            x0, y0, z0 = (math.floor(round(lo[i] + OCCUPANCY_INSET, 6)) for i in range(3))
            x1, y1, z1 = (math.ceil(round(hi[i] - OCCUPANCY_INSET, 6)) - 1 for i in range(3))
            for z in range(max(0, z0), min(fz - 1, z1) + 1):
                for y in range(max(0, y0), min(fy - 1, y1) + 1):
                    for x in range(max(0, x0), min(fx - 1, x1) + 1):
                        if not wall_mounted((x, y, z), lo, hi):
                            occupied.add((x, y, z))
            if lo[0] < -.06 or lo[1] < -.06 or hi[0] > fx + .06 or hi[1] > fy + .06:
                outside += 1
    # Wall faces: a horizontal face of an occupied cell toward open space is a
    # wall when authored parts within WALL_DEPTH of its plane cover at least
    # WALL_COVER of it (4×4 samples). Shafts are only offered on these.
    extents = [e for geo in geometries for e in geo.__dict__.get('_extents', [])]
    samples = [(i + .5) / 4 for i in range(4)]
    wall_faces = []
    for x, y, z in sorted(occupied):
        for axis, step, name in ((0, -1, 'Left'), (0, 1, 'Right'), (1, -1, 'Down'), (1, 1, 'Up')):
            neighbour = [x, y, z]
            neighbour[axis] += step
            if tuple(neighbour) in occupied:
                continue
            plane = (x, y)[axis] + (1 if step > 0 else 0)
            other = 1 - axis
            base = (x, y)[other]
            near = [(lo, hi) for lo, hi in extents
                    if (hi[axis] >= plane - WALL_DEPTH and lo[axis] <= plane + .02 if step > 0
                        else lo[axis] <= plane + WALL_DEPTH and hi[axis] >= plane - .02)]
            covered = sum(any(lo[other] <= base + u <= hi[other] and lo[2] <= z + v <= hi[2] for lo, hi in near)
                          for u in samples for v in samples)
            if covered >= WALL_COVER * 16:
                wall_faces.append([x, y, z, name])
    return {'footprint': [fx, fy], 'height': fz, 'occupied': sorted(list(c) for c in occupied),
            'partsOutsideFootprint': outside, 'doors': doors, 'wallFaces': wall_faces}


def smoke_emitters(module, static, parts):
    """Vanilla smoke/steam emitters recorded by lategame_kit.emitter (and
    kit stacks) on the static art: kind, mouth position in artwork
    coordinates (x, y across the footprint, z up) and mouth radius.
    tools/vanilla_smoke.mjs attaches the shipped particle prefabs there.
    Emitters on animated parts would leave their plume behind; rejected.
    Emitters add no geometry, so they never affect the saved .blend."""
    for geo, kind, _ in parts:
        if geo.__dict__.get('emitters'):
            raise ValueError(f'{module.IDENT}: emitter on animated part {geo.name}; record it on the static art')
    fx, fy = module.FOOTPRINT
    for e in static.__dict__.get('emitters', []):
        x, y, z = e['position']
        if not (0 <= x <= fx and 0 <= y <= fy and 0 < z <= module.HEIGHT + .02):
            raise ValueError(f'{module.IDENT}: {e["kind"]} emitter {e["position"]} lies outside the '
                             f'{fx}x{fy}x{module.HEIGHT} envelope')
    return list(static.__dict__.get('emitters', []))


def apply_grid_origin(module, static, parts):
    """Optional module GRID_ORIGIN = (dx, dy): the artwork point that becomes
    the footprint's (0, 0) corner. Modules keep authoring in their original
    artwork coordinates; after build() every authored record moves by
    (-dx, -dy) so the footprint starts at the grid origin. Used where yards,
    aprons and props in front of or beside the walls were removed and the
    footprint now ends at the walls. Whole tiles only (the grid rule)."""
    dx, dy = getattr(module, 'GRID_ORIGIN', (0, 0))
    if (dx, dy) == (0, 0):
        return
    if dx != int(dx) or dy != int(dy):
        raise ValueError(f'{module.IDENT}: GRID_ORIGIN {dx, dy} must be whole tiles')
    shift = lambda p: [p[0] - dx, p[1] - dy] + list(p[2:])
    for geo in [static] + [g for g, _, _ in parts]:
        if tuple(geo.origin) == (0, 0, 0):
            # Mesh coordinates are (-x, -y, z) of the artwork.
            geo.vertices = [(x + dx, y + dy, z) for x, y, z in geo.vertices]
            for v in geo.hidden_volumes:
                v['lo'] = (v['lo'][0] + dx, v['lo'][1] + dy, v['lo'][2])
                v['hi'] = (v['hi'][0] + dx, v['hi'][1] + dy, v['hi'][2])
        else:
            geo.origin = Vector((geo.origin.x - dx, geo.origin.y - dy, geo.origin.z))
        geo.__dict__['_extents'] = [(tuple(shift(lo)), tuple(shift(hi))) for lo, hi in geo.__dict__.get('_extents', [])]
        for record in geo.doorways + geo.native_props + geo.__dict__.get('lategame_props', []) + \
                geo.__dict__.get('emitters', []):
            record['position'] = [round(v, 6) for v in shift(record['position'])]
        for surface in geo.liquid_surfaces:
            surface['center'] = shift(surface['center'])
        if geo.visitor_seats:
            raise ValueError(f'{module.IDENT}: GRID_ORIGIN does not move visitor seats')


def build_model(ident):
    module = importlib.import_module('lategame_' + ident)
    for attr in ('IDENT', 'FOOTPRINT', 'HEIGHT', 'HERO', 'FRAME_END', 'build'):
        if not hasattr(module, attr):
            raise ValueError(f'lategame_{ident} is missing {attr}')
    if module.IDENT != ident:
        raise ValueError('Module IDENT mismatch')
    clear_scene()
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = module.FRAME_END
    # Native animated props (e.g. CompactWaterWheel at 24 fps) need their clip rate.
    scene.render.fps = getattr(module, 'FPS', 30)
    materials = palette()
    model = bpy.data.collections.new(ident + '.ReferenceStudy')
    scene.collection.children.link(model)
    static = Geometry(ident + '.Architecture')
    parts = []
    original_add = record_extents()
    try:
        module.build(static, parts)
    finally:
        Geometry.add = original_add
    apply_grid_origin(module, static, parts)
    static.registration = registration(module, [static] + [geo for geo, _, _ in parts], static.doorways)
    static.registration['smokeEmitters'] = smoke_emitters(module, static, parts)
    material_use = check_materials(ident, [static] + [geo for geo, _, _ in parts])
    # Faces buried inside solid primitives of the same part are never seen
    # (frontier_architecture enclosed-face cull, proved by
    # audit_hidden_geometry.py --culled against the saved scene).
    static.cull_enclosed = CULL_ENCLOSED
    author_extra_native_uvs(budget_shading(static.build(model, materials, .012, 'research-native')))
    names = set()
    animated = []
    for geo, kind, value in parts:
        if kind not in ANIMATION_KINDS and not kind.startswith('CUSTOM_'):
            raise ValueError(f'{ident}: unknown animation kind {kind}')
        if geo.name in names:
            raise ValueError(f'{ident}: duplicate part name {geo.name}')
        names.add(geo.name)
        geo.cull_enclosed = CULL_ENCLOSED
        obj = budget_shading(geo.build(model, materials, .006, 'research-native'))
        author_extra_native_uvs(obj)
        animate(obj, kind, value, module.FRAME_END, module)
        if kind != 'STATIC':
            animated.append(geo.name)
    native_animated = build_native_assembly(static, model, module.FRAME_END)
    native_animated += import_redic_props(static, model, module.FRAME_END)
    if len(animated) + len(native_animated) < 2:
        raise ValueError(f'{ident}: late-game buildings need at least two animated parts')
    scene.frame_set(1)
    bpy.context.view_layer.update()
    # Bounds in artwork coordinates (Blender x,y are negated).
    lo = Vector((1e9, 1e9, 1e9))
    hi = Vector((-1e9, -1e9, -1e9))
    for frame in (1, 1 + (module.FRAME_END - 1) // 4, 1 + (module.FRAME_END - 1) // 2,
                  1 + 3 * (module.FRAME_END - 1) // 4):
        scene.frame_set(frame)
        graph = bpy.context.evaluated_depsgraph_get()
        for o in model.all_objects:
            if o.type != 'MESH':
                continue
            for corner in o.evaluated_get(graph).bound_box:
                w = o.matrix_world @ Vector(corner)
                a = Vector((-w.x, -w.y, w.z))
                lo = Vector(tuple(min(lo[i], a[i]) for i in range(3)))
                hi = Vector(tuple(max(hi[i], a[i]) for i in range(3)))
    scene.frame_set(1)
    fx, fy = module.FOOTPRINT
    # Small facade details (lamps, plaques, door frames) may overhang the
    # footprint edge as on vanilla buildings; structure may not. The native
    # Barrack door portal stands 0.25 proud of a wall on the footprint edge.
    tol = .3
    problems = []
    if lo.x < -tol or lo.y < -tol or hi.x > fx + tol or hi.y > fy + tol:
        problems.append(f'outside footprint {module.FOOTPRINT}: x {lo.x:.2f}..{hi.x:.2f}, y {lo.y:.2f}..{hi.y:.2f}')
    if lo.z < -.06:
        problems.append(f'below ground: z min {lo.z:.2f}')
    if hi.z > module.HEIGHT + .02:
        problems.append(f'above HEIGHT {module.HEIGHT}: z max {hi.z:.2f}')
    if not static.doorways:
        problems.append('no doorway recorded in g.doorways')
    for d in static.doorways:
        x, y, z = d['position']
        if z != int(z) or abs((x % 1) - .5) > .01:
            problems.append(f'door {d.get("id")} not centred on a tile at a whole layer: {d["position"]}')
    if problems:
        raise ValueError(f'{ident} envelope check failed: ' + '; '.join(problems))
    static.material_use = material_use
    return module, model, static, animated + native_animated, lo, hi


def setup_render(cli):
    scene = bpy.context.scene
    scene.world.color = (.28, .28, .28)
    scene.view_settings.view_transform = 'AgX'
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = cli.samples
    scene.cycles.use_denoising = True
    scene.cycles.transparent_max_bounces = 32
    prefs = bpy.context.preferences.addons['cycles'].preferences
    prefs.compute_device_type = 'OPTIX'
    prefs.get_devices()
    required = [d for d in prefs.devices if d.type == 'OPTIX' and d.name == 'NVIDIA GeForce RTX 2060']
    if len(required) != 1:
        raise RuntimeError('Required RTX 2060 OptiX render device is unavailable')
    for device in prefs.devices:
        device.use = device in required
    scene.cycles.device = 'GPU'
    scene.render.resolution_x = scene.render.resolution_y = cli.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'


def studio(low, high):
    """Camera, lights and ground in a separate collection (never exported)."""
    scene = bpy.context.scene
    rig = bpy.data.collections.new('Studio')
    scene.collection.children.link(rig)

    def move(o):
        for c in list(o.users_collection):
            c.objects.unlink(o)
        rig.objects.link(o)
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    move(camera)
    scene.camera = camera
    camera.data.type = 'ORTHO'
    # Blender-space centre (artwork x/y negated).
    center = Vector((-(low.x + high.x) / 2, -(low.y + high.y) / 2, (low.z + high.z) / 2))
    for p, energy, size in [((1, 2, 14), 2600, 8), ((-12, 1, 10), 1400, 7), ((-7, -13, 13), 2300, 7)]:
        bpy.ops.object.light_add(type='AREA', location=center + Vector(p))
        light = bpy.context.object
        move(light)
        light.data.energy = energy
        light.data.size = size
        light.rotation_euler = (center - light.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=300, location=(0, 0, -.04))
    ground = bpy.context.object
    move(ground)
    mat = bpy.data.materials.new('Studio warm grey')
    mat.use_nodes = True
    mat.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = (.18, .165, .135, 1)
    mat.node_tree.nodes['Principled BSDF'].inputs['Roughness'].default_value = .9
    ground.data.materials.append(mat)
    # Tile grid on the ground, studio only, so footprints read in review.
    return rig, camera, center


def render_views(ident, cli, camera, center, low, high):
    scene = bpy.context.scene
    extent = max(high - low)
    out = cli.output_dir
    target = Vector((center.x, center.y, center.z * .85))
    for view in cli.views.split(','):
        if view not in VIEWS:
            raise ValueError('Unknown view ' + view)
        scene.frame_set(1)
        camera.location = target + Vector(VIEWS[view])
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = extent * 1.32
        scene.render.filepath = str(out / f'{ident}-{view}.png')
        bpy.ops.render.render(write_still=True)
        print('LATEGAME STUDY RENDERED', ident, view, flush=True)


def render_culled(ident, cli, camera, center, low, high):
    """Workbench render with back-face culling: wrong winding shows as holes."""
    scene = bpy.context.scene
    engine = scene.render.engine
    scene.render.engine = 'BLENDER_WORKBENCH'
    shading = scene.display.shading
    shading.light = 'STUDIO'
    shading.color_type = 'MATERIAL'
    shading.show_backface_culling = True
    shading.show_cavity = True
    shading.show_shadows = False
    extent = max(high - low)
    target = Vector((center.x, center.y, center.z * .85))
    for view in ('front', 'rear'):
        camera.location = target + Vector(VIEWS[view])
        camera.rotation_euler = (target - camera.location).to_track_quat('-Z', 'Y').to_euler()
        camera.data.ortho_scale = extent * 1.32
        scene.render.filepath = str(cli.output_dir / f'{ident}-culled-{view}.png')
        bpy.ops.render.render(write_still=True)
    scene.render.engine = engine


def source_hash(ident, harness=True):
    """Hash of every source that shapes this study: its module, the shared
    kit and helpers, and this harness. Unchanged hash = nothing to rebuild.
    harness=False is the artwork alone (registration-only reruns)."""
    import hashlib
    here = Path(__file__).parent
    names = sorted({f'lategame_{ident}.py', 'lategame_kit.py', 'native_window_atlas.py',
                    *(['render_lategame_studies.py'] if harness else []),
                    'frontier_architecture.py', 'architectural_windows.py',
                    'industrial_facades.py', 'reference_details.py', 'native_building_assets.py'}
                   | {p.name for p in here.glob('lategame_*_parts.py')})
    digest = hashlib.sha256()
    for name in names:
        path = here / name
        if path.is_file():
            digest.update(name.encode() + b'|' + path.read_bytes())
    return digest.hexdigest()


def up_to_date(ident, cli):
    study = cli.output_dir / f'{ident}-study.json'
    if not study.is_file():
        return False
    try:
        recorded = json.loads(study.read_text()).get('sourceHash')
    except ValueError:
        return False
    views = [] if cli.save_only else cli.views.split(',')
    images = all((cli.output_dir / f'{ident}-{v}.png').is_file() for v in views)
    blend = (ROOT / f'src/DeepFrontier/Art/Source/{ident}-ReferenceStudy.blend').is_file()
    return recorded == source_hash(ident) and images and blend


def native_assembly(ident, static):
    """Runtime prop list: shipped native props plus dependency (REDIC) props.
    Dependency props record their mod and the installed model file, so
    validators read the actual mesh rather than guessing its location."""
    from lategame_kit import REDIC_ROOT
    props = list(static.native_props)
    for p in getattr(static, 'lategame_props', []):
        source = Path(REDIC_ROOT) / (p['resource'] + '.timbermesh')
        if not source.is_file():
            raise ValueError(f'{ident}: dependency model missing: {source}')
        props.append(dict(name=p['name'], model=p['model'], resource=p['resource'], position=p['position'],
                          scale=p['scale'], yaw=p['yaw'], dependency=p['dependency'], sourceFile=source.as_posix()))
    (ROOT / f'outputs/reference-studies/{ident}-native-assembly.json').write_text(json.dumps({
        'scope': 'Late-game study; runtime references the original shipped or dependency resources',
        'props': props, 'liquids': []}, indent=2) + '\n')


def registration_only(ident, cli):
    """Rewrite <Ident>-registration.json from the module source alone (no
    scene). Only valid while the saved study was built from this same source:
    the exporter pairs the registration with that .blend."""
    study = json.loads((cli.output_dir / f'{ident}-study.json').read_text())
    if study.get('artHash') != source_hash(ident, harness=False):
        raise ValueError(f'{ident}: artwork changed since the saved study; rebuild it instead')
    module = importlib.import_module('lategame_' + ident)
    static = Geometry(ident + '.Architecture')
    parts = []
    original_add = record_extents()
    try:
        module.build(static, parts)
    finally:
        Geometry.add = original_add
    apply_grid_origin(module, static, parts)
    animated = [geo.name for geo, kind, _ in parts if kind != 'STATIC']
    # The saved list continues with animated nodes imported from native props.
    if animated != study['animatedParts'][:len(animated)]:
        raise ValueError(f'{ident}: animated parts differ from the saved study')
    animated = study['animatedParts']
    reg = registration(module, [static] + [geo for geo, _, _ in parts], static.doorways)
    reg['smokeEmitters'] = smoke_emitters(module, static, parts)
    (cli.output_dir / f'{ident}-registration.json').write_text(json.dumps(dict(
        reg, ident=ident, frameEnd=module.FRAME_END, fps=getattr(module, 'FPS', 30),
        animatedParts=animated, sourceHash=study['sourceHash']), indent=1) + '\n')
    native_assembly(ident, static)
    print('LATEGAME REGISTRATION', ident, flush=True)


def run(ident, cli):
    if cli.registration_only:
        registration_only(ident, cli)
        return
    if cli.skip_unchanged and up_to_date(ident, cli):
        print('LATEGAME STUDY UNCHANGED; SKIPPED', ident, flush=True)
        return
    module, model, static, animated, low, high = build_model(ident)
    out = cli.output_dir
    out.mkdir(parents=True, exist_ok=True)
    (out / f'{ident}-study.json').write_text(json.dumps({
        'status': 'Blender late-game art study; not exported or installed',
        'hero': module.HERO, 'footprint': list(module.FOOTPRINT), 'heightLayers': module.HEIGHT,
        'boundsMin': [round(v, 4) for v in low], 'boundsMax': [round(v, 4) for v in high],
        'doors': static.doorways, 'animatedParts': animated,
        'animationFrames': module.FRAME_END, 'animationFps': getattr(module, 'FPS', 30),
        'nativeProps': static.native_props,
        'redicProps': getattr(static, 'lategame_props', []),
        'faces': len(static.faces), 'materialFaces': static.material_use,
        'sourceHash': source_hash(ident), 'artHash': source_hash(ident, harness=False),
    }, indent=2) + '\n')
    # Grid registration and native props for game integration (see
    # lategame_building_content.mjs). Preview water exports as static native
    # Water surfaces, so the runtime assembly lists props only.
    (out / f'{ident}-registration.json').write_text(json.dumps(dict(
        static.registration, ident=ident, frameEnd=module.FRAME_END, fps=getattr(module, 'FPS', 30),
        animatedParts=animated, sourceHash=source_hash(ident)), indent=1) + '\n')
    native_assembly(ident, static)
    # The studio rig is always saved so zfight_audit.py --render has a camera.
    rig, camera, center = studio(low, high)
    if not cli.save_only:
        setup_render(cli)
        render_views(ident, cli, camera, center, low, high)
        if cli.culled:
            render_culled(ident, cli, camera, center, low, high)
    blend = ROOT / f'src/DeepFrontier/Art/Source/{ident}-ReferenceStudy.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    print('LATEGAME STUDY SAVED', ident, blend, 'faces', len(static.faces), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    parser.add_argument('--views', default='front,front-right,rear')
    parser.add_argument('--resolution', type=int, default=1200)
    parser.add_argument('--samples', type=int, default=64)
    parser.add_argument('--save-only', action='store_true')
    parser.add_argument('--culled', action='store_true', help='Also render back-face-culled diagnostics')
    parser.add_argument('--skip-unchanged', action='store_true',
                        help='Skip a model whose sources are unchanged since its last saved study and renders')
    parser.add_argument('--registration-only', action='store_true',
                        help='Rewrite grid registrations from unchanged sources without building the scene')
    parser.add_argument('--output-dir', type=Path, default=ROOT / 'outputs/lategame-studies')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    for ident in cli.models.split(','):
        run(ident, cli)


if __name__ == '__main__':
    main()
