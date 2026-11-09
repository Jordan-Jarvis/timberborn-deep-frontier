# Fluids API extraction inventory

Completed 2026-11-09 against Timberborn 1.1.2.8 and the Deep Frontier source at `d418394`. This is item 2 of the [Fluids API plan](fluids-api-plan.md): every Deep Frontier water, weather, rendering and save hook, the optional assemblies, and every direct consumer of the radiation simulation. Each entry gives its proposed owner after the split. The source files were read in full. Line numbers are those at `d418394`.

Owners: **API** means the Fluids API foundation. **DF** means Deep Frontier content. **Adapter** means a public API hook through which Deep Frontier supplies values or callbacks.

## Rules for the foundation

The inventory shows the same failure modes repeatedly. The foundation should adopt these rules before it takes over any hook:

1. **Pair every patch with an unpatch.** None of Deep Frontier's water, weather, sensor, storage or planting patches is ever removed; only two unrelated transpilers (`DebugBuildingVisibility`, `TeleporterCitizenRecovery`) unpatch. The patches below are installed once per process, either at mod start or lazily by a static `_patched` flag, and reach scene objects through static fields (`RadiationLockstep.Simulation`, `RadiationSoilPatches._soil`, `RadioactiveTideService.Current`, `RadioactiveTideNewGameSettings.Current`). The foundation should patch per scene with its own Harmony owner, unpatch on scene unload, and refuse a second owner of the same target. `NativeTransportHooks` already does this for its two targets.
2. **Verify every native member at startup.** Several members the radiation code uses are never checked, so a game update would first fail on a worker thread during the first tick (section 2). The foundation should check every member a job will touch before it installs a patch, and report all failures in one message.
3. **Have one owner per native target, and no load-order winners.** Several Deep Frontier patches assume they are the only one on their target: the hazardous-weather selection postfix, the custom game-mode postfix, the Weather Station skip prefix, the sensor and sluice `__result` overwrites, and the global `SetSourceRadioactiveShare` scalar. When another mod patches the same target, the patch applied last silently wins. The foundation dispatches each target to registered providers and treats a foreign patch on a target it replaces as an explicit conflict.
4. **Do not read Deep Frontier internals.** The prototype's `NativeTransportHooks.RequireNoLegacyRadiationOwner` reflects `DeepFrontier.Scripts.Radiation.RadiationLockstep.Simulation` by name. It should instead detect foreign Harmony owners on the methods it replaces, a check that names the conflicting owner and needs no knowledge of Deep Frontier. This change is listed under next work.
5. **Keep optional types out of always-loaded assemblies.** Source evidence is in section 7.

## 1. Harmony patches

Deep Frontier never calls `PatchAll`. Every class is patched with `new Harmony(id)` plus `CreateClassProcessor(T).Patch()` or `Patch(...)`. "Startup check" means the target is verified before patching and a mismatch throws a clear error.

### Water simulation and soil

