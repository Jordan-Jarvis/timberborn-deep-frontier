// Static checks for workforce risks (tools/workforce_risks.json,
// tools/workforce_risk_content.mjs, src/DeepFrontier/Scripts/Workforce/).
//
//   node tools/validate_workforce_risks.mjs [dataRoot] [--design]
//
// Read-only. Checks the catalog, the installed 1.1.2.8 native contract it
// relies on (vanilla blueprints and, when present, the decompiled assemblies
// in outputs/workforce-api-1.1.2.8/original), that the runtime specs and
// localization keys match what the generator writes, and the generated data:
// - not yet applied (no settings blueprint): a dry run must have no errors;
// - applied: every declared template carries exactly the expected specs.
// The Technical School's supplies follow the taught profession everywhere the
// player and haulers see them: runtime sources, and the native contract they
// rely on, decompiled from the plugin assemblies (publicized: access modifiers
// are not matched).
// Automation declarations for the new specs are checked against
// tools/automation_content.json. Exits 1 on any error.
import {readFile, readdir, access} from 'node:fs/promises';
import {execFileSync} from 'node:child_process';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {loadWorkforceConfig, checkWorkforceConfig, planWorkforceRisks, settingsBlueprint, riskSpec, schoolSpec,
  localizationRows, SETTINGS_BLUEPRINT, COLLECTION, WORKFORCE_SPECS, NATIVE_INJURY_SPEC, TEXTS, dangerKey,
  schoolAttractionSpecs, studyNeed, studyNeedId, studyNeedPath, NEED_COLLECTION, SCHOOL_WORKSHOP_SPECS} from './workforce_risk_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const args = process.argv.slice(2);
const design = args.includes('--design');
const dataRoot = resolve(args.find((a) => !a.startsWith('--')) ?? resolve(root, 'src', 'DeepFrontier', 'Data'));
const vanilla = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'Workforce');
const decompiled = resolve(root, 'outputs', 'workforce-api-1.1.2.8', 'original');

const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const exists = (path) => access(path).then(() => true, () => false);
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);
const errors = [];
const notes = [];

const config = await loadWorkforceConfig(root);
errors.push(...checkWorkforceConfig(config).map((e) => `catalog: ${e}`));

// --- Native 1.1.2.8 contract (vanilla blueprints) ---
const groups = (await readJson(resolve(vanilla, 'Configurations', 'ProbabilityGroups.blueprint.json'))).ProbabilityGroupsSpec.Groups;
const group = groups.find((g) => g.Id === config.settings.probabilityGroupId);
if (!group) errors.push(`native: probability group ${config.settings.probabilityGroupId} does not exist`);
else for (const p of ['Low', 'Medium', 'High'])
  if (group[p] !== config.settings.nativeChances[p]) errors.push(`native: ${group.Id}.${p} is ${group[p]}, catalog says ${config.settings.nativeChances[p]}`);
const injury = await readJson(resolve(vanilla, 'Needs', `Need.Beaver.${config.settings.injuryNeedId}.blueprint.json`));
if (!injury.InjurableNeedSpec) errors.push('native: the injury need lacks InjurableNeedSpec, so the game mode InjuryChance would not apply');
if (!injury.NeedPreventingWorkSpec) errors.push('native: the injury need no longer stops work');
if (injury.NeedSpec.MinimumValue !== -1 || injury.NeedSpec.MaximumValue !== 0) errors.push('native: the injury need no longer spans [-1, 0]');
const fatigue = await readJson(resolve(vanilla, 'Needs', `Need.Beaver.${config.settings.fatigueNeedId}.blueprint.json`));
if (fatigue.NeedSpec.CharacterType !== 'Beaver') errors.push('native: the fatigue need is not a beaver need');
// Native Need: IsFavorable = Points > 0 (not never-positive); IsInCriticalState = has CriticalNeedSpec && !IsFavorable.
if (!fatigue.CriticalNeedSpec || !(fatigue.NeedSpec.MaximumValue > 0)) errors.push('native: the fatigue need must have a critical state and a positive range');
else if (!(config.settings.strainedBelowFatiguePoints < fatigue.NeedSpec.MaximumValue)) errors.push(`catalog: strainedBelowFatiguePoints must be below the fatigue maximum ${fatigue.NeedSpec.MaximumValue}`);

