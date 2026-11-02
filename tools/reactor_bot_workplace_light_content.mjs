// Reactor Bot workplace light (tools/reactor_bot_workplace_light.json; user
// 2026-11-02: "We have blue windows when the bots are doing stuff, we should
// make it neon green when nuclear bots do things."). Runtime:
// src/DeepFrontier/Scripts/SuperBots/ReactorBotWorkplaceLight.cs.
//
// Runs in canonical generation after the Reactor Bots step:
//   await (await import('./reactor_bot_workplace_light_content.mjs')).applyReactorBotWorkplaceLight();
//
// Writes:
// - IlluminationColors/IlluminationColor.<id>: the colour (native
//   IlluminationColorSpec; no IlluminationPresetSpec, so it is not offered in
//   the player's light colour palette).
// - Configurations/DeepFrontierReactorBotColors.blueprint.json: the singleton
//   FrontierReactorBotColorsSpec {WorkplaceColorId} the runtime reads, as
//   native Configurations/BotColors.blueprint.json holds BotColorsSpec
//   {BotColorId} for the bot blue.
// Reruns rewrite both files byte-identically. It fails, without writing, on
// an invalid catalog or a colour id a vanilla colour already uses.
import {readFile, writeFile, readdir, mkdir} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const CONFIG = 'tools/reactor_bot_workplace_light.json';
export const COLORS_PATH = 'Configurations/DeepFrontierReactorBotColors.blueprint.json';
export const COLORS_SPEC = 'FrontierReactorBotColorsSpec';
export const VANILLA = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];
export const colorPath = (id) => `IlluminationColors/IlluminationColor.${id}.blueprint.json`;

export const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};

export const loadWorkplaceLightConfig = async (root = defaultRoot) => readJson(resolve(root, CONFIG));

export function checkWorkplaceLightConfig(c) {
  const errors = [];
  const keys = Object.keys(c).filter((k) => !k.startsWith('$')).sort().join(',');
  if (keys !== 'illumination') errors.push(`${CONFIG}: expected only "illumination", found ${keys}`);
  const light = c.illumination ?? {};
  if (Object.keys(light).sort().join(',') !== 'color,id') errors.push(`${CONFIG}: illumination needs exactly id and color`);
  if (!/^DeepFrontier[A-Za-z]+$/.test(light.id ?? '')) errors.push(`${CONFIG}: illumination.id must be a DeepFrontier* name (letters only)`);
  const color = light.color ?? {};
  if (Object.keys(color).sort().join(',') !== 'a,b,g,r' || !['r', 'g', 'b', 'a'].every((k) => typeof color[k] === 'number' && color[k] >= 0 && color[k] <= 1))
    errors.push(`${CONFIG}: illumination.color needs r, g, b, a in 0..1`);
  else if (color.a !== 1) errors.push(`${CONFIG}: illumination.color.a must be 1 (vanilla colours are opaque)`);
  return errors;
}

export const colorBlueprint = (c) => ({IlluminationColorSpec: {Id: c.illumination.id, Color: {...c.illumination.color}}});
export const colorsBlueprint = (c) => ({[COLORS_SPEC]: {WorkplaceColorId: c.illumination.id}});

// Vanilla IlluminationColorSpec ids (IlluminationService keeps the last
// blueprint per id, so a shared id would replace a vanilla colour).
export async function vanillaColorIds(root = defaultRoot) {
  const dir = resolve(root, ...VANILLA, 'IlluminationColors');
  const ids = [];
  for (const name of (await readdir(dir)).filter((n) => n.endsWith('.blueprint.json')).sort())
    ids.push((await readJson(resolve(dir, name))).IlluminationColorSpec.Id);
  return ids;
}

export async function planReactorBotWorkplaceLight({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const config = await loadWorkplaceLightConfig(root);
  const errors = checkWorkplaceLightConfig(config);
  if (!errors.length && (await vanillaColorIds(root)).includes(config.illumination.id))
    errors.push(`illumination id ${config.illumination.id} collides with a vanilla colour`);
  const writes = errors.length ? [] : [
    {path: resolve(dataRoot, colorPath(config.illumination.id)), value: colorBlueprint(config)},
    {path: resolve(dataRoot, COLORS_PATH), value: colorsBlueprint(config)},
  ];
  return {config, errors, writes};
}

export async function applyReactorBotWorkplaceLight({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const plan = await planReactorBotWorkplaceLight({root, dataRoot});
  if (plan.errors.length) throw new Error(`Reactor Bot workplace light: generation stopped:\n  ${plan.errors.join('\n  ')}`);
  for (const {path, value} of plan.writes) await writeJson(path, value);
  const {r, g, b} = plan.config.illumination.color;
  console.log(`Reactor Bot workplace light: ${plan.config.illumination.id} (${r}, ${g}, ${b}).`);
  return {id: plan.config.illumination.id};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applyReactorBotWorkplaceLight(dataRoot ? {dataRoot} : {})));
}
