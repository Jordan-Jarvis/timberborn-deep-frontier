"""Measure triangles that no game camera can see, per object and per source line.

Reads a saved source scene (frame 1, evaluated modifiers) and counts, for the
geometry the exporter ships (native preview props and preview liquids are
excluded), the triangles that are not visible from any orbit-camera direction.

A triangle counts as visible when, for at least one direction d of the orbit
set (elevations ELEVATIONS, AZIMUTHS azimuths; the game camera never looks from
below), the triangle faces d (back faces are culled by the native shaders) and
a ray from one of its sample points towards the camera reaches open sky. A hit
occludes only when the camera sees that face's front (dot(n, d) > 0): a
single-sided facade seen from behind is culled in game, so the ray continues
through it. Animated parts, water and native props never occlude (they move
or are transparent), so the count is conservative.

The rays run on the RTX 2060 (gpu_visibility.py) in the persistent GPU
visibility service (gpu_visibility_service.py: one warm Blender takes the jobs
of every agent; this script's command line submits to it and starts it when
needed). gpu_visibility.py reproduces the
mathutils BVHTree ray casts this audit used, ray for ray: see that module for
the exact test. A ray exactly along a seam between two triangles can slip
between them (the BVH's box culling of grazing rays), so an escape counts only
when two rays offset 0.1 mm sideways escape too.

Optional terrain: --terrain-z Z adds an opaque ground plane at scene height Z
for land buildings (parts below it are buried). Without it, nothing below the
building counts as hidden by ground.

Sampling is discrete (centroid plus three inner points per triangle), so this
is a measurement and a guide to the producing source lines, not proof that a
given face may be deleted. Producing generators must remove geometry by
construction (shells, not solids).

Run: blender -b --python-exit-code 1 --python audit_hidden_geometry.py --
         --models A,B [--terrain-z 0] [--out DIR]
"""
import argparse
import json
import math
import sys
import time
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).parent))
from enclosed_cull import FACING  # noqa: E402
import gpu_visibility  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ELEVATIONS = (12, 30, 48, 66, 84)
AZIMUTHS = 16
STUDIES = {'GroceryStore': 'GroceryMarket'}
F32 = np.float32