| Target | Kind | Source | Installed | Startup check | Owner |
| --- | --- | --- | --- | --- | --- |
| `WaterSimulationTaskStarter.ScheduleSimulationSteps(ParallelizerHandle, in SimulationParameters)` | Postfix that replaces `__result` with the lockstep tail | `Radiation/RadiationLockstep.cs:94-101`, owner `DeepFrontier.RadiationLockstep` | First game scene (`RadiationSimulation.Load` → `Attach`); static `_patched` | `Verify()` :53-83: signature, `SimulationParameters` properties, 7 starter fields, `SubstepCount == 2` | API (the existing `NativeTransportHooks` replaces it) |
| `UpdateWaterSourcesTask.Run()` | Prefix on a `ref` struct | :103-108 | same | Fields `_mapIndexService`, `_waterColumns`, `_waterColumnCounts`, `_verticalStride`, `_waterSources`, `_deltaTime`, `_waterDepthSetter`, `UpdateContaminationFromWaterChange(ref WaterColumn, float, float)` | API (sources run inside the shared substep job) |
| `UpdateWaterChangesTask.Run()` | Prefix and postfix | :110-119 | same | `Run`, `_waterChanges` and the common fields | API (`ScheduleUpdateWaterChanges` job) |
| `WaterChangeService.Tick()` | Postfix that promotes queued radioactive additions | :121-124 | same | Existence only; `WaterService.AddCleanWater` is not checked to enqueue a change | API (owned addition requests) |
| `SoilMoistureSimulationTaskStarter.StartTask(..., in ReadOnlyArray<ReadOnlyWaterColumn> waterColumns, ...)` | Prefix that substitutes `waterColumns` (bad plus radioactive share) | `Radiation/RadiationSoil.cs:595-598`, owner `DeepFrontier.RadiationSoil` | First game scene; static `_patched` | Signature and by-ref parameter. The claim that the caller passes a local copy is not checked; the runtime check at :449-452 throws | API, with an adapter: each fluid supplies its moisture-blocking share |

### Plants, beavers, storage

| Target | Kind | Source | Installed | Startup check | Owner |
| --- | --- | --- | --- | --- | --- |
| `PlantingSpotFinder.CanPlantAt(PlantingSpot, PlantableSpec)` | Postfix | `Radiation/IrradiatedPlantingSpots.cs:129-139` | Mod start | Strong: signature, not inlinable (`NativeIl.Inlinable`), IL call graph. Throws for a planter without the decorator, so it assumes Deep Frontier is bound | DF |
| `CitizenTint.UpdateTint()` | Postfix | `Radiation/RadioactiveZombieTint.cs:44-47` | Mod start | Existence and `void` return | DF |
| `InventoryInitializer.Initialize` | Prefix with field injection | `Radiation/ShieldedRadioactiveStoragePatches.cs:23-33` and `Cryogenics/CryogenicsPatches.cs:26-34` | Mod start | Only Harmony's own injection failure. The two prefixes share the target with no declared order | DF (goods, not world water) |
| `StockpileDropdownProvider.InitializeEntity` | Postfix | `ShieldedRadioactiveStoragePatches.cs:37-47` | Mod start | `TargetMethod` throws when missing | DF |

### Weather and tide (vanilla weather path)

These are installed at mod start by `RadioactiveTideModStarter`, owner `DeepFrontier.RadioactiveTide`. They are skipped entirely when the assembly `ModdableWeathers` is loaded (`RadioactiveTidePatches.cs:44-59`).

| Target | Kind | Source | Startup check | Owner |
| --- | --- | --- | --- | --- |
| `HazardousWeatherRandomizer.GetRandomWeatherForCycle(int)` | Postfix that may replace the native weather with the tide | `RadioactiveTidePatches.cs:110-115` | Method (:66-67, 80-91); inlining not checked | API: one selection owner that dispatches to registered tides |
| `HazardousWeatherService.Load()` | Postfix that restores a saved tide (native `Save` writes only `IsDrought`) | :121-128 | Method and `_mapEditorMode` | API: restore the active registered tide |
| `HazardousWeatherUIHelper.UpdateCurrentUISpecification()` | Skipping prefix | :132-136 | Method | API |
| Eight `HazardousWeatherUIHelper` string getters (`NameLocKey` … `NotificationBackgroundClass`) | Prefixes that return tide values | :139-147 | Existence and return type; inlining of these small getters not checked | API, with per-tide presentation supplied by DF |
| `HazardousWeatherSoundPlayer.OnHazardousWeatherStarted` (internal type) | Prefix that replays the badtide sound | :151-159 | Type, method, parameter, `_gameUISoundController`, `PlayBadtideStartedSound()` | API |
| `CustomNewGameModeController.TryGetValidatedGameMode(out GameModeSpec)` | Postfix that validates tide rows and swaps in `WithTide` | `RadioactiveTideNewGamePatch.cs:39-52`; applied with or without Moddable Weathers | Thorough IL checks (`RadioactiveTideNewGameSettings.cs:287-315`) | Adapter: generic new-game rows and a per-tide spec, with DF's curve |
| `WeatherStation.Sample()` and `UpdateOutputState()` | Non-skipping prefix; skipping prefix in tide mode | `WeatherStations/WeatherStationPatches.cs:147-167` | IL and member checks. `WeatherStationMode` must be exactly {Temperate, Drought, Badtide} | API: one mode per registered tide, saving the tide ID |
| `WeatherStationFragment.InitializeFragment()` and `UpdateFragment()` | Postfixes that add a fourth mode toggle | :186-219 | Throws unless the container holds exactly three buttons, so a second mod adding a toggle fails | API, plus a migration adapter for `DeepFrontier.WeatherStationRadioactiveTide` |

