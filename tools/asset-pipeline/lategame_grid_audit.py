"""Grid-alignment audit of late-game building studies (art only, no scene).

Runs each module's build() exactly as `render_lategame_studies.registration_only`
does, records every Geometry.add call with its artwork-space extent, shape and
the call stack that produced it, and reports three things per building:

(a) Footprint edges. Exposed vertical faces of ground masses (blocks, plinths,
    walls, decks, aprons, basins, kerbs) should sit on a tile boundary within
    EDGE_TOL. A face inset 0.06-0.4 from its outward boundary, or standing
    proud of it, is a miss. Faces in the door wall plane (deliberately 0.15
    off the edge for the door rule) and inside a door recess are exempt. Props,
    pipes, lamps, ladders, rails, windows, roofs and other small parts are
    exempt by the function that authored them or by size. Round masses (tanks,
    basins of revolution) are reported separately by their bounding tangents.

(b) Heights. Exposed flat tops of decks, platforms, catwalks, plinths and
    terraces that a beaver could stand on are floors and must sit on a whole
    layer within HEIGHT_TOL. Tops fully built over or enclosed by walls are
    wall bases (reported, not required to be whole). Tops ringed by a parapet
    are roof terraces (reported). Tops below PAVING_TOP are ground paving.

(c) Ground. Near-ground parts that should stand on something but have no
    support below them float; parts reaching more than GROUND_SINK below
    z = 0 sink.

Run (Blender only for its Python modules; no scene is built or saved):
  blender.exe -b --factory-startup --python-exit-code 1 --python \
      tools/asset-pipeline/lategame_grid_audit.py -- [--models A,B]

Writes outputs/lategame-grid-audit.json. Nothing is changed or repaired.
"""
import argparse
import importlib
import json
import math
import os
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))

import render_lategame_studies as H  # noqa: E402  (imports bpy; Blender only)
from frontier_architecture import Geometry, WOOD, PLANK, IRON, ROOF, BRASS  # noqa: E402
from lategame_kit import (GROUND_SINK, CONCRETE, ORANGE, FORGED, PAINTED, GREYWOOD, GREYPLANK,  # noqa: E402
                          WINDOW, GLOW, GLASS, CYAN)

EDGE_TOL = .03      # face on the tile boundary
NEAR_TOL = .06      # inset up to this is "near" (minor)
MISS_MAX = .40      # inset beyond this is a half-tile layout, reported for review
HEIGHT_TOL = .02
PAVING_TOP = .45    # tops below this read as ground paving inside layer 0
DOOR_PLANE_TOL = .04
MERGE_TOL = .04      # base courses and copings proud of their block
OVERLAP = .05        # cross-feature interpenetration reported as a diagnostic
MIN_FACE = .8       # shortest face that counts as a building edge
MIN_DEPTH = .08     # thinner parts are skins and trims
GROUND_TOP = .2     # a part whose bottom is at most this high meets the ground
CELL = 1.0

