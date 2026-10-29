# Building sounds

Status 2026-10-22: data and generation integrated, checked in a scratch copy of the repository. Nothing has been built, installed or heard in game. `tools/STATUS.md` remains the record of runtime verification.

- Choices: `tools/building_sounds.json`. One entry for every Deep Frontier building template under `src/DeepFrontier/Data/Buildings`, plus the two radioactive spring placements. Each entry's `comment` gives the reason for the choice.
- Applier: `tools/building_sounds_content.mjs`. It runs in canonical generation (`tools/create_vertical_slice_content.mjs`) after radiation, workforce risks and smog, and before the automation audit.
- Validator: `node tools/validate_building_sounds.mjs [--root <repo>] [--game <Timberborn_Data>]`.

## How 1.1.2.8 plays building sounds (source-confirmed)

Evidence: decompiled `Timberborn.Buildings`, `Timberborn.SoundSystem`, `Timberborn.CoreSound`, `Timberborn.WorkshopsEffects`, `Timberborn.PowerGeneration`, `Timberborn.EnterableSystem`, `Timberborn.Attractions`, `Timberborn.DwellingSystem`, `Timberborn.RangedEffectSystem`, `Timberborn.GameWaterSourceSystem` and `Timberborn.ModularShafts` from game 1.1.2.8-ffc2de0-xsw.

**Registry.** `AudioClipService.LoadAudioClips` loads every `AudioClip` under the `Sounds` resources key and stores it by exact `name`. `GetAudioClipNames(x)` returns the clip named `x` plus any `x_<suffix>` variants, and `Sounds` plays a random variant. A name with no clip throws `ArgumentException("No sound files for: ...")` the first time it plays. A wrong name in a blueprint is a runtime error, not silence.

**Selection.** `BuildingSelectionSound.OnSelect` plays the 2D sound `UI.Buildings.Selected.<BuildingSpec.SelectionSoundName>` on the UI mixer. An unfinished building always plays `Default`. The spec default is also `Default`.

**Loop.** `BuildingSounds` plays `Environment.Buildings.Loop.<BuildingSpec.LoopingSoundName>` as a 3D loop. It uses priority 128 and the building mixer, and is offset from the block-object centre. An empty name means no loop. `LoopingSoundPlayer` starts after a random delay of up to 0.5 s and fades in. Stopping fades out over three seconds, and the source stays `isPlaying` at zero volume; see the turbine reload 103 notes.

`BuildingSounds` never starts itself. A loop plays only when one of these components calls `ToggleSound`:

| Spec on the template | Component | Loop plays while |
|---|---|---|
| `WorkshopSpec` | `Workshop` → `WorkshopSounds` (ticks) | `Workshop.CurrentlyWorking` |
| `PowerGeneratorSoundsSpec` | `PowerGeneratorSounds` (ticks) | `MechanicalNode.ActiveAndPowered && OutputMultiplier > 0` |
| `AttractionSpec` | `Attraction` → `EnterableSounds` (events) | anyone is inside |
| `DwellingSpec` | `Dwelling` → `EnterableSounds` (events) | anyone is inside |
| `RangedEffectBuildingSpec` | `RangedEffectBuilding` (on change) | finished, unpaused and the power graph is powered; staffing and stock are not checked |
| `UndergroundWaterSourceDrillSpec` | `UndergroundWaterSourceDrillSounds` | the drilled water source's strength is above 0 |

No 1.1.2.8 component plays a building loop all the time. A template with a loop name and no driver is silent. Two drivers on one template toggle the same `BuildingSounds` against each other. The ticking driver wins on the next tick, so the other one causes start-then-fade blips. The applier therefore requires exactly the declared driver whenever a loop is set.

**Basic selection.** Objects without a `BuildingSpec`, such as natural resources and water sources, use `BasicSelectionSoundSpec`. They play `UI.BasicSelection.<SoundName>`, or `<AlternativeSoundName>.AltSound` 10% of the time when an alternative is set.

