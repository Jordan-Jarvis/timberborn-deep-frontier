"""Orbit-camera ray visibility on the GPU (RTX 2060, OpenGL compute shader).

Reproduces, ray for ray, the CPU test the visibility audits used with
mathutils.bvhtree.BVHTree (audit_hidden_geometry.escapes, enclosed_cull.visible):

    origin = point + d * 2e-4
    escapes(origin) and escapes(origin + side) and escapes(origin + up)
    escapes(o): up to 64 times: nearest hit along d (BVHTree.ray_cast, max 500);
        none -> open sky; the hit face's front faces the camera (n.d > 0) ->
        blocked; a front face within 2e-5 of the hit point (find_nearest_range)
        -> blocked; else continue from hit + d * 2e-4. 64 hits -> blocked.

The arithmetic follows Blender's single-precision code paths exactly:
mathutils float32 vectors, the normalised ray direction (normalize_v3),
isect_ray_tri_watertight_v3 with its precalculated shear (computed here in
numpy float32, IEEE like the CPU), normal_tri_v3 for the hit normal and
closest_on_tri_to_point_v3 for the range test. GLSL `precise` forbids fused
multiply-adds, and the two divisions done on the GPU are corrected to the
IEEE-rounded quotient. The BVH only prunes (boxes are grown by 1 mm), so it
never changes which triangle a ray hits.

The GPU context: Blender's gpu module refuses to run in background mode
until the GPU is initialised; a 4x4 Workbench render of a temporary scene
initialises it. The renderer must be the RTX 2060; anything else fails.
"""
import math

import bpy
import numpy as np
from mathutils import Vector

import gpu_render_lock

REQUIRED_RENDERER = 'NVIDIA GeForce RTX 2060'
TEX_W = 4096
CHUNK = 1 << 20          # rays per dispatch (keeps each dispatch well under the driver watchdog)
LEAF = 4                 # triangles per BVH leaf
BOX_GROW = 1e-3          # BVH boxes only prune; growing them never changes a result
STACK = 128              # traversal stack per ray; the builder keeps the tree shallower
SAH_DEPTH = 48           # below this depth splits are median splits, so depth stays < STACK
F32 = np.float32

_shader = None


def init_gpu():
    import gpu
    try:
        gpu.platform.renderer_get()
    except SystemError:
        scene = bpy.data.scenes.new('gpu_visibility_init')
        camera = bpy.data.objects.new('gpu_visibility_init', bpy.data.cameras.new('gpu_visibility_init'))
        scene.collection.objects.link(camera)
        scene.camera = camera
        scene.render.engine = 'BLENDER_WORKBENCH'
        scene.render.resolution_x = scene.render.resolution_y = 4
        bpy.ops.render.render(scene=scene.name)
        data = camera.data
        bpy.data.objects.remove(camera)
        bpy.data.cameras.remove(data)
        bpy.data.scenes.remove(scene)
    renderer = gpu.platform.renderer_get()
    if not renderer.startswith(REQUIRED_RENDERER):
        raise RuntimeError(f'GPU visibility needs the {REQUIRED_RENDERER}; the OpenGL renderer is {renderer}')
    return gpu


