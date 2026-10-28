// Radioactive tide content for Deep Frontier (runtime:
// src/DeepFrontier/Scripts/RadioactiveTide).
//
// Called at the END of tools/create_frontier_expansion_content.mjs, after
// that generator has rewritten Localizations/enUS.csv:
//
//   await (await import('./radioactive_tide_content.mjs')).applyRadioactiveTide();
//
// or standalone: node tools/radioactive_tide_content.mjs [dataRoot]
// (dataRoot defaults to src/DeepFrontier/Data; use a scratch copy to test).
//
// What it writes:
// - Localization rows (weather names, notifications, the explanation lines
//   and the mod-settings labels) appended to the canonical
//   Localizations/enUS.csv. The file must exist and must not already define
//   any of them (each canonical run rewrites it fresh).
// - Configurations/Sun.blueprint.json (module-owned, rewritten each run): a
//   native array overlay that appends a RadioactiveTideWeather fog to each
//   day stage's SunSpec HazardousWeatherFogs. Native Sun.GetFogSettings
//   throws "Weather fog settings not found" for a hazardous weather without
//   one (Timberborn 1.1.2.8); JsonMerger applies nested "#append" keys.
// - Sprites/Weather/RadioactiveTideIcon.png (+ .meta.json): the top-bar
//   weather icon, rendered from src/DeepFrontier/Art/Icons/RadioactiveTide.svg
//   with the shared native icon renderer on the vanilla weather-icon canvas
//   (ico-weather-badtide/drought are 46x46 sprites shown at 26 px) in the
//   radiation yellow-green ink. Review sheet:
//   outputs/radioactive-tide-icons/radioactive-tide-icon.png.
// - Sprites/Weather/RadioactiveTideProgress.png and
//   RadioactiveTideNotification.png (+ .meta.json): the weather-panel bar and
//   the notification banner, the native badtide wave art (exported to
//   outputs/vanilla-icons by tools/asset-pipeline/export_vanilla_icon_references.py)
//   recoloured from its orange/red to the radiation yellow-green, so the tide
//   never reads as badtide. Only the saturated warm wave and water pixels
//   move; the gold frame and the white mist keep their native colours.
//   Review sheet: outputs/radioactive-tide-icons/radioactive-tide-banner.png
//   (each badtide original above its recolour).
// - ModdableWeatherSpecs/RadioactiveTideWeather.blueprint.json (module-owned,
//   rewritten each run): the Moddable Weathers 11.0.0 weather spec used by
//   the optional assembly Scripts/RadioactiveTide/ModdableWeathers when Moddable
//   Weathers is enabled: name, description, icon, progress/stripe/banner art,
//   start sound and a ModdableWeatherSkySpec with the same fogs as the Sun
//   overlay (Moddable Weathers' SunPatches take fog from that spec). Same
//   folder and shape as Moddable Weathers' own Root/ModdableWeatherSpecs.
//   Without Moddable Weathers nothing requests it: native SpecService.Load
//   indexes blueprints by known spec types only, logs "No type found for key
//   ModdableWeatherSpec" (and ModdableWeatherSkySpec) and never deserializes
//   it (BlueprintSystem SpecService/SpecTypeCache, Timberborn 1.1.2.8). The
//   native optional form (*.optional.blueprint.json) only merges into a
//   blueprint another mod defines at the same path, so it cannot carry a new
//   blueprint.
//
// The ids it relies on are read from RadioactiveTideTuning.cs; every
// mismatch, missing target or duplicate throws.
import {readFile, writeFile, mkdir, access} from 'node:fs/promises';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';
import {ICON_KINDS, renderNativeIcon, writeReviewSheet} from './native_icon_style.mjs';
import {RADIATION_ICON_INK} from './create_radiation_icons.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
export const TUNING_SOURCE = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'RadioactiveTide', 'RadioactiveTideTuning.cs');
export const ICON_SVG = resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', 'RadioactiveTide.svg');

