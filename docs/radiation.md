# Radiation: radioactive water, contaminated stores and irradiation

Status 2026-10-22: **one-fluid model, staged in `outputs/radiation-onefluid/` only.** It replaces the two-layer model (sludge as its own fluid) that build 122 ships. Compile-checked with the whole Scripts tree and run through the shipped native water tasks in a scratch harness. Nothing here has been built, launched or played; `tools/STATUS.md` records runtime verification.

## Model: one fluid

Every native water column holds one body of water split into **fresh + bad + radioactive**, summing to 1.

- **Badwater share b:** native `WaterColumn.Contamination`, unchanged.
- **Radioactive share r:** kept by `RadiationSimulation` per native column, moved by the native contamination kernels in lockstep. Radioactive volume = r × water volume.
- **Fresh:** 1 − b − r. Checked within `RadiationTuning.ShareTolerance` (1e-5); past it the game throws.
- **RadioactiveSludge** stays a barrelled good: 0.2 radioactive volume per good.
- There is no second fluid, no sludge mesh and no sludge simulation.

Internal native types and private members are compiled against the publicized ModsBuild assemblies. That is valid at runtime only because `Scripts/DeepFrontier.asmdef` has `"allowUnsafeCode": true` (SkipVerification); see `outputs/radiation-mono-access-probe`.

### Native code that changes contamination, and the r rule

Source: decompiled `Timberborn.WaterSystem` 1.1.2.8. Rules live in `RadiationMixing.cs`.

| Native path | What it does to b | r rule |
|---|---|---|
| `SimulateContaminationTask` + `UpdateContaminationTask` (advection, diffusion) | volume-weighted mix along the substep's outflows, diffusion between near-still neighbours, clamped to 0..1 | the same native tasks run on a shadow column array whose Contamination slot is r (`RadiationLockstep`) |
| — kernel exceptions | advection: a column whose retained weight (depth − received) is negative, a thin film that drained and evaporated more than it held, extrapolates and clamps; diffusion: per-partner `min()` limits differ between columns with different partner counts | b + r can exceed 1 in exactly these cases (harness). `KernelExcess`: r is reduced to 1 − b and the excess radioactive volume goes into the soil; counted in `KernelCorrections` |
| `WaterParametersUpdateTask` (evaporation) | none: evaporation lowers depth and keeps the share, so the evaporated water carries its contamination away | evaporated radioactive volume (r × native evaporation, `EvaporatedVolume`, equal to native within 5e-8) goes into the soil, so a pond that dries out leaves irradiated ground |
| `UpdateWaterSourcesTask` (badwater and clean sources) | (b·I + bSource·(F − I)) / F per source cell, after the kernels | `MixSource`, the same formula with rSource. The source cells are recorded before the sources run (prefix) and restored for the r kernels, so r sees the native order |
| `UpdateWaterChangesTask` (dumps, pumps, workshops, `AddRadioactiveWater`) | clean and contaminated volumes, each clamped at 0, then b = bad / total | `ReplayChange` replays each change on (clean, bad, radioactive), radioactive water counting as clean water. Clean removals (pumps) take radioactive water at the clean water's own mix; the replayed b equals native within 1e-6 |
| `WaterSimulator` geometry (split, merge, raised floor, removed column) | split copies b, merge averages by depth, deleted water is gone | `Reconcile` does the same for r; the radioactive volume of deleted water goes into the soil of the lowest open column |
| Off-map padding | water flowing into the padding ring leaves the map | leaves with the water |
| Decay | — | 365-day half-life on r |
| Cutoff | none: no kernel drops small contamination (`UpdateContaminationTask` clamps only at the maximum and zeroes only dry columns) | below `DetectionLimit` 0.005, r is gone (next section) |

### The 0.5% cutoff (one threshold)

Design decision 2026-10-22: "make the radiation act like badwater then. If it is below 0.5 percent then it is gone."

`RadiationTuning.DetectionLimit = 0.005` is the only water-share threshold.

**Removal.** `Rescan` is the last step of the late tick, after the lockstep's mixing, decay and soil washout. There, a column whose share is below 0.005 and did not grow since the last late tick is set to 0. This is deliberately not conserved.
- A share that is still growing keeps accumulating, reading 0 until it reaches 0.005. This covers a source, leak, outfall or tide filling deep water.
- Without that exception, a 1% tide source of strength 1 pouring into water deeper than about 0.6 would be cut back to 0 every tick and never show.
- Once the share stops growing below 0.005 (dilution, decay, stagnation), it is removed. A diluted plume therefore vanishes within a few ticks.
- `_radPrevious` holds the previous value; it is not saved.

