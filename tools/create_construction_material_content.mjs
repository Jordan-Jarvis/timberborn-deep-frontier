import { readFile, writeFile, mkdir } from 'node:fs/promises';
import { mapObjectModel, mapObjectCollider, checkMapObjectBlueprint } from './map_object_content.mjs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {applyIndustrialLayout} from './industrial_building_content.mjs';
import {applyPitLayout} from './pit_building_content.mjs';
import {structuralBlueprints} from './structural_building_content.mjs';
import {hydroBlueprint} from './hydro_building_content.mjs';
import {researchContent} from './research_building_content.mjs';

const root = fileURLToPath(new URL('../', import.meta.url));
const dataRoot = resolve(root, 'src/DeepFrontier/Data');
const vanillaRoot = resolve(root, 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources');
const catalog = JSON.parse(await readFile(new URL('./construction_materials.json', import.meta.url), 'utf8'));
const read = async (base, path) => JSON.parse((await readFile(resolve(base, path), 'utf8')).replace(/^﻿/, '')); // vanilla blueprints may start with a BOM
const write = async (path, value) => {
  const target = resolve(dataRoot, path);
  await mkdir(dirname(target), { recursive: true });
  await writeFile(target, JSON.stringify(value, null, 2) + '\n');
};
async function appendCollection(path, spec, field, values) {
  const value = await read(dataRoot, path);
  const existing = value[spec][field];
  if (!Array.isArray(existing)) throw new Error(`Missing collection array: ${path}`);
  for (const id of values) if (existing.includes(id)) throw new Error(`Duplicate generated ID ${id}; run create_vertical_slice_content.mjs from the start.`);
  value[spec][field] = [...existing, ...values];
  await write(path, value);
}
const amount = ([Id, Amount]) => ({ Id, Amount });
const modelPath = id => `Buildings/Metal/${id}/${id}.IronTeeth`;
const rows = [];
await write('MaterialCollections/MaterialCollection.DeepFrontierIndustrial.blueprint.json', {
  MaterialCollectionSpec:{CollectionId:'Common',Materials:Array.from({length:27},(_,i)=>`Materials/DeepFrontierIndustrial/DFIndustrial${String(i).padStart(2,'0')}`)},
});
// Map objects are loaded without a faction in the editor. Register their exact
// authored materials in Common as well; native MaterialRepository deduplicates assets.
await write('MaterialCollections/MaterialCollection.DeepFrontierMapResources.blueprint.json', {
  MaterialCollectionSpec: { CollectionId: 'Common', Materials: [
    'Materials/UberAtlas/Materials/IronTeeth/BaseMetal.IronTeeth',
    'Materials/UberAtlas/Materials/IronTeeth/PaintedMetal.IronTeeth',
    'Materials/UberAtlas/Materials/IronTeeth/Plaster_Orange.IronTeeth',
    'Materials/UberAtlas/Materials/IronTeeth/Plaster_White.IronTeeth',
  ] },
});
function label(id, name, description, icon) {
  rows.push([`Building.${id}.DisplayName`, name], [`Building.${id}.Description`, description],
    [`Building.${id}.FlavorDescription`, 'The next age begins with a solid foundation.']);
  return { DisplayNameLocKey: `Building.${id}.DisplayName`, DescriptionLocKey: `Building.${id}.Description`,
    FlavorDescriptionLocKey: `Building.${id}.FlavorDescription`, Icon: icon };
}
function collision([width, depth, height]) {
  return { BoxColliders: [{ Center: { X: width / 2, Y: height / 2, Z: depth / 2 },
    Size: { X: width, Y: height, Z: depth } }], SphereColliders: [], CapsuleColliders: [] };
}
function buildingGeometry(value, [width, depth, height], groundOnly, entranceX) {
  value.BlockObjectSpec = {
    Size: { X: width, Y: depth, Z: height },
    Blocks: Array.from({ length: width * depth * height }, (_, index) => ({
      MatterBelow: index < width * depth ? (groundOnly ? 'Ground' : 'GroundOrStackable') : 'Any',
      Occupations: 'All', Stackable: 'None', OccupyAllBelow: false, Underground: false,
    })),
    Entrance: { HasEntrance: true, Coordinates: { X: entranceX, Y: -1, Z: 0 } },
    BaseZ: 0, Overridable: false, Flippable: true,
  };
  value.BuildingAccessibleSpec.LocalAccess = { X: entranceX + 0.5, Y: 0, Z: 0.2 };
}
for (const good of catalog.goods) {
  const value = await read(vanillaRoot, 'Goods/Good.Paper.blueprint.json');
  const [r, g, b] = good.color;
  Object.assign(value.GoodSpec, { Id: good.id, BackwardCompatibleIds: [], GoodGroupId: 'Materials',
    GoodOrder: 5400 + catalog.goods.indexOf(good), Weight: good.weight, ForceImport: true,
    Icon: `Sprites/Goods/${good.id}Icon`, ContainerColor: { r, g, b, a: 1 },
    DisplayNameLocKey: `Good.${good.id}.DisplayName`, PluralDisplayNameLocKey: `Good.${good.id}.PluralDisplayName` });
  rows.push([`Good.${good.id}.DisplayName`, good.name], [`Good.${good.id}.PluralDisplayName`, good.name]);
  await write(`Goods/Good.${good.id}.blueprint.json`, value);
}
// Register the authored goods before recipes/buildings validate their inputs.
await appendCollection('GoodCollections/GoodCollection.IronTeeth.blueprint.json',
  'GoodCollectionSpec', 'Goods#append', catalog.goods.map(g => g.id));
for (const recipe of catalog.recipes) {
  const value = await read(vanillaRoot, 'Recipes/Recipe.MetalBlock.blueprint.json');
  Object.assign(value.RecipeSpec, { Id: recipe.id, BackwardCompatibleIds: [], DisplayLocKey: `Recipe.${recipe.id}.DisplayName`,
    CycleDurationInHours: recipe.hours, Ingredients: recipe.inputs.map(amount), Products: recipe.outputs.map(amount),
    ProducedSciencePoints: 0, Fuel: recipe.fuel, CyclesFuelLasts: recipe.fuelCycles, FuelCapacity: recipe.fuelCapacity,
    CyclesCapacity: 4, Icon: `Sprites/Goods/${recipe.outputs[0][0]}Icon` });
  rows.push([`Recipe.${recipe.id}.DisplayName`, recipe.name]);
  await write(`Recipes/Recipe.${recipe.id}.blueprint.json`, value);
}
const buildingPaths = [];
for (const building of catalog.buildings) {
  const { id, kind, size } = building;
  let template;
  switch (kind) {
    case 'pit': template = 'Buildings/Metal/ScavengerFlag/ScavengerFlag.IronTeeth.blueprint.json'; break;
    case 'quarry': template = 'Buildings/Metal/EfficientMine/EfficientMine.IronTeeth.blueprint.json'; break;
    case 'crusher': case 'kiln': case 'mixer': template = 'Buildings/Metal/Smelter/Smelter.IronTeeth.blueprint.json'; break;
    default: throw new Error(`Unknown construction building kind: ${kind}`);
  }
  const value = await read(vanillaRoot, template);
  value.TemplateSpec.TemplateName = `${id}.IronTeeth`;
  value.TemplateSpec.BackwardCompatibleTemplateNames = [];
  value.BuildingSpec.BuildingCost = building.cost.map(amount);
  value.BuildingSpec.ScienceCost = building.science;
  Object.assign(value.WorkplaceSpec, { MaxWorkers: building.workers, DefaultWorkers: building.workers,
    WorkerTypeUnlockCosts: [{ WorkerType: 'Bot', ScienceCost: building.botScience }] });
  Object.assign(value.PlaceableBlockObjectSpec, { ToolGroupId: 'Metal', ToolOrder: 70 + catalog.buildings.indexOf(building), Layout: 'Single' });
  value.LabeledEntitySpec = label(id, building.name, building.description, `Buildings/Metal/${id}/Icon`);
  if (kind === 'pit') {
    delete value.ScavengerSpec;
    value.MineralPitSpec = { GoodId: building.good };
    value.YieldRemovingBuildingSpec.ResourceGroup = `DeepFrontier${building.good}`;
    value.SimpleOutputInventorySpec.Capacity = 40;
  } else {
    value.ManufactorySpec.ProductionRecipeIds = building.recipes;
    value.MechanicalNodeSpec = { PowerInput: building.hp, PowerOutput: 0, IsShaft: false };
    value.MechanicalBuildingSpec = {};
    value.MechanicalNodeAnimatorSpec = { MinSpeedMultiplier: 0 };
    value.MechanicalConnectorTargetSpec = {};
    value.TransputProviderSpec = { IgnoreRotation: false, Transputs: [
      { Coordinates: { X: 0, Y: 1, Z: 0 }, Directions: 'Left, Bottom', ReverseRotation: false },
      { Coordinates: { X: size[0] - 1, Y: 1, Z: 0 }, Directions: 'Right, Bottom', ReverseRotation: false },
    ] };
  }
  // Quarry block and walking topology are the native 5x5 mine contract.
  if (kind === 'quarry') {
    value.UnderstructureConstraintSpec.UnderstructureTemplateNames = [building.source];
  } else {
    buildingGeometry(value, size, kind === 'pit', kind === 'crusher' ? 0 : Math.floor(size[0] / 2));
  }
  // These hooks target vanilla mesh nodes or smoke attachments, absent from our authored art.
  for (const key of ['TransformSlotInitializerSpec', 'WorkplaceSlotManagerSpec', 'WorkshopWorkerHiderSpec', 'TemplateAttachmentsSpec',
    'WorkshopParticleControllerSpec', 'WindParticleControllerSpec']) delete value[key];
  value.BuildingModelSpec.UndergroundModelName = '';
  value.BuildingModelSpec.UndergroundModelDepth = 0;
  // One authored unfinished model is the construction base; there are no later stages.
  value.ConstructionSiteProgressVisualizerSpec = { ProgressThresholds: [] };
  value.Children = {
    '#Finished': { TimbermeshSpec: { Model: `${modelPath(id)}.Model` }, CollidersSpec: collision(size) },
    '#Unfinished': { Children: { ConstructionStage0: {
      TimbermeshSpec: { Model: `${modelPath(id)}.ConstructionStage0.Model` }, CollidersSpec: collision(size),
    } } },
  };
  if (['crusher','kiln','quarry','mixer'].includes(kind)) await applyIndustrialLayout(value,building);
  if (kind==='pit') await applyPitLayout(value,building);
  const path = `Buildings/Metal/${id}/${id}.IronTeeth.blueprint`;
  buildingPaths.push(path);
  await write(`${path}.json`, value);
}
const structures=await structuralBlueprints();
for(const entry of structures) {
  await write(entry.path,entry.blueprint);
  buildingPaths.push(entry.path.slice(0,-5));
  rows.push(...entry.rows);
}
const turbine=await hydroBlueprint();
await write(turbine.path,turbine.blueprint);
buildingPaths.push(turbine.path.slice(0,-5));
rows.push(...turbine.rows);
const research=await researchContent();
for(const entry of research.buildings) {
  await write(entry.path,entry.blueprint);
  buildingPaths.push(entry.path.slice(0,-5));
  rows.push(...entry.rows);
}
for(const entry of research.recipes) {
  await write(entry.path,entry.blueprint);
  rows.push(...entry.rows);
}
const sourcePaths = [];
for (const source of catalog.sources) {
  const path = `MapEditor/Objects/${source.id}/${source.id}`;
  let value;
  if (source.kind === 'finite') {
    value = await read(vanillaRoot, 'MapEditor/Ruins/RuinColumnH1/RuinColumnH1.blueprint.json');
    delete value.RuinSpec;
    value.MineralDepositSpec = { Yielder: { YielderComponentName: 'Mineral',
      Yield: { Id: source.good, Amount: source.yield }, RemovalTimeInHours: source.removalHours, ResourceGroup: `DeepFrontier${source.good}` } };
  } else if (source.kind === 'permanent') {
    value = await read(vanillaRoot, 'MapEditor/Ruins/UndergroundRuins/UndergroundRuins.blueprint.json');
    for (const key of ['BlockObjectTerrainCutoutSpec', 'DryObjectSpec', 'DryObjectModelSpec']) delete value[key];
  } else throw new Error(`Unknown source kind: ${source.kind}`);
  value.TemplateSpec.TemplateName = source.id;
  value.TemplateSpec.BackwardCompatibleTemplateNames = [];
  Object.assign(value.PlaceableBlockObjectSpec, { ToolGroupId: 'MapEditorObjects',
    ToolOrder: 1020 + catalog.sources.indexOf(source), Layout: 'Single', DevModeTool: true });
  value.LabeledEntitySpec = label(source.id, source.name, source.description, `${path}Icon`);
  value.BlockObjectModelSpec = { FullModelName: '#Models', UncoveredModelName: '', UndergroundModelName: '', UndergroundModelDepth: 0 };
  // Own models and colliders that fit them (tools/map_objects.json): the seams
  // are 0.3 high understructures under a quarry, not full-layer boxes.
  value.Children = { '#Models': { TimbermeshSpec: { Model: mapObjectModel(source.id) }, CollidersSpec: mapObjectCollider(source.id) } };
  checkMapObjectBlueprint(source.id, value, '#Models');
  sourcePaths.push(`${path}.blueprint`);
  await write(`${path}.blueprint.json`, value);
}
await write('RemoveYieldStrategies/RemoveYieldStrategy.Ruins.blueprint.json', {
  RemoveYieldStrategySpec: { Id: 'Ruins', 'CompatibleResourceGroups#append': ['DeepFrontierSandstone', 'DeepFrontierLimestone'] },
});
for (const [path, spec, field, values] of [
  ['TemplateCollections/TemplateCollection.Buildings.IronTeeth.blueprint.json', 'TemplateCollectionSpec', 'Blueprints#append', buildingPaths],
  ['TemplateCollections/TemplateCollection.MapEditor.Common.blueprint.json', 'TemplateCollectionSpec', 'Blueprints#append', sourcePaths],
]) {
  await appendCollection(path, spec, field, values);
}
const cell = value => {
  if (typeof value !== 'string') throw new TypeError('Localization cells require strings.');
  return /[",\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
};
const localizationPath = resolve(dataRoot, 'Localizations/enUS.csv');
const localization = await readFile(localizationPath, 'utf8');
await writeFile(localizationPath, localization + rows.map(row => [...row, 'Deep Frontier construction materials'].map(cell).join(',')).join('\n') + '\n');
console.log(`Construction chain: ${catalog.goods.length} goods, ${catalog.buildings.length} production buildings, ${structures.length} structures, ${catalog.sources.length} sources, ${catalog.recipes.length} recipes.`);
