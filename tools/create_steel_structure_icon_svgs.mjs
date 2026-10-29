// Ivory line-art icons for the steel structures, in the drawing language of
// the hand-authored ConcreteOverhang8x1.svg and the concrete platform icons:
// one isometric view, a single pale stroke colour, no fills.
//   cantilever: a long deck strip with a tapering Warren truss under it and
//               one concrete pier per anchor tile;
//   bridge:     a deck strip between two truss rails on an abutment block;
//   column:     a riveted trestle, one collar per layer, height by layers;
//   deck:       an n×n plate grid on four paired-post corner trestles.
// Tile counts are drawn (strip cells, layers, deck grid) so the sizes read
// apart. create_structural_icons.mjs rasterizes the written SVGs.
import {readFile,writeFile} from 'node:fs/promises';
import {overhangContract,bridgeSpan,columnHeight,deckSpan} from './structural_building_content.mjs';

const root=new URL('../',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('tools/structural_content.json',root),'utf8'));
const r=v=>Math.round(v*10)/10;
const P=([x,y])=>`${r(x)} ${r(y)}`;
const add=(a,b,k=1)=>[a[0]+b[0]*k,a[1]+b[1]*k];
const svg=(paths,dy=0)=>`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
 <g${dy?` transform="translate(0 ${dy})"`:''} fill="none" stroke="#f2e3bb" stroke-linecap="round" stroke-linejoin="round">
${paths.map(([width,d])=>`  <path stroke-width="${width}" d="${d}"/>`).join('\n')}
 </g>
</svg>
`;
// Isometric axes of the long pieces: along the strip (up and right) and across it.
const ALONG=[.919,-.394],ACROSS=[.82,.35],DOWN=[0,1];

function strip(cells,start,length,width,thickness) {
  const u=[ALONG[0]*length/cells,ALONG[1]*length/cells],v=[ACROSS[0]*width,ACROSS[1]*width];
  const a=start,b=add(a,u,cells),c=add(b,v),d=add(a,v);
  const outline=`M${P(a)}L${P(b)}L${P(c)}V${r(c[1]+thickness)}L${P(add(d,DOWN,thickness))}L${P(add(a,DOWN,thickness))}ZM${P(d)}L${P(c)}M${P(d)}V${r(d[1]+thickness)}`;
  const seams=Array.from({length:cells-1},(_,k)=>`M${P(add(a,u,k+1))}L${P(add(d,u,k+1))}`).join('');
  return {u,v,a,d,outline,seams};
}

function cantilever(length,anchors) {
  const s=strip(length,[30,150],196,30,10);
  const front=add(s.d,DOWN,10);                 // near-side lower deck edge
  const depth=k=>k<=anchors?44:44-30*(k-anchors)/(length-anchors);
  const node=k=>add(add(front,s.u,k),DOWN,depth(k));
  const truss=[`M${P(node(0))}`];
  for(let k=1;k<=length;k++)truss.push(`L${P(node(k))}`);
  const webs=[];
  for(let k=0;k<length;k++)webs.push(k%2?`M${P(add(front,s.u,k))}L${P(node(k+1))}`:`M${P(node(k))}L${P(add(front,s.u,k+1))}`);
  for(let k=0;k<=length;k++)webs.push(`M${P(add(front,s.u,k))}L${P(node(k))}`);
  const piers=[];
  for(let k=0;k<anchors;k++) {
    const p=add(add(node(k),s.u,.15),DOWN,4),q=add(add(node(k),s.u,.85),DOWN,4);
    piers.push(`M${P(p)}V${r(p[1]+26)}L${P(add(q,DOWN,26))}V${r(q[1])}`);
  }
  return svg([[6,s.outline],[3,s.seams],[length>12?3.5:4.5,truss.join('')+webs.join('')],[6,piers.join('')]],-6);
}

function bridge(span) {
  const cells=span+1;
  const s=strip(cells,[26,172],204,30,6);
  const rail=46;
  const lines=[];
  // The far truss shows its top chord and end posts; the near truss its webs.
  for(const base of [s.a,s.d]) {
    const top=k=>add(add(base,s.u,k),DOWN,-rail);
    lines.push(`M${P(add(base,s.u,1))}L${P(top(1))}L${P(top(cells))}L${P(add(base,s.u,cells))}`);
    if(base===s.a)continue;
    for(let k=2;k<cells;k++)lines.push(`M${P(add(base,s.u,k))}L${P(top(k))}`);
    for(let k=1;k<cells;k++)lines.push(k%2?`M${P(add(base,s.u,k))}L${P(top(k+1))}`:`M${P(top(k))}L${P(add(base,s.u,k+1))}`);
  }
  // Abutment block under the supported first tile, with its portal posts.
  const a=add(s.d,DOWN,6),b=add(a,s.u,1);
  const abutment=`M${P(a)}V${r(a[1]+22)}L${P(add(b,DOWN,22))}V${r(b[1])}`;
  const portal=[s.a,s.d].map(base=>{const p=add(base,s.u,.5);return `M${P(p)}V${r(p[1]-rail-6)}L${P(add(add(base,s.u,1),DOWN,-rail))}`;}).join('');
  return svg([[6,s.outline],[3,s.seams],[span>10?3.5:4.5,lines.join('')],[6,abutment+portal]],-8);
}

