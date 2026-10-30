// Static checks for bot upkeep (tools/workforce_risks.json botMaintenance,
// botAssembly and workplaceUpkeep, tools/bot_upkeep_content.mjs,
// Scripts/Workforce/BotMaintenance.cs, WorkplaceUpkeep.cs, BotWear.cs and
// BotUpkeepPanels.cs).
//
//   node tools/validate_bot_upkeep.mjs [dataRoot]
//
// Read-only: the catalog, that the runtime records and localization keys
// match what the generator writes, the generated data (exact maintenance spec
// on every open bot-wear workplace and nowhere else, exact upkeep spec on every
// workplaceUpkeep template and nowhere else, the industrial bot recipe and the
// vanilla Bot Assembler patch) and the automation declarations. Exits 1 on
// any error. Runtime behaviour is verified in game, not here.
import {readFile, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadBotUpkeepConfig, checkBotUpkeepConfig, maintainedTemplates, maintenanceSpec, assemblerPatch, assemblyRecipe,
  localizationRows, TEXTS, MAINTENANCE_SPEC, ASSEMBLER, RECIPE_TEMPLATE, UPKEEP_SPEC, upkeepTemplates, upkeepSpec} from './bot_upkeep_content.mjs';

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
const upkeepSource = await readFile(resolve(scripts, 'WorkplaceUpkeep.cs'), 'utf8');
const serialized = (text, file, record) => {
  const body = text.match(new RegExp(`record ${record}\\b[^{]*\\{([\\s\\S]*?)\\n  \\}`))?.[1];
  if (!body) { errors.push(`runtime: record ${record} not found in ${file}`); return []; }
  return [...body.matchAll(/\[Serialize\] public [\w<>.]+ (\w+) \{/g)].map((m) => m[1]).sort();
};
const firstUpkept = upkeepTemplates(config)[0];
const sampleUpkeep = firstUpkept ? upkeepSpec(config, firstUpkept) : null;
for (const [text, file, record, value] of [[source, 'BotMaintenance.cs', 'FrontierBotMaintenanceSpec', spec], [source, 'BotMaintenance.cs', 'FrontierBotMaintenanceGoodSpec', spec.Goods[0]],
    ...(sampleUpkeep ? [[upkeepSource, 'WorkplaceUpkeep.cs', UPKEEP_SPEC, sampleUpkeep], [upkeepSource, 'WorkplaceUpkeep.cs', 'FrontierUpkeepGoodSpec', sampleUpkeep.Goods[0]]] : [])]) {
  const keys = serialized(text, file, record);
  if (!same(keys, Object.keys(value).sort())) errors.push(`runtime: ${record} serializes [${keys}], generator writes [${Object.keys(value).sort()}]`);
}
if (!/AddDecorator<FrontierBotMaintenanceSpec,BotMaintenance>\(\)/.test(source)) errors.push('runtime: BotMaintenance is not decorated on FrontierBotMaintenanceSpec');
if (!/AddDecorator<FrontierWorkplaceUpkeepSpec,WorkplaceUpkeep>\(\)/.test(upkeepSource)) errors.push('runtime: WorkplaceUpkeep is not decorated on FrontierWorkplaceUpkeepSpec');
// Role texts: WorkplaceUpkeepLoc builds DeepFrontier.WorkplaceUpkeep.<Role>.<suffix>.
for (const suffix of ['Name', 'Status', 'Status.Short'])
  if (!upkeepSource.includes(`Prefix + role + ".${suffix}"`)) errors.push(`runtime: WorkplaceUpkeepLoc no longer builds <Role>.${suffix}`);
if (!upkeepSource.includes('Prefix = "DeepFrontier.WorkplaceUpkeep."')) errors.push('runtime: WorkplaceUpkeepLoc.Prefix differs from the generator');
const panels = await readFile(resolve(scripts, 'BotUpkeepPanels.cs'), 'utf8');
for (const [, key] of panels.matchAll(/"(DeepFrontier\.(?:BotUpkeep|WorkplaceUpkeep)\.[A-Za-z.]+)"/g))
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
  const upkept = new Set(upkeepTemplates(config));
  for (const id of collection) {
    const path = resolve(dataRoot, `${id}.json`);
    if (!await exists(path)) continue;
    const blueprint = await readJson(path);
    if (upkept.has(id)) {
      if (!same(blueprint[UPKEEP_SPEC], upkeepSpec(config, id))) errors.push(`${id}: ${UPKEEP_SPEC} differs from the catalog`);
    } else if (blueprint[UPKEEP_SPEC]) errors.push(`${id}: undeclared ${UPKEEP_SPEC}`);
  }
  for (const id of upkept) if (!collection.includes(id)) errors.push(`${id}: upkeep template is not collected`);
  if (!same(await readJson(recipePath), assemblyRecipe(template, config))) errors.push(`Recipe.${config.assembly.recipe} differs from the catalog`);
  const patchPath = resolve(dataRoot, `${ASSEMBLER}.json`);
  if (!await exists(patchPath) || !same(await readJson(patchPath), assemblerPatch(config))) errors.push(`${ASSEMBLER}: same-path patch missing or different`);
  const csv = await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8');
  for (const [key] of localizationRows(config)) if (!csv.includes(`\n${key},`)) errors.push(`enUS.csv lacks ${key}`);
}

// Automation declarations.
const automation = await readJson(resolve(root, 'tools', 'automation_content.json'));
for (const key of [MAINTENANCE_SPEC, UPKEEP_SPEC])
  if (automation.customSpecs[key]?.kind !== 'operational') errors.push(`automation: customSpecs.${key} must be an operational declaration`);
if (automation.vanillaPatches[ASSEMBLER]?.producer !== 'tools/bot_upkeep_content.mjs') errors.push(`automation: vanillaPatches lacks ${ASSEMBLER}`);

if (errors.length) {
  console.error(`Bot upkeep: ${errors.length} error(s)\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
const rates = Object.entries(config.templates).filter(([id]) => maintainedTemplates(config).includes(id))
  .map(([id, e]) => `${id.split('/').at(-2)} ${e.botWear}x -> ${config.maintenance.goods.map(([g, f]) => `${g} ${Math.max(1, e.botWear * f)}x`).join(' / ')}`);
const upkeepRates = upkeepTemplates(config).map((id) => `${id.split('/').at(-2)}: ${config.upkeep.templates[id].map(([g, h, r]) => `${g} ${h}/h at full crew (${r})`).join(', ')}; stock ${config.upkeep.capacityPerGood} each`);
console.log(`Bot upkeep: OK (${applied ? 'applied data' : 'catalog only'}; ${rates.length} maintained workplaces, ${upkeepRates.length} with workplace upkeep, ${config.assembly.recipe} ${config.assembly.hours} h).`);
for (const line of [...rates, ...upkeepRates]) console.log(`  ${line}`);
