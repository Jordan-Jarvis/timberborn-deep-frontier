// Static validator for Deep Frontier building sounds (tools/building_sounds.json).
//
//   node tools/validate_building_sounds.mjs [--root <repo>] [--game <Timberborn_Data>] [--report <json>]
//
// Checks, without writing Data:
// - schema and every sound name against the recorded 1.1.2.8 registry;
// - every template under Data/Buildings with a BuildingSpec or
//   BasicSelectionSoundSpec has an entry, and every entry's template exists;
// - the generated Data already carries exactly the listed sounds (and
//   PowerGeneratorSoundsSpec only on powerGenerator entries);
// - each non-empty loop has exactly its one declared native driver;
// - the hydro catalog agrees with the turbine entry.
// With --game it also re-reads the installed game's Resources container
// (globalgamemanagers) and requires the recorded registry to match the
// shipped UI.Buildings.Selected.*, Environment.Buildings.Loop.* and
// UI.BasicSelection.* clips exactly (case-insensitive, as Unity stores the
// container paths in lowercase).
import {readFile, writeFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {PREFIX, planBuildingSounds, presentDrivers} from './building_sounds_content.mjs';

const args = process.argv.slice(2);
const opt = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : null; };
const root = opt('--root') ? resolve(opt('--root')) : resolve(fileURLToPath(new URL('../', import.meta.url)));
const game = opt('--game');
const reportPath = opt('--report');
const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

const {config, errors, plan} = await planBuildingSounds(root);
const rows = [];
for (const item of plan) {
  if (!same(item.current, item.expected)) {
    const now = item.kind === 'buildings'
      ? {selection: item.current.BuildingSpec.SelectionSoundName, looping: item.current.BuildingSpec.LoopingSoundName,
        powerGeneratorSounds: 'PowerGeneratorSoundsSpec' in item.current}
      : {sound: item.current.BasicSelectionSoundSpec.SoundName, alternative: item.current.BasicSelectionSoundSpec.AlternativeSoundName};
    errors.push(`${item.kind}.${item.id}: generated Data ${JSON.stringify(now)} differs from ${'tools/building_sounds.json'}; run canonical generation`);
  }
  const entry = config[item.kind][item.id];
  rows.push(item.kind === 'buildings'
    ? {id: item.id, selection: entry.selection, looping: entry.looping, loopDriver: entry.loopDriver,
      family: entry.family, drivers: presentDrivers(item.expected)}
    : {id: item.id, basicSelection: entry.sound, alternative: entry.alternative});
}

if (game && !['selection', 'looping', 'basicSelection'].every((kind) => Array.isArray(config.registry?.[kind])))
  errors.push('--game: registry lists are malformed; fix tools/building_sounds.json first');
else if (game) {
  const text = (await readFile(resolve(game, 'globalgamemanagers'))).toString('latin1');
  const shipped = {selection: new Set(), looping: new Set(), basicSelection: new Set()};
  const folders = {selection: 'sounds/ui/buildings/selected/', looping: 'sounds/environment/buildings/loop/', basicSelection: 'sounds/ui/basicselection/'};
  for (const [kind, folder] of Object.entries(folders)) {
    const prefix = PREFIX[kind].toLowerCase();
    for (const match of text.matchAll(new RegExp(`${folder.replaceAll('/', '\\/').replaceAll('.', '\\.')}([a-z0-9_.]+)`, 'g'))) {
      if (!match[1].startsWith(prefix)) errors.push(`--game: ${match[0]} does not use the ${PREFIX[kind]} prefix`);
      else shipped[kind].add(match[1].slice(prefix.length));
    }
    const recorded = new Set(config.registry[kind].map((name) => name.toLowerCase()));
    const missing = [...shipped[kind]].filter((name) => !recorded.has(name));
    const absent = [...recorded].filter((name) => !shipped[kind].has(name));
    if (!shipped[kind].size) errors.push(`--game: no ${folder} clips found in ${game}`);
    if (missing.length) errors.push(`--game: shipped ${PREFIX[kind]}* clips not in registry.${kind}: ${missing.join(', ')}`);
    if (absent.length) errors.push(`--game: registry.${kind} names not shipped: ${absent.join(', ')}`);
  }
}

const report = {status: errors.length ? 'failed' : 'passed', game: config.game, gameChecked: Boolean(game),
  buildings: rows.filter((r) => 'selection' in r).length, basicSelection: rows.filter((r) => 'basicSelection' in r).length,
  planned: Object.keys(config.planned ?? {}), errors, rows};
if (reportPath) await writeFile(resolve(reportPath), `${JSON.stringify(report, null, 2)}\n`);
if (errors.length) {
  console.error(`Building sounds validation failed (${errors.length}):\n- ${errors.join('\n- ')}`);
  process.exit(1);
}
console.log(JSON.stringify({status: report.status, buildings: report.buildings, basicSelection: report.basicSelection,
  planned: report.planned.length, gameChecked: report.gameChecked}));
