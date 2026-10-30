// Static checks for the rocket program (tools/rocket_program_content.mjs and
// src/DeepFrontier/Scripts/RocketProgram). Usage:
//   node tools/validate_rocket_program.mjs [dataRoot]
// Static evidence only: it does not establish hauling, launches or reload.
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {LAUNCH_PAD, MISSION_CONTROL, LEGACY_RADIUS, LIQUID_FUELS, VISUAL_NODES, MISSIONS, PROGRAM,
  launchPadSpec, recipeId, legacyNeedId, localizationRows} from './rocket_program_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'RocketProgram');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const data = (...parts) => resolve(dataRoot, ...parts);
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const exists = (path) => access(path).then(() => true, () => false);

// ---- Launch Pad blueprint ----
const pad = await readJson(data(`${LAUNCH_PAD}.json`));
// Its exact draw is the power rule's (validate_power_rule.mjs).
const launchHp = pad.MechanicalNodeSpec?.PowerInput;
assert(launchHp > 0 && pad.MechanicalNodeSpec.PowerOutput === 0, 'Launch Pad must be a power consumer');
assert(pad.WorkplaceSpec && pad.WorkshopSpec && pad.MechanicalBuildingSpec, 'Launch Pad must stay a powered native workshop (automation role pausable)');
const padRecipes = pad.ManufactorySpec?.ProductionRecipeIds ?? [];
assert(padRecipes.includes('GuidanceTelemetry'), 'Launch Pad keeps its GuidanceTelemetry recipe');
for (const m of MISSIONS) assert(padRecipes.filter((id) => id === recipeId(m)).length === 1, `Launch Pad must list ${recipeId(m)} once`);
assert(same(pad.RocketLaunchPadSpec, launchPadSpec()), 'RocketLaunchPadSpec differs from the producing module');
assert(!pad.RangedEffectBuildingSpec, 'Launch Pad has no RangedEffectBuildingSpec: its native activity gate would switch the legacy off when paused or automation-blocked (review 2026-10-21 #2)');
assert(pad.RocketLaunchPadSpec?.LegacyRadius === LEGACY_RADIUS, `Launch Pad legacy radius must be ${LEGACY_RADIUS}`);
if (pad.RocketLaunchVisualSpec) {
  assert(pad.RocketLaunchVisualSpec.RocketNode === VISUAL_NODES.RocketNode && pad.RocketLaunchVisualSpec.ExhaustNode === VISUAL_NODES.ExhaustNode
    && pad.RocketLaunchVisualSpec.AscentHeight > 0, 'RocketLaunchVisualSpec names the authored rocket/exhaust nodes');
}
const study = await readFile(resolve(root, 'outputs', 'lategame-studies', 'LaunchPad-study.json'), 'utf8');
const artReady = Object.values(VISUAL_NODES).every((node) => study.includes(`"${node}"`));
assert(Boolean(pad.RocketLaunchVisualSpec) === artReady, 'Launch visual must be wired exactly when the art study declares both nodes');

// ---- Program parameters ----
const spec = launchPadSpec();
assert(spec.Missions.length === 3, 'Three mission tiers');
spec.Missions.forEach((m, i) => {
  assert(i === 0 ? m.PrerequisiteMissionId === '' : m.PrerequisiteMissionId === spec.Missions[i - 1].Id, `${m.Id}: ordered chain`);
  assert(m.CompletesStory === (i === spec.Missions.length - 1), `${m.Id}: only the last mission completes the story`);
  assert(m.BaseFailureChance >= PROGRAM.MinimumFailureChance && m.BaseFailureChance < 1, `${m.Id}: base failure chance`);
  assert(m.LegacyWellbeing > 0 && m.LegacyEffect.PointsPerHour > 0 && m.ScienceReward >= 0, `${m.Id}: rewards`);
});
// Odds a player sees: first attempt of each tier after succeeding the earlier ones with an operating Mission Control.
const odds = spec.Missions.map((m, attempts) => Math.max(PROGRAM.MinimumFailureChance,
  m.BaseFailureChance - PROGRAM.MissionControlFailureReduction - Math.min(PROGRAM.MaxHeritageFailureReduction, attempts * PROGRAM.HeritageFailureReductionPerLaunch)));
