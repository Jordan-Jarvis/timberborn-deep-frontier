// Static check: Deep Frontier changes native game code and state only in the
// ways docs/native-safety-audit.md records, and every such place keeps the
// rules that came out of that audit (2026-11-09).
//
// 1. Harmony goes through NativePatches.Install (Scripts/NativePatches.cs):
//    no other file creates a Harmony instance, and every CreateClassProcessor
//    or harmony.Patch call sits inside an Install call, so every patch is
//    installed once at mod start after its startup check. The only exception
//    is the -deepFrontierMemoryTrace diagnostic (MemoryTrace.cs).
// 2. Every Install passes a real startup check: a method group or lambda that
//    resolves members and throws (not null, not an empty lambda).
// 3. Every Harmony id and every patch class is listed in the audit, and every
//    [HarmonyPatch] class is installed by some Install call.
// 4. Scene-owner statics (Current/Instance) are assigned only in a constructor
//    (before any singleton's Load) and cleared only in Unload; a Load or
//    PostLoad assigns no static member of its class, and a Load that attaches
//    to a static owner (X.Attach / X.Load) detaches in Unload.
// 5. No native event subscription in Awake: native Load methods replay state
//    through events (NeedManager.Load, GoodCarrier.Load, Manufactory.Awake,
//    Worker.InitializeEntity) and a handler subscribed in Awake runs mid-load.
//    A line may opt out only with "// native-safety: awake-subscription
//    <reason>" for an event never raised while loading, listed in the audit.
// 6. Every file that reflects on native members by name is checked at mod
//    start: it installs a patch, has its own IModStarter, or one of its types
//    is checked by NativeContracts.cs. Acceptance, probe and diagnostic code
//    (command-line flags only) is exempt.
// 7. Patch methods on hot paths (per tick, per frame, per hauler query)
//    allocate nothing: no LINQ, lambdas, string formatting or reference-type
//    `new` outside a throw.
//
// Usage: node tools/validate_native_safety.mjs
import {readFile, readdir} from 'node:fs/promises';
import {join, relative, resolve, basename} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const scripts = join(root, 'src', 'DeepFrontier', 'Scripts');
const auditPath = join(root, 'docs', 'native-safety-audit.md');
const audit = await readFile(auditPath, 'utf8');
const failures = [];
const fail = (file, message) => failures.push(`${file}: ${message}`);
// Names are listed in the audit as code: `Name`.
const listed = name => audit.includes('`' + name + '`');

const DIAGNOSTIC = /(Acceptance|Probe|ShowcaseCapture|MemoryTrace|ArtReviewMode|AcceptanceStartupPanels|SaveInspection)\w*\.cs$/;
const HARMONY_OWNER = 'NativePatches.cs';
const HARMONY_DIAGNOSTIC = 'MemoryTrace.cs';

async function files(dir, out = []) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) await files(path, out);
    else if (entry.name.endsWith('.cs')) out.push(path);
  }
  return out;
}

// Comments and string contents blanked (lengths kept, so offsets match the
// source); string literals are kept separately where needed.
function code(text) {
  return text
    .replace(/\/\*[\s\S]*?\*\//g, m => m.replace(/[^\n]/g, ' '))
    .replace(/@?\$?"(?:[^"\\\n]|\\.)*"/g, m => '"' + ' '.repeat(Math.max(0, m.length - 2)) + '"')
    .replace(/\/\/[^\n]*/g, m => ' '.repeat(m.length));
}

// Index just past the bracket that closes the one at `open`.
function close(text, open) {
  const pairs = {'(': ')', '{': '}', '[': ']'};
  const want = pairs[text[open]];
  let depth = 0;
  for (let i = open; i < text.length; i++) {
    if (text[i] === text[open]) depth++;
    else if (text[i] === want && --depth === 0) return i + 1;
  }
  return text.length;
}

const lineOf = (text, index) => text.slice(0, index).split('\n').length;