### Sensors and Sluice is Back!

| Target | Kind | Source | Installed | Startup check | Owner |
| --- | --- | --- | --- | --- | --- |
| `ContaminationSensor.GetContamination(int)` | Postfix that overwrites `__result` | `Sensors/ContaminationSensorPatches.cs:111-120` | Mod start | Parameter, IL length, call chain, fields, `Precision == 0.01` | API: a substance chosen by registry ID, plus a migration adapter for the `SensedSubstance` enum |
| `SluiceIsBack.Components.Sluice.GetContamination()` | Postfix that overwrites `__result` | `SluiceIsBack/SluiceContaminationPatches.cs:109-118` | Optional bridge start | Private, not inlinable, call chain, fields | API optional bridge (for example `FluidsApi.SluiceIsBack`) |
| `SluiceState.SetState(SluiceState, int)` | Postfix that copies the substance to the neighbour | :121-132 | same | Parameters, callers | same |

## 2. Native members without a startup check

These are read directly through the publicized ModsBuild assemblies (`DeepFrontier.asmdef` has `allowUnsafeCode: true`) or used inside jobs. A changed contract fails during the first radiation tick, on a worker or inside native scheduling, instead of at load:

- `SimulateContaminationTask` (17 arguments), `UpdateContaminationTask` (13) and `ClearBuffersTask` constructors (`RadiationSimulation.cs:330-337`)
- `WaterDepthSetter.SetWaterDepth(float, ref WaterColumn)` (:423). The field is checked; the method is not.
- `WaterSimulator.MaxColumnCount`, `ColumnCounts`, `WaterColumns`; `WaterSourceRegistry.ThreadSafeWaterSources`; `ThreadSafeWaterSource.CurrentStrength`, `Coordinates`, `Contamination`
- `ITickableSingletonService.ParalleTicklIsFinished` and `IsStartingParallelTick`
- `WaterChange.Coordinates`, `DepthChange`, `ContaminationChange`; the internal `Diffusions`, `TargetedDiffusion`, `ColumnOutflows`, `WaterFlow`
- `IThreadSafeColumnTerrainMap` index methods and events; `SoilBarrierMap.ContaminationBarriers` and `AboveMoistureBarriers`
- The Moddable Weathers public API (`ModdableWeatherBase`, `IModdableHazardousWeather`, `WeatherHistoryService`, `WeatherGenerator` …). It is compiled against directly, but only the spec `RadioactiveTideWeather` is checked.

The Fluids API prototype has the same gap. `NativeTransportHooks` verifies its two scheduling methods and `SubstepCount` in its constructor. Its jobs then look up about 40 more private members on worker threads: starter fields, `SimulationParameters` properties, four native task constructors, `WaterChange` and `WaterAmountChange` members, diffusion structs, and `ReadOnlyArray._array`. Next work moves these checks into the constructor (see "Next work" in [the native adapter document](fluids-native-adapter.md)).

