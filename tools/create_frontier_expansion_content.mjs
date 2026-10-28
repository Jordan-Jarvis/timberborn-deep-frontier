import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {applyRestaurant,authorRestaurantNeed,RESTAURANT_LOCALIZATION} from './civic_building_content.mjs';
import {applyFishery,applyHatchery,authorShoreFishing,WATERSIDE_ROWS} from './fishery_building_content.mjs';
import {applyHospital,authorHospitalNeed,HOSPITAL_DESCRIPTION,HOSPITAL_LOCALIZATION} from './hospital_building_content.mjs';
import {applyGroceryStore,authorGroceryNeed} from './grocery_building_content.mjs';
import {LATEGAME,applyLategame,studyPipePort} from './lategame_building_content.mjs';
import {lategameCost} from './lategame_costs.mjs';
import {loadWorkforceConfig,trainingRecipeIds} from './workforce_risk_content.mjs';

// Data-only expansion layer. Every template is cloned from a captured 1.1
// Iron Teeth/Folktails blueprint so the importer gets the complete nested
// specs (colliders, access, animation, construction stages, and UI hooks).
// The new IDs and recipes are namespaced by this mod's content collection.

const root = resolve(fileURLToPath(new URL('../', import.meta.url)));
const sourceRoot = resolve(root, 'src', 'DeepFrontier');
const vanillaRoot = resolve(root, 'vendor', 'timberborn-modding', 'Assets', 'Tools', 'ImportedAssets', 'Editor', 'Resources');

async function readJson(path) {
  return JSON.parse(await readFile(path, 'utf8'));
}

async function writeJson(path, value) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, `${JSON.stringify(value, null, 2)}\n`, 'utf8');
}

const clone = (value) => JSON.parse(JSON.stringify(value));
const vanilla = (relative) => resolve(vanillaRoot, relative);
const data = (...parts) => resolve(sourceRoot, 'Data', ...parts);
const icon = (id) => `Sprites/Goods/${id}Icon`;
// Reactor coolant travels by Timber Pipes: the treatment plant releases
// ReactorCoolantWater (a Liquid good) and the reactor accepts it.
const coolantPipePorts = await readJson(resolve(root, 'tools', 'coolant_pipe_ports.json'));
function coolantPorts(id) {
  const spec = coolantPipePorts[id];
  if (!spec?.Ports?.length) throw new Error(`Missing coolant pipe ports for ${id}`);
  return clone(spec);
}
const progression = await readJson(resolve(root, 'tools/frontier_progression.json'));
const constructionCosts = await readJson(resolve(root, 'tools/building_construction_costs.json'));
// Technical School courses are product-less training recipes owned by
// tools/workforce_risks.json and written by workforce_risk_content.mjs.
const trainingRecipes = trainingRecipeIds(await loadWorkforceConfig(root));

const goodDefinitions = [
  ['Compost', 'solid', 'Ingredients', 5195, 0.28, 0.45, 'compost'],
  ['Coal', 'solid', 'Materials', 5196, 0.12, 0.14, 'coal'],
  ['Chemical', 'liquid', 'Ingredients', 10055, 0.42, 0.52, 'chemical'],
  ['RecoveredArtifact', 'solid', 'Materials', 5197, 0.62, 0.48, 'artifact'],
  ['Fertilizer', 'solid', 'Ingredients', 5200, 0.58, 0.72, 'fertilizer'],
  ['FreshFish', 'food', 'Food', 11090, 0.20, 0.55, 'fish'],
  ['JuvenileFish', 'solid', 'Ingredients', 5205, 0.20, 0.55, 'juvenile'],
  ['FishOil', 'liquid', 'Ingredients', 10040, 0.95, 0.74, 'oil'],
  ['CannedFish', 'food', 'Food', 11100, 0.32, 0.58, 'can'],
  ['EmergencyRation', 'food', 'Food', 11110, 0.38, 0.58, 'ration'],
  ['PackagedFood', 'food', 'Food', 11120, 0.28, 0.58, 'package'],
  ['Medicine', 'solid', 'Ingredients', 5210, 0.72, 0.84, 'medicine'],
  ['MedicalFood', 'food', 'Food', 11130, 0.45, 0.58, 'medical'],
  ['SweetBerryCake', 'food', 'Food', 11140, 0.79, 0.36, 'cake'],
  ['Flux', 'solid', 'Materials', 5090, 0.25, 0.27, 'flux'],
  ['HighGradeSteel', 'solid', 'Materials', 5100, 0.34, 0.38, 'steel'],
  ['Alloy', 'solid', 'Materials', 5110, 0.38, 0.44, 'alloy'],
  ['Polymer', 'solid', 'Materials', 5120, 0.18, 0.52, 'polymer'],
  ['Lubricant', 'liquid', 'Ingredients', 10050, 0.95, 0.70, 'lubricant'],
  ['MachineCore', 'solid', 'Materials', 5130, 0.42, 0.50, 'core'],
  ['PowerModule', 'solid', 'Materials', 5140, 0.28, 0.45, 'power'],
  ['FilterMedia', 'solid', 'Materials', 5150, 0.70, 0.70, 'filter'],
  ['ConcentratedWaste', 'solid', 'Materials', 5160, 0.30, 0.23, 'waste'],
  ['CrudeOil', 'liquid', 'Ingredients', 10060, 0.10, 0.08, 'oil'],
  ['UraniumOre', 'solid', 'Materials', 5170, 0.20, 0.28, 'uranium'],
  ['Yellowcake', 'solid', 'Materials', 5180, 0.72, 0.68, 'yellowcake'],
  ['EnrichedFuel', 'solid', 'Materials', 5190, 0.85, 0.44, 'fuel'],
  ['PureWater', 'liquid', 'Ingredients', 10120, 0.20, 0.70, 'purewater'],
  ['HydrogenGas', 'liquid', 'Ingredients', 10130, 0.30, 0.82, 'hydrogen'],
  ['OxygenGas', 'liquid', 'Ingredients', 10140, 0.38, 0.82, 'oxygen'],
  ['LiquidHydrogen', 'liquid', 'Ingredients', 10150, 0.16, 0.72, 'liquidhydrogen'],
  ['LiquidOxygen', 'liquid', 'Ingredients', 10160, 0.32, 0.72, 'liquidoxygen'],
  ['Cryocoolant', 'liquid', 'Ingredients', 10170, 0.20, 0.50, 'coolant'],
  ['RadioactiveWaste', 'solid', 'Materials', 5200, 0.18, 0.18, 'radioactive'],
  ['RocketAirframe', 'solid', 'Materials', 5230, 0.38, 0.48, 'airframe'],
  ['PropulsionPackage', 'solid', 'Materials', 5240, 0.42, 0.52, 'propulsion'],
  ['GuidanceComputer', 'solid', 'Materials', 5250, 0.25, 0.72, 'guidance'],
  ['MissionPayload', 'solid', 'Materials', 5260, 0.36, 0.65, 'payload'],
  ['RecoveredTelemetry', 'solid', 'Materials', 5270, 0.20, 0.80, 'telemetry'],
  // Legacy licence tokens: unproduced and unused, kept so saves holding them
  // load (tools/content_policy.json legacySaveOnlyGoods).
  ['IndustrialLicense', 'solid', 'Materials', 5280, 0.82, 0.55, 'license'],
  ['SpecialistLicense', 'solid', 'Materials', 5290, 0.90, 0.35, 'specialist'],
  ['FlightLicense', 'solid', 'Materials', 5300, 0.42, 0.78, 'flight'],
  ['Electronics', 'solid', 'Materials', 5310, 0.15, 0.74, 'electronics'],
  ['ReactorCoolantWater', 'liquid', 'Ingredients', 10180, 0.18, 0.60, 'coolantwater'],
  ['RecoveredMinerals', 'solid', 'Materials', 5320, 0.55, 0.48, 'recovered'],
  ['ArchiveData', 'solid', 'Materials', 5330, 0.18, 0.72, 'archive'],
];

// Native tank-surface materials for liquids that must not read as golden
// canola oil: crude oil uses the near-black Coffee liquid.
const LIQUID_MATERIALS = { CrudeOil: 'Materials/Goods/Coffee' };

async function makeGood([id, kind, group, order, r, g, symbol]) {
  const goodTemplates = { liquid: 'CanolaOil', food: 'AlgaeRation', solid: 'Paper' };
  if (!Object.hasOwn(goodTemplates, kind)) throw new Error(`Unknown good kind ${kind} for ${id}`);
  const basePath = vanilla(`Goods/Good.${goodTemplates[kind]}.blueprint.json`);
  const value = clone(await readJson(basePath));
  const spec = value.GoodSpec;
  spec.Id = id;
  spec.BackwardCompatibleIds = [];
  spec.GoodGroupId = group;
  spec.GoodOrder = order;
  spec.Weight = kind === 'liquid' ? 2 : kind === 'food' ? 1 : 8;
  spec.ForceImport = true;
  spec.DisplayNameLocKey = `Good.${id}.DisplayName`;
  spec.PluralDisplayNameLocKey = `Good.${id}.PluralDisplayName`;
  spec.Icon = icon(id);
  const b = kind === 'food' ? 0.32 : kind === 'liquid' ? 0.22 : 0.28;
  spec.ContainerColor = { r, g, b, a: 1.0 };
  if (kind === 'liquid') {
    spec.GoodType = 'Liquid';
    spec.StockpileVisualization = 'Liquid';
    spec.VisibleContainer = 'Barrel';
    spec.ContainerMaterial = LIQUID_MATERIALS[id] ?? 'Materials/Goods/CanolaOil';
    spec.CarryingAnimation = 'CarryInHands';
  } else {
    spec.GoodType = 'Box';
    spec.StockpileVisualization = 'Box';
    spec.VisibleContainer = 'Box';
    spec.ContainerMaterial = '';
    spec.CarryingAnimation = 'CarryInHands';
  }
  if (kind === 'food') {
    spec.ConsumptionEffects = [{ NeedId: 'Hunger', Points: 0.3 }];
  } else {
    spec.ConsumptionEffects = [];
  }
  if(id==='SweetBerryCake') {
    // A native Box good: the top-bar tooltip lists the stockpiles for every good
    // type and crashed on a type no stockpile takes (build 190). The cake stays
    // table-only because the Restaurant inventory never gives goods out
    // (RestaurantKitchenInventory: givable only) and blocks counter eating.
    spec.ConsumptionEffects.push({NeedId:'SweetBerryCake',Points:progression.restaurant.sweetBerryCake.needPoints});
  }
  await writeJson(data('Goods', `Good.${id}.blueprint.json`), value);
}

