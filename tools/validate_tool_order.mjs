// Left to right is the unlock order (user 2026-11-01: "the menu items are ordered
// correctly to guide them for buildings from left to right"). Checks the toolbar order
// of every group that holds a Deep Frontier tool or sub-group, in a generated Data root:
//   node tools/validate_tool_order.mjs [dataRoot] [--print]
//
// Visible order (Moddable Tool Groups 11.0.0, source-inspected; see tools/tool_groups.json):
// a group's children are the tools whose ToolGroupId names it (unless a group claims them
// with DoNotIncludePlaceableToolGroup), the tools it claims and the sub-groups whose
// ParentIds name it. Ids in the group's ChildrenOrderedIds (a Deep Frontier group's
// blueprint, or a native group's same-path partial with ChildrenOrderedIds#append) sort at
// 10, 20, ...; every other child sorts at its ToolOrder (tool) or Order (group). Dev-mode
// tools are hidden. A tool's science is its BuildingSpec.ScienceCost (a Deep Frontier
// same-path partial may raise a vanilla one); a sub-group's is the earliest unlock below it.
//
// Rules:
// - Inside a Deep Frontier group every tool (claims included) follows science ascending.
//   Equal science: a tool whose products (recipes or map gathering) another tool consumes
//   (recipe input, fuel or construction good) comes first; otherwise the smaller footprint
//   (X*Y), then the lower one (Z), comes first; tools equal on all of these may stand in any
//   order.
// - In a native group the vanilla and other-mod buttons keep their own order. The Deep
//   Frontier tools and sub-groups follow the same ascending rule among themselves, and each
//   stands at a place with the fewest science inversions against those buttons (a button
//   to its left with more science, or to its right with less; equal science is neutral).
// - Two children of a checked group never share an order value (the native sort would
//   break the tie arbitrarily).
// - Declared upgrades (tools/tool_groups.json upgrades; user 2026-11-02: the Reactor
//   Charging Bay right next to the Charging Station) stand immediately to the right of the
//   building they upgrade, in its group. That is their whole order rule: they are left out
//   of the science rules above, which every other tool keeps.
// Unlocking before construction goods or recipe inputs is tools/audit_progression.mjs's
// unlock-order check, with the reactor and power-plant order checks.
import {readFile, readdir, access} from 'node:fs/promises';
import {relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {CONFIG, VANILLA_RESOURCES, groupPath} from './tool_group_content.mjs';
import {loadProgressionData, MAP_SOURCES, recipeInputs} from './progression_data.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const args = process.argv.slice(2);
const print = args.includes('--print');
const dataRoot = resolve(args.find((a) => !a.startsWith('--')) ?? resolve(root, 'src', 'DeepFrontier', 'Data'));
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const posix = (path) => path.split(sep).join('/');
const vanillaRoot = resolve(root, ...VANILLA_RESOURCES);
const errors = [];

const config = await readJson(resolve(root, CONFIG));
const {buildings, recipes} = await loadProgressionData(dataRoot);
// upgrade template name (with the faction suffix) -> the template it upgrades
const upgrades = new Map(Object.entries(config.upgrades).map(([template, base]) => [`${template}.IronTeeth`, base]));

// ---- Tools: vanilla (Iron Teeth and Common collections), Deep Frontier, catalogued other mods ----
const tools = new Map();   // template name -> {name, origin, group, order, science, size, products, consumes}
const products = (b) => {
  const out = new Set(b.recipes.flatMap((id) => recipes.get(id)?.Products.map((p) => p.Id) ?? []));
  for (const [good, source] of Object.entries(MAP_SOURCES)) if (source.via.includes(b.id)) out.add(good);
  return out;
};
const consumes = (b) => new Set([...b.recipes.flatMap((id) => recipes.has(id) ? recipeInputs(recipes.get(id)) : []), ...b.cost.map(([g]) => g)]);
for (const b of buildings.values()) {
  let placeable = b.bp.PlaceableBlockObjectSpec;
  if (!placeable) continue;
  if (b.origin === 'vanilla') {
    const partial = resolve(dataRoot, `${b.path}.json`);
    if (await exists(partial)) placeable = {...placeable, ...((await readJson(partial)).PlaceableBlockObjectSpec ?? {})};
  }
  if (placeable.DevModeTool) continue;
  const size = b.bp.BlockObjectSpec?.Size;
  tools.set(b.id, {name: b.id, origin: b.origin, group: placeable.ToolGroupId, order: placeable.ToolOrder, science: b.science,
    size: size ? [size.X, size.Y, size.Z] : null, products: products(b), consumes: consumes(b)});
}
for (const [modId, mod] of Object.entries(config.externalMods)) {
  for (const [name, tool] of Object.entries(mod.templates)) {
    if (!Number.isInteger(tool.science)) { errors.push(`externalMods ${modId}: ${name} needs its science`); continue; }
    tools.set(name, {name, origin: modId, group: tool.toolGroup, order: null, science: tool.science, size: null, products: new Set(), consumes: new Set()});
  }
}

// ---- Groups: native (vanilla) specs merged with Deep Frontier partials, and Deep Frontier groups ----
const groups = new Map();   // id -> {id, deepFrontier, parents, order, claims, orderedIds, dropClaimed}
for (const file of await readdir(resolve(vanillaRoot, 'BlockObjectToolGroups'))) {
  if (!file.endsWith('.blueprint.json')) continue;
  const spec = (await readJson(resolve(vanillaRoot, 'BlockObjectToolGroups', file))).BlockObjectToolGroupSpec;
  if (spec) groups.set(spec.Id, {id: spec.Id, deepFrontier: false, parents: [], order: spec.Order, claims: [], orderedIds: [], dropClaimed: false});
}
for (const file of await readdir(resolve(dataRoot, 'BlockObjectToolGroups'))) {
  if (!file.endsWith('.blueprint.json')) continue;
  const blueprint = await readJson(resolve(dataRoot, 'BlockObjectToolGroups', file));
  const children = blueprint.ToolGroupChildrenSpec ?? {};
  if (blueprint.BlockObjectToolGroupSpec) {
    const spec = blueprint.BlockObjectToolGroupSpec;
    groups.set(spec.Id, {id: spec.Id, deepFrontier: true, parents: blueprint.ParentToolGroupSpec?.ParentIds ?? [], order: spec.Order,
      claims: children.ChildrenToolsTemplateNames ?? [], orderedIds: children.ChildrenOrderedIds ?? [], dropClaimed: Boolean(children.DoNotIncludePlaceableToolGroup)});
  } else {
    const id = file.replace(/^BlockObjectToolGroup\./, '').replace(/\.blueprint\.json$/, '');
    const native = groups.get(id);
    if (!native) { errors.push(`${posix(relative(dataRoot, resolve(dataRoot, 'BlockObjectToolGroups', file)))}: partial of an unknown native group`); continue; }
    if (children.ChildrenExplicitOrderedIds) errors.push(`${id}: ChildrenExplicitOrderedIds is not modelled here`);
    native.orderedIds = [...native.orderedIds, ...(children['ChildrenOrderedIds#append'] ?? [])];
  }
}
const claimedAway = new Set([...groups.values()].filter((g) => g.dropClaimed).flatMap((g) => g.claims));

// Children of a group with their visible order key and science.
const subtreeScience = new Map();
function scienceOf(child) {
  if (child.kind === 'tool') return child.tool.science;
  if (subtreeScience.has(child.id)) return subtreeScience.get(child.id);
  const values = childrenOf(child.id).map(scienceOf).filter((s) => s !== null);
  const value = values.length ? Math.min(...values) : null;
  subtreeScience.set(child.id, value);
  return value;
}
function childrenOf(groupId) {
  const group = groups.get(groupId);
  const list = [];
  for (const tool of tools.values()) if (tool.group === groupId && !claimedAway.has(tool.name)) list.push({kind: 'tool', id: tool.name, tool});
  for (const name of group.claims) if (tools.has(name)) list.push({kind: 'tool', id: name, tool: tools.get(name), claimed: true});
  for (const sub of groups.values()) if (sub.parents.includes(groupId)) list.push({kind: 'group', id: sub.id, group: sub});
  for (const child of list) {
    const index = group.orderedIds.indexOf(child.id);
    child.key = index >= 0 ? 10 * (index + 1) : child.kind === 'tool' ? child.tool.order : child.group.order;
    child.listed = index >= 0;
  }
  return list.sort((a, b) => a.key - b.key);
}
const deepFrontierChild = (child) => child.kind === 'group' ? child.group.deepFrontier : child.tool.origin === 'DeepFrontier';
const label = (child) => `${child.kind === 'group' ? '▸' : ''}${child.id.replace(/\.IronTeeth$/, '')} (${scienceOf(child) ?? '?'})`;

// a must come before b on a science tie.
function mustPrecede(a, b) {
  if (a.kind !== 'tool' || b.kind !== 'tool') return false;
  const feeds = (x, y) => [...x.tool.products].some((g) => y.tool.consumes.has(g));
  if (feeds(a, b) !== feeds(b, a)) return feeds(a, b);
  if (feeds(a, b)) return false;
  const [sa, sb] = [a.tool.size, b.tool.size];
  if (!sa || !sb) return false;
  const area = (s) => s[0] * s[1];
  return area(sa) < area(sb) || (area(sa) === area(sb) && sa[2] < sb[2]);
}
function checkAscending(groupId, list) {
  for (let i = 0; i < list.length; i++) for (let j = i + 1; j < list.length; j++) {
    const [a, b] = [list[i], list[j]];
    const [x, y] = [scienceOf(a), scienceOf(b)];
    if (x === null || y === null) continue;
    if (x > y) errors.push(`${groupId}: ${label(a)} stands left of ${label(b)}`);
    else if (x === y && mustPrecede(b, a)) errors.push(`${groupId}: ${label(b)} must come before ${label(a)} on the science tie (products or smaller footprint first)`);
  }
}

const report = {};
const checked = [...groups.values()].filter((g) => g.deepFrontier || childrenOf(g.id).some(deepFrontierChild));
const placedUpgrades = new Set();
for (const group of checked) {
  const all = childrenOf(group.id);
  report[group.id] = all.map(label);
  for (let i = 1; i < all.length; i++)
    if (all[i].key === all[i - 1].key) errors.push(`${group.id}: ${all[i - 1].id} and ${all[i].id} share order ${all[i].key}`);
  const isUpgrade = (child) => child.kind === 'tool' && upgrades.has(child.id);
  for (const [i, child] of all.entries()) {
    if (!isUpgrade(child)) continue;
    placedUpgrades.add(child.id);
    const base = upgrades.get(child.id);
    const at = all.findIndex((c) => c.kind === 'tool' && c.id === base);
    if (at < 0) errors.push(`${group.id}: ${child.id} upgrades ${base}, which is not in this group`);
    else if (at !== i - 1) errors.push(`${group.id}: ${child.id} must stand immediately right of ${base}, which it upgrades (it stands at ${i + 1}, ${base} at ${at + 1})`);
  }
  const list = all.filter((child) => !isUpgrade(child));
  if (group.deepFrontier) { checkAscending(group.id, list); continue; }
  const own = list.filter(deepFrontierChild);
  checkAscending(group.id, own);
  // Inversions of a Deep Frontier child against the native buttons, if it stood before fixed[p].
  const fixed = list.filter((child) => !deepFrontierChild(child) && scienceOf(child) !== null);
  const inversions = (s, p) => fixed.slice(0, p).filter((c) => scienceOf(c) > s).length + fixed.slice(p).filter((c) => scienceOf(c) < s).length;
  for (const child of own) {
    const s = scienceOf(child);
    if (s === null) continue;
    const at = fixed.filter((c) => c.key < child.key).length;
    const best = Math.min(...fixed.map((_, p) => inversions(s, p)), inversions(s, fixed.length));
    if (inversions(s, at) > best) {
      const places = [...Array(fixed.length + 1).keys()].filter((p) => inversions(s, p) === best)
        .map((p) => p === 0 ? `before ${fixed[0].id}` : p === fixed.length ? `after ${fixed.at(-1).id}` : `between ${fixed[p - 1].id} and ${fixed[p].id}`);
      errors.push(`${group.id}: ${label(child)} has ${inversions(s, at)} science inversions where it stands, ${best} ${places.join(' or ')}`);
    }
  }
}

for (const name of upgrades.keys()) if (!placedUpgrades.has(name)) errors.push(`upgrades: ${name} is in no toolbar group that holds Deep Frontier tools`);

if (print) for (const [id, row] of Object.entries(report)) console.log(`${id}: ${row.join(', ')}`);
if (errors.length) {
  console.error(`Tool order validation failed (${errors.length}):\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(JSON.stringify({status: 'tool-order-valid', groups: checked.length, upgrades: Object.fromEntries(upgrades), data: posix(relative(root, dataRoot))}));