Members that are checked with a clear error include `TickOnlyArrayService._forceAllowAccess`, the rendering mirror contract in `RadiationShading.Verify` (`WaterRenderer._contaminations`, `UpdateWaterTexturesTask._contaminations/_waterColumns`, `TerrainMaterialMap` fields, `sizeof(PixelData) == 2`), the eleven soil starter floats and two soil task constructors (`RadiationSoil.cs:528-550`), the planting members, and `GoodConsumingBuilding._goodConsumingBuildingSpec`. The last one is checked in a static initializer, so its failure arrives wrapped in a `TypeInitializationException`.

## 3. Rendering

| Touch point | Source | Owner |
| --- | --- | --- |
| Swaps the native water materials (`Shader Graphs/PhysicalWaterURP_Opaque/_Transparent`) to bundle variants `Shaders/DeepFrontier/RadioactiveWaterURP_*`, and the terrain materials (`TerrainURP`) to `IrradiatedTerrainURP`. Restores them on `Unload` and accepts `Hidden/InternalErrorShader` because the asset-loader reset destroys the variants first. | `RadiationRenderer.cs:57-72`, `RadiationShading.cs` `ShaderSwap` | API (one material owner); a second owner of these materials would conflict |
| Water surface: reads `_MinContaminationThreshold`, `_MaxContaminationThreshold`, `_ContaminationNonlinearity`. Writes `_DFRadioactiveBaseColorA/B`, `_DFRadioactiveDetailColorA/B` and the global R8 texture arrays `_DFOldRadioactivity` and `_DFNewRadioactivity`, with one layer per column layer. Sets the keyword `_DEEP_FRONTIER_RADIOACTIVE_WATER`. | `RadiationShading.cs:236-365` | API: a composition or resolved-appearance texture. DF supplies colours and its visibility curve through an adapter |
| Irradiated soil: `_DFIrradiatedSoilMap` (RG16), `_DFIrradiatedSoilColor`, keyword `_DEEP_FRONTIER_IRRADIATED_SOIL` | `RadiationShading.cs:373-499` | DF, or an API terrain overlay through an adapter |
| Shader variants generated by `tools/native_shader_variants.mjs` with DF-named properties and keywords | tools | API must own a renamed variant set; DF keeps its soil variant |
| Spring material copied from `DFIndustrial18` | `RadiationMaterials.cs:14-70` | DF |
| Tick order: the renderer's late tick must follow the simulation's, which follows `RadiationSoil.Tick`. The order is set by binding order in `RadiationConfigurator`. | `RadiationRenderer.cs:26-28` | API: explicit stages, not binding order |

## 4. Persistence

| Key | Contents | Version | Owner after the split |
| --- | --- | --- | --- |
| Singleton `DeepFrontier.Radiation` | `Version` (3), `Cells` (x, y, column floor), `WaterRadiation`, `Soil`, `SourceIds`/`SourceCells`/`SourceRates`/`SourceHours`, `NextSourceId`, `HourAccumulator`, optional `LastCompletedTickSnapshot`; version 2 adds `Sludge` | 3, reads 2 | Column state moves to the API under a new key. DF keeps `Soil`, `HourAccumulator` and both importers: it reads the old key once and queues the water through the API. |
| Singleton `DeepFrontier.RadioactiveTideSettings` | `Enabled`, `CyclesWithoutTide`, `ChancePercent`, `MinDurationDays`, `MaxDurationDays`; partial data throws | none | DF settings for its tide, read through the API's per-save tide settings |
| Singleton `DeepFrontier.RadioactiveTide` | `CurrentCycleIsTide`, `LastTideCycle`, `LastTideDuration`, `SludgeEmittedThisTide` | none | API: active tide ID, duration and cooldown history, with a migration reader. DF keeps the sludge accounting. |
| Moddable Weathers settings JSON keyed by `DeepFrontier.RadioactiveTideModdableWeathers.RadioactiveTideModdableWeatherSettings` | Same fields plus `FirstLoad` | n/a | Adapter. Renaming the type breaks Moddable Weathers persistence, so a rename needs a migration. |
| Native `HazardousWeatherHistory` entries with the ID `RadioactiveTideWeather`; native `IsDrought` | Native | Native | Keep the tide ID; if DF is removed, a saved tide reloads as a badtide |
| Entity `DeepFrontier.WeatherStationRadioactiveTide` (`SignalsRadioactiveTide`) | Native mode extension | none | API, by tide ID, with a migration |
| Entity `DeepFrontier.ContaminationSensorSubstance` (`Substance` enum, `RadioactiveShare` snapshot) | Sensor choice | none | API, by fluid ID, with a migration |
| Entity `DeepFrontier.SluiceContaminationSubstance` (`Substance`) | Sluice choice | none | API bridge, by fluid ID, with a migration |
| Entities `DeepFrontier.RadioactiveSludgeIntake` (`Buffer`), `DeepFrontier.RadiationExposure`, `DeepFrontier.WasteLeak`, `DeepFrontier.ReactorBotLeak`, `DeepFrontier.DeepWell`, `DeepFrontierFisherCatch`, legacy `DeepFrontier.RadiationFloraDose` | Content state | none | DF |

