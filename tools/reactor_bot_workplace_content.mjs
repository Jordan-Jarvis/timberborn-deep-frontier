// Reactor Bot workplaces (tools/reactor_bot_workplaces.json; user 2026-11-02:
// Option 1 of docs/worker-types-study.md). The worker-type toggle reads
// Beaver | Bot | Reactor Bot; the modes are exclusive, every workplace can be
// set to Reactor Bots behind its own science unlock, and the District Center's
// default worker type has the same option. Runtime:
// src/DeepFrontier/Scripts/SuperBots/ReactorBotWorkplace*.cs.
//
// Runs in canonical generation after the Reactor Bots step:
//   await (await import('./reactor_bot_workplace_content.mjs')).applyReactorBotWorkplaces();
//
// Writes:
// - IlluminationColors/IlluminationColor.<id>: the window colour while a
//   workplace is set to Reactor Bots (native IlluminationColorSpec; no
//   IlluminationPresetSpec, so it is not offered in the player's palette).
// - Configurations/DeepFrontierReactorBotWorkplaces.blueprint.json: the
//   singleton FrontierReactorBotWorkplacesSpec the runtime reads (colour id and
//   the unlock rule), as native Configurations/BotColors holds BotColorsSpec.
// - Its rows in Localizations/enUS.csv.
// Reruns rewrite its files byte-identically; enUS.csv is rewritten fresh by
// canonical generation before this step, so none of its keys may be there
// yet. It fails, without writing, on an invalid catalog, a vanilla colour id or
// a key that is already present.
import {readFile, writeFile, readdir, mkdir} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const defaultRoot = resolve(fileURLToPath(new URL('../', import.meta.url)));
export const CONFIG = 'tools/reactor_bot_workplaces.json';
export const SETTINGS_PATH = 'Configurations/DeepFrontierReactorBotWorkplaces.blueprint.json';
export const SETTINGS_SPEC = 'FrontierReactorBotWorkplacesSpec';
export const VANILLA = ['vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources'];
export const LOCALIZATION = 'Localizations/enUS.csv';
export const LOCALIZATION_COMMENT = 'Deep Frontier Reactor Bot workplaces';
// Keys the runtime uses (ReactorBotWorkplaceUi, ReactorBotWorkplaceUnlocks, WorkforcePanels).
export const LOC_KEYS = ['DeepFrontier.WorkerType.ReactorBot', 'DeepFrontier.WorkerType.ReactorBot.Unlock.Tooltip',
  'DeepFrontier.WorkerType.ReactorBot.Unlock.Prompt', 'DeepFrontier.WorkerType.ReactorBot.Unlock.CantUnlock',
  'DeepFrontier.ReactorBotWorkplace.NoBotWear', 'DeepFrontier.ReactorBotWorkplace.InsteadOfSpecialists'];
export const colorPath = (id) => `IlluminationColors/IlluminationColor.${id}.blueprint.json`;

