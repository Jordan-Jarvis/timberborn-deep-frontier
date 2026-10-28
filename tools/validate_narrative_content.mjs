// Static checks for the narrative layer (tools/narrative_content.mjs and
// src/DeepFrontier/Scripts/Narrative). Usage:
//   node tools/validate_narrative_content.mjs [dataRoot]
// Static evidence only: it does not establish triggers firing, dialogs, the
// journal UI, cache surveys or save/reload in game.
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve, relative, sep} from 'node:path';
import {fileURLToPath} from 'node:url';
import {NARRATIVE_FILES, CACHE, STAGES, DISCOVERIES, ENDINGS, UI_ROWS, narrativeSpec, localizationRows,
  checkAuthoredContent, checkTargets, referencedTargets} from './narrative_content.mjs';
import {mapObjectModel, mapObjectCollider} from './map_object_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Narrative');
const vanilla = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const failures = [];
const assert = (condition, message) => { if (!condition) failures.push(message); };
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

async function blueprintFiles(dir) {
  const result = [];
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) result.push(...await blueprintFiles(path));
    else if (entry.name.endsWith('.blueprint.json')) result.push(path);
  }
  return result;
}

// ---- Authored content and trigger targets ----
for (const error of checkAuthoredContent()) failures.push(`authored: ${error}`);
for (const error of await checkTargets(dataRoot)) failures.push(`target: ${error}`);

// ---- Settings blueprint ----
const settingsPath = resolve(dataRoot, NARRATIVE_FILES.settings);
if (!await exists(settingsPath)) failures.push(`missing ${NARRATIVE_FILES.settings}`);
else assert(same((await readJson(settingsPath)).NarrativeSettingsSpec, narrativeSpec()), 'NarrativeSettingsSpec differs from tools/narrative_content.mjs');

// Exactly one blueprint carries the singleton spec; the cache spec lives only on map objects.
const blueprints = await blueprintFiles(dataRoot);
const holders = {NarrativeSettingsSpec: [], HumanRecordCacheSpec: []};
for (const path of blueprints) {
  const value = await readJson(path);
  for (const key of Object.keys(holders)) if (value[key]) holders[key].push(relative(dataRoot, path).split(sep).join('/'));
}
assert(same(holders.NarrativeSettingsSpec, [NARRATIVE_FILES.settings]), `NarrativeSettingsSpec must be on exactly ${NARRATIVE_FILES.settings}: ${holders.NarrativeSettingsSpec}`);
assert(holders.HumanRecordCacheSpec.every((p) => p.startsWith('MapEditor/')), `HumanRecordCacheSpec only on map objects (no automation role): ${holders.HumanRecordCacheSpec}`);

// ---- Human Record Cache map object ----
const cachePath = resolve(dataRoot, `${NARRATIVE_FILES.cache}.json`);
if (!await exists(cachePath)) failures.push(`missing ${NARRATIVE_FILES.cache}`);
else {
  const cache = await readJson(cachePath);
  const base = await readJson(resolve(vanilla, 'MapEditor', 'Objects', CACHE.template, `${CACHE.template}.blueprint.json`));
  assert(cache.TemplateSpec.TemplateName === CACHE.templateName, 'cache template name');
  assert(same(cache.HumanRecordCacheSpec, CACHE.spec), 'HumanRecordCacheSpec differs from CACHE.spec');
  assert(cache.PlaceableBlockObjectSpec.ToolGroupId === CACHE.toolGroup && cache.PlaceableBlockObjectSpec.ToolOrder === CACHE.toolOrder, 'cache tool group/order');
  assert(!cache.BuildingSpec, 'the cache is a map object, not a building');
  assert(same(cache.BlockObjectSpec, base.BlockObjectSpec) && same(cache.Children['#Underground'], base.Children['#Underground']),
    `cache keeps the vanilla ${CACHE.template} blocks and underground part`);
  assert(cache.Children['#Model']?.TimbermeshSpec?.Model === mapObjectModel(CACHE.templateName)
    && same(cache.Children['#Model'].CollidersSpec, mapObjectCollider(CACHE.templateName)),
    'cache uses its own vault model and collider (tools/map_objects.json)');
  assert(await exists(resolve(dataRoot, `${mapObjectModel(CACHE.templateName)}.timbermesh`)), 'cache vault model is exported into Data');
  assert(cache.DemolishableSpec && cache.DemolishableScienceRewardSpec, 'cache keeps native relic demolition');
  assert(CACHE.spec.SurveyRadius >= 1 && CACHE.spec.SurveyHours > 0 && CACHE.spec.RewardAmount >= 1, 'cache survey values are positive');
  const mapCollection = (await readJson(resolve(dataRoot, NARRATIVE_FILES.mapCollection))).TemplateCollectionSpec['Blueprints#append'];
  assert(mapCollection.filter((p) => p === NARRATIVE_FILES.cache).length === 1, 'cache listed once in the Common map-editor collection');
  for (const path of blueprints) {
    const value = await readJson(path);
    if (path !== cachePath && value.PlaceableBlockObjectSpec?.ToolGroupId === CACHE.toolGroup && value.PlaceableBlockObjectSpec.ToolOrder === CACHE.toolOrder)
      failures.push(`${path} shares ${CACHE.toolGroup}#${CACHE.toolOrder} with the cache`);
  }
  const icon = cache.LabeledEntitySpec.Icon;
  assert(icon === CACHE.icon && await exists(resolve(dataRoot, `${icon}.png`)), `cache icon must be its own ${CACHE.icon}.png`);
}

