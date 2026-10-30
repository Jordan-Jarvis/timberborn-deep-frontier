// Rocket program: real launches on the Launch Pad.
//
// Called once, last, from tools/create_frontier_expansion_content.mjs after
// the Launch Pad and Mission Control blueprints, goods and localization exist:
//   await (await import('./rocket_program_content.mjs')).applyRocketProgram();
//
// Design (runtime in src/DeepFrontier/Scripts/RocketProgram/):
// - Each mission is a native Launch Pad recipe whose ingredients are one
//   complete rocket plus its liquid hydrogen/oxygen load (CyclesCapacity 1:
//   the pad stages exactly one rocket). Native haulers deliver, the native
//   recipe selector chooses the mission, workers and the pad's launch power
//   run the preparation window (the recipe cycle).
// - RocketLaunchPadSpec drives sequencing, odds, rewards and the story; the
//   pad's own native RangedEffectApplier (driven by RocketLaunchPad, not a
//   RangedEffectBuilding) carries the permanent wellbeing legacy of completed
//   missions within LegacyRadius while the pad is on a powered grid.
// - Mission Control gets RocketMissionControlSpec: an operating, staffed one
//   lowers launch risk.
// - RocketLaunchVisualSpec is written only when the Launch Pad art study
//   declares the rocket and exhaust nodes (art pending).
//
// Goods are owned by the goods generator; this module only checks the goods
// it consumes and fails if they are missing or of the wrong type.
import {readFile, writeFile, access} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRelative = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];

export const LAUNCH_PAD = 'Buildings/Metal/LaunchPad/LaunchPad.IronTeeth.blueprint';
export const MISSION_CONTROL = 'Buildings/Science/MissionControl/MissionControl.IronTeeth.blueprint';
export const LEGACY_RADIUS = 40;
export const LIQUID_FUELS = ['LiquidHydrogen', 'LiquidOxygen'];
export const VISUAL_NODES = {RocketNode: 'LaunchPad.Rocket', ExhaustNode: 'LaunchPad.RocketExhaust'};

// Ingredient amounts are one complete rocket and fuel load. Preparation hours
// are worker-hours of the native recipe cycle (two pad workers halve them).
export const MISSIONS = [
  {Id: 'OrbitalObservatory', prerequisite: '', baseFailure: .30, science: 100000, legacyWellbeing: 2, needOrder: 52,
    prepHours: 24, icon: 'RocketAirframe',
    ingredients: [['RocketAirframe', 24], ['PropulsionPackage', 12], ['GuidanceComputer', 4], ['RecoveredTelemetry', 2],
      ['LiquidHydrogen', 200], ['LiquidOxygen', 200]]},
  {Id: 'RecoveryProbe', prerequisite: 'OrbitalObservatory', baseFailure: .35, science: 250000, legacyWellbeing: 3, needOrder: 53,
    prepHours: 32, icon: 'MissionPayload',
    ingredients: [['RocketAirframe', 28], ['PropulsionPackage', 14], ['GuidanceComputer', 6], ['MissionPayload', 2],
      ['RecoveredTelemetry', 4], ['LiquidHydrogen', 280], ['LiquidOxygen', 280]]},
  {Id: 'LongRangeBeacon', prerequisite: 'RecoveryProbe', baseFailure: .40, science: 0, legacyWellbeing: 5, needOrder: 54,
    prepHours: 40, icon: 'GuidanceComputer', completesStory: true,
    ingredients: [['RocketAirframe', 32], ['PropulsionPackage', 16], ['GuidanceComputer', 8], ['MissionPayload', 4],
      ['RecoveredTelemetry', 6], ['LiquidHydrogen', 360], ['LiquidOxygen', 360]]},
];

export const PROGRAM = {
  MissionControlFailureReduction: .15,
  HeritageFailureReductionPerLaunch: .05,
  MaxHeritageFailureReduction: .15,
  MinimumFailureChance: .05,
  LaunchHoldProgress: .99,
  FlightHours: .75,
  FailurePointFraction: .4,
  RefurbishmentHours: 72,
  LegacyRadius: LEGACY_RADIUS,
};

