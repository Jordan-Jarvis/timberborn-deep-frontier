// Restore vanilla shafts as normal build tools.
//
// Power Lines 11.1.1 (a required dependency) overrides the vanilla Power
// Shaft, Vertical Power Shaft and Impermeable Power Shaft blueprints with
// "PlaceableBlockObjectSpec": {"DevModeTool": true}, which hides them outside
// dev mode and tags them as dev tools. Deep Frontier depends on Power Lines,
// so it loads afterwards; this same-path partial blueprint sets the flag back.
// Only that one field is written; everything else stays vanilla/Power Lines.
import {mkdir, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const SHAFTS = ['PowerShaft', 'VerticalPowerShaft', 'ImpermeablePowerShaft'];
const FACTIONS = ['IronTeeth', 'Folktails'];

for (const name of SHAFTS) {
  for (const faction of FACTIONS) {
    const path = resolve(root, 'src', 'DeepFrontier', 'Data', 'Buildings', 'Power', name, `${name}.${faction}.blueprint.json`);
    await mkdir(dirname(path), {recursive: true});
    await writeFile(path, `${JSON.stringify({PlaceableBlockObjectSpec: {DevModeTool: false}}, null, 2)}\n`, 'utf8');
  }
}
console.log(`Vanilla shaft tools restored: ${SHAFTS.length * FACTIONS.length} partial blueprints.`);
