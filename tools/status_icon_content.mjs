// Status icon anchors (user decision 2026-10-23): the native status icon floats 0.7 above a
// building's highest mesh (BuildingStatusIconOffsetter, Timberborn 1.1.2.8), so a Deep Frontier
// chimney, mast or gantry lifts it 3-14 layers above the main body. Every Deep Frontier building
// template (TemplateCollection.Buildings.IronTeeth with a BuildingSpec) gets
//   StatusIconAnchorSpec { Height }
// and Scripts/StatusIconAnchor.cs caps the native icon height at it (never raises it).
//
// Height, in layers above the building's layer 0 (BlockObject.Coordinates.z):
//   max(main roof, top of the occupied cells under the icon) + NATIVE_OFFSET
//   main roof: the top of the highest layer holding at least MAIN_SHARE of the widest
//     layer's occupied cells (the main body, not a chimney or mast);
//   under the icon: cells whose centre lies within CENTRE_REACH of the footprint centre, where
//     the native icon stands (BlockObjectCenter.GridCenter), so it never sinks into a central tower.
// Runs once at the end of generation (create_vertical_slice_content.mjs), after every building's
// blocks are final, or standalone on a generated Data root:
//   node tools/status_icon_content.mjs [dataRoot]
// Checked by tools/validate_status_icon_anchors.mjs.
//
// The same step marks every Deep Frontier power consumer (MechanicalNodeSpec.PowerInput > 0) with
//   PowerConnectionStatusSpec {}
// (Scripts/PowerConnectionStatus.cs: "Not connected to a power source" while its graph has no
// generator or battery) and appends that status's localization rows to Localizations/enUS.csv.
import {readFile, writeFile} from 'node:fs/promises';
import {join, resolve, dirname, basename} from 'node:path';
import {fileURLToPath} from 'node:url';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
export const NATIVE_OFFSET = 0.7;   // BuildingStatusIconOffsetter.FinishedOffset (1.1.2.8)
export const MAIN_SHARE = 0.3;
export const CENTRE_REACH = 1;
// PowerConnectionLoc (Scripts/PowerConnectionStatus.cs).
export const POWER_LOC = {
  'DeepFrontier.Power.Status.NotConnected': 'Not connected to a power source. Connect it to a generator with shafts or power lines.',
  'DeepFrontier.Power.Status.NotConnected.Short': 'Not connected to power',
};
export const LOCALIZATION_FILE = 'Localizations/enUS.csv';
export const isConsumer = (value) => (value.MechanicalNodeSpec?.PowerInput ?? 0) > 0;

function csvCell(value) {
  return /[",\n\r]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

function fail(message) { throw new Error(`status_icon_content: ${message}`); }

export function anchorHeight(blockObject, id) {
  const {Size: size, Blocks: blocks} = blockObject ?? {};
  if (!size || !Array.isArray(blocks) || blocks.length !== size.X * size.Y * size.Z) fail(`${id}: BlockObjectSpec Size/Blocks mismatch`);
  const perLayer = new Map();
  let centreTop = 0;
  const cx = size.X / 2, cy = size.Y / 2;
  blocks.forEach((block, i) => {
    if (block.Occupations === 'None') return;
    const z = Math.floor(i / (size.X * size.Y)), r = i % (size.X * size.Y), y = Math.floor(r / size.X), x = r % size.X;
    perLayer.set(z, (perLayer.get(z) ?? 0) + 1);
    if (Math.abs(x + 0.5 - cx) <= CENTRE_REACH && Math.abs(y + 0.5 - cy) <= CENTRE_REACH) centreTop = Math.max(centreTop, z + 1);
  });
  if (!perLayer.size) fail(`${id}: no occupied block`);
  const widest = Math.max(...perLayer.values());
  const mainRoof = Math.max(...[...perLayer].filter(([, n]) => n >= MAIN_SHARE * widest).map(([z]) => z)) + 1;
  return {height: Math.round((Math.max(mainRoof, centreTop) + NATIVE_OFFSET) * 100) / 100, mainRoof, centreTop,
    occupiedTop: Math.max(...perLayer.keys()) + 1};
}

export async function deepFrontierBuildings(dataRoot) {
  const collection = JSON.parse(await readFile(join(dataRoot, 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'), 'utf8'));
  const paths = collection.TemplateCollectionSpec?.['Blueprints#append'];
  if (!Array.isArray(paths) || !paths.length) fail('TemplateCollection.Buildings.IronTeeth lists no blueprints');
  const result = [];
  for (const path of paths) {
    const file = join(dataRoot, `${path}.json`);
    const value = JSON.parse(await readFile(file, 'utf8'));
    if (!value.BuildingSpec) continue;   // map-authored objects (the radioactive spring) have no building icon
    result.push({id: basename(path).replace('.blueprint', ''), file, value});
  }
  return result;
}

export async function applyStatusIconAnchors({dataRoot = join(repo, 'src/DeepFrontier/Data')} = {}) {
  const rows = [];
  for (const {id, file, value} of await deepFrontierBuildings(dataRoot)) {
    if (value.StatusIconAnchorSpec || value.PowerConnectionStatusSpec) fail(`${id}: status specs already present; run once on freshly generated blueprints`);
    const anchor = anchorHeight(value.BlockObjectSpec, id);
    value.StatusIconAnchorSpec = {Height: anchor.height};
    if (isConsumer(value)) value.PowerConnectionStatusSpec = {};
    await writeFile(file, JSON.stringify(value, null, 2) + '\n');
    rows.push({id, consumer: isConsumer(value), ...anchor});
  }
  const path = join(dataRoot, LOCALIZATION_FILE);
  const text = await readFile(path, 'utf8');
  if (!text.endsWith('\n')) fail(`${path} must end with a newline`);
  const ids = new Set(text.split(/\r?\n/).map((line) => line.split(',')[0]));
  for (const id of Object.keys(POWER_LOC)) if (ids.has(id)) fail(`${path} already defines ${id}`);
  const lines = Object.entries(POWER_LOC).map(([id, value]) => [id, value, 'Deep Frontier'].map(csvCell).join(','));
  await writeFile(path, text + lines.join('\n') + '\n', 'utf8');
  const lowered = rows.filter((r) => r.height < r.occupiedTop + NATIVE_OFFSET).length;
  console.log(`Status icon anchors: ${rows.length} buildings, ${lowered} below their occupied top; ` +
    `power connection status on ${rows.filter((r) => r.consumer).length} consumers.`);
  return rows;
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const rows = await applyStatusIconAnchors(process.argv[2] ? {dataRoot: resolve(process.argv[2])} : {});
  for (const r of rows) console.log(JSON.stringify(r));
}
