// Content for mods Deep Frontier integrates with but does not require (manifest OptionalMods).
//
// A spec owned by an optional mod cannot sit in a Deep Frontier blueprint: the game's SpecService
// deserializes templates with BlueprintDeserializer.DeserializeUnsafe, which throws "No type found
// for key <Spec>" when that mod is absent (Timberborn.BlueprintSystem 1.1.2.8). A producer returns
// such specs as `integrations: {<ModId>: {<Spec>: ...}}` and this module writes them to
//   Data/Integrations/<ModId>/<Template>.json   {"Blueprint": "<blueprint path>", "Modifier": {...}}
// The mod's optional assembly DeepFrontier.<ModId> (Scripts/<ModId>/, loaded by Moddable
// Timberborn's OptionalModsLoader only while the mod is enabled) adds each Modifier to its
// blueprint through the game's IBlueprintModifierProvider (Scripts/PowerLines/PowerLineConnectionPoints.cs).
// tools/validate_mod_dependencies.mjs checks the files against the manifest, asmdefs and installed mods.
import {mkdir, readFile, readdir, writeFile} from 'node:fs/promises';
import {basename, dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const INTEGRATIONS_FOLDER = 'Integrations';

async function asmdefNames(scriptsRoot) {
  const names = [];
  for (const entry of await readdir(scriptsRoot, {withFileTypes: true, recursive: true})) {
    if (entry.isFile() && entry.name.endsWith('.asmdef')) names.push(basename(entry.name, '.asmdef'));
  }
  return names;
}

// blueprintPath: "Buildings/Metal/ConcreteMixer/ConcreteMixer.IronTeeth.blueprint.json" (relative to Data).
export async function writeIntegrations(blueprintPath, integrations, {root = defaultRoot} = {}) {
  if (!integrations || !Object.keys(integrations).length) return [];
  if (!blueprintPath.endsWith('.blueprint.json')) throw new Error(`${blueprintPath}: integrations attach to a .blueprint.json`);
  const sourceRoot = resolve(root, 'src', 'DeepFrontier');
  const manifest = JSON.parse((await readFile(resolve(sourceRoot, 'manifest.json'), 'utf8')).replace(/^﻿/, ''));
  const optional = new Set((manifest.OptionalMods ?? []).map((mod) => mod.Id));
  const assemblies = new Set(await asmdefNames(resolve(sourceRoot, 'Scripts')));
  const written = [];
  for (const [modId, modifier] of Object.entries(integrations)) {
    if (!optional.has(modId)) throw new Error(`${blueprintPath}: integration for ${modId}, which is not in the manifest's OptionalMods`);
    if (!assemblies.has(`DeepFrontier.${modId}`)) throw new Error(`${blueprintPath}: integration for ${modId}, but no DeepFrontier.${modId} assembly applies it`);
    if (!modifier || !Object.keys(modifier).length) throw new Error(`${blueprintPath}: empty ${modId} integration`);
    const name = basename(blueprintPath, '.blueprint.json');
    const target = resolve(sourceRoot, 'Data', INTEGRATIONS_FOLDER, modId, `${name}.json`);
    await mkdir(dirname(target), {recursive: true});
    await writeFile(target, `${JSON.stringify({Blueprint: blueprintPath.slice(0, -'.json'.length), Modifier: modifier}, null, 2)}\n`, 'utf8');
    written.push(target);
  }
  return written;
}

// Every integration file under Data/Integrations: [{modId, file, blueprint, modifier}].
export async function readIntegrations(dataRoot) {
  const folder = resolve(dataRoot, INTEGRATIONS_FOLDER);
  const result = [];
  let mods;
  try { mods = await readdir(folder, {withFileTypes: true}); } catch (error) { if (error.code === 'ENOENT') return result; throw error; }
  for (const mod of mods) {
    if (!mod.isDirectory()) throw new Error(`${folder}: ${mod.name} is not a mod folder`);
    for (const file of await readdir(resolve(folder, mod.name))) {
      if (!file.endsWith('.json')) throw new Error(`${folder}/${mod.name}/${file}: integration files are .json`);
      const value = JSON.parse(await readFile(resolve(folder, mod.name, file), 'utf8'));
      const keys = Object.keys(value).sort().join(',');
      if (keys !== 'Blueprint,Modifier') throw new Error(`${mod.name}/${file}: expected {Blueprint, Modifier}, found {${keys}}`);
      result.push({modId: mod.name, file: `${INTEGRATIONS_FOLDER}/${mod.name}/${file}`, blueprint: value.Blueprint, modifier: value.Modifier});
    }
  }
  return result;
}
