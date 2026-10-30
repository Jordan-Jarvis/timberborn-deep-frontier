// Reactor Bots (super bots): an in-place upgrade of the ordinary Iron Teeth bot
// (tools/super_bots.json; user direction 2026-10-29: same bot, same template,
// a saved per-bot flag). Runtime: src/DeepFrontier/Scripts/SuperBots.
//
// Runs in canonical generation after the expansion generator (it extends
// the generated goods, the Precision Machine Works and Uranium Processing
// Plant recipe lists, and the Iron Teeth good, need and template collections)
// and after bot upkeep, before the automation audit:
//   await (await import('./super_bot_content.mjs')).applySuperBots();
//
// Writes:
// - Configurations/DeepFrontierReactorBots.blueprint.json: the singleton
//   FrontierReactorBotSettingsSpec the runtime reads (buffs, need ids, skin).
// - The Bot needs (retrofit parts, charge, coolant, plating) and their
//   NeedCollection entries. The runtime switches them per bot with native
//   NeedManager.EnableNeed/DisableNeed: ordinary bots keep only vanilla Energy.
// - Three part goods with their recipes, appended to the generated
//   manufactories named in the catalog. Each part's ConsumptionEffects fill
//   one retrofit need: a queued bot takes one of each from storage (native
//   InventoryNeedBehavior) and is upgraded once every retrofit need is full.
// - Bot-only ConsumptionEffects on generated upkeep goods (coolant, plating).
// - IlluminationColors/IlluminationColor.<id>: the Reactor Bot light colour.
// - The Reactor Charging Bay: vanilla ChargingStation.IronTeeth turned into a
//   powered goods-consuming attraction serving only ReactorCharge, with the
//   geometry, model and visitor slots of its late-game study.
// - Icons and DeepFrontier.ReactorBot.* / goods / needs / building rows.
// Reruns: its own files (settings, needs, part goods and recipes, light
// colour, charging bay, icons) are rewritten each run, byte-identical when
// the inputs are unchanged. The files it extends (collections, manufactories,
// upkeep goods, enUS.csv) are rewritten fresh by their producers each
// canonical run, so none of its ids may already be in them, and no vanilla
// good, recipe, need or colour may carry one of its ids. It fails, without
// writing anything, on any missing input or such collision.
import {readFile, writeFile, access, mkdir} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
// The late-game modules load their catalogs at import; they are imported
// only by generation, so the validator does not depend on them.
const lategame = () => import('./lategame_building_content.mjs');
const costs = () => import('./lategame_costs.mjs');
import {ICON_KINDS, renderNativeIcon, writeReviewSheet} from './native_icon_style.mjs';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const CONFIG = 'tools/super_bots.json';
export const SETTINGS_PATH = 'Configurations/DeepFrontierReactorBots.blueprint.json';
export const SETTINGS_SPEC = 'FrontierReactorBotSettingsSpec';
const VANILLA = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];
const GOODS = 'GoodCollections/GoodCollection.IronTeeth.blueprint.json';
const NEEDS = 'NeedCollections/NeedCollection.IronTeeth.blueprint.json';
const TEMPLATES = 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json';
const STATION_TEMPLATE = 'Buildings/Science/ChargingStation/ChargingStation.IronTeeth.blueprint.json';
// Components of the vanilla station that belong to its own model.
const STATION_MODEL_ONLY = ['EnterableParticleControllerSpec', 'TemplateAttachmentsSpec'];

// Fixed texts used by ReactorBotPanel.cs (ILoc.T takes at most three parameters).
export const PANEL_KEYS = ['Title', 'Ordinary', 'Queued', 'Upgraded', 'Unplated', 'Queue', 'Cancel'].map((k) => `DeepFrontier.ReactorBot.Panel.${k}`);

