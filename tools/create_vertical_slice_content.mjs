import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { applyLategame } from './lategame_building_content.mjs';
import { lategameCost } from './lategame_costs.mjs';
import { mapObjectModel, mapObjectCollider, checkMapObjectBlueprint, applyPileGoodVisualizations } from './map_object_content.mjs';
// Late-game construction costs follow the size rule (docs/progression.md).
const ruleCost = async (id) => (await lategameCost(id)).map(([Id, Amount]) => ({ Id, Amount }));

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const sourceRoot = resolve(root, 'src', 'DeepFrontier');
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');

async function readJson(path) {
  return JSON.parse((await readFile(path, 'utf8')).replace(/^﻿/, '')); // vanilla blueprints may start with a BOM
}

async function writeJson(path, value) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

const clone = (value) => JSON.parse(JSON.stringify(value));
const setLoc = (labeled, id) => {
  labeled.DisplayNameLocKey = `Building.${id}.DisplayName`;
  labeled.DescriptionLocKey = `Building.${id}.Description`;
  labeled.FlavorDescriptionLocKey = `Building.${id}.FlavorDescription`;
};
// The deep buildings use their late-game studies (lategame_building_content.mjs).
// Template specs bound to the vanilla mesh do not describe the study: Smelter's
// smoke attachment, EfficientMine's interior navmesh edges and its
// underground cut-view model (the studies author no underground part).
const useStudyModel = (value) => {
  for (const key of ['TemplateAttachmentsSpec', 'WorkshopParticleControllerSpec', 'WindParticleControllerSpec',
    'BlockObjectNavMeshSettingsSpec']) delete value[key];
  value.BuildingModelSpec = { ...value.BuildingModelSpec, UndergroundModelName: '', UndergroundModelDepth: 0 };
  delete value.Children['#Underground'];
};

const scrapMetal = await readJson(resolve(vanillaRoot, 'Goods', 'Good.ScrapMetal.blueprint.json'));
const deepOre = clone(scrapMetal);
deepOre.GoodSpec = {
  ...deepOre.GoodSpec,
  Id: 'DeepOre',
  BackwardCompatibleIds: [],
  ContainerColor: { r: 0.16, g: 0.22, b: 0.25, a: 1.0 },
  Weight: 12,
  GoodGroupId: 'Materials',
  GoodOrder: 5070,
  ForceImport: true,
  DisplayNameLocKey: 'Good.DeepOre.DisplayName',
  PluralDisplayNameLocKey: 'Good.DeepOre.PluralDisplayName',
  // Its own icon (create_frontier_expansion_icons.mjs), not the cloned ScrapMetal one.
  Icon: 'Sprites/Goods/DeepOreIcon',
};
await writeJson(resolve(sourceRoot, 'Data', 'Goods', 'Good.DeepOre.blueprint.json'), deepOre);

const metalBlock = await readJson(resolve(vanillaRoot, 'Goods', 'Good.MetalBlock.blueprint.json'));
const deepAlloy = clone(metalBlock);
deepAlloy.GoodSpec = {
  ...deepAlloy.GoodSpec,
  Id: 'DeepAlloy',
  BackwardCompatibleIds: [],
  ContainerColor: { r: 0.33, g: 0.38, b: 0.42, a: 1.0 },
  Weight: 8,
  GoodGroupId: 'Materials',
  GoodOrder: 5080,
  ForceImport: true,
  DisplayNameLocKey: 'Good.DeepAlloy.DisplayName',
  PluralDisplayNameLocKey: 'Good.DeepAlloy.PluralDisplayName',
  // Its own icon (create_frontier_expansion_icons.mjs), not the cloned MetalBlock one.
  Icon: 'Sprites/Goods/DeepAlloyIcon',
};
await writeJson(resolve(sourceRoot, 'Data', 'Goods', 'Good.DeepAlloy.blueprint.json'), deepAlloy);
// Their own pile models (tools/map_objects.json goods, map_object_content.mjs):
// DeepOre piled as ore nuggets, DeepAlloy as ingots, not as scrap and blocks.
await applyPileGoodVisualizations();

