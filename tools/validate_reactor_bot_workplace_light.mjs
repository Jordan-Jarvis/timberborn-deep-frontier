// Static checks for the Reactor Bot workplace light (tools/reactor_bot_workplace_light.json,
// tools/reactor_bot_workplace_light_content.mjs, src/DeepFrontier/Scripts/SuperBots/ReactorBotWorkplaceLight.cs):
//
// 1. The catalog: a DeepFrontier* id and a neon green (hue 100-130 degrees,
//    saturation >= 0.85, value >= 0.95), distinct from every vanilla colour and
//    the Reactor Bot eye colour (tools/super_bots.json).
// 2. The generated data: the colour blueprint and the BotColors-style singleton
//    match the generator; the singleton is the only FrontierReactorBotColorsSpec
//    (native GetSingleSpec throws on two) and the colour id is unique.
// 3. The runtime: the light is decorated on WorkplaceIlluminator, ticks late,
//    tests IsReactor and JobRunning, and its colorizer priority lies strictly
//    between the native bot blue and the player's custom colour.
// 4. The native contract, decompiled from the project's Timberborn plugin
//    assemblies (project ilspycmd): the priorities, the decorators, the
//    highest-priority colour rule, the lights-on test, the late-tick order and
//    the worker-type check on assignment. A game update that changes any of
//    them fails here.
// Usage: node tools/validate_reactor_bot_workplace_light.mjs
import {execFileSync} from 'node:child_process';
import {readFile, readdir} from 'node:fs/promises';
import {resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {CONFIG, COLORS_PATH, COLORS_SPEC, VANILLA, colorPath, readJson, loadWorkplaceLightConfig, checkWorkplaceLightConfig,
  colorBlueprint, colorsBlueprint, vanillaColorIds} from './reactor_bot_workplace_light_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data');
const script = resolve(root, 'src', 'DeepFrontier', 'Scripts', 'SuperBots', 'ReactorBotWorkplaceLight.cs');
const pluginsRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Plugins', 'Timberborn');
const ilspy = resolve(root, 'tools', 'dotnet', 'ilspycmd.exe');
const errors = [];

// 1. Catalog.
const config = await loadWorkplaceLightConfig(root);
errors.push(...checkWorkplaceLightConfig(config));
const color = config.illumination?.color;
const id = config.illumination?.id;
if (!errors.length) {
  const {r, g, b} = color;
  const max = Math.max(r, g, b), min = Math.min(r, g, b);
  const hue = max === min ? NaN : max === g ? 60 * (2 + (b - r) / (max - min)) : NaN;
  const saturation = max === 0 ? 0 : (max - min) / max;
  if (!(hue >= 100 && hue <= 130) || saturation < 0.85 || max < 0.95)
    errors.push(`${CONFIG}: ${r}/${g}/${b} is not a neon green (hue ${hue.toFixed?.(1)}, saturation ${saturation.toFixed(2)}, value ${max})`);
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
  if (text !== `${JSON.stringify(value, null, 2)}\n`) errors.push(`Data/${path} differs from tools/reactor_bot_workplace_light_content.mjs; regenerate`);
};
let workplaces = 0, lit = 0;
if (!errors.length) {
  await expectFile(colorPath(id), colorBlueprint(config));
  await expectFile(COLORS_PATH, colorsBlueprint(config));
  const singletons = [], sameId = [];
  for (const path of await blueprints(dataRoot)) {
    const text = await readFile(path, 'utf8');
    if (text.includes(`"${COLORS_SPEC}"`)) singletons.push(relative(dataRoot, path));
    if (text.includes('"IlluminationColorSpec"') && JSON.parse(text.replace(/^﻿/, '')).IlluminationColorSpec?.Id === id) sameId.push(relative(dataRoot, path));
    if (text.includes('"WorkplaceSpec"')) { workplaces++; if (text.includes('"WorkplaceIlluminatorSpec"')) lit++; }
  }
  if (singletons.length !== 1) errors.push(`${COLORS_SPEC} must be in exactly one blueprint (native GetSingleSpec): ${singletons.join(', ') || 'none'}`);
  if (sameId.length !== 1) errors.push(`IlluminationColorSpec ${id} must be in exactly one blueprint: ${sameId.join(', ') || 'none'}`);
  const generation = await readFile(resolve(root, 'tools', 'create_vertical_slice_content.mjs'), 'utf8');
  const superBots = generation.indexOf("import('./super_bot_content.mjs')");
  const light = generation.indexOf("(await import('./reactor_bot_workplace_light_content.mjs')).applyReactorBotWorkplaceLight()");
  if (light < 0 || light < superBots) errors.push('tools/create_vertical_slice_content.mjs must run applyReactorBotWorkplaceLight after the Reactor Bots step');
}

