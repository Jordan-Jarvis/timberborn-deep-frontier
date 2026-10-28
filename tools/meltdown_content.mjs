// Reactor meltdown and radioactive waste leaks (docs/meltdown.md; runtime in
// src/DeepFrontier/Scripts/Meltdown).
//
// Called once, last, from tools/create_frontier_expansion_content.mjs after
// the reactor, vault and refinery blueprints, their recipes and the expansion
// localization rows exist:
//   await (await import('./meltdown_content.mjs')).applyMeltdownContent();
// or standalone on a scratch copy: node tools/meltdown_content.mjs <dataRoot>
//
// What it writes:
// - ReactorMeltdownSpec on the Nuclear Reactor (core heat, SCRAM, meltdown).
// - WasteLeakSpec on the Radioactive Waste Vault (StorageFull) and the
//   Radioactive Waste Refinery (OutputBlocked).
// - Building descriptions that state each risk before it is built, replacing
//   the producer's exact current text, and every runtime localization row.
// Everything fails explicitly: a missing blueprint, recipe or component, a
// producer text that changed, a spec or row that already exists.
import {readFile, writeFile, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));

export const REACTOR = 'Buildings/Power/NuclearReactor/NuclearReactor.IronTeeth.blueprint';
export const VAULT = 'Buildings/Storage/RadioactiveWasteVault/RadioactiveWasteVault.IronTeeth.blueprint';
export const REFINERY = 'Buildings/Metal/RadioactiveWasteRefinery/RadioactiveWasteRefinery.IronTeeth.blueprint';
export const REACTOR_RECIPE = 'NuclearWaste';
export const REFINING_RECIPE = 'WasteRefining';
export const WASTE = 'RadioactiveWaste';
export const SLUDGE = 'RadioactiveSludge';
export const COOLANT = 'ReactorCoolantWater';
export const TRIGGERS = ['StorageFull', 'OutputBlocked'];

// Authored reactor tuning (heat is a 0..1 fraction of meltdown; rates per
// game hour). Timeline at these values:
// - one running fault: 60% warning after 24 running hours, SCRAM at 34;
// - SCRAM 85% -> restart 40% in 5.6 hours of cooling;
// - coolant dry after it stops: +1.5%/h for 72 h, so 0% -> meltdown in 67 h
//   and SCRAM -> meltdown in 10 h unless coolant arrives or it is paused.
export const REACTOR_TUNING = {
  CoolantGoodId: COOLANT,
  CoolantReserveWarningHours: 12,
  MinOperators: 4,
  MaintenanceIntervalHours: 360,
  MaintenanceWarningHours: 48,
  MaintenanceOutageHours: 24,
  HeatPerFaultPerHour: 0.025,
  RunningCoolingPerHour: 0.04,
  ShutdownCoolingPerHour: 0.08,
  DecayHeatHours: 72,
  DecayHeatPerHour: 0.015,
  WarningHeat: 0.6,
  ScramHeat: 0.85,
  RestartHeat: 0.4,
  MeltdownInstantSludge: 60,
  MeltdownSourceSludgePerHour: 0.5,
  MeltdownSourceHours: 240,
  MeltdownRadius: 12,
  MeltdownFootprintSoilRadiation: 0.5,
  MeltdownEdgeSoilRadiation: 0.16,
  MeltdownFootprintWaterRadiation: 2,
  MeltdownEdgeWaterRadiation: 0.2,
  MeltdownKillRadius: 2,
  MeltdownIrradiationRadius: 16,
  MeltdownIrradiationDose: 1.5,
};

// Authored leak tuning. GoodsPerLeak and SludgeVolumePerGood are derived from
// the WasteRefining recipe and RadiationTuning.VolumePerGood (wasteLeakSpecs):
// each leak is one refinery batch of material.
export const LEAK_TUNING = {
  vault: {GoodId: WASTE, Trigger: 'StorageFull', WarningFillFraction: 0.9, LeakIntervalHours: 24, SoilRadiationPerLeak: 0.16, SoilRadius: 3},
  refinery: {GoodId: SLUDGE, Trigger: 'OutputBlocked', WarningFillFraction: 0.75, LeakIntervalHours: 24, SoilRadiationPerLeak: 0.16, SoilRadius: 3},
};

