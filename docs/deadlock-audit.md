# Deadlock audit

Status 2026-11-03. User request: "Let's find anywhere the user can deadlock themselves and change the recipes up a bit. Please look through." Static audit of the generated Iron Teeth economy (vanilla plus Deep Frontier): recipes, construction costs, workplace upkeep, goods-consuming buildings, specialist training, food services, map resources and unlock order. One deadlock is fixed (D1). The rest are verified safe, accepted by design with a check that fails if they change, or proposed for a decision. None of it has been played in game; `tools/STATUS.md` records runtime verification.

The check is `tools/validate_deadlocks.mjs` (a validate_all check, `deadlocks`). It covers what `tools/audit_progression.mjs` does not model, so it does not repeat the audit's construction-good, recipe-input and bootstrap checks.

## Findings

| ID | Finding | Severity | Status |
|---|---|---|---|
| D1 | The Deep Mine wore Steel drill bits, and Steel is made from mined deep ore | High: the permanent deep ore source, and all the late game behind it, stops for good | **Fixed**: Metal Block bits |
| D2 | Technical School programs against the specialist-only buildings | (would be High) | Verified: no training supply needs its own specialists (after D1) |
| D3 | The Deep Mine is built from finite deep ore (Deep Iron gate, Steel) | Low | Accepted by design; deep-ore item for the coordinator |
| D4 | The quarries cost Deep Iron; renewable Deep Iron needs the Deep Mine, whose concrete lining needs quarry stone | Very low | Accepted; proposal P3 |
| D5 | Contaminated water exists from the first radioactive tide (cycle 15), but nothing takes it before 300,000 science, and its storage cannot be deleted | Medium (stuck storage, no production stop) | Proposal P1 |
| D6 | Reactor Bots can be made from 300,000 science, but they can only charge at the Reactor Charging Bay (400,000) | Low (recovers at 400,000) | Proposal P2 |
| D7 | Deep ore: the Deep Drill and its finite sources | — | Items for the coordinator (the Deep Drill agent owns these files) |
| S1-S13 | Soft risks that ordinary play or vanilla mechanics resolve | Low | No change; listed below |

### D1. Deep Mine drill bits (fixed)

- **Chain:** Deep Ore ← Deep Mine ← Steel drill bits (0.1 per full-crew hour; production stops without them, `WorkplaceUpkeep.cs`) ← Steel Mill ← 2 Deep Iron + 2 Coal + 1 Limestone ← Deep Ore Processor ← Deep Ore. One steel embodies about 2.33 deep ore.
- **How a player gets there:** the mine burns its steel stock (15 units at the mine) while the finite Deep Ore Sources are spent and no steel is left in storage, for example after spending it on steel structures, rockets or bot frames. The mine shows "Waiting for drill bits" and nothing can ever make steel again, so Alloy, Machine Cores, Electronics, Power Modules, fuel, rockets and the reactor all stop.
- **Specialists** (coordinator brief): the same loop ran through training. Metallurgy needs Deep Iron; Deep Iron needs the Deep Mine; the mine needed Steel; Steel needs metallurgists at the Steel Mill. If the metallurgists died (the Steel Mill is Extreme danger, 2% of injuries fatal) after the sources were spent, they could not be retrained.
- **Fix (`tools/workforce_risks.json` `workplaceUpkeep`):** the Deep Mine wears **0.3 Metal Block** per full-crew hour (0.1 Steel by raw effort: 0.1 × 11.45 / 4.2 = 0.27, rounded up), with its 0.1 Concrete shaft lining unchanged. This is the change the Deep Drill got on 2026-10-31 for the same reason. Metal Block is renewable from the Efficient Mine (4,000) and the Smelter, and needs no deep ore. The role `SteelDrillBits` is removed; the mine uses `DrillBits` ("Waiting for drill bits: production has stopped until haulers bring metal blocks."). Description: "Uses up metal blocks as drill bits and concrete as shaft lining; stops without them." The mine's 15-unit stock now lasts 50 full-crew hours (150 with steel).
- **Steel keeps ongoing uses:** the Deep Well's drill bits, the reactor's casks (1 per 2-hour cycle), rocket airframes and propulsion, reinforced bot frames, Reactor Bot plating, Alloy, and steel structures.
- **Saves:** a saved steel part-unit at a mine is dropped with a log warning (`WorkplaceUpkeep.Load`). Steel in the mine's stock becomes a leftover that haulers carry out (`BotMaintenanceInventory` and Moddable Recipes' leftover rule). The Deep Drill change of 2026-10-31 used the same path. Not tested in game.

### D2. Technical School programs and specialist-only buildings (verified)

The coordinator's rule: no training supply may depend on a building that needs that same specialist. The beaver-specialist path must work on its own, so the 0.8.5 Reactor Bot bypass (any workplace can be set to Reactor Bots) is not counted.

