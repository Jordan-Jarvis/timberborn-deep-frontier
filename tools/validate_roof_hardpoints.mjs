// Roof hardpoints (tools/roof_hardpoint_content.mjs, tools/roof_hardpoints.json;
// src/DeepFrontier/Scripts/SteelStructures/RoofHardpoints.cs).
//
//   node tools/validate_roof_hardpoints.mjs [dataRoot]
//
// Checks, per Deep Frontier template of the generated Data root that owns its model:
// - tools/roof_hardpoints.json is current: per template it equals the plan recomputed from
//   outputs/roof-hardpoints, outputs/connection-faces and the blueprint (generated, never edited);
// - the blueprint's RoofHardpointsSpec.Cells are exactly the listed hardpoints; each is an occupied
//   top cell with Top occupation, Stackable, nothing of the building above it, no flat roof face
//   (no roof deck cell) and no Top shaft face; GenerateFloorsOnStackable is on;
// - every top cell of a building is decided: a flat roof face (roof_decks.json), a family-stackable
//   top, a hardpoint, or excluded with a known reason, so no roof is left out silently; every
//   curved or sloped roof face the connection measurement found on a top cell is a hardpoint or
//   excluded with a reason (the non-flat roofs this step exists for);
// - structural pieces have no hardpoints; exactly the steel columns, steel decks and leg deck tools
//   carry SteelSupportSpec; each column carries its hardpoint sleeve (the one-layer column model one
//   layer down);
// - the C# wiring: service, preview-only validator for non-steel previews, the sleeve decorator,
//   the tool preview's sleeve, and the placement message row.
// Writes outputs/roof-hardpoints-report.json (per template: tops, flat, hardpoints, excluded).
import {readFile, readdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {connectionTemplates, faceRecord} from './connection_content.mjs';
import {roofDeckPlan} from './roof_deck_content.mjs';
import {LIST, REASONS, STRUCTURES, roofHardpointPlan, topCells} from './roof_hardpoint_content.mjs';
import {HARDPOINT_SLEEVE} from './structural_building_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : join(root, 'src/DeepFrontier/Data');
const failures = [];
const fail = (m) => failures.push(m);
const key = (c) => c.join(',');
const list = JSON.parse(await readFile(join(root, LIST), 'utf8')).buildings;
const structural = JSON.parse(await readFile(join(root, 'tools/structural_content.json'), 'utf8'));
const reasons = new Set(Object.values(REASONS));
const report = {};
const seen = new Set();
const steel = new Set([...structural.buildings.filter((b) => b.kind === 'column' || b.kind === 'deck'), ...structural.legDecks.tools].map((b) => b.id));
const supports = new Set();
let total = 0, tops = 0, curvedTops = 0;
for (const {id, value} of await connectionTemplates(dataRoot)) {
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size;
  const block = ([x, y, z]) => spec.Blocks[(z * h + y) * w + x];
  if (STRUCTURES.has(id)) {
    if (list[id] || value.RoofHardpointsSpec) fail(`${id}: a structural piece must have no hardpoints`);
    if (steel.has(id) && id.startsWith('SteelColumn')) {
      const node = value.Children['#Finished']?.Children?.[HARDPOINT_SLEEVE];
      if (value.HardpointSleeveSpec?.NodeName !== HARDPOINT_SLEEVE || !node || node.TransformSpec?.Position?.Y !== -1
          || node.TimbermeshSpec?.Model !== `Buildings/Platforms/${structural.legDecks.columns[0]}/${structural.legDecks.columns[0]}.IronTeeth.Model`)
        fail(`${id}: the column needs its hardpoint sleeve (${HARDPOINT_SLEEVE}: the one-layer column one layer down)`);
    } else if (value.HardpointSleeveSpec) fail(`${id}: only steel columns have a hardpoint sleeve`);
    continue;
  }
  if (value.HardpointSleeveSpec) fail(`${id}: only steel columns have a hardpoint sleeve`);
  let plan, record, deck;
  try {
    plan = await roofHardpointPlan(id, value, root);
    record = await faceRecord(id, value, root);
    deck = await roofDeckPlan(id, value, root);
  } catch (error) { fail(error.message); continue; }
  const listedPlan = plan.hardpoints.length || plan.excluded.length ? {hardpoints: plan.hardpoints, excluded: plan.excluded} : null;
  if (listedPlan) seen.add(id);
  if (JSON.stringify(list[id] ?? null) !== JSON.stringify(listedPlan))
    fail(`${id}: ${LIST} differs from the recomputed plan; rerun node tools/roof_hardpoint_content.mjs --write <generated Data>`);
  const cells = (value.RoofHardpointsSpec?.Cells ?? []).map((c) => [c.X, c.Y, c.Z]);
  if (JSON.stringify(cells) !== JSON.stringify(plan.hardpoints)) fail(`${id}: RoofHardpointsSpec.Cells differ from the listed hardpoints`);
  if (value.RoofHardpointsSpec && !plan.hardpoints.length) fail(`${id}: an empty RoofHardpointsSpec`);
  const flat = new Set([...deck.platformable, ...deck.excluded.map((e) => e.cell)].map(key));
  const topFaces = new Set((value.TransputProviderSpec?.Transputs ?? []).filter((t) => t.Directions.includes('Top')).map((t) => key([t.Coordinates.X, t.Coordinates.Y, t.Coordinates.Z])));
  const hard = new Set(plan.hardpoints.map(key));
  for (const c of plan.hardpoints) {
    const [x, y, z] = c;
    const b = block(c);
    if (b.Occupations !== 'All' && !b.Occupations.split(', ').includes('Top')) fail(`${id}: hardpoint ${c} has no Top occupation`);
    if (b.Stackable !== 'BlockObject') fail(`${id}: hardpoint ${c} is not Stackable`);
    if (z + 1 < layers && block([x, y, z + 1]).Occupations !== 'None') fail(`${id}: hardpoint ${c} has the building above`);
    if (flat.has(key(c))) fail(`${id}: hardpoint ${c} is a flat roof face (a roof deck cell)`);
    if (topFaces.has(key(c))) fail(`${id}: hardpoint ${c} carries a roof shaft face`);
  }
  if (plan.hardpoints.length && value.BlockObjectNavMeshSettingsSpec?.GenerateFloorsOnStackable !== true)
    fail(`${id}: hardpoints without GenerateFloorsOnStackable`);
  for (const e of plan.excluded) if (!reasons.has(e.reason)) fail(`${id}: excluded top ${e.cell} has no known reason`);
  const decided = new Set([...hard, ...plan.excluded.map((e) => key(e.cell)), ...flat]);
  const mine = new Set(cells.map(key));
  const own = topCells(value);
  for (const c of own)
    if (!decided.has(key(c)) && !(block(c).Stackable !== 'None' && !mine.has(key(c)))) fail(`${id}: top cell ${c} is neither a bed nor excluded with a reason`);
  const topSet = new Set(own.map(key));
  for (const [x, y, z, dir] of record.curvedFaces) {
    if (dir !== 'Top' || !topSet.has(key([x, y, z]))) continue;
    curvedTops++;
    if (!hard.has(key([x, y, z])) && !plan.excluded.some((e) => key(e.cell) === key([x, y, z])))
      fail(`${id}: the curved or sloped roof ${[x, y, z]} is neither a hardpoint nor excluded with a reason`);
  }
  total += plan.hardpoints.length; tops += own.length;
  if (listedPlan) report[id] = {tops: own.length, flat: plan.flat, hardpoints: plan.hardpoints.length, excluded: plan.excluded};
}
for (const id of Object.keys(list)) if (!seen.has(id)) fail(`${id}: listed in ${LIST} but has nothing to decide (or is gone)`);
// Every building blueprint (the leg deck tools own no model, so connectionTemplates skips them).
async function* blueprints(dir) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* blueprints(path);
    else if (entry.name.endsWith('.IronTeeth.blueprint.json')) yield path;
  }
}
for await (const path of blueprints(join(dataRoot, 'Buildings'))) {
  const value = JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
  if (value.SteelSupportSpec) supports.add(value.TemplateSpec.TemplateName.replace(/\.IronTeeth$/, ''));
}
const missing = [...steel].filter((id) => !supports.has(id)), extra = [...supports].filter((id) => !steel.has(id));
if (missing.length || extra.length) fail(`SteelSupportSpec must be on exactly the steel columns, decks and leg deck tools (missing ${missing.join(', ') || 'none'}; extra ${extra.join(', ') || 'none'})`);

