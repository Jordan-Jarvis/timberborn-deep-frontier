// Platformable flat roofs (tools/roof_deck_content.mjs, tools/roof_decks.json).
//
//   node tools/validate_roof_decks.mjs [dataRoot]
//
// Checks, per Deep Frontier template of the generated Data root that owns its model:
// - tools/roof_decks.json is current: it equals the plan recomputed from
//   outputs/connection-faces and the blueprint (a generated list, never hand-edited);
// - every listed roof cell is Stackable, is occupied, and has a free cell (or the sky) above;
// - every flat roof face of the record (flat Top face of an occupied cell with nothing of
//   the building above) is either platformable or excluded with a recorded reason, so no
//   qualifying flat roof is left unplatformable silently;
// - every template with a stackable block has GenerateFloorsOnStackable true, as every
//   vanilla Iron Teeth blueprint with a stackable block has;
// - roof shaft faces sit only on stackable blocks (validate_connection_faces.mjs owns the
//   connection rule; this repeats the roof part for the decks).
// Writes outputs/roof-decks-report.json (per template: platformable, excluded with reasons).
import {readFile, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {connectionTemplates, faceRecord} from './connection_content.mjs';
import {LIST, REASONS, roofDeckPlan} from './roof_deck_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : join(root, 'src/DeepFrontier/Data');
const failures = [];
const fail = (m) => failures.push(m);
const list = JSON.parse(await readFile(join(root, LIST), 'utf8')).buildings;
const reasons = new Set(Object.values(REASONS));
const report = {};
const seen = new Set();
for (const {id, value} of await connectionTemplates(dataRoot)) {
  let plan, record;
  try { plan = await roofDeckPlan(id, value, root); record = await faceRecord(id, value, root); } catch (error) { fail(error.message); continue; }
  const empty = !plan.platformable.length && !plan.excluded.length;
  if (!empty) seen.add(id);
  const listed = list[id] ?? {platformable: [], excluded: []};
  if (JSON.stringify(listed) !== JSON.stringify(empty ? {platformable: [], excluded: []} : plan))
    fail(`${id}: ${LIST} differs from the recomputed plan; rerun node tools/roof_deck_content.mjs --write <generated Data>`);
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size;
  const block = ([x, y, z]) => spec.Blocks[(z * h + y) * w + x];
  for (const c of plan.platformable) {
    const [x, y, z] = c;
    if (block(c).Occupations === 'None') fail(`${id}: platformable roof ${c} is not an occupied cell`);
    if (z + 1 < layers && block([x, y, z + 1]).Occupations !== 'None') fail(`${id}: platformable roof ${c} has the building above`);
    if (block(c).Stackable === 'None') fail(`${id}: platformable roof ${c} is not Stackable`);
  }
  for (const e of plan.excluded) if (!reasons.has(e.reason)) fail(`${id}: excluded roof ${e.cell} has no known reason`);
  const decided = new Set([...plan.platformable, ...plan.excluded.map((e) => e.cell)].map((c) => c.join(',')));
  for (const [x, y, z, d] of record.faces) {
    if (d !== 'Top' || block([x, y, z]).Occupations === 'None') continue;
    if (z + 1 < layers && block([x, y, z + 1]).Occupations !== 'None') continue;
    if (!decided.has([x, y, z].join(','))) fail(`${id}: flat roof ${[x, y, z]} is neither platformable nor excluded with a reason`);
  }
  if (spec.Blocks.some((b) => b.Stackable !== 'None') && value.BlockObjectNavMeshSettingsSpec?.GenerateFloorsOnStackable !== true)
    fail(`${id}: stackable blocks without GenerateFloorsOnStackable (every vanilla stackable blueprint sets it)`);
  for (const t of value.TransputProviderSpec?.Transputs ?? []) {
    const c = [t.Coordinates.X, t.Coordinates.Y, t.Coordinates.Z];
    if (t.Directions.includes('Top') && block(c).Stackable === 'None') fail(`${id}: roof shaft face ${c} on a non-stackable block`);
  }
  if (!empty) report[id] = {platformable: plan.platformable.length, excluded: plan.excluded};
}
for (const id of Object.keys(list)) if (!seen.has(id)) fail(`${id}: listed in ${LIST} but has no flat roof (or is gone)`);
await writeFile(join(root, 'outputs/roof-decks-report.json'), JSON.stringify({
  scope: 'Generated blueprints against tools/roof_decks.json (static; native placement is tested by AllBuildingsAcceptance)',
  buildings: report}, null, 1) + '\n');
if (failures.length) {
  console.log(failures.map((f) => 'FAIL ' + f).join('\n'));
  console.error(`Roof deck validation failed (${failures.length})`);
  process.exit(1);
}
const total = Object.values(report).reduce((n, r) => n + r.platformable, 0);
console.log(`Roof decks: ${Object.values(report).filter((r) => r.platformable).length} templates, ${total} platformable flat roof cells; `
  + `${Object.values(report).reduce((n, r) => n + r.excluded.length, 0)} flat roof cells excluded with a reason.`);
