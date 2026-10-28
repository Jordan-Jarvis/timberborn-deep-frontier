// Native-style UI icons for the frontier expansion goods/buildings and the deep-ore
// vertical slice. Each icon is an authored single-ink SVG in
// src/DeepFrontier/Art/Icons/<Id>.svg, rendered by tools/native_icon_style.mjs
// (vanilla 80px goods / 112px tool icons, vanilla ink and shadow). Building icons
// trace the approved study silhouettes in outputs/lategame-studies/<Id>-front.png.
// This replaces the coloured placeholder squares of generate_frontier_expansion_icons.py
// and the Blender make_icon() swatches of generate_deep_frontier_assets.py.
import {readFile, mkdir} from 'node:fs/promises';
import {fileURLToPath} from 'node:url';
import {writeNativeIcon, writeReviewSheet} from './native_icon_style.mjs';

const root = new URL('../', import.meta.url);

const goods = [
  'Compost', 'Coal', 'Chemical', 'RecoveredArtifact', 'Fertilizer', 'EmergencyRation',
  'Flux', 'HighGradeSteel', 'Alloy', 'Polymer', 'Lubricant',
  'MachineCore', 'PowerModule', 'FilterMedia', 'ConcentratedWaste', 'CrudeOil',
  'UraniumOre', 'Yellowcake', 'EnrichedFuel', 'PureWater', 'HydrogenGas', 'OxygenGas',
  'LiquidHydrogen', 'LiquidOxygen', 'Cryocoolant', 'RadioactiveWaste', 'RocketAirframe', 'PropulsionPackage',
  'GuidanceComputer', 'MissionPayload', 'RecoveredTelemetry', 'IndustrialLicense', 'SpecialistLicense', 'FlightLicense',
  'Electronics', 'ReactorCoolantWater', 'RecoveredMinerals', 'ArchiveData',
  'DeepOre', 'DeepAlloy',
];
const buildings = {
  FertilizerWorks: 'Buildings/Food/FertilizerWorks/Icon.png',
  FoodPackagingWorks: 'Buildings/Food/FoodPackagingWorks/Icon.png',
  PublicHealthLab: 'Buildings/Wellbeing/PublicHealthLab/Icon.png',
  Greenhouse: 'Buildings/Food/Greenhouse/Icon.png',
  ChemicalWorks: 'Buildings/Metal/ChemicalWorks/Icon.png',
  PrecisionMachineWorks: 'Buildings/Metal/PrecisionMachineWorks/Icon.png',
  WaterTreatmentPlant: 'Buildings/Water/WaterTreatmentPlant/Icon.png',
  TechnicalSchool: 'Buildings/Science/TechnicalSchool/Icon.png',
  UraniumProcessingPlant: 'Buildings/Metal/UraniumProcessingPlant/Icon.png',
  RadioactiveWasteRefinery: 'Buildings/Metal/RadioactiveWasteRefinery/Icon.png',
  ElectrolysisPlant: 'Buildings/Metal/ElectrolysisPlant/Icon.png',
  CryogenicLiquefactionPlant: 'Buildings/Metal/CryogenicLiquefactionPlant/Icon.png',
  RocketAssemblyHangar: 'Buildings/Metal/RocketAssemblyHangar/Icon.png',
  MissionControl: 'Buildings/Science/MissionControl/Icon.png',
  LaunchPad: 'Buildings/Metal/LaunchPad/Icon.png',
  NuclearReactor: 'Buildings/Power/NuclearReactor/Icon.png',
  RadioactiveWasteVault: 'Buildings/Storage/RadioactiveWasteVault/Icon.png',
  DeepDrill: 'Buildings/Metal/DeepDrill/DeepDrillIcon.png',
  DeepMine: 'Buildings/Metal/DeepMine/DeepMineIcon.png',
  DeepProcessor: 'Buildings/Metal/DeepProcessor/DeepProcessorIcon.png',
  SteelMill: 'Buildings/Metal/SteelMill/Icon.png',
  ArchiveExcavation: 'Buildings/Science/ArchiveExcavation/Icon.png',
  CryogenicTankFarm: 'Buildings/Storage/CryogenicTankFarm/Icon.png',
  SmogScrubber: 'Buildings/Wellbeing/SmogScrubber/Icon.png',
  Bathhouse: 'Buildings/Wellbeing/Bathhouse/Icon.png',
  TownPlaza: 'Buildings/Wellbeing/TownPlaza/Icon.png',
  ObservationDeck: 'Buildings/Wellbeing/ObservationDeck/Icon.png',
  CoalPowerPlant: 'Buildings/Power/CoalPowerPlant/Icon.png',
  OilPowerPlant: 'Buildings/Power/OilPowerPlant/Icon.png',
};
const mapObjects = {
  DeepOreSource: 'MapEditor/Objects/DeepOreSource/DeepOreSourceIcon.png',
  DeepOreVein: 'MapEditor/Objects/DeepOreVein/DeepOreVeinIcon.png',
  // The old-world records vault (narrative_content.mjs CACHE.icon), not the vanilla relic icon.
  HumanRecordCache: 'MapEditor/Objects/HumanRecordCache/HumanRecordCacheIcon.png',
};

const entries = [
  ...goods.map(id => [id, 'good', `Sprites/Goods/${id}Icon.png`]),
  ...Object.entries(buildings).map(([id, path]) => [id, 'building', path]),
  ...Object.entries(mapObjects).map(([id, path]) => [id, 'mapObject', path]),
];
const review = [];
for (const [id, kind, path] of entries) {
  const svg = await readFile(new URL(`src/DeepFrontier/Art/Icons/${id}.svg`, root));
  const result = await writeNativeIcon(svg, kind, new URL(`src/DeepFrontier/Data/${path}`, root), id);
  review.push({label: `${id} ${result.stroke.toFixed(1)}px`, png: result.png, kind});
}

const reviews = new URL('docs/art/reviews/2026-10-21-icons/', root);
await mkdir(reviews, {recursive: true});
const vanilla = names => names.map(n => ({label: n, path: fileURLToPath(new URL(`outputs/vanilla-icons/${n}Icon.png`, root))}));
await writeReviewSheet(review.filter(e => e.kind === 'good'), vanilla(['Gear', 'Biofuel', 'Extract', 'Grease', 'Catalyst', 'Paper', 'Badwater', 'MetalBlock']),
  new URL('expansion-goods.png', reviews), 8);
await writeReviewSheet(review.filter(e => e.kind !== 'good'), vanilla(['Smelter', 'Refinery', 'Centrifuge', 'FoodFactory', 'EfficientMine', 'GreaseFactory', 'Observatory', 'GeothermalField']),
  new URL('expansion-buildings.png', reviews), 8);
console.log(`Rendered ${entries.length} native-style expansion icons (${goods.length} goods, ${Object.keys(buildings).length} buildings, ${Object.keys(mapObjects).length} map objects).`);
