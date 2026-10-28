import assert from 'node:assert/strict';
import { readFile, access, readdir, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = fileURLToPath(new URL('../', import.meta.url));
const data = resolve(root, 'src/DeepFrontier/Data');
const vanilla = resolve(root, 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources');
const read = async (base, path) => JSON.parse((await readFile(resolve(base, path), 'utf8')).replace(/^﻿/, '')); // vanilla blueprints may start with a BOM
const catalog = await read(root, 'tools/construction_materials.json');
const goodsCollection = (await read(data, 'GoodCollections/GoodCollection.IronTeeth.blueprint.json')).GoodCollectionSpec['Goods#append'];
const buildingsCollection = (await read(data, 'TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json')).TemplateCollectionSpec['Blueprints#append'];
const sourcesCollection = (await read(data, 'TemplateCollections/TemplateCollection.MapEditor.Common.blueprint.json')).TemplateCollectionSpec['Blueprints#append'];
const baseline = new Set();
for (const faction of ['Common', 'IronTeeth']) {
  for (const id of (await read(vanilla, `GoodCollections/GoodCollection.${faction}.blueprint.json`)).GoodCollectionSpec.Goods) baseline.add(id);
}
const validGoods = new Set([...baseline, ...goodsCollection]);
const goodGroups = new Map();
for (const name of await readdir(resolve(vanilla, 'GoodGroups'))) {
  if (!name.endsWith('.blueprint.json')) continue;
  const group = (await read(vanilla, `GoodGroups/${name}`)).GoodGroupSpec;
  goodGroups.set(group.Id, {spec: group, members: []});
}
for (const id of validGoods) {
  const base = goodsCollection.includes(id) ? data : vanilla;
  const good = (await read(base, `Goods/Good.${id}.blueprint.json`)).GoodSpec;
  assert(goodGroups.has(good.GoodGroupId), `${id}: unregistered resource-bar group ${good.GoodGroupId}`);
  goodGroups.get(good.GoodGroupId).members.push(id);
}
for (const {spec, members} of goodGroups.values()) {
  if (spec.SingleResourceGroup) assert.equal(members.length, 1, `${spec.Id}: native resource bar requires exactly one good; found ${members.join(', ')}`);
}
const buildings = [];
for (const entry of catalog.buildings) {
  const path = `Buildings/Metal/${entry.id}/${entry.id}.IronTeeth.blueprint`;
  assert(buildingsCollection.includes(path), `${entry.id}: missing faction registration`);
  const value = await read(data, `${path}.json`);
  buildings.push(value);
  const size = value.BlockObjectSpec.Size;
  assert.deepEqual([size.X, size.Y, size.Z], entry.size, `${entry.id}: grid axes are width, depth, height`);
  assert.equal(value.BlockObjectSpec.Blocks.length, size.X*size.Y*size.Z);
  for (const cost of value.BuildingSpec.BuildingCost) assert(validGoods.has(cost.Id), `${entry.id}: unknown cost ${cost.Id}`);
  if (entry.kind === 'pit') {
    assert.equal(value.MineralPitSpec.GoodId, entry.good);
    assert.equal(value.YieldRemovingBuildingSpec.ResourceGroup, `DeepFrontier${entry.good}`);
    assert(!value.ScavengerSpec, 'A pit must use the mineral selector, not the vanilla ruin selector');
  } else {
    assert.equal(value.MechanicalNodeSpec.PowerInput, entry.hp);
    assert.equal(value.MechanicalNodeSpec.PowerOutput, 0);
    assert.deepEqual(value.ManufactorySpec.ProductionRecipeIds, entry.recipes);
    for (const port of value.TransputProviderSpec.Transputs) {
      const {X,Y,Z} = port.Coordinates;
      assert(X>=0 && X<size.X && Y>=0 && Y<size.Y && Z>=0 && Z<size.Z, `${entry.id}: power port outside footprint`);
    }
  }
  if (entry.kind === 'quarry') assert.deepEqual(value.UnderstructureConstraintSpec.UnderstructureTemplateNames, [entry.source]);
  if (entry.id === 'ConcreteMixer') {
    // Deck-free mixer (2026-10-21): the drop pipe reaches the ground at the
    // foot of the header-tank tower, cell (6,4); the power-line insulator is
    // on that tower's rear-right pier. The tested inlet stays first; the
    // other flat exterior faces follow (validate_connection_faces.mjs).
    assert.deepEqual(value.BuildingPipeTargetPortsSpec.Ports[0],
      {Coordinates:{X:6,Y:4,Z:0},Directions:'Right',State:'OpenIn'});
    const portBlock=value.BlockObjectSpec.Blocks[4*size.X+6];
    assert.notEqual(portBlock.Occupations,'None','Mixer service inlet requires an occupied frame cell');
    assert.deepEqual(value.PowerLineSpec.ConnectionLocations,[{X:6.9,Y:4.9,Z:3.8}]);
    // A navmesh spec may only switch on native floors over platformable roofs (roof_deck_content.mjs).
    const nav=value.BlockObjectNavMeshSettingsSpec;
    assert(!value.BuildingWalkwaySpec && (!nav || !(nav.EdgeGroups.length || nav.UnblockedCoordinates.length || nav.BlockedEdges.length)),'Mixer has no walkway data');
  }
  await access(resolve(data, value.LabeledEntitySpec.Icon + '.png'));
  await access(resolve(data, value.Children['#Finished'].TimbermeshSpec.Model + '.timbermesh'));
}
const recipes = new Map();
for (const entry of catalog.recipes) {
  const recipe = (await read(data, `Recipes/Recipe.${entry.id}.blueprint.json`)).RecipeSpec;
  for (const amount of [...recipe.Ingredients, ...recipe.Products]) assert(validGoods.has(amount.Id), `${entry.id}: unknown good ${amount.Id}`);
  if (recipe.Fuel) assert(baseline.has(recipe.Fuel), `${entry.id}: fuel requires a later mod chain`);
  assert(recipe.CycleDurationInHours>0);
  recipes.set(recipe.Id,recipe);
}
for (const source of catalog.sources) {
  const path = `MapEditor/Objects/${source.id}/${source.id}.blueprint`;
  assert(sourcesCollection.includes(path));
  const value = await read(data, `${path}.json`);
  assert.equal(value.TemplateSpec.TemplateName, source.id);
  if(source.kind==='finite') {
    assert.equal(value.MineralDepositSpec.Yielder.Yield.Id, source.good);
    assert.equal(value.MineralDepositSpec.Yielder.Yield.Amount, source.yield);
    assert.equal(value.MineralDepositSpec.Yielder.ResourceGroup, `DeepFrontier${source.good}`);
    assert(!value.RuinSpec, 'Mineral deposits must not acquire vanilla random ruin models');
  }
  await access(resolve(data, value.Children['#Models'].TimbermeshSpec.Model+'.timbermesh'));
  await access(resolve(data, value.LabeledEntitySpec.Icon+'.png'));
}
for(const good of catalog.goods) {
  assert(goodsCollection.includes(good.id));
  const value = (await read(data,`Goods/Good.${good.id}.blueprint.json`)).GoodSpec;
  assert.equal(value.Id,good.id);
  await access(resolve(data,value.Icon+'.png'));
}
const removalGroups = (await read(data, 'RemoveYieldStrategies/RemoveYieldStrategy.Ruins.blueprint.json')).RemoveYieldStrategySpec['CompatibleResourceGroups#append'];
for (const building of buildings.filter(b => b.MineralPitSpec)) {
  assert(removalGroups.includes(building.YieldRemovingBuildingSpec.ResourceGroup), `${building.TemplateSpec.TemplateName}: removal strategy must accept its mineral group`);
}

// Resource graph includes construction costs, not just recipe inputs.
function reachable({finite, permanent, initial, disabledRecipe=''}) {
  const available = new Set(initial);
  const built = new Set();
  const steps = [];
  let progress = true;
  while(progress) {
    progress = false;
    for(const b of catalog.buildings) {
      if (b.kind==='quarry' && !permanent) continue;
      if (!b.cost.every(([id])=>available.has(id))) continue;
      if(!built.has(b.id)) { built.add(b.id); steps.push(`Build ${b.id}`); progress=true; }
      const outputs=[];
      if(b.kind==='pit' && finite) outputs.push(b.good);
      for(const id of b.recipes) {
        if(id===disabledRecipe) continue;
        const r=recipes.get(id);
        if(r.Ingredients.every(a=>available.has(a.Id)) && (!r.Fuel || available.has(r.Fuel))) outputs.push(...r.Products.map(a=>a.Id));
      }
      for(const id of outputs) if(!available.has(id)) { available.add(id); steps.push(`Obtain ${id} via ${b.id}`); progress=true; }
    }
  }
  return {available,built,steps};
}
const bootstrap=reachable({finite:true,permanent:false,initial:baseline});
assert(bootstrap.available.has('Concrete'), 'Concrete must bootstrap without permanent quarries, nuclear goods or concrete construction costs');
const full=reachable({finite:true,permanent:true,initial:baseline});
assert(full.built.has('SandstoneQuarry') && full.built.has('LimestoneQuarry'));
const renewable=reachable({finite:false,permanent:true,initial:new Set([...baseline,'Concrete'])});
assert(catalog.goods.every(g=>renewable.available.has(g.id)), 'Every mineral must remain producible after surface deposits run out');
const broken=reachable({finite:true,permanent:false,initial:baseline,disabledRecipe:'Cement'});
assert(!broken.available.has('Concrete'), 'Reachability check must detect a missing cement producer');

const missingReferences=[];
for(const path of buildingsCollection) {
  const b=await read(data,path+'.json');
  // Dev tools (e.g. the Radioactive Spring, like vanilla DevWaterSource) carry no BuildingSpec.
  for(const cost of b.BuildingSpec?.BuildingCost??[]) assert(validGoods.has(cost.Id), `${b.TemplateSpec.TemplateName}: unknown construction good ${cost.Id}`);
}
for(const name of await readdir(resolve(data,'Recipes'))) {
  if(!name.endsWith('.blueprint.json')) continue;
  const r=(await read(data,`Recipes/${name}`)).RecipeSpec;
  for(const amount of [...r.Ingredients,...r.Products]) if(!validGoods.has(amount.Id)) missingReferences.push({recipe:r.Id,good:amount.Id});
}
const report={status:'construction-chain-static-checks-passed',baseline:'Vanilla Common + Iron Teeth goods; authored map must supply both outcrops and both seams',
  goods:catalog.goods.length,buildings:catalog.buildings.length,sources:catalog.sources.length,recipes:catalog.recipes.length,
  bootstrap:bootstrap.steps,renewable:renewable.steps,otherRecipeFactionErrors:missingReferences,
  limitations:'Static graph assumes baseline vanilla goods, science, workforce, map access and power. Does not verify runtime extraction, animation, save/reload, transport compatibility or quantitative supply rates.'};
await writeFile(resolve(root,'outputs/construction-material-validation.json'),JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify(report,null,2));
