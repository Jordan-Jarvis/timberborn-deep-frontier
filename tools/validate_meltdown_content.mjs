// Static checks for reactor meltdown and waste leaks (tools/meltdown_content.mjs
// and src/DeepFrontier/Scripts/Meltdown). Usage:
//   node tools/validate_meltdown_content.mjs [dataRoot]
// Run after canonical generation (or on a scratch copy's Data). Static
// evidence only: heat, SCRAM, meltdown, leaks and reload are verified in game.
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {PIPE_PHRASES, parseCsvRow} from './connection_content.mjs';
import {REACTOR, VAULT, REFINERY, REACTOR_RECIPE, REFINING_RECIPE, WASTE, SLUDGE, COOLANT, TRIGGERS, REACTOR_TUNING,
  SPEC_KEYS, PRODUCER_DESCRIPTIONS, radiationTuning, refiningBatch, wasteLeakSpecs, descriptions, localizationRows} from './meltdown_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Meltdown');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const data = (...parts) => resolve(dataRoot, ...parts);
const exists = (path) => access(path).then(() => true, () => false);
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const source = async (name) => readFile(resolve(scripts, name), 'utf8');

// ---- blueprints carry exactly the module's specs ----
const reactor = await readJson(data(`${REACTOR}.json`));
const vault = await readJson(data(`${VAULT}.json`));
const refinery = await readJson(data(`${REFINERY}.json`));
const recipes = new Map();
for (const file of await readdir(data('Recipes'))) if (file.endsWith('.blueprint.json')) {
  const r = (await readJson(data('Recipes', file))).RecipeSpec; recipes.set(r.Id, r);
}
const tuning = await radiationTuning(root);
const batch = refiningBatch(recipes.get(REFINING_RECIPE));
const leaks = wasteLeakSpecs(batch, tuning.volumePerGood);
assert(same(reactor.ReactorMeltdownSpec, REACTOR_TUNING), 'NuclearReactor ReactorMeltdownSpec differs from tools/meltdown_content.mjs');
assert(same(vault.WasteLeakSpec, leaks.vault), 'RadioactiveWasteVault WasteLeakSpec differs from the module');
assert(same(refinery.WasteLeakSpec, leaks.refinery), 'RadioactiveWasteRefinery WasteLeakSpec differs from the module');
assert(!reactor.WasteLeakSpec && !vault.ReactorMeltdownSpec && !refinery.ReactorMeltdownSpec, 'specs appear on the wrong building');

// ---- the native contracts the runtime relies on ----
for (const key of ['ManufactorySpec', 'WorkshopSpec', 'WorkplaceSpec', 'WorkshopPoweredGeneratorSpec', 'BuildingSpec'])
  assert(reactor[key], `reactor lacks ${key}`);
assert(!reactor.GoodConsumingBuildingSpec, 'reactor must keep a single IGoodProcessor (Manufactory)');
assert(reactor.WorkplaceSpec?.MaxWorkers >= REACTOR_TUNING.MinOperators, 'MinOperators exceeds the reactor crew');
for (const id of reactor.ManufactorySpec?.ProductionRecipeIds ?? [])
  assert(recipes.get(id)?.Ingredients.some((g) => g.Id === COOLANT && g.Amount > 0), `reactor recipe ${id} must consume ${COOLANT}`);
assert(reactor.ManufactorySpec?.ProductionRecipeIds.includes(REACTOR_RECIPE), `reactor runs ${REACTOR_RECIPE}`);
assert(vault.StockpileSpec?.MaxCapacity > 0, 'vault is a native Stockpile');
assert(refinery.ManufactorySpec?.ProductionRecipeIds.includes(REFINING_RECIPE), `refinery runs ${REFINING_RECIPE}`);
const good = async (id) => (await exists(data('Goods', `Good.${id}.blueprint.json`))) ? (await readJson(data('Goods', `Good.${id}.blueprint.json`))).GoodSpec : null;
assert((await good(WASTE))?.GoodType === vault.StockpileSpec?.WhitelistedGoodType, `${WASTE} must be storable in the vault`);
assert((await good(SLUDGE))?.GoodType === 'Liquid', `${SLUDGE} must be an authored Liquid good`);
assert((await good(COOLANT))?.GoodType === 'Liquid', `${COOLANT} must be an authored Liquid good`);

