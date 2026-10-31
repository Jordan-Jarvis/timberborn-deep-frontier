// Static contract check for the radioactive tide weather.
//
// Usage: node tools/validate_radioactive_tide_content.mjs [dataRoot] [--native <dir>] [--moddable-weathers <dir>]
//   dataRoot defaults to src/DeepFrontier/Data (use a scratch copy after a
//   scratch generation). --native points at decompiled Timberborn 1.1.2.8
//   sources (outputs/weather-api-1.1.2.8) and re-checks the native evidence
//   the Harmony patches and the data overlay rely on. --moddable-weathers
//   points at the installed Moddable Weathers mod folder (Workshop
//   3630523180/version-1.1) and checks the spec against its own specs.
//
// Moddable Weathers (optional dependency):
// - ModdableWeatherSpecs/RadioactiveTideWeather.blueprint.json equals the
//   module's spec (ids, loc keys, sprites, start sound, the Sun overlay fogs).
// - No file of the main assembly (src/DeepFrontier/Scripts) references a
//   Moddable Weathers type, and the manifest does not require the mod: the
//   main DLL must load and Assembly.GetTypes() must succeed without it.
// - The optional assembly Scripts/RadioactiveTide/ModdableWeathers is editor-guarded,
//   named RadioactiveTideTuning.ModdableWeathersBridgeAssembly, binds the
//   weather in Game, and its settings' labels have Moddable Weathers' "Desc"
//   rows. It may only enter the staged tree (src/DeepFrontier) once the
//   build packages it as *.dll.ModdableWeathers.optional.
//
// Checks:
// - RadioactiveTideTuning.cs: defaults inside their slider ranges, the
//   user-requested defaults (enabled, earliest cycle 15), the cooldown, a
//   positive sludge rate, distinct unstyled CSS classes.
// - Localization: every RadioactiveTideLoc key is a module row and appears
//   exactly once in Localizations/enUS.csv with the module text.
// - Configurations/Sun.blueprint.json: exactly one RadioactiveTideWeather fog
//   appended to each of the four native day stages, valid colours/density;
//   the vanilla SunSpec has those stages and no tide fog of its own.
// - Sprites/Weather/RadioactiveTideIcon.png: 46x46 RGBA sprite with the
//   native sidecar, re-rendered from the SVG byte-for-byte.
// - Sprites/Weather/RadioactiveTideProgress.png / RadioactiveTideNotification.png:
//   the native badtide art's size, the native sidecar, re-rendered from that
//   art byte-for-byte, and used by both the vanilla UI and the Moddable
//   Weathers spec (never the badtide sprites themselves).
// - C#: every HazardousWeatherUIHelper getter is answered, Harmony and
//   ModSettings code is excluded from the Unity editor compile, the settings
//   owner uses the manifest id, the configurators have the right contexts,
//   the manifest requires Harmony and eMka.ModSettings, the expansion
//   generator imports the module once, docs carry the default numbers.
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';
import {
  BANNER_ART, DAY_STAGES, FOGS, FOG_DENSITY, ICON_META, LOCALIZATION, MODDABLE_SKY_STAGES, TIDE_FILES, VANILLA_SUN,
  moddableWeatherSpec, readTideTuning, renderBannerArt, renderTideIcon,
} from './radioactive_tide_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'RadioactiveTide');
const mainScripts = resolve(root, 'src', 'DeepFrontier', 'Scripts');
const stagedTree = resolve(root, 'src', 'DeepFrontier');
const bridge = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'RadioactiveTide', 'ModdableWeathers');
const args = process.argv.slice(2);
const flags = {};
const positional = [];
for (let i = 0; i < args.length; i++) {
  if (args[i] === '--native' || args[i] === '--moddable-weathers') {
    if (!args[i + 1]) throw new Error(`${args[i]} needs a directory`);
    flags[args[i]] = resolve(args[++i]);
  } else positional.push(args[i]);
}
const nativeDir = flags['--native'] ?? null;
const moddableWeathersDir = flags['--moddable-weathers'] ?? null;
const dataRoot = positional[0] ? resolve(positional[0]) : resolve(root, 'src', 'DeepFrontier', 'Data');
async function csFiles(directory) {
  const result = [];
  for (const entry of await readdir(directory, {withFileTypes: true})) {
    const path = resolve(directory, entry.name);
    if (entry.isDirectory()) result.push(...await csFiles(path));
    else if (entry.name.endsWith('.cs')) result.push(path);
  }
  return result;
}