const recipeDefinitions = [
  ['SweetBerryCake', 'SweetBerryCake', progression.restaurant.sweetBerryCake.cycleHours, progression.restaurant.sweetBerryCake.ingredients, [{Id:'SweetBerryCake',Amount:progression.restaurant.sweetBerryCake.products}], 'SweetBerryCake'],
  // Dirt-free compost from wood and algae (Dirt needs the 2,000-science excavator).
  ['Compost', 'Compost', 1.0, [{ Id: 'Log', Amount: 1 }, { Id: 'Algae', Amount: 1 }, { Id: 'Water', Amount: 1 }], [{ Id: 'Compost', Amount: 2 }], 'Compost'],
  ['Fertilizer', 'Fertilizer', 1.0, [{ Id: 'Compost', Amount: 2 }, { Id: 'Water', Amount: 1 }, { Id: 'Algae', Amount: 1 }], [{ Id: 'Fertilizer', Amount: 2 }], 'Fertilizer'],
  ['JuvenileFish', 'JuvenileFish', 2.0, [{ Id: 'FreshFish', Amount: 1 }, { Id: 'Algae', Amount: 1 }, { Id: 'Water', Amount: 2 }], [{ Id: 'JuvenileFish', Amount: 2 }], 'JuvenileFish'],
  ['FreshFish', 'FreshFish', 3.0, [{ Id: 'JuvenileFish', Amount: 1 }, { Id: 'Algae', Amount: 1 }, { Id: 'Water', Amount: 3 }], [{ Id: 'FreshFish', Amount: 3 }], 'FreshFish'],
  ['FishOil', 'FishOil', 1.0, [{ Id: 'FreshFish', Amount: 2 }], [{ Id: 'FishOil', Amount: 1 }], 'FishOil'],
  ['CannedFish', 'CannedFish', 2.0, [{ Id: 'FreshFish', Amount: 3 }, { Id: 'MetalBlock', Amount: 1 }, { Id: 'FishOil', Amount: 1 }], [{ Id: 'CannedFish', Amount: 3 }], 'CannedFish'],
  ['EmergencyRation', 'EmergencyRation', 0.5, [{ Id: 'Corn', Amount: 1 }, { Id: 'Log', Amount: 1 }], [{ Id: 'EmergencyRation', Amount: 2 }], 'EmergencyRation'],
  ['PackagedFood', 'PackagedFood', 1.0, [{ Id: 'CornRation', Amount: 1 }, { Id: 'CannedFish', Amount: 1 }, { Id: 'Plank', Amount: 1 }], [{ Id: 'PackagedFood', Amount: 2 }], 'PackagedFood'],
  // Greenhouse glasshouse crops: two fertilizer per 8 h cycle. Products are 8x
  // the first balance (user, 2026-10-27), about 12-16x an equal-area vanilla
  // field (42 ground cells), so the fertilizer chain pays off.
  ['GreenhouseEggplant', 'Eggplant', 8.0, [{ Id: 'Fertilizer', Amount: 2 }, { Id: 'Water', Amount: 4 }], [{ Id: 'Eggplant', Amount: 48 }], 'Eggplant'],
  ['GreenhouseKohlrabi', 'Kohlrabi', 8.0, [{ Id: 'Fertilizer', Amount: 2 }, { Id: 'Water', Amount: 4 }], [{ Id: 'Kohlrabi', Amount: 112 }], 'Kohlrabi'],
  ['GreenhouseCoffee', 'CoffeeBean', 8.0, [{ Id: 'Fertilizer', Amount: 2 }, { Id: 'Water', Amount: 3 }], [{ Id: 'CoffeeBean', Amount: 24 }], 'CoffeeBean'],
  ['Medicine', 'Medicine', 2.0, [{ Id: 'Mushroom', Amount: 2 }, { Id: 'Algae', Amount: 1 }, { Id: 'Water', Amount: 1 }], [{ Id: 'Medicine', Amount: 2 }], 'Medicine'],
  ['MedicalFood', 'MedicalFood', 1.0, [{ Id: 'CannedFish', Amount: 1 }, { Id: 'CornRation', Amount: 1 }, { Id: 'Medicine', Amount: 1 }], [{ Id: 'MedicalFood', Amount: 2 }], 'MedicalFood'],
  ['Flux', 'Flux', 1.0, [{ Id: 'ScrapMetal', Amount: 2 }, { Id: 'DeepOre', Amount: 1 }], [{ Id: 'Flux', Amount: 2 }], 'Flux'],
  ['HighGradeSteel', 'HighGradeSteel', 4.0, [{ Id: 'MetalBlock', Amount: 4 }, { Id: 'Coal', Amount: 2 }, { Id: 'Flux', Amount: 1 }], [{ Id: 'HighGradeSteel', Amount: 2 }], 'HighGradeSteel'],
  ['Alloy', 'Alloy', 1.5, [{ Id: 'HighGradeSteel', Amount: 2 }, { Id: 'DeepAlloy', Amount: 1 }], [{ Id: 'Alloy', Amount: 2 }], 'Alloy'],
  // Industrial chemical from native badwater and extract (ChemicalWorks).
  ['Chemical', 'Chemical', 2.0, [{ Id: 'Badwater', Amount: 4 }, { Id: 'Extract', Amount: 1 }], [{ Id: 'Chemical', Amount: 2 }], 'Chemical'],
  ['Polymer', 'Polymer', 3.0, [{ Id: 'CrudeOil', Amount: 3 }, { Id: 'Chemical', Amount: 1 }, { Id: 'Water', Amount: 2 }], [{ Id: 'Polymer', Amount: 3 }], 'Polymer'],
  ['Lubricant', 'Lubricant', 2.0, [{ Id: 'CrudeOil', Amount: 2 }, { Id: 'FishOil', Amount: 1 }, { Id: 'Water', Amount: 1 }], [{ Id: 'Lubricant', Amount: 2 }], 'Lubricant'],
  ['MachineCore', 'MachineCore', 2.0, [{ Id: 'Alloy', Amount: 2 }, { Id: 'Polymer', Amount: 1 }, { Id: 'Gear', Amount: 2 }, { Id: 'DeepAlloy', Amount: 1 }], [{ Id: 'MachineCore', Amount: 1 }], 'MachineCore'],
  // Second uses (docs/progression.md "Second uses"): solder flux in electronics,
  // graphite electrodes (coal) in power modules.
  ['Electronics', 'Electronics', 2.0, [{ Id: 'MachineCore', Amount: 1 }, { Id: 'MetalPart', Amount: 2 }, { Id: 'Polymer', Amount: 1 }, { Id: 'Flux', Amount: 1 }], [{ Id: 'Electronics', Amount: 1 }], 'Electronics'],
  ['PowerModule', 'PowerModule', 2.0, [{ Id: 'Electronics', Amount: 1 }, { Id: 'Alloy', Amount: 1 }, { Id: 'MetalPart', Amount: 2 }, { Id: 'Coal', Amount: 1 }], [{ Id: 'PowerModule', Amount: 1 }], 'PowerModule'],
  ['FilterMedia', 'FilterMedia', 1.0, [{ Id: 'Plank', Amount: 2 }, { Id: 'Algae', Amount: 1 }], [{ Id: 'FilterMedia', Amount: 2 }], 'FilterMedia'],
  ['PureWater', 'PureWater', 8.0, [{ Id: 'Water', Amount: 10 }, { Id: 'FilterMedia', Amount: 1 }], [{ Id: 'PureWater', Amount: 8 }, { Id: 'ConcentratedWaste', Amount: 1 }], 'PureWater'],
  // Cryocoolant is consumed while conditioning high-purity reactor coolant.
  // This gives the cryogenic chain a meaningful non-rocket sink and keeps
  // reactor startup tied to the advanced cold-process infrastructure.
  ['ReactorCoolantWater', 'ReactorCoolantWater', 4.0, [{ Id: 'PureWater', Amount: 4 }, { Id: 'FilterMedia', Amount: 1 }, { Id: 'Cryocoolant', Amount: 1 }], [{ Id: 'ReactorCoolantWater', Amount: 4 }], 'ReactorCoolantWater'],
  ['DeepCoal', 'Coal', 2.0, [{ Id: 'DeepOre', Amount: 1 }, { Id: 'Water', Amount: 2 }], [{ Id: 'Coal', Amount: 3 }], 'Coal'],
  ['DeepOil', 'CrudeOil', 2.0, [{ Id: 'DeepOre', Amount: 1 }, { Id: 'Water', Amount: 3 }], [{ Id: 'CrudeOil', Amount: 6 }], 'CrudeOil'],
  ['DeepUranium', 'UraniumOre', 3.0, [{ Id: 'DeepOre', Amount: 2 }, { Id: 'Water', Amount: 4 }], [{ Id: 'UraniumOre', Amount: 1 }], 'UraniumOre'],
  // Oxygen as the leaching oxidant; hydrogen reduces the oxide for fuel pellets.
  ['Yellowcake', 'Yellowcake', 2.0, [{ Id: 'UraniumOre', Amount: 3 }, { Id: 'Chemical', Amount: 1 }, { Id: 'Water', Amount: 2 }, { Id: 'OxygenGas', Amount: 1 }], [{ Id: 'Yellowcake', Amount: 2 }], 'Yellowcake'],
  ['EnrichedFuel', 'EnrichedFuel', 1.0, [{ Id: 'Yellowcake', Amount: 2 }, { Id: 'MachineCore', Amount: 1 }, { Id: 'PowerModule', Amount: 1 }, { Id: 'HydrogenGas', Amount: 1 }], [{ Id: 'EnrichedFuel', Amount: 1 }, { Id: 'RadioactiveWaste', Amount: 1 }], 'EnrichedFuel'],
  ['Cryocoolant', 'Cryocoolant', 2.0, [{ Id: 'Polymer', Amount: 1 }, { Id: 'Lubricant', Amount: 1 }, { Id: 'Water', Amount: 2 }], [{ Id: 'Cryocoolant', Amount: 2 }], 'Cryocoolant'],
  ['Electrolysis', 'HydrogenGas/OxygenGas', 3.0, [{ Id: 'PureWater', Amount: 8 }], [{ Id: 'HydrogenGas', Amount: 4 }, { Id: 'OxygenGas', Amount: 4 }], 'HydrogenGas'],
  ['Liquefaction', 'LiquidHydrogen/LiquidOxygen', 2.0, [{ Id: 'HydrogenGas', Amount: 4 }, { Id: 'OxygenGas', Amount: 4 }, { Id: 'Cryocoolant', Amount: 2 }], [{ Id: 'LiquidHydrogen', Amount: 2 }, { Id: 'LiquidOxygen', Amount: 2 }], 'LiquidHydrogen'],
  ['RocketAirframe', 'RocketAirframe', 1.0, [{ Id: 'HighGradeSteel', Amount: 12 }, { Id: 'Alloy', Amount: 8 }, { Id: 'TreatedPlank', Amount: 4 }, { Id: 'Polymer', Amount: 4 }], [{ Id: 'RocketAirframe', Amount: 1 }], 'RocketAirframe'],
  ['PropulsionPackage', 'PropulsionPackage', 1.0, [{ Id: 'Alloy', Amount: 10 }, { Id: 'MachineCore', Amount: 4 }, { Id: 'Polymer', Amount: 6 }, { Id: 'HighGradeSteel', Amount: 6 }], [{ Id: 'PropulsionPackage', Amount: 1 }], 'PropulsionPackage'],
  ['GuidanceComputer', 'GuidanceComputer', 1.0, [{ Id: 'Electronics', Amount: 4 }, { Id: 'MachineCore', Amount: 2 }, { Id: 'ArchiveData', Amount: 1 }], [{ Id: 'GuidanceComputer', Amount: 1 }], 'GuidanceComputer'],
  ['MissionPayload', 'MissionPayload', 1.0, [{ Id: 'GuidanceComputer', Amount: 1 }, { Id: 'RecoveredArtifact', Amount: 2 }, { Id: 'TreatedPlank', Amount: 2 }], [{ Id: 'MissionPayload', Amount: 1 }], 'MissionPayload'],
  // The licence token recipes are retired: specialists are trained beavers
  // (tools/workforce_risks.json). The licence goods stay for saves only.
  // Waste balance: 0.5 waste/hour per reactor; one refinery (4 per 8 h) keeps up.
  // Radiation (docs/radiation.md): solid RadioactiveWaste stays as spent-fuel
  // casks (vault custody, refinery input). Activated coolant leaves as liquid
  // RadioactiveSludge, and the refinery concentrates casks into sludge for the
  // map-edge Radioactive Waste Export. RadioactiveSludge and ContaminatedWater
  // are defined by tools/radiation_content.mjs later in the generation chain.
  ['NuclearWaste', 'RadioactiveWaste', 2, [{ Id: 'ReactorCoolantWater', Amount: 6 }], [{ Id: 'RadioactiveWaste', Amount: 1 }, { Id: 'RadioactiveSludge', Amount: 1 }], 'RadioactiveWaste'],
  ['WasteRefining', 'RadioactiveSludge/RecoveredMinerals', 8.0, [{ Id: 'RadioactiveWaste', Amount: 4 }, { Id: 'Chemical', Amount: 2 }, { Id: 'Water', Amount: 8 }], [{ Id: 'RadioactiveSludge', Amount: 6 }, { Id: 'RecoveredMinerals', Amount: 2 }], 'RadioactiveSludge'],
  ['DecontaminateWater', 'Water', 4.0, [{ Id: 'ContaminatedWater', Amount: 10 }, { Id: 'Chemical', Amount: 1 }], [{ Id: 'Water', Amount: 8 }, { Id: 'RadioactiveSludge', Amount: 1 }], 'ContaminatedWater'],
  ['GuidanceTelemetry', 'RecoveredTelemetry', 1.0, [{ Id: 'GuidanceComputer', Amount: 1 }, { Id: 'ArchiveData', Amount: 1 }], [{ Id: 'RecoveredTelemetry', Amount: 1 }], 'RecoveredTelemetry'],
  // Archive Excavation (planned, frontier_progression.json plannedBuildings):
  // charges and shoring open human ruins; grease and parts restore their data.
  ['RecoveredArtifact', 'RecoveredArtifact', 6.0, [{ Id: 'Explosives', Amount: 1 }, { Id: 'TreatedPlank', Amount: 2 }], [{ Id: 'RecoveredArtifact', Amount: 1 }], 'RecoveredArtifact'],
  ['ArchiveData', 'ArchiveData', 4.0, [{ Id: 'RecoveredArtifact', Amount: 2 }, { Id: 'Grease', Amount: 1 }, { Id: 'MetalPart', Amount: 1 }], [{ Id: 'ArchiveData', Amount: 1 }], 'ArchiveData'],
  // Second uses (docs/progression.md "Second uses"). Each consumer unlocks at
  // or after its inputs' producers (tools/audit_progression.mjs).
  // Water Treatment Plant: activated-carbon filters from coal.
  ['CarbonFilterMedia', 'FilterMedia', 1.0, [{ Id: 'Coal', Amount: 1 }, { Id: 'Plank', Amount: 1 }], [{ Id: 'FilterMedia', Amount: 3 }], 'FilterMedia'],
  // Chemical Works: chlor-alkali chemical from the treatment plant's brine.
  ['BrineChemical', 'Chemical', 2.0, [{ Id: 'ConcentratedWaste', Amount: 3 }, { Id: 'Extract', Amount: 1 }], [{ Id: 'Chemical', Amount: 2 }], 'Chemical'],
  // Greenhouse aquaponics: juvenile fish grow in the beds' tanks and their
  // waste stands in for half the fertilizer of the kohlrabi crop.
  ['GreenhouseAquaponics', 'Kohlrabi/FreshFish', 8.0, [{ Id: 'JuvenileFish', Amount: 1 }, { Id: 'Fertilizer', Amount: 1 }, { Id: 'Water', Amount: 4 }], [{ Id: 'Kohlrabi', Amount: 80 }, { Id: 'FreshFish', Amount: 16 }], 'Kohlrabi'],
  // Precision Machine Works: late-game parts for the native Iron Teeth bot
  // (vanilla BotChassis/BotLimb/BotHead goods), far faster than the Bot Part
  // Factory; the industrial assembly recipe is in tools/bot_upkeep_content.mjs.
  ['ReinforcedBotChassis', 'BotChassis', 4.0, [{ Id: 'Alloy', Amount: 1 }, { Id: 'Polymer', Amount: 1 }, { Id: 'Flux', Amount: 1 }], [{ Id: 'BotChassis', Amount: 2 }], 'BotChassis'],
  ['ServoBotLimbs', 'BotLimb', 4.0, [{ Id: 'MachineCore', Amount: 1 }, { Id: 'Lubricant', Amount: 1 }, { Id: 'MetalPart', Amount: 2 }], [{ Id: 'BotLimb', Amount: 4 }], 'BotLimb'],
  ['BotCortex', 'BotHead', 4.0, [{ Id: 'Electronics', Amount: 1 }, { Id: 'Polymer', Amount: 1 }], [{ Id: 'BotHead', Amount: 2 }], 'BotHead'],
  // Uranium Processing Plant: spent casks reprocessed into fresh fuel. The
  // fuel's own life yields ten casks, so reprocessing never shrinks waste.
  ['FuelReprocessing', 'EnrichedFuel', 4.0, [{ Id: 'RadioactiveWaste', Amount: 4 }, { Id: 'Chemical', Amount: 2 }, { Id: 'Yellowcake', Amount: 1 }], [{ Id: 'EnrichedFuel', Amount: 1 }, { Id: 'RadioactiveWaste', Amount: 2 }], 'EnrichedFuel'],
  // Waste Refinery: contaminated water as process water (radioactivity stays
  // in the sludge), and vitrification of sludge into casks for the vault with
  // recovered minerals as glass formers. WasteRefining followed by
  // Vitrification returns the same four casks: no waste is destroyed.
  ['ContaminatedWaterRefining', 'RadioactiveSludge/RecoveredMinerals', 8.0, [{ Id: 'RadioactiveWaste', Amount: 4 }, { Id: 'Chemical', Amount: 2 }, { Id: 'ContaminatedWater', Amount: 8 }], [{ Id: 'RadioactiveSludge', Amount: 6 }, { Id: 'RecoveredMinerals', Amount: 2 }], 'RadioactiveSludge'],
  ['Vitrification', 'RadioactiveWaste', 4.0, [{ Id: 'RadioactiveSludge', Amount: 3 }, { Id: 'RecoveredMinerals', Amount: 1 }], [{ Id: 'RadioactiveWaste', Amount: 2 }], 'RadioactiveWaste'],
  // A second, productive sludge sink: the refinery can recover trace metals
  // from dilute sludge instead of sending every cask to vitrification.
  ['SludgeMineralRecovery', 'RecoveredMinerals/ConcentratedWaste', 6.0, [{ Id: 'RadioactiveSludge', Amount: 2 }, { Id: 'Chemical', Amount: 1 }, { Id: 'Water', Amount: 4 }], [{ Id: 'RecoveredMinerals', Amount: 2 }, { Id: 'ConcentratedWaste', Amount: 1 }], 'RecoveredMinerals'],
];

