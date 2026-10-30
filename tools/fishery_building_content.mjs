import {readFile,copyFile,mkdir,writeFile} from 'node:fs/promises';
import {solidPowerFaces} from './power_faces.mjs';
import {industrialColliders} from './industrial_occupancy.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {applyVanillaSmoke,sceneSmokeRegistration} from './vanilla_smoke.mjs';
import {nativeEntrance} from './native_entrance.mjs';
const root=new URL('../',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});

export async function authorShoreFishing() {
  const plan=await read('tools/aquaculture.json');
  const folder=new URL('src/DeepFrontier/Data/Buildings/Food/GathererFlag/',root);
  await mkdir(folder,{recursive:true});
  await writeFile(new URL('GathererFlag.IronTeeth.blueprint.json',folder),JSON.stringify({ShoreFishingSpec:plan.shoreFishing},null,2)+'\n');
}

// enUS rows for src/DeepFrontier/Scripts/Waterside (WatersideLoc keys).
export const WATERSIDE_ROWS=[
  ['DeepFrontier.Waterside.SupportTooDeep','A support post would need more than {0} m to reach the ground or riverbed.','Deep Frontier waterside placement error; {0} = AdaptiveSupportsSpec.MaxDepth'],
  ['DeepFrontier.Waterside.SupportOutsideMap','A support post would stand outside the map.','Deep Frontier waterside placement error: a support column lies outside the map'],
  ['DeepFrontier.Waterside.WorkCellsTooShallow','Water does not reach {0} marked working cell(s): the surface must stand at least {1} m above their floor.','Deep Frontier waterside preview warning; {0} = cell count; {1} = MinDepth'],
  ['DeepFrontier.Waterside.WorkCellsTooDeep','Too deep under {0} marked working cell(s): at most {1} m of water is allowed.','Deep Frontier waterside preview warning; {0} = cell count; {1} = MaxDepth'],
  ['DeepFrontier.Waterside.Status.WaterTooDeep','The water under the working area is too deep.','Deep Frontier waterside building status'],
  ['DeepFrontier.Waterside.Status.WaterTooDeep.Short','Water too deep','Deep Frontier waterside building status alert'],
];

export async function applyHatchery(value) {
  const {applyHatchery: apply}=await import('./hatchery_building_content.mjs');
  return apply(value);
}

