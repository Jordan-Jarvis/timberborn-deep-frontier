// Native automation for every Deep Frontier building template.
//
// Last step of canonical generation (tools/create_vertical_slice_content.mjs).
// Timberborn 1.1.2.8 automation is decorator-driven: any finished building
// whose components include an IFinishedPausable (Workplace, MechanicalBuilding,
// GoodConsumingBuilding, ...) receives the native PausableBuildingTerminal,
// AutoAutomatableNeeder, Automatable and Automator. Vanilla workshops and
// generators carry no automation spec, so nothing is written here. This step
// asserts that each generated template still has exactly the automation role
// declared in tools/automation_content.json, and fails on any template that is
// missing from, or absent in, that declaration. Correct the producing
// generator or the declaration; never add specs here to hide a difference.
import {readFile, readdir} from 'node:fs/promises';
import {resolve, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {readIntegrations} from './optional_mod_content.mjs';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRelative = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];

const readJson = async (path) => JSON.parse(await readFile(path, 'utf8'));
// Some shipped vanilla blueprints are saved as UTF-8 with a byte-order mark.
const readVanillaJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const sorted = (values) => [...values].sort();
const sameSet = (a, b) => JSON.stringify(sorted(a)) === JSON.stringify(sorted(b));

async function blueprintFiles(dir) {
  const result = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) result.push(...await blueprintFiles(path));
    else if (entry.name.endsWith('.blueprint.json')) result.push(path);
  }
  return result;
}

const blueprintId = (dataRoot, path) => relative(dataRoot, path).split(sep).join('/').replace(/\.json$/, '');

// Role computed from a blueprint's own specs under the native 1.1.2.8 contract.
export function nativeAutomationRole(blueprint, contract) {
  const keys = Object.keys(blueprint);
  const sources = keys.filter((key) => Object.hasOwn(contract.pausableSources, key));
  const terminals = keys.filter((key) => Object.hasOwn(contract.terminalSpecs, key));
  const transmitters = keys.filter((key) => contract.transmitterSpecs.includes(key));
  const building = contract.requiredForAutomation.every((key) => keys.includes(key));
  let role = 'none';
  if (transmitters.length) role = 'transmitter';
  else if (sources.length && terminals.length) role = 'pausable+terminal';
  else if (sources.length) role = 'pausable';
  else if (terminals.length) role = 'terminal';
  return {role, sources, terminals, transmitters, building};
}

