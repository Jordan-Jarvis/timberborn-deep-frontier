import { access, readFile } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const sourceRoot = resolve(root, 'src', 'DeepFrontier');

async function readJson(relativePath) {
  return JSON.parse(await readFile(resolve(sourceRoot, relativePath), 'utf8'));
}

const goods = [
  await readJson('Data/Goods/Good.DeepOre.blueprint.json'),
  await readJson('Data/Goods/Good.DeepAlloy.blueprint.json'),
];
const recipes = [
  await readJson('Data/Recipes/Recipe.DeepOre.blueprint.json'),
  await readJson('Data/Recipes/Recipe.DeepOre.Mine.blueprint.json'),
  await readJson('Data/Recipes/Recipe.DeepAlloy.blueprint.json'),
];
const drill = await readJson('Data/Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.blueprint.json');
const mine = await readJson('Data/Buildings/Metal/DeepMine/DeepMine.IronTeeth.blueprint.json');
const processor = await readJson('Data/Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.blueprint.json');
const source = await readJson('Data/MapEditor/Objects/DeepOreSource/DeepOreSource.blueprint.json');
const vein = await readJson('Data/MapEditor/Objects/DeepOreVein/DeepOreVein.blueprint.json');
const goodsCollection = await readJson('Data/GoodCollections/GoodCollection.IronTeeth.blueprint.json');
const buildingCollection = await readJson('Data/TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json');
const mapCollection = await readJson('Data/TemplateCollections/TemplateCollection.MapEditor.Common.blueprint.json');
const expansionGoodIds = ['Compost', 'Coal', 'Chemical', 'RecoveredArtifact', 'Fertilizer', 'FreshFish', 'JuvenileFish', 'FishOil', 'CannedFish', 'EmergencyRation', 'PackagedFood', 'Medicine', 'MedicalFood', 'Flux', 'HighGradeSteel', 'Alloy', 'Polymer', 'Lubricant', 'MachineCore', 'PowerModule', 'FilterMedia', 'ConcentratedWaste', 'CrudeOil', 'UraniumOre', 'Yellowcake', 'EnrichedFuel', 'PureWater', 'HydrogenGas', 'OxygenGas', 'LiquidHydrogen', 'LiquidOxygen', 'Cryocoolant', 'RadioactiveWaste', 'RocketAirframe', 'PropulsionPackage', 'GuidanceComputer', 'MissionPayload', 'RecoveredTelemetry', 'IndustrialLicense', 'SpecialistLicense', 'FlightLicense', 'Electronics', 'ReactorCoolantWater', 'RecoveredMinerals', 'ArchiveData'];
const expansionRecipeIds = ['Compost', 'Fertilizer', 'JuvenileFish', 'FreshFish', 'FishOil', 'CannedFish', 'EmergencyRation', 'PackagedFood', 'Medicine', 'MedicalFood', 'Flux', 'HighGradeSteel', 'Alloy', 'Chemical', 'Polymer', 'Lubricant', 'MachineCore', 'Electronics', 'PowerModule', 'FilterMedia', 'PureWater', 'ReactorCoolantWater', 'DeepCoal', 'DeepOil', 'DeepUranium', 'Yellowcake', 'EnrichedFuel', 'Cryocoolant', 'Electrolysis', 'Liquefaction', 'RocketAirframe', 'PropulsionPackage', 'GuidanceComputer', 'MissionPayload', 'NuclearWaste', 'WasteRefining', 'GuidanceTelemetry', 'RecoveredArtifact', 'ArchiveData', 'CarbonFilterMedia', 'BrineChemical', 'GreenhouseAquaponics', 'ReinforcedBotChassis', 'ServoBotLimbs', 'BotCortex', 'FuelReprocessing', 'ContaminatedWaterRefining'];
const expansionBuildingBlueprints = ['Buildings/Food/FertilizerWorks/FertilizerWorks.IronTeeth.blueprint', 'Buildings/Food/FishHatchery/FishHatchery.IronTeeth.blueprint', 'Buildings/Food/FisheryWorks/FisheryWorks.IronTeeth.blueprint', 'Buildings/Food/FoodPackagingWorks/FoodPackagingWorks.IronTeeth.blueprint', 'Buildings/Wellbeing/PublicHealthLab/PublicHealthLab.IronTeeth.blueprint', 'Buildings/Food/GroceryStore/GroceryStore.IronTeeth.blueprint', 'Buildings/Food/Restaurant/Restaurant.IronTeeth.blueprint', 'Buildings/Wellbeing/Hospital/Hospital.IronTeeth.blueprint', 'Buildings/Food/Greenhouse/Greenhouse.IronTeeth.blueprint', 'Buildings/Metal/ChemicalWorks/ChemicalWorks.IronTeeth.blueprint', 'Buildings/Metal/PrecisionMachineWorks/PrecisionMachineWorks.IronTeeth.blueprint', 'Buildings/Water/WaterTreatmentPlant/WaterTreatmentPlant.IronTeeth.blueprint', 'Buildings/Science/TechnicalSchool/TechnicalSchool.IronTeeth.blueprint', 'Buildings/Metal/UraniumProcessingPlant/UraniumProcessingPlant.IronTeeth.blueprint', 'Buildings/Metal/RadioactiveWasteRefinery/RadioactiveWasteRefinery.IronTeeth.blueprint', 'Buildings/Metal/ElectrolysisPlant/ElectrolysisPlant.IronTeeth.blueprint', 'Buildings/Metal/CryogenicLiquefactionPlant/CryogenicLiquefactionPlant.IronTeeth.blueprint', 'Buildings/Metal/RocketAssemblyHangar/RocketAssemblyHangar.IronTeeth.blueprint', 'Buildings/Science/MissionControl/MissionControl.IronTeeth.blueprint', 'Buildings/Metal/LaunchPad/LaunchPad.IronTeeth.blueprint', 'Buildings/Power/NuclearReactor/NuclearReactor.IronTeeth.blueprint', 'Buildings/Storage/RadioactiveWasteVault/RadioactiveWasteVault.IronTeeth.blueprint', 'Buildings/Metal/SteelMill/SteelMill.IronTeeth.blueprint', 'Buildings/Science/ArchiveExcavation/ArchiveExcavation.IronTeeth.blueprint', 'Buildings/Storage/CryogenicTankFarm/CryogenicTankFarm.IronTeeth.blueprint', 'Buildings/Wellbeing/SmogScrubber/SmogScrubber.IronTeeth.blueprint', 'Buildings/Wellbeing/Bathhouse/Bathhouse.IronTeeth.blueprint', 'Buildings/Wellbeing/TownPlaza/TownPlaza.IronTeeth.blueprint', 'Buildings/Wellbeing/ObservationDeck/ObservationDeck.IronTeeth.blueprint', 'Buildings/Power/CoalPowerPlant/CoalPowerPlant.IronTeeth.blueprint', 'Buildings/Power/OilPowerPlant/OilPowerPlant.IronTeeth.blueprint'];
const authoredDimensions = {
  FertilizerWorks: [2, 3, 2], FishHatchery: [7, 7, 5], FisheryWorks: [11, 8, 7], FoodPackagingWorks: [3, 3, 3],
  PublicHealthLab: [2, 3, 2], GroceryStore: [11, 9, 9], Restaurant: [9, 7, 9], Hospital: [12, 9, 9], Greenhouse: [3, 1, 3],
  ChemicalWorks: [3, 3, 3], PrecisionMachineWorks: [3, 2, 3], WaterTreatmentPlant: [3, 3, 3], TechnicalSchool: [2, 3, 2],
  UraniumProcessingPlant: [3, 3, 3], RadioactiveWasteRefinery: [3, 3, 3], ElectrolysisPlant: [3, 3, 3], CryogenicLiquefactionPlant: [3, 3, 3],
  RocketAssemblyHangar: [3, 3, 3], MissionControl: [2, 3, 2], LaunchPad: [3, 3, 3], NuclearReactor: [3, 3, 3], RadioactiveWasteVault: [3, 2, 3],
};
// Integrated late-game studies carry their footprint in their grid registration.
for (const id of JSON.parse(await readFile(resolve(root, 'tools/lategame_batches.json'), 'utf8')).integrated) {
  const registration = JSON.parse(await readFile(resolve(root, `outputs/lategame-studies/${id}-registration.json`), 'utf8'));
  authoredDimensions[id] = [...registration.footprint, registration.height];
}
{
  const registration = JSON.parse(await readFile(resolve(root, 'outputs/lategame-studies/GroceryMarket-registration.json'), 'utf8'));
  authoredDimensions.GroceryStore = [...registration.footprint, registration.height];
}

