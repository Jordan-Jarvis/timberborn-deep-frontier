import {access, readFile, readdir, writeFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve, relative} from 'node:path';
const root=fileURLToPath(new URL('../',import.meta.url));
const data=resolve(root,'src/DeepFrontier/Data');
const vanilla=resolve(root,'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources');
// Native imported blueprints use UTF-8 with or without its encoding signature.
// Decode that file format once at the input boundary.
const utf8=new TextDecoder('utf-8',{fatal:true});
const read=async p=>JSON.parse(utf8.decode(await readFile(p)));
const policy=await read(resolve(root,'tools/content_policy.json'));
async function files(directory){
  const result=[];
  for(const entry of await readdir(directory,{withFileTypes:true})){
    const path=resolve(directory,entry.name);
    if(entry.isDirectory())result.push(...await files(path));
    else if(entry.name.endsWith('.blueprint.json'))result.push(path);
  }
  return result;
}
const goods=new Map();
const vanillaGoods=new Set();
for(const p of await files(resolve(vanilla,'Goods')))vanillaGoods.add((await read(p)).GoodSpec.Id);
for(const p of await files(resolve(data,'Goods'))){
  const good=(await read(p)).GoodSpec;
  if(!vanillaGoods.has(good.Id))goods.set(good.Id,{id:good.Id,uses:new Map(),production:new Set(),
    foodException:good.GoodGroupId==='Food'&&good.ConsumptionEffects.some(e=>e.NeedId==='Hunger'&&e.Points>0)});
}
const add=(id,key,evidence)=>{if(goods.has(id))goods.get(id).uses.set(key,evidence);};
const buildingCollection=await read(resolve(data,'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json'));
const activeRecipes=new Set();
const launchRecipes=new Set();
const trainingRecipes=new Set();
const botRecipes=new Set();
const generatorRecipes=new Set();
const recipes=new Map();
for(const directory of [resolve(vanilla,'Recipes'),resolve(data,'Recipes')])for(const p of await files(directory)){
  const value=(await read(p)).RecipeSpec;
  if(recipes.has(value.Id))throw Error('Duplicate recipe definition: '+value.Id);
  recipes.set(value.Id,{value,path:relative(root,p)});
}
for(const blueprint of buildingCollection.TemplateCollectionSpec['Blueprints#append']){
  const path=resolve(data,blueprint+'.json'), bp=await read(path);
  const target=bp.TemplateSpec.TemplateName;
  // Dev tools such as the Radioactive Spring (like vanilla DevWaterSource) have
  // no BuildingSpec and therefore no construction cost.
  for(const cost of bp.BuildingSpec?.BuildingCost??[])add(cost.Id,'Construction: '+target,relative(root,path));
  if(Object.hasOwn(bp,'ManufactorySpec'))for(const id of bp.ManufactorySpec.ProductionRecipeIds)activeRecipes.add(id);
  if(Object.hasOwn(bp,'GoodConsumingBuildingSpec'))for(const g of bp.GoodConsumingBuildingSpec.ConsumedGoods)add(g.GoodId,'Operation: '+target,relative(root,path));
  if(Object.hasOwn(bp,'RestaurantSpec'))for(const id of [...bp.RestaurantSpec.Foods,...bp.RestaurantSpec.OptionalGoods])add(id,'Seated meal: '+target,relative(root,path));
  // A launch mission recipe consumes a whole rocket and fuel load without products.
  if(Object.hasOwn(bp,'RocketLaunchPadSpec'))for(const m of bp.RocketLaunchPadSpec.Missions)launchRecipes.add(m.RecipeId);
  // A specialist course consumes its supplies without products and graduates a beaver.
  if(Object.hasOwn(bp,'FrontierSpecialistSchoolSpec'))for(const p of bp.FrontierSpecialistSchoolSpec.Programs)trainingRecipes.add(p.RecipeId);
  // Bot maintenance oils (tools/bot_upkeep_content.mjs): one destination for every workplace.
  // A workshop generator's fuel recipe (the reactor) burns its fuel for hp, not for products. The coal and oil
  // plants are GoodConsumingBuilding generators and count above as Operation.
  if(Object.hasOwn(bp,'WorkshopPoweredGeneratorSpec'))for(const id of bp.ManufactorySpec.ProductionRecipeIds)generatorRecipes.add(id);
  if(Object.hasOwn(bp,'FrontierBotMaintenanceSpec'))for(const g of bp.FrontierBotMaintenanceSpec.Goods)add(g.GoodId,'Bot maintenance',relative(root,path));
}
// Vanilla templates patched by a same-path Deep Frontier blueprint (native
// array overlay): the recipes they append are active. A Bot Assembler recipe
// has no products; finishing it builds a bot.
for(const name of ['Common','IronTeeth'])for(const template of (await read(resolve(vanilla,`TemplateCollections/TemplateCollection.Buildings.${name}.blueprint.json`))).TemplateCollectionSpec.Blueprints){
  const path=resolve(data,template+'.json');
  if(!await access(path).then(()=>true,()=>false))continue;
  const base=await read(resolve(vanilla,template+'.json'));
  for(const id of (await read(path)).ManufactorySpec?.['ProductionRecipeIds#append']??[]){
    activeRecipes.add(id);
    if(Object.hasOwn(base,'BotManufactorySpec'))botRecipes.add(id);
  }
}
for(const id of activeRecipes){
  if(!recipes.has(id))throw Error('Missing recipe: '+id);
  const {value:r,path}=recipes.get(id);
  // Two recipes making the same product are one destination. Moving a good
  // through a source stockpile or recycling it into itself is not another use.
  const destinations=r.Products.map(p=>p.Id);
  for(const product of r.Products)if(goods.has(product.Id))goods.get(product.Id).production.add(id);
  for(const ingredient of r.Ingredients){
    const outputs=destinations.filter(output=>output!==ingredient.Id).sort();
    if(outputs.length)add(ingredient.Id,'Products: '+outputs.join(' + '),path);
    if(r.ProducedSciencePoints>0)add(ingredient.Id,'Research: Science',path);
    // All missions are one destination: the launch consumer.
    if(launchRecipes.has(id))add(ingredient.Id,'Launch: rocket missions',path);
    // All courses are one destination: the specialist workforce.
    if(trainingRecipes.has(id))add(ingredient.Id,'Training: specialists',path);
    // All bot assembly recipes are one destination: the bot workforce.
    if(botRecipes.has(id))add(ingredient.Id,'Bot assembly: bots',path);
  }
  if(r.Fuel!=='')add(r.Fuel,'Fuel: '+(generatorRecipes.has(id)?'power generation':destinations.slice().sort().join(' + ')),path);
}
const assortment=await read(resolve(data,'GoodCollections/GoodCollection.IronTeeth.blueprint.json'));
for(const id of assortment.GoodCollectionSpec['Goods#append']){
  if(!goods.has(id))continue;
  const good=(await read(resolve(data,'Goods/Good.'+id+'.blueprint.json'))).GoodSpec;
  // Sweet berry cake is eaten only at the Restaurant's tables, not directly.
  if(good.ConsumptionEffects.length&&id!=='SweetBerryCake')add(id,'Direct consumption',relative(root,resolve(data,'Goods/Good.'+id+'.blueprint.json')));
}
for(const id of Object.keys(policy.legacySaveOnlyGoods))
  if(!policy.prohibitedNewInventoryConcepts.includes(id))throw Error('Legacy save-only good '+id+' must remain a prohibited concept');
