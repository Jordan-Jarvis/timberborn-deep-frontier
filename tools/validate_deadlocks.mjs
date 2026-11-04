// Deadlock audit of the generated Iron Teeth economy (vanilla + Deep Frontier):
// ways a player can get stuck that tools/audit_progression.mjs does not model
// because they lie outside recipes and construction costs. docs/deadlock-audit.md
// records the findings, the fixes and the proposals.
//
// Operating model (static; no rates, workforce, power supply or map placement):
// - A building runs only while it has its operating goods: workplace upkeep
//   (FrontierWorkplaceUpkeepSpec: production stops without it, WorkplaceUpkeep.cs),
//   goods a native consumer uses up (GoodConsumingBuildingSpec: fuel, supplies)
//   and the Deep Well's drill bits (DeepWellSpec). A building whose crew must be
//   trained specialists (FrontierSpecialistWorkplaceSpec) runs only once that
//   discipline can be taught: a Technical School program
//   (FrontierSpecialistSchoolSpec) whose supplies are all available. Reactor
//   Bots can staff any workplace instead (0.8.5), but the beaver path is the one
//   that must work, so the bot bypass is not counted.
// - Map sources (progression_data.mjs MAP_SOURCES) are finite (ruins, outcrops)
//   or renewable (shore fishing; radiation turning stored water into contaminated
//   water). A slow source is renewable only through a recharge: the Deep Ore
//   Sources' stock is finite, but an empty one recharges (DeepOreDepositSpec). A
//   good is slow exactly when a map-editor deposit of it recharges. Every map
//   source must be classified here.
// - A recipe of a map source's own building that makes that map good draws it
//   from the map (the Deep Drill bores the Deep Ore Sources of its district,
//   Scripts/DeepOre/DeepDrill.cs): it counts only as the map source, never as a
//   free recipe.
// - "Available" is a closure: goods from primary goods, the map sources allowed,
//   and the recipes of buildings that can run (inputs, fuel, operating goods and
//   discipline available). A good can never come from its own building's output
//   first: a building's operating goods gate all of its recipes.
//
// Checks (each failure names the chain):
// - renewable-economy: with every building standing and no finite map source,
//   every good the economy uses (recipe inputs and fuel, operating goods,
//   construction goods, the training supplies of every required discipline, the
//   foods a restaurant or grocery needs) is still produced. A good missing here
//   lives on a finite stock forever: when the stock runs out the chain stops
//   and cannot restart (e.g. a mine whose drill bits are made from what it mines).
// - discipline-trainable: every discipline a workplace requires can be taught
//   from renewable goods, and no training supply depends on a building staffed
//   by that same discipline (the closure only trains a discipline from goods
//   already available without it).
// - operating-unlock: at each Deep Frontier building's unlock (buildings unlocked at or below
//   it, built from producible goods, finite sources allowed, without the
//   building itself) its operating goods are producible, its discipline can be
//   taught, and a restaurant or grocery has enough of its foods. A building may
//   not unlock before it can run.
// - rebuild: each building's construction goods are produced, with every other
//   building standing and no finite map source, without the building itself (the
//   last copy of a building can be rebuilt once the map's finite stocks are gone).
//   Goods that already fail renewable-economy are not repeated here.
// - finite-replacement: for each finite map good, a renewable producer of it can
//   be built and run at its own unlock without that finite source (the other
//   finite sources and the buildings unlocked by then standing): a player who
//   spends the finite stock on anything else can still reach the replacement.
// - slow-replacement: for each slow map good, a producer other than its map source
//   (the Deep Mine for deep ore) can be built and run at its own unlock from the
//   recharge alone: a player who spent the deposits' stock reaches the real supply
//   (slowly) instead of living on the trickle forever.
// Accepted failures (ACCEPTED) carry a reason and fail when they no longer apply.
//
// Usage: node tools/validate_deadlocks.mjs [dataRoot] [--print]   (default src/DeepFrontier/Data)
import {readFileSync} from 'node:fs';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
import {loadProgressionData, MAP_SOURCES, recipeInputs} from './progression_data.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const args = process.argv.slice(2);
const print = args.includes('--print');
const data = resolve(root, args.find((a) => !a.startsWith('--')) ?? 'src/DeepFrontier/Data');
const {buildings, recipes, primary} = await loadProgressionData(data);

