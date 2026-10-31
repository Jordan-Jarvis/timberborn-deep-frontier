// Deep Frontier toolbar sub-groups (tools/tool_groups.json; see its $comment for the
// Moddable Tool Groups 11.0.0 contracts). Moddable Tool Groups (a required mod) shows a
// BlockObjectToolGroupSpec with ParentToolGroupSpec.ParentIds as a button inside that group;
// a building whose PlaceableBlockObjectSpec.ToolGroupId names it, or a template its
// ToolGroupChildrenSpec.ChildrenToolsTemplateNames lists, appears in it
// (ModdableToolGroupSpecService). Writes:
// - BlockObjectToolGroups/BlockObjectToolGroup.<Id>.blueprint.json for every group;
// - the ToolGroupId of the listed Deep Frontier buildings;
// - BlockObjectToolGroups/BlockObjectToolGroup.<Native>.blueprint.json, a same-path partial of a
//   native group carrying nativeOrders;
// - the group names in Localizations/enUS.csv.
// Runs at the end of canonical generation (create_vertical_slice_content.mjs), after every
// building exists, or standalone on a generated Data root:
//   node tools/tool_group_content.mjs [dataRoot]
// Checked by tools/validate_tool_groups.mjs, which also checks claims against the installed
// packages. Fails without writing anything when the catalog is inconsistent.
import {readFile, writeFile, mkdir, access, readdir} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const CONFIG = 'tools/tool_groups.json';
export const VANILLA_RESOURCES = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];
const COLLECTION = 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json';
const FACTION = '.IronTeeth';
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const exists = (path) => access(path).then(() => true, () => false);
const csvCell = (value) => (/[",\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value);

export const groupPath = (id) => `BlockObjectToolGroups/BlockObjectToolGroup.${id}.blueprint.json`;
export const nameKey = (id) => `ToolGroups.${id}`;
export const nativeGroupExists = (root, id) => exists(resolve(root, ...VANILLA_RESOURCES, groupPath(id)));

// Every vanilla template that has a PlaceableBlockObjectSpec: name -> {toolGroup, icon, devModeTool, path}.
export async function vanillaTools(root = repo) {
  const tools = new Map();
  const walk = async (dir) => {
    for (const entry of await readdir(dir, {withFileTypes: true})) {
      const path = resolve(dir, entry.name);
      if (entry.isDirectory()) await walk(path);
      else if (entry.name.endsWith('.blueprint.json')) {
        const blueprint = await readJson(path);
        const placeable = blueprint.PlaceableBlockObjectSpec;
        const name = blueprint.TemplateSpec?.TemplateName;
        if (placeable && name) tools.set(name, {toolGroup: placeable.ToolGroupId, icon: blueprint.LabeledEntitySpec?.Icon, devModeTool: placeable.DevModeTool === true, path});
      }
    }
  };
  await walk(resolve(root, ...VANILLA_RESOURCES, 'Buildings'));
  return tools;
}

// The group's own tools and every tool below it, as template names (Deep Frontier ones with the suffix).
export function subtreeTools(config, id) {
  const group = config.groups[id];
  const own = [...(group.claims ?? []), ...(group.templates ?? []).map((t) => `${t}${FACTION}`)];
  const children = Object.keys(config.groups).filter((child) => config.groups[child].parent === id);
  return [...own, ...children.flatMap((child) => subtreeTools(config, child))];
}

export function groupBlueprint(id, group, icon) {
  const blueprint = {
    BlockObjectToolGroupSpec: {Id: id, Order: group.order, NameLocKey: nameKey(id), Icon: icon, FallbackGroup: false},
    ParentToolGroupSpec: {ParentIds: [group.parent]},
  };
  if (group.claims?.length) {
    blueprint.ToolGroupChildrenSpec = {
      ChildrenToolsTemplateNames: group.claims,
      DoNotIncludePlaceableToolGroup: true,
      ChildrenOrderedIds: [...group.claims, ...(group.templates ?? []).map((t) => `${t}${FACTION}`)],
    };
  }
  return blueprint;
}

export const nativeOrderBlueprint = (ids) => ({ToolGroupChildrenSpec: {'ChildrenOrderedIds#append': ids}});

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
  const vanilla = await vanillaTools(root);
  const external = new Map();
  for (const [modId, mod] of Object.entries(config.externalMods))
    for (const [name, tool] of Object.entries(mod.templates)) external.set(name, {...tool, modId, optional: mod.optional});
  // Where a claimed or ordered template comes from: {source, toolGroup, icon, optionalMod}.
  const origin = (name) => {
    if (vanilla.has(name)) return {source: 'vanilla', ...vanilla.get(name), optionalMod: null};
    const tool = external.get(name);
    if (tool) return {source: tool.modId, toolGroup: tool.toolGroup, icon: tool.icon, optionalMod: tool.optional ? tool.modId : null};
    if (name.endsWith(FACTION) && byTemplate.has(name.slice(0, -FACTION.length))) {
      const blueprint = byTemplate.get(name.slice(0, -FACTION.length)).blueprint;
      return {source: 'DeepFrontier', toolGroup: blueprint.PlaceableBlockObjectSpec.ToolGroupId, icon: blueprint.LabeledEntitySpec?.Icon, optionalMod: null};
    }
    return null;
  };
  const rootGroup = (id) => {
    const seen = new Set();
    while (Object.hasOwn(config.groups, id)) {
      if (seen.has(id)) return null;
      seen.add(id);
      id = config.groups[id].parent;
    }
    return id;
  };

  const files = new Map();
  const groups = [];
  const listed = new Set();
  const claimed = new Set();
  for (const [id, group] of Object.entries(config.groups)) {
    if (!/^DeepFrontier[A-Z][A-Za-z]+$/.test(id)) errors.push(`group ${id}: the id must be DeepFrontier<Name>`);
    const nativeRoot = rootGroup(id);
    if (!nativeRoot) errors.push(`group ${id}: its parents form a cycle`);
    else if (!await nativeGroupExists(root, nativeRoot)) errors.push(`group ${id}: ${group.parent} is neither a native tool group nor a declared group`);
    if (!Number.isInteger(group.order)) errors.push(`group ${id}: order must be an integer`);
    if (!group.name) errors.push(`group ${id}: name is required`);
    const children = Object.keys(config.groups).filter((child) => config.groups[child].parent === id);
    const ownTools = (group.claims?.length ?? 0) + (group.templates?.length ?? 0);
    if (children.length && ownTools) errors.push(`group ${id}: holds both tools and sub-groups`);
    if (!children.length && !ownTools) errors.push(`group ${id}: holds nothing`);
    for (const template of group.templates ?? []) {
      if (listed.has(template)) { errors.push(`${template} is listed in two groups`); continue; }
      listed.add(template);
      const entry = byTemplate.get(template);
      if (!entry) { errors.push(`group ${id}: ${template} is not a generated Deep Frontier building`); continue; }
      const placeable = entry.blueprint.PlaceableBlockObjectSpec;
      if (placeable.ToolGroupId?.startsWith('DeepFrontier')) errors.push(`${template} is already in ${placeable.ToolGroupId}; regenerate it from its producer`);
      files.set(entry.path, {...entry.blueprint, PlaceableBlockObjectSpec: {...placeable, ToolGroupId: id}});
    }
    for (const name of group.claims ?? []) {
      if (claimed.has(name)) { errors.push(`${name} is claimed by two groups`); continue; }
      claimed.add(name);
      const from = origin(name);
      if (!from || from.source === 'DeepFrontier') errors.push(`group ${id}: claim ${name} is neither vanilla nor in externalMods (Deep Frontier buildings go in templates)`);
      else if (from.toolGroup !== nativeRoot) errors.push(`group ${id}: claim ${name} is a ${from.toolGroup} tool, not ${nativeRoot}`);
    }
    const subtree = subtreeTools(config, id);
    const iconName = group.icon && (subtree.includes(group.icon) ? group.icon : subtree.includes(`${group.icon}${FACTION}`) ? `${group.icon}${FACTION}` : null);
    const iconFrom = iconName && origin(iconName);
    if (!iconFrom?.icon) errors.push(`group ${id}: icon ${group.icon} must be a tool in the group or below it, with a LabeledEntitySpec icon`);
    else if (iconFrom.optionalMod && subtree.some((name) => origin(name)?.optionalMod !== iconFrom.optionalMod))
      errors.push(`group ${id}: icon ${group.icon} comes from the optional ${iconFrom.optionalMod}, but the group also shows without it`);
    groups.push({id, group, blueprint: groupBlueprint(id, group, iconFrom?.icon)});
  }

  const natives = [];
  for (const [nativeId, ids] of Object.entries(config.nativeOrders)) {
    if (!await nativeGroupExists(root, nativeId)) errors.push(`nativeOrders ${nativeId}: not a native tool group`);
    if (new Set(ids).size !== ids.length) errors.push(`nativeOrders ${nativeId}: lists a template twice`);
    for (const name of ids) {
      const from = origin(name);
      if (!from) errors.push(`nativeOrders ${nativeId}: ${name} is not a vanilla, externalMods or Deep Frontier tool`);
      else if (from.toolGroup !== nativeId) errors.push(`nativeOrders ${nativeId}: ${name} is a ${from.toolGroup} tool`);
      if (claimed.has(name)) errors.push(`nativeOrders ${nativeId}: ${name} is claimed by a sub-group`);
    }
    natives.push({id: nativeId, blueprint: nativeOrderBlueprint(ids)});
  }

  const localizationPath = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  if (lines.at(-1) !== '') errors.push('enUS.csv must end with a newline');
  const keys = new Set(lines.map((line) => line.split(',')[0]));
  for (const {id} of groups) if (keys.has(nameKey(id))) errors.push(`localization ${nameKey(id)} already exists`);
  return {config, errors, files, groups, natives, lines, localizationPath, vanilla, origin};
}

export async function applyToolGroups({root = repo, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const {errors, files, groups, natives, lines, localizationPath} = await planToolGroups({root, dataRoot});
  if (errors.length) throw new Error(`Tool groups not applied:\n  ${errors.join('\n  ')}`);
  for (const [path, blueprint] of files) await writeJson(path, blueprint);
  for (const {id, blueprint} of groups) await writeJson(resolve(dataRoot, groupPath(id)), blueprint);
  for (const {id, blueprint} of natives) await writeJson(resolve(dataRoot, groupPath(id)), blueprint);
  lines.pop();
  for (const {id, group} of groups) lines.push([nameKey(id), group.name, 'Deep Frontier toolbar group'].map(csvCell).join(','));
  await writeFile(localizationPath, `${lines.join('\n')}\n`, 'utf8');
  const claims = groups.reduce((n, {group}) => n + (group.claims?.length ?? 0), 0);
  console.log(`Tool groups: ${groups.length} sub-groups, ${files.size} buildings moved, ${claims} tools claimed, ${natives.length} native groups ordered.`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await applyToolGroups(process.argv[2] ? {dataRoot: resolve(process.argv[2])} : {});
}