**Readers.** Every reader sees a share below the limit as 0 (`RadiationTuning.Detected`):
- `Sample`, `GetRadiation`, `ColumnRadiation` and `IsColumnContaminated`;
- pumps: they refuse at 0.005 or more and resume when the share reads 0, with no second resume threshold;
- barrels turning to ContaminatedWater;
- beaver water dose;
- the soil target min(1, 4r), the bank field and the moisture shadow;
- the Contamination Sensor;
- the water tint (`RadiationShading`), whose visibility runs log-scaled from 0.12 at 0.005 to 1 at r = 1.

**Saves.** Loaded shares below 0.005 are zeroed (versions 2 and 3). There is no new save data.

**Native evidence (1.1.2.8).** Native badwater never deletes small contamination; it only hides or ignores it:
- the water renderer stores contamination as a byte, `(byte)(255 × c)` in `UpdateWaterTexturesTask`, so c < 1/255 ≈ 0.39% renders as clean water;
- beavers catch badwater only at c ≥ 0.05 (`ContaminationApplier.MinimumWaterContamination`);
- pumps and workshops switch at 1e-4 (`WaterMover`, `WaterInput*ManufactoryLimiter` `EfficiencyThreshold`), the former radiation detection limit;
- soil moisture reacts from 0.01, soil contamination from 0.5.

The 0.5% cutoff is therefore a Deep Frontier rule, close to the native render floor.

Soil radiation s (0..1) decays with a 120-day half-life and spreads slowly, as before. Soil is a hazard level capped at 1, so radioactive volume deposited beyond saturation is not tracked. How water changes it is in the next section.

### Soil: moisture, irradiated banks and washout (`RadiationSoil.cs`)

Status 2026-10-22: compile-checked; the native soil kernels and the exchange were run in the game's Mono 6.13 by `outputs/radiation-soil-harness` (`harness-result.txt`). Not built or played.

The native rules come from decompiled `Timberborn.SoilMoistureSystem` and `Timberborn.SoilContaminationSystem` 1.1.2.8 (`outputs/soil-native-1.1.2.8`), with vanilla specs.

**Native moisture.** `MoistureCalculationTask` reads the water column's `Contamination` c:
- c < `MinimumWaterContamination` 0.01: full range, 2 × cluster saturation (up to 16);
- c ≥ `MaximumWaterContamination` 0.53: no range;
- between them: `(int)(range × (1 − c/0.53))`;
- a cell's moisture is multiplied by 1 − c of the water standing on it.

Before this change the native columns carried only b, so radioactive water irrigated like fresh water.

**Moisture fix.** A Harmony prefix on `SoilMoistureSimulationTaskStarter.StartTask` (editor-excluded) replaces its `in waterColumns` local with a copy of the thread-safe columns whose `Contamination` is b + r (≤ 1). Only the moisture tasks see this copy. With it:
- pure radioactive water irrigates nothing;
- mixed water irrigates by the native badwater rule on b + r;
- clean water and badwater are unchanged;
- tide water (r = 1) irrigates nothing; mixed water downstream irrigates only by its clean share.

The copy is built only while radioactive water exists. It costs one copy of the thread-safe array per tick, as large as native `ThreadSafeWaterMap.Update`.

**Native soil contamination.** Native soil contamination is a field recomputed every tick from the water.
- Next to water: 2 × (c − 0.5), so water below c = 0.5 contaminates nothing.
- Each step away costs 1/7 orthogonally and √2/7 diagonally (`MaxRangeFromSource` 7).
- Each level uphill costs 5/7; downhill costs nothing. Soil barriers block it.
- The level follows the candidate at +0.035/s and −0.01/s. Levels below 0.001 are 0.

It has no washout and stores nothing. Under clean water, or on dry land, it falls at −0.01/s.

**Irradiated banks.** The shipped `ContaminationCandidatesCountingTask` and `ContaminationsUpdateTask` run, with the native per-tick parameters read from the native starter, on shadow arrays.
- In the shadow, a water column with r ≥ 0.005 carries c = 0.5 + T/2, where T = min(1, 4r) is the existing soil target. Every other column carries 0, so badwater is ignored.
- The kernels run on the radiation rows + 6, plus rows whose banks are still clearing.
- The resulting level is the **bank layer** (`RadiationSoil.BankAt`). Every reader (sample, beaver dose, plants, tint) sees max(soil, bank). The bank is never written into the stored soil.
- Banks rise and clear exactly like native contaminated banks: up at +0.035/s; down at −0.01/s × 0.6 s = 0.006 per tick once the water is clean. A bank of 1 next to a pond that turns clean drops below the tint threshold after 5.0 game hours and reaches 0 after 5.2 (harness).
- Bank levels are not saved. After a load they rebuild in about 1.5 game hours while the water is still radioactive.

Steady levels by tiles from the water's edge on flat ground (harness):

| Water share r | Level by tile | Reach |
|---|---|---|
| r ≥ 0.25 (T = 1) | 1, 0.857, 0.714, 0.571, 0.429, 0.286, 0.143 | 7 tiles |
| r = 0.1 | 0.4, 0.257, 0.114 | 3 tiles |
| tide r = 1 | 1 | 7 tiles (a full radioactive bank) |

