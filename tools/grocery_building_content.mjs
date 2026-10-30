import {readFile,writeFile,copyFile} from 'node:fs/promises';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {lategameBlocks,lategameColliders,wallTransputs} from './lategame_building_content.mjs';
import {solidPowerFaces} from './power_faces.mjs';
import {applyVanillaSmoke} from './vanilla_smoke.mjs';
import {buildingCost,scaledPower} from './lategame_costs.mjs';
const root=new URL('../',import.meta.url);
const data=new URL('src/DeepFrontier/Data/',root);
const vanilla=new URL('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/',root);
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});
const shop=(await read(new URL('tools/frontier_progression.json',root))).groceryStore;

// The approved Grocery Market hall (grocery_market_geometry.py). Its grid
// registration comes from the authored parts (register_grocery_market.py):
// solid cells, the native Entrance path cell in front of the main door, and
// the access contract. The balcony deck takes player paths and the stair bay
// takes native stairs; the market hall itself is not walked through.
export async function applyGroceryStore(value) {
  for(const key of ['ManufactorySpec','WorkshopSpec','SimpleManufactoryBehaviorsSpec',
    'WorkshopAnimationControllerSpec','WorkplaceIlluminatorSpec','WorkplaceSlotManagerSpec',
    'WorkshopWorkerHiderSpec','StatusHidingEnterableSpec','BuildingWalkwaySpec','BlockObjectNavMeshSettingsSpec'])delete value[key];
  const reg=await read(new URL('outputs/lategame-studies/GroceryMarket-registration.json',root));
  const [w,d]=reg.footprint,h=reg.height,size=[w,d,h],index=([x,y,z])=>(z*d+y)*w+x;
  const blocks=lategameBlocks(reg);
  const door=reg.doors.find(x=>x.id==='MainDoor');
  if(!door||door.position[2]!==0||door.faceOffset>.25)throw new Error('Grocery main door is not a registered ground door');
  if(blocks[index(door.doorstep)].Occupations!=='All')throw new Error('Grocery doorstep is not a building cell');
  if(blocks[index(door.entrance)].Occupations!=='None')throw new Error('Grocery entrance path cell is occupied');
  // Balcony deck: cells on its whole-tile area at the deck layer are free for
  // player paths; the deck structure below carries them.
  const balcony=reg.access.balcony,[bx0,by0,bx1,by1]=balcony.bounds,layer=balcony.layer;
  if([bx0,by0,bx1,by1].some(v=>!Number.isInteger(v)))throw new Error('Grocery balcony is not on whole tiles: '+balcony.bounds);
  for(let y=by0;y<by1;y++)for(let x=bx0;x<bx1;x++) {
    blocks[index([x,y,layer])].Occupations='None';
    blocks[index([x,y,layer])].MatterBelow='Any';
    const support=blocks[index([x,y,layer-1])];
    if(support.Occupations!=='All')throw new Error(`Grocery balcony lacks deck structure under ${[x,y,layer]}`);
    support.Stackable='BlockObject';
  }
  value.BlockObjectSpec={Size:xyz(size),Blocks:blocks,Entrance:{HasEntrance:true,Coordinates:xyz(door.entrance)},BaseZ:0,Overridable:false,Flippable:true};
  const [dx,dy,dz]=door.position;
  value.BuildingAccessibleSpec={LocalAccess:xyz([dx,dz,dy]),ForceOneFinalAccess:false};
  value.EnterableSpec={OperatingState:'Finished',LimitedCapacityFinished:false,CapacityFinished:0,LimitedCapacityUnfinished:false,CapacityUnfinished:0};
  value.WorkplaceSpec={MaxWorkers:shop.workers,DefaultWorkers:shop.workers,DefaultWorkerType:'Beaver',DisallowOtherWorkerTypes:true,WorkerTypeUnlockCosts:[]};
  Object.assign(value.BuildingSpec,{ScienceCost:shop.scienceUnlock,BuildingCost:buildingCost('GroceryStore',shop.buildingCost,shop.scienceUnlock),SelectionSoundName:'Warehouse',LoopingSoundName:''});
  value.MechanicalNodeSpec={PowerInput:scaledPower('GroceryStore',shop.powerDemandHp,shop.scienceUnlock),PowerOutput:0,IsShaft:false};
  value.TransputProviderSpec={IgnoreRotation:false,Transputs:wallTransputs(solidPowerFaces(blocks,size,{exclude:[door.entrance,door.doorstep]}),reg)};
  value.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
  const model='Buildings/Food/GroceryStore/GroceryStore.IronTeeth.Model';
  const stage='Buildings/Food/GroceryStore/GroceryStore.IronTeeth.ConstructionStage0.Model';
  const colliders=lategameColliders(blocks,size);
  value.Children['#Finished'].TimbermeshSpec={Model:model};
  value.Children['#Finished'].CollidersSpec=colliders;
  value.Children['#Unfinished']={Children:{ConstructionStage0:{TimbermeshSpec:{Model:stage},CollidersSpec:colliders}}};
  value.EnterableIlluminatorSpec={};
  value.RangedEffectBuildingSpec={EffectRadius:shop.areaRadius};
  // The clerk works at the centre of the native Entrance path cell in front of
  // the main door, beside the awning counter. The hall has no interior
  // navigation; the entrance cell is the one cell the path network must reach
  // for the shop to be accessible at all (GroceryClerkBehavior walks there and
  // GroceryStore.AttendingStaff counts clerks within 0.3 of it).
  value.GroceryStoreSpec={Foods:shop.stock,CapacityPerFood:shop.capacityPerFood,MinimumStockedFoodTypes:shop.minimumStockedFoodTypes,
    ClerkWorkPosition:xyz([door.entrance[0]+.5,door.entrance[2],door.entrance[1]+.5]),
    NeighborhoodEffect:{NeedId:'NeighborhoodGroceries',PointsPerHour:shop.areaPointsPerHour,SatisfyToMaxValue:false}};
  // The stands show the actual stock: GroceryStock.<Food>.<1..3> model nodes,
  // switched by GroceryStockDisplay.cs from the native inventory.
  value.GroceryStockDisplaySpec={Stages:3};
  // Chimney steam while the shop is staffed (EnterableParticleController).
  applyVanillaSmoke(value,reg,'GroceryStore');
  await applyNativeBuildingAssembly(value,'GroceryMarket',[0,0,0],{goodId:'Water',flowNodes:[],wheelNodes:[]});
  for(const resource of [model,stage])
    await copyFile(new URL(`outputs/lategame-integration/Data/${resource}.timbermesh`,root),new URL(`${resource}.timbermesh`,data));
}
export async function authorGroceryNeed() {
  const need=await read(new URL('Needs/Need.Beaver.RooftopTerrace.blueprint.json',vanilla));
  Object.assign(need.NeedSpec,{Id:'NeighborhoodGroceries',BackwardCompatibleIds:[],Order:37,DailyDelta:-.5,
    DisplayNameLocKey:'Need.NeighborhoodGroceries.DisplayName',FavorableWellbeing:shop.areaWellbeingPoints});
  await writeFile(new URL('Needs/Need.Beaver.NeighborhoodGroceries.blueprint.json',data),JSON.stringify(need,null,2)+'\n');
  const path=new URL('NeedCollections/NeedCollection.IronTeeth.blueprint.json',data),collection=await read(path);
  if(collection.NeedCollectionSpec['Needs#append'].includes('NeighborhoodGroceries'))throw new Error('NeighborhoodGroceries already authored');
  collection.NeedCollectionSpec['Needs#append'].push('NeighborhoodGroceries');
  await writeFile(path,JSON.stringify(collection,null,2)+'\n');
}
