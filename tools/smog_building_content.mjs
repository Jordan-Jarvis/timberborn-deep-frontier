// Smog content for Deep Frontier (runtime: src/DeepFrontier/Scripts/Smog).
//
// Run at the END of generation, after every building blueprint (with its
// vanilla smoke from vanilla_smoke.mjs) has been written to
// src/DeepFrontier/Data:
//
//   import {applySmog} from './smog_building_content.mjs';
//   await applySmog();
//
// or standalone: node tools/smog_building_content.mjs
//
// What it writes:
// - SmogEmitterSpec on every polluting template from tools/smog_content.json:
//   one source per 'smoke' emitter in the study registration
//   (outputs/lategame-studies/<registration>-registration.json, smokeEmitters:
//   kind, mouth position in artwork coordinates, mouth radius; for the civic,
//   industrial and research buildings <registration> is the relative
//   ../<pipeline>-integration/<Model>-smoke written by
//   register_smoke_emitters.py, in the native grid frame). The emitter's
//   Activity is the particle controller that runs the same smoke attachments
//   in the blueprint, so smog and smoke start and stop together.
// - Needs Smog and HeavySmog (never-positive, hidden while inactive), their
//   need collection (CollectionId Common), the SmogSettingsSpec blueprint and
//   Localizations/enUS_smog.csv. These four module-owned files are rewritten
//   on every run; nothing else is touched.
// - SmogScrubberSpec on the SmogScrubber template once its art is integrated
//   (scrubber.status 'ready').
//
// Everything fails explicitly: missing smokeEmitters, smoke without a
// matching content entry, attachments that do not match the registration,
// a polluter without a particle controller, a second IBuildingWithRange,
// double application, unknown keys.
import {readdir, readFile, writeFile, mkdir} from 'node:fs/promises';
import {fileURLToPath, pathToFileURL} from 'node:url';
import {dirname} from 'node:path';

const VANILLA = 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/';
const STUDIES = 'outputs/lategame-studies/';
const DATA = 'src/DeepFrontier/Data/';
export const SMOG_FILES = {
  collection: 'NeedCollections/NeedCollection.DeepFrontierSmog.blueprint.json',
  settings: 'Configurations/DeepFrontierSmog.blueprint.json',
  localization: 'Localizations/enUS_smog.csv',
  need: (id) => `Needs/Need.Beaver.${id}.blueprint.json`,
};
export const SETTINGS_KEYS = ['LightThreshold', 'HeavyThreshold', 'LightNeedId', 'HeavyNeedId', 'ExposurePointsPerHour',
  'GrowthSlowdownAtThreshold', 'GrowthSlowdownPerIntensity', 'GrowthSlowdownMax', 'TreeReduction', 'BushReduction',
  'GreeneryRadius', 'GreeneryMaxReduction', 'ScrubberMaxReduction', 'WindDriftCells', 'CoreFraction', 'EdgeFactor',
  'FieldIntervalHours', 'GrowthIntervalHours'];
// Panel text used by the C# (keys must match _loc.T calls; validated).
export const SMOG_LOCALIZATION = [
  ['DeepFrontier.Smog.Emitter.Planned', 'Smog: {0} smokestack(s) will pollute up to {1} tiles away while working (up to -{2} wellbeing nearby).'],
  ['DeepFrontier.Smog.Emitter.Idle', 'Smog: idle. Its {0} smokestack(s) pollute up to {1} tiles away while working.'],
  ['DeepFrontier.Smog.Emitter.Active', 'Smog: -{0} wellbeing nearby (up to {1} tiles); crops and trees there grow {2}% slower.'],
  ['DeepFrontier.Smog.Emitter.Mitigation', 'Keep homes and fields outside the tinted range. Trees and scrubbers clean the air around them.'],
  ['DeepFrontier.Smog.Building', 'Smog {0}%: beavers here lose {1} wellbeing (up to {2} in heavy smog).'],
  ['DeepFrontier.Smog.Building.Mitigated', 'Trees remove {0}% of the smog here, scrubbers {1}%.'],
  ['DeepFrontier.Smog.Growth', 'Smog {0}%: growing {1}% slower.'],
  ['DeepFrontier.Smog.Greenery', 'Cleans the air: removes {0}% of the smog within {1} tiles.'],
  ['DeepFrontier.Smog.Scrubber.Planned', 'Smog Scrubber: will remove {0}% of the smog within {1} tiles while powered.'],
  ['DeepFrontier.Smog.Scrubber.Active', 'Smog Scrubber: removing {0}% of the smog within {1} tiles.'],
  ['DeepFrontier.Smog.Scrubber.Idle', 'Smog Scrubber: stopped (needs power and must not be paused). Removes {0}% of the smog within {1} tiles.'],
];