const scrapRecipe = await readJson(resolve(vanillaRoot, 'Recipes', 'Recipe.ScrapMetal.blueprint.json'));
const deepOreRecipe = clone(scrapRecipe);
deepOreRecipe.RecipeSpec = {
  ...deepOreRecipe.RecipeSpec,
  Id: 'DeepOre',
  BackwardCompatibleIds: [],
  DisplayLocKey: 'Good.DeepOre.PluralDisplayName',
  CycleDurationInHours: 2 / 60,
  Ingredients: [
    { Id: 'DeepOre', Amount: 1 },
    { Id: 'Water', Amount: 3 },
  ],
  Products: [{ Id: 'DeepOre', Amount: 1 }],
  ProducedSciencePoints: 0,
  Fuel: '',
  CyclesFuelLasts: 0,
  FuelCapacity: 0,
  CyclesCapacity: 30,
  Icon: 'Sprites/Goods/DeepOreIcon',
};
await writeJson(resolve(sourceRoot, 'Data', 'Recipes', 'Recipe.DeepOre.blueprint.json'), deepOreRecipe);

const deepOreMineRecipe = clone(scrapRecipe);
deepOreMineRecipe.RecipeSpec = {
  ...deepOreMineRecipe.RecipeSpec,
  Id: 'DeepOre.Mine',
  BackwardCompatibleIds: [],
  DisplayLocKey: 'Good.DeepOre.PluralDisplayName',
  CycleDurationInHours: 2 / 60,
  Ingredients: [
    { Id: 'Water', Amount: 12 },
  ],
  Products: [{ Id: 'DeepOre', Amount: 4 }],
  ProducedSciencePoints: 0,
  Fuel: '',
  CyclesFuelLasts: 0,
  FuelCapacity: 0,
  CyclesCapacity: 30,
  Icon: 'Sprites/Goods/DeepOreIcon',
};
await writeJson(resolve(sourceRoot, 'Data', 'Recipes', 'Recipe.DeepOre.Mine.blueprint.json'), deepOreMineRecipe);

const metalBlockRecipe = await readJson(resolve(vanillaRoot, 'Recipes', 'Recipe.MetalBlock.blueprint.json'));
const deepAlloyRecipe = clone(metalBlockRecipe);
deepAlloyRecipe.RecipeSpec = {
  ...deepAlloyRecipe.RecipeSpec,
  Id: 'DeepAlloy',
  BackwardCompatibleIds: [],
  DisplayLocKey: 'Good.DeepAlloy.PluralDisplayName',
  CycleDurationInHours: 1.5,
  Ingredients: [
    { Id: 'DeepOre', Amount: 2 },
    { Id: 'Water', Amount: 1 },
    { Id: 'MetalPart', Amount: 1 },
  ],
  Products: [{ Id: 'DeepAlloy', Amount: 1 }],
  ProducedSciencePoints: 0,
  Fuel: '',
  CyclesFuelLasts: 0,
  FuelCapacity: 0,
  CyclesCapacity: 20,
  Icon: 'Sprites/Goods/DeepAlloyIcon',
};
await writeJson(resolve(sourceRoot, 'Data', 'Recipes', 'Recipe.DeepAlloy.blueprint.json'), deepAlloyRecipe);

const efficientMine = await readJson(resolve(vanillaRoot, 'Buildings', 'Metal', 'EfficientMine', 'EfficientMine.IronTeeth.blueprint.json'));
const deepDrill = clone(efficientMine);
// The drill is fed from the authored DeepOreSource stockpile by haulers
// (docs/source-authoring.md); EfficientMine's UndergroundRuins placement
// constraint does not apply to it.
delete deepDrill.UnderstructureConstraintSpec;
deepDrill.BuildingSpec = {
  ...deepDrill.BuildingSpec,
  SelectionSoundName: 'Mine',
  LoopingSoundName: 'GearWorkshop',
  BuildingCost: await ruleCost('DeepDrill'),
  ScienceCost: 1000,
};
deepDrill.WorkplaceSpec = {
  ...deepDrill.WorkplaceSpec,
  MaxWorkers: 3,
  DefaultWorkers: 3,
  WorkerTypeUnlockCosts: [{ WorkerType: 'Bot', ScienceCost: 2000 }],
};
deepDrill.ManufactorySpec = { ProductionRecipeIds: ['DeepOre'] };
deepDrill.TemplateSpec = {
  ...deepDrill.TemplateSpec,
  TemplateName: 'DeepDrill.IronTeeth',
  BackwardCompatibleTemplateNames: [],
};
deepDrill.PlaceableBlockObjectSpec = {
  ...deepDrill.PlaceableBlockObjectSpec,
  ToolGroupId: 'Metal',
  ToolOrder: 35,
  ToolShape: 'Square',
  Layout: 'Single',
};
deepDrill.LabeledEntitySpec = { ...deepDrill.LabeledEntitySpec };
setLoc(deepDrill.LabeledEntitySpec, 'DeepDrill');
deepDrill.LabeledEntitySpec.Icon = 'Buildings/Metal/EfficientMine/EfficientMineIcon';
deepDrill.MechanicalBuildingSpec = {};
deepDrill.MechanicalNodeSpec = { PowerOutput: 0, PowerInput: 1000, IsShaft: false };
// Every vanilla powered consumer carries the native connector target: it draws the gear socket where a
// shaft or generator meets a transput (MechanicalConnectorActivator). EfficientMine is unpowered.
deepDrill.MechanicalConnectorTargetSpec = {};
deepDrill.MechanicalNodeAnimatorSpec = { MinSpeedMultiplier: 0.0 };
deepDrill.Children['#Finished'].TimbermeshSpec.Model = 'Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.Model';
deepDrill.LabeledEntitySpec.Icon = 'Buildings/Metal/DeepDrill/DeepDrillIcon';
useStudyModel(deepDrill);
await applyLategame(deepDrill, 'DeepDrill');
await writeJson(resolve(sourceRoot, 'Data', 'Buildings', 'Metal', 'DeepDrill', 'DeepDrill.IronTeeth.blueprint.json'), deepDrill);