A bank one level above the water top gets 0.286, then 0.143.

For a pure radioactive pond:
- plants die within 7 tiles (every bank level is at least 0.05, the irradiated-ground threshold);
- beavers (threshold 0.05) are dosed within 7 tiles, at most 0.25·s/h;
- the bank reaches its level in about 1.5 game hours, at the native rise.

Dose rates and thresholds are unchanged.

**Ground under water: rinsing and exchange.** Any wet column counts as contact, as natively. There is no depth or film threshold.
- **Clean water** (the share reads 0, below 0.005) rinses the stored soil at the native recovery rate: 0.006 per tick = 0.192 per game hour, at any depth.
  - The water takes the washed volume up to `RinseShareCap` (0.0025, half the limit), so rinse water never reads radioactive and pumps keep running.
  - The rest counts as diluted below the cutoff and is gone, as the cutoff removes it from flowing water anyway.
- **Radioactive water** exchanges with the soil, conserved (0.1 radioactive volume per unit of s), toward the equilibrium s = min(1, 4r). It never overshoots, so it cannot oscillate.
  - s rises at the existing +0.05/h, drawing that volume from the water: a depth-1 r = 1 pond saturates its bed in 20 h and keeps r = 0.9.
  - s washes out at the native rate into the water's share: standing r = 0.05 water over soil 1 settles at s = 0.43, r = 0.107.

What happens to fully irradiated ground under clean water (harness, any depth from 0.001 to 3):

| Measure | Result |
|---|---|
| Tint gone (s < 0.05) | 4.97 game hours |
| s = 0 | 5.22 game hours |
| Water share | peaks at 0.0025, reads 0 |

Before this, the washout took 72–81 hours, and the tint (full at s ≥ 0.5) did not change for the first 36 of them, which read as "rinsing does nothing".

**Dry ground** keeps its stored soil and only decays (120-day half-life) and spreads, as before.

**Non-conserved inputs.** Only existing deposits beyond saturation are not drawn from any water. Banks are a transient layer and add nothing to the stored soil.

### Plants on irradiated ground (`IrradiatedPlantWarning.cs`)

User rule 2026-10-22: "Irradiated ground should kill plants immediately."

- **Irradiated ground** is `SoilAt` (stored soil or bank layer) of 0.05 or more (`RadiationTuning.IrradiatedGroundThreshold`). This is exactly where the yellow-green ground tint starts (`IrradiatedSoilSurface.MinRenderedSoil`), so what the player sees is what kills.
- **Death path:** native `LivingNaturalResource.Die`, where native badwater and drought deaths end (`ContaminatedNaturalResource` and `WateredNaturalResource` call it from a time trigger). Native `Died` listeners then take over:
  - `Growable` stops;
  - `Crop` and the dead models switch;
  - `DeadCuttableYieldRemover` and `EmptyDeadNaturalResourceOverrider` make the remains clearable.
  Nothing is deleted.
- **When:**
  - the tick ground becomes irradiated under a standing plant. `RadiationSimulation.KillOnIrradiatedGround` runs after `Rescan` on the rows holding soil radiation or banks, and checks a slot when it turns irradiated or its column geometry changes;
  - when a plant is planted or spawns there (`IrradiatedGroundDeath.PostInitializeEntity`, after every native `InitializeEntity`);
  - natural spreading never seeds irradiated ground (`IrradiatedGroundSpawnValidator`, as native `ContaminatedNaturalResourceSpawnValidator` does for badwater soil).
- **Planting warning:** the planting tooltip and plant panel say plants there die immediately. Planting stays allowed.
- **Affected area:**
  - under radioactive water from r = 0.0125 (4r = 0.05);
  - on banks within 7 tiles of r ≥ 0.25 water;
  - within 3 tiles of r = 0.1;
  - the 100% tide kills plants under and beside its water, like any pure radioactive water;
  - deposits (evaporation, spills, meltdown and waste-leak soil) kill wherever they reach 0.05.
- **Recovery:** rinsing (5.2 h) or bank clearing below 0.05 stops the killing at once. Replanting then survives.
- **Saves:** no new data. Plants on irradiated ground in an old save die on the first tick.
- **Cost:** one block lookup per slot when it turns irradiated, on tracked rows only. No per-plant work.

### Sources and sinks

| Path | Implementation |
|---|---|
| `AddRadioactiveWater(cell, volume)` (outfall, spills, meltdown, waste leaks, continuous sources) | native `IWaterService.AddCleanWater` plus a record promoted with the native change queue (postfix of `WaterChangeService.Tick`); the replay gives that change r = 1 |
| Radioactive Spring | a native water source (DevWaterSource clone with `WaterSourceSpec`, `WaterSourceContaminationSpec` 0, no badtide controller) plus `RadioactiveWaterSourceSpec {RadioactiveShare: 1}` |
| Radioactive tide | `SetSourceRadioactiveShare`: every native source's added non-bad water carries r = `SourceRadioactiveShare` 1 (19.2 radioactive volume per strength-hour from a clean source) |
| Sludge Recovery Pump | native `WaterInput.DemandCleanWaterAmount` (the pump path). The replayed removal reports its radioactive volume; the pump buffers it (saved) and makes 1 good per 0.2. Water demand = shortfall / (r / (1 − b)), at most `MaxWaterPerCycle` 4. The fresh water pumped with it is used up. The buffer returns as radioactive water when the pump is deleted |
| Waste Export, refinery | recipes unchanged |

