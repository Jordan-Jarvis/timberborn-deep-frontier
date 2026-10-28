// Every powered Deep Frontier building offers a native shaft transput, and
// every liquid building a Timber Pipes port, on each flat exterior face, and
// nowhere else (tools/connection_content.mjs; outputs/connection-faces).
//
//   node tools/validate_connection_faces.mjs [dataRoot]
//
// Checks, per template of the generated Data root that owns its model:
// - the face record belongs to the exact export, model, Size and BaseZ, and
//   no connection face is one the record lists as curved, faceted or sloped
//   (validate_connection_exports.py re-measures planarity itself);
// - roofs: a Top face only on a block that is already Stackable (a
//   platformable roof terrace or deck); the connection step never changes a
//   block (it writes no Stackable, and re-applying the plan to a copy changes
//   neither blocks nor connections);
// - powered (non-shaft MechanicalNodeSpec): the transput face set equals the
//   recomputed plan (measured flat exterior faces plus vanilla ground-layer
//   Bottom faces); authored entries may lead, generated ones follow in grid
//   order; every face sits on an occupied cell; no face points at an occupied
//   neighbour (interior), the Entrance, a door or another access cell;
//   a face into the building's own cell needs native support there (rule 2a:
//   platforms down to a stackable block or the ground); directions and
//   coordinates are valid native values with no duplicate face;
// - native graph contract (Timberborn.MechanicalSystem 1.1.2.8): a vanilla
//   PowerShaft (horizontal faces, Top) or VerticalPowerShaft (Bottom) in the
//   target cell has the reciprocal transput, which is what Transput.Faces and
//   MechanicalGraphManager.AddNode join;
// - liquid templates: the ports are the authored sockets followed by exactly
//   the plan's faces in the building's state (OpenIn / OpenOut / Open); a
//   Liquid stockpile carries them in BuildingPipeSpec, never in
//   BuildingPipeTargetPortsSpec; templates without liquid goods have no ports;
// - Timber Pipes target contract (11.4.0, outputs/modding-api-audit-1.1/
//   TimberPipes.cs): a building with target ports is a BuildingSpec entity
//   that is not itself a pipe; every port face is horizontal (only the
//   horizontal extraction valves reach buildings); an OpenIn port needs a
//   Liquid good among its inventories' InputGoods and an OpenOut port one
//   among their OutputGoods (pipeTargetGoods mirrors the initializers);
// - native connector sockets: every powered consumer carries
//   MechanicalConnectorTargetSpec, as every vanilla Iron Teeth consumer with
//   transputs does (re-read here from the vanilla blueprints). Without it
//   MechanicalConnectorActivator draws no gear socket where a shaft or
//   generator meets a transput, so a joined shaft ends at a bare wall (build
//   176: FishHatchery and Greenhouse, made from the unpowered HydroponicGarden);
// - every piped template's description ends with the shared pipe phrase for
//   its port state (PIPE_PHRASES; the tank farm's says pipes connect
//   directly), and no unpiped template carries one.
// Writes outputs/connection-faces-report.json (per-template counts and the
// native cost figures quoted in docs/transport-adapters.md).
import {readFile, readdir, writeFile} from 'node:fs/promises';
import {join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {HORIZONTAL, PIPE_PHRASES, STEP, accessCells, applyPlan, connectionPlan, connectionTemplates, externalAccess, liquidContext, mergePorts,
  parseCsvRow, pipePhrase, pipeTargetGoods, shaftFits, supportedInside} from './connection_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : join(root, 'src/DeepFrontier/Data');
const VANILLA = join(root, 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Buildings/Power');
const failures = [];
const fail = (m) => failures.push(m);
const readJson = async (p) => JSON.parse((await readFile(p, 'utf8')).replace(/^﻿/, ''));
const dirs = (e) => e.Directions.split(',').map((s) => s.trim()).filter(Boolean);
const ACROSS = {Left: 'Right', Right: 'Left', Down: 'Up', Up: 'Down', Bottom: 'Top', Top: 'Bottom'};
const STATES = new Set(['OpenIn', 'OpenOut', 'Open']);

// Reciprocal transputs of the vanilla shafts a player builds against a face.
const shaftFaces = async (name) => new Set((await readJson(join(VANILLA, name, `${name}.IronTeeth.blueprint.json`)))
  .TransputProviderSpec.Transputs.flatMap(dirs));
const powerShaft = await shaftFaces('PowerShaft'), verticalShaft = await shaftFaces('VerticalPowerShaft');
const shaftFor = (d) => d === 'Bottom' ? verticalShaft : powerShaft;

// Vanilla evidence for the connector-socket rule: every Iron Teeth consumer
// (PowerInput > 0) with transputs carries MechanicalConnectorTargetSpec.
const VANILLA_BUILDINGS = join(VANILLA, '..');
const vanillaConsumers = [];
for (const entry of await readdir(VANILLA_BUILDINGS, {recursive: true})) {
  if (!entry.endsWith('.IronTeeth.blueprint.json')) continue;
  const blueprint = await readJson(join(VANILLA_BUILDINGS, entry));
  if (blueprint.MechanicalNodeSpec?.PowerInput > 0 && blueprint.TransputProviderSpec?.Transputs?.length)
    vanillaConsumers.push({entry, socket: Object.hasOwn(blueprint, 'MechanicalConnectorTargetSpec')});
}
if (!vanillaConsumers.length) fail(`vanilla evidence: no Iron Teeth consumers with transputs found under ${VANILLA_BUILDINGS}`);
for (const v of vanillaConsumers.filter((v) => !v.socket)) fail(`vanilla evidence: consumer ${v.entry} has no MechanicalConnectorTargetSpec; revisit the connector-socket rule`);

function entryFaces(id, entries, what, value) {
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size;
  const seen = new Set(), faces = [];
  for (const e of entries) {
    const {X, Y, Z} = e.Coordinates;
    if (![X, Y, Z].every(Number.isInteger) || X < 0 || Y < 0 || Z < 0 || X >= w || Y >= h || Z >= layers) { fail(`${id}: ${what} at ${X},${Y},${Z} lies outside the ${w}x${h}x${layers} Size`); continue; }
    const list = dirs(e);
    if (!list.length) fail(`${id}: ${what} at ${X},${Y},${Z} has no direction`);
    for (const d of list) {
      if (!STEP[d]) { fail(`${id}: ${what} direction ${d} is not a Direction3D`); continue; }
      const k = [X, Y, Z, d].join(',');
      if (seen.has(k)) fail(`${id}: duplicate ${what} face ${k}`);
      seen.add(k);
      faces.push([X, Y, Z, d]);
    }
  }
  return faces;
}

// The connection step must never make a roof stackable (user: "We don't
// connect to roof tiles unless it is platformable roof").
const source = await readFile(join(root, 'tools/connection_content.mjs'), 'utf8');
if (/\.Stackable\s*=[^=]/.test(source)) fail('tools/connection_content.mjs assigns Stackable; the connection step must not change blocks');
const context = await liquidContext(dataRoot);
const descriptions = new Map((await readFile(join(dataRoot, 'Localizations', 'enUS.csv'), 'utf8')).split('\n').filter(Boolean)
  .map((line) => parseCsvRow(line)).map(([k, text]) => [k, text]));
const report = [];
let connectable = 0, largest = {id: null, count: 0};
for (const {id, value} of await connectionTemplates(dataRoot)) {
  let plan;
  try { plan = await connectionPlan(id, value, context, root); } catch (error) { fail(error.message); continue; }
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size;
  const index = ([x, y, z]) => (z * h + y) * w + x;
  const inside = ([x, y, z]) => x >= 0 && y >= 0 && z >= 0 && x < w && y < h && z < layers;
  const block = (c) => spec.Blocks[index(c)];
  const {extra, skipSides} = await externalAccess(id, value, root);
  const {cells: access} = accessCells(value, extra);
  const row = {id, powered: false, power: 0, top: 0, liquids: null, state: null, ports: 0, roofPorts: 0};
  if (plan) {
    const curved = new Set((plan.record.curvedFaces ?? []).map((f) => f.slice(0, 4).join(',')));
    for (const f of plan.faces) if (curved.has(f.join(','))) fail(`${id}: connection face ${f} sits on a curved or sloped surface`);
    for (const [x, y, z, d] of plan.faces) if (d === 'Top' && block([x, y, z]).Stackable === 'None') fail(`${id}: roof face ${x},${y},${z} is not on a platformable (Stackable) roof`);
    const copy = structuredClone(value);
    try {
      applyPlan(copy, plan);
      if (JSON.stringify(copy.TransputProviderSpec) !== JSON.stringify(value.TransputProviderSpec)
        || JSON.stringify(copy.BuildingPipeTargetPortsSpec) !== JSON.stringify(value.BuildingPipeTargetPortsSpec)
        || JSON.stringify(copy.BuildingPipeSpec) !== JSON.stringify(value.BuildingPipeSpec)) fail(`${id}: re-applying the connection plan changes the connections`);
    } catch (error) { fail(error.message); }
  }
  const neighbourChecks = (faces, what) => {
    for (const [x, y, z, d] of faces) {
      const c = [x, y, z], n = c.map((v, i) => v + STEP[d][i]);
      if (block(c).Occupations === 'None') fail(`${id}: ${what} ${c} ${d} is on an unoccupied cell`);
      if (access.has(n.join(','))) fail(`${id}: ${what} ${c} ${d} points at access cell ${n} (door, entrance, walkway or water flow)`);
      if (inside(n)) {
        if (!shaftFits(block(n).Occupations, d)) fail(`${id}: ${what} ${c} ${d} points into a cell no vanilla shaft fits in ${n} (interior)`);
        else if (!supportedInside(spec, n)) fail(`${id}: ${what} ${c} ${d} points into ${n}, where nothing can carry a shaft or valve (a non-stackable building block a Platform cannot share is below)`);
      } else if (skipSides.includes(d)) fail(`${id}: ${what} ${c} ${d} points off the map edge`);
    }
  };
  if (plan?.powered) {
    const transputs = value.TransputProviderSpec?.Transputs;
    if (!Array.isArray(transputs)) { fail(`${id}: powered template without TransputProviderSpec.Transputs`); continue; }
    if (typeof value.TransputProviderSpec.IgnoreRotation !== 'boolean') fail(`${id}: TransputProviderSpec.IgnoreRotation must be a boolean`);
    for (const t of transputs) if (typeof t.ReverseRotation !== 'boolean') fail(`${id}: transput ReverseRotation must be a boolean`);
    const faces = entryFaces(id, transputs, 'transput', value);
    const actual = new Set(faces.map((f) => f.join(',')));
    const expected = new Set([...plan.ground, ...plan.faces].map((f) => f.join(',')));
    const missing = [...expected].filter((k) => !actual.has(k)), extraFaces = [...actual].filter((k) => !expected.has(k));
    if (missing.length) fail(`${id}: ${missing.length} flat exterior faces offer no shaft transput, e.g. ${missing.slice(0, 4).join(' ')}`);
    if (extraFaces.length) fail(`${id}: ${extraFaces.length} transput faces are not flat exterior faces, e.g. ${extraFaces.slice(0, 4).join(' ')}`);
    neighbourChecks(faces.filter((f) => !(f[3] === 'Bottom' && f[2] === 0)), 'transput');
    for (const [x, y, z, d] of faces) {
      if (!shaftFor(d).has(ACROSS[d])) fail(`${id}: no vanilla shaft has a ${ACROSS[d]} transput to meet ${x},${y},${z} ${d}`);
      if (d === 'Top' && block([x, y, z]).Stackable === 'None') fail(`${id}: Top transput ${x},${y},${z} is not on a platformable (Stackable) roof`);
    }
    if (value.MechanicalNodeSpec.PowerInput > 0 && !Object.hasOwn(value, 'MechanicalConnectorTargetSpec'))
      fail(`${id}: powered consumer without MechanicalConnectorTargetSpec: no gear socket is drawn where a shaft meets its walls (every vanilla consumer has one)`);
    const count = faces.filter((f) => f[3] !== 'Bottom').length;   // MechanicalConnectorActivator: horizontal + Top
    connectable += count;
    if (count > largest.count) largest = {id, count};
    Object.assign(row, {powered: true, power: faces.length, top: faces.filter((f) => f[3] === 'Top').length, connectable: count});
  } else if (value.TransputProviderSpec?.Transputs?.length && value.MechanicalNodeSpec && !value.MechanicalNodeSpec.IsShaft) {
    fail(`${id}: unexpected transputs`);
  }
  const tank = value.StockpileSpec?.WhitelistedGoodType === 'Liquid';
  const portSpec = tank ? value.BuildingPipeSpec : value.BuildingPipeTargetPortsSpec;
  if (plan?.state) {
    if (tank && value.BuildingPipeTargetPortsSpec) fail(`${id}: BuildingPipeTargetPortsSpec is ignored on a Liquid stockpile`);
    const ports = portSpec?.Ports;
    if (!Array.isArray(ports)) { fail(`${id}: liquid template (${[...plan.liquids.input, ...plan.liquids.output]}) has no pipe ports`); continue; }
    for (const p of ports) if (!STATES.has(p.State)) fail(`${id}: pipe port State ${p.State} is not OpenIn/OpenOut/Open`);
    const state = tank ? 'Open' : plan.state;
    let authored = -1;
    const portFaces = tank ? plan.faces : plan.faces.filter((f) => HORIZONTAL[f[3]]);
    for (let k = 0; k <= ports.length && authored < 0; k++) {
      if (JSON.stringify(mergePorts(ports.slice(0, k), portFaces, state)) === JSON.stringify(ports)) authored = k;
    }
    if (!tank) {
      const goods = pipeTargetGoods(value, context);
      if (!goods.target) fail(`${id}: Timber Pipes does not treat it as a building pipe target (needs BuildingSpec, not a pipe)`);
      for (const p of ports) {
        for (const d of dirs(p)) if (!HORIZONTAL[d]) fail(`${id}: pipe port ${JSON.stringify(p.Coordinates)} ${d} is vertical; no Timber Pipes valve can meet it`);
        if ((p.State === 'OpenIn' || p.State === 'Open') && !goods.input.size) fail(`${id}: ${p.State} port but no inventory takes a Liquid good`);
        if ((p.State === 'OpenOut' || p.State === 'Open') && !goods.output.size && !(p.State === 'Open' && goods.input.size)) fail(`${id}: ${p.State} port but no inventory gives a Liquid good`);
      }
      for (const g of plan.liquids.input) if (!goods.input.has(g)) fail(`${id}: takes ${g}, but no inventory registers it as an input Timber Pipes can fill`);
      for (const g of plan.liquids.output) if (!goods.output.has(g)) fail(`${id}: gives ${g}, but no inventory registers it as an output Timber Pipes can drain`);
      row.pipeTarget = {input: [...goods.input].sort(), output: [...goods.output].sort()};
    }
    if (authored < 0) fail(`${id}: pipe ports are not the authored sockets followed by every flat exterior face (${state})`);
    const faces = entryFaces(id, ports, 'pipe port', value);
    neighbourChecks(faces.slice(ports.slice(0, Math.max(authored, 0)).reduce((n, p) => n + dirs(p).length, 0)), 'pipe port');
    for (const p of ports.slice(0, Math.max(authored, 0))) for (const d of dirs(p)) {
      const c = [p.Coordinates.X, p.Coordinates.Y, p.Coordinates.Z], n = c.map((v, i) => v + STEP[d][i]);
      if (block(c).Occupations === 'None') fail(`${id}: authored pipe socket ${c} ${d} is on an unoccupied cell`);
      if (inside(n) && block(n).Occupations !== 'None') fail(`${id}: authored pipe socket ${c} ${d} faces occupied cell ${n}`);
    }
    Object.assign(row, {liquids: {in: plan.liquids.input, out: plan.liquids.output}, state, ports: faces.length,
      roofPorts: faces.filter((f) => f[3] === 'Top').length, authoredPorts: Math.max(authored, 0)});
  } else if (value.BuildingPipeTargetPortsSpec || value.BuildingPipeSpec) {
    fail(`${id}: has pipe ports but no liquid good`);
  }
  const description = descriptions.get(`Building.${id}.Description`) ?? '';
  if (plan?.state) {
    if (!description.endsWith(' ' + pipePhrase(plan.state, plan.liquids.tank))) fail(`${id}: description does not end with the pipe phrase for ${plan.liquids.tank ? 'a tank' : plan.state} ports`);
  } else if (Object.values(PIPE_PHRASES).some((phrase) => description.includes(phrase))) fail(`${id}: unpiped building describes pipe valves`);
  report.push(row);
}
const summary = {
  scope: 'Generated blueprint connection faces against outputs/connection-faces records (static; in-game placement is separate)',
  templates: report.length,
  powered: report.filter((r) => r.powered).length,
  liquid: report.filter((r) => r.state).length,
  withoutPipes: report.filter((r) => !r.state).map((r) => r.id),
  connectableTransputsOneOfEach: connectable,
  vanillaConsumersWithSocket: `${vanillaConsumers.filter((v) => v.socket).length}/${vanillaConsumers.length}`,
  largestConnectable: largest,
  buildings: report,
};
await writeFile(join(root, 'outputs/connection-faces-report.json'), JSON.stringify(summary, null, 1) + '\n');
if (failures.length) {
  console.log(failures.map((f) => 'FAIL ' + f).join('\n'));
  console.error(`Connection face validation failed (${failures.length})`);
  process.exit(1);
}
console.log(`Connection faces: ${summary.powered} powered templates (shaft transputs on every flat exterior face, ${connectable} connectable faces for one of each), ${summary.liquid} liquid templates with pipe ports there; ${summary.withoutPipes.length} without pipes.`);
