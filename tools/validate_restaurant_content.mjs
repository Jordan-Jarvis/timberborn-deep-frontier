import {readFile,writeFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const b=await read('src/DeepFrontier/Data/Buildings/Food/Restaurant/Restaurant.IronTeeth.blueprint.json');
const layout=(await read('tools/civic-layouts.json')).Restaurant;
const check=(condition,message)=>{if(!condition)throw new Error(message);};
const xyz=c=>[c.X,c.Y,c.Z];
const spec=b.RestaurantSpec;
check(spec.Seats.length===14&&new Set(spec.Seats.map(s=>s.Name)).size===14,'Exactly fourteen distinct native guest slots required');
check(b.EnterableSpec.CapacityFinished===14&&b.WorkplaceSpec.MaxWorkers===4,'Staff and guest capacities must be separate');
for(const old of ['AttractionSpec','GoodConsumingBuildingSpec','WorkplaceSlotManagerSpec','WorkshopWorkerHiderSpec'])
  check(!Object.hasOwn(b,old),`Restaurant retained conflicting prototype component: ${old}`);
check(spec.Foods.length===4&&new Set(spec.Foods).size===4&&!spec.Foods.includes('DiningService'),'The first menu requires four distinct actual foods');
check(b.MechanicalNodeSpec.PowerInput===400&&b.MechanicalNodeSpec.PowerOutput===0,'Restaurant requires 400 hp and produces none');
check(b.ManufactorySpec.ProductionRecipeIds.join()==='FermentedCassava,FermentedSoybean,FermentedMushroom,SweetBerryCake','Restaurant kitchen must retain exact native fermenter recipes and unique cake');
check(spec.OptionalGoods.includes('Coffee')&&!spec.Foods.includes('Coffee'),'Coffee must be optional');
check(spec.DrinkingWater==='Water'&&spec.Stock.find(s=>s.GoodId==='Water').AlwaysStocked&&!spec.OptionalGoods.includes('Water')&&!spec.Foods.includes('Water'),'Water must remain stocked for conditional thirsty-diner service');
// Cake is a native Box good (every good type needs a stockpile for the top-bar tooltip); it stays
// table-only because the restaurant inventory is givable only (RestaurantKitchenInventory).
check(spec.OptionalGoods.includes('SweetBerryCake')&&(await read('src/DeepFrontier/Data/Goods/Good.SweetBerryCake.blueprint.json')).GoodSpec.GoodType==='Box','Cake must be a native Box good served at the tables');
check(xyz(b.BlockObjectSpec.Size).join()===layout.size.join(),'Registration must match exported civic layout');
const [w,d,h]=layout.size;
check(b.BlockObjectSpec.Blocks.length===w*d*h,'Occupation array must cover exact envelope');
const block=c=>b.BlockObjectSpec.Blocks[(c[2]*d+c[1])*w+c[0]];
for(const c of layout.buildableCells) {
  check(block([c[0],c[1],c[2]-1]).Stackable==='BlockObject',`Terrace support missing at ${c}`);
  check(block(c).Occupations!=='All',`Terrace construction space occupied at ${c}`);
}
for(const seat of spec.Seats) {
  check(layout.nodes.some(n=>[n.point[0]+layout.origin[0],n.point[2]+layout.origin[2],n.point[1]+layout.origin[1]].every((v,i)=>Math.abs(v-xyz(seat.ServicePosition)[i])<1e-6)),`Seat service position must belong to explicit graph: ${seat.Name}`);
}
// Table service: each seat's served dish (native Box good model at DishScale
// 0.5, so 0.1125 wide assuming the 0.225 GoodStack box) rests on its table
// cloth, clear of the authored plates and candle of terrace_table() in
// tools/asset-pipeline/civic_isometric_geometry.py. Offsets are seat-local
// native slot frames: X right, Y up, Z towards the table.
const visitors=await read('outputs/reference-studies/Restaurant-visitor-manifest.json');
const table=b.RestaurantTableServiceSpec;
check(table&&table.Dishes.length===spec.Seats.length&&table.Dishes.map(d=>d.Seat).sort().join()===spec.Seats.map(s=>s.Name).sort().join(),'Every guest seat needs exactly one authored table dish (RestaurantTableServiceSpec; see outputs/restaurant-service-compile/civic_building_content-table-dishes.patch)');
const tableHalf=[.325,.265],plates=[[-.17,0],[.17,0]],plateRim=.145,candle=[0,.11],candleRadius=.034,clothTop=.0475,dishHalf=.05625,eps=1e-9;
for(const dish of table.Dishes) {
  const seat=visitors.visitorSeats.find(s=>'#Slot#'+s.id===dish.Seat);
  check(seat,`No authored visitor seat for table dish ${dish.Seat}`);
  const [fx,fy]=seat.facing,[px,py,pz]=seat.position,[tx,ty,tz]=seat.tableCenter;
  const {X:right,Y:up,Z:forward}=dish.Offset;
  check(forward>0&&up>0,`Table dish must be in front of and above its seat: ${dish.Seat}`);
  const lx=px+fx*forward+fy*right-tx,ly=py+fy*forward-fx*right-ty;
  check(Math.abs(pz+up-(tz+clothTop))<1e-6,`Table dish must rest on the cloth: ${dish.Seat}`);
  check(Math.abs(lx)+dishHalf<=tableHalf[0]+eps&&Math.abs(ly)+dishHalf<=tableHalf[1]+eps,`Table dish must stand on its own table: ${dish.Seat}`);
  for(const [cx,cy] of plates)check(Math.abs(lx-cx)>=plateRim+dishHalf-eps||Math.abs(ly-cy)>=plateRim+dishHalf-eps,`Table dish overlaps an authored plate: ${dish.Seat}`);
  check(Math.abs(lx-candle[0])>=candleRadius+dishHalf-eps||Math.abs(ly-candle[1])>=candleRadius+dishHalf-eps,`Table dish overlaps the table candle: ${dish.Seat}`);
}
// Delivery contract in the scripts: the dish physically travels in native
// GoodCarrier hands with a native return reservation, menu stock is held by
// native Inventory reservations restored after load, and the meal is committed
// from the carried order without in-memory claims.
const serviceSource=await readFile(new URL('src/DeepFrontier/Scripts/RestaurantService.cs',root),'utf8');
const restaurantSource=await readFile(new URL('src/DeepFrontier/Scripts/Restaurant.cs',root),'utf8');
for(const token of ['PutGoodsInHands(new CarriedGood(dish,CarriedGoodType.Unavailable))','_reserver.ReserveCapacity(Restaurant.Inventory,dish)','Restaurant.Inventory.TakeExisting(dish)','Restaurant.Inventory.ReserveStock(new GoodAmount(id,1))','public void PostLoadEntity()','Environment/GoodStack/GoodStackModel.blueprint'])
  check(serviceSource.includes(token),'Restaurant table service lost its native delivery contract: '+token);
check(restaurantSource.includes('waiter.HandOverMeal()')&&restaurantSource.includes('RestaurantWaiterWalkExecutor')&&!restaurantSource.includes('Dictionary<BehaviorAgent'),'Meals must be committed from a carried, persisted order without in-memory claims');
// Review 2026-10-21 (outputs/review-2026-10-21/civic-service.json).
// (3) The carried lead dish must emit a native Consumed stock change at commit.
const handOver=serviceSource.slice(serviceSource.indexOf('public List<string> HandOverMeal()'),serviceSource.indexOf('public bool BeginReturn()'));
check(handOver.includes('Restaurant.Inventory.GiveExisting(dish)')&&handOver.indexOf('Restaurant.Inventory.TakeConsumed(dish)')>handOver.indexOf('Restaurant.Inventory.GiveExisting(dish)'),'The served lead dish must be recorded as a native Consumed stock change');
// (2) The native Manufactory alone enables the shared inventory, which needs
// recipes that consume ingredients (Manufactory.NeedsInventory).
check(!/Inventory\.(Enable|Disable)\(\)/.test(restaurantSource),'Restaurant must not enable/disable the Manufactory-owned inventory a second time');
for(const id of b.ManufactorySpec.ProductionRecipeIds) {
  const path=id==='SweetBerryCake'?'src/DeepFrontier/Data/Recipes/Recipe.SweetBerryCake.blueprint.json':`vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Recipes/Recipe.${id}.blueprint.json`;
  check((await read(path)).RecipeSpec.Ingredients.length>0,`Kitchen recipe must consume ingredients so the native Manufactory owns the inventory: ${id}`);
}
// Automatic kitchen: no recipe picker, every recipe cooked as resources allow.
for(const id of b.ManufactorySpec.ProductionRecipeIds) {
  const path=id==='SweetBerryCake'?'src/DeepFrontier/Data/Recipes/Recipe.SweetBerryCake.blueprint.json':`vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Recipes/Recipe.${id}.blueprint.json`;
  const recipe=(await read(path)).RecipeSpec;
  for(const good of [...recipe.Ingredients,...recipe.Products]) {
    const stock=spec.Stock.find(s=>s.GoodId===good.Id);
    check(stock&&stock.Capacity>=good.Amount,`Kitchen inventory must hold every recipe's ${good.Id} (${good.Amount}) at once: ${id}`);
  }
}
const kitchenSource=await readFile(new URL('src/DeepFrontier/Scripts/RestaurantKitchenInventory.cs',root),'utf8');
const stockClass=kitchenSource.slice(kitchenSource.indexOf('class RestaurantKitchenStock'));
check(/_kitchen\.ProductionRecipes\.SelectMany\(r=>r\.Ingredients/.test(stockClass)&&!/CurrentRecipe/.test(stockClass),'Kitchen stock must accept every recipe\'s ingredients, independent of the recipe cooking');
check(/b\.AddDecorator<Restaurant,AutomaticRecipeManufactory>\(\)/.test(restaurantSource),'Restaurant must carry native AutomaticRecipeManufactory (hides the native recipe picker and NoRecipeStatus)');
check(/b\.AddDecorator<Restaurant,RestaurantKitchenChooser>\(\)/.test(restaurantSource)&&/class RestaurantKitchenChooser\b[^{]*IFinishedStateListener/.test(restaurantSource),'Restaurant kitchen chooser missing');
const chooser=restaurantSource.slice(restaurantSource.indexOf('class RestaurantKitchenChooser'),restaurantSource.indexOf('class RestaurantConfigurator'));
// Only Switch sets the recipe, and it restores a set-aside batch's progress and consumed ingredients;
// mid-batch the chooser switches only when the batch's products no longer fit, setting it aside first.
const switchBody=chooser.slice(chooser.indexOf('private void Switch(RecipeSpec recipe)'),chooser.indexOf('internal bool HasIngredients'));
check((chooser.match(/_kitchen\.SetRecipe\(/g)??[]).length===1&&/_kitchen\.SetRecipe\(recipe\)[\s\S]*_setAside\.Remove\(recipe,out var progress\)[\s\S]*SetProgress\(_kitchen,progress\);IngredientsConsumed\(_kitchen\)=true;/.test(switchBody),'Kitchen recipe switches must keep each set-aside batch\'s progress and consumed ingredients');
const tick=chooser.slice(chooser.indexOf('public override void Tick()'),chooser.indexOf('private void Switch('));
check(/if\(_kitchen\.ProductionProgress>0f\) \{\s*\/\/[^\n]*\n\s*if\(_kitchen\.HasUnreservedCapacityForCurrentProducts\(\)\)return;[\s\S]*?_setAside\.Add\(current,_kitchen\.ProductionProgress\);\s*Switch\(/.test(tick),'Mid-batch the kitchen may switch only after setting the stalled batch aside');
check((restaurantSource.match(/\.SetRecipe\(/g)??[]).length===(chooser.match(/\.SetRecipe\(/g)??[]).length,'Only the kitchen chooser may set the Restaurant recipe');
const csv=await readFile(new URL('src/DeepFrontier/Data/Localizations/enUS.csv',root),'utf8');
const dining=await read('src/DeepFrontier/Data/Needs/Need.Beaver.RestaurantDining.blueprint.json');
check(dining.NeedSpec.DisplayNameLocKey==='DeepFrontier.Need.FineDining'&&csv.includes('\nDeepFrontier.Need.FineDining,Fine dining,'),'The RestaurantDining need must be named Fine dining');
// Partial meals: any main food opens the dining room; only a full meal adds Fine Dining.
check(/HasMeal => Spec\.Foods\.Any\(/.test(restaurantSource)&&/if\(Spec\.Foods\.All\(served\.Contains\)\)needs\.ApplyEffect\(new InstantEffect\(FineDiningNeed/.test(restaurantSource),'Restaurant must serve partial meals and grant Fine Dining only for a full meal');
// (1) A restaurant's own staff are neither offered nor kept in its diner seats.
const visitSource=restaurantSource.slice(restaurantSource.indexOf('class RestaurantVisitBehavior'),restaurantSource.indexOf('class RestaurantWorkBehavior'));
check(/ActionPosition[\s\S]*?_restaurant\.IsOwnStaff\(needManager\)[\s\S]*?Decide[\s\S]*?_restaurant\.IsOwnStaff\(agent\)/.test(visitSource),'Restaurant staff must be excluded from their own diner seats');
const collection=await read('src/DeepFrontier/Data/NeedCollections/NeedCollection.IronTeeth.blueprint.json');
check(Object.keys(collection.NeedCollectionSpec).join()==='Needs#append','Dining must append to native needs rather than replace them');
// The civic needs come first; the rocket program then appends its mission
// legacy needs (tools/rocket_program_content.mjs), radiation adds
// Irradiation (tools/radiation_content.mjs) and the Technical School its
// study needs (tools/workforce_risk_content.mjs).
check(collection.NeedCollectionSpec['Needs#append'].join()==='RestaurantDining,SweetBerryCake,PublicHealthcare,NeighborhoodGroceries,OrbitalObservatoryLegacy,RecoveryProbeLegacy,LongRangeBeaconLegacy,Irradiation,StudyMetallurgy,StudyNuclear,StudyFlight','Unexpected combined civic and rocket legacy needs');
check(!b.BuildingWalkwaySpec&&b.PlatformDeckSpec.Doors.length===4,'Restaurant must use native player-built paths and four interior doors');
check(!b.BlockObjectSpec.Blocks.some(b=>b.Occupations.split(', ').includes('Path')),'Building must not reserve player path occupation');
const result={status:'restaurant-blueprint-static-checks-passed',registration:layout.size,guestSeats:14,staff:4,foods:spec.Foods,optionalGoods:spec.OptionalGoods,kitchenRecipes:b.ManufactorySpec.ProductionRecipeIds,powerDemandHp:400,powerOutputHp:0,clearTerraceCells:layout.buildableCells.length,adaptiveOpenings:b.PlatformDeckSpec.Openings.length,tableDishes:table.Dishes.length,tableService:'kitchen pass -> native GoodCarrier hands -> table; native stock/capacity reservations',reviewFixes:['staff excluded from own diner seats','inventory enabled once by native Manufactory','lead dish recorded as native Consumed at commit'],limits:'Static authoring contracts only; native routing, actual service and persistence require game tests.'};
await writeFile(new URL('outputs/civic-integration/restaurant-content-checks.json',root),JSON.stringify(result,null,2)+'\n');
console.log(JSON.stringify(result,null,2));