### Gameplay hooks

| Need | Implementation |
|---|---|
| Pumps refuse | `RadiationIntakeGuard` on native `WaterInput` blocks when r ≥ 0.005 (`DetectionLimit`) at the intake and resumes once the share reads 0 (no second threshold). Its entity panel shows "Water at the intake: x% fresh, y% bad, z% radioactive". Inert on the recovery pump |
| Barrels and tanks | unchanged: Water in irradiated storage becomes ContaminatedWater; a Water tank switches on any pass |
| Deleting waste storage | refused (2026-10-29, user decision): any native Stockpile holding RadioactiveWaste, RadioactiveSludge or ContaminatedWater has `HazardousStorageDeletionBlocker`, a native `IBlockObjectDeletionBlocker` like the fixed-stockpile one. The panel's delete button is disabled with the reason and the deconstruction tool skips it until the stock is moved out (Empty storage, or another good selected); then it can be deleted. ContaminatedWater can be selected in any tank, so a contaminated water supply can be emptied into new barrels. |
| Contamination Sensor | native sensor with a per-sensor "Measures" choice (`Scripts/Sensors/`): Badwater (native, default), Radiation (r of the measured column) or Any contamination (b + r), rounded to the native 1% precision and compared against the native threshold and mode. The native panel shows the selected reading; the choice panel adds "Radiation: x%". Saved per sensor; saves without it load as Badwater. Below 0.5% the radioactive share is 0 (the cutoff); the native 1% rounding then reports 0.5–1.5% as 1%, the same threshold pumps use |
| Sluice (Sluice is Back! 11.0.0, optional mod) | the same "Measures: Badwater / Radiation / Any contamination" choice for the sluice's "close above / below x% contamination" automation, in the optional assembly `DeepFrontier.SluiceIsBack` (`Scripts/SluiceIsBack`, shipped as `Scripts/DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional`, loaded by Moddable Timberborn only with the mod). A postfix on the mod's private `Sluice.GetContamination()` substitutes r or b + r of the source column, rounded like the mod (`Math.Round(x, 2)`); a postfix on `SluiceState.SetState(neighbor, minLimit)` copies the choice between synchronized sluices and on copy-settings. Default Badwater; saved under `DeepFrontier.SluiceContaminationSubstance`; the panel adds the dropdown and "Radiation: x%" after the mod's fragment |
| Stream Gauge | display only (no automation output, no threshold), so no choice: its panel gains "Radiation: x%" for the gauge cell next to the native badwater "Contamination" (`Scripts/Sensors/StreamGaugeRadiationPanel.cs`) |
| Weather Station | a fourth mode "Radioactive tide" (`Scripts/WeatherStations`): On while the cycle's hazardous weather is the tide and it has started, or earlier by the native early-activation hours. Works on the vanilla tide and the Moddable Weathers tide (both are the cycle's `IHazardousWeather` with id `RadioactiveTideWeather`). The native Temperate/Drought/Badtide modes are unchanged; the choice is saved under `DeepFrontier.WeatherStationRadioactiveTide` |
| Swimming Pool, Fish Hatchery (native `ContaminationBlockableBuilding`, blocks above 5.5% badwater) | not changed: radioactive water does not block them. Pumps and showers with a `WaterInput` are blocked by `RadiationIntakeGuard` |
| Irradiated beavers | dose outside buildings: water 60·r/h (r = 1 is as harmful as sludge was), soil 0.25·s/h when s ≥ 0.05 |
| Hospital, sickness, kits | unchanged: 10-day hospital course, 8-day untreated death, kit-to-adult carry-over |
| Plants | irradiated ground kills at once (next section) |

### Visibility

Drawn by the native surfaces, with no overlay meshes (`RadiationShading.cs`, `RadiationRenderer.cs`, `tools/native_shader_variants.mjs`; compile-checked and statically validated only, not yet built or seen in game).