// The vein marker is the Deep Mine's understructure; the mine's core is sized
// from it below.
const undergroundRuins = await readJson(resolve(vanillaRoot, 'MapEditor', 'Ruins', 'UndergroundRuins', 'UndergroundRuins.blueprint.json'));
const deepOreVein = clone(undergroundRuins);
for (const key of ['BlockObjectTerrainCutoutSpec', 'DryObjectSpec', 'DryObjectModelSpec']) delete deepOreVein[key];
deepOreVein.TemplateSpec = {
  ...deepOreVein.TemplateSpec,
  TemplateName: 'DeepOreVein',
  BackwardCompatibleTemplateNames: [],
};
deepOreVein.PlaceableBlockObjectSpec = {
  ...deepOreVein.PlaceableBlockObjectSpec,
  ToolGroupId: 'MapEditorObjects',
  ToolOrder: 1011,
  DevModeTool: true,
};
deepOreVein.LabeledEntitySpec = { ...deepOreVein.LabeledEntitySpec };
setLoc(deepOreVein.LabeledEntitySpec, 'DeepOreVein');
deepOreVein.LabeledEntitySpec.Icon = 'MapEditor/Objects/DeepOreVein/DeepOreVeinIcon';
deepOreVein.BlockObjectModelSpec = { FullModelName: '#Finished', UncoveredModelName: '', UndergroundModelName: '', UndergroundModelDepth: 0 };
// Own model (tools/map_objects.json, build_map_objects.py) and a collider:
// the vanilla UndergroundRuins collider was dropped with its children, which
// left the vein unselectable in the map editor.
deepOreVein.Children = {
  '#Finished': {
    TimbermeshSpec: { Model: mapObjectModel('DeepOreVein') },
    CollidersSpec: mapObjectCollider('DeepOreVein'),
  },
};
checkMapObjectBlueprint('DeepOreVein', deepOreVein, '#Finished');
await writeJson(resolve(sourceRoot, 'Data', 'MapEditor', 'Objects', 'DeepOreVein', 'DeepOreVein.blueprint.json'), deepOreVein);

