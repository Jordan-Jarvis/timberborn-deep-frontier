// Roof hardpoints: steel legs on non-flat roofs (docs/platforms-design.md, slice 3 "D1").
// User, 2026-10-29: platforms should "connect to and sit on top of non flat topped buildings
// (going through/into the building) allowing for easier building on top of existing
// infrastructure".
//
// Flat roofs are platformable for everything (tools/roof_deck_content.mjs). A hardpoint is
// the top cell of any other column of a building: its top-most occupied block, with nothing of
// the building above it, whose roof is pitched, gabled, sawtooth, curved or otherwise not a
// flat platformable face. It becomes a native stackable block (Stackable BlockObject) so a
// steel column can stand on it with fully native support, cursor picking, load validation,
// stack deletion and the building's "object atop" deletion blocker, and the column's
// hardpoint sleeve (a one-layer column segment one layer down) shows the leg entering the
// roof. Only steel supports may use it: RoofHardpointValidator (C#,
// src/DeepFrontier/Scripts/SteelStructures/RoofHardpoints.cs) rejects every other preview
// whose foundation would rest on a hardpoint, so paths, platforms and buildings still need a
// flat roof. A top cell qualifies when
//  1. it is not a flat roof face (those are platformable or excluded with a reason by
//     roof_deck_content.mjs), not already stackable by its family, and a roof: its block has
//     Top occupation (a porch or walkway floor is not), it is not below the building's BaseZ
//     (the Fish Hatchery's pens stand in the water), and the building has no contract that
//     keeps every block unstackable (CLOSED: the Deep Well);
//  2. the cell above is exterior and no access cell (the roof-deck rule: connectionFaces with
//     every block stackable, so the cell above can carry a column);
//  3. nothing of the building stands in the middle of the cell above, nothing hangs over it,
//     and no animated part moves in it or in the top cell (outputs/roof-hardpoints,
//     tools/asset-pipeline/measure_roof_hardpoints.py, measured on the exported model);
//  4. no smoke or steam mouth in its column and no native prop in the middle of the cell above
//     (the roof-deck emitter and prop rules).
// Everything else is listed with its reason. The list is generated, never written by hand:
// tools/roof_hardpoints.json, rewritten by
//   node tools/roof_hardpoint_content.mjs --write [dataRoot]
// from a generated Data root. Generation (create_vertical_slice_content.mjs, after the roof
// decks and before the connection step) recomputes it, refuses a stale list, and applies it:
//   - each hardpoint becomes Stackable BlockObject;
//   - the blueprint gets RoofHardpointsSpec {Cells} (the C# validator and sleeve read it);
//   - GenerateFloorsOnStackable true, as for every stackable template (native floor edges over
//     the hardpoint, which also let builders reach a column standing there).
// Hardpoints are never flat, so the connection step offers no shaft or pipe face on them (it
// offers Top faces only on measured flat faces). Removing a hardpoint later would delete what
// stands on it at load: the list only grows unless a model changes.
import {createHash} from 'node:crypto';
import {readFile, writeFile} from 'node:fs/promises';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {accessCells, connectionFaces, connectionTemplates, externalAccess, faceRecord} from './connection_content.mjs';
import {EMITTER_REACH, EMITTER_RISE, INNER_INSET, roofDeckPlan} from './roof_deck_content.mjs';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const LIST = 'tools/roof_hardpoints.json';
export const RECORDS = 'outputs/roof-hardpoints';
export const REASONS = {
  closed: 'the building keeps every block unstackable (CLOSED)',
  below: 'below the base layer of the building (in the water or bank it stands in), not a roof',
  floor: 'a floor the building is walked on (no Top occupation), not a roof',
  enclosed: 'enclosed, or a door, entrance or walkway cell above',
  blocked: 'building geometry in the middle of the cell above',
  covered: 'building geometry hangs over the cell',
  animated: 'animated part in the top cell or the cell above',
  emitter: 'smoke or steam mouth in the cell column',
  prop: 'native prop in the middle of the cell above',
};
const key = (c) => c.join(',');
// Buildings whose own contract forbids any stackable block, with the check that holds it.
export const CLOSED = {
  DeepWell: 'validate_deep_well_content.mjs: the drill hangs over a water source and no Deep Well block may be stackable',
};
// Structural pieces (masonry, platforms, decks, overhangs, bridges, columns, the leg deck tools) are supports
// or paths themselves, not buildings to build over: they get no hardpoints.
const structural = JSON.parse(await readFile(join(repo, 'tools/structural_content.json'), 'utf8'));
export const STRUCTURES = new Set([...structural.buildings, ...structural.legDecks.tools].map((b) => b.id));
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const grid = (p, baseZ) => [p.X, p.Z, p.Y + baseZ];
const propReach = (p) => .5 - INNER_INSET + .5 * Math.max(p.Scale.X, p.Scale.Y, p.Scale.Z);