**Other sound specs found in vanilla blueprints.** None of these is used for building identity:
- `PowerGeneratorSoundsSpec` (empty marker) appears on 8 vanilla generators: water wheels, wind turbines, both geothermal engines and the steam engine.
- `ShaftSoundEmitterSpec` (empty marker) appears on 4 power shafts. `ShaftSoundController` plays one area sound, `Environment.Buildings.ShaftWorking`, for animated shafts.
- `BotSelectionSoundSpec.SoundNameKey`: Ironbot, Timberbot.
- `SpeakerSoundSpec.SoundId`: speaker alarm, buzz and two chimes.
- `FireworkSpec.TrailSound` and `BurstSound`.
- `ActivationWarningStatusSpec.WarningSound`: water and badwater sources, unstable core.
- `GameUISoundSpec` weather and wonder keys, `FactionSpec.SoundId`, `FactionWonderSpec.WonderLaunchSound`.
- `CoreSoundSpec`: fade distances and the wind ambient key.

## Inventory

All 1,067 vanilla blueprints under `vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources` were scanned, BOM-prefixed files included. The registry lists the shipped clips: `AudioClip.m_Name` read from `Timberborn_Data/resources.assets` with the project's UnityPy 1.25.4, cross-checked against the lowercase Resources container paths in `globalgamemanagers`. `--game` repeats that container check. Every name used by a vanilla blueprint is in the registry.

Six shipped clips are used by no 1.1 blueprint: the selections BuilderFlag, DirtPile, TerraformingStation and WateringPlace, the WateringPlace loop, and the basic selection Default. Deep Frontier does not use them.

Loop characters were measured from the decoded clips (FMOD via `tools/asset-pipeline/unitypy/fmod_toolkit`) and are not a listening test:
- band energy: one-pole filters at 150, 600 and 2,500 Hz;
- onsets per second: 20 ms frames with a threefold energy jump;
- envelope periodicity.

Selection descriptions are inferred from the vanilla buildings that use each sound.

### Looping sounds (`Environment.Buildings.Loop.<name>`), 15 clips

| Name | Length | Vanilla users | Measured character |
|---|---|---|---|
| Agora | 29.6 s | Agora (FT) | Crowd murmur, mid-band and broadband, 1.3 onsets/s. |
| Bakery | 5.6 s | Bakery (FT) | Steady low oven or burner roar: 63% of energy below 150 Hz, 0.5 onsets/s. |
| Carousel | 13.7 s | Carousel (FT) | Fairground music, periodic. |
| DanceHall | 30.8 s | DanceHall (FT), DancePit (IT) | Quiet dance music, strongly modulated. |
| GearWorkshop | 19.4 s | EfficientMine (IT), GearWorkshop, Mine (FT) | Metallic clatter: high band, 4.6 onsets/s. |
| Grill | 5.6 s | CoffeeBrewery (IT), FoodFactory (IT), Grill (FT) | Low fire roar with crackle: 73% below 150 Hz, 3 onsets/s. |
| Gristmill | 6.5 s | Fermenter (IT), Gristmill (FT), LargeWindTurbine (FT), WindTurbine (FT) | Creaking millstone grind: broadband, 3.2 onsets/s. |
| Inventor | 9.1 s | Inventor, OilPress (IT) | Quiet bench tinkering: broadband, about 1 onset/s, 3 s cycle. |
| LumberMill | 17.4 s | IndustrialLumberMill (IT), LumberMill (FT), WoodWorkshop | Saw: high band, 6.3 onsets/s. |
| PaperMill | 7.5 s | Centrifuge, GeothermalEngine, PaperMill (FT) | Steady mid/high whir or churn: 31% at 600 Hz-2.5 kHz, few onsets. |
| PrintingPress | 26.6 s | ExplosivesFactory, PrintingPress (FT), SteamEngine (IT) | Heaviest loop: deep continuous throb, 79% below 150 Hz, 1.65 s pulse. |
| TributeToIngenuity | 17.3 s | TributeToIngenuity (IT) | Mechanical whir and chime cycle: mid band, 2 s period. |
| WaterPump | 8.0 s | BadwaterPump (FT), DeepBadwaterPump (IT), DeepWaterPump (IT), LargeWaterPump (FT), WaterPump (FT) | Rhythmic pump strokes: mid band, strongly periodic (0.78). |
| WaterWheel | 16.5 s | AncientAquiferDrill, AquiferDrill, CompactWaterWheel (IT), FountainOfJoy (FT), HydroponicGarden (IT), LargePowerWheel (IT) and 3 more | Steady water rush with wheel: 55% below 150 Hz. |
| WateringPlace | 7.9 s | none | Very quiet water lapping; no 1.1 blueprint uses it. |