| Discipline | Needed by (science) | Supplies (`workforce_risks.json` school) | Producers (crew) | Trainable from |
|---|---|---|---|---|
| Metallurgy | Steel Mill (10,000) | Metal Block, Deep Iron, Corn Ration | Smelter; Deep Ore Processor ← Deep Mine (open crews; Metal Block and Concrete upkeep since D1); Food Factory | 2,200 (school; Deep Iron from 1,200) |
| Nuclear | Nuclear Reactor (1,000,000) | Electronics, Yellowcake, Medicine | Precision Machine Works; Uranium Processing Plant; Public Health Lab (all open or beaver crews) | 300,000 |
| Flight | Launch Pad (200,000) | Electronics, Recovered Telemetry, Canned Fish | Precision Machine Works; **Mission Control's Guidance telemetry** (beaver crew, 75,000; the Launch Pad's own copy of the recipe needs flight engineers and is not needed); Food Packaging Works | 75,000 |

Recovered Telemetry before the first launch: Mission Control (75,000, beaver crew) makes Guidance Computers (4 Electronics, 2 Machine Cores, 2 Recovered Artifacts, 1 Grease) and Guidance telemetry (1 Guidance Computer, 2 Recovered Artifacts, 1 Metal Part). Its artifacts come from the Archive Excavation (25,000, open crew) or the Human Record Caches, so neither needs a flight engineer. The validator trains a discipline only from goods available without it, and fails if any program's goods need its own discipline (fault injection: Metallurgy needing Steel, and Mission Control without Guidance telemetry, both fail).

### D3. The Deep Mine is built from finite deep ore (accepted by design)

- **Chain:** the Deep Mine costs 80 Deep Iron (20 of them the gate that keeps the permanent mine behind the drill phase) and 60 Steel. Both come from deep ore, which is renewable only from a running Deep Mine.
- **First mine:** built from drilled ore. The map check (`prepare_deep_frontier_map.py` `finiteDeepOreMargin`) holds the Deep Ore Sources at or above the deep ore of every building up to the mine plus 5%: 1,437 (1,509 with the margin) against 17,000-18,000 on every built-in map.
- **Stuck case:** losing the last Deep Mine (a meltdown blast within 6 tiles, or deconstruction) after the sources are spent, with no Deep Iron and Steel in storage. A second mine is always built from the first (every map has at least two veins with mine sites).
- **Check:** `rebuild:DeepMine.IronTeeth` and `finite-replacement:DeepOre` are accepted in `validate_deadlocks.mjs`, with this reason; each fails as stale when the design changes. The slow refill of the Deep Ore Sources (in progress, Deep Drill agent) removes the stuck case.

### D4. Quarries and the Deep Mine's concrete lining (accepted)

- **Chain:** each quarry costs 35 Deep Iron. Renewable Deep Iron comes from the Deep Mine, whose shaft lining is Concrete, and Concrete is 3 Sandstone + 2 Cement (3 Limestone + 1 Brick). With the pits spent, that stone is renewable only from the quarries.
- **Stuck case:** the last Sandstone (or Limestone) Quarry is lost after both the outcrops and the Deep Ore Sources are spent, with no Concrete and no Deep Iron in storage.
- **First build is fine:** the quarries (9,000) come before the mine (15,000) and take drilled Deep Iron.
- **Check:** `rebuild:SandstoneQuarry.IronTeeth` and `rebuild:LimestoneQuarry.IronTeeth` are accepted with this reason. Proposal P3 would remove the loop.

### D5. Contaminated water before any consumer (proposal P1)

- **Chain:** the radioactive tide (optional weather; Normal: from cycle 15, 25% per cycle) irradiates water and banks, and stored Water in irradiated barrels and tanks turns into Contaminated Water (`docs/radiation.md`). That storage cannot be deleted while it holds the good (`HazardousStorageDeletionBlocker`), and carrying it irradiates beavers (0.5% per carrying hour).
- **No consumer early:** nothing takes Contaminated Water before the Radioactive Waste Export (300,000). The refinery's two recipes come at 600,000. The Radioactive Water Outfall (50,000, unlocked with the Hospital "so tide water can be cleaned up before the nuclear stage") releases only Radioactive Water goods.
- **Modelling gap:** `audit_progression.mjs` `MAP_SOURCES` dates Contaminated Water from the refinery (600,000), so the audit reports the export's recipe as a late input. In play it can exist at any science once tides are on.
- **Effect:** the tanks and barrels stay full and cannot be removed or reused for about 250,000 science. Production keeps running.
- **P1:** add a recipe to the Outfall, "Release contaminated water: 30 Contaminated Water → nothing, 1 h" (`radiation_content.mjs`). The outfall releases its fixed 0.6 radioactive volume per cycle, as for 3 Radioactive Water goods; 30 matches the refinery's decontamination, where 10 Contaminated Water hold the radiation of one Radioactive Water good. It needs no new good, building or code. **Taste:** the survival design says contaminated waste leaves the map (the export), but the outfall already pours Radioactive Water into a river. User decision.

