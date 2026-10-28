// Cryogenic fuel storage behaviour for the Cryogenic Tank Farm
// (runtime: src/DeepFrontier/Scripts/Cryogenics).
//
// Called last from tools/create_frontier_expansion_content.mjs, after every
// building blueprint has been written:
//   await (await import('./cryogenic_content.mjs')).applyCryogenics();
// or standalone (use a scratch copy to test):
//   node tools/cryogenic_content.mjs [dataRoot]
//
// The building itself (model, footprint, LargeTank-derived liquid Stockpile,
// 2,000 capacity, 1,000 hp MechanicalNode, costs, unlock) is owned by the
// building integration. This module adds behaviour to that template only:
// - CryogenicTankSpec {Goods, VentPerHourOnPowerLoss, BufferHours}.
// - Timber Pipes BuildingPipeSpec.Ports from the study's PIPE_SOCKETS
//   (tools/asset-pipeline/lategame_CryogenicTankFarm.py), each 'Open'.
//   Timber Pipes 11.4.0 decorates every Stockpile with TankPipe; a Liquid
//   stockpile becomes an in-network PipeTank whose ports come from an explicit
//   BuildingPipeSpec, or else from every exposed face (BuildingPipe.ResolveSpec).
//   BuildingPipeTargetPortsSpec is ignored on such a tank
//   (DefaultBuildingConnectionProvider returns null when isAlreadyPipe), so it
//   must not be authored. Port states are static per template while the farm's
//   good is the native stockpile selection, so both sockets are Open (fill and
//   draw on one port, as TankPipe does for vanilla tanks); a foreign network
//   at either socket fails visibly (Timber Pipes contamination plus the tank's
//   wrong-network status).
// - Localizations/enUS_cryogenics.csv (module-owned, rewritten every run).
//
// TANK_FARM.status follows the smog scrubber pattern: 'awaiting-template'
// requires that no CryogenicTankFarm.IronTeeth blueprint exists yet;
// 'ready' requires it and applies the behaviour. Either mismatch throws, as do
// a changed study socket list, a socket on a free cell or with its outward
// cell inside the building, missing or non-Liquid goods, a template that is
// not a powered Liquid stockpile, and specs already present (run once on
// freshly generated blueprints).
import {mkdir, readdir, readFile, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));

export const TANK_FARM = {
  status: 'ready',
  template: 'CryogenicTankFarm',
  study: 'tools/asset-pipeline/lategame_CryogenicTankFarm.py',
  registration: 'outputs/lategame-studies/CryogenicTankFarm-registration.json',
  // Native single-good selection chooses one of these per farm.
  goods: ['LiquidHydrogen', 'LiquidOxygen'],
  // Hours without power (or paused / automation Off) before venting starts.
  bufferHours: 12,
  // Units of the stored fuel vented per hour once the buffer is exhausted.
  ventPerHourOnPowerLoss: 4,
  socketState: 'Open',
};
export const STATUSES = ['awaiting-template', 'ready'];
export const SPEC_KEYS = ['Goods', 'VentPerHourOnPowerLoss', 'BufferHours'];
// Owned here; the integration must not author them on the template.
export const MODULE_SPECS = ['CryogenicTankSpec', 'BuildingPipeSpec'];
export const IGNORED_ON_TANKS = ['BuildingPipeTargetPortsSpec'];
export const LOCALIZATION_FILE = 'Localizations/enUS_cryogenics.csv';
// Panel text used by src/DeepFrontier/Scripts/Cryogenics (CryogenicLoc keys;
// placeholder counts are validated against the _loc.T calls).
export const CRYOGENIC_LOCALIZATION = [
  ['DeepFrontier.Cryogenics.Status.Holding', 'No power: fuel intake is closed. Stored fuel starts venting {0} hours after the power fails unless power returns.'],
  ['DeepFrontier.Cryogenics.Status.Venting', 'Venting cryogenic fuel: {0} units are lost every hour until power returns.'],
  ['DeepFrontier.Cryogenics.Status.Venting.Short', 'Venting cryogenic fuel'],
  ['DeepFrontier.Cryogenics.Status.WrongGood', 'Stores only one of: {0}. Select one of them; nothing else is accepted.'],
  ['DeepFrontier.Cryogenics.Status.WrongNetwork', 'A connected pipe network carries a different fuel or is contaminated and cannot exchange fuel with this tank farm. Liquid hydrogen and liquid oxygen need separate pipe networks; flush contaminated pipes.'],
  ['DeepFrontier.Cryogenics.Status.WrongNetwork.Short', 'Wrong fuel network'],
  ['DeepFrontier.Cryogenics.Notification.Venting', '{0} lost power and is venting cryogenic fuel.'],
  ['DeepFrontier.Cryogenics.Describe.Rules', 'Cryogenic storage: accepts fuel only while powered. Without power, intake closes at once and stored fuel vents {1} units per hour after {0} hours.'],
  ['DeepFrontier.Cryogenics.Describe.Holding', 'No power: intake closed. Venting starts in {0} hours.'],
  ['DeepFrontier.Cryogenics.Describe.Venting', 'Venting {0} units per hour; {1} lost since the power failed.'],
];
// Timberborn Direction3D grid offsets (x, y, z with z up).
export const DIRECTION_OFFSETS = {Left: [-1, 0, 0], Right: [1, 0, 0], Down: [0, -1, 0], Up: [0, 1, 0], Bottom: [0, 0, -1], Top: [0, 0, 1]};

