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
// game hour). The core cools exactly as fast as one fault heats it (user
// direction 2026-10-29), and power output is 1 - heat. Timeline:
// - coolant dry, or its radioactive waste or sludge full: +2.5%/h running or
//   stopped, so 0% -> warning 60% in 24 h and meltdown in 40 h unless coolant
//   arrives, the waste is hauled away or the reactor is paused;
// - coolant 45% of the time: +2.5% x 0.55 - 2.5% x 0.45 = +0.25%/h, a
//   meltdown after about 400 h (17 days) of falling output;
// - crew or maintenance fault alone: up to 85% (15% output) in 34 running h;
// - cooling from 85%, with coolant or paused: 34 h to cold, 18 h to restart.
export const REACTOR_TUNING = {
  CoolantGoodId: COOLANT,
  CoolantReserveWarningHours: 12,
  MinOperators: 4,
  MaintenanceIntervalHours: 360,
  MaintenanceWarningHours: 48,
  MaintenanceOutageHours: 24,
  // Repairs at each maintenance stop (user 2026-10-29: building materials need
  // ongoing industrial uses); both are reactor recipe ingredients (the casks).
  MaintenanceGoods: [{Id: 'HighGradeSteel', Amount: 20}, {Id: 'Concrete', Amount: 40}],
  HeatPerFaultPerHour: 0.025,
  CoolingPerHour: 0.025,
  WarningHeat: 0.6,
  FaultHeatLimit: 0.85,
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
  NuclearReactor: 'An 800000 hp reactor that consumes enriched fuel and pipe-fed coolant water. Produces spent-fuel casks and radioactive water that must be shipped off the map.',
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
    NuclearReactor: `${PRODUCER_DESCRIPTIONS.NuclearReactor} Its power output falls as its core heats. Without coolant, or with its radioactive waste or radioactive water storage full, a hot core keeps heating, running or stopped, as fast as it cools otherwise, so a reactor short of coolant or waste hauling more than half the time ends in a meltdown. Each cycle seals its spent fuel in a cask of High-Grade Steel and Concrete. Fewer than ${t.MinOperators} trained operators working or overdue maintenance (a ${t.MaintenanceOutageHours}-hour stop every ${t.MaintenanceIntervalHours} running hours, using ${t.MaintenanceGoods.map((g) => `${g.Amount} ${g.Id === 'HighGradeSteel' ? 'High-Grade Steel' : g.Id}`).join(' and ')}) also heat it while it runs, up to ${pct(t.FaultHeatLimit)}%. At 100% it melts down: the reactor is destroyed, nearby beavers are killed or irradiated and the land and water around it stay radioactive for weeks. Pausing is a safe cold shutdown.`,
    RadioactiveWasteVault: `${PRODUCER_DESCRIPTIONS.RadioactiveWasteVault} Keep it below full: when full, ${v.GoodsPerLeak} casks breach every ${v.LeakIntervalHours} hours, spilling radioactive water and irradiating the soil within ${v.SoilRadius} tiles, which kills crops.`,
    RadioactiveWasteRefinery: `Dissolves spent-fuel casks in water into radioactive water and recovered minerals, and cleans contaminated water. Requires ${refineryPowerHp} hp. Casks can also go straight to a Radioactive Waste Export. Haul its radioactive water to a Radioactive Water Outfall or Radioactive Waste Export: when its tanks are full, ${r.GoodsPerLeak} radioactive water leaks every ${r.LeakIntervalHours} hours and irradiates the soil within ${r.SoilRadius} tiles, killing crops. Pausing it seals the tanks.`,
  };
}

