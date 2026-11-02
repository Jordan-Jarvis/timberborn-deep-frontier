// Static checks for Reactor Bot workplaces (tools/reactor_bot_workplaces.json,
// tools/reactor_bot_workplace_content.mjs, src/DeepFrontier/Scripts/SuperBots/ReactorBotWorkplace*.cs,
// ReactorBotStaffing.cs, and the specialist and workforce panel hooks):
//
// 1. The catalog: neon green light (hue 100-130 degrees, saturation >= 0.85,
//    value >= 0.95) distinct from every vanilla colour and the Reactor Bot eye
//    colour; the unlock rule; the localization texts.
// 2. The generated data: colour, singleton and localization rows match the
//    generator, one singleton, a unique colour id, no stale singleton.
// 3. The unlock rule over every Iron Teeth workplace (vanilla and generated):
//    every Reactor Bot unlock costs science.
// 4. The runtime: decorators, bindings, light priority and rule, staffing,
//    specialist hand-over, localization keys, no native event subscription in
//    Awake, and the Harmony file (editor-guarded, five verified targets).
// 5. The native contract, decompiled from the project's Timberborn plugin
//    assemblies (project ilspycmd): what the mode, the patches and the save
//    claims rely on. A game update that changes any of it fails here.
// Usage: node tools/validate_reactor_bot_workplaces.mjs
import {execFileSync} from 'node:child_process';
import {readFile, readdir, access} from 'node:fs/promises';
import {resolve, relative, basename} from 'node:path';
import {fileURLToPath} from 'node:url';
import {CONFIG, SETTINGS_PATH, SETTINGS_SPEC, VANILLA, LOCALIZATION, LOC_KEYS, colorPath, readJson, loadWorkplacesConfig,
  checkWorkplacesConfig, colorBlueprint, settingsBlueprint, localizationRows, csvRow, vanillaColorIds} from './reactor_bot_workplace_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data');
const scripts = resolve(root, 'src', 'DeepFrontier', 'Scripts');
const pluginsRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
const ilspy = resolve(root, 'tools', 'dotnet', 'ilspycmd.exe');
const errors = [];
const exists = (path) => access(path).then(() => true, () => false);

// 1. Catalog.
const config = await loadWorkplacesConfig(root);
errors.push(...checkWorkplacesConfig(config));
const color = config.illumination?.color;
const id = config.illumination?.id;
if (!errors.length) {
  const {r, g, b} = color;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const hue = max === min || max !== g ? NaN : 60 * (2 + (b - r) / (max - min));
  const saturation = max === 0 ? 0 : (max - min) / max;
  if (!(hue >= 100 && hue <= 130) || saturation < 0.85 || max < 0.95)
    errors.push(`${CONFIG}: ${r}/${g}/${b} is not a neon green (hue ${hue.toFixed(1)}, saturation ${saturation.toFixed(2)}, value ${max})`);
  const same = (c) => ['r', 'g', 'b'].every((k) => Math.abs(c[k] - color[k]) < 0.05);
  const vanillaDir = resolve(root, ...VANILLA, 'IlluminationColors');
  for (const name of (await readdir(vanillaDir)).filter((n) => n.endsWith('.blueprint.json'))) {
    const spec = (await readJson(resolve(vanillaDir, name))).IlluminationColorSpec;
    if (same(spec.Color)) errors.push(`${CONFIG}: the colour repeats vanilla IlluminationColor.${spec.Id}`);
  }
  const eyes = (await readJson(resolve(root, 'tools', 'super_bots.json'))).upgrade.illumination;
  if (same(eyes.color)) errors.push(`${CONFIG}: the colour repeats the Reactor Bot eye colour ${eyes.id}`);
  if (eyes.id === id) errors.push(`${CONFIG}: the id repeats the Reactor Bot eye colour id`);
  if ((await vanillaColorIds(root)).includes(id)) errors.push(`${CONFIG}: ${id} is a vanilla colour id`);
}