### Selection sounds (`UI.Buildings.Selected.<name>`), 100 clips

| Name | Vanilla users | Description (inferred from users) |
|---|---|---|
| AdvancedBreedingPod | AdvancedBreedingPod (IT) | Advanced breeding pod: bubbling vat machine. |
| Agora | Agora (FT) | Social plaza: crowd murmur. |
| AquaticFarmhouse | AquaticFarmhouse (FT) | Aquatic farm: water farming. |
| AquiferDrill | AncientAquiferDrill, AquiferDrill | Drill rig boring into an aquifer: rhythmic drilling thump. |
| Automation | Chronometer, ContaminationSensor, DepthSensor, Detonator, FlowSensor, HttpAdapter and 12 more | Sensors, levers, relays and gauges: small mechanical click. |
| BadwaterDome | BadwaterDome (FT) | Badwater dome: toxic-water machinery. |
| BadwaterPressurizer | BadwaterPressurizer (IT) | Badwater source regulator: deep pressurised thump. |
| BadwaterRig | BadwaterRig (FT) | Badwater extraction rig. |
| Bakery | Bakery (FT) | Bakery. |
| Beehive | Beehive (FT) | Bees. |
| Bell | Bell (IT) | Bell. |
| BotAssembler | BotAssembler | Bot assembler: assembling bots from parts. |
| BotPartFactory | BotPartFactory | Bot part factory: making bot parts. |
| Brazier | Brazier (IT) | Fire brazier. |
| BreedingPod | BreedingPod (IT) | Breeding pod: gurgling vat, mostly low frequencies. |
| BuilderFlag | none | Builder flag; no 1.1 blueprint uses it. |
| BuildersHut | BuildersHut | Builders' hut: construction tools. |
| Campfire | Campfire | Campfire crackle. |
| Carousel | Carousel (FT) | Carousel. |
| Centrifuge | Centrifuge | Centrifuge (badwater to extract): spinning water-processing machine. |
| ChargingStation | ChargingStation (IT) | Bot charging station: electrical. |
| CoffeeBrewery | CoffeeBrewery (IT) | Coffee brewery: brewing. |
| ContemplationSpot | ContemplationSpot (FT) | Contemplation spot: calm. |
| ControlTower | ControlTower (IT) | Bot control tower: signals and radio. |
| DanceHall | DanceHall (FT) | Dance hall: music. |
| DecontaminationPod | DecontaminationPod (IT) | Decontamination pod. |
| DecorativeClock | DecorativeClock (IT) | Decorative clock: ticking. |
| Default | Airlock, BeaverBust (IT), BeaverStatue, Bench, BulletinPole (FT), ContaminationBarrier (FT) and 46 more | Generic thud. Used by platforms, levees, dams, overhangs, roofs and decorations, and played by every unfinished building. |
| Detailer.Folktails | Detailer (FT) | Folktails detailer (decoration). |
| Detailer.IronTeeth | Detailer (IT) | Iron Teeth detailer (decoration). |
| DirtExcavator | DirtExcavator | Dirt excavator: digging. |
| DirtPile | none | Dirt pile; no 1.1 blueprint uses it. |
| Discharge | Discharge | Discharge outlet: water release. |
| DistrictCenter | DistrictCenter | District centre. |
| DistrictCrossing | DistrictCrossing | District crossing. |
| Dynamite | DoubleDynamite, Dynamite, TripleDynamite, Tunnel | Dynamite and tunnels: fuse. |
| EarthRecultivator | EarthRecultivator (FT) | Folktails wonder. |
| EarthRepopulator | EarthRepopulator (IT) | Iron Teeth wonder. |
| Engine | SteamEngine (IT) | Steam Engine: steam and pistons, heavy and low. |
| ExercisePlaza | ExercisePlaza (IT) | Exercise plaza. |
| ExplosivesFactory | ExplosivesFactory | Explosives factory. |
| Farmhouse | EfficientFarmHouse (FT), FarmHouse (IT) | Farmhouses. |
| Fermenter | Fermenter (IT) | Fermenter: vats. |
| FlameOfProgress | BrazierOfBonding (FT), FlameOfUnity (IT) | Fire monuments. |
| Floodgate | DoubleFloodgate, FillValve, Floodgate, ThrottlingValve, TripleFloodgate | Floodgates and valves: gate mechanism and water. |
| FoodFactory | FoodFactory (IT) | Iron Teeth food factory: industrial food processing. |
| Forester | Forester | Forester: planting. |
| GathererFlag | GathererFlag | Gatherer flag. |
| GearWorkshop | GearWorkshop | Gear workshop: metal gear work. |
| GeothermalEngine | GeothermalEngine | Geothermal engine: deep pressurised rumble. |
| GravityBattery | GravityBattery | Gravity battery: heavy weight. |
| GreaseFactory | GreaseFactory (IT) | Grease factory (makes grease): viscous chemical process. |
| Grill | Grill (FT) | Grill: short sizzle. |
| Gristmill | Gristmill (FT) | Gristmill: millstones. |
| HallOfAbundance | ArchOfProgress (IT), HallOfAbundance (FT) | Wonders and monuments. |
| HaulingPost | HaulingPost | Hauling post. |
| Herbalist | Herbalist (FT) | Herbalist (makes medicine). |
| HydroponicGarden | HydroponicGarden (IT) | Hydroponic garden: water and plants. |
| Inventor | Inventor | Inventor: tinkering. |
| LaborerMonument | FarmerMonument (FT), LaborerMonument (IT) | Monuments. |
| Lido | Lido (FT), SwimmingPool (IT) | Lido and swimming pool: splashing. |
| Lodge | Barrack (IT), DoubleLodge (FT), LargeBarrack (IT), LargeRowhouse (IT), Lodge (FT), MiniLodge (FT), Rowhouse (IT), TripleLodge (FT) | Housing. |
| LumberMill | IndustrialLumberMill (IT), LumberMill (FT) | Lumber mills: saw. |
| LumberjackFlag | LumberjackFlag | Lumberjack flag: axe. |
| MechanicalPump | DeepMechanicalPump (IT), MechanicalPump (FT) | Mechanical pumps. |
| MedicalBed | MedicalBed | Medical bed. |
| Mine | EfficientMine (IT), Mine (FT) | Mines: rock and pick. |
| Motivatorium | Motivatorium (IT) | Motivatorium. |
| MudBath | MudBath (IT) | Mud bath. |
| MudPit | DancePit (IT), MudPit (FT) | Mud pit and dance pit. |
| Numbercruncher | Numbercruncher (IT) | Numbercruncher (Iron Teeth science machine). |
| Observatory | Observatory (FT) | Observatory (Folktails science). |
| OilPress | OilPress (IT) | Oil press. |
| PaperMill | PaperMill (FT) | Paper mill. |
| Pile | LargeIndustrialPile (IT), LargePile (FT), ReservePile, SmallIndustrialPile (IT), SmallPile (FT), UndergroundPile (FT) | Piles: stacking goods. |
| PowerWheel | LargePowerWheel (IT), PowerWheel (FT) | Treadwheels. |
| PrintingPress | PrintingPress (FT) | Printing press. |
| Refinery | Refinery (FT) | Biofuel and catalyst refinery: industrial liquids. |
| ScavengerFlag | ScavengerFlag | Scrap scavenger flag. |
| Scratcher | Massager (IT), Scratcher (IT) | Scratcher and massager. |
| Shaft | Clutch, PowerShaft, VerticalPowerShaft | Power shafts and clutch. |
| Shower | DoubleShower (IT), Shower (FT) | Showers. |
| Smelter | Metalsmith (IT), Smelter | Smelter and metalsmith: furnace and metal. |
| StreamGauge | StreamGauge | Stream gauge. |
| Tank | LargeTank, MediumTank, ReserveTank, SmallTank | Liquid tanks. |
| TappersShack | TappersShack | Tappers' shack. |
| TeethGrindstone | TeethGrindstone | Teeth grindstone. |
| TerraformingStation | none | Terraforming station; no 1.1 blueprint uses it. |
| TributeToIngenuity | FountainOfJoy (FT), TributeToIngenuity (IT) | Tribute to Ingenuity and Fountain of Joy monuments. |
| Tubeway | ImpermeableTubeway (IT), Tubeway (IT), VerticalTubeway (IT) | Tubeways. |
| TubewayStation | TubewayStation (IT) | Tubeway station. |
| Warehouse | LargeWarehouse, MediumWarehouse, ReserveWarehouse, SmallWarehouse | Warehouses: crates. |
| WaterPump | BadwaterPump (FT), DeepBadwaterPump (IT), DeepWaterPump (IT), LargeWaterPump (FT), WaterPump (FT) | Water pumps. |
| WaterWheel | CompactMechanicalPump, CompactWaterWheel (IT), LargeWaterWheel (IT), WaterWheel (FT) | Water wheels and the compact mechanical pump: water and a wooden wheel. |
| WateringPlace | none | Watering place; no 1.1 blueprint uses it. |
| WindTunnel | WindTunnel (IT) | Wind tunnel: fan and air rush. |
| WindTurbine | LargeWindTurbine (FT), WindTurbine (FT) | Wind turbines. |
| WoodWorkshop | WoodWorkshop | Wood workshop. |
| ZiplinePylon | ZiplineBeam (FT), ZiplinePylon (FT) | Zipline pylon and beam. |
| ZiplineStation | ZiplineStation (FT) | Zipline station. |