export const TIDE_FILES = {
  sun: 'Configurations/Sun.blueprint.json',
  icon: 'Sprites/Weather/RadioactiveTideIcon.png',
  progress: 'Sprites/Weather/RadioactiveTideProgress.png',
  notification: 'Sprites/Weather/RadioactiveTideNotification.png',
  localization: 'Localizations/enUS.csv',
  moddableWeatherSpec: 'ModdableWeatherSpecs/RadioactiveTideWeather.blueprint.json',
};
// SunSpec day-stage colour blocks -> ModdableWeatherSkySpec day stages.
export const MODDABLE_SKY_STAGES = {SunriseColors: 'Sunrise', DayColors: 'Day', SunsetColors: 'Sunset', NightColors: 'Night'};
export const VANILLA_SUN = resolve(vanillaRoot, 'Configurations', 'Sun.blueprint.json');
export const DAY_STAGES = ['SunriseColors', 'DayColors', 'SunsetColors', 'NightColors'];

// A yellow-green haze per day stage, at the native hazardous fog density.
// Native badtide fogs for comparison: sunrise (0.80, 0.56, 0.48), day (0.70,
// 0.44, 0.35), sunset (0.80, 0.62, 0.56), night (0.50, 0.45, 0.45).
export const FOG_DENSITY = 0.003;
export const FOGS = {
  SunriseColors: {r: 0.74, g: 0.76, b: 0.46},
  DayColors: {r: 0.62, g: 0.70, b: 0.36},
  SunsetColors: {r: 0.78, g: 0.74, b: 0.50},
  NightColors: {r: 0.36, g: 0.44, b: 0.26},
};

// Vanilla weather icon canvas (resources.assets ico-weather-*: 46x46,
// artwork ~38 px), single radioactive ink with a short native drop shadow.
export const ICON_STYLE = {
  canvas: 46,
  ink: RADIATION_ICON_INK,
  shadow: {dy: 1, sigma: 0.9, opacity: 0.9},
  hand: {frequency: 0.03, scale: 3},
  extent: [0.70, 0.90],
};
export const ICON_META = ICON_KINDS.building.meta;   // {isSprite: true}

// Weather-panel and banner art: [file key, native badtide source].
export const BANNER_ART = [
  ['progress', resolve(root, 'outputs', 'vanilla-icons', 'weather-progress-badtide.png')],
  ['notification', resolve(root, 'outputs', 'vanilla-icons', 'weather-notification-badtide.png')],
];
// Badtide pixels with saturation >= minSaturation and hue in [hueLow, hueHigh]
// degrees (deep red .. orange; the gold frame is ~40 deg at 0.43 saturation)
// move to hue limeHue (orange) .. greenHue (deep red); darker reds darken further.
export const BANNER_RECOLOUR = {minSaturation: 0.55, hueLow: -15, hueHigh: 40, limeHue: 70, greenHue: 118, darkValue: 0.62, valueGain: 0.42, darkSaturation: 0.75, saturationGain: 0.15};