const failures = [];
const check = (condition, message) => { if (!condition) failures.push(message); };
const read = async (path) => {
  try { return await readFile(path, 'utf8'); } catch { failures.push(`missing ${path}`); return null; }
};

// --- tuning ---------------------------------------------------------------
const tuning = await readTideTuning();
const t = (name) => tuning.get(`RadioactiveTideTuning.${name}`);
check(tuning.weatherId === 'RadioactiveTideWeather', `WeatherId is ${tuning.weatherId}`);
check(t('DefaultEnabled') === true, 'the tide must be enabled by default (user request: an option the player can turn off)');
check(t('DefaultMinCycle') === 15, `default earliest cycle is ${t('DefaultMinCycle')}, user requested 15`);
check(t('EarliestCycle') === 2 && t('MinCycleLowest') === t('EarliestCycle'), 'the earliest-cycle slider must start at cycle 2 (cycle 1 is chosen before settings load)');
for (const [value, low, high, name] of [
  [t('DefaultMinCycle'), t('MinCycleLowest'), t('MinCycleHighest'), 'earliest cycle'],
  [t('DefaultChancePercent'), t('ChancePercentLowest'), t('ChancePercentHighest'), 'chance'],
  [t('DefaultMinDurationDays'), t('DurationLowest'), t('DurationHighest'), 'shortest tide'],
  [t('DefaultMaxDurationDays'), t('DurationLowest'), t('DurationHighest'), 'longest tide'],
]) check(Number.isInteger(value) && low <= value && value <= high, `default ${name} ${value} outside ${low}..${high}`);
check(t('DefaultMinDurationDays') <= t('DefaultMaxDurationDays'), 'default shortest tide exceeds the longest');
check(t('DurationLowest') >= 1, 'a tide must last at least one day');
check(t('ChancePercentLowest') >= 1 && t('ChancePercentHighest') === 100, 'chance range must be 1..100 %');
check(t('CooldownCycles') >= 1, 'two tides must never be consecutive');
// The tide share must land clearly above the radiation cutoff (RadiationTuning.DetectionLimit:
// shares below it are gone), and both emission paths must set exactly that share.
{
  const radiationService = await read(resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Radiation', 'IRadiationService.cs')) ?? '';
  const detection = Number(radiationService.match(/public const float DetectionLimit = ([\d.]+)f;/)?.[1]);
  const share = t('SourceRadioactiveShare');
  check(Number.isFinite(detection) && detection > 0, 'RadiationTuning.DetectionLimit not found');
  check(share >= 2 * detection && share <= 1, `SourceRadioactiveShare ${share} must be within [2 x DetectionLimit ${detection}, 1]`);
  const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'RadioactiveTide');
  const vanillaPath = await read(resolve(scripts, 'RadioactiveTideService.cs')) ?? '';
  const moddablePath = await read(resolve(scripts, 'ModdableWeathers', 'RadioactiveTideModdableEmitter.cs')) ?? '';
  for (const [name, text] of [['RadioactiveTideService', vanillaPath], ['RadioactiveTideModdableEmitter', moddablePath]])
    check(/SetSourceRadioactiveShare\([^;]*\? RadioactiveTideTuning\.SourceRadioactiveShare : 0f\);/.test(text), `${name} must set exactly SourceRadioactiveShare (both tide paths agree)`);
  check(!/SludgePerStrengthHour/.test(vanillaPath + moddablePath), 'SludgePerStrengthHour is gone: the tide is a share of the source water');
}
const classes = ['DatePanelClass', 'WeatherPanelClass', 'NotificationClass'].map(t);
check(new Set(classes).size === 3 && classes.every(c => c.startsWith('deep-frontier-')), `CSS classes must be distinct Deep Frontier names: ${classes}`);
check(`${t('ProgressSpritePath')}.png` === TIDE_FILES.progress, `ProgressSpritePath must be the tide's own art ${TIDE_FILES.progress}`);
check(`${t('NotificationSpritePath')}.png` === TIDE_FILES.notification, `NotificationSpritePath must be the tide's own art ${TIDE_FILES.notification}`);
check(t('ModdableProgressSpritePath') === t('ProgressSpritePath') && t('ModdableNotificationSpritePath') === t('NotificationSpritePath'),
  'with Moddable Weathers the tide must use its own progress and banner art, not the badtide sprites');