// --- Worker condition rule: run the exact C# body of WorkerConditions.Classify on a case table ---
const riskSource = await readFile(resolve(scripts, 'IndustrialRisk.cs'), 'utf8');
const classifyBody = riskSource.match(/public static WorkerCondition Classify\(bool fatigueCritical, float fatiguePoints, int wellbeing, FrontierWorkforceSettingsSpec s\) \{([\s\S]*?)\r?\n    \}/)?.[1];
const conditionRows = [];
if (!classifyBody) errors.push('runtime: WorkerConditions.Classify(bool fatigueCritical, float fatiguePoints, int wellbeing, FrontierWorkforceSettingsSpec s) not found in IndustrialRisk.cs');
else {
  const classify = new Function('fatigueCritical', 'fatiguePoints', 'wellbeing', 's', classifyBody.replace(/WorkerCondition\.(\w+)/g, "'$1'"));
  const spec = settingsBlueprint(config).FrontierWorkforceSettingsSpec;
  const t = spec.StrainedBelowFatiguePoints, sw = spec.StrainedBelowWellbeing, ew = spec.ExhaustedBelowWellbeing;
  const max = fatigue.NeedSpec.MaximumValue, min = fatigue.NeedSpec.MinimumValue;
  // Sleep points drive both predicates exactly as the native Need does: critical <=> points <= 0.
  const cases = [
    ['rested, content', max, sw + 10, 'Fit'],
    ['rested at the strained wellbeing line', max, sw, 'Fit'],
    ['tired (0 < sleep < threshold), content', t / 2, sw + 10, 'Strained'],
    ['sleep exactly at threshold', t, sw + 10, 'Fit'],
    ['rested, low wellbeing', max, sw - 1, 'Strained'],
    ['sleep at 0 (critical)', 0, sw + 10, 'Exhausted'],
    ['sleep at minimum', min, sw + 10, 'Exhausted'],
    ['rested, very low wellbeing', max, ew - 1, 'Exhausted'],
    ['tired and very low wellbeing', t / 2, ew - 1, 'Exhausted'],
  ];
  for (const [name, points, wellbeing, expected] of cases) {
    const actual = classify(points <= 0, points, wellbeing, spec);
    conditionRows.push([name, points, wellbeing, expected, actual]);
    if (actual !== expected) errors.push(`condition rule: ${name} (sleep ${points}, wellbeing ${wellbeing}) is ${actual}, expected ${expected}`);
  }
}
const common = (await readJson(resolve(vanilla, 'NeedCollections', 'NeedCollection.Common.blueprint.json'))).NeedCollectionSpec.Needs;
for (const need of [config.settings.injuryNeedId, config.settings.fatigueNeedId])
  if (!common.includes(need)) errors.push(`native: ${need} is not a common (Iron Teeth) need`);
const bot = await readJson(resolve(vanilla, 'Characters', 'Bot', 'Bot.IronTeeth.blueprint.json'));
const botDays = bot.DeteriorableSpec?.DeteriorationInDays;
if (!botDays) errors.push('native: Iron Teeth bots no longer have DeteriorableSpec');
const adult = await readJson(resolve(vanilla, 'Characters', 'Beaver', 'BeaverAdult.blueprint.json'));
if (!adult.AdultSpec || !adult.WorkerSpec) errors.push('native: adult beavers lack AdultSpec/WorkerSpec (SpecialistTrait decorates AdultSpec)');
if (!bot.BotSpec || !bot.WorkerSpec) errors.push('native: bots lack BotSpec/WorkerSpec (BotWear decorates BotSpec)');