export const readJson = async (path) => JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, ''));
const writeJson = async (path, value) => {
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
};
const csvCell = (value) => {
  const text = String(value);
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
export const csvRow = (id, text) => [id, text, LOCALIZATION_COMMENT].map(csvCell).join(',');
const keysOf = (value) => Object.keys(value ?? {}).filter((k) => !k.startsWith('$')).sort().join(',');

export const loadWorkplacesConfig = async (root = defaultRoot) => readJson(resolve(root, CONFIG));

export function checkWorkplacesConfig(c) {
  const errors = [];
  if (keysOf(c) !== 'illumination,localization,unlock') errors.push(`${CONFIG}: expected illumination, unlock and localization, found ${keysOf(c)}`);
  const light = c.illumination ?? {};
  if (keysOf(light) !== 'color,id') errors.push(`${CONFIG}: illumination needs exactly id and color`);
  if (!/^DeepFrontier[A-Za-z]+$/.test(light.id ?? '')) errors.push(`${CONFIG}: illumination.id must be a DeepFrontier* name (letters only)`);
  const color = light.color ?? {};
  if (keysOf(color) !== 'a,b,g,r' || !['r', 'g', 'b', 'a'].every((k) => typeof color[k] === 'number' && color[k] >= 0 && color[k] <= 1))
    errors.push(`${CONFIG}: illumination.color needs r, g, b, a in 0..1`);
  else if (color.a !== 1) errors.push(`${CONFIG}: illumination.color.a must be 1 (vanilla colours are opaque)`);
  const unlock = c.unlock ?? {};
  if (keysOf(unlock) !== 'botUnlockMultiplier,missingBotUnlockAddend') errors.push(`${CONFIG}: unlock needs exactly botUnlockMultiplier and missingBotUnlockAddend`);
  if (!(Number.isInteger(unlock.botUnlockMultiplier) && unlock.botUnlockMultiplier >= 1)) errors.push(`${CONFIG}: unlock.botUnlockMultiplier must be an integer of at least 1`);
  if (!(Number.isInteger(unlock.missingBotUnlockAddend) && unlock.missingBotUnlockAddend > 0)) errors.push(`${CONFIG}: unlock.missingBotUnlockAddend must be a positive integer (the Reactor Bot option is never free)`);
  const loc = c.localization ?? {};
  if (keysOf(loc) !== [...LOC_KEYS].sort().join(',')) errors.push(`${CONFIG}: localization must hold exactly ${LOC_KEYS.join(', ')}`);
  for (const [key, text] of Object.entries(loc)) if (typeof text !== 'string' || !text.trim()) errors.push(`${CONFIG}: ${key} needs a text`);
  for (const key of ['DeepFrontier.WorkerType.ReactorBot.Unlock.Prompt', 'DeepFrontier.ReactorBotWorkplace.InsteadOfSpecialists'])
    if (!(loc[key] ?? '').includes('{0}')) errors.push(`${CONFIG}: ${key} must contain {0}`);
  return errors;
}

export const colorBlueprint = (c) => ({IlluminationColorSpec: {Id: c.illumination.id, Color: {...c.illumination.color}}});
export const settingsBlueprint = (c) => ({[SETTINGS_SPEC]: {
  WorkplaceColorId: c.illumination.id,
  BotUnlockMultiplier: c.unlock.botUnlockMultiplier,
  MissingBotUnlockAddend: c.unlock.missingBotUnlockAddend,
}});
export const localizationRows = (c) => LOC_KEYS.map((key) => [key, c.localization[key]]);

// Vanilla IlluminationColorSpec ids (IlluminationService keeps the last
// blueprint per id, so a shared id would replace a vanilla colour).
export async function vanillaColorIds(root = defaultRoot) {
  const dir = resolve(root, ...VANILLA, 'IlluminationColors');
  const ids = [];
  for (const name of (await readdir(dir)).filter((n) => n.endsWith('.blueprint.json')).sort())
    ids.push((await readJson(resolve(dir, name))).IlluminationColorSpec.Id);
  return ids;
}

export async function planReactorBotWorkplaces({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const config = await loadWorkplacesConfig(root);
  const errors = checkWorkplacesConfig(config);
  if (!errors.length && (await vanillaColorIds(root)).includes(config.illumination.id))
    errors.push(`illumination id ${config.illumination.id} collides with a vanilla colour`);
  const localizationPath = resolve(dataRoot, LOCALIZATION);
  const lines = (await readFile(localizationPath, 'utf8')).split('\n');
  if (lines.at(-1) !== '') errors.push(`${LOCALIZATION} must end with a newline`);
  const present = new Set(lines.map((line) => line.split(',')[0]));
  for (const key of LOC_KEYS) if (present.has(key)) errors.push(`${LOCALIZATION} already has ${key}`);
  const writes = errors.length ? [] : [
    {path: resolve(dataRoot, colorPath(config.illumination.id)), value: colorBlueprint(config)},
    {path: resolve(dataRoot, SETTINGS_PATH), value: settingsBlueprint(config)},
  ];
  return {config, errors, writes, lines, localizationPath};
}

export async function applyReactorBotWorkplaces({root = defaultRoot, dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')} = {}) {
  const plan = await planReactorBotWorkplaces({root, dataRoot});
  if (plan.errors.length) throw new Error(`Reactor Bot workplaces: generation stopped:\n  ${plan.errors.join('\n  ')}`);
  for (const {path, value} of plan.writes) await writeJson(path, value);
  plan.lines.pop();
  for (const [id, text] of localizationRows(plan.config)) plan.lines.push(csvRow(id, text));
  await writeFile(plan.localizationPath, `${plan.lines.join('\n')}\n`, 'utf8');
  const {r, g, b} = plan.config.illumination.color;
  console.log(`Reactor Bot workplaces: light ${plan.config.illumination.id} (${r}, ${g}, ${b}); unlock ${plan.config.unlock.botUnlockMultiplier}x the bot unlock ` +
    `(no bot unlock: science + ${plan.config.unlock.missingBotUnlockAddend}); ${LOC_KEYS.length} localization rows.`);
  return {id: plan.config.illumination.id};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const dataRoot = process.argv[2] ? resolve(process.argv[2]) : undefined;
  console.log(JSON.stringify(await applyReactorBotWorkplaces(dataRoot ? {dataRoot} : {})));
}