// --- localization ---------------------------------------------------------
const rows = new Map(LOCALIZATION);
check(rows.size === LOCALIZATION.length, 'duplicate module localization keys');
for (const key of tuning.locKeys) check(rows.has(key), `RadioactiveTideLoc ${key} has no module row`);
for (const key of rows.keys()) check(tuning.locKeys.includes(key), `module row ${key} is not a RadioactiveTideLoc key`);
const csv = await read(resolve(dataRoot, TIDE_FILES.localization));
if (csv) {
  const parsed = parseCsv(csv);
  for (const [key, text] of rows) {
    const matches = parsed.filter(r => r[0] === key);
    check(matches.length === 1, `${TIDE_FILES.localization}: ${key} appears ${matches.length} times`);
    if (matches.length === 1) check(matches[0][1] === text, `${TIDE_FILES.localization}: ${key} text differs from the module`);
  }
  check((rows.get('DeepFrontier.Weather.RadioactiveTideApproachingDescription').match(/\{0\}/g) ?? []).length === 1, 'approaching description must take the duration as {0}');
}

// --- sky fog overlay --------------------------------------------------------
const vanilla = JSON.parse(await readFile(VANILLA_SUN, 'utf8'));
const overlayText = await read(resolve(dataRoot, TIDE_FILES.sun));
if (overlayText) {
  const overlay = JSON.parse(overlayText);
  check(Object.keys(overlay).join() === 'SunSpec', `${TIDE_FILES.sun} must contain only SunSpec`);
  check(JSON.stringify(Object.keys(overlay.SunSpec ?? {})) === JSON.stringify(DAY_STAGES), `${TIDE_FILES.sun} must cover exactly ${DAY_STAGES}`);
  for (const stage of DAY_STAGES) {
    const vanillaFogs = vanilla.SunSpec?.[stage]?.HazardousWeatherFogs;
    check(Array.isArray(vanillaFogs) && !vanillaFogs.some(f => f.HazardousWeatherId === tuning.weatherId), `vanilla SunSpec.${stage} fogs missing or already tide`);
    const entry = overlay.SunSpec?.[stage];
    check(entry && Object.keys(entry).join() === 'HazardousWeatherFogs#append', `${stage} must only append HazardousWeatherFogs`);
    const fogs = entry?.['HazardousWeatherFogs#append'];
    check(Array.isArray(fogs) && fogs.length === 1, `${stage} must append exactly one fog`);
    const fog = fogs?.[0];
    check(fog?.HazardousWeatherId === tuning.weatherId, `${stage} fog id ${fog?.HazardousWeatherId}`);
    const color = fog?.FogSettings?.FogColor;
    check(color && ['r', 'g', 'b'].every(c => color[c] === FOGS[stage][c] && color[c] >= 0 && color[c] <= 1) && color.a === 1, `${stage} fog colour invalid`);
    check(fog?.FogSettings?.FogDensity === FOG_DENSITY && FOG_DENSITY > 0, `${stage} fog density invalid`);
    const native = vanillaFogs?.find(f => f.HazardousWeatherId === 'BadtideWeather');
    check(native && Object.keys(native.FogSettings).sort().join() === Object.keys(fog?.FogSettings ?? {}).sort().join(), `${stage} fog fields differ from the native badtide fog`);
  }
}

// --- icon -------------------------------------------------------------------
const iconPath = resolve(dataRoot, TIDE_FILES.icon);
try {
  const meta = await sharp(iconPath).metadata();
  check(meta.width === 46 && meta.height === 46 && meta.channels === 4, `${TIDE_FILES.icon} is ${meta.width}x${meta.height}x${meta.channels}, expected 46x46 RGBA`);
  const sidecar = await read(`${iconPath}.meta.json`);
  if (sidecar) check(JSON.stringify(JSON.parse(sidecar)) === JSON.stringify(ICON_META), `${TIDE_FILES.icon}.meta.json must be ${JSON.stringify(ICON_META)}`);
  const rendered = await renderTideIcon();
  check(Buffer.compare(rendered.png, await readFile(iconPath)) === 0, `${TIDE_FILES.icon} is stale; regenerate from RadioactiveTide.svg`);
  check(`${t('IconSpritePath')}.png` === TIDE_FILES.icon, 'IconSpritePath does not match the icon file');
} catch (error) {
  failures.push(`icon: ${error.message}`);
}