# Parts authored by these functions are props, fittings or roofing: never
# building edges or floors. Names are matched anywhere in the call stack.
PROP_FUNCS = {
    'lamp', 'lamp_post', 'ladder', 'pipe', 'pipe_run', 'pipe_path', 'straight_pipe', 'tube', 'flanged_pipe',
    'valve', 'valve_wheel', '_flat_wheel', 'gauge', 'beacon', 'beacon_shutter', 'trefoil', 'rivet', 'bolt_row',
    'bolt_ring', 'window', 'window_y', 'side_window', 'native_window', 'framed_window', 'facet_window',
    'atlas_window', 'glass_curtain', 'building_portal', 'building_portal_side', 'arched_portal', 'portal',
    'drum', 'barrel', 'cask', 'plant', 'prop', 'redic_prop', 'rail', 'steel_rail', 'ring_rail', 'grating_ring',
    'fan', 'motor', 'insulator', 'flywheel', 'pulley', 'hoop', 'knee', 'manipulator_port', 'hazard_stripes',
    'riveted_panel', 'cable_tray', 'band', 'elbow', 'pipe_flange', 'lit_window_slit', 'clock', 'spoked_wheel',
    'rotor', 'ore_cart', 'ore_heap', 'track', 'pipe_support', 'loop_belt', 'cowl', 'ball', 'wheel', 'beam',
    'obox', 'oriented_box', 'rock', 'stack', 'sphere', 'lattice_tower', 'lattice', 'portal_frame', 'louvre',
    'frame_wall_window', 'plate', 'ibeam', 'boards', 'face_member', 'pilasters', 'bracket', 'arc_bar',
    '_arc_bar', 'rocket', 'horizontal_vessel', 'h_tank', 'sphere_tank', 'gauge', 'raised_tank', 'hopper',
    # civic_wellbeing_parts / Bathhouse / TownPlaza / ObservationDeck
    'thermal_window', 'sweep', 'flagpole', 'lamp_standard', 'engineer_statue', '_ellipsoid', '_glass', 'column',
}
ROOF_FUNCS = {
    'plank_roof', 'plank_slope', 'gable_roof', 'plank_gable', 'barrel_roof', 'plank_barrel', 'plank_vault',
    'sawtooth_roof', 'sawtooth', 'flat_roof', 'parapet', 'ring_parapet', 'end_prism', 'board_gable',
    'boarded_gable', 'dome', 'slope_quad', 'pyramid_roof', 'hip_roof', 'mansard', 'lean_to', 'coping_ring',
    '_end_dome', 'arch_infill', 'octagon_frustum', 'groin_vault',
}
PARAPET_FUNCS = {'parapet', 'ring_parapet', 'coping_ring'}
WALK_FUNCS = {'catwalk', 'grating', 'annulus', 'deck', 'walk', 'slab', 'podium', 'plinth', 'plinth_course'}
ROUND_FUNCS = {'revolve', 'hollow_revolve', 'lathe', 'tank', 'cylinder', 'silo', 'octagon_frustum'}
MACHINE_MATS = {PAINTED, BRASS, GLOW, GLASS, CYAN, WINDOW}
# Hanging fittings: never expected to stand on anything.
HANGING_FUNCS = {
    'lamp', 'pipe', 'pipe_path', 'straight_pipe', 'tube', 'flanged_pipe', 'valve', 'gauge', 'beam', 'window',
    'native_window', 'framed_window', 'facet_window', 'rivet', 'bolt_row', 'bolt_ring', 'trefoil',
    'riveted_panel', 'hazard_stripes', 'manipulator_port', 'building_portal', 'motor', 'fan', 'hoop', 'band',
    'elbow', 'pipe_flange', 'cable_tray', 'insulator', 'knee', 'ladder', 'rail', 'steel_rail', 'ring_rail',
    'clock', 'native_piece', 'lit_window_slit', 'valve_wheel', 'beacon', 'wheel', 'ring', 'loop_belt',
    'pipe_support', 'bracket', 'thermal_window', 'sweep', '_glass',
} | ROOF_FUNCS


class Part:
    __slots__ = ('lo', 'hi', 'mat', 'box', 'funcs', 'where', 'line', 'geo', 'animated', 'idx', 'nfaces')

    def __init__(self, lo, hi, mat, box, funcs, where, line, geo):
        self.lo, self.hi, self.mat, self.box = lo, hi, mat, box
        self.funcs, self.where, self.line, self.geo = funcs, where, line, geo
        self.animated = False
        self.idx = 0

    @property
    def size(self):
        return tuple(self.hi[i] - self.lo[i] for i in range(3))

    def kind(self):
        if self.funcs & PROP_FUNCS:
            return 'prop'
        if self.funcs & ROOF_FUNCS:
            return 'roof'
        if not self.box or self.funcs & ROUND_FUNCS:
            return 'round' if self.funcs & ROUND_FUNCS else 'mesh'
        return 'box'


