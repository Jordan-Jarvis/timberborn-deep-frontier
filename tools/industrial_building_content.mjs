import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {solidPowerFaces} from './power_faces.mjs';
import {industrialBlocks,industrialColliders} from './industrial_occupancy.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {applyVanillaSmoke,sceneSmokeRegistration} from './vanilla_smoke.mjs';
const layouts=JSON.parse(await readFile(new URL('./industrial-layouts.json',import.meta.url),'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});
// Grid-registered artwork: native grid door contract and wall-measured shaft
// faces. Since 2026-10-21 none of these machines is walked on above the
// ground door (layout deck mode 'None': no lanes, rail openings or walkway
// spec).
const ALIGNED=new Set(['StoneCrusher','CementKiln','ConcreteMixer','MineralQuarry']);
const SIDE_STEP={Left:[-1,0],Right:[1,0],Down:[0,-1],Up:[0,1]};

// Native entrance on the path cell in front of the door (vanilla convention):
// the door is centred on a tile at a whole layer with its face within 0.15
// of the tile edge, the doorstep (cell behind the face) is occupied and the
// entrance cell is free. The idle slot stands 0.08 in front of the face.
function checkGroundDoor(ident,d,blocks,index,inBounds){
  if(!d.door)throw new Error(`${ident}: no registered ground door`);
  const [x,y,z]=d.door.position,[ox,oy]=d.door.outward;
  if(!Number.isInteger(z)||Math.abs(ox)+Math.abs(oy)!==1)throw new Error(`${ident}: door must be axis-aligned at a whole layer`);
  const along=ox===0?x:y,across=ox===0?y:x,normal=ox===0?oy:ox;
  if(Math.abs(along-Math.floor(along)-.5)>.01)throw new Error(`${ident}: door is not centred on a tile (${along})`);
  const step=normal<0?Math.floor(across+1e-6):Math.ceil(across-1e-6)-1;
  const offset=normal<0?across-step:step+1-across;
  if(offset<-1e-9||offset>.15+1e-9)throw new Error(`${ident}: door face is ${offset.toFixed(3)} from its tile edge`);
  const doorstep=ox===0?[Math.floor(along),step,z]:[step,Math.floor(along),z];
  const entrance=[doorstep[0]+ox,doorstep[1]+oy,z];
  if(JSON.stringify(entrance)!==JSON.stringify(d.entrance))throw new Error(`${ident}: entrance ${d.entrance} is not the path cell ${entrance} in front of the door`);
  if(!inBounds(doorstep)||blocks[index(doorstep)].Occupations==='None')throw new Error(`${ident}: doorstep ${doorstep} is not occupied`);
  if(inBounds(entrance)&&blocks[index(entrance)].Occupations!=='None')throw new Error(`${ident}: entrance cell ${entrance} is occupied`);
  const [ix,iy,iz]=d.idle[0],[gx,gy,gz]=d.origin;
  if(Math.abs(ix+gx-(x+ox*.08))>1e-6||Math.abs(iy+gy-(y+oy*.08))>1e-6||iz+gz!==z)
    throw new Error(`${ident}: idle slot is not 0.08 in front of the door face`);
}

// Shafts only where an authored wall closes the face, measured from the saved
// scene by tools/asset-pipeline/industrial_wall_faces.py. Faces toward empty
// cells come from solidPowerFaces' walls option; faces toward the open bays
// under the walkways (Corners / Top+Corners leave a shaft's Bottom, Path and
// Middle free) are passed as kept sockets. A Left face stays first where one
// exists: the native acceptance fixture builds its shaft one cell left of
// Transputs[0].
async function wallTransputs(ident,d,blocks,index,inBounds,exclude){
  const record=JSON.parse(await readFile(new URL(`../outputs/industrial-integration/${ident}-wall-faces.json`,import.meta.url),'utf8'));
  const scene=await readFile(new URL(`../src/DeepFrontier/Art/Source/${ident}-ReferenceStudy.blend`,import.meta.url));
  if(record.model!==ident||record.sourceSha256!==createHash('sha256').update(scene).digest('hex'))
    throw new Error(`${ident}: wall faces were measured on a different scene; rerun industrial_wall_faces.py`);
  const blocked=new Set(exclude.map(c=>c.join(',')));
  const admits=(c)=>{
    if(!inBounds(c))return true;
    const flags=blocks[index(c)].Occupations.split(', ');
    return flags[0]==='None'||flags.every(f=>f==='Top'||f==='Corners');
  };
  const open=new Map();
  for(const [x,y,z,dir] of record.walls){
    if(blocks[index([x,y,z])].Occupations!=='All')continue;
    const [dx,dy]=SIDE_STEP[dir],n=[x+dx,y+dy,z];
    if(blocked.has(n.join(','))||!admits(n))continue;
    const key=[x,y,z].join(',');
    if(!open.has(key))open.set(key,{cell:[x,y,z],dirs:new Set(),bay:false});
    open.get(key).dirs.add(dir);
    if(inBounds(n)&&blocks[index(n)].Occupations!=='None')open.get(key).bay=true;
  }
  const order=['Left','Right','Down','Up'];
  const sorted=[...open.values()].sort((a,b)=>a.cell[2]-b.cell[2]||a.cell[1]-b.cell[1]||a.cell[0]-b.cell[0]);
  if(sorted.length===0)throw new Error(`${ident}: no authored wall closes an accessible face`);
  const first=sorted.find(f=>f.dirs.has('Left'))??sorted[0];
  const keep=[first,...sorted.filter(f=>f!==first&&f.bay)].map(f=>({Coordinates:xyz(f.cell),
    Directions:order.filter(dir=>f.dirs.has(dir)).join(', '),ReverseRotation:false}));
  return solidPowerFaces(blocks,d.size,{exclude,walls:record.walls,keep});
}
// Final native blocks of a registration (also read by validate_freed_cells.mjs).
export function industrialBlockSpec(ident,d){
  const [w,h]=d.size;
  const index=([x,y,z])=>(z*h+y)*w+x;
  const blocks=industrialBlocks(ident,d.size);
  // Ground approach to the door: the entrance column stays open.
  for(let y=0;y<=d.entrance[1];y++) {
    blocks[index([d.entrance[0],y,0])].Occupations='None';
    blocks[index([d.entrance[0],y,0])].MatterBelow='Any';
  }
  if(ident==='MineralQuarry'){
    // Exactly one native 5x5 seam under the extraction core. Outer foundations
    // remain regular ground foundations, rather than requiring a 10x10 seam.
    for(let y=1;y<6;y++)for(let x=3;x<8;x++){
      blocks[index([x,y,0])].Occupations='Top';blocks[index([x,y,0])].MatterBelow='Ground';
    }
  }
  return blocks;
}

export function industrialLayout(ident){return layouts[ident];}

export async function applyIndustrialLayout(value,building){
  const ident=building.kind==='quarry'?'MineralQuarry':building.id;
  const d=layouts[ident];
  if(!d)throw new Error(`No authored industrial layout: ${ident}`);
  if(JSON.stringify(d.size)!==JSON.stringify(building.size))throw new Error(`Catalog footprint mismatch: ${ident}`);
  const [w,h,layers]=d.size;
  const index=([x,y,z])=>(z*h+y)*w+x;
  const inBounds=([x,y,z])=>x>=0&&y>=0&&z>=0&&x<w&&y<h&&z<layers;
  if(!ALIGNED.has(ident))throw new Error(`No grid-registered industrial artwork: ${ident}`);
  if(d.deckMode!=='None'||d.nodes.length||d.edges.length||d.ports.length)
    throw new Error(`${ident}: industrial machines have no walkways; deck mode must be None without lanes or ports`);
  const blocks=industrialBlockSpec(ident,d);
  checkGroundDoor(ident,d,blocks,index,inBounds);
  value.BlockObjectSpec={Size:xyz(d.size),Blocks:blocks,Entrance:{HasEntrance:true,Coordinates:xyz(d.entrance)},BaseZ:0,Overridable:false,Flippable:true};
  value.Children['#Finished'].CollidersSpec=industrialColliders(blocks,d.size,d.baseZ);
  value.Children['#Unfinished'].Children.ConstructionStage0.CollidersSpec=industrialColliders(blocks,d.size,d.baseZ);
  const exclude=[d.entrance,[d.entrance[0],d.entrance[1]-1,d.entrance[2]]];
  value.TransputProviderSpec.Transputs=await wallTransputs(ident,d,blocks,index,inBounds,exclude);
  const [ix,iy,iz]=d.idle[0], [ox,oy,oz]=d.origin;
  value.BuildingAccessibleSpec.LocalAccess=xyz([ix+ox,iz+oz,iy+oy]);
  // No building-internal walking graph or adaptive rails.
  delete value.BlockObjectNavMeshSettingsSpec;
  delete value.BuildingWalkwaySpec;
  value.TransformSlotInitializerSpec={Slots:[{SlotKeyword:'Entrance',Animation:'ForcedIdle',Inanimate:false,RandomizeYRotation:false,WaterSlot:false}]};
  value.WorkplaceSlotManagerSpec={};value.WorkshopWorkerHiderSpec={};
  value.SimpleManufactoryBehaviorsSpec={};
  if(ident==='MineralQuarry'||ident==='ConcreteMixer')await applyNativeBuildingAssembly(value,ident,d.origin,
    {goodId:'Water',flowNodes:[],wheelNodes:[]});
  // The service inlet is at the foot of the header-tank tower, where the
  // drop pipe reaches the ground. Recipe Water stays in the native
  // manufactory inventory.
  if(ident==='ConcreteMixer')value.BuildingPipeTargetPortsSpec={
    Ports:[{Coordinates:xyz([6,4,0]),Directions:'Right',State:'OpenIn'}],
  };
  // Rear-right pier of the header-tank tower; Power Lines expects grid XYZ
  // (Z is height). Connection count/range remain player-configured settings.
  if(ident==='ConcreteMixer')value.PowerLineSpec={
    ConnectionLocations:[xyz([6.90,4.90,3.80])],
  };
  // Kiln firing smoke at the steel stack while it works (the other machines
  // have no flue). Smog lists the kiln as a polluter.
  if(ident==='CementKiln')applyVanillaSmoke(value,await sceneSmokeRegistration('industrial-integration',ident,d),ident);
}