// Hardpoint record of a template, checked against the export it measured.
export async function hardpointRecord(id, value, root = repo) {
  const record = await readJson(join(root, RECORDS, `${id}.json`));
  const model = value.Children?.['#Finished']?.TimbermeshSpec?.Model;
  const spec = value.BlockObjectSpec;
  if (record.template !== id || record.model !== model) throw new Error(`${id}: roof tops were measured on ${record.model}, not ${model}`);
  if (JSON.stringify(record.size) !== JSON.stringify([spec.Size.X, spec.Size.Y, spec.Size.Z]) || record.baseZ !== spec.BaseZ)
    throw new Error(`${id}: roof tops were measured over another Size/BaseZ; rerun measure_roof_hardpoints.py`);
  const digest = createHash('sha256').update(await readFile(join(root, record.export))).digest('hex');
  if (digest !== record.exportSha256) throw new Error(`${id}: ${record.export} changed since its roof tops were measured; rerun measure_roof_hardpoints.py`);
  return record;
}

// Top cells of a blueprint: occupied, nothing occupied above (grid order z, y, x).
export function topCells(value) {
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size;
  const occupied = (x, y, z) => spec.Blocks[(z * h + y) * w + x].Occupations !== 'None';
  const cells = [];
  for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
    for (let z = layers - 1; z >= 0; z--) if (occupied(x, y, z)) { cells.push([x, y, z]); break; }
  return cells.sort((a, b) => a[2] - b[2] || a[1] - b[1] || a[0] - b[0]);
}

export async function roofHardpointPlan(id, value, root = repo) {
  if (STRUCTURES.has(id)) return {hardpoints: [], excluded: [], tops: 0, flat: 0};
  const spec = value.BlockObjectSpec, {X: w, Y: h} = spec.Size, baseZ = spec.BaseZ;
  const block = ([x, y, z]) => spec.Blocks[(z * h + y) * w + x];
  // Hardpoints this step applied earlier (a generated Data root) count as not yet stackable.
  const mine = new Set((value.RoofHardpointsSpec?.Cells ?? []).map((c) => key([c.X, c.Y, c.Z])));
  const deck = await roofDeckPlan(id, value, root);
  const flat = new Set([...deck.platformable, ...deck.excluded.map((e) => e.cell)].map(key));
  const record = await hardpointRecord(id, value, root);
  const measured = new Map(record.cells.map((c) => [key(c.cell), c]));
  const tops = topCells(value);
  if (JSON.stringify(record.cells.map((c) => c.cell)) !== JSON.stringify(tops))
    throw new Error(`${id}: measured roof tops differ from the blueprint's top cells; rerun measure_roof_hardpoints.py`);
  const candidates = tops.filter((c) => !flat.has(key(c)) && (block(c).Stackable === 'None' || mine.has(key(c))));
  // Exterior and access test of the roof-deck and connection rules, as if every roof could
  // hold a column (connectionFaces needs a stackable block under the cell above).
  const copy = structuredClone(value);
  for (const b of copy.BlockObjectSpec.Blocks) if (b.Stackable === 'None') b.Stackable = 'BlockObject';
  const {extra, skipSides} = await externalAccess(id, copy, root);
  const {cells: access, own} = accessCells(copy, extra);
  const open = new Set(connectionFaces(copy, candidates.map((c) => [...c, 'Top']), {access, own, skipSides}).map((f) => key(f.slice(0, 3))));
  const emitters = (value.TemplateAttachmentsSpec?.Attachments ?? []).filter((a) => a.Parent === '#Finished').map((a) => grid(a.Position, baseZ));
  const props = (value.NativeBuildingPropsSpec?.Props ?? []).map((p) => ({at: grid(p.Position, baseZ), reach: propReach(p)}));
  const near = ([x, y, z], [px, py, pz], reach, rise) => Math.abs(px - (x + .5)) <= reach && Math.abs(py - (y + .5)) <= reach
    && pz >= z + 1 - .1 && pz <= z + 1 + rise;
  const hardpoints = [], excluded = [];
  for (const c of candidates) {
    const m = measured.get(key(c));
    const occupations = block(c).Occupations;
    let reason = null;
    if (Object.hasOwn(CLOSED, id)) reason = REASONS.closed;
    else if (c[2] < baseZ) reason = REASONS.below;
    else if (occupations !== 'All' && !occupations.split(', ').includes('Top')) reason = REASONS.floor;
    else if (!open.has(key(c))) reason = REASONS.enclosed;
    else if (m.blocked) reason = REASONS.blocked;
    else if (m.covered) reason = REASONS.covered;
    else if (m.animated) reason = REASONS.animated;
    else if (emitters.some((e) => near(c, e, EMITTER_REACH, EMITTER_RISE))) reason = REASONS.emitter;
    else if (props.some((p) => near(c, p.at, p.reach, 1))) reason = REASONS.prop;
    if (reason) excluded.push({cell: c, reason}); else hardpoints.push(c);
  }
  return {hardpoints, excluded, tops: tops.length, flat: tops.filter((c) => flat.has(key(c))).length};
}

