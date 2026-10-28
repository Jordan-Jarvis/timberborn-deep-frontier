// Civic and aquaculture UI icons from their authored SVGs, rendered in the vanilla
// icon style by tools/native_icon_style.mjs (see docs/art/icon-style.md).
import {readFile, mkdir} from 'node:fs/promises';
import {writeNativeIcon, writeReviewSheet} from './native_icon_style.mjs';
const root=new URL('../',import.meta.url);
const review=[];
for(const [name,kind,path] of [
  ['SweetBerryCake','good','Sprites/Goods/SweetBerryCakeIcon.png'],['Restaurant','building','Buildings/Food/Restaurant/Icon.png'],
  ['FreshFish','good','Sprites/Goods/FreshFishIcon.png'],['JuvenileFish','good','Sprites/Goods/JuvenileFishIcon.png'],['FishOil','good','Sprites/Goods/FishOilIcon.png'],
  ['FisheryWorks','building','Buildings/Food/FisheryWorks/Icon.png'],['FishHatchery','building','Buildings/Food/FishHatchery/Icon.png'],
  ['GroceryStore','building','Buildings/Food/GroceryStore/Icon.png'],['Hospital','building','Buildings/Wellbeing/Hospital/Icon.png'],
  ['CannedFish','good','Sprites/Goods/CannedFishIcon.png'],['PackagedFood','good','Sprites/Goods/PackagedFoodIcon.png'],
  ['Medicine','good','Sprites/Goods/MedicineIcon.png'],['MedicalFood','good','Sprites/Goods/MedicalFoodIcon.png']
]) {
  const svg=await readFile(new URL(`src/DeepFrontier/Art/Icons/${name}.svg`,root));
  const result=await writeNativeIcon(svg,kind,new URL(`src/DeepFrontier/Data/${path}`,root),name);
  review.push({label:`${name} ${result.stroke.toFixed(1)}px`,png:result.png});
}
const reviews=new URL('docs/art/reviews/2026-10-21-icons/',root);
await mkdir(reviews,{recursive:true});
await writeReviewSheet(review,[],new URL('civic-aquaculture.png',reviews),7);
console.log('Created native-style civic and aquaculture icons from authored SVGs.');
