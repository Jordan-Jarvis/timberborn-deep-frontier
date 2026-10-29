// Static checks for Reactor Bots (tools/super_bots.json, tools/super_bot_content.mjs,
// src/DeepFrontier/Scripts/SuperBots, tools/asset-pipeline/lategame_ReactorChargingBay.py).
//
//   node tools/validate_super_bots.mjs [dataRoot]
//
// Read-only. Checks:
// - the catalog;
// - that the runtime settings record serializes exactly what the generator writes;
// - that the panel's localization keys are generated;
// - the native contracts the design relies on;
// - when generated: the settings, needs, goods, recipes, manufactories, upkeep effects, light colour, charging bay, collections, icons, localization and its automation declaration.
// Exits 1 on any error. Runtime behaviour is verified in game, not here.
import {readFile, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSuperBotConfig, checkSuperBotConfig, settingsBlueprint, needBlueprints, partGood, partRecipe, consumptionEffects,
  illuminationBlueprint, stationComponents, localizationRows, chargeDailyDelta, allNeeds, PANEL_KEYS, SETTINGS_PATH, SETTINGS_SPEC} from './super_bot_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(process.argv[2] ?? resolve(root, 'src', 'DeepFrontier', 'Data'));
const vanilla = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'SuperBots');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const errors = [];

const config = await loadSuperBotConfig(root);
errors.push(...checkSuperBotConfig(config).map((e) => `catalog: ${e}`));
const energy = await readJson(resolve(vanilla, 'Needs', 'Need.Bot.Energy.blueprint.json'));
const grease = await readJson(resolve(vanilla, 'Needs', 'Need.Bot.Grease.blueprint.json'));

