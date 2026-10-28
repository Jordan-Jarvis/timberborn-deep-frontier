// Bot upkeep: late-game industrial bot assembly and bot maintenance
// (tools/workforce_risks.json botAssembly and botMaintenance).
//
// Run once in canonical generation after workforce risks (it needs their
// FrontierWorkforceRiskSpec on the hazardous templates) and before the
// automation audit (which must see the spec and the vanilla patch):
//   await (await import('./bot_upkeep_content.mjs')).applyBotUpkeep();
//
// Writes:
// - FrontierBotMaintenanceSpec on every open workplace with bot wear
//   (runtime: src/DeepFrontier/Scripts/Workforce/BotMaintenance.cs). Bots
//   working there take a dose of maintenance oil from the building's own
//   maintenance inventory; while it lasts their wear multiplier is reduced.
// - Recipe.<botAssembly.recipe>: a product-less native bot recipe cloned from
//   vanilla Recipe.Bot.IronTeeth. The native BotManufactory (1.1.2.8) spawns
//   the faction's single BotSpec template whenever any assembler recipe
//   finishes (BotFactory.Load uses TemplateService.GetSingle<BotSpec>), so the
//   industrial bot is the ordinary Iron Teeth bot made faster from late-game
//   parts; no second bot template exists.
// - The vanilla Bot Assembler same-path patch
//   {ManufactorySpec: {"ProductionRecipeIds#append": [recipe]}}: native
//   blueprint array overlay, as the mod's GoodCollection and NeedCollection.
// - DeepFrontier.BotUpkeep.* localization rows.
// The late-game part recipes (bot chassis, limbs and heads from alloy,
// machine cores and electronics) are ordinary recipes of the Precision
// Machine Works in tools/create_frontier_expansion_content.mjs.
// It fails, without writing anything, on any missing input or duplicate.
import {readFile, writeFile, access, mkdir} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const CONFIG = 'tools/workforce_risks.json';
export const MAINTENANCE_SPEC = 'FrontierBotMaintenanceSpec';
export const ASSEMBLER = 'Buildings/Science/BotAssembler/BotAssembler.IronTeeth.blueprint';
export const RECIPE_TEMPLATE = 'Recipes/Recipe.Bot.IronTeeth.blueprint.json';
const VANILLA = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];
const COLLECTION = 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json';

// Fixed texts used by BotUpkeepPanels.cs (ILoc.T takes at most three parameters).
export const TEXTS = {
  'DeepFrontier.BotUpkeep.Panel.Title': 'Bot maintenance',
  'DeepFrontier.BotUpkeep.Panel.Bots': 'Bots assigned: {0}. Serviced: {1}.',
  'DeepFrontier.BotUpkeep.Panel.NoBots': 'No bots assigned: maintenance oil is only stocked while bots work here.',
  'DeepFrontier.BotUpkeep.Panel.Good': '{0}: {1} in stock. A bot serviced with it wears out {2}× here.',
  'DeepFrontier.BotUpkeep.Panel.Dose': 'One dose lasts {0} hours of work here; unserviced bots wear out {1}×. Bots take the first oil in stock, in the order listed.',
  'DeepFrontier.BotUpkeep.Bot.Serviced': 'Serviced with {0}: wears out {1}× here for {2} more hours.',
  'DeepFrontier.BotUpkeep.Bot.Unserviced': 'Not serviced: stock maintenance oil at the {0} to slow wear.',
};

