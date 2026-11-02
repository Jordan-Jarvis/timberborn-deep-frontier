// Building tooltip text stays vanilla-short (player feedback 2026-11-01: the
// tooltips took half the screen). Usage:
//   node tools/validate_building_descriptions.mjs [dataRoot]
//
// Contract, checked on the generated Localizations/*.csv:
// - every Building.<Id>.Description is at most DESCRIPTION_MAX characters and
//   their mean at most DESCRIPTION_MEAN_MAX. Vanilla Iron Teeth descriptions are
//   at most 154 characters (mean 57); ours may add the one shared upkeep or pipe
//   clause (bot_upkeep_content.mjs, connection_content.mjs PIPE_PHRASES). The
//   native tooltip lists cost, science, workers, power and recipes, so the
//   producers keep those numbers out of the prose;
// - no generated placeholder ("... production building") and no "×" boost
//   notation (players read "1×" as a puzzle);
// - every Building.<Id>.FlavorDescription is at most FLAVOR_MAX characters;
// - the sections Deep Frontier adds to a building's tooltip before it is built
//   (TOOLTIP_SECTIONS: smog, scrubber, cryogenic storage) are at most
//   SECTION_MAX characters each.
// Naming and wording, on every row (second description pass 2026-11-01: "make
// sure they are clear and make sense"), in the vanilla 1.1 enUS style:
// - building names in Title Case (vanilla "Deep Water Pump", "Overhang 2x1"):
//   every word capitalized except SMALL_WORDS and a trailing "(N high)";
// - good names in sentence case (vanilla "Metal block" / "Metal blocks"), each
//   good with both its singular and its plural row;
// - a flavor line belongs to one building; only size variants of one family
//   (the id without its NxN / Hn suffix) share one;
// - every Recipe.* row is the DisplayLocKey of a recipe in Data/Recipes (recipes
//   without an authored name show their product's plural; no dead rows);
// - no "×" sign anywhere ("2 times", or "2x" on a slider), no INTERNAL_TERMS,
//   US spelling as in the vanilla enUS text (UK_SPELLINGS), and none of the
//   RETIRED_TERMS (names and labels the game no longer shows).
// The producers own the text (create_frontier_expansion_content.mjs BUILDING_TEXT
// and the modules it names); this check only measures it.
import {readFile, readdir} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {parseCsvRow} from './connection_content.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : resolve(root, 'src', 'DeepFrontier', 'Data');

export const DESCRIPTION_MAX = 200;
export const DESCRIPTION_MEAN_MAX = 120;
export const FLAVOR_MAX = 100;
export const SECTION_MAX = 100;
export const TOOLTIP_SECTIONS = ['DeepFrontier.Smog.Emitter.Planned', 'DeepFrontier.Smog.Emitter.Mitigation',
  'DeepFrontier.Smog.Scrubber.Planned', 'DeepFrontier.Cryogenics.Describe.Rules'];
export const SMALL_WORDS = new Set(['a', 'and', 'for', 'in', 'of', 'on', 'the', 'to']);
export const INTERNAL_TERMS = [/\bblueprints?\b/i, /\bspecs?\b/i, /\bstockpiles?\b/i, /\bticks?\b/i,
  /\bunderstructures?\b/i, /\bauthored\b/i, /\bplaceholder\b/i];
export const UK_SPELLINGS = [/colour/i, /labell/i, /fuell/i, /travell/i, /humour/i, /neighbour/i, /\bdistils\b/i, /\bcentre\b/i];
// [pattern, what the game shows instead]
export const RETIRED_TERMS = [
  [/\bDeep Processor\b/, 'the building is the Deep Ore Processor'],
  [/\bbrine\b/i, 'the good is concentrated waste'],
  [/valves? set to (Inlet|Outlet)/, 'Timber Pipes valves show Fill and Extract'],
  [/production building/i, 'a generated placeholder'],
];

const failures = [];
const fail = (message) => failures.push(message);
const rows = new Map();
const dir = resolve(dataRoot, 'Localizations');
for (const name of (await readdir(dir)).filter((n) => n.endsWith('.csv')).sort()) {
  const lines = (await readFile(resolve(dir, name), 'utf8')).split(/\r?\n/).slice(1).filter(Boolean);
  for (const line of lines) {
    const [id, text] = parseCsvRow(line);
    if (rows.has(id)) fail(`${id} is defined twice (${rows.get(id).file}, ${name})`);
    rows.set(id, {text, file: name});
  }
}