SHADER = r'''
#define BIG 1e30
vec4 fetch(sampler2D s, int i) { return texelFetch(s, ivec2(i % TEXW, i / TEXW), 0); }

/* IEEE-rounded a / b: GLSL division may be approximate. One residual
   correction (exact with fma) gives the correctly rounded quotient. */
float div_rn(float a, float b) {
  precise float q = a / b;
  precise float r = fma(-q, b, a);
  precise float q2 = fma(r, 1.0 / b, q);
  /* pick the closer of q and q2 by their residuals */
  precise float r2 = fma(-q2, b, a);
  return abs(r2) < abs(r) ? q2 : q;
}

struct Dir { vec3 dn; vec3 d; vec3 d2; vec3 side; vec3 up; vec3 s; ivec3 k; vec3 idot; };

Dir load_dir(int k) {
  Dir r;
  vec4 a = texelFetch(dirs, ivec2(0, k), 0);
  vec4 b = texelFetch(dirs, ivec2(1, k), 0);
  vec4 c = texelFetch(dirs, ivec2(2, k), 0);
  vec4 e = texelFetch(dirs, ivec2(3, k), 0);
  vec4 f = texelFetch(dirs, ivec2(4, k), 0);
  vec4 g = texelFetch(dirs, ivec2(5, k), 0);
  r.idot = texelFetch(dirs, ivec2(6, k), 0).xyz;
  r.dn = a.xyz; r.d = b.xyz; r.d2 = c.xyz; r.side = e.xyz; r.up = f.xyz; r.s = g.xyz;
  int kbits = int(g.w);
  r.k = ivec3(kbits & 3, (kbits >> 2) & 3, (kbits >> 4) & 3);
  return r;
}

/* Entry distance of the ray into a node box, or BIG when it misses or
   enters beyond tmax. Boxes are grown by BOX_GROW, which covers the
   approximate divisions here; the box test only prunes. */
float box_entry(int node, vec3 o, vec3 dn, float tmax) {
  vec3 lo = fetch(nodes, 2 * node).xyz;
  vec3 hi = fetch(nodes, 2 * node + 1).xyz;
  float t0 = -BIG, t1 = BIG;
  for (int a = 0; a < 3; a++) {
    if (abs(dn[a]) < 1e-20) {
      if (o[a] < lo[a] || o[a] > hi[a]) return BIG;
    } else {
      float ta = (lo[a] - o[a]) / dn[a];
      float tb = (hi[a] - o[a]) / dn[a];
      t0 = max(t0, min(ta, tb));
      t1 = min(t1, max(ta, tb));
    }
  }
  if (t0 > t1 || t1 < -1e-3 || t0 > tmax + 1e-3) return BIG;
  return t0;
}

bool box_point(int node, vec3 p, float r) {
  vec3 lo = fetch(nodes, 2 * node).xyz - vec3(r);
  vec3 hi = fetch(nodes, 2 * node + 1).xyz + vec3(r);
  return all(greaterThanEqual(p, lo)) && all(lessThanEqual(p, hi));
}

/* isect_ray_tri_watertight_v3 (Blender math_geom.cc), with its precalc. */
bool isect_tri(vec3 o, Dir D, vec3 v0, vec3 v1, vec3 v2, out float lambda) {
  precise vec3 a = v0 - o;
  precise vec3 b = v1 - o;
  precise vec3 c = v2 - o;
  int kx = D.k.x, ky = D.k.y, kz = D.k.z;
  float sx = D.s.x, sy = D.s.y, sz = D.s.z;
  precise float ax = a[kx] - sx * a[kz];
  precise float ay = a[ky] - sy * a[kz];
  precise float bx = b[kx] - sx * b[kz];
  precise float by = b[ky] - sy * b[kz];
  precise float cx = c[kx] - sx * c[kz];
  precise float cy = c[ky] - sy * c[kz];
  precise float u = cx * by - cy * bx;
  precise float v = ax * cy - ay * cx;
  precise float w = bx * ay - by * ax;
  if ((u < 0.0 || v < 0.0 || w < 0.0) && (u > 0.0 || v > 0.0 || w > 0.0)) return false;
  precise float det = u + v + w;
  if (det == 0.0 || isinf(det) || isnan(det)) return false;
  precise float t = (u * a[kz] + v * b[kz] + w * c[kz]) * sz;
  /* sign_t = xor_fl(t, sign of det): t / det < 0 -> behind the origin */
  float sign_t = (det < 0.0) ? -t : t;
  if (sign_t < 0.0) return false;
  precise float inv_det = div_rn(1.0, det);
  lambda = t * inv_det;
  return true;
}

/* BLI_kdopbvh: the BVHTree's own box test of the triangle's leaf (its
   bounds grown by FLT_EPSILON, the tree epsilon floor of BLI_bvhtree_new)
   in fast_ray_nearest_hit, with the leaf skipped when it starts at or beyond
   the best hit (dfs_raycast). Direction components under FLT_EPSILON count
   as parallel (inverse FLT_MAX). Boxes nest, so testing only the leaf is
   exactly the tree's verdict. */
bool cpu_leaf_box(vec3 o, Dir D, vec3 v0, vec3 v1, vec3 v2, float best) {
  precise vec3 lo = min(min(v0, v1), v2) - vec3(FLT_EPS);
  precise vec3 hi = max(max(v0, v1), v2) + vec3(FLT_EPS);
  float t1[3], t2[3];
  for (int a = 0; a < 3; a++) {
    float near = D.idot[a] < 0.0 ? hi[a] : lo[a];
    float far = D.idot[a] < 0.0 ? lo[a] : hi[a];
    precise float n = near - o[a];
    precise float f = far - o[a];
    precise float tn = n * D.idot[a];
    precise float tf = f * D.idot[a];
    t1[a] = tn; t2[a] = tf;
  }
  if (t1[0] > t2[1] || t2[0] < t1[1] || t1[0] > t2[2] || t2[0] < t1[2] || t1[1] > t2[2] || t2[1] < t1[2]) return false;
  if (t2[0] < 0.0 || t2[1] < 0.0 || t2[2] < 0.0) return false;
  if (t1[0] > best || t1[1] > best || t1[2] > best) return false;
  float m = t1[0] > t1[1] ? t1[0] : t1[1];
  m = m > t1[2] ? m : t1[2];
  return !(m >= best);
}

vec3 tri_vertex(int t, int j) { return fetch(tris, 3 * t + j).xyz; }

/* normal_tri_v3 direction (not normalised: only its sign against d is used). */
vec3 tri_normal(int t) {
  precise vec3 v1 = tri_vertex(t, 0), v2 = tri_vertex(t, 1), v3 = tri_vertex(t, 2);
  precise vec3 n1 = v1 - v2;
  precise vec3 n2 = v2 - v3;
  precise vec3 n = vec3(n1.y * n2.z - n1.z * n2.y, n1.z * n2.x - n1.x * n2.z, n1.x * n2.y - n1.y * n2.x);
  return n;
}

float dot3(vec3 a, vec3 b) { precise float r = a.x * b.x + a.y * b.y + a.z * b.z; return r; }

/* closest_on_tri_to_point_v3 (Blender math_geom.cc, Ericson). */
vec3 closest_on_tri(vec3 p, vec3 v1, vec3 v2, vec3 v3) {
  precise vec3 ab = v2 - v1;
  precise vec3 ac = v3 - v1;
  precise vec3 ap = p - v1;
  precise float d1 = dot3(ab, ap);
  precise float d2 = dot3(ac, ap);
  if (d1 <= 0.0 && d2 <= 0.0) return v1;
  precise vec3 bp = p - v2;
  precise float d3 = dot3(ab, bp);
  precise float d4 = dot3(ac, bp);
  if (d3 >= 0.0 && d4 <= d3) return v2;
  precise float vc = d1 * d4 - d3 * d2;
  if (vc <= 0.0 && d1 >= 0.0 && d3 <= 0.0) {
    precise float v = div_rn(d1, d1 - d3);
    precise vec3 r = v1 + ab * v;
    return r;
  }
  precise vec3 cp = p - v3;
  precise float d5 = dot3(ab, cp);
  precise float d6 = dot3(ac, cp);
  if (d6 >= 0.0 && d5 <= d6) return v3;
  precise float vb = d5 * d2 - d1 * d6;
  if (vb <= 0.0 && d2 >= 0.0 && d6 <= 0.0) {
    precise float w = div_rn(d2, d2 - d6);
    precise vec3 r = v1 + ac * w;
    return r;
  }
  precise float va = d3 * d6 - d5 * d4;
  if (va <= 0.0 && (d4 - d3) >= 0.0 && (d5 - d6) >= 0.0) {
    precise float w = div_rn(d4 - d3, (d4 - d3) + (d5 - d6));
    precise vec3 r = (v3 - v2) * w;
    precise vec3 r2 = r + v2;
    return r2;
  }
  precise float denom = div_rn(1.0, va + vb + vc);
  precise float v = vb * denom;
  precise float w = vc * denom;
  precise vec3 acw = ac * w;
  precise vec3 r = v1 + ab * v;
  precise vec3 r2 = r + acw;
  return r2;
}

/* BVHTree.ray_cast: nearest triangle with 0 <= dist < 500. Nearer child
   first; a node is skipped only when its box starts beyond the best hit,
   which cannot hold a nearer triangle. */
int ray_cast(vec3 o, Dir D, out float best) {
  best = 500.0;
  int hit = -1;
  int stack[STACK];
  float entry[STACK];
  int sp = 0;
  if (box_entry(0, o, D.dn, best) < BIG) { stack[0] = 0; entry[0] = -BIG; sp = 1; }
  while (sp > 0) {
    sp--;
    int node = stack[sp];
    if (entry[sp] > best + 1e-3) continue;
    vec4 na = fetch(nodes, 2 * node), nb = fetch(nodes, 2 * node + 1);
    int a = int(na.w), b = int(nb.w);
    if (a < 0) {
      int first = -a - 1;
      for (int t = first; t < first + b; t++) {
        float lambda;
        vec3 v0 = tri_vertex(t, 0), v1 = tri_vertex(t, 1), v2 = tri_vertex(t, 2);
        if (cpu_leaf_box(o, D, v0, v1, v2, best) && isect_tri(o, D, v0, v1, v2, lambda)) {
          if (lambda >= 0.0 && lambda < best) { best = lambda; hit = t; }
        }
      }
    } else {
      int l = a, r = b;
      float tl = box_entry(l, o, D.dn, best), tr = box_entry(r, o, D.dn, best);
      if (tl > tr) { int x = l; l = r; r = x; float y = tl; tl = tr; tr = y; }
      if (tr < BIG) { stack[sp] = r; entry[sp] = tr; sp++; }
      if (tl < BIG) { stack[sp] = l; entry[sp] = tl; sp++; }
    }
  }
  return hit;
}

/* any(n.d > 0 for find_nearest_range(co, 2e-5)) */
bool front_face_near(vec3 co, Dir D) {
  int stack[STACK];
  int sp = 0;
  stack[sp++] = 0;
  while (sp > 0) {
    int node = stack[--sp];
    if (!box_point(node, co, RANGE)) continue;
    int a = int(fetch(nodes, 2 * node).w), b = int(fetch(nodes, 2 * node + 1).w);
    if (a < 0) {
      int first = -a - 1;
      for (int t = first; t < first + b; t++) {
        vec3 q = closest_on_tri(co, tri_vertex(t, 0), tri_vertex(t, 1), tri_vertex(t, 2));
        precise vec3 e = co - q;
        precise float dsq = e.x * e.x + e.y * e.y + e.z * e.z;
        if (dsq < range_sq && dot3(tri_normal(t), D.d) > 0.0) return true;
      }
    } else {
      stack[sp++] = b;
      stack[sp++] = a;
    }
  }
  return false;
}

bool escapes_one(vec3 o, Dir D) {
  for (int i = 0; i < 64; i++) {
    float dist;
    int t = ray_cast(o, D, dist);
    if (t < 0) return true;
    if (dot3(tri_normal(t), D.d) > 0.0) return false;
    precise vec3 co = o + D.dn * dist;
    if (front_face_near(co, D)) return false;
    precise vec3 next = co + D.d2;
    o = next;
  }
  return false;
}

void main() {
  int i = int(gl_GlobalInvocationID.x) + offset;
  if (i >= ray_count) return;
  vec4 r = fetch(rays, i);
  Dir D = load_dir(int(r.w));
  precise vec3 o = r.xyz + D.d2;
  bool seen = escapes_one(o, D);
  if (seen) { precise vec3 os = o + D.side; seen = escapes_one(os, D); }
  if (seen) { precise vec3 ou = o + D.up; seen = escapes_one(ou, D); }
  imageStore(result, ivec2(i % TEXW, i / TEXW), vec4(seen ? 1.0 : 0.0));
}
'''


