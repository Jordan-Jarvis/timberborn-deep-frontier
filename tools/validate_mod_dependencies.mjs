// Deep Frontier's mod dependencies stay honest: everything the package loads unconditionally uses
// only the game and the manifest's RequiredMods; each OptionalMods integration loads only with its mod.
//
// Derived, not hand-kept: the mod list comes from src/DeepFrontier/manifest.json, the assembly split
// from the asmdefs under Scripts/, and each mod's namespaces and type names from the DLLs of its
// installed Workshop package (tools/dotnet_metadata.mjs). Namespaces and type names the game itself
// defines (Timberborn_Data/Managed) belong to nobody.
//
// Why (Timberborn 1.1.2.8, source-confirmed):
// - A missing RequiredMod only shows a mod-manager warning (ModdingUI ModWarningUpdater); loading continues.
// - ModCodeStarter, Bindito and BlueprintSystem SpecTypeCache call Assembly.GetTypes() unguarded on every
//   mod assembly, and Bindito resolves constructor parameter types, so main-assembly code naming an absent
//   mod's types breaks mod start or the context that binds it.
// - SpecService deserializes templates with DeserializeUnsafe: an unknown spec key throws
//   "No type found for key <Spec>" when the blueprint loads.
//
// Checks:
// 1. Manifest: every RequiredMods/OptionalMods Id is installed at its MinimumVersion or newer.
// 2. Assemblies: Scripts/DeepFrontier.asmdef is the main assembly; every other asmdef is
//    DeepFrontier.<ModId> with <ModId> in OptionalMods, referencing DeepFrontier (packaged as
//    *.dll.<ModId>.optional by tools/unity/DeepFrontierBatchBuild.cs).
// 3. Sources: main-assembly .cs files reference no namespace owned only by mods outside RequiredMods;
//    an optional assembly's files may add only its own mod.
// 4. Blueprints: a Deep Frontier blueprint uses no spec type owned only by a non-required mod, except a
//    standalone blueprint made solely of one optional mod's specs that nothing references (only that
//    mod reads it; without it SpecService only logs the unknown keys). A same-path partial blueprint of
//    a non-required mod's template is a native *.optional.blueprint.json, and that mod is optional.
// 5. Integrations (Data/Integrations/<ModId>/*.json, tools/optional_mod_content.mjs): <ModId> is optional
//    with its assembly, the target is a Deep Frontier blueprint, and every spec belongs to that mod.
// 6. Hidden tools: a vanilla tool that Deep Frontier hides (DevModeTool) keeps a visible replacement with
//    the same display name from a required mod, so the build menu never loses it.
import {readFile, readdir, stat} from 'node:fs/promises';
import {basename, dirname, relative, resolve, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {devEnvironment} from './dev_environment.mjs';
import {readTypeDefinitions} from './dotnet_metadata.mjs';
import {readIntegrations} from './optional_mod_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const source = resolve(root, 'src', 'DeepFrontier');
const scripts = resolve(source, 'Scripts');
const data = resolve(source, 'Data');
const vanilla = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const dev = await devEnvironment(root, ['workshopContent', 'gameManaged']);
const errors = [];
const notes = [];
const posix = (path) => path.split(sep).join('/');

async function walk(dir, accept) {
  const out = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) out.push(...await walk(path, accept));
    else if (accept(entry.name)) out.push(path);
  }
  return out;
}
const exists = (path) => stat(path).then(() => true, () => false);
// Timberborn reads manifests and blueprints with Newtonsoft, which accepts a BOM, comments, trailing
// commas and raw line breaks inside strings; some installed packages rely on that.
const lenientJson = (text) => JSON.parse(text.replace(/^\uFEFF/, '').replace(/[\u0000-\u001f]/g, ' ').replace(/\/\*[\s\S]*?\*\//g, '').replace(/,(\s*[}\]])/g, '$1'));
const readJson = async (path) => lenientJson(await readFile(path, 'utf8'));
function compareVersions(a, b) {
  const x = a.split('.').map(Number), y = b.split('.').map(Number);
  for (let i = 0; i < Math.max(x.length, y.length); i++) if ((x[i] ?? 0) !== (y[i] ?? 0)) return (x[i] ?? 0) - (y[i] ?? 0);
  return 0;
}

// ---- Manifest and installed packages ----
const manifest = await readJson(resolve(source, 'manifest.json'));
const required = new Map(manifest.RequiredMods.map((m) => [m.Id, m.MinimumVersion]));
const optional = new Map((manifest.OptionalMods ?? []).map((m) => [m.Id, m.MinimumVersion]));

// The folder the game loads for Timberborn 1.1: version-1.1 when present, else the package root.
const packages = new Map();
for (const entry of await readdir(dev.workshopContent, {withFileTypes: true})) {
  if (!entry.isDirectory()) continue;
  const item = resolve(dev.workshopContent, entry.name);
  const folder = await exists(resolve(item, 'version-1.1', 'manifest.json')) ? resolve(item, 'version-1.1')
    : await exists(resolve(item, 'manifest.json')) ? item : null;
  if (!folder) continue;
  const value = await readJson(resolve(folder, 'manifest.json'));
  if (!packages.has(value.Id)) packages.set(value.Id, []);
  packages.get(value.Id).push({workshopId: entry.name, folder, version: value.Version, requiredMods: value.RequiredMods ?? []});
}
const packageOf = (id) => {
  const found = packages.get(id) ?? [];
  if (found.length !== 1) throw new Error(`${id}: ${found.length} installed Workshop packages (${found.map((p) => p.workshopId).join(', ')})`);
  return found[0];
};
for (const [kind, mods] of [['RequiredMods', required], ['OptionalMods', optional]]) {
  for (const [id, minimum] of mods) {
    if (!packages.has(id)) { errors.push(`${kind} ${id} is not installed in ${dev.workshopContent}`); continue; }
    const pkg = packageOf(id);
    if (compareVersions(pkg.version, minimum) < 0) errors.push(`${kind} ${id}: installed ${pkg.version} is older than ${minimum}`);
  }
}
// A required mod's own requirements must be required too (the test set is closed).
for (const id of required.keys()) {
  if (!packages.has(id)) continue;
  for (const dep of packageOf(id).requiredMods) {
    if (dep.Id !== 'DeepFrontier' && !required.has(dep.Id)) notes.push(`${id} itself requires ${dep.Id}, which RequiredMods does not list`);
  }
}

// ---- Type ownership: namespace -> mods, type name -> mods ----
const gameTypes = [];
for (const dll of await walk(dev.gameManaged, (name) => name.endsWith('.dll'))) {
  if (/^DeepFrontier/.test(basename(dll))) continue;
  try { gameTypes.push(...await readTypeDefinitions(dll)); } catch { /* native or resource-only DLL */ }
}
const gameNamespaces = new Set(gameTypes.map((t) => t.namespace));
const gameTypeNames = new Set(gameTypes.map((t) => t.name));
const namespaceOwners = new Map(), typeOwners = new Map(), typesByMod = new Map();
const own = (map, key, id) => { if (!map.has(key)) map.set(key, new Set()); map.get(key).add(id); };
for (const [id, list] of packages) {
  if (id === 'DeepFrontier') continue;
  for (const pkg of list) {
    const names = new Set();
    for (const dll of await walk(pkg.folder, (name) => name.endsWith('.dll'))) {
      let types;
      try { types = await readTypeDefinitions(dll); } catch { continue; }
      for (const t of types) {
        if (t.namespace && !gameNamespaces.has(t.namespace)) own(namespaceOwners, t.namespace, id);
        if (t.namespace && !gameTypeNames.has(t.name)) { own(typeOwners, t.name, id); names.add(t.name); }
      }
    }
    typesByMod.set(id, names);
  }
}
const allowedFor = (assembly) => new Set([...required.keys(), ...(assembly === 'DeepFrontier' ? [] : [assembly.slice('DeepFrontier.'.length)])]);

// ---- Assemblies ----
const asmdefs = await walk(scripts, (name) => name.endsWith('.asmdef'));
const assemblyDirs = new Map();
for (const path of asmdefs) {
  const name = basename(path, '.asmdef');
  const value = await readJson(path);
  if (value.name !== name) errors.push(`${posix(relative(root, path))}: asmdef name ${value.name} differs from its file name`);
  assemblyDirs.set(dirname(path), name);
  if (name === 'DeepFrontier') {
    if (dirname(path) !== scripts) errors.push(`The main asmdef must be Scripts/DeepFrontier.asmdef, found ${posix(relative(root, path))}`);
    continue;
  }
  const modId = name.startsWith('DeepFrontier.') ? name.slice('DeepFrontier.'.length) : null;
  if (!modId) { errors.push(`${posix(relative(root, path))}: an optional assembly is named DeepFrontier.<ModId>`); continue; }
  if (!optional.has(modId)) errors.push(`${name}: ${modId} is not in the manifest's OptionalMods`);
  if (required.has(modId)) errors.push(`${name}: ${modId} is required, so its code belongs in the main assembly`);
  if (JSON.stringify(value.references ?? []) !== '["DeepFrontier"]') errors.push(`${name}: references must be exactly ["DeepFrontier"], found ${JSON.stringify(value.references)}`);
}
if (![...assemblyDirs.values()].includes('DeepFrontier')) errors.push('Scripts/DeepFrontier.asmdef is missing');
const assemblyOf = (file) => {
  for (let dir = dirname(file); dir.startsWith(scripts); dir = dirname(dir)) if (assemblyDirs.has(dir)) return assemblyDirs.get(dir);
  throw new Error(`${file}: no asmdef above it`);
};

// ---- Sources ----
// Comments and string/char literals are removed, then every dotted name that does not follow a '.'
// is checked prefix by prefix against the owned namespaces (using directives, aliases, qualified names).
function code(text) {
  return text
    .replace(/\/\*[\s\S]*?\*\//g, ' ')
    .replace(/@"(?:[^"]|"")*"/g, '""')
    .replace(/\$?"(?:\\.|[^"\\\n])*"/g, '""')
    .replace(/'(?:\\.|[^'\\\n])+'/g, "''")
    .replace(/\/\/[^\n]*/g, ' ');
}
const sourceFiles = await walk(scripts, (name) => name.endsWith('.cs'));
const referencedMods = new Map();
for (const file of sourceFiles) {
  const assembly = assemblyOf(file);
  const allowed = allowedFor(assembly);
  const text = code(await readFile(file, 'utf8'));
  const hits = new Map();
  for (const match of text.matchAll(/(?<![\w.])(?:global::)?([A-Za-z_]\w*(?:\s*\.\s*[A-Za-z_]\w*)*)/g)) {
    const parts = match[1].split('.').map((s) => s.trim());
    for (let n = parts.length; n >= 1; n--) {
      const owners = namespaceOwners.get(parts.slice(0, n).join('.'));
      if (!owners) continue;
      for (const id of owners) { if (!referencedMods.has(id)) referencedMods.set(id, new Set()); referencedMods.get(id).add(assembly); }
      if (![...owners].some((id) => allowed.has(id))) hits.set(parts.slice(0, n).join('.'), [...owners]);
      break;
    }
  }
  for (const [namespace, owners] of hits) {
    errors.push(`${posix(relative(root, file))} (${assembly}) uses ${namespace} from ${owners.join('/')}, which ${assembly === 'DeepFrontier' ? 'RequiredMods does not list' : 'is neither required nor this assembly\'s mod'}; move it to Scripts/<folder>/DeepFrontier.<ModId>.asmdef and list the mod in OptionalMods`);
  }
}

