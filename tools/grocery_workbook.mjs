import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);
const read=async path=>JSON.parse(await readFile(new URL(path,root),'utf8'));
const b=await read('src/DeepFrontier/Data/Buildings/Food/GroceryStore/GroceryStore.IronTeeth.blueprint.json');
const packaging=await read('src/DeepFrontier/Data/Buildings/Food/FoodPackagingWorks/FoodPackagingWorks.IronTeeth.blueprint.json');
const p=(await read('tools/frontier_progression.json')).groceryStore;
const name=id=>id.replace(/([a-z])([A-Z])/g,'$1 $2');
const cost=b.BuildingSpec.BuildingCost.map(g=>`${g.Amount} ${name(g.Id)}`).join('; ');
const foods=p.stock.map(name).join('; ');
const source='tools/frontier_progression.json; src/DeepFrontier/Data/Buildings/Food/GroceryStore; src/DeepFrontier/Scripts/GroceryStore.cs; docs/transport-adapters.md';
const size=b.BlockObjectSpec.Size;
export const groceryBuildingUpdates=new Map([['B009',{
  'Infobox':'Native multi-food inventory and workplace',
  'Width':size.X,'Length':size.Y,'Footprint':`${size.X}x${size.Y}`,'Footprint tiles':size.X*size.Y,'Height':size.Z,
  'Workers':b.WorkplaceSpec.MaxWorkers,'Power demand (hp)':b.MechanicalNodeSpec.PowerInput,
  'Power output (hp)':b.MechanicalNodeSpec.PowerOutput,'Power role':'Consumer',
  'Science unlock':b.BuildingSpec.ScienceCost,'Bot unlock':'Beaver clerks only','Build materials':cost,
  // The market hall has no built-in walkway (player paths; GroceryStockDisplaySpec shows stock).
  'Flags':`${p.stock.length*p.capacityPerFood} food capacity; ${b.GroceryStockDisplaySpec.Stages.length} stock display stages; native player-built paths`,
  'Recipe names':'None; stocks and serves existing foods','Source':source,'Data status':p.requirementStatus,
  'Role':'One place for six native food types; staffed neighborhood wellbeing',
  'Stackable':'Clear gallery and roof cells','Stacking rule':'Native support and collision; roof construction at layer 6; no layer cap',
  'Conveyor-only solids':'No','Pipe ports':'None','Power mode':'Grid',
  'Unlock prerequisites':`${p.scienceUnlock} science; concrete, planks, metal blocks and gears; food delivery`,
  'Inputs':foods,'Outputs':'Native food effects; Neighborhood Groceries wellbeing','Waste / side effect':'None',
  'Placement':'Supported surface; connected original doors at layers 0/2/4/6',
  'Player cue':'Stock panel shows assortment, clerks and neighborhood service',
  'Status':p.requirementStatus,
  'Notes':`${p.capacityPerFood} of each food. Radius ${p.areaRadius}; +${p.areaWellbeingPoints} wellbeing cap. At least one attending clerk, power and ${p.minimumStockedFoodTypes} stocked types activate the area benefit. Shoppers can eat stored food while unpowered or paused. ${p.balanceStatus}`
}]]);
export const groceryItemUpdates=new Map([
  ['I006',{'Consumed by':'Native food consumption; Grocery Store shoppers',
    'Primary uses':'Direct eating; stocked grocery assortment','Notes':'Food Packaging Works makes canned fish. The grocery stocks it; the Fishery does not can it.'}],
  ['I010',{'Source / recipe':'Food Packaging Works','Consumed by':'Native food consumption; Grocery Store shoppers',
    'Primary uses':'Direct eating; stocked grocery assortment','Science value':0,
    'Notes':'Existing general preserved food. Not a restaurant service token or a restaurant menu dish.'}]
]);
for(const [row,id] of [['I006','CannedFish'],['I010','PackagedFood']]) {
  const path=`src/DeepFrontier/Data/Goods/Good.${id}.blueprint.json`;
  const good=(await read(path)).GoodSpec;
  Object.assign(groceryItemUpdates.get(row),{'Type':good.GoodType,'Weight':good.Weight,'Source':path,
    'Satisfies / effects':good.ConsumptionEffects.map(e=>`${e.NeedId}: +${e.Points}`).join('; '),
    'Data status':'Exact authored food and packaging recipe; native factory production pending','Science value':0,'Perishable':'No'});
}
groceryItemUpdates.get('I006')['Consumed by']='Native food consumption; Grocery Store shoppers; Food Packaging Works';
groceryItemUpdates.get('I006')['Primary uses']='Direct eating; Packaged Food ingredient; stocked grocery assortment';
const amounts=goods=>goods.map(g=>`${g.Amount} ${name(g.Id)}`).join('; ');
export const grocerySupplyRecipes=[];
for(const [row,id] of [['R006','CannedFish'],['PackagedFood','PackagedFood']]) {
  const r=(await read(`src/DeepFrontier/Data/Recipes/Recipe.${id}.blueprint.json`)).RecipeSpec;
  grocerySupplyRecipes.push([row,'Food Packaging Works','Iron Teeth',name(id),amounts(r.Ingredients),amounts(r.Products),
    r.CycleDurationInHours,packaging.MechanicalNodeSpec.PowerInput,packaging.MechanicalNodeSpec.PowerOutput,'Consumer',packaging.WorkplaceSpec.MaxWorkers,
    'None',`${r.CyclesCapacity} recipe cycles`,`src/DeepFrontier/Data/Recipes/Recipe.${id}.blueprint.json; FoodPackagingWorks.IronTeeth.blueprint.json`,
    JSON.stringify(r.Ingredients),JSON.stringify(r.Products),r.Products[0].Amount,r.CycleDurationInHours*60,
    r.Ingredients.map(g=>name(g.Id)).join('; '),r.Ingredients.map(g=>g.Amount).join('; '),'None','3. Industrial city',
    'Direct food consumption and grocery supply','Exact authored recipe; native factory production pending']);
}
export const groceryProgression=['G022','Iron Teeth','3. Industrial city','Centralize neighborhood groceries',
  p.scienceUnlock,'Grocery Store; native food producers; Food Packaging Works',cost,
  `${p.powerDemandHp} hp; ${p.workers} clerks; at least ${p.minimumStockedFoodTypes} stocked food types`,
  'Residents travel to several food warehouses','Six foods in one store; staffed neighborhood wellbeing',
  'Makes existing food production and local delivery more useful','Stock panel explains missing assortment, power or clerks',
  'Industrial city','Native science and construction materials',p.requirementStatus,p.balanceStatus];
export const groceryTransport=['T019','Iron Teeth','Grocery stocking and shopping','Native hauling, intake-only belts and shopper reservations',
  foods,null,p.powerDemandHp,'Ground entrance; native power shaft',
  'Connected doors at layers 0/2/4/6',`${p.areaRadius}-cell neighborhood radius`,
  'Consolidate local access to food variety',`${p.capacityPerFood} per food; ${p.stock.length*p.capacityPerFood} stored units total; hauling rate depends on travel and workers`,
  'Belt intake, capacity, power and saved queue passed 73/75','One native inventory; shoppers can eat; outgoing belts cannot withdraw',
  'Supported clear deck and roof cells; no layer cap',source,p.requirementStatus];
export const grocerySource=['Grocery reference and native shopping',source,
  'Exact dimensions, construction costs, hp, science, staff, inventory and neighborhood rules','2026-10-20',
  'Approved isometric model preserved. Native inventory owns stock, reservations, hauling and save data.',
  'DeepFrontier',p.requirementStatus,'11x9x9; 100 hp input; zero output; 6000 science; 600 food capacity'];
