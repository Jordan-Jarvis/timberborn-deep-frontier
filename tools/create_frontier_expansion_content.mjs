import { mkdir, readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import {applyRestaurant,authorRestaurantNeed,RESTAURANT_LOCALIZATION} from './civic_building_content.mjs';
import {applyFishery,applyHatchery,authorFisherFlag,WATERSIDE_ROWS} from './fishery_building_content.mjs';
import {applyHospital,authorHospitalNeed,HOSPITAL_DESCRIPTION,HOSPITAL_LOCALIZATION} from './hospital_building_content.mjs';
import {applyGroceryStore,authorGroceryNeed} from './grocery_building_content.mjs';
import {LATEGAME,applyLategame,studyPipePort} from './lategame_building_content.mjs';
import {CACHE} from './narrative_content.mjs';
import {lategameCost, buildingCost, scaledPower} from './lategame_costs.mjs';
import {unbindConstructionSite} from './construction_stage_content.mjs';
import {SCHOOL_WORKSHOP_SPECS} from './workforce_risk_content.mjs';
import {backwardGoodIds, backwardRecipeIds} from './good_migrations.mjs';

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

const goodDefinitions = [
  ['Coal', 'solid', 'Materials', 5196, 0.12, 0.14, 'coal'],
  ['Chemical', 'liquid', 'Ingredients', 10055, 0.42, 0.52, 'chemical'],
  ['RecoveredArtifact', 'solid', 'Materials', 5197, 0.62, 0.48, 'artifact'],
  ['Fertilizer', 'solid', 'Ingredients', 5200, 0.58, 0.72, 'fertilizer'],
  ['FreshFish', 'food', 'Food', 11090, 0.20, 0.55, 'fish'],
  ['JuvenileFish', 'solid', 'Ingredients', 5205, 0.20, 0.55, 'juvenile'],
  ['FishOil', 'liquid', 'Ingredients', 10040, 0.95, 0.74, 'oil'],
  ['CannedFish', 'food', 'Food', 11100, 0.32, 0.58, 'can'],
  ['Medicine', 'solid', 'Ingredients', 5210, 0.72, 0.84, 'medicine'],
  ['SweetBerryCake', 'food', 'Food', 11140, 0.79, 0.36, 'cake'],
  ['HighGradeSteel', 'solid', 'Materials', 5100, 0.34, 0.38, 'steel'],
  ['Alloy', 'solid', 'Materials', 5110, 0.38, 0.44, 'alloy'],
  ['Polymer', 'solid', 'Materials', 5120, 0.18, 0.52, 'polymer'],
  // Retired 2026-10-30 for the vanilla Iron Teeth Grease (Grease Factory:
  // Extract + Canola Oil): unproduced and unused, kept so saves holding it load
  // (tools/content_policy.json legacySaveOnlyGoods).
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
  spec.BackwardCompatibleIds = backwardGoodIds(id);
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
  // One step from wood and algae (the retired Compost intermediate folded in,
  // tools/content_policy.json migratedGoods): the two old recipes added together.
  ['Fertilizer', 'Fertilizer', 2.0, [{ Id: 'Log', Amount: 1 }, { Id: 'Algae', Amount: 2 }, { Id: 'Water', Amount: 2 }], [{ Id: 'Fertilizer', Amount: 2 }], 'Fertilizer'],
  ['JuvenileFish', 'JuvenileFish', 2.0, [{ Id: 'Algae', Amount: 1 }, { Id: 'Water', Amount: 2 }], [{ Id: 'JuvenileFish', Amount: 2 }], 'JuvenileFish'],
  ['FreshFish', 'FreshFish', 3.0, [{ Id: 'JuvenileFish', Amount: 1 }, { Id: 'Algae', Amount: 1 }, { Id: 'Water', Amount: 3 }], [{ Id: 'FreshFish', Amount: 3 }], 'FreshFish'],
  ['FishOil', 'FishOil', 1.0, [{ Id: 'FreshFish', Amount: 2 }], [{ Id: 'FishOil', Amount: 1 }], 'FishOil'],
  ['CannedFish', 'CannedFish', 2.0, [{ Id: 'FreshFish', Amount: 3 }, { Id: 'MetalBlock', Amount: 1 }, { Id: 'FishOil', Amount: 1 }], [{ Id: 'CannedFish', Amount: 3 }], 'CannedFish'],
  // Greenhouse glasshouse crops: two fertilizer per 8 h cycle. Products are 8x
  // the first balance (user, 2026-10-27), about 12-16x an equal-area vanilla
  // field (42 ground cells), so the fertilizer chain pays off.
  ['GreenhouseEggplant', 'Eggplant', 8.0, [{ Id: 'Fertilizer', Amount: 2 }, { Id: 'Water', Amount: 4 }], [{ Id: 'Eggplant', Amount: 48 }], 'Eggplant'],
  ['GreenhouseKohlrabi', 'Kohlrabi', 8.0, [{ Id: 'Fertilizer', Amount: 2 }, { Id: 'Water', Amount: 4 }], [{ Id: 'Kohlrabi', Amount: 112 }], 'Kohlrabi'],
  ['GreenhouseCoffee', 'CoffeeBean', 8.0, [{ Id: 'Fertilizer', Amount: 2 }, { Id: 'Water', Amount: 3 }], [{ Id: 'CoffeeBean', Amount: 24 }], 'CoffeeBean'],
  ['Medicine', 'Medicine', 2.0, [{ Id: 'Mushroom', Amount: 2 }, { Id: 'Algae', Amount: 1 }, { Id: 'Water', Amount: 1 }], [{ Id: 'Medicine', Amount: 2 }], 'Medicine'],
  // Steel (id HighGradeSteel) from Deep Iron (id DeepAlloy): the deep metal
  // ladder Deep Ore -> Deep Iron -> Steel -> Alloy (docs/progression.md
  // "Progression sets"). 2 Deep Iron replace the 4 Metal Blocks, keeping the
  // embodied value close (11.8 -> 11.4). Limestone is the flux (the retired
  // Flux intermediate, tools/content_policy.json migratedGoods).
  ['HighGradeSteel', 'HighGradeSteel', 4.0, [{ Id: 'DeepAlloy', Amount: 2 }, { Id: 'Coal', Amount: 2 }, { Id: 'Limestone', Amount: 1 }], [{ Id: 'HighGradeSteel', Amount: 2 }], 'HighGradeSteel'],
  ['Alloy', 'Alloy', 1.5, [{ Id: 'HighGradeSteel', Amount: 2 }, { Id: 'DeepAlloy', Amount: 1 }], [{ Id: 'Alloy', Amount: 2 }], 'Alloy'],
  // Industrial chemical from crude oil and extract (ChemicalWorks): the
  // chemistry ladder Crude Oil -> Chemical -> Polymer (docs/progression.md
  // "Progression sets"). 2 Crude Oil replace the 4 Badwater at the same
  // embodied value (3.12); Extract is the Centrifuge's badwater distillate.
  ['Chemical', 'Chemical', 2.0, [{ Id: 'CrudeOil', Amount: 2 }, { Id: 'Extract', Amount: 1 }], [{ Id: 'Chemical', Amount: 2 }], 'Chemical'],
  ['Polymer', 'Polymer', 3.0, [{ Id: 'CrudeOil', Amount: 3 }, { Id: 'Chemical', Amount: 1 }, { Id: 'Water', Amount: 2 }], [{ Id: 'Polymer', Amount: 3 }], 'Polymer'],
  ['MachineCore', 'MachineCore', 2.0, [{ Id: 'Alloy', Amount: 2 }, { Id: 'Polymer', Amount: 1 }, { Id: 'Gear', Amount: 2 }, { Id: 'DeepAlloy', Amount: 1 }], [{ Id: 'MachineCore', Amount: 1 }], 'MachineCore'],
  // Second use (docs/progression.md "Second uses"): graphite electrodes (coal) in power modules.
  ['Electronics', 'Electronics', 2.0, [{ Id: 'MachineCore', Amount: 1 }, { Id: 'MetalPart', Amount: 2 }, { Id: 'Polymer', Amount: 1 }], [{ Id: 'Electronics', Amount: 1 }], 'Electronics'],
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
  ['Cryocoolant', 'Cryocoolant', 2.0, [{ Id: 'Polymer', Amount: 1 }, { Id: 'Grease', Amount: 1 }, { Id: 'Water', Amount: 2 }], [{ Id: 'Cryocoolant', Amount: 2 }], 'Cryocoolant'],
  ['Electrolysis', 'HydrogenGas/OxygenGas', 3.0, [{ Id: 'PureWater', Amount: 8 }], [{ Id: 'HydrogenGas', Amount: 4 }, { Id: 'OxygenGas', Amount: 4 }], 'HydrogenGas'],
  ['Liquefaction', 'LiquidHydrogen/LiquidOxygen', 2.0, [{ Id: 'HydrogenGas', Amount: 4 }, { Id: 'OxygenGas', Amount: 4 }, { Id: 'Cryocoolant', Amount: 2 }], [{ Id: 'LiquidHydrogen', Amount: 2 }, { Id: 'LiquidOxygen', Amount: 2 }], 'LiquidHydrogen'],
  ['RocketAirframe', 'RocketAirframe', 1.0, [{ Id: 'HighGradeSteel', Amount: 12 }, { Id: 'Alloy', Amount: 8 }, { Id: 'TreatedPlank', Amount: 4 }, { Id: 'Polymer', Amount: 4 }], [{ Id: 'RocketAirframe', Amount: 1 }], 'RocketAirframe'],
  ['PropulsionPackage', 'PropulsionPackage', 1.0, [{ Id: 'Alloy', Amount: 10 }, { Id: 'MachineCore', Amount: 4 }, { Id: 'Polymer', Amount: 6 }, { Id: 'HighGradeSteel', Amount: 6 }], [{ Id: 'PropulsionPackage', Amount: 1 }], 'PropulsionPackage'],
  // Guidance computers and telemetry read the recovered artifacts' human data
  // drives directly (the retired ArchiveData intermediate: 2 artifacts, grease
  // and a metal part, folded into each recipe; tools/content_policy.json migratedGoods).
  ['GuidanceComputer', 'GuidanceComputer', 1.0, [{ Id: 'Electronics', Amount: 4 }, { Id: 'MachineCore', Amount: 2 }, { Id: 'RecoveredArtifact', Amount: 2 }, { Id: 'Grease', Amount: 1 }], [{ Id: 'GuidanceComputer', Amount: 1 }], 'GuidanceComputer'],
  ['MissionPayload', 'MissionPayload', 1.0, [{ Id: 'GuidanceComputer', Amount: 1 }, { Id: 'RecoveredArtifact', Amount: 2 }, { Id: 'TreatedPlank', Amount: 2 }], [{ Id: 'MissionPayload', Amount: 1 }], 'MissionPayload'],
  // The licence token recipes are retired: specialists are trained beavers
  // (tools/workforce_risks.json). The licence goods stay for saves only.
  // Waste balance: 0.5 waste/hour per reactor; one refinery (4 per 8 h) keeps up.
  // Radiation (docs/radiation.md): solid RadioactiveWaste stays as spent-fuel
  // casks (vault custody, refinery input). Activated coolant leaves as liquid
  // RadioactiveSludge, and the refinery concentrates casks into sludge for the
  // map-edge Radioactive Waste Export. RadioactiveSludge and ContaminatedWater
  // are defined by tools/radiation_content.mjs later in the generation chain.
  // Each cycle's spent-fuel cask is steel and concrete (user 2026-10-29:
  // building materials need ongoing industrial uses).
  ['NuclearWaste', 'RadioactiveWaste', 2, [{ Id: 'ReactorCoolantWater', Amount: 6 }, { Id: 'HighGradeSteel', Amount: 1 }, { Id: 'Concrete', Amount: 2 }], [{ Id: 'RadioactiveWaste', Amount: 1 }, { Id: 'RadioactiveSludge', Amount: 1 }], 'RadioactiveWaste'],
  ['WasteRefining', 'RadioactiveSludge', 8.0, [{ Id: 'RadioactiveWaste', Amount: 4 }, { Id: 'Water', Amount: 8 }], [{ Id: 'RadioactiveSludge', Amount: 6 }], 'RadioactiveSludge'],
  ['DecontaminateWater', 'Water', 4.0, [{ Id: 'ContaminatedWater', Amount: 10 }, { Id: 'Chemical', Amount: 1 }], [{ Id: 'Water', Amount: 8 }, { Id: 'RadioactiveSludge', Amount: 1 }], 'ContaminatedWater'],
  ['GuidanceTelemetry', 'RecoveredTelemetry', 1.0, [{ Id: 'GuidanceComputer', Amount: 1 }, { Id: 'RecoveredArtifact', Amount: 2 }, { Id: 'MetalPart', Amount: 1 }], [{ Id: 'RecoveredTelemetry', Amount: 1 }], 'RecoveredTelemetry'],
  // Archive Excavation (planned, frontier_progression.json plannedBuildings):
  // charges and shoring open human ruins for artifacts and their sealed data drives.
  ['RecoveredArtifact', 'RecoveredArtifact', 6.0, [{ Id: 'Explosives', Amount: 1 }, { Id: 'TreatedPlank', Amount: 2 }], [{ Id: 'RecoveredArtifact', Amount: 1 }], 'RecoveredArtifact'],
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
  ['ReinforcedBotChassis', 'BotChassis', 4.0, [{ Id: 'Alloy', Amount: 1 }, { Id: 'Polymer', Amount: 1 }], [{ Id: 'BotChassis', Amount: 2 }], 'BotChassis'],
  ['ServoBotLimbs', 'BotLimb', 4.0, [{ Id: 'MachineCore', Amount: 1 }, { Id: 'Grease', Amount: 1 }, { Id: 'MetalPart', Amount: 2 }], [{ Id: 'BotLimb', Amount: 4 }], 'BotLimb'],
  ['BotCortex', 'BotHead', 4.0, [{ Id: 'Electronics', Amount: 1 }, { Id: 'Polymer', Amount: 1 }], [{ Id: 'BotHead', Amount: 2 }], 'BotHead'],
  // Uranium Processing Plant: spent casks reprocessed into fresh fuel. The
  // fuel's own life yields ten casks, so reprocessing never shrinks waste.
  ['FuelReprocessing', 'EnrichedFuel', 4.0, [{ Id: 'RadioactiveWaste', Amount: 4 }, { Id: 'Chemical', Amount: 2 }, { Id: 'Yellowcake', Amount: 1 }], [{ Id: 'EnrichedFuel', Amount: 1 }, { Id: 'RadioactiveWaste', Amount: 2 }], 'EnrichedFuel'],
  // Waste Refinery: contaminated water as process water (radioactivity stays
  // in the radioactive water). No chemicals and no vitrification (user
  // direction 2026-10-29: the waste chain was too complex); casks can also be
  // dissolved and shipped at the Radioactive Waste Export.
  ['ContaminatedWaterRefining', 'RadioactiveSludge', 8.0, [{ Id: 'RadioactiveWaste', Amount: 4 }, { Id: 'ContaminatedWater', Amount: 8 }], [{ Id: 'RadioactiveSludge', Amount: 6 }], 'RadioactiveSludge'],
  // Badwater filtering (user direction 2026-10-29): the refinery is not a
  // single-purpose building. Filter Media, the input with the fewest uses.
  ['BadwaterFiltering', 'Water', 2.0, [{ Id: 'Badwater', Amount: 10 }, { Id: 'FilterMedia', Amount: 1 }], [{ Id: 'Water', Amount: 8 }], 'Badwater'],
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
  CarbonFilterMedia: 'Filter media from coal',
  BrineChemical: 'Chemicals from concentrated waste',
  GreenhouseAquaponics: 'Kohlrabi and fresh fish',
  FuelReprocessing: 'Enriched fuel from radioactive waste',
  ContaminatedWaterRefining: 'Radioactive water from contaminated water',
  DecontaminateWater: 'Water from contaminated water',
  BadwaterFiltering: 'Water from badwater',
};
for (const id of Object.keys(RECIPE_NAMES)) if (!recipeDefinitions.some(([recipe]) => recipe === id)) throw new Error(`RECIPE_NAMES names undefined recipe ${id}`);

async function makeRecipe([id, outputLabel, hours, ingredients, products, iconId]) {
  const base = clone(await readJson(vanilla('Recipes/Recipe.MetalBlock.blueprint.json')));
  base.RecipeSpec = {
    ...base.RecipeSpec,
    Id: id,
    BackwardCompatibleIds: backwardRecipeIds(id),
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
  ['FertilizerWorks', 'Buildings/Food/FertilizerWorks', 'OilPress', 'Fertilizer', 'Food', 105, 80, 2, 350, 'Fertilizer Works'],
  ['FishHatchery', 'Buildings/Food/FishHatchery', 'HydroponicGarden', 'JuvenileFish', 'Food', 111, 55, 2, 600, 'Fish Hatchery'],
  ['FisheryWorks', 'Buildings/Food/FisheryWorks', 'FoodFactory', 'FreshFish,FishOil', 'Food', 113, 80, 3, 900, 'Fishery Works'],
  ['FoodPackagingWorks', 'Buildings/Food/FoodPackagingWorks', 'FoodFactory', 'CannedFish', 'Food', 114, 140, 3, 1400, 'Food Packaging Works'],
  ['PublicHealthLab', 'Buildings/Wellbeing/PublicHealthLab', 'OilPress', 'Medicine', 'Wellbeing', 36, 100, 3, 1000, 'Public Health Lab'],
  ['GroceryStore', 'Buildings/Food/GroceryStore', 'FoodFactory', '', 'Wellbeing', 38, progression.groceryStore.powerDemandHp, progression.groceryStore.workers, progression.groceryStore.scienceUnlock, 'Grocery Store'],
  ['Restaurant', 'Buildings/Food/Restaurant', 'FoodFactory', progression.restaurant.kitchenRecipes.join(','), 'Wellbeing', 37, progression.restaurant.powerDemandHp, 4, 1000, 'Restaurant'],
  ['Hospital', 'Buildings/Wellbeing/Hospital', 'FoodFactory', '', 'Wellbeing', 40, progression.hospital.powerDemandHp, progression.hospital.workers, progression.hospital.scienceUnlock, 'Hospital'],
  ['Greenhouse', 'Buildings/Food/Greenhouse', 'HydroponicGarden', 'GreenhouseEggplant,GreenhouseKohlrabi,GreenhouseCoffee,GreenhouseAquaponics', 'Food', 112, 35, 1, 600, 'Greenhouse'],
  ['ChemicalWorks', 'Buildings/Metal/ChemicalWorks', 'Smelter', 'Chemical,BrineChemical,Polymer,Cryocoolant', 'Metal', 40, 3500, 8, 9000, 'Chemical Works'],
  ['PrecisionMachineWorks', 'Buildings/Metal/PrecisionMachineWorks', 'BotPartFactory', 'MachineCore,Electronics,PowerModule,ReinforcedBotChassis,ServoBotLimbs,BotCortex', 'Metal', 42, 2200, 6, 12000, 'Precision Machine Works'],
  ['WaterTreatmentPlant', 'Buildings/Water/WaterTreatmentPlant', 'Centrifuge', 'PureWater,ReactorCoolantWater,FilterMedia,CarbonFilterMedia', 'Water', 43, 500, 4, 1800, 'Water Treatment Plant'],
  ['TechnicalSchool', 'Buildings/Science/TechnicalSchool', 'Inventor', '', 'Science', 92, 300, 4, 2200, 'Technical School'],
  ['UraniumProcessingPlant', 'Buildings/Metal/UraniumProcessingPlant', 'Centrifuge', 'Yellowcake,EnrichedFuel,FuelReprocessing', 'Metal', 45, 5000, 6, progression.implementedBuildingScienceOverrides.UraniumProcessingPlant, 'Uranium Processing Plant'],
  ['RadioactiveWasteRefinery', 'Buildings/Metal/RadioactiveWasteRefinery', 'Centrifuge', 'WasteRefining,ContaminatedWaterRefining,DecontaminateWater,BadwaterFiltering', 'Metal', 47, 8000, 6, progression.implementedBuildingScienceOverrides.RadioactiveWasteRefinery, 'Radioactive Waste Refinery'],
  ['ElectrolysisPlant', 'Buildings/Metal/ElectrolysisPlant', 'Centrifuge', 'Electrolysis', 'Metal', 47, 6000, 5, 30000, 'Electrolysis Plant'],
  ['CryogenicLiquefactionPlant', 'Buildings/Metal/CryogenicLiquefactionPlant', 'Centrifuge', 'Liquefaction', 'Metal', 48, 10000, 6, 40000, 'Cryogenic Liquefaction Plant'],
  ['RocketAssemblyHangar', 'Buildings/Metal/RocketAssemblyHangar', 'FoodFactory', 'RocketAirframe,PropulsionPackage', 'Metal', 50, 12000, 10, 125000, 'Rocket Assembly Hangar'],
  ['MissionControl', 'Buildings/Science/MissionControl', 'Inventor', 'GuidanceComputer,MissionPayload,GuidanceTelemetry', 'Science', 49, 1500, 4, 75000, 'Mission Control'],
  ['LaunchPad', 'Buildings/Metal/LaunchPad', 'FoodFactory', 'GuidanceTelemetry', 'Metal', 51, 25000, 8, 200000, 'Launch Pad'],
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

// Authored player-facing text, one entry per building: [description, flavor].
// Descriptions follow the vanilla tooltip (one or two short sentences: what the
// building is for and the one thing a player must know to place or run it). The
// native tooltip already lists cost, science, workers, power and recipes, so
// those numbers stay out of the prose; tools/validate_building_descriptions.mjs
// checks the length. Later modules extend or replace some of them: the Launch
// Pad (rocket_program_content.mjs) and the Nuclear Reactor, vault and refinery
// (meltdown_content.mjs); the Hospital's comes from hospital_building_content.mjs.
// bot_upkeep_content.mjs and connection_content.mjs append the upkeep and pipe clauses.
// Flavor lines are one per building, in the vanilla manner (a wry line about the
// place, not a rule); tools/validate_building_descriptions.mjs rejects a flavor
// shared by two different buildings.
const BUILDING_TEXT = {
  FertilizerWorks: ['Makes fertilizer from logs and algae for the Greenhouse.',
    'Logs and algae go in. Nobody asks about the smell.'],
  FishHatchery: ['Raises juvenile fish using algae and water. Its pens need clean river water beneath them.',
    'Thousands of tiny fish and one very patient beaver.'],
  FisheryWorks: ['Raises juvenile fish into fresh fish, or presses fresh fish into fish oil.',
    'Grow them big, then press the rest for oil.'],
  FoodPackagingWorks: ['Cans fresh fish with fish oil in metal tins. Canned fish feeds beavers and stocks the Grocery Store.',
    'Fish in a tin: the frontier lunch, whether it likes it or not.'],
  PublicHealthLab: ['Makes medicine from mushrooms and algae for the Hospital and the Technical School.',
    'Mushrooms, algae and a great deal of careful stirring.'],
  GroceryStore: ['A neighborhood shop for canned fish, rations and fermented food. Staffed and stocked with three or more foods, it gives nearby beavers up to +2 wellbeing.',
    'Everything a busy beaver needs, two paws from home.'],
  Restaurant: ['Serves food at its tables and makes sweet berry cake and fermented food. A meal of fresh fish, berries, fermented mushrooms and an eggplant ration gives Fine dining.',
    'A good meal deserves a table, a view and good company.'],
  Hospital: [null, 'Rest, clean water and a very strict ward nurse.'], // HOSPITAL_DESCRIPTION
  Greenhouse: ['Grows eggplants, kohlrabi and coffee beans indoors with fertilizer. Aquaponics also raises fresh fish from juvenile fish.',
    'Summer all year round, under glass.'],
  ChemicalWorks: ['Makes chemicals and polymer from crude oil and extract, and cryocoolant from polymer and grease.',
    'Oil and extract go in, chemistry comes out, and the smell stays.'],
  PrecisionMachineWorks: ['Builds machine cores, electronics, power modules, bot parts and reinforced bot frames.',
    'Measure twice, file once, and never sneeze near the electronics.'],
  WaterTreatmentPlant: ['Filters water into pure water, leaving concentrated waste, and makes filter media and reactor coolant water.',
    'Every barrel tested, every filter changed on time.'],
  TechnicalSchool: ['Beavers study here in their free time to become metallurgists, reactor operators or flight engineers. Each school teaches one, chosen in its panel.',
    'Night classes for beavers who want a dangerous job done properly.'],
  UraniumProcessingPlant: ['Turns uranium ore into enriched fuel and reactor power cells, and reprocesses spent fuel. Its fuel leaves radioactive waste.',
    'Yellowcake is not for eating, however much it looks like it.'],
  // Replaced by meltdown_content.mjs (PRODUCER_DESCRIPTIONS) with its risk text.
  RadioactiveWasteRefinery: ['Refines radioactive waste.', 'It turns a problem you store into a problem you can ship.'],
  ElectrolysisPlant: ['Splits pure water into hydrogen gas and oxygen gas.',
    'Water goes in. Two very excitable gases come out.'],
  CryogenicLiquefactionPlant: ['Chills hydrogen and oxygen gas with cryocoolant into liquid hydrogen and liquid oxygen, the rocket fuel.',
    'So cold that the frost has frost.'],
  RocketAssemblyHangar: ['Builds rocket airframes and propulsion packages for the Launch Pad.',
    'The tallest thing the colony has ever built, one piece at a time.'],
  MissionControl: ['Turns recovered artifacts into guidance computers, mission payloads and telemetry. Staffed and powered, it lowers the launch risk.',
    'Old human drives, new beaver math and a lot of coffee.'],
  // Replaced by rocket_program_content.mjs (GENERIC_PAD_DESCRIPTION).
  LaunchPad: ["Launches the colony's rockets.", 'Everything the colony has learned, pointed at the sky.'],
  SteelMill: ['Makes steel and alloy from deep iron, coal and limestone. Only trained metallurgists can work here, and the work is dangerous.',
    'Every reactor, rocket and machine core starts as a white-hot pour on this floor.'],
  ArchiveExcavation: [`Digs up recovered artifacts anywhere with explosives. Within ${CACHE.spec.SurveyRadius} tiles of a Human Record Cache, it also surveys the cache for ${CACHE.spec.RewardAmount} more.`,
    'The humans buried their warnings in the strata. Dig carefully.'],
  CryogenicTankFarm: ['Stores one fuel: liquid hydrogen or liquid oxygen. It takes fuel only while powered; without power the fuel starts to vent.',
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
  // The construction site (vanilla base + generated stage) is bound by construction_stage_content.mjs.
  unbindConstructionSite(value);
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

// Rule-owned rows (late-game buildings) already carry their tier's costFactor;
// every other authored cost is scaled here by its science unlock's tier.
function authoredCost(id, science) {
  if(id==='Hospital')return buildingCost(id,clone(progression.hospital.buildingCost),science);
  if(id==='GroceryStore')return buildingCost(id,clone(progression.groceryStore.buildingCost),science);
  if(!Object.hasOwn(constructionCosts.buildings,id))throw new Error('Missing explicit construction cost: '+id);
  const rows=constructionCosts.buildings[id];
  if(new Set(rows.map(([good])=>good)).size!==rows.length||
     rows.some(([good,amount])=>typeof good!=='string'||!Number.isInteger(amount)||amount<=0))
    throw new Error('Invalid authored construction cost: '+id);
  const cost=rows.map(([Id,Amount])=>({Id,Amount}));
  return Object.hasOwn(constructionCosts.lategameTier,id)?cost:buildingCost(id,cost,science);
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
    BuildingCost: authoredCost(id, science),
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
  // Every building row is a consumer; its draw follows the power rule (lategame_costs.mjs scaledPower).
  const hp = scaledPower(id, power, science);
  if (value.MechanicalNodeSpec) {
    value.MechanicalNodeSpec = { ...value.MechanicalNodeSpec, PowerOutput: 0, PowerInput: hp, IsShaft: false };
  } else {
    // An unpowered template (HydroponicGarden for the FishHatchery and Greenhouse) becomes a consumer.
    // Every vanilla powered consumer also carries the native connector target, which draws the gear
    // socket where a shaft or generator meets a transput (MechanicalConnectorActivator, 1.1.2.8);
    // without it a shaft ends at a bare wall (build 176 user report).
    value.MechanicalNodeSpec = { PowerOutput: 0, PowerInput: hp, IsShaft: false };
    value.MechanicalBuildingSpec = {};
    value.MechanicalConnectorTargetSpec = {};
  }
  if (id === 'TechnicalSchool' || id === 'MissionControl') {
    value.MechanicalNodeSpec = { PowerOutput: 0, PowerInput: hp, IsShaft: false };
    value.MechanicalBuildingSpec = {};
  }
  // Nobody staffs the Technical School: it takes the Inventor's building, not
  // its workshop. workforce_risk_content.mjs makes it a goods-consuming
  // attraction for free-time study (tools/workforce_risks.json school).
  if (id === 'TechnicalSchool') for (const key of SCHOOL_WORKSHOP_SPECS) delete value[key];
  setModels(value, id, outputPath);
  if (id === 'CryogenicTankFarm') configureTankFarm(value);
  if(id==='Restaurant')await applyRestaurant(value);
  else if(id==='FisheryWorks')await applyFishery(value);
  else if(id==='FishHatchery')await applyHatchery(value);
  else if(id==='Hospital')await applyHospital(value);
  else if(id==='GroceryStore')await applyGroceryStore(value);
  else if(LATEGAME.has(id))await applyLategame(value,id);
  else setGeometry(value, id);
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
  value.BuildingSpec = {...value.BuildingSpec, BuildingCost: (await lategameCost(id, science)).map(([Id, Amount]) => ({Id, Amount})), ScienceCost: science};
  value.TemplateSpec = {...value.TemplateSpec, TemplateName: `${id}.IronTeeth`, BackwardCompatibleTemplateNames: []};
  value.PlaceableBlockObjectSpec = {...value.PlaceableBlockObjectSpec, ToolGroupId: 'Wellbeing', ToolOrder: 160, DevModeTool: false};
  value.MechanicalNodeSpec = {PowerOutput: 0, PowerInput: scaledPower(id, design.powerInputHp, science), IsShaft: false};
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
  value.BuildingSpec = {...value.BuildingSpec, BuildingCost: (await lategameCost(id, entry.scienceUnlock)).map(([Id, Amount]) => ({Id, Amount})), ScienceCost: entry.scienceUnlock};
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
    value.MechanicalNodeSpec = {...value.MechanicalNodeSpec, PowerOutput: 0, PowerInput: scaledPower(id, entry.powerDemandHp, entry.scienceUnlock), IsShaft: false};
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
  value.BuildingSpec = { ...value.BuildingSpec, BuildingCost: authoredCost('NuclearReactor', progression.implementedBuildingScienceOverrides.NuclearReactor), ScienceCost: progression.implementedBuildingScienceOverrides.NuclearReactor };
  value.TemplateSpec = { ...value.TemplateSpec, TemplateName: 'NuclearReactor.IronTeeth', BackwardCompatibleTemplateNames: [] };
  value.PlaceableBlockObjectSpec = { ...value.PlaceableBlockObjectSpec, ToolGroupId: 'Power', ToolOrder: 250, DevModeTool: false };
  setLabels(value, 'NuclearReactor', 'Buildings/Power/NuclearReactor');
  const workerTemplate = await readJson(vanilla('Buildings/Metal/Smelter/Smelter.IronTeeth.blueprint.json'));
  value.WorkplaceSpec = { ...workerTemplate.WorkplaceSpec, MaxWorkers: 6, DefaultWorkers: 6, WorkerTypeUnlockCosts: [{ WorkerType: 'Bot', ScienceCost: 12000 }] };
  value.ManufactorySpec = { ProductionRecipeIds: ['NuclearWaste'] };
  value.MechanicalNodeSpec = { PowerOutput: 1000000, PowerInput: 0, IsShaft: false };
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
  value.BuildingSpec = { ...value.BuildingSpec, BuildingCost: authoredCost(id, entry.scienceUnlock), ScienceCost: entry.scienceUnlock };
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

// Modular Warehouse (frontier_progression.json modularWarehouse; behaviour in
// Scripts/ModularStorage): the core haulers use and the Warehouse Module that
// attaches to it, both from the vanilla Large Warehouse without its native
// single-good stockpile and its box columns (the studies show their own
// crates). The core's ModularWarehouseSpec gives the slots and its own
// capacity; a module (WarehouseModuleSpec) adds capacity and a slot, holds no
// goods and has no door, so it loses the warehouse's entrance, access and
// enterable specs (lategame_building_content.mjs doorless). Unpowered and
// worker-free, as the vanilla warehouses. Costs come from the late-game rule
// (T1, early goods) like the Smog Scrubber's.
const MODULAR = progression.modularWarehouse;
async function makeModularStorage(entry, specs, doorless) {
  const {id, template, toolGroup, scienceUnlock: science, toolOrder} = entry;
  if (template !== 'LargeWarehouse' || toolGroup !== 'Storage') throw new Error(`${id}: modular storage clones the vanilla Large Warehouse into Storage`);
  if (!LATEGAME.has(id)) throw new Error(`${id}: its study is not integrated (tools/lategame_batches.json)`);
  const outputPath = `Buildings/Storage/${id}`;
  const value = clone(await readJson(vanilla('Buildings/Storage/LargeWarehouse/LargeWarehouse.IronTeeth.blueprint.json')));
  removeTemplateSpecs(value, ['StockpileSpec', 'StockpileGoodColumnVisualizerSpec'], id);
  if (doorless) removeTemplateSpecs(value, ['EnterableSpec', 'BuildingAccessibleSpec'], id);
  if (value.MechanicalNodeSpec || value.WorkplaceSpec) throw new Error(`${id}: the Large Warehouse template gained power or workers`);
  value.BuildingSpec = {...value.BuildingSpec, BuildingCost: (await lategameCost(id, science)).map(([Id, Amount]) => ({Id, Amount})), ScienceCost: science};
  value.TemplateSpec = {...value.TemplateSpec, TemplateName: `${id}.IronTeeth`, BackwardCompatibleTemplateNames: []};
  value.PlaceableBlockObjectSpec = {...value.PlaceableBlockObjectSpec, ToolGroupId: 'Storage', ToolOrder: toolOrder, DevModeTool: false};
  Object.assign(value, specs);
  setLabels(value, id, outputPath);
  setModels(value, id, outputPath);
  await applyLategame(value, id, doorless ? {doorless: true} : {});
  await writeJson(data(...outputPath.split('/'), `${id}.IronTeeth.blueprint.json`), value);
  return `${outputPath}/${id}.IronTeeth.blueprint`;
}
async function makeModularWarehouse() {
  const {core} = MODULAR;
  if (!Number.isInteger(core.maxSlots) || core.maxSlots < 1 || !Number.isInteger(core.capacity) || core.capacity < 1 || core.goodType !== 'Box')
    throw new Error('ModularWarehouse: modularWarehouse.core needs whole positive maxSlots and capacity of Box goods');
  return makeModularStorage(core, {ModularWarehouseSpec: {MaxSlots: core.maxSlots, CoreCapacity: core.capacity, GoodType: core.goodType}}, false);
}
async function makeWarehouseModule() {
  const {module} = MODULAR;
  if (!Number.isInteger(module.capacity) || module.capacity < 1) throw new Error('WarehouseModule: modularWarehouse.module needs a whole positive capacity');
  return makeModularStorage(module, {WarehouseModuleSpec: {Capacity: module.capacity}}, true);
}

async function makeVault() {
  const value = clone(await readJson(vanilla('Buildings/Storage/LargeWarehouse/LargeWarehouse.IronTeeth.blueprint.json')));
  const vaultScience = progression.implementedBuildingScienceOverrides.RadioactiveWasteVault;
  value.BuildingSpec = { ...value.BuildingSpec, BuildingCost: (await lategameCost('RadioactiveWasteVault', vaultScience)).map(([Id, Amount]) => ({ Id, Amount })), ScienceCost: vaultScience };
  value.TemplateSpec = { ...value.TemplateSpec, TemplateName: 'RadioactiveWasteVault.IronTeeth', BackwardCompatibleTemplateNames: [] };
  value.PlaceableBlockObjectSpec = { ...value.PlaceableBlockObjectSpec, ToolGroupId: 'Water', ToolOrder: 61 };
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
buildingBlueprints.push(await authorFisherFlag());
buildingBlueprints.push(await makeReactor());
for (const entry of POWER_PLANTS) buildingBlueprints.push(await makePowerPlant(entry));
buildingBlueprints.push(await makeVault());
buildingBlueprints.push(await makeScrubber());
buildingBlueprints.push(await makeModularWarehouse());
buildingBlueprints.push(await makeWarehouseModule());
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
// Good names, [singular, plural], in the vanilla style: sentence case, with a
// plural for countable goods (vanilla "Metal block" / "Metal blocks"). The ids
// stay (HighGradeSteel is shown as Steel since the progression sets of
// 2026-10-31), so saves are unaffected. Recipes without an authored name show
// their product's plural.
const GOOD_DISPLAY_NAMES = {
  Coal: ['Coal', 'Coal'], Chemical: ['Chemical', 'Chemicals'],
  RecoveredArtifact: ['Recovered artifact', 'Recovered artifacts'], Fertilizer: ['Fertilizer', 'Fertilizer'],
  FreshFish: ['Fresh fish', 'Fresh fish'], JuvenileFish: ['Juvenile fish', 'Juvenile fish'], FishOil: ['Fish oil', 'Fish oil'],
  CannedFish: ['Canned fish', 'Canned fish'], Medicine: ['Medicine', 'Medicine'],
  SweetBerryCake: ['Sweet berry cake', 'Sweet berry cakes'], HighGradeSteel: ['Steel', 'Steel'], Alloy: ['Alloy', 'Alloy'],
  Polymer: ['Polymer', 'Polymer'], Lubricant: ['Lubricant', 'Lubricant'],
  MachineCore: ['Machine core', 'Machine cores'], PowerModule: ['Power module', 'Power modules'],
  FilterMedia: ['Filter media', 'Filter media'], ConcentratedWaste: ['Concentrated waste', 'Concentrated waste'],
  CrudeOil: ['Crude oil', 'Crude oil'], UraniumOre: ['Uranium ore', 'Uranium ore'], Yellowcake: ['Yellowcake', 'Yellowcake'],
  EnrichedFuel: ['Enriched fuel', 'Enriched fuel'], PureWater: ['Pure water', 'Pure water'],
  HydrogenGas: ['Hydrogen gas', 'Hydrogen gas'], OxygenGas: ['Oxygen gas', 'Oxygen gas'],
  LiquidHydrogen: ['Liquid hydrogen', 'Liquid hydrogen'], LiquidOxygen: ['Liquid oxygen', 'Liquid oxygen'],
  Cryocoolant: ['Cryocoolant', 'Cryocoolant'], RadioactiveWaste: ['Radioactive waste', 'Radioactive waste'],
  RocketAirframe: ['Rocket airframe', 'Rocket airframes'], PropulsionPackage: ['Propulsion package', 'Propulsion packages'],
  GuidanceComputer: ['Guidance computer', 'Guidance computers'], MissionPayload: ['Mission payload', 'Mission payloads'],
  RecoveredTelemetry: ['Recovered telemetry', 'Recovered telemetry'],
  IndustrialLicense: ['Industrial license', 'Industrial licenses'], SpecialistLicense: ['Specialist license', 'Specialist licenses'],
  FlightLicense: ['Flight license', 'Flight licenses'], Electronics: ['Electronics', 'Electronics'],
  ReactorCoolantWater: ['Reactor coolant water', 'Reactor coolant water'], RecoveredMinerals: ['Recovered minerals', 'Recovered minerals'],
};
for (const id of Object.keys(GOOD_DISPLAY_NAMES)) if (!goodDefinitions.some(([good]) => good === id)) throw new Error(`GOOD_DISPLAY_NAMES names undefined good ${id}`);
for (const [id] of goodDefinitions) {
  if (!Object.hasOwn(GOOD_DISPLAY_NAMES, id)) throw new Error(`No display name for good ${id} (GOOD_DISPLAY_NAMES)`);
  const [singular, plural] = GOOD_DISPLAY_NAMES[id];
  rows.push(csvRow(`Good.${id}.DisplayName`, singular));
  rows.push(csvRow(`Good.${id}.PluralDisplayName`, plural));
}
for (const definition of buildingDefinitions) {
  const id = definition[0];
  const display = definition[9];
  rows.push(csvRow(`Building.${id}.DisplayName`, display));
  if (!Object.hasOwn(BUILDING_TEXT, id)) throw new Error(`No authored description for ${id} (BUILDING_TEXT)`);
  rows.push(csvRow(`Building.${id}.Description`, id === 'Hospital' ? HOSPITAL_DESCRIPTION : BUILDING_TEXT[id][0]));
  rows.push(csvRow(`Building.${id}.FlavorDescription`, BUILDING_TEXT[id][1]));
}
for (const id of Object.keys(BUILDING_TEXT)) if (!buildingDefinitions.some(([building]) => building === id)) throw new Error(`BUILDING_TEXT names unknown building ${id}`);
{
  // Fisher Flag (fishery_building_content.mjs authorFisherFlag): the first step of the fish chain,
  // named and worded after the vanilla flags ("Employs a lumberjack that cuts trees.").
  rows.push(csvRow('Building.FisherFlag.DisplayName', 'Fisher Flag'));
  // The numbers are the fishing rule itself (tools/aquaculture.json fisherFlag.spec).
  const fishing = JSON.parse(await readFile(resolve(root, 'tools', 'aquaculture.json'), 'utf8')).fisherFlag.spec;
  rows.push(csvRow('Building.FisherFlag.Description',
    `Employs a fisher who catches fresh fish from the shore, where clean water at least ${fishing.MinimumDepth} m deep lies no more than ${fishing.MaximumReachDown} m below the bank.`));
  rows.push(csvRow('Building.FisherFlag.FlavorDescription', 'A quiet bank, a long wait and a longer story about the one that got away.'));
}
{
  // Modular Warehouse and Warehouse Module, and the two lines their panel and status show.
  const {core, module} = MODULAR;
  rows.push(csvRow(`Building.${core.id}.DisplayName`, core.name));
  rows.push(csvRow(`Building.${core.id}.Description`,
    `Stores up to ${core.maxSlots} goods, each in its own slot with its own warehouse settings. Each attached ${module.name} adds a slot and storage.`));
  rows.push(csvRow(`Building.${core.id}.FlavorDescription`, 'One door, one ledger and a beaver who knows where everything is.'));
  rows.push(csvRow(`Building.${module.id}.DisplayName`, module.name));
  rows.push(csvRow(`Building.${module.id}.Description`,
    `Adds storage and a slot to a ${core.name} when built beside it, on top of it, or on another attached module.`));
  rows.push(csvRow(`Building.${module.id}.FlavorDescription`, 'Another floor of crates, and the ledger grows a page.'));
  rows.push(csvRow('DeepFrontier.ModularWarehouse.Network', 'Modules: {0}. Capacity: {1}'));
  rows.push(csvRow('DeepFrontier.ModularWarehouse.ModuleUnattached', `Not attached to a ${core.name}`));
  rows.push(csvRow('Building.SmogScrubber.DisplayName', 'Smog Scrubber'));
  // Its share and range are in the tooltip's smog section (DeepFrontier.Smog.Scrubber.Planned).
  rows.push(csvRow('Building.SmogScrubber.Description', 'Cleans smog out of the air around it while powered. No workers.'));
  rows.push(csvRow('Building.SmogScrubber.FlavorDescription', 'What goes up the smokestack comes down in the scrubber.'));
}
// Wellbeing attractions: names and needs from frontier_progression.json.
const WELLBEING_TEXT = {
  Bathhouse: [() => 'Steam baths that count as a Mud Bath and a Massager and give Wet fur, all in one visit. Uses water.',
    'The boilers run hot so the colony can run warm.'],
  TownPlaza: [() => 'A square where beavers dance and gather: it counts as a Dance Pit and a Campfire. Needs no power or supplies.',
    'Every frontier town needs one place where nothing is being built.'],
  ObservationDeck: [() => 'A viewing tower: the climb counts as an Exercise Plaza and the deck as a Rooftop Terrace.',
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
    ? 'Huge power from enriched fuel, run by trained reactor operators.'
    : 'Stores radioactive waste.'));
  rows.push(csvRow(`Building.${id}.FlavorDescription`, id === 'NuclearReactor'
    ? 'The frontier makes power and consequences at the same scale.'
    : 'Labeled, logged and never, ever full.'));
}
// Power plants: output, fuel and water rates from frontier_progression.json.
const POWER_PLANT_TEXT = {
  CoalPowerPlant: [() => 'Burns coal and water for power day and night. No workers.',
    'Black smoke, white steam and the hum of every machine in the district.'],
  OilPowerPlant: [() => 'Burns crude oil and water for power day and night, with less smog than coal. No workers.',
    'The deep ore gives up its oil, and the oil gives up its fire.'],
};
for (const entry of POWER_PLANTS) {
  if (!Object.hasOwn(POWER_PLANT_TEXT, entry.id)) throw new Error(`No authored text for ${entry.id}`);
  rows.push(csvRow(`Building.${entry.id}.DisplayName`, entry.name));
  rows.push(csvRow(`Building.${entry.id}.Description`, POWER_PLANT_TEXT[entry.id][0](entry)));
  rows.push(csvRow(`Building.${entry.id}.FlavorDescription`, POWER_PLANT_TEXT[entry.id][1]));
}
// Only recipes with an authored name read a Recipe.<id>.DisplayName row (makeRecipe).
for (const [id, name] of Object.entries(RECIPE_NAMES)) rows.push(csvRow(`Recipe.${id}.DisplayName`, name));
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