export async function auditAutomationContent({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const config = await readJson(resolve(root, 'tools', 'automation_content.json'));
  const contract = config.nativeContract;
  const vanillaRoot = resolve(root, ...vanillaRelative);
  const errors = [];

  const collectionSpec = (await readJson(resolve(dataRoot, config.templateCollection))).TemplateCollectionSpec;
  if (collectionSpec?.CollectionId !== 'Buildings.IronTeeth' || !Array.isArray(collectionSpec['Blueprints#append']))
    throw new Error(`${config.templateCollection}: expected the Buildings.IronTeeth Blueprints#append list`);
  const collection = collectionSpec['Blueprints#append'];
  const generated = new Map();
  for (const path of await blueprintFiles(dataRoot)) {
    const id = blueprintId(dataRoot, path);
    const value = await readJson(path);
    if (id.startsWith('Buildings/') || value.BuildingSpec) generated.set(id, value);
  }
  // Optional-mod specs (Data/Integrations, tools/optional_mod_content.mjs) join their template
  // while that mod is enabled, so they are audited as part of it.
  for (const {file, blueprint, modifier} of await readIntegrations(dataRoot)) {
    const value = generated.get(blueprint);
    if (!value) throw new Error(`${file}: no generated template ${blueprint}`);
    for (const key of Object.keys(modifier)) {
      if (Object.hasOwn(value, key)) throw new Error(`${file}: ${blueprint} already has ${key}`);
      value[key] = modifier[key];
    }
  }

  const collected = new Set(collection);
  for (const id of collection) {
    if (!Object.hasOwn(config.templates, id)) errors.push(`${id}: Deep Frontier building template has no automation role in tools/automation_content.json`);
    if (!generated.has(id)) errors.push(`${id}: listed in the template collection but no blueprint was generated`);
  }
  for (const id of Object.keys(config.templates)) {
    if (!collected.has(id)) errors.push(`${id}: declared in tools/automation_content.json but not in the generated Buildings.IronTeeth collection`);
  }
  for (const id of generated.keys()) {
    if (!collected.has(id) && !Object.hasOwn(config.vanillaPatches, id) && !Object.hasOwn(config.mapObjects, id))
      errors.push(`${id}: blueprint with BuildingSpec is neither a collected template, a map object nor a vanilla patch in tools/automation_content.json`);
  }
  for (const [section, label] of [['vanillaPatches', 'vanilla patch'], ['mapObjects', 'map object']]) {
    for (const id of Object.keys(config[section])) {
      if (!generated.has(id)) errors.push(`${id}: declared ${label} was not generated`);
    }
  }

  // Specs that no vanilla blueprint uses are Deep Frontier or dependency
  // runtime behaviour; on an automatable building each must be declared.
  const vanillaKeys = new Set();
  for (const path of await blueprintFiles(vanillaRoot)) {
    for (const key of Object.keys(await readVanillaJson(path))) vanillaKeys.add(key);
  }
  const vanillaBlueprint = async (id) => readVanillaJson(resolve(vanillaRoot, `${id}.json`));

  const rows = [];
  for (const [id, declared] of Object.entries(config.mapObjects)) {
    if (declared.role !== 'none') errors.push(`${id}: map objects are not player buildings; declare role none`);
  }
  for (const [id, declared] of [...Object.entries(config.templates), ...Object.entries(config.mapObjects)]) {
    const blueprint = generated.get(id);
    if (!blueprint) continue;
    const actual = nativeAutomationRole(blueprint, contract);
    const custom = Object.keys(blueprint).filter((key) => !vanillaKeys.has(key));
    if (!actual.building && declared.role !== 'none') errors.push(`${id}: lacks ${contract.requiredForAutomation.join('/')}, which native PausableBuilding and Automator need`);
    if (actual.role !== declared.role) errors.push(`${id}: automation role is ${actual.role} (${[...actual.sources, ...actual.terminals, ...actual.transmitters].join(', ') || 'no pausable or terminal component'}); declared ${declared.role}`);
    if (declared.role === 'none') {
      if (!declared.precedent) errors.push(`${id}: role none needs a vanilla precedent`);
      else {
        const precedent = nativeAutomationRole(await vanillaBlueprint(declared.precedent), contract);
        if (precedent.role !== 'none') errors.push(`${id}: precedent ${declared.precedent} is ${precedent.role}, not none`);
      }
    } else {
      if (!sameSet(actual.sources, declared.sources ?? [])) errors.push(`${id}: IFinishedPausable sources are [${actual.sources}], declared [${declared.sources ?? []}]`);
      if (!sameSet(actual.terminals, declared.terminals ?? [])) errors.push(`${id}: automatable terminals are [${actual.terminals}], declared [${declared.terminals ?? []}]`);
      for (const key of custom) {
        if (!Object.hasOwn(config.customSpecs, key)) errors.push(`${id}: custom spec ${key} on an automatable building has no declared Off-signal response in customSpecs`);
      }
    }
    rows.push({id, role: actual.role, sources: actual.sources, terminals: actual.terminals, custom});
  }

  for (const [id, declared] of Object.entries(config.vanillaPatches)) {
    const patch = generated.get(id);
    if (!patch) continue;
    const touched = nativeAutomationRole(patch, contract);
    // A patch may raise the science unlock (BuildingSpec.ScienceCost only, the
    // Terrain Block in tools/vanilla_tool_overrides.mjs); any other
    // BuildingSpec field counts as a change to the building.
    const buildingFields = Object.keys(patch.BuildingSpec ?? {}).filter((key) => key !== 'ScienceCost');
    if (touched.sources.length || touched.terminals.length || touched.transmitters.length || buildingFields.length)
      errors.push(`${id}: vanilla patch changes automation-relevant specs (${[...touched.sources, ...touched.terminals, ...touched.transmitters, ...buildingFields.map((key) => `BuildingSpec.${key}`)].join(', ')})`);
    // A patch of a dependency's template names that installed dependency
    // folder as baseRoot; otherwise the base is vanilla. A native *.optional
    // patch merges into the file at the same path without ".optional".
    const baseId = id.replace(/\.optional\.blueprint$/, '.blueprint');
    const base = nativeAutomationRole(declared.baseRoot ? await readVanillaJson(resolve(declared.baseRoot, `${baseId}.json`)) : await vanillaBlueprint(baseId), contract);
    if (base.role !== declared.nativeRole || !sameSet(base.sources, declared.nativeSources))
      errors.push(`${id}: vanilla base is ${base.role} [${base.sources}], declared ${declared.nativeRole} [${declared.nativeSources}]`);
    for (const key of Object.keys(patch).filter((key) => !vanillaKeys.has(key))) {
      if (base.role !== 'none' && !Object.hasOwn(config.customSpecs, key)) errors.push(`${id}: custom spec ${key} on an automatable vanilla building has no declared Off-signal response in customSpecs`);
    }
    rows.push({id, role: base.role, sources: base.sources, terminals: base.terminals, custom: Object.keys(patch).filter((key) => !vanillaKeys.has(key)), patch: true});
  }

  const usedCustom = new Set(rows.filter((row) => row.role !== 'none').flatMap((row) => row.custom));
  for (const key of Object.keys(config.customSpecs)) {
    if (!usedCustom.has(key)) errors.push(`customSpecs.${key}: no automatable Deep Frontier building uses this spec any more`);
  }

  if (errors.length) throw new Error(`Automation content check failed:\n  ${errors.join('\n  ')}`);
  return {config, rows};
}

// Importing this module (as the generator does) audits the generated data.
export const automationAudit = await auditAutomationContent();
{
  const {rows} = automationAudit;
  const count = (role) => rows.filter((row) => !row.patch && row.role === role).length;
  console.log(`Native automation: ${count('pausable')} pausable, ${count('pausable+terminal')} pausable with custom terminal, ` +
    `${count('none')} not automatable (vanilla precedent), ${rows.filter((row) => row.patch).length} vanilla patches unchanged.`);
}
