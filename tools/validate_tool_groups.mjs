// Checks the Deep Frontier toolbar sub-groups (tools/tool_groups.json, written by
// tools/tool_group_content.mjs) in a generated Data root:
//   node tools/validate_tool_groups.mjs [dataRoot]
// Every group blueprint matches the catalog, every listed building sits in its group, every
// Deep Frontier group a building names is declared, and every group has a localized name.
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {CONFIG, groupBlueprint, groupPath, nameKey} from './tool_group_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(process.argv[2] ?? resolve(root, 'src', 'DeepFrontier', 'Data'));
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const errors = [];

const config = await readJson(resolve(root, CONFIG));
const collection = (await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json')))
  .TemplateCollectionSpec['Blueprints#append'];
const buildings = new Map();
for (const id of collection) {
  const path = resolve(dataRoot, `${id}.json`);
  if (!await exists(path)) continue;
  const blueprint = await readJson(path);
  if (blueprint.PlaceableBlockObjectSpec) buildings.set(blueprint.TemplateSpec.TemplateName.replace(/\.IronTeeth$/, ''), blueprint);
}
const csv = await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8');
for (const [id, group] of Object.entries(config.groups)) {
  const path = resolve(dataRoot, groupPath(id));
  const icon = buildings.get(group.icon)?.LabeledEntitySpec?.Icon;
  if (!await exists(path)) errors.push(`${groupPath(id)} was not written`);
  else if (!same(await readJson(path), groupBlueprint(id, group, icon))) errors.push(`${groupPath(id)} differs from the catalog`);
  if (!csv.includes(`\n${nameKey(id)},`)) errors.push(`enUS.csv lacks ${nameKey(id)}`);
  const orders = new Map();
  for (const template of group.templates) {
    const placeable = buildings.get(template)?.PlaceableBlockObjectSpec;
    if (placeable?.ToolGroupId !== id) errors.push(`${template} is in ${placeable?.ToolGroupId}, expected ${id}`);
    else if (orders.has(placeable.ToolOrder)) errors.push(`${id}: ${template} and ${orders.get(placeable.ToolOrder)} share ToolOrder ${placeable.ToolOrder}`);
    else orders.set(placeable.ToolOrder, template);
  }
}
for (const [template, blueprint] of buildings) {
  const group = blueprint.PlaceableBlockObjectSpec.ToolGroupId;
  if (group?.startsWith('DeepFrontier') && !Object.hasOwn(config.groups, group)) errors.push(`${template} names the undeclared group ${group}`);
}
const written = (await readdir(resolve(dataRoot, 'BlockObjectToolGroups')).catch(() => [])).filter((f) => f.endsWith('.blueprint.json'));
for (const file of written)
  if (!Object.keys(config.groups).some((id) => groupPath(id).endsWith(file))) errors.push(`BlockObjectToolGroups/${file} is not in the catalog`);

if (errors.length) {
  console.error(`Tool group validation failed (${errors.length}):\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(JSON.stringify({status: 'tool-groups-valid', groups: Object.keys(config.groups).length,
  buildings: Object.values(config.groups).reduce((n, g) => n + g.templates.length, 0)}));
