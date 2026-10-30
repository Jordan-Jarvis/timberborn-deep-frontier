// Power shafts and Timber Pipes on every flat exterior surface (user
// direction, 2026-10-23: "The Bathhouse and basically any and all buildings
// need to accept power and pipes on any flat surface of the building").
//
// Runs once at the end of generation, after every building blueprint exists
// (create_vertical_slice_content.mjs), or standalone on a generated Data root:
//   node tools/connection_content.mjs [dataRoot]
//
// Face set (connectionFaces): a face of a cell is a connection face when
//  1. the cell is occupied (any occupation) and the face was measured flat on
//     the exported model (outputs/connection-faces/<Template>.json, written by
//     tools/asset-pipeline/measure_connection_faces.py): one plane parallel to
//     the face covers >= 60% of it within 0.35 of the cell plane, and no
//     covering surface is curved, faceted or sloped (user: "we don't want to
//     be able to connect to the curved edges, just the flat ones"); flat
//     window glazing counts as wall (2026-10-26, the Greenhouse); no animated
//     part in front;
//  1a. a Top (roof) face only where the roof is already platformable: its
//     block is Stackable in the blueprint as the families generated it
//     (roof terraces, decks, the restaurant's and hospital's roof terraces).
//     User: "We don't connect to roof tiles unless it is platformable roof."
//     This step never makes a block stackable;
//  2. the neighbour cell across the face is exterior: outside the Size, or an
//     open cell that a flood fill through open cells reaches from outside the
//     Size. Open means the native BlockValidator would let the shaft stand
//     there: its occupation shares no flag with the vanilla PowerShaft's
//     (Bottom, Path, Middle), e.g. None, a deck's Top/Corners, or a porch's
//     Floor (the Fish Hatchery's front walk). Under a Bottom face the
//     VerticalPowerShaft's flags must fit instead. Enclosed voids never qualify;
//  2a. a neighbour cell inside the Size can carry the shaft or valve: both need
//     ground or a stackable block below (MatterBelow GroundOrStackable). Going
//     down from the neighbour, every building cell a vanilla Platform fits in
//     (no Top or Corners occupation) can hold a player's platform, until a
//     Stackable block of the building or the ground below its lowest layer;
//     a non-stackable block of the building that a Platform cannot share
//     (a walkway's corner posts, a lower roof that is not platformable)
//     leaves the face unreachable (build 176: FisheryWorks, Hospital and
//     Restaurant faces over their own walkways and eaves). Outside the Size a
//     player builds platform columns up from the terrain;
//  3. the neighbour is not an access cell: the native Entrance, every door's
//     path cell (late-game/grocery registrations, civic structure doors),
//     walkway openings' outside cells, building navmesh edge ends that are
//     not occupied, and the cells native water/sludge in- and outlets use.
//     The radiation export's MAP_EDGE side (off the map) is skipped as well.
// Undersides (user: "From the bottom counts as flat"): power (every non-shaft
// MechanicalNodeSpec) offers a Bottom face on every occupied ground-layer
// cell that stands on ground or a platform (not MatterBelow Air), as the
// vanilla Smelter/BotPartFactory do; a VerticalPowerShaft meets it from below.
// Undersides above open space (overhangs, raised floors, decks over free
// cells) are measured faces like walls: rule 1 (flat, uncurved) and 2 (a
// None, exterior cell below), and they carry pipe ports too. They do not
// need a platformable roof (rule 1a is for Top faces only).
//
// Native contract (Timberborn 1.1.2.8, Timberborn.MechanicalSystem): one
// Transput per TransputSpec direction; Transput.Faces joins two transputs
// whose targets are each other's cells with opposite directions. Top/Bottom
// are vertical, Up/Down are grid Y. A shaft above a roof needs a stackable
// block below it (PowerShaft/VerticalPowerShaft MatterBelow
// GroundOrStackable), as on the vanilla BotPartFactory roof (Top transputs on
// Stackable All blocks); rule 1a offers Top faces only on such blocks.
//
// Timber Pipes 11.4.0: BuildingPipeTargetPortsSpec.Ports {Coordinates,
// Directions, State} name the building cell and the outward face a pipe
// meets (DefaultBuildingConnectionProvider; FaceAllowed scans the transformed
// list). Without the spec every face is accepted; with it only the listed
// ones. Every BuildingSpec entity is a target (BuildingPipeTarget is an
// AddTemplateModule2 of BuildingSpec); it exchanges the Liquid goods its
// enabled inventories register: InputGoods (Givable) when a pipe gives,
// OutputGoods or takeable stock when a pipe takes (ValvePipeIo.
// LiquidIdsForConnection). Only the two extraction valves reach a building
// (ExtractionPipe.FindInletTarget / FindOutletTarget -> ValvePipeService.
// FindConnection): HorizontalPipeValve (local Down OpenIn from the network,
// Up OpenOut into the building) and ElbowPipeValve (Down / Right). Transport
// pipes connect only to other pipes and tanks (PipeRegistry.portOwners), and
// no valve is vertical, so building ports are horizontal faces only. A new
// valve's Inlet starts off (ExtractionPipe.InletEnabled). A Liquid stockpile
// is an in-network PipeTank whose ports are its BuildingPipeSpec.Ports
// instead (cryogenic_content.mjs); transport pipes, vertical ones included,
// meet those directly.
//
// Authored entries stay first and unchanged in order: power sockets keep
// their surviving directions (acceptance fixtures build beside Transputs[0]),
// pipe ports (study sockets, coolant, aquaculture and mixer inlets) are kept
// verbatim. Generated faces follow in grid order.
import {createHash} from 'node:crypto';
import {access, readdir, readFile, writeFile} from 'node:fs/promises';
import {dirname, join, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const VANILLA = join(repo, 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources');
export const RECORDS = 'outputs/connection-faces';
export const HORIZONTAL = {Left: [-1, 0, 0], Right: [1, 0, 0], Down: [0, -1, 0], Up: [0, 1, 0]};
export const STEP = {...HORIZONTAL, Bottom: [0, 0, -1], Top: [0, 0, 1]};
export const ORDER = ['Left', 'Right', 'Down', 'Up', 'Bottom', 'Top'];
// A vanilla PowerShaft occupies Bottom, Path, Middle; Top and Corners stay free.
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
// Occupations of the vanilla shafts a player builds against a face (read from the
// installed blueprints): a neighbour cell can hold one when it shares no flag.
const shaftFlags = async (name) => new Set((await readJson(join(VANILLA, 'Buildings/Power', name, `${name}.IronTeeth.blueprint.json`)))
  .BlockObjectSpec.Blocks[0].Occupations.split(', '));
export const SHAFT_FLAGS = {horizontal: await shaftFlags('PowerShaft'), vertical: await shaftFlags('VerticalPowerShaft')};
// Occupations of the vanilla Platform a player stacks under a raised shaft or valve.
const platformFlags = new Set((await readJson(join(VANILLA, 'Buildings/Paths/Platform/Platform.IronTeeth.blueprint.json')))
  .BlockObjectSpec.Blocks[0].Occupations.split(', '));
// Rule 2a: whether a shaft or valve standing in the building's own cell n has native support.
export function supportedInside(spec, n) {
  const {X: w, Y: h} = spec.Size;
  for (let z = n[2] - 1; z >= 0; z--) {
    const b = spec.Blocks[(z * h + n[1]) * w + n[0]];
    if (b.Stackable !== 'None' && b.Occupations !== 'None') return true;
    if (b.Occupations !== 'None' && b.Occupations.split(', ').some((f) => platformFlags.has(f))) return false;
  }
  return true;
}
// Whether a cell with this occupation can hold the shaft for a face in direction dir.
export function shaftFits(occupations, dir) {
  if (occupations === 'All') return false;
  const shaft = dir === 'Bottom' ? SHAFT_FLAGS.vertical : SHAFT_FLAGS.horizontal;
  return occupations === 'None' || occupations.split(', ').every((f) => !shaft.has(f));
}
// Late-game studies whose registration is named differently from the template.
const STUDY = {GroceryStore: 'GroceryMarket'};

const key = (c) => c.join(',');
const xyz = ([X, Y, Z]) => ({X, Y, Z});

async function blueprintFiles(dir) {
  const out = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) out.push(...await blueprintFiles(path));
    else if (entry.name.endsWith('.blueprint.json')) out.push(path);
  }
  return out;
}