assert(odds.every((p) => p > PROGRAM.MinimumFailureChance && p <= .2), `Staffed first attempts carry real but bounded risk: ${odds.map((p) => p.toFixed(2))}`);
assert(spec.Missions.every((m) => m.BaseFailureChance >= .3), 'Launching without Mission Control or heritage is at least 30% risk');

// ---- Mission recipes and goods ----
const collection = (await readJson(data('GoodCollections', 'GoodCollection.IronTeeth.blueprint.json'))).GoodCollectionSpec['Goods#append'];
const recipes = new Map();
for (const file of await readdir(data('Recipes'))) if (file.endsWith('.blueprint.json')) {
  const r = (await readJson(data('Recipes', file))).RecipeSpec; recipes.set(r.Id, r);
}
for (const m of MISSIONS) {
  const r = recipes.get(recipeId(m));
  if (!r) { failures.push(`Missing recipe ${recipeId(m)}`); continue; }
  assert(same(r.Ingredients, m.ingredients.map(([Id, Amount]) => ({Id, Amount}))), `${r.Id}: ingredients are one complete rocket and fuel load`);
  assert(r.Products.length === 0 && r.ProducedSciencePoints === 0 && r.Fuel === '' && r.FuelCapacity === 0, `${r.Id}: no products, science or fuel (rewards are runtime)`);
  assert(r.CyclesCapacity === 1, `${r.Id}: the pad stages exactly one rocket`);
  assert(r.CycleDurationInHours === m.prepHours && r.CycleDurationInHours > 0, `${r.Id}: preparation window`);
  assert(await exists(data(...`${r.Icon}.png`.split('/'))), `${r.Id}: icon ${r.Icon} exists`);
  for (const good of ['RocketAirframe', 'PropulsionPackage', 'GuidanceComputer', 'RecoveredTelemetry', ...LIQUID_FUELS])
    assert(r.Ingredients.some((i) => i.Id === good), `${r.Id}: consumes ${good}`);
  if (m.prerequisite) assert(r.Ingredients.some((i) => i.Id === 'MissionPayload'), `${r.Id}: higher tiers carry a MissionPayload`);
  assert(!r.Ingredients.some((i) => ['FlightLicense', 'IndustrialLicense', 'SpecialistLicense'].includes(i.Id)), `${r.Id}: no prohibited license tokens (tools/content_policy.json)`);
  for (const {Id} of r.Ingredients) {
    assert(collection.includes(Id), `${r.Id}: ${Id} is an Iron Teeth good`);
    const good = (await readJson(data('Goods', `Good.${Id}.blueprint.json`))).GoodSpec;
    assert((good.GoodType === 'Liquid') === LIQUID_FUELS.includes(Id), `${Id}: launch fuels are Liquid goods, parts are not`);
  }
}
// Fuel grows with tier; each launch costs more than the last.
for (let i = 1; i < MISSIONS.length; i++) {
  const amount = (m, id) => m.ingredients.find(([g]) => g === id)[1];
  for (const id of LIQUID_FUELS) assert(amount(MISSIONS[i], id) > amount(MISSIONS[i - 1], id), `${MISSIONS[i].Id}: more ${id} than ${MISSIONS[i - 1].Id}`);
}

// ---- Mission Control ----
const control = await readJson(data(`${MISSION_CONTROL}.json`));
assert(same(control.RocketMissionControlSpec, {}), 'Mission Control carries RocketMissionControlSpec');