- **Native mechanism** (decompiled `Timberborn.WaterSystemRendering` and `Timberborn.TerrainSystemRendering` 1.1.2.8). Water: `UpdateWaterTexturesTask` writes `byte(255 × Contamination)` into `WaterRenderer._contaminations` (`DataTextureArray<byte>`, R8, layer = column index, pixel x + y·width, old and new arrays), published as `_OldContaminations`/`_NewContaminations`; the `WaterContamination` subgraph of `PhysicalWaterURP_Opaque`/`_Transparent` samples them (old/new lerped by `_TickProgress`, blended with linked neighbours) and applies `Lerp(clean albedo, contamination colour, smoothstep(0.01, 1, c)^0.25)` plus emission, metallic, smoothness and normal. Soil: `TerrainMaterialMap._contaminationMapTexture` (RG16 `PixelData`, R old, G new, layer = terrain z) as `_ContaminationMap`, blended in by the `SoilContaminationVisualization` subgraph of `TerrainURP`. Neither texture has a spare channel.
- **Variants.** `tools/native_shader_variants.mjs` copies those three native graphs from the official modding tools and adds a second instance of the graph's own contamination subgraph, fed from Deep Frontier texture arrays in the native layout (`_DFOld/NewRadioactivity`, `_DFIrradiatedSoilMap`) with its own colours, lerped over the native result. Reflections, transparency, foam, flow, waterfalls and level visibility are the unchanged native graph. Global multi_compile keywords (`_DEEP_FRONTIER_RADIOACTIVE_WATER`, `_DEEP_FRONTIER_IRRADIATED_SOIL`) are on only while radiation is drawn; off, the variant is the native code. The native shader_feature keywords that the native materials enable (`_CALCULATE_OUTFLOWS`; `_USELAYERTOOL`, `_SAMPLE_SPLATMAP`, `_USE_TRIPLANAR_SPLATMAP`) compile as multi_compile. Output: `src/DeepFrontier/AssetBundles/Resources/Shaders/DeepFrontier/*.shadergraph`, bundled by the Mod Builder.
- **Materials.** In PostLoad the renderer sets the variants on the native `PhysicalWater_Opaque`/`_Transparent` (from `WaterMeshSpec`) and the five `TerrainURP` materials (`Grass`, `Cliff`, `CliffEdge`, `SlopeCliff`, `SlopeCliffEdge`, from the material repository), and restores the native shaders on unload. `RadiationShading.Verify` (Load) and each swap throw if the native members, shader names, material keywords or any native shader property changed.
- **Radioactive water:** one surface per tile. The stored value is the inverse of the native contamination curve applied to the wanted lerp weight w = visibility(r) × r / (b + r), so the colour mixes with badwater by share and pure radioactive water is fully yellow (base colours 0.50/0.56/0.04 to the radiation yellow 0.86/0.92/0.08, a yellow-green detail glow at the native glow luminance). Visibility is log-scaled from the detection limit: 0.12 at r = 0.005 (`RadiationTuning.DetectionLimit`), 1 at r = 1; below it nothing is drawn. Reflections are the native contaminated-water reflections.
- **Irradiated ground:** the native soil-contamination veins, tinted yellow-green (SoilVeinColor), wherever s ≥ 0.05; the map value follows the native soil rule (0.1 at the first visible level, 1 from s = 0.5).
- **Updates.** Per tick, after `RadiationSimulation.Tick`, for the radiation rows plus rows still settling; old/new follow the native update rules (newly wet water shows at once; a soil change moves G to R and settles next tick); only changed layers upload, through the native buffer + `Graphics.CopyTexture` path. Nothing runs per frame.
- **Radioactive Spring:** the native source model in the radioactive material.

### Cost per tick

Rows that hold radiation (plus margins); idle cost is zero, as before.

| Work | Two-layer (build 122) | One fluid |
|---|---|---|
| Sludge simulation | 2 substeps × (full `_sludgeBase` clear + `OutflowsUpdateTask` + `WaterParametersUpdateTask` over sludge rows), the two heaviest native water kernels | none |
| r lockstep | 2 × (copy, clear, `SimulateContaminationTask`, `UpdateContaminationTask`, harvest) | the same 4 row passes ×2, plus two O(source cells) single tasks; the copy also computes evaporation for cells with r > 0 |
| Water changes | — | O(changes) per tick (prefix + postfix) |
| Main thread | geometry mirror and reconcile for sludge, radiation and soil; dissolving and soil uptake; rescan | geometry mirror and reconcile for r and soil; decay; soil rinse, exchange and bank layer (RadiationSoil); rescan; while radioactive water exists, the soil shadows (one full thread-safe column copy for moisture, the field rows for the soil kernels) |
| Memory | sludge columns, sludge outflows (with lists), base flows, one `List<DirectedFlow>` per 2D cell | dropped; one `bool[]` source-cell flag added |

12 → 8 row passes per active row per tick, and the outflow and parameter kernels are gone.

## API (`IRadiationService`)

