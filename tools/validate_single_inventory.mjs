// Static check: no Deep Frontier template may end up with two enabled native
// Inventory components.
//
// Native 1.1.2.8 code assumes one: InventoryDebugFragment (dev "Modify
// Inventory") takes _inventories.SingleOrDefault(i => i && i.Enabled) and
// throws "Sequence contains more than one matching element" (build 145
// Hospital crash). Multi-good buildings use one inventory with several
// allowed goods instead.
//
// Every native component that creates an Inventory does so through an
// IDedicatedDecoratorInitializer<_, Inventory> (decompiled 1.1.2.8:
// ConstructionSites, DistributionSystem, FireworkSystem,
// GoodConsumingBuildingSystem, GoodStackSystem, Reproduction,
// SimpleOutputBuildings, Stockpiles, Wonders, Workshops). Deep Frontier's
// dependency mods create none. The construction-site inventory is enabled only
// while unfinished and every other one only when finished, so it is not
// counted. Deep Frontier components that add an inventory are found in
// src/DeepFrontier/Scripts and must be declared in MOD_INVENTORIES below.
//
// Usage: node tools/validate_single_inventory.mjs [dataRoot]
import {readFile, readdir} from 'node:fs/promises';
import {join, resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(process.argv[2] ?? join(root, 'src', 'DeepFrontier', 'Data'));
const vanillaRoot = join(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const scripts = join(root, 'src', 'DeepFrontier', 'Scripts');

// Native specs whose component owns an inventory (always, when finished).
const NATIVE_INVENTORIES = ['GoodConsumingBuildingSpec', 'StockpileSpec', 'FireworkLauncherSpec', 'BreedingPodSpec',
  'SimpleOutputInventorySpec', 'WonderInventorySpec', 'DistrictCrossingSpec'];
// ManufactorySpec owns one when Manufactory.NeedsInventory: any recipe with fuel, ingredients or products.
// Deep Frontier components that add an inventory: C# subject -> spec it is decorated on.
const MOD_INVENTORIES = {GroceryStore: 'GroceryStoreSpec'};
// Specs whose goods live in another component's inventory (never a second
// one): Hospital patient meals in the GoodConsumingBuilding inventory
// (HospitalPantryInventory.cs), bot maintenance oils and workplace upkeep
// goods in the Manufactory inventory (BotMaintenanceInventory.cs), the
// Technical School's supplies in its GoodConsumingBuilding inventory
// (SchoolSupplyInventory.cs).
const SHARED_INVENTORIES = {HospitalPantrySpec: 'GoodConsumingBuildingSpec', FrontierBotMaintenanceSpec: 'ManufactorySpec',
  FrontierWorkplaceUpkeepSpec: 'ManufactorySpec', FrontierSpecialistSchoolSpec: 'GoodConsumingBuildingSpec'};

const failures = [];
const fail = message => failures.push(message);
const rj = async path => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
async function walk(dir, suffix, out = []) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) await walk(path, suffix, out);
    else if (entry.name.endsWith(suffix)) out.push(path);
  }
  return out;
}

// --- Deep Frontier components that create inventories must be declared.
const sources = new Map();
for (const file of await walk(scripts, '.cs')) sources.set(file, await readFile(file, 'utf8'));
const allSource = [...sources.values()].join('\n');
for (const [file, text] of sources) {
  for (const match of text.matchAll(/IDedicatedDecoratorInitializer<\s*(\w+)\s*,\s*Inventory\s*>/g)) {
    const subject = match[1];
    if (!Object.hasOwn(MOD_INVENTORIES, subject)) {
      fail(`${relative(root, file)}: ${subject} adds a native Inventory that is not declared in MOD_INVENTORIES`);
      continue;
    }
    const spec = MOD_INVENTORIES[subject];
    if (!new RegExp(`AddDecorator<\\s*${spec}\\s*,\\s*${subject}\\s*>`).test(allSource))
      fail(`${subject} is no longer decorated on ${spec}; update MOD_INVENTORIES`);
  }
}
for (const subject of Object.keys(MOD_INVENTORIES))
  if (!new RegExp(`IDedicatedDecoratorInitializer<\\s*${subject}\\s*,\\s*Inventory\\s*>`).test(allSource))
    fail(`MOD_INVENTORIES.${subject} no longer adds an inventory; remove it`);
