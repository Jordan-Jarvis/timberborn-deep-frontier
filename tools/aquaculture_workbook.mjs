import {readFile} from 'node:fs/promises';
const root=new URL('../',import.meta.url);
const read=async p=>JSON.parse(await readFile(new URL(p,root),'utf8'));
const name=id=>id.replace(/([a-z])([A-Z])/g,'$1 $2');
const amounts=goods=>goods.map(g=>`${g.Amount} ${name(g.Id)}`).join('; ');
export const aquaculture=await read('tools/aquaculture.json');
const fishery=await read('src/DeepFrontier/Data/Buildings/Food/FisheryWorks/FisheryWorks.IronTeeth.blueprint.json');
const hatchery=await read('src/DeepFrontier/Data/Buildings/Food/FishHatchery/FishHatchery.IronTeeth.blueprint.json');
const flag=await read('vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Buildings/Food/GathererFlag/GathererFlag.IronTeeth.blueprint.json');
const source='tools/aquaculture.json; src/DeepFrontier/Data/Buildings/Food; src/DeepFrontier/Data/Recipes; docs/transport-adapters.md';
const pipePorts=b=>b.BuildingPipeTargetPortsSpec.Ports.map(p=>
  `(${p.Coordinates.X},${p.Coordinates.Y},${p.Coordinates.Z}) ${p.Directions} ${p.State}`).join('; ');
const hatcheryStatus=aquaculture.hatchery.status;
const fisheryStatus=aquaculture.fishery.status;
const flagStatus='Catch/delivery/save/reload and water/job interruptions passed through build 51; build 57 bootstrapped breeding and Fishery production from zero fish stock';
const juvenile=(await read('src/DeepFrontier/Data/Recipes/Recipe.JuvenileFish.blueprint.json')).RecipeSpec;
const fish=(await read('src/DeepFrontier/Data/Recipes/Recipe.FreshFish.blueprint.json')).RecipeSpec;
const oil=(await read('src/DeepFrontier/Data/Recipes/Recipe.FishOil.blueprint.json')).RecipeSpec;

