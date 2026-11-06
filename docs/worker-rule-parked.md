# Science-scaled worker rule (parked 2026-10-30)

The user asked for later-game buildings to need more beavers, then parked it to focus on the building compaction pass. Nothing is implemented. These are the research findings and the approved plan.

## Findings (decompiled Timberborn 1.1.2.8)
- **Production scales with crew.** `ProduceExecutor.Tick` calls `Manufactory.IncreaseProductionProgress(deltaHours x WorkingSpeedMultiplier)` once per producing worker, and progress = hours / `CycleDurationInHours` x power efficiency. `CycleDurationInHours` is therefore worker-hours per cycle. Raising `MaxWorkers` alone raises output per building and doesn't increase beavers per unit.
- **Slots:** workers beyond the visible slots are hidden by `WorkplaceSlotManager` (`CharacterModel.Hide`) and keep working. Every ruled building has a single "Entrance" slot, so no slot data is needed.
- **Hard limit:** `Workplace.ValidateEnterable` throws if `EnterableSpec.LimitedCapacityFinished` is set and `CapacityFinished < MaxWorkers`. Only the Hospital is limited (30). The validator should check this.
- **Saves:** existing buildings keep their saved desired crew, capped at the new maximum, and players raise it by hand.
- **Side effects:** injuries roll per worker-hour, so there are more per unit of output. Bot wear and maintenance goods also rise per unit. `WorkplaceUpkeep` uses Cycle / MaxWorkers, so drill-bit use per unit stays the same.

## Approved plan
- **Rule:** add `lategameRule.workers` to `tools/building_construction_costs.json`. Every workplace at 2,000 science or more gets `max(base, round(6 x (science / 2000)^0.25))` workers, with per-building overrides kept in the data.
- **Code:** put `scaledWorkers` beside `scaledPower` in `tools/lategame_costs.mjs`, and call it at every generator that writes `MaxWorkers` (grep `tools/*.mjs`).
- **Recipe durations:** scale each ruled building's recipes by `CycleDurationInHours x new/base workers`. Full-crew output per building stays the same, and beavers per unit go up.
- **Exempt:** the RadioactiveSludgeOutfall, RadioactiveSludgeRecoveryPump and RadioactiveWasteExport (one worker each), and the GroceryStore (one attending clerk runs the service).
- **Hospital stays ruled:** its RequiredStaff follows `care.workers`, and treatment efficiency = crew / RequiredStaff.
- **GuidanceTelemetry:** it is shared by Mission Control (x3) and the Launch Pad (x1.875). Give the Launch Pad its own recipe id, and make sure a saved Launch Pad holding the old id still loads.
- **Nuclear Reactor:** goes from 6 to 28 trained operators. The user may want this lowered, so keep it easy to override.
- **Checks and texts:** add `validate_worker_rule.mjs`; `validate_all` picks up `validate_*.mjs` automatically. Update the tests that hard-code worker counts (`validate_vertical_slice_content`, `validate_grocery_exports`, `validate_research_exports`, the workbooks), the descriptions, the docs and `audit_progression.mjs`.

## Worker table

Buildings marked "unchanged" are already at or above the floor.

| Building | Science | Workers |
|---|---|---|
| Chemical Works | 4,000 | 8 (unchanged) |
| Limestone / Sandstone Quarry | 4,000 | 4 -> 7 |
| Steel Mill | 4,500 | 6 -> 7 |
| Precision Machine Works | 5,000 | 6 -> 8 |
| Deep Mine | 6,000 | 6 -> 8 |
| Archive Excavation | 9,000 | 4 -> 9 |
| Electrolysis Plant | 10,000 | 5 -> 9 |
| Cryogenic Liquefaction Plant | 12,000 | 6 -> 9 |
| Materials Laboratory | 12,000 | 4 -> 9 |
| Hospital | 25,000 | 6 -> 11 |
| Mission Control | 30,000 | 4 -> 12 |
| Rocket Assembly Hangar | 50,000 | 10 -> 13 |
| Launch Pad | 80,000 | 8 -> 15 |
| Uranium Processing Plant | 200,000 | 6 -> 19 |
| Radioactive Waste Refinery | 500,000 | 6 -> 24 |
| Nuclear Reactor | 1,000,000 | 6 -> 28 |