export async function roofHardpointPlans(dataRoot, root = repo) {
  const plans = {};
  for (const {id, value} of await connectionTemplates(dataRoot)) {
    const {hardpoints, excluded} = await roofHardpointPlan(id, value, root);
    if (hardpoints.length || excluded.length) plans[id] = {hardpoints, excluded};
  }
  return plans;
}

export function listDocument(plans) {
  return {
    scope: 'Generated by tools/roof_hardpoint_content.mjs --write from outputs/roof-hardpoints, outputs/connection-faces and the generated blueprints; do not edit by hand.',
    rule: 'Top cell of a building column (nothing of the building above) that is no flat roof face and not already stackable; exterior, non-access '
      + 'cell above; no building geometry in the middle of the cell above or over it, no animated part in the top cell or the cell above, '
      + 'no smoke/steam mouth in its column, no native prop in the middle of the cell above. Only steel supports may stand on it.',
    coordinateSystem: 'Native grid XYZ, blueprint block indices; the listed cell is the top cell, a steel column stands in the cell above',
    buildings: plans,
  };
}

const NAV_DEFAULT = {NoAutoWalls: false, GenerateFloorsOnStackable: true, EdgeGroups: [], UnblockedCoordinates: [], BlockedEdges: []};
const xyz = ([X, Y, Z]) => ({X, Y, Z});

export async function applyRoofHardpoints({dataRoot = join(repo, 'src/DeepFrontier/Data')} = {}) {
  const list = (await readJson(join(repo, LIST))).buildings;
  const seen = new Set();
  let templates = 0, cells = 0;
  for (const {id, file, value} of await connectionTemplates(dataRoot)) {
    const {hardpoints, excluded} = await roofHardpointPlan(id, value);
    const plan = hardpoints.length || excluded.length ? {hardpoints, excluded} : null;
    if (plan) seen.add(id);
    if (JSON.stringify(list[id] ?? null) !== JSON.stringify(plan))
      throw new Error(`${id}: ${LIST} is stale; rerun node tools/roof_hardpoint_content.mjs --write <generated Data>`);
    if (!hardpoints.length) continue;
    if (value.RoofHardpointsSpec) throw new Error(`${id}: RoofHardpointsSpec applied twice; regenerate from the start`);
    const spec = value.BlockObjectSpec;
    for (const [x, y, z] of hardpoints) {
      const b = spec.Blocks[(z * spec.Size.Y + y) * spec.Size.X + x];
      if (b.Stackable !== 'None') throw new Error(`${id}: hardpoint ${[x, y, z]} is already stackable`);
      b.Stackable = 'BlockObject';
    }
    value.RoofHardpointsSpec = {Cells: hardpoints.map(xyz)};
    value.BlockObjectNavMeshSettingsSpec = {...NAV_DEFAULT, ...value.BlockObjectNavMeshSettingsSpec, GenerateFloorsOnStackable: true};
    await writeFile(file, JSON.stringify(value, null, 2) + '\n');
    templates++; cells += hardpoints.length;
  }
  for (const id of Object.keys(list)) if (!seen.has(id)) throw new Error(`${id}: listed in ${LIST} but has no roof top to decide (or is gone)`);
  console.log(`Roof hardpoints: ${cells} cells on ${templates} templates where steel legs can stand on a roof that is not flat.`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const write = args.includes('--write');
  const dataRoot = resolve(args.find((a) => !a.startsWith('--')) ?? join(repo, 'src/DeepFrontier/Data'));
  if (write) {
    const plans = await roofHardpointPlans(dataRoot);
    await writeFile(join(repo, LIST), JSON.stringify(listDocument(plans), null, 1) + '\n');
    for (const [id, p] of Object.entries(plans)) console.log(id, 'hardpoints', p.hardpoints.length, 'excluded', p.excluded.length);
  } else {
    await applyRoofHardpoints({dataRoot});
  }
}