// Naming and wording on every row.
for (const [id, {text}] of rows) {
  if (/×/.test(text)) fail(`${id} uses the × sign; write "2 times" (or "2x" on a slider): ${text}`);
  for (const term of INTERNAL_TERMS) if (term.test(text)) fail(`${id} uses the internal term ${term}: ${text}`);
  for (const spelling of UK_SPELLINGS) if (spelling.test(text)) fail(`${id} uses UK spelling ${spelling} (the vanilla text is US English): ${text}`);
  for (const [term, why] of RETIRED_TERMS) if (term.test(text)) fail(`${id} says ${term} (${why}): ${text}`);
}
const titleCase = (name) => name.replace(/ \(\d+ high\)$/, '').split(' ').every((word, i) =>
  /^[A-Z0-9]/.test(word) || (i > 0 && SMALL_WORDS.has(word)));
for (const [id, {text}] of rows) {
  if (/^Building\.\w+\.DisplayName$/.test(id) && !titleCase(text)) fail(`${id} "${text}" is not in Title Case like the vanilla building names`);
  const good = /^Good\.(\w+)\.(DisplayName|PluralDisplayName)$/.exec(id);
  if (!good) continue;
  if (!/^[A-Z]/.test(text) || text.split(' ').slice(1).some((word) => /^[A-Z]/.test(word)))
    fail(`${id} "${text}" is not in sentence case like the vanilla good names`);
  const other = `Good.${good[1]}.${good[2] === 'DisplayName' ? 'PluralDisplayName' : 'DisplayName'}`;
  if (!rows.has(other)) fail(`${id} has no ${other} row`);
}
const family = (id) => id.replace(/(\d+x\d+)?(H\d+)?$/, '');
const flavorOwners = new Map();
for (const [id, {text}] of rows) {
  const match = /^Building\.(\w+)\.FlavorDescription$/.exec(id);
  if (!match) continue;
  if (!flavorOwners.has(text)) flavorOwners.set(text, new Set());
  flavorOwners.get(text).add(family(match[1]));
}
for (const [text, families] of flavorOwners)
  if (families.size > 1) fail(`flavor "${text}" is shared by different buildings (${[...families].join(', ')}); give each its own line`);
const recipeKeys = new Set();
const recipeDir = resolve(dataRoot, 'Recipes');
for (const name of (await readdir(recipeDir)).filter((n) => n.endsWith('.json'))) {
  const spec = JSON.parse((await readFile(resolve(recipeDir, name), 'utf8')).replace(/^﻿/, '')).RecipeSpec;
  if (spec?.DisplayLocKey) recipeKeys.add(spec.DisplayLocKey);
}
for (const [id] of rows) if (/^Recipe\./.test(id) && !recipeKeys.has(id)) fail(`${id} is no recipe's DisplayLocKey (a dead row)`);

const descriptions = [...rows].filter(([id]) => /^Building\.\w+\.Description$/.test(id));
if (!descriptions.length) fail(`no Building.*.Description rows under ${dir}`);
for (const [id, {text}] of descriptions) {
  if (!text.trim()) fail(`${id} is empty`);
  if (text.length > DESCRIPTION_MAX) fail(`${id}: ${text.length} characters, more than ${DESCRIPTION_MAX}: ${text}`);
  if (/production building/i.test(text)) fail(`${id} is a generated placeholder: ${text}`);
  if (/×/.test(text)) fail(`${id} uses the × notation; say "times": ${text}`);
}
const mean = descriptions.reduce((n, [, {text}]) => n + text.length, 0) / Math.max(descriptions.length, 1);
if (mean > DESCRIPTION_MEAN_MAX) fail(`Building descriptions average ${mean.toFixed(1)} characters, more than ${DESCRIPTION_MEAN_MAX}`);
for (const [id, {text}] of rows) {
  if (/^Building\.\w+\.FlavorDescription$/.test(id) && text.length > FLAVOR_MAX) fail(`${id}: ${text.length} characters, more than ${FLAVOR_MAX}`);
}
for (const id of TOOLTIP_SECTIONS) {
  const row = rows.get(id);
  if (!row) fail(`tooltip section ${id} has no localization row`);
  else if (row.text.length > SECTION_MAX) fail(`${id}: ${row.text.length} characters, more than ${SECTION_MAX}: ${row.text}`);
}

if (failures.length) {
  console.error(`Building description validation failed (${failures.length}):\n- ${failures.join('\n- ')}`);
  process.exit(1);
}
const longest = descriptions.reduce((a, b) => (b[1].text.length > a[1].text.length ? b : a));
console.log(`Building descriptions OK (${dataRoot}): ${descriptions.length} descriptions, mean ${mean.toFixed(1)} characters, longest ${longest[1].text.length} (${longest[0]}).`);
