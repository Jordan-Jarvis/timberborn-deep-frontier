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
- **Planters skip irradiated ground** (`IrradiatedPlantingSpots.cs`, 2026-11-02; user report: farmers replanted dead crops on irradiated ground, the crop died at once, and they replanted it again forever instead of moving on).
  - Native rule (decompiled `Timberborn.Planting` 1.1.2.8): every planter (farmhouses, foresters) picks its spot with `PlantingSpotFinder.FindClosest`, which keeps a marked spot only if the private `CanPlantAt` passes: the prioritized plantable, `PlantingSoilValidator.Validate` (soil moist, or dry for arid plants, and not `ISoilContaminationService.SoilIsContaminated`), the building's `IPlantingSpotValidator`, the floodable water depth and `SpawnValidationService.IsUnobstructed`. The planting tool (`PlantingAreaValidator`) checks only obstruction, so badwater-contaminated or dry soil stays marked, planters skip it and planting resumes by itself when the soil recovers.
  - Irradiated ground now gets the same rule: one Harmony postfix on `PlantingSpotFinder.CanPlantAt` refuses a spot where `RadiationSimulation.IsIrradiatedGround` is true, the same call that kills a plant planted there. One threshold, soil and bank layer, Radioactive Tide water included.
  - Why a patch: the soil rule is hard-coded. `PlantingSoilValidator` is an internal singleton with a non-virtual `Validate`; `IPlantingSpotValidator` is the planter building's own single component (`FarmHouse`, `Forester`), read with `GetComponent`, which throws when a second component implements it; `ISoilContaminationService` is the badwater field every native system reads; `ISpawnValidator` is consulted only by natural spreading.
  - The postfix reaches the rule through the planter itself: `IrradiatedPlantingSpots` is decorated on `PlantablePrioritizer`, where native `PlantingSpotFinder` is decorated, with `RadiationSimulation` injected. No static state. Mod start verifies the native contract and throws on a changed game: `CanPlantAt` exceeds the Mono inline limit (120 IL bytes), calls `PlantingSoilValidator.Validate` (which calls `SoilIsContaminated` and `SoilIsMoist`), is called from `GetClosestOrDefault`, `FindClosest` is called from `PlanterWorkplaceBehavior.Decide` and `PlantBehavior.ReserveCoordinates`, and `PlantingConfigurator` decorates `PlantingSpotFinder` on `PlantablePrioritizer`.
  - Marks stay: the player can mark irradiated ground, and planting resumes on its own once the ground is clean. While no marked spot is plantable the planters harvest or idle, as for contaminated soil (native `PlanterBuildingStatusUpdater` does not test soil, so no new status).
  - Plants killed while growing stay dead in place, as after a badwater death. Crops are `RemoveOnCut`, so native `EmptyDeadNaturalResourceOverrider` makes a dead crop overridable at once; that is why a farmer could plant straight over it, and now plants over it only once the ground is clean. A forester set to replant dead trees demolishes and replants them (`PlanterWorkplaceBehavior`, after `FindClosest`) also only once the ground is clean. Nothing replants on irradiated ground.
  - A planter that reserved its spot before the ground turned irradiated still plants it once (native planters do not re-check a reserved spot); that plant dies and the spot is skipped from then on.
- **Planting warning:** the planting tooltip and plant panel say plants there die immediately and planters skip that ground until it is clean. Marking it for planting stays allowed.
- **Affected area:**
  - under radioactive water from r = 0.0125 (4r = 0.05);
  - on banks within 7 tiles of r ≥ 0.25 water;
  - within 3 tiles of r = 0.1;
  - the 100% tide kills plants under and beside its water, like any pure radioactive water;
  - deposits (evaporation, spills, meltdown and waste-leak soil) kill wherever they reach 0.05.
- **Recovery:** rinsing (5.2 h) or bank clearing below 0.05 stops the killing at once. Planters resume on the marked spots by themselves and the new plants survive.
- **Saves:** no new data. Plants on irradiated ground in an old save die on the first tick.
- **Cost:** one block lookup per slot when it turns irradiated, on tracked rows only. No per-plant work. Planting: one component lookup and one slot lookup per candidate spot that already passed every native test.

### Reactor Bot leaks (`Scripts/SuperBots/ReactorBotLeak.cs`)