// Liquid goods and recipes visible to a Deep Frontier template.
export async function liquidContext(dataRoot) {
  const liquid = new Set(), recipes = new Map();
  for (const root of [VANILLA, dataRoot]) {
    for (const file of await blueprintFiles(join(root, 'Goods'))) {
      const spec = (await readJson(file)).GoodSpec;
      if (spec?.GoodType === 'Liquid') liquid.add(spec.Id);
    }
    for (const file of await blueprintFiles(join(root, 'Recipes'))) {
      const spec = (await readJson(file)).RecipeSpec;
      if (spec) recipes.set(spec.Id, spec);
    }
  }
  return {liquid, recipes};
}

// Liquids a template takes in and gives out through native inventories, from
// the specs that own one. Unknown recipe ids fail.
export function liquidUse(value, {liquid, recipes}) {
  const input = new Set(), output = new Set();
  const take = (id) => { if (liquid.has(id)) input.add(id); };
  const give = (id) => { if (liquid.has(id)) output.add(id); };
  for (const id of value.ManufactorySpec?.ProductionRecipeIds ?? []) {
    const recipe = recipes.get(id);
    if (!recipe) throw new Error(`${value.TemplateSpec.TemplateName}: unknown recipe ${id}`);
    for (const g of recipe.Ingredients) take(g.Id);
    if (recipe.Fuel) take(recipe.Fuel);
    for (const g of recipe.Products) give(g.Id);
  }
  for (const g of value.GoodConsumingBuildingSpec?.ConsumedGoods ?? []) take(g.GoodId);
  if (value.HospitalPantrySpec) take(value.HospitalPantrySpec.WaterGoodId);
  if (value.RestaurantSpec) {
    take(value.RestaurantSpec.DrinkingWater);
    for (const g of [...value.RestaurantSpec.Foods, ...value.RestaurantSpec.OptionalGoods]) take(g);
    for (const s of value.RestaurantSpec.Stock) take(s.GoodId);
  }
  for (const id of value.GroceryStoreSpec?.Foods ?? []) take(id);
  const tank = value.StockpileSpec?.WhitelistedGoodType === 'Liquid';
  return {input: [...input].sort(), output: [...output].sort(), tank};
}

