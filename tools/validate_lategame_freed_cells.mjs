// Ground the 2026-10-22 no-forced-decoration pass freed on the late-game
// buildings must take the player's own path or 1x1 decoration.
//
// tools/lategame_freed_cells.json (record_freed_cells.py) lists, per
// building, the footprint before -> after and the freed ground cells in the
// new footprint frame:
//   - outside cells: the building has no block there any more, so native
//     placement meets no building occupation, matter rule or collider;
//   - inside cells: the generated blueprint's ground block there must be
//     Occupations None with MatterBelow Any, and no collider may reach into
//     that cell's ground layer. Native BlockService then reports no
//     conflicting occupation for a Path or a one-layer decoration, and the
//     building neither demands ground below nor stands there. clearHeight
//     reports the free layers above ground (an overhang may cover the cell
//     higher up).
// The blueprint's size must equal the recorded footprint. Writes
// outputs/lategame-freed-cells.json: the inside cells are the in-game
// acceptance points (place a Path and a 1x1 decoration on each).
import {readFile, readdir, writeFile} from 'node:fs/promises';
import {join} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const record = JSON.parse(await readFile(join(root, 'tools/lategame_freed_cells.json'), 'utf8'));

async function findBlueprints(dir, found = new Map()) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) await findBlueprints(path, found);
    else if (entry.name.endsWith('.IronTeeth.blueprint.json')) found.set(entry.name.slice(0, -'.IronTeeth.blueprint.json'.length), path);
  }
  return found;
}
const blueprints = await findBlueprints(join(root, 'src/DeepFrontier/Data/Buildings'));

const failures = [];
const report = {};
for (const [ident, entry] of Object.entries(record.buildings)) {
  const path = blueprints.get(ident);
  if (!path) { failures.push(`${ident}: no active blueprint`); continue; }
  const bp = JSON.parse(await readFile(path, 'utf8'));
  const spec = bp.BlockObjectSpec;
  const [w, h, layers] = [spec.Size.X, spec.Size.Y, spec.Size.Z];
  if ([w, h, layers].join() !== entry.footprintAfter.join()) {
    failures.push(`${ident}: blueprint size ${[w, h, layers]} is not the recorded footprint ${entry.footprintAfter}`);
    continue;
  }
  const at = (x, y, z) => spec.Blocks[(z * h + y) * w + x];
  const colliders = bp.Children['#Finished'].CollidersSpec.BoxColliders;
  const points = [];
  for (const [x, y] of entry.insideCells) {
    if (x < 0 || y < 0 || x >= w || y >= h) { failures.push(`${ident} (${x},${y}): recorded inside cell lies outside`); continue; }
    const ground = at(x, y, 0);
    const blocked = ground.Occupations !== 'None' || ground.MatterBelow !== 'Any';
    const collider = colliders.find((c) => Math.abs(c.Center.X - (x + .5)) < c.Size.X / 2 &&
      Math.abs(c.Center.Z - (y + .5)) < c.Size.Z / 2 && c.Center.Y - c.Size.Y / 2 < 1);
    let clearHeight = 0;
    while (clearHeight < layers && at(x, y, clearHeight).Occupations === 'None') clearHeight++;
    if (blocked || collider) failures.push(`${ident} (${x},${y}): ${blocked ? JSON.stringify(ground) : 'collider ' + JSON.stringify(collider)}`);
    points.push({cell: [x, y, 0], clearHeight, path: !blocked && !collider, decoration: !blocked && !collider});
  }
  report[ident] = {footprint: `${entry.footprintBefore.slice(0, 2).join('x')} -> ${entry.footprintAfter.slice(0, 2).join('x')}`,
    gridOrigin: entry.gridOrigin, entrance: [spec.Entrance.Coordinates.X, spec.Entrance.Coordinates.Y, spec.Entrance.Coordinates.Z],
    outsideCells: entry.outsideCells, insidePoints: points};
}
await writeFile(join(root, 'outputs/lategame-freed-cells.json'), JSON.stringify({
  scope: 'Static native-occupation check of the late-game ground freed by the 2026-10-22 pass; place a Path and a 1x1 decoration on each inside point in game to accept it.',
  coordinates: 'Native grid XYZ of each building (cell x,y at layer 0), unrotated placement',
  buildings: report,
}, null, 1) + '\n');
if (failures.length) {
  console.error(failures.join('\n'));
  throw new Error(`Late-game freed cells are not placeable (${failures.length})`);
}
console.log(JSON.stringify(Object.fromEntries(Object.entries(report).map(([k, v]) => [k, {footprint: v.footprint,
  outside: v.outsideCells, inside: v.insidePoints.map((p) => `${p.cell[0]},${p.cell[1]}` + (p.clearHeight < 2 ? `(h${p.clearHeight})` : ''))}]))));