const fail = (message) => { throw new Error(`cryogenics: ${message}`); };
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const csvCell = (text) => {
  if (typeof text !== 'string') fail('localization cells must be strings');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

export function validateTankFarmConfig(c = TANK_FARM) {
  const keys = ['status', 'template', 'study', 'registration', 'goods', 'bufferHours', 'ventPerHourOnPowerLoss', 'socketState'];
  if (Object.keys(c).sort().join() !== [...keys].sort().join()) fail(`TANK_FARM keys must be exactly [${keys}]`);
  if (!STATUSES.includes(c.status)) fail(`TANK_FARM.status must be one of ${STATUSES}`);
  if (!Array.isArray(c.goods) || !c.goods.length || new Set(c.goods).size !== c.goods.length) fail('TANK_FARM.goods must be unique good ids');
  if (!(c.bufferHours > 0) || !(c.ventPerHourOnPowerLoss > 0)) fail('bufferHours and ventPerHourOnPowerLoss must be positive');
  if (c.socketState !== 'Open') fail('socketState must be Open (fill and draw on one socket; the farm good is a runtime selection)');
  return c;
}

export function cryogenicTankSpec(c = TANK_FARM) {
  return {Goods: [...c.goods], VentPerHourOnPowerLoss: c.ventPerHourOnPowerLoss, BufferHours: c.bufferHours};
}

// PIPE_SOCKETS from the study source: [{cell: [x, y, z], direction, good}].
export async function readStudySockets(root = defaultRoot, c = TANK_FARM) {
  const text = await readFile(resolve(root, c.study), 'utf8');
  const block = text.match(/^PIPE_SOCKETS = \(\r?\n([\s\S]*?)\r?\n\)/m);
  if (!block) fail(`${c.study}: PIPE_SOCKETS tuple not found`);
  const lines = block[1].split(/\r?\n/).filter((line) => line.trim());
  const sockets = lines.map((line) => {
    const m = line.match(/^\s*\{'cell': \[(-?\d+), (-?\d+), (-?\d+)\], 'direction': '(\w+)', 'good': '(\w+)', 'socket': \[[^\]]+\]\},?\s*$/);
    if (!m) fail(`${c.study}: unrecognised PIPE_SOCKETS entry: ${line.trim()}`);
    return {cell: [Number(m[1]), Number(m[2]), Number(m[3])], direction: m[4], good: m[5]};
  });
  for (const s of sockets) if (!Object.hasOwn(DIRECTION_OFFSETS, s.direction)) fail(`${c.study}: socket direction ${s.direction} is not a Direction3D`);
  const goods = sockets.map((s) => s.good);
  if (new Set(goods).size !== goods.length || goods.slice().sort().join() !== [...c.goods].sort().join())
    fail(`${c.study}: socket goods [${goods}] must be exactly one per TANK_FARM good [${c.goods}]`);
  const cells = sockets.map((s) => `${s.cell}:${s.direction}`);
  if (new Set(cells).size !== cells.length) fail(`${c.study}: duplicate socket port`);
  return sockets;
}