// Runtime: the settings record serializes exactly the generated keys.
const settingsSource = await readFile(resolve(scripts, 'ReactorBotSettings.cs'), 'utf8');
const body = settingsSource.match(/record FrontierReactorBotSettingsSpec\b[^{]*\{([\s\S]*?)\n  \}/)?.[1];
const fields = body ? [...body.matchAll(/\[Serialize\] public [\w<>.]+ (\w+) \{/g)].map((m) => m[1]).sort() : [];
if (!same(fields, Object.keys(settingsBlueprint(config)[SETTINGS_SPEC]).sort()))
  errors.push(`runtime: FrontierReactorBotSettingsSpec serializes [${fields}], generator writes [${Object.keys(settingsBlueprint(config)[SETTINGS_SPEC]).sort()}]`);
const configurator = await readFile(resolve(scripts, 'ReactorBotConfigurator.cs'), 'utf8');
if (!/AddDecorator<BotSpec,ReactorBot>\(\)/.test(configurator)) errors.push('runtime: ReactorBot is not decorated on the native BotSpec');
const panel = await readFile(resolve(scripts, 'ReactorBotPanel.cs'), 'utf8');
const rows = localizationRows(config, energy);
const rowKeys = new Set(rows.map(([k]) => k));
for (const [, key] of panel.matchAll(/"(DeepFrontier\.ReactorBot\.[A-Za-z.]+)"/g)) if (!rowKeys.has(key)) errors.push(`runtime: ReactorBotPanel.cs uses ${key}, which the generator does not write`);
for (const key of PANEL_KEYS) if (!panel.includes(`"${key}"`)) errors.push(`runtime: ${key} is generated but unused by ReactorBotPanel.cs`);
const patches = await readFile(resolve(scripts, 'ReactorBotPatches.cs'), 'utf8');
for (const target of ['WalkerSpeedManager),nameof(WalkerSpeedManager.Tick)', 'Deteriorable),nameof(Deteriorable.Tick)', 'CitizenTint),nameof(CitizenTint.UpdateTint)'])
  if (!patches.includes(target)) errors.push(`runtime: ReactorBotPatches.cs no longer patches ${target}`);

// Native contracts.
const bot = await readJson(resolve(vanilla, 'Characters', 'Bot', 'Bot.IronTeeth.blueprint.json'));
if (!bot.BotSpec || bot.CriticalNeedStateAnimationSpec?.NeedId !== config.upgrade.replacedNeeds[0] || bot.CriticalNeedStateAnimationSpec?.Animation !== config.upgrade.noChargeAnimation)
  errors.push('native: the vanilla bot template no longer drives the catalog noChargeAnimation from the replaced need');
const speed = await readJson(resolve(vanilla, 'BonusTypes', 'BonusType.MovementSpeed.blueprint.json')).catch(() => null);
const carry = await readJson(resolve(vanilla, 'BonusTypes', 'BonusType.CarryingCapacity.blueprint.json')).catch(() => null);
if (!speed || speed.BonusTypeSpec.MaximumValue >= config.upgrade.speedMultiplier) errors.push('native: MovementSpeed bonus no longer clamps below the speed multiplier; reconsider the speed patch');
if (!carry || 1 + config.upgrade.carryingCapacityBonus > carry.BonusTypeSpec.MaximumValue) errors.push('native: CarryingCapacity bonus clamps below the carrying buff');
if (!(await exists(resolve(root, 'tools', 'asset-pipeline', `lategame_${config.station.id}.py`)))) errors.push(`art: tools/asset-pipeline/lategame_${config.station.id}.py is missing`);

// Generated data.
const settingsPath = resolve(dataRoot, SETTINGS_PATH);
const applied = await exists(settingsPath);
if (applied) {
  if (!same(await readJson(settingsPath), settingsBlueprint(config))) errors.push(`${SETTINGS_PATH} differs from the catalog`);
  for (const [id, value] of Object.entries(needBlueprints(config, energy, grease))) {
    const path = resolve(dataRoot, 'Needs', `Need.Bot.${id}.blueprint.json`);
    if (!await exists(path) || !same(await readJson(path), value)) errors.push(`Need.Bot.${id} missing or different`);
  }
  const goodTemplate = await readJson(resolve(vanilla, 'Goods', 'Good.BotChassis.blueprint.json'));
  const recipeTemplate = await readJson(resolve(vanilla, 'Recipes', 'Recipe.MetalBlock.blueprint.json'));
  for (const part of config.parts) {
    const good = resolve(dataRoot, 'Goods', `Good.${part.id}.blueprint.json`);
    if (!await exists(good) || !same(await readJson(good), partGood(config, part, goodTemplate))) errors.push(`Good.${part.id} missing or different`);
    const recipe = resolve(dataRoot, 'Recipes', `Recipe.${part.id}.blueprint.json`);
    if (!await exists(recipe) || !same(await readJson(recipe), partRecipe(part, recipeTemplate))) errors.push(`Recipe.${part.id} missing or different`);
    const building = await readJson(resolve(dataRoot, `${part.building}.json`));
    if (building.ManufactorySpec.ProductionRecipeIds.filter((r) => r === part.id).length !== 1) errors.push(`${part.building} must run ${part.id} once`);
    for (const icon of [`Sprites/Goods/${part.id}Icon.png`, `Sprites/Goods/${part.id}Icon.png.meta.json`]) if (!await exists(resolve(dataRoot, icon))) errors.push(`${icon} is not generated`);
  }
  for (const [id, effects] of Object.entries(config.consumption)) {
    const good = await readJson(resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`));
    if (!same(good.GoodSpec.ConsumptionEffects, consumptionEffects(effects))) errors.push(`Good.${id}: ConsumptionEffects differ from the catalog`);
  }
  // No other good may serve a Reactor Bot need (they are bot-only and switched per bot).
  const needIds = new Set(allNeeds(config).map((n) => n.id));
  const goods = (await readJson(resolve(dataRoot, 'GoodCollections', 'GoodCollection.IronTeeth.blueprint.json'))).GoodCollectionSpec['Goods#append'];
  for (const id of goods) {
    if (Object.hasOwn(config.consumption, id)) continue;
    const path = resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`);
    if (await exists(path) && (await readJson(path)).GoodSpec.ConsumptionEffects.some((e) => needIds.has(e.NeedId))) errors.push(`Good.${id}: undeclared Reactor Bot ConsumptionEffects`);
  }
  for (const part of config.parts) if (!goods.includes(part.id)) errors.push(`GoodCollection lacks ${part.id}`);
  const needs = (await readJson(resolve(dataRoot, 'NeedCollections', 'NeedCollection.IronTeeth.blueprint.json'))).NeedCollectionSpec['Needs#append'];
  for (const id of needIds) if (!needs.includes(id)) errors.push(`NeedCollection lacks ${id}`);
  const light = resolve(dataRoot, 'IlluminationColors', `IlluminationColor.${config.upgrade.illumination.id}.blueprint.json`);
  if (!await exists(light) || !same(await readJson(light), illuminationBlueprint(config))) errors.push('Reactor Bot illumination colour missing or different');

  const s = config.station;
  const stationRel = `${s.folder}/${s.id}.IronTeeth.blueprint`;
  const stationPath = resolve(dataRoot, `${stationRel}.json`);
  if (!await exists(stationPath)) errors.push(`${stationRel} is not generated`);
  else {
    const station = await readJson(stationPath);
    const slots = await readJson(resolve(root, 'outputs', 'lategame-integration', `${s.id}-visitor-slots.json`));
    for (const [name, value] of Object.entries(stationComponents(config, slots.count))) if (!same(station[name], value)) errors.push(`${stationRel}: ${name} differs from the catalog`);
    if (station.AttractionSpec.Effects.some((e) => config.upgrade.replacedNeeds.includes(e.NeedId))) errors.push(`${stationRel} serves a vanilla need; ordinary bots would use it`);
    if (station.BuildingSpec.ScienceCost !== s.science) errors.push(`${stationRel}: ScienceCost differs`);
    if (station.TransformSlotInitializerSpec?.Slots?.[0]?.SlotKeyword !== slots.keyword) errors.push(`${stationRel}: slot keyword differs from the exported model`);
    if (station.TemplateAttachmentsSpec || station.EnterableParticleControllerSpec) errors.push(`${stationRel} keeps the vanilla station's smoke attachment`);
    const collection = (await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'))).TemplateCollectionSpec['Blueprints#append'];
    if (!collection.includes(stationRel)) errors.push(`${stationRel} is not collected`);
    const automation = await readJson(resolve(root, 'tools', 'automation_content.json'));
    if (!automation.templates[stationRel]) errors.push(`automation: templates lacks ${stationRel}`);
    if (!await exists(resolve(dataRoot, `${s.folder}/${s.id}Icon.png`))) errors.push(`${s.id} icon is not generated`);
  }
  const csv = await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8');
  for (const [key] of rows) if (!csv.includes(`\n${key},`)) errors.push(`enUS.csv lacks ${key}`);
}

if (errors.length) {
  console.error(`Reactor bots: ${errors.length} error(s)\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
const days = 1 / -chargeDailyDelta(config, energy);
console.log(`Reactor bots: OK (${applied ? 'applied data' : 'catalog only'}; x${1 + config.upgrade.carryingCapacityBonus} load, x${config.upgrade.speedMultiplier} speed, ` +
  `x${config.upgrade.lifespanMultiplier} lifespan, charge every ${days.toFixed(1)} days at ${config.station.id} ${config.station.powerInput} hp).`);
