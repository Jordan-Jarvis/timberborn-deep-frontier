// Built-in new-game setup data (docs/maps.md "Built-in maps: new-game setup").
//
// Called last from tools/create_vertical_slice_content.mjs (canonical generation):
//   await (await import('./map_setup_content.mjs')).applyMapSetup();
//
// Runtime: src/DeepFrontier/Scripts/MapSetup (BuiltinMapSetup places the objects of the built-in map
// a new game starts on; BuiltinMapHeight gives it the entry's total height through Map Transformer).
//
// Sources (the only ones): tools/map_variants/*.json, one variant per built-in map whose source is
// builtin:<Name> and hardVariant false (placements, totalHeight, mapSize, unmet), and
// tools/map_setup.json (dev maps, small-map rule, dialog text). The terrain validation of every
// placement is tools/prepare_deep_frontier_map.py builtin; tools/validate_map_setup.mjs checks that
// the generated data equals what this module derives from the sources.
//
// Writes:
// - Configurations/DeepFrontierMapSetup.blueprint.json (BuiltinMapSetupSpec)
// - enUS.csv rows DeepFrontier.MapSetup.* (dialog text and one row per unmet item)
import {readFile, writeFile, mkdir, readdir} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));

export const MAP_SETUP_FILES = {
  settings: 'Configurations/DeepFrontierMapSetup.blueprint.json',
  mapCollection: 'TemplateCollections/TemplateCollection.MapEditor.Common.blueprint.json',
  localization: 'Localizations/enUS.csv',
};
export const LOC_PREFIX = 'DeepFrontier.MapSetup.';
const ORIENTATIONS = ['Cw0', 'Cw90', 'Cw180', 'Cw270'];
const PLACEMENT_KEYS = new Set(['template', 'label', 'x', 'y', 'z', 'orientation', 'good', 'amount', 'radioactivePerHour']);
// Loc keys the runtime uses (Scripts/MapSetup/BuiltinMapSetup.cs MapSetupLoc), from tools/map_setup.json text.
export const TEXT_KEYS = ['smallTitle', 'smallIntro', 'smallReasonsHeader', 'smallSpace', 'smallHeight', 'smallNoDeepMine', 'smallNoUnmet',
  'unmetTitle', 'setupFailedTitle', 'setupFailed', 'heightFailed', 'noSetup', 'devMap'];

const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const fail = (message) => { throw new Error(`Map setup: ${message}`); };
const pascal = (key) => key[0].toUpperCase() + key.slice(1);
export const textLocKey = (key) => LOC_PREFIX + pascal(key);
export const unmetLocKey = (mapName, index) => `${LOC_PREFIX}Unmet.${mapName}.${index + 1}`;
export const unmetSitesLocKey = (mapName) => `${LOC_PREFIX}Unmet.${mapName}.Sites`;
const SITE_ITEM = /^(\w+)\.IronTeeth site \((\w+)\)$/;

// enUS display names of buildings (Building.<Id>.DisplayName), from the generated localization.
async function displayNames(dataRoot) {
  const names = new Map();
  for (const line of (await readFile(resolve(dataRoot, MAP_SETUP_FILES.localization), 'utf8')).split(/\r?\n/)) {
    const match = /^Building\.(\w+)\.DisplayName,("(?:[^"]|"")*"|[^,]*),/.exec(line);
    if (match) names.set(match[1], match[2].startsWith('"') ? match[2].slice(1, -1).replaceAll('""', '"') : match[2]);
  }
  return names;
}