def record(module_file):
    """Patch Geometry.add to collect every authored part with its call stack."""
    parts = []
    original = Geometry.add
    study = os.path.basename(module_file)

    def add(self, vertices, faces, mat):
        pts = [tuple(p) for p in vertices]
        if pts:
            lo = tuple(min(p[i] for p in pts) for i in range(3))
            hi = tuple(max(p[i] for p in pts) for i in range(3))
            box = len(pts) == 8 and all(
                all(abs(p[i] - lo[i]) < 1e-6 or abs(p[i] - hi[i]) < 1e-6 for i in range(3)) for p in pts)
            chain = []
            line = None
            f = sys._getframe(1)
            while f is not None:
                base = os.path.basename(f.f_code.co_filename)
                name = f.f_code.co_name
                if name != 'add' or base != 'frontier_architecture.py':
                    chain.append(name)
                if base == study and line is None:
                    line = f.f_lineno
                if base == study and name == 'build':
                    break
                f = f.f_back
            chain.reverse()
            part = Part(lo, hi, mat, box, frozenset(chain), ' > '.join(chain), line, self.name)
            part.nfaces = len(faces)
            parts.append(part)
        return original(self, vertices, faces, mat)
    Geometry.add = add
    return parts, original


class Grid:
    """Spatial hash of parts by the tiles their footprint touches."""

    def __init__(self, parts):
        self.cells = defaultdict(list)
        for p in parts:
            for x in range(math.floor(p.lo[0]), math.floor(p.hi[0]) + 1):
                for y in range(math.floor(p.lo[1]), math.floor(p.hi[1]) + 1):
                    self.cells[(x, y)].append(p)

    def near(self, x, y):
        return self.cells.get((math.floor(x), math.floor(y)), ())

    def inside(self, pt, skip=None, pred=None):
        x, y, z = pt
        for p in self.near(x, y):
            if p is skip or (pred and not pred(p)):
                continue
            if p.lo[0] <= x <= p.hi[0] and p.lo[1] <= y <= p.hi[1] and p.lo[2] <= z <= p.hi[2]:
                return p
        return None


def door_planes(doorways):
    planes = []
    for d in doorways:
        x, y, z = d['position']
        ox, oy = d.get('outward', [0, -1])
        if ox == 0:
            planes.append(dict(axis=1, normal=oy, plane=y, along_axis=0, along=x, z=z, id=d.get('id')))
        else:
            planes.append(dict(axis=0, normal=ox, plane=x, along_axis=1, along=y, z=z, id=d.get('id')))
    return planes


def group(p):
    """The study-level feature a part belongs to (first function under build)."""
    chain = p.where.split(' > ')
    return chain[1] if len(chain) > 1 and chain[0] == 'build' else chain[0]


def classify_offset(plane, normal):
    """Inset of a face from its outward tile boundary (> 0) or proud of it (< 0)."""
    d = plane - round(plane)
    return d if normal < 0 else -d


def portal_boxes(parts):
    """Union boxes of every native portal (recorded or decorative)."""
    boxes = []
    for p in parts:
        if 'building_portal' not in p.funcs:
            continue
        for b in boxes:
            if all(p.lo[i] <= b[1][i] + .3 and p.hi[i] >= b[0][i] - .3 for i in range(3)):
                b[0] = [min(b[0][i], p.lo[i]) for i in range(3)]
                b[1] = [max(b[1][i], p.hi[i]) for i in range(3)]
                break
        else:
            boxes.append([list(p.lo), list(p.hi)])
    return boxes