// Every method or constructor body: {name, start, end, bodyStart}.
function methods(clean) {
  const found = [];
  const header = /(?:^|[;{}\]])\s*((?:(?:public|private|internal|protected|static|override|virtual|sealed|unsafe|async|extern|new)\s+)*)(?:[\w<>,\[\]?. ]+?\s+)?(\w+)\s*\(([^()]*(?:\([^()]*\)[^()]*)*)\)\s*(?:where[^{]*)?(\{|=>)/g;
  for (let m; (m = header.exec(clean));) {
    const name = m[2];
    if (['if', 'for', 'foreach', 'while', 'switch', 'catch', 'using', 'lock', 'return', 'new', 'nameof', 'typeof', 'throw', 'base', 'this', 'fixed'].includes(name)) continue;
    const arrow = m[4] === '=>';
    const bodyStart = header.lastIndex - (arrow ? 2 : 1);
    const end = arrow ? clean.indexOf(';', bodyStart) + 1 : close(clean, bodyStart);
    // The header starts after the delimiter the pattern anchors on.
    let start = m.index;
    if (/[;{}\]]/.test(clean[start])) start++;
    while (/\s/.test(clean[start])) start++;
    found.push({name, start, bodyStart, end, body: clean.slice(bodyStart, end), modifiers: m[1]});
  }
  return found;
}