Status 2026-11-02: compile-checked, generated and validated in mirror `botleak`. Not built or played.

User request 2026-11-02: "If they overheat or go unmaintained for too long then they can leak radioactive water on the ground."

- **Conditions** (native need states, read every tick; numbers in `tools/super_bots.json` `leak`):
  - *overheated:* the coolant need (`ReactorBotCoolant`) is in its native critical state for more than `overheatHours` 6. That is points at 0: the native "Reactor Bot is overheating" status, and the bot refuses work (`NeedPreventingWorkSpec`).
  - *unmaintained:* the plating need (`ReactorBotPlating`) is exhausted for more than `unmaintainedHours` 24 (`ReactorBot.IsPlated` false, the panel's "No plating" line).
  - Lifespan wear does not count: every bot ages however well it is kept, and an unplated Reactor Bot already wears 5 times faster.
  - A condition's hours restart from 0 once it is fixed.
- **Rate:** while either condition is past its threshold, `volumePerHour` 0.02 radioactive volume per game hour (a tenth of a RadioactiveSludge good), one pulse at once and then one every `pulseHours` 1. That is 0.48 per day, 40% of what a full Radioactive Waste Vault or a blocked Waste Refinery leaks (1.2 per day); `validate_super_bots` keeps it below both. It stops as soon as both conditions are fixed.
- **Path:** `IRadiationService.AddRadioactiveWater`, the native add path with r = 1, so the existing rules do the rest:
  - on dry ground the puddle runs off and evaporates, and evaporated radioactive volume becomes soil radiation (10 per unit of volume): a pulse leaves up to 0.2 of soil, tinted ground where plants die at once;
  - in water it raises r (0.02 in a column 1 deep reads 2%), so pumps on that water refuse until it dilutes below 0.005 and the cutoff removes it, and stored water in irradiated barrels and tanks turns to ContaminatedWater;
  - beavers wading in it are dosed at 60·r per hour, on the ground at 0.25·s per hour, and hospitals treat them over 10 days;
  - the Sludge Recovery Pump recovers it; decay and rinsing work as for any radioactive water and soil.
- **Where (decision):** the bot's own cell, the cell `RadiationExposure` samples for beavers. While the bot is hidden inside a building (`Enterer.CurrentBuilding`), it is that building's doorstep (`PositionedEntrance.DoorstepCoordinates`): the building's blocks keep water out, so the leak runs out of the door. A building without an entrance uses the bot's cell.
  - `TryFindOpenCell` then picks the open fluid column at that cell. Its floor takes the water natively: the ground, a platform or flat roof top, or the water surface below the bot. Water on a platform or roof runs off its edge natively, so platforms need nothing special.
  - If the cell is closed to water (inside a water-blocking block), the water goes to the lowest open cell above it, as for waste leaks and meltdowns. A column closed all the way up takes nothing that pulse.
- **Visible:** no status or notification of its own (the user wants no hand-holding). The native overheating status and the panel's "No plating" line come first, then the yellow water and ground.
- **Saved** per bot under `DeepFrontier.ReactorBotLeak`: `OverheatedHours`, `UnplatedHours` and `NextPulseHours`, written only while one is non-zero. Saves without it load with no leak history.

### Sources and sinks

| Path | Implementation |
|---|---|
| `AddRadioactiveWater(cell, volume)` (outfall, spills, meltdown, waste leaks, continuous sources) | native `IWaterService.AddCleanWater` plus a record promoted with the native change queue (postfix of `WaterChangeService.Tick`); the replay gives that change r = 1 |
| Radioactive Spring | a native water source (DevWaterSource clone with `WaterSourceSpec`, `WaterSourceContaminationSpec` 0, no badtide controller) plus `RadioactiveWaterSourceSpec {RadioactiveShare: 1}` |
| Radioactive tide | `SetSourceRadioactiveShare`: every native source's added non-bad water carries r = `SourceRadioactiveShare` 1 (19.2 radioactive volume per strength-hour from a clean source) |
| Sludge Recovery Pump | native `WaterInput.DemandCleanWaterAmount` (the pump path). The replayed removal reports its radioactive volume; the pump buffers it (saved) and makes 1 good per 0.2. Water demand = shortfall / (r / (1 − b)), at most `MaxWaterPerCycle` 4. The fresh water pumped with it is used up. The buffer returns as radioactive water when the pump is deleted |
| Waste Export, refinery | recipes unchanged |
| Reactor Bot leaks | `ReactorBotLeak`: `AddRadioactiveWater` at the bot's cell, or its building's doorstep, 0.02 per hour while it has overheated for more than 6 h or gone unplated for more than 24 h (previous section) |

### Gameplay hooks

| Need | Implementation |
|---|---|
| Pumps refuse | `RadiationIntakeGuard` on native `WaterInput` blocks when r ≥ 0.005 (`DetectionLimit`) at the intake and resumes once the share reads 0 (no second threshold). Its entity panel shows "Water at the intake: x% fresh, y% bad, z% radioactive". Inert on the recovery pump |
| Barrels and tanks | unchanged: Water in irradiated storage becomes ContaminatedWater; a Water tank switches on any pass |
| Hauling radioactive goods | 2026-10-29 (user request): a beaver carrying Radioactive Waste or Radioactive Water (`RadioactiveSludge`) has a 2% chance per carrying hour of being irradiated outright, Contaminated Water 0.5% (`RadiationTuning.HaulingIrradiationRate`, rolled each tick with the native `IRandomNumberGenerator`). A 15-minute haul of waste is about 0.5%. A notification names the beaver and the good; the usual hospital course follows. Bots are unaffected. |
| Deleting waste storage | refused (2026-10-29, user decision): any native Stockpile holding RadioactiveWaste, RadioactiveSludge or ContaminatedWater has `HazardousStorageDeletionBlocker`, a native `IBlockObjectDeletionBlocker` like the fixed-stockpile one. The panel's delete button is disabled with the reason and the deconstruction tool skips it until the stock is moved out (Empty storage, or another good selected); then it can be deleted. ContaminatedWater can be selected in any tank, so a contaminated water supply can be emptied into new barrels. Since 2026-11-03 the Radioactive Water Outfall (50,000, with the Hospital) also pours out contaminated water, 30 per hour, the radioactivity of its 3 radioactive water goods per hour (10 contaminated water hold one good's radiation, as the refinery's decontamination counts it), so tide-irradiated storage can be emptied and deleted long before the Radioactive Waste Export (300,000) (`docs/deadlock-audit.md` D5). |
| Contamination Sensor | native sensor with a per-sensor "Measures" choice (`Scripts/Sensors/`): Badwater (native, default), Radiation (r of the measured column) or Any contamination (b + r), rounded to the native 1% precision and compared against the native threshold and mode. The native panel shows the selected reading; the choice panel adds "Radiation: x%". Saved per sensor; saves without it load as Badwater. Below 0.5% the radioactive share is 0 (the cutoff); the native 1% rounding then reports 0.5–1.5% as 1%, the same threshold pumps use |
| Sluice (Sluice is Back! 11.0.0, optional mod) | the same "Measures: Badwater / Radiation / Any contamination" choice for the sluice's "close above / below x% contamination" automation, in the optional assembly `DeepFrontier.SluiceIsBack` (`Scripts/SluiceIsBack`, shipped as `Scripts/DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional`, loaded by Moddable Timberborn only with the mod). A postfix on the mod's private `Sluice.GetContamination()` substitutes r or b + r of the source column, rounded like the mod (`Math.Round(x, 2)`); a postfix on `SluiceState.SetState(neighbor, minLimit)` copies the choice between synchronized sluices and on copy-settings. Default Badwater; saved under `DeepFrontier.SluiceContaminationSubstance`; the panel adds the dropdown and "Radiation: x%" after the mod's fragment |
| Stream Gauge | display only (no automation output, no threshold), so no choice: its panel gains "Radiation: x%" for the gauge cell next to the native badwater "Contamination" (`Scripts/Sensors/StreamGaugeRadiationPanel.cs`) |
| Weather Station | a fourth mode "Radioactive tide" (`Scripts/WeatherStations`): On while the cycle's hazardous weather is the tide and it has started, or earlier by the native early-activation hours. Works on the vanilla tide and the Moddable Weathers tide (both are the cycle's `IHazardousWeather` with id `RadioactiveTideWeather`). The native Temperate/Drought/Badtide modes are unchanged; the choice is saved under `DeepFrontier.WeatherStationRadioactiveTide` |
| Swimming Pool, Fish Hatchery (native `ContaminationBlockableBuilding`, blocks above 5.5% badwater) | not changed: radioactive water does not block them. Pumps and showers with a `WaterInput` are blocked by `RadiationIntakeGuard` |
| Irradiated beavers | dose outside buildings: water 60·r/h (r = 1 is as harmful as sludge was), soil 0.25·s/h when s ≥ 0.05 |
| Hospital, sickness, kits | unchanged: 10-day hospital course, 8-day untreated death, kit-to-adult carry-over |
| Plants | irradiated ground kills at once (next section) |

