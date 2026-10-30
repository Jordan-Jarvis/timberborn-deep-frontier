// Bank-height Hatchery geometry contracts. Only the nursery owns these rules.
import {readFile,copyFile} from 'node:fs/promises';
import {structureBlocks,authoredColliders,roomPowerFaces} from './grid_structure.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {nativeEntrance} from './native_entrance.mjs';
const root=new URL('../',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});

export function hatcheryBlocks(layout) {
  // 7x7 since the compact early-game footprint (2026-10-26; 8x8x5 before),
  // 3 high since the one-layer headhouse and canopy (2026-10-30).
  if(layout.deckMode!=='PlayerPlacedPaths'||layout.baseZ!==1||layout.size.join(',')!=='7,7,3')
    throw new Error('Hatchery native bank/platform registration changed');
  const blocks=structureBlocks(layout.structure,layout.size);
  const [w,depth]=layout.size;
  const index=([x,y,z])=>(z*depth+y)*w+x;
  // Native SwimmingPool convention: terrain occupies the submerged front
  // row. The entry apron is worn at bank height, so no cell below it is ours.
  for(let x=0;x<w;x++) {
    Object.assign(blocks[index([x,0,0])],{MatterBelow:'Any',Occupations:'None',Stackable:'None'});
    blocks[index([x,0,1])].MatterBelow='GroundOrStackable';
    if(blocks[index([x,0,1])].Occupations==='None')blocks[index([x,0,1])].Occupations='Floor';
  }
  // Pens hang in the water; the bank row anchors the entire nursery. They do
  // not demand riverbed terrain at exactly one unit below their cage bottoms.
  for(let y=1;y<depth;y++)for(let x=0;x<w;x++)blocks[index([x,y,0])].MatterBelow='Any';
  for(const cell of layout.buildableCells) {
    if(blocks[index(cell)].Occupations!=='None')throw new Error('Hatchery clear dock is occupied: '+cell);
    if(blocks[index([cell[0],cell[1],cell[2]-1])].Stackable!=='BlockObject')throw new Error('Hatchery dock has no native stackable slab: '+cell);
  }
  if(blocks.some(b=>b.Occupations.includes('Path')))throw new Error('Hatchery decorative deck acquired built-in paths');
  return blocks;
}

