# Reactor meltdown and radioactive waste leaks

Status 2026-10-22: source written, compile-checked and generated in a scratch copy of the repository. Crater, blast, flood and circular radii 2026-11-02: compile-checked, generated and validated in mirror `meltdown`. Nothing here has been built, launched or played; `tools/STATUS.md` records runtime verification.

User direction: a reactor that runs out of coolant, workers or maintenance heats up, warns, trips an emergency shutdown and finally melts down, destroying itself and contaminating the land and water around it; a full waste vault or a backed-up refinery leaks into soil and water and kills crops. Every risk is stated in the building tooltip, the entity panel, statuses and notifications before it bites.

## Reactor core (`ReactorMeltdownSpec`, `ReactorCore`)

Reworked 2026-10-29 (user direction): power output falls as the core heats, the core cools exactly as slowly as it heats, and full waste storage heats it like dry coolant. There is no automatic emergency shutdown any more: an automatic SCRAM let the coolant stock refill and saved a reactor that was short of coolant most of the time.

Heat is 0..1 of meltdown, evaluated every tick (rates per game hour):

| Reactor state | Heat |
|---|---|
| Blocked: native pause or automation Off | cold shutdown, −2.5%/h, coolant not needed |
| Uncooled: radioactive waste or sludge full, or coolant dry while running or while the core holds any heat | +2.5%/h, running, idle or SCRAM alike |
| Running, fewer than 4 operators working | +2.5%/h below 85% |
| Running, maintenance overdue | +2.5%/h below 85% |
| Otherwise, with coolant | −2.5%/h |
| Dry and cold (0%), not running | stays cold |

