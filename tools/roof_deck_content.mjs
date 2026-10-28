// Platformable flat roofs on every Deep Frontier building (user, 2026-10-26: "A lot of
// buildings like the mines and whatnot have flat areas on their roofs, but don't allow
// placement of anything on top. We need to fix that.").
//
// A roof cell becomes platformable (native Stackable BlockObject, as the vanilla
// BotPartFactory, Barrack, Rowhouse and Warehouse roofs) when
//  1. its Top face is flat on the exported model (outputs/connection-faces: one plane, no
//     curve or slope, measure_connection_faces.py), at a cell boundary;
//  2. the cell above is outside the building or one of its free cells, reachable from
//     outside (not enclosed) and not an access cell (door, entrance, walkway opening);
//  3. nothing of the building stands in the cell above: no static geometry in its inner box
//     (its middle, 0.31 in from every cell edge, from 0.1 over the roof up, probed
//     along all three axes; record roof.blocked: stacks, chimneys, masts, tanks, vents,
//     frames; railings and trim within 0.31 of a cell edge do not block), no animated part (dropped from the flat faces at
//     measuring), no smoke or steam emitter within one cell (TemplateAttachmentsSpec
//     under '#Finished') and no native prop on that roof (NativeBuildingPropsSpec).
// Late-game registrations mark a cell occupied when any authored part's bounding box reaches
// 0.15 into it, so a railing loop or rooftop frame claims the empty cells over a flat roof
// (the Deep Drill's front terrace). freedAbove lists those registered cells that are empty in
// fact: their middle holds no geometry, they see the sky, and they are no door, emitter or
// prop cell. lategame_building_content.mjs leaves them unoccupied, and the roof below them is
// then platformable like any other.
// Every other flat roof face open to the sky is listed with its reason. The list is generated, never
// written by hand: tools/roof_decks.json, rewritten by
//   node tools/roof_deck_content.mjs --write [dataRoot]
// from a generated Data root. Generation (create_vertical_slice_content.mjs, before the
// connection step) recomputes it, refuses a stale list, and applies it:
//   - each listed cell becomes Stackable BlockObject;
//   - every template with a stackable block gets BlockObjectNavMeshSettingsSpec
//     GenerateFloorsOnStackable true. Every vanilla Iron Teeth blueprint with a stackable
//     block sets it (33 of 33: platforms, overhangs, warehouses, barracks, rowhouses,
//     BotPartFactory, HydroponicGarden). AddEdgesAddedByStackable then lays native floor
//     edges over each stackable block, so beavers can walk onto the roof from a stair, path
//     or platform and build there.
// Models, footprints and occupations do not change. The connection step then offers roof
// shaft faces on these cells (connection_content.mjs: roof faces only on stackable blocks).
import {readFile, writeFile} from 'node:fs/promises';
import {dirname, join, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {accessCells, connectionFaces, connectionTemplates, externalAccess, faceRecord} from './connection_content.mjs';
import {LATEGAME} from './lategame_building_content.mjs';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const LIST = 'tools/roof_decks.json';
export const EMITTER_REACH = 1;      // cells: smoke/steam plume around a mouth
export const EMITTER_RISE = 3;       // layers above the roof a mouth still clouds it
export const REASONS = {
  enclosed: 'enclosed, or a door, entrance or walkway cell above',
  blocked: 'building geometry in the middle of the cell above (stack, chimney, mast, tank, vent or frame)',
  animated: 'animated part above',
  emitter: 'smoke or steam emitter above',
  prop: 'native prop on the roof',
  above: 'a registered room, walkway, deck or machinery cell of the building above',
};
const key = (c) => c.join(',');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));

// Model-space point (Unity X, Y up, Z) of a child of '#Finished' -> native grid.
const grid = (p, baseZ) => [p.X, p.Z, p.Y + baseZ];