export function applyHatcheryStructure(value,layout,manifest) {
  const blocks=hatcheryBlocks(layout);
  const [w,depth]=layout.size,layer=w*depth;
  const index=([x,y,z])=>(z*depth+y)*w+x;
  if(blocks[index(layout.entrance)].Occupations!=='Floor')throw new Error('Native bank entrance lost its authored floor-only cell');
  // Player paths, shafts and platforms on the deck stand on z=0 slabs below
  // BaseZ and share the hatchery's native load layer. They survive a reload
  // only because StackableBaseLoadOrder (Scripts/Waterside) adds the hatchery
  // first in that layer, which is valid only while every foundation block is
  // at or below BaseZ (here: the bank row at z=1, resting on terrain).
  const solid=new Set(['Ground','GroundOrStackable','Stackable']);
  if(!blocks.some((b,i)=>i<layer&&b.Stackable!=='None')||blocks.some((b,i)=>solid.has(b.MatterBelow)&&Math.floor(i/layer)>1))
    throw new Error('Hatchery deck load order needs stackable slabs below BaseZ and no foundation above it');
  // Native Entrance: the bank cell in front of the door (layout `entrance` is the door cell), so a
  // player's ordinary Path there is the access (tools/native_entrance.mjs). Until 2026-10-26 the
  // Entrance was the floor-only door cell itself: off the road network, so the hatchery reported
  // "not connected" until a path was laid on its own door cell.
  const door=layout.entrance,entrance=nativeEntrance('FishHatchery',door,layout.size,blocks);
  value.BlockObjectSpec={Size:xyz(layout.size),Blocks:blocks,Entrance:{HasEntrance:true,Coordinates:xyz(entrance)},BaseZ:1,Overridable:false,Flippable:true};
  value.BuildingAccessibleSpec={LocalAccess:xyz(layout.localAccess),ForceOneFinalAccess:false};
  // Native BlockObjectPreviewPicker places origin = (cursor cell - pivot) and
  // takes the height from the terrain or stackable top the cursor ray hits,
  // minus BaseZ. Without a pivot the cursor sits over the footprint centre,
  // i.e. over the water under the deck, so the preview dropped to the
  // riverbed. The pivot puts the door cell on the bank under the cursor. A
  // CustomPivot is rotated but never flipped (BlockObjectPreviewPicker
  // .ComposeCoordinates), so a flipped hatchery has the mirrored bank-row
  // cell under the cursor: still the bank, though on an uneven bank that
  // cell may sit lower than the door (waterside_sites.json landCells).
  const [ex,ey]=layout.entrance;
  value.PlaceableBlockObjectSpec={...value.PlaceableBlockObjectSpec,
    CustomPivot:{HasCustomPivot:true,Coordinates:{X:ex+.5,Y:ey+.5,Z:0}}};
  value.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
  const colliders=authoredColliders(manifest,layout.structure,1);
  value.Children['#Finished'].CollidersSpec=colliders;
  value.Children['#Unfinished']={Children:{ConstructionStage0:{TimbermeshSpec:{Model:'Buildings/Food/FishHatchery/FishHatchery.IronTeeth.ConstructionStage0.Model'},CollidersSpec:colliders}}};
  value.BlockObjectNavMeshSettingsSpec={NoAutoWalls:false,GenerateFloorsOnStackable:true,
    EdgeGroups:[{Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,
      // The door links, and the door cell to the player's path on the Entrance cell.
      AddedEdges:[...layout.doorLinks.map(link=>({Start:xyz(link.Interior),End:xyz(link.Exterior),IsTwoWay:true})),
        {Start:xyz(door),End:xyz(entrance),IsTwoWay:true}]}],
    UnblockedCoordinates:[],BlockedEdges:[]};
  delete value.BuildingWalkwaySpec;
  // The native ImpermeableFloor uses the same Floor-only/roof-path contract
  // on terrain. DirtPath meshes sit only 0.3mm above soil and would be hidden
  // inside this actual 20mm raised timber wearing surface.
  value.PathModelTypeEnforcerSpec={PathModelType:'Roof'};
  // Every exposed headhouse wall can receive a shaft, except the door. The
  // separate filter-machine right face retains its original power socket.
  const transputs=new Map(roomPowerFaces(layout.structure,layout.size).map(p=>[Object.values(p.Coordinates).join(','),p]));
  for(const socket of layout.shaftPorts) {
    const key=Object.values(socket.Coordinates).join(',');
    const existing=transputs.get(key);
    const directions=new Set([...(existing?existing.Directions.split(', '):[]),...socket.Directions.split(', ')]);
    transputs.set(key,{...socket,Directions:[...directions].join(', ')});
  }
  value.TransputProviderSpec={IgnoreRotation:false,Transputs:[...transputs.values()]};
  return value;
}

