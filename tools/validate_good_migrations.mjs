// Removed goods and recipes migrate natively (tools/content_policy.json
// migratedGoods / migratedRecipes, tools/good_migrations.mjs). Checks the
// generated data:
// - a removed good has no blueprint, icon, collection entry or localization
//   row, and no generated blueprint names it outside BackwardCompatibleIds;
// - its target good exists, is collected for Iron Teeth (the mod's goods or the
//   vanilla Common/IronTeeth collections), has the removed good's GoodType and
//   lists the removed id in BackwardCompatibleIds;
// - a removed recipe has no blueprint and its target recipe lists it;
// - every BackwardCompatibleIds entry in the generated goods and recipes comes
//   from the table.
//   node tools/validate_good_migrations.mjs [dataRoot]
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {MIGRATED_GOODS, MIGRATED_GOOD_TYPES, MIGRATED_RECIPES, backwardGoodIds, backwardRecipeIds} from './good_migrations.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const data = resolve(root, process.argv[2] ?? 'src/DeepFrontier/Data');
const vanilla = resolve(root, 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources');
const read = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const failures = [];
const fail = (message) => failures.push(message);

async function* walk(dir) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (entry.name.endsWith('.json')) yield path;
  }
}

const removed = new Set([...MIGRATED_GOODS.keys(), ...MIGRATED_RECIPES.keys()]);
const goodSpecs = new Map(), recipeSpecs = new Map();
for await (const path of walk(data)) {
  const value = await read(path);
  if (value.GoodSpec) goodSpecs.set(value.GoodSpec.Id, value.GoodSpec);
  if (value.RecipeSpec) recipeSpecs.set(value.RecipeSpec.Id, value.RecipeSpec);
  // Any string value naming a removed id, except the migration lists themselves.
  const visit = (node, trail) => {
    if (typeof node === 'string') { if (removed.has(node)) fail(`${relative(data, path)}: ${trail} still names removed ${node}`); return; }
    if (Array.isArray(node)) { node.forEach((item, i) => visit(item, `${trail}[${i}]`)); return; }
    if (node && typeof node === 'object') {
      for (const [key, child] of Object.entries(node)) if (key !== 'BackwardCompatibleIds') visit(child, trail ? `${trail}.${key}` : key);
    }
  };
  visit(value, '');
}

const collection = new Set((await read(resolve(data, 'GoodCollections/GoodCollection.IronTeeth.blueprint.json'))).GoodCollectionSpec['Goods#append']);
const vanillaGoods = new Set();
for (const name of ['Common', 'IronTeeth']) {
  for (const id of (await read(resolve(vanilla, `GoodCollections/GoodCollection.${name}.blueprint.json`))).GoodCollectionSpec.Goods) vanillaGoods.add(id);
}
const localization = (await readFile(resolve(data, 'Localizations/enUS.csv'), 'utf8')).split(/\r?\n/).map((line) => line.split(',')[0]);

for (const [id, to] of MIGRATED_GOODS) {
  if (goodSpecs.has(id)) fail(`removed good ${id} still has a blueprint`);
  if (collection.has(id)) fail(`removed good ${id} is still in the Iron Teeth collection`);
  if (await exists(resolve(data, 'Sprites/Goods', `${id}Icon.png`))) fail(`removed good ${id} still has Sprites/Goods/${id}Icon.png`);
  if (localization.some((key) => key.startsWith(`Good.${id}.`))) fail(`removed good ${id} still has localization rows`);
  let target = goodSpecs.get(to);
  if (target && !collection.has(to)) fail(`${id} -> ${to}: ${to} is not in the Iron Teeth collection`);
  if (!target && vanillaGoods.has(to)) target = (await read(resolve(vanilla, `Goods/Good.${to}.blueprint.json`))).GoodSpec;
  if (!target) { fail(`${id} -> ${to}: no Iron Teeth good ${to}`); continue; }
  if (target.GoodType !== MIGRATED_GOOD_TYPES.get(id)) fail(`${id} (${MIGRATED_GOOD_TYPES.get(id)}) -> ${to}: ${to} is ${target.GoodType}`);
  if (!target.BackwardCompatibleIds?.includes(id)) fail(`${id} -> ${to}: Good.${to} does not list ${id} in BackwardCompatibleIds`);
}
for (const [id, to] of MIGRATED_RECIPES) {
  if (recipeSpecs.has(id)) fail(`removed recipe ${id} still has a blueprint`);
  const target = recipeSpecs.get(to);
  if (!target) fail(`recipe ${id} -> ${to}: no generated recipe ${to}`);
  else if (!target.BackwardCompatibleIds?.includes(id)) fail(`recipe ${id} -> ${to}: Recipe.${to} does not list ${id} in BackwardCompatibleIds`);
}
for (const [id, spec] of goodSpecs) {
  if ((spec.BackwardCompatibleIds ?? []).join() !== backwardGoodIds(id).join()) fail(`Good.${id} BackwardCompatibleIds ${JSON.stringify(spec.BackwardCompatibleIds)} differ from content_policy.json (${backwardGoodIds(id)})`);
}
for (const [id, spec] of recipeSpecs) {
  if ((spec.BackwardCompatibleIds ?? []).join() !== backwardRecipeIds(id).join()) fail(`Recipe.${id} BackwardCompatibleIds ${JSON.stringify(spec.BackwardCompatibleIds)} differ from content_policy.json (${backwardRecipeIds(id)})`);
}

if (failures.length) {
  console.error(`Good migration validation failed (${failures.length}):`);
  for (const message of failures) console.error(`- ${message}`);
  process.exit(1);
}
console.log(`Good migrations: ${MIGRATED_GOODS.size} removed goods and ${MIGRATED_RECIPES.size} removed recipes resolve natively; no generated blueprint names them.`);