const errors = [];
const fail = (kind, key, message) => errors.push({kind, key, message});

// Every map source is classified; a new one must be added here explicitly.
const MAP_SOURCE_KIND = {
  ScrapMetal: {finite: true, why: 'ruins scavenged by the Scavenger Flag run out (the Efficient Mine recipes are the renewable route)'},
  DeepOre: {finite: false, slow: true, why: 'Deep Ore Sources bored by the Deep Drill: their stock is finite, but an empty source recharges (DeepOreDepositSpec, 20 every 5 days, about a tenth of one Deep Ore Processor), so deep ore stays renewable, slowly; the Deep Mine is the real supply'},
  Sandstone: {finite: true, why: 'Sandstone Outcrops dug by the pit run out (the Sandstone Quarry is the renewable route)'},
  Limestone: {finite: true, why: 'Limestone Outcrops dug by the pit run out (the Limestone Quarry is the renewable route)'},
  FreshFish: {finite: false, why: 'Fisher Flag shore fishing never runs out'},
  ContaminatedWater: {finite: false, why: 'radiation turns stored water into contaminated water (a waste, never a supply)'},
};
for (const good of Object.keys(MAP_SOURCES)) if (!MAP_SOURCE_KIND[good]) fail('map-source-kind', good, `MAP_SOURCES ${good} is not classified finite or renewable in validate_deadlocks.mjs`);
for (const good of Object.keys(MAP_SOURCE_KIND)) if (!MAP_SOURCES[good]) fail('map-source-kind', good, `MAP_SOURCE_KIND ${good} is not a MAP_SOURCES good`);
const FINITE = new Set(Object.keys(MAP_SOURCE_KIND).filter((g) => MAP_SOURCE_KIND[g].finite));
const SLOW = new Set(Object.keys(MAP_SOURCE_KIND).filter((g) => MAP_SOURCE_KIND[g].slow));
// Slow sources from the data: the goods of the map-editor deposits that recharge.
const readBlueprint = (path) => JSON.parse(readFileSync(resolve(data, path + '.json'), 'utf8').replace(/^\uFEFF/, ''));
const recharging = new Set(readBlueprint('TemplateCollections/TemplateCollection.MapEditor.Common.blueprint')
  .TemplateCollectionSpec['Blueprints#append'].map(readBlueprint).map((bp) => bp.DeepOreDepositSpec)
  .filter((d) => d && d.RechargeAmount > 0 && d.RechargeTimeInDays > 0).map((d) => d.GoodId));
for (const good of Object.keys(MAP_SOURCE_KIND)) {
  if (MAP_SOURCE_KIND[good].slow && MAP_SOURCE_KIND[good].finite) fail('map-source-kind', good, `${good} is classified both finite and slow`);
  if (Boolean(MAP_SOURCE_KIND[good].slow) !== recharging.has(good))
    fail('map-source-kind', good, `${good} is ${MAP_SOURCE_KIND[good].slow ? '' : 'not '}classified slow, but ${recharging.has(good) ? 'a map-editor deposit recharges it' : 'no map-editor deposit recharges it'}`);
}
// Recipes that draw a map good from the map: they count only as the map source.
const gathers = (b, good) => MAP_SOURCES[good]?.via.includes(b.id);

// Known failures kept by design, each with its reason (docs/deadlock-audit.md).
// None since 2026-11-03: the recharge of empty Deep Ore Sources makes drilled ore
// renewable (slowly), which closed D3 (the Deep Mine built from drilled ore) and D4
// (the quarries' Deep Iron against the mine's concrete lining); docs/deadlock-audit.md.
const ACCEPTED = {};