const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const exists = (path) => access(path).then(() => true, () => false);
const clone = (value) => JSON.parse(JSON.stringify(value));
const csvCell = (value) => {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csvRow = (id, text) => [id, text, 'Deep Frontier reactor bots'].map(csvCell).join(',');
const isColor = (c) => c && ['r', 'g', 'b', 'a'].every((k) => typeof c[k] === 'number' && c[k] >= 0 && c[k] <= 1);
const fmt = (n) => Number(n.toFixed(2)).toString();

export const allNeeds = (c) => [...c.needs.retrofit, c.needs.charge, c.needs.coolant, c.needs.plating];
export const loadSuperBotConfig = async (root = defaultRoot) => readJson(resolve(root, CONFIG));

export function checkSuperBotConfig(c) {
  const errors = [];
  const u = c.upgrade, n = c.needs, s = c.station;
  if (!u) errors.push('upgrade is missing');
  else {
    if (!(u.carryingCapacityBonus > 0)) errors.push('upgrade.carryingCapacityBonus must be positive');
    if (!(u.speedMultiplier > 1)) errors.push('upgrade.speedMultiplier must exceed 1');
    if (!(u.lifespanMultiplier > 1)) errors.push('upgrade.lifespanMultiplier must exceed 1');
    if (!(u.unplatedWearMultiplier > 1)) errors.push('upgrade.unplatedWearMultiplier must exceed 1');
    if (!Array.isArray(u.replacedNeeds) || !u.replacedNeeds.length) errors.push('upgrade.replacedNeeds must list the vanilla needs a Reactor Bot loses');
    if (!u.noChargeAnimation) errors.push('upgrade.noChargeAnimation is required');
    if (!/^[A-Za-z]+$/.test(u.illumination?.id ?? '') || !isColor(u.illumination?.color)) errors.push('upgrade.illumination needs an id and an rgba colour');
    if (!isColor(u.tint)) errors.push('upgrade.tint must be an rgba colour');
  }
  for (const key of ['charge', 'coolant', 'plating']) {
    if (!/^[A-Z][A-Za-z]+$/.test(n?.[key]?.id ?? '') || !n[key].name) errors.push(`needs.${key} needs a PascalCase id and a name`);
  }
  if (!Array.isArray(n?.retrofit) || !n.retrofit.length || n.retrofit.some((r) => !/^[A-Z][A-Za-z]+$/.test(r.id ?? '') || !r.name))
    errors.push('needs.retrofit must list {id, name} retrofit needs');
  if (n?.charge && !(n.charge.energyFactor > 0 && n.charge.energyFactor < 1)) errors.push('needs.charge.energyFactor must lie in (0, 1)');
  for (const key of ['coolant', 'plating']) if (n?.[key] && !(n[key].dailyDelta < 0)) errors.push(`needs.${key}.dailyDelta must be negative`);
  for (const key of ['charge', 'coolant']) if (n?.[key] && !(n[key].sprite && n[key].status && n[key].statusShort)) errors.push(`needs.${key} is critical: sprite, status and statusShort are required`);
  for (const key of ['charge', 'coolant', 'plating']) if (n?.[key] && !(n[key].hoursWarningThreshold > 0 && n[key].unfavorableWellbeing < 0)) errors.push(`needs.${key} needs hoursWarningThreshold and a negative unfavorableWellbeing`);
  const needIds = new Set(allNeeds(c).map((x) => x.id));
  for (const [good, effects] of Object.entries(c.consumption ?? {})) {
    if (!Array.isArray(effects) || !effects.length || effects.some(([need, points]) => !needIds.has(need) || !(points > 0 && points <= 1)))
      errors.push(`consumption.${good} must list [Reactor Bot need, points in (0, 1]]`);
  }
  // Each retrofit need is filled, exactly once, by one part.
  for (const r of n?.retrofit ?? []) {
    const fillers = (c.parts ?? []).filter((p) => (c.consumption?.[p.id] ?? []).some(([need, points]) => need === r.id && points === 1));
    const others = Object.entries(c.consumption ?? {}).filter(([g, e]) => !(c.parts ?? []).some((p) => p.id === g) && e.some(([need]) => need === r.id));
    if (fillers.length !== 1 || others.length) errors.push(`consumption: retrofit need ${r.id} must be filled with 1 point by exactly one part`);
  }
  if (!Array.isArray(c.parts) || !c.parts.length) errors.push('parts are missing');
  for (const p of c.parts ?? []) {
    if (!/^[A-Z][A-Za-z]+$/.test(p.id ?? '') || !p.name || !p.plural) errors.push(`part ${p.id}: id, name and plural are required`);
    if (!/^Buildings\/.+\.IronTeeth\.blueprint$/.test(p.building ?? '')) errors.push(`part ${p.id}: building must be a generated Buildings/ blueprint path`);
    if (!(p.hours > 0) || !Number.isInteger(p.products) || p.products < 1) errors.push(`part ${p.id}: hours and products are required`);
    if (!Array.isArray(p.ingredients) || !p.ingredients.length || p.ingredients.length > 4 || p.ingredients.some(([g, a]) => !g || !Number.isInteger(a) || a <= 0))
      errors.push(`part ${p.id}: 1..4 [good, positive integer] ingredients`);
    if (!Number.isInteger(p.order) || !Array.isArray(p.color) || p.color.length !== 2) errors.push(`part ${p.id}: order and [r, g] colour are required`);
  }
  if (!s) errors.push('station is missing');
  else {
    if (!/^[A-Z][A-Za-z]+$/.test(s.id ?? '') || s.folder !== `Buildings/Science/${s.id}` || !s.name || !s.flavor) errors.push('station: id, folder Buildings/Science/<id>, name and flavor are required');
    if (!(s.pointsPerHour > 0) || !Number.isInteger(s.powerInput) || s.powerInput <= 0) errors.push('station: pointsPerHour and powerInput are required');
    if (!Array.isArray(s.fuel) || s.fuel.length !== 2 || !(s.fuel[1] > 0)) errors.push('station.fuel must be [good, goods per hour]');
    if (!Number.isInteger(s.fullInventoryWorkHours) || !Number.isInteger(s.science) || !s.toolGroup || !Number.isInteger(s.toolOrder)) errors.push('station: fullInventoryWorkHours, science, toolGroup and toolOrder are required');
  }
  return errors;
}

// Daily delta of the vanilla need the charge need replaces, scaled.
export const chargeDailyDelta = (config, energy) => energy.NeedSpec.DailyDelta * config.needs.charge.energyFactor;

export function settingsBlueprint(c) {
  const n = c.needs, u = c.upgrade;
  return {[SETTINGS_SPEC]: {
    RetrofitNeedIds: n.retrofit.map((r) => r.id),
    ChargeNeedId: n.charge.id,
    PlatingNeedId: n.plating.id,
    ReactorNeedIds: [n.charge.id, n.coolant.id, n.plating.id],
    ReplacedNeedIds: [...u.replacedNeeds],
    NoChargeAnimation: u.noChargeAnimation,
    CarryingCapacityBonus: u.carryingCapacityBonus,
    SpeedMultiplier: u.speedMultiplier,
    LifespanMultiplier: u.lifespanMultiplier,
    UnplatedWearMultiplier: u.unplatedWearMultiplier,
    IlluminationColorId: u.illumination.id,
    Tint: {...u.tint},
  }};
}

// Need blueprints from vanilla Bot needs: critical ones from Energy, the
// others from Grease (a boost need, regrouped as a basic need here).
export function needBlueprints(c, energy, grease) {
  const n = c.needs;
  const critical = (need, order, dailyDelta) => {
    const value = clone(energy);
    Object.assign(value.NeedSpec, {Id: need.id, BackwardCompatibleIds: [], Order: order, StartingValue: 1, DailyDelta: dailyDelta,
      HoursWarningThreshold: need.hoursWarningThreshold, DisplayNameLocKey: `Need.${need.id}.DisplayName`,
      FavorableWellbeing: 0, UnfavorableWellbeing: need.unfavorableWellbeing});
    Object.assign(value.CriticalNeedSpec, {SpriteName: need.sprite, DescriptionLocKey: `Status.Need.${need.id}`, DescriptionShortLocKey: `Status.Need.${need.id}.Short`});
    return value;
  };
  const plain = (need, order, fields) => {
    const value = clone(grease);
    Object.assign(value.NeedSpec, {Id: need.id, BackwardCompatibleIds: [], Order: order, NeedGroupId: energy.NeedSpec.NeedGroupId,
      DisplayNameLocKey: `Need.${need.id}.DisplayName`, FavorableWellbeing: 0, ...fields});
    return value;
  };
  return {
    ...Object.fromEntries(n.retrofit.map((r, i) => [r.id, plain(r, 5 + i, {StartingValue: 0, DailyDelta: 0, HoursWarningThreshold: 0, UnfavorableWellbeing: 0})])),
    [n.charge.id]: critical(n.charge, 11, chargeDailyDelta(c, energy)),
    [n.coolant.id]: critical(n.coolant, 12, n.coolant.dailyDelta),
    [n.plating.id]: plain(n.plating, 13, {StartingValue: 1, DailyDelta: n.plating.dailyDelta,
      HoursWarningThreshold: n.plating.hoursWarningThreshold, UnfavorableWellbeing: n.plating.unfavorableWellbeing}),
  };
}

export const consumptionEffects = (effects) => effects.map(([NeedId, Points]) => ({NeedId, Points}));

export function partGood(c, part, template) {
  const value = clone(template);
  Object.assign(value.GoodSpec, {Id: part.id, BackwardCompatibleIds: [], ConsumptionEffects: consumptionEffects(c.consumption[part.id] ?? []),
    GoodOrder: part.order, ContainerColor: {r: part.color[0], g: part.color[1], b: 0.28, a: 1}, ForceImport: true,
    Icon: `Sprites/Goods/${part.id}Icon`, DisplayNameLocKey: `Good.${part.id}.DisplayName`, PluralDisplayNameLocKey: `Good.${part.id}.PluralDisplayName`});
  return value;
}

export function partRecipe(part, template) {
  const value = clone(template);
  value.RecipeSpec = {...value.RecipeSpec, Id: part.id, BackwardCompatibleIds: [], DisplayLocKey: `Good.${part.id}.PluralDisplayName`,
    CycleDurationInHours: part.hours, Ingredients: part.ingredients.map(([Id, Amount]) => ({Id, Amount})),
    Products: [{Id: part.id, Amount: part.products}], ProducedSciencePoints: 0, Fuel: '', CyclesFuelLasts: 0, FuelCapacity: 0,
    CyclesCapacity: 30, Icon: `Sprites/Goods/${part.id}Icon`};
  return value;
}

export const illuminationBlueprint = (c) => ({IlluminationColorSpec: {Id: c.upgrade.illumination.id, Color: {...c.upgrade.illumination.color}}});

// Station native components (everything but geometry, which applyLategame adds).
export function stationComponents(c, slots) {
  const s = c.station;
  return {
    AttractionSpec: {Effects: [{NeedId: c.needs.charge.id, PointsPerHour: s.pointsPerHour, SatisfyToMaxValue: true}]},
    EnterableSpec: {OperatingState: 'Finished', LimitedCapacityFinished: true, CapacityFinished: slots, LimitedCapacityUnfinished: false, CapacityUnfinished: 0},
    GoodConsumingBuildingSpec: {FullInventoryWorkHours: s.fullInventoryWorkHours, ConsumedGoods: [{GoodId: s.fuel[0], GoodPerHour: s.fuel[1]}]},
    PoweredGoodConsumingBuildingSpec: {},
    GoodConsumingAttractionSpec: {},
    MechanicalNodeSpec: {PowerOutput: 0, PowerInput: s.powerInput, IsShaft: false},
  };
}

export function localizationRows(c, energy) {
  const n = c.needs, u = c.upgrade, s = c.station;
  const chargeDays = 1 / -chargeDailyDelta(c, energy);
  const parts = c.parts.filter((p) => (c.consumption[p.id] ?? []).some(([need]) => n.retrofit.some((r) => r.id === need))).map((p) => p.name).join(' and ');
  const coolant = Object.entries(c.consumption).filter(([, e]) => e.some(([id]) => id === n.coolant.id)).map(([g]) => g);
  const rows = [];
  for (const p of c.parts) rows.push([`Good.${p.id}.DisplayName`, p.name], [`Good.${p.id}.PluralDisplayName`, p.plural]);
  for (const need of allNeeds(c)) rows.push([`Need.${need.id}.DisplayName`, need.name]);
  for (const key of ['charge', 'coolant']) rows.push([`Status.Need.${n[key].id}`, n[key].status], [`Status.Need.${n[key].id}.Short`, n[key].statusShort]);
  rows.push([`Building.${s.id}.DisplayName`, s.name],
    [`Building.${s.id}.Description`, `Charges two Reactor Bots at once; ordinary bots use the Charging Station. Burns ${fmt(s.fuel[1])} enriched fuel per hour while a bot charges and needs ${s.powerInput.toLocaleString('en-US')} hp. A full charge lasts a Reactor Bot ${fmt(chargeDays)} days. No workers.`],
    [`Building.${s.id}.FlavorDescription`, s.flavor],
    ['DeepFrontier.ReactorBot.Panel.Title', 'Reactor retrofit'],
    ['DeepFrontier.ReactorBot.Panel.Ordinary', `A ${parts} retrofit makes this bot a Reactor Bot: ${1 + u.carryingCapacityBonus}× load, ${u.speedMultiplier}× speed, ${u.lifespanMultiplier}× lifespan, charged at a ${s.name} every ${fmt(chargeDays)} days. Upkeep: coolant (${coolant.length} kinds) and steel plating from storage.`],
    ['DeepFrontier.ReactorBot.Panel.Queued', `Retrofit queued: the bot fetches a ${parts} from storage as soon as its district stocks them.`],
    ['DeepFrontier.ReactorBot.Panel.Upgraded', `Reactor Bot: ${1 + u.carryingCapacityBonus}× load, ${u.speedMultiplier}× speed, wears out ${u.lifespanMultiplier}× slower. Charges at a ${s.name}.`],
    ['DeepFrontier.ReactorBot.Panel.Unplated', `No steel plating: wearing out ${u.unplatedWearMultiplier}× faster until it takes high-grade steel or alloy.`],
    ['DeepFrontier.ReactorBot.Panel.Queue', 'Retrofit to Reactor Bot'],
    ['DeepFrontier.ReactorBot.Panel.Cancel', 'Cancel retrofit']);
  return rows;
}

const icons = (c) => [...c.parts.map((p) => [p.id, 'good', `Sprites/Goods/${p.id}Icon.png`]),
  [c.station.id, 'building', `${c.station.folder}/${c.station.id}Icon.png`]];

export async function planSuperBots({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const config = await loadSuperBotConfig(root);
  const configErrors = checkSuperBotConfig(config);
  if (configErrors.length) throw new Error(`Reactor bots: ${CONFIG} is invalid:\n  ${configErrors.join('\n  ')}`);
  const vanilla = resolve(root, ...VANILLA);
  const errors = [];
  const writes = [];
  const goodPath = async (id) => {
    for (const base of [dataRoot, vanilla]) {
      const path = resolve(base, 'Goods', `Good.${id}.blueprint.json`);
      if (await exists(path)) return {path, generated: base === dataRoot};
    }
    return null;
  };
  const partIds = new Set(config.parts.map((p) => p.id));

  const energy = await readJson(resolve(vanilla, 'Needs', 'Need.Bot.Energy.blueprint.json'));
  const grease = await readJson(resolve(vanilla, 'Needs', 'Need.Bot.Grease.blueprint.json'));
  if (energy.NeedSpec.CharacterType !== 'Bot' || !energy.CriticalNeedSpec || !energy.NeedPreventingWorkSpec) errors.push('vanilla Need.Bot.Energy is no longer a critical, work-preventing Bot need');
  if (grease.NeedSpec.CharacterType !== 'Bot' || grease.CriticalNeedSpec) errors.push('vanilla Need.Bot.Grease is no longer a plain Bot need');
  for (const id of config.upgrade.replacedNeeds) if (!await exists(resolve(vanilla, 'Needs', `Need.Bot.${id}.blueprint.json`))) errors.push(`replaced need ${id} is not a vanilla Bot need`);
  for (const [id, value] of Object.entries(needBlueprints(config, energy, grease))) {
    if (await exists(resolve(vanilla, 'Needs', `Need.Bot.${id}.blueprint.json`))) errors.push(`need ${id} is a vanilla need`);
    writes.push({path: resolve(dataRoot, 'Needs', `Need.Bot.${id}.blueprint.json`), value});
  }

  // Parts: goods, recipes and their manufactories.
  const goodTemplate = await readJson(resolve(vanilla, 'Goods', 'Good.BotChassis.blueprint.json'));
  const recipeTemplate = await readJson(resolve(vanilla, 'Recipes', 'Recipe.MetalBlock.blueprint.json'));
  const buildings = new Map();
  for (const part of config.parts) {
    if (await exists(resolve(vanilla, 'Goods', `Good.${part.id}.blueprint.json`))) errors.push(`good ${part.id} is a vanilla good`);
    if (await exists(resolve(vanilla, 'Recipes', `Recipe.${part.id}.blueprint.json`))) errors.push(`recipe ${part.id} is a vanilla recipe`);
    for (const [good] of part.ingredients) if (!partIds.has(good) && !await goodPath(good)) errors.push(`part ${part.id}: ingredient ${good} is not a vanilla or generated good`);
    writes.push({path: resolve(dataRoot, 'Goods', `Good.${part.id}.blueprint.json`), value: partGood(config, part, goodTemplate)});
    writes.push({path: resolve(dataRoot, 'Recipes', `Recipe.${part.id}.blueprint.json`), value: partRecipe(part, recipeTemplate)});
    const path = resolve(dataRoot, `${part.building}.json`);
    if (!buildings.has(path)) {
      if (!await exists(path)) { errors.push(`part ${part.id}: ${part.building} is not generated`); continue; }
      buildings.set(path, await readJson(path));
    }
    const recipes = buildings.get(path).ManufactorySpec?.ProductionRecipeIds;
    if (!Array.isArray(recipes)) errors.push(`${part.building} is not a manufactory`);
    else if (recipes.includes(part.id)) errors.push(`${part.building} already runs ${part.id}`);
    else recipes.push(part.id);
  }
  for (const [path, value] of buildings) writes.push({path, value});

  // Bot-only consumption effects on existing generated goods.
  for (const [id, effects] of Object.entries(config.consumption)) {
    if (partIds.has(id)) continue;
    const found = await goodPath(id);
    if (!found?.generated) { errors.push(`consumption: ${id} is not a generated Deep Frontier good`); continue; }
    const value = await readJson(found.path);
    if (value.GoodSpec.ConsumptionEffects.length) { errors.push(`consumption: ${id} already has ConsumptionEffects; its producer must not`); continue; }
    value.GoodSpec.ConsumptionEffects = consumptionEffects(effects);
    writes.push({path: found.path, value});
  }

  // Settings, light colour.
  writes.push({path: resolve(dataRoot, SETTINGS_PATH), value: settingsBlueprint(config)});
  const lightPath = resolve(dataRoot, 'IlluminationColors', `IlluminationColor.${config.upgrade.illumination.id}.blueprint.json`);
  if (await exists(resolve(vanilla, 'IlluminationColors', `IlluminationColor.${config.upgrade.illumination.id}.blueprint.json`))) errors.push('illumination id collides with a vanilla colour');
  writes.push({path: lightPath, value: illuminationBlueprint(config)});

  // The charging bay.
  const s = config.station;
  const station = clone(await readJson(resolve(vanilla, STATION_TEMPLATE)));
  if (!station.AttractionSpec?.Effects?.some((e) => config.upgrade.replacedNeeds.includes(e.NeedId))) errors.push('vanilla ChargingStation no longer serves the replaced need');
  for (const name of STATION_MODEL_ONLY) if (!station[name]) errors.push(`vanilla ChargingStation lost ${name}`);
  if (!(await lategame()).LATEGAME.has(s.id)) errors.push(`${s.id}: its study is not integrated (tools/lategame_batches.json)`);
  if (!await goodPath(s.fuel[0])) errors.push(`station fuel ${s.fuel[0]} is not a good`);
  const slotsPath = resolve(root, 'outputs', 'lategame-integration', `${s.id}-visitor-slots.json`);
  const slots = await exists(slotsPath) ? await readJson(slotsPath) : null;
  if (!slots || slots.keyword !== station.TransformSlotInitializerSpec.Slots[0].SlotKeyword || !(slots.count > 0))
    errors.push(`${s.id}: ${slotsPath} must record the exported '${station.TransformSlotInitializerSpec.Slots[0].SlotKeyword}' slots`);
  const stationPath = resolve(dataRoot, `${s.folder}/${s.id}.IronTeeth.blueprint.json`);

  const collections = {};
  for (const [key, rel, spec, field, values] of [
    ['goods', GOODS, 'GoodCollectionSpec', 'Goods#append', config.parts.map((p) => p.id)],
    ['needs', NEEDS, 'NeedCollectionSpec', 'Needs#append', allNeeds(config).map((n) => n.id)],
    ['templates', TEMPLATES, 'TemplateCollectionSpec', 'Blueprints#append', [`${s.folder}/${s.id}.IronTeeth.blueprint`]],
  ]) {
    const path = resolve(dataRoot, rel);
    if (!await exists(path)) { errors.push(`${rel} is not generated`); continue; }
    const value = await readJson(path);
    const list = value[spec]?.[field];
    if (!Array.isArray(list)) { errors.push(`${rel} has no ${field}`); continue; }
    for (const id of values) if (list.includes(id)) errors.push(`${rel} already lists ${id}`); else list.push(id);
    collections[key] = {path, value};
  }

  const localizationPath = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  if (lines.at(-1) !== '') errors.push('enUS.csv must end with a newline');
  const ids = new Set(lines.map((line) => line.split(',')[0]));
  const rows = localizationRows(config, energy);
  for (const [id] of rows) if (ids.has(id)) errors.push(`localization ${id} already exists`);
  for (const [id] of icons(config)) if (!await exists(resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', `${id}.svg`))) errors.push(`icon src/DeepFrontier/Art/Icons/${id}.svg is missing`);
  return {config, errors, writes, collections, station, stationPath, slots, lines, rows, localizationPath, energy};
}

export async function buildStation(config, station, slots, dataRoot) {
  const s = config.station;
  for (const name of STATION_MODEL_ONLY) delete station[name];
  Object.assign(station, stationComponents(config, slots.count));
  station.TemplateSpec = {...station.TemplateSpec, TemplateName: `${s.id}.IronTeeth`, BackwardCompatibleTemplateNames: []};
  station.BuildingSpec = {...station.BuildingSpec, BuildingCost: (await (await costs()).lategameCost(s.id)).map(([Id, Amount]) => ({Id, Amount})), ScienceCost: s.science};
  Object.assign(station.PlaceableBlockObjectSpec, {ToolGroupId: s.toolGroup, ToolOrder: s.toolOrder});
  Object.assign(station.LabeledEntitySpec, {DisplayNameLocKey: `Building.${s.id}.DisplayName`, DescriptionLocKey: `Building.${s.id}.Description`,
    FlavorDescriptionLocKey: `Building.${s.id}.FlavorDescription`, Icon: `${s.folder}/${s.id}Icon`});
  station.Children = {'#Finished': {TimbermeshSpec: {Model: `${s.folder}/${s.id}.IronTeeth.Model`}}};
  // Flippable, blocks, entrance, shafts, colliders, construction stage,
  // ambient animation and the study meshes (copied into dataRoot).
  await (await lategame()).applyLategame(station, s.id, {dataRoot});
  return station;
}

export async function createSuperBotIcons(config, root, dataRoot) {
  const review = [];
  for (const [id, kind, path] of icons(config)) {
    const svg = await readFile(resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', `${id}.svg`));
    const result = await renderNativeIcon(svg, kind, id);
    const output = resolve(dataRoot, path);
    await mkdir(dirname(output), {recursive: true});
    await writeFile(output, result.png);
    await writeFile(`${output}.meta.json`, JSON.stringify(ICON_KINDS[kind].meta) + '\n');
    review.push({label: `${id} ${result.stroke.toFixed(1)}px`, png: result.png});
  }
  const sheet = resolve(root, 'outputs', 'super-bot-icons', 'super-bot-icons.png');
  await mkdir(dirname(sheet), {recursive: true});
  const vanilla = ['BotChassis', 'BotHead', 'ChargingStation'].map((n) => ({label: n, path: resolve(root, 'outputs', 'vanilla-icons', `${n}Icon.png`)}));
  await writeReviewSheet(review, vanilla, sheet, 4);
  return sheet;
}

export async function applySuperBots({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const plan = await planSuperBots({root, dataRoot});
  if (plan.errors.length) throw new Error(`Reactor bots: generation stopped:\n  ${plan.errors.join('\n  ')}`);
  const station = await buildStation(plan.config, plan.station, plan.slots, dataRoot);
  for (const {path, value} of [...plan.writes, ...Object.values(plan.collections), {path: plan.stationPath, value: station}]) await writeJson(path, value);
  plan.lines.pop();
  for (const [id, text] of plan.rows) plan.lines.push(csvRow(id, text));
  await writeFile(plan.localizationPath, `${plan.lines.join('\n')}\n`, 'utf8');
  const sheet = await createSuperBotIcons(plan.config, root, dataRoot);
  console.log(`Reactor bots: ${plan.config.parts.length} parts, ${allNeeds(plan.config).length} needs, ` +
    `${Object.keys(plan.config.consumption).length} upkeep goods, ${plan.config.station.id} (${plan.slots.count} cradles); icons ${sheet}.`);
  return {parts: plan.config.parts.length};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applySuperBots(dataRoot ? {dataRoot} : {})));
}