### Visibility

Drawn by the native surfaces, with no overlay meshes (`RadiationShading.cs`, `RadiationRenderer.cs`, `tools/native_shader_variants.mjs`). Built and loaded in game since build 222; the dark water it caused until build 235 and the check that found it are under "In game" below.

- **Native mechanism** (decompiled `Timberborn.WaterSystemRendering` and `Timberborn.TerrainSystemRendering` 1.1.2.8). Water: `UpdateWaterTexturesTask` writes `byte(255 × Contamination)` into `WaterRenderer._contaminations` (`DataTextureArray<byte>`, R8, layer = column index, pixel x + y·width, old and new arrays), published as `_OldContaminations`/`_NewContaminations`; the `WaterContamination` subgraph of `PhysicalWaterURP_Opaque`/`_Transparent` samples them (old/new lerped by `_TickProgress`, blended with linked neighbours) and applies `Lerp(clean albedo, contamination colour, smoothstep(0.01, 1, c)^0.25)` plus emission, metallic, smoothness and normal. Soil: `TerrainMaterialMap._contaminationMapTexture` (RG16 `PixelData`, R old, G new, layer = terrain z) as `_ContaminationMap`, blended in by the `SoilContaminationVisualization` subgraph of `TerrainURP`. Neither texture has a spare channel.
- **Variants.** `tools/native_shader_variants.mjs` copies those three native graphs from the official modding tools and adds a second instance of the graph's own contamination subgraph, fed from Deep Frontier texture arrays in the native layout (`_DFOld/NewRadioactivity`, `_DFIrradiatedSoilMap`) with its own colours, lerped over the native result. Reflections, transparency, foam, flow, waterfalls and level visibility are the unchanged native graph. Global multi_compile keywords (`_DEEP_FRONTIER_RADIOACTIVE_WATER`, `_DEEP_FRONTIER_IRRADIATED_SOIL`) are on only while radiation is drawn; off, the variant is the native code. The native shader_feature keywords that the native materials enable (`_CALCULATE_OUTFLOWS`; `_USELAYERTOOL`, `_SAMPLE_SPLATMAP`, `_USE_TRIPLANAR_SPLATMAP`) compile as multi_compile. Output: `src/DeepFrontier/AssetBundles/Resources/Shaders/DeepFrontier/*.shadergraph`, bundled by the Mod Builder.
- **Materials.** In PostLoad the renderer sets the variants on the native `PhysicalWater_Opaque`/`_Transparent` (from `WaterMeshSpec`) and the five `TerrainURP` materials (`Grass`, `Cliff`, `CliffEdge`, `SlopeCliff`, `SlopeCliffEdge`, from the material repository), and restores the native shaders on unload. After every shader assignment (variant or native) the swap puts the native material's render queue back: assigning `Material.shader` drops a custom queue, and `PhysicalWater_Opaque` carries custom queue 3000 while its shader's own queue is AlphaTest 2450 (see "In game"). `RadiationShading.Verify` (Load) and each swap throw if the native members, shader names, material keywords, render queue or any native shader property changed.
- **Radioactive water:** one surface per tile. The stored value is the inverse of the native contamination curve applied to the wanted lerp weight w = visibility(r) × r / (b + r), so the colour mixes with badwater by share and pure radioactive water is fully yellow (base colours 0.38/0.42/0.03 to 0.64/0.69/0.06 and a yellow-green detail glow 0.33/0.41/0.07 to 0.37/0.43/0.10; toned down on 2026-11-01 from 0.50/0.56/0.04 to the radiation yellow 0.86/0.92/0.08 with glow 0.55/0.68/0.12 to 0.62/0.72/0.16, which the user found too bright). Visibility is log-scaled from the detection limit: 0.12 at r = 0.005 (`RadiationTuning.DetectionLimit`), 1 at r = 1; below it nothing is drawn. Reflections are the native contaminated-water reflections.
- **Irradiated ground:** the native soil-contamination veins, tinted yellow-green (SoilVeinColor), wherever s ≥ 0.05; the map value follows the native soil rule (0.1 at the first visible level, 1 from s = 0.5).
- **Updates.** Per tick, after `RadiationSimulation.Tick`, for the radiation rows plus rows still settling; old/new follow the native update rules (newly wet water shows at once; a soil change moves G to R and settles next tick); only changed layers upload, through the native buffer + `Graphics.CopyTexture` path. Nothing runs per frame.
- **Radioactive Spring:** the native source model in the radioactive material.