// Native recipe fuel: [good, cycles one unit lasts, fuel inventory capacity].
const RECIPE_FUELS = {
  NuclearWaste: ['EnrichedFuel', 10, 2],
};
for (const id of Object.keys(RECIPE_FUELS)) if (!recipeDefinitions.some(([recipe]) => recipe === id)) throw new Error(`RECIPE_FUELS names undefined recipe ${id}`);

// Planned buildings (art in progress) run recipes defined above; they are
// generated once their studies are integrated (tools/lategame_batches.json).
for (const planned of progression.plannedBuildings) {
  for (const id of planned.recipes) {
    if (!recipeDefinitions.some(([recipe]) => recipe === id)) throw new Error(`Planned ${planned.id} runs undefined recipe ${id}`);
  }
}

// Authored display names (Recipe.<id>.DisplayName) for recipes that share a
// product with another recipe of the same building; the others show their
// product's plural name.
const RECIPE_NAMES = {
  CarbonFilterMedia: 'Activated carbon filters',
  BrineChemical: 'Chemical from brine',
  GreenhouseAquaponics: 'Aquaponic kohlrabi and fish',
  FuelReprocessing: 'Spent fuel reprocessing',
  ContaminatedWaterRefining: 'Waste refining with contaminated water',
  Vitrification: 'Sludge vitrification',
  SludgeMineralRecovery: 'Sludge mineral recovery',
};
for (const id of Object.keys(RECIPE_NAMES)) if (!recipeDefinitions.some(([recipe]) => recipe === id)) throw new Error(`RECIPE_NAMES names undefined recipe ${id}`);