// 3. Runtime source.
const source = (await readFile(script, 'utf8')).replace(/\/\/.*$/gm, '');
const priority = Number(/const\s+int\s+ColorizerPriority\s*=\s*(\d+)\s*;/.exec(source)?.[1]);
const runtime = [
  [/class\s+ReactorBotWorkplaceLight\s*:\s*TickableComponent\s*,[^{]*\bILateTickable\b/, 'ReactorBotWorkplaceLight is a TickableComponent with ILateTickable (ticks after WorkplaceIlluminator)'],
  [/AddDecorator<WorkplaceIlluminator,\s*ReactorBotWorkplaceLight>\(\)/, 'the light is decorated on native WorkplaceIlluminator'],
  [/Bind<ReactorBotColors>\(\)\.AsSingleton\(\)/, 'ReactorBotColors is bound as a singleton'],
  [/Bind<ReactorBotWorkplaceLight>\(\)\.AsTransient\(\)/, 'ReactorBotWorkplaceLight is bound as transient'],
  [/\[Context\("Game"\)\]\s*public\s+sealed\s+class\s+ReactorBotWorkplaceLightConfigurator\s*:\s*Configurator/, 'a Game-context configurator'],
  [/CreateColorizer\(ColorizerPriority\)/, 'the colorizer uses ColorizerPriority'],
  [/\.Bot\.IsReactor\s*&&\s*_bots\[i\]\.Worker\.JobRunning/, 'green while a Reactor Bot has its job running'],
  [/WorkerAssigned\s*\+=/, 'assignments are followed (WorkerAssigned)'],
  [/WorkerUnassigned\s*\+=/, 'unassignments are followed (WorkerUnassigned)'],
  [/GetSingleSpec<FrontierReactorBotColorsSpec>\(\)/, 'the colour id is read from the singleton'],
  [/record\s+FrontierReactorBotColorsSpec\s*:\s*ComponentSpec\s*\{\s*\[Serialize\]\s*public\s+string\s+WorkplaceColorId/, 'FrontierReactorBotColorsSpec {WorkplaceColorId}'],
];
for (const [pattern, text] of runtime) if (!pattern.test(source)) errors.push(`ReactorBotWorkplaceLight.cs: expected ${text}`);
if (/HarmonyLib|\[HarmonyPatch/.test(source)) errors.push('ReactorBotWorkplaceLight.cs: no Harmony (native colorizer hook)');

// 4. Native contract.
const decompile = (dll, type) => {
  try {
    return execFileSync(ilspy, [resolve(pluginsRoot, dll), '-r', pluginsRoot, '-t', type], {encoding: 'utf8', maxBuffer: 64 << 20});
  } catch (error) {
    errors.push(`${dll} ${type}: decompilation failed (${error.message.split('\n')[0]})`);
    return '';
  }
};
const colorizer = (text) => Number(/CreateColorizer\((\d+)\)/.exec(text)?.[1]);
const native = {
  bot: decompile('Timberborn.WorkSystemUI.dll', 'Timberborn.WorkSystemUI.WorkerTypeIlluminator'),
  custom: decompile('Timberborn.Illumination.dll', 'Timberborn.Illumination.CustomizableIlluminator'),
  illuminator: decompile('Timberborn.Illumination.dll', 'Timberborn.Illumination.Illuminator'),
  workplaceLight: decompile('Timberborn.WorkSystemUI.dll', 'Timberborn.WorkSystemUI.WorkplaceIlluminator'),
  configurator: decompile('Timberborn.WorkSystemUI.dll', 'Timberborn.WorkSystemUI.WorkSystemUIConfigurator'),
  ticking: decompile('Timberborn.TickSystem.dll', 'Timberborn.TickSystem.TickableEntityLifecycleManager'),
  workplace: decompile('Timberborn.WorkSystem.dll', 'Timberborn.WorkSystem.Workplace'),
};
const contract = [
  ['bot', '_workerTypeHelper.IsBotWorkerType(_workplaceWorkerType.WorkerType)', 'WorkerTypeIlluminator colours bot workplaces by worker type'],
  ['bot', '_illuminatorColorizer.SetColor(_botColors.BotIlluminationColor)', 'WorkerTypeIlluminator sets the bot blue'],
  ['illuminator', '_colors.Values[_colors.Count - 1]', 'Illuminator shows its highest-priority colour'],
  ['workplaceLight', '_workplace.AnyWorkerHasJobRunning()', 'WorkplaceIlluminator lights while any worker has its job running'],
  ['configurator', 'AddDecorator<WorkplaceIlluminatorSpec, WorkplaceIlluminator>()', 'WorkplaceIlluminatorSpec gets WorkplaceIlluminator'],
  ['configurator', 'AddDecorator<WorkplaceIlluminator, WorkerTypeIlluminator>()', 'WorkplaceIlluminator gets WorkerTypeIlluminator'],
  ['configurator', 'AddDecorator<WorkplaceIlluminator, Illuminator>()', 'WorkplaceIlluminator gets Illuminator'],
  ['ticking', '(tickable is ILateTickable) ? 1 : 0', 'ILateTickable components tick after the others of their entity'],
  ['workplace', '_workplaceWorkerType.WorkerType != worker.WorkerType', 'Workplace.AssignWorker rejects another worker type'],
];
for (const [key, text, what] of contract) if (native[key] && !native[key].includes(text)) errors.push(`native contract changed: ${what} (no "${text}")`);
const botPriority = colorizer(native.bot), customPriority = colorizer(native.custom);
if (!(botPriority < priority && priority < customPriority))
  errors.push(`ColorizerPriority ${priority} must lie strictly between the native bot blue (${botPriority}) and the player's custom colour (${customPriority})`);

if (errors.length) {
  console.error(`Reactor Bot workplace light validation failed:\n  ${errors.join('\n  ')}`);
  process.exit(1);
}
console.log(`Reactor Bot workplace light: ${id} ${color.r}/${color.g}/${color.b} at priority ${priority} ` +
  `(native bot blue ${botPriority}, custom colour ${customPriority}); ${lit} of ${workplaces} generated workplaces carry WorkplaceIlluminatorSpec.`);
