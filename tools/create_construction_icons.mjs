// Construction-material UI icons from authored SVGs, rendered in the vanilla icon
// style by tools/native_icon_style.mjs (see docs/art/icon-style.md). Map sources
// have their own outcrop/seam drawings, in the mineral's motif.
import {readFile,mkdir} from 'node:fs/promises';
import {writeNativeIcon,writeReviewSheet} from './native_icon_style.mjs';
const root=new URL('../',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('tools/construction_materials.json',root),'utf8'));
const entries=[
  ...catalog.buildings.map(b=>[b.id,'building',`Buildings/Metal/${b.id}/Icon.png`]),
  ...catalog.goods.map(g=>[g.id,'good',`Sprites/Goods/${g.id}Icon.png`]),
  ...catalog.sources.map(s=>[s.id,'mapObject',`MapEditor/Objects/${s.id}/${s.id}Icon.png`]),
];
const review=[];
for(const [id,kind,path] of entries) {
  const svg=await readFile(new URL(`src/DeepFrontier/Art/Icons/${id}.svg`,root));
  const result=await writeNativeIcon(svg,kind,new URL(`src/DeepFrontier/Data/${path}`,root),id);
  review.push({label:`${id} ${result.stroke.toFixed(1)}px`,png:result.png});
}
const reviews=new URL('docs/art/reviews/2026-10-21-icons/',root);
await mkdir(reviews,{recursive:true});
await writeReviewSheet(review,[],new URL('construction.png',reviews),8);
console.log(`Exported ${entries.length} native-style construction icons.`);