export async function roofDeckPlan(id, value, root = repo) {
  const record = await faceRecord(id, value, root);
  const spec = value.BlockObjectSpec, {X: w, Y: h, Z: layers} = spec.Size, baseZ = spec.BaseZ;
  const block = ([x, y, z]) => spec.Blocks[(z * h + y) * w + x];
  const roofOf = ([x, y, z]) => block([x, y, z]).Occupations !== 'None' && (z + 1 >= layers || block([x, y, z + 1]).Occupations === 'None');
  // Exterior and access test of the connection rule, as if every roof could hold a shaft.
  const copy = structuredClone(value);
  for (const b of copy.BlockObjectSpec.Blocks) if (b.Stackable === 'None') b.Stackable = 'BlockObject';
  const {extra, skipSides} = await externalAccess(id, copy, root);
  const {cells: access, own} = accessCells(copy, extra);
  const open = new Set(connectionFaces(copy, record.faces, {access, own, skipSides}).filter((f) => f[3] === 'Top').map((f) => key(f.slice(0, 3))));
  const blocked = new Set(record.roof.blocked.map(key));
  const emitters = (value.TemplateAttachmentsSpec?.Attachments ?? []).filter((a) => a.Parent === '#Finished').map((a) => grid(a.Position, baseZ));
  const props = (value.NativeBuildingPropsSpec?.Props ?? []).map((p) => ({at: grid(p.Position, baseZ),
    reach: .5 + .5 * Math.max(p.Scale.X, p.Scale.Y, p.Scale.Z)}));
  const near = ([x, y, z], [px, py, pz], reach, rise) => Math.abs(px - (x + .5)) <= reach && Math.abs(py - (y + .5)) <= reach
    && pz >= z + 1 - .1 && pz <= z + 1 + rise;
  const platformable = [], excluded = [];
  const flat = record.faces.filter((f) => f[3] === 'Top').map((f) => f.slice(0, 3)).filter(roofOf);
  for (const c of flat) {
    let reason = null;
    if (!open.has(key(c))) reason = REASONS.enclosed;
    else if (blocked.has(key(c))) reason = REASONS.blocked;
    else if (emitters.some((e) => near(c, e, EMITTER_REACH, EMITTER_RISE))) reason = REASONS.emitter;
    else if (props.some((p) => near(c, p.at, p.reach, 1))) reason = REASONS.prop;
    if (reason) excluded.push({cell: c, reason}); else platformable.push(c);
  }
  // Flat roofs open to the sky with a registered block of the building above (not freed).
  const covered = new Set(record.roof.covered.map(key));
  for (const f of record.faces) {
    const c = f.slice(0, 3);
    if (f[3] !== 'Top' || block(c).Occupations === 'None' || roofOf(c) || covered.has(key(c))) continue;
    excluded.push({cell: c, reason: blocked.has(key(c)) ? REASONS.blocked : REASONS.above});
  }
  for (const c of record.roof.animated.filter(roofOf)) excluded.push({cell: c, reason: REASONS.animated});
  const order = (a, b) => a[2] - b[2] || a[1] - b[1] || a[0] - b[0];
  platformable.sort(order);
  excluded.sort((a, b) => order(a.cell, b.cell));
  return {platformable, excluded};
}

// Every template that owns its model and has at least one flat roof face.
export async function roofDeckPlans(dataRoot, root = repo) {
  const plans = {};
  for (const {id, value} of await connectionTemplates(dataRoot)) {
    const plan = await roofDeckPlan(id, value, root);
    if (plan.platformable.length || plan.excluded.length) plans[id] = plan;
  }
  return plans;
}

// Registered late-game cells over a flat roof that hold nothing (see the header).
export async function freedAbove(id, value, root = repo) {
  if (!LATEGAME.has(id)) return [];
  const registration = await readJson(join(root, 'outputs/lategame-studies', `${id}-registration.json`));
  const record = await faceRecord(id, value, root);
  const occupied = new Set(registration.occupied.map(key));
  const doors = new Set(registration.doors.flatMap((d) => [d.doorstep, d.entrance]).map(key));
  const blocked = new Set(record.roof.blocked.map(key)), covered = new Set(record.roof.covered.map(key));
  const baseZ = value.BlockObjectSpec.BaseZ;
  const emitters = (value.TemplateAttachmentsSpec?.Attachments ?? []).filter((a) => a.Parent === '#Finished').map((a) => grid(a.Position, baseZ));
  const props = (value.NativeBuildingPropsSpec?.Props ?? []).map((p) => ({at: grid(p.Position, baseZ), reach: .5 + .5 * Math.max(p.Scale.X, p.Scale.Y, p.Scale.Z)}));
  const near = ([x, y, z], [px, py, pz], reach, rise) => Math.abs(px - (x + .5)) <= reach && Math.abs(py - (y + .5)) <= reach
    && pz >= z + 1 - .1 && pz <= z + 1 + rise;
  const freed = [];
  for (const [x, y, z, d] of record.faces) {
    const c = [x, y, z], above = [x, y, z + 1];
    if (d !== 'Top' || !occupied.has(key(c)) || !occupied.has(key(above)) || z + 1 >= registration.height) continue;
    if (blocked.has(key(c)) || covered.has(key(c)) || doors.has(key(above))) continue;
    if (emitters.some((e) => near(c, e, EMITTER_REACH, EMITTER_RISE)) || props.some((p) => near(c, p.at, p.reach, 1))) continue;
    freed.push(above);
  }
  return freed;
}

