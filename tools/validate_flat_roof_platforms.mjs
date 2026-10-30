// Every flat roof tile is a placeable area, like a platform (user, 2026-10-30: "all flat roof
// tiles should be placeable areas, similar to a platform.").
//
//   node tools/validate_flat_roof_platforms.mjs [dataRoot] [--table]
//
// For every Deep Frontier template of the generated Data root that owns its model (the
// templates of tools/connection_content.mjs), from its measured connection-face record
// (outputs/connection-faces/<Template>.json, measure_connection_faces.py; it must be current
// for the export) and its generated blueprint:
// - a flat roof cell is an occupied cell whose Top face the measurement found flat (one plane,
//   no curve or slope: the connection-face flatness test) and that has no block of the
//   building above or whose middle sees the sky (not in roof.covered; a registered block
//   over an open roof), or an occupied cell with no block above whose flat Top face was
//   dropped for an animated part above (roof.animated). A flat floor under a registered
//   block and a ceiling is an interior floor, not a roof;
// - it is under solid geometry when the measurement found static geometry of the building in
//   the middle of the cell above or anywhere higher over its middle (roof.blocked,
//   roof.covered: a stack, vent shaft, tower, dome, tank, mast or overhang), an animated
//   part standing in the cell above (roof.animated), or a smoke/steam mouth in its cell
//   column (a TemplateAttachmentsSpec emitter under '#Finished' within EMITTER_REACH of the
//   cell's middle and up to EMITTER_RISE above the roof: the top of a stack that rises
//   through the cell's outer band, roof_deck_content.mjs);
// - every other flat roof cell must be Stackable in the blueprint (a platformable roof deck,
//   tools/roof_decks.json applied by roof_deck_content.mjs) with the cell above free: outside
//   the Size or a block with no occupation, so a platform can stand there.
// Any flat roof cell that is neither Stackable nor under solid geometry fails, with the reason
// tools/roof_decks.json records for it, if any. There is no list of exempt buildings.
// Writes outputs/flat-roof-platforms-report.json (per template: counts and offending cells).
import {writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {readFileSync} from 'node:fs';
import {connectionTemplates, faceRecord} from './connection_content.mjs';
import {EMITTER_REACH, EMITTER_RISE, LIST} from './roof_deck_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const args = process.argv.slice(2);
const dataRoot = resolve(args.find((a) => !a.startsWith('--')) ?? join(root, 'src/DeepFrontier/Data'));
const table = args.includes('--table');
const key = (c) => c.join(',');
const listed = JSON.parse(readFileSync(join(root, LIST), 'utf8')).buildings;

const failures = [];
const report = {};
for (const {id, value} of await connectionTemplates(dataRoot)) {
  let record;
  try { record = await faceRecord(id, value, root); } catch (error) { failures.push(error.message); continue; }
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size;
  const block = ([x, y, z]) => spec.Blocks[(z * h + y) * w + x];
  const open = ([x, y, z]) => z + 1 >= layers || block([x, y, z + 1]).Occupations === 'None';
  const placeable = (c) => block(c).Stackable !== 'None' && open(c);
  const blocked = new Set(record.roof.blocked.map(key)), covered = new Set(record.roof.covered.map(key));
  const mouths = (value.TemplateAttachmentsSpec?.Attachments ?? []).filter((a) => a.Parent === '#Finished')
    .map((a) => [a.Position.X, a.Position.Z, a.Position.Y + spec.BaseZ]);
  const stack = ([x, y, z]) => mouths.some(([px, py, pz]) => Math.abs(px - (x + .5)) <= EMITTER_REACH
    && Math.abs(py - (y + .5)) <= EMITTER_REACH && pz >= z + 1 - .1 && pz <= z + 1 + EMITTER_RISE);
  const reasons = new Map((listed[id]?.excluded ?? []).map((e) => [key(e.cell), e.reason]));
  const roofs = new Map();
  for (const [x, y, z, d] of record.faces) {
    const c = [x, y, z];
    if (d !== 'Top' || block(c).Occupations === 'None' || (!open(c) && covered.has(key(c)))) continue;
    roofs.set(key(c), {cell: c, solid: blocked.has(key(c)) || covered.has(key(c)) || stack(c)});
  }
  for (const c of record.roof.animated) if (block(c).Occupations !== 'None' && open(c)) roofs.set(key(c), {cell: c, solid: true});
  if (!roofs.size) continue;
  const row = {flat: roofs.size, platformable: 0, underSolid: 0, offenders: []};
  for (const {cell, solid} of roofs.values()) {
    if (placeable(cell)) row.platformable++;
    else if (solid) row.underSolid++;
    else row.offenders.push({cell, reason: reasons.get(key(cell)) ?? 'not listed in ' + LIST});
  }
  row.offenders.sort((a, b) => a.cell[2] - b.cell[2] || a.cell[1] - b.cell[1] || a.cell[0] - b.cell[0]);
  report[id] = row;
  for (const o of row.offenders) failures.push(`${id}: flat roof ${o.cell} is not platformable (${o.reason})`);
}
await writeFile(join(root, 'outputs/flat-roof-platforms-report.json'), JSON.stringify({
  rule: 'Every flat roof cell (flat Top face of an occupied cell open to the sky, measure_connection_faces.py) is Stackable, '
    + 'unless static or animated building geometry stands in the middle of the cell above.',
  buildings: report}, null, 1) + '\n');
if (table) {
  console.log('building'.padEnd(34), 'flat', 'platformable', 'underSolid', 'offenders');
  for (const [id, r] of Object.entries(report).sort())
    console.log(id.padEnd(34), String(r.flat).padStart(4), String(r.platformable).padStart(12), String(r.underSolid).padStart(10), String(r.offenders.length).padStart(9));
}
const sum = (f) => Object.values(report).reduce((n, r) => n + f(r), 0);
if (failures.length) {
  console.log(failures.map((f) => 'FAIL ' + f).join('\n'));
  console.error(`Flat roof platform validation failed (${failures.length})`);
  process.exit(1);
}
console.log(`Flat roofs: ${Object.keys(report).length} templates, ${sum((r) => r.flat)} flat roof cells: `
  + `${sum((r) => r.platformable)} platformable, ${sum((r) => r.underSolid)} under solid geometry, none left unplaceable.`);