export const recipeId = (mission) => `RocketMission.${mission.Id}`;
export const legacyNeedId = (mission) => `${mission.Id}Legacy`;
const missionKey = (mission, suffix) => `RocketProgram.Mission.${mission.Id}.${suffix}`;

export function launchPadSpec() {
  return {
    Missions: MISSIONS.map((m) => ({
      Id: m.Id, RecipeId: recipeId(m), PrerequisiteMissionId: m.prerequisite, BaseFailureChance: m.baseFailure,
      ScienceReward: m.science,
      LegacyEffect: {NeedId: legacyNeedId(m), PointsPerHour: 10, SatisfyToMaxValue: false},
      LegacyWellbeing: m.legacyWellbeing,
      DisplayNameLocKey: missionKey(m, 'DisplayName'), DescriptionLocKey: missionKey(m, 'Description'),
      SuccessLocKey: missionKey(m, 'Success'), FailureLocKey: missionKey(m, 'Failure'),
      CompletesStory: Boolean(m.completesStory),
    })),
    ...PROGRAM,
  };
}

export function missionRecipe(template, mission) {
  return {...template, RecipeSpec: {...template.RecipeSpec,
    Id: recipeId(mission), BackwardCompatibleIds: [], DisplayLocKey: `Recipe.${recipeId(mission)}`,
    CycleDurationInHours: mission.prepHours,
    Ingredients: mission.ingredients.map(([Id, Amount]) => ({Id, Amount})), Products: [],
    ProducedSciencePoints: 0, Fuel: '', CyclesFuelLasts: 0, FuelCapacity: 0, CyclesCapacity: 1,
    Icon: `Sprites/Goods/${mission.icon}Icon`}};
}

const GENERIC_PAD_DESCRIPTION = 'Deep Frontier launch pad production building';

