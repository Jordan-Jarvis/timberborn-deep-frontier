// Radiation content module (goods, need, hospital treatment, recipes and the
// three radiation buildings) for src/DeepFrontier/Scripts/Radiation.
//
// Called by tools/create_vertical_slice_content.mjs after the expansion,
// construction and tool-override generators (it extends their output: the
// Hospital blueprint, the Iron Teeth good/need/template collections and
// enUS.csv, all rewritten fresh by each canonical run) and before workforce
// risks and the automation audit. Every target must exist and none of this
// module's ids may already be in those per-run files; anything else throws.
// Its own goods, recipes, buildings, need and icons are rewritten each run.
//
// Usage:
//   node tools/radiation_content.mjs [dataRoot]
//   import {applyRadiationContent} from './radiation_content.mjs';
//   await applyRadiationContent();             // src/DeepFrontier/Data
// dataRoot defaults to src/DeepFrontier/Data; use a scratch copy to test.
import {readFile, writeFile, mkdir, access} from 'node:fs/promises';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createRadiationIcons} from './create_radiation_icons.mjs';
import {LATEGAME, applyLategame, studyCell, studyPipePort, studyString} from './lategame_building_content.mjs';
import {lategameCost} from './lategame_costs.mjs';
import {mapObjectModel, mapObjectCollider} from './map_object_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const tuningSource = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Radiation', 'IRadiationService.cs');

export const SLUDGE = 'RadioactiveSludge';
export const CONTAMINATED_WATER = 'ContaminatedWater';
export const NEED = 'Irradiation';
// The irradiated beaver is the Radioactive Zombie (C#: RadioactiveZombie.cs).
// It must walk slower than a native badwater-contaminated beaver: vanilla
// Need.Beaver.BadwaterContamination has MovementSpeed -0.7 (x0.30); the
// MovementSpeed bonus is additive and clamped at BonusType.MovementSpeed
// MinimumValue 0.25. -0.8 gives x0.25 (the native floor) on its own and
// stays 0.1 below a contaminated beaver with any shared bonus until both
// reach the floor.
export const ZOMBIE_MOVEMENT_DELTA = -0.8;
export const ZOMBIE_NAME = 'Radioactive Zombie';
export const VOLUME_PER_GOOD = 0.2;         // radioactive volume (r * water volume) per RadioactiveSludge good
// Recovery pump: native water it may pump per recipe cycle (0.5 h) to find the
// 0.2 radioactive volume of one good; 4 is pure radioactive water down to r = 0.05.
export const RECOVERY_MAX_WATER_PER_CYCLE = 4;

// Radiation buildings. Each clones a vanilla Iron Teeth template for its
// native behaviour (workplace, manufactory, intake pipe) and swaps in
// radiation recipes and specs; geometry, model, construction stage, colliders
// and animation come from its late-game study (tools/asset-pipeline/
// lategame_<Id>.py, outputs/lategame-studies/<Id>-registration.json) through
// lategame_building_content.mjs, and its cost from the late-game cost rule.
// pipe: the study's Timber Pipes socket constant.
export const RADIATION_BUILDINGS = [
  {id: 'RadioactiveWasteExport', template: 'Buildings/Water/Discharge/Discharge.IronTeeth.blueprint.json',
   recipes: ['ExportRadioactiveSludge', 'ExportContaminatedWater'], toolOrder: 22, science: 200000, kind: 'export', pipe: 'PIPE_INLET'},
  {id: 'RadioactiveSludgeOutfall', template: 'Buildings/Water/Discharge/Discharge.IronTeeth.blueprint.json',
   recipes: ['ReleaseRadioactiveSludge'], toolOrder: 21, science: 200000, kind: 'outfall', pipe: 'PIPE_INLET'},
  {id: 'RadioactiveSludgeRecoveryPump', template: 'Buildings/Water/DeepBadwaterPump/DeepBadwaterPump.IronTeeth.blueprint.json',
   recipes: ['RecoverRadioactiveSludge'], toolOrder: 13, science: 200000, kind: 'recovery', pipe: 'PIPE_OUTLET'},
];
// Footprint sides as Timberborn Direction2D (local block coordinates).
const EDGE_ROWS = {Down: ([w, h]) => [...Array(w).keys()].map((x) => [x, 0]), Up: ([w, h]) => [...Array(w).keys()].map((x) => [x, h - 1]),
  Left: ([w, h]) => [...Array(h).keys()].map((y) => [0, y]), Right: ([w, h]) => [...Array(h).keys()].map((y) => [w - 1, y])};

