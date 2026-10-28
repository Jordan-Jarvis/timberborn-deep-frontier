import {readFile,writeFile,mkdir,copyFile} from 'node:fs/promises';
import {existsSync} from 'node:fs';
import {structureBlocks,authoredColliders,roomPowerFaces} from './grid_structure.mjs';
import {applyNativeBuildingAssembly} from './native_building_content.mjs';
import {wallRoomPowerFaces} from './civic_wall_faces.mjs';
import {applyVanillaSmoke,sceneSmokeRegistration} from './vanilla_smoke.mjs';
const root=new URL('../',import.meta.url);
const data=new URL('src/DeepFrontier/Data/',root);
const vanilla=new URL('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/',root);
const read=async path=>JSON.parse(await readFile(path,'utf8'));
const xyz=([X,Y,Z])=>({X,Y,Z});
const layout=(await read(new URL('tools/civic-layouts.json',root))).Restaurant;
const menu=(await read(new URL('tools/frontier_progression.json',root))).restaurant;

// Vanilla convention (138 of 139 shipped buildings): the native Entrance is
// the path cell in front of the door, and its doorstep is the door cell.
// Timberborn's DynamicPathModel only draws a path's connection stub toward an
// entrance flag on that path cell, so an Entrance on the door cell itself
// leaves the path visually unconnected. Use the ground door's exterior cell.
function nativeEntrance(layout,blocks,index){
  const door=layout.doorLinks.find(d=>d.Interior.join()===layout.entrance.join());
  if(!door)throw new Error('No door link leaves the layout entrance '+layout.entrance);
  const [a,b]=[door.Interior,door.Exterior];
  if(a[2]!==b[2]||Math.abs(a[0]-b[0])+Math.abs(a[1]-b[1])!==1)throw new Error('Entrance door link is not one horizontal step: '+a+' -> '+b);
  const [w,d,h]=layout.size;
  const inside=b[0]>=0&&b[1]>=0&&b[2]>=0&&b[0]<w&&b[1]<d&&b[2]<h;
  if(inside&&blocks[index(b)].Occupations!=='None')throw new Error('Entrance path cell is occupied: '+b);
  return b;
}

// A served dish rests on the cloth beside the diner's authored plate. The decor
// is terrace_table() in tools/asset-pipeline/civic_isometric_geometry.py: plank
// 0.65 x 0.53 (X x Y), cloth top 0.0475 above tableCenter, plates at +/-0.17 X
// (rim 0.145) and a candle at +0.11 Y. X-facing diners have their plate straight
// ahead, so the dish stands on the cloth strip to their right; Y-facing diners
// face the plate-free strip between the plates and the table edge.
// validate_restaurant_content.mjs checks the clearances against that decor.
export function restaurantDishOffset(seat){
  const [fx,fy]=seat.facing,[px,py,pz]=seat.position,[tx,ty,tz]=seat.tableCenter;
  if(!(Math.abs(fx)+Math.abs(fy)===1&&fx*fy===0))throw new Error('Restaurant seat must face one native axis: '+seat.id);
  const [dx,dy]=fx!==0?[tx-fx*.17-px,ty-fx*.206-py]:[tx-px,ty-fy*.206-py];
  return xyz([dx*fy-dy*fx,tz+.0475-pz,dx*fx+dy*fy]);
}