// ---- tuning: visible before it bites, real when ignored ----
const t = REACTOR_TUNING;
assert(0 < t.RestartHeat && t.RestartHeat < t.WarningHeat && t.WarningHeat < t.FaultHeatLimit && t.FaultHeatLimit < 1, 'thresholds: 0 < restart < warning < fault limit < 1');
assert(t.CoolingPerHour === t.HeatPerFaultPerHour, 'the core cools as slowly as a dry core heats (coolant less than half the time ends in a meltdown)');
assert(1 / t.HeatPerFaultPerHour >= 24, 'a cold core with dry coolant melts down only after a day or more');
assert((1 - t.WarningHeat) / t.HeatPerFaultPerHour >= 12, 'at least 12 hours between the warning and a dry-core meltdown');
assert((t.FaultHeatLimit - t.WarningHeat) / t.HeatPerFaultPerHour >= 8, 'a single crew or maintenance fault gives at least 8 running hours between warning and its limit');
assert(t.MaintenanceWarningHours < t.MaintenanceIntervalHours && t.MaintenanceOutageHours > 12, 'maintenance warning precedes the due date and a nightly idle does not count as maintenance');
assert(t.MeltdownKillRadius < t.MeltdownIrradiationRadius && t.MeltdownRadius >= 1, 'radii: kill < irradiation, contamination >= 1');
assert(t.MeltdownIrradiationDose > 1, 'meltdown dose must irradiate (RadiationExposure irradiates at dose >= 1)');
assert(t.MeltdownEdgeSoilRadiation > tuning.floraThreshold && t.MeltdownFootprintSoilRadiation <= 1,
  `meltdown soil radiation must kill plants across the radius (edge > IrradiatedGroundThreshold ${tuning.floraThreshold})`);
for (const [name, spec] of Object.entries(leaks)) {
  assert(TRIGGERS.includes(spec.Trigger), `${name}: unknown trigger ${spec.Trigger}`);
  assert(spec.WarningFillFraction > 0 && spec.WarningFillFraction < 1, `${name}: warning must start before full`);
  assert(spec.SoilRadiationPerLeak >= tuning.floraThreshold && spec.SoilRadiationPerLeak <= 1, `${name}: one leak must make nearby soil lethal to crops`);
  assert(spec.GoodsPerLeak > 0 && spec.SludgeVolumePerGood > 0 && spec.LeakIntervalHours > 0 && spec.SoilRadius >= 0, `${name}: positive leak amounts`);
}
assert(leaks.refinery.SludgeVolumePerGood === tuning.volumePerGood, 'refinery sludge goods convert at RadiationTuning.VolumePerGood');
assert(leaks.vault.GoodId === WASTE && leaks.refinery.GoodId === SLUDGE, 'leak goods');

// ---- C# contracts ----
const specs = await source('MeltdownSpecs.cs');
const recordKeys = (record) => {
  const body = specs.match(new RegExp(`record ${record} : ComponentSpec \\{([\\s\\S]*?)\\n  \\}`))?.[1] ?? '';
  return [...body.matchAll(/\[Serialize\] public \w+ (\w+) \{ get; init; \}/g)].map((m) => m[1]);
};
for (const [record, keys] of Object.entries(SPEC_KEYS)) assert(same(recordKeys(record), keys), `${record}: C# [Serialize] properties differ from the authored keys`);
assert(TRIGGERS.every((trigger) => specs.includes(`public const string ${trigger} = "${trigger}";`)), 'WasteLeakTriggers constants match TRIGGERS');
// Status sprites must be vanilla 1.1.2.8 status icons (names from native status code).
const nativeSprites = ['BuildingBlockedByContamination', 'NoPower', 'LackOfResources', 'NoUnemployed', 'NothingToDo', 'NoStorage'];
for (const [, sprite] of specs.matchAll(/public const string \w+ = "(\w+)";/g))
  if (!TRIGGERS.includes(sprite)) assert(nativeSprites.includes(sprite), `MeltdownSprites uses ${sprite}, not a checked native status icon`);
const configurator = await source('MeltdownConfigurator.cs');
assert(configurator.includes('[Context("Game")]') && /AddDecorator<ReactorMeltdownSpec,\s*ReactorCore>/.test(configurator)
  && /AddDecorator<WasteLeakSpec,\s*WasteLeak>/.test(configurator) && configurator.includes('Bind<MeltdownService>().AsSingleton()'), 'MeltdownConfigurator binds the service and both decorators');