// Runtime rows; placeholders are filled by the C# (MeltdownLoc keys).
export function localizationRows(treatmentDays) {
  const leak = (trigger, rows) => rows.map(([suffix, text]) => [`DeepFrontier.WasteLeak.${trigger}${suffix}`, text]);
  return [
    ['DeepFrontier.Meltdown.Status.Overheating', 'Reactor overheating: its power output falls as the core heats and it melts down at 100%. Open the reactor to see why.'],
    ['DeepFrontier.Meltdown.Status.Overheating.Short', 'Reactor overheating'],
    ['DeepFrontier.Meltdown.Status.Scram', 'Shut down by the operators (SCRAM): no power. Without coolant the core still heats. Restart possible at {0}% core heat or below.'],
    ['DeepFrontier.Meltdown.Status.Scram.Short', 'Reactor shut down (SCRAM)'],
    ['DeepFrontier.Meltdown.Status.CoolantDry', 'Coolant dry: the hot core is heating toward a meltdown, running or stopped. Deliver reactor coolant water, or pause the reactor for a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Status.CoolantDry.Short', 'Reactor coolant dry: meltdown risk'],
    ['DeepFrontier.Meltdown.Status.WasteFull', 'Radioactive waste or radioactive water storage full: the hot core cannot shed its heat and is heating toward a meltdown, running or stopped. Haul the waste away, or pause the reactor for a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Status.WasteFull.Short', 'Reactor waste full: meltdown risk'],
    ['DeepFrontier.Meltdown.Status.CoolantLow', 'Coolant reserve below {0} hours of running.'],
    ['DeepFrontier.Meltdown.Status.Crew', 'Fewer than {0} operators working: the core heats while it runs, costing power.'],
    ['DeepFrontier.Meltdown.Status.MaintenanceDue', 'Maintenance due soon: plan a {0}-hour stop.'],
    ['DeepFrontier.Meltdown.Status.MaintenanceGoods', 'Maintenance stop waiting for repair materials: {0}.'],
    ['DeepFrontier.Meltdown.Status.MaintenanceOverdue', 'Maintenance overdue: the core heats while it runs, costing power. Stop the reactor for {0} hours.'],
    ['DeepFrontier.Meltdown.Notification.Warning', 'Reactor overheating: core heat {0}% ({1}); power output down to {2}%. It melts down at 100%.'],
    ['DeepFrontier.Meltdown.Notification.CoolantDry', 'Reactor coolant dry: core heat {0}% and rising {1}% per hour. A hot core keeps heating without coolant, running or stopped, and melts down in about {2} hours. Deliver reactor coolant water, or pause the reactor for a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Notification.WasteFull', 'Reactor waste storage full: core heat {0}% and rising {1}% per hour. A hot core keeps heating while its radioactive waste or radioactive water is full, running or stopped, and melts down in about {2} hours. Haul the waste away, or pause the reactor for a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Notification.Imminent', 'MELTDOWN IMMINENT: core heat {0}%, meltdown in about {1} hours. Deliver reactor coolant water, haul away its waste or pause the reactor now.'],
    ['DeepFrontier.Meltdown.Notification.MaintenanceOverdue', 'Reactor maintenance overdue: stop it for {0} hours, or its core heats while it runs.'],
    ['DeepFrontier.Meltdown.Notification.MaintenanceDone', 'Reactor maintenance completed during the stop.'],
    ['DeepFrontier.Meltdown.Notification.Meltdown', 'REACTOR MELTDOWN: the Nuclear Reactor was destroyed. {0} killed, {1} irradiated.'],
    ['DeepFrontier.Meltdown.Dialog.Title', 'Reactor meltdown'],
    ['DeepFrontier.Meltdown.Dialog.Casualties', `The core melted down and destroyed the Nuclear Reactor. {0} were killed and {1} beavers were irradiated; irradiated beavers need ${treatmentDays} days of hospital care, and untreated radiation sickness is fatal.`],
    ['DeepFrontier.Meltdown.Dialog.Contamination', 'Radioactive water is pouring from the ruin and will keep flowing for {0} days. Soil and water within {1} tiles are contaminated: crops there die, pumps refuse contaminated water and beavers who walk in are irradiated. Clean up with Radioactive Water Recovery Pumps and ship it off the map.'],
    ['DeepFrontier.Meltdown.Dialog.ShowSite', 'Show the site'],
    ['DeepFrontier.Meltdown.DeathMessage', '{0} was killed in the reactor meltdown.'],
    ['DeepFrontier.Meltdown.Cause.Coolant', 'coolant dry'],
    ['DeepFrontier.Meltdown.Cause.Crew', 'fewer than {0} operators working'],
    ['DeepFrontier.Meltdown.Cause.Waste', 'radioactive waste or radioactive water full'],
    ['DeepFrontier.Meltdown.Cause.Maintenance', 'maintenance overdue'],
    ['DeepFrontier.Meltdown.Panel.Title', 'Reactor core'],
    ['DeepFrontier.Meltdown.Panel.Heat', 'Core heat: {0}% {1}'],
    ['DeepFrontier.Meltdown.Panel.Thresholds', 'Warning {0}%, meltdown 100%. Crew and maintenance faults alone heat it to at most {1}%.'],
    ['DeepFrontier.Meltdown.Panel.Output', 'Power output: {0}% of full ({1} hp). Output falls as the core heats: half power at 50%.'],
    ['DeepFrontier.Meltdown.Panel.Rising', '(rising {0}% per hour)'],
    ['DeepFrontier.Meltdown.Panel.Falling', '(falling {0}% per hour)'],
    ['DeepFrontier.Meltdown.Panel.EtaMeltdown', 'Meltdown in about {0} hours.'],
    ['DeepFrontier.Meltdown.Panel.EtaLimit', 'Heats to {0}% in about {1} running hours; crew and maintenance faults alone never melt the core.'],
    ['DeepFrontier.Meltdown.Panel.EtaCool', 'Cold in about {0} hours.'],
    ['DeepFrontier.Meltdown.Panel.EtaRestart', 'Cool enough to restart in about {0} hours.'],
    ['DeepFrontier.Meltdown.Panel.State.UnderConstruction', 'Under construction.'],
    ['DeepFrontier.Meltdown.Panel.State.ColdShutdown', 'Cold shutdown (paused or switched off by automation): cooling safely without coolant. Haulers empty a paused reactor.'],
    ['DeepFrontier.Meltdown.Panel.State.Running', 'Running.'],
    ['DeepFrontier.Meltdown.Panel.State.Scram', 'Shut down by the operators (SCRAM).'],
    ['DeepFrontier.Meltdown.Panel.State.Idle', 'Idle: not producing.'],
    ['DeepFrontier.Meltdown.Panel.State.MeltingDown', 'Melting down.'],
    ['DeepFrontier.Meltdown.Panel.DryCore', 'Not cooling ({0}): the hot core heats {1}% per hour, running or stopped, until that is fixed. Pausing is a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Panel.Coolant', '{0}: {1} in stock, {2} per cycle (about {3} hours of running).'],
    ['DeepFrontier.Meltdown.Panel.Waste', '{0}: {1} of {2} stored (full storage heats the core).'],
    ['DeepFrontier.Meltdown.Panel.Crew', 'Operators working: {0} (needs {1} while running).'],
    ['DeepFrontier.Meltdown.Panel.MaintenanceDue', 'Maintenance due in {0} running hours; it needs a {1}-hour stop.'],
    ['DeepFrontier.Meltdown.Panel.MaintenanceGoods', 'Each maintenance stop uses {0} from the reactor stock.'],
    ['DeepFrontier.Meltdown.Panel.MaintenanceOverdue', 'Maintenance overdue: stop the reactor for {0} hours ({1} so far).'],
    ['DeepFrontier.Meltdown.Panel.Rules', 'Without coolant, or with its radioactive waste or radioactive water full, a hot core heats {0}% per hour, running or stopped; otherwise it cools {1}% per hour, so a reactor short of coolant or waste hauling more than half the time ends in a meltdown. While running, fewer than {2} operators working or overdue maintenance (a {3}-hour stop every {4} running hours) also heat it, up to {5}%.'],
    ['DeepFrontier.Meltdown.Panel.Consequences', 'A meltdown destroys the reactor: beavers within {0} tiles die, beavers within {1} tiles are irradiated, radioactive water pours out for {2} days and soil and water within {3} tiles stay radioactive for weeks. Pausing the reactor is a safe cold shutdown.'],
    ['DeepFrontier.Meltdown.Panel.ScramButton', 'Emergency shutdown (SCRAM)'],
    ['DeepFrontier.Meltdown.Panel.RestartButton', 'Restart reactor'],
    ['DeepFrontier.Meltdown.Panel.RestartBlocked', 'Restart possible once core heat is at or below {0}%.'],
    ...leak('StorageFull', [
      ['.Status.Warning', 'Nearly full of radioactive waste: once full, casks breach every {0} hours.'],
      ['.Status.Leaking', 'Full: radioactive waste casks are breaching and leaking radioactive water. Export, refine or move the waste.'],
      ['.Status.Leaking.Short', 'Waste vault leaking'],
      ['.Notification.Warning', 'Radioactive Waste Vault {0}% full: once full, its casks breach and leak.'],
      ['.Notification.Full', 'Radioactive Waste Vault full: {0} casks will breach in {1} hours unless waste is refined or moved.'],
      ['.Notification.Leak', 'Radioactive Waste Vault leak: {0} casks breached, spilling radioactive water and irradiating the soil around the vault.'],
      ['.Panel.Rules', 'When full, {0} casks breach every {1} hours: their waste spills out as radioactive water and irradiates the soil within {2} tiles, killing crops there.'],
    ]),
    ...leak('OutputBlocked', [
      ['.Status.Warning', 'Radioactive water tanks nearly full: once full, radioactive water leaks every {0} hours.'],
      ['.Status.Leaking', 'Radioactive water tanks full: radioactive water is leaking. Haul it to a Radioactive Water Outfall or Radioactive Waste Export.'],
      ['.Status.Leaking.Short', 'Waste refinery leaking'],
      ['.Notification.Warning', 'Waste refinery radioactive water tanks {0}% full: haul it away before they leak.'],
      ['.Notification.Full', 'Waste refinery radioactive water tanks full: {0} radioactive water will leak in {1} hours.'],
      ['.Notification.Leak', 'Waste refinery leak: {0} radioactive water spilled around the refinery.'],
      ['.Panel.Rules', 'When its radioactive water tanks are full, {0} radioactive water leaks every {1} hours and irradiates the soil within {2} tiles, killing crops there. Pausing it seals the tanks.'],
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