// Natural radioactive water source (C#: RadioactiveSpring.cs): a native water
// source (vanilla DevWaterSource with its WaterSourceSpec, strength UI and
// saving, WaterSourceContaminationSpec 0) whose water is radioactive. The
// dev-mode tool and the map-editor object (MapEditorWater group, map editor
// Common collection) are the same spring.
export const RADIATION_SPRINGS = [
  {id: 'RadioactiveSpring', path: 'Buildings/Water/RadioactiveSpring/RadioactiveSpring.blueprint', collection: 'buildings',
   toolGroup: 'Water', toolOrder: 9001, icon: 'Buildings/Water/RadioactiveSpring/RadioactiveSpringIcon'},
  {id: 'RadioactiveSpringSource', path: 'MapEditor/Objects/RadioactiveSpringSource/RadioactiveSpringSource.blueprint', collection: 'mapEditor',
   toolGroup: 'MapEditorWater', toolOrder: 510, icon: 'MapEditor/Objects/RadioactiveSpringSource/RadioactiveSpringSourceIcon'},
];
export const SPRING_SPEC = {RadioactiveShare: 1};
// Default output 0.5 radioactive water units per game hour, as the sludge
// spring released. Native strength is water per simulated second; a strength-1
// source adds TickIntervalInSeconds * ConfiguredDayLengthInTicks / 24 water per
// game hour (19.2 in 1.1.2.8).
export const SPRING_RADIOACTIVE_PER_HOUR = 0.5;

export const RADIATION_RECIPES = [
  {id: 'ExportRadioactiveSludge', hours: 1, ingredients: [[SLUDGE, 5]], products: [], label: SLUDGE},
  {id: 'ExportContaminatedWater', hours: 1, ingredients: [[CONTAMINATED_WATER, 5]], products: [], label: CONTAMINATED_WATER},
  {id: 'ReleaseRadioactiveSludge', hours: 1, ingredients: [[SLUDGE, 3]], products: [], label: SLUDGE},
  {id: 'RecoverRadioactiveSludge', hours: 0.5, ingredients: [], products: [[SLUDGE, 1]], label: SLUDGE},
];

// Radioactive yellow-green, distinct from Water and the Badwater brown.
// Tank surfaces: sludge uses the native yellow-green Biofuel liquid (it read as
// golden canola oil in tanks); contaminated water keeps the canola material.
const GOODS = [
  {id: SLUDGE, order: 10190, color: {r: 0.80, g: 0.87, b: 0.10, a: 1}, name: 'Radioactive Sludge', material: 'Materials/Goods/BioFuel'},
  {id: CONTAMINATED_WATER, order: 10200, color: {r: 0.62, g: 0.72, b: 0.18, a: 1}, name: 'Contaminated Water', material: 'Materials/Goods/CanolaOil'},
];