// ---- Who produces the evidence goods (generated or planned buildings) ----
const progression = await readJson(resolve(root, 'tools', 'frontier_progression.json'));
const recipeProducts = new Map();
for (const file of await readdir(resolve(dataRoot, 'Recipes'))) {
  if (!file.endsWith('.blueprint.json')) continue;
  const spec = (await readJson(resolve(dataRoot, 'Recipes', file))).RecipeSpec;
  recipeProducts.set(spec.Id, spec.Products.map((p) => p.Id));
}
const runners = new Map();
const addRunner = (recipe, who) => runners.set(recipe, [...(runners.get(recipe) ?? []), who]);
for (const path of blueprints) {
  const value = await readJson(path);
  for (const id of value.ManufactorySpec?.ProductionRecipeIds ?? []) addRunner(id, value.TemplateSpec?.TemplateName ?? path);
}
for (const planned of progression.plannedBuildings ?? []) for (const id of planned.recipes) addRunner(id, `${planned.id} (planned)`);
const {goods, recipes} = referencedTargets();
for (const good of [...goods, CACHE.spec.RewardGoodId]) {
  const sources = [...recipeProducts].filter(([, products]) => products.includes(good)).flatMap(([id]) => runners.get(id) ?? []);
  assert(sources.length > 0, `${good}: no generated or planned building runs a recipe that produces it`);
  console.log(`${good}: produced by ${[...new Set(sources)].join(', ') || 'nothing'}`);
}
for (const recipe of [...recipes, CACHE.spec.SurveyRecipeId]) {
  assert((runners.get(recipe) ?? []).length > 0, `${recipe}: no generated or planned building runs it`);
  console.log(`${recipe}: run by ${(runners.get(recipe) ?? []).join(', ') || 'nothing'}`);
}

// ---- Localization ----
const loc = new Map((await readFile(resolve(dataRoot, NARRATIVE_FILES.localization), 'utf8')).split(/\r?\n/).slice(1).filter(Boolean)
  .map((line) => [line.split(',')[0], line]));
const spec = narrativeSpec();
const specKeys = [...spec.Stages, ...spec.Discoveries].flatMap((s) => [s.TitleLocKey, s.ObjectiveLocKey, s.HintLocKey, ...s.StoryLocKeys,
  ...s.Requirements.flatMap((r) => [r.LabelLocKey, ...r.VariantLocKeys])]).filter(Boolean)
  .concat(spec.Endings.flatMap((e) => [e.TitleLocKey, e.DescriptionLocKey, ...e.EpilogueLocKeys]));
const csharpFiles = (await readdir(scripts)).filter((f) => f.endsWith('.cs'));
const csharp = (await Promise.all(csharpFiles.map((f) => readFile(resolve(scripts, f), 'utf8')))).join('\n');
const codeKeys = [...new Set([...csharp.matchAll(/"(Narrative\.[A-Za-z.]+)"/g)].map((match) => match[1]))];
const cacheBlueprint = await exists(cachePath) ? await readJson(cachePath) : null;
const labelKeys = cacheBlueprint ? ['DisplayNameLocKey', 'DescriptionLocKey', 'FlavorDescriptionLocKey'].map((k) => cacheBlueprint.LabeledEntitySpec[k]) : [];
for (const key of [...specKeys, ...codeKeys, ...labelKeys]) assert(loc.has(key), `missing enUS row ${key}`);
for (const [id] of localizationRows()) assert(loc.has(id), `missing authored enUS row ${id}`);
for (const key of codeKeys) assert(UI_ROWS.some(([id]) => id === key), `${key} is used by C# but not authored in UI_ROWS`);
for (const [id] of UI_ROWS) assert(codeKeys.includes(id) || id.startsWith('Building.HumanRecordCache.'), `UI row ${id} is unused by the narrative C#`);
// Placeholder counts the code passes.
const placeholders = {'Narrative.Notification.Chapter': 1, 'Narrative.Notification.Discovery': 1, 'Narrative.Dialog.Chapter': 2,
  'Narrative.Dialog.Reward': 1, 'Narrative.Dialog.Decision': 1, 'Narrative.Journal.Widget': 2, 'Narrative.Journal.Current': 3,
  'Narrative.Journal.Progress': 3, 'Narrative.Journal.ProgressDone': 1, 'Narrative.Journal.Hint': 1, 'Narrative.Journal.ChooseButton': 1,
  'Narrative.Journal.Chosen': 1, 'Narrative.Journal.Discoveries': 2, 'Narrative.Journal.DiscoveryPending': 1, 'Narrative.Journal.ChapterEntry': 2,
  'Narrative.Cache.NoSurveyor': 1, 'Narrative.Cache.Surveying': 1, 'Narrative.Cache.WaitingForStorage': 2, 'Narrative.Cache.Reward': 2};