// C# wiring and the message.
const cs = await readFile(join(root, 'src/DeepFrontier/Scripts/SteelStructures/RoofHardpoints.cs'), 'utf8');
const legs = await readFile(join(root, 'src/DeepFrontier/Scripts/SteelStructures/SteelLegDecks.cs'), 'utf8');
for (const what of ['internal record RoofHardpointsSpec : ComponentSpec', '[Serialize] public ImmutableArray<Vector3Int> Cells { get; init; }',
  'internal record SteelSupportSpec : ComponentSpec;', '[Serialize] public string NodeName { get; init; }',
  'if(!blockObject.IsPreview||blockObject.HasComponent<SteelSupportSpec>())return true;',
  'foreach(Vector3Int foundation in blockObject.PositionedBlocks.GetFoundationCoordinates())',
  'MultiBind<IBlockObjectValidator>().ToExisting<RoofHardpointValidator>()', 'Bind<RoofHardpointService>().AsSingleton()',
  'b.AddDecorator<HardpointSleeveSpec,HardpointSleeve>()', '[Context("Game")]'])
  if (!cs.includes(what)) fail(`RoofHardpoints.cs: missing ${what}`);
if (!legs.includes('if(leg.Length>0&&_hardpoints.IsHardpoint(leg.Bottom.Below()))Show(0,leg.Bottom.Below(),ref created);'))
  fail('SteelLegDecks.cs: the tool preview must draw the sleeve of a leg standing on a hardpoint');
const csv = await readFile(join(dataRoot, 'Localizations/enUS.csv'), 'utf8');
for (const [, k] of cs.matchAll(/public const string \w+="([^"]+)";/g))
  if (!csv.split('\n').some((line) => line.startsWith(k + ','))) fail(`RoofHardpointLoc key ${k} has no enUS row`);

await writeFile(join(root, 'outputs/roof-hardpoints-report.json'), JSON.stringify({
  scope: 'Generated blueprints against tools/roof_hardpoints.json (static; placing columns on hardpoints is an in-game test)',
  buildings: report}, null, 1) + '\n');
if (failures.length) {
  console.log(failures.map((f) => 'FAIL ' + f).join('\n'));
  console.error(`Roof hardpoint validation failed (${failures.length})`);
  process.exit(1);
}
console.log(`Roof hardpoints: ${total} cells on ${Object.values(report).filter((r) => r.hardpoints).length} templates; `
  + `${tops} building top cells all decided (${curvedTops} curved or sloped roof faces among them); `
  + `${[...supports].length} steel supports; validator and sleeves wired.`);
