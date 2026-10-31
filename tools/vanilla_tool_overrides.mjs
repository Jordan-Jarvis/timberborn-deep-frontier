// Vanilla build-menu tools that Deep Frontier shows or hides, as same-path
// partial blueprints that set only PlaceableBlockObjectSpec.DevModeTool.
// Native ToolButton (Timberborn.ToolButtonSystem 1.1.2.8) hides a DevModeTool
// tool outside dev mode and the map editor; the template stays loaded, so
// placed instances keep loading in saves.
//
// Shafts shown: Power Lines 11.1.1, an optional integration (manifest
// OptionalMods), overrides the vanilla Power Shaft, Vertical Power Shaft and
// Impermeable Power Shaft blueprints with "DevModeTool": true. OptionalMods
// sorts Power Lines before Deep Frontier, so this patch merges after it and sets
// the flag back. Without Power Lines it repeats the vanilla value.
//
// Tubeway station hidden (user decision, 2026-10-30): New Building Styles
// (Redic.NewStyles, a required mod) adds TubewayStop.IronTeeth, a second Iron
// Teeth tubeway station in the same Paths slot with the vanilla station's
// name. The vanilla TubewayStation.IronTeeth is hidden so the menu shows one
// station. tools/validate_mod_dependencies.mjs checks that New Styles'
// station is still installed, collected and not itself a dev tool, so both
// are never hidden. A plain partial blueprint is the native form here: the
// vanilla base always exists, so *.optional (merged only when a base exists)
// would change nothing.
import {mkdir, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const SHAFTS = ['PowerShaft', 'VerticalPowerShaft', 'ImpermeablePowerShaft'];
const FACTIONS = ['IronTeeth', 'Folktails'];
const HIDDEN_VANILLA_TOOLS = ['Buildings/Paths/TubewayStation/TubewayStation.IronTeeth.blueprint.json'];

const write = async (relative, devModeTool) => {
  const path = resolve(root, 'src', 'DeepFrontier', 'Data', relative);
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify({PlaceableBlockObjectSpec: {DevModeTool: devModeTool}}, null, 2)}\n`, 'utf8');
};

for (const name of SHAFTS) {
  for (const faction of FACTIONS) await write(`Buildings/Power/${name}/${name}.${faction}.blueprint.json`, false);
}
for (const path of HIDDEN_VANILLA_TOOLS) await write(path, true);
console.log(`Vanilla tool overrides: ${SHAFTS.length * FACTIONS.length} shaft tools shown, ${HIDDEN_VANILLA_TOOLS.length} hidden.`);