// Player buildings (placeable, not dev tools) and what each needs to run.
const players = [...buildings.values()].filter((b) => b.bp.PlaceableBlockObjectSpec && !b.bp.PlaceableBlockObjectSpec.DevModeTool);
const schoolPrograms = new Map();   // discipline -> [{school, supplies}]
for (const b of players) {
  for (const p of b.bp.FrontierSpecialistSchoolSpec?.Programs ?? []) {
    if (!p.Discipline || !(p.Supplies?.length)) fail('school-program', b.id, `${b.id}: a program needs a discipline and supplies`);
    (schoolPrograms.get(p.Discipline) ?? schoolPrograms.set(p.Discipline, []).get(p.Discipline)).push({school: b.id, supplies: p.Supplies.map((s) => s.GoodId)});
  }
}
const operation = new Map(players.map((b) => {
  const bp = b.bp;
  const upkeep = (bp.FrontierWorkplaceUpkeepSpec?.Goods ?? []).map((g) => g.GoodId);
  // A school's consumer lists every program's goods; it uses only the taught one's (the programs below).
  const consumed = bp.FrontierSpecialistSchoolSpec ? [] : (bp.GoodConsumingBuildingSpec?.ConsumedGoods ?? []).map((g) => g.GoodId);
  const bits = bp.DeepWellSpec?.DrillBitGoodId ? [bp.DeepWellSpec.DrillBitGoodId] : [];
  const required = [...new Set([...upkeep, ...consumed, ...bits])];
  const discipline = bp.FrontierSpecialistWorkplaceSpec?.Discipline ?? null;
  // Food services: the restaurant serves any of its foods; the grocery serves
  // the neighborhood only with MinimumStockedFoodTypes kinds in stock.
  const foods = bp.RestaurantSpec ? {goods: bp.RestaurantSpec.Foods, minimum: 1}
    : bp.GroceryStoreSpec ? {goods: bp.GroceryStoreSpec.Foods, minimum: bp.GroceryStoreSpec.MinimumStockedFoodTypes} : null;
  return [b.id, {upkeep, consumed: [...new Set([...consumed, ...bits])], required, discipline, foods}];
}));
for (const [good, source] of Object.entries(MAP_SOURCES)) {
  for (const via of source.via) if (!operation.has(via)) fail('map-source-kind', good, `MAP_SOURCES ${good}: ${via} is not a player building`);
}
for (const [id, op] of operation) {
  if (op.discipline && !schoolPrograms.has(op.discipline)) fail('discipline-trainable', id, `${id} needs ${op.discipline} specialists, and no school teaches ${op.discipline}`);
}

// Closure of available goods (see the header). Options: science (buildings
// unlocked at or below it), costGated (a building counts only once its
// construction goods are available), finite (map goods whose finite source is
// allowed: true, false, or a Set of goods), exclude (building ids).
function closure({science = Infinity, costGated = false, finite = true, exclude = new Set()} = {}) {
  const finiteAllowed = (good) => finite === true || (finite instanceof Set && finite.has(good));
  const pool = players.filter((b) => !exclude.has(b.id) && b.science <= science);
  const have = new Set(primary);
  const trained = new Set();
  const built = new Set();
  const runs = (b) => {
    const op = operation.get(b.id);
    return op.required.every((g) => have.has(g)) && (!op.discipline || trained.has(op.discipline));
  };
  for (let changed = true; changed;) {
    changed = false;
    const add = (g) => { if (!have.has(g)) { have.add(g); changed = true; } };
    for (const b of pool) {
      if (built.has(b.id) || (costGated && !b.cost.every(([g]) => have.has(g)))) continue;
      built.add(b.id); changed = true;
    }
    for (const [good, source] of Object.entries(MAP_SOURCES)) {
      if (FINITE.has(good) && !finiteAllowed(good)) continue;
      if (source.via.some((v) => built.has(v) && runs(buildings.get(v)))) add(good);
    }
    for (const [discipline, programs] of schoolPrograms) {
      if (trained.has(discipline)) continue;
      if (programs.some((p) => built.has(p.school) && p.supplies.every((g) => have.has(g)))) { trained.add(discipline); changed = true; }
    }
    for (const b of pool) {
      if (!built.has(b.id) || !runs(b)) continue;
      for (const id of b.recipes) {
        const r = recipes.get(id);
        if (r && recipeInputs(r).every((g) => have.has(g))) for (const p of r.Products) if (!gathers(b, p.Id)) add(p.Id);
      }
    }
  }
  return {have, trained, built};
}