// A shared spec adds no initializer, so the undeclared-initializer check above covers it.

// Harmony prefixes on native inventory initializers must leave every other
// building on the native path: their first statements fetch the specs they
// own and the next returns true (run native) when all of them are absent.
const NATIVE_INITIALIZERS = ['GoodConsumingBuildingInventoryInitializer', 'ManufactoryInventoryInitializer', 'StockpileInventoryInitializer', 'InventoryInitializer'];
for (const [file, text] of sources) {
  for (const match of text.matchAll(/\[HarmonyPatch\(typeof\((\w+)\),\s*nameof\([^)]*\)\)\]\s*internal static class (\w+)\s*\{([\s\S]*?)\n  \}/g)) {
    const [, target, patch, body] = match;
    if (!NATIVE_INITIALIZERS.includes(target)) continue;
    // A bool prefix replaces native code: it must return true (run native)
    // unless its own component is present. A void prefix always runs native
    // code and may only act after its own spec check returns early.
    const prefix = body.match(/static bool Prefix\([^)]*\)\s*\{\s*((?:var\s+\w+\s*=\s*\w+\.GetComponent<\w+>\(\);\s*)+)if\s*\(([^)]*)\)\s*return\s+true;/);
    const voidPrefix = body.match(/static void Prefix\([^)]*\)\s*\{([\s\S]*?)\n    \}/);
    const names = prefix ? [...prefix[1].matchAll(/var\s+(\w+)/g)].map((m) => m[1]) : [];
    const condition = prefix ? prefix[2].replace(/\s+/g, '') : '';
    const guarded = prefix
      ? condition === names.map((name) => `${name}==null`).join('&&') || (names.length === 1 && condition === `!${names[0]}`)
      : !!body.match(/static bool Prefix\(/) ? false
      : !!voidPrefix && /GetComponent<\w+Spec>\(\);\s*if\s*\(\s*\w+\s*==\s*null\s*\)\s*return;/.test(voidPrefix[1]);
    if (!guarded) fail(`${relative(root, file)}: ${patch} prefix on native ${target} must first return true for buildings without its own spec`);
  }
}

// --- Count inventory owners per template.
const recipes = new Map();
for (const base of [vanillaRoot, dataRoot])
  for (const file of await walk(join(base, 'Recipes'), '.blueprint.json')) { const r = (await rj(file)).RecipeSpec; if (r) recipes.set(r.Id, r); }
const needsInventory = ids => ids.some(id => {
  const recipe = recipes.get(id);
  if (!recipe) { fail(`unknown recipe ${id}`); return false; }
  return recipe.Ingredients?.length > 0 || recipe.Products?.length > 0 || !!recipe.Fuel;
});
const owners = blueprint => {
  const list = [...NATIVE_INVENTORIES, ...Object.values(MOD_INVENTORIES)].filter(key => blueprint[key]);
  if (blueprint.ManufactorySpec && needsInventory(blueprint.ManufactorySpec.ProductionRecipeIds ?? [])) list.push('ManufactorySpec');
  return list;
};
let templates = 0;
for (const file of await walk(dataRoot, '.blueprint.json')) {
  const blueprint = await rj(file);
  if (!blueprint.TemplateSpec) continue;
  templates++;
  const list = owners(blueprint);
  if (list.length > 1) fail(`${relative(dataRoot, file)}: ${list.length} enabled inventories (${list.join(' + ')})`);
  for (const [shared, owner] of Object.entries(SHARED_INVENTORIES))
    if (blueprint[shared] && !list.includes(owner)) fail(`${relative(dataRoot, file)}: ${shared} needs ${owner} with an inventory, which holds its goods`);
}
// Vanilla precedent the rule relies on (Iron Teeth and shared templates).
for (const file of await walk(join(vanillaRoot, 'Buildings'), '.blueprint.json')) {
  if (file.includes('.Folktails.')) continue;
  const list = owners(await rj(file));
  if (list.length > 1) fail(`vanilla ${relative(vanillaRoot, file)} has ${list.join(' + ')}: the one-inventory rule no longer matches vanilla`);
}

if (failures.length) {
  for (const failure of failures) console.error(`FAIL: ${failure}`);
  console.error(`Single-inventory validation failed (${failures.length}) for ${dataRoot}`);
  process.exit(1);
}
console.log(`Single-inventory validation passed: ${templates} templates, at most one enabled inventory each.`);