async function makeRecipe([id, outputLabel, hours, ingredients, products, iconId]) {
  const base = clone(await readJson(vanilla('Recipes/Recipe.MetalBlock.blueprint.json')));
  base.RecipeSpec = {
    ...base.RecipeSpec,
    Id: id,
    BackwardCompatibleIds: [],
    DisplayLocKey: Object.hasOwn(RECIPE_NAMES, id) ? `Recipe.${id}.DisplayName` : `Good.${String(outputLabel).split('/')[0]}.PluralDisplayName`,
    CycleDurationInHours: hours,
    Ingredients: ingredients,
    Products: products,
    ProducedSciencePoints: 0,
    Fuel: RECIPE_FUELS[id]?.[0] ?? '',
    CyclesFuelLasts: RECIPE_FUELS[id]?.[1] ?? 0,
    FuelCapacity: RECIPE_FUELS[id]?.[2] ?? 0,
    CyclesCapacity: 30,
    Icon: icon(iconId),
  };
  await writeJson(data('Recipes', `Recipe.${id}.blueprint.json`), base);
}

const buildingDefinitions = [
  ['FertilizerWorks', 'Buildings/Food/FertilizerWorks', 'OilPress', 'Compost,Fertilizer', 'Food', 32, 80, 2, 350, 'Fertilizer works'],
  ['FishHatchery', 'Buildings/Food/FishHatchery', 'HydroponicGarden', 'JuvenileFish', 'Food', 33, 55, 2, 600, 'Fish hatchery'],
  ['FisheryWorks', 'Buildings/Food/FisheryWorks', 'FoodFactory', 'FreshFish,FishOil', 'Food', 34, 80, 3, 900, 'Fishery works'],
  ['FoodPackagingWorks', 'Buildings/Food/FoodPackagingWorks', 'FoodFactory', 'CannedFish,EmergencyRation,PackagedFood', 'Food', 35, 140, 3, 1400, 'Food packaging works'],
  ['PublicHealthLab', 'Buildings/Wellbeing/PublicHealthLab', 'OilPress', 'Medicine', 'Wellbeing', 36, 100, 3, 1000, 'Public health lab'],
  ['GroceryStore', 'Buildings/Food/GroceryStore', 'FoodFactory', '', 'Wellbeing', 37, progression.groceryStore.powerDemandHp, progression.groceryStore.workers, progression.groceryStore.scienceUnlock, 'Grocery store'],
  ['Restaurant', 'Buildings/Food/Restaurant', 'FoodFactory', progression.restaurant.kitchenRecipes.join(','), 'Wellbeing', 38, progression.restaurant.powerDemandHp, 4, 1000, 'Restaurant'],
  ['Hospital', 'Buildings/Wellbeing/Hospital', 'FoodFactory', '', 'Wellbeing', 39, progression.hospital.powerDemandHp, progression.hospital.workers, progression.hospital.scienceUnlock, 'Hospital'],
  ['Greenhouse', 'Buildings/Food/Greenhouse', 'HydroponicGarden', 'GreenhouseEggplant,GreenhouseKohlrabi,GreenhouseCoffee,GreenhouseAquaponics', 'Food', 40, 35, 1, 600, 'Greenhouse'],
  ['ChemicalWorks', 'Buildings/Metal/ChemicalWorks', 'Smelter', 'Chemical,BrineChemical,Polymer,Lubricant,Cryocoolant', 'Metal', 41, 3500, 8, 4000, 'Chemical works'],
  ['PrecisionMachineWorks', 'Buildings/Metal/PrecisionMachineWorks', 'BotPartFactory', 'MachineCore,Electronics,PowerModule,ReinforcedBotChassis,ServoBotLimbs,BotCortex', 'Metal', 42, 2200, 6, 5000, 'Precision machine works'],
  ['WaterTreatmentPlant', 'Buildings/Water/WaterTreatmentPlant', 'Centrifuge', 'PureWater,ReactorCoolantWater,FilterMedia,CarbonFilterMedia', 'Water', 43, 500, 4, 1800, 'Water treatment plant'],
  ['TechnicalSchool', 'Buildings/Science/TechnicalSchool', 'Inventor', trainingRecipes.join(','), 'Science', 44, 300, 4, 2200, 'Technical school'],
  ['UraniumProcessingPlant', 'Buildings/Metal/UraniumProcessingPlant', 'Centrifuge', 'Yellowcake,EnrichedFuel,FuelReprocessing', 'Metal', 45, 5000, 6, progression.implementedBuildingScienceOverrides.UraniumProcessingPlant, 'Uranium processing plant'],
  ['RadioactiveWasteRefinery', 'Buildings/Metal/RadioactiveWasteRefinery', 'Centrifuge', 'WasteRefining,ContaminatedWaterRefining,DecontaminateWater,Vitrification,SludgeMineralRecovery', 'Metal', 46, 8000, 6, progression.implementedBuildingScienceOverrides.RadioactiveWasteRefinery, 'Radioactive waste refinery'],
  ['ElectrolysisPlant', 'Buildings/Metal/ElectrolysisPlant', 'Centrifuge', 'Electrolysis', 'Metal', 47, 6000, 5, 10000, 'Electrolysis plant'],
  ['CryogenicLiquefactionPlant', 'Buildings/Metal/CryogenicLiquefactionPlant', 'Centrifuge', 'Liquefaction', 'Metal', 48, 10000, 6, 12000, 'Cryogenic liquefaction plant'],
  ['RocketAssemblyHangar', 'Buildings/Metal/RocketAssemblyHangar', 'FoodFactory', 'RocketAirframe,PropulsionPackage', 'Metal', 49, 12000, 10, 18000, 'Rocket assembly hangar'],
  ['MissionControl', 'Buildings/Science/MissionControl', 'Inventor', 'GuidanceComputer,MissionPayload,GuidanceTelemetry', 'Science', 110, 1500, 4, 14000, 'Mission control'],
  ['LaunchPad', 'Buildings/Metal/LaunchPad', 'FoodFactory', 'GuidanceTelemetry', 'Metal', 51, 25000, 8, 20000, 'Launch pad'],
  // Planned buildings integrated from their late-game studies (build 122):
  // recipes, menu, power, workers and science come from their
  // frontier_progression.json plannedBuildings entry.
  plannedRow('SteelMill', 'Buildings/Metal/SteelMill', 'Smelter'),
  plannedRow('ArchiveExcavation', 'Buildings/Science/ArchiveExcavation', 'BotPartFactory'),
  plannedRow('CryogenicTankFarm', 'Buildings/Storage/CryogenicTankFarm', 'LargeTank'),
];

function plannedRow(id, outputPath, template) {
  const planned = progression.plannedBuildings.find((p) => p.id === id);
  if (!planned) throw new Error(`frontier_progression.json plannedBuildings has no ${id}`);
  if (!planned.template.startsWith(template)) throw new Error(`${id}: planned template ${planned.template} is not ${template}`);
  if (!LATEGAME.has(id)) throw new Error(`${id}: its study is not integrated (tools/lategame_batches.json)`);
  return [id, outputPath, template, planned.recipes.join(','), planned.toolGroup, planned.toolOrder, planned.powerDemandHp,
    planned.workers, planned.scienceUnlock, planned.name];
}