```csharp
void AddRadioactiveWater(Vector3Int cell, float radioactiveVolume);   // native add path, r = 1
int  AddContinuousSource(Vector3Int cell, float volumePerHour, float durationHours);
void RemoveContinuousSource(int id);
void AddSoilRadiation(Vector3Int cell, float amount);
void SetSourceRadioactiveShare(float share);   // the tide; 0 = off
float WaterPerStrengthHour { get; }            // 19.2 in 1.1.2.8
bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell);
RadiationSample Sample(Vector3Int cell);       // r, b, fresh, Submerged, soil
float GetRadiation(Vector3Int cell);
bool IsColumnContaminated(Vector3Int cell);    // r >= DetectionLimit (0.005); Sample/GetRadiation read smaller r as 0
float TotalWaterRadiation { get; }
bool SavedStatePending { get; }                // from a save's Load until the first frame applies its radiation
```

Removed: `AddSludge`, `AddSource`, `AddWaterRadiation`, `QueueSludgeRemoval`, `CancelSludgeRemovals`, `ISludgeRemovalReceiver`, `SludgeVolumeInColumn`, `TotalSludgeVolume`.

## Saves

Singleton `DeepFrontier.Radiation`, **version 3**: per-column `(x, y, floor)` with r and soil; continuous sources; NextSourceId; hour accumulator.