// 2. Generated data.
async function blueprints(dir, out = []) {
  for (const entry of await readdir(dir, {withFileTypes: true})) {
    const path = resolve(dir, entry.name);
    if (entry.isDirectory()) await blueprints(path, out);
    else if (entry.name.endsWith('.blueprint.json')) out.push(path);
  }
  return out;
}
const expectFile = async (path, value) => {
  let text;
  try { text = await readFile(resolve(dataRoot, path), 'utf8'); } catch { errors.push(`Data/${path} is missing; run canonical generation`); return; }
  if (text !== `${JSON.stringify(value, null, 2)}\n`) errors.push(`Data/${path} differs from tools/reactor_bot_workplace_content.mjs; regenerate`);
};
const workplaces = [];
if (!errors.length) {
  await expectFile(colorPath(id), colorBlueprint(config));
  await expectFile(SETTINGS_PATH, settingsBlueprint(config));
  if (await exists(resolve(dataRoot, 'Configurations', 'DeepFrontierReactorBotColors.blueprint.json')))
    errors.push('Data/Configurations/DeepFrontierReactorBotColors.blueprint.json is stale (replaced by the Reactor Bot workplaces singleton); delete it');
  const singletons = [], sameId = [];
  for (const path of await blueprints(dataRoot)) {
    const text = await readFile(path, 'utf8');
    if (text.includes(`"${SETTINGS_SPEC}"`)) singletons.push(relative(dataRoot, path));
    if (text.includes('"IlluminationColorSpec"') && JSON.parse(text.replace(/^﻿/, '')).IlluminationColorSpec?.Id === id) sameId.push(relative(dataRoot, path));
  }
  if (singletons.length !== 1) errors.push(`${SETTINGS_SPEC} must be in exactly one blueprint (native GetSingleSpec): ${singletons.join(', ') || 'none'}`);
  if (sameId.length !== 1) errors.push(`IlluminationColorSpec ${id} must be in exactly one blueprint: ${sameId.join(', ') || 'none'}`);
  const lines = (await readFile(resolve(dataRoot, LOCALIZATION), 'utf8')).split('\n');
  for (const [key, text] of localizationRows(config)) {
    const rows = lines.filter((line) => line.split(',')[0] === key);
    if (rows.length !== 1 || rows[0] !== csvRow(key, text)) errors.push(`${LOCALIZATION}: ${key} must appear once as generated (found ${rows.length})`);
  }
  const generation = await readFile(resolve(root, 'tools', 'create_vertical_slice_content.mjs'), 'utf8');
  const superBots = generation.indexOf("import('./super_bot_content.mjs')");
  const step = generation.indexOf("(await import('./reactor_bot_workplace_content.mjs')).applyReactorBotWorkplaces()");
  if (step < 0 || step < superBots) errors.push('tools/create_vertical_slice_content.mjs must run applyReactorBotWorkplaces after the Reactor Bots step');

  // 3. The unlock rule (ReactorBotWorkplaceSettings.ReactorUnlockCost) over every Iron Teeth workplace.
  for (const [origin, dir] of [['vanilla', resolve(root, ...VANILLA, 'Buildings')], ['generated', resolve(dataRoot, 'Buildings')]]) {
    for (const path of await blueprints(dir)) {
      if (origin === 'vanilla' && !basename(path).includes('IronTeeth')) continue;
      const value = await readJson(path);
      if (!value.WorkplaceSpec) continue;
      const bot = (value.WorkplaceSpec.WorkerTypeUnlockCosts ?? []).find((c) => c.WorkerType === 'Bot')?.ScienceCost ?? 0;
      const science = value.BuildingSpec?.ScienceCost ?? 0;
      const cost = config.unlock.botUnlockMultiplier * (bot > 0 ? bot : science + config.unlock.missingBotUnlockAddend);
      workplaces.push({name: basename(path, '.blueprint.json'), origin, bot, science, cost, disallow: !!value.WorkplaceSpec.DisallowOtherWorkerTypes});
      if (!(cost > 0)) errors.push(`${basename(path)}: the Reactor Bot unlock would be free`);
    }
  }
  if (!workplaces.some((w) => w.disallow)) errors.push('no beaver-only workplace found to check the missing bot unlock rule');
}