### D6. Reactor Bots before the Reactor Charging Bay (proposal P2)

- **Chain:** the Bot Assembler's Reactor bot recipe and the retrofit need Reactor Power Cells (Uranium Processing Plant, 300,000). Reactor Bots charge only at the Reactor Charging Bay (400,000; they never use the vanilla Charging Station). The bay's own cost (2 Reinforced Bot Frames, 2 Reactor Power Cells, Enriched Fuel as fuel) is available from 300,000.
- **Effect:** Reactor Bots made between 300,000 and 400,000 run out of charge (the critical charge state: the native out-of-energy pose and -3 wellbeing) with nowhere to charge until the bay unlocks. This recovers once the bay is unlocked, so it is not a hard deadlock.
- **P2:** move the Reactor Charging Bay from 400,000 to 300,000 science, with the plant that makes the cells. It is a declared upgrade of the Charging Station, so the menu-order rule keeps it beside the station. Its cost tier (T5) and its power (exempt, 5,000 hp) do not change. Taste: the 2026-11-01 science curve placed it at 400,000 on purpose.

### D7. Deep ore items for the coordinator (Deep Drill agent's files, not edited here)

1. The Deep Drill's recipe "1 Deep Ore + 3 Water → 1 Deep Ore" is a pass-through from the Deep Ore Source stockpile (being redesigned, with a slow refill).
2. **Deep ore spent outside the path to the Deep Mine** is not in the finite budget, which counts one of each building:
   - steel structures from 11,250 science: columns cost 20-120 Steel, the 3x3 decks 108 (about 250 deep ore each);
   - the Coal Power Plant from 10,000: 1 Coal per hour, a third of a deep ore, about 8 a day at full load;
   - Metallurgy training: 0.75 Deep Iron per hour while anyone studies, 1.5 deep ore.

   The sources hold more than 15,000 beyond the 1,437 the path needs, so only deliberate heavy spending strands a settlement before the mine. Since D1, a running mine no longer needs ore-made goods, so once it runs the remaining stock no longer matters.
3. D3: rebuilding the last Deep Mine needs deep ore; the refill resolves it.
4. The quarries' 35 Deep Iron (9,000) come before the mine. A settlement that spends all deep ore before 9,000 and then its pit stone has no quarries, so no concrete, so no Deep Mine (725 Concrete): a double exhaustion, covered by the budget and resolved by the refill.
5. `validate_deadlocks.mjs` classifies `DeepOre` as finite (`MAP_SOURCE_KIND`: "run out or refill slowly"). Keep it finite after the refill unless the refill alone is meant to sustain the late game. The Deep Drill's own upkeep (0.1 Metal Block) is renewable, and the map tool still fails if its bits ever embody deep ore.

### Soft risks (no change)

| ID | Risk | Why no change |
|---|---|---|
| S1 | The first Cement Kiln costs 95 pit Limestone (the Stone Crusher 35), and the Limestone Quarry's bricks are fired in a kiln | Every limestone use before the quarries runs through that chain, so a settlement that spends its outcrops has a kiln. The stone budget sizes the outcrops for one of each building. With buildings standing, the validator's finite-replacement check passes. |
| S2 | Power black start: the Deep Mine (7,700 hp), the coolant chain and the coal and oil plants need power to make their own fuel | Vanilla water wheels, power wheels and log-fired steam engines need no Deep Frontier goods, so a dead grid restarts. Power supply is outside the static model. |
| S3 | Radioactive tide: pumps refuse at 0.5% radioactive; the Hospital (12 Water per hour), Bathhouse and every water recipe run on stored water; closed lakes stay radioactive until drained or pumped out by the Recovery Pump (50,000) | A chosen survival risk (`deep-frontier-survival-design`); tides can be turned off on the new-game screen. |
| S4 | The fish loop (Fresh Fish ↔ Juvenile Fish at the hatchery and fishery) restarts only from the Fisher Flag, which refuses radioactive or bad water | The loop gains fish every cycle (1 juvenile → 3 fish; 1 fish → 2 juveniles), so it stops only if both stocks reach zero while every bank is contaminated. |
| S5 | Byproducts with no consumer at unlock, e.g. Concentrated Waste from Pure Water (1,800) before Brine Chemical (9,000) | Ordinary goods; storage can be deleted. Of the three hazardous goods that cannot be deleted, Radioactive Waste has the export and vault at its own unlock (300,000) and Radioactive Water (sludge) has the outfall with the recovery pump (50,000). Contaminated Water is D5. |
| S6 | Goods-consuming buildings take goods without priority: the Coal Power Plant against the Steel Mill's coal, the Technical School's supplies against construction | Native pause, storage and haul priority settings. |
| S7 | Vanilla Decontamination Pod (400) uses Extract from the Centrifuge (600) | Vanilla's own order; the validator's unlock check covers Deep Frontier buildings only. |
| S8 | Restaurant (1,000) serves any of Fresh Fish, Berries, Fermented Mushroom, Eggplant Ration (all from 300 or less); the Grocery Store (3,000) needs 3 of its 6 foods (all 6 available by then) | Checked (operating-unlock and renewable-economy). |
| S9 | Hospital (50,000): Medicine (1,000), Extract (600), Water | Checked. |
| S10 | Reactor: coolant (Cryocoolant from 9,000), Steel and Concrete casks, waste disposal (export and vault at 300,000), reactor operators (Yellowcake from 300,000), first core load | Checked; all before 1,000,000 and renewable. |
| S11 | Rocket missions: a failed launch consumes the whole rocket | Every input is renewable (checked). |
| S12 | Narrative chapters and Human Record Caches | Chapters gate nothing; artifacts are renewable from the Archive Excavation's recipe. |
| S13 | Reactor Bot workplaces: each workplace unlocks Reactor Bots for 3 times its bot unlock (District Center 3,000; Nuclear Reactor 3,003,000) | An optional bypass; the beaver path stands alone (D2). |

