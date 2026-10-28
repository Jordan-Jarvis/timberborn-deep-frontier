// Structural building icon candidates from authored SVGs, rendered in the vanilla
// icon style by tools/native_icon_style.mjs. promote_style_exports.ps1 copies
// them (with their .meta.json) into the mod; active game data is unchanged here.
import {readFile,mkdir} from 'node:fs/promises';
import {writeNativeIcon,writeReviewSheet} from './native_icon_style.mjs';

const root=new URL('../',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('tools/structural_content.json',root),'utf8'));
const review=[];
for(const building of catalog.buildings) {
  const svg=await readFile(new URL(`src/DeepFrontier/Art/Icons/${building.id}.svg`,root));
  const output=new URL(`outputs/structural-integration/Data/Buildings/Platforms/${building.id}/Icon.png`,root);
  const result=await writeNativeIcon(svg,'building',output,building.id);
  review.push({label:`${building.name} ${result.stroke.toFixed(1)}px`,png:result.png});
}
const reviews=new URL('docs/art/reviews/2026-10-21-icons/',root);
await mkdir(reviews,{recursive:true});
await writeReviewSheet(review,[],new URL('structural-candidates.png',reviews),5);
console.log(`${catalog.buildings.length} native-style structural icon candidates exported; active game data unchanged.`);