#### In game (2026-11-01, builds 232-235)

Player report on 0.8.x (required mods only): water "very, very dark", "more like black, definitely not blue", badwater "much darker than it should be". Checked with `tools/start_water_shading.ps1` (`Scripts/Radiation/WaterShadingProbe.cs`) on a copy of a Memory Test autosave, same camera and time of day each run; screenshots in `outputs/water-shading/<label>/`, side by side in `outputs/water-shading/comparison-232-233-235.png` (local, untracked).

- **Before (build 232 = HEAD 1364df0 + the probe):** clean water near-black (screen-centre mean RGB 45,48,45), badwater near-black with orange veins (44,44,40), radioactive water dark green. The native shaders put back in the same process changed nothing.
- **Swap never applied (mirror-only experiment, build 233):** clean water blue (54,66,69), badwater red-brown (55,48,42). Terrain pixel-identical to the swapped run.
- **Isolation (build 234 experiments):** with the radiation textures, uploads and keywords running but the variant never assigned, the water was blue; with the variant assigned and the native shader restored before the first frame, it stayed dark for the whole game. So the assignment itself left something behind.
- **Ruled out:** the compiled variants match the game's shaders (with the radiation keyword off, all 160 `RadioactiveWaterURP_Opaque` ForwardLit programs are byte-identical DXBC to `PhysicalWaterURP_Opaque`; transparent water and terrain differ only in the `$Globals` constant-buffer layout; property names, defaults and flags, keyword sets, pass states and tags match); every material property value matched `resources.assets`; forcing both radiation keywords on with no radiation changed nothing.
- **Cause:** `PhysicalWater_Opaque` has `m_CustomRenderQueue` 3000 in `resources.assets` (logged at runtime in the menu before any game: queue 3000). Under the variant it drew at 2450, the variant's AlphaTest queue, and stayed at 2450 after the native shader came back. At 2450 it draws in URP's opaque pass, before the camera colour and depth copies its transparency and depth tint sample, so shallow water showed black. `PhysicalWater_Transparent` (custom 3000 = its shader's queue) and the terrain (2450) were unaffected.
- **After (build 235, fix in `ShaderSwap.Use`):** clean water 60,69,70 and badwater 55,48,42, matching the run without the swap; the native and the forced-keyword captures match the variant capture within the frame-to-frame noise of moving water; radioactive water bright yellow (135,140,63) with the yellow-green soil veins beside it. `tools/start_scene_cycle.ps1 -Label 235 -Cycles 1` (save, menu, new Canyon game, menu) COMPLETE: both games drew the variants at the native queues and both menus found all seven materials as before the first game, render queue included.

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

User request 2026-11-02: the radioactive tide settings belong on the new-game screen with the native badtide settings ("badtide percent chance and first bad tide and drought duration etc.... we should add radioactive tide settings into there as well"), for Easy, Normal and Hard.

### Behaviour and numbers

| Item | Value |
|---|---|
| Weather id | `RadioactiveTideWeather` (third native `IHazardousWeather`) |
| Settings | per game, chosen on the native new-game screen (next section); Normal: from cycle 15, 25% per cycle, 3–6 days |
| Chance | per cycle, tested after the native drought/badtide roll and replacing it |
| Consecutive tides | never: a tide cannot follow a tide (`CooldownCycles` 1) |
| Duration | uniform whole days between the game's shortest and longest tide |
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
- **Dev mode.** "Deep Frontier: radioactive tide next cycle" forces the next cycle's tide. It ignores the cycles without tide, the chance and the cooldown, and is not saved. It refuses while tides are off in the game.

### Settings per game: the new-game screen (since 2026-11-02)

Status: compile-checked (also against the shipped, non-publicized assemblies), generated and validated in mirror `tidemode`. Not built, not seen in game.

The settings sit with the native weather settings and work like them:

| Mode | Radioactive tides | Cycles without radioactive tide | Radioactive tide chance | Radioactive tide duration |
|---|---|---|---|---|
| Easy | on | 24 (from cycle 25) | 15% | 2–4 days |
| Normal | on | 14 (from cycle 15) | 25% | 3–6 days |
| Hard | on | 9 (from cycle 10) | 35% | 5–10 days |

- Normal keeps the 0.8.3 defaults; Easy brings tides later, more rarely and shorter, Hard earlier, more often and longer. The tide replaces the cycle's drought or badtide, so a Hard tide is still shorter than the Hard drought (15–30 days) it replaces.
- **Presets** are data: `Data/NewGameModes/GameMode.{Easy,Normal,Hard}.blueprint.json` add a `RadioactiveTideGameModeSpec` (`Enabled`, `CyclesWithoutTide`, `ChancePercent`, `Duration {Min, Max}`) to each native game-mode blueprint. Written by `tools/radioactive_tide_content.mjs` (`GAME_MODE_PRESETS`).
- **Custom mode.** "Customize" shows "Radioactive tides" (toggle) and, while it is on, "Cycles without radioactive tide", "Radioactive tide chance" (%) and "Radioactive tide duration" (*x* to *y* days), right after the native badtide rows and filled from the selected preset like the native fields. Ranges: cycles without 1–99, chance 1–100%, durations 1–30 days. Fields clamp on leaving them (native `TextFields`); a shortest tide longer than the longest is marked red and keeps Start disabled, like the native duration rows. A switched-off section is not checked (native rule).
- **Meaning.** Tides can come in the cycles after "Cycles without radioactive tide", as badtides do after the native "Cycles without badtide". Cycle 1 never has a tide.
- **Stored per game.** A new game reads the settings from its game mode once, then saves them in singleton `DeepFrontier.RadioactiveTideSettings` (`Enabled`, `CyclesWithoutTide`, `ChancePercent`, `MinDurationDays`, `MaxDurationDays`). They cannot change during the game, like the native weather settings. The game logs `[DeepFrontier] Radioactive tide settings: ...` with their source.
- **Older saves** (0.8.3 and before) have no per-game settings. They keep the values the player had in the former Deep Frontier mod settings: eMka.ModSettings stored them in the native settings store (PlayerPrefs) under `ModSetting.DeepFrontier.RadioactiveTideSettings.TideEnabled`, `TideMinCycle`, `TideChancePercent`, `TideMinDurationDays` and `TideMaxDurationDays`. A key never changed reads as the old default (on, from cycle 15, 25%, 3–6 days), which equals Normal. The values are saved with the game at its next save.
- **The Mod Settings page is gone.** The per-game settings replace all five global options, so Deep Frontier's eMka.ModSettings "Radioactive tide" page and `RadioactiveTideSettings.cs` were removed. No other Deep Frontier code uses eMka.ModSettings; it stays a required mod in the manifest until its removal is decided.
- **Moddable Weathers.** With it, Moddable Weathers' per-save tide settings (its Weather Settings dialog) are the game's only tide settings; `RadioactiveTideGameSettings` is not bound. They are seeded once per save from the same source the vanilla path uses (`RadioactiveTideStartingValues`): the save's own vanilla tide settings (a save played without Moddable Weathers), else the new game's mode, else the former mod settings. The dialog keeps "Earliest cycle", which is cycles without + 1. A save played with Moddable Weathers and then loaded without it takes the former mod settings, as Moddable Weathers keeps its own weather settings.

#### Native mechanism (Timberborn 1.1.2.8, source-inspected 2026-11-02)

[S] = decompiled from the shipped assemblies with `tools/dotnet/ilspycmd.exe`.

- [S] **Presets are blueprints.** `GameModeSpecService.Load` collects `ISpecService.GetSpecs<GameModeSpec>()` ordered by `Order`; the default is the one with `IsDefault` (Timberborn.NewGameConfigurationSystem). The vanilla files are `NewGameModes/GameMode.Easy|Normal|Hard.blueprint.json` (Order 10/20/30, Normal `IsDefault`).
- [S] **`GameModeSpec` is a fixed record** (`ComponentSpec`): `StartingAdults`, `AdultAgeProgress`, ..., `TemperateWeatherDuration`, `DroughtDuration`, `DroughtDurationHandicapMultiplier/Cycles`, `CyclesBeforeRandomizingBadtide`, `ChanceForBadtide` (0..1), `BadtideDuration`, `BadtideDurationHandicapMultiplier/Cycles`, `InjuryChance`, `DemolishableRecoveryRate`. Nothing can add a field to it.
- [S] **A blueprint holds several specs.** `ComponentSpec.Blueprint` links a spec to its blueprint and `GetSpec<T>()` finds a sibling spec. `BlueprintFileBundleLoader.GetBundles` groups every blueprint asset with the same path (vanilla and mods), so a mod file at a vanilla path merges into that blueprint.
- [S] **The screen** (Timberborn.MainMenuPanels): `NewGameModePanel.Load` adds one `MainMenu/NewGameModeButton` per spec into `Modes` and selects the default. "Customize" (`OnCustomizeButtonClicked`) calls `CustomNewGameModeController.Initialize(root, selected preset, UpdateNextButton)`, which fills the fields of `UI/Views/MainMenu/NewGameModePanel.uxml` (`CustomModeSettings`: `BadtideEnabledWrapper`, `BadtideWrapper` with `CyclesBeforeRandomizingBadtideWrapper`, `ChanceForBadtideWrapper`, `BadtideDurationWrapper`, `BadtideDurationHandicapWrapper`) through `TextFields.InitializeIntegerField` (clamps on focus-out). `TryGetValidatedGameMode(out GameModeSpec)` builds `new GameModeSpec {...}` from the fields (`GetGameMode`) and checks min ≤ max (`ValidateGameMode`, class `new-game-mode-panel__setting-input--invalid`); a switched-off drought or badtide is not checked and is stored as zeros. `UpdateNextButton` enables Start from it. `StartNewGame` passes the preset or the custom spec to `GameSceneLoader.StartNewGame(new NewGameConfiguration(faction, map, gameMode, ""))`.
- [S] **Into the game.** `GameSceneParameters.CreateNewGameParameters` keeps the `NewGameConfiguration` (with the `GameModeSpec` object itself) for the Game scene; `NewGame` is true only for a new game.
- [S] **Stored per save by each weather.** `BadtideWeather.Load`: saved singleton `BadtideWeather` if present, else for a new game `Initialize(sceneParameters.NewGameConfiguration.GameMode)`, else (older saves) `Initialize(_gameModeSpecService.GetDefaultSpec())`; `Save` writes min/max duration, handicap, cycles before randomizing and chance. `DroughtWeather` does the same with its own singleton. `HazardousWeatherRandomizer` reads `BadtideWeather.ChanceForBadtide` and `CanOccurAtCycle(cycle)` = cycle > cycles before randomizing.
- [S] **Moddable Timberborn 11.1.3** `PersistentGameModeService`: on a new game `StartedMode = ReconstructedMode = NewGameConfiguration.GameMode`; for a save it rebuilds a plain `GameModeSpec` from the native weather services. `Save` sets the started mode's `Blueprint` to null before JSON-serializing it, so a new game's mode must be read during load, as Deep Frontier does. **Moddable Weathers 11.0.0** `ModdableWeatherSettingsService.Load` seeds a weather's settings once (`FirstLoad`) with the first of ReconstructedMode, BestMatchedMode and Default its `CanSupport` accepts.
- **Why one Harmony patch.** Presets need none. The custom mode is created inside `CustomNewGameModeController.TryGetValidatedGameMode`, passed straight to `GameSceneLoader.StartNewGame`, and the same method enables Start; no interface, binding or event sits in between. `RadioactiveTideNewGamePatch` is one postfix on it: false while the tide rows are invalid, else a copy of the custom `GameModeSpec` whose blueprint also holds the custom `RadioactiveTideGameModeSpec` (native `Blueprint(name, specs, children)`). It is applied at mod start, with or without Moddable Weathers, after `RadioactiveTideNewGameNative.Verify()` checks the native members by signature and IL calls (the panel's start and Start-button paths reach the patched method, it builds the spec with `GetGameMode`, `OnCustomizeButtonClicked` calls `Initialize`, `Load` loads the panel view, `NewGameModePanel._root`).
- **The rows are native UI.** `RadioactiveTideNewGameSettings` (main menu) reads the panel root through the verified private `NewGameModePanel._root`, loads a second copy of the native panel view through the public `VisualElementLoader` (localized, text fields and sounds set up natively), moves its badtide toggle and three badtide rows (without the handicap row) after the native badtide rows, renames them and sets their labels. No UXML or stylesheet is added. It tracks the selected preset from the mode buttons (checked at load: one per spec, in order, with the spec's name) and fills the rows when "Customize" is pressed, after the native handler.

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

Singleton `DeepFrontier.RadioactiveTideSettings` holds the game's tide settings (previous section). Singleton `DeepFrontier.RadioactiveTide` stores:

- `CurrentCycleIsTide`;
- `LastTideCycle` and `LastTideDuration`;
- `SludgeEmittedThisTide` (radioactive volume, estimated from the share and the source strengths).

Remaining days are derived from the native cycle and weather state. `PostLoad` throws if the saved tide does not match the restored native weather, cycle and duration.

### Files

- `src/DeepFrontier/Scripts/RadioactiveTide/`:
  - `RadioactiveTideTuning.cs`: numbers, ranges, the former mod-settings keys, loc keys and the settings interface
  - `RadioactiveTideGameModeSpec.cs`: the game-mode spec and the custom-mode copy
  - `RadioactiveTideGameSettings.cs`: per-game values, their sources (`RadioactiveTideStartingValues`) and checks
  - `RadioactiveTideNewGameSettings.cs`: the new-game rows (main menu) and `RadioactiveTideNewGameNative`
  - `RadioactiveTideNewGamePatch.cs`: the custom-mode postfix, editor-excluded
  - `RadioactiveTideWeather.cs`
  - `RadioactiveTideService.cs`
  - `RadioactiveTideNative.cs`
  - `RadioactiveTideUi.cs`
  - `RadioactiveTidePatches.cs`: Harmony, editor-excluded
  - `RadioactiveTideConfigurator.cs`: `[Context("Game")]`, the dev module, and `RadioactiveTideNewGameConfigurator` `[Context("MainMenu")]`
- `tools/radioactive_tide_content.mjs`: localization rows, the game-mode presets (`NewGameModes/`), the `Configurations/Sun.blueprint.json` fog overlay and the icon. It is imported at the end of `tools/create_frontier_expansion_content.mjs`.
- `src/DeepFrontier/Art/Icons/RadioactiveTide.svg` becomes `Sprites/Weather/RadioactiveTideIcon.png` (46×46, radiation ink).
- `tools/validate_radioactive_tide_content.mjs [dataRoot] [--native outputs/weather-api-1.1.2.8]`.

### Open questions

- **Incompatible mods.** Moddable Weathers replaces the native weather services, so the tide is incompatible with it.
- **Underground water drills.** Native drills block on any hazardous-weather start but, after a reload, only for drought or badtide. A drill reloaded during a tide runs, and its aquifer's water is then partly radioactive.
- **Weather Station.** Resolved without an enum patch: the Radioactive Tide mode is a decorator with its own save key, a prefix on the native `Sample()` that samples the tide, a prefix on the native `UpdateOutputState()` that sets the tide output only while that mode is on, and a fourth native radio button in the native panel (`Scripts/WeatherStations/WeatherStationPatches.cs`). Not verified in game.
- **Moddable Weathers and the native Weather Station (source-confirmed, Moddable Weathers 11.0.0).** Moddable Weathers does not patch `WeatherStation`. Its drought and badtide weathers are `GameDroughtWeather`/`GameBadtideWeather`, which are not the native `DroughtWeather`/`BadtideWeather` classes the native station tests with `is`, so with Moddable Weathers the native Drought and Badtide modes never signal. The Radioactive Tide mode compares the weather id and is not affected. Deep Frontier does not change the native modes.
- **Balance.** The emission rate and the Easy/Normal/Hard values need in-game tuning.