const LOCALIZATION = [
  [`Good.${SLUDGE}.DisplayName`, 'Radioactive Sludge'],
  [`Good.${SLUDGE}.PluralDisplayName`, 'Radioactive Sludge'],
  [`Good.${CONTAMINATED_WATER}.DisplayName`, 'Contaminated Water'],
  [`Good.${CONTAMINATED_WATER}.PluralDisplayName`, 'Contaminated Water'],
  [`Need.${NEED}.DisplayName`, ZOMBIE_NAME],
  [`Status.Need.${NEED}`, `${ZOMBIE_NAME}: shambles slowly, eats and drinks twice as much and cannot work. Needs 10 days of hospital care; untreated radiation sickness is fatal after 8 days.`],
  [`Status.Need.${NEED}.Short`, ZOMBIE_NAME],
  ['DeepFrontier.Radiation.Zombie.Subtitle', `{0} · ${ZOMBIE_NAME}`],
  ['DeepFrontier.Radiation.Zombie.Countdown', 'Dies in {0} days without hospital treatment.'],
  ['DeepFrontier.Radiation.Zombie.CountdownPaused', 'Hospital care has paused the radiation sickness: {0} days left untreated.'],
  ['DeepFrontier.Radiation.Zombie.Flavor', 'Glows faintly, eats for two, works for nobody.'],
  ['DeepFrontier.Radiation.Zombie.Dying', `${ZOMBIE_NAME}: dies in under 2 days without hospital treatment.`],
  ['DeepFrontier.Radiation.Zombie.Dying.Short', 'Zombie dying'],
  ['Building.RadioactiveWasteExport.DisplayName', 'Radioactive Waste Export'],
  ['Building.RadioactiveWasteExport.Description', 'Ships barrelled radioactive sludge and contaminated water off the map for good. Must touch the map edge: place its dispatch gate on the edge. Fed by pipe at its front socket or by haulers.'],
  ['Building.RadioactiveWasteExport.FlavorDescription', 'Somewhere downstream, it is somebody else\'s problem.'],
  ['Building.RadioactiveSludgeOutfall.DisplayName', 'Sludge Outfall'],
  ['Building.RadioactiveSludgeOutfall.Description', 'Pours barrelled radioactive sludge into the world as radioactive water over the lip of its spillway. It mixes with the water it meets, stops pumps, irradiates beavers, leaves irradiated ground where it dries, and only leaves through open map edges. Fed by pipe at its front socket or by haulers.'],
  ['Building.RadioactiveSludgeOutfall.FlavorDescription', 'Out of sight is not out of the river.'],
  ['Building.RadioactiveSludgeRecoveryPump.DisplayName', 'Sludge Recovery Pump'],
  ['Building.RadioactiveSludgeRecoveryPump.Description', 'Pumps radioactive water through its intake pipe and barrels its radioactivity as sludge for export; the fresh water pumped with it is used up. The intake drops from the middle of the back deck, so that cell must stand over open water, with ground under the two piers beside it. Delivers the barrels by pipe from its front socket or to haulers.'],
  ['Building.RadioactiveSludgeRecoveryPump.FlavorDescription', 'The cleanup always takes longer than the spill.'],
  ['DeepFrontier.Radiation.Status.PumpBlocked', 'Radiation detected at the intake. Pumps cannot filter radiation, so pumping has stopped until the water is clean.'],
  ['DeepFrontier.Radiation.Status.PumpBlocked.Short', 'Radiation detected'],
  ['DeepFrontier.Radiation.Status.StorageIrradiated', 'Stored water is irradiated and undrinkable.'],
  ['DeepFrontier.Radiation.Status.NoRadiation', 'No radioactive water at the intake.'],
  ['DeepFrontier.Radiation.WaterShares', 'Water at the intake: {0}% fresh, {1}% bad, {2}% radioactive.'],
  ['DeepFrontier.Radiation.Status.OutletBlocked', 'The outlet is blocked.'],
  ['DeepFrontier.Radiation.Placement.NotAtMapEdge', 'Must touch the map edge.'],
  ['DeepFrontier.Radiation.DeathMessage', '{0} the radioactive zombie fell apart from untreated radiation sickness.'],
  ['DeepFrontier.Radiation.Planting.Warning', 'Radiation: plants on irradiated (yellow-green) ground die immediately, including anything planted there.'],
  ['Building.RadioactiveSpring.DisplayName', 'Radioactive Spring'],
  ['Building.RadioactiveSpring.Description', 'A natural spring of radioactive water. Its strength works like a water source; 0 stops it.'],
  ['Building.RadioactiveSpringSource.DisplayName', 'Radioactive Spring'],
  ['Building.RadioactiveSpringSource.Description', 'A natural spring of radioactive water. Its strength works like a water source; 0 stops it.'],
];

const clone = value => JSON.parse(JSON.stringify(value));

async function exists(path) {
  try { await access(path); return true; } catch { return false; }
}

async function readJson(path) {
  if (!await exists(path)) throw new Error(`Radiation content target is missing: ${path}`);
  // Vanilla 1.1.2.8 blueprints may carry a UTF-8 byte order mark.
  return JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
}

async function writeJson(path, value) {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}


function appendUnique(list, values, what) {
  if (!Array.isArray(list)) throw new Error(`${what} is not an append list`);
  for (const value of values) {
    if (list.includes(value)) throw new Error(`${what} already contains ${value}`);
    list.push(value);
  }
}

function csvCell(value) {
  const text = String(value);
  return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
}

