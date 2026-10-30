// Deep Well (tools/deep_well_content.json; runtime Scripts/DeepWell/DeepWell.cs).
//
// A powered, worker-free building that boosts the native map water source
// under its DRILL cell (tools/asset-pipeline/lategame_DeepWell.py): a 1x1
// Water/Badwater Source, a cell of a Water/Badwater Seep or of a 3x3 Badwater
// Source. Timberborn 1.1.2.8 placement contract (decompiled):
// - every source block is Stackable None and the 1x1 sources occupy All, so
//   nothing can stand on a source or share a 1x1 source's cell
//   (MatterBelowValidator, BlockValidator.BlockConflictsWithExistingObject);
// - so the drill block is MatterBelow Any / Occupations None: it hangs over
//   the source from the anchor cell and conflicts with no source occupation;
// - the anchor (every other ground-layer cell) is Top on GroundOrStackable:
//   it stands on ground, and on a seep or badwater-source cell, whose Top is
//   free (the vanilla Badwater Pressurizer's occupation over its source);
// - the native understructure system cannot bind a source through a None
//   block (UnderstructureFinder reads Top/Corners foundation blocks), so the
//   runtime's DeepWellPlacementValidator requires the source (message in the
//   placement preview) and DeepWell links it.
// Waterproof with deliveries: BuildingAccessibleSpec (haulers fill the native
// GoodConsumingBuilding; no workplace) adds the native floodable components,
// and FloodableObjectBlockerSpec keeps them from ever flooding (vanilla Tubeway
// Station and Resource Counter). No FloodableBuildingSpec, no WorkplaceSpec.
// PoweredGoodConsumingBuildingSpec is not used: it sets the node's input
// multiplier to 0 or 1 every tick (MechanicalBuilding.SetConsumptionDisabled),
// which would override the boost-scaled demand; DeepWell does its job.
//
// Runs in canonical generation after radiation_content.mjs (before workforce
// risks, connections, sounds and the automation audit), or standalone on a
// generated Data root: node tools/deep_well_content.mjs [dataRoot]
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {LATEGAME, applyLategame, studyCell} from './lategame_building_content.mjs';
import {lategameCost} from './lategame_costs.mjs';
import {writeNativeIcon} from './native_icon_style.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const clone = (value) => JSON.parse(JSON.stringify(value));
const csvCell = (value) => {
  if (typeof value !== 'string') throw new TypeError('Localization cells must be authored strings.');
  return /[",\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
};

export const CONFIG = await readJson(resolve(root, 'tools', 'deep_well_content.json'));
export const ID = CONFIG.id;
export const TEMPLATE_PATH = `${CONFIG.folder}/${ID}.IronTeeth.blueprint`;
export const ICON_PATH = `${CONFIG.folder}/${ID}Icon`;
export const DRILL_CELL = await studyCell(ID, 'DRILL');
// Decimal rate (0.05 x 6 = 0.3, not the binary product 0.30000000000000004).
export const FULL_BOOST_RATE = Number((CONFIG.drillBits.perBoostStepPerHour * CONFIG.maxBoost).toFixed(6));
// The blocks the runtime and the validator rely on.
export const HANGING_BLOCK = {MatterBelow: 'Any', Occupations: 'None', Stackable: 'None', OccupyAllBelow: false, Underground: false};
export const ANCHOR_BLOCK = {MatterBelow: 'GroundOrStackable', Occupations: 'Top', Stackable: 'None', OccupyAllBelow: false, Underground: false};

const hp = (value) => value.toLocaleString('en-US');
const rate = CONFIG.drillBits.perBoostStepPerHour;
export const LOCALIZATION = [
  [`Building.${ID}.DisplayName`, 'Deep Well'],
  [`Building.${ID}.Description`, `Stands with its drill over a water source, water seep or badwater source and drives the source harder while powered: up to ${CONFIG.maxBoost}× its flow, at most ${CONFIG.maxWaterSourceStrengthPerCell} per source cell. A seep flows like a normal source, and the source keeps flowing through droughts. Draws ${hp(Math.ceil(CONFIG.powerInputHp / CONFIG.maxBoost))} hp at 1×, rising with the boost to ${hp(CONFIG.powerInputHp)} hp at ${CONFIG.maxBoost}×, and wears out ${rate} high-grade steel drill bits per hour per step. No workers; haulers bring the steel. Waterproof.`],
  [`Building.${ID}.FlavorDescription`, 'When the river runs dry, drill deeper.'],
  ['DeepFrontier.DeepWell.Placement.NoSource', 'The drill must stand over a water source, water seep or badwater source.'],
  ['DeepFrontier.DeepWell.Placement.SourceTaken', 'Another Deep Well already drives this water source.'],
  ['DeepFrontier.DeepWell.Placement.SourceControlled', 'A building on this water source already controls it.'],
  ['DeepFrontier.DeepWell.Status.NoDrillBits', 'No drill bits: the well needs high-grade steel to drive its source.'],
  ['DeepFrontier.DeepWell.Status.NoDrillBits.Short', 'No drill bits'],
  ['DeepFrontier.DeepWell.Status.NoSource', 'The water source under the drill is gone.'],
  ['DeepFrontier.DeepWell.Status.NoSource.Short', 'No water source'],
  ['DeepFrontier.DeepWell.Panel.Title', 'Deep well'],
  ['DeepFrontier.DeepWell.Panel.Boost', 'Source boost'],
  ['DeepFrontier.DeepWell.Panel.BoostValue', '{0}×'],
  ['DeepFrontier.DeepWell.Panel.ShutOffDuringTide', 'Shut the source off during the radioactive tide'],
  ['DeepFrontier.DeepWell.Panel.Demand', 'Power at this boost: {0} hp'],
  ['DeepFrontier.DeepWell.Panel.DrillBits', 'Drill bits: {0} per hour, {1} hours in stock'],
  ['DeepFrontier.DeepWell.Panel.Source', 'Source strength: {0} set, {1} now'],
  ['DeepFrontier.DeepWell.Panel.Seep', 'A seep: while the well runs it pours like a normal source.'],
  ['DeepFrontier.DeepWell.Panel.Capped', `Limited by the source maximum of ${CONFIG.maxWaterSourceStrengthPerCell} per cell.`],
  ['DeepFrontier.DeepWell.State.UnderConstruction', 'Under construction.'],
  ['DeepFrontier.DeepWell.State.NoSource', 'No water source under the drill.'],
  ['DeepFrontier.DeepWell.State.Paused', 'Paused: the source flows as normal.'],
  ['DeepFrontier.DeepWell.State.TideShutOff', 'Shut off for the radioactive tide: the source is closed.'],
  ['DeepFrontier.DeepWell.State.SourceDormant', 'The source has not started flowing yet.'],
  ['DeepFrontier.DeepWell.State.NoDrillBits', 'Waiting for drill bits: the source flows as normal.'],
  ['DeepFrontier.DeepWell.State.NoPower', 'No power: the source flows as normal.'],
  ['DeepFrontier.DeepWell.State.Boosting', 'Driving the source at {0}×.'],
];

function removeSpecs(value, keys) {
  for (const key of keys) {
    if (!Object.hasOwn(value, key)) throw new Error(`${ID}: template spec ${key} is missing`);
    delete value[key];
  }
}

export async function deepWellBlueprint(dataRoot) {
  if (!LATEGAME.has(ID)) throw new Error(`${ID}: its study is not integrated (tools/lategame_batches.json)`);
  const value = clone(await readJson(resolve(vanillaRoot, CONFIG.template)));
  removeSpecs(value, CONFIG.templateSpecsRemoved);
  for (const key of ['FloodableBuildingSpec', 'FloodableObjectSpec', 'WorkplaceSpec', 'BuildingAccessibleSpec'])
    if (value[key]) throw new Error(`${ID}: template ${CONFIG.template} carries ${key}`);
  value.BuildingModelSpec = {...value.BuildingModelSpec, UndergroundModelName: '', UndergroundModelDepth: 0};
  delete value.Children['#Underground'];
  value.BuildingSpec = {...value.BuildingSpec,
    BuildingCost: (await lategameCost(ID, CONFIG.science)).map(([Id, Amount]) => ({Id, Amount})), ScienceCost: CONFIG.science};
  value.TemplateSpec = {...value.TemplateSpec, TemplateName: `${ID}.IronTeeth`, BackwardCompatibleTemplateNames: []};
  value.PlaceableBlockObjectSpec = {...value.PlaceableBlockObjectSpec, ToolGroupId: CONFIG.toolGroup, ToolOrder: CONFIG.toolOrder, DevModeTool: false};
  value.LabeledEntitySpec = {...value.LabeledEntitySpec, DisplayNameLocKey: `Building.${ID}.DisplayName`,
    DescriptionLocKey: `Building.${ID}.Description`, FlavorDescriptionLocKey: `Building.${ID}.FlavorDescription`, Icon: ICON_PATH};
  value.MechanicalNodeSpec = {PowerOutput: 0, PowerInput: CONFIG.powerInputHp, IsShaft: false};
  value.Children['#Finished'].TimbermeshSpec.Model = `${CONFIG.folder}/${ID}.IronTeeth.Model`;
  value.GoodConsumingBuildingSpec = {FullInventoryWorkHours: CONFIG.drillBits.fullInventoryWorkHours,
    ConsumedGoods: [{GoodId: CONFIG.drillBits.good, GoodPerHour: FULL_BOOST_RATE}]};
  value.FloodableObjectBlockerSpec = {};
  value.DeepWellSpec = {DrillCell: {X: DRILL_CELL[0], Y: DRILL_CELL[1], Z: DRILL_CELL[2]}, MaxBoost: CONFIG.maxBoost,
    DefaultBoost: CONFIG.defaultBoost, DefaultShutOffDuringTide: CONFIG.defaultShutOffDuringTide,
    DrillBitGoodId: CONFIG.drillBits.good, DrillBitsPerBoostStepPerHour: CONFIG.drillBits.perBoostStepPerHour};
  // Blocks, entrance and access point, colliders, construction stage, meshes.
  const result = await applyLategame(value, ID, {dataRoot});
  // DeepWell plays the study's machinery only while it boosts.
  removeSpecs(value, ['AmbientAnimationSpec']);
  const [w, h] = [result.size[0], result.size[1]];
  const blocks = value.BlockObjectSpec.Blocks;
  const [dx, dy, dz] = DRILL_CELL;
  if (dz !== 0 || dx < 0 || dy < 0 || dx >= w || dy >= h) throw new Error(`${ID}: DRILL ${DRILL_CELL} is not a ground-layer cell of the ${w}×${h} footprint`);
  if ([result.entrance, result.doorstep].some((c) => c.join() === DRILL_CELL.join())) throw new Error(`${ID}: DRILL ${DRILL_CELL} is a door cell`);
  let anchors = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const block = blocks[y * w + x];
    if (x === dx && y === dy) {
      if (block.Occupations !== 'All') throw new Error(`${ID}: the drill cell is not a building cell of the study`);
      Object.assign(block, HANGING_BLOCK);
    } else if (block.Occupations !== 'None') {
      Object.assign(block, ANCHOR_BLOCK);
      anchors++;
    }
  }
  if (!anchors) throw new Error(`${ID}: no ground cell carries the hanging drill`);
  if (blocks[(1 * h + dy) * w + dx]?.Occupations !== 'All') throw new Error(`${ID}: the derrick does not stand over the drill cell`);
  return value;
}