def edge_audit(parts, grid, doors, footprint):
    portals = portal_boxes(parts)
    solid = [p for p in parts if p.kind() not in ('prop',) and not p.animated]
    # Single polygons (battered or sloped faces) have bounding-box sides that
    # are not faces; masses are boxes, rounds and closed meshes.
    masses = [p for p in solid if p.kind() in ('box', 'round', 'mesh') and p.lo[2] <= GROUND_TOP
              and p.size[2] >= .1 and p.mat not in MACHINE_MATS and p.nfaces > 1]
    faces = {}
    for p in masses:
        for axis in (0, 1):
            other = 1 - axis
            length = p.size[other]
            depth = p.size[axis]
            if length < MIN_FACE or depth < MIN_DEPTH:
                continue
            for normal, plane in ((-1, p.lo[axis]), (1, p.hi[axis])):
                # Door wall and door recess exemptions.
                door = None
                for d in doors:
                    if d['axis'] == axis and d['normal'] == normal and abs(plane - d['plane']) <= DOOR_PLANE_TOL:
                        door = 'door wall ' + str(d['id'])
                    if (d['axis'] == axis and d['along'] - .56 <= p.lo[other] and p.hi[other] <= d['along'] + .56
                            and -.05 <= (plane - d['plane']) * -d['normal'] <= 1.05 and p.lo[2] <= d['z'] + .1):
                        door = 'door recess ' + str(d['id'])
                # Decorative (unrecorded) portals: faces inside their notch.
                cx_, cy_ = [(p.lo[i] + p.hi[i]) / 2 for i in (0, 1)]
                fc = [cx_, cy_]
                fc[axis] = plane
                for lo_, hi_ in portals:
                    if (lo_[0] - .15 <= fc[0] <= hi_[0] + .15 and lo_[1] - .15 <= fc[1] <= hi_[1] + .15
                            and p.lo[2] < hi_[2] and p.hi[2] > lo_[2]):
                        door = door or 'portal recess'
                # Exposure: sample just outside the face.
                n = max(3, int(length / .25))
                hz = min(p.hi[2], 3.0)
                zs = sorted({max(p.lo[2], 0) + min(.12, p.size[2] / 2), (max(p.lo[2], 0) + hz) / 2})
                exposed = 0
                total = 0
                inner = 0
                solid_pred = (lambda q: q.kind() != 'prop' and q.size[axis] > .02 and q.mat not in (WINDOW, GLASS))
                for i in range(n):
                    u = p.lo[other] + .05 + (length - .1) * (i + .5) / n
                    for z in zs:
                        total += 1
                        # Exposed only when free just outside and beyond a
                        # narrow seam between two adjacent masses.
                        free = True
                        for d_out in (.03, .12):
                            pt = [0, 0, z]
                            pt[axis] = plane + normal * d_out
                            pt[other] = u
                            if grid.inside(tuple(pt), skip=p, pred=solid_pred):
                                free = False
                                break
                        if not free:
                            continue
                        exposed += 1
                        # Inner face of a basin, channel or enclosure: the
                        # same feature's mass stands opposite within 3 tiles.
                        for k in range(2, 60):
                            pt = [0, 0, z]
                            pt[axis] = plane + normal * k * .05
                            pt[other] = u
                            q = grid.inside(tuple(pt), skip=p, pred=solid_pred)
                            if q is not None:
                                if group(q) == group(p) and q.lo[2] <= GROUND_TOP:
                                    inner += 1
                                break
                if exposed / total < .25 or inner >= exposed * .6:
                    continue
                off = classify_offset(plane, normal)
                key = (axis, normal, round(plane, 3))
                f = faces.setdefault(key, dict(axis='xy'[axis], normal=normal, plane=round(plane, 4),
                                               offset=round(off, 4), length=0.0, kinds=set(), sources={},
                                               door=door, lowTop=round(p.hi[2], 3), span=[1e9, -1e9],
                                               height=0.0))
                f['height'] = max(f['height'], round(p.size[2], 3))
                f['length'] += length * exposed / total
                f['kinds'].add(p.kind())
                f['sources'].setdefault(f'{p.where}  (line {p.line})', round(length, 2))
                f['lowTop'] = max(f['lowTop'], round(p.hi[2], 3))
                f['span'] = [min(f['span'][0], round(p.lo[other], 3)), max(f['span'][1], round(p.hi[other], 3))]
                if door and not f['door']:
                    f['door'] = door
    # A base course or coping a few centimetres proud of its block is the
    # same edge: merge parallel planes within MERGE_TOL whose spans overlap,
    # keeping the tallest part's plane.
    merged = []
    for key in sorted(faces, key=lambda k: (k[0], k[1], k[2])):
        f = faces[key]
        for m in merged:
            if (m['axis'] == f['axis'] and m['normal'] == f['normal'] and abs(m['plane'] - f['plane']) <= MERGE_TOL
                    and f['span'][0] < m['span'][1] and f['span'][1] > m['span'][0]):
                if f['height'] > m['height']:
                    f['merged'] = m.get('merged', []) + [m['plane']]
                    f['length'] = max(f['length'], m['length'])
                    merged[merged.index(m)] = f
                else:
                    m.setdefault('merged', []).append(f['plane'])
                    m['length'] = max(f['length'], m['length'])
                break
        else:
            merged.append(f)
    result = dict(misses=[], near=[], midTile=[], round=[], doorExempt=[], ok=0)
    for f in merged:
        f['kinds'] = sorted(f['kinds'])
        f['length'] = round(f['length'], 2)
        f['sources'] = [f'{k} [len {v}]' for k, v in list(f['sources'].items())[:4]]
        off = f['offset']
        if abs(off) <= EDGE_TOL + 1e-6:
            result['ok'] += 1
            continue
        if f['door']:
            result['doorExempt'].append(f)
            continue
        if f['kinds'] == ['round']:
            result['round'].append(f)
        elif abs(off) <= NEAR_TOL:
            result['near'].append(f)
        elif abs(off) <= MISS_MAX:
            result['misses'].append(f)
        else:
            result['midTile'].append(f)
    for k in result:
        if isinstance(result[k], list):
            result[k].sort(key=lambda f: -f['length'])
    return result