def directions():
    out = []
    for e in ELEVATIONS:
        for i in range(AZIMUTHS):
            a = 2 * math.pi * (i + .5 * (e // 18 % 2)) / AZIMUTHS
            ce = math.cos(math.radians(e))
            out.append(Vector((ce * math.cos(a), ce * math.sin(a), math.sin(math.radians(e)))))
    return out


def animated(obj):
    while obj is not None:
        if obj.animation_data and obj.animation_data.action:
            return True
        obj = obj.parent
    return False


def triangles(obj, deps):
    ev = obj.evaluated_get(deps)
    mesh = ev.to_mesh()
    mesh.calc_loop_triangles()
    n = len(mesh.loop_triangles)
    co = np.empty(len(mesh.vertices) * 3)
    mesh.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3)
    tri = np.empty(n * 3, dtype=np.int64)
    mesh.loop_triangles.foreach_get('vertices', tri)
    tri = tri.reshape(-1, 3)
    poly = np.empty(n, dtype=np.int64)
    mesh.loop_triangles.foreach_get('polygon_index', poly)
    mat = np.empty(len(mesh.polygons), dtype=np.int64)
    mesh.polygons.foreach_get('material_index', mat)
    names = [m.name if m else '' for m in mesh.materials]
    source = None
    if 'df_source' in mesh.attributes and mesh.attributes['df_source'].domain == 'FACE':
        values = np.empty(len(mesh.polygons), dtype=np.int64)
        mesh.attributes['df_source'].data.foreach_get('value', values)
        source = values[poly]
    m = np.array(ev.matrix_world)
    world = co @ m[:3, :3].T + m[:3, 3]
    ev.to_mesh_clear()
    return world, tri, [names[i] if i < len(names) else '' for i in mat[poly]], source


def check_culled(collection, scene, dirs, table):
    """Every face removed by enclosed_cull.py (sidecar written at build) must
    stay occluded from every camera direction in this saved scene. Samples:
    centroid, inner points and corners pulled 5% towards the centroid."""
    folder = ROOT / 'outputs/triangle-budget/culled'
    checked, exposed, examples = 0, 0, []
    # one GPU batch per occluder scene: the static scene and each moving part
    batches = {id(scene): (scene, [])}
    for obj in collection.all_objects:
        path = folder / (obj.name + '.json')
        if obj.type != 'MESH' or 'df_enclosed_culled' not in obj or not path.is_file():
            continue
        record = json.loads(path.read_text(encoding='utf-8'))
        if record['object'] != obj.name or len(record['polygons']) != obj['df_enclosed_culled']:
            raise SystemExit(f'{obj.name}: culled-face sidecar does not belong to this build')
        m = obj.matrix_world
        tree = scene
        if animated(obj):
            # A moving part is culled only against its own solids, which move
            # with it: check it against itself.
            world, tri, _, _ = triangles(obj, bpy.context.evaluated_depsgraph_get())
            tree = gpu_visibility.Scene(world, tri)
        faces = []
        for polygon in record['polygons']:
            pts = [m @ Vector(p) for p in polygon]
            n = Vector((0, 0, 0))
            for i, p in enumerate(pts):
                q = pts[(i + 1) % len(pts)]
                n += Vector(((p.y - q.y) * (p.z + q.z), (p.z - q.z) * (p.x + q.x), (p.x - q.x) * (p.y + q.y)))
            if n.length < 1e-12:
                continue
            n.normalize()
            c = sum(pts, Vector((0, 0, 0))) / len(pts)
            samples = [c] + [c + (p - c) * .95 for p in pts] + [c + (p - c) * .5 for p in pts]
            checked += 1
            base = [tuple(sample + n * 2e-4) for sample in samples]
            points, dir_index = [], []
            for k, d in enumerate(dirs):
                if n.dot(d) <= FACING:
                    continue
                points += base
                dir_index += [k] * len(base)
            faces.append((obj.name, m, c, points, dir_index))
        batches.setdefault(id(tree), (tree, []))[1].extend(faces)
    for tree, faces in batches.values():
        points = [p for face in faces for p in face[3]]
        dir_index = [k for face in faces for k in face[4]]
        seen = tree.escapes(np.array(points, dtype=F32).reshape(-1, 3), np.array(dir_index, dtype=np.int64), table)
        at = 0
        for name, m, c, face_points, _ in faces:
            if seen[at:at + len(face_points)].any():
                exposed += 1
                if len(examples) < 20:
                    examples.append({'object': name, 'centroid': [round(v, 3) for v in (m.inverted() @ c)]})
            at += len(face_points)
    return {'culledFacesChecked': checked, 'culledFacesExposed': exposed, 'exposedExamples': examples}


def study_of(ident):
    return STUDIES.get(ident, ident)


def hidden_triangles(scene, meshes, dirs_np, table):
    """For each (world, tri) mesh, per triangle: no sample sees open sky along
    any orbit direction it faces. All meshes go to the GPU in one batch."""
    rays_tri, rays_dir, rays_base, offsets = [], [], [], [0]
    for world, tri in meshes:
        a, b, c = world[tri[:, 0]], world[tri[:, 1]], world[tri[:, 2]]
        normal = np.cross(b - a, c - a)
        area2 = np.linalg.norm(normal, axis=1)
        unit = normal / np.maximum(area2, 1e-30)[:, None]
        centroid = (a + b + c) / 3
        facing = unit @ dirs_np.T > FACING
        facing[area2 < 1e-14] = False          # degenerate: never rasterised
        # centroid, then three inner points unless the triangle is tiny
        samples = np.stack([centroid, .5 * (centroid + a), .5 * (centroid + b), .5 * (centroid + c)], 1)
        count = np.where(area2 < 1e-5, 1, 4)
        # float32 exactly as mathutils computes Vector(s) + n * 2e-4
        base = samples.astype(F32) + unit.astype(F32)[:, None, :] * F32(2e-4)
        t_idx, k_idx = np.nonzero(facing)
        s_count = count[t_idx]
        reps = np.repeat(np.arange(len(t_idx)), s_count)
        s_idx = np.arange(len(reps)) - np.repeat(np.cumsum(s_count) - s_count, s_count)
        rays_tri.append(t_idx[reps] + offsets[-1])
        rays_dir.append(k_idx[reps])
        rays_base.append(base[t_idx[reps], s_idx])
        offsets.append(offsets[-1] + len(tri))
    if not meshes:
        return []
    ray_tri = np.concatenate(rays_tri)
    seen_ray = scene.escapes(np.concatenate(rays_base), np.concatenate(rays_dir), table)
    seen = np.zeros(offsets[-1], dtype=bool)
    seen[ray_tri[seen_ray]] = True
    return [~seen[offsets[i]:offsets[i + 1]] for i in range(len(meshes))]


def audit(ident, terrain_z, blend_dir=None):
    study = study_of(ident)
    path = Path(blend_dir or ROOT / 'src/DeepFrontier/Art/Source') / f'{study}-ReferenceStudy.blend'
    bpy.ops.wm.open_mainfile(filepath=str(path))
    bpy.context.scene.frame_set(1)
    deps = bpy.context.evaluated_depsgraph_get()
    collection = bpy.data.collections[study + '.ReferenceStudy']
    shipped, occluders = [], []
    native_tris = 0
    for obj in collection.all_objects:
        if obj.type != 'MESH':
            continue
        if 'native_resource' in obj:
            native_tris += len(triangles(obj, deps)[1])
            continue
        if 'liquid_surface' in obj:
            continue
        world, tri, mats, source = triangles(obj, deps)
        moving = animated(obj)
        shipped.append((obj, world, tri, mats, source, moving))
        if not moving:
            keep = np.array([name != 'Water' for name in mats], dtype=bool)
            if keep.any():
                occluders.append((world, tri[keep]))
    verts, polys, base = [], [], 0
    for world, tri in occluders:
        verts.append(world)
        polys.append(tri + base)
        base += len(world)
    if terrain_z is not None:
        lo = min(w[:, :2].min(axis=0).min() for _, w, *_ in shipped) - 200
        hi = max(w[:, :2].max(axis=0).max() for _, w, *_ in shipped) + 200
        verts.append(np.array([[lo, lo, terrain_z], [hi, lo, terrain_z], [hi, hi, terrain_z], [lo, hi, terrain_z]]))
        polys.append(np.array([[base, base + 1, base + 2], [base, base + 2, base + 3]]))
        base += 4
    allv = np.vstack(verts)
    allp = np.vstack(polys)
    scene = gpu_visibility.Scene(allv, allp)
    dirs = directions()
    dirs_np = np.array([tuple(d) for d in dirs])
    table = gpu_visibility.direction_table(dirs)
    started = time.time()
    objects = []
    total = hidden_total = 0
    by_source = {}
    static = iter(hidden_triangles(scene, [(world, tri) for _, world, tri, _, _, moving in shipped if not moving], dirs_np, table))
    for obj, world, tri, mats, source, moving in shipped:
        sources = json.loads(obj.get('df_source_locations', '[]'))
        hidden = np.zeros(len(tri), dtype=bool) if moving else next(static)
        count = int(hidden.sum())
        total += len(tri)
        hidden_total += count
        per = {}
        if source is not None and count:
            for sid, h in zip(source.tolist(), hidden.tolist()):
                key = sources[sid] if 0 <= sid < len(sources) else f'#{sid}'
                row = per.setdefault(key, [0, 0])
                row[0] += 1
                row[1] += h
        elif source is not None:
            for sid in source.tolist():
                key = sources[sid] if 0 <= sid < len(sources) else f'#{sid}'
                per.setdefault(key, [0, 0])[0] += 1
        for key, (t, h) in per.items():
            row = by_source.setdefault(key, [0, 0])
            row[0] += t
            row[1] += h
        hidden_mats = {}
        for name, h in zip(mats, hidden.tolist()):
            if h:
                hidden_mats[name] = hidden_mats.get(name, 0) + 1
        objects.append({'name': obj.name, 'animated': moving, 'triangles': len(tri), 'hidden': count,
                        'hiddenByMaterial': dict(sorted(hidden_mats.items(), key=lambda kv: -kv[1]))})
    culled = check_culled(collection, scene, dirs, table)
    report = {
        **culled,
        'model': ident, 'study': study, 'source': str(path).replace('\\', '/'),
        'method': f'orbit ray visibility, elevations {list(ELEVATIONS)} deg x {AZIMUTHS} azimuths, back faces culled, '
                  f'animated/water/native props never occlude, terrain plane {terrain_z}',
        'shippedTriangles': total, 'hiddenTriangles': hidden_total,
        'hiddenShare': round(hidden_total / total, 4) if total else 0,
        'nativePreviewTriangles': native_tris, 'seconds': round(time.time() - started, 1),
        'objects': sorted(objects, key=lambda o: -o['hidden']),
        'sources': [{'source': k, 'triangles': t, 'hidden': h}
                    for k, (t, h) in sorted(by_source.items(), key=lambda kv: -kv[1][1]) if t][:400],
    }
    return report


def run():
    """The audit itself; runs inside the GPU visibility service."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', required=True)
    parser.add_argument('--terrain-z', type=float, default=None)
    parser.add_argument('--out', default=str(ROOT / 'outputs/triangle-budget/hidden'))
    parser.add_argument('--blend-dir', default=None, help='read <Study>-ReferenceStudy.blend from here (e.g. a saved before copy)')
    cli = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    out = Path(cli.out)
    out.mkdir(parents=True, exist_ok=True)
    gpu_visibility.init_gpu()
    failed = False
    for ident in cli.models.split(','):
        report = audit(ident, cli.terrain_z, cli.blend_dir)
        (out / f'{ident}.json').write_text(json.dumps(report, indent=1) + '\n', encoding='utf-8')
        print('HIDDEN', json.dumps({k: report[k] for k in ('model', 'shippedTriangles', 'hiddenTriangles', 'hiddenShare', 'seconds',
                                                           'culledFacesChecked', 'culledFacesExposed')}), flush=True)
        if report['culledFacesExposed']:
            failed = True
    if failed:
        raise SystemExit('Enclosed-face cull exposed faces a camera can see (see culledFacesExposed)')


def main():
    """Client: the job runs in the warm GPU visibility service
    (gpu_visibility_service.py), which this starts when it is not running."""
    import gpu_visibility_service
    gpu_visibility_service.submit(__file__, 'run', sys.argv[sys.argv.index('--') + 1:])


if __name__ == '__main__':
    main()