// 4. Runtime sources.
const read = async (path) => (await readFile(resolve(scripts, path), 'utf8')).replace(/\r\n/g, '\n');
const strip = (text) => text.replace(/\/\/.*$/gm, '');
const sources = {
  workplace: await read('SuperBots/ReactorBotWorkplace.cs'),
  light: await read('SuperBots/ReactorBotWorkplaceLight.cs'),
  unlocks: await read('SuperBots/ReactorBotWorkplaceUnlocks.cs'),
  staffing: await read('SuperBots/ReactorBotStaffing.cs'),
  patches: await read('SuperBots/ReactorBotWorkplacePatches.cs'),
  specialist: await read('Workforce/SpecialistWorkplace.cs'),
  panels: await read('Workforce/WorkforcePanels.cs'),
};
const code = Object.fromEntries(Object.entries(sources).map(([k, v]) => [k, strip(v)]));
const priority = Number(/const\s+int\s+ColorizerPriority\s*=\s*(\d+)\s*;/.exec(code.light)?.[1]);
const runtime = [
  ['workplace', /AddDecorator<WorkplaceWorkerType,\s*ReactorBotWorkplace>\(\)/, 'ReactorBotWorkplace decorated on every WorkplaceWorkerType'],
  ['workplace', /AddDecorator<DistrictDefaultWorkerType,\s*ReactorBotDistrictDefault>\(\)/, 'ReactorBotDistrictDefault decorated on DistrictDefaultWorkerType'],
  ['workplace', /AddDecorator<BotSpec,\s*ReactorBotWorker>\(\)/, 'ReactorBotWorker decorated on BotSpec'],
  ['workplace', /AddDecorator<WorkplaceIlluminator,\s*ReactorBotWorkplaceLight>\(\)/, 'the light decorated on native WorkplaceIlluminator'],
  ['workplace', /\[Context\("Game"\)\]\s*public\s+sealed\s+class\s+ReactorBotWorkplaceConfigurator\s*:\s*Configurator/, 'a Game-context configurator'],
  ...['ReactorBotWorkplaceSettings', 'ReactorBotWorkplaceRegistry', 'ReactorBotWorkplaceUnlocks', 'ReactorBotWorkplaceUi', 'ReactorBotStaffing']
    .map((name) => ['workplace', new RegExp(`Bind<${name}>\\(\\)\\.AsSingleton\\(\\)`), `${name} bound as a singleton`]),
  ...['ReactorBotWorkplace', 'ReactorBotDistrictDefault', 'ReactorBotWorker', 'ReactorBotWorkplaceLight']
    .map((name) => ['workplace', new RegExp(`Bind<${name}>\\(\\)\\.AsTransient\\(\\)`), `${name} bound as transient`]),
  ...Object.keys(settingsBlueprint({illumination: {id: ''}, unlock: {}})[SETTINGS_SPEC])
    .map((key) => ['workplace', new RegExp(`\\[Serialize\\]\\s*public\\s+\\w+\\s+${key}\\s*\\{`), `FrontierReactorBotWorkplacesSpec.${key}`]),
  ['workplace', /BotUnlockMultiplier\*basis/, 'the unlock rule: multiplier x (bot unlock, or science + addend)'],
  ['workplace', /NativeWorkerTypeAccess\.LoadBot\(WorkerType\)/, 'the saved mode restores the native Bot type on load'],
  ['workplace', /WorkerTypeChanged\+=OnWorkerTypeChanged/, 'a changed native type ends the mode'],
  ['light', /CreateColorizer\(ColorizerPriority\)/, 'the light colorizer uses ColorizerPriority'],
  ['light', /if\(_workplace\.ReactorMode\)_colorizer\.SetColor\(_settings\.WorkplaceColor\)/, 'green while the workplace is set to Reactor Bots'],
  ['staffing', /if\(workplace&&!_workplaces\.IsReactor\(workplace\)\)bot\.Worker\.Unemploy\(\)/, 'Reactor Bots released from other workplaces'],
  ['staffing', /OrderByDescending\(w=>w\.Priority\.Priority\)/, 'Reactor Bot workplaces staffed by priority'],
  ['staffing', /bot\.Citizen\.AssignedDistrict!=district/, 'staffing within the district'],
  ['specialist', /if\(workplace\.ReactorBots\)\s*\{workplace\.ClearStatus\(\);continue;\}/, 'SpecialistStaffing leaves Reactor Bot workplaces to ReactorBotStaffing'],
  ['panels', /GetComponent<ReactorBotWorkplace>\(\)\.ReactorMode/, 'the workforce panel knows the Reactor Bot mode'],
  ['unlocks', /_input\.IsKeyHeld\(InstantUnlockKey\)/, 'the native InstantUnlock key'],
  ['unlocks', /_dialogs\.Create\(\)\.SetMessage\(_loc\.T\(PromptLocKey,cost\)\)\.SetConfirmButton/, 'the native dialog box with a confirmation'],
  ['unlocks', /LoadVisualElement\("Game\/ScienceCostTooltip"\)/, 'the native locked-workplace tooltip'],
  ['patches', /^#if !UNITY_EDITOR\n[\s\S]*\n#endif\s*$/, 'the Harmony file guarded by #if !UNITY_EDITOR'],
  ['patches', /class\s+ReactorBotWorkplaceModStarter\s*:\s*IModStarter/, 'an IModStarter that applies the patches'],
  ['patches', /NativeWorkerTypeAccess\.Verify\(\)/, 'the WorkplaceWorkerType members verified at mod start'],
];
for (const [file, pattern, text] of runtime) if (!pattern.test(code[file])) errors.push(`${file}: expected ${text}`);
const targets = ['"Initialize"', '"InitializeFragment"', '"UpdateUnemployedState"', 'GetHighestPriorityUnderstaffedWorkplace', 'GetLowestPriorityStaffedWorkplace', '"SetWorkerTypeToDistrict"'];
for (const target of targets) if (!code.patches.includes(target)) errors.push(`patches: no Harmony target ${target}`);
const patchCalls = (code.patches.match(/harmony\.Patch\(/g) ?? []).length;
const requires = (code.patches.match(/Require\(/g) ?? []).length;
if (patchCalls !== 5) errors.push(`patches: expected 5 harmony.Patch calls (one in the PriorityOrderedWorkplaces loop), found ${patchCalls}`);
if (requires < 15) errors.push(`patches: expected the targets verified before patching (Require calls), found ${requires}`);
// Coordinator rule (2026-11-02): native events are subscribed after loading, not in Awake.
for (const [file, text] of Object.entries(code)) {
  for (const match of text.matchAll(/public\s+void\s+Awake\s*\(\s*\)\s*\{/g)) {
    let depth = 0, end = match.index + match[0].length - 1;
    for (let i = end; i < text.length; i++) { if (text[i] === '{') depth++; else if (text[i] === '}' && --depth === 0) { end = i; break; } }
    if (['workplace', 'light', 'staffing', 'unlocks'].includes(file) && /\+=/.test(text.slice(match.index, end)))
      errors.push(`${file}: an event is subscribed in Awake; subscribe in InitializeEntity`);
  }
}
const usedKeys = new Set(Object.values(sources).flatMap((text) => [...text.matchAll(/"(DeepFrontier\.(?:WorkerType\.ReactorBot[\w.]*|ReactorBotWorkplace\.[\w.]+))"/g)].map((m) => m[1])));
for (const key of usedKeys) if (!LOC_KEYS.includes(key)) errors.push(`C# uses ${key}, which tools/reactor_bot_workplace_content.mjs does not write`);
for (const key of LOC_KEYS) if (!usedKeys.has(key)) errors.push(`${key} is written but no C# uses it`);
if (/HarmonyLib/.test(code.workplace + code.light + code.unlocks + code.staffing)) errors.push('Harmony belongs in ReactorBotWorkplacePatches.cs only');

// 5. Native contract.
const decompile = (dll, type) => {
  try {
    return execFileSync(ilspy, [resolve(pluginsRoot, dll), '-r', pluginsRoot, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20});
  } catch (error) {
    errors.push(`${dll} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
    return '';
  }
};
const ui = 'Timberborn.WorkSystemUI.dll', work = 'Timberborn.WorkSystem.dll';
const native = {
  bot: decompile(ui, 'Timberborn.WorkSystemUI.WorkerTypeIlluminator'),
  custom: decompile('Timberborn.Illumination.dll', 'Timberborn.Illumination.CustomizableIlluminator'),
  illuminator: decompile('Timberborn.Illumination.dll', 'Timberborn.Illumination.Illuminator'),
  uiConfigurator: decompile(ui, 'Timberborn.WorkSystemUI.WorkSystemUIConfigurator'),
  toggle: decompile(ui, 'Timberborn.WorkSystemUI.WorkerTypeToggle'),
  toggleFactory: decompile(ui, 'Timberborn.WorkSystemUI.WorkerTypeToggleFactory'),
  fragment: decompile('Timberborn.GameDistrictsUI.dll', 'Timberborn.GameDistrictsUI.DistrictCenterFragment'),
  workplace: decompile(work, 'Timberborn.WorkSystem.Workplace'),
  workerType: decompile(work, 'Timberborn.WorkSystem.WorkplaceWorkerType'),
  unemployed: decompile(work, 'Timberborn.WorkSystem.UnemployedWorkers'),
  assigner: decompile(work, 'Timberborn.WorkSystem.WorkplaceAssigner'),
  unlocking: decompile(work, 'Timberborn.WorkSystem.WorkplaceUnlockingService'),
};
const contract = [
  ['bot', '_illuminatorColorizer.SetColor(_botColors.BotIlluminationColor)', 'WorkerTypeIlluminator sets the bot blue'],
  ['illuminator', '_colors.Values[_colors.Count - 1]', 'Illuminator shows its highest-priority colour'],
  ['uiConfigurator', 'AddDecorator<WorkplaceIlluminator, WorkerTypeIlluminator>()', 'WorkplaceIlluminator gets WorkerTypeIlluminator'],
  ['uiConfigurator', 'AddDecorator<WorkplaceIlluminator, Illuminator>()', 'WorkplaceIlluminator gets Illuminator'],
  ['toggle', '_sliderToggle = (string.IsNullOrWhiteSpace(toggleBindingKey) ? _sliderToggleFactory.Create(parent, sliderToggleItem, sliderToggleItem2) : _sliderToggleFactory.CreateBindable(parent, toggleBindingKey, sliderToggleItem, sliderToggleItem2));',
    'WorkerTypeToggle.Initialize builds its slider from two items'],
  ['toggleFactory', 'workerTypeToggle.Initialize(parent, toggleBindingKey);', 'WorkerTypeToggleFactory initializes every toggle'],
  ['fragment', '_sliderToggle = _sliderToggleFactory.Create(_workerTypeRoot, sliderToggleItem, sliderToggleItem2);', 'DistrictCenterFragment builds its slider from two items'],
  ['workplace', '_workplaceWorkerType.WorkerType != worker.WorkerType', 'Workplace.AssignWorker rejects another worker type'],
  ['workerType', 'if (IsWorkerTypeAllowed(workerType) && IsWorkerTypeUnlocked(workerType))\n\t\t{\n\t\t\tWorkerType = workerType;\n\t\t}\n\t\t_wasSet = component.Get(WasSetKey);',
    'WorkplaceWorkerType.Load keeps a saved type only where it is allowed and unlocked (the save fallback)'],
  ['workerType', 'if (!_wasSet && (bool)districtCenter)', 'a new workplace takes its district default once'],
  ['workerType', 'return _workplaceSpec.DefaultWorkerType == workerType;', 'DisallowOtherWorkerTypes allows only the default type'],
  ['unemployed', '_unemployed.First()', 'the native hiring pool is UnemployedWorkers._unemployed'],
  ['assigner', 'workplace.AssignWorker(_unemployedWorkers.GetUnemployedWorker());', 'native hiring takes workers from the unemployed pool'],
  ['assigner', '_priorityOrderedWorkplaces.GetHighestPriorityUnderstaffedWorkplace()', 'native hiring picks the highest-priority understaffed workplace'],
  ['assigner', '_priorityOrderedWorkplaces.GetLowestPriorityStaffedWorkplace()', 'native reassignment takes from the lowest-priority staffed workplace'],
  ['unlocking', '_workerTypeService.GetWorkerType(item.WorkerType)', 'saved native unlocks resolve their worker type on load (why Reactor Bot unlocks are saved apart)'],
];
for (const [key, text, what] of contract) if (native[key] && !native[key].replace(/\r\n/g, '\n').includes(text)) errors.push(`native contract changed: ${what}`);
const colorizer = (text) => Number(/CreateColorizer\((\d+)\)/.exec(text)?.[1]);
const botPriority = colorizer(native.bot), customPriority = colorizer(native.custom);
if (!(botPriority < priority && priority < customPriority))
  errors.push(`ColorizerPriority ${priority} must lie strictly between the native bot blue (${botPriority}) and the player's custom colour (${customPriority})`);

if (errors.length) {
  console.error(`Reactor Bot workplace validation failed:\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
const example = (name) => { const w = workplaces.find((x) => x.name === name); return w ? `${name.replace('.IronTeeth', '')} ${w.cost.toLocaleString('en-US')}` : `${name} missing`; };
console.log(`Reactor Bot workplaces: light ${id} at priority ${priority} (native bot blue ${botPriority}, custom colour ${customPriority}); ` +
  `${workplaces.length} Iron Teeth workplaces, ${workplaces.filter((w) => w.bot === 0).length} without a bot unlock; unlocks e.g. ` +
  ['Smelter.IronTeeth', 'DistrictCenter.IronTeeth', 'Restaurant.IronTeeth', 'LaunchPad.IronTeeth', 'NuclearReactor.IronTeeth'].map(example).join(', ') + '.');