def height_audit(parts, grid):
    floors, bases, terraces, paving = [], [], [], []
    seen = set()
    for p in parts:
        if p.animated or p.kind() in ('prop', 'roof', 'round'):
            continue
        sx, sy, sz = p.size
        if sx < .5 or sy < .5 or sx * sy < .5:
            continue
        walkfn = bool(p.funcs & WALK_FUNCS)
        if p.mat in MACHINE_MATS or (p.mat in (IRON, FORGED) and not walkfn):
            continue
        zt = p.hi[2]
        # Sample the top: covered (something stands on it or sits just
        # above), enclosed by walls, ringed by a parapet, or open.
        nx, ny = max(2, int(sx / .3)), max(2, int(sy / .3))
        counts = dict(covered=0, enclosed=0, parapet=0, open=0, rim=0)
        for i in range(nx):
            for j in range(ny):
                x = p.lo[0] + sx * (i + .5) / nx
                y = p.lo[1] + sy * (j + .5) / ny
                above = grid.inside((x, y, zt + .06), skip=p, pred=lambda q: q.kind() != 'prop' or q.size[2] > .5)
                if above is None:
                    # A top buried in a proud coping or slab is not a surface.
                    above = grid.inside((x, y, zt + .015), skip=p, pred=lambda q: q.kind() != 'prop'
                                        and q.lo[2] < zt)
                if above is None:
                    # No standing room under a floor or deck close above.
                    for dz in (.3, .6, .9):
                        above = grid.inside((x, y, zt + dz), skip=p, pred=lambda q: q.kind() != 'prop'
                                            and q.size[0] > .3 and q.size[1] > .3 and q.size[2] < .4)
                        if above is not None:
                            break
                if above is not None:
                    counts['covered'] += 1
                    continue
                if min(x - p.lo[0], p.hi[0] - x, y - p.lo[1], p.hi[1] - y) < .25:
                    # A narrow ledge or the rim of a top is not standing room.
                    counts['rim'] += 1
                    continue
                walls = parapets = 0
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    hit = None
                    for k in range(1, 220):
                        px, py = x + dx * k * .04, y + dy * k * .04
                        q = grid.inside((px, py, zt + .2), skip=p)
                        if q is not None and zt - .15 <= q.lo[2] <= zt + .2:
                            hit = q
                            break
                    if hit is None:
                        continue
                    if hit.funcs & PARAPET_FUNCS or hit.hi[2] < zt + .8:
                        parapets += 1
                    else:
                        walls += 1
                if walls == 4:
                    counts['enclosed'] += 1
                elif walls + parapets == 4 and parapets:
                    counts['parapet'] += 1
                else:
                    counts['open'] += 1
        total = nx * ny
        key = (round(zt, 3), round(p.lo[0], 2), round(p.lo[1], 2), round(p.hi[0], 2), round(p.hi[1], 2))
        if key in seen:
            continue
        seen.add(key)
        entry = dict(z=round(zt, 4), layerOffset=round(zt - round(zt), 4), rect=[round(v, 3) for v in
                     (p.lo[0], p.lo[1], p.hi[0], p.hi[1])], area=round(sx * sy, 2),
                     exposure={k: round(v / total, 2) for k, v in counts.items() if v},
                     source=f'{p.where}  (line {p.line})', walkFunction=walkfn)
        if zt < PAVING_TOP:
            if zt > .05:
                paving.append(entry)
            continue
        open_area = counts['open'] / total * sx * sy
        if (min(sx, sy) < 1.0 and sx * sy < 1.5) and not walkfn:
            # Caps of towers, piers and hoods: too small to stand on.
            entry['class'] = 'cap'
            bases.append(entry)
        elif counts['open'] / total >= .2 and open_area >= .5:
            entry['ok'] = abs(entry['layerOffset']) <= HEIGHT_TOL
            floors.append(entry)
        elif counts['parapet'] / total >= .2:
            entry['ok'] = abs(entry['layerOffset']) <= HEIGHT_TOL
            terraces.append(entry)
        else:
            bases.append(entry)
    # Keep the report readable: the top part at each height and place only.
    return dict(floorMisses=[f for f in floors if not f['ok']], floorsOk=len([f for f in floors if f['ok']]),
                terraces=terraces, wallBases=bases, paving=len(paving),
                floorsOkList=[(f['z'], f['rect']) for f in floors if f['ok']][:40])


