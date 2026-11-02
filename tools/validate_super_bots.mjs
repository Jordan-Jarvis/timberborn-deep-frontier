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
// - the skin: the glow is a neon yellow of the radiation hue (RadiationMaterials.WaterTintColor,
//   within 5 degrees, at full saturation and value) written to an HDR emission map, the joint seams
//   come from the body mesh, the BotURP texture names ReactorBotSkin sets match the official shader
//   graph, no native texture setter replaces them, and the dark plating follows the plating need;
// - working speed: ReactorBot adds the native WorkingSpeed bonus (delta workingSpeedMultiplier - 1), whose
//   clamp allows it, and the native Worker, ProduceExecutor and BuildExecutor still read and apply it
//   (decompiled from the project's Timberborn plugin assemblies with tools/dotnet/ilspycmd.exe);
// - leaks: ReactorBotLeak's settings record, its conditions (the coolant need's native critical state,
//   the plating need), the radiation system's own add path and open-cell rule, the doorstep while inside
//   a building, saved state, no notices of its own; the coolant need is critical (Need.IsInCriticalState);
//   the rate stays below a waste building's leak;
// - when generated: the settings, needs, goods, recipes, manufactories, upkeep effects, light colour, charging bay, collections, icons, localization and its automation declaration.
// Exits 1 on any error. Runtime behaviour is verified in game, not here.
import {readFile, access} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadSuperBotConfig, checkSuperBotConfig, settingsBlueprint, glowJoints, needBlueprints, partGood, partRecipe, consumptionEffects,
  illuminationBlueprint, stationComponents, localizationRows, chargeDailyDelta, allNeeds, PANEL_KEYS, SETTINGS_PATH, SETTINGS_SPEC, LEAK_SPEC} from './super_bot_content.mjs';