export function socketPorts(sockets, c = TANK_FARM) {
  return sockets.map(({cell: [X, Y, Z], direction}) => ({Coordinates: {X, Y, Z}, Directions: direction, State: c.socketState}));
}

// Socket cells are occupied in the study registration; the outward cell (where
// the pipe goes) is not.
export async function checkRegistrationSockets(root, sockets, c = TANK_FARM) {
  const registration = await readJson(resolve(root, c.registration));
  if (registration.ident !== c.template) fail(`${c.registration}: ident ${registration.ident} is not ${c.template}`);
  const occupied = new Set(registration.occupied.map((cell) => cell.join(',')));
  for (const s of sockets) {
    if (!occupied.has(s.cell.join(','))) fail(`${c.registration}: ${s.good} socket cell ${s.cell} is not an occupied building cell`);
    const outward = s.cell.map((v, i) => v + DIRECTION_OFFSETS[s.direction][i]);
    if (occupied.has(outward.join(','))) fail(`${c.registration}: ${s.good} socket faces ${s.direction} into building cell ${outward}`);
  }
  return registration;
}

// The same rule against the generated blueprint's own block grid
// (BlockObjectSpec.Blocks, x fastest, then y, then z).
export function checkBlueprintSockets(blueprint, sockets, id) {
  const {Size: {X: w, Y: h, Z: layers}, Blocks: blocks} = blueprint.BlockObjectSpec;
  if (blocks.length !== w * h * layers) fail(`${id}: BlockObjectSpec has ${blocks.length} blocks for size ${w}x${h}x${layers}`);
  const inside = ([x, y, z]) => x >= 0 && y >= 0 && z >= 0 && x < w && y < h && z < layers;
  const solid = (cell) => inside(cell) && blocks[(cell[2] * h + cell[1]) * w + cell[0]].Occupations !== 'None';
  for (const s of sockets) {
    if (!solid(s.cell)) fail(`${id}: ${s.good} socket cell ${s.cell} is not an occupied block`);
    const outward = s.cell.map((v, i) => v + DIRECTION_OFFSETS[s.direction][i]);
    if (solid(outward)) fail(`${id}: ${s.good} socket faces ${s.direction} into occupied block ${outward}`);
  }
}

export async function findTemplate(dataRoot, c = TANK_FARM) {
  const name = `${c.template}.IronTeeth`;
  const found = [];
  const walk = async (dir) => {
    for (const entry of await readdir(dir, {withFileTypes: true})) {
      const path = resolve(dir, entry.name);
      if (entry.isDirectory()) await walk(path);
      else if (entry.name.endsWith('.blueprint.json') && (await readJson(path)).TemplateSpec?.TemplateName === name) found.push(path);
    }
  };
  await walk(resolve(dataRoot, 'Buildings'));
  if (found.length > 1) fail(`${found.length} blueprints declare TemplateName ${name}: ${found.join(', ')}`);
  return found[0] ?? null;
}

export function cryogenicLocalization() {
  const rows = [['ID', 'Text', 'Comment'], ...CRYOGENIC_LOCALIZATION.map(([id, text]) => [id, text, 'Deep Frontier cryogenic storage'])];
  return rows.map((row) => row.map(csvCell).join(',')).join('\n') + '\n';
}