// Top-level and nested class extents: {name, start, end, bases}.
function classes(clean) {
  const found = [];
  const header = /\b(?:class|struct|record)\s+(\w+)\s*(?:<[^>{]*>)?\s*(?::\s*([^{]+))?\{/g;
  for (let m; (m = header.exec(clean));) {
    const open = header.lastIndex - 1;
    found.push({name: m[1], start: m.index, end: close(clean, open), bases: (m[2] ?? '').split(',').map(b => b.trim().replace(/<.*$/, ''))});
  }
  return found;
}
const classAt = (list, index) => list.filter(c => c.start <= index && index < c.end).sort((a, b) => b.start - a.start)[0];
const methodAt = (list, index) => list.filter(m => m.bodyStart <= index && index < m.end).sort((a, b) => b.bodyStart - a.bodyStart)[0];

const sources = [];
for (const path of await files(scripts)) {
  const text = await readFile(path, 'utf8');
  const clean = code(text);
  sources.push({path, file: relative(root, path).replaceAll('\\', '/'), name: basename(path), text, clean, methods: methods(clean), classes: classes(clean)});
}
const allClean = sources.map(s => s.clean).join('\n');

// ---------------------------------------------------------------- 1-3 Harmony
const installs = [];
for (const s of sources) {
  for (const m of s.clean.matchAll(/NativePatches\.Install\(/g)) {
    const open = m.index + m[0].length - 1;
    installs.push({source: s, start: m.index, end: close(s.clean, open), args: s.text.slice(open + 1, close(s.clean, open) - 1)});
  }
}
const insideInstall = (s, index) => installs.some(i => i.source === s && i.start <= index && index < i.end);

for (const s of sources) {
  if (s.name === HARMONY_OWNER) continue;
  for (const m of s.clean.matchAll(/\bnew\s+(?:HarmonyLib\.)?Harmony\s*\(|\.PatchAll\s*\(|\bHarmony\.UnpatchID\s*\(|\.UnpatchAll\s*\(/g))
    if (s.name !== HARMONY_DIAGNOSTIC) fail(s.file, `line ${lineOf(s.clean, m.index)}: creates or clears Harmony patches outside NativePatches.Install`);
  for (const m of s.clean.matchAll(/\bCreateClassProcessor\s*\(|\bharmony\.Patch\s*\(|\.Unpatch\s*\(/g))
    if (s.name !== HARMONY_DIAGNOSTIC && !insideInstall(s, m.index))
      fail(s.file, `line ${lineOf(s.clean, m.index)}: Harmony patch applied outside a NativePatches.Install call`);
}

// The verify argument: a method group or a lambda that calls something.
function splitArgs(args) {
  const out = []; let depth = 0, last = 0;
  for (let i = 0; i < args.length; i++) {
    const c = args[i];
    if ('({['.includes(c)) depth++;
    else if (')}]'.includes(c)) depth--;
    else if (c === ',' && depth === 0) { out.push(args.slice(last, i).trim()); last = i + 1; }
  }
  out.push(args.slice(last).trim());
  return out;
}
const methodBodies = name => sources.flatMap(s => s.methods.filter(m => m.name === name).map(m => m.body));
const CHECKS = /\bthrow\b|Require\w*\(|NativeMember\.|NativeIl\.(Require|Calls|Callees|Inlinable|LoadsString|Size)|\.Verify\w*\(|Changed\(|Verify\(|TypeDigest\(|Il\(/;
const ids = new Map();   // id -> file
const installedTypes = new Set();
for (const install of installs) {
  const {source: s} = install;
  if (s.name === HARMONY_OWNER) continue;
  const args = splitArgs(code(install.args));
  const rawArgs = splitArgs(install.args);
  if (args.length < 3) { fail(s.file, `line ${lineOf(s.clean, install.start)}: NativePatches.Install needs an id, a startup check and the patches`); continue; }
  // Id: a literal, or a const string in this file (or any file for Type.Const).
  let id = /^"(DeepFrontier\.[\w.]+)"$/.exec(rawArgs[0])?.[1];
  if (!id) {
    // A const of the named class, else of the class around the call.
    const constName = rawArgs[0].split('.').pop();
    const owner = rawArgs[0].includes('.') ? rawArgs[0].split('.').slice(-2)[0] : classAt(s.classes, install.start)?.name;
    const constPattern = new RegExp(`\\bconst\\s+string\\s+${constName}\\s*=\\s*"(DeepFrontier\\.[\\w.]+)"`);
    for (const o of sources) {
      const cls = o.classes.find(c => c.name === owner);
      const hit = cls && constPattern.exec(o.text.slice(cls.start, cls.end));
      if (hit) { id = hit[1]; break; }
    }
  }
  if (!id) fail(s.file, `line ${lineOf(s.clean, install.start)}: Harmony id ${rawArgs[0]} is not a DeepFrontier.* string constant`);
  else if (ids.has(id) && ids.get(id) !== s.file) fail(s.file, `Harmony id ${id} is also installed in ${ids.get(id)}`);
  else ids.set(id, s.file);
  // Startup check.
  const verify = args[1];
  if (/^null$/.test(verify) || /^\(\)\s*=>\s*\{\s*\}$/.test(verify)) fail(s.file, `line ${lineOf(s.clean, install.start)}: ${id} has no startup check`);
  else if (/^[\w.]+$/.test(verify)) {
    const bodies = methodBodies(verify.split('.').pop());
    if (!bodies.length) fail(s.file, `${id}: startup check ${verify} not found`);
    else if (!bodies.some(b => CHECKS.test(b))) fail(s.file, `${id}: startup check ${verify} resolves nothing that can fail`);
  } else if (!/=>/.test(verify) || !/\w+\s*\(/.test(verify)) fail(s.file, `${id}: startup check must be a method group or a lambda that calls one`);
  for (const t of install.args.matchAll(/typeof\((\w+)\)/g)) installedTypes.add(t[1]);
  for (const t of install.args.matchAll(/HarmonyMethod\((?:typeof\((\w+)\)|(self))/g)) installedTypes.add(t[1] ?? s.classes.find(c => c.start <= install.start && install.start < c.end)?.name);
  // Patch methods passed as nameof(...) in a HarmonyMethod of the enclosing class.
  const enclosing = classAt(s.classes, install.start);
  if (/HarmonyMethod\(/.test(install.args) && enclosing) installedTypes.add(enclosing.name);
}

const patchClasses = new Map();   // class -> file
for (const s of sources) {
  if (s.name === HARMONY_DIAGNOSTIC) continue;
  for (const m of s.clean.matchAll(/\[HarmonyPatch\b[^\]]*\]\s*(?:\[[^\]]*\]\s*)*(?:(?:internal|private|public|static|sealed)\s+)*class\s+(\w+)/g))
    patchClasses.set(m[1], s.file);
  for (const install of installs.filter(i => i.source === s))
    for (const m of install.args.matchAll(/HarmonyMethod\(\s*typeof\((\w+)\)/g)) patchClasses.set(m[1], s.file);
}
for (const [name, file] of patchClasses) {
  if (!installedTypes.has(name)) fail(file, `patch class ${name} is not installed by any NativePatches.Install call`);
  if (!listed(name)) fail(file, `patch class ${name} is not listed in docs/native-safety-audit.md`);
}
for (const [id, file] of ids) if (!listed(id)) fail(file, `Harmony id ${id} is not listed in docs/native-safety-audit.md`);

// ---------------------------------------------------------------- 4 lifecycle
for (const s of sources) {
  if (DIAGNOSTIC.test(s.name)) continue;
  for (const cls of s.classes) {
    const own = s.methods.filter(m => cls.start <= m.start && m.end <= cls.end && classAt(s.classes, m.start) === cls);
    const body = s.clean.slice(cls.start, cls.end);
    const statics = new Set([...body.matchAll(/\bstatic\s+(?!readonly\b|class\b|void\b|extern\b|bool\s+\w+\s*\(|[\w<>\[\],.?]+\s+\w+\s*\()[\w<>\[\],.? ]+?\s+(\w+)\s*(?:=|;|\{\s*get)/g)].map(m => m[1]));
    const owners = [...statics].filter(n => /^(Current|Instance|\w+Current)$/.test(n));
    for (const name of owners) {
      for (const m of body.matchAll(new RegExp(`(?<![\\w.])${name}\\s*=(?!=)\\s*([^;]+);`, 'g'))) {
        const at = cls.start + m.index;
        const where = methodAt(own, at);
        if (!where) continue;   // the declaration itself
        const isCtor = where.name === cls.name;
        const clears = m[1].trim() === 'null';
        if (!(isCtor && !clears) && !(where.name === 'Unload' && clears))
          fail(s.file, `line ${lineOf(s.clean, at)}: ${cls.name}.${name} is assigned in ${where.name}; scene owners are set in the constructor (before any Load) and cleared in Unload`);
      }
    }
    // Singleton Load/PostLoad (instance methods; a static helper named Load is not one).
    for (const load of own.filter(m => (m.name === 'Load' || m.name === 'PostLoad') && !/\bstatic\b/.test(m.modifiers))) {
      for (const name of statics)
        if (new RegExp(`(?<![\\w.])${name}\\s*(=(?!=)|\\+\\+|--|\\+=|-=)`).test(load.body))
          fail(s.file, `${cls.name}.${load.name} assigns static ${name}; scene state belongs to the instance (or to the constructor/Unload pair)`);
      const unload = own.find(m => m.name === 'Unload')?.body ?? '';
      for (const m of load.body.matchAll(/\b([A-Z]\w+)\.(Attach|Load)\(/g)) {
        const partner = m[2] === 'Attach' ? 'Detach' : 'Unload';
        if (!new RegExp(`\\b${m[1]}\\.${partner}\\(`).test(unload))
          fail(s.file, `${cls.name}.${load.name} calls ${m[1]}.${m[2]} but its Unload does not call ${m[1]}.${partner}`);
      }
    }
  }
}

// ---------------------------------------------------------------- 5 Awake
const AWAKE_MARKER = /\/\/\s*native-safety:\s*awake-subscription\b/;
for (const s of sources) {
  if (DIAGNOSTIC.test(s.name)) continue;
  for (const awake of s.methods.filter(m => m.name === 'Awake')) {
    const lines = s.text.slice(awake.bodyStart, awake.end).split('\n');
    const cleanLines = awake.body.split('\n');
    cleanLines.forEach((line, i) => {
      const subscribes = /[\w)\]]\s*\+=\s*(?!\s*-?\d)/.test(line) && !/\b(int|float|double|long)\s+\w+\s*\+=/.test(line)
        || /\.(Register|RegisterListener|RegisterNavMeshListener|Subscribe)\s*\(/.test(line);
      if (!subscribes) return;
      if (AWAKE_MARKER.test(lines[i])) {
        const cls = classAt(s.classes, awake.start)?.name;
        if (!cls || !listed(cls)) fail(s.file, `${cls}: awake-subscription exception is not listed in docs/native-safety-audit.md`);
        return;
      }
      fail(s.file, `line ${lineOf(s.clean, awake.bodyStart) + i}: subscribes to an event in Awake; subscribe in InitializeEntity (after native Load replays state)`);
    });
  }
}

// ---------------------------------------------------------------- 6 reflection
const REFLECTS = /AccessTools\.(Field|Method|DeclaredMethod|Property|PropertyGetter|PropertySetter|TypeByName|FieldRefAccess|MethodDelegate|DeclaredField)\b|\.GetField\(\s*"|\.GetMethod\(\s*"|\.GetProperty\(|GetSetMethod\(\s*true\s*\)|\bType\.GetType\(\s*"|\.GetType\(\s*"|BindingFlags\.NonPublic/;
const contracts = sources.find(s => s.name === 'NativeContracts.cs')?.text ?? '';
const startupFiles = sources.filter(s => /NativePatches\.Install\(|:\s*(Timberborn\.ModManagerScene\.)?IModStarter\b/.test(s.clean) || s.name === 'NativeContracts.cs');
const startupText = startupFiles.map(s => s.clean).join('\n');
for (const s of sources) {
  if (DIAGNOSTIC.test(s.name) || s.name === HARMONY_OWNER || s.name === 'NativeIl.cs') continue;
  if (!REFLECTS.test(s.clean.replace(/"[^"\n]*"/g, '""')) && !REFLECTS.test(s.text.replace(/\/\/[^\n]*/g, ''))) continue;
  if (startupFiles.includes(s)) continue;
  const types = s.classes.map(c => c.name);
  const covered = types.some(t => new RegExp(`typeof\\((?:[\\w.]+\\.)?${t}\\)|\\b${t}\\.\\w+`).test(startupText));
  if (!covered) fail(s.file, `reflects on native members by name but nothing checks them at mod start (NativePatches.Install, an IModStarter or NativeContracts.cs)`);
}

// ---------------------------------------------------------------- 7 hot paths
// Patch methods that run per tick, per frame or per hauler query.
const HOT = {
  RestaurantLateShift: ['Postfix'],
  ReactorBotSpeedPatch: ['Postfix'], ReactorBotLifespanPatch: ['Prefix'], BotWearDeteriorationPatch: ['Prefix'],
  HospitalSupplyAvailability: ['Prefix'], HospitalSupplyAcquisition: ['Prefix'], HospitalSupplyConsumption: ['Prefix'], HospitalMedicalEffects: ['Prefix'],
  HospitalMedicalOffer: ['Postfix'], HospitalMedicalStay: ['Postfix'],
  IrradiatedPlantingSpotsPatch: ['Postfix'], ContaminationSensorMeasurementPatch: ['Postfix'], SluiceMeasurementPatch: ['Postfix'],
  PositionedBlocksIndex: ['TryGetBlockPrefix', 'HasBlockAtPrefix', 'HasStackableBlockAtPrefix'],
  PassageEdgeBlocking: ['Prefix'], PassageObstacles: ['Postfix'],
  PreviewNavMeshCache: ['AddPrefix', 'RemovePrefix', 'PopulatePrefix'], PreviewAccessCache: ['OnPreviewSelectPrefix'],
  PowerGraphReorganizer: ['VisitConnectedNodesPrefix'],
  ReactorBotWorkplacePatches: ['UpdateUnemployedStatePrefix', 'HighestUnderstaffedPostfix', 'LowestStaffedPostfix'],
  WeatherStationSamplePatch: ['Prefix'], WeatherStationOutputPatch: ['Prefix'],
  RestaurantKitchenStock: ['AllowedAmount'],
};
const STRUCTS = /\bnew\s+(Vector3Int|Vector3|Vector2Int|Vector2|GoodAmount|ContinuousEffect|StorableGoodAmount)\s*\(/g;
const seenHot = new Set();
for (const s of sources) {
  for (const cls of s.classes) {
    const wanted = HOT[cls.name];
    if (!wanted) continue;
    for (const m of s.methods.filter(m => wanted.includes(m.name) && classAt(s.classes, m.start) === cls)) {
      seenHot.add(`${cls.name}.${m.name}`);
      const body = m.body.replace(/\bthrow\s+new\b[^;]*;/g, '').replace(STRUCTS, '');
      const found = /\bnew\b/.test(body) ? 'new' : /=>/.test(body) ? 'a lambda' : /\$"/.test(s.text.slice(m.bodyStart, m.end).replace(/throw\s+new\b[^;]*;/g, '')) ? 'string formatting'
        : /(?<!\bMathf?)\.(Where|Select|Any|All|ToList|ToArray|First|FirstOrDefault|Single|SingleOrDefault|Count|Concat|OrderBy|Sum|Max|Min|Distinct)\s*\(/.test(body) ? 'LINQ' : null;
      if (found) fail(s.file, `${cls.name}.${m.name} runs on a hot path and allocates (${found})`);
    }
  }
}
for (const [cls, names] of Object.entries(HOT))
  for (const name of names) if (!seenHot.has(`${cls}.${name}`)) fail('tools/validate_native_safety.mjs', `hot-path method ${cls}.${name} no longer exists; update the HOT list`);

if (failures.length) {
  for (const failure of failures) console.error(`FAIL: ${failure}`);
  console.error(`Native safety validation failed (${failures.length})`);
  process.exit(1);
}
console.log(`Native safety validation passed: ${ids.size} Harmony ids and ${patchClasses.size} patch classes installed through NativePatches with startup checks and listed in the audit; scene owners, Load statics, Awake subscriptions, reflected members and ${seenHot.size} hot-path patch methods checked.`);
