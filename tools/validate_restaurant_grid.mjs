import {readFile,writeFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url),read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const d=(await read('tools/civic-layouts.json')).Restaurant;
const b=await read('src/DeepFrontier/Data/Buildings/Food/Restaurant/Restaurant.IronTeeth.blueprint.json');
const m=await read('outputs/reference-studies/Restaurant-structure.json');
const visitor=await read('outputs/reference-studies/Restaurant-visitor-manifest.json');
const check=(ok,message)=>{if(!ok)throw new Error(message);};
const [w,depth]=d.size,at=([x,y,z])=>b.BlockObjectSpec.Blocks[(z*depth+y)*w+x];
check(d.deckMode==='PlayerPlacedPaths'&&!b.BuildingWalkwaySpec&&b.PlatformDeckSpec,'Native player-deck contract absent');
check(b.BlockObjectNavMeshSettingsSpec.GenerateFloorsOnStackable,'Native platform floor generation disabled');
check(b.BlockObjectSpec.Blocks.every(b=>!b.Occupations.split(', ').includes('Path')),'Building reserves outdoor Path occupation');
const doors=[];
for(const [id,door] of Object.entries(d.structure.doors)) {
  const source=visitor.doors.filter(v=>v.id===id);check(source.length===1,'Missing source doorway '+id);
  const pos=source[0].position.map((v,i)=>v+d.origin[i]);
  check(pos.every((v,i)=>Math.abs(v-door.position[i])<1e-8),'Source/grid door disagreement '+id);
  const axis=door.outward[0]!==0?0:1;
  // Float tolerance: the native origin is a double near a tenth (restaurant_structure.ORIGIN).
  check(Math.abs(pos[axis]-Math.round(pos[axis]))<1e-8&&Math.abs((pos[1-axis]-Math.floor(pos[1-axis]))-.5)<1e-8,'Door is off its tile boundary/center '+id);
  doors.push({id,position:pos,centerOffset:0,boundaryOffset:0});
}
for(const cell of d.suggestedPathCells) {
  check(!['All','Middle'].includes(at(cell).Occupations),'Fixed geometry blocks authored public aisle '+cell);
  if(cell[2]>0)check(at([cell[0],cell[1],cell[2]-1]).Stackable==='BlockObject','Unsupported public deck '+cell);
}
const inside=new Set(d.interiorCells.map(c=>c.join(',')));
for(const group of b.BlockObjectNavMeshSettingsSpec.EdgeGroups)for(const e of group.AddedEdges) {
  const a=[e.Start.X,e.Start.Y,e.Start.Z].join(','),c=[e.End.X,e.End.Y,e.End.Z].join(',');
  check(inside.has(a)||inside.has(c),'Building still supplies an outdoor road edge '+a+' -> '+c);
}
let pickingBoxes=0;
for(const p of m.parts)for(const box of p.pickingBoxes) {
  for(let axis=0;axis<3;axis++)check(box.center[axis]-box.size[axis]/2>=p.bounds[axis]-1e-8&&box.center[axis]+box.size[axis]/2<=p.bounds[axis+3]+1e-8,'Picking box extends beyond authored visible structural part '+p.id);
  pickingBoxes++;
}
const supports=Object.values(d.structure.supports).flat();
check(supports.length===16,'Restaurant must retain sixteen explicitly placed short deck posts');
check(d.structure.supports.RoofTerraceOuter.length===0,'Cantilevered roof terrace acquired ground-reaching legs');
for(const [id,bounds] of Object.entries(d.structure.platforms))for(const [cell,corner,bottom] of d.structure.supports[id])check(bounds[5]-bottom<=2,'Deck post extends through multiple storeys '+id);
// One layer per storey (2026-10-30): the cantilevered roof bay's slab is layer 2.
for(let z=0;z<2;z++)for(let y=2;y<5;y++)for(let x=7;x<9;x++)check(at([x,y,z]).Occupations==='None','Former roof leg still reserves empty construction space');
for(let y=2;y<5;y++)for(let x=6;x<9;x++) {
  check(at([x,y,3]).Occupations==='None','Fixed furniture still consumes the 3x3 roof area');
  check(at([x,y,2]).Stackable==='BlockObject','Roof tile does not support native construction');
}
check(JSON.stringify(d.structure.platforms.RoofTerraceOuter)==='[7,2,2,9,5,3]','Roof slab was enlarged instead of clearing fixed furniture');
const levels=[...new Set(b.TransputProviderSpec.Transputs.map(t=>t.Coordinates.Z))].sort((a,b)=>a-b);
// Shafts meet every flat exterior face (validate_connection_faces.mjs). Since
// the 2026-10-30 compaction the three storeys are layers 0, 1 and 2 (the roof
// deck's slab is layer 2 too).
check([0,1,2].every(z=>levels.includes(z)),'Missing multi-level mechanical faces');
const report={scope:'Source and blueprint contracts only; native placement/traversal must be tested separately.',
  doors,structuralParts:m.parts.length,pickingBoxes,shortDeckPosts:supports.length,roofTerraceGroundLegs:0,playerPathCells:d.suggestedPathCells.length,
  mechanicalFaces:b.TransputProviderSpec.Transputs.length,powerLevels:levels,roadOccupationReservedByBuilding:0};
await writeFile(new URL('outputs/restaurant-grid-source-checks.json',root),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report));