// [key (RadioactiveTideLoc), English text]. Wording follows the native
// Weather.* rows (e.g. "Badtide approaching", "Badtide started").
export const LOCALIZATION = [
  ['DeepFrontier.Weather.RadioactiveTide', 'Radioactive tide'],
  ['DeepFrontier.Weather.Notification.RadioactiveTideApproaching', 'Radioactive tide approaching'],
  ['DeepFrontier.Weather.Notification.RadioactiveTideInProgress', 'Radioactive tide in progress'],
  ['DeepFrontier.Weather.RadioactiveTideStartedNotification', 'Radioactive tide started'],
  ['DeepFrontier.Weather.RadioactiveTideEndedNotification', 'Radioactive tide ended'],
  ['DeepFrontier.Weather.RadioactiveTideApproachingDescription',
    'For {0} days the water of every water source will be partly radioactive. Store clean water: pumps stop wherever radiation reaches them.'],
  ['DeepFrontier.Weather.RadioactiveTideStartedDescription',
    'Water sources are releasing radioactive water. It stays after the tide until it drains off the map, decays, dries into irradiated ground or is pumped out.'],
  ['DeepFrontier.RadioactiveTide.Settings.Header', 'Radioactive tide'],
  ['DeepFrontier.RadioactiveTide.Settings.Enabled', 'Radioactive tides'],
  ['DeepFrontier.RadioactiveTide.Settings.Enabled.Tooltip',
    'A late-game hazardous season that can replace a drought or badtide: water keeps flowing, but the water of every source is partly radioactive.'],
  ['DeepFrontier.RadioactiveTide.Settings.MinCycle', 'Earliest cycle'],
  ['DeepFrontier.RadioactiveTide.Settings.MinCycle.Tooltip', 'No radioactive tide happens before this cycle.'],
  ['DeepFrontier.RadioactiveTide.Settings.Chance', 'Chance per cycle (%)'],
  ['DeepFrontier.RadioactiveTide.Settings.Chance.Tooltip',
    "Chance that a cycle's hazardous season is a radioactive tide. Never two cycles in a row."],
  ['DeepFrontier.RadioactiveTide.Settings.MinDuration', 'Shortest tide (days)'],
  ['DeepFrontier.RadioactiveTide.Settings.MinDuration.Tooltip', 'Must not be longer than the longest tide.'],
  ['DeepFrontier.RadioactiveTide.Settings.MaxDuration', 'Longest tide (days)'],
  ['DeepFrontier.RadioactiveTide.Settings.MaxDuration.Tooltip', 'Must not be shorter than the shortest tide.'],
  // Moddable Weathers: weather description (ModdableWeatherSpec.DescLoc) and
  // the per-save setting descriptions (<label key> + "Desc").
  ['DeepFrontier.Weather.RadioactiveTideDescription',
    'Hazardous weather (Deep Frontier). Water keeps flowing, but part of the water of every water source is radioactive. It stays after the tide until it drains off the map, decays, dries into irradiated ground or is pumped out. Pumps stop wherever radiation reaches them.'],
  ['DeepFrontier.RadioactiveTide.Settings.EnabledDesc',
    'Whether radioactive tides can happen in this save. New saves start from the Deep Frontier mod settings.'],
  ['DeepFrontier.RadioactiveTide.Settings.MinCycleDesc', 'No radioactive tide happens before this cycle.'],
  ['DeepFrontier.RadioactiveTide.Settings.ChanceDesc',
    'Chance that a hazardous season is a radioactive tide instead of the other hazardous weathers. A percentage, not a weight. Never two cycles in a row.'],
  ['DeepFrontier.RadioactiveTide.Settings.MinDurationDesc', 'Shortest radioactive tide in days. Must not be longer than the longest tide.'],
  ['DeepFrontier.RadioactiveTide.Settings.MaxDurationDesc', 'Longest radioactive tide in days. Must not be shorter than the shortest tide.'],
];

function fail(message) { throw new Error(`Radioactive tide content: ${message}`); }

async function readText(path) {
  try { return await readFile(path, 'utf8'); } catch { fail(`required target is missing: ${path}`); }
}