The radiation save has to handle a native contract: `GameSaver.Save` finishes the tick first, but the exception saver (`GameSceneExceptionStateSaver.CreateExceptionSave`) can arrive mid-tick while workers still run. `RadiationSimulation.Save` therefore writes the last completed tick's snapshot in that case, and loads it leniently. A normal save that arrives mid-tick throws. The foundation's persistence needs the same rule. Its document is captured only at a completed-tick barrier (`Phase == Ready`).

## 5. Direct consumers of the radiation simulation

These consumers inject the concrete `RadiationSimulation`. Changing only `IRadiationService` would leave them coupled to the old implementation.

| Consumer | Members used | Owner after the split |
| --- | --- | --- |
| `RadiationLockstep` (static `Simulation`) | `ScheduleLockstepSubstep`, `RecordSourceCells`, `RecordChangedColumns`, `MixWaterChanges`, `PromoteRadioactiveAdds`, row tasks `CopyRow`, `HarvestRow`, `RestoreSourceCells`, `MixSourceCells` | API |
| `RadiationSoil` | `Counts`, `WaterSnapshot`, `WaterRadiation` and `SoilRadiation` (it writes both arrays), `VisibleRows`, `Layers`, `EffectiveDepth`, `RadiationRows`, `TotalWaterRadiation`, `RowRange`. In the other direction, the simulation calls `BankAt`, `Exchange`, `Prepare`. | DF, through an adapter: a per-tick snapshot, a guarded share write for soil exchange, and geometry events |
| `RadiationRenderer`, `RadiationShading` | `Layers`, `StateVersion`, `HasTicked`, `XSize`, `YSize`, `Stride`, `VerticalStride`, `VisibleRows`, `WaterRadiation`, `Counts`, `WaterSnapshot`, `SoilAt` | API renderer; DF soil overlay |
| `RadiationIntakeGuard` | `ColumnRadiation`, `Sample` | DF on API sampling |
| `RadiationBuildings` (outfall, sludge intake) | `IsOpenCell`, `AddRadioactiveWater`, `RegisterIntake`/`UnregisterIntake`, `IsColumnContaminated`, `Sample`, `TryFindOpenCell`, the `OnRadioactiveRemoved` callback | DF on API emission and intake results |
| `RadiationExposure`, `RadiationStorage` | `Sample` | DF |
| `RadioactiveSpring` | `RegisterSpring`/`UnregisterSpring` | DF on API owned emitters |
| `IrradiatedPlantWarning`, `IrradiatedPlantingSpots` | `IsIrradiatedGround` | DF |
| `WaterShadingProbe` (test) | `TotalWaterRadiation`, `RadiationRenderer.Swaps` | DF test |
| **Fluids API `NativeTransportHooks`** | Reads `RadiationLockstep.Simulation` by name | To be replaced by Harmony-owner conflict detection (rule 4) |