for (const [key, count] of Object.entries(placeholders)) {
  const text = UI_ROWS.find(([id]) => id === key)?.[1] ?? '';
  for (let i = 0; i < count; i++) assert(text.includes(`{${i}}`), `${key} must contain {${i}}`);
  assert(!text.includes(`{${count}}`), `${key} has more placeholders than the code passes`);
}
for (const [id, text] of localizationRows()) if (!UI_ROWS.some(([k]) => k === id)) assert(!/\{\d\}/.test(text), `${id}: story text has no placeholders`);

// ---- C# spec contract matches the authored JSON ----
const specSource = await readFile(resolve(scripts, 'NarrativeSpecs.cs'), 'utf8');
const fields = (record) => {
  const body = specSource.match(new RegExp(`record ${record}\\b[^{]*\\{([\\s\\S]*?)\\n  \\}`))?.[1] ?? '';
  return [...body.matchAll(/\[Serialize\] public [^ ]+ (\w+)/g)].map((match) => match[1]).sort();
};
assert(same(fields('NarrativeSettingsSpec'), Object.keys(spec).sort()), 'NarrativeSettingsSpec C# fields match the blueprint');
assert(same(fields('NarrativeStageSpec'), Object.keys(spec.Stages[0]).sort()), 'NarrativeStageSpec C# fields match the blueprint');
assert(same(fields('NarrativeRequirementSpec'), Object.keys(spec.Stages[0].Requirements[0]).sort()), 'NarrativeRequirementSpec C# fields match the blueprint');
assert(same(fields('NarrativeEndingSpec'), Object.keys(spec.Endings[0]).sort()), 'NarrativeEndingSpec C# fields match the blueprint');
assert(same(fields('HumanRecordCacheSpec'), Object.keys(CACHE.spec).sort()), 'HumanRecordCacheSpec C# fields match the module');
const service = await readFile(resolve(scripts, 'NarrativeObjectiveService.cs'), 'utf8');
for (const kind of ['BuildingFinished', 'GoodProduced', 'RecipeCompleted', 'MissionCompleted', 'EndingChosen', 'CachesSurveyed'])
  assert(service.includes(`${kind}="${kind}"`), `service implements requirement kind ${kind}`);
assert(/AddDecorator<Manufactory,NarrativeProductionReporter>/.test(csharp) && /AddDecorator<HumanRecordCacheSpec,HumanRecordCache>/.test(csharp),
  'narrative decorators are registered');
assert(/\[Context\("Game"\)\]\s*public sealed class NarrativeConfigurator/.test(csharp), 'NarrativeConfigurator is a Game context configurator');
assert(/\[Context\("Game"\)\]\s*public sealed class NarrativeJournalConfigurator/.test(csharp), 'NarrativeJournalConfigurator is a Game context configurator');
const journal = await readFile(resolve(scripts, 'NarrativeJournal.cs'), 'utf8');
assert(journal.startsWith('#if !UNITY_EDITOR') && journal.trimEnd().endsWith('#endif'), 'TimberUi journal code is guarded for the editor (Win64-only plugin)');
for (const file of csharpFiles.filter((f) => f !== 'NarrativeJournal.cs'))
  assert(!/using TimberUi/.test(await readFile(resolve(scripts, file), 'utf8')), `${file}: TimberUi only in the guarded journal file`);

// ---- Story bible lists every chapter, discovery and ending ----
const bible = await readFile(resolve(root, 'docs', 'story.md'), 'utf8');
for (const id of [...STAGES, ...DISCOVERIES, ...ENDINGS].map((e) => e.id)) assert(bible.includes(`\`${id}\``), `docs/story.md does not list \`${id}\``);

if (failures.length) {
  console.error(`NARRATIVE VALIDATION FAILED (${failures.length}):\n- ${failures.join('\n- ')}`);
  process.exit(1);
}
console.log(`Narrative validation passed (${dataRoot}): ${STAGES.length} chapters, ${DISCOVERIES.length} discoveries, ${ENDINGS.length} endings, ${localizationRows().length} enUS rows.`);