function column(height) {
  // Drawn like the concrete platform legs: a cap plate on three visible
  // corner posts, one collar per layer joint. Short columns draw wider so
  // every icon spans the vanilla building extent; the layer pitch is fixed.
  const LAYER=28,cap=10,H=height*LAYER;
  const W=Math.min(98,Math.max(50,(205-cap-H)/.88));
  const y0=Math.round((256-(.88*W+cap+H+8))/2);
  const L=[128-W,y0+.44*W],B=[128,y0],R=[128+W,y0+.44*W],F=[128,y0+.88*W];
  const capPath=`M${P(L)}L${P(B)}L${P(R)}L${P(F)}ZM${P(L)}V${r(L[1]+cap)}L${P(add(F,DOWN,cap))}L${P(add(R,DOWN,cap))}V${r(R[1])}M${P(F)}V${r(F[1]+cap)}`;
  const ls=L[1]+cap,fs=F[1]+cap;
  const legs=[
    `M${r(L[0])} ${r(ls)}V${r(ls+H)}L${r(L[0]+15)} ${r(ls+H+7)}V${r(ls+7)}`,
    `M${r(R[0])} ${r(ls)}V${r(ls+H)}L${r(R[0]-15)} ${r(ls+H+7)}V${r(ls+7)}`,
    `M119 ${r(fs-4)}V${r(fs+H-7)}L137 ${r(fs+H+1)}V${r(fs-4)}`,
  ].join('');
  const collars=[];
  for(let k=1;k<height;k++) {
    collars.push(`M${r(L[0]-6)} ${r(ls+k*LAYER-4)}L${r(L[0]+21)} ${r(ls+k*LAYER+8)}`);
    collars.push(`M${r(R[0]+6)} ${r(ls+k*LAYER-4)}L${r(R[0]-21)} ${r(ls+k*LAYER+8)}`);
    collars.push(`M113 ${r(fs+k*LAYER-7)}L143 ${r(fs+k*LAYER+5)}`);
  }
  return svg([[7,capPath],[7,legs],...(collars.length?[[6,collars.join('')]]:[])]);
}

function deck(n) {
  const left=[23,79],back=[128,34],right=[233,79],front=[128,124],T=12,LEG=46;
  const lerp=(a,b,t)=>[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t];
  const grid=[];
  for(let i=1;i<n;i++) {
    grid.push(`M${P(lerp(left,back,i/n))}L${P(lerp(front,right,i/n))}`);
    grid.push(`M${P(lerp(left,front,i/n))}L${P(lerp(back,right,i/n))}`);
  }
  const slab=`M${P(left)}L${P(back)}L${P(right)}V${right[1]+T}L${front[0]} ${front[1]+T}L${left[0]} ${left[1]+T}ZM${P(left)}L${P(front)}L${P(right)}M${P(front)}V${front[1]+T}`;
  // Paired-post trestles under the three visible corners.
  const posts=[];
  for(const [x,y,dx] of [[left[0]+5,left[1]+T+2,14],[right[0]-5,right[1]+T+2,-14],[front[0]-8,front[1]+T,16]]) {
    posts.push(`M${x} ${y}V${y+LEG}M${x+dx} ${y+6}V${y+LEG+6}`);
    posts.push(`M${x} ${y+LEG-14}L${x+dx} ${y+LEG-8}M${x} ${y+12}L${x+dx} ${y+LEG-8}`);
  }
  return svg([[9,slab],[n>4?5:6,grid.join('')],[7,posts.join('')]],12);
}

let count=0;
for(const building of catalog.buildings) {
  let text;
  if(building.kind==='overhang'&&building.id.startsWith('Steel')) {const {length,anchors}=overhangContract(building);text=cantilever(length,anchors);}
  else if(building.kind==='bridge')text=bridge(bridgeSpan(building));
  else if(building.kind==='column')text=column(columnHeight(building));
  else if(building.kind==='deck')text=deck(deckSpan(building));
  else continue;
  await writeFile(new URL(`src/DeepFrontier/Art/Icons/${building.id}.svg`,root),text);
  count++;
}
console.log(`${count} steel structure icon SVGs written.`);
