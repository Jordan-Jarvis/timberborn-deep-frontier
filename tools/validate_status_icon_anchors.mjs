// Every Deep Frontier building template carries StatusIconAnchorSpec with the height
// tools/status_icon_content.mjs derives from its blocks (Scripts/StatusIconAnchor.cs caps the
// native status icon there). Every building whose main body lies below its tallest part, chimneys
// and masts included, is therefore covered; no other blueprint in Data carries the spec.
// Every Deep Frontier power consumer, and only those, carries PowerConnectionStatusSpec
// (Scripts/PowerConnectionStatus.cs), and its localization rows exist exactly once.
import {readFile, readdir} from 'node:fs/promises';
import {join, resolve, dirname, relative} from 'node:path';
import {fileURLToPath} from 'node:url';
import {anchorHeight, deepFrontierBuildings, NATIVE_OFFSET, POWER_LOC, LOCALIZATION_FILE, isConsumer} from './status_icon_content.mjs';

const repo = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const dataRoot = process.argv[2] ? resolve(process.argv[2]) : join(repo, 'src/DeepFrontier/Data');
const failures = [];
const buildings = await deepFrontierBuildings(dataRoot);
const covered = new Set();
let lowered = 0, aboveMain = 0, consumers = 0;
for (const {id, file, value} of buildings) {
  covered.add(resolve(file));
  const expected = anchorHeight(value.BlockObjectSpec, id);
  const spec = value.StatusIconAnchorSpec;
  if (!spec) { failures.push(`${id}: no StatusIconAnchorSpec`); continue; }
  if (Object.keys(spec).join() !== 'Height') failures.push(`${id}: StatusIconAnchorSpec must hold only Height, has ${Object.keys(spec).join(',')}`);
  if (spec.Height !== expected.height) failures.push(`${id}: StatusIconAnchorSpec.Height ${spec.Height} differs from the derived ${expected.height} (main roof ${expected.mainRoof}, centre ${expected.centreTop})`);
  if (!(spec.Height > 0) || spec.Height > expected.occupiedTop + NATIVE_OFFSET) failures.push(`${id}: Height ${spec.Height} outside (0, occupied top ${expected.occupiedTop} + ${NATIVE_OFFSET}]`);
  if (spec.Height < expected.occupiedTop + NATIVE_OFFSET) lowered++;
  if (expected.occupiedTop - expected.mainRoof > 3) aboveMain++;
  if (isConsumer(value)) consumers++;
  if (isConsumer(value) !== Boolean(value.PowerConnectionStatusSpec))
    failures.push(`${id}: PowerConnectionStatusSpec ${value.PowerConnectionStatusSpec ? 'on a building without power input' : 'missing on a power consumer'}`);
  if (value.PowerConnectionStatusSpec && Object.keys(value.PowerConnectionStatusSpec).length) failures.push(`${id}: PowerConnectionStatusSpec takes no fields`);
}
const csvLines = (await readFile(join(dataRoot, LOCALIZATION_FILE), 'utf8')).split(/\r?\n/);
const source = await readFile(join(repo, 'src/DeepFrontier/Scripts/PowerConnectionStatus.cs'), 'utf8');
for (const id of Object.keys(POWER_LOC)) {
  if (csvLines.filter((line) => line.startsWith(id + ',')).length !== 1) failures.push(`${LOCALIZATION_FILE}: ${id} must be defined exactly once`);
  if (!source.includes(`"${id}"`)) failures.push(`PowerConnectionStatus.cs does not use ${id}`);
}
async function walk(dir) {
  const out = [];
  for (const e of await readdir(dir, {withFileTypes: true})) {
    const p = join(dir, e.name);
    if (e.isDirectory()) out.push(...await walk(p)); else if (e.name.endsWith('.blueprint.json')) out.push(p);
  }
  return out;
}
for (const file of await walk(dataRoot)) {
  if (covered.has(resolve(file))) continue;
  const text = await readFile(file, 'utf8');
  if (text.includes('"PowerConnectionStatusSpec"')) failures.push(`${relative(dataRoot, file)}: PowerConnectionStatusSpec outside the Deep Frontier building templates`);
  if (text.includes('"StatusIconAnchorSpec"')) failures.push(`${relative(dataRoot, file)}: StatusIconAnchorSpec outside the Deep Frontier building templates`);
}
if (failures.length) throw new Error('Status icon anchor check failed:\n' + failures.join('\n'));
console.log(JSON.stringify({status: 'status-icon-anchors-checked', buildings: buildings.length, loweredBelowOccupiedTop: lowered,
  tallPartsAboveMainBody: aboveMain, powerConnectionStatus: consumers}));
