// Static validator for the Deep Well (tools/deep_well_content.json,
// tools/deep_well_content.mjs, src/DeepFrontier/Scripts/DeepWell).
//
//   node tools/validate_deep_well_content.mjs [dataRoot]
//
// Checks the generated blueprint against the config and the native
// Timberborn 1.1.2.8 contracts the design rests on (source blocks, seep
// modifier, source strength cap, floodable and goods-consuming specs), the
// cost against the late-game rule, the localization rows and the C# contract.
import {access, readFile, readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {ANCHOR_BLOCK, CONFIG, DRILL_CELL, FULL_BOOST_RATE, HANGING_BLOCK, ICON_PATH, ID, LOCALIZATION, TEMPLATE_PATH} from './deep_well_content.mjs';
import {catalog, lategameCost, tierForScience} from './lategame_costs.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const errors = [];
const check = (ok, message) => { if (!ok) errors.push(message); };

// --- native contracts the design rests on (vanilla blueprints) -----------
const strengthFiles = [];
async function walk(dir) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) await walk(path);
    else if (entry.name.endsWith('.blueprint.json')) strengthFiles.push(path);
  }
}
await walk(resolve(vanillaRoot, 'Configurations'));
const strengthSpecs = [];
for (const path of strengthFiles) {
  const value = await readJson(path);
  if (value.WaterStrengthSpec) strengthSpecs.push(value.WaterStrengthSpec);
}
check(strengthSpecs.length === 1 && strengthSpecs[0].MaxWaterSourceStrength === CONFIG.maxWaterSourceStrengthPerCell,
  `native WaterStrengthSpec.MaxWaterSourceStrength is not the configured ${CONFIG.maxWaterSourceStrengthPerCell} per cell`);
const sources = {
  WaterSource: 'MapEditor/Water/WaterSource/WaterSource.blueprint.json',
  BadwaterSource: 'MapEditor/Water/BadwaterSource/BadwaterSource.blueprint.json',
  WaterSeep: 'MapEditor/Water/WaterSeep/WaterSeep.blueprint.json',
  BadwaterSeep: 'MapEditor/Water/BadwaterSeep/BadwaterSeep.blueprint.json',
};
const occupationFlags = (text) => text === 'All' ? ['Floor', 'Bottom', 'Top', 'Corners', 'Path', 'Middle'] : text === 'None' ? [] : text.split(', ');
for (const [name, path] of Object.entries(sources)) {
  const value = await readJson(resolve(vanillaRoot, path));
  check(value.WaterSourceSpec && value.BlockObjectSpec.Blocks.every((b) => b.Stackable === 'None'),
    `${name}: the design assumes a native water source whose blocks are not stackable`);
  const multi = value.WaterSourceSpec.Coordinates.length > 1;
  // Multi-cell sources leave Top free, so the anchor (Top) may stand on them.
  if (multi) check(value.BlockObjectSpec.Blocks.every((b) => !occupationFlags(b.Occupations).includes('Top')),
    `${name}: a multi-cell source must leave Top free for the Deep Well anchor`);
  check(Boolean(value.WaterDepthStrengthModifierSpec) === name.endsWith('Seep'), `${name}: only seeps carry WaterDepthStrengthModifierSpec`);
}