// --- weather-panel and banner art ------------------------------------------
for (const [key, source] of BANNER_ART) {
  const path = resolve(dataRoot, TIDE_FILES[key]);
  try {
    const [meta, native] = [await sharp(path).metadata(), await sharp(source).metadata()];
    check(meta.width === native.width && meta.height === native.height && meta.channels === 4, `${TIDE_FILES[key]} is ${meta.width}x${meta.height}x${meta.channels}, expected the native ${native.width}x${native.height} RGBA`);
    const sidecar = await read(`${path}.meta.json`);
    if (sidecar) check(JSON.stringify(JSON.parse(sidecar)) === JSON.stringify(ICON_META), `${TIDE_FILES[key]}.meta.json must be ${JSON.stringify(ICON_META)}`);
    check(Buffer.compare((await renderBannerArt(source)).png, await readFile(path)) === 0, `${TIDE_FILES[key]} is stale; regenerate from ${source}`);
  } catch (error) {
    failures.push(`${key} art: ${error.message}`);
  }
}

// --- C# and wiring ----------------------------------------------------------
const ui = await read(resolve(scripts, 'RadioactiveTideUi.cs'));
const patches = await read(resolve(scripts, 'RadioactiveTidePatches.cs'));
const settings = await read(resolve(scripts, 'RadioactiveTideSettings.cs'));
const configurator = await read(resolve(scripts, 'RadioactiveTideConfigurator.cs'));
const manifest = JSON.parse(await readFile(resolve(root, 'src', 'DeepFrontier', 'manifest.json'), 'utf8'));
const helperGetters = ['NameLocKey', 'ApproachingLocKey', 'InProgressLocKey', 'StartedNotificationLocKey', 'EndedNotificationLocKey',
  'InProgressClass', 'IconClass', 'NotificationBackgroundClass'];
if (ui) {
  for (const getter of helperGetters) {
    check(ui.includes(`"get_${getter}" =>`), `RadioactiveTideUi.Value does not answer ${getter}`);
    check(ui.includes(`"${getter}"`), `RadioactiveTideUi.HelperGetters lacks ${getter}`);
  }
}
if (patches) {
  check(patches.trimStart().startsWith('#if !UNITY_EDITOR') && patches.trimEnd().endsWith('#endif'), 'Harmony patches must be excluded from the Unity editor compile');
  for (const patch of ['RadioactiveTideSelectionPatch', 'RadioactiveTideRestorePatch', 'RadioactiveTideUiSpecificationPatch', 'RadioactiveTideUiTextPatch', 'RadioactiveTideStartSoundPatch'])
    check(new RegExp(`CreateClassProcessor\\(typeof\\(${patch}\\)\\)\\.Patch\\(\\)`).test(patches) && patches.includes(`class ${patch}`), `patch ${patch} is not defined and applied`);
  check(/RadioactiveTidePatchTargets\.Verify\(\);\s*RadioactiveTideNative\.Verify\(\);\s*var harmony/.test(patches), 'native members must be verified before patching');
}
if (settings) {
  check(settings.trimStart().startsWith('#if !UNITY_EDITOR') && settings.trimEnd().endsWith('#endif'), 'ModSettings code must be excluded from the Unity editor compile');
  check(settings.includes(`ModId => "${manifest.Id}"`), `settings owner ModId must be the manifest id ${manifest.Id}`);
  check(/\[Context\("MainMenu"\)\]\s*\[Context\("Game"\)\]\s*public sealed class RadioactiveTideSettingsConfigurator/.test(settings), 'settings must be bound in MainMenu and Game');
  check(!/ChangeableOn/.test(settings), 'settings stay main-menu only (ModSettings default)');
}
if (configurator) check(/\[Context\("Game"\)\]\s*public sealed class RadioactiveTideConfigurator/.test(configurator), 'RadioactiveTideConfigurator must be [Context("Game")]');
for (const id of ['Harmony', 'eMka.ModSettings']) check(manifest.RequiredMods.some(m => m.Id === id), `manifest must require ${id}`);
const expansion = await read(resolve(root, 'tools', 'create_frontier_expansion_content.mjs'));
if (expansion) check((expansion.match(/import\('\.\/radioactive_tide_content\.mjs'\)\)\.applyRadioactiveTide\(\)/g) ?? []).length === 1, 'the expansion generator must import the module exactly once');
const docs = await read(resolve(root, 'docs', 'radiation.md'));
if (docs) {
  const section = docs.slice(docs.indexOf('## Radioactive tide'));
  check(docs.includes('## Radioactive tide'), 'docs/radiation.md lacks the Radioactive tide section');
  for (const value of [String(t('DefaultMinCycle')), `${t('DefaultChancePercent')}%`, `${t('DefaultMinDurationDays')}–${t('DefaultMaxDurationDays')} days`, `${Math.round(t('SourceRadioactiveShare') * 100)}%`])
    check(section.includes(value), `docs/radiation.md Radioactive tide section does not state ${value}`);
}