async function appendTemplate(dataRoot) {
  const path = resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json');
  const collection = await readJson(path);
  const list = collection.TemplateCollectionSpec['Blueprints#append'];
  if (!Array.isArray(list)) throw new Error(`${path}: Blueprints#append is not a list`);
  if (list.includes(TEMPLATE_PATH)) throw new Error(`${path} already lists ${TEMPLATE_PATH}`);
  list.push(TEMPLATE_PATH);
  await writeJson(path, collection);
}

async function appendLocalization(dataRoot) {
  const path = resolve(dataRoot, 'Localizations', 'enUS.csv');
  const text = await readFile(path, 'utf8');
  const ids = new Set(text.split(/\r?\n/).map((line) => line.split(',')[0]));
  for (const [id] of LOCALIZATION) if (ids.has(id)) throw new Error(`enUS.csv already defines ${id}`);
  const rows = LOCALIZATION.map(([id, value]) => [id, value, 'Deep Frontier'].map(csvCell).join(','));
  await writeFile(path, `${text.endsWith('\n') ? text : `${text}\n`}${rows.join('\n')}\n`, 'utf8');
}

export async function applyDeepWell(dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')) {
  const value = await deepWellBlueprint(dataRoot);
  await writeJson(resolve(dataRoot, `${TEMPLATE_PATH}.json`), value);
  await appendTemplate(dataRoot);
  await appendLocalization(dataRoot);
  const svg = await readFile(resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', `${ID}.svg`));
  await writeNativeIcon(svg, 'building', resolve(dataRoot, `${ICON_PATH}.png`), ID);
  return {template: TEMPLATE_PATH, cost: value.BuildingSpec.BuildingCost};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await applyDeepWell(process.argv[2] ? resolve(process.argv[2]) : undefined);
  console.log(`Deep Well content applied: ${result.template}, cost ${result.cost.map((c) => `${c.Amount} ${c.Id}`).join(', ')}.`);
}