// The goods each inventory Timber Pipes can see registers, mirroring the
// native and Deep Frontier inventory initializers (for the static target
// check): Manufactory recipes (ingredients and fuel Givable, products
// Takeable), except the Restaurant, whose kitchen inventory replaces it with
// its Givable stock (RestaurantKitchenInventory); GoodConsumingBuilding
// supplies (Givable) plus the Hospital pantry water (HospitalPantryInventory);
// Grocery foods (Givable and Takeable); bot-maintenance oils and workplace
// upkeep goods (Givable, BotMaintenanceInventory.WithExtraGoods). Liquid goods only.
export function pipeTargetGoods(value, {liquid, recipes}) {
  const input = new Set(), output = new Set();
  const add = (set, id) => { if (liquid.has(id)) set.add(id); };
  if (value.RestaurantSpec) for (const g of value.RestaurantSpec.Stock) add(input, g.GoodId);
  else for (const id of value.ManufactorySpec?.ProductionRecipeIds ?? []) {
    const recipe = recipes.get(id);
    if (!recipe) throw new Error(`${value.TemplateSpec.TemplateName}: unknown recipe ${id}`);
    for (const g of recipe.Ingredients) add(input, g.Id);
    if (recipe.Fuel) add(input, recipe.Fuel);
    for (const g of recipe.Products) add(output, g.Id);
  }
  for (const g of value.GoodConsumingBuildingSpec?.ConsumedGoods ?? []) add(input, g.GoodId);
  if (value.HospitalPantrySpec) add(input, value.HospitalPantrySpec.WaterGoodId);
  for (const id of value.GroceryStoreSpec?.Foods ?? []) { add(input, id); add(output, id); }
  for (const g of value.FrontierBotMaintenanceSpec?.Goods ?? []) add(input, g.GoodId);
  for (const g of value.FrontierWorkplaceUpkeepSpec?.Goods ?? []) add(input, g.GoodId);
  return {input, output, target: Boolean(value.BuildingSpec) && !value.BuildingPipeSpec && !value.TransportPipeSpec};
}

