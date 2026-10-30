// Generated Iron Teeth progression data (vanilla + Deep Frontier) shared by
// tools/audit_progression.mjs and tools/material_costs.mjs: building templates
// with science, construction cost and recipes; recipes; Iron Teeth goods; the
// map-gathered goods; and the per-building bootstrap reachability.
import {access, readFile, readdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';

export const root = fileURLToPath(new URL('../', import.meta.url));
export const vanillaRoot = resolve(root, 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources');
const utf8 = new TextDecoder('utf-8', {fatal: true});
const read = async (path) => JSON.parse(utf8.decode(await readFile(path)).replace(/^﻿/, ''));

// Goods gathered by a workplace rather than produced by a recipe.
export const MAP_SOURCES = {
  ScrapMetal: {via: ['ScavengerFlag.IronTeeth'], note: 'vanilla Scavenger Flag at ruins (EfficientMine is the recipe route)'},
  DeepOre: {via: ['DeepDrill.IronTeeth'], note: 'finite DeepOreSource marker (DeepDrill), then DeepMine over a DeepOreVein'},
  Sandstone: {via: ['SandstonePit.IronTeeth'], note: 'finite SandstoneOutcrop yielders'},
  Limestone: {via: ['LimestonePit.IronTeeth'], note: 'finite LimestoneOutcrop yielders'},
  FreshFish: {via: ['GathererFlag.IronTeeth'], note: 'Gatherer Flag shore fishing'},
  // Not gathered: produced at runtime when stored Water is irradiated
  // (RadiationStorageService). Radiation first exists once the refinery (or
  // reactor) makes RadioactiveSludge, so the refinery is its earliest source.
  ContaminatedWater: {via: ['RadioactiveWasteRefinery.IronTeeth'], note: 'runtime: irradiated stored Water converts (docs/radiation.md)'},
};

export const recipeInputs = (r) => [...r.Ingredients.map((i) => i.Id), ...(r.Fuel ? [r.Fuel] : [])];

export async function loadProgressionData(data) {
  const templatesOf = async (path) => {
    const spec = (await read(path)).TemplateCollectionSpec;
    return spec.Blueprints ?? spec['Blueprints#append'];
  };
  const vanillaPaths = [...await templatesOf(resolve(vanillaRoot, 'TemplateCollections/TemplateCollection.Buildings.Common.blueprint.json')),
    ...await templatesOf(resolve(vanillaRoot, 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json'))];
  const modPaths = await templatesOf(resolve(data, 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json'));

  const buildings = new Map();
  for (const [origin, base, paths] of [['vanilla', vanillaRoot, vanillaPaths], ['DeepFrontier', data, modPaths]]) {
    for (const path of paths) {
      const bp = await read(resolve(base, path + '.json'));
      const id = bp.TemplateSpec.TemplateName;
      if (buildings.has(id)) throw new Error(`Duplicate template ${id}`);
      // Templates without a BuildingSpec (vanilla Path) are free tools.
      buildings.set(id, {id, origin, path, bp, science: bp.BuildingSpec?.ScienceCost ?? 0,
        cost: (bp.BuildingSpec?.BuildingCost ?? []).map((c) => [c.Id, c.Amount]),
        recipes: bp.ManufactorySpec?.ProductionRecipeIds ?? []});
    }
  }
  // Vanilla templates patched by a same-path Deep Frontier blueprint (native
  // array overlay, e.g. the Bot Assembler's industrial bot): the recipes they
  // append run there.
  for (const b of buildings.values()) {
    if (b.origin !== 'vanilla') continue;
    const patchPath = resolve(data, b.path + '.json');
    if (!await access(patchPath).then(() => true, () => false)) continue;
    b.appended = (await read(patchPath)).ManufactorySpec?.['ProductionRecipeIds#append'] ?? [];
    b.recipes = [...b.recipes, ...b.appended];
  }
  for (const [good, source] of Object.entries(MAP_SOURCES)) {
    for (const via of source.via) if (!buildings.has(via)) throw new Error(`MAP_SOURCES ${good}: no template ${via}`);
  }

  const recipes = new Map();
  const recipeFiles = async (dir) => (await readdir(dir)).filter((n) => n.endsWith('.blueprint.json')).map((n) => resolve(dir, n));
  const modRecipeIds = new Set();
  for (const [dir, mod] of [[resolve(vanillaRoot, 'Recipes'), false], [resolve(data, 'Recipes'), true]]) {
    for (const path of await recipeFiles(dir)) {
      const r = (await read(path)).RecipeSpec;
      if (recipes.has(r.Id)) throw new Error(`Duplicate recipe ${r.Id}`);
      recipes.set(r.Id, r);
      if (mod) modRecipeIds.add(r.Id);
    }
  }
  // Iron Teeth goods: the vanilla Common + IronTeeth collections and the mod's
  // appended goods (Folktails-only goods such as Paper are not available).
  const collection = async (name) => (await read(resolve(vanillaRoot, `GoodCollections/GoodCollection.${name}.blueprint.json`))).GoodCollectionSpec.Goods;
  const modGoods = new Set((await read(resolve(data, 'GoodCollections/GoodCollection.IronTeeth.blueprint.json'))).GoodCollectionSpec['Goods#append']);
  const goods = new Set([...await collection('Common'), ...await collection('IronTeeth'), ...modGoods]);
  // A vanilla good no vanilla recipe produces is primary (gathered, grown,
  // pumped or scavenged) and available from the start.
  const vanillaRecipeProducts = new Set([...buildings.values()].filter((b) => b.origin === 'vanilla')
    .flatMap((b) => b.recipes.flatMap((id) => recipes.get(id)?.Products.map((p) => p.Id) ?? [])));
  const primary = new Set([...goods].filter((g) => !modGoods.has(g) && !vanillaRecipeProducts.has(g)));
  return {buildings, recipes, goods, modGoods, modRecipeIds, primary};
}

// Goods the settlement can make without `excluded`, from player-placeable
// buildings unlocked at or below `science`. With `costGated`, a building
// counts only once every good of its construction cost is available (the
// first unit of each good must not depend on the excluded building).
// `buildings` maps id -> {science, cost, recipes, devOnly}; `recipes` maps id
// -> RecipeSpec.
export function reachableWithout({buildings, recipes, primary}, excluded, science, costGated) {
  const pool = [...buildings.values()].filter((b) => b.id !== excluded && b.science <= science && !b.devOnly);
  const have = new Set(primary);
  const usable = new Set();
  for (let changed = true; changed;) {
    changed = false;
    for (const b of pool) {
      if (usable.has(b.id) || (costGated && !b.cost.every(([g]) => have.has(g)))) continue;
      usable.add(b.id);
      changed = true;
    }
    for (const [good, source] of Object.entries(MAP_SOURCES)) {
      if (!have.has(good) && source.via.some((v) => usable.has(v))) { have.add(good); changed = true; }
    }
    for (const b of pool) {
      if (!usable.has(b.id)) continue;
      for (const id of b.recipes) {
        const r = recipes.get(id);
        // A recipe that consumes its own product (DeepOre from DeepOre) needs
        // that good from another route first.
        if (!r || !recipeInputs(r).every((i) => have.has(i))) continue;
        for (const p of r.Products) if (!have.has(p.Id)) { have.add(p.Id); changed = true; }
      }
    }
  }
  return have;
}
