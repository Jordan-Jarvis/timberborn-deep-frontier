// Static check of the late-game power rule (building_construction_costs.json
// lategameRule.power, tools/lategame_costs.mjs scaledPower) on the generated
// blueprints. Usage:
//   node tools/validate_power_rule.mjs [dataRoot]
// Every generated power consumer (MechanicalNodeSpec.PowerInput > 0) unlocked
// at power.scienceMin science or more must draw max(authored base, floor):
// exactly the floor, or more (its authored base wins). A consumer below its
// floor must be in power.exempt, and every exemption must name such a
// consumer: a missing or an unneeded exemption fails. Generators
// (PowerInput 0) are outside the rule.
import {readdir, readFile} from 'node:fs/promises';
import {join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {powerRule, powerFloor} from './lategame_costs.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');
const failures = [];

async function* blueprints(dir) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) yield* blueprints(path);
    else if (entry.name.endsWith('.blueprint.json')) yield path;
  }
}

const consumers = [];
for await (const path of blueprints(resolve(dataRoot, 'Buildings'))) {
  const value = JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
  const input = value.MechanicalNodeSpec?.PowerInput ?? 0;
  if (!(input > 0)) continue;
  const science = value.BuildingSpec?.ScienceCost;
  const name = value.TemplateSpec?.TemplateName;
  if (!Number.isInteger(science) || typeof name !== 'string') {
    failures.push(`${relative(dataRoot, path)}: a consumer needs BuildingSpec.ScienceCost and TemplateSpec.TemplateName`);
    continue;
  }
  consumers.push({id: name.replace(/\.IronTeeth$/, ''), science, input, output: value.MechanicalNodeSpec.PowerOutput ?? 0});
}

const ruled = consumers.filter((c) => c.science >= powerRule.scienceMin).sort((a, b) => a.science - b.science || a.id.localeCompare(b.id));
const exempt = new Set(Object.keys(powerRule.exempt));
const rows = [];
for (const c of ruled) {
  const floor = powerFloor(c.science);
  if (c.output !== 0) failures.push(`${c.id}: a consumer must produce no power (PowerOutput ${c.output})`);
  if (exempt.has(c.id)) {
    if (c.input >= floor) failures.push(`${c.id}: exempt, yet its ${c.input} hp already meets the ${floor} hp floor; remove the exemption`);
    rows.push([c.id, c.science, floor, c.input, 'exempt: ' + powerRule.exempt[c.id]]);
    continue;
  }
  if (c.input < floor) failures.push(`${c.id}: draws ${c.input} hp, below its ${floor} hp floor at ${c.science} science (call scaledPower in its generator)`);
  rows.push([c.id, c.science, floor, c.input, c.input === floor ? 'floor' : 'authored base above the floor']);
}
for (const id of exempt) {
  if (!ruled.some((c) => c.id === id)) failures.push(`power.exempt.${id}: no generated consumer at ${powerRule.scienceMin}+ science has this id`);
}

for (const [id, science, floor, input, note] of rows) {
  console.log(`${id.padEnd(28)} ${String(science).padStart(8)} sci  floor ${String(floor).padStart(7)}  draws ${String(input).padStart(7)} hp  ${note}`);
}
if (failures.length) {
  for (const failure of failures) console.error('FAIL ' + failure);
  process.exit(1);
}
console.log(`Power rule valid (${dataRoot}): ${rows.length} consumers at ${powerRule.scienceMin}+ science, ${exempt.size} exempt.`);
