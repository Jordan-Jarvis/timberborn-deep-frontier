import {readFile,copyFile,mkdir,writeFile} from 'node:fs/promises';
import {solidPowerFaces} from './power_faces.mjs';
import {industrialColliders} from './industrial_occupancy.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {applyVanillaSmoke,sceneSmokeRegistration} from './vanilla_smoke.mjs';
import {nativeEntrance} from './native_entrance.mjs';
import {buildingCost} from './lategame_costs.mjs';
const root=new URL('../',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});

// Fisher Flag (2026-11-02; tools/aquaculture.json fisherFlag). It replaced the Gatherer
// Flag's "Catch fish" mode, which players could not find: the vanilla Gatherer Flag is
// no longer patched, and fresh fish come from this one flag beside it in the Food menu.
// The blueprint is the vanilla Iron Teeth Gatherer Flag (workplace, terrain range,
// output inventory, idle seat, outfit, lamp, construction base) with the fishing job
// (FisherFlagSpec, Scripts/FisherFlag.cs) in place of gathering, its own model
// and construction stage (tools/asset-pipeline/build_fisher_flag.py, exported to
// outputs/civic-integration) and
// an authored cost on the material rule (building_construction_costs.json buildings).
export async function authorFisherFlag() {
  const plan=(await read('tools/aquaculture.json')).fisherFlag;
  const value=await read('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Buildings/Food/GathererFlag/GathererFlag.IronTeeth.blueprint.json');
  for(const key of ['GathererFlagSpec','YieldRemovingBuildingSpec'])
    if(!value[key])throw new Error('Fisher Flag: the vanilla Gatherer Flag lost '+key);
  delete value.GathererFlagSpec;delete value.YieldRemovingBuildingSpec;
  const rows=(await read('tools/building_construction_costs.json')).buildings.FisherFlag;
  if(!rows)throw new Error('Fisher Flag: no construction cost in building_construction_costs.json buildings');
  if(!Number.isInteger(plan.science)||plan.science<0)throw new Error('Fisher Flag: invalid science');
  value.BuildingSpec={...value.BuildingSpec,BuildingCost:buildingCost('FisherFlag',rows.map(([Id,Amount])=>({Id,Amount})),plan.science),ScienceCost:plan.science};
  value.TemplateSpec={...value.TemplateSpec,TemplateName:'FisherFlag.IronTeeth',BackwardCompatibleTemplateNames:[]};
  value.PlaceableBlockObjectSpec={...value.PlaceableBlockObjectSpec,ToolGroupId:'Food',ToolOrder:plan.toolOrder,DevModeTool:false};
  value.LabeledEntitySpec={...value.LabeledEntitySpec,DisplayNameLocKey:'Building.FisherFlag.DisplayName',
    DescriptionLocKey:'Building.FisherFlag.Description',FlavorDescriptionLocKey:'Building.FisherFlag.FlavorDescription',
    Icon:'Buildings/Food/FisherFlag/Icon'};
  // Native F mirroring like every Deep Frontier building (audit_building_assets --require-mirroring).
  value.BlockObjectSpec={...value.BlockObjectSpec,Flippable:true};
  for(const key of ['GoodId','CatchHours','MinimumDepth','MaximumContamination','MaximumReachDown'])
    if(plan.spec[key]===undefined)throw new Error('Fisher Flag: spec lacks '+key);
  value.FisherFlagSpec=plan.spec;
  // The banner swings while the flag stands (Scripts/AmbientAnimation.cs).
  value.AmbientAnimationSpec={};
  const finished=value.Children['#Finished'];
  finished.TimbermeshSpec={Model:plan.model.resource};
  // Unity axes: X across, Y up, Z back. The landing with its posts, the pole, the banner.
  finished.CollidersSpec={BoxColliders:[
    {Center:{X:.5,Y:.24,Z:.5},Size:{X:.9,Y:.48,Z:.92}},
    {Center:{X:.5,Y:.89,Z:.58},Size:{X:.07,Y:1.7,Z:.07}},
    {Center:{X:.5,Y:1.36,Z:.547},Size:{X:.5,Y:.62,Z:.05}}],SphereColliders:[],CapsuleColliders:[]};
  // The vanilla nested construction base stays; the stage model is the flag's own.
  const stage=value.Children['#Unfinished'].Children.ConstructionStage0;
  if(!stage?.TimbermeshSpec)throw new Error('Fisher Flag: the vanilla Gatherer Flag lost its ConstructionStage0');
  stage.TimbermeshSpec={Model:plan.model.stageResource};
  const folder='Buildings/Food/FisherFlag/';
  await mkdir(new URL('src/DeepFrontier/Data/'+folder,root),{recursive:true});
  for(const resource of [plan.model.resource,plan.model.stageResource])
    await copyFile(new URL('outputs/civic-integration/Data/'+resource+'.timbermesh',root),new URL('src/DeepFrontier/Data/'+resource+'.timbermesh',root));
  await writeFile(new URL('src/DeepFrontier/Data/'+folder+'FisherFlag.IronTeeth.blueprint.json',root),JSON.stringify(value,null,2)+'\n');
  return folder+'FisherFlag.IronTeeth.blueprint';
}