export function localizationRows(powerHp) {
  const rows = [
    ['Building.LaunchPad.Description', `Launches the colony's rockets. Select a mission in the recipe list: haulers stage one complete rocket (airframes, propulsion, guidance, payload and telemetry) and its liquid hydrogen and oxygen; workers then prepare it under a ${powerHp.toLocaleString('en-US')} hp load. Every launch consumes the whole rocket and fuel, and a launch can fail. Also produces guidance telemetry.`],
    ['RocketProgram.Mission.OrbitalObservatory.DisplayName', 'Orbital Observatory'],
    ['RocketProgram.Mission.OrbitalObservatory.Description', 'First launch: lofts a telescope and archive receiver to read what the old orbital records saw.'],
    ['RocketProgram.Mission.OrbitalObservatory.Success', 'The observatory is in orbit. Its first passes recover fragments of the old orbital records: survey images of this valley before the drought, and a faint green trail of badwater running back to a single source far upriver. The archive now knows where to look.'],
    ['RocketProgram.Mission.OrbitalObservatory.Failure', 'Debris rained over the flame trench; the observatory was lost with its rocket and fuel.'],
    ['RocketProgram.Mission.RecoveryProbe.DisplayName', 'Recovery Probe'],
    ['RocketProgram.Mission.RecoveryProbe.Description', 'Second launch: sends a probe to a derelict orbital station to bring back its data core.'],
    ['RocketProgram.Mission.RecoveryProbe.Success', 'The probe docked with a silent human station and returned its data core. Among the corrupted files are intact fabrication notes and a map of the treatment works that once held the badwater back. The industrial frontier has its next blueprint.'],
    ['RocketProgram.Mission.RecoveryProbe.Failure', 'The probe never reached the station; the rocket broke up on ascent.'],
    ['RocketProgram.Mission.LongRangeBeacon.DisplayName', 'Long-Range Beacon'],
    ['RocketProgram.Mission.LongRangeBeacon.Description', "Final launch: places a long-lived beacon carrying the colony's archive and a standing signal."],
    ['RocketProgram.Mission.LongRangeBeacon.Success', "The beacon is aloft and transmitting. It carries the colony's archive, the record of the badwater source and a simple message: beavers live here, and the land is healing. Whoever listens next will know the way."],
    ['RocketProgram.Mission.LongRangeBeacon.Failure', 'The beacon was lost on ascent. The archive is safe on the ground; the colony must build and fuel another rocket.'],
    ['RocketProgram.Status.Locked', 'Mission locked: {0} must succeed first'],
    ['RocketProgram.Status.Completed', '{0} is already complete; select another mission'],
    ['RocketProgram.Status.Refurbishing', 'Launch pad refurbishing after a failed launch'],
    ['RocketProgram.Notification.Scrubbed', 'Launch scrubbed: {0} destacked; its parts and fuel were returned to the pad'],
    ['RocketProgram.Notification.Liftoff', 'Liftoff: {0} ({1}% failure risk)'],
    ['RocketProgram.Notification.Success', 'Mission success: {0}'],
    ['RocketProgram.Notification.Failure', 'Launch failure: {0} was lost ({1}% risk). The rocket and its fuel are gone and the pad needs {2} hours of refurbishment.'],
    ['RocketProgram.Notification.Refurbished', 'Launch pad refurbished and ready'],
    ['RocketProgram.Reward', 'Success reward: {0} science and a permanent +{1} wellbeing for beavers within {2} tiles of the pad while it is on a powered grid (pausing or automation do not remove it)'],
    ['RocketProgram.Panel.LegacyActive', 'Mission legacy: {0} completed missions give wellbeing within {1} tiles'],
    ['RocketProgram.Panel.LegacyUnpowered', 'Mission legacy paused: connect the pad to a powered grid to restore wellbeing from {0} completed missions within {1} tiles'],
    ['RocketProgram.Panel.Title', 'Rocket program'],
    ['RocketProgram.Panel.MissionCompleted', '{0}: completed'],
    ['RocketProgram.Panel.MissionLocked', '{0}: locked (requires {1})'],
    ['RocketProgram.Panel.MissionAvailable', '{0}: available'],
    ['RocketProgram.Panel.RocketStacked', 'Rocket stacked and fuelled on the pad'],
    ['RocketProgram.Panel.Odds', 'Failure chance at liftoff: {0}% (mission base {1}%)'],
    ['RocketProgram.Panel.OddsMissionControl', 'Operating Mission Control (staffed, powered): -{0}% of -{1}%'],
    ['RocketProgram.Panel.OddsHeritage', 'Flight heritage: -{0}% after {1} launches'],
    ['RocketProgram.Panel.OddsFloor', 'Risk never falls below {0}%'],
    ['RocketProgram.Panel.Stakes', 'Parts and fuel are loaded when preparation starts; changing the mission before liftoff returns them to the pad. Liftoff holds until the grid delivers full launch power. A failed launch destroys the rocket and its fuel and closes the pad for {0} hours of refurbishment.'],
    ['RocketProgram.Panel.FinalMission', "Final mission: success completes the colony's story."],
    ['RocketProgram.Panel.NoLaunches', 'No launches yet'],
    ['RocketProgram.Panel.LastSuccess', 'Last launch: {0} succeeded ({1}% risk)'],
    ['RocketProgram.Panel.LastFailure', 'Last launch: {0} failed ({1}% risk)'],
    ['RocketProgram.Stage.UnderConstruction', 'Under construction'],
    ['RocketProgram.Stage.NoMission', 'Select a mission, or guidance telemetry, in the recipe list'],
    ['RocketProgram.Stage.Telemetry', 'Producing guidance telemetry'],
    ['RocketProgram.Stage.InFlight', '{0} in flight'],
    ['RocketProgram.Stage.Refurbishing', 'Refurbishing after a failed launch: {0} hours left'],
    ['RocketProgram.Stage.Blocked', 'Paused or blocked by automation: no launch work'],
    ['RocketProgram.Stage.MissionCompleted', 'The selected mission is already complete'],
    ['RocketProgram.Stage.MissionLocked', 'The selected mission is locked'],
    ['RocketProgram.Stage.MissionInFlightElsewhere', 'The selected mission is in flight from another pad'],
    ['RocketProgram.Stage.Staging', 'Staging the rocket: waiting for every part and the full fuel load'],
    ['RocketProgram.Stage.Preparing', 'Launch preparation: {0}%'],
    ['RocketProgram.Stage.HoldingForPower', 'Countdown hold at {0}%: liftoff needs full launch power'],
  ];
  for (const m of MISSIONS) {
    const name = rows.find(([id]) => id === missionKey(m, 'DisplayName'))[1];
    rows.push([`Recipe.${recipeId(m)}`, `Launch: ${name}`]);
    rows.push([`Need.${legacyNeedId(m)}.DisplayName`, `${name} legacy`]);
  }
  return rows;
}