// ---- Legacy needs ----
const needs = (await readJson(data('NeedCollections', 'NeedCollection.IronTeeth.blueprint.json'))).NeedCollectionSpec['Needs#append'];
for (const m of MISSIONS) {
  const id = legacyNeedId(m);
  assert(needs.filter((n) => n === id).length === 1, `${id} collected once for Iron Teeth`);
  const path = data('Needs', `Need.Beaver.${id}.blueprint.json`);
  if (!await exists(path)) { failures.push(`Missing need blueprint ${id}`); continue; }
  const need = (await readJson(path)).NeedSpec;
  assert(need.Id === id && need.NeedGroupId === 'Awe' && need.CharacterType === 'Beaver' && need.FavorableWellbeing === m.legacyWellbeing,
    `${id}: Awe need worth +${m.legacyWellbeing} wellbeing`);
}

// ---- Localization ----
const loc = new Map((await readFile(data('Localizations', 'enUS.csv'), 'utf8')).split('\n').slice(1).filter(Boolean)
  .map((line) => [line.split(',')[0], line]));
const csharp = (await Promise.all((await readdir(scripts)).filter((f) => f.endsWith('.cs')).map((f) => readFile(resolve(scripts, f), 'utf8')))).join('\n');
const codeKeys = new Set([...csharp.matchAll(/"(RocketProgram\.[A-Za-z.]+)"/g)].map((match) => match[1]));
const specKeys = spec.Missions.flatMap((m) => [m.DisplayNameLocKey, m.DescriptionLocKey, m.SuccessLocKey, m.FailureLocKey]);
for (const key of [...codeKeys, ...specKeys, ...MISSIONS.map((m) => `Recipe.${recipeId(m)}`), ...MISSIONS.map((m) => `Need.${legacyNeedId(m)}.DisplayName`)])
  assert(loc.has(key), `Missing enUS row ${key}`);
for (const [id] of localizationRows(launchHp)) assert(loc.has(id), `Missing authored enUS row ${id}`);
assert(!loc.get('Building.LaunchPad.Description')?.includes('production building'), 'Launch Pad description explains launches');
// Placeholder counts used by the code must exist in the text.
const placeholders = {'RocketProgram.Status.Locked': 1, 'RocketProgram.Notification.Liftoff': 2, 'RocketProgram.Notification.Failure': 3,
  'RocketProgram.Reward': 3, 'RocketProgram.Panel.LegacyActive': 2, 'RocketProgram.Panel.LegacyUnpowered': 2, 'RocketProgram.Panel.Odds': 2, 'RocketProgram.Panel.OddsHeritage': 2, 'RocketProgram.Stage.Refurbishing': 1};
for (const [key, count] of Object.entries(placeholders))
  for (let i = 0; i < count; i++) assert(loc.get(key)?.includes(`{${i}}`), `${key} must contain {${i}}`);

// ---- C# spec contract matches the authored JSON ----
const specSource = await readFile(resolve(scripts, 'RocketProgramSpecs.cs'), 'utf8');
const fields = (record) => {
  const body = specSource.match(new RegExp(`record ${record}\\b[^{]*\\{([\\s\\S]*?)\\n  \\}`))?.[1] ?? '';
  return [...body.matchAll(/\[Serialize\] public [^ ]+ (\w+)/g)].map((match) => match[1]).sort();
};
assert(same(fields('RocketLaunchPadSpec'), Object.keys(spec).sort()), 'RocketLaunchPadSpec C# fields match the blueprint');
assert(same(fields('RocketMissionSpec'), Object.keys(spec.Missions[0]).sort()), 'RocketMissionSpec C# fields match the blueprint');
assert(same(fields('RocketLaunchVisualSpec'), [...Object.keys(VISUAL_NODES), 'AscentHeight'].sort()), 'RocketLaunchVisualSpec C# fields match the module');
assert(/AddDecorator<RocketLaunchPadSpec,RocketLaunchPad>/.test(csharp) && /AddDecorator<RocketMissionControlSpec,RocketMissionControl>/.test(csharp)
  && /AddDecorator<RocketLaunchVisualSpec,RocketLaunchVisual>/.test(csharp), 'Rocket program decorators are registered');
assert(/\[Context\("Game"\)\]\s*public sealed class RocketProgramConfigurator/.test(csharp), 'RocketProgramConfigurator is a Game context configurator');