// Exact texts written by tools/create_frontier_expansion_content.mjs; the
// descriptions below replace them.
export const PRODUCER_DESCRIPTIONS = {
  NuclearReactor: 'A 750000 hp reactor that consumes enriched fuel and pipe-fed coolant water. Produces spent-fuel casks and radioactive sludge that must be shipped off the map.',
  RadioactiveWasteVault: 'Locked storage for radioactive waste; the contents must be processed or moved before demolition.',
  RadioactiveWasteRefinery: 'Deep Frontier radioactive waste refinery production building',
};

export const SPEC_KEYS = {
  ReactorMeltdownSpec: Object.keys(REACTOR_TUNING),
  WasteLeakSpec: ['GoodId', 'Trigger', 'WarningFillFraction', 'LeakIntervalHours', 'GoodsPerLeak', 'SludgeVolumePerGood', 'SoilRadiationPerLeak', 'SoilRadius'],
};

const pct = (fraction) => Math.round(fraction * 100);

// Reads RadiationTuning constants from the C# source the runtime uses.
export async function radiationTuning(root = defaultRoot) {
  const source = await readFile(resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Radiation', 'IRadiationService.cs'), 'utf8');
  const number = (name) => {
    const match = source.match(new RegExp(`const float ${name} = ([0-9.]+)f;`));
    if (!match) throw new Error(`meltdown: RadiationTuning.${name} not found in IRadiationService.cs`);
    return Number(match[1]);
  };
  return {volumePerGood: number('VolumePerGood'), floraThreshold: number('IrradiatedGroundThreshold'), treatmentDays: number('TreatmentDays')};
}

// Refinery batch: waste in, sludge out per WasteRefining cycle.
export function refiningBatch(recipe) {
  const amount = (list, id) => list.find((good) => good.Id === id)?.Amount;
  const waste = amount(recipe.Ingredients, WASTE), sludge = amount(recipe.Products, SLUDGE);
  if (!(Number.isInteger(waste) && waste > 0 && Number.isInteger(sludge) && sludge > 0))
    throw new Error(`meltdown: ${REFINING_RECIPE} must consume ${WASTE} and produce ${SLUDGE}`);
  return {waste, sludge};
}

export function wasteLeakSpecs(batch, volumePerGood) {
  const round = (value) => Math.round(value * 1e6) / 1e6;
  const spec = (tuning, goodsPerLeak, sludgeVolumePerGood) => Object.fromEntries(SPEC_KEYS.WasteLeakSpec.map((key) => [key,
    key === 'GoodsPerLeak' ? goodsPerLeak : key === 'SludgeVolumePerGood' ? round(sludgeVolumePerGood) : tuning[key]]));
  return {
    vault: spec(LEAK_TUNING.vault, batch.waste, batch.sludge / batch.waste * volumePerGood),
    refinery: spec(LEAK_TUNING.refinery, batch.sludge, volumePerGood),
  };
}

export function descriptions(reactor, leaks, refineryPowerHp) {
  const t = reactor, v = leaks.vault, r = leaks.refinery;
  return {
    NuclearReactor: `${PRODUCER_DESCRIPTIONS.NuclearReactor} Its core overheats when coolant runs dry, fewer than ${t.MinOperators} trained operators are working or maintenance is overdue (a ${t.MaintenanceOutageHours}-hour stop every ${t.MaintenanceIntervalHours} running hours). At ${pct(t.ScramHeat)}% heat it trips an emergency shutdown; without coolant the core keeps heating for ${t.DecayHeatHours} hours after it stops, and at 100% it melts down: the reactor is destroyed, nearby beavers are killed or irradiated and the land and water around it stay radioactive for weeks. Pausing is a safe cold shutdown.`,
    RadioactiveWasteVault: `${PRODUCER_DESCRIPTIONS.RadioactiveWasteVault} Keep it below full: when full, ${v.GoodsPerLeak} casks breach every ${v.LeakIntervalHours} hours, spilling radioactive sludge and irradiating the soil within ${v.SoilRadius} tiles, which kills crops.`,
    RadioactiveWasteRefinery: `Refines spent-fuel casks into radioactive sludge and recovered minerals, and cleans contaminated water. Requires ${refineryPowerHp} hp. Haul its sludge to a Sludge Outfall or Radioactive Waste Export: when its sludge tanks are full, ${r.GoodsPerLeak} sludge leaks every ${r.LeakIntervalHours} hours and irradiates the soil within ${r.SoilRadius} tiles, killing crops. Pausing it seals the tanks.`,
  };
}

// Runtime rows; placeholders are filled by the C# (MeltdownLoc keys).
export function localizationRows(treatmentDays) {
  const leak = (trigger, rows) => rows.map(([suffix, text]) => [`DeepFrontier.WasteLeak.${trigger}${suffix}`, text]);
  return [
    ['DeepFrontier.Meltdown.Status.Overheating', 'Reactor overheating. It trips an emergency shutdown at {0}% core heat and melts down at 100%; open the reactor to see why.'],
    ['DeepFrontier.Meltdown.Status.Overheating.Short', 'Reactor overheating'],
    ['DeepFrontier.Meltdown.Status.Scram', 'Emergency shutdown (SCRAM): no power until the core cools to {0}%.'],
    ['DeepFrontier.Meltdown.Status.Scram.Short', 'Reactor emergency shutdown'],
    ['DeepFrontier.Meltdown.Status.CoolantDry', 'Coolant dry while the core still holds decay heat: it is heating toward a meltdown. Deliver reactor coolant water, or pause the reactor for a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Status.CoolantDry.Short', 'Reactor coolant dry: meltdown risk'],
    ['DeepFrontier.Meltdown.Status.CoolantLow', 'Coolant reserve below {0} hours of running.'],
    ['DeepFrontier.Meltdown.Status.Crew', 'Fewer than {0} operators working: the core heats while it runs.'],
    ['DeepFrontier.Meltdown.Status.MaintenanceDue', 'Maintenance due soon: plan a {0}-hour stop.'],
    ['DeepFrontier.Meltdown.Status.MaintenanceOverdue', 'Maintenance overdue: the core heats while it runs. Stop the reactor for {0} hours.'],
    ['DeepFrontier.Meltdown.Notification.Warning', 'Reactor overheating: core heat {0}% ({1}). Emergency shutdown at {2}%.'],
    ['DeepFrontier.Meltdown.Notification.Scram', 'Reactor emergency shutdown (SCRAM) at {0}% core heat: no power until it cools to {1}%.'],
    ['DeepFrontier.Meltdown.Notification.Restarted', 'Reactor restarted automatically at {0}% core heat.'],
    ['DeepFrontier.Meltdown.Notification.CoolantDry', 'Reactor coolant dry: core heat {0}% and rising from decay heat for up to {1} more hours. Deliver reactor coolant water or pause the reactor.'],
    ['DeepFrontier.Meltdown.Notification.Imminent', 'MELTDOWN IMMINENT: core heat {0}%, meltdown in about {1} hours. Deliver reactor coolant water or pause the reactor now.'],
    ['DeepFrontier.Meltdown.Notification.MaintenanceOverdue', 'Reactor maintenance overdue: stop it for {0} hours, or its core heats while it runs.'],
    ['DeepFrontier.Meltdown.Notification.MaintenanceDone', 'Reactor maintenance completed during the stop.'],
    ['DeepFrontier.Meltdown.Notification.Meltdown', 'REACTOR MELTDOWN: the Nuclear Reactor was destroyed. {0} killed, {1} irradiated.'],
    ['DeepFrontier.Meltdown.Dialog.Title', 'Reactor meltdown'],
    ['DeepFrontier.Meltdown.Dialog.Casualties', `The core melted down and destroyed the Nuclear Reactor. {0} were killed and {1} beavers were irradiated; irradiated beavers need ${treatmentDays} days of hospital care, and untreated radiation sickness is fatal.`],
    ['DeepFrontier.Meltdown.Dialog.Contamination', 'Radioactive sludge is pouring from the ruin and will keep flowing for {0} days. Soil and water within {1} tiles are contaminated: crops there die, pumps refuse contaminated water and beavers who walk in are irradiated. Clean up with Sludge Recovery Pumps and ship the sludge off the map.'],
    ['DeepFrontier.Meltdown.Dialog.ShowSite', 'Show the site'],
    ['DeepFrontier.Meltdown.DeathMessage', '{0} was killed in the reactor meltdown.'],
    ['DeepFrontier.Meltdown.Cause.Coolant', 'coolant dry'],
    ['DeepFrontier.Meltdown.Cause.Crew', 'fewer than {0} operators working'],
    ['DeepFrontier.Meltdown.Cause.Maintenance', 'maintenance overdue'],
    ['DeepFrontier.Meltdown.Cause.DecayHeat', 'decay heat without coolant'],
    ['DeepFrontier.Meltdown.Panel.Title', 'Reactor core'],
    ['DeepFrontier.Meltdown.Panel.Heat', 'Core heat: {0}% {1}'],
    ['DeepFrontier.Meltdown.Panel.Thresholds', 'Warning {0}%, emergency shutdown {1}%, meltdown 100%'],
    ['DeepFrontier.Meltdown.Panel.Rising', '(rising {0}% per hour)'],
    ['DeepFrontier.Meltdown.Panel.Falling', '(falling {0}% per hour)'],
    ['DeepFrontier.Meltdown.Panel.EtaScram', 'Emergency shutdown after about {0} more hours of running.'],
    ['DeepFrontier.Meltdown.Panel.EtaMeltdown', 'Meltdown in about {0} hours.'],
    ['DeepFrontier.Meltdown.Panel.EtaPeak', 'Decay heat fades before a meltdown: peak about {0}% in {1} hours.'],
    ['DeepFrontier.Meltdown.Panel.EtaRestart', 'Cool enough to restart in about {0} hours.'],
    ['DeepFrontier.Meltdown.Panel.State.UnderConstruction', 'Under construction.'],
    ['DeepFrontier.Meltdown.Panel.State.ColdShutdown', 'Cold shutdown (paused or switched off by automation): cooling safely without coolant. Haulers empty a paused reactor.'],
    ['DeepFrontier.Meltdown.Panel.State.Running', 'Running.'],
    ['DeepFrontier.Meltdown.Panel.State.Scram', 'Emergency shutdown (SCRAM).'],
    ['DeepFrontier.Meltdown.Panel.State.ScramManual', 'Shut down by the operators (SCRAM).'],
    ['DeepFrontier.Meltdown.Panel.State.Idle', 'Idle: not producing.'],
    ['DeepFrontier.Meltdown.Panel.State.MeltingDown', 'Melting down.'],
    ['DeepFrontier.Meltdown.Panel.DecayHeat', 'Decay heat for {0} more hours: until then the core needs coolant even when stopped.'],
    ['DeepFrontier.Meltdown.Panel.NoDecayHeat', 'No decay heat: safe without coolant while stopped.'],
    ['DeepFrontier.Meltdown.Panel.Coolant', '{0}: {1} in stock, {2} per cycle (about {3} hours of running).'],
    ['DeepFrontier.Meltdown.Panel.Crew', 'Operators working: {0} (needs {1} while running).'],
    ['DeepFrontier.Meltdown.Panel.MaintenanceDue', 'Maintenance due in {0} running hours; it needs a {1}-hour stop.'],
    ['DeepFrontier.Meltdown.Panel.MaintenanceOverdue', 'Maintenance overdue: stop the reactor for {0} hours ({1} so far).'],
    ['DeepFrontier.Meltdown.Panel.Rules', 'While running, the core heats {0}% per hour for each fault: coolant dry, fewer than {1} operators working, or maintenance overdue (a {2}-hour stop every {3} running hours). At {4}% it trips an emergency shutdown. Without coolant, decay heat keeps heating it for {5} hours after it stops.'],
    ['DeepFrontier.Meltdown.Panel.Consequences', 'A meltdown destroys the reactor: beavers within {0} tiles die, beavers within {1} tiles are irradiated, sludge pours out for {2} days and soil and water within {3} tiles stay radioactive for weeks. Pausing the reactor is a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Panel.ScramButton', 'Emergency shutdown (SCRAM)'],
    ['DeepFrontier.Meltdown.Panel.RestartButton', 'Restart reactor'],
    ['DeepFrontier.Meltdown.Panel.RestartBlocked', 'Restart possible once core heat is at or below {0}%.'],
    ['DeepFrontier.Meltdown.Panel.AutoRestart', 'Restart automatically after an emergency shutdown (once cool, maintained and with coolant)'],
    ...leak('StorageFull', [
      ['.Status.Warning', 'Nearly full of radioactive waste: once full, casks breach every {0} hours.'],
      ['.Status.Leaking', 'Full: radioactive waste casks are breaching and leaking sludge. Refine or move the waste.'],
      ['.Status.Leaking.Short', 'Waste vault leaking'],
      ['.Notification.Warning', 'Radioactive Waste Vault {0}% full: once full, its casks breach and leak.'],
      ['.Notification.Full', 'Radioactive Waste Vault full: {0} casks will breach in {1} hours unless waste is refined or moved.'],
      ['.Notification.Leak', 'Radioactive Waste Vault leak: {0} casks breached, spilling radioactive sludge and irradiating the soil around the vault.'],
      ['.Panel.Rules', 'When full, {0} casks breach every {1} hours: their waste spills out as radioactive sludge and irradiates the soil within {2} tiles, killing crops there.'],
    ]),
    ...leak('OutputBlocked', [
      ['.Status.Warning', 'Sludge tanks nearly full: once full, sludge leaks every {0} hours.'],
      ['.Status.Leaking', 'Sludge tanks full: radioactive sludge is leaking. Haul it to a Sludge Outfall or Radioactive Waste Export.'],
      ['.Status.Leaking.Short', 'Waste refinery leaking'],
      ['.Notification.Warning', 'Waste refinery sludge tanks {0}% full: haul the sludge away before they leak.'],
      ['.Notification.Full', 'Waste refinery sludge tanks full: {0} sludge will leak in {1} hours.'],
      ['.Notification.Leak', 'Waste refinery leak: {0} radioactive sludge spilled around the refinery.'],
      ['.Panel.Rules', 'When its sludge tanks are full, {0} sludge leaks every {1} hours and irradiates the soil within {2} tiles, killing crops there. Pausing it seals the tanks.'],
    ]),
    ['DeepFrontier.WasteLeak.Panel.Title', 'Radioactive containment'],
    ['DeepFrontier.WasteLeak.Panel.Fill', '{0}: {1} / {2} ({3}%)'],
    ['DeepFrontier.WasteLeak.Panel.Contained', 'Contained. Warnings start at {0}% full; leaks only when full.'],
    ['DeepFrontier.WasteLeak.Panel.Warning', 'Nearly full: it leaks once full.'],
    ['DeepFrontier.WasteLeak.Panel.Full', 'Full: next leak in about {0} hours.'],
    ['DeepFrontier.WasteLeak.Panel.Sealed', 'Paused: tanks sealed, no leaks.'],
    ['DeepFrontier.WasteLeak.Panel.History', 'Leaks so far: {0} ({1} {2}).'],
  ];
}

const csvCell = (text) => {
  if (typeof text !== 'string') throw new TypeError('meltdown: localization cells must be authored strings');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csvRow = (id, text, comment) => [id, text, comment].map(csvCell).join(',');
const COMMENT = 'Deep Frontier meltdown';

export async function applyMeltdownContent({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
  const writeJson = (path, value) => writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  const exists = (path) => access(path).then(() => true, () => false);
  const fail = (message) => { throw new Error(`meltdown: ${message}`); };
  const load = async (relative, what) => {
    const path = resolve(dataRoot, `${relative}.json`);
    if (!await exists(path)) fail(`${what} is missing (${path}); generate it first`);
    return {path, value: await readJson(path)};
  };
  const recipe = async (id) => (await load(`Recipes/Recipe.${id}.blueprint`, `recipe ${id}`)).value.RecipeSpec;

  const reactor = await load(REACTOR, 'the Nuclear Reactor blueprint');
  const vault = await load(VAULT, 'the Radioactive Waste Vault blueprint');
  const refinery = await load(REFINERY, 'the Radioactive Waste Refinery blueprint');
  for (const [{value}, name] of [[reactor, 'reactor'], [vault, 'vault'], [refinery, 'refinery']])
    for (const spec of Object.keys(SPEC_KEYS)) if (value[spec]) fail(`the ${name} already has ${spec}; regenerate it from its producer`);

  // Reactor: a native powered-generator workshop whose every recipe burns coolant.
  const r = reactor.value;
  for (const key of ['ManufactorySpec', 'WorkshopSpec', 'WorkplaceSpec', 'WorkshopPoweredGeneratorSpec', 'MechanicalNodeSpec'])
    if (!r[key]) fail(`the reactor lacks ${key}`);
  if (!(r.MechanicalNodeSpec.PowerOutput > 0)) fail('the reactor must be a power generator');
  if (!r.ManufactorySpec.ProductionRecipeIds.includes(REACTOR_RECIPE)) fail(`the reactor no longer runs ${REACTOR_RECIPE}`);
  const coolant = [];
  for (const id of r.ManufactorySpec.ProductionRecipeIds) {
    const spec = await recipe(id);
    const amount = spec.Ingredients.find((good) => good.Id === COOLANT)?.Amount;
    if (!(amount > 0)) fail(`reactor recipe ${id} does not consume ${COOLANT}`);
    coolant.push(`${amount}/${spec.CycleDurationInHours}`);
  }
  if (new Set(coolant).size !== 1) fail('reactor recipes disagree on coolant per cycle or cycle length');
  if (r.WorkplaceSpec.MaxWorkers < REACTOR_TUNING.MinOperators) fail(`the reactor holds ${r.WorkplaceSpec.MaxWorkers} workers, fewer than MinOperators ${REACTOR_TUNING.MinOperators}`);

  // Vault: a native stockpile that stores the waste casks.
  const v = vault.value;
  if (!(v.StockpileSpec?.MaxCapacity > 0)) fail('the vault lacks a StockpileSpec capacity');
  const wasteGood = await load(`Goods/Good.${WASTE}.blueprint`, `good ${WASTE}`);
  if (wasteGood.value.GoodSpec.GoodType !== v.StockpileSpec.WhitelistedGoodType)
    fail(`${WASTE} (${wasteGood.value.GoodSpec.GoodType}) cannot be stored in the vault (${v.StockpileSpec.WhitelistedGoodType})`);

  // Refinery: a native powered workshop running WasteRefining.
  const f = refinery.value;
  for (const key of ['ManufactorySpec', 'WorkshopSpec', 'MechanicalNodeSpec']) if (!f[key]) fail(`the refinery lacks ${key}`);
  if (!f.ManufactorySpec.ProductionRecipeIds.includes(REFINING_RECIPE)) fail(`the refinery no longer runs ${REFINING_RECIPE}`);
  if (!(f.MechanicalNodeSpec.PowerInput > 0)) fail('the refinery must demand power');
  const batch = refiningBatch(await recipe(REFINING_RECIPE));

  const tuning = await radiationTuning(root);
  const leaks = wasteLeakSpecs(batch, tuning.volumePerGood);
  r.ReactorMeltdownSpec = {...REACTOR_TUNING};
  v.WasteLeakSpec = leaks.vault;
  f.WasteLeakSpec = leaks.refinery;

  // Localization: replace the producer's descriptions, append runtime rows.
  const localizationPath = resolve(dataRoot, 'Localizations', 'enUS.csv');
  if (!await exists(localizationPath)) fail(`enUS.csv is missing (${localizationPath})`);
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  if (lines.at(-1) !== '') fail('enUS.csv must end with a newline');
  lines.pop();
  const index = new Map(lines.map((line, i) => [line.split(',')[0], i]));
  for (const [id, text] of Object.entries(descriptions(REACTOR_TUNING, leaks, f.MechanicalNodeSpec.PowerInput))) {
    const key = `Building.${id}.Description`;
    const expected = csvRow(key, PRODUCER_DESCRIPTIONS[id], 'Deep Frontier');
    if (!index.has(key) || lines[index.get(key)] !== expected)
      fail(`${key} is not the producer text this module replaces; update PRODUCER_DESCRIPTIONS and the risk text together`);
    lines[index.get(key)] = csvRow(key, text, 'Deep Frontier');
  }
  for (const [id, text] of localizationRows(tuning.treatmentDays)) {
    if (index.has(id)) fail(`localization ${id} already exists`);
    lines.push(csvRow(id, text, COMMENT));
  }

  await writeJson(reactor.path, r);
  await writeJson(vault.path, v);
  await writeJson(refinery.path, f);
  await writeFile(localizationPath, `${lines.join('\n')}\n`, 'utf8');
  return {reactor: REACTOR_TUNING, leaks};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  const {leaks} = await applyMeltdownContent(dataRoot ? {dataRoot} : {});
  console.log(`Meltdown content applied: reactor core, vault leak ${leaks.vault.GoodsPerLeak} casks/${leaks.vault.LeakIntervalHours} h, refinery leak ${leaks.refinery.GoodsPerLeak} sludge/${leaks.refinery.LeakIntervalHours} h.`);
}