export function portState({input, output, tank}) {
  if (tank || (input.length && output.length)) return 'Open';
  if (input.length) return 'OpenIn';
  if (output.length) return 'OpenOut';
  return null;
}

// Access cells: neighbours that keep their face free for walking, doors and
// native water/sludge flows. `extra` comes from registrations and layouts.
export function accessCells(value, extra = []) {
  const cells = new Set(), own = new Set(), spec = value.BlockObjectSpec;
  const {X: w, Y: h, Z: layers} = spec.Size;
  const block = ([x, y, z]) => spec.Blocks[(z * h + y) * w + x];
  const inside = ([x, y, z]) => x >= 0 && y >= 0 && z >= 0 && x < w && y < h && z < layers;
  const add = (c) => cells.add(key(c));
  const E = spec.Entrance;
  if (E?.HasEntrance) add([E.Coordinates.X, E.Coordinates.Y, E.Coordinates.Z]);
  for (const o of value.BuildingWalkwaySpec?.Openings ?? []) add([o.Outside.X, o.Outside.Y, o.Outside.Z]);
  for (const g of value.BlockObjectNavMeshSettingsSpec?.EdgeGroups ?? []) {
    for (const e of g.AddedEdges) for (const p of [e.Start, e.End]) {
      const c = [p.X, p.Y, p.Z];
      if (!inside(c) || block(c).Occupations === 'None') add(c);
    }
  }
  const W = value.WaterInputSpec?.WaterInputCoordinates;
  if (W) for (let z = W.Z + 1; z >= 0; z--) { add([W.X, W.Y, z]); own.add(key([W.X, W.Y, z])); }
  const O = value.RadioactiveSludgeOutfallSpec?.OutputCoordinates;
  if (O) { add([O.X, O.Y, O.Z]); own.add(key([O.X, O.Y, O.Z])); }
  for (const c of extra) add(c);
  return {cells, own};
}

// Every face of the measured set that is exterior and not an access face.
export function connectionFaces(value, measured, {access, own = new Set(), skipSides = []}) {
  const spec = value.BlockObjectSpec;
  const {X: w, Y: h, Z: layers} = spec.Size;
  const index = ([x, y, z]) => (z * h + y) * w + x;
  const inside = ([x, y, z]) => x >= 0 && y >= 0 && z >= 0 && x < w && y < h && z < layers;
  const open = (c) => shaftFits(spec.Blocks[index(c)].Occupations, 'Left');
  // Flood fill of open cells reachable from outside the Size.
  const exterior = new Set(), queue = [];
  for (let z = 0; z < layers; z++) for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const c = [x, y, z];
    if (open(c) && Object.values(STEP).some(([dx, dy, dz]) => !inside([x + dx, y + dy, z + dz]))) { exterior.add(key(c)); queue.push(c); }
  }
  while (queue.length) {
    const [x, y, z] = queue.pop();
    for (const [dx, dy, dz] of Object.values(STEP)) {
      const n = [x + dx, y + dy, z + dz];
      if (inside(n) && !exterior.has(key(n)) && open(n)) { exterior.add(key(n)); queue.push(n); }
    }
  }
  const faces = [];
  for (const [x, y, z, dir] of measured) {
    const step = STEP[dir];
    if (!step) throw new Error(`Unknown face direction ${dir}`);
    const c = [x, y, z], n = [x + step[0], y + step[1], z + step[2]];
    if (!inside(c)) throw new Error(`Measured face ${c} ${dir} lies outside the Size`);
    if (spec.Blocks[index(c)].Occupations === 'None') continue;
    if (dir === 'Top' && spec.Blocks[index(c)].Stackable === 'None') continue;
    if (access.has(key(n)) || own.has(key(c))) continue;
    if (inside(n)) {
      if (!exterior.has(key(n))) continue;
      if (!shaftFits(spec.Blocks[index(n)].Occupations, dir)) continue;
      if (!supportedInside(spec, n)) continue;
    } else if (skipSides.includes(dir)) continue;
    faces.push([x, y, z, dir]);
  }
  return faces;
}