export async function applyFishery(value) {
  const d=(await read('tools/civic-layouts.json')).FisheryWorks;
  const [w,depth,h]=d.size,index=([x,y,z])=>(z*depth+y)*w+x;
  const blocks=Array.from({length:w*depth*h},()=>({MatterBelow:'Any',Occupations:'None',Stackable:'None',OccupyAllBelow:false,Underground:false}));
  const region=(a,b,occupation)=>{
    for(let z=a[2];z<=b[2];z++)for(let y=a[1];y<=b[1];y++)for(let x=a[0];x<=b[0];x++) {
      if(x<0||y<0||z<0||x>=w||y>=depth||z>=h)throw new Error('Fishery structural region outside authored envelope');
      Object.assign(blocks[index([x,y,z])],{Occupations:occupation,MatterBelow:z===0?'GroundOrStackable':'Any'});
    }
  };
  // Occupation describes actual rooms, slab supports and machinery; it does
  // not fill the registration envelope, especially below the roof terrace.
  // 2026-10-22: the footprint ends at the walls (12x10 -> 11x8, native y 2
  // less). The front basin and the rear stock are gone; the two rear water
  // tanks stay as the pipe inlet.
  // 2026-10-30 compaction: one layer per storey (galleries and the upper
  // hall at layer 1, the long roof lower, 11x8x7 -> 11x8x4); the rear water
  // tanks stand under the rear gallery (no-clutter rule).
  region([2,1,0],[8,6,0],'Top, Corners'); // Gallery slabs on their corner posts.
  region([2,1,0],[7,5,0],'All'); // Lower processing hall.
  region([3,1,1],[7,5,1],'All'); // Set-back upper hall.
  region([2,0,0],[4,2,0],'All'); // Enclosed entrance vestibule.
  region([2,0,1],[4,1,1],'All'); // Low entrance roof.
  region([2,1,2],[7,6,2],'All'); // Main roof.
  region([4,1,3],[5,6,3],'All'); // Main roof ridge.
  region([0,2,0],[2,5,0],'All'); // One-storey warehouse and roof slab.
  region([2,3,1],[3,4,2],'All'); // Terrace door house and its roof.
  region([9,0,0],[10,5,0],'All'); // Low water basins.
  region([9,2,1],[10,5,2],'All'); // Native wheel and upper header.
  region([3,6,0],[4,6,0],'All'); // Rear water tanks under the gallery: the pipe inlet.
  region([8,6,0],[8,6,1],'Corners'); // Hoist mast outside the walking lane.
  region([8,6,2],[10,6,2],'All');
  // Player-placed-path galleries and roof terrace (2026-10-30, user: every
  // flat roof tile placeable like a platform): the deck cells stay free and
  // the slab under each is a stackable roof deck.
  if(d.deckMode!=='PlayerPlacedPaths')throw new Error('Fishery galleries must be player-path decks');
  const interior=new Set(d.interiorCells.map(c=>c.join(',')));
  for(const n of d.nodes) {
    if(interior.has(n.cell.join(',')))continue;
    const [x,y,z]=n.cell;
    if(z>0) {
      const support=blocks[index([x,y,z-1])];
      if(support.Occupations==='None')throw new Error(`Fishery route lacks slab support: ${n.cell}`);
      support.Stackable='BlockObject';
    }
  }
  for(const cell of d.buildableCells)blocks[index([cell[0],cell[1],cell[2]-1])].Stackable='BlockObject';
  // Waterside flume wing: the wheel and both long basins may overhang a lower
  // bank or water on adaptive piles. Everything else, including the ground
  // door, vestibule and entrance, still needs ground or a stackable below.
  const site=(await read('tools/waterside_sites.json')).FisheryWorks;
  if(site.workCells!==null)throw new Error('Fishery has no site water requirement; it uses delivered Water');
  const wing=new Set(site.supports.groundOptionalCells.map(c=>c.join(',')));
  for(const key of wing) {
    const [x,y,z]=key.split(',').map(Number),b=blocks[index([x,y,z])];
    if(z!==0||b.MatterBelow!=='GroundOrStackable'||b.Occupations!=='All'||x<9)
      throw new Error('Fishery waterside wing must be the occupied ground-layer basin cells: '+key);
    b.MatterBelow='Any';
  }
  for(const [x,y,z] of site.supports.columns)
    if(z!==-1||!wing.has([x,y,0].join(',')))throw new Error('Fishery pile must stand directly below a wing cell: '+[x,y,z]);
  for(const n of d.nodes)if(n.cell[2]===0&&wing.has(n.cell.join(',')))throw new Error('Fishery ground route enters the overhanging wing');
  if(wing.has(d.entrance.join(','))||wing.has([d.entrance[0],d.entrance[1]+1,0].join(',')))throw new Error('Fishery door must stay on land');
  value.AdaptiveSupportsSpec={Columns:site.supports.columns.map(xyz),MaxDepth:site.supports.maxDepth,
    SegmentNodeName:'#SupportSegment',FootNodeName:'#SupportFoot'};
  // Native Entrance: the path cell in front of the ground door (layout `entrance` is the door cell),
  // so a player's ordinary Path there is the access (tools/native_entrance.mjs). Until 2026-10-26 the
  // Entrance was the door cell itself and the player's path showed no connection to the door.
  const door=d.entrance,entrance=nativeEntrance('FisheryWorks',door,d.size,blocks);
  value.BlockObjectSpec={Size:xyz(d.size),Blocks:blocks,Entrance:{HasEntrance:true,Coordinates:xyz(entrance)},BaseZ:0,Overridable:false,Flippable:true};
  value.BuildingAccessibleSpec={LocalAccess:xyz([3.25,0,.25]),ForceOneFinalAccess:false};
  value.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
  value.Children['#Finished'].CollidersSpec=industrialColliders(blocks,d.size,d.baseZ);
  value.Children['#Unfinished']={Children:{ConstructionStage0:{TimbermeshSpec:{Model:'Buildings/Food/FisheryWorks/FisheryWorks.IronTeeth.ConstructionStage0.Model'},CollidersSpec:industrialColliders(blocks,d.size,d.baseZ)}}};
  // Only the enclosed interior route is building navigation; the galleries and
  // the terrace are native stackable floors reached through the door links.
  const edgeGroups=d.edges.filter(([a,b])=>interior.has(a.join(','))&&interior.has(b.join(',')))
    .map(([a,b])=>({Cost:1,Group:{UseGroup:a[2]!==b[2],GroupName:a[2]!==b[2]?'DeepFrontierInterior':''},IsPath:true,AddedEdges:[{Start:xyz(a),End:xyz(b),IsTwoWay:true}]}));
  edgeGroups.push({Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,AddedEdges:d.doorLinks.map(l=>({Start:xyz(l.Interior),End:xyz(l.Exterior),IsTwoWay:true}))});
  // The door cell's deck route meets the player's path on the Entrance cell.
  edgeGroups.push({Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,AddedEdges:[{Start:xyz(door),End:xyz(entrance),IsTwoWay:true}]});
  value.BlockObjectNavMeshSettingsSpec={NoAutoWalls:false,GenerateFloorsOnStackable:true,EdgeGroups:edgeGroups,UnblockedCoordinates:[],BlockedEdges:[]};
  value.PlatformDeckSpec=await read('outputs/civic-integration/FisheryWorks-platform-deck.json');
  // Shafts may meet any solid wall; the tested sockets stay first.
  {value.TransputProviderSpec={IgnoreRotation:false,Transputs:solidPowerFaces(blocks,d.size,{exclude:[door,entrance],keep:[
    {Coordinates:xyz([0,3,0]),Directions:'Left, Bottom',ReverseRotation:false},
    {Coordinates:xyz([6,5,0]),Directions:'Up, Bottom',ReverseRotation:false}
  ]})};}
  value.BuildingPipeTargetPortsSpec=(await read('tools/aquaculture_pipe_ports.json')).FisheryWorks;
  value.TransformSlotInitializerSpec={Slots:[{SlotKeyword:'Entrance',Animation:'ForcedIdle',Inanimate:false,RandomizeYRotation:false,WaterSlot:false}]};
  value.WorkplaceSlotManagerSpec={};value.WorkshopWorkerHiderSpec={};
  // Vanilla smoke from the scene's registered emitters: none since the roof
  // chimney went (no roof vents, user 2026-10-30).
  applyVanillaSmoke(value,await sceneSmokeRegistration('civic-integration','FisheryWorks',d),'FisheryWorks');
  await applyNativeBuildingAssembly(value,'FisheryWorks',d.origin,{goodId:'Water',flowNodes:['FisheryCascade'],wheelNodes:['FisheryNativeWheel']});
  const folder='Buildings/Food/FisheryWorks/';
  for(const suffix of ['Model','ConstructionStage0.Model']) {
    const path=folder+`FisheryWorks.IronTeeth.${suffix}.timbermesh`;
    await copyFile(new URL('outputs/civic-integration/Data/'+path,root),new URL('src/DeepFrontier/Data/'+path,root));
  }
}