// Constants from RadioactiveTideTuning.cs: `public const <type> Name = <value>;`.
export async function readTideTuning(source = TUNING_SOURCE) {
  const text = await readText(source);
  const constants = {};
  for (const [, cls, body] of text.matchAll(/public static class (\w+) \{([\s\S]*?)\n  \}/g)) {
    for (const [, type, name, value] of body.matchAll(/public const (string|int|float|bool) (\w+) = ([^;]+);/g)) {
      let parsed;
      if (type === 'string' && value.startsWith('"')) parsed = JSON.parse(value);
      else if (type === 'bool') parsed = value === 'true' ? true : value === 'false' ? false : fail(`${name}: bad bool ${value}`);
      else if (type === 'int' && /^\d+$/.test(value)) parsed = Number(value);
      else if (type === 'float' && /^\d+(\.\d+)?f$/.test(value)) parsed = Number(value.slice(0, -1));
      else parsed = {reference: value.trim()};
      constants[`${cls}.${name}`] = parsed;
    }
  }
  const resolveRef = (key) => {
    const value = constants[key];
    if (value && typeof value === 'object') {
      const target = constants[`RadioactiveTideTuning.${value.reference}`];
      if (target === undefined || typeof target === 'object') fail(`${key} refers to unknown ${value.reference}`);
      constants[key] = target;
    }
  };
  for (const key of Object.keys(constants)) resolveRef(key);
  const get = (key) => constants[key] ?? fail(`${source} defines no ${key}`);
  return {
    constants,
    weatherId: get('RadioactiveTideTuning.WeatherId'),
    iconSpritePath: get('RadioactiveTideTuning.IconSpritePath'),
    locKeys: Object.entries(constants).filter(([key]) => key.startsWith('RadioactiveTideLoc.')).map(([, value]) => value),
    get,
  };
}

export function sunOverlay(weatherId) {
  const spec = {};
  for (const stage of DAY_STAGES) {
    const {r, g, b} = FOGS[stage];
    spec[stage] = {'HazardousWeatherFogs#append': [{
      HazardousWeatherId: weatherId,
      FogSettings: {FogColor: {r, g, b, a: 1}, FogDensity: FOG_DENSITY},
    }]};
  }
  return {SunSpec: spec};
}

// Moddable Weathers 11.0.0 ModdableWeatherSpec + ModdableWeatherSkySpec
// (ModdableWeathers Weathers/ModdableWeatherSpec.cs, ModdableWeatherSkySpec.cs).
export function moddableWeatherSpec(tuning) {
  const t = (name) => tuning.get(`RadioactiveTideTuning.${name}`);
  const loc = (name) => tuning.get(`RadioactiveTideLoc.${name}`);
  const sky = {};
  for (const stage of DAY_STAGES) {
    const {r, g, b} = FOGS[stage];
    sky[MODDABLE_SKY_STAGES[stage]] = {FogColor: {r, g, b, a: 1}, FogDensity: FOG_DENSITY};
  }
  return {
    ModdableWeatherSpec: {
      Id: tuning.weatherId,
      Order: t('ModdableWeatherOrder'),
      DisplayLoc: loc('Name'),
      DescLoc: loc('ModdableDescription'),
      WeatherPanelProgressBackground: t('ModdableProgressSpritePath'),
      WeatherPanelBlinkBackground: t('ModdableBlinkSpritePath'),
      DatePanelIcon: tuning.iconSpritePath,
      WeatherNotification: t('ModdableNotificationSpritePath'),
      StartSound: t('ModdableStartSound'),
    },
    ModdableWeatherSkySpec: sky,
  };
}

export async function checkVanillaSun(weatherId) {
  const vanilla = JSON.parse(await readText(VANILLA_SUN));
  for (const stage of DAY_STAGES) {
    const fogs = vanilla.SunSpec?.[stage]?.HazardousWeatherFogs;
    if (!Array.isArray(fogs)) fail(`vanilla SunSpec.${stage}.HazardousWeatherFogs is missing`);
    const ids = fogs.map(f => f.HazardousWeatherId);
    if (!ids.includes('DroughtWeather') || !ids.includes('BadtideWeather')) fail(`vanilla SunSpec.${stage} lacks the drought/badtide fogs`);
    if (ids.includes(weatherId)) fail(`vanilla SunSpec.${stage} already has a ${weatherId} fog`);
  }
  return vanilla;
}