// Authored player-facing text for buildings whose description is more than the
// generic production line.
const BUILDING_TEXT = {
  SteelMill: ['An electric-arc melt shop and rolling mill. Makes flux from scrap metal and deep ore, high-grade steel from metal blocks, coal and flux, and alloy from high-grade steel and deep alloy. Only 6 trained metallurgists can work here, and the work is extremely dangerous. Requires 2,500 hp. Its two smokestacks pollute the air nearby.',
    'Every reactor, rocket and machine core starts as a white-hot pour on this floor.'],
  ArchiveExcavation: ['Opens human ruins anywhere with explosive charges and treated-plank shoring to recover artifacts, then restores their data drives into archive data with grease and metal parts. A Human Record Cache within 4 tiles can be surveyed for extra archive data. 4 workers, dangerous work. Requires 400 hp. Its stove chimney pollutes the air nearby.',
    'The humans buried their warnings in the strata. Dig carefully.'],
  CryogenicTankFarm: ['Stores up to 2,000 units of one cryogenic fuel, liquid hydrogen or liquid oxygen, delivered and drawn by pipes at its two front sockets or by haulers. Needs 1,000 hp to keep the fuel cold: without power the intake closes, and after 12 hours the stored fuel starts to vent.',
    'The coldest place in the colony, kept that way at great expense.'],
};


function setLabels(value, id, outputPath = `Buildings/${id}`) {
  value.LabeledEntitySpec = { ...value.LabeledEntitySpec };
  value.LabeledEntitySpec.DisplayNameLocKey = `Building.${id}.DisplayName`;
  value.LabeledEntitySpec.DescriptionLocKey = `Building.${id}.Description`;
  value.LabeledEntitySpec.FlavorDescriptionLocKey = `Building.${id}.FlavorDescription`;
  value.LabeledEntitySpec.Icon = `${outputPath}/Icon`;
}

function setModels(value, id, outputPath) {
  // These authored models contain their own animated machinery. They do not
  // contain the template's crop stages, sitting slots, or smoke attachment nodes.
  for (const key of ['ManufactoryProgressVisualizerSpec', 'ManufactoryRecipeVisualizerSpec',
    'TransformSlotInitializerSpec', 'WorkplaceSlotManagerSpec', 'WorkshopWorkerHiderSpec', 'TemplateAttachmentsSpec',
    'WorkshopParticleControllerSpec', 'WindParticleControllerSpec', 'PowerGeneratorParticleControllerSpec']) {
    delete value[key];
  }
  value.Children['#Finished'].TimbermeshSpec.Model = `${outputPath}/${id}.IronTeeth.Model`;
  value.Children['#Unfinished'].Children.ConstructionStage0.TimbermeshSpec.Model = `${outputPath}/${id}.IronTeeth.ConstructionStage0.Model`;
}

const authoredFootprints = new Map([
  ['FertilizerWorks', [2, 3, 2]],
  ['FoodPackagingWorks', [3, 3, 3]], ['PublicHealthLab', [2, 3, 2]],
  ['Hospital', [3, 3, 3]], ['Greenhouse', [3, 1, 3]],
  ['ChemicalWorks', [3, 3, 3]], ['PrecisionMachineWorks', [3, 2, 3]], ['WaterTreatmentPlant', [3, 3, 3]],
  ['TechnicalSchool', [2, 3, 2]], ['UraniumProcessingPlant', [3, 3, 3]],
  ['RadioactiveWasteRefinery', [3, 3, 3]], ['ElectrolysisPlant', [3, 3, 3]],
  ['CryogenicLiquefactionPlant', [3, 3, 3]], ['RocketAssemblyHangar', [3, 3, 3]],
  ['MissionControl', [2, 3, 2]], ['LaunchPad', [3, 3, 3]], ['NuclearReactor', [3, 3, 3]],
  ['RadioactiveWasteVault', [3, 2, 3]],
]);

function setGeometry(value, id) {
  const footprint = authoredFootprints.get(id);
  if (!footprint || !value.BlockObjectSpec) throw new Error(`Missing authored geometry for ${id}`);
  const [width, height, depth] = footprint;
  const baseBlock = value.BlockObjectSpec.Blocks[0];
  if (!baseBlock) throw new Error(`Template has no block contract for ${id}`);
  value.BlockObjectSpec = {
    ...value.BlockObjectSpec,
    Flippable: true,
    Size: { X: width, Y: height, Z: depth },
    Blocks: Array.from({ length: width * height * depth }, () => clone(baseBlock)),
  };
  if (value.BlockObjectSpec.Entrance?.Coordinates) {
    value.BlockObjectSpec.Entrance.Coordinates = { X: Math.floor(width / 2), Y: -1, Z: 0 };
  }
  const collider = {
    BoxColliders: [{ Center: { X: width / 2, Y: height / 2, Z: depth / 2 }, Size: { X: width, Y: height, Z: depth } }],
    SphereColliders: [],
    CapsuleColliders: [],
  };
  if (value.Children?.['#Finished']) value.Children['#Finished'].CollidersSpec = clone(collider);
  if (value.Children?.['#Unfinished']) value.Children['#Unfinished'].CollidersSpec = clone(collider);
}

function authoredCost(id) {
  if(id==='Hospital')return clone(progression.hospital.buildingCost);
  if(id==='GroceryStore')return clone(progression.groceryStore.buildingCost);
  if(!Object.hasOwn(constructionCosts.buildings,id))throw new Error('Missing explicit construction cost: '+id);
  const rows=constructionCosts.buildings[id];
  if(new Set(rows.map(([good])=>good)).size!==rows.length||
     rows.some(([good,amount])=>typeof good!=='string'||!Number.isInteger(amount)||amount<=0))
    throw new Error('Invalid authored construction cost: '+id);
  return rows.map(([Id,Amount])=>({Id,Amount}));
}

async function makeBuilding(definition) {
  const [id, outputPath, template, recipes, toolGroup, toolOrder, power, workers, science, display] = definition;
  const templateGroups = { SteamEngine: 'Power', HydroponicGarden: 'Food', FoodFactory: 'Food',
    OilPress: 'Food', BotPartFactory: 'Science', Inventor: 'Science', Centrifuge: 'Water',
    MediumTank: 'Storage', LargeTank: 'Storage', Smelter: 'Metal' };
  if (!Object.hasOwn(templateGroups, template)) throw new Error(`Unknown template ${template} for ${id}`);
  const templatePath = `Buildings/${templateGroups[template]}/${template}/${template}.IronTeeth.blueprint.json`;
  const value = clone(await readJson(vanilla(templatePath)));
  value.BuildingSpec = {
    ...value.BuildingSpec,
    BuildingCost: authoredCost(id),
    ScienceCost: science,
  };
  value.TemplateSpec = { ...value.TemplateSpec, TemplateName: `${id}.IronTeeth`, BackwardCompatibleTemplateNames: [] };
  value.PlaceableBlockObjectSpec = { ...value.PlaceableBlockObjectSpec, ToolGroupId: toolGroup, ToolOrder: toolOrder, DevModeTool: false };
  setLabels(value, id, outputPath);
  if (value.WorkplaceSpec) {
    value.WorkplaceSpec = { ...value.WorkplaceSpec, MaxWorkers: workers, DefaultWorkers: workers, WorkerTypeUnlockCosts: [{ WorkerType: 'Bot', ScienceCost: science + 1000 }] };
  }
  if (value.ManufactorySpec) value.ManufactorySpec = { ...value.ManufactorySpec, ProductionRecipeIds: recipes.split(',') };
  if (!value.ManufactorySpec && recipes) value.ManufactorySpec = { ProductionRecipeIds: recipes.split(',') };
  if (value.MechanicalNodeSpec) {
    value.MechanicalNodeSpec = { ...value.MechanicalNodeSpec, PowerOutput: 0, PowerInput: power, IsShaft: false };
  } else if (power > 0) {
    // An unpowered template (HydroponicGarden for the FishHatchery and Greenhouse) becomes a consumer.
    // Every vanilla powered consumer also carries the native connector target, which draws the gear
    // socket where a shaft or generator meets a transput (MechanicalConnectorActivator, 1.1.2.8);
    // without it a shaft ends at a bare wall (build 176 user report).
    value.MechanicalNodeSpec = { PowerOutput: 0, PowerInput: power, IsShaft: false };
    value.MechanicalBuildingSpec = {};
    value.MechanicalConnectorTargetSpec = {};
  }
  if (id === 'TechnicalSchool' || id === 'MissionControl') {
    value.MechanicalNodeSpec = { PowerOutput: 0, PowerInput: power, IsShaft: false };
    value.MechanicalBuildingSpec = {};
  }
  setModels(value, id, outputPath);
  if (id === 'CryogenicTankFarm') configureTankFarm(value);
  if(id==='Restaurant')await applyRestaurant(value);
  else if(id==='FisheryWorks')await applyFishery(value);
  else if(id==='FishHatchery')await applyHatchery(value);
  else if(id==='Hospital')await applyHospital(value);
  else if(id==='GroceryStore')await applyGroceryStore(value);
  else if(LATEGAME.has(id))await applyLategame(value,id);
  else setGeometry(value, id);
  if(id==='FoodPackagingWorks')value.ManufactorySpec.ProductionRecipeIds.push('MedicalFood');
  if(id==='WaterTreatmentPlant')value.BuildingPipeTargetPortsSpec=coolantPorts(id);
  await writeJson(data(...outputPath.split('/'), `${id}.IronTeeth.blueprint.json`), value);
  return `${outputPath}/${id}.IronTeeth.blueprint`;
}