// --- blueprint ------------------------------------------------------------
const path = resolve(dataRoot, `${TEMPLATE_PATH}.json`);
check(await exists(path), `${TEMPLATE_PATH}.json is missing`);
if (await exists(path)) {
  const bp = await readJson(path);
  for (const key of ['FloodableBuildingSpec', 'FloodableObjectSpec', 'WorkplaceSpec', 'UnderstructureConstraintSpec',
    'UndergroundWaterSourceDrillSpec', 'PoweredGoodConsumingBuildingSpec', 'AmbientAnimationSpec', 'MechanicalNodeAnimatorSpec',
    'WorkshopSpec', 'ManufactorySpec'])
    check(!bp[key], `${ID}: must not carry ${key}`);
  for (const key of ['FloodableObjectBlockerSpec', 'BuildingAccessibleSpec', 'MechanicalBuildingSpec', 'DeepWellSpec'])
    check(bp[key], `${ID}: needs ${key}`);
  check(same(bp.MechanicalNodeSpec, {PowerOutput: 0, PowerInput: CONFIG.powerInputHp, IsShaft: false}), `${ID}: MechanicalNodeSpec must be a ${CONFIG.powerInputHp} hp consumer`);
  const goods = bp.GoodConsumingBuildingSpec;
  check(goods && same(goods.ConsumedGoods, [{GoodId: CONFIG.drillBits.good, GoodPerHour: FULL_BOOST_RATE}])
    && goods.FullInventoryWorkHours === CONFIG.drillBits.fullInventoryWorkHours,
    `${ID}: GoodConsumingBuildingSpec must consume only ${CONFIG.drillBits.good} at the full-boost rate ${FULL_BOOST_RATE}/h`);
  check(same(bp.DeepWellSpec, {DrillCell: {X: DRILL_CELL[0], Y: DRILL_CELL[1], Z: DRILL_CELL[2]}, MaxBoost: CONFIG.maxBoost,
    DefaultBoost: CONFIG.defaultBoost, DefaultShutOffDuringTide: CONFIG.defaultShutOffDuringTide,
    DrillBitGoodId: CONFIG.drillBits.good, DrillBitsPerBoostStepPerHour: CONFIG.drillBits.perBoostStepPerHour}), `${ID}: DeepWellSpec differs from the config`);
  check(CONFIG.defaultBoost >= 1 && CONFIG.defaultBoost <= CONFIG.maxBoost, `${ID}: default boost outside 1..${CONFIG.maxBoost}`);
  const {X: w, Y: h, Z: layers} = bp.BlockObjectSpec.Size;
  check(Math.min(w, h) <= 2 && Math.max(w, h) <= 4, `${ID}: footprint ${w}×${h} is larger than 2×4`);
  const blocks = bp.BlockObjectSpec.Blocks;
  check(blocks.length === w * h * layers, `${ID}: ${blocks.length} blocks for a ${w}×${h}×${layers} size`);
  const block = ([x, y, z]) => blocks[(z * h + y) * w + x];
  check(same(block(DRILL_CELL), HANGING_BLOCK), `${ID}: the drill cell ${DRILL_CELL} must hang (MatterBelow Any, Occupations None)`);
  check(block([DRILL_CELL[0], DRILL_CELL[1], 1])?.Occupations === 'All', `${ID}: the derrick must stand over the drill cell`);
  let anchors = 0;
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    if (x === DRILL_CELL[0] && y === DRILL_CELL[1]) continue;
    const b = block([x, y, 0]);
    if (b.Occupations === 'None') continue;
    check(same(b, ANCHOR_BLOCK), `${ID}: ground cell ${[x, y, 0]} must be the Top anchor on GroundOrStackable`);
    anchors++;
  }
  check(anchors > 0, `${ID}: nothing carries the hanging drill`);
  for (const b of blocks) check(b.Stackable === 'None', `${ID}: no Deep Well block may be stackable`);
  const entrance = bp.BlockObjectSpec.Entrance;
  check(entrance.HasEntrance && !(entrance.Coordinates.X >= 0 && entrance.Coordinates.X < w && entrance.Coordinates.Y >= 0 && entrance.Coordinates.Y < h),
    `${ID}: the entrance must be a path cell outside the footprint`);
  check(same(bp.BuildingSpec.BuildingCost, (await lategameCost(ID)).map(([Id, Amount]) => ({Id, Amount}))), `${ID}: BuildingCost differs from the late-game rule`);
  check(bp.BuildingSpec.ScienceCost === CONFIG.science && tierForScience(CONFIG.science) === catalog.lategameTier[ID],
    `${ID}: science ${CONFIG.science} lies outside tier ${catalog.lategameTier[ID]}`);
  check(bp.PlaceableBlockObjectSpec.ToolGroupId === CONFIG.toolGroup && bp.PlaceableBlockObjectSpec.ToolOrder === CONFIG.toolOrder && !bp.PlaceableBlockObjectSpec.DevModeTool,
    `${ID}: tool group or order differs from the config`);
  check(bp.LabeledEntitySpec.Icon === ICON_PATH && await exists(resolve(dataRoot, `${ICON_PATH}.png`)), `${ID}: icon ${ICON_PATH}.png missing`);
  for (const child of ['#Finished', '#Unfinished']) check(bp.Children[child], `${ID}: ${child} model missing`);
  check(!bp.Children['#Underground'], `${ID}: no underground model`);
  for (const model of [bp.Children['#Finished'].TimbermeshSpec.Model, bp.Children['#Unfinished'].Children.ConstructionStage0.TimbermeshSpec.Model])
    check(await exists(resolve(dataRoot, `${model}.timbermesh`)), `${ID}: ${model}.timbermesh missing`);
}
const collection = await readJson(resolve(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'));
check(collection.TemplateCollectionSpec['Blueprints#append'].filter((p) => p === TEMPLATE_PATH).length === 1, `${TEMPLATE_PATH} must be listed once in the Iron Teeth building collection`);

// --- localization ---------------------------------------------------------
const csv = await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8');
const rows = new Map(csv.split(/\r?\n/).map((line) => [line.split(',')[0], line]));
for (const [id] of LOCALIZATION) check(rows.has(id), `enUS.csv lacks ${id}`);

// --- C# contract ----------------------------------------------------------
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'DeepWell');
const cs = (await Promise.all((await readdir(scripts)).filter((f) => f.endsWith('.cs')).map((f) => readFile(resolve(scripts, f), 'utf8')))).join('\n');
const spec = cs.match(/record DeepWellSpec : ComponentSpec \{([\s\S]*?)\n  \}/);
check(spec && same([...spec[1].matchAll(/\[Serialize\] public \S+ (\w+) \{ get; init; \}/g)].map((m) => m[1]),
  ['DrillCell', 'MaxBoost', 'DefaultBoost', 'DefaultShutOffDuringTide', 'DrillBitGoodId', 'DrillBitsPerBoostStepPerHour']), 'C#: DeepWellSpec properties differ from the blueprint');
const locIds = new Set(LOCALIZATION.map(([id]) => id));
for (const [, key] of cs.matchAll(/public const string \w+ = "(DeepFrontier\.DeepWell\.[\w.]+)";/g))
  if (!key.endsWith('.')) check(locIds.has(key), `C#: loc key ${key} has no localization row`);
const states = cs.match(/enum DeepWellState \{([^}]*)\}/);
check(states, 'C#: DeepWellState not found');
if (states) for (const state of states[1].split(',').map((s) => s.trim()).filter(Boolean))
  check(locIds.has(`DeepFrontier.DeepWell.State.${state}`), `C#: state ${state} has no localization row`);
for (const line of ['MultiBind<IBlockObjectValidator>().To<DeepWellPlacementValidator>().AsSingleton()', 'AddDecorator<DeepWellSpec, DeepWell>()',
  'Bind<DeepWellRegistry>().AsSingleton()', '[Context("Game")]', 'RadioactiveTideTuning.WeatherId'])
  check(cs.includes(line), `C#: DeepWell lacks ${line}`);
// The placement message must reach the preview: the validator returns it.
check(/errorMessage = _loc\.T\(DeepWellLoc\.NoSource\)/.test(cs), 'C#: the placement validator must report the missing source');

if (errors.length) {
  console.error(`Deep Well validation failed (${errors.length}):\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log(`Deep Well content valid: ${TEMPLATE_PATH}, drill ${DRILL_CELL}, ${CONFIG.powerInputHp} hp at ${CONFIG.maxBoost}x, ${CONFIG.drillBits.perBoostStepPerHour} ${CONFIG.drillBits.good}/h per step.`);