const deepMine = clone(efficientMine);
deepMine.BuildingSpec = {
  ...deepMine.BuildingSpec,
  SelectionSoundName: 'Mine',
  LoopingSoundName: 'GearWorkshop',
  BuildingCost: await ruleCost('DeepMine'),
  ScienceCost: 6000,
};
deepMine.WorkplaceSpec = {
  ...deepMine.WorkplaceSpec,
  MaxWorkers: 6,
  DefaultWorkers: 6,
  WorkerTypeUnlockCosts: [{ WorkerType: 'Bot', ScienceCost: 6000 }],
};
deepMine.ManufactorySpec = { ProductionRecipeIds: ['DeepOre.Mine'] };
deepMine.TemplateSpec = {
  ...deepMine.TemplateSpec,
  TemplateName: 'DeepMine.IronTeeth',
  BackwardCompatibleTemplateNames: [],
};
deepMine.PlaceableBlockObjectSpec = {
  ...deepMine.PlaceableBlockObjectSpec,
  ToolGroupId: 'Metal',
  ToolOrder: 37,
  ToolShape: 'Square',
  Layout: 'Single',
};
deepMine.LabeledEntitySpec = { ...deepMine.LabeledEntitySpec };
setLoc(deepMine.LabeledEntitySpec, 'DeepMine');
deepMine.LabeledEntitySpec.Icon = 'Buildings/Metal/DeepMine/DeepMineIcon';
deepMine.UnderstructureConstraintSpec = { UnderstructureTemplateNames: ['DeepOreVein'] };
deepMine.MechanicalBuildingSpec = {};
deepMine.MechanicalNodeSpec = { PowerOutput: 0, PowerInput: 4000, IsShaft: false };
deepMine.MechanicalConnectorTargetSpec = {};
deepMine.MechanicalNodeAnimatorSpec = { MinSpeedMultiplier: 0.0 };
deepMine.Children['#Finished'].TimbermeshSpec.Model = 'Buildings/Metal/DeepMine/DeepMine.IronTeeth.Model';
useStudyModel(deepMine);
// Ground core over the vein: tiles x 2-6, y 1-5, centred on the study's shaft
// collar (lategame_DeepMine.py collar x 2.7-6.1, y 2.1-4.8; opening centre
// 4.4, 3.45). Its four corner cells are building cells, so the vein has a
// single valid alignment, as under vanilla EfficientMine.
await applyLategame(deepMine, 'DeepMine', {
  understructure: { core: [2, 1, 6, 5], size: [deepOreVein.BlockObjectSpec.Size.X, deepOreVein.BlockObjectSpec.Size.Y] },
});
await writeJson(resolve(sourceRoot, 'Data', 'Buildings', 'Metal', 'DeepMine', 'DeepMine.IronTeeth.blueprint.json'), deepMine);

const smelter = await readJson(resolve(vanillaRoot, 'Buildings', 'Metal', 'Smelter', 'Smelter.IronTeeth.blueprint.json'));
const deepProcessor = clone(smelter);
deepProcessor.BuildingSpec = {
  ...deepProcessor.BuildingSpec,
  SelectionSoundName: 'Smelter',
  LoopingSoundName: '',
  BuildingCost: await ruleCost('DeepProcessor'),
  ScienceCost: 1200,
};
deepProcessor.WorkplaceSpec = {
  ...deepProcessor.WorkplaceSpec,
  MaxWorkers: 2,
  DefaultWorkers: 2,
  WorkerTypeUnlockCosts: [{ WorkerType: 'Bot', ScienceCost: 2200 }],
};
// Surface processing of deep ore: alloy, plus the coal, crude oil and uranium
// recipes authored in create_frontier_expansion_content.mjs.
deepProcessor.ManufactorySpec = { ProductionRecipeIds: ['DeepAlloy', 'DeepCoal', 'DeepOil', 'DeepUranium'] };
deepProcessor.TemplateSpec = {
  ...deepProcessor.TemplateSpec,
  TemplateName: 'DeepProcessor.IronTeeth',
  BackwardCompatibleTemplateNames: [],
};
deepProcessor.PlaceableBlockObjectSpec = {
  ...deepProcessor.PlaceableBlockObjectSpec,
  ToolGroupId: 'Metal',
  ToolOrder: 36,
  ToolShape: 'Square',
  Layout: 'Single',
};
deepProcessor.LabeledEntitySpec = { ...deepProcessor.LabeledEntitySpec };
setLoc(deepProcessor.LabeledEntitySpec, 'DeepProcessor');
deepProcessor.LabeledEntitySpec.Icon = 'Buildings/Metal/Smelter/SmelterIcon';
deepProcessor.MechanicalNodeSpec = { PowerOutput: 0, PowerInput: 500, IsShaft: false };
deepProcessor.Children['#Finished'].TimbermeshSpec.Model = 'Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.Model';
deepProcessor.LabeledEntitySpec.Icon = 'Buildings/Metal/DeepProcessor/DeepProcessorIcon';
useStudyModel(deepProcessor);
await applyLategame(deepProcessor, 'DeepProcessor');
await writeJson(resolve(sourceRoot, 'Data', 'Buildings', 'Metal', 'DeepProcessor', 'DeepProcessor.IronTeeth.blueprint.json'), deepProcessor);