// --- Decompiled assemblies: the members the Harmony patches and runtime use ---
if (await exists(decompiled)) {
  const source = async (name) => readFile(resolve(decompiled, `Timberborn.${name}.cs`), 'utf8');
  const expect = (text, needle, what) => { if (!text.includes(needle)) errors.push(`decompiled 1.1.2.8: ${what} (missing "${needle}")`); };
  const det = await source('DeteriorationSystem');
  expect(det, 'private float _currentDeterioration;', 'Deteriorable._currentDeterioration (BotWear patch)');
  expect(det, 'private float _fixedDeltaTimeInDays;', 'Deteriorable._fixedDeltaTimeInDays (BotWear patch)');
  expect(det, 'public override void Tick()', 'Deteriorable.Tick');
  const work = await source('WorkSystem');
  expect(work, 'internal class DistrictWorkplaceAssigner', 'DistrictWorkplaceAssigner');
  expect(work, 'private void OnFinishedBuildingRegistered(object sender, FinishedBuildingRegisteredEventArgs finishedBuildingRegisteredEventArgs)', 'registration handler signature');
  expect(work, 'private void OnFinishedBuildingUnregistered(object sender, FinishedBuildingUnregisteredEventArgs finishedBuildingUnregisteredEventArgs)', 'unregistration handler signature');
  expect(work, 'public void AssignWorker(Worker worker)', 'Workplace.AssignWorker');
  expect(work, 'If DisallowOtherWorkerTypes is set, WorkerTypeUnlockCosts must be empty.', 'Workplace.ValidateWorkplaceSpec rule');
  const needs = await source('NeedApplication');
  expect(needs, 'public bool CanApply(IProbabilityGroupProvider probabilityGroupProvider, NeedApplierEffectSpec spec)', 'EffectProbabilityService.CanApply');
  expect(needs, 'return num * _injuryChanceModifier;', 'game-mode injury modifier');
  expect(await source('ModManagerScene'), 'modStarterType.IsAssignableFrom(type)', 'every IModStarter is started');
} else notes.push(`decompiled contract not checked: ${decompiled} is absent`);