- **Version 2** (build 122: sludge as its own fluid) is converted explicitly. Sludge becomes radioactive water added at its cell through the native add path on the first tick. The dissolved share becomes r = r₂ × (1 − b).
- **Version 1** is rejected. No loadable version-1 save can exist: build 121 crashed on every game-scene load, and builds up to 120 had no radiation (build 120's package has no sludge good, outfall or pump; the radiation scripts were written after build 120 was checked).
- Plant dose (`DeepFrontier.RadiationFloraDose`, saves up to 2026-10-22) is read and discarded by `IrradiatedGroundDeath.Load`. The plant then dies on the first tick if it stands on irradiated ground. Other entity data is unchanged: beaver dose and clocks, and the pump buffer (`DeepFrontier.RadioactiveSludgeIntake.Buffer`, now radioactive volume, same units).
- A version-2 Radioactive Spring loses its strength: the old `DeepFrontier.RadioactiveSpring.Strength` key is no longer read, and the native source starts at the blueprint default.

### Exception saves (crash saves)

Build 145 crash: the native exception save failed with "Radiation can only be saved between parallel ticks".

**Native evidence (1.1.2.8):**
- `GameSaver.Save` runs `Ticker.FinishFullTick` first: `TickableBucketService.FinishFullTick`, then `ForceFinishParallelTick`. Normal saves therefore never arrive mid-tick.
- `GameSceneExceptionStateSaver.CreateExceptionSave` (Timberborn.GameScene) calls `TickOnlyArrayService.ForceAllowAccess()` and then `GameSaver.SaveWithoutFinishingTick`, which writes at once. The parallel tick runs across frames, so a crash in any frame update arrives while worker threads may still be running the lockstep tasks. After a worker exception, those tasks are abandoned: `Parallelizer.ThreadStart` stops taking tasks once an exception is queued.
- The parallelizer has no per-handle wait. `ParallelizerHandle` only offers `ContinueWith`, and `Parallelizer.Wait` waits for every pending task and throws on worker exceptions. Waiting deterministically is therefore impossible in the crash path.

**Mechanism:**
- Every completed late tick (and the applied save in `UpdateSingleton`) ends with `TakeSnapshot` on the main thread. It records what a save writes: cells with r or soil (reused lists, rows with radiation or soil only), the continuous sources, NextSourceId and the hour accumulator.
- `Save` recognises the exception saver by `TickOnlyArrayService._forceAllowAccess`; the member is checked by reflection at load. When that saver arrives mid-tick, or inside an unfinished radiation `Tick`, `WriteSnapshot` writes the last completed tick plus `LastCompletedTickSnapshot = true`, and never throws.
- An exception save between ticks writes the current state, falling back to the snapshot if that fails.
- A mid-tick save without the marker still throws, which keeps the strict guard for normal saves.
- Still save version 3; the new key is optional.

**Loading a snapshot save:**
- Its r comes from the last completed tick, while native water was written mid-tick.
- A saved cell whose floor no longer exists (geometry queued during the crashed tick) is dropped instead of throwing.
- r is capped at 1 − b where native badwater moved in.
- Both counts are logged. Other saves load strictly.

**Acceptance (not testable on demand):** a crash while radiation is present produces an exception save. In `Player.log`, "Creating an exception game save" appears with no "Failed to create an exception game save". Loading that save logs the "loaded an exception save holding the last completed tick" line, and the radioactive water and soil are back.

## Files (staged)

- `outputs/radiation-onefluid/Radiation/` replaces `src/DeepFrontier/Scripts/Radiation/`. `RadiationMixing.cs` is new. `RadiationSoil.cs` (moisture, irradiated banks, washout) was added in `src` directly; `outputs/radiation-soil-harness` is its harness.
- `outputs/radiation-onefluid/Meltdown/MeltdownService.cs`, `WasteLeak.cs`: `AddSludge`/`AddWaterRadiation` → `AddRadioactiveWater`.
- `outputs/radiation-onefluid/RadioactiveTide/RadioactiveTideService.cs`, `RadioactiveTideTuning.cs`: a radioactive share of the source water instead of emitted sludge (`SludgePerStrengthHour` keeps its name; it is now radioactive volume).
- `outputs/radiation-onefluid/tools/radiation_content.mjs`, `validate_radiation_content.mjs`.
- `outputs/radiation-onefluid/harness/`: invariant harness (`harness-result.txt`).

## Open questions

- **Native surfaces.** Does the Unity build compile the three variants (variant count and build time are unmeasured), and in game: one blended surface per mixed tile, clearly yellow pure radioactive water, unchanged clean and badwater, no flicker on save/reload? The colours are first guesses.
- **Kernel corrections.** How often do thin films and diffusion trigger `KernelExcess` in a real map? The counter is exposed for acceptance.
- **Pressurised columns.** Water changes on overflowing columns, which have overflow pressure under ceilings, use the effective depth as native does. The harness covers non-overflowing columns only.
- **Balance.** Recovery pump water demand (`MaxWaterPerCycle`), exposure 60·r/h, the tide share.

## Radioactive tide (optional hazardous weather)

Status 2026-10-22: source written, compile-checked and generated in a scratch copy only. Nothing is built, installed or tested in game; `tools/STATUS.md` records runtime verification.

User request: a contaminated weather "like badtide but with the radioactive waste", only after at least 15 cycles, and an option the player can turn off.

### Behaviour and numbers

| Item | Value |
|---|---|
| Weather id | `RadioactiveTideWeather` (third native `IHazardousWeather`) |
| Earliest cycle | 15 by default (setting 2–100) |
| Chance | 25% per cycle by default (setting 1–100%), tested after the native drought/badtide roll and replacing it |
| Consecutive tides | never: a tide cannot follow a tide (`CooldownCycles` 1) |
| Duration | 3–6 days by default, uniform whole days (settings 1–30 each; shortest ≤ longest, else loading or the next cycle throws) |
| Emission | 100% of the source's own non-bad water (`SourceRadioactiveShare` 1, as a badtide makes source water fully bad): 19.2 radioactive water units per game hour per unit of current strength from a clean source |
| Water | sources keep flowing; all of their non-bad water is radioactive (a badwater source keeps its bad share). They are neither dried (drought) nor turned bad (badtide) |
| Sky | yellow-green fog per day stage at the native density 0.003 |

- **Scale.** A strength-1 native source pours 19.2 water units per game hour (strength per simulated second; 0.6 s ticks, 768 ticks per day). The radioactive share is 100% of its non-bad water (`SourceRadioactiveShare` 1, by user decision 2026-10-22: the tide behaves like a badtide of radiation).
  - One strength unit of a clean source releases 19.2 radioactive units per hour, 461 per day.
  - Every clean source becomes a full radioactive spring for the tide's duration: pumps on its water refuse, its banks irradiate (and kill plants), and wading beavers take the full 60/h dose.
  - A 5-day tide on a map whose sources total strength 12 releases about 27,600 radioactive units (276 at the earlier 1%).
  - Pure tide water doses a wading beaver at the full 60 per hour.
  - Soil under and beside tide water saturates (4r capped at 1), so plants die under it and on its banks out to 7 tiles, and irradiated ground needs rinsing (about 5.2 game hours of clean water) after the tide.
  - Tide water does not irrigate (r = 1 is above the native 0.53 moisture limit); mixed downstream water irrigates only by its clean share.
  - Pumps refuse wherever tide water reaches their intake at 0.5% or more, i.e. effectively on every river fed by a source until the tide ends and the water is flushed.
- **Which sources.** Every native water source: `RadioactiveTideService.Tick` sets `IRadiationService.SetSourceRadioactiveShare`, and the native `UpdateWaterSourcesTask` adds the water. `CurrentStrength` already applies the native modifiers, so closed regulators, unpowered aquifer drills and weather-gated badtide drains release nothing.
- **Emission choice.** A share of the native source water rather than `AddContinuousSource`, so it follows live strength changes, stops exactly when the cycle ends (share 0) and is never saved twice.
- **Afterwards.** The radioactive water stays: it drains off open map edges, decays with the 365-day half-life, leaves irradiated ground where it dries, or is recovered by the Sludge Recovery Pump. Pumps refuse to run wherever radiation reaches their intake.
- **Settings.** The options use eMka.ModSettings (Deep Frontier → "Radioactive tide": enabled, earliest cycle, chance %, shortest and longest tide). They are global and changeable in the main menu only. Each cycle's selection reads them live. A tide that is already chosen continues if the option is later turned off.
- **Dev mode.** "Deep Frontier: radioactive tide next cycle" forces the next cycle's tide. It ignores the earliest cycle, the chance and the cooldown, and is not saved.

### Native evidence (Timberborn 1.1.2.8, `outputs/weather-api-1.1.2.8`)

Hazardous weather is not a registry, so a third weather needs Harmony:

- `HazardousWeatherRandomizer` and `HazardousWeatherService` take `DroughtWeather` and `BadtideWeather` as constructor arguments. No `IHazardousWeather` is multi-bound.
- `HazardousWeatherService.Save` writes only `IsDrought`, and `Load` turns false into badtide.
- `HazardousWeatherUIHelper.UpdateCurrentUISpecification` throws "No UI for weather" for any other type. Its UI specification interface is internal.
- `HazardousWeatherSoundPlayer` throws "No start sound for weather type".
- `Sun.GetFogSettings` throws without a fog for the weather id. This one is data: `SunSpec.*.HazardousWeatherFogs#append`, merged by the native `JsonMerger`, which recurses into nested objects.

The patches are applied at mod start after `RadioactiveTidePatchTargets.Verify()` and `RadioactiveTideNative.Verify()` resolve every native member they use:

1. A postfix on `GetRandomWeatherForCycle` performs the selection.
2. A postfix on `HazardousWeatherService.Load` restores a saved tide through the private setter, before other systems read it.
3. A prefix on `UpdateCurrentUISpecification` skips the native lookup while the tide is current.
4. Prefixes on the eight `HazardousWeatherUIHelper` getters return the tide's names and three unstyled CSS classes.
5. A prefix on the start sound plays the badtide alarm.

Native code still drives everything else from the tide as an `IHazardousWeather`: cycle length, the approach timer and banner, the started and ended events and banners, music, and `HazardousWeatherWaterSource` lists. Achievements and the tutorial see neither a drought nor a badtide. The Weather Station's drought and badtide modes stay off and its temperate mode turns off during the tide; its added Radioactive Tide mode (`Scripts/WeatherStations`) signals for it, with the native early activation.

The native panels are internal classes. `RadioactiveTideUi` reaches them through `PanelStack._root`, a verified reflection read, and recognises the tide classes each frame. It then applies:

- the 46 px tide icon to the date panel;
- the native wet progress and banner art, tinted yellow-green;
- an approaching-fill overlay;
- a one-line explanation under the banner.

### Saved state

Singleton `DeepFrontier.RadioactiveTide` stores:

- `CurrentCycleIsTide`;
- `LastTideCycle` and `LastTideDuration`;
- `SludgeEmittedThisTide` (radioactive volume, estimated from the share and the source strengths).

Remaining days are derived from the native cycle and weather state. `PostLoad` throws if the saved tide does not match the restored native weather, cycle and duration.

### Files

- `src/DeepFrontier/Scripts/RadioactiveTide/`:
  - `RadioactiveTideTuning.cs`: numbers, loc keys and the settings interface
  - `RadioactiveTideWeather.cs`
  - `RadioactiveTideService.cs`
  - `RadioactiveTideNative.cs`
  - `RadioactiveTideUi.cs`
  - `RadioactiveTidePatches.cs`: Harmony, editor-excluded
  - `RadioactiveTideSettings.cs`: ModSettings, editor-excluded, `[Context("MainMenu")]` and `[Context("Game")]`
  - `RadioactiveTideConfigurator.cs`: `[Context("Game")]`, plus the dev module
- `tools/radioactive_tide_content.mjs`: localization rows, the `Configurations/Sun.blueprint.json` fog overlay and the icon. It is imported at the end of `tools/create_frontier_expansion_content.mjs`.
- `src/DeepFrontier/Art/Icons/RadioactiveTide.svg` becomes `Sprites/Weather/RadioactiveTideIcon.png` (46×46, radiation ink).
- `tools/validate_radioactive_tide_content.mjs [dataRoot] [--native outputs/weather-api-1.1.2.8]`.

### Open questions

- **Incompatible mods.** Moddable Weathers replaces the native weather services, so the tide is incompatible with it.
- **Underground water drills.** Native drills block on any hazardous-weather start but, after a reload, only for drought or badtide. A drill reloaded during a tide runs, and its aquifer's water is then partly radioactive.
- **Weather Station.** Resolved without an enum patch: the Radioactive Tide mode is a decorator with its own save key, a prefix on the native `Sample()` that samples the tide, a prefix on the native `UpdateOutputState()` that sets the tide output only while that mode is on, and a fourth native radio button in the native panel (`Scripts/WeatherStations/WeatherStationPatches.cs`). Not verified in game.
- **Moddable Weathers and the native Weather Station (source-confirmed, Moddable Weathers 11.0.0).** Moddable Weathers does not patch `WeatherStation`. Its drought and badtide weathers are `GameDroughtWeather`/`GameBadtideWeather`, which are not the native `DroughtWeather`/`BadtideWeather` classes the native station tests with `is`, so with Moddable Weathers the native Drought and Badtide modes never signal. The Radioactive Tide mode compares the weather id and is not affected. Deep Frontier does not change the native modes.
- **Balance.** The emission rate, the chance and the durations need in-game tuning.