// Cryogenic Tank Farm storage (frontier_progression.json plannedBuildings
// storage). Behaviour specs and pipe sockets are owned by cryogenic_content.mjs.
function configureTankFarm(value) {
  const {storage} = progression.plannedBuildings.find((p) => p.id === 'CryogenicTankFarm');
  if (storage.goodType !== 'Liquid' || !Number.isInteger(storage.capacity)) throw new Error('CryogenicTankFarm: planned storage must be an integer Liquid capacity');
  value.StockpileSpec = {...value.StockpileSpec, MaxCapacity: storage.capacity, WhitelistedGoodType: storage.goodType};
  // The double-walled tank is sealed: the study has no visible liquid plane.
  if (!value.StockpilePlaneVisualizerSpec) throw new Error('CryogenicTankFarm: LargeTank template lost StockpilePlaneVisualizerSpec');
  delete value.StockpilePlaneVisualizerSpec;
  value.MechanicalConnectorTargetSpec = {};
}

function removeTemplateSpecs(value, keys, id) {
  for (const key of keys) {
    if (!Object.hasOwn(value, key)) throw new Error(`${id}: template spec ${key} is missing`);
    delete value[key];
  }
}

// Smog Scrubber (tools/smog_content.json scrubber): a powered building without
// workers, cloned from the vanilla Aquifer Drill (the Iron Teeth powered,
// non-enterable, worker-free building) without its aquifer requirement. The
// scrubbing itself (SmogScrubberSpec) is added by smog_building_content.mjs.
async function makeScrubber() {
  const id = 'SmogScrubber', outputPath = 'Buildings/Wellbeing/SmogScrubber';
  const smog = await readJson(resolve(root, 'tools', 'smog_content.json'));
  const design = smog.scrubber.proposed;
  if (smog.scrubber.template !== id) throw new Error(`smog_content.json scrubber template is ${smog.scrubber.template}`);
  const registration = await readJson(resolve(root, 'outputs', 'lategame-studies', `${id}-registration.json`));
  if (registration.footprint.join() !== design.footprint.join() || registration.height !== design.height || design.workers !== 0)
    throw new Error(`${id}: study ${registration.footprint}x${registration.height} differs from smog_content.json scrubber.proposed`);
  const science = progression.implementedBuildingScienceOverrides[id];
  if (!Number.isInteger(science)) throw new Error(`${id}: no science in frontier_progression.json implementedBuildingScienceOverrides`);
  const value = clone(await readJson(vanilla('Buildings/Water/AquiferDrill/AquiferDrill.IronTeeth.blueprint.json')));
  removeTemplateSpecs(value, ['UnderstructureConstraintSpec', 'UndergroundWaterSourceDrillSpec', 'NoPowerStatusAlertDisablerSpec',
    // AmbientAnimation plays the study's fan and pump; one driver per animator.
    'MechanicalNodeAnimatorSpec'], id);
  value.BuildingModelSpec = {...value.BuildingModelSpec, UndergroundModelName: '', UndergroundModelDepth: 0};
  delete value.Children['#Underground'];
  value.BuildingSpec = {...value.BuildingSpec, BuildingCost: (await lategameCost(id)).map(([Id, Amount]) => ({Id, Amount})), ScienceCost: science};
  value.TemplateSpec = {...value.TemplateSpec, TemplateName: `${id}.IronTeeth`, BackwardCompatibleTemplateNames: []};
  value.PlaceableBlockObjectSpec = {...value.PlaceableBlockObjectSpec, ToolGroupId: 'Wellbeing', ToolOrder: 160, DevModeTool: false};
  value.MechanicalNodeSpec = {PowerOutput: 0, PowerInput: design.powerInputHp, IsShaft: false};
  setLabels(value, id, outputPath);
  setModels(value, id, outputPath);
  await applyLategame(value, id);
  await writeJson(data(...outputPath.split('/'), `${id}.IronTeeth.blueprint.json`), value);
  return `${outputPath}/${id}.IronTeeth.blueprint`;
}

// Late-game wellbeing attractions (frontier_progression.json lategameWellbeing):
// vanilla Iron Teeth attraction templates with native needs only.
const WELLBEING = progression.lategameWellbeing.buildings;
const vanillaNeeds = new Set([
  ...(await readJson(vanilla('NeedCollections/NeedCollection.Common.blueprint.json'))).NeedCollectionSpec.Needs,
  ...(await readJson(vanilla('NeedCollections/NeedCollection.IronTeeth.blueprint.json'))).NeedCollectionSpec.Needs]);
// Effects of the vanilla template's own model (fire, light objects, liquid
// surface, attachments) and named-slot retrieval: the studies author none.
const ATTRACTION_MODEL_SPECS = ['FireSpec', 'AttractionFireSpec', 'IlluminatorLightObjectsSpec', 'TemplateAttachmentsSpec',
  'SlotAnimationSynchronizerSpec', 'PrioritySlotRetrieverSpec', 'GoodConsumingAttractionSurfaceControllerSpec'];
const ATTRACTION_TEMPLATE_SPECS = {
  // The Mud Bath's navmesh edges describe its own tub interior.
  MudBath: ['TemplateAttachmentsSpec', 'GoodConsumingAttractionSurfaceControllerSpec', 'BlockObjectNavMeshSettingsSpec'],
  ExercisePlaza: ['FireSpec', 'AttractionFireSpec', 'IlluminatorLightObjectsSpec', 'TemplateAttachmentsSpec', 'SlotAnimationSynchronizerSpec', 'PrioritySlotRetrieverSpec'],
};

async function makeAttraction(entry) {
  const {id} = entry, outputPath = `Buildings/Wellbeing/${id}`;
  if (!LATEGAME.has(id)) throw new Error(`${id}: its study is not integrated (tools/lategame_batches.json)`);
  const value = clone(await readJson(vanilla(`Buildings/Wellbeing/${entry.template}/${entry.template}.IronTeeth.blueprint.json`)));
  if (!value.AttractionSpec || !value.EnterableSpec) throw new Error(`${id}: template ${entry.template} is not an attraction`);
  if (!Object.hasOwn(ATTRACTION_TEMPLATE_SPECS, entry.template)) throw new Error(`${id}: no model-spec list for template ${entry.template}`);
  removeTemplateSpecs(value, ATTRACTION_TEMPLATE_SPECS[entry.template], id);
  for (const key of ATTRACTION_MODEL_SPECS) if (value[key]) throw new Error(`${id}: template ${entry.template} keeps ${key}`);
  value.BuildingSpec = {...value.BuildingSpec, BuildingCost: (await lategameCost(id)).map(([Id, Amount]) => ({Id, Amount})), ScienceCost: entry.scienceUnlock};
  value.TemplateSpec = {...value.TemplateSpec, TemplateName: `${id}.IronTeeth`, BackwardCompatibleTemplateNames: []};
  value.PlaceableBlockObjectSpec = {...value.PlaceableBlockObjectSpec, ToolGroupId: 'Wellbeing', ToolOrder: entry.toolOrder, DevModeTool: false};
  setLabels(value, id, outputPath);
  for (const [need, points] of entry.effects) {
    if (!vanillaNeeds.has(need)) throw new Error(`${id}: ${need} is not a shipped Iron Teeth or Common need`);
    if (!(points > 0)) throw new Error(`${id}: ${need} needs positive points per hour`);
  }
  value.AttractionSpec = {Effects: entry.effects.map(([NeedId, PointsPerHour]) => ({NeedId, PointsPerHour, SatisfyToMaxValue: false}))};
  value.EnterableSpec = {...value.EnterableSpec, LimitedCapacityFinished: true, CapacityFinished: entry.capacity};
  if (entry.powerDemandHp > 0) {
    if (!value.MechanicalNodeSpec || !value.MechanicalBuildingSpec) throw new Error(`${id}: template ${entry.template} is not powered`);
    value.MechanicalNodeSpec = {...value.MechanicalNodeSpec, PowerOutput: 0, PowerInput: entry.powerDemandHp, IsShaft: false};
  } else if (value.MechanicalNodeSpec) throw new Error(`${id}: template ${entry.template} is powered but the design is not`);
  if (entry.consumes.length) {
    if (!value.GoodConsumingBuildingSpec || !value.GoodConsumingAttractionSpec) throw new Error(`${id}: template ${entry.template} consumes no goods`);
    value.GoodConsumingBuildingSpec = {FullInventoryWorkHours: entry.fullInventoryWorkHours,
      ConsumedGoods: entry.consumes.map(([GoodId, GoodPerHour]) => ({GoodId, GoodPerHour}))};
  } else if (value.GoodConsumingBuildingSpec) throw new Error(`${id}: template ${entry.template} consumes goods but the design does not`);
  // setModels drops template slot specs; the visitors are set after it.
  setModels(value, id, outputPath);
  // Visitors: native slots exported on the study's walking surfaces, or none
  // (visitors stay inside, as Hospital patients do).
  const slotRecord = resolve(root, 'outputs', 'lategame-integration', `${id}-visitor-slots.json`);
  if (entry.slotAnimation) {
    const slots = await readJson(slotRecord);
    if (slots.ident !== id || slots.model !== `${outputPath}/${id}.IronTeeth.Model` || slots.count !== entry.capacity)
      throw new Error(`${id}: exported visitor slots ${JSON.stringify(slots)} do not match capacity ${entry.capacity}; re-export the model`);
    value.TransformSlotInitializerSpec = {Slots: [{SlotKeyword: slots.keyword, Animation: entry.slotAnimation, Inanimate: false,
      RandomizeYRotation: false, WaterSlot: false}]};
    value.FixedSlotManagerSpec = {};
  } else {
    removeTemplateSpecs(value, ['FixedSlotManagerSpec'], id);
  }
  const options = {};
  if (id === 'ObservationDeck') {
    // Roof terrace: every free layer-12 cell on the deck slab (layer 11).
    const registration = await readJson(resolve(root, 'outputs', 'lategame-studies', `${id}-registration.json`));
    const occupied = new Set(registration.occupied.map((c) => c.join()));
    const [w, h] = registration.footprint, deck = registration.doors.find((d) => d.id === 'DeckDoor').position[2];
    options.terrace = [];
    for (let y = 0; y < h; y++) for (let x = 0; x < w; x++)
      if (!occupied.has([x, y, deck].join()) && occupied.has([x, y, deck - 1].join())) options.terrace.push([x, y, deck]);
  }
  if (id === 'Bathhouse') value.BuildingPipeTargetPortsSpec = {Ports: [await studyPipePort(id, 'PIPE_INLET')]};
  await applyLategame(value, id, options);
  await writeJson(data(...outputPath.split('/'), `${id}.IronTeeth.blueprint.json`), value);
  return `${outputPath}/${id}.IronTeeth.blueprint`;
}