// --- Runtime specs and localization keys match the generator ---
const specSource = await readFile(resolve(scripts, 'WorkforceSpecs.cs'), 'utf8');
const serialized = (record) => {
  const body = specSource.match(new RegExp(`record ${record}\\b[^{]*\\{([\\s\\S]*?)\\n  \\}`))?.[1];
  if (!body) { errors.push(`runtime: record ${record} not found in WorkforceSpecs.cs`); return []; }
  return [...body.matchAll(/\[Serialize\] public [\w<>.]+ (\w+) \{/g)].map((m) => m[1]).sort();
};
const keysOf = (value) => Object.keys(value).sort();
const anyTemplate = Object.values(config.templates);
const sample = {
  FrontierWorkforceSettingsSpec: settingsBlueprint(config).FrontierWorkforceSettingsSpec,
  FrontierSpecialistDisciplineSpec: settingsBlueprint(config).FrontierWorkforceSettingsSpec.Disciplines[0],
  FrontierWorkforceRiskSpec: riskSpec(config, anyTemplate.find((e) => e.danger)),
  FrontierSpecialistWorkplaceSpec: {Discipline: ''},
  FrontierSpecialistSchoolSpec: schoolSpec(config),
  FrontierSpecialistProgramSpec: schoolSpec(config).Programs[0],
  FrontierSchoolSupplySpec: schoolSpec(config).Programs[0].Supplies[0],
};
for (const [record, value] of Object.entries(sample))
  if (!same(serialized(record), keysOf(value))) errors.push(`runtime: ${record} serializes [${serialized(record)}], generator writes [${keysOf(value)}]`);
const rows = new Map(localizationRows(config));
for (const file of (await readdir(scripts)).filter((f) => f.endsWith('.cs'))) {
  const text = await readFile(resolve(scripts, file), 'utf8');
  for (const [, key] of text.matchAll(/"(DeepFrontier\.Workforce\.[A-Za-z.]+)"/g))
    if (!rows.has(key)) errors.push(`runtime: ${file} uses localization ${key}, which the generator does not write`);
  for (const [, prefix] of text.matchAll(/\$"(DeepFrontier\.Workforce\.[A-Za-z.]+)\{/g))
    if (prefix !== 'DeepFrontier.Workforce.Danger.') errors.push(`runtime: ${file} builds an undeclared dynamic key ${prefix}{...}`);
}
for (const [key, text] of Object.entries(TEXTS)) {
  const params = new Set([...text.matchAll(/\{(\d)\}/g)].map((m) => Number(m[1])));
  if ([...params].some((p) => p > 2)) errors.push(`localization ${key}: ILoc.T takes at most three parameters`);
}
for (const tier of Object.keys(config.dangerTiers)) if (!rows.has(dangerKey(tier))) errors.push(`localization ${dangerKey(tier)} missing`);

// --- Generated data ---
const applied = await exists(resolve(dataRoot, SETTINGS_BLUEPRINT));
const collection = (await readJson(resolve(dataRoot, COLLECTION))).TemplateCollectionSpec['Blueprints#append'];
if (!applied) {
  const plan = await planWorkforceRisks({root, dataRoot});
  for (const e of plan.errors) errors.push(`dry run on ${dataRoot}: ${e}`);
  notes.push(`${dataRoot} has no ${SETTINGS_BLUEPRINT}: checked as a dry run (${plan.changed.size} templates would change)`);
} else {
  if (!same(await readJson(resolve(dataRoot, SETTINGS_BLUEPRINT)), settingsBlueprint(config))) errors.push(`${SETTINGS_BLUEPRINT} differs from the catalog`);
  for (const [id, entry] of Object.entries(config.templates)) {
    const blueprint = await readJson(resolve(dataRoot, `${id}.json`));
    const w = blueprint.WorkplaceSpec;
    if (entry.workers === 'open') {
      if (w.DisallowOtherWorkerTypes || !w.WorkerTypeUnlockCosts.some((c) => c.WorkerType === 'Bot')) errors.push(`${id}: open workplace does not allow bots`);
    } else if (!w.DisallowOtherWorkerTypes || w.DefaultWorkerType !== 'Beaver' || w.WorkerTypeUnlockCosts.length) errors.push(`${id}: not beaver-only`);
    const expected = {
      FrontierWorkforceRiskSpec: entry.danger ? riskSpec(config, entry) : undefined,
      FrontierSpecialistWorkplaceSpec: entry.workers === 'specialists' ? {Discipline: entry.discipline} : undefined,
    };
    for (const key of WORKFORCE_SPECS) if (!same(blueprint[key], expected[key])) errors.push(`${id}: ${key} is ${JSON.stringify(blueprint[key])}, expected ${JSON.stringify(expected[key])}`);
    if (entry.danger && blueprint[NATIVE_INJURY_SPEC]) errors.push(`${id}: still has native ${NATIVE_INJURY_SPEC}`);
  }
  for (const id of collection) {
    const path = resolve(dataRoot, `${id}.json`);
    if (!Object.hasOwn(config.templates, id) && await exists(path)) {
      const blueprint = await readJson(path);
      if (blueprint[NATIVE_INJURY_SPEC]) errors.push(`${id}: undeclared native ${NATIVE_INJURY_SPEC}`);
      for (const key of WORKFORCE_SPECS)
        if (blueprint[key] && !(key === 'FrontierSpecialistSchoolSpec' && id === config.school.template)) errors.push(`${id}: undeclared ${key}`);
    }
  }
  const school = await readJson(resolve(dataRoot, `${config.school.template}.json`));
  for (const [key, value] of Object.entries(schoolAttractionSpecs(config)))
    if (!same(school[key], value)) errors.push(`${config.school.template}: ${key} differs from the catalog`);
  for (const key of SCHOOL_WORKSHOP_SPECS) if (school[key]) errors.push(`${config.school.template}: still has the workshop spec ${key}`);
  if (!school.EnterableSpec?.LimitedCapacityFinished || school.EnterableSpec.CapacityFinished !== config.school.students)
    errors.push(`${config.school.template}: EnterableSpec must seat exactly ${config.school.students} students (the native attraction panel needs a limit)`);
  const books = await readJson(resolve(vanilla, 'Needs', 'Need.Beaver.Books.blueprint.json'));
  const needCollection = (await readJson(resolve(dataRoot, NEED_COLLECTION))).NeedCollectionSpec['Needs#append'];
  for (const [index, program] of config.school.programs.entries()) {
    const path = resolve(dataRoot, studyNeedPath(program));
    if (!await exists(path)) errors.push(`study need ${studyNeedId(program)} was not written`);
    else if (!same(await readJson(path), studyNeed(books, config, program, index))) errors.push(`study need ${studyNeedId(program)} differs from the catalog`);
    if (needCollection.filter((id) => id === studyNeedId(program)).length !== 1) errors.push(`${NEED_COLLECTION} must list ${studyNeedId(program)} once`);
  }
  const csv = await readFile(resolve(dataRoot, 'Localizations', 'enUS.csv'), 'utf8');
  for (const key of rows.keys()) if (!csv.includes(`\n${key},`)) errors.push(`enUS.csv lacks ${key}`);
}
for (const id of Object.keys(config.pendingTemplates))
  if (collection.includes(id)) errors.push(`${id} is generated but still pending in the catalog`);

// --- Automation: every new spec on an automatable building needs an Off-signal declaration ---
const automation = await readJson(resolve(root, 'tools', 'automation_content.json'));
const usedSpecs = new Set();
for (const [id, entry] of Object.entries(config.templates)) {
  if ((automation.templates[id]?.role ?? 'none') === 'none') continue;
  if (entry.danger) usedSpecs.add('FrontierWorkforceRiskSpec');
  if (entry.workers === 'specialists') usedSpecs.add('FrontierSpecialistWorkplaceSpec');
}
if ((automation.templates[config.school.template]?.role ?? 'none') !== 'none') usedSpecs.add('FrontierSpecialistSchoolSpec');
for (const key of usedSpecs)
  if (!automation.customSpecs[key]) errors.push(`automation: tools/automation_content.json customSpecs lacks ${key} (see the workforce report for the entry)`);

// --- Design table ---
if (design) {
  console.log('worker condition cases (C# WorkerConditions.Classify): case | sleep | wellbeing | expected | actual');
  for (const row of conditionRows) console.log(`  ${row.join(' | ')}`);
  const s = config.settings;
  const hours = 14; // rolling hours per day: inside a running workshop at default working hours (assumption)
  const unaided = 0.1; // native Injury DailyDelta
  const hospital = 0.0193 * 24; // measured full-staff Hospital recovery, points/day (STATUS hospital114)
  const overhead = 0.5; // days walking to and waiting at the hospital (assumption)
  console.log('tier       | fit %/h | strained | exhausted | heal days unaided/hospital | injured share fit: unaided / hospital | fatal per accident');
  for (const [id, t] of Object.entries(config.dangerTiers)) {
    const p = s.nativeChances[t.probability] / t.rollIntervalHours;
    const rolls = (k) => 1 - (1 - s.nativeChances[t.probability]) ** k;
    const days = [-t.injuryPoints / unaided, -t.injuryPoints / hospital + overhead];
    const share = (d) => { const x = p * hours * d; return x / (1 + x); };
    console.log(`${id.padEnd(10)} | ${(p * 100).toFixed(2).padStart(7)} | ${(rolls(s.strainedRolls) / t.rollIntervalHours * 100).toFixed(2).padStart(8)} | ${(rolls(s.exhaustedRolls) / t.rollIntervalHours * 100).toFixed(2).padStart(9)} | ${days[0].toFixed(1)} / ${days[1].toFixed(1)}`.padEnd(70)
      + ` | ${(share(days[0]) * 100).toFixed(0)}% / ${(share(days[1]) * 100).toFixed(0)}% | ${(t.fatalAccidentChance * 100).toFixed(0)}%`);
  }
  console.log(`bot wear (native life ${botDays} days):`);
  for (const [id, e] of Object.entries(config.templates)) if (e.botWear) console.log(`  ${id.split('/').at(-1).replace('.IronTeeth.blueprint', '')}: ${e.botWear}x -> ${(botDays / e.botWear).toFixed(1)} days working there`);
}

// --- Technical School supplies follow the taught profession ---
// Runtime: the consumer's goods, the inventory's allowed amounts, the native
// supply panel, the tooltip and the school panel all use only the taught
// profession's supplies.
{
  const school = await readFile(resolve(scripts, 'SpecialistSchool.cs'), 'utf8');
  const inventory = await readFile(resolve(scripts, 'SchoolSupplyInventory.cs'), 'utf8');
  const panelPatch = await readFile(resolve(scripts, 'SchoolSupplyPanel.cs'), 'utf8');
  const panels = await readFile(resolve(scripts, 'WorkforcePanels.cs'), 'utf8');
  const need = (text, pattern, what) => { if (!pattern.test(text)) errors.push(`school supplies: ${what}`); };
  need(school, /public ImmutableArray<ConsumedGoodSpec> Supplies=>Discipline==null\?ImmutableArray<ConsumedGoodSpec>\.Empty:_supplies\[Discipline\];/,
    'SpecialistSchool.Supplies must be the taught profession\'s supplies, empty without one');
  need(school, /public int AllowedAmount\(string goodId\) \{\s*foreach\(var good in Supplies\)\s*if\(good\.GoodId==goodId\)return Mathf\.CeilToInt\(good\.GoodPerHour\*_allSupplies\.FullInventoryWorkHours\);\s*return 0;\s*\}/,
    'SpecialistSchool.AllowedAmount must allow only the taught supplies, each at its native capacity ceil(goods per hour x FullInventoryWorkHours)');
  need(school, /ConsumerSpecField\.SetValue\(_consumer,_allSupplies with \{ConsumedGoods=goods\}\);/, 'ApplySupplies must give the native consumer the taught goods only');
  need(school, /MaximumWorkingTimeSetter\.Invoke\(_consumer,new object\[\]\{_allSupplies\.FullInventoryWorkHours\+1f\/goods\.Max\(g=>g\.GoodPerHour\)\}\);/,
    'ApplySupplies must set MaximumWorkingTime by the native formula over the taught goods');
  need(school, /foreach\(var good in _allSupplies\.ConsumedGoods\)\s*DisallowedGoodsChanged\?\.Invoke/, 'ApplySupplies must notify the inventory for every good');
  need(inventory, /initializer\.AddGoodDisallower\(school\);/, 'SchoolSupplyInventory must make the school its inventory\'s IGoodDisallower');
  if (!(panelPatch.trimStart().startsWith('#if !UNITY_EDITOR') && panelPatch.trimEnd().endsWith('#endif')))
    errors.push('school supplies: SchoolSupplyPanel.cs must be wrapped in #if !UNITY_EDITOR');
  need(panelPatch, /class SchoolSupplyPanelModStarter : IModStarter \{\s*public void StartMod\(IModEnvironment modEnvironment\) \{\s*SchoolSupplyPanel\.Verify\(\);[\s\S]*?CreateClassProcessor\(typeof\(SchoolSupplyFragmentPatch\)\)\.Patch\(\);\s*harmony\.CreateClassProcessor\(typeof\(SchoolSupplyDescriberPatch\)\)\.Patch\(\);/,
    'SchoolSupplyPanel must verify the native contract, then apply both patches at mod start');
  need(panelPatch, /\[HarmonyPatch\(typeof\(GoodConsumingBuildingFragment\), nameof\(GoodConsumingBuildingFragment\.UpdateFragment\)\)\]\s*internal static class SchoolSupplyFragmentPatch \{\s*private static void Postfix\(/,
    'the supply panel patch is a postfix on GoodConsumingBuildingFragment.UpdateFragment');
  need(panelPatch, /var school = ____goodConsumingBuilding\.GetComponent<SpecialistSchool>\(\);\s*if \(!school\) return;\s*if \(school\.Discipline == null\) \{\s*____root\.ToggleDisplayStyle\(visible: false\);/,
    'the supply panel patch leaves other buildings alone and hides the supply panel while nothing is taught');
  need(panelPatch, /if \(inventory\.LimitedAmount\(row\.GoodId\) <= 0 && inventory\.AmountInStock\(row\.GoodId\) <= 0\) row\.Hide\(\);/,
    'the supply panel patch hides rows by the native InventoryRowUpdater.ShouldShow rule');
  need(panelPatch, /if \(school && school\.Discipline == null\) __result = __result\.Where\(description => !description\.Input\)\.ToList\(\);/,
    'the tooltip patch drops the supply section only while the school teaches nothing');
  need(panels, /component\.Supplies\.Select\(/, 'the school panel lists the taught profession\'s supplies');
  if (/_allSupplies|FrontierSpecialistSchoolSpec/.test(panels)) errors.push('school supplies: the school panel must not list every profession\'s supplies');
}
// Native contract (Timberborn 1.1.2.8, decompiled from the plugin assemblies).
{
  const plugins = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
  const decompile = (dll, type) => {
    try {
      return execFileSync(resolve(root, 'tools', 'dotnet', 'ilspycmd.exe'), [resolve(plugins, dll), '-r', plugins, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20}).replace(/\r\n/g, '\n');
    } catch (error) {
      errors.push(`native: ${dll} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
      return null;
    }
  };
  for (const [dll, type, patterns, what] of [
    ['Timberborn.GoodConsumingBuildingSystem.dll', 'Timberborn.GoodConsumingBuildingSystem.GoodConsumingBuilding',
      [/(?:private|public) GoodConsumingBuildingSpec _goodConsumingBuildingSpec;/, /(?:private|public) readonly List<float> _suppliesLeft = new List<float>\(\);/,
        /public float MaximumWorkingTime \{ get; (?:private )?set; \}/, /public ImmutableArray<ConsumedGoodSpec> ConsumedGoods => _goodConsumingBuildingSpec\.ConsumedGoods;/,
        /MaximumWorkingTime = \(float\)_goodConsumingBuildingSpec\.FullInventoryWorkHours \+ 1f \/ ConsumedGoods\.Max\(/],
      'the consumer reads its goods from its private spec field and computes MaximumWorkingTime from them'],
    ['Timberborn.GoodConsumingBuildingSystem.dll', 'Timberborn.GoodConsumingBuildingSystem.GoodConsumingBuildingInventoryInitializer',
      [/int amount = Mathf\.CeilToInt\(current\.GoodPerHour \* \(float\)component\.FullInventoryWorkHours\);/],
      'a consumed good\'s capacity is ceil(goods per hour x FullInventoryWorkHours)'],
    ['Timberborn.GoodConsumingBuildingSystem.dll', 'Timberborn.GoodConsumingBuildingSystem.GoodConsumingBuildingStatusInitializer',
      [/_goodConsumingBuilding\.ConsumedGoods\.GetEnumerator\(\)/], 'the lack-of-supplies status checks the consumer\'s goods'],
    ['Timberborn.GoodConsumingBuildingSystemUI.dll', 'Timberborn.GoodConsumingBuildingSystemUI.GoodConsumingBuildingFragment',
      [/\.ShowRowLimit\(\)\.ShowEmptyRows\(\)/, /(?:private|public) GoodConsumingBuilding _goodConsumingBuilding;/, /(?:private|public) VisualElement _root;/, /(?:private|public) InventoryFragment _inventoryFragment;/,
        /_inventoryFragment\.UpdateFragment\(\);\s*UpdateProgressBar\(\);\s*_root\.ToggleDisplayStyle\(visible: true\);/],
      'the supply panel shows a row for every allowed good, then its root, in UpdateFragment'],
    ['Timberborn.GoodConsumingBuildingSystemUI.dll', 'Timberborn.GoodConsumingBuildingSystemUI.GoodConsumingBuildingDescriber',
      [/if \(_blockObject\.IsPreview \|\| _blockObject\.IsUnfinished\)\s*\{\s*yield return DescribeSupply\(\);/, /EntityDescription\.CreateInputSectionWithTime\(/,
        /_goodConsumingBuilding\.ConsumedGoods\.GetEnumerator\(\)/],
      'the tooltip of an unbuilt or unfinished building lists the consumer\'s goods as an input section'],
    ['Timberborn.BlockObjectTools.dll', 'Timberborn.BlockObjectTools.PreviewFactory',
      [/componentSlow\.GetComponent<BlockObject>\(\)\.MarkAsPreviewAndInitialize\(\);\s*return componentSlow;/],
      'tool previews are instantiated without InitializeEntity (so the school has no profession there)'],
    ['Timberborn.InventorySystemUI.dll', 'Timberborn.InventorySystemUI.InventoryFragment',
      [/(?:private|public) readonly List<InformationalRow> _rows = new List<InformationalRow>\(\);/, /if \(_showEmptyRows \|\| row\.CurrentAmount > 0\)/],
      'inventory fragment rows live in _rows and show when empty rows are on'],
    ['Timberborn.InventorySystemUI.dll', 'Timberborn.InventorySystemUI.InventoryRowUpdater',
      [/bool num = inventory\.LimitedAmount\(goodId\) > 0;\s*bool flag = inventory\.AmountInStock\(goodId\) > 0;\s*return num \|\| flag;/],
      'workshop panels show a good while it is allowed or in stock (the rule the school panel uses)'],
    ['Timberborn.InventorySystem.dll', 'Timberborn.InventorySystem.Inventory',
      [/return Math\.Min\(_goodDisallower\.AllowedAmount\(goodId\), _allowedGoods\.GetAmount\(goodId\)\);/,
        /if \(num > 0\)\s*\{\s*capacity\.Add\(new GoodAmount\(goodId, num\)\);/, /(?:private|public) void OnDisallowedGoodsChanged\(object sender, DisallowedGoodsChangedEventArgs e\)\s*\{\s*CheckIfUnwantedStockAppeared\(\);/],
      'the disallower caps each good, only goods it allows are requested, and a change marks leftovers as unwanted stock'],
    ['Timberborn.Emptying.dll', 'Timberborn.Emptying.EmptyingStarter',
      [/IEnumerable<GoodAmount> goods = \(unwantedStock \? inventory\.UnreservedUnwantedStock\(\) : GetUnreservedGoods\(inventory\)\);/],
      'haulers carry unwanted stock out'],
  ]) {
    const text = decompile(dll, type);
    if (text !== null && !patterns.every((p) => p.test(text))) errors.push(`native: ${type}: no longer true that ${what}`);
  }
}

for (const note of notes) console.log(`note: ${note}`);
if (errors.length) {
  console.error(`Workforce risks: ${errors.length} error(s)\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`Workforce risks: OK (${applied ? 'applied data' : 'dry run'}; ${Object.keys(config.templates).length} templates, ${Object.keys(config.pendingTemplates).length} pending).`);