export async function checkGoods(dataRoot, c = TANK_FARM) {
  const collection = (await readJson(resolve(dataRoot, 'GoodCollections', 'GoodCollection.IronTeeth.blueprint.json'))).GoodCollectionSpec['Goods#append'];
  for (const id of c.goods) {
    let good;
    try { good = await readJson(resolve(dataRoot, 'Goods', `Good.${id}.blueprint.json`)); } catch { fail(`good ${id} is not authored in ${dataRoot}`); }
    if (good.GoodSpec?.GoodType !== 'Liquid') fail(`good ${id} has GoodType ${good.GoodSpec?.GoodType}; Timber Pipes and the tank need Liquid`);
    if (!collection.includes(id)) fail(`good ${id} is not in the Iron Teeth good collection`);
  }
}

// Template contract the behaviour relies on (native liquid Stockpile with a
// powered MechanicalNode; Timber Pipes sockets owned by this module).
export function checkTemplate(blueprint, id, c = TANK_FARM) {
  if (blueprint.TemplateSpec?.TemplateName !== `${c.template}.IronTeeth`) fail(`${id}: unexpected TemplateName ${blueprint.TemplateSpec?.TemplateName}`);
  const stockpile = blueprint.StockpileSpec;
  if (stockpile?.WhitelistedGoodType !== 'Liquid' || !Number.isInteger(stockpile.MaxCapacity) || stockpile.MaxCapacity <= 0)
    fail(`${id}: needs a native Liquid StockpileSpec with a positive MaxCapacity`);
  if (!blueprint.MechanicalBuildingSpec || !(blueprint.MechanicalNodeSpec?.PowerInput > 0) || blueprint.MechanicalNodeSpec.PowerOutput !== 0)
    fail(`${id}: must be a powered consumer (MechanicalBuildingSpec, MechanicalNodeSpec.PowerInput > 0, PowerOutput 0)`);
  for (const key of MODULE_SPECS) if (blueprint[key]) fail(`${id}: ${key} already present; applyCryogenics owns it and must run once on freshly generated blueprints`);
  for (const key of IGNORED_ON_TANKS) if (blueprint[key]) fail(`${id}: ${key} is ignored by Timber Pipes on a Liquid stockpile (in-network PipeTank); remove it from the producer`);
}

// config is TANK_FARM; scratch tests pass a copy with another status.
export async function applyCryogenics({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data'), config = TANK_FARM} = {}) {
  const c = validateTankFarmConfig(config);
  const sockets = await readStudySockets(root, c);
  await checkRegistrationSockets(root, sockets, c);
  const path = await findTemplate(dataRoot, c);
  let applied = null;
  if (c.status === 'awaiting-template') {
    if (path) fail(`${c.template}.IronTeeth now exists (${path}); set TANK_FARM.status to 'ready' and declare CryogenicTankSpec and BuildingPipeSpec in tools/automation_content.json customSpecs`);
  } else {
    if (!path) fail(`TANK_FARM.status is ready but no ${c.template}.IronTeeth blueprint was generated under ${resolve(dataRoot, 'Buildings')}`);
    await checkGoods(dataRoot, c);
    const blueprint = await readJson(path);
    checkTemplate(blueprint, c.template, c);
    checkBlueprintSockets(blueprint, sockets, c.template);
    blueprint.CryogenicTankSpec = cryogenicTankSpec(c);
    blueprint.BuildingPipeSpec = {Ports: socketPorts(sockets, c)};
    await writeJson(path, blueprint);
    applied = {path, capacity: blueprint.StockpileSpec.MaxCapacity, powerHp: blueprint.MechanicalNodeSpec.PowerInput};
  }
  const locPath = resolve(dataRoot, LOCALIZATION_FILE);
  await mkdir(dirname(locPath), {recursive: true});
  await writeFile(locPath, cryogenicLocalization(), 'utf8');
  return {status: c.status, sockets, applied};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  const summary = await applyCryogenics(dataRoot ? {dataRoot} : {});
  console.log(`Cryogenics: ${summary.status}; sockets ${summary.sockets.map((s) => `${s.good} ${s.cell} ${s.direction}`).join(', ')}`
    + (summary.applied ? `; applied to ${summary.applied.path} (${summary.applied.capacity} capacity, ${summary.applied.powerHp} hp)` : '; template not yet generated'));
}
