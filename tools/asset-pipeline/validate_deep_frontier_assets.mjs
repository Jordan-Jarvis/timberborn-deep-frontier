import { access, readFile, stat } from 'node:fs/promises';
import { resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(fileURLToPath(new URL('../..', import.meta.url)));
const sourceRoot = resolve(root, 'src', 'DeepFrontier');

const expected = [
  'Art/Source/DeepFrontierModels.blend',
  'Art/Textures/DeepFrontierMetal.png',
  'Art/Textures/DeepFrontierOre.png',
  'Art/Textures/DeepFrontierHazard.png',
  'Data/Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.Model.timbermesh',
  'Data/Buildings/Metal/DeepDrill/DeepDrill.IronTeeth.ConstructionStage0.Model.timbermesh',
  'Data/Buildings/Metal/DeepMine/DeepMine.IronTeeth.Model.timbermesh',
  'Data/Buildings/Metal/DeepMine/DeepMine.IronTeeth.ConstructionStage0.Model.timbermesh',
  'Data/Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.Model.timbermesh',
  'Data/Buildings/Metal/DeepProcessor/DeepProcessor.IronTeeth.ConstructionStage0.Model.timbermesh',
  'Data/MapEditor/Objects/DeepOreVein/DeepOreVein.Model.timbermesh',
  'Data/Buildings/Metal/DeepDrill/DeepDrillIcon.png',
  'Data/Buildings/Metal/DeepMine/DeepMineIcon.png',
  'Data/Buildings/Metal/DeepProcessor/DeepProcessorIcon.png',
  'Data/MapEditor/Objects/DeepOreSource/DeepOreSourceIcon.png',
  'Data/MapEditor/Objects/DeepOreVein/DeepOreVeinIcon.png',
  'Data/Sprites/Goods/DeepOreIcon.png',
  'Data/Sprites/Goods/DeepAlloyIcon.png',
];

const expansionGoodIds = [
  'Coal', 'Chemical', 'RecoveredArtifact', 'Fertilizer', 'FreshFish', 'JuvenileFish',
  'FishOil', 'CannedFish', 'Medicine', 
  'HighGradeSteel', 'Alloy', 'Polymer', 'Lubricant', 'MachineCore',
  'PowerModule', 'FilterMedia', 'ConcentratedWaste', 'CrudeOil',
  'UraniumOre', 'Yellowcake', 'EnrichedFuel', 'PureWater', 'HydrogenGas',
  'OxygenGas', 'LiquidHydrogen', 'LiquidOxygen', 'Cryocoolant', 'RadioactiveWaste', 'RocketAirframe',
  'PropulsionPackage', 'GuidanceComputer', 'MissionPayload', 'RecoveredTelemetry', 'IndustrialLicense',
  'SpecialistLicense', 'FlightLicense', 'Electronics', 'ReactorCoolantWater', 'RecoveredMinerals', 
];
const expansionBuildings = [
  ['Food', 'FertilizerWorks'], ['Food', 'FishHatchery'], ['Food', 'FisheryWorks'], ['Food', 'FoodPackagingWorks'],
  ['Wellbeing', 'PublicHealthLab'], ['Food', 'GroceryStore'], ['Food', 'Restaurant'], ['Wellbeing', 'Hospital'],
  ['Food', 'Greenhouse'], ['Metal', 'ChemicalWorks'], ['Metal', 'PrecisionMachineWorks'], ['Water', 'WaterTreatmentPlant'],
  ['Science', 'TechnicalSchool'], ['Metal', 'UraniumProcessingPlant'], ['Metal', 'RadioactiveWasteRefinery'],
  ['Metal', 'ElectrolysisPlant'], ['Metal', 'CryogenicLiquefactionPlant'], ['Metal', 'RocketAssemblyHangar'],
  ['Science', 'MissionControl'], ['Metal', 'LaunchPad'], ['Power', 'NuclearReactor'], ['Storage', 'RadioactiveWasteVault'],
];
for (const id of expansionGoodIds) expected.push(`Data/Sprites/Goods/${id}Icon.png`);
for (const [group, id] of expansionBuildings) {
  expected.push(`Data/Buildings/${group}/${id}/${id}.IronTeeth.Model.timbermesh`);
  expected.push(`Data/Buildings/${group}/${id}/${id}.IronTeeth.ConstructionStage0.Model.timbermesh`);
  expected.push(`Data/Buildings/${group}/${id}/Icon.png`);
}

const missing = [];
const zeroLength = [];
for (const relative of expected) {
  const path = resolve(sourceRoot, relative);
  try {
    const info = await stat(path);
    if (info.size === 0) zeroLength.push(relative);
  } catch {
    missing.push(relative);
  }
}

for (const relative of expected.filter((p) => p.endsWith('.png') && (p.includes('DeepDrillIcon') || p.includes('DeepMineIcon') || p.includes('DeepProcessorIcon') || p.includes('DeepOreSourceIcon') || p.includes('DeepOreVeinIcon') || p.includes('DeepOreIcon') || p.includes('DeepAlloyIcon')))) {
  const meta = resolve(sourceRoot, `${relative}.meta.json`);
  try {
    await access(meta);
  } catch {
    missing.push(`${relative}.meta.json`);
  }
}

if (missing.length || zeroLength.length) {
  console.error(JSON.stringify({ status: 'error', missing, zeroLength }, null, 2));
  process.exit(1);
}

console.log(JSON.stringify({ status: 'ok', files: expected.length, sourceRoot }, null, 2));