// enUS rows for src/DeepFrontier/Scripts/Waterside (WatersideLoc keys).
export const WATERSIDE_ROWS=[
  ['DeepFrontier.Waterside.SupportTooDeep','A support post would need more than {0} m to reach the ground or riverbed.','Deep Frontier waterside placement error; {0} = AdaptiveSupportsSpec.MaxDepth'],
  ['DeepFrontier.Waterside.SupportOutsideMap','A support post would stand outside the map.','Deep Frontier waterside placement error: a support column lies outside the map'],
  ['DeepFrontier.Waterside.WorkCellsTooShallow','{0} pen tile(s) are too shallow: the water there must be at least {1} m deep.','Deep Frontier waterside preview warning; {0} = cell count; {1} = MinDepth'],
  ['DeepFrontier.Waterside.WorkCellsTooDeep','{0} pen tile(s) are too deep: at most {1} m of water is allowed there.','Deep Frontier waterside preview warning; {0} = cell count; {1} = MaxDepth'],
  ['DeepFrontier.Waterside.Status.WaterTooDeep','The water under the pens is too deep.','Deep Frontier waterside building status'],
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
  // not fill the registration envelope.
  // Second shrink pass (2026-11-01): 11x8x4 -> 6x5x3 (fishery_works_geometry.py,
  // grid coordinates). Water wing on the left (x 0..1), the lower hall x 2..5
  // with its deck roof at layer 1, the upper hall x 2..4 behind it.
  region([0,0,0],[1,4,0],'All'); // Long and small basins (the crane mast stands in (1,0)).
  region([0,2,1],[1,4,1],'All'); // Native wheel, cascade and header basin.
  region([0,3,2],[1,4,2],'All'); // Header basin rim.
  region([1,0,1],[1,0,1],'Corners'); // Crane mast beside the small basin.
  region([0,0,2],[1,0,2],'All'); // Crane jib.
  region([2,0,0],[5,3,0],'All'); // Lower processing hall under its deck roof.
  region([2,4,0],[4,4,0],'All'); // Undercroft: the water tanks (the pipe inlet), posts and net.
  region([2,2,1],[4,4,1],'All'); // Upper hall.
  region([2,2,2],[4,4,2],'All'); // Its long gabled roof.
  // Player-placed-path deck on the lower hall's roof (2026-10-30, user: every
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
  // Waterside flume wing: the wheel and both basins (x 0..1) may overhang a lower
  // bank or water on adaptive piles. Everything else, including the ground
  // door, vestibule and entrance, still needs ground or a stackable below.
  const site=(await read('tools/waterside_sites.json')).FisheryWorks;
  if(site.workCells!==null)throw new Error('Fishery has no site water requirement; it uses delivered Water');
  const wing=new Set(site.supports.groundOptionalCells.map(c=>c.join(',')));
  for(const key of wing) {
    const [x,y,z]=key.split(',').map(Number),b=blocks[index([x,y,z])];
    if(z!==0||b.MatterBelow!=='GroundOrStackable'||b.Occupations!=='All'||x>1)
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
  value.BuildingAccessibleSpec={LocalAccess:xyz([3.5,0,.25]),ForceOneFinalAccess:false};
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
    {Coordinates:xyz([5,2,0]),Directions:'Right, Bottom',ReverseRotation:false}
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
