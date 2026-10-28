// Static checks for native automation on Deep Frontier buildings.
//
// 1. tools/automation_building_content.mjs: every generated building template
//    has its declared native automation role (imported; it throws on failure).
// 2. Every operational custom spec is bound to a Deep Frontier component and
//    its Off-signal response is present in the named script.
// 3. The decorator chain the roles rely on is present in the referenced
//    Timberborn assemblies (type names in metadata; catches renames/removals).
// Runtime behaviour is verified in game, not here.
import {execFileSync} from 'node:child_process';
import {readFile, readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {automationAudit} from './automation_building_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const scriptsRoot = resolve(root, 'src', 'DeepFrontier', 'Scripts');
const pluginsRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
const ilspy = resolve(root, 'tools', 'dotnet', 'ilspycmd.exe');
const {config, rows} = automationAudit;
const errors = [];

async function sources(dir) {
  const result = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) result.push(...await sources(path));
    else if (entry.name.endsWith('.cs')) result.push(await readFile(path, 'utf8'));
  }
  return result;
}
const allScripts = (await sources(scriptsRoot)).join('\n');

for (const [spec, declared] of Object.entries(config.customSpecs)) {
  if (!['operational', 'native', 'cosmetic', 'passive', 'display', 'dependency'].includes(declared.kind)) errors.push(`customSpecs.${spec}: unknown kind ${declared.kind}`);
  if (!declared.response) errors.push(`customSpecs.${spec}: state its response to an Off signal`);
  if (declared.kind === 'dependency') {
    if (allScripts.includes(`record ${spec}`)) errors.push(`customSpecs.${spec}: declared as a dependency spec but defined in Deep Frontier scripts`);
    continue;
  }
  // A display spec is read by a Harmony patch of a native display component (no
  // decorator of its own); it must be defined and read by Deep Frontier scripts.
  if (declared.kind === 'display') {
    if (!allScripts.includes(`record ${spec}`) || !allScripts.includes(`GetComponent<${spec}>()`))
      errors.push(`customSpecs.${spec}: display specs must be defined and read (GetComponent<${spec}>()) by Deep Frontier scripts`);
    continue;
  }
  if (!new RegExp(`AddDecorator<${spec}\\s*,`).test(allScripts)) errors.push(`customSpecs.${spec}: no Deep Frontier TemplateModule decorates this spec`);
  if (declared.kind !== 'operational') continue;
  if (!declared.evidence?.length) errors.push(`customSpecs.${spec}: operational specs need source evidence`);
  for (const {file, contains} of declared.evidence ?? []) {
    let text;
    try { text = await readFile(resolve(root, file), 'utf8'); } catch { errors.push(`customSpecs.${spec}: evidence file ${file} is missing`); continue; }
    if (!text.includes(contains)) errors.push(`customSpecs.${spec}: ${file} no longer contains "${contains}"`);
  }
}

// HydroTurbine is the only Deep Frontier IAutomatableNeeder; any other
// custom terminal must be added to nativeContract.terminalSpecs explicitly.
for (const match of allScripts.matchAll(/class\s+(\w+)[^{]*\bIAutomatableNeeder\b/g)) {
  const spec = `${match[1]}Spec`;
  if (!Object.hasOwn(config.nativeContract.terminalSpecs, spec)) errors.push(`${match[1]} implements IAutomatableNeeder but ${spec} is not in nativeContract.terminalSpecs`);
}

// Decompile each native type the roles rely on (project ilspycmd, project
// Timberborn plugin assemblies) and require the decorator registrations.
for (const {dll, type, contains} of config.nativeContract.decoratorEvidence) {
  let source;
  try {
    source = execFileSync(ilspy, [resolve(pluginsRoot, dll), '-r', pluginsRoot, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20});
  } catch (error) {
    errors.push(`${dll} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
    continue;
  }
  for (const text of contains) if (!source.includes(text)) errors.push(`${dll} ${type}: no "${text}"; the native automation contract changed`);
}
const usedSources = new Set(rows.filter((row) => row.role !== 'none').flatMap((row) => row.sources));
for (const spec of usedSources) {
  if (!config.nativeContract.decoratorEvidence.some(({contains}) => contains.some((text) => text.startsWith(`AddDecorator<${spec},`))))
    errors.push(`${spec}: used as an IFinishedPausable source but has no decoratorEvidence entry`);
}

const automatable = rows.filter((row) => row.role !== 'none');
if (!automatable.length) errors.push('no automatable Deep Frontier buildings found');

if (errors.length) {
  console.error(`Automation validation failed:\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`Automation validation passed: ${automatable.length} automatable buildings (${automatable.filter((row) => row.patch).length} vanilla patch), ` +
  `${rows.length - automatable.length} non-automatable, ${Object.keys(config.customSpecs).length} custom specs reviewed.`);
