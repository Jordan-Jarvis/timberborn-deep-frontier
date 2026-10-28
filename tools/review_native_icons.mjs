// Contact sheets and a conformance audit for every UI icon the mod ships.
// Usage: node tools/review_native_icons.mjs <output-folder>
// Reads src/DeepFrontier/Data (goods, building tools, map objects), checks each
// against the vanilla canvas/metadata contract in tools/native_icon_style.mjs, and
// writes goods.png / buildings.png sheets (1x and 2x beside vanilla references
// from outputs/vanilla-icons). Exits non-zero when an icon breaks the contract.
import {readdir, readFile, mkdir} from 'node:fs/promises';
import {join, relative, resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import sharp from 'sharp';
import {ICON_KINDS, writeReviewSheet} from './native_icon_style.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const data = join(root, 'src/DeepFrontier/Data');
const out = process.argv[2] ? resolve(process.argv[2]) : null;
if (!out) throw new Error('Usage: node tools/review_native_icons.mjs <output-folder>');

async function* walk(folder) {
  for (const entry of await readdir(folder, {withFileTypes: true})) {
    const path = join(folder, entry.name);
    if (entry.isDirectory()) yield* walk(path);
    else if (/Icon\.png$/.test(entry.name)) yield path;
  }
}
const kindOf = rel => rel.startsWith('Sprites/Goods/') ? 'good' : rel.startsWith('MapEditor/') ? 'mapObject' : 'building';
const label = rel => rel.startsWith('Sprites/Goods/') ? rel.slice(14).replace(/Icon\.png$/, '') : rel.split('/').at(-2);

const icons = {good: [], building: []}, problems = [];
for await (const path of walk(data)) {
  const rel = relative(data, path).replace(/\\/g, '/');
  if (!/^(Sprites\/Goods|Buildings|MapEditor)\//.test(rel)) continue;
  const kind = kindOf(rel), style = ICON_KINDS[kind];
  const png = await readFile(path);
  const {width, height, channels} = await sharp(png).metadata();
  const meta = JSON.parse(await readFile(`${path}.meta.json`, 'utf8'));
  const before = problems.length;
  if (width !== style.canvas || height !== style.canvas) problems.push(`${rel}: ${width}x${height}, vanilla ${kind} canvas is ${style.canvas}`);
  if (channels !== 4) problems.push(`${rel}: no alpha channel`);
  if (JSON.stringify(meta) !== JSON.stringify(style.meta)) problems.push(`${rel}: meta ${JSON.stringify(meta)} != ${JSON.stringify(style.meta)}`);
  const flag = problems.length > before ? `off-contract ${width}px` : undefined;
  icons[kind === 'good' ? 'good' : 'building'].push({label: label(rel), png, flag});
}
for (const list of Object.values(icons)) list.sort((a, b) => a.label.localeCompare(b.label));

await mkdir(out, {recursive: true});
const vanilla = names => names.map(n => ({label: n, path: join(root, `outputs/vanilla-icons/${n}Icon.png`)}));
await writeReviewSheet(icons.good, vanilla(['Gear', 'Biofuel', 'Extract', 'Plank', 'Catalyst', 'Paper', 'Badwater', 'MetalBlock']), join(out, 'goods.png'), 8);
await writeReviewSheet(icons.building, vanilla(['Smelter', 'Refinery', 'Centrifuge', 'FoodFactory', 'EfficientMine', 'Observatory', 'GeothermalField', 'LargeWarehouse']), join(out, 'buildings.png'), 8);
console.log(`Reviewed ${icons.good.length} goods and ${icons.building.length} tool/map icons -> ${out}`);
if (problems.length) {
  console.error(problems.join('\n'));
  process.exit(1);
}