def ground_audit(parts, grid):
    floating, sinking = [], []
    for p in parts:
        if p.animated:
            continue
        if p.lo[2] < -GROUND_SINK - .01:
            sinking.append(dict(z=round(p.lo[2], 4), source=f'{p.where}  (line {p.line})'))
        if not (.005 < p.lo[2] < .6) or p.funcs & HANGING_FUNCS:
            continue
        if p.size[0] < .04 or p.size[1] < .04:
            continue
        supported = False
        cx, cy = (p.lo[0] + p.hi[0]) / 2, (p.lo[1] + p.hi[1]) / 2
        for x in (p.lo[0], cx, p.hi[0]):
            for y in (p.lo[1], cy, p.hi[1]):
                for q in grid.near(x, y):
                    if q is p or q.animated:
                        continue
                    if (q.lo[0] < p.hi[0] and q.hi[0] > p.lo[0] and q.lo[1] < p.hi[1] and q.hi[1] > p.lo[1]
                            and q.lo[2] < p.lo[2] - 1e-4 and q.hi[2] >= p.lo[2] - .02):
                        supported = True
                        break
                if supported:
                    break
            if supported:
                break
        if not supported:
            floating.append(dict(z=round(p.lo[2], 4), size=[round(v, 2) for v in p.size],
                                 at=[round(cx, 2), round(cy, 2)], source=f'{p.where}  (line {p.line})'))
    # Collapse repeats from one source line.
    def collapse(items):
        out = {}
        for it in items:
            k = (it['source'], it['z'])
            if k in out:
                out[k]['count'] += 1
            else:
                out[k] = dict(it, count=1)
        return list(out.values())
    return dict(floating=collapse(floating), sinking=collapse(sinking))