const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const exists = (path) => access(path).then(() => true, () => false);
const csvCell = (value) => {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csvRow = (id, text) => [id, text, 'Deep Frontier bot upkeep'].map(csvCell).join(',');
const pair = (p) => Array.isArray(p) && p.length === 2 && typeof p[0] === 'string' && p[0];

export async function loadBotUpkeepConfig(root = defaultRoot) {
  const config = await readJson(resolve(root, CONFIG));
  return {templates: config.templates, maintenance: config.botMaintenance, assembly: config.botAssembly};
}

export function checkBotUpkeepConfig({maintenance: m, assembly: a}) {
  const errors = [];
  if (!m) errors.push('botMaintenance is missing');
  else {
    if (!Array.isArray(m.goods) || !m.goods.length || m.goods.some((g) => !pair(g) || !(g[1] > 0 && g[1] < 1))
        || new Set(m.goods.map((g) => g[0])).size !== m.goods.length)
      errors.push('botMaintenance.goods must be distinct [good, wearFactor in (0, 1)] pairs, in order of preference');
    else if (m.goods.some((g, i) => i && !(g[1] > m.goods[i - 1][1]))) errors.push('botMaintenance.goods: list the best oil (lowest wearFactor) first');
    if (!Number.isInteger(m.capacityPerGood) || m.capacityPerGood <= 0) errors.push('botMaintenance.capacityPerGood must be a positive integer');
    if (!(typeof m.serviceHours === 'number' && m.serviceHours > 0)) errors.push('botMaintenance.serviceHours must be positive');
  }
  if (!a) errors.push('botAssembly is missing');
  else {
    if (!/^[A-Z][A-Za-z]+$/.test(a.recipe ?? '')) errors.push('botAssembly.recipe must be a PascalCase recipe id');
    if (!a.displayName) errors.push('botAssembly.displayName is required');
    if (!(typeof a.hours === 'number' && a.hours > 0)) errors.push('botAssembly.hours must be positive');
    if (!Number.isInteger(a.cyclesCapacity) || a.cyclesCapacity < 1) errors.push('botAssembly.cyclesCapacity must be a positive integer');
    // Shown in the assembler's native recipe dropdown beside the vanilla recipe.
    if (!/^Sprites\/Goods\/\w+Icon$/.test(a.icon ?? '')) errors.push('botAssembly.icon must be a Sprites/Goods/<Name>Icon sprite');
    if (!Array.isArray(a.ingredients) || !a.ingredients.length || a.ingredients.some((i) => !pair(i) || !Number.isInteger(i[1]) || i[1] <= 0)
        || new Set(a.ingredients.map((i) => i[0])).size !== a.ingredients.length)
      errors.push('botAssembly.ingredients must be distinct [good, positive integer] pairs');
  }
  return errors;
}

// Open workplaces with bot wear (the generated, not the pending, templates).
export const maintainedTemplates = ({templates}) => Object.entries(templates)
  .filter(([, e]) => e.workers === 'open' && e.botWear > 1).map(([id]) => id);

export const maintenanceSpec = ({maintenance: m}) => ({
  Goods: m.goods.map(([GoodId, WearFactor]) => ({GoodId, WearFactor})),
  CapacityPerGood: m.capacityPerGood,
  ServiceHours: m.serviceHours,
});

export const assemblerPatch = ({assembly: a}) => ({ManufactorySpec: {'ProductionRecipeIds#append': [a.recipe]}});

export function assemblyRecipe(template, {assembly: a}) {
  return {
    ...template,
    RecipeSpec: {
      ...template.RecipeSpec,
      Id: a.recipe,
      BackwardCompatibleIds: [],
      DisplayLocKey: `Recipe.${a.recipe}.DisplayName`,
      CycleDurationInHours: a.hours,
      Ingredients: a.ingredients.map(([Id, Amount]) => ({Id, Amount})),
      Products: [],
      ProducedSciencePoints: 0,
      Fuel: '',
      CyclesFuelLasts: 0,
      FuelCapacity: 0,
      CyclesCapacity: a.cyclesCapacity,
      Icon: a.icon,
    },
  };
}

export const localizationRows = ({assembly: a}) => [[`Recipe.${a.recipe}.DisplayName`, a.displayName], ...Object.entries(TEXTS)];

export async function planBotUpkeep({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const config = await loadBotUpkeepConfig(root);
  const configErrors = checkBotUpkeepConfig(config);
  if (configErrors.length) throw new Error(`Bot upkeep: ${CONFIG} is invalid:\n  ${configErrors.join('\n  ')}`);
  const vanilla = resolve(root, ...VANILLA);
  const errors = [];
  const goodExists = async (id) => await exists(resolve(vanilla, 'Goods', `Good.${id}.blueprint.json`)) || await exists(resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`));

  const collected = new Set((await readJson(resolve(dataRoot, COLLECTION))).TemplateCollectionSpec['Blueprints#append']);
  const changed = [];
  const spec = maintenanceSpec(config);
  for (const [good] of config.maintenance.goods) if (!await goodExists(good)) errors.push(`maintenance good ${good} is not a vanilla or generated good`);
  for (const id of maintainedTemplates(config)) {
    const path = resolve(dataRoot, `${id}.json`);
    if (!collected.has(id) || !await exists(path)) { errors.push(`${id} is not a generated, collected template`); continue; }
    const blueprint = await readJson(path);
    if (blueprint[MAINTENANCE_SPEC]) { errors.push(`${id} already has ${MAINTENANCE_SPEC}; regenerate it from its producer`); continue; }
    if (!(blueprint.FrontierWorkforceRiskSpec?.BotWearMultiplier > 1)) { errors.push(`${id} has no bot-wear FrontierWorkforceRiskSpec; run workforce risks first`); continue; }
    // Native ManufactoryHaulBehaviorProvider/FillInputWorkplaceBehavior stock the extra inventory.
    if (!blueprint.ManufactorySpec || !blueprint.SimpleManufactoryBehaviorsSpec) { errors.push(`${id} is not a native manufactory with simple behaviours`); continue; }
    blueprint[MAINTENANCE_SPEC] = spec;
    changed.push({path, blueprint});
  }

  const assembler = await readJson(resolve(vanilla, `${ASSEMBLER}.json`));
  if (!assembler.BotManufactorySpec || !Array.isArray(assembler.ManufactorySpec?.ProductionRecipeIds))
    errors.push(`vanilla ${ASSEMBLER} is no longer a BotManufactory manufactory`);
  else if (assembler.ManufactorySpec.ProductionRecipeIds.includes(config.assembly.recipe)) errors.push(`vanilla ${ASSEMBLER} already runs ${config.assembly.recipe}`);
  const template = await readJson(resolve(vanilla, RECIPE_TEMPLATE));
  if (template.RecipeSpec.Products.length) errors.push('vanilla Recipe.Bot.IronTeeth is no longer product-less');
  if (await exists(resolve(vanilla, 'Recipes', `Recipe.${config.assembly.recipe}.blueprint.json`))) errors.push(`recipe id ${config.assembly.recipe} is a vanilla recipe`);
  for (const [good] of config.assembly.ingredients) if (!await goodExists(good)) errors.push(`bot assembly ingredient ${good} is not a vanilla or generated good`);
  if (!await exists(resolve(dataRoot, `${config.assembly.icon}.png`))) errors.push(`bot assembly icon ${config.assembly.icon}.png is not generated`);

  const localizationPath = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  if (lines.at(-1) !== '') errors.push('enUS.csv must end with a newline');
  const ids = new Set(lines.map((line) => line.split(',')[0]));
  const rows = localizationRows(config);
  for (const [id] of rows) if (ids.has(id)) errors.push(`localization ${id} already exists`);
  return {config, changed, errors, lines, rows, localizationPath,
    recipe: {path: resolve(dataRoot, 'Recipes', `Recipe.${config.assembly.recipe}.blueprint.json`), blueprint: assemblyRecipe(template, config)},
    patch: {path: resolve(dataRoot, `${ASSEMBLER}.json`), blueprint: assemblerPatch(config)}};
}

export async function applyBotUpkeep({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const {config, changed, errors, lines, rows, localizationPath, recipe, patch} = await planBotUpkeep({root, dataRoot});
  if (errors.length) throw new Error(`Bot upkeep: generation stopped:\n  ${errors.join('\n  ')}`);
  for (const {path, blueprint} of [...changed, recipe, patch]) await writeJson(path, blueprint);
  lines.pop();
  for (const [id, text] of rows) lines.push(csvRow(id, text));
  await writeFile(localizationPath, `${lines.join('\n')}\n`, 'utf8');
  console.log(`Bot upkeep: maintenance on ${changed.length} workplaces (${config.maintenance.goods.map(([g, f]) => `${g} x${f}`).join(', ')}), ` +
    `${config.assembly.recipe} at the vanilla Bot Assembler.`);
  return {maintained: changed.length};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applyBotUpkeep(dataRoot ? {dataRoot} : {})));
}