import {VAULT, REFINERY} from './meltdown_content.mjs';

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
const leakSource = await readFile(resolve(scripts, 'ReactorBotLeak.cs'), 'utf8');
const leakBody = leakSource.match(/record FrontierReactorBotLeakSpec\b[^{]*\{([\s\S]*?)\n  \}/)?.[1];
const leakFields = leakBody ? [...leakBody.matchAll(/\[Serialize\] public [\w<>.]+ (\w+) \{/g)].map((m) => m[1]).sort() : [];
if (!same(leakFields, Object.keys(settingsBlueprint(config)[LEAK_SPEC]).sort()))
  errors.push(`runtime: FrontierReactorBotLeakSpec serializes [${leakFields}], generator writes [${Object.keys(settingsBlueprint(config)[LEAK_SPEC]).sort()}]`);
// The leak: native need states, the radiation system's own open-cell rule and add path, the doorstep while
// hidden in a building, saved hours, decorated on every bot's ReactorBot, and no status or notification.
for (const [needle, what] of [
  ['_needs.NeedIsInCriticalState(Spec.CoolantNeedId)', "reads overheating as the coolant need's native critical state"],
  ['_unplatedHours=_bot.IsPlated?0f:', 'reads unmaintained as the plating need (ReactorBot.IsPlated)'],
  ['_overheatedHours>Spec.OverheatHours||_unplatedHours>Spec.UnmaintainedHours', 'leaks past either threshold'],
  ['_radiation.TryFindOpenCell(new Vector2Int(at.x,at.y),at.z,out var cell)', 'finds the cell with IRadiationService.TryFindOpenCell'],
  ['_radiation.AddRadioactiveWater(cell,Spec.VolumePerHour*Spec.PulseHours)', 'adds VolumePerHour x PulseHours through IRadiationService.AddRadioactiveWater'],
  ['block.PositionedEntrance.DoorstepCoordinates', 'leaks at the doorstep while inside a building'],
  ['NavigationCoordinateSystem.WorldToGridInt(Transform.position)', "leaks at the bot's own cell outside"],
  ['IPersistentEntity', 'saves its hours'],
  ['AddDecorator<ReactorBot,ReactorBotLeak>()', 'is decorated on ReactorBot'],
]) if (!leakSource.includes(needle)) errors.push(`runtime: ReactorBotLeak no longer ${what} (${needle})`);
if (/NotificationBus|StatusToggle|StatusSubject|IAlertFragment/.test(leakSource)) errors.push('runtime: ReactorBotLeak must add no notice or status of its own (the native need statuses and the yellow water show it)');
if (/\+=/.test(leakSource.match(/public void Awake\(\) \{([\s\S]*?)\n    \}/)?.[1] ?? '')) errors.push('runtime: ReactorBotLeak subscribes to events in Awake (subscribe after loading, as ReactorBot does)');
const configurator = await readFile(resolve(scripts, 'ReactorBotConfigurator.cs'), 'utf8');
if (!/AddDecorator<BotSpec,ReactorBot>\(\)/.test(configurator)) errors.push('runtime: ReactorBot is not decorated on the native BotSpec');
const panel = await readFile(resolve(scripts, 'ReactorBotPanel.cs'), 'utf8');
const rows = localizationRows(config, energy);
const rowKeys = new Set(rows.map(([k]) => k));
for (const [, key] of panel.matchAll(/"(DeepFrontier\.ReactorBot\.[A-Za-z.]+)"/g)) if (!rowKeys.has(key)) errors.push(`runtime: ReactorBotPanel.cs uses ${key}, which the generator does not write`);
for (const key of PANEL_KEYS) if (!panel.includes(`"${key}"`)) errors.push(`runtime: ${key} is generated but unused by ReactorBotPanel.cs`);
const reactorBot = await readFile(resolve(scripts, 'ReactorBot.cs'), 'utf8');
if (!reactorBot.includes('_material.SetTexture(ReactorBotSkin.BaseMapId,IsPlated?_textures.Plated:_textures.Unplated)') || !reactorBot.includes('e.NeedSpec.Id==Spec.PlatingNeedId) { ApplyPlating();')
    || !reactorBot.includes('_material.SetTexture(ReactorBotSkin.EmissionMapId,_textures.Emission)'))
  errors.push('runtime: ReactorBot no longer sets the yellow eyes and swaps the dark plating with the plating need');
if (!reactorBot.includes('WorkingSpeedBonusId="WorkingSpeed"') || !reactorBot.includes('_bonuses.AddBonus(WorkingSpeedBonusId,Spec.WorkingSpeedMultiplier-1f)'))
  errors.push('runtime: ReactorBot no longer adds the native WorkingSpeed bonus (delta WorkingSpeedMultiplier - 1)');
const radiation = await readFile(resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Radiation', 'RadiationMaterials.cs'), 'utf8');
const yellow = radiation.match(/\bWaterTintColor = new Color\(([\d.]+)f, ([\d.]+)f, ([\d.]+)f,/)?.slice(1).map(Number);
if (!yellow) errors.push('runtime: RadiationMaterials.WaterTintColor (the radiation yellow) not found');
// Neon: the radiation yellow's hue (within 5 degrees) at full saturation and value (user 2026-11-02: "neon yellow, bright yellow").
const hue = ([r, g, b]) => {
  const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
  if (d === 0) return NaN;
  const h = max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4;
  return (h * 60 + 360) % 360;
};
const glow = config.upgrade.glow?.color;
if (yellow && glow) {
  const rgb = [glow.r, glow.g, glow.b];
  if (!(Math.abs(hue(rgb) - hue(yellow)) <= 5)) errors.push(`catalog: upgrade.glow.color hue ${hue(rgb).toFixed(1)} must be within 5 degrees of the radiation yellow's ${hue(yellow).toFixed(1)} (RadiationMaterials.WaterTintColor)`);
  if (Math.max(...rgb) !== 1 || Math.min(...rgb) !== 0) errors.push(`catalog: upgrade.glow.color ${rgb} must be neon: full value (a channel at 1) and full saturation (a channel at 0)`);
  const light = config.upgrade.illumination.color;
  if (!same([light.r, light.g, light.b], rgb)) errors.push('catalog: upgrade.illumination.color must be the glow colour');
}
const jointNames = glowJoints(config).map((j) => j.Name);
if (new Set(jointNames).size !== jointNames.length) errors.push(`catalog: upgrade.glow.joints give duplicate names (${jointNames})`);
// BotURP: the reference names of Base Map and Emission Map (official shader graph) are what ReactorBotSkin sets.
const graph = await readFile(resolve(vanilla, 'Shaders', 'BotURP.shadergraph'), 'utf8');
const skin = await readFile(resolve(scripts, 'ReactorBotSkin.cs'), 'utf8');
// HDR glow (a half-float linear emission map can exceed 1) and the joint seams from the body mesh.
if (!skin.includes('new Texture2D(width,height,TextureFormat.RGBAHalf,true,true)')) errors.push('runtime: ReactorBotSkin no longer writes the glow to a linear half-float emission map');
if (!reactorBot.includes('_skin.For(body.sharedMaterial,filter.sharedMesh)')) errors.push('runtime: ReactorBot no longer gives the skin the bot body mesh for the joint seams');
for (const [display, reference, constant] of [['Base Map', '_BaseMap', 'BaseMapProperty'], ['Emission Map', '_BaseMap_1', 'EmissionMapProperty']]) {
  if (!new RegExp(`"m_Name": "${display}"[\\s\\S]{0,600}?"m_OverrideReferenceName": "${reference}"`).test(graph)) errors.push(`native: BotURP.shadergraph ${display} is no longer ${reference}`);
  if (!skin.includes(`${constant}="${reference}"`)) errors.push(`runtime: ReactorBotSkin.${constant} must be "${reference}"`);
}
const patches = await readFile(resolve(scripts, 'ReactorBotPatches.cs'), 'utf8');
for (const target of ['WalkerSpeedManager),nameof(WalkerSpeedManager.Tick)', 'Deteriorable),nameof(Deteriorable.Tick)'])
  if (!patches.includes(target)) errors.push(`runtime: ReactorBotPatches.cs no longer patches ${target}`);

// Native contracts.
const bot = await readJson(resolve(vanilla, 'Characters', 'Bot', 'Bot.IronTeeth.blueprint.json'));
// Native CharacterTextureSetter would replace the body textures in PostInitializeEntity.
if (bot.CharacterTextureSetterSpec) errors.push('native: the vanilla bot now has a CharacterTextureSetterSpec, which would replace the Reactor Bot skin');
if (!bot.BotSpec || bot.CriticalNeedStateAnimationSpec?.NeedId !== config.upgrade.replacedNeeds[0] || bot.CriticalNeedStateAnimationSpec?.Animation !== config.upgrade.noChargeAnimation)
  errors.push('native: the vanilla bot template no longer drives the catalog noChargeAnimation from the replaced need');
const speed = await readJson(resolve(vanilla, 'BonusTypes', 'BonusType.MovementSpeed.blueprint.json')).catch(() => null);
const carry = await readJson(resolve(vanilla, 'BonusTypes', 'BonusType.CarryingCapacity.blueprint.json')).catch(() => null);
if (!speed || speed.BonusTypeSpec.MaximumValue >= config.upgrade.speedMultiplier) errors.push('native: MovementSpeed bonus no longer clamps below the speed multiplier; reconsider the speed patch');
if (!carry || 1 + config.upgrade.carryingCapacityBonus > carry.BonusTypeSpec.MaximumValue) errors.push('native: CarryingCapacity bonus clamps below the carrying buff');
if (!(await exists(resolve(root, 'tools', 'asset-pipeline', `lategame_${config.station.id}.py`)))) errors.push(`art: tools/asset-pipeline/lategame_${config.station.id}.py is missing`);
const working = await readJson(resolve(vanilla, 'BonusTypes', 'BonusType.WorkingSpeed.blueprint.json')).catch(() => null);
if (!working || working.BonusTypeSpec.Id !== 'WorkingSpeed' || working.BonusTypeSpec.MaximumValue < config.upgrade.workingSpeedMultiplier)
  errors.push(`native: the WorkingSpeed bonus clamps below x${config.upgrade.workingSpeedMultiplier}; reconsider the working speed`);
if (!needBlueprints(config, energy, grease)[config.needs.coolant.id].CriticalNeedSpec) errors.push("catalog: the leak's coolant need must be critical (its critical state is overheating)");

// Native contract (Timberborn 1.1.2.8), decompiled from the project's plugin assemblies.
const plugins = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
const decompile = (dll, type) => {
  try {
    return execFileSync(resolve(root, 'tools', 'dotnet', 'ilspycmd.exe'), [resolve(plugins, dll), '-r', plugins, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20});
  } catch (error) {
    errors.push(`native: ${dll} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
    return '';
  }
};
for (const [dll, type, patterns, what] of [
  ['Timberborn.WorkSystem.dll', 'Timberborn.WorkSystem.Worker', [/WorkingSpeedBonusId = "WorkingSpeed"/, /WorkingSpeedMultiplier = _bonusManager\.Multiplier\(WorkingSpeedBonusId\)/],
    'Worker.Tick reads the WorkingSpeed bonus into WorkingSpeedMultiplier'],
  ['Timberborn.Workshops.dll', 'Timberborn.Workshops.ProduceExecutor', [/IncreaseProductionProgress\(deltaTimeInHours \* _worker\.WorkingSpeedMultiplier\)/], 'production progress scales with WorkingSpeedMultiplier'],
  ['Timberborn.ConstructionSites.dll', 'Timberborn.ConstructionSites.BuildExecutor', [/IncreaseBuildTime\(deltaTimeInHours \* _worker\.WorkingSpeedMultiplier\)/], 'construction progress scales with WorkingSpeedMultiplier'],
  ['Timberborn.BonusSystem.dll', 'Timberborn.BonusSystem.BonusManager', [/new Bonus\(1f, spec\.MinimumValue, spec\.MaximumValue\)/, /_bonuses\[bonusId\]\.ModifyValue\(multiplierDelta\)/, /Mathf\.Clamp\(_value, _min, _max\)/],
    'bonuses start at 1, add deltas and clamp to the bonus type'],
  ['Timberborn.NeedSystem.dll', 'Timberborn.NeedSystem.Need', [/if \(IsCritical\)\s*\{\s*return !IsFavorable;/], 'a critical need is in its critical state while not favourable'],
]) {
  const source = decompile(dll, type);
  if (source && !patterns.every((p) => p.test(source))) errors.push(`native: ${type}: no longer true that ${what}`);
}

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
  // Modest: a leaking bot releases less than a full waste vault or a blocked refinery.
  for (const building of [VAULT, REFINERY]) {
    const spec = (await readJson(resolve(dataRoot, `${building}.json`))).WasteLeakSpec;
    const rate = spec.GoodsPerLeak * spec.SludgeVolumePerGood / spec.LeakIntervalHours;
    if (!(config.leak.volumePerHour < rate)) errors.push(`catalog: leak.volumePerHour ${config.leak.volumePerHour} must stay below ${building}'s leak (${rate.toFixed(3)} per hour)`);
  }
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
  `x${config.upgrade.workingSpeedMultiplier} working speed, x${config.upgrade.lifespanMultiplier} lifespan, charge every ${days.toFixed(1)} days at ${config.station.id} ${config.station.powerInput} hp; ` +
  `leaks ${config.leak.volumePerHour}/h after ${config.leak.overheatHours} h overheated or ${config.leak.unmaintainedHours} h unplated).`);
