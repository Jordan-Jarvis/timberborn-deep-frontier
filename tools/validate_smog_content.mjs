// Static validator for Deep Frontier smog (data + C# contract).
//
//   node tools/validate_smog_content.mjs [--root <repo>] [--report <json>]
//
// Checks the generated Data against tools/smog_content.json, the study
// registrations and the C# specs in src/DeepFrontier/Scripts/Smog, then
// simulates each polluter's footprint (no wind, no greenery) with the same
// formulas as SmogService and reports the design numbers.
import {readdir, readFile, writeFile} from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {SETTINGS_KEYS, SMOG_FILES, SMOG_LOCALIZATION, buildingBlueprints, emitterActivity, loadSmogContent, readRegistration,
  smogLocalization, smogNeed, smogPaths, smokePrefab} from './smog_building_content.mjs';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const root = opt('--root') ? pathToFileURL(resolve(opt('--root')) + '/') : new URL('../', import.meta.url);
const reportPath = opt('--report');
const errors = [];
const check = (ok, message) => { if (!ok) errors.push(message); };
const readJson = async (url) => JSON.parse(await readFile(url, 'utf8'));
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const paths = smogPaths(root);
const content = await loadSmogContent(root);
const s = content.settings;
const prefab = await smokePrefab(paths);
const blueprints = await buildingBlueprints(paths);
const scripts = new URL('src/DeepFrontier/Scripts/Smog/', root);
const sources = Object.fromEntries(await Promise.all((await readdir(scripts)).filter((f) => f.endsWith('.cs'))
  .map(async (f) => [f, await readFile(new URL(f, scripts), 'utf8')])));

// --- C# contract ---------------------------------------------------------
const recordProps = (name) => {
  const all = Object.values(sources).join('\n');
  const m = all.match(new RegExp(`record ${name}\\b[^{]*\\{([\\s\\S]*?)\\n  \\}`));
  if (!m) { errors.push(`C#: record ${name} not found`); return []; }
  return [...m[1].matchAll(/\[Serialize\] public \S+ (\w+) \{ get; init; \}/g)].map((x) => x[1]);
};
check(same(recordProps('SmogSettingsSpec').sort(), [...SETTINGS_KEYS].sort()), `C#: SmogSettingsSpec properties ${recordProps('SmogSettingsSpec')} != settings keys`);
check(same(recordProps('SmogEmitterSpec'), ['Activity', 'Sources']), 'C#: SmogEmitterSpec must serialize Activity, Sources');
check(same(recordProps('SmogSourceSpec'), ['Position', 'Radius', 'Strength']), 'C#: SmogSourceSpec must serialize Position, Radius, Strength');
check(same(recordProps('SmogScrubberSpec'), ['Radius', 'Reduction']), 'C#: SmogScrubberSpec must serialize Radius, Reduction');
const configurator = sources['SmogConfigurator.cs'] ?? '';
for (const line of ['Bind<SmogService>().AsSingleton()', 'AddDecorator<SmogEmitterSpec,SmogEmitter>()', 'AddDecorator<SmogScrubberSpec,SmogScrubber>()',
  'AddDecorator<Enterer,SmogExposure>()', 'AddDecorator<Growable,SmogGrowth>()', 'AddDecorator<Enterable,SmogBuildingDescriber>()',
  'AddDecorator<SmogEmitter,RangeEnterableHighlighter>()', '[Context("Game")]'])
  check(configurator.includes(line), `C#: SmogConfigurator lacks ${line}`);
for (const kind of ['"Workshop"', '"Generator"', '"Occupied"']) check(sources['SmogEmitter.cs']?.includes(kind), `C#: SmogEmitter does not handle Activity ${kind}`);

// --- Regression checks (outputs/review-2026-10-21/smog.json) --------------
const service = sources['SmogService.cs'] ?? '';
const growthSource = sources['SmogGrowth.cs'] ?? '';
// Body of the first `{...}` block that follows `head` in text.
const blockAfter = (text, head) => {
  const at = text.indexOf(head);
  if (at < 0) return null;
  const open = text.indexOf('{', at);
  for (let j = open, depth = 0; j < text.length; j++) {
    if (text[j] === '{') depth++;
    else if (text[j] === '}' && --depth === 0) return text.slice(open + 1, j);
  }
  return null;
};
// 1. Building footprints come from occupied blocks only. BlockValidator.FitsInMap
//    skips unoccupied blocks, so an empty edge row (FertilizerWorks y=7, ...) may
//    sit off the map, and SmogService.Index throws for it on every worker tick.
check(/FootprintCells\(BlockObject building\)=>\s*building\.PositionedBlocks\.GetOccupiedCoordinates\(\)/.test(service),
  'C#: SmogService.FootprintCells must use PositionedBlocks.GetOccupiedCoordinates (unoccupied blocks may lie off the map)');