const fail = (message) => { throw new Error(`smog: ${message}`); };
const exactKeys = (object, keys, what) => {
  if (!object || typeof object !== 'object' || Array.isArray(object)) fail(`${what} must be an object`);
  const actual = Object.keys(object).sort().join(), expected = [...keys].sort().join();
  if (actual !== expected) fail(`${what} keys must be exactly [${expected}], got [${actual}]`);
};
const fraction = (v) => typeof v === 'number' && v > 0 && v <= 1;
const positive = (v) => typeof v === 'number' && v > 0;
const csvCell = (text) => {
  if (typeof text !== 'string') fail('localization cells must be strings');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};

export function smogPaths(root = new URL('../', import.meta.url)) {
  return {root, data: new URL(DATA, root), vanilla: new URL(VANILLA, root), studies: new URL(STUDIES, root)};
}
const readJson = async (url) => JSON.parse(await readFile(url, 'utf8'));

export function validateSmogContent(c) {
  exactKeys(c, ['comment', 'settings', 'needs', 'pollutingKind', 'nonPollutingKinds', 'templates', 'exempt', 'scrubber'], 'smog_content');
  const s = c.settings;
  exactKeys(s, SETTINGS_KEYS, 'settings');
  for (const k of SETTINGS_KEYS) if (!k.endsWith('NeedId') && typeof s[k] !== 'number') fail(`settings.${k} must be a number`);
  if (!fraction(s.LightThreshold) || !fraction(s.HeavyThreshold) || s.HeavyThreshold <= s.LightThreshold) fail('thresholds must satisfy 0 < light < heavy <= 1');
  if (!positive(s.ExposurePointsPerHour)) fail('ExposurePointsPerHour must be positive');
  if (!fraction(s.GrowthSlowdownAtThreshold) || !(s.GrowthSlowdownPerIntensity >= 0) || !fraction(s.GrowthSlowdownMax)
    || s.GrowthSlowdownMax < s.GrowthSlowdownAtThreshold) fail('growth slowdown must satisfy 0 < atThreshold <= max <= 1');
  for (const k of ['TreeReduction', 'BushReduction', 'GreeneryMaxReduction', 'ScrubberMaxReduction', 'EdgeFactor']) if (!fraction(s[k])) fail(`settings.${k} must be in (0, 1]`);
  if (!(s.CoreFraction > 0 && s.CoreFraction < 1)) fail('CoreFraction must be in (0, 1)');
  for (const k of ['GreeneryRadius', 'FieldIntervalHours', 'GrowthIntervalHours']) if (!positive(s[k])) fail(`settings.${k} must be positive`);
  if (!(s.WindDriftCells >= 0)) fail('WindDriftCells must be >= 0');
  exactKeys(c.needs, [s.LightNeedId, s.HeavyNeedId], 'needs (must be exactly the settings need ids)');
  for (const [id, n] of Object.entries(c.needs)) {
    exactKeys(n, ['order', 'displayName', 'unfavorableWellbeing', 'dailyRecovery'], `needs.${id}`);
    if (!/^[A-Z][A-Za-z]+$/.test(id)) fail(`need id ${id} must be PascalCase letters`);
    if (!Number.isInteger(n.order) || !Number.isInteger(n.unfavorableWellbeing) || n.unfavorableWellbeing >= 0) fail(`needs.${id}: integer order and negative integer unfavorableWellbeing required`);
    if (!positive(n.dailyRecovery) || typeof n.displayName !== 'string' || !n.displayName) fail(`needs.${id}: positive dailyRecovery and a displayName required`);
  }
  if (c.pollutingKind !== 'smoke') fail('pollutingKind must be smoke');
  // fountainSpray: the vanilla Fountain of Joy water over the Town Plaza fountain (lategame_kit.EMITTER_KINDS).
  if (c.nonPollutingKinds.join() !== 'steam,towerSteam,fountainSpray') fail('nonPollutingKinds must be [steam, towerSteam, fountainSpray]');
  for (const [id, t] of Object.entries(c.templates)) {
    exactKeys(t, ['registration', 'smoke'], `templates.${id}`);
    exactKeys(t.smoke, ['radius', 'strength'], `templates.${id}.smoke`);
    if (!positive(t.smoke.radius) || !fraction(t.smoke.strength)) fail(`templates.${id}: positive radius and strength in (0, 1] required`);
    // Fair boundary: every cell inside the drawn radius is actually affected.
    if (t.smoke.strength * s.EdgeFactor < s.LightThreshold - 1e-9)
      fail(`templates.${id}: strength*EdgeFactor ${t.smoke.strength * s.EdgeFactor} is below LightThreshold; the range edge would show unaffected cells`);
    if (c.exempt[id]) fail(`${id} is both polluting and exempt`);
  }
  for (const [id, e] of Object.entries(c.exempt)) {
    exactKeys(e, ['registration', 'reason'], `exempt.${id}`);
    if (typeof e.reason !== 'string' || e.reason.length < 20) fail(`exempt.${id} needs a real reason`);
  }
  const sc = c.scrubber;
  exactKeys(sc, ['template', 'status', 'radius', 'reduction', 'proposed'], 'scrubber');
  if (!['awaiting-art', 'ready'].includes(sc.status)) fail('scrubber.status must be awaiting-art or ready');
  if (!positive(sc.radius) || !fraction(sc.reduction)) fail('scrubber needs a positive radius and a reduction in (0, 1]');
  return c;
}

