const fs = require('fs');
const path = require('path');

const workshopRoot = 'C:/Program Files (x86)/Steam/steamapps/workshop/content/1062090';
const outputPath = 'C:/Users/Jordan/Documents/TimberbornModding/tools/target_mod_packages_1_1.json';

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}

function buildingRow({ packageId, packageName, manifest, source, blueprintPath, role, placement, stackingRule }) {
  const absolute = path.join(workshopRoot, packageId, blueprintPath);
  const blueprint = readJson(absolute);
  const building = blueprint.BuildingSpec ?? {};
  const block = blueprint.BlockObjectSpec ?? {};
  const blocks = block.Blocks ?? [];
  const costs = Object.fromEntries((building.BuildingCost ?? []).map((entry) => [entry.Id, entry.Amount]));
  const stackable = [...new Set(blocks.map((entry) => entry.Stackable).filter(Boolean))];
  const occupations = [...new Set(blocks.map((entry) => entry.Occupations).filter(Boolean))];
  const stockpile = blueprint.StockpileSpec ?? {};
  const mechanical = blueprint.MechanicalNodeSpec ?? {};
  const size = block.Size ?? {};
  return {
    packageId,
    packageName,
    packageVersion: manifest.Version,
    manifestId: manifest.Id,
    minimumGameVersion: manifest.MinimumGameVersion,
    requiredMods: manifest.RequiredMods ?? [],
    optionalMods: manifest.OptionalMods ?? [],
    source,
    blueprintPath,
    template: blueprint.TemplateSpec?.TemplateName ?? '',
    building: blueprint.TemplateSpec?.TemplateName?.replace(/\.(IronTeeth|Folktails)$/, '') ?? path.basename(blueprintPath, '.blueprint.json'),
    faction: 'Iron Teeth',
    infobox: role === 'power' ? 'Structure' : 'Storage',
    categories: role === 'power' ? 'Power; Mod dependency' : `Storage; ${stockpile.WhitelistedGoodType ?? 'Storage'}; Mod dependency`,
    buildable: 'Yes',
    availability: 'Build menu',
    width: size.X ?? '',
    length: size.Y ?? '',
    height: size.Z ?? '',
    footprint: size.X !== undefined && size.Y !== undefined ? `${size.X}x${size.Y}` : '',
    footprintTiles: size.X !== undefined && size.Y !== undefined ? size.X * size.Y : '',
    workers: 0,
    powerDemandHp: Number(mechanical.PowerInput ?? 0),
    powerOutputHp: Number(mechanical.PowerOutput ?? 0),
    scienceUnlock: building.ScienceCost ?? '',
    botUnlock: '',
    materials: costs,
    flags: {
      stackableValues: stackable,
      occupations,
      hasEntrance: Boolean(block.Entrance?.HasEntrance),
      flippable: Boolean(block.Flippable),
      toolGroup: blueprint.PlaceableBlockObjectSpec?.ToolGroupId ?? '',
      toolOrder: blueprint.PlaceableBlockObjectSpec?.ToolOrder ?? '',
      whitelistedGoodType: stockpile.WhitelistedGoodType ?? '',
      maxCapacity: stockpile.MaxCapacity ?? '',
      placement,
      stackingRule,
    },
    recipeNames: [],
    inputs: '',
    outputs: role === 'power' ? `Power (up to ${mechanical.PowerOutput ?? 0} hp)` : `${stockpile.MaxCapacity ?? ''} ${stockpile.WhitelistedGoodType ?? 'storage capacity'}`.trim(),
    sourceUrl: source,
    dataStatus: 'Exact installed 1.1 blueprint; Iron Teeth variant',
  };
}

const packages = [
  {
    packageId: '3801036916',
    packageName: 'Northforge - Solar Panel',
    root: 'version-1.0',
    source: 'https://steamcommunity.com/sharedfiles/filedetails/?id=3801036916',
    role: 'power',
    manifest: readJson(path.join(workshopRoot, '3801036916/version-1.0/manifest.json')),
    blueprints: [
      ['Buildings/Power/SolarPanel/SolarPanel.IronTeeth.blueprint.json', 'Surface 1x1; side and rear gear connections only', 'No artificial layer cap; blueprint Stackable=None'],
    ],
  },
  {
    packageId: '3795292508',
    packageName: 'Expanded Storage',
    root: '',
    source: 'https://steamcommunity.com/sharedfiles/filedetails/?id=3795292508',
    role: 'storage',
    manifest: readJson(path.join(workshopRoot, '3795292508/manifest.json')),
    blueprints: [
      ['Buildings/Storage/GrandWarehouse/GrandWarehouse.IronTeeth.blueprint.json', 'Surface storage with entrance', 'No artificial layer cap; blueprint Stackable=None'],
      ['Buildings/Storage/GrandTank/GrandTank.IronTeeth.blueprint.json', 'Surface liquid storage with entrance', 'No artificial layer cap; blueprint Stackable=None'],
      ['Buildings/Storage/GrandUndergroundPile/GrandUndergroundPile.IronTeeth.blueprint.json', 'Underground pile storage with entrance', 'No artificial layer cap; blueprint Stackable=None'],
      ['Buildings/Storage/StorageModule/StorageModule.IronTeeth.blueprint.json', 'Stackable storage module', 'Unlimited compatible BlockObject stacking; no numeric layer cap in blueprint'],
      ['Buildings/Storage/TankModule/TankModule.IronTeeth.blueprint.json', 'Stackable liquid module', 'Unlimited compatible BlockObject stacking; no numeric layer cap in blueprint'],
      ['Buildings/Storage/PileModule/PileModule.IronTeeth.blueprint.json', 'Stackable pile module', 'Unlimited compatible BlockObject stacking; no numeric layer cap in blueprint'],
    ],
  },
];

const buildings = [];
for (const pkg of packages) {
  for (const [blueprintPath, placement, stackingRule] of pkg.blueprints) {
    buildings.push(buildingRow({ ...pkg, blueprintPath: pkg.root ? `${pkg.root}/${blueprintPath}` : blueprintPath, placement, stackingRule }));
  }
}

const payload = {
  schemaVersion: 1,
  gameVersion: 'Timberborn 1.1.2.8',
  checkedDate: '2026-10-17',
  source: 'Installed Steam Workshop package blueprints and manifests',
  packages: packages.map((pkg) => ({
    packageId: pkg.packageId,
    name: pkg.packageName,
    version: pkg.manifest.Version,
    id: pkg.manifest.Id,
    minimumGameVersion: pkg.manifest.MinimumGameVersion,
    requiredMods: pkg.manifest.RequiredMods ?? [],
    optionalMods: pkg.manifest.OptionalMods ?? [],
    source: pkg.source,
  })),
  buildings,
  notes: [
    'Only Iron Teeth blueprint variants are included because Deep Frontier is an Iron Teeth project.',
    'Stacking is captured from BlockObjectSpec.Stackable. No numeric maximum layer count is imposed by these package blueprints.',
    'Solar Panel has no production recipe; its output is a mechanical power node up to 100 hp.',
    'Expanded Storage buildings have no production recipes; their relevant output is storage capacity and good-type filtering.',
  ],
};

fs.writeFileSync(outputPath, JSON.stringify(payload, null, 2));
console.log(JSON.stringify({ outputPath, packages: payload.packages.length, buildings: payload.buildings.length }, null, 2));