export async function applyRestaurant(value) {
  for(const id of ['SimpleManufactoryBehaviorsSpec','WorkshopAnimationControllerSpec','WorkplaceIlluminatorSpec','WorkplaceSlotManagerSpec','WorkshopWorkerHiderSpec'])delete value[id];
  value.ManufactorySpec={ProductionRecipeIds:menu.kitchenRecipes};
  value.WorkshopSpec={};
  const [w,d,h]=layout.size,index=([x,y,z])=>(z*d+y)*w+x;
  const blocks=structureBlocks(layout.structure,layout.size);
  const interior=new Set(layout.interiorCells.map(c=>c.join(',')));
  for(const n of layout.nodes) {
    if(interior.has(n.cell.join(',')))continue;
    const [x,y,z]=n.cell;
    if(blocks[index(n.cell)].Occupations==='All')throw new Error('Suggested player path intersects fixed furniture or a room: '+n.cell);
    if(z>0) {
      const support=blocks[index([x,y,z-1])];
      if(support.Occupations==='None')throw new Error(`Missing restaurant slab: ${n.cell}`);
      support.Stackable='BlockObject';
    }
  }
  for(const cell of layout.buildableCells)blocks[index([cell[0],cell[1],cell[2]-1])].Stackable='BlockObject';
  value.BlockObjectSpec={Size:xyz(layout.size),Blocks:blocks,Entrance:{HasEntrance:true,Coordinates:xyz(nativeEntrance(layout,blocks,index))},BaseZ:0,Overridable:false,Flippable:true};
  value.BuildingAccessibleSpec={LocalAccess:xyz([1.5,0,1]),ForceOneFinalAccess:false};
  value.EnterableSpec={OperatingState:'Finished',LimitedCapacityFinished:true,CapacityFinished:menu.seats,LimitedCapacityUnfinished:false,CapacityUnfinished:0};
  value.FixedSlotManagerSpec={};
  value.WorkplaceSpec={MaxWorkers:menu.workers,DefaultWorkers:menu.workers,DefaultWorkerType:'Beaver',DisallowOtherWorkerTypes:true,WorkerTypeUnlockCosts:[]};
  value.ConstructionSiteProgressVisualizerSpec={ProgressThresholds:[]};
  const colliders=authoredColliders(await read(new URL('outputs/reference-studies/Restaurant-structure.json',root)),layout.structure,layout.baseZ);
  value.Children['#Finished'].CollidersSpec=colliders;
  value.Children['#Unfinished']={Children:{ConstructionStage0:{TimbermeshSpec:{Model:'Buildings/Food/Restaurant/Restaurant.IronTeeth.ConstructionStage0.Model'},CollidersSpec:colliders}}};
  const edges=layout.edges.filter(([a,b])=>interior.has(a.join(','))&&interior.has(b.join(','))).map(([a,b])=>({Cost:1,Group:{UseGroup:a[2]!==b[2],GroupName:a[2]!==b[2]?'DeepFrontierInterior':''},IsPath:true,AddedEdges:[{Start:xyz(a),End:xyz(b),IsTwoWay:true}]}));
  edges.push({Cost:1,Group:{UseGroup:false,GroupName:''},IsPath:true,AddedEdges:layout.doorLinks.map(d=>({Start:xyz(d.Interior),End:xyz(d.Exterior),IsTwoWay:true}))});
  value.BlockObjectNavMeshSettingsSpec={NoAutoWalls:false,GenerateFloorsOnStackable:true,EdgeGroups:edges,UnblockedCoordinates:[],BlockedEdges:[]};
  delete value.BuildingWalkwaySpec;
  value.PlatformDeckSpec=await read(new URL('outputs/civic-integration/Restaurant-platform-deck.json',root));
  value.TransputProviderSpec={IgnoreRotation:false,Transputs:await wallRoomPowerFaces('Restaurant',layout.structure,layout.size)};
  const serviceCells=[[0,1,4],[0,1,4],[4,1,4],[4,1,4],[0,1,2],[0,1,2],[2,1,2],[2,1,2],[4,1,2],[4,1,2],[5,2,2],[5,2,2],[5,4,2],[5,4,2]];
  const point=cell=>{
    const n=layout.nodes.find(n=>n.cell.every((v,i)=>v===cell[i]));
    if(!n)throw new Error(`No authored restaurant service cell: ${cell}`);
    return xyz([n.point[0]+layout.origin[0],n.point[2]+layout.origin[2],n.point[1]+layout.origin[1]]);
  };
  const stock=new Set([...menu.mealFoods,...menu.optionalServedGoods,menu.drinkingWater]);
  for(const id of menu.kitchenRecipes) {
    const recipe=(await read(new URL(`Recipes/Recipe.${id}.blueprint.json`,id==='SweetBerryCake'?data:vanilla))).RecipeSpec;
    for(const good of [...recipe.Ingredients,...recipe.Products])stock.add(good.Id);
  }
  // Native need behaviors send a beaver to the restaurant for any need a served
  // good satisfies, not only hunger: each served good's own consumption effects
  // (fermented foods, cake, coffee, water for thirst), at their points per
  // service time. Hunger keeps the main-food rate (4 foods x 0.3 per 0.25 h).
  const servedNeeds=new Map();
  for(const id of [...menu.mealFoods,...menu.optionalServedGoods,menu.drinkingWater]) {
    // Deep Frontier's own goods (FreshFish, SweetBerryCake) are authored in Data; the rest are vanilla.
    const path=`Goods/Good.${id}.blueprint.json`;
    const good=(await read(new URL(path,existsSync(new URL(path,data))?data:vanilla))).GoodSpec;
    for(const {NeedId,Points} of good.ConsumptionEffects)if(NeedId!=='Hunger')servedNeeds.set(NeedId,(servedNeeds.get(NeedId)??0)+Points);
  }
  value.RestaurantSpec={Foods:menu.mealFoods,OptionalGoods:menu.optionalServedGoods,DrinkingWater:menu.drinkingWater,MealsCapacity:32,ServiceHours:.25,EatingHours:.5,
    Stock:[...stock].map(GoodId=>({GoodId,Capacity:32,AlwaysStocked:menu.mealFoods.includes(GoodId)||menu.optionalServedGoods.includes(GoodId)||GoodId===menu.drinkingWater})),
    KitchenPosition:point([2,2,0]),
    Seats:serviceCells.map((cell,i)=>({Name:`#Slot#Seat${i}`,ServicePosition:point(cell)})),StaffIdlePosition:xyz([1.5,0,1]),
    VisitEffects:[{NeedId:'RestaurantDining',PointsPerHour:1,SatisfyToMaxValue:false},
      {NeedId:'Hunger',PointsPerHour:4.8,SatisfyToMaxValue:false},
      ...[...servedNeeds].map(([NeedId,points])=>({NeedId,PointsPerHour:points/.25,SatisfyToMaxValue:false}))]};
  // Table service: where a served dish rests for each guest seat, in that
  // seat's native slot frame (X right, Y up, Z towards the table).
  const visitors=await read(new URL('outputs/reference-studies/Restaurant-visitor-manifest.json',root));
  value.RestaurantTableServiceSpec={Dishes:value.RestaurantSpec.Seats.map(({Name})=>{
    const seat=visitors.visitorSeats.find(s=>'#Slot#'+s.id===Name);
    if(!seat)throw new Error('No authored visitor seat for '+Name);
    return {Seat:Name,Offset:restaurantDishOffset(seat)};
  })};
  // Kitchen and hearth smoke at both chimneys while the kitchen works
  // (WorkshopParticleController; smog lists the Restaurant as a polluter).
  applyVanillaSmoke(value,await sceneSmokeRegistration('civic-integration','Restaurant',layout),'Restaurant');
  await applyNativeBuildingAssembly(value,'Restaurant',layout.origin,{goodId:'Water',flowNodes:[],wheelNodes:[]});
  const folder=new URL('Buildings/Food/Restaurant/',data);
  for(const file of ['Restaurant.IronTeeth.Model.timbermesh','Restaurant.IronTeeth.ConstructionStage0.Model.timbermesh'])
    await copyFile(new URL(`outputs/civic-integration/Data/Buildings/Food/Restaurant/${file}`,root),new URL(file,folder));
}

