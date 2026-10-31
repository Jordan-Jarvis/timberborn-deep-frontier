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
//
// Science raised (user decision, 2026-10-30, bricks pass): the Stone Crusher
// grinds sandstone into vanilla Dirt from 600 science, so the vanilla Iron
// Teeth Terrain Block (4 Dirt, 1,000 science) would arrive on cheap crusher
// dirt with the first bricks. It unlocks with the vanilla Dirt Excavator at
// 2,000 instead, after bricks (600) and concrete (1,000). The partial
// blueprint sets only BuildingSpec.ScienceCost (native blueprint merge); the
// Mud Bath (1,800) is unchanged. tools/progression_data.mjs reads the patched
// value.
import {mkdir, readFile, writeFile} from 'node:fs/promises';
import {dirname, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');
const SHAFTS = ['PowerShaft', 'VerticalPowerShaft', 'ImpermeablePowerShaft'];
const FACTIONS = ['IronTeeth', 'Folktails'];
const HIDDEN_VANILLA_TOOLS = ['Buildings/Paths/TubewayStation/TubewayStation.IronTeeth.blueprint.json'];
const RAISED_SCIENCE = {'Buildings/Landscaping/TerrainBlock/TerrainBlock.IronTeeth.blueprint.json': 2000};

const writePatch = async (relative, patch) => {
  const path = resolve(root, 'src', 'DeepFrontier', 'Data', relative);
  await mkdir(dirname(path), {recursive: true});
  await writeFile(path, `${JSON.stringify(patch, null, 2)}\n`, 'utf8');
};
const write = (relative, devModeTool) => writePatch(relative, {PlaceableBlockObjectSpec: {DevModeTool: devModeTool}});

for (const name of SHAFTS) {
  for (const faction of FACTIONS) await write(`Buildings/Power/${name}/${name}.${faction}.blueprint.json`, false);
}
for (const path of HIDDEN_VANILLA_TOOLS) await write(path, true);
for (const [path, science] of Object.entries(RAISED_SCIENCE)) {
  const vanilla = JSON.parse((await readFile(resolve(vanillaRoot, path), 'utf8')).replace(/^﻿/, ''));
  const current = vanilla.BuildingSpec?.ScienceCost;
  if (!Number.isInteger(current)) throw new Error(`${path}: the vanilla blueprint has no BuildingSpec.ScienceCost`);
  if (!(Number.isInteger(science) && science > current)) throw new Error(`${path}: ${science} does not raise the vanilla ${current}`);
  await writePatch(path, {BuildingSpec: {ScienceCost: science}});
}
console.log(`Vanilla tool overrides: ${SHAFTS.length * FACTIONS.length} shaft tools shown, ${HIDDEN_VANILLA_TOOLS.length} hidden, ${Object.keys(RAISED_SCIENCE).length} science raised.`);