// Ground-layer Bottom faces of every occupied cell (power only). A building with
// BaseZ > 0 has no such faces: its lowest layer stands below its placement level
// (in water or under a bank, as the Fish Hatchery's pens), where no shaft can
// reach it from below; its undersides above open cells are measured faces.
export function groundBottoms(value, own = new Set()) {
  const spec = value.BlockObjectSpec;
  if (spec.BaseZ > 0) return [];
  const {X: w, Y: h} = spec.Size;
  const faces = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++) {
    const b = spec.Blocks[y * w + x];
    if (b.Occupations !== 'None' && b.MatterBelow !== 'Air' && !own.has(key([x, y, 0]))) faces.push([x, y, 0, 'Bottom']);
  }
  return faces;
}

// Entries grouped by cell in grid order (z, y, x), directions in ORDER.
function grouped(faces, extra) {
  const cells = new Map();
  for (const [x, y, z, dir] of faces) {
    const k = key([x, y, z]);
    if (!cells.has(k)) cells.set(k, {cell: [x, y, z], dirs: new Set()});
    cells.get(k).dirs.add(dir);
  }
  return [...cells.values()].sort((a, b) => a.cell[2] - b.cell[2] || a.cell[1] - b.cell[1] || a.cell[0] - b.cell[0])
    .map(({cell, dirs}) => ({Coordinates: xyz(cell), Directions: ORDER.filter((d) => dirs.has(d)).join(', '), ...extra}));
}

const directionsOf = (entry) => entry.Directions.split(',').map((s) => s.trim()).filter(Boolean);

// Authored transputs keep their order and surviving directions; the rest of
// the allowed faces follow.
export function mergeTransputs(prior, allowed) {
  const allow = new Set(allowed.map((f) => f.join(',')));
  const used = new Set(), result = [];
  for (const t of prior) {
    const c = [t.Coordinates.X, t.Coordinates.Y, t.Coordinates.Z];
    const dirs = directionsOf(t).filter((d) => { if (!ORDER.includes(d)) throw new Error(`Unknown transput direction ${d}`); return allow.has([...c, d].join(',')) && !used.has([...c, d].join(',')); });
    for (const d of dirs) used.add([...c, d].join(','));
    if (dirs.length) result.push({...t, Directions: ORDER.filter((d) => dirs.includes(d)).join(', ')});
  }
  return [...result, ...grouped(allowed.filter((f) => !used.has(f.join(','))), {ReverseRotation: false})];
}

// Authored ports stay verbatim; generated ports cover the other allowed faces.
export function mergePorts(prior, allowed, state) {
  const used = new Set();
  for (const p of prior) for (const d of directionsOf(p)) used.add([p.Coordinates.X, p.Coordinates.Y, p.Coordinates.Z, d].join(','));
  return [...prior, ...grouped(allowed.filter((f) => !used.has(f.join(','))), {State: state})];
}

// Face record of a template, checked against the export it measured.
export async function faceRecord(id, value, root = repo) {
  const record = await readJson(join(root, RECORDS, `${id}.json`));
  const model = value.Children?.['#Finished']?.TimbermeshSpec?.Model;
  const spec = value.BlockObjectSpec;
  if (record.template !== id || record.model !== model) throw new Error(`${id}: connection faces were measured on ${record.model}, not ${model}`);
  if (JSON.stringify(record.size) !== JSON.stringify([spec.Size.X, spec.Size.Y, spec.Size.Z]) || record.baseZ !== spec.BaseZ)
    throw new Error(`${id}: connection faces were measured over another Size/BaseZ; rerun measure_connection_faces.py`);
  const digest = createHash('sha256').update(await readFile(join(root, record.export))).digest('hex');
  if (digest !== record.exportSha256) throw new Error(`${id}: ${record.export} changed since its connection faces were measured; rerun measure_connection_faces.py`);
  return record;
}