// Restaurant rows; create_frontier_expansion_content.mjs writes them with the other rows.
export const RESTAURANT_LOCALIZATION=[
  // RestaurantDining need, granted only for a full meal (Restaurant.Serve).
  ['DeepFrontier.Need.FineDining','Fine dining'],
];

export async function authorRestaurantNeed() {
  const need=await read(new URL('Needs/Need.Beaver.RooftopTerrace.blueprint.json',vanilla));
  Object.assign(need.NeedSpec,{Id:'RestaurantDining',Order:35,DailyDelta:-.25,DisplayNameLocKey:'DeepFrontier.Need.FineDining',FavorableWellbeing:2});
  const nativeCollection=await read(new URL('NeedCollections/NeedCollection.IronTeeth.blueprint.json',vanilla));
  if(nativeCollection.NeedCollectionSpec.Needs.includes('RestaurantDining'))throw new Error('RestaurantDining is already a native need');
  const dessert=await read(new URL('Needs/Need.Beaver.FermentedMushroom.blueprint.json',vanilla));
  Object.assign(dessert.NeedSpec,{Id:'SweetBerryCake',BackwardCompatibleIds:[],Order:45,DisplayNameLocKey:'Good.SweetBerryCake.DisplayName',FavorableWellbeing:menu.sweetBerryCake.wellbeing});
  const collection={NeedCollectionSpec:{'Needs#append':['RestaurantDining','SweetBerryCake']}};
  for(const [path,value] of [['Needs/Need.Beaver.RestaurantDining.blueprint.json',need],['Needs/Need.Beaver.SweetBerryCake.blueprint.json',dessert],['NeedCollections/NeedCollection.IronTeeth.blueprint.json',collection]]) {
    await mkdir(new URL(path.substring(0,path.lastIndexOf('/')+1),data),{recursive:true});
    await writeFile(new URL(path,data),JSON.stringify(value,null,2)+'\n');
  }
  // Native flowers normally belong to the Folktails palette. Register their
  // original materials explicitly for these Iron Teeth ornamental planters.
  await writeFile(new URL('MaterialCollections/MaterialCollection.DeepFrontierCivic.blueprint.json',data),JSON.stringify({MaterialCollectionSpec:{CollectionId:'IronTeeth',Materials:[
    'Materials/UberAtlas/Materials/Folktails/BaseWood_Brown.Folktails',
    'NaturalResources/Bushes/Dandelion/Materials/Dandelion',
    'NaturalResources/Crops/Sunflower/Materials/Sunflower',
    'Materials/Goods/Water'
  ]}},null,2)+'\n');
}