const reservePile = await readJson(resolve(vanillaRoot, 'MapEditor', 'Objects', 'ReservePile', 'ReservePile.blueprint.json'));
const deepOreSource = clone(reservePile);
deepOreSource.BuildingSpec = {
  ...deepOreSource.BuildingSpec,
  BuildingCost: [],
  ScienceCost: 0,
  PlaceFinished: true,
  FinishableWithBeaversOnSite: true,
};
deepOreSource.TemplateSpec = {
  ...deepOreSource.TemplateSpec,
  TemplateName: 'DeepOreSource',
  BackwardCompatibleTemplateNames: [],
};
deepOreSource.StockpileSpec = { MaxCapacity: 4000, WhitelistedGoodType: 'Pileable' };
deepOreSource.PlaceableBlockObjectSpec = {
  ...deepOreSource.PlaceableBlockObjectSpec,
  ToolGroupId: 'MapEditorObjects',
  ToolOrder: 1010,
  DevModeTool: true,
};
deepOreSource.LabeledEntitySpec = { ...deepOreSource.LabeledEntitySpec };
setLoc(deepOreSource.LabeledEntitySpec, 'DeepOreSource');
deepOreSource.LabeledEntitySpec.Icon = 'MapEditor/Objects/DeepOreSource/DeepOreSourceIcon';
deepOreSource.StockpileGoodPileVisualizerSpec = {
  ...deepOreSource.StockpileGoodPileVisualizerSpec,
  GoodPileVisualizations: ['DeepOre'],
};
// The authored source marker has its own ore geometry; vanilla dirt/pile
// visualization IDs do not describe DeepOre.
delete deepOreSource.StockpileGoodPileVisualizerSpec;
delete deepOreSource.StockpilePlaneVisualizerSpec;
deepOreSource.Children['#Finished'].TimbermeshSpec.Model = mapObjectModel('DeepOreSource');
// The ore mound stands 1.3 high; the ReservePile collider covered 0.49.
deepOreSource.Children['#Finished'].CollidersSpec = mapObjectCollider('DeepOreSource');
checkMapObjectBlueprint('DeepOreSource', deepOreSource, '#Finished');
await writeJson(resolve(sourceRoot, 'Data', 'MapEditor', 'Objects', 'DeepOreSource', 'DeepOreSource.blueprint.json'), deepOreSource);

await writeJson(resolve(sourceRoot, 'Data', 'GoodCollections', 'GoodCollection.IronTeeth.blueprint.json'), {
  GoodCollectionSpec: {
    CollectionId: 'IronTeeth',
    'Goods#append': ['DeepOre', 'DeepAlloy'],
  },
});
await writeJson(resolve(sourceRoot, 'Data', 'TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json'), {
  TemplateCollectionSpec: {
    CollectionId: 'Buildings.IronTeeth',
    'Blueprints#append': [
      'Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.blueprint',
      'Buildings/Metal/DeepMine/DeepMine.IronTeeth.blueprint',
      'Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.blueprint',
    ],
  },
});
await writeJson(resolve(sourceRoot, 'Data', 'TemplateCollections', 'TemplateCollection.MapEditor.Common.blueprint.json'), {
  TemplateCollectionSpec: {
    CollectionId: 'Common',
    'Blueprints#append': [
      'MapEditor/Objects/DeepOreSource/DeepOreSource.blueprint',
      'MapEditor/Objects/DeepOreVein/DeepOreVein.blueprint',
    ],
  },
});

