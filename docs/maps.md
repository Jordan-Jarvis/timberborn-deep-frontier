# Deep Frontier map variants

Status 2026-10-30: the four map files were rebuilt with `build` for 0.6.0.0: the description names 0.6.0.0, and the Deep Ore Sources hold 18,000 (Plains, Plains Hard) or 17,000 (Lakes, Terraces), enough for one of each building (see "Full game loop"). Every built-in map also gets its Deep Frontier objects at new-game time (see "Built-in maps: new-game setup"). None of the rebuilt files has been loaded in the game.

Status 2026-10-24: the three vanilla-based maps and the hard variant are written to `C:\Users\Jordan\Documents\Timberborn\Maps\`. Each passes the static validation and the full-loop coverage check below with 0 errors. None has been loaded in the game since this pass. The in-game proof (`tools/start_map_loop_test.ps1`) is written and compiles, but has not been run. `tools/STATUS.md` records runtime verification.

| Map file (new-game list name) | Source | Character | Height | Output SHA-256 (prefix) |
|---|---|---|---|---|
| `Deep Frontier - Plains.timber` | built-in Plains, 256×256 | River plains around a central lake | 46 / 66 | `ad0c76ce7754ebaa` |
| `Deep Frontier - Plains (Hard, Radioactive Spring).timber` | built-in Plains | Same, plus a weak Radioactive Spring at a river head | 46 / 66 | `10085dcc11ad4bb1` |
| `Deep Frontier - Lakes.timber` | built-in Lakes, 256×256 | Lake district; island reactor | 46 / 66 | `7ecedc1c52341d5b` |
| `Deep Frontier - Terraces.timber` | built-in Terraces, 256×256 | Terraced highlands, start at level 15, deep valley and basin | 46 / 66 | `11d66e29a0e32205` |

The archive is rewritten on every build, so its SHA-256 changes on each build (zip entry times) even when the content is the same. The evidence file records the hash of the file it validated.

The variants are regenerated from `tools/map_variants/<id>.json` by `tools/prepare_deep_frontier_map.py`. Edit the JSON, never the `.timber`. The other files:

- `outputs/maps/<id>-validation.json`: validation evidence, including the full-loop report under `loopCoverage`.
- `outputs/maps/<id>-preview.png`: overview render, north up. Every placement (P1…) and site (S1…) is marked and listed in the legend; sites are coloured by loop stage, and any site with a problem is red.
- `tools/map_loop_requirements.json`: the authored policy minimums. Everything else is read from the generated data.

```
python tools/prepare_deep_frontier_map.py build tools/map_variants/plains.json tools/map_variants/plains-hard.json tools/map_variants/lakes.json tools/map_variants/terraces.json
python tools/prepare_deep_frontier_map.py validate tools/map_variants/plains.json tools/map_variants/plains-hard.json tools/map_variants/lakes.json tools/map_variants/terraces.json   # re-read the written files only
python tools/prepare_deep_frontier_map.py plan tools/map_variants/lakes.json --out lakes-plan.json   # propose what a variant still lacks
python tools/prepare_deep_frontier_map.py suggest builtin:Waterfalls --png out.png # candidate sites for a new map
python tools/test_prepare_deep_frontier_map.py                                    # 17 injected faults must each fail
pwsh tools/start_map_loop_test.ps1 -Label <label>                                 # in-game proof, game closed, user present
```

Use the codex runtime Python (`numpy` and `Pillow` are needed). `--out-dir DIR` writes the maps elsewhere for a dry run. `plan` writes a complete variant JSON for review. Its output is ordinary variant data, which `build` validates like any hand-written entry. This pass authored the new placements and sites with `plan` and reviewed them before adopting them.

## Built-in maps: new-game setup

Status 2026-10-29: implemented, compiled and statically validated; not built into the mod and not run in game. A new game on any built-in map now gets that map's Deep Frontier objects and a total build height of 66, so players can use the official maps. The four `Deep Frontier - *.timber` files above still work as before (they are user maps; the setup leaves them alone).

### What happens at a new game

Evidence: Timberborn 1.1.2.8 and Map Transformer 11.0.0, decompiled with `tools/dotnet/ilspycmd.exe`.

1. **New game and map.** `GameSceneLoader.StartNewGame` loads the game scene with `GameSceneParameters.CreateNewGameParameters(NewGameConfiguration)`. `GameSceneParameters.NewGame` is true only then, and `NewGameConfiguration.MapFileReference` names the map (`Resource` true for a built-in map, `Name` its asset name). This is the same test native `MapNameService.Load` and `GameLoader.LoadNew` use. A loaded save has `NewGame` false.
2. **Height, before the map loads** (`src/DeepFrontier/Scripts/MapSetup/BuiltinMapHeight.cs`, two Harmony patches applied by `DeepFrontierModStarter`):
   - a postfix on `GameSceneSerializedWorldSupplier.Load` keeps the deserialized map world and the map name, only for a new game on a built-in map;
   - a prefix on `MapSize.Load` writes `MapHeight {X: 23, Y: TotalHeight}` into that world's `MapSize` singleton with the native `ObjectSaver`. `MapSize` loads after the supplier because it depends on it (`ISingletonLoader` → `WorldSingletonLoader` → `ISerializedWorldSupplier`), and `ISpecService` is already loaded because `MapSize` itself depends on it.
   - Map Transformer's own `MapSize.Load` postfix then applies the key (`MaxHeightAboveTerrain = Y − X`, terrain height unchanged), and its `MapSize.Save` postfix writes it into every save, so reloads keep 66 without Deep Frontier doing anything.
3. **Objects, on the first frame** (`BuiltinMapSetup.cs`, a game singleton). For each placement of the map's entry, in order, it takes the map editor's own path:
   - a native preview (`PreviewFactory.Create`, `BlockObject.Reposition`) must pass `BlockObject.IsValid()`, which is `BlockValidator.BlocksValid` plus every `IBlockObjectValidator` (matter below, `ContinuousTerrainConstraint`, …), as the `BlockObjectTool`'s `PreviewPlacer` requires;
   - then `BlockObjectPlacerService.GetMatchingPlacer(spec).Place(new EntitySetup.Builder(blueprint), placement)`, exactly as `BlockObjectTool.Place`. The Deep Ore Source goes through `BuildingPlacer` (`BuildingSpec.PlaceFinished`, so it is finished); the other objects through `DefaultBlockObjectPlacer`;
   - a stockpile then gets its good and amount as the map editor's `FixedStockpileInventorySetter` does (`SingleGoodAllower.Allow`, `FixedStockpile.SetFixedGood`, `Inventory.GiveExisting`), and the stock is read back.
   - `GameStarter` spawns the starting building on its own first frame; the StartingLocation entity has the District Center's 3×3×5 footprint, and the static validation checks that no placement overlaps it or any other object.
4. **Exactly once.** The outcome is saved in a `DeepFrontierMapSetup` singleton (`Map`, `Outcome`, `Placed`, `Failed`). A world that has it is never set up again. A save from before this system loads with outcome `SavedBeforeSetup` and is never touched. A new game on a map file (including the four shipped variants) is `UserMap`.
5. **Failures are reported, never hidden.** A placement the native preview rejects is not moved or skipped: it is logged as an error (`[DeepFrontier MapSetup] FAILED …`, with the validator message) and listed in a dialog when the game UI appears. The setup also checks the resulting `MapSize` (terrain 23, total = the entry's height) and reports a mismatch, for example when Map Transformer is disabled. A built-in map with no entry is an error dialog and log line; the validation below makes that impossible for every shipped built-in map. The three developer test maps (dev mode only) get a dialog saying they have no setup.

### Height decision

- **What Deep Frontier needs is total height, not terrain layers.** Its tall late-game buildings need `top occupied layer < total height` (`BlockValidator.FitsInMap`). No Deep Frontier building or script raises terrain or reads `MaxGameTerrainHeight`; only vanilla terrain-raising would use the 46 terrain layers of the shipped variants.
- **A new game on a built-in map gets 23 terrain / 66 total.** The stored 23 terrain layers stay, so `TerrainMap.Load` → `MapIndexService.Unpack3D` reads the map's data unchanged (the out-of-range problem of `docs/map-height.md` does not arise). Map Transformer's own Resize Map Height dialog accepts the same independent terrain and total values.
- **Systems that read the height** treat terrain and total separately: `LevelVisibilityService.MaxVisibleLevel = MaxGameTerrainHeight + MaxHeightAboveTerrain` = 65 (slicing reaches the top layer); water (`WaterSimulator`, `FlowLimiterService`, `WaterOverflowCalculator`), `TerrainPhysicsPostLoader` and navigation size their arrays by `TotalSize`; the stored water columns keep their slots (ceilings are recomputed from terrain); `BlockValidator` accepts blocks up to z = 65. The camera target clamps to `TerrainSize.z + MapMargin` = 23 + 50 = 73, above 66.
- **The global `MapSizeSpec` is not changed.** Saves, map files and the map editor keep their own height.
- **Placement validity does not depend on the height.** The Plains, Lakes and Terraces placements and all their sites pass on the unmodified built-in terrain at 66 and also at the vanilla 33 (checked with `builtin` on copies set to 33). The height is for building upward, as the art direction wants, not for the placements.

### Plains Hard

The built-in Plains game gets `plains.json`. `plains-hard.json` is not applied to built-in games: it stays the separate map file `Deep Frontier - Plains (Hard, Radioactive Spring)`. The game's difficulty presets (`GameModeSpec`) set beavers, food, droughts and badtides; tying the radioactive spring to the Hard preset would give no way to play Hard without the spring or the spring on Normal. The file keeps it an explicit choice. Only default (`hardVariant: false`) variants of built-in maps are applied, and `builtin` fails if a map has two.

### Data and validation

One JSON per map stays the only source: `tools/map_variants/<id>.json`. The default variant whose `source` is `builtin:<Name>` is the setup of that built-in map.

- **Runtime-only variants** (`"output": null`) are never written as `.timber`. Their `height` has only `totalHeight`; `mapSize` records the map size.
- **`unmet`**: `[{"item", "reason"}]` lists loop-coverage items the map physically cannot provide. `builtin` fails unless the failing items equal the declared ones exactly; placement and site problems can never be declared. The reason (with numbers) stays in the JSON, the evidence and this document; the in-game line comes from `tools/map_setup.json` `unmetText`.
- **Accepted gaps** (`tools/map_loop_requirements.json` `acceptedGaps`): coverage items accepted on every map until a design decision, printed on every run. None since 2026-10-30. The last one, *finite deep ore covers one of each building*, is now a requirement: the drillable sources must hold the DeepOre of one of each building plus `finiteDeepOreMargin` (5%), and a map that cannot must declare it `unmet` (only Beaverome).
- **Generated data**: `tools/map_setup_content.mjs` (the last step of canonical generation, `create_vertical_slice_content.mjs`) writes `Configurations/DeepFrontierMapSetup.blueprint.json` (`BuiltinMapSetupSpec`: per map the name, size, total height, the two warning flags `SmallArea` and `NoDeepMineSite`, unmet text keys and placements) and the `DeepFrontier.MapSetup.*` rows of `enUS.csv`, from the variants and `tools/map_setup.json` (dev maps, small-map rule, dialog text).
- **Checks**:
  - `python tools/prepare_deep_frontier_map.py builtin` (validate_all `map-setup-terrain`) validates every default variant against its unmodified built-in map, at the stored terrain layers and the variant's total height: exactly the state the runtime produces. It uses the same placement, site and full-loop code as `validate`. It also checks that every non-dev built-in map has exactly one variant, that the dev-map list matches the game, that the small-map threshold matches its derivation, and that `smallMap.deepMineSite` is the only building over a Deep Ore Vein. Evidence: `outputs/maps/<id>-builtin-validation.json`, `<id>-builtin-preview.png`, `builtin-coverage.json`.
  - `node tools/validate_map_setup.mjs` (validate_all `map_setup`) checks that the generated blueprint and rows equal what the generator derives from the sources, and that the C# records and loc keys match.
- **Built-in map names.** The new-game list names a built-in map by its asset name (`OfficialMapItemFactory`: `MapFileReference.FromResource(name)`). In 1.1.2.8 every named built-in map's asset (GameObject) name equals the `<Name>` of its `MapMetadata.<Name>.Name` key (checked against the GameObject names in `resources.assets`, and against `MapNameService` in saves of new games on Plains, Lakes and Meander). The dev maps are `_Mini`, `_TerrainTest` and `_WaterPerformanceTest`.

```
python tools/prepare_deep_frontier_map.py builtin                                   # every variant + coverage (game files needed)
python tools/prepare_deep_frontier_map.py builtin tools/map_variants/diorama.json   # one map
python tools/prepare_deep_frontier_map.py suggest builtin:Diorama --total-height 66  # survey as the setup loads it
python tools/prepare_deep_frontier_map.py plan tools/map_variants/diorama.json --out p.json [--cache-spacing 15]
node tools/map_setup_content.mjs <dataRoot>     # only on a Data tree without the rows (canonical generation runs it)
node tools/validate_map_setup.mjs
```

`build` and `validate` refuse runtime-only variants; list the four written variants explicitly.

### Small maps and maps without a Deep Mine

A built-in map gets the **EXTREMELY difficult** warning (`BuiltinMapSpec.Small`) when either holds (`tools/map_setup.json` `smallMap`):

- **Small area** (`SmallArea`): its area is below `smallMap.maxArea` = **11,176** cells. The number is derived and checked: the largest area the full-loop sites claim on a reference map (primary footprints plus their listed open margins: Plains 5,588, Terraces 5,476, Lakes 5,134) divided by the land share 1/2. Below it the late-game sites alone would cover more than half the map, before terrain, water, farms, forest and homes. The built-in sizes fall into clear groups (2,500; 5,000; 16,384; 36,864–38,400; 65,536), so the rule picks out exactly **Diorama** (50×50) and **Cliffside** (100×50); the 128×128 maps are three times larger.
- **No Deep Mine site** (`NoDeepMineSite`): the variant lists no primary site of `smallMap.deepMineSite` (`DeepMine.IronTeeth`, which `builtin` checks is the only building over a Deep Ore Vein). The Deep Mine is the only permanent deep ore, and the finite sources are sized for one of each building, not for the launch program. This picks out **Beaverome** (no deep ore at all) and **Diorama** (finite sources only).

So three maps get the warning: Beaverome, Cliffside and Diorama. The dialog appears once when the game UI appears (`DialogBoxShower`), built from the generated text and the map's own data. The small-area lines appear only on a small map, the Deep Mine line only without a Deep Mine site:

Diorama:

```
Deep Frontier is EXTREMELY difficult on Diorama
- Small map: Diorama has 50 x 50 = 2500 tiles, and the Deep Frontier late game is built for maps of at least 11176 tiles.
- Little room: the full set of large Deep Frontier sites (the 20 x 15 Nuclear Reactor, the Launch Pad, Deep Mines and Drills, processing plants) covers about 5588 tiles with their margins on a large map.
- Build upward: Deep Frontier raises this map's build height to 66 layers (vanilla 33); on a small map most of the colony has to stack on platforms, which costs more materials.
- No Deep Mine: the Deep Mine is the only lasting source of deep ore, which the late game and the rocket launches need. Any Deep Ore Sources on this map run out.
What this map cannot provide:
- No room for: Deep Mine, Limestone quarry, Nuclear Reactor, Launch pad, Water treatment plant, Uranium processing plant, Radioactive waste refinery, Cryogenic liquefaction plant, Steel mill, Mission control, Electrolysis plant, Hospital, Precision machine works, Radioactive Waste Vault, Fishery works, Materials Laboratory, Technical school, Fertilizer works, Grocery store.
```

Cliffside:

```
Deep Frontier is EXTREMELY difficult on Cliffside
- Small map: Cliffside has 100 x 50 = 5000 tiles, and the Deep Frontier late game is built for maps of at least 11176 tiles.
- Little room: the full set of large Deep Frontier sites (the 20 x 15 Nuclear Reactor, the Launch Pad, Deep Mines and Drills, processing plants) covers about 5588 tiles with their margins on a large map.
- Build upward: Deep Frontier raises this map's build height to 66 layers (vanilla 33); on a small map most of the colony has to stack on platforms, which costs more materials.
What this map cannot provide:
- No room for: Limestone quarry, Archive excavation, Nuclear Reactor, Launch pad, Water treatment plant, Uranium processing plant, Radioactive waste refinery, Cryogenic liquefaction plant, Steel mill, Mission control, Precision machine works, Electrolysis plant, Hospital, Radioactive Waste Vault, Fishery works, Food packaging works, Materials Laboratory, Town plaza.
- No natural shore-fishing banks: dam a river deeper before the Gatherer Flag can catch the first fish.
- No Human Record Caches to survey.
```

Beaverome (192×192):

```
Deep Frontier is EXTREMELY difficult on Beaverome
- No Deep Mine: the Deep Mine is the only lasting source of deep ore, which the late game and the rocket launches need. Any Deep Ore Sources on this map run out.
What this map cannot provide:
- No room for: Limestone quarry, Sandstone quarry, Deep Drill, Deep Mine, Deep Ore Processor, Steel mill, Mission control, Radioactive waste refinery, Uranium processing plant, Cryogenic liquefaction plant, Water treatment plant, Launch pad, Nuclear Reactor, Electrolysis plant, Hospital, Precision machine works, Radioactive Waste Vault, Fishery works, Materials Laboratory, Town plaza.
- No Deep Drill site beside a Deep Ore Source.
- Not enough deep ore in Deep Ore Sources to build one of each building.
- No reachable Underground Ruins: scrap metal runs out.
```

A map without the warning but with unmet items gets a shorter dialog (`UnmetTitle` plus the same lines), for example on Canyon: "Deep Frontier on Canyon: this map cannot provide everything the full Deep Frontier game needs: - No room for: Nuclear Reactor. - No natural shore-fishing banks: dam a river deeper before the Gatherer Flag can catch the first fish."

### Per-map setup

| Map | Size | EXTREMELY difficult | Variant | Placements | Sites | Finite DeepOre | Not met on this map (declared `unmet`) |
|---|---|---|---|---:|---:|---:|---|
| Beaverome | 192×192 | yes (no Deep Mine) | `beaverome` | 11 | 18 | 0 | LimestoneQuarry site (understructure); SandstoneQuarry site (understructure); Deep Drill sites beside Deep Ore Sources; finite deep ore covers one of each building; renewable scrap (Underground Ruins for the Efficient Mine); DeepDrill site (flat); DeepMine site (understructure); DeepProcessor site (flat); SteelMill site (flat); MissionControl site (flat); RadioactiveWasteRefinery site (flat); UraniumProcessingPlant site (flat); CryogenicLiquefactionPlant site (flat); WaterTreatmentPlant site (flat); LaunchPad site (flat); NuclearReactor site (flat); ElectrolysisPlant site (flat); Hospital site (flat); PrecisionMachineWorks site (flat); RadioactiveWasteVault site (flat); FisheryWorks site (flat); MaterialsLaboratory site (flat); TownPlaza site (flat) |
| Canyon | 128×128 |  | `canyon` | 17 | 43 | 17,000 | shore fishing banks (first FreshFish); NuclearReactor site (flat) |
| Cliffside | 100×50 | yes (area) | `cliffside` | 11 | 22 | 17,000 | shore fishing banks (first FreshFish); LimestoneQuarry site (understructure); ArchiveExcavation site (flat); Human Record Caches in survey range of an Archive Excavation site; NuclearReactor site (flat); LaunchPad site (flat); WaterTreatmentPlant site (flat); UraniumProcessingPlant site (flat); RadioactiveWasteRefinery site (flat); CryogenicLiquefactionPlant site (flat); SteelMill site (flat); MissionControl site (flat); PrecisionMachineWorks site (flat); ElectrolysisPlant site (flat); Hospital site (flat); RadioactiveWasteVault site (flat); FisheryWorks site (flat); FoodPackagingWorks site (flat); MaterialsLaboratory site (flat); TownPlaza site (flat) |
| Craters | 192×192 |  | `craters` | 17 | 38 | 17,000 | shore fishing banks (first FreshFish); NuclearReactor site (flat); RadioactiveWasteExport site (mapEdge) |
| Diorama | 50×50 | yes (area, no Deep Mine) | `diorama` | 14 | 18 | 17,000 | DeepMine site (understructure); LimestoneQuarry site (understructure); NuclearReactor site (flat); LaunchPad site (flat); WaterTreatmentPlant site (flat); UraniumProcessingPlant site (flat); RadioactiveWasteRefinery site (flat); CryogenicLiquefactionPlant site (flat); SteelMill site (flat); MissionControl site (flat); ElectrolysisPlant site (flat); Hospital site (flat); PrecisionMachineWorks site (flat); RadioactiveWasteVault site (flat); FisheryWorks site (flat); MaterialsLaboratory site (flat); TechnicalSchool site (flat); FertilizerWorks site (flat); GroceryStore site (flat) |
| HelixMountain | 256×256 |  | `helix-mountain` | 17 | 44 | 17,000 | none |
| Hollows | 192×192 |  | `hollows` | 18 | 44 | 18,000 | shore fishing banks (first FreshFish); NuclearReactor site (flat) |
| Lakes | 256×256 |  | `lakes` | 18 | 45 | 17,000 | none |
| Meander | 128×128 |  | `meander` | 17 | 41 | 17,000 | CryogenicLiquefactionPlant site (flat); RadioactiveWasteRefinery site (flat); WaterTreatmentPlant site (flat) |
| MountainRange | 256×150 |  | `mountain-range` | 17 | 43 | 17,000 | shore fishing banks (first FreshFish); NuclearReactor site (flat) |
| Nomads | 256×256 |  | `nomads` | 19 | 46 | 18,000 | shore fishing banks (first FreshFish) |
| Oasis | 256×256 |  | `oasis` | 19 | 44 | 18,000 | NuclearReactor site (flat); ReinforcedHydroTurbine site (hydro) |
| Pillars | 192×192 |  | `pillars` | 17 | 38 | 17,000 | irrigated farmland near the start; NuclearReactor site (flat); ReinforcedHydroTurbine site (hydro); Hospital site (flat) |
| Plains | 256×256 |  | `plains` | 19 | 46 | 18,000 | none |
| Pressure | 256×256 |  | `pressure` | 19 | 46 | 18,000 | trees near the start; pines (resin) near the start; irrigated farmland near the start |
| Spillage | 256×150 |  | `spillage` | 17 | 43 | 17,000 | NuclearReactor site (flat) |
| Terraces | 256×256 |  | `terraces` | 18 | 47 | 17,000 | none |
| ThousandIslands | 256×256 |  | `thousand-islands` | 17 | 39 | 17,000 | trees near the start; irrigated farmland near the start; NuclearReactor site (flat); SteelMill site (flat) |
| Waterfalls | 128×128 |  | `waterfalls` | 17 | 42 | 17,000 | shore fishing banks (first FreshFish); RadioactiveWasteRefinery site (flat) |

Every row passes `builtin` (evidence `outputs/maps/builtin-coverage.json` and the per-map files). The reasons, with their numbers, are in each variant's `unmet` entries. Notes:

- **No reactor site** on 11 maps (Beaverome, Canyon, Cliffside, Craters, Diorama, Hollows, Mountain Range, Oasis, Pillars, Spillage, Thousand Islands): either no dry, flat 20×15 footprint exists at any level, or none lies within 15 cells of clean water (Craters, Oasis, Spillage). The reactor never needs more height: at 66 the highest legal base is 47.
- **Beaverome gets no deep ore at all:** shallow lakes and sloping shores; the largest dry flat square is 9×9, so no Deep Mine, Drill, Processor or quarry fits, and its two Underground Ruins lie under 6–9 of water. It is not small by area (192×192), but without a Deep Mine site it gets the EXTREMELY difficult warning (2026-10-30; before, it showed the shorter "cannot provide" notice).
- **Diorama has no Deep Mine:** every 10×11 mine footprint (the mine before the 2026-10-30 compaction) has trees on the 5×5 vein cells, and a placed object may not overlap trees (the vein would have to wait for the player to cut them). It keeps two Drills with 17,000 finite DeepOre.
- **Cliffside**: the Deep Ore Processor (without it deep ore has no use) took priority over the Limestone Quarry; an exhaustive search found no layout with both quarries, both mines, both drills and the processor. The 1,800 limestone of its outcrops remain.
- **Meander**: the three missing 12×11 plants are the best result of an optimising packing with the reactor on the north-west plateau, not a proof; a run with the reactor elsewhere was stopped for memory.
- **Shore banks** (7 maps): the saved water is too shallow (or its banks too high) for `ShoreFishingSpec`; damming a river deeper creates banks in play.
- **Tool changes made for these maps**: badwater counts the outlet of a badwater source with a positive strength (Nomads and Oasis store theirs dry), and a source feeds the surface water its tunnel water reaches (Hollows: `column_components` follows connected water columns underground).
- In game, every missing building site of a map is folded into one "No room for: …" line with the enUS building names; the other items use the lines in `tools/map_setup.json` `unmetText`.

### In-game test (user present; startup dialogs need clicking)

Build the mod with the official Mod Builder first (canonical generation must have produced `Configurations/DeepFrontierMapSetup.blueprint.json`). Use a test settlement name: these runs make autosaves.

1. **Plains, new game.** New game → Plains → Iron Teeth. In `Player.log`: `[DeepFrontier MapSetup] new game on built-in Plains: MapHeight {23, 66} written for Map Transformer`, Map Transformer's `Loaded height: Terrain = 23, Total = 66`, then 19 `placed` lines and `Plains: 19 placed, 0 failed`. No dialog appears (Plains is not small and has nothing unmet).
2. **Objects.** Look at the coordinates from `tools/map_variants/plains.json`: the three veins and seams sit on the ground, each Deep Ore Source shows its 4,500 / 6,000 / 7,500 DeepOre, the outcrops 600, the caches are unsurveyed. The starting building and beavers spawned normally.
3. **Height.** The layer slicer reaches 65; a platform stack can be built to z = 65 and a block at z = 66 is refused.
4. **Exactly once.** Save, return to the menu and load the save: no new `MapSetup` placement lines, the objects are not duplicated, and the height is still 66 (Map Transformer's log line `Terrain = 23, Total = 66`).
5. **Diorama, new game.** The EXTREMELY difficult dialog appears once with the text above; the log lists every placement. Load its save: no dialog.
6. **Beaverome, new game.** The EXTREMELY difficult dialog appears with only the Deep Mine line before the unmet list.
7. **One map with unmet items and no warning** (see the table): the shorter dialog appears.
8. **A shipped variant file** (`Deep Frontier - Lakes`): no `MapSetup` placement lines (outcome `UserMap`), the map's own objects are there as before.
9. **An existing save** from before this build loads with no `MapSetup` lines and no dialog.

## Full game loop

A map supports the loop when a player can reach every stage, from the start to the last rocket launch, using only what the map provides plus normal building. "Normal building" includes vanilla Dynamite (Iron Teeth `Dynamite`, `DoubleDynamite`, `TripleDynamite`: `DynamiteSpec.Depth` 1–3, 600–1,200 science) and dams. The table below is the requirement matrix. Every row is checked by `loop_coverage` / `check_sites` in `tools/prepare_deep_frontier_map.py`, and the build fails when any row lacks its map provision.

### Where the requirements come from

- **Which buildings need a map site.** `site_rule` classifies every building of `TemplateCollection.Buildings.IronTeeth` from its generated blueprint:
  - a special placement spec gives a special site:
    - `UnderstructureConstraintSpec`: understructure;
    - `MapEdgeSiteSpec`: map edge;
    - `WaterDepthWorkCellsSpec`: waterside depth;
    - `WaterInputSpec`: water intake;
    - `MineralPitSpec`: pit with deposits;
    - `HydroTurbineSpec`: dam site;
  - otherwise a power generator (`WorkshopPoweredGeneratorSpec` or `GoodPoweredGeneratorSpec`), or any building with a footprint side of 8 or more (`largeFootprint`), needs a checked flat site; so do the Deep Drill, the Deep Ore Processor and the Archive Excavation whatever their size (`FLAT_SITE_TEMPLATES`: the deep-industry stage counts the drill's sites and needs the processor, the only building that turns DeepOre into products; Human Record Caches are surveyed from the excavation's sites);
  - `Buildings/Platforms` pieces and the small free-standing buildings need none: the crusher, kiln, mixer, smog scrubber, observation deck and outfall place on any flat patch.
  - A new building in the collection is classified automatically, and the build fails until the variants list its site.
- **Sizes, entrances and heights** come from the blueprint `BlockObjectSpec`. `top occupied layer < 66` replaces the old z < 33 limit (see Format and Z budget).
- **Placement rules** are the native ones the blueprints declare:
  - `BlockValidator` matter below, terrain and water;
  - `ContinuousTerrainConstraint` for veins and seams;
  - `UnderstructureFinder.FindStrict`: every foundation block whose occupation is exactly Top and/or Corners stands on the understructure;
  - `MapEdgeSite.TouchesMapEdge`: an occupied block on row/column 0 or size−1;
  - the waterside specs' work cells and intakes.
- **Native constants (1.1.2.8, decompiled)** are cited in the script:
  - `NavigationDistance.ResourceBuildings = 20`: the pit's `BuildingTerrainRange`/`InRangeYielders`;
  - `ContaminationBlockableBuilding.MaximumWaterContamination = 0.05`: hatchery work cells.
- **Quantities** come from the recipes (mod and vanilla `Blueprints.zip`) and building costs, expanded by `ProgramModel` along `recipeChoices`. The launch missions come from the launch pad's `RocketLaunchPadSpec.Missions`, and the number of caches from `Configurations/DeepFrontierNarrative.blueprint.json`. Placement counts are no longer fixed: the old 2–4 veins / 2–3 sources rule is replaced by these requirements.
- **Policy minimums** (`tools/map_loop_requirements.json`, each with its reason): trees and pines near the start, irrigated farmland, shore banks, two veins with mine sites, two drill sites, one reachable Underground Ruins, and 1 layer of natural head at a dam site.

### Requirement matrix

| Stage | Building / recipe | Map provision required | Rule source | Checked as |
|---|---|---|---|---|
| 1 Start | water pumps; PureWater, coolant, electrolysis | clean water fed by a native `WaterSourceSpec` source, reachable from the start | water map, sources | `clean water` |
| 1 Start | Extract (4 Badwater), Explosives (5 Badwater), Chemical (4 Badwater + Extract) | badwater fed by a badwater source, reachable | vanilla and mod recipes | `badwater` |
| 1 Start | Log, Plank; TreatedPlank = Plank + PineResin (archive, airframes, payload) | ≥ 200 trees and ≥ 50 resin pines within route 60 | `TreeComponentSpec`, Pine `GatherableSpec` | `trees`, `pines` |
| 1 Start | crops (Canola → Grease → ArchiveData; Corn; Eggplant) | ≥ 150 dry, free, flat cells within 4 of clean water near the start | policy | `irrigated farmland` |
| 1 Start | Gatherer Flag shore fishing: FreshFish → FishOil → Lubricant → Cryocoolant (rocket fuel); hatchery stock | ≥ 4 reachable banks: dry bank, neighbour one layer down with clean water ≥ 0.5 deep (contamination ≤ 0.01), surface within 1.25 below the bank | `ShoreFishingSpec` (GathererFlag patch), `ShoreFishing.Suitable` | `shore fishing banks` |
| 2 Construction | Sandstone Pit, Limestone Pit | deposits of the pit's `ResourceGroup` within 20 steps of its door, on its level; yield ≥ the stone that every building up to the permanent quarry (4,000 science) costs: 842 sandstone, 722 limestone (2026-10-29; 249 / 214 before the cost pass) | `MineralPitSpec`, `YieldRemovingBuildingSpec`, `MineralDepositSpec`, `NavigationDistance.ResourceBuildings` | pit site + `deposits in range` |
| 2 Construction | Sandstone / Limestone Quarry (renewable stone for cement, aggregate, concrete) | a placed `SandstoneSeam` / `LimestoneSeam` (5×5) under the quarry's 5×5 Top core (local x 3–7, y 1–5), flat 11×7 site | `UnderstructureConstraintSpec` | understructure site |
| 3 Deep industry | Deep Drill (DeepOre from a finite source) | ≥ 2 flat 7×6 drill sites (the blueprint's footprint) within 25 cells of a `DeepOreSource` (Pileable, ≤ `StockpileSpec.MaxCapacity` 10,000, consumed by a DeepDrill recipe); the sources beside a checked drill site hold ≥ the DeepOre of one of each building + `finiteDeepOreMargin` 5% (15,608 → 16,389 on 2026-10-30) | `StockpileSpec`, DeepDrill recipes, `ProgramModel` | `Deep Drill sites`, `finite deep ore` |
| 3 Deep industry | Deep Mine (permanent DeepOre: coal, oil, deep alloy, uranium for the rest of the game) | ≥ 2 `DeepOreVein`s each under a checked mine site (21-cell core at local x 2–6, y 1–5) | `UnderstructureConstraintSpec` | understructure sites (min 2) |
| 3 Deep industry | Deep Ore Processor, Steel Mill (flux, high-grade steel, alloy), Precision Machine Works | flat sites | size | flat sites |
| 3 Deep industry | metal (MetalBlock = 2 ScrapMetal; MetalPart) | ruin scrap plus ≥ 1 reachable `UndergroundRuins` for the renewable Efficient Mine; ruins alone (16,125–23,730) are less than one of each building plus three launches (26,968) | vanilla `RuinSpec`, `EfficientMine` | `renewable scrap` |
| 4 Power | Coal and Oil Power Plant | flat sites (fuel from the Deep Ore Processor, water) | `GoodPoweredGeneratorSpec` | flat sites |
| 4 Power | Reinforced Hydro Turbine | a source-fed river cell with ≥ 1 layer of natural bed drop within 12 wet cells (the dam supplies the rest of the head) | `HydroTurbineSpec` | dam site |
| 4 Power | Nuclear Reactor (3 ReactorCoolantWater/h from pumped water) | flat 20×15 site, top layer < 66, clean water within 15 cells | `ReactorMeltdownSpec`, `maxWaterDistance` | flat site |
| 5 Narrative | chapters: an investigation building, 20 DeepAlloy, PureWater + Chemical, 6 RecoveredArtifact, 10/30 ArchiveData + Mission Control, the three launches | the sites, deep ore, clean water and badwater above, and pines | `DeepFrontierNarrative` stages | the rows they rely on |
| 5 Narrative | the five "Record Cache" discoveries (`CachesSurveyed` 1–5) | ≥ 5 `HumanRecordCache`s, each within `SurveyRadius` 7 (Chebyshev, ±7 layers) of the occupied cells of a checked Archive Excavation site | `HumanRecordCacheSpec`, narrative settings | `caches in survey range` |
| 6 Nuclear | DeepUranium (UraniumOre from DeepOre) | deep ore (stage 3) | recipes | stage 3 rows |
| 6 Nuclear | Uranium Processing Plant, Waste Vault, Waste Refinery | flat sites | size | flat sites |
| 6 Nuclear | Radioactive Waste Export (sludge and contaminated water leave the map) | flat 6×5 site with an occupied block on the map edge, reachable | `MapEdgeSiteSpec`, `MapEdgeSite.TouchesMapEdge` | map-edge site |
| 6 Nuclear | Radioactive Sludge Recovery Pump | bank site: the intake (local 1,2,−1) over open water within `MaxDepth` 6 and an Air-below block; on a straight shore the site lists the intake cell to blast | `WaterInputSpec`, `WaterInputPipeSpec` | water-intake site |
| 6 Nuclear | Plains Hard only | the Radioactive Spring next to a river cell at or below it | `RadioactiveWaterSourceSpec` | `Radioactive Spring` |
| 7 Rocket | Water Treatment Plant → Electrolysis → Cryogenic Liquefaction → Cryogenic Tank Farm; Rocket Assembly Hangar; Mission Control; Launch Pad | flat sites; source-fed clean water (three launches need about 26,400 Water) | sizes, mission recipes | flat sites, `clean water` |
| 8 Space | every building above | non-overlapping primary sites, door approach free and routable, listed open margins clear of other footprints and placements | — | site checks |
| — | Fish Hatchery (7×7×5 since 2026-10-26) | door cell on dry ground at the bank level; the other bank cells at or below it (adaptive bank posts); deck blocks above terrain (they may stand in water); each of the four work cells (local y 5) in an open water column whose surface stands ≥ 0.2 above the cell floor (bank − 1) and holding ≤ 7 of water; work cell 0 contamination ≤ 0.05; every pile and bank post reaches the bed within 6; Dynamite allowed on deck cells | `WaterDepthWorkCellsSpec`, `ContaminationBlockableBuilding` | waterside site |
| — | Fishery Works, Restaurant, Grocery, Hospital, Town Plaza, Greenhouse, Fertilizer Works, Food Packaging Works, Technical School, Materials Laboratory | flat sites. The fishery's basins are filled by haulers or pipes, so it does not need a shore | size | flat sites |

### Quantities: is the deep ore enough for a launch program?

From the recipes (`loopCoverage.program` in the evidence):

> Figures of 2026-10-30 (after the late-game cost pass), from the Plains evidence.

| Need | DeepOre | ScrapMetal | Water | Log | Sandstone / Limestone |
|---|---:|---:|---:|---:|---:|
| One of each collection building (reactor included) | 15,608 | 74,064 | 27,705 | 28,191 | 12,607 / 10,806 |
| Orbital Observatory | 1,263 | 4,184 | 6,039 | 1,116 | — |
| Recovery Probe | 1,662 | 5,278 | 8,332 | 1,542 | — |
| Long-Range Beacon | 2,061 | 6,372 | 10,625 | 1,967 | — |
| Three successful launches | 4,986 | 15,834 | 24,996 | 4,625 | — |

- The finite Deep Ore Sources hold 18,000 (Plains) or 17,000 (Lakes, Terraces); every built-in map with drill sites has 17,000 or 18,000 (see "Per-map setup"). That covers one of each building with the 5% margin (16,389), the reactor's 20 EnrichedFuel gate included, but not one of each building plus three launches (20,594).
- Each failed launch consumes the whole rocket (base failure 30–40%, reduced by Mission Control and flight heritage to a 5% floor).
- Oil plants burn 2 Crude Oil per working hour (0.67 DeepOre).
- **The launch program therefore depends on the permanent Deep Mines.** Every map has three veins with checked mine sites; the rule requires two.
- Scrap follows the same pattern: ruins hold 16,125–23,730, while one of each building alone needs about 74,000 (2026-10-30). The Efficient Mine on Underground Ruins is required. Every map has two to four, at least two of them reachable.
- Stone: three 600-yield outcrops per mineral (1,800) cover the 842 / 722 needed before the quarries about twice over (2026-10-29). The quarries are permanent.

### Audit: gaps before and after (2026-10-24)

The coverage check was first run on the variants as they were (`--out-dir` dry run; placements and sites converted unchanged to the new list format). Before:

| Gap | Plains / Plains Hard | Lakes | Terraces |
|---|---|---|---|
| Sandstone and limestone outcrops (pits had nothing to dig, so the concrete chain could not start) | missing | missing | missing |
| Sandstone and limestone seams (quarries impossible) | missing | missing | missing |
| Human Record Caches (5 discoveries) | 0 placed (3 unplaced candidates) | 0 (3 candidates) | 0 (3 candidates) |
| Checked sites | reactor, pad, drills, mines only; 36 building types without a site | same | same |
| Map-edge waste export site | missing | missing | missing |
| Hatchery / sludge-pump / dam sites | missing | missing | missing |
| Shore banks near the start | 0 within route 80 (the start river is 0.32 deep in the saved water; nearest bank route 105, 6 bridges) | 215 | 17 |
| Deep ore | 6,000 finite + 3 veins | 4,000 + 3 veins | 4,000 + 3 veins |
| Underground Ruins reachable | 3 of 3 | 2 of 3 | 3 of 4 |

After: every stage passes on all four maps.

- **Added per map:**
  - three Sandstone and three Limestone Outcrops, each set beside its pit site near the start (route 5–15 cells);
  - one Sandstone and one Limestone Seam, each under a checked quarry site;
  - Human Record Caches up to five, each with its own Archive Excavation site. Candidates with no room for an excavation were dropped: Plains "West Lowlands ruins" and Terraces "South ruins". Plains and Terraces have 2 old + 3 new caches, Lakes 3 + 2;
  - 40 new sites, so every building that needs one has one: 48 sites on Plains and Terraces, 47 on Lakes.
- The deep-ore placements, the reactor and launch-pad sites and the spring are unchanged.
- The shore-bank rule now counts reachable banks. A shallow start river can be dammed deeper; the near-start count is reported.
- **No terrain is edited by the script.** These sites rely on the player's Dynamite, listed in the site data under `dynamite`:
  - the sludge recovery pump on Plains and Lakes: one cell, one layer, opening the intake to the river;
  - the Terraces hatchery no longer needs Dynamite since the compact 7x7 footprint (2026-10-26): its primary site is natural. Only its listed alternative (all four pens in clean water) uses two one-layer charges.

### Building-side findings for the owners

- **Radioactive Sludge Recovery Pump.** Its intake block (local 1,2) needs Air below while its neighbours (0,2) and (2,2) need Ground. A natural shore therefore needs a one-cell water notch. Plains and Lakes have none, and Terraces has exactly one. A vanilla-style intake on the footprint edge, over a deck block, would place on any straight bank. Until then, a site lists one Dynamite cell.
- **Fish Hatchery.** Until 2026-10-24 this script disagreed with the game in two ways. It refused any hatchery block in water, which forces the pens dry. It also read MinDepth against the column depth instead of the surface above the pen cell. All three earlier sites therefore had dry pens in game (surface 0.4–1.8 below the pen floor) and would have stayed blocked for water. The check now follows `WatersideSurvey`: the pens need a water surface at least 0.2 above bank − 1. Most natural rivers on these maps sit 1.3–1.7 below their banks, so this pen depth is the rule that makes sites rare. The second filter was the straight eight-cell bank, so now only the door cell needs ground; the other bank cells may step down onto adaptive bank posts. The deck still needs all 7×8 cells at or below bank − 1. On Terraces the remaining limit is contamination.

## Why these maps

The built-in maps are `BinaryData` assets inside `Timberborn_Data/resources.assets`, loaded from the resource folder `Maps` (`MapRepository.GetBuiltinMapNames`/`OpenResourceMap`). Each is a complete `.timber` zip. The tool reads it by its `MapMetadata.<Name>.Name` key and checks the recorded SHA-256, so no copy of game content is kept in the repository. No Workshop map was needed.

The maps were chosen (2026-10-22) when the height was still the vanilla 33 layers. The deciding constraint then was a flat site for the 20×15 reactor at level ≤ 14 (a dry, object-free footprint). All 19 named built-in maps were scanned:

- **Have one:** Plains, Lakes, Terraces, Meander and Waterfalls, plus the unconventional Nomads, Oasis, Pressure and Spillage.
- **Have none:** Canyon, Mountain Range, Helix Mountain, Hollows, Craters, Thousand Islands, Beaverome, Pillars, Diorama and Cliffside.

At 66 layers the level limit no longer binds (see below), so the "have none" maps could be reconsidered. The maps themselves:

- **Plains**: the flagship map. It has large level-3/4 plains, a central lake fed by two rivers, and two badwater rivers. The user's existing `Deep Frontier - Concrete Test` map is also Plains-based and is left unchanged.
- **Lakes**: lake-cooled power. There are many lakes, three badwater sources and narrow land, so the reactor sits on an island.
- **Terraces**: the vertical map. The start is on a level-15 terrace, with a level-6 valley below and a level-3 basin.

## Format and Z budget (Timberborn 1.1.2.8, decompiled)

- **Height is per map through Map Transformer**, a required mod (`docs/map-height.md`). Map Transformer 11.0.0 Harmony-patches `MapSize.Load`/`Save` to read and write `MapHeight {X: terrain layers, Y: total}`. Without the key the global `MapSizeSpec` applies: 23 terrain / 33 total layers.
- **The variants carry `MapHeight {46, 66}`.** `resize_height` reproduces Map Transformer's *Resize Map Height*: every voxel stays at its z, empty terrain layers are appended, and the key is added. The validator checks the key and that the stored layers equal the terrain layers.
- **The real limit.** On load and placement, every occupied block must satisfy z < 66 (`BlockValidator.FitsInMap`). The highest base level for a building is 65 − its top occupied layer: NuclearReactor 47, LaunchPad 48, DeepMine and DeepDrill 50, Mission Control 50. No site is near these limits; the highest is the Terraces alternative pad at level 15.
- **Site levels.** A site's `z` is the surface level the building stands on. The native Placement z is its layer 0, i.e. `z − BaseZ`; this differs only for the Fish Hatchery (BaseZ 1). The evidence lists both, as `at` and `nativePlacement`.
- **Packed arrays.** Terrain voxels and water columns are packed z-major (`MapIndexService.Pack`). Each water column is stored as `depth:contamination:overflow:floor:old` (`WaterColumnPackedListSerializer`).
- **Block order and rotation.** Block index = (z·Y + y)·X + x. A positioned cell is `Orientation(Flip(local)) + Coordinates`, where Cw90 maps (x, y) to (y, −x).
- **Invalid objects are deleted on load.** `BlockObject.AddToServiceAfterLoad` deletes any object that fails validation, so each placement is checked for:
  - terrain and water;
  - other objects, trees included;
  - matter below;
  - `ContinuousTerrainConstraint` (veins and seams must sit on the first terrain column).
- **Saved components.**

| Placement | Saved components | Basis |
|---|---|---|
| `DeepOreSource` | `FixedStockpile` (required on load), `SingleGoodAllower`, `Inventory:Stockpile` | what vanilla `ReserveWarehouse` saves in Nomads |
| outcrops | `Yielder:Mineral {Yield: {Good, Amount}}`, with the blueprint's 600 | the format the official map editor wrote in `Deep Frontier - Concrete Test` |
| `RadioactiveSpringSource` | `WaterSource {SpecifiedStrength, CurrentStrength}` | native `WaterSource.Load` |
| veins, seams, `HumanRecordCache` | `BlockObject` only | the cache loads its survey state only when present (`TryGetComponent`); vanilla `MediumRelic`s in built-in maps save only `BlockObject` |

  A missing `BlockObjectState` means the object is finished.
- **User maps in the new-game list.** The list shows the file name and `MapDescription` (`UserMapItemFactory`); localisation keys are ignored. Each variant therefore:
  - clears the loc keys;
  - writes a plain description, generated from the manifest and `tools/installed_dependency_manifests_1_1.json`, that names Deep Frontier, its version and every `RequiredMods` entry of `src/DeepFrontier/manifest.json`;
  - keeps the source thumbnail.
- **Version.** `version.txt` and `GameVersion` stay as in the source. Built-in maps say `0`, a development version, so `VersionCompatibilityService` treats them as fully compatible.
- **Byte-faithful output.** The output `world.json` is the resized source bytes with the new entities appended to the trailing `Entities` array. Terrain (apart from the appended empty layers), water, singletons and every existing entity stay byte-identical.

## Understructure geometry

`UnderstructureFinder.FindStrict` requires every foundation block whose occupation is exactly Top and/or Corners to stand on the same understructure. The tool reads those blocks from the blueprint, rotated with the site:

- **DeepMine (7×6, was 10×11):** a 25-cell core at local x 2–6, y 1–5 (every core cell is a building cell). For Cw0, mine origin = vein origin − (2, 1).
- **Sandstone / Limestone Quarry (11×7):** a full 5×5 core at local x 3–7, y 1–5. For Cw0, quarry origin = seam origin − (3, 1).

Each understructure site is checked for:

- every core cell on its placed understructure;
- no other occupied foundation block on the understructure's cells;
- the understructure at the site level;
- a footprint that is flat, dry and free of non-removable objects.

## Placements and sites

Coordinates are map (x, y, z); z is the surface level the object stands on.

- **Route** is the path length from the start over dry land. Water cells count as bridges the player must build (dams, levees or bridges).
- **Trees** inside a site must be cut by the player. Placed objects never overlap trees or any other object.
- **"open"** lists the sides whose margin strip (width in brackets) is verified flat, dry and free. No other footprint or placement may enter a listed margin.
- The tables are generated from the evidence. The previews mark every entry.
- Plains Hard has exactly the Plains placements and sites, plus the spring:

| Object | Label | At (x, y, z) | Details |
|---|---|---|---|
| RadioactiveSpringSource | North-east river head spring (HARD) | 240, 246, 9 | 0.2 radioactive water/h |

### Plains (and Plains Hard)

| # | Object | Label | At (x, y, z) | Details | Route / bridges |
|---:|---|---|---|---|---|
| P1 | DeepOreVein | Crater Rim West vein | 156, 102, 4 |  | 51 / 0 |
| P2 | DeepOreVein | Crater Rim East vein | 187, 102, 4 |  | 82 / 0 |
| P3 | DeepOreVein | West Lowlands vein | 34, 80, 2 |  | 151 / 2 |
| P4 | DeepOreSource | Crater Road source | 159, 120, 4 | 4,500 DeepOre | 39 / 0 |
| P5 | DeepOreSource | North Bank source | 108, 167, 4 | 6,000 DeepOre | 45 / 7 |
| P6 | DeepOreSource | West Lowlands source | 21, 81, 2 | 7,500 DeepOre | 168 / 2 |
| P7 | HumanRecordCache | Crater Rim ruins | 155, 87, 4 |  | 68 / 2 |
| P8 | HumanRecordCache | North ruins | 176, 188, 6 |  | 101 / 5 |
| P9 | LimestoneOutcrop | Limestone Outcrop 1 (Limestone Pit, 13 cells south of the start) | 125, 125, 5 | 600 Limestone | 11 / 0 |
| P10 | LimestoneOutcrop | Limestone Outcrop 2 (Limestone Pit, 13 cells south of the start) | 126, 128, 5 | 600 Limestone | 7 / 0 |
| P11 | LimestoneOutcrop | Limestone Outcrop 3 (Limestone Pit, 13 cells south of the start) | 122, 126, 5 | 600 Limestone | 13 / 0 |
| P12 | SandstoneOutcrop | Sandstone Outcrop 1 (Sandstone Pit, 13 cells west of the start) | 122, 140, 3 | 600 Sandstone | 5 / 0 |
| P13 | SandstoneOutcrop | Sandstone Outcrop 2 (Sandstone Pit, 13 cells west of the start) | 120, 143, 3 | 600 Sandstone | 10 / 0 |
| P14 | SandstoneOutcrop | Sandstone Outcrop 3 (Sandstone Pit, 13 cells west of the start) | 122, 137, 3 | 600 Sandstone | 5 / 0 |
| P15 | LimestoneSeam | Limestone Seam (Limestone Quarry, 45 cells south-west of the start) | 100, 101, 3 |  | 52 / 0 |
| P16 | SandstoneSeam | Sandstone Seam (Sandstone Quarry, 46 cells south-east of the start) | 166, 109, 4 |  | 54 / 0 |
| P17 | HumanRecordCache | Ruins 78 cells north-west of the start | 79, 196, 5 |  | 112 / 8 |
| P18 | HumanRecordCache | Ruins 118 cells south of the start | 107, 22, 4 |  | 129 / 2 |
| P19 | HumanRecordCache | Ruins 110 cells south-west of the start | 64, 49, 9 |  | 145 / 2 |

| # | Site | Label | At, orientation | Rule | Notes | Route / bridges | Trees |
|---:|---|---|---|---|---|---|---:|
| S1 | NuclearReactor | North Bank plain | 111, 192, 3 Cw0 | flat | water 11; open NESW (2) | 59 / 6 | 8 |
| S2 | LaunchPad | North Bank plain, west of the reactor | 94, 192, 3 Cw0 | flat | open NESW (2) | 84 / 6 | 14 |
| S3 | DeepDrill | Crater Road drill | 163, 128, 4 Cw90 | flat | open NESW (1) | 36 / 0 | 5 |
| S4 | DeepDrill | North Bank drill | 105, 170, 4 Cw0 | flat | open NESW (1) | 54 / 6 | 16 |
| S5 | DeepDrill | West Lowlands drill | 8, 80, 2 Cw0 | flat | open NESW (1) | 171 / 2 | 5 |
| S6 | DeepMine | Crater Rim West mine | 154, 101, 4 Cw0 | understructure | on DeepOreVein 156, 102, 4; open NESW (1) | 44 / 0 | 0 |
| S7 | DeepMine | Crater Rim East mine | 185, 101, 4 Cw0 | understructure | on DeepOreVein 187, 102, 4; open NESW (1) | 75 / 0 | 0 |
| S8 | DeepMine | West Lowlands mine | 32, 79, 2 Cw0 | understructure | on DeepOreVein 34, 80, 2; open NESW (1) | 147 / 2 | 0 |
| S9 | LimestonePit | Limestone Pit, 13 cells south of the start | 128, 127, 5 Cw90 | pit | 1800 Limestone in range (3 deposits); open NSEW (1) | 7 / 0 | 1 |
| S10 | SandstonePit | Sandstone Pit, 13 cells west of the start | 120, 138, 3 Cw180 | pit | 1800 Sandstone in range (3 deposits); open NSEW (1) | 7 / 0 | 11 |
| S11 | LimestoneQuarry | Limestone Quarry, 45 cells south-west of the start | 99, 108, 3 Cw90 | understructure | on LimestoneSeam 100, 101, 3; open NSEW (1) | 48 / 0 | 0 |
| S12 | SandstoneQuarry | Sandstone Quarry, 46 cells south-east of the start | 165, 116, 4 Cw90 | understructure | on SandstoneSeam 166, 109, 4; open NSEW (1) | 50 / 0 | 2 |
| S13 | ArchiveExcavation | Archive Excavation for Crater Rim ruins | 145, 79, 4 Cw0 | flat | open N (1) | 60 / 2 | 22 |
| S14 | ArchiveExcavation | Archive Excavation for North ruins | 182, 180, 6 Cw0 | flat | open none (1) | 90 / 5 | 0 |
| S15 | ArchiveExcavation | Archive Excavation for Ruins 78 cells north-west of the start | 74, 184, 3 Cw0 | flat | open SE (1) | 98 / 8 | 0 |
| S16 | ArchiveExcavation | Archive Excavation for Ruins 118 cells south of the start | 101, 21, 4 Cw90 | flat | open none (1) | 131 / 2 | 0 |
| S17 | ArchiveExcavation | Archive Excavation for Ruins 110 cells south-west of the start | 70, 53, 6 Cw0 | flat | open NE (1) | 121 / 2 | 17 |
| S18 | FishHatchery | Fish Hatchery, 21 cells north-east of the start | 145, 147, 3 Cw0 | waterDepth | compact 7x7; surface 0.26 above the work cells, contamination ≤ 0.00; 5 bank posts | 19 / 0 | 0 |
| S19 | RadioactiveSludgeRecoveryPump | Radioactive Sludge Recovery Pump, 15 cells north-west of the start | 123, 150, 3 Cw0 | waterInput | Dynamite 1 cell(s), 1 layer(s); intake floor 2 | 12 / 0 | 0 |
| S20 | RadioactiveWasteExport | Radioactive Waste Export, 145 cells south of the start | 180, 5, 11 Cw90 | mapEdge | 12 edge cells; open NEW (1) | 192 / 0 | 12 |
| S21 | ReinforcedHydroTurbine | Dam site with 7 layers of natural drop, 113 cells north of the start | 109, 249, 3 | hydro | 7 layers natural drop, source strength 18.75 | 137 / 6 | 0 |
| S22 | WaterTreatmentPlant | Water Treatment Plant, 35 cells east of the start | 160, 130, 4 Cw0 | flat | open NSEW (1) | 27 / 0 | 68 |
| S23 | UraniumProcessingPlant | Uranium Processing Plant, 53 cells south of the start | 117, 81, 4 Cw0 | flat | open NSEW (1) | 43 / 0 | 38 |
| S24 | RadioactiveWasteRefinery | Radioactive Waste Refinery, 56 cells south-east of the start | 165, 94, 4 Cw0 | flat | open NSEW (1) | 62 / 0 | 1 |
| S25 | CryogenicLiquefactionPlant | Cryogenic Liquefaction Plant, 38 cells north-east of the start | 149, 174, 6 Cw90 | flat | open NSEW (1) | 40 / 6 | 21 |
| S26 | MissionControl | Mission Control, 64 cells south of the start | 106, 83, 4 Cw90 | flat | open NSEW (1) | 63 / 0 | 12 |
| S27 | SteelMill | Steel Mill, 53 cells west of the start | 75, 151, 3 Cw0 | flat | open NSEW (1) | 52 / 9 | 9 |
| S28 | DeepProcessor | Deep Processor, 39 cells north of the start | 122, 172, 3 Cw0 | flat | open NSEW (1) | 37 / 6 | 13 |
| S30 | Hospital | Hospital, 64 cells south of the start | 117, 71, 4 Cw0 | flat | open NSEW (1) | 55 / 0 | 34 |
| S31 | ElectrolysisPlant | Electrolysis Plant, 47 cells north-west of the start | 95, 178, 4 Cw90 | flat | open NSEW (1) | 66 / 6 | 52 |
| S32 | PrecisionMachineWorks | Precision Machine Works, 50 cells north of the start | 107, 180, 4 Cw0 | flat | open NSEW (1) | 60 / 6 | 51 |
| S34 | RadioactiveWasteVault | Radioactive Waste Vault, 39 cells north-west of the start | 92, 150, 3 Cw0 | flat | open NSEW (1) | 37 / 7 | 16 |
| S35 | FisheryWorks | Fishery Works, 13 cells south-east of the start | 137, 127, 3 Cw0 | flat | open NSEW (1) | 4 / 0 | 0 |
| S36 | TownPlaza | Town Plaza, 18 cells north of the start | 131, 152, 3 Cw0 | flat | open NSEW (1) | 12 / 0 | 25 |
| S37 | MaterialsLaboratory | Materials Laboratory, 31 cells south-east of the start | 143, 116, 5 Cw90 | flat | open NSEW (1) | 28 / 0 | 21 |
| S38 | RocketAssemblyHangar | Rocket Assembly Hangar, 32 cells south-west of the start | 103, 113, 4 Cw0 | flat | open NSEW (1) | 30 / 0 | 0 |
| S39 | FoodPackagingWorks | Food Packaging Works, 55 cells south-east of the start | 173, 106, 4 Cw0 | flat | open NSEW (1) | 62 / 0 | 6 |
| S40 | Restaurant | Restaurant, 21 cells east of the start | 148, 135, 3 Cw0 | flat | open NSEW (1) | 15 / 0 | 43 |
| S42 | TechnicalSchool | Technical School, 55 cells south-west of the start | 100, 96, 3 Cw90 | flat | open NSEW (1) | 61 / 0 | 0 |
| S43 | FertilizerWorks | Fertilizer Works, 62 cells south of the start | 130, 80, 4 Cw90 | flat | open NSEW (1) | 54 / 0 | 15 |
| S44 | GroceryStore | Grocery Store, 16 cells west of the start | 114, 148, 3 Cw90 | flat | open SW (1) | 8 / 0 | 43 |
| S46 | Greenhouse | Greenhouse, 49 cells east of the start | 177, 130, 6 Cw90 | flat | open NSEW (1) | 48 / 0 | 7 |
| S47 | OilPowerPlant | Oil Power Plant, 29 cells south-east of the start | 155, 123, 4 Cw0 | flat | open NSEW (1) | 28 / 0 | 19 |
| S48 | CoalPowerPlant | Coal Power Plant, 20 cells west of the start | 109, 134, 3 Cw0 | flat | open NSEW (1) | 14 / 0 | 16 |

### Lakes

| # | Object | Label | At (x, y, z) | Details | Route / bridges |
|---:|---|---|---|---|---|
| P1 | DeepOreVein | West Bench vein | 21, 148, 3 |  | 88 / 0 |
| P2 | DeepOreVein | Slope Ridge vein | 53, 158, 4 |  | 66 / 0 |
| P3 | DeepOreVein | Southeast Lowlands vein | 215, 2, 1 |  | 232 / 0 |
| P4 | DeepOreSource | West Clearing source | 65, 122, 2 | 7,000 DeepOre | 38 / 0 |
| P5 | DeepOreSource | Southeast Lowlands source | 179, 25, 2 | 10,000 DeepOre | 176 / 0 |
| P6 | HumanRecordCache | West ruins | 45, 113, 4 |  | 66 / 0 |
| P7 | HumanRecordCache | North river ruins | 116, 180, 3 |  | 73 / 5 |
| P8 | HumanRecordCache | East terrace ruins | 147, 117, 3 |  | 52 / 5 |
| P9 | LimestoneOutcrop | Limestone Outcrop 1 (Limestone Pit, 12 cells east of the start) | 110, 124, 2 | 600 Limestone | 9 / 0 |
| P10 | LimestoneOutcrop | Limestone Outcrop 2 (Limestone Pit, 12 cells east of the start) | 113, 123, 2 | 600 Limestone | 13 / 0 |
| P11 | LimestoneOutcrop | Limestone Outcrop 3 (Limestone Pit, 12 cells east of the start) | 112, 120, 2 | 600 Limestone | 15 / 0 |
| P12 | SandstoneOutcrop | Sandstone Outcrop 1 (Sandstone Pit, 12 cells north of the start) | 99, 140, 3 | 600 Sandstone | 6 / 0 |
| P13 | SandstoneOutcrop | Sandstone Outcrop 2 (Sandstone Pit, 12 cells north of the start) | 99, 146, 3 | 600 Sandstone | 12 / 0 |
| P14 | SandstoneOutcrop | Sandstone Outcrop 3 (Sandstone Pit, 12 cells north of the start) | 94, 143, 3 | 600 Sandstone | 14 / 0 |
| P15 | LimestoneSeam | Limestone Seam (Limestone Quarry, 85 cells south of the start) | 97, 43, 1 |  | 81 / 0 |
| P16 | SandstoneSeam | Sandstone Seam (Sandstone Quarry, 97 cells south of the start) | 94, 31, 1 |  | 94 / 0 |
| P17 | HumanRecordCache | Ruins 108 cells south of the start | 107, 22, 2 |  | 107 / 0 |
| P18 | HumanRecordCache | Ruins 99 cells west of the start | 4, 105, 4 |  | 115 / 0 |

| # | Site | Label | At, orientation | Rule | Notes | Route / bridges | Trees |
|---:|---|---|---|---|---|---|---:|
| S1 | NuclearReactor | Reactor Island (north shore of the central lake) | 79, 189, 3 Cw90 | flat | water 2; open NESW (2) | 56 / 3 | 61 |
| S2 | LaunchPad | East Launch Field (east of the river) | 128, 115, 2 Cw0 | flat | open NESW (2) | 25 / 5 | 0 |
| S3 | DeepDrill | West Clearing drill | 63, 112, 2 Cw0 | flat | open NESW (1) | 34 / 0 | 0 |
| S4 | DeepDrill | Southeast Lowlands drill | 182, 23, 2 Cw0 | flat | open NESW (1) | 174 / 0 | 5 |
| S5 | DeepMine | West Bench mine | 19, 147, 3 Cw0 | understructure | on DeepOreVein 21, 148, 3; open NESW (1) | 84 / 0 | 0 |
| S6 | DeepMine | Slope Ridge mine | 51, 157, 4 Cw0 | understructure | on DeepOreVein 53, 158, 4; open NESW (1) | 62 / 0 | 22 |
| S7 | DeepMine | Southeast Lowlands mine | 213, 1, 1 Cw0 | understructure | on DeepOreVein 215, 2, 1; open NESW (1) | 225 / 0 | 0 |
| S8 | LimestonePit | Limestone Pit, 12 cells east of the start | 111, 126, 2 Cw0 | pit | 1800 Limestone in range (3 deposits); open NSEW (1) | 6 / 0 | 5 |
| S9 | SandstonePit | Sandstone Pit, 12 cells north of the start | 101, 144, 3 Cw90 | pit | 1800 Sandstone in range (3 deposits); open NSEW (1) | 6 / 0 | 10 |
| S10 | LimestoneQuarry | Limestone Quarry, 85 cells south of the start | 96, 50, 1 Cw90 | understructure | on LimestoneSeam 97, 43, 1; open NSEW (1) | 78 / 0 | 0 |
| S11 | SandstoneQuarry | Sandstone Quarry, 97 cells south of the start | 91, 30, 1 Cw0 | understructure | on SandstoneSeam 94, 31, 1; open NSEW (1) | 92 / 0 | 0 |
| S12 | ArchiveExcavation | Archive Excavation for West ruins | 38, 116, 4 Cw0 | flat | open E (1) | 56 / 0 | 3 |
| S13 | ArchiveExcavation | Archive Excavation for North river ruins | 114, 171, 3 Cw0 | flat | open none (1) | 59 / 5 | 21 |
| S14 | ArchiveExcavation | Archive Excavation for East terrace ruins | 150, 109, 3 Cw0 | flat | open NE (1) | 56 / 5 | 17 |
| S15 | ArchiveExcavation | Archive Excavation for Ruins 108 cells south of the start | 114, 24, 2 Cw270 | flat | open none (1) | 96 / 0 | 0 |
| S16 | ArchiveExcavation | Archive Excavation for Ruins 99 cells west of the start | 3, 108, 4 Cw0 | flat | open NSE (1) | 99 / 0 | 17 |
| S17 | FishHatchery | Fish Hatchery, 23 cells north of the start | 102, 150, 3 Cw0 | waterDepth | compact 7x7; surface 0.55 above the work cells, contamination ≤ 0.00; 5 bank posts | 16 / 0 | 0 |
| S18 | RadioactiveSludgeRecoveryPump | Radioactive Sludge Recovery Pump, 18 cells east of the start | 118, 130, 2 Cw90 | waterInput | Dynamite 1 cell(s), 1 layer(s); intake floor 1 | 13 / 0 | 3 |
| S19 | RadioactiveWasteExport | Radioactive Waste Export, 101 cells west of the start | 0, 149, 8 Cw0 | mapEdge | 14 edge cells; open NE (1) | 109 / 0 | 0 |
| S20 | ReinforcedHydroTurbine | Dam site with 4 layers of natural drop, 93 cells north of the start | 99, 223, 2 | hydro | 4 layers natural drop, source strength 12.0 | 127 / 7 | 0 |
| S21 | WaterTreatmentPlant | Water Treatment Plant, 21 cells south of the start | 98, 115, 2 Cw90 | flat | open NSEW (1) | 13 / 0 | 29 |
| S22 | UraniumProcessingPlant | Uranium Processing Plant, 36 cells south-east of the start | 123, 102, 2 Cw0 | flat | open NSEW (1) | 34 / 5 | 39 |
| S23 | RadioactiveWasteRefinery | Radioactive Waste Refinery, 17 cells north-west of the start | 82, 135, 3 Cw0 | flat | open N (1) | 7 / 0 | 16 |
| S24 | CryogenicLiquefactionPlant | Cryogenic Liquefaction Plant, 33 cells south of the start | 85, 104, 3 Cw90 | flat | open none (1) | 28 / 0 | 44 |
| S25 | MissionControl | Mission Control, 77 cells south of the start | 106, 59, 2 Cw90 | flat | open NSEW (1) | 70 / 0 | 50 |
| S26 | SteelMill | Steel Mill, 70 cells south of the start | 70, 60, 4 Cw0 | flat | open S (1) | 77 / 0 | 33 |
| S27 | DeepProcessor | Deep Processor, 90 cells west of the start | 16, 120, 4 Cw270 | flat | open S (1) | 83 / 0 | 8 |
| S29 | Hospital | Hospital, 77 cells north of the start | 69, 198, 4 Cw0 | flat | open NSEW (1) | 84 / 3 | 15 |
| S30 | ElectrolysisPlant | Electrolysis Plant, 35 cells north-west of the start | 85, 162, 3 Cw180 | flat | open W (1) | 34 / 0 | 39 |
| S31 | PrecisionMachineWorks | Precision Machine Works, 71 cells west of the start | 30, 159, 3 Cw90 | flat | open NW (1) | 78 / 0 | 57 |
| S33 | RadioactiveWasteVault | Radioactive Waste Vault, 81 cells west of the start | 17, 136, 3 Cw0 | flat | open N (1) | 76 / 0 | 7 |
| S34 | FisheryWorks | Fishery Works, 43 cells south-west of the start | 65, 107, 3 Cw90 | flat | open none (1) | 48 / 0 | 28 |
| S35 | TownPlaza | Town Plaza, 77 cells west of the start | 21, 112, 3 Cw0 | flat | open S (1) | 78 / 0 | 33 |
| S36 | MaterialsLaboratory | Materials Laboratory, 89 cells west of the start | 16, 131, 4 Cw270 | flat | open N (1) | 83 / 0 | 9 |
| S37 | RocketAssemblyHangar | Rocket Assembly Hangar, 12 cells east of the start | 109, 137, 2 Cw90 | flat | open S (1) | 4 / 0 | 44 |
| S38 | FoodPackagingWorks | Food Packaging Works, 18 cells west of the start | 80, 132, 5 Cw90 | flat | open N (1) | 13 / 0 | 12 |
| S39 | Restaurant | Restaurant, 30 cells east of the start | 127, 129, 2 Cw0 | flat | open NSEW (1) | 22 / 5 | 12 |
| S41 | TechnicalSchool | Technical School, 53 cells south of the start | 89, 75, 3 Cw0 | flat | open NSEW (1) | 49 / 0 | 22 |
| S42 | FertilizerWorks | Fertilizer Works, 49 cells north-east of the start | 126, 175, 4 Cw90 | flat | open NSEW (1) | 54 / 5 | 0 |
| S43 | GroceryStore | Grocery Store, 55 cells east of the start | 150, 153, 2 Cw90 | flat | open NSEW (1) | 56 / 5 | 0 |
| S45 | Greenhouse | Greenhouse, 48 cells west of the start | 55, 116, 3 Cw90 | flat | open NSEW (1) | 52 / 0 | 15 |
| S46 | OilPowerPlant | Oil Power Plant, 53 cells south-west of the start | 58, 93, 4 Cw0 | flat | open NSEW (1) | 66 / 0 | 6 |
| S47 | CoalPowerPlant | Coal Power Plant, 20 cells south-east of the start | 110, 111, 2 Cw0 | flat | open NSEW (1) | 18 / 0 | 0 |

### Terraces

| # | Object | Label | At (x, y, z) | Details | Route / bridges |
|---:|---|---|---|---|---|
| P1 | DeepOreVein | Lower Basin vein | 169, 114, 3 |  | 121 / 0 |
| P2 | DeepOreVein | Ruin Bench vein | 147, 127, 11 |  | 86 / 0 |
| P3 | DeepOreVein | Upper Bench vein | 112, 164, 11 |  | 33 / 0 |
| P4 | DeepOreSource | Bench source | 126, 136, 9 | 7,000 DeepOre | 59 / 0 |
| P5 | DeepOreSource | Basin Rim source | 152, 106, 11 | 10,000 DeepOre | 115 / 0 |
| P6 | HumanRecordCache | Bench ruins | 149, 155, 11 |  | 64 / 0 |
| P7 | HumanRecordCache | Valley-top ruins | 45, 187, 10 |  | 61 / 5 |
| P8 | LimestoneOutcrop | Limestone Outcrop 1 (Limestone Pit, 12 cells north of the start) | 77, 167, 15 | 600 Limestone | 11 / 0 |
| P9 | LimestoneOutcrop | Limestone Outcrop 2 (Limestone Pit, 12 cells north of the start) | 79, 164, 15 | 600 Limestone | 6 / 0 |
| P10 | LimestoneOutcrop | Limestone Outcrop 3 (Limestone Pit, 12 cells north of the start) | 74, 167, 15 | 600 Limestone | 14 / 0 |
| P11 | SandstoneOutcrop | Sandstone Outcrop 1 (Sandstone Pit, 13 cells east of the start) | 90, 146, 15 | 600 Sandstone | 11 / 0 |
| P12 | SandstoneOutcrop | Sandstone Outcrop 2 (Sandstone Pit, 13 cells east of the start) | 87, 146, 15 | 600 Sandstone | 8 / 0 |
| P13 | SandstoneOutcrop | Sandstone Outcrop 3 (Sandstone Pit, 13 cells east of the start) | 90, 143, 15 | 600 Sandstone | 14 / 0 |
| P14 | LimestoneSeam | Limestone Seam (Limestone Quarry, 92 cells south-east of the start) | 150, 94, 12 |  | 122 / 0 |
| P15 | SandstoneSeam | Sandstone Seam (Sandstone Quarry, 107 cells east of the start) | 179, 114, 3 |  | 131 / 0 |
| P16 | HumanRecordCache | Ruins 93 cells south-east of the start | 144, 86, 15 |  | 127 / 0 |
| P17 | HumanRecordCache | Ruins 49 cells south-west of the start | 42, 123, 12 |  | 63 / 4 |
| P18 | HumanRecordCache | Ruins 91 cells south of the start | 89, 63, 15 |  | 93 / 7 |

| # | Site | Label | At, orientation | Rule | Notes | Route / bridges | Trees |
|---:|---|---|---|---|---|---|---:|
| S1 | NuclearReactor | Western Valley floor (river-side, below the starting terrace) | 36, 161, 6 Cw90 | flat | water 0; open NW (1) | 38 / 4 | 0 |
| S2 | LaunchPad | North-west terrace above the valley | 40, 127, 12 Cw0 | flat | open NSW (2) | 42 / 4 | 46 |
| S3 | LaunchPad | Starting terrace (alternative; highest legal level) | 86, 154, 15 Cw0 | flat | alternative; open NESW (2) | 1 / 0 | 0 |
| S4 | DeepDrill | Bench drill | 131, 139, 9 Cw0 | flat | open NESW (1) | 54 / 0 | 0 |
| S5 | DeepDrill | Basin Rim drill | 155, 102, 11 Cw0 | flat | open NEW (1) | 115 / 0 | 0 |
| S6 | DeepMine | Lower Basin mine | 167, 113, 3 Cw0 | understructure | on DeepOreVein 169, 114, 3; open NESW (1) | 114 / 0 | 0 |
| S7 | DeepMine | Ruin Bench mine | 145, 126, 11 Cw0 | understructure | on DeepOreVein 147, 127, 11; open NESW (1) | 79 / 0 | 0 |
| S8 | DeepMine | Upper Bench mine | 110, 163, 11 Cw0 | understructure | on DeepOreVein 112, 164, 11; open NESW (1) | 30 / 0 | 0 |
| S9 | LimestonePit | Limestone Pit, 12 cells north of the start | 81, 168, 15 Cw90 | pit | 1800 Limestone in range (3 deposits); open NSEW (1) | 6 / 0 | 0 |
| S10 | SandstonePit | Sandstone Pit, 13 cells east of the start | 91, 148, 15 Cw0 | pit | 1800 Sandstone in range (3 deposits); open NSEW (1) | 7 / 0 | 12 |
| S11 | LimestoneQuarry | Limestone Quarry, 92 cells south-east of the start | 147, 93, 12 Cw0 | understructure | on LimestoneSeam 150, 94, 12; open NSEW (1) | 118 / 0 | 0 |
| S12 | SandstoneQuarry | Sandstone Quarry, 107 cells east of the start | 178, 121, 3 Cw90 | understructure | on SandstoneSeam 179, 114, 3; open NSEW (1) | 127 / 0 | 0 |
| S13 | ArchiveExcavation | Archive Excavation for Bench ruins | 136, 152, 13 Cw0 | flat | open NEW (1) | 51 / 0 | 15 |
| S14 | ArchiveExcavation | Archive Excavation for Valley-top ruins | 51, 191, 8 Cw0 | flat | open E (1) | 52 / 5 | 0 |
| S15 | ArchiveExcavation | Archive Excavation for Ruins 93 cells south-east of the start | 131, 89, 15 Cw0 | flat | open N (1) | 104 / 0 | 23 |
| S16 | ArchiveExcavation | Archive Excavation for Ruins 49 cells south-west of the start | 42, 111, 12 Cw0 | flat | open SE (1) | 61 / 4 | 9 |
| S17 | ArchiveExcavation | Archive Excavation for Ruins 91 cells south of the start | 93, 67, 10 Cw0 | flat | open NE (1) | 85 / 7 | 4 |
| S18 | FishHatchery | Fish Hatchery, 57 cells north-east of the start | 121, 195, 6 Cw90 | waterDepth | compact 7x7, no Dynamite; surface 0.51 above the work cells, work cell 0 (the native sample) 0.00, the far pens 0.11 / 0.25 (mixing edge); alternative 128, 193, 6 Cw270 with two one-layer charges keeps all four pens at 0.00 | 72 / 5 | 0 |
| S19 | RadioactiveSludgeRecoveryPump | Radioactive Sludge Recovery Pump, 77 cells south-west of the start | 30, 97, 13 Cw90 | waterInput | intake floor 12 | 104 / 4 | 0 |
| S20 | RadioactiveWasteExport | Radioactive Waste Export, 79 cells west of the start | 0, 148, 6 Cw0 | mapEdge | 14 edge cells; open NSE (1) | 86 / 4 | 6 |
| S21 | ReinforcedHydroTurbine | Dam site with 5 layers of natural drop, 151 cells east of the start | 224, 201, 5 | hydro | 5 layers natural drop, source strength 39.5 | 186 / 4 | 0 |
| S22 | WaterTreatmentPlant | Water Treatment Plant, 28 cells north of the start | 67, 176, 15 Cw0 | flat | open NSEW (1) | 19 / 5 | 35 |
| S23 | UraniumProcessingPlant | Uranium Processing Plant, 62 cells north-west of the start | 37, 197, 9 Cw0 | flat | open NSEW (1) | 70 / 5 | 0 |
| S24 | RadioactiveWasteRefinery | Radioactive Waste Refinery, 94 cells north of the start | 91, 242, 14 Cw0 | flat | open NSEW (1) | 90 / 5 | 0 |
| S25 | CryogenicLiquefactionPlant | Cryogenic Liquefaction Plant, 88 cells north of the start | 50, 244, 11 Cw90 | flat | open NSEW (1) | 94 / 5 | 0 |
| S26 | MissionControl | Mission Control, 55 cells north-east of the start | 104, 197, 6 Cw0 | flat | open NSEW (1) | 58 / 5 | 27 |
| S27 | SteelMill | Steel Mill, 78 cells west of the start | 1, 172, 10 Cw0 | flat | open NSEW (1) | 81 / 5 | 28 |
| S28 | DeepProcessor | Deep Processor, 59 cells north-east of the start | 130, 174, 15 Cw0 | flat | open NSEW (1) | 61 / 0 | 29 |
| S30 | Hospital | Hospital, 56 cells east of the start | 130, 162, 13 Cw0 | flat | open NSEW (1) | 49 / 0 | 11 |
| S31 | ElectrolysisPlant | Electrolysis Plant, 76 cells north of the start | 103, 221, 14 Cw0 | flat | open NSEW (1) | 81 / 5 | 31 |
| S32 | PrecisionMachineWorks | Precision Machine Works, 62 cells south of the start | 86, 98, 7 Cw90 | flat | open NSEW (1) | 59 / 7 | 0 |
| S34 | RadioactiveWasteVault | Radioactive Waste Vault, 84 cells south of the start | 105, 70, 10 Cw0 | flat | open NSEW (1) | 93 / 7 | 27 |
| S35 | FisheryWorks | Fishery Works, 70 cells west of the start | 9, 145, 3 Cw90 | flat | open NSEW (1) | 72 / 4 | 0 |
| S36 | TownPlaza | Town Plaza, 80 cells north-west of the start | 35, 218, 16 Cw0 | flat | open NSEW (1) | 96 / 5 | 17 |
| S37 | MaterialsLaboratory | Materials Laboratory, 66 cells south of the start | 100, 96, 5 Cw90 | flat | open NSEW (1) | 71 / 7 | 0 |
| S38 | RocketAssemblyHangar | Rocket Assembly Hangar, 39 cells north-east of the start | 92, 193, 6 Cw90 | flat | open NSEW (1) | 35 / 5 | 0 |
| S39 | FoodPackagingWorks | Food Packaging Works, 30 cells north-east of the start | 102, 176, 11 Cw90 | flat | open NSEW (1) | 26 / 0 | 0 |
| S40 | Restaurant | Restaurant, 19 cells west of the start | 59, 158, 16 Cw90 | flat | open NSEW (1) | 14 / 0 | 18 |
| S42 | TechnicalSchool | Technical School, 21 cells east of the start | 100, 163, 15 Cw90 | flat | open NSEW (1) | 15 / 0 | 13 |
| S43 | FertilizerWorks | Fertilizer Works, 34 cells south of the start | 74, 118, 10 Cw0 | flat | open NSEW (1) | 66 / 0 | 1 |
| S44 | GroceryStore | Grocery Store, 66 cells east of the start | 143, 172, 13 Cw90 | flat | open NSEW (1) | 64 / 0 | 9 |
| S46 | Greenhouse | Greenhouse, 62 cells east of the start | 135, 129, 11 Cw0 | flat | open NSEW (1) | 72 / 0 | 23 |
| S47 | OilPowerPlant | Oil Power Plant, 18 cells south of the start | 80, 134, 15 Cw0 | flat | open NSEW (1) | 13 / 0 | 0 |
| S48 | CoalPowerPlant | Coal Power Plant, 19 cells east of the start | 97, 147, 15 Cw0 | flat | open NSEW (1) | 13 / 0 | 23 |

## Human-history evidence

`docs/story.md` defines the **Human Record Cache** (`MapEditor/Objects/HumanRecordCache`). `tools/narrative_content.mjs` clones it from the vanilla MediumRelic (3×2×1) and adds it to `TemplateCollection.MapEditor.Common`; the validator fails if its BlockObjectSpec stops matching MediumRelic.

Every map now places five caches, one per "Record Cache" discovery (`CachesSurveyed` 1–5 in `DeepFrontierNarrative`).

- Each cache stands beside vanilla ruins.
- Each has its own checked Archive Excavation site (10×9×11) whose occupied cells are within the cache's survey radius: 4 tiles Chebyshev and 4 layers (`HumanRecordCache.Distance`).
- The cache saves its survey state only once a survey starts, so a placed cache needs only `BlockObject`.

## Water, treatment and contamination

Default variants keep the vanilla water: no source is added, removed or changed. Every map provides river or lake water for the PureWater → ReactorCoolantWater chain, and badwater for Extract, Explosives and Chemical.

- **Plains**
  - Water sources: north edge (107–110, 255; 4 × 0.25), north-east river head (247, 243–246; 4 × 0.5) and south-east (250, 15–17; 3 × 0.5).
  - Badwater sources: (185, 62; 0.75) and (38, 226; 1.0).
  - The rivers converge north of the start into the central lake, which drains off the west edge. The south-east badwater river enters the lake from the south. Flow directions are read from the terrain and the saved water, not simulated.
  - The North Bank reactor draws coolant from the north river and lake.
  - The start river is 0.32 deep in the saved water, below shore fishing's 0.5. Dam it, or fish from the north banks (route 105).
- **Lakes**
  - Water sources: north-west (10, 239–243; strength 4 in total) and north (106, 239–241; 3), plus a seep at (25, 98).
  - Badwater sources: east plateau (170, 132; 1.0), south-west (59, 65; 1.5) and north (165, 231; 1.0).
  - The lake chain runs from the north lakes through the central lake to the south-east lake. Reactor Island stands on that chain.
- **Terraces**
  - Water sources: starting terrace (59–60, 145; 2), (20–21, 234), (209–211, 195), (153–157, 254) and (185, 89–91).
  - Badwater sources: (46, 69), (67, 54), (200, 209) and (179, 162); the badwater mixes into most rivers (0.26–0.35 at the hatchery-shaped reaches).
  - The valley reactor stands on the river that drains the starting terrace.

Contamination stays a consequence of play. Radioactive water comes from reactor waste, meltdowns and dumping, and from the optional radioactive tide (`docs/radiation.md`). The tide makes 0.1 radioactive water per hour per unit of source strength at every native water source, so on these maps it enters at the river heads listed above. It then runs past downstream farmland and the reactor intakes; pumps refuse to run when radiation reaches their intake.

**Hard variant**

- One `RadioactiveSpringSource`, **0.2 radioactive water per hour** (default 0.5), on the dry bank at 240,246,9. It is a native water source, saved with native strength 0.2 / 19.2 ≈ 0.0104.
- It is one cell from the head of the north-east river and about 7 cells downstream of that river's sources, roughly 210 route cells from the start.
- Its radioactive water (about 4.8 units per day, the radioactive content of 24 RadioactiveSludge goods) is expected to follow the river along the north edge of the start island into the central lake and the western outflow. This must be confirmed in game.
- The map name and description say HARD.

## Validation (static)

`build` writes each map, re-reads it from disk and runs the same validator as `validate`. All four variants pass with **0 errors**.

- **Archive.** Entries, version and source.
  - Exactly `map_metadata.json`, `map_thumbnail.jpg`, `version.txt` and `world.json`.
  - The source SHA-256 matches the recorded value.
  - `version.txt` and `GameVersion` equal the source (`0`).
  - Every singleton is unchanged after the height resize.
  - The source bytes are preserved up to the end of the original entities, and every source entity is unchanged.
  - Exactly one new entity is added per placement, with deterministic UUIDv5 ids.
  - `MapHeight` equals the variant's height.
- **Placements.**
  - Every placed template is in `TemplateCollection.MapEditor.Common` and has its blueprint file.
  - For each block:
    - inside the map;
    - occupied z < 66;
    - not inside terrain;
    - not in water;
    - not overlapping any existing object, tree or other placement, including `OccupyAllBelow` columns;
    - matter below satisfied;
    - the `ContinuousTerrainConstraint` of veins and seams holds.
  - Every placement except the spring has a route from the start.
  - Stockpiles:
    - the good is consumed by a DeepDrill recipe (`DeepOre`) and is of the whitelisted type `Pileable`;
    - the amount is at most the source's `StockpileSpec.MaxCapacity` (10,000 since 2026-10-30; 4,000 before);
    - the entrance cell is dry, free ground.
  - Outcrops save the blueprint yield.
  - A spring only in `hardVariant`, which also requires one; it must be next to a river cell at or below its level.
- **Sites.** Every site's template must be a building that needs one; the keys are checked per rule.
  - Flat-type sites (flat, understructure, pit, map edge):
    - footprint flat, dry, on the first terrain column and free of non-removable objects and placements;
    - top occupied z < 66;
    - listed open sides verified;
    - door approach free and routable.
  - Reactor: water within `maxWaterDistance`.
  - Understructure: core on the understructure.
  - Pits: deposits in range.
  - Map edge: an occupied block on the edge.
  - Waterside sites: native block rules with trees allowed, the declared Dynamite cells applied, work cells or intake water, and the door approach.
  - Dam sites: a wet, source-fed cell with natural head.
  - Primary sites don't overlap. No primary footprint covers another site's door approach or a listed open margin.
- **Full-loop coverage.** The eight stages of the requirement matrix. The evidence lists each item with its value and threshold (`loopCoverage.stages`), plus the start-resource survey, cache coverage and the raw-material program.
- **Description.** It names Deep Frontier and all 16 required mods from the manifest.
- **Compatibility.** All four files open with .NET `System.IO.Compression.ZipFile`, the API family the game's `SaveReader` uses.
- **Negative tests** (`tools/test_prepare_deep_frontier_map.py`, 17 cases on Plains, all caught; builds go to a temporary folder). Each injected fault fails with the expected error:
  - no sandstone outcrops;
  - a pit away from its outcrops;
  - no limestone seam;
  - a quarry on the wrong seam;
  - the export off the map edge;
  - a cache without an excavation site;
  - only four caches;
  - the hatchery off the water;
  - overlapping sites;
  - a footprint in an open margin;
  - a Dynamite cell outside the site footprint (replaces "the sludge pump without its Dynamite": Plains lists no Dynamite any more);
  - finite deep ore too small;
  - a dam site on dry land;
  - one vein only;
  - no steel mill site;
  - an outcrop over water;
  - a site for a building that needs none.

  The older harness cases (vein in water, wrong good, over capacity, mine off its vein, reactor too far from water, spring in a default variant, template outside the collection) are still enforced by the same code paths.

## In-game proof (written offline, not run)

`tools/start_map_loop_test.ps1 -Label <label> [-Variants plains,plains-hard,lakes,terraces]` starts one new Iron Teeth game per map through the acceptance loader. It runs `src/DeepFrontier/Scripts/MapLoopAcceptance.cs` (`-deepFrontierMapLoop`), which never saves. It needs a build that contains the script, the game closed and the user present: the startup dialogs need clicking.

1. **Contract.** It reads `outputs/maps/<id>-validation.json` for the loaded map, requires 0 static errors, and checks that the map file's SHA-256 equals `outputSha256`.
2. **Placements.** Each placement is registered at its coordinates and orientation, so it survived load validation. Ore sources hold their DeepOre, outcrops yield 600, and caches are unsurveyed.
3. **Sites.**
   - It removes trees in each footprint and lowers the listed Dynamite cells (`ITerrainService.UnsetTerrain`), then lets the water settle for 600 frames.
   - A native preview (`PreviewFactory`) at `nativePlacement` must pass `BlockValidator` and every `IBlockObjectValidator`: understructure, map edge, adaptive supports.
   - Hatchery work cells must be in clean water 0.2–7 deep, the pump intake column must hold water, and dam sites must be wet.
4. **Pits.** Each pit is built finished. Its native `InRangeYielders` must list the deposits the static check found in range.

Results go to `outputs/map-loop-<label>-<id>.json`. The script compiles against the installed game DLLs (a scratch copy of `outputs/all-buildings-compile/AllBuildingsCompile.csproj`), and `validate_editor_guards`, `validate_component_lifecycle` and `validate_priority_statuses` pass. It has not been built into the mod or run.

## Must be checked in game

The user must be present for these.

1. **New-game list.** Each map appears with its file name and description, and starts as Iron Teeth with Deep Frontier, Map Transformer and the other dependencies enabled.
2. **`tools/start_map_loop_test.ps1`** on all four maps. This covers loading (no "Can't validate loaded BlockObject"), every placement and every site.
3. **Map editor.** Open each map in the map editor:
   - the Deep Ore Sources show 4,500–10,000 DeepOre and the outcrops 600;
   - the vein, seam, cache, outcrop and spring models sit on the ground;
   - the spring's native strength row shows about 0.0104.
4. **Production on the sites.**
   - A Deep Drill drains a source; a Deep Mine runs on a vein; both quarries run on their seams.
   - Pits collect their outcrops.
   - An Archive Excavation surveys its cache, and the journal records it.
   - The hatchery runs on its site; the Terraces site needs its Dynamite first.
5. **Reactor and launch pad** at their sites: placement, camera and models.
6. **Flooding.** Watch the low-freeboard sites through wet seasons and badtides: Lakes reactor 0.43 and pad 0.33; Plains pad 0.35; Terraces reactor 0.58.
7. **Hard variant.** Sludge from the spring reaches the river and drifts downstream at a manageable rate.
8. **Radioactive tide.** On one map, force a tide (dev mode). Check where sludge pools relative to farms and the reactor intakes.
9. **Save and reload.** A started colony on each map preserves source stock, outcrop yield, vein, seam, cache and spring state.

## Follow-ups

- **Sludge Recovery Pump intake geometry.** Needs a decision by the building owner (see Building-side findings).
- **Other built-in maps.** Done: every built-in map has a default variant (see "Built-in maps: new-game setup").
- **Map object art.** Another agent is redesigning the visuals of the vein, source, seams, spring, cache and ore goods. The tool reads ids and footprints from the blueprints. After an id or footprint change, rerun `build`; then rerun `plan` for anything it reports.