// The door cell stands on the bank; the rest of the bank row may step down
// over a lower shore or water on adaptive bank posts, and the deck stands on
// its adaptive piles; only the pens need water. WaterDepthWorkCellsSpec
// replaces the native SwimmingPool TickableWaterBuildingSpec (the component
// refuses to coexist with it).
export function applyHatcheryWaterside(value,site,layout) {
  const blocks=value.BlockObjectSpec.Blocks,[w,depth]=layout.size;
  const block=([x,y,z])=>blocks[(z*depth+y)*w+x];
  const key=c=>c.join(',');
  const sameCell=(a,b)=>a.length===3&&a.every((v,i)=>v===b[i]);
  if(!sameCell(site.workCells.cells[0],layout.waterCell))
    throw new Error('Hatchery contamination sample must stay the verified pen probe');
  for(const cell of site.workCells.cells) {
    if(!layout.structure.reservations.some(([x0,y0,z0,x1,y1,z1])=>x0<=cell[0]&&cell[0]<x1&&y0<=cell[1]&&cell[1]<y1&&z0<=cell[2]&&cell[2]<z1&&z1-z0===1&&z0===0))
      throw new Error('Hatchery water work cell is outside a nursery pen: '+cell);
    if(block(cell).Stackable!=='None')throw new Error('Hatchery pen cell supports stacking: '+cell);
  }
  if(!site.supports.columns.length)throw new Error('Hatchery deck needs adaptive piles');
  for(const [x,y,z] of site.supports.columns) {
    if(z!==0||y===0)throw new Error('Hatchery piles start below the deck, off the bank row: '+[x,y,z]);
    const deck=block([x,y,0]);
    if(deck.MatterBelow!=='Any'||deck.Occupations==='None'||
       !Object.values(layout.structure.platforms).some(([x0,y0,,x1,y1])=>x0<=x&&x<x1&&y0<=y&&y<y1))
      throw new Error('Hatchery pile is not under a deck slab: '+[x,y,z]);
    if(site.workCells.cells.some(c=>c[0]===x&&c[1]===y))throw new Error('Hatchery pile stands in a pen: '+[x,y,z]);
  }
  // Bank row: the door cell keeps native ground below; every other bank cell
  // may overhang a lower shore, carried by an adaptive post directly below it
  // (top at the terrain row z=0, so on a level bank the post finds the bed at
  // depth 0 and shows nothing).
  const ground=new Set(site.supports.groundCells.map(key));
  if(!ground.has(key(layout.entrance))||site.supports.groundCells.some(([x,y,z])=>y!==0||z!==1))
    throw new Error('Hatchery ground cells must be bank-row cells including the door');
  const posts=new Set(site.supports.bankColumns.map(key));
  for(let x=0;x<w;x++) {
    const apron=block([x,0,1]);
    if(apron.Occupations==='None'||apron.MatterBelow!=='GroundOrStackable'||block([x,0,0]).Occupations!=='None')
      throw new Error('Hatchery bank row lost its occupied bank-height apron over the terrain row: '+x);
    if(ground.has(key([x,0,1]))===posts.has(key([x,0,0])))
      throw new Error('Each bank cell is either native ground or carried by one adaptive bank post: '+x);
    if(!ground.has(key([x,0,1])))apron.MatterBelow='Any';
  }
  if(posts.size!==site.supports.bankColumns.length)throw new Error('Duplicate hatchery bank post');
  const foundation=blocks.map((b,i)=>b.MatterBelow!=='Any'?i:-1).filter(i=>i>=0);
  if(foundation.length!==ground.size||!site.supports.groundCells.every(([x,y,z])=>block([x,y,z]).MatterBelow==='GroundOrStackable'))
    throw new Error('Only the listed bank ground cells may require ground below the Hatchery');
  delete value.TickableWaterBuildingSpec;
  value.AdaptiveSupportsSpec={Columns:[...site.supports.columns,...site.supports.bankColumns].map(xyz),MaxDepth:site.supports.maxDepth,
    SegmentNodeName:'#SupportSegment',FootNodeName:'#SupportFoot'};
  const work=site.workCells;
  value.WaterDepthWorkCellsSpec={WorkCells:work.cells.map(xyz),MinDepth:work.minDepth,MaxDepth:work.maxDepth,Hysteresis:work.hysteresis};
  return value;
}

export async function applyHatchery(value) {
  const d=(await read('tools/civic-layouts.json')).FishHatchery;
  applyHatcheryStructure(value,d,await read('outputs/reference-studies/FishHatchery-structure.json'));
  value.PlatformDeckSpec=await read('outputs/civic-integration/FishHatchery-platform-deck.json');
  applyHatcheryWaterside(value,(await read('tools/waterside_sites.json')).FishHatchery,d);
  value.BuildingPipeTargetPortsSpec=(await read('tools/aquaculture_pipe_ports.json')).FishHatchery;
  value.TransformSlotInitializerSpec={Slots:[{SlotKeyword:'Entrance',Animation:'ForcedIdle',Inanimate:false,RandomizeYRotation:false,WaterSlot:false}]};
  value.WorkplaceSlotManagerSpec={};value.WorkshopWorkerHiderSpec={};
  await applyNativeBuildingAssembly(value,'FishHatchery',d.origin,{goodId:'Water',flowNodes:[],wheelNodes:[]});
  for(const suffix of ['Model','ConstructionStage0.Model']) {
    const path=`Buildings/Food/FishHatchery/FishHatchery.IronTeeth.${suffix}.timbermesh`;
    await copyFile(new URL('outputs/civic-integration/Data/'+path,root),new URL('src/DeepFrontier/Data/'+path,root));
  }
  delete value.ProductionResetterSpec;
}
