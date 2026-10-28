// Ground the 2026-10-22 footprint pass freed must take the player's own path
// or 1x1 decoration.
//
// Each footprint now ends at the building's walls. For every ground cell that
// the earlier registration (FORMER below) covered:
//   - outside the new footprint: the building has no block there, so native
//     placement meets no building occupation, matter rule or collider;
//   - still inside the new bounds: the building's ground block there must be
//     Occupations None with MatterBelow Any and no collider in that layer
//     (native BlockService then reports no conflicting occupation for a Path
//     or a one-layer decoration's 'All' block, and the building neither
//     demands ground below nor stands there). clearHeight reports the free
//     layers above ground (a canopy or overhang may cover the cell higher up).
// Open ground cells inside the bounds that were already open are checked by
// the same rule. Writes outputs/freed-cells.json: the cells are the in-game
// acceptance points (place a Path and a 1x1 decoration on each).
import {readFile, writeFile} from 'node:fs/promises';
import {industrialBlockSpec, industrialLayout} from './industrial_building_content.mjs';
import {industrialColliders} from './industrial_occupancy.mjs';
import {pitBlocks} from './pit_building_content.mjs';

const pits = JSON.parse(await readFile(new URL('./pit-layouts.json', import.meta.url), 'utf8'));
// Registrations before the pass: artwork origin and ground size.
const FORMER = {
  StoneCrusher: {origin: [0, 0], size: [6, 7]},
  CementKiln: {origin: [1, 2], size: [9, 9]},
  ConcreteMixer: {origin: [0, 0], size: [8, 6]},
  MineralQuarry: {origin: [0, 1], size: [11, 10]},
  SandstonePit: {origin: [.57, 0], size: [5, 5]},
  LimestonePit: {origin: [.57, 0], size: [6, 5]},
};
const failures = [];
const report = {};
for (const [ident, former] of Object.entries(FORMER)) {
  const pit = ident in pits;
  const d = pit ? pits[ident] : industrialLayout(ident);
  if (!d) throw new Error(`No registration for ${ident}`);
  const blocks = pit ? pitBlocks(ident) : industrialBlockSpec(ident, d);
  const [w, h, layers] = d.size;
  const at = (x, y, z) => blocks[(z * h + y) * w + x];
  const colliders = industrialColliders(blocks, d.size, d.baseZ).BoxColliders;
  const shift = [d.origin[0] - former.origin[0], d.origin[1] - former.origin[1]];
  if (shift.some(v => Math.abs(v - Math.round(v)) > 1e-9)) throw new Error(`${ident}: registrations differ by a non-whole shift`);
  const inside = (x, y) => x >= 0 && y >= 0 && x < w && y < h;
  const cells = new Map();
  for (let y = 0; y < former.size[1]; y++) for (let x = 0; x < former.size[0]; x++) {
    const c = [x + Math.round(shift[0]), y + Math.round(shift[1])];
    cells.set(c.join(','), {cell: c, freedByPass: !inside(...c)});
  }
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (at(x, y, 0).Occupations === 'None') {
      const key = `${x},${y}`;
      cells.set(key, {cell: [x, y], freedByPass: cells.get(key)?.freedByPass ?? false, insideBounds: true});
    }
  }
  const points = [];
  for (const {cell: [x, y], freedByPass} of cells.values()) {
    if (!inside(x, y)) {
      points.push({cell: [x, y, 0], where: 'outside footprint', path: true, decoration: true});
      continue;
    }
    if (at(x, y, 0).Occupations !== 'None') continue; // still the building (walls, machinery)
    const ground = at(x, y, 0);
    const blocked = ground.Occupations !== 'None' || ground.MatterBelow !== 'Any' ? ground : null;
    const collider = colliders.find(c => Math.abs(c.Center.X - (x + .5)) < c.Size.X / 2 && Math.abs(c.Center.Z - (y + .5)) < c.Size.Z / 2 && c.Center.Y - c.Size.Y / 2 < 1 - d.baseZ);
    let clearHeight = 0;
    while (clearHeight < layers && at(x, y, clearHeight).Occupations === 'None') clearHeight++;
    if (blocked || collider) failures.push(`${ident} (${x},${y}): ${blocked ? JSON.stringify(blocked) : 'collider ' + JSON.stringify(collider)}`);
    points.push({cell: [x, y, 0], where: freedByPass ? 'freed inside bounds' : 'open inside bounds', clearHeight, path: !blocked && !collider, decoration: !blocked && !collider});
  }
  points.sort((a, b) => a.cell[1] - b.cell[1] || a.cell[0] - b.cell[0]);
  report[ident] = {formerSize: former.size, size: [w, h], entrance: d.entrance, points};
}
await writeFile(new URL('../outputs/freed-cells.json', import.meta.url), JSON.stringify({
  scope: 'Static native-occupation check of the ground freed by the 2026-10-22 footprint pass; place a Path and a 1x1 decoration on each point in game to accept it.',
  coordinates: 'Native grid XYZ of each registration (cell x,y at layer 0), unrotated placement',
  models: report,
}, null, 1) + '\n');
if (failures.length) {
  console.error(failures.join('\n'));
  throw new Error(`Freed cells are not placeable (${failures.length})`);
}
console.log(JSON.stringify(Object.fromEntries(Object.entries(report).map(([k, v]) => [k, {size: `${v.formerSize.join('x')} -> ${v.size.join('x')}`,
  outside: v.points.filter(p => p.where === 'outside footprint').length,
  freedInside: v.points.filter(p => p.where === 'freed inside bounds').map(p => p.cell.slice(0, 2).join(',')),
  openInside: v.points.filter(p => p.where === 'open inside bounds').map(p => p.cell.slice(0, 2).join(','))}]))));