// Access cells and sides that come from outside the blueprint.
export async function externalAccess(id, value, root = repo) {
  const extra = [], skipSides = [];
  const study = STUDY[id] ?? id;
  const registration = join(root, 'outputs/lategame-studies', `${study}-registration.json`);
  let doors = null;
  try { doors = (await readJson(registration)).doors; } catch (error) { if (error.code !== 'ENOENT') throw error; }
  const model = value.Children['#Finished'].TimbermeshSpec.Model;
  if (doors && model.endsWith(`/${id}.IronTeeth.Model`)) for (const d of doors) extra.push(d.entrance);
  const civic = (await readJson(join(root, 'tools/civic-layouts.json')))[id];
  for (const door of Object.values(civic?.structure?.doors ?? {})) {
    const [px, py, pz] = door.position, [dx, dy] = door.outward;
    const cell = [Math.floor(px - .5 * dx - (dx ? 0 : .5)), Math.floor(py - .5 * dy - (dy ? 0 : .5)), pz];
    // Door centred on the face between `cell` and the cell outside it.
    extra.push([cell[0] + dx, cell[1] + dy, pz]);
  }
  if (value.MapEdgeSiteSpec) {
    const source = await readFile(join(root, `tools/asset-pipeline/lategame_${id}.py`), 'utf8');
    const m = source.match(/^MAP_EDGE = '(\w+)'$/m);
    if (!m || !HORIZONTAL[m[1]]) throw new Error(`${id}: MapEdgeSiteSpec without a study MAP_EDGE side`);
    skipSides.push(m[1]);
  }
  return {extra, skipSides};
}

// The complete connection plan of one template (validators recompute it).
export async function connectionPlan(id, value, context, root = repo) {
  const powered = Boolean(value.MechanicalNodeSpec) && !value.MechanicalNodeSpec.IsShaft;
  const liquids = liquidUse(value, context);
  const state = portState(liquids);
  if (!powered && !state) return null;
  const record = await faceRecord(id, value, root);
  const {extra, skipSides} = await externalAccess(id, value, root);
  const {cells: access, own} = accessCells(value, extra);
  const faces = connectionFaces(value, record.faces, {access, own, skipSides});
  return {powered, liquids, state, faces, ground: powered ? groundBottoms(value, own) : [], record};
}

// Applies a plan to a blueprint value (transputs and pipe ports only; blocks
// are never changed). Returns before/after counts.
export function applyPlan(value, plan) {
  const count = (entries) => (entries ?? []).reduce((n, e) => n + directionsOf(e).length, 0);
  const before = {power: count(value.TransputProviderSpec?.Transputs),
    pipes: count((value.BuildingPipeSpec ?? value.BuildingPipeTargetPortsSpec)?.Ports)};
  const blocks = JSON.stringify(value.BlockObjectSpec);
  if (plan.powered) {
    const allowed = [...plan.ground, ...plan.faces];
    value.TransputProviderSpec = {IgnoreRotation: value.TransputProviderSpec?.IgnoreRotation ?? false,
      Transputs: mergeTransputs(value.TransputProviderSpec?.Transputs ?? [], allowed)};
  }
  if (plan.state) {
    if (plan.liquids.tank) {
      if (!value.BuildingPipeSpec) throw new Error(`${value.TemplateSpec.TemplateName}: a Liquid stockpile needs its BuildingPipeSpec sockets first`);
      if (value.BuildingPipeTargetPortsSpec) throw new Error(`${value.TemplateSpec.TemplateName}: BuildingPipeTargetPortsSpec is ignored on a Liquid stockpile`);
      value.BuildingPipeSpec = {...value.BuildingPipeSpec, Ports: mergePorts(value.BuildingPipeSpec.Ports, plan.faces, 'Open')};
    } else {
      // Valves are horizontal: building target ports on vertical faces could never be met.
      value.BuildingPipeTargetPortsSpec = {Ports: mergePorts(value.BuildingPipeTargetPortsSpec?.Ports ?? [],
        plan.faces.filter((f) => HORIZONTAL[f[3]]), plan.state)};
    }
  }
  if (JSON.stringify(value.BlockObjectSpec) !== blocks) throw new Error(`${value.TemplateSpec.TemplateName}: the connection step changed blocks`);
  return {before, after: {power: count(value.TransputProviderSpec?.Transputs),
    pipes: count((value.BuildingPipeSpec ?? value.BuildingPipeTargetPortsSpec)?.Ports)},
    roofFaces: plan.faces.filter((f) => f[3] === 'Top').length};
}

// Deep Frontier building templates of a Data root that own their model.
export async function connectionTemplates(dataRoot) {
  const out = [];
  for (const file of await blueprintFiles(join(dataRoot, 'Buildings'))) {
    if (!file.endsWith('.IronTeeth.blueprint.json')) continue;
    const value = await readJson(file);
    if (!value.PlaceableBlockObjectSpec || !value.BlockObjectSpec) continue;
    const model = value.Children?.['#Finished']?.TimbermeshSpec?.Model;
    try { await access(join(dataRoot, `${model}.timbermesh`)); } catch { continue; }
    out.push({id: file.split(sep).pop().replace('.IronTeeth.blueprint.json', ''), file, value});
  }
  return out;
}