function buildingFields(b,status) {
  const s=b.BlockObjectSpec.Size;
  return {'Width':s.X,'Length':s.Y,'Footprint':`${s.X}x${s.Y}`,'Footprint tiles':s.X*s.Y,'Height':s.Z,
    'Workers':b.WorkplaceSpec.MaxWorkers,'Power demand (hp)':b.MechanicalNodeSpec.PowerInput,'Power output (hp)':b.MechanicalNodeSpec.PowerOutput,
    'Science unlock':b.BuildingSpec.ScienceCost,'Bot unlock':b.WorkplaceSpec.WorkerTypeUnlockCosts.map(v=>`${v.WorkerType}: ${v.ScienceCost}`).join('; '),
    'Build materials':amounts(b.BuildingSpec.BuildingCost),'Recipe names':b.ManufactorySpec.ProductionRecipeIds.join('; '),
    'Source':source,'Data status':status,'Status':status};
}
export const aquacultureBuildingUpdates=new Map([
  ['B005',{'Status':'Design only; not authored','Data status':'Proposed fish pond; no active building or recipe','Notes':'Shore fishing provides the implemented starter fish supply.'}],
  ['B006',{...buildingFields(hatchery,hatcheryStatus),'Infobox':'Manufactory','Power role':'Consumer','Power mode':'Grid',
    'Flags':'Submerged lower layer; bank-level dock; 31 route cells; 20 adaptive rails; native header tank',
    'Stackable':'Clear side-dock tile','Stacking rule':'Native support and collision on clear dock; no artificial layer cap','Conveyor-only solids':'No','Pipe ports':pipePorts(hatchery),
    'Unlock prerequisites':'600 science; planks, gears and metal blocks; gatherer fish and native algae',
    'Inputs':amounts(juvenile.Ingredients),'Outputs':amounts(juvenile.Products),'Placement':`Front row on ground/support; real clean water below rear nursery cell (${aquaculture.hatchery.waterCell.join(',')}); BaseZ=1`,
    'Player cue':'A few shore-caught fish seed repeatable breeding','Notes':'Native pool depth rule: stops at <=0.15 tile and restarts above 0.25; badwater blocks above 5.5%, clears at <=4.5%. Header tank shows 0–60 delivered Water independently of world water. The 8x8x5 height includes one submerged layer. Closed workroom, open nursery pens and a clear side-dock construction tile.'}]
]);
const s=fishery.BlockObjectSpec.Size;
export const aquacultureBuildingAdds=[
  ['FisheryWorks','Fishery Works','Manufactory','Food; Deep Frontier','Iron Teeth','Yes','Build menu',s.X,s.Y,`${s.X}x${s.Y}`,s.X*s.Y,s.Z,fishery.WorkplaceSpec.MaxWorkers,fishery.MechanicalNodeSpec.PowerInput,0,'Consumer',fishery.BuildingSpec.ScienceCost,
    fishery.WorkplaceSpec.WorkerTypeUnlockCosts.map(v=>`${v.WorkerType}: ${v.ScienceCost}`).join('; '),amounts(fishery.BuildingSpec.BuildingCost),
    `Sparse occupation; player-path gallery and terrace decks with ${fishery.PlatformDeckSpec.Doors.length} deck doors; ${fishery.PlatformDeckSpec.Openings.length} adaptive rails; six water surfaces`,fishery.ManufactorySpec.ProductionRecipeIds.join('; '),source,fisheryStatus,'3. Industrial city',
    'Scale fish production or press fish oil','Clear gallery and terrace cells','Native support and collision; no artificial layer cap','No',pipePorts(fishery),'Grid',
    'Hatchery juvenile fish; native algae; delivered Water; shaft power',`${amounts(fish.Ingredients)} / ${amounts(oil.Ingredients)}`,`${amounts(fish.Products)} / ${amounts(oil.Products)}`,'None',
    'Supported bank or dry land; six basins show actual stored Water','Grow beyond small shore catches',fisheryStatus,'80 hp total, zero output. Original native water wheel is a process animation, not a generator. Water capacity 90. Three doors across levels 0/2.'],
  ['GathererFlag.ShoreFishing','Gatherer Flag — shore fishing','Workplace','Food; existing vanilla building extension','Iron Teeth','Yes','Existing Gatherer Flag menu',flag.BlockObjectSpec.Size.X,flag.BlockObjectSpec.Size.Y,'1x1',1,flag.BlockObjectSpec.Size.Z,
    flag.WorkplaceSpec.MaxWorkers,0,0,'Passive / transport',flag.BuildingSpec.ScienceCost,0,'None','Explicit Catch fish job; default remains plant gathering','ShoreCatch (worker activity)',source,flagStatus,'1. Settlement',
    'Small renewable starter fish supply','Yes','Unchanged native flag support rules','No','No','None','Reachable dry bank beside real clean world water','No inventory ingredient',`1 Fresh Fish per ${aquaculture.shoreFishing.CatchHours} base working hours, plus travel`,'None',
    'Water depth >=0.5; contamination <=1%; surface no more than 1.25 below bank','Select Catch fish on a flag beside water',flagStatus,'One worker; native work speed, carrying and 20-per-good output capacity. No catch if water dries/pollutes or the job is paused/switched.']
];
export function updateAquacultureRows(rows,headers,updates) {
  for(const [id,fields] of updates) {
    const matches=rows.filter(r=>r[0]===id);if(matches.length!==1)throw Error(`Expected exactly one aquaculture row ${id}`);
    for(const [key,value] of Object.entries(fields)) {
      const i=headers.indexOf(key);if(i<0)throw Error(`Unknown workbook column ${key}`);matches[0][i]=value;
    }
  }
}
export const aquacultureItemUpdates=new Map();
for(const [rowId,id,producer,consumers] of [
  ['I004','FreshFish','Gatherer Flag (shore fishing); Fishery Works','Direct eating; restaurant; hatchery; fish oil; food packaging'],
  ['I007','FishOil','Fishery Works','Medicine; lubricant; emergency rations (authored recipes; runtime pending)']
]) {
  const g=(await read(`src/DeepFrontier/Data/Goods/Good.${id}.blueprint.json`)).GoodSpec;
  aquacultureItemUpdates.set(rowId,{'Type':g.GoodType,'Source / recipe':producer,'Storage':g.GoodType==='Liquid'?'Tank':'Warehouse','Weight':g.Weight,
    'Satisfies / effects':g.ConsumptionEffects.map(e=>`${e.NeedId}: +${e.Points}`).join('; '),'Consumed by':consumers,'Source':`src/DeepFrontier/Data/Goods/Good.${id}.blueprint.json`,
    'Data status':id==='FreshFish'?'Build 57 verified shore catch, breeding, juvenile hauling and factory production from zero fish stock; other downstream factories pending':'Authored recipe and good; runtime pressing pending',
    'Primary uses':consumers,'Perishable':'No','Unit':g.GoodType==='Liquid'?'Liquid':'Solid','Science value':0,
    'Notes':id==='FreshFish'?'Renewable catches seed hatcheries; food exception applies. No spoilage mechanic.':'Native liquid inventory. Exact pipe transfer compatibility still needs testing.'});
}
aquacultureItemUpdates.set('I005',{'Data status':'Design only; no active smoked-fish recipe','Source / recipe':'Proposed smoking recipe','Notes':'Not an active Fishery Works recipe.'});
aquacultureItemUpdates.set('I006',{'Source / recipe':'Food Packaging Works','Data status':'Authored CannedFish recipe; runtime pending','Notes':'Packaging is a separate factory, not an active Fishery Works recipe.'});
const juvenileGood=(await read('src/DeepFrontier/Data/Goods/Good.JuvenileFish.blueprint.json')).GoodSpec;
export const aquacultureItemAdds=[['JuvenileFish','Juvenile Fish','Good','Aquaculture ingredient','Iron Teeth',juvenileGood.GoodType,'Fish Hatchery','Warehouse',juvenileGood.Weight,'None','','Fishery Works',source,hatcheryStatus,'3','Raise fresh fish','No','None','Solid',0,'Only one useful downstream consumer currently authored; fails the ordinary-item two-use release requirement.']];
function recipeRow(r,b,status,intent) {
  return [r.Id,name(b.TemplateSpec.TemplateName.split('.')[0]),'Iron Teeth',name(r.Id),amounts(r.Ingredients),amounts(r.Products),r.CycleDurationInHours,b.MechanicalNodeSpec.PowerInput,0,'Consumer',b.WorkplaceSpec.MaxWorkers,
    'None',`${r.CyclesCapacity} recipe cycles`,source,JSON.stringify(r.Ingredients),JSON.stringify(r.Products),r.Products[0].Amount,r.CycleDurationInHours*60,r.Ingredients.map(g=>name(g.Id)).join('; '),r.Ingredients.map(g=>g.Amount).join('; '),'None','3. Industrial city',intent,status];
}
export const juvenileRecipeRow=recipeRow(juvenile,hatchery,hatcheryStatus,'Shore-caught FreshFish provides the starting breeder. Requires actual water under nursery plus delivered recipe Water.');
juvenileRecipeRow[0]='R004';
export const aquacultureRecipeAdds=[recipeRow(fish,fishery,fisheryStatus,'Three fish per juvenile; reserve breeder stock for repeatable hatchery supply.'),recipeRow(oil,fishery,'Authored exact recipe; runtime pressing pending','Alternate fishery recipe; same 80 hp building demand.'),
  ['ShoreCatch','Gatherer Flag — shore fishing','Iron Teeth','Catch Fresh Fish','No inventory goods; real clean world water','1 Fresh Fish',aquaculture.shoreFishing.CatchHours,0,0,'Passive / transport',1,'None','20 fish; native flag output capacity',source,'[]','[{"Id":"FreshFish","Amount":1}]',1,aquaculture.shoreFishing.CatchHours*60,'None',0,'None','1. Settlement','Worker activity, not a Manufactory recipe. Native worker speed applies; travel and delivery add time.',flagStatus]];