await mkdir(resolve(sourceRoot, 'Data', 'Localizations'), { recursive: true });
const localizationRows = [
  ['ID', 'Text', 'Comment'],
  ['Building.DeepDrill.DisplayName', 'Deep Drill', 'Deep Frontier'],
  ['Building.DeepDrill.Description', 'Extracts one unit of Deep Ore from an authored source stockpile using water and 1000 hp.', 'Deep Frontier'],
  ['Building.DeepDrill.FlavorDescription', 'The first boring machine turns a finite deposit into a surface supply chain.', 'Deep Frontier'],
  ['Building.DeepMine.DisplayName', 'Deep Mine', 'Deep Frontier'],
  ['Building.DeepMine.Description', 'Extracts four Deep Ore every cycle from a marked vein using water and 4000 hp.', 'Deep Frontier'],
  ['Building.DeepMine.FlavorDescription', 'The vein is endless; the power bill is not.', 'Deep Frontier'],
  ['Building.DeepProcessor.DisplayName', 'Deep Ore Processor', 'Deep Frontier'],
  ['Building.DeepProcessor.Description', 'Refines deep ore into a dense industrial alloy.', 'Deep Frontier'],
  ['Building.DeepProcessor.FlavorDescription', 'The ore is useless until the surface factory learns how to tame it.', 'Deep Frontier'],
  ['Building.DeepOreSource.DisplayName', 'Deep Ore Source', 'Deep Frontier'],
  ['Building.DeepOreSource.Description', 'Map editor stockpile for a finite authored Deep Ore deposit.', 'Deep Frontier'],
  ['Building.DeepOreSource.FlavorDescription', 'Fill this marker with Deep Ore while authoring the map; the drill consumes that deposit.', 'Deep Frontier'],
  ['Building.DeepOreVein.DisplayName', 'Deep Ore Vein', 'Deep Frontier'],
  ['Building.DeepOreVein.Description', 'Map editor understructure that authorizes a permanent Deep Mine.', 'Deep Frontier'],
  ['Building.DeepOreVein.FlavorDescription', 'This geological seam is inexhaustible, but reaching it requires an industrial mine.', 'Deep Frontier'],
  ['Good.DeepOre.DisplayName', 'Deep ore', 'Deep Frontier'],
  ['Good.DeepOre.PluralDisplayName', 'Deep ore', 'Deep Frontier'],
  ['Good.DeepAlloy.DisplayName', 'Deep alloy', 'Deep Frontier'],
  ['Good.DeepAlloy.PluralDisplayName', 'Deep alloy', 'Deep Frontier'],
];
const csvCell = (value) => {
  const text = String(value);
  return /[\",\r\n]/.test(text) ? `\"${text.replaceAll('\"', '\"\"')}\"` : text;
};
const localizationCsv = localizationRows.map((row) => row.map(csvCell).join(',')).join('\n') + '\n';
await writeFile(resolve(sourceRoot, 'Data', 'Localizations', 'enUS.csv'), localizationCsv, 'utf8');

console.log('Created Deep Frontier vertical-slice blueprints and localization.');

// Keep the complete data layer reproducible from the original entry point.
// The expansion generator only adds namespaced files and appends to the same
// Iron Teeth collections/localization table.
await import('./create_frontier_expansion_content.mjs');
await import('./create_construction_material_content.mjs');
await import('./vanilla_tool_overrides.mjs');
// Radiation (docs/radiation.md): sludge/contaminated-water goods, the
// Irradiation need and Hospital treatment, export/outfall/recovery buildings.
// Extends the generated Hospital, collections and localization, so it runs
// after them; before workforce risks and the automation audit so both see
// the radiation buildings.
await (await import('./radiation_content.mjs')).applyRadiationContent();
// Contamination Sensor substance choice (docs/radiation.md): localization rows
// only; the native sensor blueprint is not patched.
await (await import('./contamination_sensor_content.mjs')).applyContaminationSensor();
// Workforce risks (tools/workforce_risks.json): after every building, recipe
// and localization row exists, before the automation audit checks its specs.
await (await import('./workforce_risk_content.mjs')).applyWorkforceRisks();
// Bot upkeep (tools/workforce_risks.json botMaintenance/botAssembly): needs the
// workforce bot-wear specs; before the automation audit checks its spec and patch.
await (await import('./bot_upkeep_content.mjs')).applyBotUpkeep();
// Platformable flat roofs (tools/roof_decks.json, tools/roof_deck_content.mjs): a
// design step after every building's blocks are final and before the connection
// step, which offers roof faces only on stackable blocks.
await (await import('./roof_deck_content.mjs')).applyRoofDecks();
// Power shafts and Timber Pipes on every flat exterior face
// (outputs/connection-faces, tools/connection_content.mjs): after every
// building blueprint, its blocks, doors and pipe sockets exist (radiation and
// cryogenic sockets included).
await (await import('./connection_content.mjs')).applyConnections();
// Smog (tools/smog_content.json): after every building blueprint and its
// vanilla smoke exist, including the kiln and laboratory written by the
// construction-material generator; before the automation audit.
await (await import('./smog_building_content.mjs')).applySmog();
await (await import('./building_sounds_content.mjs')).applyBuildingSounds(); // Native sounds (tools/building_sounds.json, docs/sounds.md): needs every building template, so after radiation.
// Toolbar sub-groups (tools/tool_groups.json, Moddable Tool Groups): moves buildings into
// Deep Frontier sub-groups of the native groups, after every building template exists.
await (await import('./tool_group_content.mjs')).applyToolGroups();
// Status icon anchors (tools/status_icon_content.mjs, Scripts/StatusIconAnchor.cs): from each
// building's final blocks, so after connections (roof decks) and every family generator.
await (await import('./status_icon_content.mjs')).applyStatusIconAnchors();
// Last: every generated building must keep its declared automation role.
await import('./automation_building_content.mjs');
