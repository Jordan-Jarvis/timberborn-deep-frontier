// Static checks for bot upkeep (tools/workforce_risks.json botMaintenance and
// botAssembly, tools/bot_upkeep_content.mjs, Scripts/Workforce/BotMaintenance.cs,
// BotWear.cs and BotUpkeepPanels.cs).
//
//   node tools/validate_bot_upkeep.mjs [dataRoot]
//
// Read-only: the catalog, that the runtime records and localization keys
// match what the generator writes, the generated data (exact spec on every
// open bot-wear workplace and nowhere else, the industrial bot recipe and the
// vanilla Bot Assembler patch) and the automation declarations. Exits 1 on
// any error. Runtime behaviour is verified in game, not here.
import {readFile, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadBotUpkeepConfig, checkBotUpkeepConfig, maintainedTemplates, maintenanceSpec, assemblerPatch, assemblyRecipe,
  localizationRows, TEXTS, MAINTENANCE_SPEC, ASSEMBLER, RECIPE_TEMPLATE} from './bot_upkeep_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(process.argv[2] ?? resolve(root, 'src', 'DeepFrontier', 'Data'));
const vanilla = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Workforce');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const errors = [];

const config = await loadBotUpkeepConfig(root);
errors.push(...checkBotUpkeepConfig(config).map((e) => `catalog: ${e}`));
const spec = maintenanceSpec(config);

// Runtime records serialize exactly the generated keys.
const source = await readFile(resolve(scripts, 'BotMaintenance.cs'), 'utf8');
const serialized = (record) => {
  const body = source.match(new RegExp(`record ${record}\\b[^{]*\\{([\\s\\S]*?)\\n  \\}`))?.[1];
  if (!body) { errors.push(`runtime: record ${record} not found in BotMaintenance.cs`); return []; }
  return [...body.matchAll(/\[Serialize\] public [\w<>.]+ (\w+) \{/g)].map((m) => m[1]).sort();
};
for (const [record, value] of [['FrontierBotMaintenanceSpec', spec], ['FrontierBotMaintenanceGoodSpec', spec.Goods[0]]])
  if (!same(serialized(record), Object.keys(value).sort())) errors.push(`runtime: ${record} serializes [${serialized(record)}], generator writes [${Object.keys(value).sort()}]`);
if (!/AddDecorator<FrontierBotMaintenanceSpec,BotMaintenance>\(\)/.test(source)) errors.push('runtime: BotMaintenance is not decorated on FrontierBotMaintenanceSpec');
const panels = await readFile(resolve(scripts, 'BotUpkeepPanels.cs'), 'utf8');
for (const [, key] of panels.matchAll(/"(DeepFrontier\.BotUpkeep\.[A-Za-z.]+)"/g))
  if (!Object.hasOwn(TEXTS, key)) errors.push(`runtime: BotUpkeepPanels.cs uses ${key}, which the generator does not write`);
for (const [key, text] of Object.entries(TEXTS))
  if ([...text.matchAll(/\{(\d)\}/g)].some((m) => Number(m[1]) > 2)) errors.push(`localization ${key}: ILoc.T takes at most three parameters`);

// Native contract the industrial bot relies on.
const assembler = await readJson(resolve(vanilla, `${ASSEMBLER}.json`));
if (!assembler.BotManufactorySpec) errors.push(`native: ${ASSEMBLER} has no BotManufactorySpec`);
const template = await readJson(resolve(vanilla, RECIPE_TEMPLATE));
if (template.RecipeSpec.Products.length) errors.push('native: Recipe.Bot.IronTeeth is no longer product-less');

// Generated data.
const recipePath = resolve(dataRoot, 'Recipes', `Recipe.${config.assembly.recipe}.blueprint.json`);
const applied = await exists(recipePath);
if (applied) {
  const collection = (await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'))).TemplateCollectionSpec['Blueprints#append'];
  const maintained = new Set(maintainedTemplates(config));
  for (const id of collection) {
    const path = resolve(dataRoot, `${id}.json`);
    if (!await exists(path)) continue;
    const blueprint = await readJson(path);
    if (maintained.has(id)) {
      if (!same(blueprint[MAINTENANCE_SPEC], spec)) errors.push(`${id}: ${MAINTENANCE_SPEC} differs from the catalog`);
      if (!(blueprint.FrontierWorkforceRiskSpec?.BotWearMultiplier > 1)) errors.push(`${id}: maintained but without bot wear`);
    } else if (blueprint[MAINTENANCE_SPEC]) errors.push(`${id}: undeclared ${MAINTENANCE_SPEC}`);
  }
  for (const id of maintained) if (!collection.includes(id)) errors.push(`${id}: maintained template is not collected`);
  if (!same(await readJson(recipePath), assemblyRecipe(template, config))) errors.push(`Recipe.${config.assembly.recipe} differs from the catalog`);
  const patchPath = resolve(dataRoot, `${ASSEMBLER}.json`);
  if (!await exists(patchPath) || !same(await readJson(patchPath), assemblerPatch(config))) errors.push(`${ASSEMBLER}: same-path patch missing or different`);
  const csv = await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8');
  for (const [key] of localizationRows(config)) if (!csv.includes(`\n${key},`)) errors.push(`enUS.csv lacks ${key}`);
}

// Automation declarations.
const automation = await readJson(resolve(root, 'tools', 'automation_content.json'));
if (automation.customSpecs[MAINTENANCE_SPEC]?.kind !== 'operational') errors.push(`automation: customSpecs.${MAINTENANCE_SPEC} must be an operational declaration`);
if (automation.vanillaPatches[ASSEMBLER]?.producer !== 'tools/bot_upkeep_content.mjs') errors.push(`automation: vanillaPatches lacks ${ASSEMBLER}`);

if (errors.length) {
  console.error(`Bot upkeep: ${errors.length} error(s)\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
const rates = Object.entries(config.templates).filter(([id]) => maintainedTemplates(config).includes(id))
  .map(([id, e]) => `${id.split('/').at(-2)} ${e.botWear}x -> ${config.maintenance.goods.map(([g, f]) => `${g} ${Math.max(1, e.botWear * f)}x`).join(' / ')}`);
console.log(`Bot upkeep: OK (${applied ? 'applied data' : 'catalog only'}; ${rates.length} maintained workplaces, ${config.assembly.recipe} ${config.assembly.hours} h).`);
for (const line of rates) console.log(`  ${line}`);