`IRadiationService` consumers: `MeltdownService` (`TryFindOpenCell`, `AddRadioactiveWater`, `AddContinuousSource`, `AddSoilRadiation`, `Sample().Submerged`), `WasteLeak`, `ReactorBotLeak`, `FisherFlag` (`IsColumnContaminated`), `RadioactiveTideService` and `RadioactiveTideModdableEmitter` (`WaterPerStrengthHour`, `SetSourceRadioactiveShare`), `StreamGaugeRadiationPanel`, `ContaminationSensorSubstance` (`SavedStatePending`, `Sample`), `SluiceContaminationSubstance`, and the acceptance probes. The interface remains as a DF facade backed by the API, so these files can migrate one at a time. `KernelCorrections` has no reader, and `RemoveContinuousSource` has no caller.

## 6. Radiation rules inside the water code

These rules stay in Deep Frontier. The API must report the volumes they act on, but must not apply them to other fluids.

| Rule | Value and source | Path after the split |
| --- | --- | --- |
| Detection cutoff | `RadiationTuning.DetectionLimit = 0.005`; `Rescan` zeroes a share below the limit that is not growing. This deliberately does not conserve volume. Every reader applies `Detected()`. | Adapter: a declared per-fluid transformation at a late-tick stage, accounted as removed volume |
| Kernel excess to soil | `RadiationMixing.KernelExcess` from `HarvestRow` | Removed. Joint transport has no excess to deposit. |
| Deposition into soil | `Deposit`, ×`SoilPerDepositedVolume` (10), called from evaporation (`CopyRow`), geometry loss (`Reconcile`), closed intakes (`CreditIntakes`) and pending soil (without the ×10) | Adapter: the API reports evaporated, geometry-lost and intake-lost component volumes per column; DF deposits them |
| Decay | Water half-life 365 days; soil half-life 120 days, spread 0.002 per hour | Adapter: a late-tick transformation |
| Soil exchange and washout | `SoilRiseFromWaterPerHour = 0.05`, `WaterToSoilFactor = 4`, washout from the native `_contaminationNegativeEqualizationRate` | DF, through the guarded share-write adapter |
| Irradiated ground | Threshold 0.05 kills plants and starts the tint | DF |
| Sludge conversion | `VolumePerGood = 0.2` (tools); at runtime the volumes come from the `RadioactiveSludgeIntakeSpec`, `RadioactiveSludgeOutfallSpec`, `WasteLeakSpec` and meltdown specs | DF intake and emission specs on API results |
| Source share | `SourceShare = spring ? spring : tideShare × (1 − source.Contamination)` with one global `_tideShare` | API owned per-source composition; no global last-writer scalar |

## 7. Optional assemblies and loading

Source-confirmed in the 1.1.2.8 assemblies:

- **All code loads before any mod starts.** `Timberborn.ModManagerScene.ModCodeStarter.Start` loads every `*.dll` of every enabled mod with `Assembly.Load(File.ReadAllBytes(...))` before any `IModStarter.StartMod` runs. A consumer's `StartMod` can therefore always find a loaded Fluids API assembly, whatever the load order. The API's own `StartMod` may not have run yet, so the registry is created lazily on first access and does not depend on API start order.
- **Each DLL is enumerated without a guard.** `ModCodeStarter.GetModStarters` calls `assembly.GetTypes()` on every DLL without handling exceptions. A plain-DLL bridge whose types implement an absent mod's interfaces breaks mod start for its package.
- **Dependencies do not guarantee load order.** `Timberborn.Modding.ModSorter` sorts by `RequiredMods` and `OptionalMods`, then reorders by each mod's player-set priority (`ModPlayerPrefsHelper.GetModPriority`). A player can move a consumer ahead of its dependency. Registration therefore must not depend on load order.
- **Duplicate copies load twice.** Two enabled copies with the same ID (a local and a Workshop copy) are both kept by the sorter. Two `FluidsApi` assemblies would then load into the AppDomain. The API detects this and refuses to start a second registry.