export async function loadSmogContent(root) {
  return validateSmogContent(await readJson(new URL('tools/smog_content.json', root)));
}

// The vanilla Smelter's smoke prefab, which vanilla_smoke.mjs uses for 'smoke'.
export async function smokePrefab(paths) {
  const smelter = await readJson(new URL('Buildings/Metal/Smelter/Smelter.IronTeeth.blueprint.json', paths.vanilla));
  const smoke = smelter.TemplateAttachmentsSpec?.Attachments?.find((a) => a.AttachmentId === 'Smoke');
  if (!smoke?.Prefab) fail('vanilla Smelter has no Smoke attachment');
  return smoke.Prefab;
}

export async function buildingBlueprints(paths) {
  const result = new Map();
  const walk = async (url) => {
    for (const entry of await readdir(url, {withFileTypes: true})) {
      const child = new URL(entry.name + (entry.isDirectory() ? '/' : ''), url);
      if (entry.isDirectory()) await walk(child);
      else if (entry.name.endsWith('.IronTeeth.blueprint.json')) {
        const id = entry.name.slice(0, -'.IronTeeth.blueprint.json'.length);
        if (result.has(id)) fail(`two IronTeeth blueprints for ${id}`);
        result.set(id, child);
      }
    }
  };
  await walk(new URL('Buildings/', paths.data));
  return result;
}

export async function readRegistration(paths, registrationId) {
  const registration = await readJson(new URL(`${registrationId}-registration.json`, paths.studies));
  if (!Array.isArray(registration.smokeEmitters)) fail(`${registrationId}: registration has no smokeEmitters; re-register the study`);
  for (const e of registration.smokeEmitters) {
    if (!Array.isArray(e.position) || e.position.length !== 3 || !e.position.every(Number.isFinite) || !positive(e.radius))
      fail(`${registrationId}: malformed smoke emitter ${JSON.stringify(e)}`);
  }
  return registration;
}

const samePosition = (attachment, [x, y, z]) => {
  const p = attachment.Position;
  return p && p.X === x && p.Y === z && p.Z === y;   // vanilla_smoke: {X: x, Y: z, Z: y}
};