// ---- Blueprints ----
const blueprintFiles = await walk(data, (name) => name.endsWith('.blueprint.json'));
const dfBlueprintIds = new Set(blueprintFiles.map((f) => posix(relative(data, f)).replace(/\.optional\.blueprint\.json$/, '.blueprint.json').replace(/\.json$/, '')));
function specKeys(value, out = new Set()) {
  for (const [key, child] of Object.entries(value)) {
    if (key === 'Children') { for (const c of Object.values(child)) specKeys(c, out); continue; }
    out.add(key.split('#')[0]);
  }
  return out;
}
// Which installed package (vanilla first) has a non-optional blueprint at this Data-relative path.
async function baseOwner(path) {
  if (await exists(resolve(vanilla, path))) return 'vanilla';
  const owners = [];
  for (const [id, list] of packages) for (const pkg of list) if (await exists(resolve(pkg.folder, path))) owners.push(id);
  return owners;
}
const allDfText = (await Promise.all([...blueprintFiles, ...await walk(data, (n) => n.endsWith('.json') && !n.endsWith('.blueprint.json'))]
  .map(async (f) => [f, (await readFile(f, 'utf8')).toLowerCase()])));
for (const file of blueprintFiles) {
  const rel = posix(relative(data, file));
  const isOptional = rel.endsWith('.optional.blueprint.json');
  const basePath = isOptional ? rel.replace(/\.optional\.blueprint\.json$/, '.blueprint.json') : rel;
  const owner = await baseOwner(basePath);
  const baseMods = owner === 'vanilla' ? [] : owner;
  if (isOptional) {
    if (owner !== 'vanilla' && !owner.length) errors.push(`${rel}: no installed package has ${basePath}, so this optional patch never merges`);
    for (const id of baseMods) if (!required.has(id) && !optional.has(id)) errors.push(`${rel}: patches ${id}'s template; list ${id} in OptionalMods`);
  } else {
    for (const id of baseMods) if (!required.has(id)) errors.push(`${rel}: same-path patch of ${id}'s template, which is not required; name it ${basePath.replace(/\.blueprint\.json$/, '.optional.blueprint.json')} and list ${id} in OptionalMods`);
  }
  const keys = [...specKeys(await readJson(file))];
  const foreign = keys.map((key) => [key, [...(typeOwners.get(key) ?? [])]]).filter(([, owners]) => owners.length && !owners.some((id) => required.has(id)));
  if (!foreign.length) continue;
  const allowed = new Set(isOptional ? baseMods : []);
  const bad = foreign.filter(([, owners]) => !owners.some((id) => allowed.has(id)));
  if (!bad.length) continue;
  // Standalone integration blueprint: only one optional mod's specs, nothing else, nothing points at it.
  const mods = new Set(bad.flatMap(([, owners]) => owners));
  const id = rel.replace(/\.json$/, '').toLowerCase();
  const referenced = allDfText.some(([f, text]) => f !== file && text.includes(id));
  if (!isOptional && owner !== 'vanilla' && !owner.length && mods.size === 1 && optional.has([...mods][0]) && bad.length === keys.length && !referenced) {
    notes.push(`${rel}: standalone ${[...mods][0]} blueprint (${keys.join(', ')}); only that mod reads it`);
    continue;
  }
  for (const [key, owners] of bad) errors.push(`${rel}: spec ${key} belongs to ${owners.join('/')}, which is not required; SpecService throws "No type found for key ${key}" without it. Author it as an integration (tools/optional_mod_content.mjs)`);
}

