// Static progression audit of the generated Iron Teeth data (vanilla + Deep
// Frontier): reachability of every good a building or active recipe needs,
// unlock-order inversions, tool-menu collisions and the late-game cost rule.
//
// Reachability model (static, documented in docs/progression.md):
// - A vanilla good no vanilla recipe produces is primary (gathered, grown,
//   pumped or scavenged) and available at science 0.
// - MAP_SOURCES are goods gathered by a non-recipe workplace: vanilla scrap
//   from ruins, and Deep Frontier goods from authored map objects.
// - A building is usable at max(its science, availability of its costs).
// - Planned buildings (frontier_progression.json plannedBuildings, art in
//   progress) count as producers at max(their science, their cost tier's
//   goods); their routes are marked planned.
// - Every Deep Frontier recipe must be run by a generated or planned building.
// - Unlock order fails when a building unlocks before one of its construction
//   goods, or before any of its recipes can run.
// - Bootstrap (user 2026-10-30: "we don't want to require concrete on a
//   building required to make concrete the first time around"): every good of
//   a building's cost must be producible by the settlement without that
//   building, from buildings unlocked at or below its science whose own costs
//   are producible the same way. A failure is a bootstrap cycle.
// - Material rule (tools/material_costs.mjs): measured mixes and the recorded
//   context must match the generated data; a family the rule could not price
//   fails with its failure text ("concrete shown before Concrete exists"); a
//   cost's material goods and family value shares must follow the rule.
// - A recipe's products are available at max(its building, its ingredients
//   and fuel). The cheapest such route wins; availability is that route's
//   largest single unlock ("gate") and the summed science of the distinct
//   unlocks on that route ("cumulative").
// It does not model rates, workforce, power supply, map placement or runtime.
//
// Usage: node tools/audit_progression.mjs [dataRoot]   (default src/DeepFrontier/Data)
// Writes outputs/progression-audit.json and exits 1 when a failure is found.
import {readFile, writeFile, mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {fileURLToPath} from 'node:url';
import {resolve, relative} from 'node:path';
import {catalog as costCatalog, rule as costRule, lategameCost, tierForScience, LATEGAME_IDS, PLANNED} from './lategame_costs.mjs';
import {loadProgressionData, reachableWithout, MAP_SOURCES} from './progression_data.mjs';
import {materialComposition, materialMix, materialRule, MATERIAL_GOODS, materialValue, deriveContext} from './material_costs.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const data = resolve(root, process.argv[2] ?? 'src/DeepFrontier/Data');
const {buildings, recipes, goods, modGoods, modRecipeIds} = await loadProgressionData(data);

const failures = [];
const warnings = [];
const fail = (kind, detail) => failures.push({kind, ...detail});
const warn = (kind, detail) => warnings.push({kind, ...detail});

// Active recipes: those some buildable template selects.
const producers = new Map();   // good -> [{recipe, building}]
for (const b of buildings.values()) {
  for (const id of b.recipes) {
    const r = recipes.get(id);
    if (!r) { fail('missing-recipe', {building: b.id, recipe: id}); continue; }
    for (const p of r.Products) (producers.get(p.Id) ?? producers.set(p.Id, []).get(p.Id)).push({recipe: r, building: b});
  }
}
// Planned producers: generated buildings take precedence once integrated.
const planned = PLANNED.filter((p) => !buildings.has(`${p.id}.IronTeeth`)).map((p) => {
  const tier = costRule.tiers[p.costTier];
  const cost = [...Object.keys(tier.per100BuiltCells), ...(tier.concretePerGroundCell > 0 ? ['Concrete'] : [])].map((g) => [g, 1]);
  return {id: `${p.id} (planned)`, origin: 'planned', science: p.scienceUnlock, cost, recipes: p.recipes, bp: {}};
});
for (const b of planned) {
  for (const id of b.recipes) {
    const r = recipes.get(id);
    if (!r) { fail('missing-recipe', {building: b.id, recipe: id}); continue; }
    for (const p of r.Products) (producers.get(p.Id) ?? producers.set(p.Id, []).get(p.Id)).push({recipe: r, building: b});
  }
}
const plannedById = new Map(planned.map((b) => [b.id, b]));
const anyBuilding = (id) => buildings.get(id) ?? plannedById.get(id);

const vanillaRecipeProducts = new Set([...buildings.values()].filter((b) => b.origin === 'vanilla')
  .flatMap((b) => b.recipes.flatMap((id) => recipes.get(id)?.Products.map((p) => p.Id) ?? [])));
const avail = new Map();         // good -> {gate, route}
const buildingAvail = (b) => Math.max(b.science, ...b.cost.map(([g]) => avail.get(g)?.gate ?? Infinity));
for (const g of goods) if (!modGoods.has(g) && !vanillaRecipeProducts.has(g)) avail.set(g, {gate: 0, route: {primary: true}});
for (let changed = true; changed;) {
  changed = false;
  const offer = (good, gate, route) => {
    if (gate < (avail.get(good)?.gate ?? Infinity)) { avail.set(good, {gate, route}); changed = true; }
  };
  for (const [good, source] of Object.entries(MAP_SOURCES)) {
    for (const via of source.via) offer(good, buildingAvail(buildings.get(via)), {map: source.note, building: via});
  }
  for (const [good, list] of producers) {
    for (const {recipe, building} of list) {
      const inputs = [...recipe.Ingredients.map((i) => i.Id), ...(recipe.Fuel ? [recipe.Fuel] : [])].filter((i) => i !== good);
      offer(good, Math.max(buildingAvail(building), ...inputs.map((i) => avail.get(i)?.gate ?? Infinity)), {recipe: recipe.Id, building: building.id});
    }
  }
}
// Distinct unlocks on the chosen route of a good / a building.
const routeMemo = new Map();
function routeUnlocks(good, stack = new Set()) {
  if (routeMemo.has(good)) return routeMemo.get(good);
  const entry = avail.get(good);
  if (!entry || entry.route.primary || stack.has(good)) return new Set();
  stack.add(good);
  const building = anyBuilding(entry.route.building);
  const set = new Set(buildingUnlocks(building, stack));
  if (entry.route.recipe) {
    const r = recipes.get(entry.route.recipe);
    for (const i of [...r.Ingredients.map((x) => x.Id), ...(r.Fuel ? [r.Fuel] : [])]) for (const u of routeUnlocks(i, stack)) set.add(u);
  }
  stack.delete(good);
  routeMemo.set(good, set);
  return set;
}
function buildingUnlocks(b, stack = new Set()) {
  const set = new Set(b.science > 0 ? [b.id] : []);
  for (const [g] of b.cost) for (const u of routeUnlocks(g, stack)) set.add(u);
  return set;
}
const cumulative = (set) => [...set].reduce((sum, id) => sum + anyBuilding(id).science, 0);

// 1. Goods needed by Deep Frontier buildings and their active recipes.
const modBuildings = [...buildings.values()].filter((b) => b.origin === 'DeepFrontier');
const rows = [];
for (const b of modBuildings.sort((x, y) => x.science - y.science)) {
  const unreachableCost = b.cost.filter(([g]) => !avail.has(g)).map(([g]) => g);
  if (unreachableCost.length) fail('unproducible-construction-good', {building: b.id, goods: unreachableCost});
  const usable = buildingAvail(b);
  const late = b.cost.filter(([g]) => (avail.get(g)?.gate ?? Infinity) > b.science)
    .map(([g]) => `${g} (${avail.get(g) ? avail.get(g).gate : 'never'})`);
  // A building may not unlock before its construction goods (cheapest route).
  if (!unreachableCost.length && late.length) fail('construction-good-unlocks-later', {building: b.id, science: b.science, goods: late});
  const recipeIssues = [];
  const laterRecipes = [];
  for (const id of b.recipes) {
    const r = recipes.get(id);
    if (!r) continue;
    const missing = [...r.Ingredients.map((i) => i.Id), ...(r.Fuel ? [r.Fuel] : [])].filter((i) => !avail.has(i));
    if (missing.length) { recipeIssues.push(`${id}: ${missing.join(', ')}`); fail('unproducible-recipe-input', {building: b.id, recipe: id, goods: missing}); }
    const later = [...r.Ingredients.map((i) => i.Id), ...(r.Fuel ? [r.Fuel] : [])]
      .filter((i) => avail.has(i) && avail.get(i).gate > b.science).map((i) => `${i} (${avail.get(i).gate})`);
    if (later.length) laterRecipes.push({recipe: id, goods: later});
  }
  // Fail when none of a building's recipes can run at its unlock; a later
  // extra recipe on a working building is only a warning.
  if (laterRecipes.length && laterRecipes.length === b.recipes.length) fail('recipe-input-unlocks-later', {building: b.id, science: b.science, recipes: laterRecipes});
  else for (const r of laterRecipes) warn('recipe-input-unlocks-later', {building: b.id, science: b.science, ...r});
  rows.push({building: b.id, science: b.science, usableAt: Number.isFinite(usable) ? usable : null,
    cumulativeScience: Number.isFinite(usable) ? cumulative(buildingUnlocks(b)) : null,
    workers: b.bp.WorkplaceSpec?.MaxWorkers ?? 0, powerIn: b.bp.MechanicalNodeSpec?.PowerInput ?? 0,
    powerOut: b.bp.MechanicalNodeSpec?.PowerOutput ?? 0, cost: b.cost, recipes: b.recipes, recipeIssues});
}
// Recipes appended to vanilla templates: their inputs must be producible.
// The vanilla building shows them from its own unlock, so inputs that unlock
// later are reported as warnings.
for (const b of buildings.values()) {
  for (const id of b.appended ?? []) {
    const r = recipes.get(id);
    if (!r) continue;
    const inputs = [...r.Ingredients.map((i) => i.Id), ...(r.Fuel ? [r.Fuel] : [])];
    const missing = inputs.filter((i) => !avail.has(i));
    if (missing.length) fail('unproducible-recipe-input', {building: b.id, recipe: id, goods: missing});
    const later = inputs.filter((i) => avail.has(i) && avail.get(i).gate > b.science).map((i) => `${i} (${avail.get(i).gate})`);
    if (later.length) warn('recipe-input-unlocks-later', {building: b.id, science: b.science, recipe: id, goods: later});
  }
}
// 2. Deep Frontier goods: producers and reachability.
const goodRows = [];
for (const g of [...modGoods].sort()) {
  const entry = avail.get(g);
  goodRows.push({good: g, availableAt: entry ? entry.gate : null,
    cumulativeScience: entry ? cumulative(routeUnlocks(g)) : null, route: entry?.route ?? null,
    producers: (producers.get(g) ?? []).map((p) => `${p.recipe.Id}@${p.building.id}`)});
}
// Every Deep Frontier recipe needs a generated or planned building.
const active = new Set([...buildings.values(), ...planned].flatMap((b) => b.recipes));
const unusedRecipes = [...modRecipeIds].filter((id) => !active.has(id)).sort();
if (unusedRecipes.length) fail('recipe-without-building', {recipes: unusedRecipes});

// Native ManufactoryDropdownProvider (1.1.2.8) finds the chosen recipe by its
// DisplayLocKey (SingleOrDefault), so recipes of one building must not share one.
for (const b of [...buildings.values(), ...planned]) {
  const keys = b.recipes.map((id) => recipes.get(id)?.DisplayLocKey).filter(Boolean);
  const shared = [...new Set(keys.filter((k, i) => keys.indexOf(k) !== i))];
  if (shared.length) fail('recipe-display-key-collision', {building: b.id, keys: shared});
}

// 3. Tool menus: unique order inside each group (player tools only).
const menus = new Map();
for (const b of buildings.values()) {
  const p = b.bp.PlaceableBlockObjectSpec;
  if (!p || p.DevModeTool) continue;
  const key = `${p.ToolGroupId}#${p.ToolOrder}`;
  (menus.get(key) ?? menus.set(key, []).get(key)).push(b.id);
}
for (const [key, ids] of menus) if (ids.length > 1) fail('tool-order-collision', {slot: key, buildings: ids});

// 4. Late-game construction rule and science band.
for (const id of LATEGAME_IDS) {
  const b = buildings.get(`${id}.IronTeeth`);
  if (!b) { fail('lategame-missing', {building: id}); continue; }
  const tier = costCatalog.lategameTier[id];
  if (tierForScience(b.science) !== tier) { fail('lategame-tier-band', {building: id, science: b.science, tier, band: tierForScience(b.science)}); continue; }
  const expected = await lategameCost(id, b.science);
  if (JSON.stringify(expected) !== JSON.stringify(b.cost)) fail('lategame-cost-rule', {building: id, expected, actual: b.cost});
}

// 4b. Bootstrap: no construction good may need its own building (or a later
// one) for its first unit.
const graph = {buildings: new Map([...buildings].map(([id, b]) => [id, {...b, devOnly: Boolean(b.bp.PlaceableBlockObjectSpec?.DevModeTool)}])), recipes,
  primary: new Set([...goods].filter((g) => !modGoods.has(g) && !vanillaRecipeProducts.has(g)))};
for (const b of modBuildings) {
  if (!b.cost.length) continue;
  const have = reachableWithout(graph, b.id, b.science, true);
  const missing = b.cost.filter(([g]) => !have.has(g)).map(([g]) => g);
  if (missing.length) fail('bootstrap-cycle', {building: b.id, science: b.science, goods: missing,
    detail: 'these goods cannot be produced without this building, or only by buildings unlocked after it'});
}

// 4c. Material rule (tools/material_costs.mjs, materialRule).
const structures = new Set((JSON.parse(await readFile(resolve(root, 'tools/structural_content.json'), 'utf8'))).buildings.map((b) => b.id));
const contextNow = JSON.stringify(await deriveContext(data), null, 1) + '\n';
if (contextNow !== await readFile(resolve(root, 'tools/material_cost_context.json'), 'utf8')) fail('material-context-stale', {file: 'tools/material_cost_context.json', fix: 'node tools/material_costs.mjs --write, then regenerate'});
const ruleBuildings = modBuildings.filter((b) => b.cost.length && !structures.has(b.id.replace(/\.IronTeeth$/, '')));
for (const id of Object.keys(materialMix)) if (!ruleBuildings.some((b) => b.id === `${id}.IronTeeth`)) fail('material-mix-unknown', {building: id});
for (const b of ruleBuildings) {
  const id = b.id.replace(/\.IronTeeth$/, '');
  const mix = materialMix[id];
  if (!mix) { fail('material-mix-missing', {building: id, fix: 'python tools/asset-pipeline/measure_building_materials.py'}); continue; }
  const model = b.bp.Children?.['#Finished']?.TimbermeshSpec?.Model;
  if (model !== mix.model) { fail('material-mix-stale', {building: id, model, recorded: mix.model}); continue; }
  const sha = createHash('sha256').update(await readFile(resolve(data, model + '.timbermesh'))).digest('hex');
  if (sha !== mix.sha256) { fail('material-mix-stale', {building: id, model, fix: 'python tools/asset-pipeline/measure_building_materials.py'}); continue; }
  const tier = tierForScience(b.science);
  const gates = costCatalog.lategameGates[id] ?? [];
  const rows = b.cost.map(([g, a]) => [g, a - (gates.find(([x]) => x === g)?.[1] ?? 0)]).filter(([, a]) => a > 0);
  const comp = materialComposition(id, rows, b.science, tier);
  for (const f of comp.failures) fail('material-unpriced-family', {building: id, family: f.family, share: +f.share.toFixed(3), failure: f.failure});
  // The cost's material goods must be exactly the rule's goods, and each
  // family's value share must match the measured share within the rounding
  // (each amount rounds up by less than 5 units).
  const goodsOf = (rs) => rs.filter(([g]) => MATERIAL_GOODS.has(g)).map(([g]) => g).sort().join();
  if (goodsOf(rows) !== goodsOf(comp.rows)) { fail('material-rule-goods', {building: id, actual: goodsOf(rows), expected: goodsOf(comp.rows)}); continue; }
  const material = rows.filter(([g]) => MATERIAL_GOODS.has(g));
  const total = material.reduce((sum, [g, a]) => sum + a * materialValue(id, b.science, g), 0);
  const tolerance = material.reduce((sum, [g]) => sum + 5 * materialValue(id, b.science, g), 0) / total;
  const kept = Object.values(comp.shares).reduce((sum, x) => sum + x, 0);
  for (const [f, share] of Object.entries(comp.shares)) {
    const familyGoods = new Set(Object.keys(materialRule.familyGoods[tier][f]));
    const actual = material.filter(([g]) => familyGoods.has(g)).reduce((sum, [g, a]) => sum + a * materialValue(id, b.science, g), 0) / total;
    if (Math.abs(actual - share / kept) > tolerance + 1e-9) fail('material-rule-share', {building: id, family: f, actual: +actual.toFixed(3), measured: +(share / kept).toFixed(3), tolerance: +tolerance.toFixed(3)});
  }
}

// 5. Power: the best single generator unlocked at or below each consumer's science.
const generators = [...buildings.values()].filter((b) => (b.bp.MechanicalNodeSpec?.PowerOutput ?? 0) > 0 && !b.bp.PlaceableBlockObjectSpec?.DevModeTool)
  .map((b) => ({id: b.id, science: b.science, hp: b.bp.MechanicalNodeSpec.PowerOutput})).sort((a, b) => a.science - b.science);
const power = rows.filter((r) => r.powerIn > 0).map((r) => {
  const best = generators.filter((g) => g.science <= r.science).sort((a, b) => b.hp - a.hp)[0];
  return {building: r.building, science: r.science, demand: r.powerIn, bestGenerator: best.id, generatorHp: best.hp,
    generatorsNeeded: Math.ceil(r.powerIn / best.hp)};
});
for (const p of power) if (p.generatorsNeeded > 10) warn('power-gap', p);

const report = {checkedAt: new Date().toISOString(), data: relative(root, data),
  model: 'Static reachability; gate = largest single unlock on the cheapest route; cumulative = summed science of its distinct unlocks. No rates, workforce, power supply, map placement or runtime behaviour.',
  mapSources: MAP_SOURCES, costRule: costRule.foundation + '; ' + costRule.superstructure,
  failures, warnings, buildings: rows, goods: goodRows, generators, power};
await mkdir(resolve(root, 'outputs'), {recursive: true});
await writeFile(resolve(root, 'outputs/progression-audit.json'), JSON.stringify(report, null, 2) + '\n');
const summary = {failures: failures.length, warnings: warnings.length,
  byKind: Object.fromEntries([...new Set(failures.map((f) => f.kind))].map((k) => [k, failures.filter((f) => f.kind === k).length]))};
console.log(JSON.stringify(summary));
for (const f of failures) console.log('FAIL', JSON.stringify(f));
for (const w of warnings) console.log('WARN', JSON.stringify(w));
if (failures.length) process.exitCode = 1;