### Basic selection sounds (`UI.BasicSelection.<name>`), 14 clips

| Name | Vanilla users | Description |
|---|---|---|
| Aquifer | Aquifer | Aquifer. |
| BadwaterSource | BadtideDrain, BadwaterSeep, BadwaterSource | Badwater source, seep and badtide drain: toxic water. |
| Blockage | Blockage, NaturalDam | Blockage and natural dam. |
| Bush | BlueberryBush, Canola, Carrot, Cassava, Cattail, CoffeeBush and 9 more | Crops and bushes. |
| Default | none | Fallback; no blueprint uses it. |
| GeothermalField | GeothermalField | Geothermal field. |
| Relic | LargeRelic, MediumRelic, SmallRelic | Relics. |
| Ruin | RuinColumnH1, RuinColumnH2, RuinColumnH3, RuinColumnH4, RuinColumnH5, RuinColumnH6, RuinColumnH7, RuinColumnH8 | Ruin columns. |
| Thorns | Thorns | Thorns. |
| Tree | Birch, ChestnutTree, Mangrove, Maple, Oak, Pine, Succulent | Trees. |
| UndergroundRuin | UndergroundRuins | Underground ruins. |
| UnstableCore | UnstableCore | Unstable core. |
| WaterCrop.AltSound | Cattail (10% alt), Spadderdock (10% alt) | 10% alternative for cattail and spadderdock. |
| WaterSource | DevWaterSource, WaterSeep, WaterSource | Water source, seep and dev water source. |

