// Goods icons for the radiation system: RadioactiveSludge and ContaminatedWater.
// Authored single-ink SVGs in src/DeepFrontier/Art/Icons/<Id>.svg rendered with
// the shared vanilla icon renderer (tools/native_icon_style.mjs). Deliberate,
// user-directed deviation from the vanilla ivory goods ink: these two hazard
// goods use a radioactive yellow-green ink so they read as the toxic fluid in
// menus, matching the sludge surface, stockpile barrels and pipe colour.
//
// Usage: node tools/create_radiation_icons.mjs [dataRoot]
//   dataRoot defaults to src/DeepFrontier/Data (use a scratch copy for tests).
import {readFile, mkdir, writeFile} from 'node:fs/promises';
import {resolve, dirname} from 'node:path';
import {fileURLToPath} from 'node:url';
import {ICON_KINDS, renderNativeIcon, writeReviewSheet} from './native_icon_style.mjs';

export const RADIATION_ICON_INK = [212, 222, 54];
export const RADIATION_ICON_GOODS = ['RadioactiveSludge', 'ContaminatedWater'];
// Tool icons (112 px native building style, same radioactive ink).
export const RADIATION_TOOL_ICONS = [
  ['RadioactiveSpring', 'Buildings/Water/RadioactiveSpring/RadioactiveSpringIcon.png'],
  ['RadioactiveSpring', 'MapEditor/Objects/RadioactiveSpringSource/RadioactiveSpringSourceIcon.png'],
];
// Building tool icons of the three radiation buildings: native building ink
// (only the hazard goods and the spring use the radioactive ink), traced from
// their late-game studies (outputs/lategame-studies/<Id>-front*.png).
export const RADIATION_BUILDING_ICONS = ['RadioactiveWasteExport', 'RadioactiveSludgeOutfall', 'RadioactiveSludgeRecoveryPump']
  .map((id) => [id, `Buildings/Water/${id}/${id}Icon.png`]);

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));

export async function createRadiationIcons(dataRoot = resolve(root, 'src', 'DeepFrontier', 'Data')) {
  const review = [];
  for (const id of RADIATION_ICON_GOODS) {
    const svg = await readFile(resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', `${id}.svg`));
    const result = await renderNativeIcon(svg, 'good', id, {ink: RADIATION_ICON_INK});
    const output = resolve(dataRoot, 'Sprites', 'Goods', `${id}Icon.png`);
    await mkdir(dirname(output), {recursive: true});
    await writeFile(output, result.png);
    await writeFile(`${output}.meta.json`, JSON.stringify(ICON_KINDS.good.meta) + '\n');
    review.push({label: `${id} ${result.stroke.toFixed(1)}px`, png: result.png});
  }
  for (const [id, path] of RADIATION_TOOL_ICONS) {
    const svg = await readFile(resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', `${id}.svg`));
    const result = await renderNativeIcon(svg, 'building', id, {ink: RADIATION_ICON_INK});
    const output = resolve(dataRoot, path);
    await mkdir(dirname(output), {recursive: true});
    await writeFile(output, result.png);
    await writeFile(`${output}.meta.json`, JSON.stringify(ICON_KINDS.building.meta) + '\n');
    if (path.startsWith('Buildings/')) review.push({label: `${id} tool ${result.stroke.toFixed(1)}px`, png: result.png});
  }
  for (const [id, path] of RADIATION_BUILDING_ICONS) {
    const svg = await readFile(resolve(root, 'src', 'DeepFrontier', 'Art', 'Icons', `${id}.svg`));
    const result = await renderNativeIcon(svg, 'building', id);
    const output = resolve(dataRoot, path);
    await mkdir(dirname(output), {recursive: true});
    await writeFile(output, result.png);
    await writeFile(`${output}.meta.json`, JSON.stringify(ICON_KINDS.building.meta) + '\n');
    review.push({label: `${id} ${result.stroke.toFixed(1)}px`, png: result.png});
  }
  const sheet = resolve(root, 'outputs', 'radiation-icons', 'radiation-goods.png');
  await mkdir(dirname(sheet), {recursive: true});
  const vanilla = ['Water', 'Badwater', 'DevWaterSource'].map(n => ({label: n, path: resolve(root, 'outputs', 'vanilla-icons', `${n}Icon.png`)}));
  await writeReviewSheet(review, vanilla, sheet, 4);
  return {icons: RADIATION_ICON_GOODS.length + RADIATION_TOOL_ICONS.length + RADIATION_BUILDING_ICONS.length, sheet};
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const result = await createRadiationIcons(process.argv[2] ? resolve(process.argv[2]) : undefined);
  console.log(`Rendered ${result.icons} radiation goods icons; review sheet ${result.sheet}`);
}