const assert = (condition, message) => {
  if (!condition) throw new Error(message);
};

await access(resolve(sourceRoot, 'Data/Localizations/enUS.csv'));
assert(!await access(resolve(sourceRoot, 'Localizations/enUS.csv')).then(() => true).catch(() => false), 'Localization must live under Data/Localizations for mod packaging.');

const goodIds = goods.map((good) => good.GoodSpec.Id);
assert(goodIds.join(',') === 'DeepOre,DeepAlloy', `Unexpected good IDs: ${goodIds.join(',')}`);
for (const good of goods) {
  assert(good.GoodSpec.Icon === `Sprites/Goods/${good.GoodSpec.Id}Icon`, `${good.GoodSpec.Id} must show its own icon, not ${good.GoodSpec.Icon}.`);
  await access(resolve(sourceRoot, 'Data', `${good.GoodSpec.Icon}.png`));
}
assert(recipes[0].RecipeSpec.Id === 'DeepOre' && recipes[1].RecipeSpec.Id === 'DeepOre.Mine' && recipes[2].RecipeSpec.Id === 'DeepAlloy', 'Recipe IDs do not match the vertical slice.');
assert(recipes[0].RecipeSpec.Ingredients.some((ingredient) => ingredient.Id === 'DeepOre' && ingredient.Amount === 1), 'DeepOre recipe must consume one unit from the authored source stockpile.');
assert(recipes[0].RecipeSpec.Ingredients.some((ingredient) => ingredient.Id === 'Water' && ingredient.Amount === 3), 'DeepOre recipe water demand changed unexpectedly.');
assert(recipes[0].RecipeSpec.Products.some((product) => product.Id === 'DeepOre' && product.Amount === 1), 'DeepOre recipe must output one extracted unit.');
assert(recipes[1].RecipeSpec.Ingredients.length === 1 && recipes[1].RecipeSpec.Ingredients[0].Id === 'Water' && recipes[1].RecipeSpec.Products.some((product) => product.Id === 'DeepOre' && product.Amount === 4), 'Permanent Deep Mine recipe must consume water and output four Deep Ore.');
assert(recipes[2].RecipeSpec.Ingredients.some((ingredient) => ingredient.Id === 'DeepOre'), 'DeepAlloy recipe does not consume DeepOre.');
// The deep buildings carry their late-game study registrations.
const blockSize = (building) => [building.BlockObjectSpec.Size.X, building.BlockObjectSpec.Size.Y, building.BlockObjectSpec.Size.Z].join(',');
for (const [id, building] of [['DeepDrill', drill], ['DeepMine', mine], ['DeepProcessor', processor]]) {
  const expectedSize = authoredDimensions[id];
  assert(expectedSize, `${id} is not an integrated late-game study.`);
  assert(blockSize(building) === expectedSize.join(','), `${id} footprint does not match its authored mesh.`);
  assert(building.BlockObjectSpec.Blocks.length === expectedSize[0] * expectedSize[1] * expectedSize[2], `${id} block occupancy does not match its footprint.`);
  // The studies author no underground cut-view part.
  assert(building.BuildingModelSpec.UndergroundModelName === '' && !Object.hasOwn(building.Children, '#Underground'), `${id} references an underground model its study does not author.`);
}
// UnderstructureFinder.FindStrict selects foundation blocks whose occupation
// is exactly Top, Corners or Top|Corners; for the mine that is the ground core
// over the vein, matching the vein's own size.
const foundationCore = (building) => {
  const { X, Y } = building.BlockObjectSpec.Size;
  return building.BlockObjectSpec.Blocks.flatMap((block, index) => (
    ['Ground', 'GroundOrStackable', 'Stackable'].includes(block.MatterBelow) && ['Top', 'Corners', 'Top, Corners'].includes(block.Occupations)
      ? [{ x: index % X, y: Math.floor(index / X) % Y, z: Math.floor(index / X / Y), block }] : []));
};
const mineCore = foundationCore(mine);
const coreSpan = (axis) => Math.max(...mineCore.map((c) => c[axis])) - Math.min(...mineCore.map((c) => c[axis])) + 1;
assert(mineCore.length > 0 && mineCore.every((c) => c.z === 0 && c.block.MatterBelow === 'Ground' && c.block.Occupations === 'Top'), 'Deep Mine core must be ground-layer Top blocks on Ground.');
assert(coreSpan('x') === vein.BlockObjectSpec.Size.X && coreSpan('y') === vein.BlockObjectSpec.Size.Y, 'Deep Mine core does not match the Deep Ore vein footprint.');
assert(!vein.BlockObjectSpec.Blocks.some((block) => block.Occupations.split(', ').includes('Top')), 'Deep Ore vein must leave Top free for the mine core.');
assert(!drill.UnderstructureConstraintSpec && foundationCore(drill).length === 0, 'Deep Drill is stockpile-fed and must not require an understructure.');
assert(drill.WorkplaceSpec.MaxWorkers === 3, 'Deep Drill worker count changed unexpectedly.');
assert(drill.MechanicalNodeSpec.PowerInput === 1000 && drill.MechanicalNodeSpec.PowerOutput === 0, 'Deep Drill power contract is invalid.');
assert(drill.ManufactorySpec.ProductionRecipeIds.includes('DeepOre'), 'Deep Drill is not wired to the DeepOre recipe.');
assert(mine.WorkplaceSpec.MaxWorkers === 6, 'Deep Mine worker count changed unexpectedly.');
assert(mine.MechanicalNodeSpec.PowerInput === 4000 && mine.MechanicalNodeSpec.PowerOutput === 0, 'Deep Mine power contract is invalid.');
assert(mine.ManufactorySpec.ProductionRecipeIds.includes('DeepOre.Mine'), 'Deep Mine is not wired to the permanent DeepOre.Mine recipe.');
assert(mine.UnderstructureConstraintSpec.UnderstructureTemplateNames.includes('DeepOreVein'), 'Deep Mine must require a DeepOreVein understructure.');
assert(processor.MechanicalNodeSpec.PowerInput === 500 && processor.MechanicalNodeSpec.PowerOutput === 0, 'Deep Processor power contract is invalid.');
assert(processor.ManufactorySpec.ProductionRecipeIds.includes('DeepAlloy'), 'Deep Processor is not wired to the DeepAlloy recipe.');
assert(source.StockpileSpec.MaxCapacity === 4000, 'Deep Ore source capacity changed unexpectedly.');
assert(source.Children['#Finished'].TimbermeshSpec.Model === 'MapEditor/Objects/DeepOreSource/DeepOreSource.Model', 'Deep Ore source must use its authored ore model.');
assert(vein.TemplateSpec.TemplateName === 'DeepOreVein', 'Deep Ore vein marker template is invalid.');
assert(goodsCollection.GoodCollectionSpec['Goods#append'].includes('DeepOre') && goodsCollection.GoodCollectionSpec['Goods#append'].includes('DeepAlloy'), 'Iron Teeth base good collection overlay is incomplete.');
for (const id of expansionGoodIds) {
  const good = await readJson(`Data/Goods/Good.${id}.blueprint.json`);
  assert(good.GoodSpec.Id === id, `Expansion good ${id} has a mismatched ID.`);
  assert(goodsCollection.GoodCollectionSpec['Goods#append'].includes(id), `Expansion good ${id} is not in the Iron Teeth collection.`);
  await access(resolve(sourceRoot, 'Data', 'Sprites', 'Goods', `${id}Icon.png`));
}
for (const id of expansionRecipeIds) {
  const recipe = await readJson(`Data/Recipes/Recipe.${id}.blueprint.json`);
  assert(recipe.RecipeSpec.Id === id, `Expansion recipe ${id} has a mismatched ID.`);
}
for (const blueprint of expansionBuildingBlueprints) {
  const building = await readJson(`Data/${blueprint}.json`);
  const id = building.TemplateSpec.TemplateName.replace(/\.IronTeeth$/, '');
  assert(building.TemplateSpec.TemplateName.endsWith('.IronTeeth'), `Expansion building ${blueprint} is not an Iron Teeth template.`);
  const expectedSize = authoredDimensions[id];
  assert(expectedSize, `No authored footprint is registered for ${id}.`);
  assert([building.BlockObjectSpec.Size.X, building.BlockObjectSpec.Size.Y, building.BlockObjectSpec.Size.Z].join(',') === expectedSize.join(','), `${id} footprint does not match its authored mesh.`);
  assert(building.BlockObjectSpec.Blocks.length === expectedSize[0] * expectedSize[1] * expectedSize[2], `${id} block occupancy does not match its footprint.`);
  const iconPath = building.LabeledEntitySpec.Icon.split('/');
  await access(resolve(sourceRoot, 'Data', ...iconPath) + '.png');
  assert(building.TemplateSpec.TemplateName !== 'SteamEngine.IronTeeth', `Expansion building ${blueprint} accidentally retained a vanilla template name.`);
}
const reactor = await readJson('Data/Buildings/Power/NuclearReactor/NuclearReactor.IronTeeth.blueprint.json');
assert(reactor.MechanicalNodeSpec.PowerOutput === 800000 && reactor.MechanicalNodeSpec.PowerInput === 0, 'Nuclear reactor power contract is invalid.');
assert(!reactor.GoodConsumingBuildingSpec, 'Reactor must have only one native IGoodProcessor.');
assert(reactor.WorkshopSpec && reactor.SimpleManufactoryBehaviorsSpec && reactor.WorkshopPoweredGeneratorSpec, 'Reactor requires a working manufactory and production-gated output.');
assert(reactor.ManufactorySpec.ProductionRecipeIds.includes('NuclearWaste'), 'Reactor must select the fuel-to-waste recipe.');
const reactorRecipe = (await readJson('Data/Recipes/Recipe.NuclearWaste.blueprint.json')).RecipeSpec;
assert(reactorRecipe.Ingredients.some((good) => good.Id === 'ReactorCoolantWater' && good.Amount > 0), 'Reactor recipe must require coolant.');
assert(reactorRecipe.Fuel === 'EnrichedFuel' && reactorRecipe.CyclesFuelLasts === 10, 'Reactor recipe must consume enriched fuel.');
assert(reactorRecipe.Products.some((good) => good.Id === 'RadioactiveWaste' && good.Amount > 0), 'Reactor recipe must produce waste.');
// Coal and oil power plants (frontier_progression.json powerPlants): the
// native Iron Teeth Steam Engine generator contract, no workers.
const steamEngine = JSON.parse(await readFile(resolve(root, 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Buildings/Power/SteamEngine/SteamEngine.IronTeeth.blueprint.json'), 'utf8'));
const nativeGeneratorSpecs = ['GoodConsumingBuildingSpec', 'GoodPoweredGeneratorSpec', 'MechanicalBuildingSpec', 'PowerGeneratorSoundsSpec',
  'GoodPoweredGeneratorAnimatorSpec', 'MechanicalNodeIlluminatorSpec', 'PowerGeneratorParticleControllerSpec'];
assert(nativeGeneratorSpecs.every((key) => Object.hasOwn(steamEngine, key)), 'The vanilla Steam Engine no longer carries the native generator specs.');
const staffedSpecs = ['WorkplaceSpec', 'ManufactorySpec', 'WorkshopSpec', 'WorkshopPoweredGeneratorSpec', 'SimpleManufactoryBehaviorsSpec',
  'WorkplaceIlluminatorSpec', 'WorkplaceSlotManagerSpec', 'WorkshopWorkerHiderSpec', 'WorkshopAnimationControllerSpec', 'WorkshopParticleControllerSpec',
  'WorkshopRandomNeedApplierSpec', 'TransformSlotInitializerSpec', 'FrontierWorkforceRiskSpec', 'FrontierBotMaintenanceSpec', 'FrontierWorkplaceUpkeepSpec', 'AmbientAnimationSpec'];
for (const plant of JSON.parse(await readFile(resolve(root, 'tools/frontier_progression.json'), 'utf8')).powerPlants.buildings) {
  const building = await readJson(`Data/Buildings/Power/${plant.id}/${plant.id}.IronTeeth.blueprint.json`);
  assert(plant.generator === 'GoodPoweredGenerator' && plant.workers === 0, `${plant.id} must be a workerless GoodPoweredGenerator plant in the catalog.`);
  assert(building.MechanicalNodeSpec.PowerOutput === plant.powerOutputHp && building.MechanicalNodeSpec.PowerInput === 0, `${plant.id} power contract is invalid.`);
  assert(building.BuildingSpec.ScienceCost === plant.scienceUnlock, `${plant.id} science differs from the catalog.`);
  for (const key of nativeGeneratorSpecs) assert(Object.hasOwn(building, key), `${plant.id} lacks the native Steam Engine ${key}.`);
  for (const key of staffedSpecs) assert(!Object.hasOwn(building, key), `${plant.id} keeps staffed-workshop ${key}.`);
  const consumed = building.GoodConsumingBuildingSpec;
  assert(consumed.FullInventoryWorkHours === plant.fullInventoryWorkHours && JSON.stringify(consumed.ConsumedGoods) ===
    JSON.stringify([{ GoodId: plant.fuel, GoodPerHour: plant.fuelPerHour }, { GoodId: 'Water', GoodPerHour: plant.waterPerHour }]),
    `${plant.id} must consume ${plant.fuelPerHour} ${plant.fuel} and ${plant.waterPerHour} Water per hour.`);
  const smoke = building.PowerGeneratorParticleControllerSpec.AttachmentIds;
  assert(smoke.length > 0 && smoke.every((a) => building.TemplateAttachmentsSpec.Attachments.some((x) => x.AttachmentId === a && x.Parent === '#Finished')),
    `${plant.id} smoke must run the study's own flue attachments.`);
}
// This checks batch production only. Continuous coolant-loss hazards and waste
// custody need runtime implementation and acceptance; blueprint presence cannot prove them.
const vault = await readJson('Data/Buildings/Storage/RadioactiveWasteVault/RadioactiveWasteVault.IronTeeth.blueprint.json');
assert(vault.StockpileSpec.MaxCapacity >= 1600, 'Radioactive waste vault capacity is too small.');
assert(expansionBuildingBlueprints.every((blueprint) => buildingCollection.TemplateCollectionSpec['Blueprints#append'].includes(blueprint)), 'One or more expansion buildings are missing from the Iron Teeth collection.');
assert(mapCollection.TemplateCollectionSpec['Blueprints#append'].includes('MapEditor/Objects/DeepOreSource/DeepOreSource.blueprint'), 'Map editor collection overlay is incomplete.');
assert(mapCollection.TemplateCollectionSpec['Blueprints#append'].includes('MapEditor/Objects/DeepOreVein/DeepOreVein.blueprint'), 'Deep Ore vein map editor overlay is incomplete.');

for (const blueprint of buildingCollection.TemplateCollectionSpec['Blueprints#append']) {
  const building = await readJson(`Data/${blueprint}.json`);
  assert(building.BlockObjectSpec.Flippable === true,
    `${building.TemplateSpec.TemplateName} disables the required native F mirror action.`);
}

console.log(JSON.stringify({
  status: 'ok',
  goods: goodIds,
  recipes: recipes.map((recipe) => recipe.RecipeSpec.Id),
  poweredBuildings: {
    DeepDrill: drill.MechanicalNodeSpec.PowerInput,
    DeepMine: mine.MechanicalNodeSpec.PowerInput,
    DeepProcessor: processor.MechanicalNodeSpec.PowerInput,
  },
  sourceCapacity: source.StockpileSpec.MaxCapacity,
}, null, 2));