## Proposals for the coordinator

| ID | Change | Fixes | Taste question |
|---|---|---|---|
| P1 | Outfall recipe "Release contaminated water": 30 Contaminated Water per hour | D5 | Contaminated water poured into a river, not shipped off the map |
| P2 | Reactor Charging Bay 400,000 → 300,000 science | D6 | The nuclear stage's order |
| P3 | Deep Mine shaft lining Concrete → Brick (0.1 → about 0.1 Brick per hour by value: Concrete 1.24, Brick 1.11) | D4 (and lets the mine run while the quarries are down) | Concrete loses an ongoing industrial use (user preference: concrete and steel keep industrial uses); keeps Materials Research and the reactor's casks |

## Model and checks (`tools/validate_deadlocks.mjs`)

- **Operating goods:** a building runs only with its workplace upkeep (`FrontierWorkplaceUpkeepSpec`), the goods its native consumer uses (`GoodConsumingBuildingSpec`: fuel and supplies) and the Deep Well's bits (`DeepWellSpec`). A specialist-only building (`FrontierSpecialistWorkplaceSpec`) also needs its discipline to be teachable, from a school program (`FrontierSpecialistSchoolSpec`) whose supplies are available. These gate all of the building's recipes, so a good never comes first from its own building's output.
- **Map sources:** each `MAP_SOURCES` good is classified finite (ruin scrap, pit stone, Deep Ore Sources) or renewable (shore fishing, contaminated water as a waste). A new map source fails until it is classified.
- **renewable-economy:** every building standing and no finite source. Every good the economy uses must still be made: recipe inputs and fuel, operating goods, construction goods, the supplies of every required discipline, and enough foods for the restaurant and grocery. Before D1, 25 goods failed, every one behind "DeepOre.Mine@DeepMine (needs HighGradeSteel to run)".
- **discipline-trainable:** every required discipline can be taught from renewable goods without itself.
- **operating-unlock:** at each Deep Frontier building's unlock, its operating goods, discipline and foods are producible (buildings unlocked by then, built from producible goods, finite sources allowed, without the building itself).
- **rebuild:** with every other building standing and no finite source, each building's construction goods are made without it (goods already failing renewable-economy are not repeated).
- **finite-replacement:** for each finite map good, a renewable producer of it can be built and run at its own unlock without that finite source (scrap: Efficient Mine 4,000; Sandstone and Limestone: quarries 9,000; deep ore: Deep Mine 15,000, accepted, D3).
- **Accepted** (`ACCEPTED`, with reasons): `rebuild:DeepMine.IronTeeth`, `finite-replacement:DeepOre` (D3), `rebuild:SandstoneQuarry.IronTeeth`, `rebuild:LimestoneQuarry.IronTeeth` (D4). Each fails as stale when it stops failing.
- **Fault injection** (mirror only; each fails): Deep Mine on Steel bits; Metallurgy needing Steel; Mission Control without Guidance telemetry; Deep Drill on Steel bits (operating-unlock at 1,000); Coal Power Plant at 1,000 science; Deep Ore Processor costing Deep Iron; a grocery list with only 2 foods available at its unlock. Unchanged data passes.
- `node tools/validate_deadlocks.mjs [dataRoot] [--print]`; `--print` lists each discipline's training route and each finite good's renewable producers.
- **Out of scope:** rates, workforce, power supply, water and radiation at runtime, map placement.