const csvCell = (text) => {
  if (typeof text !== 'string') throw new TypeError('Localization cells must be authored strings.');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csvRow = (id, text) => [id, text, 'Deep Frontier rocket program'].map(csvCell).join(',');

export async function applyRocketProgram({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
  const writeJson = (path, value) => writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
  const exists = (path) => access(path).then(() => true, () => false);
  const vanilla = resolve(root, ...vanillaRelative);

  const padPath = resolve(dataRoot, `${LAUNCH_PAD}.json`);
  if (!await exists(padPath)) throw new Error(`Rocket program: the Launch Pad blueprint is missing (${padPath}); generate it first`);
  const pad = await readJson(padPath);
  for (const key of ['ManufactorySpec', 'WorkshopSpec', 'WorkplaceSpec', 'MechanicalNodeSpec', 'MechanicalBuildingSpec'])
    if (!pad[key]) throw new Error(`Rocket program: the Launch Pad lacks ${key}`);
  // The launch load is the pad's generated draw (power rule: lategame_costs.mjs scaledPower).
  const launchHp = pad.MechanicalNodeSpec.PowerInput;
  if (!(launchHp > 0) || pad.MechanicalNodeSpec.PowerOutput !== 0)
    throw new Error(`Rocket program: the Launch Pad must be a power consumer (PowerInput ${launchHp})`);
  for (const key of ['RocketLaunchPadSpec', 'RangedEffectBuildingSpec', 'RocketLaunchVisualSpec'])
    if (pad[key]) throw new Error(`Rocket program: the Launch Pad already has ${key}; regenerate it from its producer`);

  // Consumed goods are authored by the goods generator.
  const collection = (await readJson(resolve(dataRoot, 'GoodCollections', 'GoodCollection.IronTeeth.blueprint.json'))).GoodCollectionSpec['Goods#append'];
  for (const id of new Set(MISSIONS.flatMap((m) => m.ingredients.map(([good]) => good)))) {
    const path = resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`);
    if (!await exists(path) || !collection.includes(id)) throw new Error(`Rocket program: good ${id} is not authored for Iron Teeth`);
    const type = (await readJson(path)).GoodSpec.GoodType;
    if (LIQUID_FUELS.includes(id) !== (type === 'Liquid')) throw new Error(`Rocket program: ${id} has GoodType ${type}; launch fuel must be Liquid and parts must not`);
  }

  const template = await readJson(resolve(vanilla, 'Recipes', 'Recipe.MetalBlock.blueprint.json'));
  for (const mission of MISSIONS) {
    if (pad.ManufactorySpec.ProductionRecipeIds.includes(recipeId(mission))) throw new Error(`Rocket program: ${recipeId(mission)} is already a Launch Pad recipe`);
    await writeJson(resolve(dataRoot, 'Recipes', `Recipe.${recipeId(mission)}.blueprint.json`), missionRecipe(template, mission));
    pad.ManufactorySpec.ProductionRecipeIds.push(recipeId(mission));
  }
  pad.RocketLaunchPadSpec = launchPadSpec();
  // No RangedEffectBuildingSpec: it would gate the legacy on pause/automation.

  // The rocket model node is authored in the Launch Pad art; wire the visual
  // once the study declares both nodes.
  const studyPath = resolve(root, 'outputs', 'lategame-studies', 'LaunchPad-study.json');
  const studyText = await readFile(studyPath, 'utf8');
  const declared = Object.values(VISUAL_NODES).filter((node) => studyText.includes(`"${node}"`));
  if (declared.length === 2) pad.RocketLaunchVisualSpec = {...VISUAL_NODES, AscentHeight: 40};
  else if (declared.length === 1) throw new Error(`Rocket program: the Launch Pad study declares only ${declared[0]}; the rocket and exhaust nodes ship together`);
  else console.log(`Rocket program: Launch Pad art does not yet declare ${Object.values(VISUAL_NODES).join(' and ')}; launch visual not wired.`);
  await writeJson(padPath, pad);

  const controlPath = resolve(dataRoot, `${MISSION_CONTROL}.json`);
  if (!await exists(controlPath)) throw new Error(`Rocket program: the Mission Control blueprint is missing (${controlPath})`);
  const control = await readJson(controlPath);
  if (control.RocketMissionControlSpec) throw new Error('Rocket program: Mission Control already has RocketMissionControlSpec');
  if (!control.WorkplaceSpec || !control.MechanicalNodeSpec) throw new Error('Rocket program: Mission Control must be a powered workplace');
  control.RocketMissionControlSpec = {};
  await writeJson(controlPath, control);

  // Legacy wellbeing: one Awe need per mission, cloned from the native wonder need.
  const needTemplate = await readJson(resolve(vanilla, 'Needs', 'Need.Beaver.EarthRepopulator.blueprint.json'));
  const needCollectionPath = resolve(dataRoot, 'NeedCollections', 'NeedCollection.IronTeeth.blueprint.json');
  const needCollection = await readJson(needCollectionPath);
  const needs = needCollection.NeedCollectionSpec['Needs#append'];
  for (const mission of MISSIONS) {
    const id = legacyNeedId(mission);
    if (needs.includes(id)) throw new Error(`Rocket program: need ${id} is already collected`);
    await writeJson(resolve(dataRoot, 'Needs', `Need.Beaver.${id}.blueprint.json`), {...needTemplate, NeedSpec: {...needTemplate.NeedSpec,
      Id: id, BackwardCompatibleIds: [], Order: mission.needOrder, DisplayNameLocKey: `Need.${id}.DisplayName`,
      FavorableWellbeing: mission.legacyWellbeing, UnfavorableWellbeing: 0}});
    needs.push(id);
  }
  await writeJson(needCollectionPath, needCollection);

  const localizationPath = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  const rows = localizationRows(launchHp);
  const index = new Map(lines.map((line, i) => [line.split(',')[0], i]));
  const [descriptionId, description] = rows[0];
  const generic = csvRow(descriptionId, GENERIC_PAD_DESCRIPTION).split(',').slice(0, 2).join(',');
  if (!index.has(descriptionId) || !lines[index.get(descriptionId)].startsWith(generic + ','))
    throw new Error('Rocket program: Building.LaunchPad.Description is not the generic producer text; update its producer instead');
  lines[index.get(descriptionId)] = csvRow(descriptionId, description);
  if (lines.at(-1) !== '') throw new Error('Rocket program: enUS.csv must end with a newline');
  lines.pop();
  for (const [id, text] of rows.slice(1)) {
    if (index.has(id)) throw new Error(`Rocket program: localization ${id} already exists`);
    lines.push(csvRow(id, text));
  }
  await writeFile(localizationPath, `${lines.join('\n')}\n`, 'utf8');
  return {missions: MISSIONS.length, visual: Boolean(pad.RocketLaunchVisualSpec)};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applyRocketProgram(dataRoot ? {dataRoot} : {})));
}
