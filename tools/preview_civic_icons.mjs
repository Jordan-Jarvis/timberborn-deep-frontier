import {readFile,mkdir} from 'node:fs/promises';
import sharp from 'sharp';
import {fileURLToPath} from 'node:url';
const root=new URL('../',import.meta.url);
const names=['GroceryStore','Hospital','CannedFish','PackagedFood','Medicine','MedicalFood'];
const layers=[];
for(let i=0;i<names.length;i++) {
  const svg=await readFile(new URL(`src/DeepFrontier/Art/Icons/${names[i]}.svg`,root));
  const x=(i%3)*240,y=Math.floor(i/3)*240;
  layers.push({input:await sharp(svg).resize(128,128).png().toBuffer(),left:x+56,top:y+15});
  layers.push({input:await sharp(svg).resize(32,32).png().toBuffer(),left:x+104,top:y+156});
  const label=Buffer.from(`<svg width="240" height="36"><text x="120" y="24" text-anchor="middle" fill="#f2e3bb" font-family="Arial" font-size="18">${names[i]}</text></svg>`);
  layers.push({input:label,left:x,top:y+196});
}
const directory=new URL('docs/art/reviews/2026-10-20-grocery-runtime/',root);
await mkdir(directory,{recursive:true});
const output=new URL('civic-ivory-icons.png',directory);
await sharp({create:{width:720,height:480,channels:4,background:'#18332d'}})
  .composite(layers).png().toFile(fileURLToPath(output));
console.log(fileURLToPath(output));
