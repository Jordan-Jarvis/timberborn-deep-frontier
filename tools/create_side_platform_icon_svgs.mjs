// Ivory line-art icons for the concrete side platforms: an n×n deck grid hung
// beside a two-layer reinforced dam pillar, level with its top, with the steel
// knee braces under the deck. Same single-ink drawing language and strokes as
// create_scaffold_icon_svgs.mjs. Hidden lines are removed exactly by clipping
// segments against the projected silhouettes of the solids in front of them.
// create_structural_icons.mjs rasterizes the written SVGs.
import {readFile,writeFile} from 'node:fs/promises';
import {sideDeckAnchor,sideDeckSpan} from './structural_building_content.mjs';

const root=new URL('../',import.meta.url);
const catalog=JSON.parse(await readFile(new URL('tools/structural_content.json',root),'utf8'));
// Same dimetric axes as the scaffold icons: one cell = (±35, 15), one layer = 33.
const project=([x,y,z])=>[35*(x-y),15*(x+y)-33*z];
const DECK=.32;   // deck thickness in layers
const PILLAR=2;   // pillar height in layers

function hull(points) {
  const p=[...points].sort((a,b)=>a[0]-b[0]||a[1]-b[1]);
  const cross=(o,a,b)=>(a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0]);
  const half=list=>{const h=[];for(const q of list){while(h.length>1&&cross(h[h.length-2],h[h.length-1],q)<=0)h.pop();h.push(q);}h.pop();return h;};
  return [...half(p),...half(p.reverse())];
}

// Parts of segment a-b outside the convex polygon (counter-clockwise hull).
function outside(a,b,poly) {
  let t0=0,t1=1;
  const d=[b[0]-a[0],b[1]-a[1]];
  for(let i=0;i<poly.length;i++) {
    const p=poly[i],q=poly[(i+1)%poly.length];
    const n=[q[1]-p[1],p[0]-q[0]];          // outward normal for this winding
    const num=n[0]*(a[0]-p[0])+n[1]*(a[1]-p[1]);
    const den=n[0]*d[0]+n[1]*d[1];
    if(Math.abs(den)<1e-9){if(num>0)return [[a,b]];continue;}
    const t=-num/den;
    if(den<0)t0=Math.max(t0,t);else t1=Math.min(t1,t);
    if(t0>=t1)return [[a,b]];
  }
  const at=t=>[a[0]+d[0]*t,a[1]+d[1]*t];
  return [[a,at(t0)],[at(t1),b]].filter(([u,v])=>Math.hypot(v[0]-u[0],v[1]-u[1])>.5);
}

function box(x0,x1,y0,y1,z0,z1) {
  const corners=[];
  for(const x of [x0,x1])for(const y of [y0,y1])for(const z of [z0,z1])corners.push(project([x,y,z]));
  return hull(corners);
}

function icon(n,ay) {
  // Deck x 0..n, y 0..n, z -DECK..0. The pillar stands in front of the deck's
  // right edge: x n..n+1, y ay..ay+1, z -PILLAR..0 (the icon's anchor sits on
  // the viewer side so it stays fully visible; the game model is the same
  // arrangement seen from another angle).
  const pillar=box(n,n+1,ay,ay+1,-PILLAR,0), deck=box(0,n,0,n,-DECK,0);
  const pillarLines=[],deckLines=[],grid=[],braces=[],dots=[];
  const seg=(list,a,b)=>list.push([project(a),project(b)]);
  // Pillar: top face, its two visible faces, a layer-joint band, two bolts.
  seg(pillarLines,[n,ay,0],[n+1,ay,0]);seg(pillarLines,[n+1,ay,0],[n+1,ay+1,0]);
  seg(pillarLines,[n+1,ay+1,0],[n,ay+1,0]);seg(pillarLines,[n,ay+1,0],[n,ay,0]);
  for(const [x,y] of [[n+1,ay],[n+1,ay+1],[n,ay+1]])seg(pillarLines,[x,y,0],[x,y,-PILLAR]);
  seg(pillarLines,[n+1,ay,-PILLAR],[n+1,ay+1,-PILLAR]);seg(pillarLines,[n+1,ay+1,-PILLAR],[n,ay+1,-PILLAR]);
  seg(pillarLines,[n+1,ay,-1],[n+1,ay+1,-1]);seg(pillarLines,[n+1,ay+1,-1],[n,ay+1,-1]);
  for(const z of [-.5,-1.5])dots.push(project([n+1,ay+.5,z]));
  // Deck: top outline, the two visible side faces and the cell grid.
  seg(deckLines,[0,0,0],[n,0,0]);seg(deckLines,[n,0,0],[n,n,0]);seg(deckLines,[n,n,0],[0,n,0]);seg(deckLines,[0,n,0],[0,0,0]);
  for(const [x,y] of [[n,0],[n,n],[0,n]])seg(deckLines,[x,y,0],[x,y,-DECK]);
  seg(deckLines,[n,0,-DECK],[n,n,-DECK]);seg(deckLines,[n,n,-DECK],[0,n,-DECK]);
  for(let i=1;i<n;i++){seg(grid,[i,0,0],[i,n,0]);seg(grid,[0,i,0],[n,i,0]);}
  // Knee braces from the pillar face up to the deck soffit.
  for(const y of [ay+.3,ay+.7])seg(braces,[n,y,-1.35],[n-1.1,y,-DECK]);
  // Front to back: the pillar hides the deck; both hide the braces.
  const clip=(list,silhouettes)=>silhouettes.reduce((parts,poly)=>parts.flatMap(([a,b])=>outside(a,b,poly)),list);
  const deckVisible=clip(deckLines,[pillar]),gridVisible=clip(grid,[pillar]),braceVisible=clip(braces,[pillar,deck]);
  // Fit the drawing into the native padding range, centred on the canvas.
  const all=[...pillarLines,...deckVisible,...gridVisible,...braceVisible].flat();
  const xs=all.map(p=>p[0]),ys=all.map(p=>p[1]);
  const span=Math.max(Math.max(...xs)-Math.min(...xs),Math.max(...ys)-Math.min(...ys));
  const s=212/span,cx=(Math.max(...xs)+Math.min(...xs))/2,cy=(Math.max(...ys)+Math.min(...ys))/2;
  const map=([x,y])=>`${Math.round(128+(x-cx)*s)} ${Math.round(128+(y-cy)*s)}`;
  const path=list=>list.map(([a,b])=>`M${map(a)}L${map(b)}`).join('');
  const circles=dots.map(p=>{const [x,y]=map(p).split(' ');return `<circle cx="${x}" cy="${y}" r="6"/>`;}).join('');
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 256 256">
 <g fill="none" stroke="#f2e3bb" stroke-linecap="round" stroke-linejoin="round">
  <path stroke-width="10" d="${path(pillarLines)}${path(deckVisible)}${path(braceVisible)}"/>
  <path stroke-width="${n>4?6:7}" d="${path(gridVisible)}"/>
 </g>
 <g fill="#f2e3bb" stroke="none">${circles}</g>
</svg>
`;
}

let count=0;
for(const building of catalog.buildings) {
  if(building.kind!=='sidedeck')continue;
  const [ax]=sideDeckAnchor(building);
  await writeFile(new URL(`src/DeepFrontier/Art/Icons/${building.id}.svg`,root),icon(sideDeckSpan(building),ax));
  count++;
}
console.log(`${count} concrete side platform icon SVGs written.`);
