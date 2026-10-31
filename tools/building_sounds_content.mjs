// Native building sounds for every Deep Frontier building template
// (tools/building_sounds.json; contract and evidence in docs/sounds.md).
//
// Run in canonical generation once every building template exists: after
// radiation (which writes the radiation buildings and springs) and workforce
// risks, before the automation audit:
//   await (await import('./building_sounds_content.mjs')).applyBuildingSounds();
// or standalone: node tools/building_sounds_content.mjs [<repo root>]
//
// It writes only these fields of the listed templates:
// - BuildingSpec.SelectionSoundName and BuildingSpec.LoopingSoundName;
// - PowerGeneratorSoundsSpec ({}) on entries whose loop driver is
//   powerGenerator (a mechanical generator that is not a workshop);
// - BasicSelectionSoundSpec.SoundName/AlternativeSoundName on the listed
//   natural objects.
// Files whose sound fields already match are not rewritten.
//
// It fails without writing anything when:
// - a template under Data/Buildings with a BuildingSpec or
//   BasicSelectionSoundSpec has no entry, a listed template is missing, or a
//   planned building has appeared without a buildings entry;
// - a sound name is not in the recorded 1.1.2.8 registry;
// - a non-empty loop has no native driver, or more than one, or a driver
//   other than the declared one (two drivers toggle the same BuildingSounds
//   against each other);
// - PowerGeneratorSoundsSpec is present on an entry that does not declare it,
//   or is declared on a template that is not a non-workshop generator;
// - a file to be rewritten is not in canonical generator format, or the hydro
//   catalog's loopingSound disagrees with the turbine entry.
import {readdir, readFile, writeFile} from 'node:fs/promises';
import {resolve, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const CONFIG = 'tools/building_sounds.json';
export const DATA = ['src', 'DeepFrontier', 'Data'];
export const HYDRO_CATALOG = 'tools/hydro_content.json';
export const COLLECTION = 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json';

// Native 1.1.2.8 key prefixes (Timberborn.Buildings BuildingSelectionSound and
// BuildingSounds, Timberborn.CoreSound BasicSelectionSound).
export const PREFIX = {
  selection: 'UI.Buildings.Selected.',
  looping: 'Environment.Buildings.Loop.',
  basicSelection: 'UI.BasicSelection.',
};
// Spec whose decorator calls BuildingSounds.ToggleSound in 1.1.2.8:
// WorkshopSpec -> Workshop -> WorkshopSounds (Workshop.CurrentlyWorking, every tick)
// PowerGeneratorSoundsSpec -> PowerGeneratorSounds (ActiveAndPowered && OutputMultiplier > 0)
// AttractionSpec -> Attraction -> EnterableSounds (anyone inside)
// DwellingSpec -> Dwelling -> EnterableSounds (anyone inside)
// RangedEffectBuildingSpec -> RangedEffectBuilding (unpaused and powered)
// UndergroundWaterSourceDrillSpec -> UndergroundWaterSourceDrillSounds (water strength > 0)
export const LOOP_DRIVERS = {
  workshop: 'WorkshopSpec',
  powerGenerator: 'PowerGeneratorSoundsSpec',
  attraction: 'AttractionSpec',
  dwelling: 'DwellingSpec',
  rangedEffect: 'RangedEffectBuildingSpec',
  aquiferDrill: 'UndergroundWaterSourceDrillSpec',
};
export const FAMILIES = ['steam/generator', 'furnace/smelter', 'gear/workshop', 'pump/water', 'mining',
  'civic/service', 'food/agri', 'storage', 'platform/levee'];
const BUILDING_KEYS = ['template', 'selection', 'looping', 'loopDriver', 'family', 'comment'];
const BASIC_KEYS = ['template', 'sound', 'alternative', 'comment'];
const PLANNED_KEYS = ['selection', 'looping', 'loopDriver', 'family', 'comment'];
const TOP_KEYS = ['status', 'game', 'registry', 'buildings', 'basicSelection', 'planned'];
const REGISTRY_KEYS = ['source', 'selection', 'looping', 'basicSelection'];

const BOM = '﻿';
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const canonical = (value) => `${JSON.stringify(value, null, 2)}\n`;
const keysExactly = (value, keys, where, errors) => {
  if (!value || typeof value !== 'object' || Array.isArray(value)) { errors.push(`${where}: must be an object`); return false; }
  const actual = Object.keys(value);
  const missing = keys.filter((k) => !actual.includes(k));
  const unknown = actual.filter((k) => !keys.includes(k));
  if (missing.length) errors.push(`${where}: missing ${missing.join(', ')}`);
  if (unknown.length) errors.push(`${where}: unknown ${unknown.join(', ')}`);
  return !missing.length && !unknown.length;
};
const isText = (value) => typeof value === 'string';

export const dataRootOf = (root) => resolve(root, ...DATA);
export const templateFile = (dataRoot, template) => resolve(dataRoot, `${template}.json`);
export const templateName = (template) => template.split('/').pop().replace(/\.blueprint$/, '');
export const entryId = (template) => templateName(template).replace(/\.IronTeeth$/, '');

async function readText(path) {
  try { return await readFile(path, 'utf8'); } catch (error) {
    if (error.code === 'ENOENT') return null;
    throw error;
  }
}
const parse = (text, path) => {
  try { return JSON.parse(text.startsWith(BOM) ? text.slice(1) : text); } catch (error) {
    throw new Error(`${path}: ${error.message}`);
  }
};

// Config schema and registry membership. Returns {config, errors}.
export async function loadBuildingSounds(root = defaultRoot) {
  const path = resolve(root, CONFIG);
  const config = parse(await readFile(path, 'utf8'), path);
  const errors = [];
  if (!keysExactly(config, TOP_KEYS, CONFIG, errors)) return {config, errors};
  if (config.game !== '1.1.2.8-ffc2de0-xsw') errors.push(`${CONFIG}: game must be the inspected 1.1.2.8-ffc2de0-xsw`);
  if (!keysExactly(config.registry, REGISTRY_KEYS, 'registry', errors)) return {config, errors};
  const registry = {};
  for (const kind of ['selection', 'looping', 'basicSelection']) {
    const list = config.registry[kind];
    if (!Array.isArray(list) || !list.length || !list.every(isText) || new Set(list).size !== list.length || list.includes(''))
      errors.push(`registry.${kind}: must be a non-empty list of distinct sound names`);
    registry[kind] = new Set(Array.isArray(list) ? list : []);
  }
  const checkSounds = (where, entry) => {
    if (!registry.selection.has(entry.selection))
      errors.push(`${where}: selection ${JSON.stringify(entry.selection)} is not a 1.1.2.8 ${PREFIX.selection}* clip`);
    if (!isText(entry.looping) || (entry.looping !== '' && !registry.looping.has(entry.looping)))
      errors.push(`${where}: looping ${JSON.stringify(entry.looping)} is not '' or a 1.1.2.8 ${PREFIX.looping}* clip`);
    if (entry.loopDriver !== 'none' && !(entry.loopDriver in LOOP_DRIVERS))
      errors.push(`${where}: loopDriver ${JSON.stringify(entry.loopDriver)} is not none or one of ${Object.keys(LOOP_DRIVERS).join(', ')}`);
    if ((entry.looping === '') !== (entry.loopDriver === 'none'))
      errors.push(`${where}: an empty loop needs loopDriver none, and loopDriver none needs an empty loop`);
    if (!FAMILIES.includes(entry.family)) errors.push(`${where}: family ${JSON.stringify(entry.family)} is not one of ${FAMILIES.join(', ')}`);
    if (!isText(entry.comment) || entry.comment.trim().length < 40) errors.push(`${where}: comment must explain the choice`);
  };
  const templates = new Set();
  for (const [id, entry] of Object.entries(config.buildings ?? {})) {
    const where = `buildings.${id}`;
    if (!keysExactly(entry, BUILDING_KEYS, where, errors)) continue;
    if (!isText(entry.template) || !entry.template.startsWith('Buildings/') || entryId(entry.template) !== id)
      errors.push(`${where}: template must be a Buildings/ blueprint path ending in ${id}[.IronTeeth].blueprint`);
    if (templates.has(entry.template)) errors.push(`${where}: template listed twice`);
    templates.add(entry.template);
    checkSounds(where, entry);
  }
  for (const [id, entry] of Object.entries(config.basicSelection ?? {})) {
    const where = `basicSelection.${id}`;
    if (!keysExactly(entry, BASIC_KEYS, where, errors)) continue;
    if (!isText(entry.template) || entryId(entry.template) !== id) errors.push(`${where}: template must end in ${id}.blueprint`);
    if (templates.has(entry.template)) errors.push(`${where}: template listed twice`);
    templates.add(entry.template);
    if (!registry.basicSelection.has(entry.sound)) errors.push(`${where}: sound ${JSON.stringify(entry.sound)} is not a 1.1.2.8 ${PREFIX.basicSelection}* clip`);
    if (!isText(entry.alternative) || (entry.alternative !== '' && !registry.basicSelection.has(`${entry.alternative}.AltSound`)))
      errors.push(`${where}: alternative ${JSON.stringify(entry.alternative)} is not '' or a name with a ${PREFIX.basicSelection}<name>.AltSound clip`);
    if (!isText(entry.comment) || entry.comment.trim().length < 40) errors.push(`${where}: comment must explain the choice`);
  }
  for (const [id, entry] of Object.entries(config.planned ?? {})) {
    const where = `planned.${id}`;
    if (!keysExactly(entry, PLANNED_KEYS, where, errors)) continue;
    if (id in (config.buildings ?? {})) errors.push(`${where}: also listed in buildings`);
    checkSounds(where, entry);
  }
  return {config, errors};
}

// Every blueprint under Data/Buildings that plays a selection sound. A
// same-path partial patch of a vanilla template (no TemplateSpec, e.g. the
// Terrain Block's raised science in tools/vanilla_tool_overrides.mjs) keeps
// the vanilla sounds.
export async function soundTemplates(dataRoot) {
  const base = resolve(dataRoot, 'Buildings');
  const found = [];
  const walk = async (dir) => {
    for (const entry of await readdir(dir, {withFileTypes: true})) {
      const path = resolve(dir, entry.name);
      if (entry.isDirectory()) await walk(path);
      else if (entry.name.endsWith('.blueprint.json')) {
        const value = parse(await readFile(path, 'utf8'), path);
        if (value.TemplateSpec && (value.BuildingSpec || value.BasicSelectionSoundSpec))
          found.push(relative(dataRoot, path).split(sep).join('/').replace(/\.json$/, ''));
      }
    }
  };
  await walk(base);
  return found.sort();
}

// Native drivers present on a blueprint, by loop-driver name.
export const presentDrivers = (value) => Object.entries(LOOP_DRIVERS).filter(([, spec]) => spec in value).map(([name]) => name);

// The blueprint with this module's fields applied, or errors.
export function expectedBuilding(id, entry, value) {
  const errors = [];
  const where = `buildings.${id}`;
  if (value.TemplateSpec?.TemplateName !== templateName(entry.template))
    errors.push(`${where}: TemplateSpec.TemplateName ${value.TemplateSpec?.TemplateName} != ${templateName(entry.template)}`);
  if (!value.BuildingSpec) { errors.push(`${where}: template has no BuildingSpec`); return {errors}; }
  if (value.BasicSelectionSoundSpec) errors.push(`${where}: template also has BasicSelectionSoundSpec`);
  const next = structuredClone(value);
  next.BuildingSpec.SelectionSoundName = entry.selection;
  next.BuildingSpec.LoopingSoundName = entry.looping;
  if (entry.loopDriver === 'powerGenerator') {
    if (!(next.MechanicalNodeSpec?.PowerOutput > 0)) errors.push(`${where}: powerGenerator driver on a template without MechanicalNodeSpec.PowerOutput > 0`);
    if (next.WorkshopSpec) errors.push(`${where}: powerGenerator driver on a workshop; WorkshopSounds already drives it`);
    if ('PowerGeneratorSoundsSpec' in next && !same(next.PowerGeneratorSoundsSpec, {}))
      errors.push(`${where}: PowerGeneratorSoundsSpec must be the empty native spec`);
    next.PowerGeneratorSoundsSpec = {};
  } else if ('PowerGeneratorSoundsSpec' in next) {
    errors.push(`${where}: template carries PowerGeneratorSoundsSpec but the entry declares loopDriver ${entry.loopDriver}`);
  }
  const drivers = presentDrivers(next);
  if (entry.looping !== '' && !same(drivers, [entry.loopDriver]))
    errors.push(`${where}: loop ${entry.looping} needs exactly the ${entry.loopDriver} driver (${LOOP_DRIVERS[entry.loopDriver]}); template has [${drivers.join(', ')}]`);
  return {errors, value: next};
}

export function expectedBasic(id, entry, value) {
  const errors = [];
  const where = `basicSelection.${id}`;
  if (value.TemplateSpec?.TemplateName !== templateName(entry.template))
    errors.push(`${where}: TemplateSpec.TemplateName ${value.TemplateSpec?.TemplateName} != ${templateName(entry.template)}`);
  if (value.BuildingSpec) errors.push(`${where}: template has a BuildingSpec; list it under buildings`);
  if (!value.BasicSelectionSoundSpec) { errors.push(`${where}: template has no BasicSelectionSoundSpec`); return {errors}; }
  const next = structuredClone(value);
  next.BasicSelectionSoundSpec.SoundName = entry.sound;
  next.BasicSelectionSoundSpec.AlternativeSoundName = entry.alternative;
  return {errors, value: next};
}

// Coverage, drivers and the hydro cross-check. Returns {config, errors, plan}
// where plan lists {path, text, current, expected} for every listed template.
export async function planBuildingSounds(root = defaultRoot) {
  const {config, errors} = await loadBuildingSounds(root);
  if (errors.length) return {config, errors, plan: []};
  const dataRoot = dataRootOf(root);
  const buildings = Object.entries(config.buildings);
  const basics = Object.entries(config.basicSelection);
  const listed = new Set([...buildings, ...basics].map(([, e]) => e.template));
  const inData = await soundTemplates(dataRoot);
  for (const template of inData) {
    if (listed.has(template)) continue;
    const id = entryId(template);
    errors.push(id in config.planned
      ? `${template}: planned building ${id} now exists; move its entry from planned to buildings with this template path`
      : `${template}: Deep Frontier building template has no entry in ${CONFIG}`);
  }
  const collection = parse(await readFile(resolve(dataRoot, COLLECTION), 'utf8'), COLLECTION).TemplateCollectionSpec?.['Blueprints#append'];
  if (!Array.isArray(collection)) errors.push(`${COLLECTION}: Blueprints#append missing`);
  else for (const template of collection) if (!listed.has(template)) {
    const value = parse((await readText(templateFile(dataRoot, template))) ?? '{}', template);
    if (value.BuildingSpec || value.BasicSelectionSoundSpec) errors.push(`${template}: collected building template has no entry in ${CONFIG}`);
  }
  const plan = [];
  for (const [kind, entries, expect] of [['buildings', buildings, expectedBuilding], ['basicSelection', basics, expectedBasic]]) {
    for (const [id, entry] of entries) {
      const path = templateFile(dataRoot, entry.template);
      const text = await readText(path);
      if (text === null) { errors.push(`${kind}.${id}: listed template ${entry.template} is missing from Data`); continue; }
      const current = parse(text, path);
      const result = expect(id, entry, current);
      errors.push(...result.errors);
      if (result.value) plan.push({kind, id, path, text, current, expected: result.value});
    }
  }
  const hydro = parse(await readFile(resolve(root, HYDRO_CATALOG), 'utf8'), HYDRO_CATALOG);
  const turbine = config.buildings.ReinforcedHydroTurbine;
  if (!turbine) errors.push('buildings.ReinforcedHydroTurbine: missing');
  else if (hydro.loopingSound !== turbine.looping)
    errors.push(`${HYDRO_CATALOG} loopingSound ${hydro.loopingSound} != buildings.ReinforcedHydroTurbine.looping ${turbine.looping}`);
  return {config, errors, plan};
}

export async function applyBuildingSounds(root = defaultRoot) {
  const {errors, plan} = await planBuildingSounds(root);
  const writes = [];
  for (const item of plan) {
    if (same(item.current, item.expected)) continue;
    const body = item.text.startsWith(BOM) ? item.text.slice(1) : item.text;
    if (body !== canonical(item.current))
      errors.push(`${item.kind}.${item.id}: ${relative(root, item.path)} is not in canonical generator JSON format; regenerate it before applying sounds`);
    writes.push({path: item.path, text: (item.text.startsWith(BOM) ? BOM : '') + canonical(item.expected)});
  }
  if (errors.length) throw new Error(`Building sounds not applied:\n- ${errors.join('\n- ')}`);
  for (const write of writes) await writeFile(write.path, write.text, 'utf8');
  return {buildings: plan.filter((p) => p.kind === 'buildings').length, basicSelection: plan.filter((p) => p.kind === 'basicSelection').length, changed: writes.length};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const root = process.argv[2] ? resolve(process.argv[2]) : defaultRoot;
  const result = await applyBuildingSounds(root);
  console.log(`Building sounds applied: ${result.buildings} buildings, ${result.basicSelection} basic-selection objects, ${result.changed} files changed.`);
}