const rows=[...goods.values()].map(g=>{
  const exception=Object.hasOwn(policy.singleUseExceptions,g.id);
  const prohibited=policy.prohibitedNewInventoryConcepts.includes(g.id);
  // Retired placeholder kept defined only so saves load: valid only while
  // nothing produces or consumes it.
  const legacy=Object.hasOwn(policy.legacySaveOnlyGoods,g.id);
  const retired=legacy&&g.uses.size===0&&g.production.size===0;
  const minimum=retired?0:exception||g.foodException?1:policy.minimumDistinctUses;
  return {id:g.id,uses:[...g.uses].map(([destination,evidence])=>({destination,evidence})),distinctUses:g.uses.size,
    activeProducingRecipes:[...g.production],minimum,rocketException:exception,foodException:g.foodException,legacyPlaceholder:prohibited&&!retired,legacySaveOnly:legacy,
    status:retired?'LEGACY SAVE-ONLY (unproduced, unused)':legacy?'LEGACY GOOD STILL PRODUCED OR USED':prohibited?'REPLACE PLACEHOLDER':g.uses.size<minimum?'NEEDS USES':g.uses.size<3?'MINIMUM MET':'PREFERRED RANGE MET'};
}).sort((a,b)=>a.id.localeCompare(b.id));
for(const id of Object.keys(policy.legacySaveOnlyGoods))if(!goods.has(id))throw Error('Legacy save-only good '+id+' is no longer defined; existing saves need it or an explicit migration');
const failures=rows.filter(r=>r.legacyPlaceholder||r.distinctUses<r.minimum);
const report={checkedAt:new Date().toISOString(),policy:'tools/content_policy.json',
  scope:'Static reachable blueprint consumption only, including authored restaurant menu inputs; a consumer does not establish production-chain bootstrap or runtime functionality. Planned services and aluminum uses are excluded.',
  releaseReady:failures.length===0,total:rows.length,failures:failures.length,items:rows};
await writeFile(resolve(root,'outputs/item-use-audit.json'),JSON.stringify(report,null,2)+'\n');
const table=['# Item use audit','','Generated from active Iron Teeth building recipes (including recipes appended to vanilla buildings), construction costs, restaurant menus, bot assembly, bot maintenance and faction-consumable goods. Planned uses do not count. The reasoning for each second use is in docs/progression.md (Second uses).','',
  `**${rows.length} new goods checked; ${failures.length} require redesign or additional uses before release.**`,'',
  'Food may have direct eating as its only use. Rocket-specific parts still need one real launch consumer. Transport/storage/disposal do not count.','',
  '| Item | Uses | Required | Result | Authored destinations |','|---|---:|---:|---|---|',
  ...rows.map(r=>`| ${r.id} | ${r.distinctUses} | ${r.minimum} | ${r.status} | ${r.uses.map(u=>u.destination).join('; ')} |`)];
await writeFile(resolve(root,'docs/item-use-audit.md'),table.join('\n')+'\n');
console.log(JSON.stringify({checked:rows.length,failures:failures.map(r=>r.id),releaseReady:report.releaseReady},null,2));
if(process.argv.includes('--release-check')&&!report.releaseReady)process.exitCode=1;
