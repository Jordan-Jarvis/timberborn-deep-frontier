// More Fluids UI icons in the vanilla Timberborn 1.1 style (docs/art/icon-style.md),
// rendered by tools/native_icon_style.mjs from the single-ink SVGs in
// src/MoreFluids/Art/Icons/<Id>.svg to the resource paths of
// docs/more-fluids-design.md ("Art"), with their {"isSprite":true} sidecars.
// Also writes a 1x/2x review sheet beside vanilla references to
// outputs/more-fluids-art/icons-review.png.
//
// Run: node tools/asset-pipeline/more_fluids_icons.mjs [Id ...]
import {access, readFile} from 'node:fs/promises';
import {renderNativeIcon, writeNativeIcon, writeReviewSheet} from '../native_icon_style.mjs';

const root = new URL('../../', import.meta.url);
export const ICONS = {
  MoreFluidsFluidExtractor: ['building', 'Buildings/Water/MoreFluidsFluidExtractor/MoreFluidsFluidExtractorIcon.png'],
  MoreFluidsDesalinator: ['building', 'Buildings/Water/MoreFluidsDesalinator/MoreFluidsDesalinatorIcon.png'],
  MoreFluidsHealingWell: ['building', 'Buildings/Water/MoreFluidsHealingWell/MoreFluidsHealingWellIcon.png'],
  MoreFluidsHealingSpring: ['mapObject', 'MapEditor/Objects/MoreFluidsHealingSpring/MoreFluidsHealingSpringIcon.png'],
  MoreFluidsGeyser: ['mapObject', 'MapEditor/Objects/MoreFluidsGeyser/MoreFluidsGeyserIcon.png'],
};
const REFERENCES = ['DeepWaterPumpIcon', 'LargeWaterPumpIcon', 'CentrifugeIcon', 'WaterSourceIcon'];

const wanted = process.argv.slice(2);
for (const id of wanted) if (!ICONS[id]) throw new Error(`Unknown icon ${id}`);
const entries = [];
for (const [id, [kind, path]] of Object.entries(ICONS)) {
  const source = new URL(`src/MoreFluids/Art/Icons/${id}.svg`, root);
  try { await access(source); } catch { if (wanted.includes(id)) throw new Error(`${id}: no ${source.pathname}`); continue; }
  const svg = await readFile(source);
  if (!wanted.length || wanted.includes(id)) {
    const result = await writeNativeIcon(svg, kind, new URL(`src/MoreFluids/Data/${path}`, root), id);
    console.log(`${id}: ${result.canvas}px, ${(result.extent * 100).toFixed(0)}% extent, ${result.stroke.toFixed(1)} px lines`);
  }
  entries.push({label: id.replace('MoreFluids', ''), png: (await renderNativeIcon(svg, kind, id)).png});
}
const references = [];
for (const name of REFERENCES) {
  const path = new URL(`outputs/vanilla-icons/${name}.png`, root);
  await access(path);  // local vanilla cache: tools/asset-pipeline/export_vanilla_icon_references.py
  references.push({label: name.replace('Icon', ''), path: path.pathname.replace(/^\/([A-Za-z]:)/, '$1')});
}
await writeReviewSheet(entries, references, new URL('outputs/more-fluids-art/icons-review.png', root).pathname.replace(/^\/([A-Za-z]:)/, '$1'), 4);
console.log('review sheet: outputs/more-fluids-art/icons-review.png');