Deep Frontier's mechanism: every non-main asmdef must be named `DeepFrontier.<ModId>` (`DeepFrontierBatchBuild.cs:55-64`). After the official build, each is renamed to `Scripts/DeepFrontier.<ModId>.dll.<ModId>.optional`. Moddable Timberborn's `OptionalModsLoader` loads those files only when the named mod is enabled. The main assembly checks for optional mods only by assembly name, and keeps shared contracts (`IContaminationSubstanceChoice`, `SensedSubstance`, `RadioactiveTideTuning`, `IRadiationService`) in its own assembly. `verify_deep_frontier_package.ps1` rejects plain-DLL bridges, and each bridge's configurator throws when the bridge is missing. The bridges are `DeepFrontier.ModdableWeathers`, `DeepFrontier.SluiceIsBack` and `DeepFrontier.PowerLines`.

The Fluids API depends only on Harmony, so it cannot use Moddable Timberborn's loader for itself. Its core assembly references nothing but the base library, so it is safe to enumerate in any installation. Consumers have three routes:

1. Reflection only: no compile reference and no load-order assumption.
2. A compiled reference in a package that lists `FluidsApi` in `RequiredMods`.
3. A Moddable Timberborn `.optional` bridge when the consumer already depends on Moddable Timberborn.

The synthetic consumer packages exercise the first two routes. The harness verifies under both .NET 8 and the installed Mono that a compiled bridge fails `GetTypes()` when the API is absent.

## 8. Tide selection as implemented

Vanilla path: `RadioactiveTideService.Choose` (`RadioactiveTideService.cs:158-168`) runs after the native drought or badtide draw. The checks are, in order:

- earliest cycle 2;
- `Enabled`;
- a validated setting;
- a one-shot development force;
- `cycle <= CyclesWithoutTide`;
- a cooldown of one cycle (`CooldownCycles = 1`), so a tide never follows a tide;
- `CheckProbability(ChancePercent / 100)`.

In an eligible cycle, P(tide) = c and the native weather keeps 1 − c. The defaults (`RadioactiveTideTuning.GameModeCurve`) are 15, 25 and 35 percent on Easy, Normal and Hard. Their long-run shares are 13.0, 20.0 and 25.9 percent because of the cooldown. Game modes from other mods derive their values from each mode's hazard share.

Moddable Weathers path: `RadioactiveTideModdableWeather.GetChance` returns a weight. It calls `GetChance` on every other enabled hazardous weather and converts the chance to a weight relative to their total. Two weathers that both did this would call each other indefinitely. When the other weights total zero, the tide always wins. The combined-policy proposal is in [the plan](fluids-api-plan.md#combined-tide-selection-proposal).

## 9. Migration order implied by the inventory

1. Replace the reverse coupling (`RequireNoLegacyRadiationOwner`) with Harmony-owner conflict detection, and verify every job member at attach time.
2. Add API sampling, owned emitters and intake results that match the `IRadiationService` members DF uses. Back the facade with the API while DF still owns soil, decay and the cutoff through adapters.
3. Move the column-state save to the API with a one-time importer for `DeepFrontier.Radiation` versions 2 and 3. DF keeps `Soil` under its own key.
4. Move the renderer, material ownership and shader variants to the API. Leave DF's soil overlay as an adapter.
5. Move tide selection, presentation, Weather Station modes, sensors and the sluice bridge to registry IDs, with migration adapters for the four DF entity and singleton keys.
6. Remove each DF patch only after the API owns its target. Never run both owners on the same native method.
