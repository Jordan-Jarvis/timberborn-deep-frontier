// Render only the map-object icons of create_frontier_expansion_icons.mjs into a
// chosen Data root (default src/DeepFrontier/Data), without rewriting the
// expansion review sheets in docs/art. For scratch mirrors and quick checks:
//   node tools/render_map_object_icons.mjs [--data <Data root>] [--sheet <png>]
import {readFile} from 'node:fs/promises';
import {resolve} from 'node:path';
import {fileURLToPath} from 'node:url';
import {writeNativeIcon, writeReviewSheet} from './native_icon_style.mjs';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const args = process.argv.slice(2);
const option = (name) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : undefined; };
const data = resolve(option('--data') ?? resolve(root, 'src', 'DeepFrontier', 'Data'));
const ICONS = {
  DeepOreSource: 'MapEditor/Objects/DeepOreSource/DeepOreSourceIcon.png',
  DeepOreVein: 'MapEditor/Objects/DeepOreVein/DeepOreVeinIcon.png',
  HumanRecordCache: 'MapEditor/Objects/HumanRecordCache/HumanRecordCacheIcon.png',
};
const review = [];
for (const [id, path] of Object.entries(ICONS)) {
  const svg = await readFile(resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', `${id}.svg`));
  const result = await writeNativeIcon(svg, 'mapObject', resolve(data, path), id);
  review.push({label: `${id} ${result.stroke.toFixed(1)}px`, png: result.png, kind: 'mapObject'});
}
const sheet = option('--sheet');
if (sheet) await writeReviewSheet(review, [], resolve(sheet), 4);
console.log(`Rendered ${review.length} map-object icons into ${data}`);