export async function readTuning() {
  const source = await readFile(tuningSource, 'utf8');
  const number = name => {
    const match = source.match(new RegExp(`const float ${name} = ([0-9.]+)f`));
    if (!match) throw new Error(`RadiationTuning.${name} not found in ${tuningSource}`);
    return Number(match[1]);
  };
  return {treatmentDays: number('TreatmentDays'), volumePerGood: number('VolumePerGood')};
}

async function makeGood({id, order, color, material}, dataRoot) {
  const value = clone(await readJson(resolve(vanillaRoot, 'Goods', 'Good.Badwater.blueprint.json')));
  const spec = value.GoodSpec;
  Object.assign(spec, {
    Id: id, BackwardCompatibleIds: [], ConsumptionEffects: [], GoodType: 'Liquid', StockpileVisualization: 'Liquid',
    VisibleContainer: 'Barrel', ContainerColor: color, ContainerMaterial: material,
    CarryingAnimation: 'CarryInHands', Weight: 2, GoodGroupId: 'Ingredients', GoodOrder: order,
    Icon: `Sprites/Goods/${id}Icon`, ForceImport: true,
    DisplayNameLocKey: `Good.${id}.DisplayName`, PluralDisplayNameLocKey: `Good.${id}.PluralDisplayName`,
  });
  await writeJson(resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`), value);
}

async function makeRecipe({id, hours, ingredients, products, label}, dataRoot) {
  const value = clone(await readJson(resolve(vanillaRoot, 'Recipes', 'Recipe.FlowingBadwater.blueprint.json')));
  Object.assign(value.RecipeSpec, {
    Id: id, BackwardCompatibleIds: [], DisplayLocKey: `Good.${label}.DisplayName`, CycleDurationInHours: hours,
    Ingredients: ingredients.map(([Id, Amount]) => ({Id, Amount})), Products: products.map(([Id, Amount]) => ({Id, Amount})),
    ProducedSciencePoints: 0, Fuel: '', CyclesFuelLasts: 0, FuelCapacity: 0, CyclesCapacity: 5, Icon: `Sprites/Goods/${label}Icon`,
  });
  await writeJson(resolve(dataRoot, 'Recipes', `Recipe.${id}.blueprint.json`), value);
}

function removeComponents(value, names, id) {
  for (const name of names) {
    if (!Object.hasOwn(value, name)) throw new Error(`${id}: expected template component ${name} is missing`);
    delete value[name];
  }
}

async function makeBuilding(building, dataRoot, tuning) {
  const value = clone(await readJson(resolve(vanillaRoot, building.template)));
  const id = building.id;
  if (!LATEGAME.has(id)) throw new Error(`${id}: its study is not integrated (tools/lategame_batches.json)`);
  const folder = `Buildings/Water/${id}`;
  const registration = await readJson(resolve(root, 'outputs', 'lategame-studies', `${id}-registration.json`));
  value.TemplateSpec.TemplateName = `${id}.IronTeeth`;
  value.TemplateSpec.BackwardCompatibleTemplateNames = [];
  value.ManufactorySpec.ProductionRecipeIds = [...building.recipes];
  value.BuildingSpec.BuildingCost = (await lategameCost(id)).map(([Id, Amount]) => ({Id, Amount}));
  value.BuildingSpec.ScienceCost = building.science;
  value.PlaceableBlockObjectSpec.ToolGroupId = 'Water';
  value.PlaceableBlockObjectSpec.ToolOrder = building.toolOrder;
  Object.assign(value.LabeledEntitySpec, {
    DisplayNameLocKey: `Building.${id}.DisplayName`, DescriptionLocKey: `Building.${id}.Description`,
    FlavorDescriptionLocKey: `Building.${id}.FlavorDescription`, Icon: `${folder}/${id}Icon`,
  });
  value.Children['#Finished'].TimbermeshSpec.Model = `${folder}/${id}.IronTeeth.Model`;
  const options = {dataRoot};
  if (building.kind === 'export' || building.kind === 'outfall') {
    // The template's water outlet, its overhang block and its splash effects
    // belong to the vanilla Discharge model; the study replaces all of them.
    removeComponents(value, ['WaterOutputSpec', 'ManufactoryWaterProducerSpec', 'ManufactoryWaterContaminationProducerSpec',
      'WaterOutputParticleSpec', 'ManufactoryTogglableRecipesSpec', 'WorkshopParticleControllerSpec', 'TemplateAttachmentsSpec'], id);
    if (building.kind === 'export') {
      // The dispatch-gate side (study MAP_EDGE) is fully built on the ground
      // layer, so that side touching the map edge satisfies MapEdgeSiteValidator.
      const edge = await studyString(id, 'MAP_EDGE');
      if (!Object.hasOwn(EDGE_ROWS, edge)) throw new Error(`${id}: MAP_EDGE ${edge} is not a footprint side`);
      const occupied = new Set(registration.occupied.map((c) => c.join()));
      const open = EDGE_ROWS[edge](registration.footprint).filter(([x, y]) => !occupied.has([x, y, 0].join()));
      if (open.length) throw new Error(`${id}: MAP_EDGE ${edge} side has free ground cells ${open.join(' ')}`);
      value.MapEdgeSiteSpec = {};
    } else {
      const release = RADIATION_RECIPES.find(r => r.id === 'ReleaseRadioactiveSludge');
      const [X, Y, Z] = await studyCell(id, 'SLUDGE_OUTPUT');
      value.RadioactiveSludgeOutfallSpec = {
        OutputCoordinates: {X, Y, Z},
        RadioactiveVolumePerCycle: release.ingredients[0][1] * tuning.volumePerGood,
      };
    }
  } else if (building.kind === 'recovery') {
    removeComponents(value, ['ManufactoryWaterContaminationConsumerSpec'], id);
    if (!value.WaterInputSpec || !value.WaterInputPipeSpec) throw new Error(`${id}: recovery pump template needs WaterInputSpec and WaterInputPipeSpec`);
    // The study's strainer stands in its INTAKE cell; the native pipe starts
    // in the column below (WaterInputPipeCoordinates scans down from the cell
    // under WaterInputCoordinates + BaseZ + 1), so that cell must be open.
    const [x, y, z] = await studyCell(id, 'INTAKE');
    value.WaterInputSpec = {...value.WaterInputSpec, WaterInputCoordinates: {X: x, Y: y, Z: z - 1}};
    options.overhangs = [[x, y, z]];
    const recover = RADIATION_RECIPES.find(r => r.id === 'RecoverRadioactiveSludge');
    value.RadioactiveSludgeIntakeSpec = {RadioactiveVolumePerCycle: recover.products[0][1] * tuning.volumePerGood,
      MaxWaterPerCycle: RECOVERY_MAX_WATER_PER_CYCLE};
  } else {
    throw new Error(`${id}: unknown radiation building kind ${building.kind}`);
  }
  value.BuildingPipeTargetPortsSpec = {Ports: [await studyPipePort(id, building.pipe)]};
  // Flippable, blocks, entrance, colliders, construction stage, animation and
  // the study meshes (copied into dataRoot).
  await applyLategame(value, id, options);
  const relative = `${folder}/${id}.IronTeeth.blueprint`;
  await writeJson(resolve(dataRoot, `${relative}.json`), value);
  return relative;
}

export async function waterPerStrengthHour() {
  const tick = (await readJson(resolve(vanillaRoot, 'Configurations', 'TickTime.blueprint.json'))).TickTimeSpec.TickIntervalInSeconds;
  const ticks = (await readJson(resolve(vanillaRoot, 'Configurations', 'DayNightCycle.blueprint.json'))).DayNightCycleSpec.ConfiguredDayLengthInTicks;
  if (!(tick > 0) || !(ticks > 0)) throw new Error('Vanilla TickTimeSpec / DayNightCycleSpec values are missing');
  return tick * ticks / 24;
}

async function makeSpring(spring, dataRoot) {
  const value = clone(await readJson(resolve(vanillaRoot, 'Buildings', 'Water', 'DevWaterSource', 'DevWaterSource.blueprint.json')));
  // Keep the native source and its contamination (0); a badtide must not turn it bad.
  removeComponents(value, ['BadtideWaterSourceContaminationControllerSpec'], spring.id);
  if (value.WaterSourceContaminationSpec?.DefaultContamination !== 0) throw new Error(`${spring.id}: vanilla DevWaterSource contamination is no longer 0`);
  value.WaterSourceSpec = {...value.WaterSourceSpec, DefaultStrength: SPRING_RADIOACTIVE_PER_HOUR / await waterPerStrengthHour()};
  value.TemplateSpec.TemplateName = spring.id;
  value.TemplateSpec.BackwardCompatibleTemplateNames = [];
  Object.assign(value.PlaceableBlockObjectSpec, {ToolGroupId: spring.toolGroup, ToolOrder: spring.toolOrder, DevModeTool: true});
  Object.assign(value.LabeledEntitySpec, {DisplayNameLocKey: `Building.${spring.id}.DisplayName`,
    DescriptionLocKey: `Building.${spring.id}.Description`, FlavorDescriptionLocKey: '', Icon: spring.icon});
  if (value.BlockObjectSpec.Flippable !== true) throw new Error(`${spring.id}: vanilla DevWaterSource is no longer flippable`);
  value.RadioactiveWaterSourceSpec = {...SPRING_SPEC};
  // Own vent model (tools/map_objects.json, build_map_objects.py), shared by the
  // dev tool and the map-editor spring, not the vanilla water source recoloured
  // whole: RadioactiveSpringVisual tints only its RadioactiveGlow node.
  if (value.Children?.['#Model']?.TimbermeshSpec?.Model !== 'MapEditor/Water/WaterSource/WaterSource.Model')
    throw new Error(`${spring.id}: vanilla DevWaterSource no longer binds the water source model at #Model`);
  value.Children['#Model'] = {TimbermeshSpec: {Model: mapObjectModel('RadioactiveSpringSource')}, CollidersSpec: mapObjectCollider('RadioactiveSpringSource')};
  await writeJson(resolve(dataRoot, `${spring.path}.json`), value);
}

async function makeNeed(dataRoot) {
  const value = clone(await readJson(resolve(vanillaRoot, 'Needs', 'Need.Beaver.BadwaterContamination.blueprint.json')));
  Object.assign(value.NeedSpec, {
    Id: NEED, BackwardCompatibleIds: [], Order: 91, DisplayNameLocKey: `Need.${NEED}.DisplayName`,
    StartingValue: 0, MinimumValue: -1, MaximumValue: 0, DailyDelta: 0, UnfavorableWellbeing: -12, FavorableWellbeing: 0,
  });
  // Placeholder status sprite (vanilla badwater contamination) until the
  // requested irradiation status icon is authored.
  Object.assign(value.CriticalNeedSpec, {
    CriticalNeedType: 'Alert', SpriteName: 'BadwaterContamination',
    DescriptionLocKey: `Status.Need.${NEED}`, DescriptionShortLocKey: `Status.Need.${NEED}.Short`,
  });
  const contaminated = value.PunitiveNeedSpec?.Penalties?.find(p => p.Id === 'MovementSpeed')?.MultiplierDelta;
  if (!(ZOMBIE_MOVEMENT_DELTA < contaminated)) throw new Error(`Radioactive zombie MovementSpeed ${ZOMBIE_MOVEMENT_DELTA} must be below vanilla BadwaterContamination ${contaminated}`);
  value.PunitiveNeedSpec = {Penalties: [{Id: 'MovementSpeed', MultiplierDelta: ZOMBIE_MOVEMENT_DELTA}]};
  for (const required of ['NeedPreventingWorkSpec', 'InactiveHiddenNeedSpec'])
    if (!value[required]) throw new Error(`Vanilla BadwaterContamination need lost ${required}`);
  await writeJson(resolve(dataRoot, 'Needs', `Need.Beaver.${NEED}.blueprint.json`), value);
}

// The Hospital's native AttractionSpec does the cure. Rate: the need runs from
// -1 to 0, so 10 days of care need 1/(10*24) points per hour of care. A native
// stay applies effects only every other tick (AttractionNeedBehavior launches
// a 0.05 h ApplyEffectExecutor; the tick on which it completes applies none
// before the next is launched), so divide by the measured treatment duty from
// tools/frontier_progression.json (the same evidence the Injury rate uses).
// That cadence holds for a continuous stay too, so the course is 10 days
// admitted. SatisfyToMaxValue is true like every Hospital effect
// (hospital_building_content.mjs): native MaxValueNeedsAreActive releases a
// patient only when all of them are at their maximum, so the patient stays
// until cured of every condition.
export async function hospitalTreatmentRate(tuning) {
  const progression = await readJson(resolve(root, 'tools', 'frontier_progression.json'));
  const duty = progression?.hospital?.nativeTreatmentEvidence?.observedRepeatVisitTreatmentFraction;
  if (!(duty > 0 && duty <= 1)) throw new Error('frontier_progression.json hospital.nativeTreatmentEvidence.observedRepeatVisitTreatmentFraction is missing or invalid');
  return {duty, pointsPerHour: 1 / (tuning.treatmentDays * 24 * duty)};
}

async function extendHospital(dataRoot, tuning) {
  const path = resolve(dataRoot, 'Buildings', 'Wellbeing', 'Hospital', 'Hospital.IronTeeth.blueprint.json');
  const value = await readJson(path);
  const effects = value?.AttractionSpec?.Effects;
  if (!Array.isArray(effects)) throw new Error(`Hospital blueprint has no AttractionSpec.Effects: ${path}`);
  if (effects.some(e => e.NeedId === NEED)) throw new Error('Hospital already treats Irradiation');
  if (!effects.some(e => e.NeedId === 'BadwaterContamination')) throw new Error('Hospital blueprint no longer treats BadwaterContamination; check the hospital generator before adding Irradiation');
  if (!effects.every(e => e.SatisfyToMaxValue === true)) throw new Error('Hospital effects must all SatisfyToMaxValue (admitted until cured); check the hospital generator');
  const {pointsPerHour} = await hospitalTreatmentRate(tuning);
  effects.push({NeedId: NEED, PointsPerHour: pointsPerHour, SatisfyToMaxValue: true});
  await writeJson(path, value);
}

async function appendCollection(path, specName, field, values) {
  const value = await readJson(path);
  if (!value[specName]) throw new Error(`${path} has no ${specName}`);
  appendUnique(value[specName][field], values, `${path} ${field}`);
  await writeJson(path, value);
}

async function appendLocalization(dataRoot) {
  const path = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const text = await readFile(path, 'utf8').catch(() => { throw new Error(`Radiation content target is missing: ${path}`); });
  const ids = new Set(text.split(/\r?\n/).map(line => line.split(',')[0]));
  for (const [id] of LOCALIZATION) if (ids.has(id)) throw new Error(`enUS.csv already defines ${id}`);
  const rows = LOCALIZATION.map(([id, value]) => [id, value, 'Deep Frontier'].map(csvCell).join(','));
  await writeFile(path, `${text.endsWith('\n') ? text : `${text}\n`}${rows.join('\n')}\n`, 'utf8');
}

export async function applyRadiationContent(dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')) {
  const tuning = await readTuning();
  if (tuning.volumePerGood !== VOLUME_PER_GOOD) throw new Error('RadiationTuning.VolumePerGood differs from the content module');
  for (const good of GOODS) await makeGood(good, dataRoot);
  for (const recipe of RADIATION_RECIPES) await makeRecipe(recipe, dataRoot);
  const buildingPaths = [];
  for (const building of RADIATION_BUILDINGS) buildingPaths.push(await makeBuilding(building, dataRoot, tuning));
  for (const spring of RADIATION_SPRINGS) await makeSpring(spring, dataRoot);
  buildingPaths.push(...RADIATION_SPRINGS.filter(s => s.collection === 'buildings').map(s => s.path));
  await makeNeed(dataRoot);
  await extendHospital(dataRoot, tuning);
  await appendCollection(resolve(dataRoot, 'GoodCollections', 'GoodCollection.IronTeeth.blueprint.json'), 'GoodCollectionSpec', 'Goods#append', GOODS.map(g => g.id));
  await appendCollection(resolve(dataRoot, 'NeedCollections', 'NeedCollection.IronTeeth.blueprint.json'), 'NeedCollectionSpec', 'Needs#append', [NEED]);
  await appendCollection(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'), 'TemplateCollectionSpec', 'Blueprints#append', buildingPaths);
  await appendCollection(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.MapEditor.Common.blueprint.json'), 'TemplateCollectionSpec', 'Blueprints#append',
    RADIATION_SPRINGS.filter(s => s.collection === 'mapEditor').map(s => s.path));
  await appendLocalization(dataRoot);
  await createRadiationIcons(dataRoot);
  return {goods: GOODS.length, recipes: RADIATION_RECIPES.length, buildings: buildingPaths.length};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  const result = await applyRadiationContent(dataRoot);
  console.log(`Radiation content applied: ${result.goods} goods, ${result.recipes} recipes, ${result.buildings} buildings, need ${NEED}, hospital treatment.`);
}