export const aquacultureOverview=[
  ['Aquaculture','Starter supply','Hatchery','Fishery Works','Water requirement','Verification'],
  ['Progression','Existing Gatherer Flag; 1 fish / 4 base work hours plus travel','600 science; 55 hp; breeds juveniles','900 science; 80 hp; raises fish or presses oil','Real water below hatchery nursery; delivered water for recipes',aquaculture.status],
  ['Balance','One worker; renewable; no power','1 fish + 1 algae + 2 water → 2 juveniles / 2 hours','1 juvenile + 1 algae + 3 water → 3 fish / 3 hours','Native pool depth and contamination blocking','Juvenile fish still needs a second useful consumer']
];
export const aquacultureProgression=['G021','Iron Teeth','1–3. Aquaculture','Start fishing, then breed and raise fish',0,'Gatherer Flag → Fish Hatchery → Fishery Works','Hatchery: 40 planks / 20 gears / 15 metal blocks; Fishery: same',
  'Flag 0 hp; hatchery 55 hp / 600 science; fishery 80 hp / 900 science','Low shore output encourages aquaculture investment','Fresh fish; fish oil; restaurant supply','Starter catch avoids a closed juvenile/adult recipe loop',
  'Catch fish toggle; native hatchery water warning; factory inventory and recipe selection','Settlement to industrial city','Exact authored blueprints and recipes; native pool behavior',aquaculture.status,source];
export const aquacultureTransport=['T017','Iron Teeth','Aquaculture supply','Native carrying and Timber Pipes Water intake','FreshFish, JuvenileFish, Algae, Water, FishOil',null,null,'Factories: 55/80 hp; each horizontal pipe pump: 50 hp; paths for workers','Fishery doors 0/2; supported working roof','Native district hauling and attached pipe lines','Carry starter fish into breeding; pipe Water into recipe buffers','Flag output 20; fishery Water 90; hatchery Water 60; network demand varies with pieces','Water pipe delivery passed 76; factory belts and FishOil pipes pending','Build 57 zero-stock catch/breeding/hauling; build 76 conserved tank-to-factory Water and valve stop/resume','Clear fishery terrace supports; ordinary collision rules',source,aquaculture.transportStatus];
export const aquacultureSource=['Aquaculture and native shore fishing',source,'Buildings, items, recipes, progression, transport and water requirements','2026-10-20','Exact package recipes and dimensions; native SwimmingPool TickableWaterBuildingSpec and contamination decorator. New Fishery: outputs/fishery-run51.log, fishery-reload51.log, fishery-hatchery57.log, fishery-continuity57.log and fishery-bootstrap57.log.','DeepFrontier',aquaculture.status,'4-hour catches; native carrying; fishery 80 hp / 900 science; hatchery 55 hp / 600 science; recipes and water gates'];
