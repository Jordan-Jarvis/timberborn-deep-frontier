# Deep Frontier on Moddable Fluids

Deep Frontier's radioactive water is moving onto [Moddable Fluids](fluids-api-contract.md). The migration lives behind the compile flag `DEEP_FRONTIER_MODDABLE_FLUIDS`. The shipped Deep Frontier package does not define it, so the shipped game is unchanged.

Status on 2026-11-09:

- The flagged build compiles, binds every service it uses, and installs no water or weather patch that Moddable Fluids also owns.
- It has passed the .NET harness and the compile checks only. **Nothing in it has run in game.**
- The shipped package has not switched. The plan for that is [below](#switch-over-plan).

## Where the code is

| Path | Contents |
| --- | --- |
| `src/DeepFrontier/ModdableFluids` | The migration code. It sits outside `Scripts`, so `tools/stage_deep_frontier.ps1` never stages it; only the [test build](#test-packages-and-the-launcher) does. Files that need game types are wrapped in `#if DEEP_FRONTIER_MODDABLE_FLUIDS`. |
| `src/DeepFrontier/Scripts` | Flag-guarded switches where the two builds differ: bindings, patches not installed, the inert intake guard, the custom-intake marker and the scene-cycle probe. Also the service interfaces both builds use. |
| `tools/compile-check/deep-frontier-fluids` | The pure part, without game references. The fluid harness uses it. |
| `tools/compile-check/deep-frontier-moddable-fluids` | All Deep Frontier scripts with the flag. `tools/test_fluid_transport.ps1` builds it. |
| `tools/compile-check/fluid-transport-harness` | `DeepFrontierFluidsScenarios.cs` and `HarnessExtensions.DeepFrontier.cs` |
| `tools/build_deep_frontier_moddable_fluids.ps1` (run by `tools/build_deep_frontier.ps1 -ModdableFluids`) | The disposable flagged test package, kept out of Mods |
| `tools/start_deep_frontier_moddable_fluids.ps1` | One interactive run with the test packages, restoring everything afterwards |

## The pieces

| Piece | What it does |
| --- | --- |
| `DeepFrontierRadioactiveWater` | The provider `DeepFrontier.Radiation`. It registers the fluid `DeepFrontier.RadioactiveWater` and its two policies (below). It registers both springs as source types: 1 tile, native strength 0.026041666666666668, follows drought, no badtide, not tide-overridable, emits radioactive water only. It also registers the radioactive tide, imports `DeepFrontier.Radiation` versions 2 and 3 once, and runs the soil field as its column rules. |
| `RadiationSoilField` | Deep Frontier's water and soil rules after every completed fluid tick, on the worker thread. See [the rules](#the-rules-after-each-fluid-tick). Main-thread readers see whole published passes. |
| `RadiationSoilFormulas` | `RadiationSoil.SoilWaterExchange`, `Rinse`, `KernelContamination` and both constants, copied unchanged. The harness compares each member's source text with `RadiationSoil.cs`, so the two copies cannot drift apart. |
| `RadiationSaveMigration` | Versions 2 and 3 to a `FluidSaveDocument`, with `ApplyLoaded`'s rules. |
| `ModdableFluidsRadiationService` | The facade. It serves `IRadiationService`, `IIrradiatedGround` and `IRadiationWaterCells` from the world state of the last completed fluid tick. Open cells, submerged and badwater readings come from the native thread-safe water map, exactly as `RadiationSimulation` read them, so they work before the first fluid tick. |
| `ModdableFluidsRadiation` | The game singleton (flagged). It handles the lifecycle and the `DeepFrontier.Radiation` version 4 save. It also serves `IRadioactiveIntakes` and `IRadioactiveSprings`. Its late tick emits timed sources, credits sludge intakes, updates the bank layer, kills plants on newly irradiated ground and prepares the kernels. |
| `ModdableFluidsBankLayer` | `RadiationSoil`'s native-kernel part with unchanged rules, fed from the published shares. It also gives the soil overlay its view. At load it checks that the native `MaximumWaterContamination` is the moisture policy's 0.53. |
| `IrradiatedSoilOverlay` | The irradiated ground as a Moddable Fluids terrain overlay, `DeepFrontier.IrradiatedSoil`, with `IrradiatedSoilSurface`'s curve (0.05, 0.5, 0.1) and colour. The flagged mod starter registers it. |
| `ModdableFluidsSoilRenderer` | Writes the bank layer's view (soil field and bank layer) into that overlay (`IrradiatedSoilOverlayWriter`, `IrradiatedSoilSurface.Update`'s cell loop), when a new soil pass is published. Moddable Fluids draws it; no Deep Frontier shader touches a native material. |
| `RadioactiveTideRegistration` | The radioactive tide as a Moddable Fluids tide, built from `RadioactiveTideTuning`. |
| `RadioactiveTideImport` | Maps a Deep Frontier save's tide state and settings to Moddable Fluids tide state. The flagged mod starter reads them for the provider's `IFluidTideImporter` ([Saves](#saves)). |
| `RadioactiveTideModdableWeathersSave` | Reads the radioactive tide of a save played with Moddable Weathers, from its settings and history, as `RadioactiveTideImport` then maps it ([Saves played with Moddable Weathers](#saves-played-with-moddable-weathers)). |

### Services the consumers use

The consumers inject service interfaces instead of `RadiationSimulation`. In the shipped build, `RadiationSimulation` implements each interface by forwarding to the method the consumers called before. In the flagged build, the facade implements them.

| Consumer | Service |
| --- | --- |
| `IrradiatedPlantingSpots`, `IrradiatedGroundDeath`, `IrradiatedGroundSpawnValidator` | `IIrradiatedGround` |
| `RadioactiveSludgeOutfall` | `IRadiationService`, `IRadiationWaterCells.IsOpenCell` |
| `RadioactiveSludgeIntake` | `IRadiationService`, `IRadioactiveIntakes` |
| `RadiationIntakeGuard` | `IRadiationService`, `IRadiationWaterCells.ColumnRadiation` |
| `RadiationExposure`, `RadiationStorageService` | `IRadiationService` |
| `RadioactiveWaterSource` (springs) | `IRadioactiveSprings`. The facade checks the spring's share against the registered emission; Moddable Fluids classifies placed sources by blueprint. |
| `IrradiatedSoilSurface` (shipped), `IrradiatedSoilOverlayWriter` (flagged) | `IIrradiatedSoilView` |
| `WaterShadingProbe` | `IRadiationService`. The flagged build refuses the probe: it compares Deep Frontier's water shader variants, which that build does not use. |
| `NativeContracts` | The `RadiationSimulation` exception-save check runs in the shipped build only. |

### The rules after each fluid tick

`RadiationSoilField` follows the order of `RadiationSimulation.Tick`, with its formulas and constants (`RadiationTuning`):

1. **Geometry.** When a cell's columns change, its soil follows `Reconcile`'s rule. The soil of an old floor moves to the new column with that floor, or else to a floor raised directly above it. Each old surface moves at most once, and the cell's ground is checked for plants again.
2. **Deposition.** This step uses the tick's Moddable Fluids losses. Evaporated radioactive volume goes into that column's soil. Volume deleted by a geometry change goes into the cell's lowest column (only above `MinWaterRadiation`, as `Reconcile` does). An addition dropped into a closed cell goes into the lowest column above it. Each deposit is multiplied by `SoilPerDepositedVolume` and capped at 1. Discharge, pressure losses, source withdrawals and other mods' extractions leave nothing, as before.
3. **Intakes.** Radioactive volume in native removals is credited to the sludge intake registered at that cell, once per tick on the main thread (`CreditIntakes`).
4. **Soil requests** (`AddSoilRadiation`). Each goes to the column containing the cell, or else the lowest one above it, capped at 1 (`ApplyPendingSoil`).
5. **Per column.** First the radioactive share decays (`RunInteraction`). Then comes the soil-water exchange, or rinsing under clean water (`RadiationSoil.Exchange`). Last, a share below 0.5% that did not grow since the last pass is cut off (`Rescan`). The share change becomes a conversion between radioactive and fresh water, so physical volume and badwater never change.
6. **Hourly pass.** Once per accumulated game hour, `HourlySoilPass` runs: spread to the neighbouring column whose floor is within one level (`NeighborSlot`), then decay.

### Native policies and hooks

- **Water intakes.** Radioactive water is refused at `RadiationTuning.DetectionLimit`, with Deep Frontier's pump status and alert. Below that share, what a pump draws becomes clean water (`DeepFrontier.RadioactiveWaterDrawnAsWater`). Moddable Fluids' guard does the blocking. `RadiationIntakeGuard` stays only to describe the intake water. The sludge intake implements `IFluidCustomIntake`, so the guard leaves it alone, as before.
- **Soil moisture.** Radioactive water blocks moisture at 0.53, the native `MaximumWaterContamination`. The moisture tasks therefore see b + r, as `RadiationSoil`'s moisture shadow showed them. Deep Frontier's own moisture hook is not installed.
- **Tide.** The radioactive tide keeps the weather ID `RadioactiveTideWeather`, so its fog, history and Deep Well behaviour are unchanged. It uses `GameModeCurve`'s Easy, Normal and Hard values, full radioactive emission, and Deep Frontier's texts, art and the badtide sound. Moddable Fluids' tide service selects it with policy C′, restores it, shows it, emits it and draws its new-game rows. With Deep Frontier's tide alone, the draws are exactly `RadioactiveTideService.Choose`'s. The facade refuses a radioactive source share rather than compete for the source composition.
- **Weather Station.** Moddable Fluids gives every registered tide a Weather Station mode (`FluidTideWeatherStation`, saved by tide ID). Deep Frontier's own station mode (`WeatherStationRadioactiveTide` and its patches) is neither bound nor installed. The provider is an `IFluidTideStationImporter`: a station saved with `DeepFrontier.WeatherStationRadioactiveTide` and `SignalsRadioactiveTide` true signals `DeepFrontier.RadioactiveTide`. Any other station keeps its native mode. Moddable Fluids asks once per station loaded without its own component, and the next save writes that component.

Hooks in the flagged build:

| Not installed or not bound (Moddable Fluids owns the target) | Still Deep Frontier's (no Moddable Fluids counterpart) |
| --- | --- |
| The water lockstep (`DeepFrontier.RadiationLockstep`) | Planting-spot postfix (`DeepFrontier.IrradiatedPlantingSpots`) |
| The soil moisture prefix (`DeepFrontier.RadiationSoil`) | Zombie tint, storage and stockpile patches |
| The tide weather patches (`DeepFrontier.RadioactiveTide`) | Contamination sensor postfix (through `IRadiationService`) |
| The new-game postfix (`DeepFrontier.RadioactiveTideNewGame`) | The optional Sluice is Back! bridge |
| The Weather Station patches (`DeepFrontier.WeatherStation`) and `WeatherStationRadioactiveTide` | |
| `RadiationSimulation`, `RadiationSoil`, `RadiationRenderer`, `RadioactiveTideService`, its weather, settings, UI and dev method, `RadioactiveTideNewGameSettings` | |

Moddable Fluids refuses to attach, naming the owner, if any of the left-hand patches is present. The flagged build still compiles the old classes, but binds none of them. Its own code uses only `RadiationSimulation.RowRange` and `RadiationSoil`'s static kernel helpers (`KernelContamination`, `FieldRowMargin`, `RadiationSoilNative.Verify`).

Materials: no Deep Frontier shader goes on a native material in the flagged build. Moddable Fluids draws the water and the irradiated ground with per-scene copies of the native water and terrain materials ([Shared rendering](fluids-native-adapter.md#shared-rendering)). The scene-cycle probe expects the native water and terrain materials on their native shaders in every game of the flagged build.

## Differences from the one-fluid simulation

Each difference is deliberate or forced by the shared model.

1. **Exchange depth.** The depth `d` is the column's physical volume (depth plus overflow). `RadiationSimulation` used depth plus overflow times the pressure factor. Rates differ only in pressurized columns.
2. **The b input.** `b` in the exchange counts everything that is neither fresh nor radioactive water. In a Deep Frontier-only world that is the badwater share.
3. **Rinse limit.** A rinse whose float shares overrun the fresh water by less than `ShareTolerance` of the column takes all the fresh water there is. A larger overrun throws.
4. **Transport.** Moddable Fluids transports the fluids jointly, so there is no kernel excess to deposit. Evaporation deposits land on the tick's column after the geometry change, not before it.
5. **Hour counter.** It advances while soil, radioactive water, requests or deposits exist. This approximates `RadiationSimulation`'s row envelope and changes only the phase of the hourly pass.
6. **Keys and threads.** The kill check and the bank layer use (x, y, floor) keys instead of native slots. Readers see the last completed pass, never a half-done one.
7. **Moisture below 0.5%.** Moddable Fluids also counts shares below 0.5% toward moisture; `RadiationSoil` used `Detected(r)`.
8. **Water tint.** Moddable Fluids' shared renderer tints by the fluid's single colour, with Deep Frontier's visibility curve: nothing below 0.5%, 0.12 there, log-scaled to 1. The harness checks the curve against `RadioactiveWaterSurface.Encode`. The second base and detail colours of Deep Frontier's water variant are not used.
9. **Early additions.** Water added before the first fluid tick waits for it, and version 4 saves keep it. Soil requests not yet applied are saved too.
10. **Exception saves.** These write the last published pass. Requests that a running pass had already taken are lost.
11. **Pending state.** `SavedStatePending` is true from loading a radiation record until the first completed fluid tick applies it. A new game has nothing pending.
12. **Tide accounting.** `SludgeEmittedThisTide` is gone. It was only ever saved.
13. **Irradiated ground.** Moddable Fluids' terrain overlay draws it, with `IrradiatedSoilSurface.Encode`'s bytes (the harness checks every soil value it tries, in .NET and under Mono) and its colour. Four things differ:
    - **Where.** Only terrain tiles show the tint. The shipped variant sat on the five native terrain materials themselves, so other models drawn with them on irradiated ground could show it too. In 1.1.2.8 the terrain blocks use only Cliff and CliffEdge; Grass, SlopeCliff and SlopeCliffEdge are drawn by other models.
    - **Colour precision.** The colour reaches the shader through a half-float map instead of a material property: within 0.05% of the material colour.
    - **Settling.** Moddable Fluids applies the native update rule once per frame in which ticks ran. At high game speeds, several ticks in one frame settle as one.
    - **Writes.** Deep Frontier writes only when a new soil pass is published; it no longer re-runs its loop each tick to settle pixels.

The sludge intake keeps the native pump path, credited from native-removal losses at its cell. This is the shipped mechanism. It does not use `IFluidExtraction`, which would stop it from using up the fresh water it pumps.

## Saves

| Save | Flagged build |
| --- | --- |
| `DeepFrontier.Radiation` v2/v3 (shipped) | Moddable Fluids imports the water in the first substep through the provider's importer. Deep Frontier loads soil, sources and the hour counter. A save before that substep writes the record back unchanged, with any requests, and Moddable Fluids marks its own entry `ImportPending`. |
| `DeepFrontier.Radiation` v4 | Holds the last soil pass, the hour counter, sources, unapplied soil requests and water added before the first fluid tick (`RadiationFacadeRecord.Capture` and `Restore`). Moddable Fluids saves the water. |
| `DeepFrontier.RadioactiveTide`, `DeepFrontier.RadioactiveTideSettings` (shipped) | Imported once by Moddable Fluids' tide service (`IFluidTideImporter`, capability `ModdableFluids.Tides.Import`) for a loaded save without its tide state. See [Tide import](#tide-import). The next save writes Moddable Fluids' tide singletons, so the import never repeats. |
| Moddable Weathers' `ModdableWeatherSettingsService` and `WeatherHistoryRegistry` (shipped with Moddable Weathers) | Imported once by the same importer: the bridge's settings and the state its history gives. See [Saves played with Moddable Weathers](#saves-played-with-moddable-weathers). |
| Entity `DeepFrontier.WeatherStationRadioactiveTide` (`SignalsRadioactiveTide`) | Imported once per station into Moddable Fluids' `ModdableFluids.WeatherStationTide` (see Weather Station above). |
| Sensor, sluice, intake buffer, exposure | Unchanged keys. |

### Tide import

Deep Frontier's provider is the importer. The flagged mod starter reads the save:

- **State.** `DeepFrontier.RadioactiveTide`, with `RadioactiveTideService`'s keys and load checks. `SludgeEmittedThisTide` is not carried over.
- **Settings.** `RadioactiveTideStartingValues.ForLoadedSave`: the save's `DeepFrontier.RadioactiveTideSettings`, or else, for saves from 0.8.3 and older, the former mod-setting keys through the game's settings. Keys the player never changed read as the old defaults. This is the shipped rule, now extracted so it needs no scene loader.

`RadioactiveTideImport.Map` then builds the Moddable Fluids state:

| Deep Frontier | Moddable Fluids |
| --- | --- |
| `CurrentCycleIsTide` | current tide = last tide = `DeepFrontier.RadioactiveTide` |
| `LastTideCycle`, `LastTideDuration` | the last tide's cycle and duration; cycle 0 means no tide yet |
| no `DeepFrontier.RadioactiveTide` singleton (a save older than the tide) | no tide yet |
| tide on: `ChancePercent`, `CyclesWithoutTide`, `MinDurationDays`, `MaxDurationDays` | budget = weight = `ChancePercent`, and the same cycles without and durations |
| tide off | the tide off, its values passed unchecked as Deep Frontier never checked them; budget 1, the lowest valid one |

The budget of a save whose tide is off draws nothing: no listed tide is on, and unlisted tides are off. Moddable Fluids then checks that a current tide matches the native weather and duration. A vanilla save first loaded with Deep Frontier gets the former defaults, as the shipped build gives it.

#### Saves played with Moddable Weathers

With Moddable Weathers, the shipped build runs the tide through its optional bridge `DeepFrontier.ModdableWeathers`: the Moddable Weathers weather `RadioactiveTideWeather`. The bridge saves nothing of its own. `RadioactiveTideConfigurator` binds neither `RadioactiveTideService` nor `RadioactiveTideGameSettings` then, and a save holds only the singletons bound when it was made (`SerializedWorldFactory`). Such a save therefore has no `DeepFrontier.RadioactiveTide` or `DeepFrontier.RadioactiveTideSettings`. Before this import it read as a save with no tide and the former mod settings. Under Moddable Weathers, Moddable Fluids refused it once its history held a tide, because that imported state disagreed with the history. Before any tide it took the former mod settings instead of the bridge's.

What the save holds instead (Moddable Weathers 11.0.0):

| Key | Contents |
| --- | --- |
| Singleton `ModdableWeatherSettingsService`, property `Settings` | One JSON object, an entry per settings type keyed by its full name (`BaseWeatherSettingsService.SerializeSettings`). The bridge's entry is `DeepFrontier.RadioactiveTideModdableWeathers.RadioactiveTideModdableWeatherSettings`, with its `[Description]` properties `Enabled`, `StartCycle`, `ChancePercent`, `MinDurationDays`, `MaxDurationDays`. |
| Singleton `WeatherHistoryRegistry`, list `WeatherCycles` | Entry i is cycle i, entry 0 the empty cycle. Each is a `WeatherCycle` as Newtonsoft JSON, with `Stages` of `Index`, `IsBenign`, `WeatherId`, `WeatherModifierIds` and `Days`. Moddable Weathers generates one cycle ahead. |
| Native `GameCycleService` | `Cycle`, `CycleDay` |

`RadioactiveTideModdableWeathersSave.Read` (groundwork, with the game's Newtonsoft) maps it. The importer reads it first: it applies when the settings hold the bridge's entry.

| Moddable Weathers | Moddable Fluids |
| --- | --- |
| The latest non-benign stage with `RadioactiveTideWeather` in this or an earlier cycle | the last tide, with that cycle and the stage's `Days`; none means no tide yet |
| Moddable Weathers' current or next hazardous stage in this cycle is the tide | current tide = last tide |
| `Enabled`, `StartCycle`, `ChancePercent`, `MinDurationDays`, `MaxDurationDays` | as Deep Frontier's own settings, with cycles without = `StartCycle` − 1: budget = weight = chance, by the rules of the table above |

Moddable Fluids' Moddable Weathers adapter derives its state from the same history in the same way (`FluidTideModdableWeathersService.Derive`), so its load check accepts the import. The current stage follows `WeatherCycleService` as written:

- **The current stage** is the first stage, in list order, whose last day is at or after the cycle day. A day past the last stage takes the last stage.
- **The next hazardous stage** is searched from list position `Index` + 1 of the current stage, and only when the current stage lasts more than 0 days. A skipped stage leaves a gap in the indices, so Moddable Weathers can miss a hazardous stage that follows. The import misses it too.

The settings are checked by Deep Frontier's own rule (`RadioactiveTideSettingsCheck.Validate`, only when on), and the state by `RadioactiveTideSavedState`. The import refuses, naming Deep Frontier:

- a missing key, or a value of the wrong JSON type (nothing is defaulted);
- a save with both Deep Frontier's own tide keys and the bridge's settings;
- bridge settings without the history or without `GameCycleService`;
- a game cycle outside the history, or entries out of cycle order;
- a benign stage naming the tide, or a stage with a negative index or days;
- a history with the tide but no bridge settings: the save was played on without Deep Frontier, and Moddable Weathers dropped the bridge's settings.

A Moddable Weathers save that never ran Deep Frontier is not read here: it gets the former mod settings, as a vanilla save does.

## Evidence

- **.NET harness.** Run by `tools/test_fluid_transport.ps1` in a scratch mirror on 2026-11-09, with the terrain overlay and the Moddable Weathers save import: 410,287 assertions in 102 scenarios, 1,198 Mono checks, 5 absence checks, 49 tide Mono checks and 83 Moddable Weathers adapter Mono checks. The flagged Deep Frontier build compiles. The Deep Frontier scenarios cover:
  - registration with both policies and existing localization keys;
  - the v2/v3 import and its variants;
  - the facade, including the new-game pending rule;
  - the formula source text;
  - 408 columns × 70 passes (two hourly passes) equal, bit for bit, a transcription of `RunInteraction`, `Exchange` and `Rescan` with the hour counter;
  - 30 random worlds of `HourlySoilPass` with `NeighborSlot`;
  - `Reconcile`'s soil rule;
  - deposits and credits from every loss kind;
  - soil requests and strict or lenient loads;
  - the tide registration, parsed from `RadioactiveTideTuning.cs`, with each vanilla mode's defaults and 12,000 cycles of C′ draws matching `Choose`, random calls included;
  - the version 4 round trip;
  - the tide import, through the host, for these saves:
    - in a tide, after a tide, before any tide, and older than the tide;
    - the tide switched off;
    - 0.8.3 settings, default and changed by the player, using the legacy rule transcribed with keys and defaults read from `RadioactiveTideTuning.cs` and its text checked in `RadioactiveTideGameSettings.cs`;
    - impossible saved state.

    Each imported save then continues with `Choose`'s draws;
  - the Weather Station import: the radioactive tide mode, a native mode, a station older than the mode, an unreadable station;
  - the import of a save played with Moddable Weathers (the bridge):
    - the bridge's settings type and properties, read from its source;
    - 14 positions in a history with tides at a cycle's end, between benign stages, after a drought stage and after a skipped stage;
    - the settings through the host, switched off and out of range;
    - every refusal listed above;
  - the visibility curve against `Encode`.
  - the irradiated-soil overlay: `IrradiatedSoilSurface`'s constants, `Encode` and `SoilColor` source text; its curve against `Encode` for every soil value from 0 to 1.2 in steps of 1e-6, every float near both ends of the line, and 200,000 random floats; its registration and colour.
- **Mono, against Moddable Weathers 11.0.0.** The Moddable Weathers adapter probe (`ModdableWeathersMonoProbe.DeepFrontier.cs`) writes a bridge save with the real `WeatherHistoryRegistry`, `ModdableWeatherSettingsService` and `GameCycleService`, through the game's JSON writer and reader. For the same 14 positions:
  - Deep Frontier's parse of every stage equals Moddable Weathers' own reading of the save;
  - the cycle's tide agrees with the stage the real `WeatherCycleService` finds;
  - the adapter's load check accepts the import.

  A save with both tide systems' keys is refused.
- **Shipped build.** The unflagged build compiles, and the radiation content, tide content, native safety and native access checks pass.

Not covered by the harness: the game glue (lifecycle, kill check, bank kernels, the soil writer, policies applied by Moddable Fluids in game) and Moddable Fluids' terrain renderer. It compiles; the in-game runs below cover it.

## Requests to Moddable Fluids

Done:

- **Tide state import** (`4b7d7b7`).
- **Visibility curve** (`92ed207`).
- **Custom-intake documentation** (`92ed207`).
- **Additions to reshaped cells** (`92ed207`). Deep Frontier still holds water added before the first fluid tick itself; that hold could now be dropped.
- **Terrain overlay** (user decision 8a, 2026-11-09). Moddable Fluids' terrain overlays (`ModdableFluids.Rendering.TerrainOverlays`) on per-scene terrain material copies. Deep Frontier's flagged build draws its irradiated ground with it and no longer puts its soil variant on the native terrain materials (native-safety audit C2); the flagged package leaves out `IrradiatedTerrainURP`.

Open:

1. **Second water colour (mf-core, optional).** Deep Frontier's variant blends two base and two detail colours (`RadiationMaterials.WaterBaseColorA/B`, `WaterDetailColorA/B`); Moddable Fluids tints by one colour.

## Switch-over plan

The shipped package switches only after every gate below has passed in game. Until then, keep shipping the unflagged build.

### Test packages and the launcher

Build the packages from one commit, with Unity closed, Timberborn closed, and no other official build running (the builds share one Unity project):

```powershell
pwsh tools/build_moddable_fluids.ps1 -MoreFluids    # Moddable Fluids (and More Fluids), kept in outputs/fluids-api-prototype/packages
pwsh tools/build_deep_frontier.ps1 -ModdableFluids  # the flagged Deep Frontier test package, kept in outputs/deep-frontier-moddable-fluids/package
```

`build_deep_frontier.ps1` without the switch is the default shipped build. With it, `tools/build_deep_frontier_moddable_fluids.ps1` runs the same official build with a flagged staging (both builds reuse their last verified asset bundles while the bundle inputs are unchanged: [unity-build-performance.md](unity-build-performance.md)):

- `src/DeepFrontier/ModdableFluids` is staged into `Scripts/ModdableFluids`.
- The staged `DeepFrontier.asmdef` defines `DEEP_FRONTIER_MODDABLE_FLUIDS` for that assembly only (`versionDefines` on the editor version).
- That asmdef references the `ModdableFluids` assembly definition, which `build_moddable_fluids.ps1` stages from `src/ModdableFluids/Api`. More Fluids compiles against it the same way. A precompiled `ModdableFluids.dll` would collide with that assembly definition.
- The manifest requires `ModdableFluids` at the kept package's version, leaves out `ModdableWeathers`, and has " (Moddable Fluids test build)" added to its name.
- All three of Deep Frontier's shader variants (`RadioactiveWaterURP_Opaque`/`_Transparent` and `IrradiatedTerrainURP`, with their `.meta` files) are set aside for the build, because Moddable Fluids draws the water and the irradiated ground. Only `RadiationRenderer` loads them, and it is bound only without the flag.

The official builder only writes into `Mods/DeepFrontier`. The script therefore:

1. **Backs up.** It copies the installed package and the builder's `DeepFrontier*.dll` aside, with hashes.
2. **Verifies the output.**
   - The manifest is the variant.
   - No `ModdableFluids*.dll` or Moddable Weathers bridge is packaged.
   - `DeepFrontier.dll` is the official output, defines the flagged types, and references `ModdableFluids` at the package's assembly version.
   - The builder's `ModdableFluids.dll` is byte-identical to the kept package's.
   - The data and both bundles are in place.
   - The bundles hold no Deep Frontier shader (`tools/asset-pipeline/check_bundle_shaders.py --expect` with no names).
3. **Moves the package out** to `outputs/deep-frontier-moddable-fluids/package/DeepFrontier`.
4. **Restores everything byte for byte**, then puts the default staging back. A restore that does not match stops with its backup named.

One interactive run with the test packages:

```powershell
pwsh tools/start_deep_frontier_moddable_fluids.ps1 [-MoreFluids] [-SaveCopies <path.timber>,...]
```

Before the game starts, the launcher copies aside, with hashes:

- the installed `Mods/DeepFrontier`;
- `Saves` and `ExperimentalSaves`;
- the PlayerData files;
- every `ModEnabled` and `ModPriority` preference value, with its registry type.

It then installs the packages and enables them. It switches Moddable Weathers off for the run, so the tides run on the native weather, and refuses to start while Moddable Weathers is enabled only by default. `-ModdableWeathers` keeps Moddable Weathers on instead, with the mods it requires (Moddable Timberborn, TimberUi, Harmony). The tides then run through Moddable Fluids' optional Moddable Weathers adapter, which the kept Moddable Fluids package must carry. `-SaveCopies` puts copies of the given saves into a settlement named "Deep Frontier Moddable Fluids Test". Click through the startup dialogs, and quit the game to end the run.

Afterwards, also after a crash:

- The test packages leave, and `Mods/DeepFrontier` comes back.
- Preference values come back with their types, and new ones are deleted.
- PlayerData is restored.
- Saves the run made or changed move to `outputs/deep-frontier-moddable-fluids/runs/<time>/evidence`. The save folders then return to their state before the run; the shipped build cannot read a flagged save.
- Every restore is hash-checked, and the game log is in the run folder.

### Gates

Run each with the packages built from one commit, through the launcher above. Load copies of saves only, through `-SaveCopies`.

1. **Moddable Fluids worker fixture.** mf-core's run: `pwsh tools/start_fluid_worker_acceptance.ps1`. It proves the transport, losses and policies in game.
2. **New game, flagged Deep Frontier with Moddable Fluids.** Launch with `pwsh tools/start_deep_frontier_moddable_fluids.ps1`, then check:
   - The log shows the providers registered and Moddable Fluids attached, with no foreign-owner refusal.
   - A Radioactive Spring emits radioactive water, tinted by Moddable Fluids.
   - Pumps in it block at 0.5% with Deep Frontier's status.
   - The sludge intake fills its buffer and makes sludge.
   - The outfall adds water.
   - Soil around the water turns yellow-green; plants there die and planters skip it. The tint is Moddable Fluids' terrain overlay: the log shows its line "Terrain overlays drawn on scene copies of ...". Check cliff tops, sides and edges at several heights, in layer view, with both factions, for pink, black or missing surfaces.
   - Beavers wading in it gain dose; sensors read the share.
3. **Version 4 save and reload in game.** In the same run, save mid-play and reload. Soil cells, water shares, the intake buffer and sources continue, and the loaded soil shows at once. The scene-cycle probe (its launcher with the test packages installed) passes: the native water and terrain materials stay untouched in every game.
4. **Shipped saves.** Run `pwsh tools/start_deep_frontier_moddable_fluids.ps1 -SaveCopies <v3.timber>,<v2.timber>,<exception.timber>,<in-tide.timber>,<0.8.3.timber>` and load each copy. One of them is an exception save. Compare total radioactive volume and soil cells before and after the import, accounting for the reported cutoff volume. Then save and reload as v4. One of the saves is in a radioactive tide. Check the import log line and that the tide continues with its cycle and duration. Also load one save from 0.8.3 or older.

   Then load saves played with the shipped build and Moddable Weathers: `pwsh tools/start_deep_frontier_moddable_fluids.ps1 -ModdableWeathers -SaveCopies <mw-in-tide.timber>,<mw-after-tide.timber>`. One is inside a radioactive tide stage, one after it.
   - The log shows "Radioactive tide of Deep Frontier's Moddable Weathers weather imported into Moddable Fluids" with the bridge's settings, then "Tides run as Moddable Weathers weathers".
   - Nothing is refused: the adapter's history check accepts the import.
   - The tide in progress runs to its stage's end and emits radioactive water.
   - Save, quit and reload: the save now loads from Moddable Fluids' own keys.
5. **Tide.**
   - Use Moddable Fluids' "next cycle" development method for the radioactive tide.
   - Check the banner, icons and badtide sound.
   - Check that every tide-overridable source emits radioactive water and that springs stay radioactive.
   - Check the Weather Station: Moddable Fluids' radioactive tide mode switches on during the tide (and early, by its activation hours). A station saved by the shipped build in the radioactive tide mode loads in that mode: load it through `-SaveCopies` in gate 4.
   - The all-buildings hazard probe's station part refuses to run in this build; it checks Deep Frontier's own station mode.
   - Save and reload during the tide.
   - Repeat the development method, the banner and the emission once with `-ModdableWeathers`. The tide is then a Moddable Weathers weather drawn from Deep Frontier's spec.
   - Check that a new custom game's rows show Deep Frontier's values.
6. **Performance.** Tick time and memory on the largest Deep Frontier map with a large irradiated area, against the shipped build. Run once with `-MoreFluids`, so that the shared tide budget and the More Fluids content run alongside.

### Steps

1. **Package.**
   - Make the test build's flagged staging the default. That is the staged `Scripts/ModdableFluids`, the asmdef with its define and reference, and the manifest.
   - Delete all three shader variants from `src/DeepFrontier/AssetBundles/Resources/Shaders/DeepFrontier`, which the test build already leaves out, with `RadiationRenderer`, both of its surfaces and `tools/native_shader_variants.mjs`.
   - Fold its package checks into `tools/verify_deep_frontier_package.ps1`. That script then compares the installed package with the builder output, as it does now.
2. **Manifest.**
   - Add `{ "Id": "ModdableFluids", "MinimumVersion": "<first release>" }` to `RequiredMods` and bump the version.
   - Remove `ModdableWeathers` from `OptionalMods`, and the `DeepFrontier.ModdableWeathers` bridge from the package, as the test build does. Moddable Fluids' own Moddable Weathers adapter registers the radioactive tide under the same weather ID, `RadioactiveTideWeather`. `ModdableWeatherSpecs/RadioactiveTideWeather` stays: the adapter draws the tide with it. Saves played with the bridge are imported ([Saves played with Moddable Weathers](#saves-played-with-moddable-weathers)).
3. **Validators.**
   - `tools/validate_radiation_content.mjs` and `validate_radioactive_tide_content.mjs` read the shipped `RadiationSimulation`, `RadiationSoil` and tide files. Point them at the flagged equivalents.
   - Remove `DeepFrontier.RadiationLockstep`, `.RadiationSoil`, `.RadioactiveTide` and `.RadioactiveTideNewGame` from the native-safety audit.
4. **One release with both paths.** Ship the flagged build while the unflagged code still compiles. It is the rollback build. Delete the old classes in the release after that.
5. **Status.** Record the gates and the switch in `tools/STATUS.md`.

### Rollback

The old package cannot read what the flagged build writes:

- `DeepFrontier.Radiation` version 4;
- radioactive water held only in `ModdableFluids.World`;
- tide state under `ModdableFluids.Tides`.

Loaded into the old package, such a save stops at version 4, and its radioactive water would read as fresh. The rollback build is therefore the last unflagged package plus two readers, added before the switch:

- **Water.** A version 4 reader in `RadiationSimulation` that takes `r` per column from `ModdableFluids.World` (radioactive volume over physical volume, by fluid ID) and soil from version 4.
- **Tide.** A reader that maps `ModdableFluids.Tides` and `ModdableFluids.TideSettings` back to Deep Frontier's tide keys.

With those, roll back by republishing the rollback build. Saves keep their radiation, and Moddable Fluids can then be disabled.