async function makeReactor() {
  // One native Manufactory owns fuel, coolant and waste. Combining it with
  // GoodConsumingBuilding adds two IGoodProcessor components and cannot load.
  const value = clone(await readJson(vanilla('Buildings/Metal/Smelter/Smelter.IronTeeth.blueprint.json')));
  value.BuildingSpec = { ...value.BuildingSpec, BuildingCost: authoredCost('NuclearReactor'), ScienceCost: progression.implementedBuildingScienceOverrides.NuclearReactor };
  value.TemplateSpec = { ...value.TemplateSpec, TemplateName: 'NuclearReactor.IronTeeth', BackwardCompatibleTemplateNames: [] };
  value.PlaceableBlockObjectSpec = { ...value.PlaceableBlockObjectSpec, ToolGroupId: 'Power', ToolOrder: 250, DevModeTool: false };
  setLabels(value, 'NuclearReactor', 'Buildings/Power/NuclearReactor');
  const workerTemplate = await readJson(vanilla('Buildings/Metal/Smelter/Smelter.IronTeeth.blueprint.json'));
  value.WorkplaceSpec = { ...workerTemplate.WorkplaceSpec, MaxWorkers: 6, DefaultWorkers: 6, WorkerTypeUnlockCosts: [{ WorkerType: 'Bot', ScienceCost: 12000 }] };
  value.ManufactorySpec = { ProductionRecipeIds: ['NuclearWaste'] };
  value.MechanicalNodeSpec = { PowerOutput: 750000, PowerInput: 0, IsShaft: false };
  value.WorkshopPoweredGeneratorSpec = {};
  value.BuildingPipeTargetPortsSpec = coolantPorts('NuclearReactor');
  setModels(value, 'NuclearReactor', 'Buildings/Power/NuclearReactor');
  if (LATEGAME.has('NuclearReactor')) await applyLategame(value, 'NuclearReactor');
  else setGeometry(value, 'NuclearReactor');
  await writeJson(data('Buildings', 'Power', 'NuclearReactor', 'NuclearReactor.IronTeeth.blueprint.json'), value);
  return 'Buildings/Power/NuclearReactor/NuclearReactor.IronTeeth.blueprint';
}

// Coal and oil power plants (frontier_progression.json powerPlants): the
// native Iron Teeth Steam Engine generator at a larger scale, no workers.
// GoodConsumingBuilding burns fuel and boiler water per hour; native
// GoodPoweredGenerator pauses that consumption while the power graph does not
// require power and gives the full output while it consumes, day and night.
// The Steam Engine's own sound, smoke, animation and illumination specs come
// with the clone; its smoke attachments are replaced by the study's flues
// (vanilla_smoke.mjs runs them with PowerGeneratorParticleController).
const POWER_PLANTS = progression.powerPlants.buildings;
async function makePowerPlant(entry) {
  const {id} = entry, outputPath = `Buildings/Power/${id}`;
  if (!LATEGAME.has(id)) throw new Error(`${id}: its study is not integrated (tools/lategame_batches.json)`);
  if (entry.template !== 'SteamEngine' || entry.generator !== 'GoodPoweredGenerator')
    throw new Error(`${id}: power plants clone the native Steam Engine generator (template SteamEngine, generator GoodPoweredGenerator), not ${entry.template}/${entry.generator}`);
  if (entry.workers !== 0) throw new Error(`${id}: a GoodPoweredGenerator plant has no workers (workers 0)`);
  for (const key of ['fuelPerHour', 'waterPerHour', 'fullInventoryWorkHours'])
    if (!(typeof entry[key] === 'number' && entry[key] > 0)) throw new Error(`${id}: ${key} must be a positive number`);
  if (!(Number.isInteger(entry.powerOutputHp) && entry.powerOutputHp > 0)) throw new Error(`${id}: power output must be a positive integer`);
  if (!goodDefinitions.some(([good]) => good === entry.fuel)) throw new Error(`${id}: fuel ${entry.fuel} is not a generated good`);
  const value = clone(await readJson(vanilla('Buildings/Power/SteamEngine/SteamEngine.IronTeeth.blueprint.json')));
  for (const key of ['GoodConsumingBuildingSpec', 'GoodPoweredGeneratorSpec', 'PowerGeneratorSoundsSpec', 'GoodPoweredGeneratorAnimatorSpec',
    'MechanicalNodeIlluminatorSpec', 'PowerGeneratorParticleControllerSpec', 'MechanicalBuildingSpec'])
    if (!Object.hasOwn(value, key)) throw new Error(`Vanilla Steam Engine no longer has ${key}`);
  value.BuildingSpec = { ...value.BuildingSpec, BuildingCost: authoredCost(id), ScienceCost: entry.scienceUnlock };
  value.TemplateSpec = { ...value.TemplateSpec, TemplateName: `${id}.IronTeeth`, BackwardCompatibleTemplateNames: [] };
  value.PlaceableBlockObjectSpec = { ...value.PlaceableBlockObjectSpec, ToolGroupId: entry.toolGroup, ToolOrder: entry.toolOrder, DevModeTool: false };
  setLabels(value, id, outputPath);
  value.GoodConsumingBuildingSpec = { FullInventoryWorkHours: entry.fullInventoryWorkHours,
    ConsumedGoods: [{ GoodId: entry.fuel, GoodPerHour: entry.fuelPerHour }, { GoodId: 'Water', GoodPerHour: entry.waterPerHour }] };
  value.MechanicalNodeSpec = { PowerOutput: entry.powerOutputHp, PowerInput: 0, IsShaft: false };
  setModels(value, id, outputPath);
  await applyLategame(value, id);
  await writeJson(data(...outputPath.split('/'), `${id}.IronTeeth.blueprint.json`), value);
  return `${outputPath}/${id}.IronTeeth.blueprint`;
}

async function makeVault() {
  const value = clone(await readJson(vanilla('Buildings/Storage/LargeWarehouse/LargeWarehouse.IronTeeth.blueprint.json')));
  value.BuildingSpec = { ...value.BuildingSpec, BuildingCost: (await lategameCost('RadioactiveWasteVault')).map(([Id, Amount]) => ({ Id, Amount })), ScienceCost: progression.implementedBuildingScienceOverrides.RadioactiveWasteVault };
  value.TemplateSpec = { ...value.TemplateSpec, TemplateName: 'RadioactiveWasteVault.IronTeeth', BackwardCompatibleTemplateNames: [] };
  value.PlaceableBlockObjectSpec = { ...value.PlaceableBlockObjectSpec, ToolGroupId: 'Storage', ToolOrder: 61 };
  value.StockpileSpec = { ...value.StockpileSpec, MaxCapacity: 1600, WhitelistedGoodType: 'Box' };
  setLabels(value, 'RadioactiveWasteVault', 'Buildings/Storage/RadioactiveWasteVault');
  setModels(value, 'RadioactiveWasteVault', 'Buildings/Storage/RadioactiveWasteVault');
  if (LATEGAME.has('RadioactiveWasteVault')) {
    // Sealed storage: the warehouse's box columns would stand at the corner
    // cell, outside the berm, and the vault's contents are not on display.
    delete value.StockpileGoodColumnVisualizerSpec;
    await applyLategame(value, 'RadioactiveWasteVault');
  }
  else setGeometry(value, 'RadioactiveWasteVault');
  await writeJson(data('Buildings', 'Storage', 'RadioactiveWasteVault', 'RadioactiveWasteVault.IronTeeth.blueprint.json'), value);
  return 'Buildings/Storage/RadioactiveWasteVault/RadioactiveWasteVault.IronTeeth.blueprint';
}

for (const definition of goodDefinitions) await makeGood(definition);
for (const definition of recipeDefinitions) await makeRecipe(definition);
const buildingBlueprints = [];
for (const definition of buildingDefinitions) buildingBlueprints.push(await makeBuilding(definition));
await authorRestaurantNeed();
await authorHospitalNeed();
await authorGroceryNeed();
await authorShoreFishing();
buildingBlueprints.push(await makeReactor());
for (const entry of POWER_PLANTS) buildingBlueprints.push(await makePowerPlant(entry));
buildingBlueprints.push(await makeVault());
buildingBlueprints.push(await makeScrubber());
for (const entry of WELLBEING) buildingBlueprints.push(await makeAttraction(entry));

const collectionPath = data('GoodCollections', 'GoodCollection.IronTeeth.blueprint.json');
const goodsCollection = await readJson(collectionPath);
const currentGoods = goodsCollection.GoodCollectionSpec['Goods#append'];
if (!Array.isArray(currentGoods)) throw new Error('The base generator must author Goods#append.');
for (const [id] of goodDefinitions) if (currentGoods.includes(id)) throw new Error(`Duplicate generated good ${id}; run the base generator first.`);
goodsCollection.GoodCollectionSpec['Goods#append'] = [...currentGoods, ...goodDefinitions.map(([id]) => id)];
await writeJson(collectionPath, goodsCollection);

