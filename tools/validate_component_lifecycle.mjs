// Static check: a Deep Frontier entity component that defines a native
// lifecycle method also declares the interface the game calls it through.
//
// Timberborn 1.1.2.8 finds lifecycle callbacks by interface, not by name: a
// BaseComponent with OnEnterFinishedState() but no IFinishedStateListener is
// never told the building finished. Build 146: HospitalPantry lost
// IFinishedStateListener in a rewrite, stayed disabled, and the Hospital
// stopped admitting patients with no error.
//
// Only classes that derive directly from BaseComponent or TickableComponent
// are checked, so an inherited declaration cannot be missed. Explicit
// interface implementations and overrides are not lifecycle definitions here.
//
// Usage: node tools/validate_component_lifecycle.mjs
import {readFile, readdir} from 'node:fs/promises';
import {join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const scripts = join(root, 'src', 'DeepFrontier', 'Scripts');
const CALLBACKS = [
  [/\bpublic\s+void\s+OnEnterFinishedState\s*\(\s*\)/, 'IFinishedStateListener'],
  [/\bpublic\s+void\s+OnExitFinishedState\s*\(\s*\)/, 'IFinishedStateListener'],
  [/\bpublic\s+void\s+OnEnterUnfinishedState\s*\(\s*\)/, 'IUnfinishedStateListener'],
  [/\bpublic\s+void\s+OnExitUnfinishedState\s*\(\s*\)/, 'IUnfinishedStateListener'],
  [/\bpublic\s+void\s+Awake\s*\(\s*\)/, 'IAwakableComponent'],
  [/\bpublic\s+void\s+InitializeEntity\s*\(\s*\)/, 'IInitializableEntity'],
  [/\bpublic\s+void\s+PostInitializeEntity\s*\(\s*\)/, 'IPostInitializableEntity'],
  [/\bpublic\s+void\s+PreInitializeEntity\s*\(\s*\)/, 'IPreInitializableEntity'],
  [/\bpublic\s+void\s+PostLoadEntity\s*\(\s*\)/, 'IPostLoadableEntity'],
  [/\bpublic\s+void\s+DeleteEntity\s*\(\s*\)/, 'IDeletableEntity'],
  // Native IExecutor also declares Save/Load (BehaviorManager saves the running executor).
  [/\bpublic\s+void\s+Save\s*\(\s*IEntitySaver\b/, ['IPersistentEntity', 'IExecutor']],
  [/\bpublic\s+void\s+Load\s*\(\s*IEntityLoader\b/, ['IPersistentEntity', 'IExecutor']],
  [/\bpublic\s+void\s+InfluenceByChildhood\s*\(/, 'IChildhoodInfluenced'],
];

async function files(dir, out = []) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) await files(path, out);
    else if (entry.name.endsWith('.cs')) out.push(path);
  }
  return out;
}

// Top-level class bodies by brace matching (strings and comments stripped).
function classes(text) {
  const clean = text.replace(/\/\/.*$/gm, '').replace(/\/\*[\s\S]*?\*\//g, '').replace(/@?"(?:[^"\\]|\\.)*"/g, '""');
  const found = [];
  const header = /\bclass\s+(\w+)\s*(?:<[^>{]*>)?\s*:\s*([^{]+)\{/g;
  for (let match; (match = header.exec(clean));) {
    const open = header.lastIndex - 1;
    let depth = 0, end = open;
    for (let i = open; i < clean.length; i++) {
      if (clean[i] === '{') depth++;
      else if (clean[i] === '}' && --depth === 0) { end = i; break; }
    }
    const body = clean.slice(open + 1, end);
    // Remove nested class bodies so their methods are not attributed to the outer class.
    const own = body.replace(/\bclass\s+\w+[^{]*\{(?:[^{}]|\{(?:[^{}]|\{[^{}]*\})*\})*\}/g, '');
    found.push({name: match[1], bases: match[2].split(',').map(b => b.trim().replace(/<.*$/, '')), body: own});
  }
  return found;
}

const failures = [];
let checked = 0;
for (const file of await files(scripts)) {
  for (const {name, bases, body} of classes(await readFile(file, 'utf8'))) {
    if (!['BaseComponent', 'TickableComponent'].includes(bases[0])) continue;
    checked++;
    for (const [pattern, contract] of CALLBACKS)
      if (pattern.test(body) && ![contract].flat().some(c => bases.includes(c)))
        failures.push(`${relative(root, file)}: ${name} defines ${pattern.source.match(/void\\s\+(\w+)/)?.[1] ?? contract} but does not declare ${[contract].flat().join(' or ')}, so the game never calls it`);
  }
}
if (failures.length) {
  for (const failure of [...new Set(failures)]) console.error(`FAIL: ${failure}`);
  console.error(`Component lifecycle validation failed (${new Set(failures).size})`);
  process.exit(1);
}
console.log(`Component lifecycle validation passed: ${checked} entity components declare every lifecycle interface they implement.`);