def _get_shader(gpu):
    global _shader
    if _shader is None:
        info = gpu.types.GPUShaderCreateInfo()
        info.local_group_size(64, 1, 1)
        info.sampler(0, 'FLOAT_2D', 'nodes')
        info.sampler(1, 'FLOAT_2D', 'tris')
        info.sampler(2, 'FLOAT_2D', 'rays')
        info.sampler(3, 'FLOAT_2D', 'dirs')
        info.image(0, 'R32F', 'FLOAT_2D', 'result', qualifiers={'WRITE'})
        for name in ('offset', 'ray_count'):
            info.push_constant('INT', name)
        info.push_constant('FLOAT', 'range_sq')
        info.define('TEXW', str(TEX_W))
        info.define('LEAFN', str(LEAF))
        info.define('RANGE', '2.1e-5')
        info.define('FLT_EPS', '1.1920929e-07')
        info.define('STACK', str(STACK))
        info.compute_source(SHADER)
        _shader = gpu.shader.create_from_info(info)
    return _shader


def _texture(gpu, rows):
    """RGBA32F texture holding rows (n, 4) float32, TEX_W texels wide."""
    rows = np.ascontiguousarray(rows, dtype=F32)
    h = max(1, -(-len(rows) // TEX_W))
    flat = np.zeros((h * TEX_W, 4), dtype=F32)
    flat[:len(rows)] = rows
    return gpu.types.GPUTexture((TEX_W, h), format='RGBA32F', data=gpu.types.Buffer('FLOAT', flat.size, flat.ravel()))


def direction_table(dirs):
    """Per orbit direction, the exact float32 values the CPU test uses:
    dn = normalize_v3(d) (BVHTree.ray_cast normalises), d, d * 2e-4,
    the two 0.1 mm side offsets of audit_hidden_geometry.escapes, and the
    watertight shear precalc (kx, ky, kz, sx, sy, sz) of dn."""
    rows = []
    for d in dirs:
        d = Vector(d)
        a = np.array(tuple(d), dtype=F32)
        dd = F32(a[0] * a[0]) + F32(a[1] * a[1])
        dd = F32(dd + F32(a[2] * a[2]))
        if not dd > F32(1e-35):
            raise ValueError('zero direction')
        dn = a * F32(F32(1) / np.sqrt(dd))
        side = d.orthogonal().normalized() * 1e-4
        up = d.cross(side).normalized() * 1e-4
        ab = np.abs(dn)
        kz = (0 if ab[0] > ab[2] else 2) if ab[0] > ab[1] else (1 if ab[1] > ab[2] else 2)
        kx = kz + 1 if kz != 2 else 0
        ky = kx + 1 if kx != 2 else 0
        if dn[kz] < 0:
            kx, ky = ky, kx
        inv = F32(F32(1) / dn[kz])
        sx, sy = F32(dn[kx] * inv), F32(dn[ky] * inv)
        d2 = d * 2e-4
        # BLI_bvhtree_ray_cast: inverse direction per axis, FLT_MAX when parallel
        idot = [F32(3.4028235e38) if abs(c) < F32(1.1920929e-07) else F32(F32(1) / c) for c in dn]
        rows.append([[*dn, 0], [*tuple(d), 0], [*tuple(d2), 0], [*tuple(side), 0], [*tuple(up), 0],
                     [sx, sy, inv, kx | (ky << 2) | (kz << 4)], [*idot, 0]])
    return np.array(rows, dtype=F32)


def build_bvh(lo, hi):
    """Top-down full-sweep SAH BVH over triangle boxes (lo, hi: (m, 3)).
    Returns the triangle order and node texels: per node (lo.xyz, a),
    (hi.xyz, b); internal a, b = child node indices; leaf a = -(first + 1),
    b = triangle count. Boxes are grown by BOX_GROW: they only prune."""
    lo = lo.astype(np.float64)
    hi = hi.astype(np.float64)
    cen = (lo + hi) * .5
    m = len(lo)
    out_lo, out_hi, out_a, out_b = [], [], [], []
    order = []

    def new_node():
        out_lo.append(None); out_hi.append(None); out_a.append(0); out_b.append(0)
        return len(out_lo) - 1

    def area(l, h):
        d = np.maximum(h - l, 0)
        return d[..., 0] * d[..., 1] + d[..., 1] * d[..., 2] + d[..., 2] * d[..., 0]

    stack = [(np.arange(m), new_node(), 0)]
    deepest = 0
    while stack:
        idx, node, depth = stack.pop()
        deepest = max(deepest, depth)
        out_lo[node] = lo[idx].min(0)
        out_hi[node] = hi[idx].max(0)
        n = len(idx)
        if n <= LEAF:
            out_a[node] = -(len(order) + 1)
            out_b[node] = n
            order.extend(idx.tolist())
            continue
        best = (np.inf, None, None)
        if depth >= SAH_DEPTH or n <= 4 * LEAF:
            # small nodes: a median split is as good and far cheaper to build;
            # deep nodes: coincident boxes can make SAH peel one triangle per level
            axis = int(np.argmax(cen[idx].max(0) - cen[idx].min(0)))
            best = (0, idx[np.argsort(cen[idx, axis], kind='stable')], n // 2)
        for axis in (range(3) if best[1] is None else ()):
            s = idx[np.argsort(cen[idx, axis], kind='stable')]
            l_lo = np.minimum.accumulate(lo[s], 0)
            l_hi = np.maximum.accumulate(hi[s], 0)
            r_lo = np.minimum.accumulate(lo[s][::-1], 0)[::-1]
            r_hi = np.maximum.accumulate(hi[s][::-1], 0)[::-1]
            k = np.arange(1, n)
            cost = area(l_lo[:-1], l_hi[:-1]) * k + area(r_lo[1:], r_hi[1:]) * (n - k)
            i = int(np.argmin(cost))
            if cost[i] < best[0]:
                best = (cost[i], s, i + 1)
        _, s, split = best
        left, right = new_node(), new_node()
        out_a[node], out_b[node] = left, right
        stack.append((s[split:], right, depth + 1))
        stack.append((s[:split], left, depth + 1))
    if deepest + 2 >= STACK:
        raise ValueError(f'BVH depth {deepest} exceeds the traversal stack')
    count = len(out_lo)
    if count >= 1 << 24:
        raise ValueError('too many BVH nodes for float-encoded indices')
    nodes = np.zeros((2 * count, 4), dtype=F32)
    nodes[0::2, :3] = np.array(out_lo, dtype=F32) - F32(BOX_GROW)
    nodes[1::2, :3] = np.array(out_hi, dtype=F32) + F32(BOX_GROW)
    nodes[0::2, 3] = out_a
    nodes[1::2, 3] = out_b
    return np.array(order, dtype=np.int64), nodes


class Scene:
    """Static triangle soup on the GPU: vertices (n, 3) float, triangles (m, 3) int."""

    def __init__(self, vertices, triangles):
        self.gpu = init_gpu()
        v = np.asarray(vertices, dtype=F32)
        t = np.asarray(triangles, dtype=np.int64).reshape(-1, 3)
        tri = v[t]                                                    # (m, 3, 3) float32, as BVHTree stores them
        m = len(tri)
        if m == 0:
            raise ValueError('empty occluder set')
        if m >= 1 << 24:
            raise ValueError('too many triangles for float-encoded indices')
        order, nodes = build_bvh(tri.min(1), tri.max(1))
        tris = np.zeros((3 * m, 4), dtype=F32)
        tris[:, :3] = tri[order].reshape(-1, 3)
        self.order = order
        self.tri_count = m
        self.node_count = len(nodes) // 2
        self.nodes = _texture(self.gpu, nodes)
        self.tris = _texture(self.gpu, tris)

    def escapes(self, points, dir_index, dir_table):
        """For each ray: point (float32, = sample + n * 2e-4 as the CPU computes
        it) and orbit direction index. True where the sample sees open sky
        along that direction (all three offset rays escape)."""
        gpu = self.gpu
        points = np.asarray(points, dtype=F32).reshape(-1, 3)
        dir_index = np.asarray(dir_index, dtype=np.int64)
        n = len(points)
        if n == 0:
            return np.zeros(0, dtype=bool)
        rows = np.empty((n, 4), dtype=F32)
        rows[:, :3] = points
        rows[:, 3] = dir_index
        rays = _texture(gpu, rows)
        h = -(-n // TEX_W)
        dirs = gpu.types.GPUTexture((7, len(dir_table)), format='RGBA32F',
                                    data=gpu.types.Buffer('FLOAT', dir_table.size, np.ascontiguousarray(dir_table).ravel()))
        result = gpu.types.GPUTexture((TEX_W, h), format='R32F')
        shader = _get_shader(gpu)
        shader.bind()
        shader.uniform_sampler('nodes', self.nodes)
        shader.uniform_sampler('tris', self.tris)
        shader.uniform_sampler('rays', rays)
        shader.uniform_sampler('dirs', dirs)
        shader.image('result', result)
        shader.uniform_int('ray_count', n)
        r = F32(2e-5)
        shader.uniform_float('range_sq', float(F32(r * r)))
        # One GPU job at a time machine-wide (gpu_render_lock): waiting for
        # the lock costs no CPU, while time-slicing with a Cycles render
        # slows both and the driver spins a core for the whole wait.
        with gpu_render_lock.held():
            for offset in range(0, n, CHUNK):
                shader.uniform_int('offset', offset)
                gpu.compute.dispatch(shader, -(-min(CHUNK, n - offset) // 64), 1, 1)
            out = result.read()
        out.dimensions = h * TEX_W
        return np.frombuffer(out, dtype=np.float32)[:n] > 0.5