// Why a good is missing from a closure: each producer and what blocks it.
const name = (id) => id.replace(/\.IronTeeth$/, '');
function why(good, c) {
  const reasons = [];
  for (const [g, source] of Object.entries(MAP_SOURCES)) {
    if (g !== good) continue;
    reasons.push(`map source ${source.via.map(name).join('/')}${FINITE.has(g) ? ' (finite: ' + MAP_SOURCE_KIND[g].why + ')' : SLOW.has(g) ? ' (slow: ' + MAP_SOURCE_KIND[g].why + ')' : ''}`);
  }
  for (const b of players) {
    for (const id of b.recipes) {
      const r = recipes.get(id);
      if (!r?.Products.some((p) => p.Id === good) || gathers(b, good)) continue;
      const op = operation.get(b.id);
      const blocks = [];
      if (!c.built.has(b.id)) blocks.push('building not available');
      const upkeep = op.required.filter((g) => !c.have.has(g));
      if (upkeep.length) blocks.push(`needs ${upkeep.join(', ')} to run`);
      if (op.discipline && !c.trained.has(op.discipline)) blocks.push(`needs ${op.discipline} specialists`);
      const inputs = recipeInputs(r).filter((g) => !c.have.has(g));
      if (inputs.length) blocks.push(`recipe needs ${inputs.join(', ')}`);
      reasons.push(`${id}@${name(b.id)}${blocks.length ? ' (' + blocks.join('; ') + ')' : ''}`);
    }
  }
  return reasons.length ? reasons.join(' | ') : 'no producer';
}

// Goods the economy uses.
const used = new Map();   // good -> [user]
const use = (good, user) => (used.get(good) ?? used.set(good, []).get(good)).push(user);
for (const b of players) {
  for (const id of b.recipes) { const r = recipes.get(id); if (r) for (const g of recipeInputs(r)) use(g, `${id}@${name(b.id)}`); }
  const op = operation.get(b.id);
  for (const g of op.upkeep) use(g, `upkeep@${name(b.id)}`);
  for (const g of op.consumed) use(g, `consumed@${name(b.id)}`);
  for (const [g] of b.cost) use(g, `cost@${name(b.id)}`);
}
const requiredDisciplines = new Map();   // discipline -> [building]
for (const [id, op] of operation) if (op.discipline) (requiredDisciplines.get(op.discipline) ?? requiredDisciplines.set(op.discipline, []).get(op.discipline)).push(id);
for (const [discipline] of requiredDisciplines) for (const p of schoolPrograms.get(discipline) ?? []) for (const g of p.supplies) use(g, `${discipline} training@${name(p.school)}`);

// 1. renewable-economy and discipline-trainable.
const renewable = closure({finite: false});
for (const [good, users] of [...used].sort(([a], [b]) => a.localeCompare(b))) {
  if (renewable.have.has(good)) continue;
  fail('renewable-economy', good, `${good} is only produced from a finite stock: used by ${users.slice(0, 6).join(', ')}${users.length > 6 ? ', ...' : ''}; producers: ${why(good, renewable)}`);
}
for (const [discipline, ids] of requiredDisciplines) {
  if (renewable.trained.has(discipline)) continue;
  const supplies = (schoolPrograms.get(discipline) ?? []).flatMap((p) => p.supplies).filter((g) => !renewable.have.has(g));
  fail('discipline-trainable', discipline, `${discipline} (needed by ${ids.map(name).join(', ')}) cannot be taught without finite stock: ${supplies.map((g) => `${g} <- ${why(g, renewable)}`).join(' || ')}`);
}
for (const [id, op] of operation) {
  if (!op.foods) continue;
  const served = op.foods.goods.filter((g) => renewable.have.has(g));
  if (served.length < op.foods.minimum) fail('renewable-economy', id, `${id} serves ${served.length} renewable foods of the ${op.foods.minimum} it needs`);
}