// ---- Integrations ----
for (const {modId, file, blueprint, modifier} of await readIntegrations(data)) {
  if (!optional.has(modId)) errors.push(`${file}: ${modId} is not in OptionalMods`);
  if (![...assemblyDirs.values()].includes(`DeepFrontier.${modId}`)) errors.push(`${file}: no DeepFrontier.${modId} assembly applies it`);
  if (!dfBlueprintIds.has(blueprint)) errors.push(`${file}: ${blueprint} is not a Deep Frontier blueprint`);
  else if (blueprintFiles.some((f) => posix(relative(data, f)) === `${blueprint}.json`)) {
    const target = await readJson(resolve(data, `${blueprint}.json`));
    for (const key of Object.keys(modifier)) if (Object.hasOwn(target, key)) errors.push(`${file}: ${blueprint} already has ${key}`);
  }
  for (const key of Object.keys(modifier)) {
    if (!(typesByMod.get(modId) ?? new Set()).has(key)) errors.push(`${file}: ${key} is not a ${modId} type`);
  }
}

// ---- Hidden vanilla tools keep a visible replacement from a required mod ----
for (const file of blueprintFiles) {
  const rel = posix(relative(data, file));
  const value = await readJson(file);
  if (value.PlaceableBlockObjectSpec?.DevModeTool !== true || value.TemplateSpec) continue;
  if (!await exists(resolve(vanilla, rel))) continue;
  const base = await readJson(resolve(vanilla, rel));
  const name = base.LabeledEntitySpec?.DisplayNameLocKey;
  const template = base.TemplateSpec?.TemplateName;
  const faction = template?.split('.').pop();
  const replacements = [];
  for (const id of required.keys()) {
    const pkg = packageOf(id);
    const collections = (await walk(pkg.folder, (n) => n.startsWith('TemplateCollection.') && n.endsWith('.blueprint.json')))
      .map(async (f) => (await readJson(f)).TemplateCollectionSpec ?? {});
    const listed = new Set((await Promise.all(collections)).flatMap((c) => [...(c.Blueprints ?? []), ...(c['Blueprints#append'] ?? [])]).map((p) => p.toLowerCase()));
    for (const f of await walk(pkg.folder, (n) => n.endsWith('.blueprint.json') && !n.endsWith('.optional.blueprint.json'))) {
      if (!(await readFile(f, 'utf8')).includes(`"${name}"`)) continue;
      const candidate = await readJson(f);
      if (candidate.LabeledEntitySpec?.DisplayNameLocKey !== name || !candidate.TemplateSpec || candidate.TemplateSpec.TemplateName === template) continue;
      if (!candidate.TemplateSpec.TemplateName.endsWith(`.${faction}`)) continue;
      const path = posix(relative(pkg.folder, f)).replace(/\.json$/, '');
      const hidden = candidate.PlaceableBlockObjectSpec?.DevModeTool === true
        || await exists(resolve(data, `${path}.json`)) && (await readJson(resolve(data, `${path}.json`))).PlaceableBlockObjectSpec?.DevModeTool === true
        || await exists(resolve(data, path.replace(/\.blueprint$/, '.optional.blueprint.json'))) && (await readJson(resolve(data, path.replace(/\.blueprint$/, '.optional.blueprint.json')))).PlaceableBlockObjectSpec?.DevModeTool === true;
      if (listed.has(path.toLowerCase()) && !hidden) replacements.push(`${id} ${candidate.TemplateSpec.TemplateName}`);
    }
  }
  if (!replacements.length) errors.push(`${rel}: hides ${template} (${name}) with no visible ${faction} replacement of the same name from a required mod`);
  else notes.push(`${rel}: ${template} hidden; visible replacement ${replacements.join(', ')}`);
}

// ---- Report ----
const usage = [...required.keys(), ...optional.keys()].map((id) => `${optional.has(id) ? 'optional' : 'required'} ${id}: code in ${[...(referencedMods.get(id) ?? [])].sort().join(', ') || 'none'}`);
console.log(JSON.stringify({required: [...required.keys()], optional: [...optional.keys()], assemblies: [...assemblyDirs.values()].sort(), usage, notes}, null, 2));
if (errors.length) {
  console.error(`Mod dependency check failed (${errors.length}):\n  ${errors.join('\n  ')}`);
  process.exitCode = 1;
}