const templateCollectionPath = data('TemplateCollections', 'TemplateCollection.Buildings.IronTeeth.blueprint.json');
const templateCollection = await readJson(templateCollectionPath);
const currentTemplates = templateCollection.TemplateCollectionSpec['Blueprints#append'];
if (!Array.isArray(currentTemplates)) throw new Error('The base generator must author Blueprints#append.');
for (const path of buildingBlueprints) if (currentTemplates.includes(path)) throw new Error(`Duplicate generated template ${path}; run the base generator first.`);
templateCollection.TemplateCollectionSpec['Blueprints#append'] = [...currentTemplates, ...buildingBlueprints];
await writeJson(templateCollectionPath, templateCollection);

const localizationPath = data('Localizations', 'enUS.csv');
let localization = await readFile(localizationPath, 'utf8');
const rows = [];
const csvCell = (value) => {
  if (typeof value !== 'string') throw new TypeError('Localization cells must be authored strings.');
  const text = value;
  return /[",\r\n]/.test(text) ? `"${text.replaceAll('"', '""')}"` : text;
};
const csvRow = (id, text, comment = 'Deep Frontier') => [id, text, comment].map(csvCell).join(',');
for (const [id] of goodDefinitions) {
  const display = id.replace(/([A-Z])/g, ' $1').trim();
  rows.push(csvRow(`Good.${id}.DisplayName`, display));
  rows.push(csvRow(`Good.${id}.PluralDisplayName`, display));
}
for (const definition of buildingDefinitions) {
  const id = definition[0];
  const display = definition[9];
  rows.push(csvRow(`Building.${id}.DisplayName`, display));
  rows.push(csvRow(`Building.${id}.Description`, id === 'Restaurant'
    ? 'A 400 hp kitchen and dining hall. Workers serve fish, berries and prepared foods at tables, with coffee when stocked and water for thirsty diners. Ferments food and bakes sweet berry cake from berries, corn and water. Cake is cooked and eaten only here. Serves whichever main foods are in stock; a full meal of fish, berries, fermented mushrooms and eggplant rations also gives Fine Dining.'
    : id === 'FishHatchery'
    ? 'Breeds juvenile fish from fresh fish, algae and water. Only the front door row needs the bank; the deck stands on piles that reach the riverbed up to 6 m down, and clean water must stand at least 0.2 m up the marked pens. Stops during droughts or badwater contamination. Requires 55 hp.'
    : id === 'FisheryWorks'
    ? 'Raises fresh fish from juveniles, algae and delivered water, or presses fish into oil. Its basins reflect stored water and its wheel runs during production. The wheel wing may stand out over water on piles up to 6 m deep. Requires 80 hp.'
    : id === 'Hospital'
    ? HOSPITAL_DESCRIPTION
    : id === 'GroceryStore'
    ? 'Stocks canned fish, packaged food, algae and corn rations, and fermented cassava and soybeans. Two clerks restock 100 of each food. With 100 hp, an attending clerk and at least three stocked foods, nearby beavers gain up to +2 wellbeing within eight cells. Food remains available during power cuts and off-duty hours.'
    : Object.hasOwn(BUILDING_TEXT, id) ? BUILDING_TEXT[id][0]
    : `Deep Frontier ${display.toLowerCase()} production building`));
  rows.push(csvRow(`Building.${id}.FlavorDescription`, id === 'Restaurant'
    ? 'A good meal deserves a table, a view and good company.'
    : Object.hasOwn(BUILDING_TEXT, id) ? BUILDING_TEXT[id][1]
    : "The colony's next industrial step is visible in every pipe and belt."));
}
{
  const smog = await readJson(resolve(root, 'tools', 'smog_content.json'));
  const pct = (v) => `${Math.round(v * 100)}%`;
  rows.push(csvRow('Building.SmogScrubber.DisplayName', 'Smog scrubber'));
  rows.push(csvRow('Building.SmogScrubber.Description', `Removes ${pct(smog.scrubber.reduction)} of the smog within ${smog.scrubber.radius} tiles while powered and not paused; scrubbers and trees together remove at most ${pct(smog.settings.ScrubberMaxReduction)}. No workers. Requires ${smog.scrubber.proposed.powerInputHp} hp.`));
  rows.push(csvRow('Building.SmogScrubber.FlavorDescription', 'What goes up the smokestack comes down in the scrubber.'));
}
// Wellbeing attractions: names and needs from frontier_progression.json.
const WELLBEING_TEXT = {
  Bathhouse: [(e) => `Steam baths for up to ${e.capacity} beavers: a warm soak, a massage and a wash in one visit (Mud Bath, Massager and Wet Fur). Uses ${e.consumes[0][1]} water per hour, piped in at the boiler-room socket or carried by haulers, and ${e.powerDemandHp} hp.`,
    'The boilers run hot so the colony can run warm.'],
  TownPlaza: [(e) => `A civic square for up to ${e.capacity} beavers, who dance to the bandstand and gather round the fountain (Dance Pit and Campfire). Needs no power or supplies.`,
    'Every frontier town needs one place where nothing is being built.'],
  ObservationDeck: [(e) => `A viewing tower for up to ${e.capacity} beavers on its deck: the climb up the helical stair is exercise and the view is a rooftop terrace (Exercise Plaza and Rooftop Terrace). Paths and platforms may be built on the deck.`,
    'From up here, the whole frontier fits in one look.'],
};
for (const entry of WELLBEING) {
  if (!Object.hasOwn(WELLBEING_TEXT, entry.id)) throw new Error(`No authored text for ${entry.id}`);
  rows.push(csvRow(`Building.${entry.id}.DisplayName`, entry.name));
  rows.push(csvRow(`Building.${entry.id}.Description`, WELLBEING_TEXT[entry.id][0](entry)));
  rows.push(csvRow(`Building.${entry.id}.FlavorDescription`, WELLBEING_TEXT[entry.id][1]));
}
for (const id of ['NuclearReactor', 'RadioactiveWasteVault']) {
  const display = id === 'NuclearReactor' ? 'Nuclear Reactor' : 'Radioactive Waste Vault';
  rows.push(csvRow(`Building.${id}.DisplayName`, display));
  rows.push(csvRow(`Building.${id}.Description`, id === 'NuclearReactor'
    ? 'A 750000 hp reactor that consumes enriched fuel and pipe-fed coolant water. Produces spent-fuel casks and radioactive sludge that must be shipped off the map.'
    : 'Locked storage for radioactive waste; the contents must be processed or moved before demolition.'));
  rows.push(csvRow(`Building.${id}.FlavorDescription`, 'The frontier makes power and consequences at the same scale.'));
}
// Power plants: output, fuel and water rates from frontier_progression.json.
const POWER_PLANT_TEXT = {
  CoalPowerPlant: [(e) => `A coal-fired steam plant. Produces ${e.powerOutputHp.toLocaleString('en-US')} hp, day and night, burning ${e.fuelPerHour} coal and ${e.waterPerHour} water per hour while the network draws power. No workers. Its chimney pollutes the air for a wide area while it runs.`,
    'Black smoke, white steam and the hum of every machine in the district.'],
  OilPowerPlant: [(e) => `An oil-fired turbine plant. Produces ${e.powerOutputHp.toLocaleString('en-US')} hp, day and night, burning ${e.fuelPerHour} crude oil and ${e.waterPerHour} water per hour while the network draws power. No workers. Its two exhaust stacks pollute the air nearby while it runs, less than coal.`,
    'The deep ore gives up its oil, and the oil gives up its fire.'],
};
for (const entry of POWER_PLANTS) {
  if (!Object.hasOwn(POWER_PLANT_TEXT, entry.id)) throw new Error(`No authored text for ${entry.id}`);
  rows.push(csvRow(`Building.${entry.id}.DisplayName`, entry.name));
  rows.push(csvRow(`Building.${entry.id}.Description`, POWER_PLANT_TEXT[entry.id][0](entry)));
  rows.push(csvRow(`Building.${entry.id}.FlavorDescription`, POWER_PLANT_TEXT[entry.id][1]));
}
for (const [id] of recipeDefinitions) rows.push(csvRow(`Recipe.${id}.DisplayName`, Object.hasOwn(RECIPE_NAMES, id) ? RECIPE_NAMES[id] : id.replace(/([A-Z])/g, ' $1').trim()));
rows.push(csvRow('Need.PublicHealthcare.DisplayName','Public healthcare'));
for (const [id, text] of HOSPITAL_LOCALIZATION) rows.push(csvRow(id, text));
for (const [id, text] of RESTAURANT_LOCALIZATION) rows.push(csvRow(id, text));
rows.push(csvRow('Need.NeighborhoodGroceries.DisplayName','Neighborhood groceries'));
for (const [id, text, comment] of WATERSIDE_ROWS) rows.push(csvRow(id, text, comment));
const existingIds = new Set(localization.split(/\r?\n/).slice(1).map((line) => line.split(',')[0]));
for (const row of rows) if (!existingIds.has(row.split(',')[0])) localization += `${row}\n`;
await writeFile(localizationPath, localization, 'utf8');

console.log(`Created expansion content: ${goodDefinitions.length} goods, ${recipeDefinitions.length} recipes, ${buildingBlueprints.length} buildings.`);
// Rocket program: launch missions, odds, rewards and the story ending.
await (await import('./rocket_program_content.mjs')).applyRocketProgram();
await (await import('./meltdown_content.mjs')).applyMeltdownContent(); // Reactor meltdown and waste leaks (docs/meltdown.md).
await (await import('./cryogenic_content.mjs')).applyCryogenics(); // Cryogenic tank farm: power-gated intake, venting, pipe sockets.
await (await import('./narrative_content.mjs')).applyNarrative(); // Story chapters, evidence, record caches and the ending (docs/story.md).
await (await import('./radioactive_tide_content.mjs')).applyRadioactiveTide(); // Radioactive tide weather: names, sky fog overlay, top-bar icon (docs/radiation.md).