const csvCell = (text) => {
  if (typeof text !== 'string') throw new TypeError('Localization cells must be authored strings.');
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
export const csvRow = (id, text) => [id, text, 'Deep Frontier map setup'].map(csvCell).join(',');

export async function readSources(root = defaultRoot) {
  const setup = await readJson(resolve(root, 'tools', 'map_setup.json'));
  if (setup.schema !== 1) fail('tools/map_setup.json schema must be 1');
  const dir = resolve(root, 'tools', 'map_variants');
  const variants = [];
  for (const name of (await readdir(dir)).filter((n) => n.endsWith('.json')).sort())
    variants.push({file: name, ...(await readJson(resolve(dir, name)))});
  return {setup, variants};
}

// Template name -> blueprint of the mod's MapEditor Common collection.
async function mapEditorTemplates(dataRoot) {
  const collection = await readJson(resolve(dataRoot, MAP_SETUP_FILES.mapCollection));
  const paths = collection.TemplateCollectionSpec?.['Blueprints#append'];
  if (!Array.isArray(paths)) fail(`${MAP_SETUP_FILES.mapCollection} has no Blueprints#append list`);
  const templates = new Map();
  for (const path of paths) {
    const blueprint = await readJson(resolve(dataRoot, `${path}.json`));
    const name = blueprint.TemplateSpec?.TemplateName;
    if (!name) fail(`${path} has no TemplateSpec.TemplateName`);
    templates.set(name, blueprint);
  }
  return templates;
}

// The BuiltinMapSetupSpec and its localization rows, derived from the sources.
export async function mapSetupContent({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const {setup, variants} = await readSources(root);
  const templates = await mapEditorTemplates(dataRoot);
  const names = await displayNames(dataRoot);
  const unmetText = setup.unmetText;
  if (typeof unmetText?.sites !== 'string' || !unmetText.sites.includes('{0}') || typeof unmetText.items !== 'object')
    fail('tools/map_setup.json unmetText needs "sites" (with {0}) and "items"');
  const text = setup.text;
  for (const key of TEXT_KEYS) if (typeof text?.[key] !== 'string' || !text[key].trim()) fail(`tools/map_setup.json text.${key} is missing`);
  const extra = Object.keys(text).filter((k) => !TEXT_KEYS.includes(k));
  if (extra.length) fail(`tools/map_setup.json text has keys the runtime does not use: ${extra.join(', ')}`);
  const small = setup.smallMap;
  const [numerator, denominator] = small.landShare;
  if (!Number.isInteger(small.maxArea) || small.maxArea <= 0) fail('smallMap.maxArea must be a positive integer (prepare_deep_frontier_map.py builtin derives it)');
  if (typeof small.deepMineSite !== 'string' || !small.deepMineSite) fail('smallMap.deepMineSite must name the Deep Mine template (prepare_deep_frontier_map.py builtin checks it)');
  const devMaps = setup.devMaps.map((d) => d.name);
  const runtime = variants.filter((v) => typeof v.source === 'string' && v.source.startsWith('builtin:') && v.hardVariant === false);
  const maps = [];
  const rows = TEXT_KEYS.map((key) => [textLocKey(key), text[key]]);
  const seen = new Set();
  for (const v of runtime) {
    const mapName = v.source.slice('builtin:'.length);
    if (seen.has(mapName)) fail(`built-in map ${mapName} has two default variants`);
    seen.add(mapName);
    if (devMaps.includes(mapName)) fail(`${v.file}: ${mapName} is listed as a dev map`);
    const totalHeight = v.height?.totalHeight;
    if (!Number.isInteger(totalHeight)) fail(`${v.file}: height.totalHeight must be an integer`);
    const {x: width, y: height} = v.mapSize ?? {};
    if (!Number.isInteger(width) || !Number.isInteger(height)) fail(`${v.file}: mapSize {x, y} is required`);
    const placements = v.placements.map((p, index) => {
      const unknown = Object.keys(p).filter((k) => !PLACEMENT_KEYS.has(k));
      if (unknown.length) fail(`${v.file} placement ${index}: unknown keys ${unknown.join(', ')}`);
      const blueprint = templates.get(p.template);
      if (!blueprint) fail(`${v.file} placement ${index}: ${p.template} is not in ${MAP_SETUP_FILES.mapCollection}`);
      if (blueprint.RadioactiveWaterSourceSpec || p.radioactivePerHour !== undefined)
        fail(`${v.file} placement ${index}: a radioactive spring is a hard-variant object; built-in new games never get one`);
      const orientation = p.orientation ?? 'Cw0';
      if (!ORIENTATIONS.includes(orientation)) fail(`${v.file} placement ${index}: orientation ${orientation}`);
      for (const key of ['x', 'y', 'z']) if (!Number.isInteger(p[key])) fail(`${v.file} placement ${index}: ${key} must be an integer`);
      if (typeof p.label !== 'string' || !p.label) fail(`${v.file} placement ${index}: label is required`);
      const stockpile = blueprint.StockpileSpec;
      if (stockpile) {
        if (typeof p.good !== 'string' || !Number.isInteger(p.amount) || p.amount <= 0 || p.amount > stockpile.MaxCapacity)
          fail(`${v.file} placement ${index}: ${p.template} needs a good and an amount of 1..${stockpile.MaxCapacity}`);
      } else if (p.good !== undefined || p.amount !== undefined) {
        fail(`${v.file} placement ${index}: ${p.template} is not a stockpile; remove good/amount`);
      }
      return {Template: p.template, Label: p.label, X: p.x, Y: p.y, Z: p.z, Orientation: orientation,
        Good: stockpile ? p.good : '', Amount: stockpile ? p.amount : 0};
    });
    // One line for every missing building site, one per other item (tools/map_setup.json unmetText).
    const unmet = v.unmet ?? [];
    const sites = [], unmetLocKeys = [];
    for (const u of unmet) {
      if (typeof u.reason !== 'string' || !u.reason.trim()) fail(`${v.file}: unmet item ${u.item} needs a reason`);
      const site = SITE_ITEM.exec(u.item);
      if (site) {
        if (!names.has(site[1])) fail(`${v.file}: unmet ${u.item}: enUS.csv has no Building.${site[1]}.DisplayName`);
        sites.push(names.get(site[1]));
      } else {
        const line = unmetText.items[u.item];
        if (typeof line !== 'string') fail(`${v.file}: unmet item "${u.item}" has no line in tools/map_setup.json unmetText.items`);
        unmetLocKeys.push(unmetLocKey(mapName, unmetLocKeys.length));
        rows.push([unmetLocKeys.at(-1), line]);
      }
    }
    if (sites.length) {
      unmetLocKeys.unshift(unmetSitesLocKey(mapName));
      rows.push([unmetSitesLocKey(mapName), unmetText.sites.replace('{0}', sites.join(', '))]);
    }
    // tools/map_setup.json smallMap: EXTREMELY difficult below maxArea, or without a primary Deep Mine site.
    if (!Array.isArray(v.sites)) fail(`${v.file}: sites must be a list`);
    const deepMineSites = v.sites.filter((s) => s.template === small.deepMineSite && !s.alternative).length;
    maps.push({MapName: mapName, VariantId: v.id, Width: width, Height: height, TotalHeight: totalHeight,
      SmallArea: width * height < small.maxArea, NoDeepMineSite: deepMineSites === 0,
      UnmetLocKeys: unmetLocKeys, Placements: placements});
  }
  maps.sort((a, b) => a.MapName.localeCompare(b.MapName));
  const spec = {
    SmallMapMaxArea: small.maxArea,
    ReferenceSiteArea: Math.floor(small.maxArea * numerator / denominator),
    DevMaps: devMaps,
    Maps: maps,
  };
  return {spec, rows};
}

export async function applyMapSetup({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const {spec, rows} = await mapSetupContent({root, dataRoot});
  const settings = resolve(dataRoot, MAP_SETUP_FILES.settings);
  await mkdir(dirname(settings), {recursive: true});
  await writeFile(settings, `${JSON.stringify({BuiltinMapSetupSpec: spec}, null, 2)}\n`, 'utf8');
  const localizationPath = resolve(dataRoot, MAP_SETUP_FILES.localization);
  const text = await readFile(localizationPath, 'utf8');
  if (!text.endsWith('\n')) fail('enUS.csv must end with a newline');
  const ids = new Set(text.split(/\r?\n/).map((line) => line.split(',')[0]));
  for (const [id] of rows) if (ids.has(id)) fail(`enUS.csv already defines ${id}`);
  await writeFile(localizationPath, text + rows.map(([id, value]) => csvRow(id, value)).join('\n') + '\n', 'utf8');
  return {maps: spec.Maps.length, small: spec.Maps.filter((m) => m.SmallArea || m.NoDeepMineSite).map((m) => m.MapName), rows: rows.length};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applyMapSetup(dataRoot ? {dataRoot} : {})));
}
