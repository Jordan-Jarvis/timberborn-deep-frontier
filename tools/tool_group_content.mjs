// Deep Frontier toolbar sub-groups (tools/tool_groups.json): Moddable Tool Groups (a required
// mod) shows a BlockObjectToolGroupSpec with ParentToolGroupSpec.ParentIds as a button inside
// that native group, and a building whose PlaceableBlockObjectSpec.ToolGroupId names the
// sub-group appears in it (ModdableToolGroupSpecService, Moddable Tool Groups 11.0.0).
// Writes BlockObjectToolGroups/BlockObjectToolGroup.<Id>.blueprint.json, moves the listed
// buildings and appends the group names to Localizations/enUS.csv. Runs at the end of
// canonical generation (create_vertical_slice_content.mjs), after every building exists, or
// standalone on a generated Data root:
//   node tools/tool_group_content.mjs [dataRoot]
// Checked by tools/validate_tool_groups.mjs. Fails without writing anything when a listed
// building is missing, listed twice, or the parent is not a native group.
import {readFile, writeFile, mkdir, access} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const CONFIG = 'tools/tool_groups.json';
const COLLECTION = 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json';
const VANILLA_GROUPS = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources', 'BlockObjectToolGroups'];
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const exists = (path) => access(path).then(() => true, () => false);
const csvCell = (value) => (/[",\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value);

export const groupPath = (id) => `BlockObjectToolGroups/BlockObjectToolGroup.${id}.blueprint.json`;
export const nameKey = (id) => `ToolGroups.${id}`;

export function groupBlueprint(id, group, icon) {
  return {
    BlockObjectToolGroupSpec: {Id: id, Order: group.order, NameLocKey: nameKey(id), Icon: icon, FallbackGroup: false},
    ParentToolGroupSpec: {ParentIds: [group.parent]},
  };
}

// Computes every change without writing; errors is empty when it may apply.
export async function planToolGroups({root = repo, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const config = await readJson(resolve(root, CONFIG));
  const errors = [];
  const byTemplate = new Map();
  for (const id of (await readJson(resolve(dataRoot, COLLECTION))).TemplateCollectionSpec['Blueprints#append']) {
    const path = resolve(dataRoot, `${id}.json`);
    if (!await exists(path)) continue;
    const blueprint = await readJson(path);
    const name = blueprint.TemplateSpec?.TemplateName?.replace(/\.IronTeeth$/, '');
    if (name && blueprint.PlaceableBlockObjectSpec) byTemplate.set(name, {path, blueprint});
  }
  const files = new Map();
  const groups = [];
  const listed = new Set();
  for (const [id, group] of Object.entries(config.groups)) {
    if (!/^DeepFrontier[A-Z][A-Za-z]+$/.test(id)) errors.push(`group ${id}: the id must be DeepFrontier<Name>`);
    if (!await exists(resolve(root, ...VANILLA_GROUPS, `BlockObjectToolGroup.${group.parent}.blueprint.json`)))
      errors.push(`group ${id}: parent ${group.parent} is not a native tool group`);
    if (!Number.isInteger(group.order)) errors.push(`group ${id}: order must be an integer`);
    if (!group.name) errors.push(`group ${id}: name is required`);
    if (!group.templates?.includes(group.icon)) errors.push(`group ${id}: icon ${group.icon} must be one of its templates`);
    for (const template of group.templates ?? []) {
      if (listed.has(template)) { errors.push(`${template} is listed in two groups`); continue; }
      listed.add(template);
      const entry = byTemplate.get(template);
      if (!entry) { errors.push(`group ${id}: ${template} is not a generated Deep Frontier building`); continue; }
      const placeable = entry.blueprint.PlaceableBlockObjectSpec;
      if (placeable.ToolGroupId?.startsWith('DeepFrontier')) errors.push(`${template} is already in ${placeable.ToolGroupId}; regenerate it from its producer`);
      files.set(entry.path, {...entry.blueprint, PlaceableBlockObjectSpec: {...placeable, ToolGroupId: id}});
    }
    const icon = byTemplate.get(group.icon)?.blueprint.LabeledEntitySpec?.Icon;
    if (!icon) errors.push(`group ${id}: ${group.icon} has no LabeledEntitySpec icon`);
    groups.push({id, group, blueprint: groupBlueprint(id, group, icon)});
  }
  const localizationPath = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  if (lines.at(-1) !== '') errors.push('enUS.csv must end with a newline');
  const keys = new Set(lines.map((line) => line.split(',')[0]));
  for (const {id} of groups) if (keys.has(nameKey(id))) errors.push(`localization ${nameKey(id)} already exists`);
  return {config, errors, files, groups, lines, localizationPath};
}

export async function applyToolGroups({root = repo, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const {errors, files, groups, lines, localizationPath} = await planToolGroups({root, dataRoot});
  if (errors.length) throw new Error(`Tool groups not applied:\n  ${errors.join('\n  ')}`);
  for (const [path, blueprint] of files) await writeJson(path, blueprint);
  for (const {id, blueprint} of groups) await writeJson(resolve(dataRoot, groupPath(id)), blueprint);
  lines.pop();
  for (const {id, group} of groups) lines.push([nameKey(id), group.name, 'Deep Frontier toolbar group'].map(csvCell).join(','));
  await writeFile(localizationPath, `${lines.join('\n')}\n`, 'utf8');
  console.log(`Tool groups: ${groups.length} sub-groups, ${files.size} buildings moved.`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await applyToolGroups(process.argv[2] ? {dataRoot: resolve(process.argv[2])} : {});
}