assert((await source('MeltdownPanels.cs')).includes('BindFragment<ReactorCorePanel>') && (await source('MeltdownPanels.cs')).includes('BindFragment<WasteLeakPanel>'), 'panels are bound');
assert((await readFile(resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Radiation', 'RadiationExposure.cs'), 'utf8')).includes('internal void AddDose(float dose)'), 'RadiationExposure.AddDose exists');
const core = await source('ReactorCore.cs');
assert(core.includes('IManufactoryLimiter') && !core.includes('_blockable.Block('), 'SCRAM is an IManufactoryLimiter, never BlockableObject.Block (which auto-empties the coolant)');
assert(core.includes('IGeneratorOutputFactor') && core.includes('1f - _heat'), 'the reactor scales its generator output by 1 - heat');
assert((await readFile(resolve(root, 'src', 'DeepFrontier', 'Scripts', 'WorkshopPoweredGenerator.cs'), 'utf8')).includes('_factor.OutputFactor'),
  'WorkshopPoweredGenerator applies IGeneratorOutputFactor');

// ---- localization ----
const csv = await readFile(data('Localizations', 'enUS.csv'), 'utf8');
const csvCell = (text) => /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
const lines = new Set(csv.split('\n'));
const ids = new Map(csv.split('\n').map((line) => [line.split(',')[0], line]));
for (const [id, text] of localizationRows(tuning.treatmentDays))
  assert(lines.has([id, text, 'Deep Frontier meltdown'].map(csvCell).join(',')), `enUS.csv lacks the authored row ${id}`);
for (const [id, text] of Object.entries(descriptions(REACTOR_TUNING, leaks, refinery.MechanicalNodeSpec.PowerInput))) {
  // connection_content.mjs appends its shared pipe phrase to piped buildings afterwards.
  const [, described = '', comment] = parseCsvRow(ids.get(`Building.${id}.Description`) ?? '');
  const extra = described.startsWith(text) ? described.slice(text.length).trim() : null;
  assert(comment === 'Deep Frontier' && extra !== null && (extra === '' || extra.split(/(?<=\.) /).every((s) => Object.values(PIPE_PHRASES).includes(s))),
    `Building.${id}.Description does not state its risk`);
  assert(text.startsWith(PRODUCER_DESCRIPTIONS[id]) || id === 'RadioactiveWasteRefinery', `${id}: risk text must extend the producer description`);
}
const loc = await source('MeltdownLoc.cs');
const constants = [...loc.matchAll(/public const string (\w+) = "([^"]+)";/g)];
for (const [, name, value] of constants) {
  const keys = value.startsWith('.') ? TRIGGERS.map((trigger) => `DeepFrontier.WasteLeak.${trigger}${value}`) : [value];
  for (const key of keys) assert(ids.has(key), `MeltdownLoc.${name}: enUS.csv has no ${key}`);
}
for (const name of ['ReactorCore.cs', 'MeltdownService.cs', 'WasteLeak.cs', 'MeltdownPanels.cs']) {
  const text = await source(name);
  for (const [, constant] of text.matchAll(/MeltdownLoc\.(\w+)/g)) assert(constants.some(([, n]) => n === constant), `${name}: MeltdownLoc.${constant} is not defined`);
  assert(!/_loc\.T\("/.test(text), `${name}: use MeltdownLoc keys, not literal localization keys`);
}

// ---- generation and automation wiring ----
const expansion = await readFile(resolve(root, 'tools', 'create_frontier_expansion_content.mjs'), 'utf8');
assert(expansion.includes("await (await import('./meltdown_content.mjs')).applyMeltdownContent();"), 'create_frontier_expansion_content.mjs runs the meltdown module');
const automation = await readJson(resolve(root, 'tools', 'automation_content.json'));
for (const spec of Object.keys(SPEC_KEYS)) {
  const declared = automation.customSpecs[spec];
  assert(declared?.kind === 'operational' && declared.evidence?.length, `automation_content.json customSpecs declares ${spec} as operational with evidence`);
  for (const {file, contains} of declared?.evidence ?? [])
    assert((await readFile(resolve(root, file), 'utf8').catch(() => '')).includes(contains), `${spec} evidence "${contains}" missing from ${file}`);
}
assert(automation.templates[REACTOR]?.role === 'pausable' && automation.templates[REFINERY]?.role === 'pausable', 'reactor and refinery are automatable (Off = cold shutdown / sealed tanks)');
assert(automation.templates[VAULT]?.role === 'none', 'vault has no automation role');

if (failures.length) {
  console.error(`Meltdown validation failed:\n  ${failures.join('\n  ')}`);
  process.exit(1);
}
console.log(`Meltdown validation passed: reactor warning ${Math.round(t.WarningHeat * 100)}% / fault limit ${Math.round(t.FaultHeatLimit * 100)}% / meltdown 100%; ` +
  `dry-core meltdown ${Math.round(1 / t.HeatPerFaultPerHour)} h from cold, ${Math.round(0.9 / (t.HeatPerFaultPerHour * 0.55 - t.CoolingPerHour * 0.45))} h from 10% at 45% coolant; ` +
  `vault leak ${leaks.vault.GoodsPerLeak} casks (${leaks.vault.SludgeVolumePerGood} each) / ${leaks.vault.LeakIntervalHours} h; ` +
  `refinery leak ${leaks.refinery.GoodsPerLeak} sludge / ${leaks.refinery.LeakIntervalHours} h; ${constants.length} localization keys.`);
