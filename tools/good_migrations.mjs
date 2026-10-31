// Native save migration of removed goods and recipes (tools/content_policy.json
// migratedGoods / migratedRecipes). A removed id is listed in the
// BackwardCompatibleIds of the good or recipe that replaces it:
// - GoodService.BindGoodToItsBackwardCompatibleIds maps a saved good id to the
//   listed good (Timberborn.Goods 1.1.2.8);
// - Manufactory.Load finds a saved recipe by Id, then by BackwardCompatibleIds
//   (Timberborn.Workshops 1.1.2.8).
// The generators call these when they write a GoodSpec or RecipeSpec;
// tools/validate_good_migrations.mjs checks the generated data against the table.
import {readFileSync} from 'node:fs';

const policy = JSON.parse(readFileSync(new URL('./content_policy.json', import.meta.url), 'utf8'));
const entries = (table, name) => {
  if (!table || typeof table !== 'object') throw new Error(`content_policy.json ${name} is missing`);
  return Object.entries(table).filter(([id]) => id !== '$comment');
};
export const MIGRATED_GOOD_TYPES = new Map();
export const MIGRATED_GOODS = new Map(entries(policy.migratedGoods, 'migratedGoods').map(([id, entry]) => {
  if (typeof entry?.to !== 'string' || !entry.to || typeof entry.why !== 'string' || !entry.why || typeof entry.type !== 'string' || !entry.type)
    throw new Error(`content_policy.json migratedGoods.${id} needs its GoodType (type), a target good (to) and a reason (why)`);
  MIGRATED_GOOD_TYPES.set(id, entry.type);
  return [id, entry.to];
}));
export const MIGRATED_RECIPES = new Map(entries(policy.migratedRecipes, 'migratedRecipes').map(([id, to]) => {
  if (typeof to !== 'string' || !to) throw new Error(`content_policy.json migratedRecipes.${id} needs a target recipe`);
  return [id, to];
}));
for (const [id, to] of [...MIGRATED_GOODS, ...MIGRATED_RECIPES]) if (id === to) throw new Error(`content_policy.json migrates ${id} onto itself`);

const sources = (map, target) => [...map].filter(([, to]) => to === target).map(([id]) => id).sort();
export const backwardGoodIds = (id) => sources(MIGRATED_GOODS, id);
export const backwardRecipeIds = (id) => sources(MIGRATED_RECIPES, id);