// ---- Review 2026-10-21 regressions (outputs/review-2026-10-21/rocket.json) ----
const source = async (file) => (await readFile(resolve(scripts, file), 'utf8')).replace(/\/\/.*$/gm, '');
const visualSource = await source('RocketLaunchVisual.cs');
const padSource = await source('RocketLaunchPad.cs');
// #1 The #Unfinished ConstructionStage0 model is an exported copy of the finished
// mesh, so node lookups must be scoped to the finished model root.
assert(/FindChildIfNameNotEmpty\(GetComponent<BuildingModelSpec>\(\)\.FinishedModelName\)/.test(visualSource)
  && /finished\.GetComponentsInChildren<Transform>\(true\)/.test(visualSource)
  && !/(^|[^.\w])GameObject\.GetComponentsInChildren/.test(visualSource), '#1: rocket nodes are searched only under the finished model');
if (pad.RocketLaunchVisualSpec) {
  assert(pad.Children?.['#Finished']?.TimbermeshSpec?.Model && pad.Children?.['#Unfinished'], '#1: Launch Pad has separate finished/unfinished models');
}
// #2 Legacy wellbeing: powered grid is the only condition.
assert(/AddDecorator<RocketLaunchPad,RangedEffectApplier>/.test(csharp), '#2: RocketLaunchPad owns a native RangedEffectApplier');
assert(/LegacyPowered=>_power\.Powered;/.test(padSource), '#2: legacy activity is the pad grid being powered');
const updateLegacy = padSource.match(/void UpdateLegacy\(\)\s*\{([\s\S]*?)\n    \}/)?.[1] ?? '';
assert(updateLegacy && !/IsUnblocked|Paused|PowerEfficiency/.test(updateLegacy), '#2: legacy ignores pause/automation and power efficiency');
assert(/UpdateEfficiency\(1f\)/.test(padSource) && !/_range\b/.test(padSource), '#2: legacy is not scaled and does not use RangedEffectBuilding');
// #3 Scrub refund re-runs the native unwanted-stock check.
const scrub = padSource.match(/void OnRecipeChanged\([^)]*\)\s*\{([\s\S]*?)\n    \}/)?.[1] ?? '';
const give = scrub.indexOf('GiveExistingIgnoringCapacity'), recheck = scrub.indexOf('_goodDisallower.UpdateAllowedAmounts(_manufactory.CurrentRecipe)');
assert(give >= 0 && recheck > give, '#3: scrub refund is followed by RecipeGoodDisallower.UpdateAllowedAmounts so overflow is hauled out');

// ---- Plan balance (informational) ----
const recipeOf = (id) => recipes.get(id);
const expand = (m) => {
  const totals = {};
  for (const [good, amount] of m.ingredients) {
    const r = recipeOf(good);
    if (r && ['RocketAirframe', 'PropulsionPackage'].includes(good))
      for (const i of r.Ingredients) totals[i.Id] = (totals[i.Id] ?? 0) + i.Amount * amount / r.Products[0].Amount;
  }
  return totals;
};
for (const m of MISSIONS) {
  const t = expand(m);
  const structural = (t.HighGradeSteel ?? 0) + (t.Alloy ?? 0) + (t.TreatedPlank ?? 0);
  console.log(`${m.Id}: airframe+propulsion structural ${structural}, machine cores ${t.MachineCore ?? 0}, polymer ${t.Polymer ?? 0}; ` +
    `fuel ${m.ingredients.filter(([g]) => LIQUID_FUELS.includes(g)).map(([g, a]) => `${a} ${g}`).join(' + ')}; prep ${m.prepHours} worker-h; ` +
    `staffed first-attempt risk ${(odds[MISSIONS.indexOf(m)] * 100).toFixed(0)}%`);
}

if (failures.length) {
  console.error(`ROCKET PROGRAM VALIDATION FAILED (${failures.length}):\n- ${failures.join('\n- ')}`);
  process.exit(1);
}
console.log(`Rocket program validation passed (${dataRoot}).`);