// How to pipe a building, appended once to its description (one shared phrase
// per direction). Target ports take and give through the extraction valves;
// a Liquid stockpile's tank ports meet transport pipes directly.
export const PIPE_PHRASES = {
  in: 'Liquids enter through a pipe valve placed against a flat wall, outlet facing the building, with its Inlet switched on.',
  out: 'Liquids leave through a pipe valve placed against a flat wall, inlet facing the building, with its Outlet switched on.',
  tank: 'Pipes connect directly to its flat walls, without a valve.',
};
export function pipePhrase(state, tank) {
  if (tank) return PIPE_PHRASES.tank;
  return [state === 'OpenIn' || state === 'Open' ? PIPE_PHRASES.in : null,
    state === 'OpenOut' || state === 'Open' ? PIPE_PHRASES.out : null].filter(Boolean).join(' ');
}

// One CSV row of enUS.csv: ID,Text,Comment with RFC 4180 quoting.
export function parseCsvRow(line) {
  const cells = [];
  let cell = '', quoted = false;
  for (let i = 0; i < line.length; i++) {
    const c = line[i];
    if (quoted) {
      if (c === '"' && line[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') quoted = false; else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { cells.push(cell); cell = ''; } else cell += c;
  }
  cells.push(cell);
  return cells;
}
const csvCell = (text) => /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;

// Appends the pipe phrase to Building.<id>.Description of every piped template.
async function describePipes(dataRoot, piped) {
  const path = join(dataRoot, 'Localizations', 'enUS.csv');
  const lines = (await readFile(path, 'utf8')).split('\n');
  if (lines.at(-1) !== '') throw new Error('enUS.csv must end with a newline');
  lines.pop();
  const index = new Map(lines.map((line, i) => [line.split(',')[0], i]));
  for (const {id, phrase} of piped) {
    const key = `Building.${id}.Description`;
    if (!index.has(key)) throw new Error(`${key} is missing from enUS.csv`);
    const [k, text, comment, ...rest] = parseCsvRow(lines[index.get(key)]);
    if (k !== key || rest.length) throw new Error(`${key}: unexpected CSV row`);
    if (Object.values(PIPE_PHRASES).some((phrase) => text.includes(phrase))) throw new Error(`${key} already carries the pipe phrase`);
    // Placeholder descriptions without closing punctuation get a full stop first.
    lines[index.get(key)] = [key, `${text}${/[.!?]$/.test(text) ? '' : '.'} ${phrase}`, comment].map(csvCell).join(',');
  }
  await writeFile(path, `${lines.join('\n')}\n`, 'utf8');
}

export async function applyConnections({dataRoot = join(repo, 'src/DeepFrontier/Data')} = {}) {
  const context = await liquidContext(dataRoot);
  const rows = [];
  for (const {id, file, value} of await connectionTemplates(dataRoot)) {
    const plan = await connectionPlan(id, value, context);
    if (!plan) { rows.push({id, power: false, pipes: null}); continue; }
    const counts = applyPlan(value, plan);
    await writeFile(file, JSON.stringify(value, null, 2) + '\n');
    rows.push({id, power: plan.powered, pipes: plan.state, tank: plan.liquids.tank,
      liquids: [...plan.liquids.input, ...plan.liquids.output], ...counts});
  }
  await describePipes(dataRoot, rows.filter((r) => r.pipes).map((r) => ({id: r.id, phrase: pipePhrase(r.pipes, r.tank)})));
  const powered = rows.filter((r) => r.power).length, piped = rows.filter((r) => r.pipes).length;
  const neither = rows.filter((r) => !r.power && !r.pipes).length;
  console.log(`Connections: ${powered} powered templates with shafts on every flat exterior face, ${piped} liquid templates with pipe ports there, ${neither} with neither.`);
  return rows;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const rows = await applyConnections(process.argv[2] ? {dataRoot: resolve(process.argv[2])} : {});
  for (const r of rows) console.log(JSON.stringify(r));
}
