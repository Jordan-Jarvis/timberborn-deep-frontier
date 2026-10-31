# Reactor meltdown and radioactive waste leaks

Status 2026-10-22: source written, compile-checked and generated in a scratch copy of the repository. Nothing here has been built, launched or played; `tools/STATUS.md` records runtime verification.

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

The meltdown runs in the service's singleton tick, the place native `ExplosionService` deletes block objects.

1. **Geometry.** Open fluid cells in every column within 12 tiles of the footprint (Chebyshev distance), using `IRadiationService.TryFindOpenCell` at the building's base height.
   - Buildings are not water obstacles in 1.1.2.8; only `WaterObstacle`/`FinishableWaterObstacle` add them. The footprint is therefore already open.
   - If no footprint column is open, the meltdown throws before any effect.
2. **Casualties.**
   - Everyone inside, and every mortal character within 2 tiles, dies through `Mortal.DieInstantly` ("<name> was killed in the reactor meltdown.").
   - Beavers within 16 tiles get `RadiationExposure.AddDose(1.5)`, which irradiates them: 10 days of hospital care, otherwise fatal.
3. **Contamination.**
   - 60 sludge units (300 goods' worth) spread over the footprint.
   - A saved continuous source at the core: 0.5 units/h for 240 h (10 days, 120 units).
   - Soil radiation falls linearly from 0.5 at the footprint to 0.16 at 12 tiles. The edge stays above the 0.15 crop threshold, so crops in the whole radius die. Recovery at the soil half-life of 120 days: about 11 days at the edge, about 140 days half way, about 210 days at the footprint (longer wherever sludge lies).
   - Submerged columns also get dissolved radiation, 2.0 → 0.2. It has a 20-day half-life and travels with the water.
4. **Destruction.** Native `EntityService.Delete`, whose `EntityDeletedEvent` drives the native deconstruction particles. Also a global explosion sound, a notification and a dialog with "Show the site", which moves the camera to the site.

## Waste leaks (`WasteLeakSpec`, `WasteLeak`)

| | Radioactive Waste Vault | Radioactive Waste Refinery |
|---|---|---|
| Trigger | `StorageFull`: its waste fills the whole stockpile (1,600) | `OutputBlocked`: the current recipe produces sludge and there is no unreserved room for one more cycle, while unblocked |
| Warning (status + notification) | 90% full | 75% of its sludge capacity |
| Leak every | 24 h full | 24 h full |
| Per leak | 4 casks destroyed → 4 × 0.3 = 1.2 sludge units | 6 sludge goods destroyed → 6 × 0.2 = 1.2 units |
| Soil | +0.16 within 3 tiles of the footprint, which kills crops after one leak | same |
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
| `src/DeepFrontier/Scripts/Meltdown/MeltdownConfigurator.cs` | `[Context("Game")]` configurator |

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

9. **At heat 1.**
   - The reactor entity is deleted within a tick.
   - The meltdown notification and dialog appear, and "Show the site" moves the camera there.
   - Everyone inside and every character within 2 tiles of the footprint is dead.
   - Beavers 3–16 tiles away have the Irradiation need active.
   - Bots in that ring are unaffected.
10. **Contamination.**
    - `TotalSludgeVolume` jumps by about 60, then rises by 0.5/h for 240 h from one saved continuous source.
    - Soil radiation is ≥ 0.5 on the footprint and ≥ 0.16 at 12 tiles, and crops in that radius die.
    - Submerged columns within 12 tiles carry `WaterRadiation > 0`, and pumps there refuse.
11. **Save/reload after a meltdown.** The reactor is gone and the source's remaining hours are preserved.

**Waste leaks**

12. **Vault.**
    - At 1,440 casks: one "90% full" notification and the warning status.
    - At 1,600: the "full" notification and the leaking alert.
    - After 24 h full: stock −4, sludge +1.2 at the footprint centre, soil +0.16 within 3 tiles, a leak notification, and the panel shows "Leaks so far: 1".
13. **Refinery** (`WasteRefining`, sludge not hauled).
    - At 135/180 sludge: the warning.
    - With no room for 6: the "full" notification.
    - After 24 h: sludge −6, world sludge +1.2, soil +0.16 within 3 tiles.
    - Paused or automation Off: `State == Sealed` and no leak.
14. **Save/reload.** Hours full and the leak count are preserved.

## Open questions

- **Maintenance stop or goods.** Maintenance is a 24-hour stop, not Grease + MachineCore consumption. The reactor's only inventory is its recipe inventory: `ManufactoryInventoryInitializer` plus `RecipeGoodDisallower`, which Moddable Recipes rebuilds on recipe change. A `GoodConsumingBuilding` cannot coexist with it (two `IGoodProcessor`s). Consumed maintenance goods would need the Restaurant-style Harmony patches on both.
- **Crew and maintenance meltdowns.** They currently cost power through SCRAMs but cannot melt the core alone. Workers are released when the building is blocked, and they go home off shift, so operator counts mean something only while running.
- **Demolition and deletion.** Demolishing a hot reactor removes it without contamination. Deleting a full vault destroys its casks silently, despite the "processed or moved before demolition" text.
- **Unverified in game:**
  - status sprite names, which are placeholders;
  - whether characters killed inside the reactor and then ejected by the deletion behave well (native `ExplosionService` uses the same order);
  - the dialog camera move;
  - the sludge flow visuals at these volumes;
  - the tuning itself.