- **Power output** is `1 − heat` of the full 1,000,000 hp: 50% heat gives half power. `ReactorCore` is the building's `IGeneratorOutputFactor`, which `WorkshopPoweredGenerator` multiplies into its native output multiplier. A SCRAM gives 0.
- **Coolant dry:** less than one cycle (6 `ReactorCoolantWater`) unreserved in stock, so the next cycle cannot start. A running core's last cycle counts, so a cold core that runs dry starts heating.
- **Waste full:** no unreserved room for one more cycle of a product of the current recipe, the 1 Radioactive Waste and 1 Radioactive Sludge each cycle makes (the Waste Refinery's `OutputBlocked` test). It heats from cold too: waste fills only by running.
- **Symmetry:** heating and cooling are the same 2.5%/h, so a reactor that is uncooled more than half the time gains heat on average and eventually melts down. At coolant 45% of the time the net is +0.25%/h, about 400 hours (17 days) from cold to meltdown with falling output.
- **Crew and maintenance faults** stop heating at 85% (15% output): they cost power but never melt the core alone. A meltdown always traces back to lost cooling or waste left in the reactor.
- **Maintenance** falls due after 360 running hours. Any 24 consecutive hours without production (pause, SCRAM or idle) is the maintenance stop; a nightly idle is shorter, so it does not count.
- **Thresholds:** 60% warning status and notification; 85% "meltdown imminent" notification when uncooled; 100% meltdown.
- **Alerts:** the first dry-coolant and the first full-waste heating each post a notification, latched until the core is cold again (an intermittent supply or hauler toggles them every cycle). Priority statuses for overheating, dry coolant, full waste and SCRAM.
- **Manual SCRAM:** the panel's button stops production and power; it does not stop uncooled heating. Restart is allowed at or below 40%. SCRAM is an `IManufactoryLimiter` returning 0, not `BlockableObject.Block`, so the crew stays and coolant deliveries continue.
- **Saves from before 0.6.0:** an automatic SCRAM loads as running; the unused `AutoRestart` and `LastRunDay` values are ignored.

Timeline at these numbers:

- **Coolant or waste failure:** from cold, the warning comes after 24 h and the meltdown after 40 h, unless coolant arrives, the waste is hauled away or the reactor is paused.
- **Cooling from 85%**, with coolant or paused: 34 h to cold, 18 h to the 40% restart heat.

### Why pause and automation Off are a safe cold shutdown

This is source-confirmed in 1.1.2.8:

- `WorkshopsTemplateModuleProvider` decorates every `Manufactory` with `AutoEmptiable`, which marks a blocked building for emptying.
- `ManufactoryHaulBehaviorProvider` and `FillInputHaulBehaviorProvider` deliver nothing to a blocked building.

So a paused reactor is drained of coolant and waste and cannot be refilled. If the uncooled rule applied while blocked, pause and automation would be meltdown traps; the requirement is that automation Off cools a reactor rather than melting it.

The panel says so explicitly: the dry-coolant and full-waste statuses suggest pausing.

### Meltdown (`MeltdownService`)

The meltdown runs in the service's singleton tick, the place native `ExplosionService` removes terrain and deletes block objects. Reworked 2026-11-02 (user: "Reactor meltdown should destroy the terrain underneath it as well. The radiation of the blocks also needs to not just be square. It should be circular."; "it should also destroy buildings and structures within 6 tiles of the reactor"; "the radioactive water should be everywhere enough to spread past the crater we make").

**Distance is a circle.** Every meltdown and leak radius is measured by `BuildingSite`: the straight-line distance in tiles from a column to the nearest footprint column (0 inside), and a column is within R tiles when that distance rounds to R or less (dx² + dy² ≤ R² + R). It replaced the Chebyshev (square) distance in the contamination area, the kill and irradiation radii, the new blast radius and the waste-leak soil radius. Around a 1x1 footprint this is an exact tile circle; around the 14x11 reactor it is the footprint swept by a circle, so "within 6 tiles of the reactor" means 6 tiles from its nearest wall, with rounded corners instead of square ones (the 12-tile area is 1,194 columns instead of 1,330).

| Radius (from the footprint) | Tiles | What happens |
|---|---|---|
| Crater rim | 2 | bowl removed (below) |
| Kill | 2 | every mortal character dies |
| Blast | 6 | every building and structure is destroyed |
| Contamination | 12 | soil and water radiation |
| Irradiation | 16 | beavers get a dose that irradiates them |

1. **Geometry, read before anything changes.**
   - Open fluid cells in every column within 12 tiles, using `IRadiationService.TryFindOpenCell` at the building's base height. Buildings are not water obstacles in 1.1.2.8 (only `WaterObstacle`/`FinishableWaterObstacle` add them), so the footprint is already open. If no footprint column is open, the meltdown throws before any effect.
   - **Crater.** An elliptical bowl centred on the footprint, semi-axes the footprint's half-extents + 2 tiles (9 x 7.5 for the reactor), limited to columns within 2 tiles of the footprint. Depth `MeltdownCraterDepth` 4 at the centre, 1 at the rim: max(1, ceil(4 x (1 - u))), u being the column's squared elliptical radius. It is cut below the ground the reactor stood on (the highest terrain top under the footprint, at or below its base) and never takes the map's bottom layer (z 0). On flat ground: 214 columns (all 154 footprint columns and 60 around them), 530 blocks (54 columns 1 deep, 56 two, 52 three, 52 four):

     ```
     ......111111......
     ....1122222211....
     ..11222333322211..
     .1122333333332211.
     .1223344444433221.
     112334444444433211
     122334444444433221
     122334444444433221     (the 14x11 footprint is the
     122334444444433221      block of 2-4s in the middle)
     112334444444433211
     .1223344444433221.
     .1122333333332211.
     ..11222333322211..
     ....1122222211....
     ......111111......
     ```
   - **Blast.** Every `BuildingSpec` object with a block in a column within 6 tiles, at any height: everything placed with the construction tools, finished or under construction (paths, platforms, stairs, decks, levees, power shafts, buildings). `BuildingSpec` is exactly where native `DeconstructionSystemConfigurator` decorates `Deconstructible`. Natural resources, ruins and map objects (water sources, springs) are not buildings and stay, unless they stand on removed ground.
   - **One native explosion outcome.** The crater tiles go through `ExplosionOutcomeGatherer.GetAffectedTerrainAndObjects`, the call native unstable-core explosions use: it keeps only tiles that are terrain, adds every object in them and every object standing on the removed ground, and applies native terrain physics. The blast buildings are added, and `ITerrainPhysicsService.GetTerrainAndBlockObjectStack` runs once more over everything, so whatever stood on a destroyed building or lost its support (stacked buildings, overhanging terrain) goes too, the native way. No terrain is ever removed under a building outside this cascade.
   - **Flood.** Each crater column gets `MeltdownCraterFloodFactor` 2 units of radioactive water per block its floor drops, at the column's open cell found now (removing terrain and buildings only opens cells, so it stays open; the water falls into the crater). On flat ground that is 1,060 units: 530 fill the bowl and 530 spill over the rim into the surroundings (about 0.5 deep spread over the rest of the 12-tile area, before evaporation; on a slope more of it runs downhill).
2. **Casualties.**
   - Everyone inside, and every mortal character within 2 tiles (which covers the crater, `MeltdownCraterRim` ≤ `MeltdownKillRadius`), dies through `Mortal.DieInstantly` ("<name> was killed in the reactor meltdown."). Bots die too.
   - Beavers within 16 tiles get `RadiationExposure.AddDose(1.5)`, which irradiates them: 10 days of hospital care, otherwise fatal. Bots have no radiation need.
   - Characters inside other destroyed buildings are put out by the native deletion (`Enterable` → `Enterer.Abandon`) and share the fate of their distance: dead within 2 tiles, irradiated (beavers) within 16.
3. **Contamination.**
   - 60 sludge units (300 goods' worth) spread over the footprint.
   - A saved continuous source at the core: 0.5 units/h for 240 h (10 days, 120 units).
   - The crater flood (above).
   - Soil radiation falls linearly with the circular distance from 0.5 at the footprint to 0.16 at 12 tiles. The edge stays above the 0.15 crop threshold, so crops in the whole radius die. Recovery at the soil half-life of 120 days: about 11 days at the edge, about 140 days half way, about 210 days at the footprint (longer wherever sludge lies). Ground the crater removes gets no fallout: its new floor lies under the flood, whose radioactive water irradiates it (soil exchange and banks, docs/radiation.md). This keeps the result independent of whether the radiation mirror sees the new floor before or after the deposit.
   - Submerged columns also get dissolved radiation, 2.0 → 0.2. It has a 20-day half-life and travels with the water.
   - Pumps on that water stop, stored water in reach turns to ContaminatedWater and decontamination works as for any radioactive water and soil: the radiation rules are unchanged, only more water and a different shape reach them.
4. **Destruction**, in native `ExplosionService.DestroyEverythingAffected` order: `ITerrainService.UnsetTerrain` on every removed block, `EntityService.Delete` on every object (its `EntityDeletedEvent` drives the native deconstruction particles; `DeconstructionNotifier` → `BuildingGoodsRecoveryService` drops the goods stored in each destroyed building as recovered-goods stacks nearby, as native explosions do, so stored waste lands on irradiated ground), then `DeconstructionParticleFactory.AddPausableParticles` on the removed terrain. The bodies of the dead then drop to the terrain below (`GetTerrainHeightBelow`), as native `CharacterExploder` does with characters killed in an explosion. Also a global explosion sound, a notification ("... destroyed N structures around it") and a dialog with "Show the site", which moves the camera to the site.

**Saves.** The whole meltdown happens in one tick, and `GameSaver` finishes the full tick before it saves (`TickableBucketService.FinishFullTick`), so a save holds either the standing reactor or the finished meltdown. A reactor saved at heat 1 before the service ran melts down on its first tick after load: `ReactorCore.Tick` requests the meltdown for a core that starts a tick at heat 1, whatever its cooling (before 2026-11-02 a core with coolant in stock cooled a little on that tick and never melted down; the service's pending list is not saved). The removed terrain reaches the native water map before the save: `WaterSimulator` processes its terrain modifications on `ForcedParallelTickFinished`, and a load rebuilds the water columns from terrain. The flood and footprint water are native water changes applied in the same tick's parallel step; the continuous source is saved. No new save data.

**Performance.** One-time work at the meltdown: about 560 columns x the map height of block lookups for the blast, about 530 crater tiles and the native terrain-physics pass, about 1,200 open-cell lookups.

**Dev mode.** "Deep Frontier: melt down selected reactor" (`MeltdownDevModule`, dev panel) melts down the selected finished Nuclear Reactor on the next tick, the same meltdown as at core heat 100%. With anything else selected it does nothing.

## Waste leaks (`WasteLeakSpec`, `WasteLeak`)

| | Radioactive Waste Vault | Radioactive Waste Refinery |
|---|---|---|
| Trigger | `StorageFull`: its waste fills the whole stockpile (1,600) | `OutputBlocked`: the current recipe produces sludge and there is no unreserved room for one more cycle, while unblocked |
| Warning (status + notification) | 90% full | 75% of its sludge capacity |
| Leak every | 24 h full | 24 h full |
| Per leak | 4 casks destroyed → 4 × 0.3 = 1.2 sludge units | 6 sludge goods destroyed → 6 × 0.2 = 1.2 units |
| Soil | +0.16 within 3 tiles of the footprint (circular distance, `BuildingSite`: 109 columns around the 5x5 footprint instead of the 121 of a square), which kills crops after one leak | same |
| Automation | role none; fill level only | Off/pause seals the tanks: no leak, and native auto-emptying hauls the sludge out |

- **Per-leak amounts** are one `WasteRefining` batch: 4 casks in, 6 sludge out. The sludge per cask is derived from that recipe and `RadiationTuning.VolumePerGood`.
- **Hours spent full** accumulate and drain at the same rate when not full, so a stock oscillating at the brim still leaks.
- **Placement:** sludge enters at the open footprint column nearest the centre. Buildings are not obstacles, so it flows out on every side.

## Files

| File | Contents |
|---|---|
| `src/DeepFrontier/Scripts/Meltdown/MeltdownSpecs.cs` | Spec records, triggers, placeholder status sprites |
| `src/DeepFrontier/Scripts/Meltdown/ReactorCore.cs` | Heat, SCRAM, maintenance, statuses, notifications, save/load |
| `src/DeepFrontier/Scripts/Meltdown/MeltdownService.cs` | Meltdown execution; footprint geometry (`BuildingSite`) |
| `src/DeepFrontier/Scripts/Meltdown/WasteLeak.cs` | Vault and refinery leaks |
| `src/DeepFrontier/Scripts/Meltdown/MeltdownPanels.cs` | `ReactorCorePanel` and `WasteLeakPanel` |
| `src/DeepFrontier/Scripts/Meltdown/MeltdownLoc.cs` | Localization keys |
| `src/DeepFrontier/Scripts/Meltdown/MeltdownConfigurator.cs` | `[Context("Game")]` configurator; `MeltdownDevModule` (dev-mode meltdown of the selected reactor) |

- `src/DeepFrontier/Scripts/Radiation/RadiationExposure.cs` gains `AddDose`.
- `tools/meltdown_content.mjs` holds all numbers and English text. It writes the specs, replaces the three producer descriptions (failing if they changed) and appends the rows to `enUS.csv`. It is imported at the end of `tools/create_frontier_expansion_content.mjs`.
- `tools/automation_content.json` declares the `ReactorMeltdownSpec` and `WasteLeakSpec` custom specs.
- `tools/validate_meltdown_content.mjs [dataRoot]` is the static validator.

Saved state:

- the reactor's `DeepFrontier.ReactorCore`: heat, SCRAM kind, auto-restart, run hours since maintenance, idle hours, last production day;
- each leaking building's `DeepFrontier.WasteLeak`: hours full, leak count, goods leaked.

Saves made before this system load cold and with no leak history.

## In-game acceptance

These checks are not yet automated, and `LategameAcceptance.cs` is unchanged. Each assertion is exact at the authored numbers.

**Reactor**

1. **Normal running.** A fuelled reactor with ≥ 6 coolant and ≥ 4 operators working: `Mode == Running` and `HeatRatePerHour == -0.04`. Heat stays at 0.
2. **Short crew.** Desired workers 3:
   - while running, `HeatRatePerHour == +0.025` and the "Fewer than 4 operators" status is active;
   - after 24 running hours heat ≥ 0.60, with one overheating notification;
   - at ≥ 0.85, `Scram == Automatic` and the shaft output is 0, the crew is still assigned and the coolant stock is unchanged (haulers still deliver).
3. **After an automatic SCRAM** with coolant ≥ 6: −0.08/h. At ≤ 0.40 with maintenance not overdue, `Scram == None` and the "restarted" notification is posted.
   - With auto-restart off it stays tripped until Restart.
   - Restart is disabled above 0.40.
4. **Manual SCRAM.** `Scram == Manual`, output 0, and no automatic restart.
5. **Coolant dry after running.**
   - The reactor stops: `Mode == Idle`, `DecayHoursLeft > 0`, `HeatRatePerHour == +0.015`.
   - The coolant-dry alert status is active and its notification is posted once.
   - The panel's meltdown estimate is (1 − heat) / 0.015 h.
6. **Pause or automation Off in that state.** `Mode == ColdShutdown`, −0.08/h, and it never melts.
7. **Maintenance.**
   - After 360 running hours: overdue, one notification, +0.025/h while running.
   - 24 consecutive hours without production resets it and posts "maintenance completed".
8. **Save/reload mid-heat.** Heat, SCRAM kind, auto-restart, run hours, idle hours and last production day are restored, with no repeated warning.

**Meltdown**

9. **At heat 1** (or the dev-mode "Deep Frontier: melt down selected reactor").
   - The reactor entity is deleted within a tick.
   - The meltdown notification ("... destroyed N structures around it") and dialog appear, and "Show the site" moves the camera there.
   - Everyone inside and every character within 2 tiles of the footprint is dead; their bodies lie on the ground below them (the crater floor where it was removed).
   - Beavers 3–16 tiles away have the Irradiation need active; the outline of that ring is round, not square.
   - Bots in that ring are unaffected.
10. **Crater.** On flat ground, an oval bowl 18 x 15 tiles across where the reactor stood: 4 layers deep in the middle, 1 at the rim, the rim at most 2 tiles beyond the walls (214 columns, 530 blocks). Never below z 1. Native terrain-removal particles play on it.
11. **Blast.** Every building, path, platform, stair, deck and other placed structure with any block within 6 tiles of the reactor's walls is gone (corners rounded), with what stood on it; their stored goods lie in recovered-goods stacks nearby. Trees, ruins and map objects at 3–6 tiles are untouched (trees die from the soil radiation).
12. **Contamination.**
    - Radioactive water fills the crater and spills over its rim: on flat ground about 1,060 units of radioactive water (530 in the bowl), plus about 60 over the footprint, then 0.5/h for 240 h from one saved continuous source.
    - Soil radiation is ≥ 0.5 on the ground left at the footprint edge and ≥ 0.16 at 12 tiles, and crops in that radius die. The crater floor is irradiated by the flood standing on it.
    - Submerged columns within 12 tiles carry `WaterRadiation > 0`, and pumps there refuse.
13. **Save/reload after a meltdown.** The reactor, the crater and the destroyed buildings stay gone and the source's remaining hours are preserved. A save made after the dev command but before the next tick (paused) melts down on the first tick after load.

**Waste leaks**

14. **Vault.**
    - At 1,440 casks: one "90% full" notification and the warning status.
    - At 1,600: the "full" notification and the leaking alert.
    - After 24 h full: stock −4, sludge +1.2 at the footprint centre, soil +0.16 within 3 tiles (a rounded outline), a leak notification, and the panel shows "Leaks so far: 1".
15. **Refinery** (`WasteRefining`, sludge not hauled).
    - At 135/180 sludge: the warning.
    - With no room for 6: the "full" notification.
    - After 24 h: sludge −6, world sludge +1.2, soil +0.16 within 3 tiles.
    - Paused or automation Off: `State == Sealed` and no leak.
16. **Save/reload.** Hours full and the leak count are preserved.

## Open questions

- **Maintenance stop or goods.** Maintenance is a 24-hour stop, not Grease + MachineCore consumption. The reactor's only inventory is its recipe inventory: `ManufactoryInventoryInitializer` plus `RecipeGoodDisallower`, which Moddable Recipes rebuilds on recipe change. A `GoodConsumingBuilding` cannot coexist with it (two `IGoodProcessor`s). Consumed maintenance goods would need the Restaurant-style Harmony patches on both.
- **Crew and maintenance meltdowns.** They currently cost power through SCRAMs but cannot melt the core alone. Workers are released when the building is blocked, and they go home off shift, so operator counts mean something only while running.
- **Demolition and deletion.** Demolishing a hot reactor removes it without contamination. Deleting a full vault destroys its casks silently, despite the "processed or moved before demolition" text.
- **Unverified in game:**
  - status sprite names, which are placeholders;
  - whether characters killed inside the reactor and then ejected by the deletion behave well (native `ExplosionService` uses the same order);
  - the crater, the blast and the terrain-physics cascade on real terrain (slopes, cliffs, water next to the reactor), and how far the flood spreads before it evaporates;
  - living characters standing on blast buildings 3–6 tiles away when they vanish (native deletion handles them as after any explosion or demolition);
  - the dialog camera move;
  - the sludge flow visuals at these volumes;
  - the tuning itself.
