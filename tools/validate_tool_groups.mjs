// Checks the Deep Frontier toolbar sub-groups (tools/tool_groups.json, written by
// tools/tool_group_content.mjs) in a generated Data root:
//   node tools/validate_tool_groups.mjs [dataRoot]
// - Every group blueprint matches the catalog, every listed building sits in its group, every
//   Deep Frontier group a building names is declared, and every group has a localized name.
// - Every claimed or ordered template exists: vanilla (vendor Resources), Deep Frontier, or an
//   externalMods entry that matches the installed Workshop package (tools/dev-environment.json
//   workshopContent), so a typo cannot hide a tool silently. A claimed vanilla tool is a visible
//   tool of the same tab, and not hidden by a Deep Frontier partial.
// - externalMods: the package's manifest Id and Version match, a required mod is in the
//   manifest's RequiredMods and an optional one is not; loose blueprints give each template's
//   tool group and icon, an asset-bundle mod's IronTeeth TemplateCollection matches.
// - nativeOrders list every vanilla Iron Teeth, Deep Frontier and externalMods tool of that group.
// Prints which groups appear only with an optional mod.
import {readFile, readdir, access} from 'node:fs/promises';
import {relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {devEnvironment} from './dev_environment.mjs';
import {CONFIG, VANILLA_RESOURCES, groupBlueprint, groupPath, nameKey, nativeGroupExists, nativeOrderBlueprint, subtreeTools, vanillaTools} from './tool_group_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(process.argv[2] ?? resolve(root, 'src', 'DeepFrontier', 'Data'));
const FACTION = '.IronTeeth';
// Installed packages are read as the game reads them: Newtonsoft accepts a BOM, comments, trailing
// commas and raw line breaks inside strings, and some installed packages rely on that (the same
// reading as tools/validate_mod_dependencies.mjs).
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, '').replace(/[\u0000-\u001f]/g, ' ')
  .replace(/\/\*[\s\S]*?\*\//g, '').replace(/,(\s*[}\]])/g, '$1'));
const exists = (path) => access(path).then(() => true, () => false);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const posix = (path) => path.split(sep).join('/');
const errors = [];

const config = await readJson(resolve(root, CONFIG));
const manifest = await readJson(resolve(root, 'src', 'DeepFrontier', 'manifest.json'));
const requiredMods = new Set(manifest.RequiredMods.map((mod) => mod.Id));

// ---- Deep Frontier buildings (generated) ----
const collection = (await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json')))
  .TemplateCollectionSpec['Blueprints#append'];
const buildings = new Map();
for (const id of collection) {
  const path = resolve(dataRoot, `${id}.json`);
  if (!await exists(path)) continue;
  const blueprint = await readJson(path);
  if (blueprint.PlaceableBlockObjectSpec) buildings.set(blueprint.TemplateSpec.TemplateName.replace(/\.IronTeeth$/, ''), blueprint);
}
const groupIds = new Set(Object.keys(config.groups));
// A Deep Frontier building's native group: the group it sits in, or that group's native root.
const nativeRoot = (id) => { while (groupIds.has(id)) id = config.groups[id].parent; return id; };

// ---- Vanilla ----
const vanilla = await vanillaTools(root);
const vanillaResources = resolve(root, ...VANILLA_RESOURCES);
const ironTeethCollections = new Set();
for (const name of ['TemplateCollection.Buildings.IronTeeth.blueprint.json', 'TemplateCollection.Buildings.Common.blueprint.json'])
  for (const path of (await readJson(resolve(vanillaResources, 'TemplateCollections', name))).TemplateCollectionSpec.Blueprints) ironTeethCollections.add(path);
const vanillaIronTeeth = (tool) => ironTeethCollections.has(posix(relative(vanillaResources, tool.path)).replace(/\.json$/, ''));

// ---- externalMods against the installed packages ----
const dev = await devEnvironment(root, ['workshopContent']);
const gameVersion = manifest.MinimumGameVersion;
const versionKey = (text) => text.split('.').map(Number);
const compare = (a, b) => { const x = versionKey(a), y = versionKey(b); for (let i = 0; i < Math.max(x.length, y.length); i++) if ((x[i] ?? 0) !== (y[i] ?? 0)) return (x[i] ?? 0) - (y[i] ?? 0); return 0; };
// Timberborn.Modding ModRepository.GetModDirectory: the version-* folder for the running game
// when the package has any, else the package root.
async function packageFolder(item) {
  const versions = (await readdir(item, {withFileTypes: true}))
    .filter((entry) => entry.isDirectory() && /^version-/i.test(entry.name))
    .map((entry) => ({path: resolve(item, entry.name), version: entry.name.slice('version-'.length)}))
    .filter((entry) => compare(entry.version, gameVersion) <= 0)
    .sort((a, b) => compare(b.version, a.version));
  return versions.length ? versions[0].path : item;
}
async function looseBlueprints(dir) {
  const out = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) out.push(...await looseBlueprints(path));
    else if (entry.name.endsWith('.blueprint.json') && !entry.name.endsWith('.optional.blueprint.json')) out.push(path);
  }
  return out;
}
const external = new Map();
for (const [modId, mod] of Object.entries(config.externalMods)) {
  for (const [name, tool] of Object.entries(mod.templates)) external.set(name, {...tool, modId, optional: mod.optional});
  if (mod.optional && requiredMods.has(modId)) errors.push(`externalMods ${modId}: optional, but the manifest requires it`);
  if (!mod.optional && !requiredMods.has(modId)) errors.push(`externalMods ${modId}: required, but not in the manifest's RequiredMods`);
  const item = resolve(dev.workshopContent, mod.workshopId);
  if (!await exists(item)) { errors.push(`externalMods ${modId}: Workshop item ${mod.workshopId} is not installed, so its templates cannot be checked`); continue; }
  const folder = await packageFolder(item);
  const installed = await readJson(resolve(folder, 'manifest.json'));
  if (installed.Id !== modId) errors.push(`externalMods ${modId}: Workshop item ${mod.workshopId} is ${installed.Id}`);
  if (installed.Version !== mod.version) errors.push(`externalMods ${modId}: installed ${installed.Version}, catalog read ${mod.version}; re-read its templates`);
  if (mod.blueprints === 'loose') {
    const tools = new Map();
    for (const path of await looseBlueprints(folder)) {
      const blueprint = await readJson(path);
      const name = blueprint.TemplateSpec?.TemplateName;
      if (name && blueprint.PlaceableBlockObjectSpec) tools.set(name, {toolGroup: blueprint.PlaceableBlockObjectSpec.ToolGroupId, icon: blueprint.LabeledEntitySpec?.Icon});
    }
    for (const [name, tool] of Object.entries(mod.templates)) {
      const found = tools.get(name);
      if (!found) errors.push(`externalMods ${modId}: ${name} is not in the installed package`);
      else if (!same(found, {toolGroup: tool.toolGroup, icon: tool.icon})) errors.push(`externalMods ${modId}: ${name} is ${JSON.stringify(found)} installed, ${JSON.stringify(tool)} in the catalog`);
    }
  } else if (mod.blueprints === 'assetBundle') {
    const listed = (await readJson(resolve(folder, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'))).TemplateCollectionSpec['Blueprints#append'];
    if (!same(listed, mod.collection)) errors.push(`externalMods ${modId}: the installed IronTeeth TemplateCollection changed; re-read its templates from the asset bundle`);
  } else errors.push(`externalMods ${modId}: blueprints must be "loose" or "assetBundle"`);
}

// Where a claimed or ordered template comes from.
function origin(name) {
  if (vanilla.has(name)) return {source: 'vanilla', ...vanilla.get(name)};
  if (external.has(name)) return {source: external.get(name).modId, ...external.get(name)};
  if (name.endsWith(FACTION) && buildings.has(name.slice(0, -FACTION.length))) {
    const blueprint = buildings.get(name.slice(0, -FACTION.length));
    return {source: 'DeepFrontier', toolGroup: nativeRoot(blueprint.PlaceableBlockObjectSpec.ToolGroupId), icon: blueprint.LabeledEntitySpec?.Icon};
  }
  return null;
}
const optionalMod = (name) => (external.get(name)?.optional ? external.get(name).modId : null);

// ---- Groups ----
const csv = await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8');
const claimed = new Set();
const report = {optionalOnly: {}, withOptionalTools: {}};
for (const [id, group] of Object.entries(config.groups)) {
  const tabId = nativeRoot(id);
  if (!await nativeGroupExists(root, tabId)) errors.push(`${id}: ${group.parent} leads to ${tabId}, not a native tool group`);
  const subtree = subtreeTools(config, id);
  const iconName = subtree.includes(group.icon) ? group.icon : subtree.includes(`${group.icon}${FACTION}`) ? `${group.icon}${FACTION}` : null;
  const icon = iconName ? origin(iconName)?.icon : undefined;
  if (!icon) errors.push(`${id}: icon ${group.icon} is not a tool in the group or below it`);
  const path = resolve(dataRoot, groupPath(id));
  if (!await exists(path)) errors.push(`${groupPath(id)} was not written`);
  else if (!same(await readJson(path), groupBlueprint(id, group, icon))) errors.push(`${groupPath(id)} differs from the catalog`);
  if (!csv.includes(`\n${nameKey(id)},`)) errors.push(`enUS.csv lacks ${nameKey(id)}`);
  const orders = new Map();
  for (const template of group.templates ?? []) {
    const placeable = buildings.get(template)?.PlaceableBlockObjectSpec;
    if (placeable?.ToolGroupId !== id) errors.push(`${template} is in ${placeable?.ToolGroupId}, expected ${id}`);
    else if (!group.claims && orders.has(placeable.ToolOrder)) errors.push(`${id}: ${template} and ${orders.get(placeable.ToolOrder)} share ToolOrder ${placeable.ToolOrder}`);
    else orders.set(placeable.ToolOrder, template);
  }
  for (const name of group.claims ?? []) {
    if (claimed.has(name)) errors.push(`${name} is claimed twice`);
    claimed.add(name);
    const from = origin(name);
    if (!from || from.source === 'DeepFrontier') { errors.push(`${id}: claim ${name} is neither vanilla nor an externalMods template`); continue; }
    if (from.toolGroup !== tabId) errors.push(`${id}: claim ${name} is a ${from.toolGroup} tool, not ${tabId}`);
    if (from.source === 'vanilla') {
      if (from.devModeTool) errors.push(`${id}: claim ${name} is a vanilla dev tool`);
      if (!vanillaIronTeeth(from)) errors.push(`${id}: claim ${name} is not in the vanilla Iron Teeth building collections`);
      const partial = resolve(dataRoot, relative(vanillaResources, from.path));
      if (await exists(partial) && (await readJson(partial)).PlaceableBlockObjectSpec?.DevModeTool === true) errors.push(`${id}: claim ${name} is hidden by Deep Frontier's partial blueprint`);
    }
  }
  const mods = new Set(subtree.map(optionalMod));
  if (mods.size === 1 && !mods.has(null)) report.optionalOnly[id] = [...mods][0];
  else if ([...mods].some(Boolean)) report.withOptionalTools[id] = [...mods].filter(Boolean);
}
for (const [template, blueprint] of buildings) {
  const group = blueprint.PlaceableBlockObjectSpec.ToolGroupId;
  if (group?.startsWith('DeepFrontier') && !groupIds.has(group)) errors.push(`${template} names the undeclared group ${group}`);
}

// ---- Native group orders ----
for (const [nativeId, ids] of Object.entries(config.nativeOrders)) {
  const path = resolve(dataRoot, groupPath(nativeId));
  if (!await exists(path)) errors.push(`${groupPath(nativeId)} was not written`);
  else if (!same(await readJson(path), nativeOrderBlueprint(ids))) errors.push(`${groupPath(nativeId)} differs from nativeOrders`);
  for (const name of ids) {
    const from = origin(name);
    if (!from) errors.push(`nativeOrders ${nativeId}: ${name} is not a vanilla, Deep Frontier or externalMods tool`);
    else if (from.toolGroup !== nativeId) errors.push(`nativeOrders ${nativeId}: ${name} is a ${from.toolGroup} tool`);
  }
  const members = [
    ...[...vanilla].filter(([, tool]) => tool.toolGroup === nativeId && !tool.devModeTool && vanillaIronTeeth(tool)).map(([name]) => name),
    ...[...buildings].filter(([, b]) => b.PlaceableBlockObjectSpec.ToolGroupId === nativeId && !b.PlaceableBlockObjectSpec.DevModeTool).map(([name]) => `${name}${FACTION}`),
    ...[...external].filter(([, tool]) => tool.toolGroup === nativeId).map(([name]) => name),
  ];
  for (const name of members) if (!ids.includes(name) && !claimed.has(name)) errors.push(`nativeOrders ${nativeId}: ${name} is a ${nativeId} tool but not ordered`);
}

const expectedFiles = new Set([...groupIds, ...Object.keys(config.nativeOrders)].map((id) => groupPath(id).split('/').at(-1)));
const written = (await readdir(resolve(dataRoot, 'BlockObjectToolGroups')).catch(() => [])).filter((f) => f.endsWith('.blueprint.json'));
for (const file of written) if (!expectedFiles.has(file)) errors.push(`BlockObjectToolGroups/${file} is not in the catalog`);

if (errors.length) {
  console.error(`Tool group validation failed (${errors.length}):\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(JSON.stringify({status: 'tool-groups-valid', groups: groupIds.size,
  buildings: Object.values(config.groups).reduce((n, g) => n + (g.templates?.length ?? 0), 0),
  claims: claimed.size, nativeOrders: Object.keys(config.nativeOrders), ...report}));
