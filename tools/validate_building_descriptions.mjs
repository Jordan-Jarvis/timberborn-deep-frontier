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
