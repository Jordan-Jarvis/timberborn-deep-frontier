// Ivory line-art icons for the concrete platform size/height variants, in the
// drawing language of the hand-authored ConcreteScaffold3x3.svg. The deck
// grid shows n×n cells; leg length and collar ticks show the leg height.
// create_structural_icons.mjs rasterizes the written SVGs.
import {readFile,writeFile} from 'node:fs/promises';
import {scaffoldLegs} from './structural_building_content.mjs';

const root=new URL('../',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('tools/structural_content.json',root),'utf8'));
const LAYER=33;            // px per leg layer; 3 layers = the original 98 px leg
const point=([x,y])=>`${Math.round(x)} ${Math.round(y)}`;
const lerp=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];

function icon(n,legs) {
  const L=legs*LAYER-1;
  // Centre the drawing vertically: the original 3-high art spans y 26..234.
  const dy=Math.round((3*LAYER-1-L)/2);
  const left=[23,71],back=[128,26],right=[233,71],front=[128,116];
  const grid=[];
  for(let i=1;i<n;i++) {
    const t=i/n;
    grid.push(`M${point(lerp(left,back,t))}L${point(lerp(front,right,t))}`);
    grid.push(`M${point(lerp(left,front,t))}L${point(lerp(back,right,t))}`);
  }
  const knee=Math.min(22,Math.round(.7*L));
  const legsPath=[
    `M23 94V${94+L}L40 ${103+L}V102`,
    `M233 94V${94+L}L216 ${103+L}V102`,
    `M119 135V${128+L}L137 ${136+L}V135`,
  ].join('');
  const braces=[
    `M31 ${94+knee}L62 111`,`M225 ${94+knee}L194 111`,
    `M119 ${135+knee}L88 122`,`M137 ${135+knee}L168 122`,
  ].join('');
  // One collar per intermediate layer joint, as on the model's columns,
  // spaced evenly over the leg below the knee braces.
  const collars=[];
  for(let k=1;k<legs;k++) {
    const side=Math.round(94+knee+(L-knee)*k/legs);
    const centre=Math.round(135+knee+(L-7-knee)*k/legs);
    collars.push(`M17 ${side-3}L46 ${side+12}`,`M239 ${side-3}L210 ${side+12}`,`M113 ${centre-3}L143 ${centre+10}`);
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
 <g transform="translate(0 ${dy})" fill="none" stroke="#f2e3bb" stroke-linecap="round" stroke-linejoin="round">
  <path stroke-width="10" d="M23 71L128 26L233 71V94L128 139L23 94ZM23 71L128 116L233 71M128 116V139${legsPath}"/>
  <path stroke-width="10" d="${braces}${collars.join('')}"/>
  <path stroke-width="${n>4?6:7}" d="${grid.join('')}"/>
 </g>
</svg>
`;
}

let count=0;
for(const building of catalog.buildings) {
  if(building.kind!=='scaffold'||building.id==='ConcreteScaffold3x3')continue;
  const legs=scaffoldLegs(building);
  await writeFile(new URL(`src/DeepFrontier/Art/Icons/${building.id}.svg`,root),icon(building.size[0],legs));
  count++;
}
console.log(`${count} concrete platform variant icon SVGs written.`);