// 2. operating-unlock: each Deep Frontier building runs at its own unlock
//    (vanilla keeps its own order: its Decontamination Pod, 400, uses Extract
//    from the 600-science Centrifuge).
for (const b of players.filter((x) => x.origin === 'DeepFrontier')) {
  const op = operation.get(b.id);
  if (!op.required.length && !op.discipline && !op.foods) continue;
  const c = closure({science: b.science, costGated: true, exclude: new Set([b.id])});
  const missing = op.required.filter((g) => !c.have.has(g));
  if (missing.length) fail('operating-unlock', b.id, `${b.id} (${b.science}) cannot run at its unlock: ${missing.map((g) => `${g} <- ${why(g, c)}`).join(' || ')}`);
  if (op.discipline && !c.trained.has(op.discipline)) {
    const supplies = (schoolPrograms.get(op.discipline) ?? []).flatMap((p) => p.supplies).filter((g) => !c.have.has(g));
    fail('operating-unlock', b.id, `${b.id} (${b.science}) needs ${op.discipline} specialists, who cannot be taught at its unlock: ${supplies.map((g) => `${g} <- ${why(g, c)}`).join(' || ') || 'no school available'}`);
  }
  if (op.foods) {
    const served = op.foods.goods.filter((g) => c.have.has(g));
    if (served.length < op.foods.minimum) fail('operating-unlock', b.id, `${b.id} (${b.science}) has ${served.length} of its ${op.foods.minimum} foods at its unlock (${op.foods.goods.join(', ')})`);
  }
}

// 3. rebuild: construction goods without the building itself and without
//    finite stock. Only goods the renewable economy makes are checked here
//    (the others already fail renewable-economy), so a failure is a building
//    whose cost depends on its own output.
const outcome = new Map();   // accepted key -> failed?
const accepted = (key) => { if (ACCEPTED[key]) { outcome.set(key, true); return true; } return false; };
for (const b of players) {
  if (!b.cost.length) continue;
  const c = closure({finite: false, exclude: new Set([b.id])});
  const missing = b.cost.filter(([g]) => renewable.have.has(g) && !c.have.has(g)).map(([g]) => g);
  if (missing.length && !accepted(`rebuild:${b.id}`)) fail('rebuild', b.id, `${b.id} cannot be rebuilt once the finite stocks are gone: ${missing.map((g) => `${g} <- ${why(g, c)}`).join(' || ')}`);
}

