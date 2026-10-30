// Material cost rule (user 2026-10-30: "each building's construction materials
// must match what the building is visibly made of"). Rule data:
// tools/building_construction_costs.json materialRule; docs/progression.md
// "Material cost rule".
//
// A building's basis cost (late-game rule rows without gates, or its authored
// cost times its tier costFactor) keeps its machinery goods (Gear,
// MachineCore). The embodied value of its material goods is shared out over
// the material families its exported model shows (tools/building_material_mix.json,
// written by tools/asset-pipeline/measure_building_materials.py), in proportion
// to their area. Inside a family the goods are the tier's familyGoods that the
// settlement can make without this building, from buildings unlocked at or
// below its science (no construction good may need the building itself for
// its first unit). Amounts round up to a multiple of 5, so the value never
// falls. The deposit families (raw stone) are unpriced on the buildings that
// produce their goods: the pits and quarries show the deposit they work.
//
// The value table and the recipe/producer graph come from the generated data
// and are recorded in tools/material_cost_context.json:
//   node tools/material_costs.mjs --write [dataRoot]   record the context
//   node tools/material_costs.mjs --check [dataRoot]   fail when it is stale
// tools/audit_progression.mjs runs the same check, fails on a family the rule
// could not price ("concrete shown before Concrete exists"), on a stale mix
// record, and on any bootstrap cycle in the generated costs.
import {readFileSync, writeFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {loadProgressionData, reachableWithout, recipeInputs, MAP_SOURCES} from './progression_data.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const readJson = (path) => JSON.parse(readFileSync(resolve(root, path), 'utf8'));
const catalog = readJson('tools/building_construction_costs.json');
export const materialRule = catalog.materialRule;
const MIX_PATH = 'tools/building_material_mix.json';
const CONTEXT_PATH = 'tools/material_cost_context.json';

// ---- Rule data checks (fail at load, never default) ----
const rule = materialRule;
if (!rule) throw new Error('building_construction_costs.json: materialRule is missing');
const FAMILIES = Object.keys(rule.families ?? {});
const tierNames = Object.keys(catalog.lategameRule.tiers);
if (!FAMILIES.length) throw new Error('materialRule.families is empty');
for (const [f, spec] of Object.entries(rule.families)) {
  if (!['fail', 'unpriced'].includes(spec.whenUnavailable)) throw new Error(`materialRule.families.${f}.whenUnavailable must be fail or unpriced`);
  if (spec.whenUnavailable === 'fail' && !spec.failure) throw new Error(`materialRule.families.${f}: a failing family needs its failure text`);
}
if (Object.keys(rule.familyGoods ?? {}).sort().join() !== [...tierNames].sort().join()) throw new Error('materialRule.familyGoods must list exactly the late-game tiers');
for (const [tier, families] of Object.entries(rule.familyGoods)) {
  if (Object.keys(families).sort().join() !== [...FAMILIES].sort().join()) throw new Error(`materialRule.familyGoods.${tier} must list every family`);
  for (const [f, goods] of Object.entries(families)) {
    for (const [g, ratio] of Object.entries(goods)) if (!(ratio > 0)) throw new Error(`materialRule.familyGoods.${tier}.${f}.${g}: ratio must be positive`);
  }
}
export const MATERIAL_GOODS = new Set(Object.values(rule.familyGoods).flatMap((t) => Object.values(t).flatMap((g) => Object.keys(g))));
export const MACHINERY = new Set(rule.machinery);
for (const g of MACHINERY) if (MATERIAL_GOODS.has(g)) throw new Error(`materialRule: ${g} is both machinery and a family good`);
if (!(rule.minFamilyShare >= 0 && rule.minFamilyShare < 1)) throw new Error('materialRule.minFamilyShare must lie in [0, 1)');
for (const [material, family] of Object.entries(rule.materials)) {
  if (![...FAMILIES, 'unpriced', 'stone'].includes(family)) throw new Error(`materialRule.materials.${material}: unknown family ${family}`);
}
const DEPOSIT = rule.depositFamilies?.families;
if (!Array.isArray(DEPOSIT) || DEPOSIT.some((f) => !FAMILIES.includes(f))) throw new Error('materialRule.depositFamilies.families must list families');
// Every good a deposit family can name in any tier.
const DEPOSIT_GOODS = new Set(Object.values(rule.familyGoods).flatMap((t) => DEPOSIT.flatMap((f) => Object.keys(t[f]))));
if (!['global', 'buildingWorld'].includes(rule.value?.scope)) throw new Error('materialRule.value.scope must be global or buildingWorld');

const MIX = readJson(MIX_PATH);
export const materialMix = MIX.buildings;
for (const [id, entry] of Object.entries(materialMix)) {
  for (const f of Object.keys(entry.families)) if (![...FAMILIES, 'unpriced'].includes(f)) throw new Error(`${MIX_PATH} ${id}: unknown family ${f}`);
}

// Embodied recipe effort (materialRule.value) over a set of recipes: primary
// and map-gathered goods count primaryGood (liquids liquidGood), each recipe
// hour recipeHour, fuel its value / CyclesFuelLasts; a recipe's effort is
// shared equally by its product units; the cheapest route wins.
function effortValues(recipes, gathered) {
  const {liquids, primaryGood, liquidGood, recipeHour} = rule.value;
  const liquid = new Set(liquids);
  const value = new Map([...gathered].map((g) => [g, liquid.has(g) ? liquidGood : primaryGood]));
  for (let changed = true; changed;) {
    changed = false;
    for (const r of recipes) {
      if (!r.ingredients.every(([g]) => value.has(g)) || (r.fuel && !value.has(r.fuel))) continue;
      const effort = r.ingredients.reduce((s, [g, a]) => s + a * value.get(g), 0)
        + (r.fuel ? value.get(r.fuel) / r.cyclesFuelLasts : 0) + recipeHour * r.hours;
      const units = r.products.reduce((s, [, a]) => s + a, 0);
      for (const [g] of r.products) {
        const v = effort / units;
        if (!value.has(g) || v < value.get(g) - 1e-9) { value.set(g, v); changed = true; }
      }
    }
  }
  return value;
}

let context = null;
function loadContext() {
  if (context) return context;
  const raw = readJson(CONTEXT_PATH);
  const buildings = new Map(Object.entries(raw.buildings).map(([id, b]) => [id, {id, science: b.science, recipes: b.recipes, devOnly: b.devOnly, cost: []}]));
  const specs = new Map(Object.entries(raw.recipes));
  const recipes = new Map([...specs].map(([id, r]) => [id, {Id: id, Ingredients: r.ingredients.map(([g]) => ({Id: g})), Fuel: r.fuel,
    Products: r.products.map(([g]) => ({Id: g}))}]));
  context = {value: raw.value, specs, primary: new Set(raw.primary), graph: {buildings, recipes, primary: new Set(raw.primary)}, worlds: new Map()};
  return context;
}
// A building's science as recorded from the generated data (for tools that
// price every building without running its generator).
export function recordedScience(id) {
  const b = loadContext().graph.buildings.get(`${id}.IronTeeth`);
  if (!b) throw new Error(`${id}: not in ${CONTEXT_PATH} (generate it, then node tools/material_costs.mjs --write)`);
  return b.science;
}

// The goods a building can be built from, and their values: the world without
// the building, from buildings unlocked at or below its science. With
// value.scope 'buildingWorld' a good is valued by the routes of that world
// (Limestone from the pits for a building unlocked before the quarries);
// with 'global' by every active route.
function world(id, science) {
  const ctx = loadContext();
  const key = `${id}@${science}`;
  if (ctx.worlds.has(key)) return ctx.worlds.get(key);
  const self = `${id}.IronTeeth`;
  const available = reachableWithout(ctx.graph, self, science, false);
  let value;
  if (rule.value.scope === 'global') value = new Map(Object.entries(ctx.value));
  else {
    const inWorld = [...ctx.graph.buildings.values()].filter((b) => b.id !== self && b.science <= science && !b.devOnly);
    const recipes = [...new Set(inWorld.flatMap((b) => b.recipes))].map((r) => ctx.specs.get(r)).filter(Boolean);
    const gathered = new Set([...ctx.primary, ...Object.entries(MAP_SOURCES).filter(([, s]) => s.via.some((v) => inWorld.some((b) => b.id === v))).map(([g]) => g)]);
    value = effortValues(recipes, gathered);
  }
  const produces = new Set([...(ctx.graph.buildings.get(self)?.recipes ?? []).flatMap((r) => ctx.specs.get(r)?.products.map(([g]) => g) ?? []),
    ...Object.entries(MAP_SOURCES).filter(([, s]) => s.via.includes(self)).map(([g]) => g)]);
  const result = {available, value, producesDeposit: [...produces].some((g) => DEPOSIT_GOODS.has(g))};
  ctx.worlds.set(key, result);
  return result;
}
// Value of a good for one building (materialRule.value.scope).
export function materialValue(id, science, good) {
  const v = world(id, science).value.get(good);
  if (!(v >= 0)) throw new Error(`${id}: no value for ${good} in its world (${rule.value.scope})`);
  return v;
}

const ceil5 = (x) => Math.max(5, Math.ceil(x / 5 - 1e-9) * 5);

// Composition of one building: rows ([[good, amount]]), plus the families the
// rule could not price (failures), left unpriced, or folded as minor.
export function materialComposition(id, rows, science, tierName) {
  if (!Object.hasOwn(materialMix, id)) throw new Error(`${id}: no measured material mix in ${MIX_PATH} (run tools/asset-pipeline/measure_building_materials.py)`);
  if (!Number.isInteger(science) || science < 0) throw new Error(`${id}: invalid science ${science}`);
  const templates = rule.familyGoods[tierName];
  if (!templates) throw new Error(`${id}: unknown tier ${tierName}`);
  const {available, producesDeposit} = world(id, science);
  const value = (g) => materialValue(id, science, g);
  const area = Object.fromEntries(FAMILIES.map((f) => [f, materialMix[id].families[f] ?? 0]));
  const goodsOf = (f) => Object.entries(templates[f]).filter(([g]) => available.has(g));
  const failures = [], unpriced = [], folded = [];
  for (const f of FAMILIES) {
    if (!(area[f] > 0)) continue;
    const deposit = producesDeposit && DEPOSIT.includes(f);
    if (deposit || (!goodsOf(f).length && rule.families[f].whenUnavailable === 'unpriced')) {
      unpriced.push({family: f, reason: deposit ? 'deposit it works' : 'no producible good'});
      area[f] = 0;
    }
  }
  const total = Object.values(area).reduce((s, a) => s + a, 0);
  if (!(total > 0)) throw new Error(`${id}: the model shows no priced material`);
  const share = Object.fromEntries(FAMILIES.map((f) => [f, area[f] / total]));
  for (const f of FAMILIES) {
    if (!share[f]) continue;
    if (share[f] < rule.minFamilyShare) folded.push({family: f, share: share[f]});
    else if (!goodsOf(f).length) failures.push({family: f, share: share[f], failure: rule.families[f].failure});
    else continue;
    share[f] = 0;
  }
  const kept = Object.values(share).reduce((s, x) => s + x, 0);
  if (!(kept > 0)) throw new Error(`${id}: no family of its model can be priced`);
  for (const [g] of rows) if (!MATERIAL_GOODS.has(g) && !MACHINERY.has(g)) throw new Error(`${id}: basis good ${g} is neither a material family good nor machinery`);
  const materialTotal = rows.filter(([g]) => MATERIAL_GOODS.has(g)).reduce((s, [g, a]) => s + a * value(g), 0);
  const out = [];
  if (materialTotal > 0) {
    for (const f of FAMILIES) {
      if (!share[f]) continue;
      const familyValue = materialTotal * share[f] / kept;
      const goods = goodsOf(f);
      const unitValue = goods.reduce((s, [g, ratio]) => s + ratio * value(g), 0);
      for (const [g, ratio] of goods) out.push([g, ceil5(familyValue * ratio / unitValue)]);
    }
  }
  for (const [g, a] of rows) if (MACHINERY.has(g)) out.push([g, a]);
  return {rows: out, failures, unpriced, folded, shares: share};
}

export const materialCost = (id, rows, science, tierName) => materialComposition(id, rows, science, tierName).rows;

// ---- Context: value table and recipe graph from the generated data ----
export async function deriveContext(dataRoot) {
  const data = await loadProgressionData(dataRoot);
  const active = [...new Set([...data.buildings.values()].flatMap((b) => b.recipes))].sort().map((id) => {
    const r = data.recipes.get(id);
    if (!r) throw new Error(`recipe ${id} is selected by a building but missing`);
    if (r.Fuel && !(r.CyclesFuelLasts > 0)) throw new Error(`recipe ${id}: fuel ${r.Fuel} without a positive CyclesFuelLasts`);
    return r;
  });
  const recipes = Object.fromEntries(active.map((r) => [r.Id, {ingredients: r.Ingredients.map((i) => [i.Id, i.Amount]),
    ...(r.Fuel ? {fuel: r.Fuel, cyclesFuelLasts: r.CyclesFuelLasts} : {}), hours: r.CycleDurationInHours,
    products: r.Products.map((p) => [p.Id, p.Amount])}]));
  const value = effortValues(Object.values(recipes), new Set([...data.primary, ...Object.keys(MAP_SOURCES)]));
  const round = (v) => Math.round(v * 1e6) / 1e6;
  const buildings = Object.fromEntries([...data.buildings.values()].sort((a, b) => a.id.localeCompare(b.id))
    .map((b) => [b.id, {science: b.science, recipes: b.recipes, devOnly: Boolean(b.bp.PlaceableBlockObjectSpec?.DevModeTool)}]));
  return {
    _comment: 'Generated by node tools/material_costs.mjs --write from the generated data; do not edit. value: embodied recipe effort per good over every active route (materialRule.value). buildings and recipes: the producer graph the material rule uses to find the goods a building can be built from without itself, and their values in that world.',
    value: Object.fromEntries([...value].sort(([a], [b]) => a.localeCompare(b)).map(([g, v]) => [g, round(v)])),
    primary: [...data.primary].sort(), buildings, recipes,
  };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const mode = process.argv[2] ?? '';
  if (!['--write', '--check'].includes(mode)) throw new Error('Usage: node tools/material_costs.mjs --write|--check [dataRoot]');
  const dataRoot = resolve(root, process.argv[3] ?? 'src/DeepFrontier/Data');
  const derived = JSON.stringify(await deriveContext(dataRoot), null, 1) + '\n';
  if (mode === '--write') {
    writeFileSync(resolve(root, CONTEXT_PATH), derived, 'utf8');
    console.log(`Wrote ${CONTEXT_PATH}`);
  } else if (readFileSync(resolve(root, CONTEXT_PATH), 'utf8') !== derived) {
    throw new Error(`${CONTEXT_PATH} is stale: run node tools/material_costs.mjs --write, then regenerate`);
  } else console.log(`${CONTEXT_PATH} matches the generated data`);
}