// The template's smoke attachments must be exactly the registration's smoke
// emitters, and one particle controller must run all of them.
export function emitterActivity(blueprint, smokeEmitters, prefab, id) {
  const attachments = (blueprint.TemplateAttachmentsSpec?.Attachments ?? []).filter((a) => a.Prefab === prefab);
  if (attachments.length !== smokeEmitters.length) fail(`${id}: ${attachments.length} smoke attachments but ${smokeEmitters.length} registration smoke emitters; run vanilla smoke first`);
  for (const e of smokeEmitters) {
    if (attachments.filter((a) => samePosition(a, e.position)).length !== 1) fail(`${id}: no single smoke attachment at registration mouth ${e.position}`);
  }
  const ids = attachments.map((a) => a.AttachmentId);
  const runs = (spec) => ids.every((a) => blueprint[spec]?.AttachmentIds?.includes(a));
  if (runs('WorkshopParticleControllerSpec')) return 'Workshop';
  if (runs('PowerGeneratorParticleControllerSpec')) return 'Generator';
  if (runs('EnterableParticleControllerSpec')) return 'Occupied';
  fail(`${id}: no WorkshopParticleControllerSpec/PowerGeneratorParticleControllerSpec/EnterableParticleControllerSpec runs its smoke attachments`);
}

export function smogNeed(id, need) {
  return {
    NeedSpec: {Id: id, BackwardCompatibleIds: [], Order: need.order, NeedGroupId: 'BasicNeeds', CharacterType: 'Beaver',
      StartingValue: 0, MinimumValue: -1, MaximumValue: 0, DailyDelta: need.dailyRecovery, ImportanceMultiplier: 1,
      Effectiveness: 1, Wastable: true, HoursWarningThreshold: 0, DisplayNameLocKey: `Need.${id}.DisplayName`,
      FavorableWellbeing: 0, UnfavorableWellbeing: need.unfavorableWellbeing},
    InactiveHiddenNeedSpec: {},
  };
}

export function smogLocalization(content) {
  const rows = [['ID', 'Text', 'Comment']];
  for (const [id, need] of Object.entries(content.needs)) rows.push([`Need.${id}.DisplayName`, need.displayName, 'Deep Frontier smog']);
  for (const [id, text] of SMOG_LOCALIZATION) rows.push([id, text, 'Deep Frontier smog']);
  return rows.map((r) => r.map(csvCell).join(',')).join('\n') + '\n';
}