## Deep Frontier choices

Reasons for each choice are in the `comment` fields of `tools/building_sounds.json`.

| Building | Selection | Loop | Loop plays while | Family |
|---|---|---|---|---|
| NuclearReactor | Engine | PrintingPress | workshop working | steam/generator |
| ReinforcedHydroTurbine | WaterWheel | Gristmill | generating | steam/generator |
| DeepDrill | AquiferDrill | GearWorkshop | workshop working | mining |
| DeepMine | Mine | GearWorkshop | workshop working | mining |
| SandstoneQuarry | Mine | GearWorkshop | workshop working | mining |
| LimestoneQuarry | Mine | GearWorkshop | workshop working | mining |
| SandstonePit | DirtExcavator | none | never (no loop) | mining |
| LimestonePit | DirtExcavator | none | never (no loop) | mining |
| DeepProcessor | Smelter | Grill | workshop working | furnace/smelter |
| CementKiln | Smelter | Grill | workshop working | furnace/smelter |
| ChemicalWorks | GreaseFactory | Bakery | workshop working | furnace/smelter |
| UraniumProcessingPlant | Smelter | PaperMill | workshop working | furnace/smelter |
| StoneCrusher | Mine | Gristmill | workshop working | mining |
| ConcreteMixer | Centrifuge | PaperMill | workshop working | pump/water |
| PrecisionMachineWorks | BotPartFactory | GearWorkshop | workshop working | gear/workshop |
| RocketAssemblyHangar | BotAssembler | GearWorkshop | workshop working | gear/workshop |
| WaterTreatmentPlant | MechanicalPump | WaterPump | workshop working | pump/water |
| ElectrolysisPlant | ChargingStation | WaterPump | workshop working | pump/water |
| CryogenicLiquefactionPlant | Tank | PaperMill | workshop working | pump/water |
| RadioactiveWasteRefinery | DecontaminationPod | WaterPump | workshop working | pump/water |
| RadioactiveWasteExport | Discharge | WaterPump | workshop working | pump/water |
| RadioactiveSludgeOutfall | Discharge | WaterPump | workshop working | pump/water |
| RadioactiveSludgeRecoveryPump | WaterPump | WaterPump | workshop working | pump/water |
| RadioactiveWasteVault | Warehouse | none | never (no loop) | storage |
| LaunchPad | GeothermalEngine | PaperMill | workshop working | steam/generator |
| MissionControl | ControlTower | Inventor | workshop working | civic/service |
| TechnicalSchool | Numbercruncher | Inventor | workshop working | civic/service |
| MaterialsLaboratory | Inventor | Inventor | workshop working | civic/service |
| PublicHealthLab | Herbalist | Inventor | workshop working | civic/service |
| Hospital | MedicalBed | none | never (no loop) | civic/service |
| GroceryStore | Agora | none | never (no loop) | civic/service |
| Restaurant | Grill | Bakery | workshop working | civic/service |
| FertilizerWorks | Fermenter | Gristmill | workshop working | food/agri |
| FishHatchery | BreedingPod | WaterWheel | workshop working | food/agri |
| FisheryWorks | AquaticFarmhouse | WaterWheel | workshop working | food/agri |
| FoodPackagingWorks | FoodFactory | Grill | workshop working | food/agri |
| Greenhouse | HydroponicGarden | WaterWheel | workshop working | food/agri |
| SandstoneMasonryBlock | Default | none | never (no loop) | platform/levee |
| LimestoneMasonryBlock | Default | none | never (no loop) | platform/levee |
| ConcreteBlock | Default | none | never (no loop) | platform/levee |
| ReinforcedDamBlock | Default | none | never (no loop) | platform/levee |
| ConcreteOverflowDam | Default | none | never (no loop) | platform/levee |
| ConcreteOverhang8x1 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold3x3 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold3x3H1 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold3x3H2 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold4x4H1 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold4x4H2 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold4x4H3 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold5x5H1 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold5x5H2 | Default | none | never (no loop) | platform/levee |
| ConcreteScaffold5x5H3 | Default | none | never (no loop) | platform/levee |
| ConcreteSidePlatform3x3 | Default | none | never (no loop) | platform/levee |
| ConcreteSidePlatform4x4 | Default | none | never (no loop) | platform/levee |
| ConcreteSidePlatform5x5 | Default | none | never (no loop) | platform/levee |
| SteelCantilever10x1 | Default | none | never (no loop) | platform/levee |
| SteelCantilever12x1 | Default | none | never (no loop) | platform/levee |
| SteelCantilever15x1 | Default | none | never (no loop) | platform/levee |
| SteelBridge8x1 | Default | none | never (no loop) | platform/levee |
| SteelBridge10x1 | Default | none | never (no loop) | platform/levee |
| SteelBridge12x1 | Default | none | never (no loop) | platform/levee |
| SteelBridge15x1 | Default | none | never (no loop) | platform/levee |
| SteelColumnH1 | Default | none | never (no loop) | platform/levee |
| SteelColumnH2 | Default | none | never (no loop) | platform/levee |
| SteelColumnH3 | Default | none | never (no loop) | platform/levee |
| SteelColumnH4 | Default | none | never (no loop) | platform/levee |
| SteelColumnH5 | Default | none | never (no loop) | platform/levee |
| SteelColumnH6 | Default | none | never (no loop) | platform/levee |
| SteelDeck3x3 | Default | none | never (no loop) | platform/levee |
| SteelDeck5x5 | Default | none | never (no loop) | platform/levee |
| RadioactiveSpring (basic selection) | BadwaterSource | n/a | n/a | natural object |
| RadioactiveSpringSource (basic selection) | BadwaterSource | n/a | n/a | natural object |

The former planned entries are applied since the build 122 integration: SteelMill Smelter/PrintingPress, ArchiveExcavation DirtExcavator/GearWorkshop, CryogenicTankFarm Tank/no loop, SmogScrubber WindTunnel/no loop (not a workshop; no native driver). New wellbeing attractions: Bathhouse Shower/WateringPlace, TownPlaza ExercisePlaza/Agora (attraction driver), ObservationDeck Observatory/no loop.