// 4. finite-replacement: a renewable producer of each finite map good is
//    reachable at its own unlock without that finite source.
const replacements = [];
for (const good of FINITE) {
  const producers = players.filter((b) => !gathers(b, good) && b.recipes.some((id) => {
    const r = recipes.get(id);
    return r?.Products.some((p) => p.Id === good) && !recipeInputs(r).includes(good);
  }));
  if (!producers.length) { fail('finite-replacement', good, `${good}: no renewable producer (only the finite map source)`); continue; }
  const results = producers.map((b) => {
    const c = closure({science: b.science, finite: new Set([...FINITE].filter((g) => g !== good)), exclude: new Set([b.id])});
    const op = operation.get(b.id);
    const recipe = b.recipes.map((id) => recipes.get(id)).find((r) => r?.Products.some((p) => p.Id === good) && !recipeInputs(r).includes(good));
    const missing = [...new Set([...b.cost.map(([g]) => g), ...op.required, ...recipeInputs(recipe)])].filter((g) => !c.have.has(g));
    const untrained = op.discipline && !c.trained.has(op.discipline) ? [`${op.discipline} specialists`] : [];
    return {b, missing: [...missing.map((g) => `${g} <- ${why(g, c)}`), ...untrained]};
  });
  replacements.push({good, producers: results.map((r) => `${name(r.b.id)} (${r.b.science})${r.missing.length ? ' blocked' : ''}`)});
  if (results.every((r) => r.missing.length) && !accepted(`finite-replacement:${good}`))
    fail('finite-replacement', good, `${good}: once its finite source is spent no renewable producer can be reached: ${results.map((r) => `${name(r.b.id)}: ${r.missing.join(' || ')}`).join(' ;; ')}`);
}
// 5. slow-replacement: a producer of each slow map good other than its map
//    source is reachable at its own unlock from the recharge alone (every
//    finite source spent).
for (const good of SLOW) {
  const producers = players.filter((b) => !gathers(b, good) && b.recipes.some((id) => {
    const r = recipes.get(id);
    return r?.Products.some((p) => p.Id === good) && !recipeInputs(r).includes(good);
  }));
  if (!producers.length) { fail('slow-replacement', good, `${good}: no producer besides its slow map source`); continue; }
  const results = producers.map((b) => {
    const c = closure({science: b.science, finite: false, exclude: new Set([b.id])});
    const op = operation.get(b.id);
    const recipe = b.recipes.map((id) => recipes.get(id)).find((r) => r?.Products.some((p) => p.Id === good) && !recipeInputs(r).includes(good));
    const missing = [...new Set([...b.cost.map(([g]) => g), ...op.required, ...recipeInputs(recipe)])].filter((g) => !c.have.has(g));
    const untrained = op.discipline && !c.trained.has(op.discipline) ? [`${op.discipline} specialists`] : [];
    return {b, missing: [...missing.map((g) => `${g} <- ${why(g, c)}`), ...untrained]};
  });
  replacements.push({good, producers: results.map((r) => `${name(r.b.id)} (${r.b.science}, from the recharge)${r.missing.length ? ' blocked' : ''}`)});
  if (results.every((r) => r.missing.length))
    fail('slow-replacement', good, `${good}: from its slow map source alone no other producer can be reached: ${results.map((r) => `${name(r.b.id)}: ${r.missing.join(' || ')}`).join(' ;; ')}`);
}
for (const key of Object.keys(ACCEPTED)) if (!outcome.get(key)) fail('accepted-stale', key, `ACCEPTED ${key} no longer fails; remove it from validate_deadlocks.mjs and docs/deadlock-audit.md`);

// Evidence: how each discipline is trained from renewable goods.
const training = [...requiredDisciplines].map(([discipline, ids]) => {
  const programs = schoolPrograms.get(discipline) ?? [];
  const supplies = [...new Set(programs.flatMap((p) => p.supplies))];
  const route = supplies.map((g) => {
    const producers = players.filter((b) => b.recipes.some((id) => recipes.get(id)?.Products.some((p) => p.Id === g)));
    return `${g} from ${producers.map((b) => name(b.id) + (operation.get(b.id).discipline ? ` [${operation.get(b.id).discipline}]` : '')).join('/') || 'map'}`;
  });
  return `${discipline} for ${ids.map(name).join(', ')}: ${route.join('; ')}`;
});

if (print) {
  console.log('Training routes:'); for (const t of training) console.log('  ' + t);
  console.log('Renewable replacements:'); for (const r of replacements) console.log(`  ${r.good}: ${r.producers.join(', ')}`);
}
for (const [key, reason] of Object.entries(ACCEPTED)) if (outcome.get(key)) console.log(`accepted ${key}: ${reason.slice(0, 120)}...`);
if (errors.length) {
  console.error(`Deadlock validation failed (${errors.length}):`);
  for (const e of errors) console.error(`  [${e.kind}] ${e.message}`);
  process.exit(1);
}
console.log(`Deadlock validation passed: ${players.length} player buildings, ${used.size} goods used, all renewable; disciplines ${[...requiredDisciplines.keys()].join(', ')} trainable from renewable goods; every building runs at its unlock; slow sources (renewable only through a recharge) ${[...SLOW].join(', ') || 'none'}, each with a reachable real supply; ${Object.keys(ACCEPTED).length} accepted by design.`);