def overlap_audit(parts):
    """Diagnostic: solid parts of different features whose boxes interpenetrate
    by more than OVERLAP in every axis (a moved mass running into a neighbour)."""
    solid = [p for p in parts if not p.animated and p.kind() in ('box', 'mesh', 'round')
             and min(p.size) > .05]
    grid = Grid(solid)
    found = {}
    for p in solid:
        gp = group(p)
        for x in range(math.floor(p.lo[0]), math.floor(p.hi[0]) + 1):
            for y in range(math.floor(p.lo[1]), math.floor(p.hi[1]) + 1):
                for q in grid.cells.get((x, y), ()):
                    if q.idx <= p.idx or group(q) == gp:
                        continue
                    o = [min(p.hi[i], q.hi[i]) - max(p.lo[i], q.lo[i]) for i in range(3)]
                    if min(o) > OVERLAP:
                        key = tuple(sorted((gp, group(q))))
                        found.setdefault(key, []).append(
                            [round(max(p.lo[i], q.lo[i]), 2) for i in range(3)] +
                            [round(min(p.hi[i], q.hi[i]), 2) for i in range(3)])
    return [dict(features=list(k), count=len(v), first=v[0]) for k, v in sorted(found.items())]


def audit(ident):
    module = importlib.import_module('lategame_' + ident)
    static = Geometry(ident + '.Architecture')
    animated = []
    parts, original = record(module.__file__)
    try:
        module.build(static, animated)
    finally:
        Geometry.add = original
    moving = {geo.name for geo, kind, _ in animated if kind != 'STATIC'}
    # Only the geometries the harness registers (scratch geometries that are
    # transformed and copied, e.g. side portals and faceted windows, are not).
    kept = {static.name} | {geo.name for geo, _, _ in animated}
    parts = [p for p in parts if p.geo in kept]
    for i, p in enumerate(parts):
        p.idx = i
        p.animated = p.geo in moving
    grid = Grid(parts)
    doors = door_planes(static.doorways)
    edges = edge_audit(parts, grid, doors, module.FOOTPRINT)
    heights = height_audit(parts, grid)
    ground = ground_audit(parts, grid)
    overlaps = overlap_audit(parts)
    summary = dict(edgeMisses=len(edges['misses']), edgeNear=len(edges['near']),
                   edgeMidTile=len(edges['midTile']), roundOffGrid=len(edges['round']), edgesOk=edges['ok'],
                   floorMisses=len(heights['floorMisses']), floorsOk=heights['floorsOk'],
                   terraces=len(heights['terraces']), wallBases=len(heights['wallBases']),
                   floating=sum(f['count'] for f in ground['floating']),
                   sinking=sum(f['count'] for f in ground['sinking']))
    return dict(ident=ident, footprint=list(module.FOOTPRINT), height=module.HEIGHT,
                doors=static.doorways, parts=len(parts), summary=summary, edges=edges, heights=heights,
                ground=ground, crossFeatureOverlaps=overlaps)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--models', default=None, help='Comma list; default all lategame_<Ident>.py studies')
    parser.add_argument('--output', type=Path, default=ROOT / 'outputs/lategame-grid-audit.json')
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    cli = parser.parse_args(argv)
    if cli.models:
        idents = cli.models.split(',')
    else:
        idents = sorted(p.stem[len('lategame_'):] for p in HERE.glob('lategame_*.py')
                        if not p.stem.endswith(('_kit', '_parts')) and p.stem != 'lategame_grid_audit')
    reports = {}
    for ident in idents:
        r = audit(ident)
        reports[ident] = r
        print('LATEGAME GRID', ident, json.dumps(r['summary']), flush=True)
    if cli.output.exists() and cli.models:
        old = json.loads(cli.output.read_text())
        old.get('buildings', {}).update(reports)
        reports = old['buildings']
    cli.output.write_text(json.dumps(dict(
        scope='Authored part extents from module build() (no scene). Edge/height/ground heuristics; '
              'see lategame_grid_audit.py docstring for the classification rules.',
        tolerances=dict(edge=EDGE_TOL, near=NEAR_TOL, missMax=MISS_MAX, height=HEIGHT_TOL, groundSink=GROUND_SINK),
        buildings=reports), indent=1, default=sorted) + '\n')
    print('LATEGAME GRID WROTE', cli.output, flush=True)


if __name__ == '__main__':
    main()