for (const [file, text] of Object.entries(sources))
  check(!text.includes('GetAllCoordinates'), `C#: ${file} reads unoccupied blocks (GetAllCoordinates) for smog lookups`);
// 2. Greenery pass: no closure, delegate or ForCells distance test per plant.
const greenLoop = blockAfter(blockAfter(service, 'private void RecomputeField()') ?? '', 'foreach(SmogGrowth growth in _growths)');
check(greenLoop !== null, 'C#: RecomputeField greenery loop not found');
if (greenLoop !== null) check(!/=>|ForCells\(|new |Distance\(/.test(greenLoop),
  'C#: RecomputeField greenery loop allocates or tests distance per plant (use the precomputed _greenDx/_greenDy offsets)');
check(/GreeneryOffsets\(\);/.test(blockAfter(service, 'public void Load()') ?? ''), 'C#: SmogService.Load must precompute GreeneryOffsets');
// The offsets reproduce ForCells exactly (float32 arithmetic as in Unity's
// Vector2.Distance), including the clamped map edge, for the authored radius
// and a sweep of others.
{
  const f = Math.fround;
  const dist = (ax, ay, bx, by) => { const dx = f(ax - bx), dy = f(ay - by); return f(Math.sqrt(f(f(dx * dx) + f(dy * dy)))); };
  const W = 9, H = 7;
  const forCells = (cx, cy, r) => {
    const ox = f(cx + .5), oy = f(cy + .5), out = [];
    const x0 = Math.max(0, Math.floor(f(ox - r))), x1 = Math.min(W - 1, Math.ceil(f(ox + r)));
    const y0 = Math.max(0, Math.floor(f(oy - r))), y1 = Math.min(H - 1, Math.ceil(f(oy + r)));
    for (let y = y0; y <= y1; y++) for (let x = x0; x <= x1; x++) if (dist(f(x + .5), f(y + .5), ox, oy) <= r) out.push(y * W + x);
    return out;
  };
  const offsets = (r) => {
    const reach = Math.ceil(r), out = [];
    for (let y = -reach; y <= reach; y++) for (let x = -reach; x <= reach; x++) if (dist(f(x + .5), f(y + .5), .5, .5) <= r) out.push([x, y]);
    return out;
  };
  const radii = [s.GreeneryRadius, ...Array.from({length: 24}, (_, i) => .25 * (i + 1)), 1.4142135, 2.2360679, 2.8284271];
  for (const radius of radii) {
    const r = f(radius), table = offsets(r);
    let same_ = true;
    for (let cy = 0; cy < H && same_; cy++) for (let cx = 0; cx < W && same_; cx++) {
      const viaOffsets = table.map(([dx, dy]) => [cx + dx, cy + dy]).filter(([x, y]) => x >= 0 && x < W && y >= 0 && y < H).map(([x, y]) => y * W + x);
      same_ = same(viaOffsets, forCells(cx, cy, r));
    }
    check(same_, `greenery offsets differ from ForCells at radius ${radius}`);
  }
}
// 3. Growth set-back is pro-rated by the plant's own growth since its last
//    charge, not by the service-wide interval.
const applySlowdown = blockAfter(growthSource, 'public void ApplySlowdown(');
check(/public void ApplySlowdown\(float slowdown\)/.test(growthSource) && applySlowdown !== null,
  'C#: SmogGrowth.ApplySlowdown(float slowdown) not found (it must not take the service interval)');
if (applySlowdown !== null) check(/GrowthProgress-_chargedProgress/.test(applySlowdown) && /_chargedProgress=Growable\.GrowthProgress;/.test(applySlowdown)
  && !/elapsed|GrowthTimeInDays|GrowthInProgress/.test(applySlowdown),
  'C#: SmogGrowth.ApplySlowdown must charge slowdown * (progress since the last charge) and reset _chargedProgress');
check(/_chargedProgress=Growable\.GrowthProgress;\s*_smog\.AddGrowth\(this\)/.test(growthSource),
  'C#: SmogGrowth.InitializeEntity must set the charge baseline when registering');
check(/growth\.ApplySlowdown\(GrowthSlowdown\(IntensityAt\(growth\.Cell\)\)\)/.test(service) && !/elapsedHours/.test(service),
  'C#: SmogService must not hand the service-wide elapsed interval to SmogGrowth');

// _loc.T("Key", args...) calls: key exists and placeholder count matches.
const locText = new Map(SMOG_LOCALIZATION);
const locCalls = [];
for (const [file, text] of Object.entries(sources)) {
  for (let i = text.indexOf('_loc.T('); i >= 0; i = text.indexOf('_loc.T(', i + 1)) {
    let depth = 0, j = i + 6, parts = [], start = j + 1;
    for (; j < text.length; j++) {
      const ch = text[j];
      if (ch === '(') depth++;
      else if (ch === ')') { depth--; if (depth === 0) { parts.push(text.slice(start, j)); break; } }
      else if (ch === ',' && depth === 1) { parts.push(text.slice(start, j)); start = j + 1; }
    }
    const keyExpr = parts[0].trim();
    // A literal key, or a local `string key=cond?"A":"B";` chosen before the call.
    const declared = /^\w+$/.test(keyExpr) && text.match(new RegExp(`string ${keyExpr}=([^;]+);`));
    const keys = keyExpr.startsWith('"') ? [JSON.parse(keyExpr)] : [...(declared ? declared[1] : keyExpr).matchAll(/"([^"]+)"/g)].map((m) => m[1]);
    if (!keys.length) errors.push(`${file}: cannot resolve localization key ${keyExpr}`);
    for (const key of keys) locCalls.push({file, key, args: parts.length - 1});
  }
}
check(locCalls.length >= 10, `C#: expected the panel _loc.T calls, found ${locCalls.length}`);
for (const {file, key, args: n} of locCalls) {
  const text = locText.get(key);
  if (!text) { errors.push(`${file}: localization key ${key} is not authored`); continue; }
  const placeholders = new Set([...text.matchAll(/\{(\d+)\}/g)].map((m) => Number(m[1])));
  check(placeholders.size === n && [...placeholders].every((p) => p < n), `${file}: ${key} passes ${n} args but text uses {${[...placeholders]}}`);
}

// --- Data ----------------------------------------------------------------
const data = (path) => new URL(path, paths.data);
check(same(await readJson(data(SMOG_FILES.settings)), {SmogSettingsSpec: s}), 'Data: settings blueprint differs from smog_content.settings');
for (const [id, need] of Object.entries(content.needs)) check(same(await readJson(data(SMOG_FILES.need(id))), smogNeed(id, need)), `Data: need ${id} differs`);
check(same(await readJson(data(SMOG_FILES.collection)), {NeedCollectionSpec: {CollectionId: 'Common', Needs: Object.keys(content.needs)}}), 'Data: smog need collection differs');
check(await readFile(data(SMOG_FILES.localization), 'utf8') === smogLocalization(content), 'Data: enUS_smog.csv differs');
const mainLoc = await readFile(data('Localizations/enUS.csv'), 'utf8');
for (const [key] of SMOG_LOCALIZATION) check(!mainLoc.includes(`\n${key},`), `Data: ${key} duplicated in enUS.csv`);
const groups = await readJson(new URL('NeedGroups/NeedGroup.BasicNeed.blueprint.json', paths.vanilla));
check(groups.NeedGroupSpec.Id === 'BasicNeeds', 'vanilla BasicNeeds group id changed');

const design = [];
for (const [id, url] of blueprints) {
  const value = await readJson(url);
  const entry = content.templates[id];
  if (!entry) { check(!value.SmogEmitterSpec, `${id}: SmogEmitterSpec on a template that is not listed as polluting`); continue; }
  const registration = await readRegistration(paths, entry.registration);
  const smoke = registration.smokeEmitters.filter((e) => e.kind === content.pollutingKind);
  let activity;
  try { activity = emitterActivity(value, smoke, prefab, id); } catch (e) { errors.push(e.message); continue; }
  const expected = {Activity: activity, Sources: smoke.map(({position: [x, y, z]}) => ({Position: {X: x, Y: y, Z: z}, Radius: entry.smoke.radius, Strength: entry.smoke.strength}))};
  check(same(value.SmogEmitterSpec, expected), `${id}: SmogEmitterSpec does not match its registration/controller`);
  check(!value.RangedEffectBuildingSpec, `${id}: second IBuildingWithRange (RangedEffectBuildingSpec)`);
  const [w, h] = registration.footprint;
  for (const {position: [x, y]} of smoke) check(x >= 0 && x <= w && y >= 0 && y <= h, `${id}: flue ${x},${y} outside its ${w}x${h} footprint`);
  design.push({id, activity, footprint: [w, h], flues: smoke.map((e) => e.position.slice(0, 2)), ...simulate(smoke, entry.smoke, [w, h])});
}
for (const id of Object.keys(content.templates)) check(blueprints.has(id), `${id}: listed polluter has no blueprint`);
for (const id of Object.keys(content.exempt)) {
  const value = blueprints.get(id) && await readJson(blueprints.get(id));
  check(value && !value.SmogEmitterSpec, `${id}: exempt template missing or carries SmogEmitterSpec`);
}

// --- Design simulation (SmogService formulas, no wind/greenery) ----------
function contribution(d, r, strength) {
  if (d > r) return 0;
  const core = r * s.CoreFraction;
  return d <= core ? strength : strength * (1 - (1 - s.EdgeFactor) * (d - core) / (r - core));
}
function slowdown(i) { return i < s.LightThreshold ? 0 : Math.min(s.GrowthSlowdownMax, s.GrowthSlowdownAtThreshold + s.GrowthSlowdownPerIntensity * (i - s.LightThreshold)); }
function simulate(smoke, {radius, strength}, [w, h]) {
  const pad = Math.ceil(radius + s.WindDriftCells) + 1;
  let light = 0, heavy = 0, peak = 0, envelope = 0;
  for (let y = -pad; y < h + pad; y++) for (let x = -pad; x < w + pad; x++) {
    let clean = 1, inEnvelope = false;
    for (const {position: [fx, fy]} of smoke) {
      const d = Math.hypot(x + .5 - fx, y + .5 - fy);
      clean *= 1 - contribution(d, radius, strength);
      if (d <= radius + s.WindDriftCells) inEnvelope = true;
    }
    const i = 1 - clean;
    const outside = x < 0 || y < 0 || x >= w || y >= h;
    if (inEnvelope && outside) envelope++;
    if (!outside) continue;   // count only cells around the building
    peak = Math.max(peak, i);
    if (i >= s.HeavyThreshold) heavy++;
    else if (i >= s.LightThreshold) light++;
  }
  const penalty = (i) => i >= s.HeavyThreshold ? -(content.needs[s.LightNeedId].unfavorableWellbeing + content.needs[s.HeavyNeedId].unfavorableWellbeing)
    : i >= s.LightThreshold ? -content.needs[s.LightNeedId].unfavorableWellbeing : 0;
  return {radius, strength, envelopeRadius: radius + s.WindDriftCells, singleFlueCore: strength, singleFlueEdge: +(strength * s.EdgeFactor).toFixed(3),
    peakOutside: +peak.toFixed(3), lightCellsOutside: light, heavyCellsOutside: heavy, envelopeCellsOutside: envelope,
    wellbeingLostAtPeak: penalty(peak), growthSlowdownAtPeak: +slowdown(peak).toFixed(3), growthSlowdownAtEdge: +slowdown(strength * s.EdgeFactor).toFixed(3)};
}

// Formula spot checks (hand-computed with the authored settings).
const near = (a, b) => Math.abs(a - b) < 1e-6;
check(near(contribution(0, 10, .4), .4) && near(contribution(5, 10, .4), .4) && near(contribution(10, 10, .4), .4 * s.EdgeFactor) && contribution(10.01, 10, .4) === 0, 'falloff spot check');
check(near(1 - (1 - .4) * (1 - .4), .64), 'union spot check');
check(near(slowdown(s.LightThreshold), s.GrowthSlowdownAtThreshold) && near(slowdown(1), s.GrowthSlowdownMax), 'slowdown spot check');

const report = {ok: errors.length === 0, errors, settings: s,
  wellbeing: {light: content.needs[s.LightNeedId].unfavorableWellbeing, heavyTotal: content.needs[s.LightNeedId].unfavorableWellbeing + content.needs[s.HeavyNeedId].unfavorableWellbeing,
    recoveryHoursFromMinimum: 24 / content.needs[s.LightNeedId].dailyRecovery},
  greenery: {treesForMaxReduction: Math.ceil(s.GreeneryMaxReduction / s.TreeReduction), radius: s.GreeneryRadius},
  scrubber: content.scrubber, exempt: Object.keys(content.exempt), polluters: design, localizationCalls: locCalls.length};
if (reportPath) await writeFile(resolve(reportPath), JSON.stringify(report, null, 2) + '\n');
for (const p of design) console.log(`${p.id.padEnd(22)} ${p.activity.padEnd(8)} flues ${p.flues.length} r${p.radius} s${p.strength} envelope ${p.envelopeRadius}: peak ${p.peakOutside} (-${p.wellbeingLostAtPeak} wb, ${Math.round(p.growthSlowdownAtPeak * 100)}% slower), light ${p.lightCellsOutside} / heavy ${p.heavyCellsOutside} cells around`);
if (errors.length) { console.error(errors.map((e) => `FAIL ${e}`).join('\n')); process.exit(1); }
console.log(`Smog content valid: ${design.length} polluters, ${Object.keys(content.exempt).length} exempt, ${locCalls.length} panel strings checked.`);
