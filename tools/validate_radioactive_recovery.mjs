// Content and balance checks; native pumping, hauling and save/reload still
// require in-game acceptance. Do not substitute these for gameplay evidence.
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {resolve} from 'node:path';
const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const data = resolve(root, 'src/DeepFrontier/Data');
const json = async path => JSON.parse(await readFile(resolve(data, path), 'utf8'));
const recipe = async id => (await json(`Recipes/Recipe.${id}.blueprint.json`)).RecipeSpec;
const amount = (rows, id) => rows.filter(g => g.Id === id).reduce((sum,g) => sum+g.Amount,0);
const recovery = await recipe('RecoveredYellowcake');
assert.deepEqual(recovery.Ingredients, [{Id:'RadioactiveSludge',Amount:6},{Id:'Chemical',Amount:2}]);
assert.deepEqual(recovery.Products, [{Id:'Yellowcake',Amount:1}]);
assert.equal(recovery.CycleDurationInHours,4);
assert.equal(recovery.DisplayLocKey,'Recipe.RecoveredYellowcake.DisplayName');
const plant = await json('Buildings/Metal/UraniumProcessingPlant/UraniumProcessingPlant.IronTeeth.blueprint.json');
assert(plant.ManufactorySpec.ProductionRecipeIds.includes('RecoveredYellowcake'));
assert(plant.ManufactorySpec.ProductionRecipeIds.includes('Yellowcake'), 'ore route remains available');
const vault = await json('Buildings/Storage/RadioactiveWasteVault/RadioactiveWasteVault.IronTeeth.blueprint.json');
assert.deepEqual(vault.ShieldedRadioactiveStorageSpec,{});
assert.equal(vault.StockpileSpec.MaxCapacity,1600);
const pump = await json('Buildings/Water/RadioactiveSludgeRecoveryPump/RadioactiveSludgeRecoveryPump.IronTeeth.blueprint.json');
assert(pump.RadioactiveSludgeIntakeSpec.RadioactiveVolumePerCycle > 0, 'output requires collected radioactive volume');

const reactor = await recipe('NuclearWaste'), refining = await recipe('WasteRefining');
const sludgePerWaste = amount(refining.Products,'RadioactiveSludge')/amount(refining.Ingredients,'RadioactiveWaste');
const sludgePerYellowcake = amount(recovery.Ingredients,'RadioactiveSludge')/amount(recovery.Products,'Yellowcake');
assert.equal(reactor.Fuel,'EnrichedFuel');
for (const id of ['EnrichedFuel','FuelReprocessing']) {
  const fuel = await recipe(id);
  const cycles = amount(fuel.Products,'EnrichedFuel')*reactor.CyclesFuelLasts;
  const waste = amount(fuel.Products,'RadioactiveWaste') - amount(fuel.Ingredients,'RadioactiveWaste')
    + cycles*amount(reactor.Products,'RadioactiveWaste');
  const recycled = waste*sludgePerWaste + cycles*amount(reactor.Products,'RadioactiveSludge');
  const consumed = amount(fuel.Ingredients,'Yellowcake')*sludgePerYellowcake;
  // User requested a practical water-and-chemicals batch. Recycling is allowed
  // to replenish nuclear feedstock; report its yield without a lossy-loop gate.
  assert(Number.isFinite(recycled) && consumed > 0);
  console.log(`${id}: ${consumed} radioactive water in, at most ${recycled} recovered`);
}
const workforce = JSON.parse(await readFile(resolve(root,'tools/workforce_risks.json'),'utf8'));
assert.match(workforce.botAssembly.assemblerDescription,/leak radioactive water into the ground/);
assert.match(workforce.botAssembly.assemblerDescription,/coolant.*plating/);
console.log('Radioactive recovery content passed; recycling yields reported above.');