export function csvCell(value) {
  if (typeof value !== 'string') fail('localization cells must be strings');
  return /[",\n\r]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

async function appendLocalization(dataRoot) {
  const path = resolve(dataRoot, TIDE_FILES.localization);
  const text = await readText(path);
  if (!text.endsWith('\n')) fail(`${path} must end with a newline`);
  const ids = new Set(text.split(/\r?\n/).map(line => line.split(',')[0]));
  for (const [id] of LOCALIZATION) if (ids.has(id)) fail(`${path} already defines ${id}`);
  const rows = LOCALIZATION.map(([id, value]) => [id, value, 'Deep Frontier'].map(csvCell).join(','));
  await writeFile(path, `${text}${rows.join('\n')}\n`, 'utf8');
}

function rgbToHsv(r, g, b) {
  r /= 255; g /= 255; b /= 255;
  const max = Math.max(r, g, b), d = max - Math.min(r, g, b);
  let h = 0;
  if (d) h = 60 * (max === r ? ((g - b) / d) % 6 : max === g ? (b - r) / d + 2 : (r - g) / d + 4);
  return [h < 0 ? h + 360 : h, max ? d / max : 0, max];
}

function hsvToRgb(h, s, v) {
  const c = v * s, x = c * (1 - Math.abs((h / 60) % 2 - 1)), m = v - c;
  const [r, g, b] = h < 60 ? [c, x, 0] : h < 120 ? [x, c, 0] : h < 180 ? [0, c, x] : h < 240 ? [0, x, c] : h < 300 ? [x, 0, c] : [c, 0, x];
  return [Math.round((r + m) * 255), Math.round((g + m) * 255), Math.round((b + m) * 255)];
}

export async function renderBannerArt(source) {
  await access(source).catch(() => fail(`native badtide art missing: ${source} (run tools/asset-pipeline/export_vanilla_icon_references.py)`));
  const {data, info} = await sharp(source).ensureAlpha().raw().toBuffer({resolveWithObject: true});
  const k = BANNER_RECOLOUR;
  for (let i = 0; i < data.length; i += 4) {
    let [h, s, v] = rgbToHsv(data[i], data[i + 1], data[i + 2]);
    if (h > 360 + k.hueLow) h -= 360;
    if (s < k.minSaturation || h < k.hueLow || h > k.hueHigh) continue;
    const t = (h - k.hueLow) / (k.hueHigh - k.hueLow);   // 0 deep red .. 1 orange
    [data[i], data[i + 1], data[i + 2]] = hsvToRgb(k.greenHue - (k.greenHue - k.limeHue) * t,
      s * (k.darkSaturation + k.saturationGain * t), Math.min(1, v * (k.darkValue + k.valueGain * t)));
  }
  return {png: await sharp(data, {raw: info}).png().toBuffer(), width: info.width, height: info.height};
}

async function writeBannerArt(dataRoot) {
  const layers = [];
  let top = 0, width = 0;
  for (const [key, source] of BANNER_ART) {
    const art = await renderBannerArt(source);
    const output = resolve(dataRoot, TIDE_FILES[key]);
    await mkdir(dirname(output), {recursive: true});
    await writeFile(output, art.png);
    await writeFile(`${output}.meta.json`, JSON.stringify(ICON_META) + '\n');
    layers.push({input: source, left: 0, top}, {input: art.png, left: 0, top: top + art.height});
    top += 2 * art.height; width = Math.max(width, art.width);
  }
  const sheet = resolve(root, 'outputs', 'radioactive-tide-icons', 'radioactive-tide-banner.png');
  await mkdir(dirname(sheet), {recursive: true});
  await sharp({create: {width, height: top, channels: 4, background: {r: 40, g: 34, b: 28, alpha: 1}}}).composite(layers).png().toFile(sheet);
  return {sheet};
}

export async function renderTideIcon() {
  const svg = await readText(ICON_SVG);
  return renderNativeIcon(svg, 'building', 'RadioactiveTide', ICON_STYLE);
}

async function writeIcon(dataRoot) {
  const result = await renderTideIcon();
  const output = resolve(dataRoot, TIDE_FILES.icon);
  await mkdir(dirname(output), {recursive: true});
  await writeFile(output, result.png);
  await writeFile(`${output}.meta.json`, JSON.stringify(ICON_META) + '\n');
  const sheet = resolve(root, 'outputs', 'radioactive-tide-icons', 'radioactive-tide-icon.png');
  await mkdir(dirname(sheet), {recursive: true});
  const references = ['ico-weather-temperate', 'ico-weather-drought', 'ico-weather-badtide']
    .map(name => ({label: name, path: resolve(root, 'outputs', 'vanilla-icons', `${name}.png`)}));
  for (const reference of references) await access(reference.path).catch(() => fail(`vanilla review reference missing: ${reference.path} (run tools/asset-pipeline/export_vanilla_icon_references.py)`));
  await writeReviewSheet([{label: `RadioactiveTide ${result.stroke.toFixed(1)}px`, png: result.png}], references, sheet, 4);
  return {sheet, stroke: result.stroke, extent: result.extent};
}

export async function applyRadioactiveTide(dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')) {
  const tuning = await readTideTuning();
  const locIds = LOCALIZATION.map(([id]) => id);
  const missing = tuning.locKeys.filter(key => !locIds.includes(key));
  const extra = locIds.filter(id => !tuning.locKeys.includes(id));
  if (missing.length || extra.length) fail(`localization rows differ from RadioactiveTideLoc (missing ${missing.join(', ') || 'none'}; extra ${extra.join(', ') || 'none'})`);
  for (const [key, name] of [['progress', 'ProgressSpritePath'], ['notification', 'NotificationSpritePath']])
    if (`${tuning.get(`RadioactiveTideTuning.${name}`)}.png` !== TIDE_FILES[key]) fail(`RadioactiveTideTuning.${name} does not match ${TIDE_FILES[key]}`);
  if (`${tuning.iconSpritePath}.png` !== TIDE_FILES.icon) fail(`RadioactiveTideTuning.IconSpritePath ${tuning.iconSpritePath} does not match ${TIDE_FILES.icon}`);
  if (TIDE_FILES.moddableWeatherSpec !== `ModdableWeatherSpecs/${tuning.weatherId}.blueprint.json`) fail(`${TIDE_FILES.moddableWeatherSpec} is not named after ${tuning.weatherId}`);
  await checkVanillaSun(tuning.weatherId);

  await appendLocalization(dataRoot);
  const sunPath = resolve(dataRoot, TIDE_FILES.sun);
  await mkdir(dirname(sunPath), {recursive: true});
  await writeFile(sunPath, JSON.stringify(sunOverlay(tuning.weatherId), null, 2) + '\n', 'utf8');
  const specPath = resolve(dataRoot, TIDE_FILES.moddableWeatherSpec);
  await mkdir(dirname(specPath), {recursive: true});
  await writeFile(specPath, JSON.stringify(moddableWeatherSpec(tuning), null, 2) + '\n', 'utf8');
  const icon = await writeIcon(dataRoot);
  const banner = await writeBannerArt(dataRoot);
  console.log(`Radioactive tide content: ${LOCALIZATION.length} localization rows, ${DAY_STAGES.length} sky fogs, Moddable Weathers spec ${TIDE_FILES.moddableWeatherSpec}, icon ${TIDE_FILES.icon} (review ${icon.sheet}), banner art ${TIDE_FILES.progress} + ${TIDE_FILES.notification} (review ${banner.sheet}).`);
  return {rows: LOCALIZATION.length, fogs: DAY_STAGES.length, icon, banner};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  await applyRadioactiveTide(process.argv[2] ? resolve(process.argv[2]) : undefined);
}