// --- Moddable Weathers (optional dependency) --------------------------------
const loc = (name) => tuning.get(`RadioactiveTideLoc.${name}`);
const expectedSpec = moddableWeatherSpec(tuning);
const specText = await read(resolve(dataRoot, TIDE_FILES.moddableWeatherSpec));
if (specText) {
  const spec = JSON.parse(specText);
  check(JSON.stringify(spec) === JSON.stringify(expectedSpec), `${TIDE_FILES.moddableWeatherSpec} differs from the module's spec; regenerate it`);
  check(spec.ModdableWeatherSpec?.Id === tuning.weatherId, `${TIDE_FILES.moddableWeatherSpec} Id must be ${tuning.weatherId}`);
  check(TIDE_FILES.moddableWeatherSpec === `ModdableWeatherSpecs/${tuning.weatherId}.blueprint.json`, 'the Moddable Weathers spec file must be named after the weather id');
  check(spec.ModdableWeatherSpec?.DatePanelIcon === t('IconSpritePath'), 'the Moddable Weathers date-panel icon must be the tide icon');
  for (const key of [spec.ModdableWeatherSpec?.DisplayLoc, spec.ModdableWeatherSpec?.DescLoc]) check(new Map(LOCALIZATION).has(key), `spec loc key ${key} has no module row`);
  for (const stage of DAY_STAGES) {
    const fog = spec.ModdableWeatherSkySpec?.[MODDABLE_SKY_STAGES[stage]];
    check(fog && ['r', 'g', 'b'].every(c => fog.FogColor?.[c] === FOGS[stage][c]) && fog.FogColor?.a === 1 && fog.FogDensity === FOG_DENSITY,
      `Moddable Weathers sky ${MODDABLE_SKY_STAGES[stage]} must equal the Sun overlay fog for ${stage}`);
  }
}
check(!manifest.RequiredMods.some(m => m.Id === t('ModdableWeathersAssembly')), 'the manifest must not require ModdableWeathers (optional dependency)');
const moddableUsage = /\bModdableWeathers\.[A-Za-z_]|\busing\s+ModdableWeathers\b/;
for (const path of (await csFiles(mainScripts)).filter(p => !p.startsWith(bridge))) {
  const lines = (await readFile(path, 'utf8')).split(/\r?\n/);
  lines.forEach((line, i) => check(!moddableUsage.test(line.replace(/\/\/.*$/, '')),
    `${relative(root, path)}:${i + 1} references Moddable Weathers in the main assembly; such code belongs in Scripts/RadioactiveTide/ModdableWeathers (Assembly.GetTypes() must succeed without the mod)`));
}
const bridgeAsmdef = await read(resolve(bridge, `${t('ModdableWeathersBridgeAssembly')}.asmdef`));
if (bridgeAsmdef) {
  const asmdef = JSON.parse(bridgeAsmdef);
  check(asmdef.name === t('ModdableWeathersBridgeAssembly'), `optional asmdef name ${asmdef.name}`);
  check(JSON.stringify(asmdef.references) === JSON.stringify(['DeepFrontier']), 'the optional assembly must reference only the DeepFrontier assembly');
}
const bridgeFiles = await csFiles(bridge).catch(() => { failures.push(`missing ${bridge}`); return []; });
const bridgeSources = new Map();
for (const path of bridgeFiles) {
  const text = await readFile(path, 'utf8');
  bridgeSources.set(relative(bridge, path), text);
  check(text.trimStart().startsWith('#if !UNITY_EDITOR') && text.trimEnd().endsWith('#endif'), `${relative(root, path)} must be excluded from the Unity editor compile`);
}
const bridgeConfigurator = bridgeSources.get('RadioactiveTideModdableWeathersConfigurator.cs') ?? '';
check(/\[Context\("Game"\)\]\s*public sealed class RadioactiveTideModdableWeathersConfigurator/.test(bridgeConfigurator), 'the Moddable Weathers configurator must be [Context("Game")]');
check(bridgeConfigurator.includes('this.BindWeather<RadioactiveTideModdableWeather, RadioactiveTideModdableWeatherSettings>()'), 'the tide must be registered with Moddable Weathers BindWeather<T, TSettings>');
const bridgeWeather = bridgeSources.get('RadioactiveTideModdableWeather.cs') ?? '';
check(/class RadioactiveTideModdableWeather : ModdableWeatherBase, IModdableHazardousWeather/.test(bridgeWeather), 'the Moddable Weathers tide must be an IModdableHazardousWeather');
check(bridgeWeather.includes('public override string Id => RadioactiveTideTuning.WeatherId;'), 'the Moddable Weathers tide id must be RadioactiveTideTuning.WeatherId');
const bridgeSettings = bridgeSources.get('RadioactiveTideModdableWeatherSettings.cs') ?? '';
const settingLabels = [...bridgeSettings.matchAll(/\[Description\(RadioactiveTideLoc\.(\w+)\)\]\s*public (bool|int) (\w+) \{ get; set; \}/g)];
check(settingLabels.map(m => m[3]).join() === 'Enabled,StartCycle,ChancePercent,MinDurationDays,MaxDurationDays', `Moddable Weathers settings properties are ${settingLabels.map(m => m[3]).join()}`);
check(settingLabels[0]?.[2] === 'bool' && settingLabels[0]?.[3] === 'Enabled', 'the enable toggle must be the bool property "Enabled" (Moddable Weathers IsEnabledProperty)');
for (const [, name] of settingLabels) {
  const key = loc(name);
  check(new Map(LOCALIZATION).has(key) && new Map(LOCALIZATION).has(`${key}Desc`), `Moddable Weathers setting ${key} needs rows ${key} and ${key}Desc`);
}
const stagedAsmdefs = (await readdir(stagedTree, {recursive: true})).filter(p => p.endsWith(`${t('ModdableWeathersBridgeAssembly')}.asmdef`));
if (stagedAsmdefs.length) {
  const batch = await read(resolve(root, 'tools', 'unity', 'DeepFrontierBatchBuild.cs')) ?? '';
  // The build packages every DeepFrontier.<ModId> asmdef as <name>.dll.<ModId>.optional (ac37d5c).
  check(t('ModdableWeathersBridgeAssembly') === 'DeepFrontier.ModdableWeathers'
      && batch.includes('OptionalPrefix = "DeepFrontier."')
      && batch.includes('PackageOptionalAssembly(mod.Name, name + ".dll", name + ".dll." + name.Substring(OptionalPrefix.Length) + ".optional");'),
    `${stagedAsmdefs.join(', ')} is staged, but the build does not package it as *.dll.ModdableWeathers.optional; as a plain .dll it breaks mod loading without Moddable Weathers`);
}
if (moddableWeathersDir) {
  const mwManifest = JSON.parse((await read(resolve(moddableWeathersDir, 'manifest.json')))?.replace(/^﻿/, '') ?? '{}');
  check(mwManifest.Id === 'ModdableWeathers' && mwManifest.Version === '11.0.0', `Moddable Weathers at ${moddableWeathersDir} is ${mwManifest.Id} ${mwManifest.Version}, expected ModdableWeathers 11.0.0`);
  const badtide = JSON.parse((await read(resolve(moddableWeathersDir, 'ModdableWeatherSpecs', 'BadtideWeather.blueprint.json')))?.replace(/^﻿/, '') ?? '{}').ModdableWeatherSpec ?? {};
  for (const [field, name] of [['WeatherPanelBlinkBackground', 'ModdableBlinkSpritePath'], ['StartSound', 'ModdableStartSound']])
    check(badtide[field] === t(name), `RadioactiveTideTuning.${name} ${t(name)} differs from Moddable Weathers' BadtideWeather ${field} ${badtide[field]}`);
  check(Object.keys(expectedSpec.ModdableWeatherSpec).every(k => k === 'DescLoc' || k in badtide), 'the spec uses a field Moddable Weathers\' BadtideWeather spec does not');
  const orders = [];
  for (const file of await readdir(resolve(moddableWeathersDir, 'ModdableWeatherSpecs'))) {
    const other = JSON.parse((await readFile(resolve(moddableWeathersDir, 'ModdableWeatherSpecs', file), 'utf8')).replace(/^﻿/, '')).ModdableWeatherSpec;
    check(other.Id !== tuning.weatherId, `Moddable Weathers already defines ${tuning.weatherId}`);
    orders.push(other.Order);
  }
  check(!orders.includes(t('ModdableWeatherOrder')), `Moddable Weathers order ${t('ModdableWeatherOrder')} is already used`);
}

