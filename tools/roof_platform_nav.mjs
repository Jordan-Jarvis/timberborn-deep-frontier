// Native navigation and placement model of a building's roof, for
// validate_flat_roof_platforms.mjs (user, 2026-10-31: "I want it to be like an actual
// platform where roads can connect. buildings can be built on edges of two buildings
// butting up to each other").
//
// Source-confirmed (Timberborn 1.1.2.8, Timberborn.BlockSystemNavigation
// NavMeshObjectUpdater.Update, decompiled with tools/dotnet/ilspycmd.exe):
// - added edges: every EdgeGroups edge (two-way doubled) and, with
//   GenerateFloorsOnStackable, an edge from the cell above every Stackable block to
//   each of its four neighbours (AddEdgesAddedByStackable);
// - blocked edges (every nav group): Top-occupied cell -> the cell above it; the spec's
//   BlockedEdges; and unless NoAutoWalls, walls round Bottom-occupied cells:
//   with an entrance, AddEdgesBlockedByElevatedEntrance (entrance z > 0: the cells
//   below that layer with Bottom/Floor/All, blocked among themselves and walled) and
//   AddEdgesBlockedByWalls over the Bottom cells, then the doorstep -> entrance edge is
//   removed; without one, AddEdgesBlockedByCoordinates over the Bottom cells;
// - UnblockedCoordinates exempt their 8 neighbour edges from blocking;
// - a blocked edge is dropped when an added edge has the same start, end and group
//   (CanAddBlockingEdge).
// Path (vanilla Buildings/Paths/Path): one cell, MatterBelow GroundOrStackable,
// Occupations Path; its IsPath edges join neighbouring paths where the navmesh has an
// edge (PathSystem ConnectionService.IsPath). A building block stands on a roof when
// its foundation's MatterBelow is GroundOrStackable/Stackable, the block below is
// Stackable and the cell itself has no conflicting occupation (BlockValidator,
// MatterBelowValidator); a None block of the roof's building is no occupation.
//
// Only the default nav group is modelled: floors and player paths use it, and a
// building's other groups (UseGroup edge groups) are not floors.
const OCC = ['Floor', 'Bottom', 'Top', 'Corners', 'Path', 'Middle'];
export function occupations(text) {
  if (text === 'None') return new Set();
  if (text === 'All') return new Set(OCC);
  const set = new Set(text.split(',').map((s) => s.trim()));
  for (const o of set) if (!OCC.includes(o)) throw new Error(`Unknown occupation ${o} in '${text}'`);
  return set;
}
const key = (c) => c.join(',');
const N4 = [[-1, 0, 0], [1, 0, 0], [0, -1, 0], [0, 1, 0]];
const N8 = [[-1, -1, 0], [0, -1, 0], [1, -1, 0], [-1, 0, 0], [1, 0, 0], [-1, 1, 0], [0, 1, 0], [1, 1, 0]];
const add = (a, b) => [a[0] + b[0], a[1] + b[1], a[2] + b[2]];
const v3 = (p) => [p.X, p.Y, p.Z];

// The building in its own (unrotated) grid: blocks, entrance and nav settings.
export function buildingModel(value) {
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size;
  const nav = value.BlockObjectNavMeshSettingsSpec ?? null;
  const inside = ([x, y, z]) => x >= 0 && y >= 0 && z >= 0 && x < w && y < h && z < layers;
  const block = (c) => (inside(c) ? spec.Blocks[(c[2] * h + c[1]) * w + c[0]] : null);
  const occ = (c) => (block(c) ? occupations(block(c).Occupations) : new Set());
  return {w, h, layers, nav, inside, block, occ, entrance: spec.Entrance?.HasEntrance ? v3(spec.Entrance.Coordinates) : null};
}