const writeJson = async (url, value) => {
  await mkdir(dirname(fileURLToPath(url)), {recursive: true});
  await writeFile(url, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};

export async function applySmog({root = new URL('../', import.meta.url)} = {}) {
  const paths = smogPaths(root);
  const content = await loadSmogContent(root);
  const prefab = await smokePrefab(paths);
  const blueprints = await buildingBlueprints(paths);
  const integrated = (await readJson(new URL('tools/lategame_batches.json', root))).integrated;
  const covered = new Map([...Object.entries(content.templates), ...Object.entries(content.exempt)]);

  // Registrations of everything in the package: every smoke emitter is covered.
  const registrationOf = new Map(integrated.map((id) => [id, id]));
  for (const [id, entry] of covered) registrationOf.set(id, entry.registration);
  const registrations = new Map();
  for (const [id, registrationId] of registrationOf) {
    if (!blueprints.has(id)) fail(`${id}: no IronTeeth blueprint in Data`);
    const registration = await readRegistration(paths, registrationId);
    for (const e of registration.smokeEmitters) {
      if (e.kind !== content.pollutingKind && !content.nonPollutingKinds.includes(e.kind)) fail(`${id}: unknown emitter kind ${e.kind}`);
    }
    const smoke = registration.smokeEmitters.filter((e) => e.kind === content.pollutingKind);
    if (smoke.length && !covered.has(id)) fail(`${id}: ${smoke.length} smoke emitter(s) but no smog_content templates/exempt entry`);
    if (content.templates[id] && !smoke.length) fail(`${id}: listed as polluting but its registration has no smoke emitters`);
    registrations.set(id, smoke);
  }
  // Blueprints in Data: every smoke attachment belongs to a covered template.
  for (const [id, url] of blueprints) {
    const value = await readJson(url);
    if (value.SmogEmitterSpec || value.SmogScrubberSpec) fail(`${id}: smog specs already present; applySmog must run once on freshly generated blueprints`);
    const smoke = (value.TemplateAttachmentsSpec?.Attachments ?? []).filter((a) => a.Prefab === prefab);
    if (smoke.length && !covered.has(id)) fail(`${id}: blueprint carries ${smoke.length} smoke attachment(s) but no smog_content entry`);
  }

  // Every check runs before anything is written.
  const polluters = [], writes = [];
  for (const [id, entry] of Object.entries(content.templates)) {
    const url = blueprints.get(id);
    const value = await readJson(url);
    if (value.TemplateSpec?.TemplateName !== `${id}.IronTeeth`) fail(`${id}: unexpected TemplateName ${value.TemplateSpec?.TemplateName}`);
    if (value.RangedEffectBuildingSpec) fail(`${id}: a RangedEffectBuilding already owns this entity's IBuildingWithRange`);
    const smoke = registrations.get(id);
    const activity = emitterActivity(value, smoke, prefab, id);
    value.SmogEmitterSpec = {Activity: activity, Sources: smoke.map(({position: [x, y, z]}) => ({
      Position: {X: x, Y: y, Z: z}, Radius: entry.smoke.radius, Strength: entry.smoke.strength}))};
    writes.push([url, value]);
    polluters.push({id, activity, flues: smoke.length, radius: entry.smoke.radius, strength: entry.smoke.strength});
  }

  const sc = content.scrubber;
  const scrubberUrl = blueprints.get(sc.template);
  if (sc.status === 'awaiting-art') {
    if (scrubberUrl) fail(`${sc.template} blueprint exists but scrubber.status is awaiting-art; set it to ready`);
  } else {
    if (!scrubberUrl) fail(`scrubber.status is ready but no ${sc.template} blueprint was generated`);
    const value = await readJson(scrubberUrl);
    if (!value.MechanicalBuildingSpec || !(value.MechanicalNodeSpec?.PowerInput > 0)) fail(`${sc.template} must be a powered building`);
    if (value.RangedEffectBuildingSpec) fail(`${sc.template}: a RangedEffectBuilding already owns this entity's IBuildingWithRange`);
    value.SmogScrubberSpec = {Radius: sc.radius, Reduction: sc.reduction};
    writes.push([scrubberUrl, value]);
  }

  // Module-owned files: no other need may reuse the ids.
  const ownNeeds = new Set(Object.keys(content.needs).map((id) => SMOG_FILES.need(id).split('/')[1]));
  for (const name of await readdir(new URL('Needs/', paths.data))) {
    if (ownNeeds.has(name)) continue;
    const need = await readJson(new URL(`Needs/${name}`, paths.data));
    if (content.needs[need.NeedSpec?.Id]) fail(`Needs/${name} already defines need ${need.NeedSpec.Id}`);
  }
  for (const [url, value] of writes) await writeJson(url, value);
  for (const [id, need] of Object.entries(content.needs)) await writeJson(new URL(SMOG_FILES.need(id), paths.data), smogNeed(id, need));
  await writeJson(new URL(SMOG_FILES.collection, paths.data), {NeedCollectionSpec: {CollectionId: 'Common', Needs: Object.keys(content.needs)}});
  await writeJson(new URL(SMOG_FILES.settings, paths.data), {SmogSettingsSpec: content.settings});
  const locUrl = new URL(SMOG_FILES.localization, paths.data);
  await mkdir(dirname(fileURLToPath(locUrl)), {recursive: true});
  await writeFile(locUrl, smogLocalization(content), 'utf8');
  return {polluters, exempt: Object.keys(content.exempt), scrubber: sc.status};
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  const summary = await applySmog();
  console.log(`Smog: ${summary.polluters.length} polluting templates (${summary.polluters.map((p) => `${p.id} ${p.flues}x r${p.radius} s${p.strength} ${p.activity}`).join('; ')}); exempt ${summary.exempt.join(', ')}; scrubber ${summary.scrubber}.`);
}