// --- native evidence (optional) ---------------------------------------------
if (nativeDir) {
  const n = async (relative) => (await read(resolve(nativeDir, relative))) ?? '';
  const randomizer = await n('Timberborn.HazardousWeatherSystem/Timberborn.HazardousWeatherSystem/HazardousWeatherRandomizer.cs');
  check(/public IHazardousWeather GetRandomWeatherForCycle\(int cycle\)/.test(randomizer), 'native GetRandomWeatherForCycle(int cycle) not found');
  const service = await n('Timberborn.HazardousWeatherSystem/Timberborn.HazardousWeatherSystem/HazardousWeatherService.cs');
  check(service.includes('"IsDrought"') && service.includes('CurrentCycleHazardousWeather = _badtideWeather;'), 'native save/load no longer maps IsDrought=false to badtide; re-check the restore patch');
  check(/public IHazardousWeather CurrentCycleHazardousWeather \{ get; private set; \}/.test(service), 'native CurrentCycleHazardousWeather setter changed');
  const helper = await n('Timberborn.HazardousWeatherSystemUI/Timberborn.HazardousWeatherSystemUI/HazardousWeatherUIHelper.cs');
  check(helper.includes('private void UpdateCurrentUISpecification()') && helper.includes('No UI for weather'), 'native UpdateCurrentUISpecification changed');
  for (const getter of helperGetters) check(helper.includes(`public string ${getter} =>`), `native HazardousWeatherUIHelper.${getter} changed`);
  const sound = await n('Timberborn.HazardousWeatherSystemUI/Timberborn.HazardousWeatherSystemUI/HazardousWeatherSoundPlayer.cs');
  check(sound.includes('public void OnHazardousWeatherStarted(HazardousWeatherStartedEvent hazardousWeatherStartedEvent)') && sound.includes('No start sound for weather type'), 'native start sound player changed');
  const sun = await n('Timberborn.SkySystem/Timberborn.SkySystem/Sun.cs');
  check(sun.includes('Weather fog settings not found for'), 'native Sun fog lookup changed');
  const merger = await n('Timberborn.SerializationSystem/Timberborn.SerializationSystem/JsonMerger.cs');
  check(merger.includes('ProcessArrayTokens(item.Value, keyword, arrayModifications)'), 'native JsonMerger no longer recurses into nested objects for #append');
  const config = await n('Timberborn.HazardousWeatherSystem/Timberborn.HazardousWeatherSystem/HazardousWeatherSystemConfigurator.cs');
  check(!/MultiBind<IHazardousWeather>/.test(config), 'native now multi-binds IHazardousWeather: re-evaluate the selection patch');
}

function parseCsv(text) {
  const out = []; let row = [], cell = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (quoted) {
      if (c === '"' && text[i + 1] === '"') { cell += '"'; i++; } else if (c === '"') quoted = false; else cell += c;
    } else if (c === '"') quoted = true;
    else if (c === ',') { row.push(cell); cell = ''; }
    else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(cell); out.push(row); row = []; cell = ''; }
    else cell += c;
  }
  if (cell || row.length) { row.push(cell); out.push(row); }
  return out;
}

await access(dataRoot).catch(() => failures.push(`data root ${dataRoot} does not exist`));
if (failures.length) {
  console.error(`Radioactive tide validation FAILED (${failures.length}):\n - ${failures.join('\n - ')}`);
  process.exit(1);
}
console.log(`Radioactive tide content valid: ${LOCALIZATION.length} localization rows, ${DAY_STAGES.length} sky fogs, 46 px icon, tide banner art, ${helperGetters.length} UI getters, Moddable Weathers spec + ${bridgeFiles.length} optional-assembly files${nativeDir ? ', native evidence re-checked' : ''}${moddableWeathersDir ? ', checked against installed Moddable Weathers' : ''} (${dataRoot}).`);