// Added and blocked default-group edges of NavMeshObjectUpdater.Update for one building.
export function navEdges(m) {
  const added = new Set(), blocked = new Set(), unblocked = new Set();
  const edge = (a, b) => key(a) + '>' + key(b);
  if (m.nav) {
    for (const group of m.nav.EdgeGroups) {
      if (group.Group.UseGroup) continue;
      for (const e of group.AddedEdges) {
        added.add(edge(v3(e.Start), v3(e.End)));
        if (e.IsTwoWay) added.add(edge(v3(e.End), v3(e.Start)));
      }
    }
    if (m.nav.GenerateFloorsOnStackable) {
      for (const c of cells(m)) if (m.block(c).Stackable !== 'None')
        for (const d of N4) added.add(edge(add(c, [0, 0, 1]), add(add(c, [0, 0, 1]), d)));
    }
    for (const u of m.nav.UnblockedCoordinates) for (const d of N8) unblocked.add(edge(v3(u.Coordinates), add(v3(u.Coordinates), d)));
  }
  const block = (a, b) => { const e = edge(a, b); if (!unblocked.has(e)) blocked.add(e); };
  const bottom = [], top = [];
  for (const c of cells(m)) {
    const o = m.occ(c);
    if (o.has('Bottom')) bottom.push(c);
    if (o.has('Top')) top.push(c);
  }
  for (const c of top) block(c, add(c, [0, 0, 1]));
  for (const e of m.nav?.BlockedEdges ?? []) block(v3(e.Start), v3(e.End));
  const wallOf = (set) => {
    const has = new Set(set.map(key));
    for (const c of set) for (const d of N4) {
      if (has.has(key(add(c, d)))) continue;
      const n = add(c, d), p = [d[1], d[0], 0];
      block(c, n); block(c, add(n, p)); block(c, add(n, p.map((x) => -x)));
      block(add(c, p), n); block(add(c, p.map((x) => -x)), n);
    }
  };
  const byCoordinates = (set) => {
    const has = new Set(set.map(key));
    for (const c of set) for (const d of N8) if (has.has(key(add(c, d)))) block(c, add(c, d));
    wallOf(set);
  };
  if (!m.nav?.NoAutoWalls) {
    if (m.entrance) {
      if (m.entrance[2] > 0) byCoordinates(cells(m).filter((c) => c[2] < m.entrance[2]
        && ['Bottom', 'Floor'].some((o) => m.occ(c).has(o))));
      wallOf(bottom);
      blocked.delete(edge(add(m.entrance, [0, -1, 0]), m.entrance));
    } else {
      byCoordinates(bottom);
    }
  }
  for (const e of added) blocked.delete(e);
  return {added, blocked, edge};
}

function cells(m) {
  const out = [];
  for (let z = 0; z < m.layers; z++) for (let y = 0; y < m.h; y++) for (let x = 0; x < m.w; x++) out.push([x, y, z]);
  return out;
}

// A cell a block can be built into: outside the building, or a None block of it.
export const free = (m, c) => m.occ(c).size === 0;

// Roof links of the platformable roof cells `roofs` (roof cell coordinates):
// - within: a neighbouring platformable roof cell of the same building at the same layer;
// - seam: the neighbour's column, from the roof layer up to the stand layer, holds no
//   block of this building, so another building's roof (or a vanilla Platform) can butt
//   up there at the same height.
// For each link the stand cells (above the roofs) must carry a floor edge both ways
// that this building does not block, so player paths join across it, and for a seam a
// two-cell building foundation over both stand cells must be valid on this side
// (Stackable roof below, free stand cell). The far side of a seam is a vanilla
// Platform.IronTeeth (Top, Corners; Stackable; GenerateFloorsOnStackable; NoAutoWalls),
// the reference every abutting roof must match.
export function roofLinks(m, roofs) {
  const {added, blocked, edge} = navEdges(m);
  const isRoof = new Set(roofs.map(key));
  const out = {within: 0, seam: 0, seamCells: new Set(), failures: []};
  for (const c of roofs) {
    const s = add(c, [0, 0, 1]);
    if (!free(m, s)) { out.failures.push({cell: c, why: `stand cell ${s} is occupied`}); continue; }
    if (m.block(c).Stackable === 'None') { out.failures.push({cell: c, why: 'roof block is not Stackable'}); continue; }
    for (const d of N4) {
      const nc = add(c, d), ns = add(s, d);
      let kind = null;
      if (isRoof.has(key(nc))) kind = 'within';
      else if ([nc, ns].every((p) => free(m, p))) kind = 'seam';
      if (!kind) continue;
      const there = edge(s, ns), back = edge(ns, s);
      // The far side's own floor edge back: this building's floors for a roof within,
      // the abutting Platform's floors at a seam.
      const ok = added.has(there) && !blocked.has(there) && !blocked.has(back)
        && (kind === 'seam' || added.has(back));
      if (!ok) {
        out.failures.push({cell: c, why: `${kind} link ${s} -> ${ns}: `
          + (!added.has(there) ? 'no floor edge (GenerateFloorsOnStackable off?)' : 'edge blocked by this building')});
        continue;
      }
      if (kind === 'seam') { out.seam++; out.seamCells.add(key(c)); } else out.within++;
    }
  }
  return out;
}

// Path occupation conflicts: a Path cannot be placed in a cell whose block occupies Path.
export const pathBlocked = (m, c) => m.occ(c).has('Path');