export function listDocument(plans, freed = {}) {
  return {
    scope: 'Generated by tools/roof_deck_content.mjs --write from outputs/connection-faces and the generated blueprints; do not edit by hand.',
    rule: 'Flat Top face (one plane, no curve or slope; glass counts) at a cell boundary; free, exterior, non-access cell above; '
      + 'no building geometry in the middle of the cell above, animated part, smoke/steam emitter or native prop above.',
    coordinateSystem: 'Native grid XYZ, blueprint block indices; the listed cell is the roof cell, things stand in the cell above',
    freedAbove: freed,
    buildings: plans,
  };
}

const NAV_DEFAULT = {NoAutoWalls: false, GenerateFloorsOnStackable: true, EdgeGroups: [], UnblockedCoordinates: [], BlockedEdges: []};

export async function applyRoofDecks({dataRoot = join(repo, 'src/DeepFrontier/Data')} = {}) {
  const list = (await readJson(join(repo, LIST))).buildings;
  const rows = [];
  for (const {id, file, value} of await connectionTemplates(dataRoot)) {
    const plan = await roofDeckPlan(id, value);
    const listed = list[id] ?? {platformable: [], excluded: []};
    if (JSON.stringify(listed) !== JSON.stringify(plan.platformable.length || plan.excluded.length ? plan : {platformable: [], excluded: []}))
      throw new Error(`${id}: ${LIST} is stale; rerun node tools/roof_deck_content.mjs --write <generated Data>`);
    const spec = value.BlockObjectSpec;
    let added = 0;
    for (const [x, y, z] of plan.platformable) {
      const b = spec.Blocks[(z * spec.Size.Y + y) * spec.Size.X + x];
      if (b.Stackable === 'None') { b.Stackable = 'BlockObject'; added++; }
    }
    let floors = false;
    if (spec.Blocks.some((b) => b.Stackable !== 'None') && !value.BlockObjectNavMeshSettingsSpec?.GenerateFloorsOnStackable) {
      value.BlockObjectNavMeshSettingsSpec = {...NAV_DEFAULT, ...value.BlockObjectNavMeshSettingsSpec, GenerateFloorsOnStackable: true};
      floors = true;
    }
    if (added || floors) await writeFile(file, JSON.stringify(value, null, 2) + '\n');
    rows.push({id, platformable: plan.platformable.length, added, excluded: plan.excluded.length, floors});
  }
  console.log(`Roof decks: ${rows.filter((r) => r.platformable).length} templates with platformable flat roofs `
    + `(${rows.reduce((n, r) => n + r.platformable, 0)} cells, ${rows.reduce((n, r) => n + r.added, 0)} newly stackable); `
    + `GenerateFloorsOnStackable turned on for ${rows.filter((r) => r.floors).length}.`);
  return rows;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const args = process.argv.slice(2);
  const write = args.includes('--write');
  const dataRoot = resolve(args.find((a) => !a.startsWith('--')) ?? join(repo, 'src/DeepFrontier/Data'));
  if (write) {
    const freed = {};
    for (const {id, value} of await connectionTemplates(dataRoot)) {
      const cells = await freedAbove(id, value);
      if (cells.length) freed[id] = cells;
    }
    const plans = await roofDeckPlans(dataRoot);
    await writeFile(join(repo, LIST), JSON.stringify(listDocument(plans, freed), null, 1) + '\n');
    for (const [id, cells] of Object.entries(freed)) console.log(id, 'freed above roof', cells.length);
    for (const [id, p] of Object.entries(plans)) console.log(id, 'platformable', p.platformable.length, 'excluded', p.excluded.length);
  } else {
    await applyRoofDecks({dataRoot});
  }
}
