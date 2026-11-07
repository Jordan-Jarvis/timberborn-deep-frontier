# Progression and construction balance

Status 2026-10-21. These are the rules for unlock order, construction cost and chain reachability, with the static audit that checks them. They are authored balance plus static checks. None of this has been played or tested in game. `tools/STATUS.md` holds the runtime verification state.

## Progression sets (2026-10-31)

User request: "we need our own progression sets", ladders like vanilla Iron Teeth's Logs → Planks → Gears → Treated Planks and Scrap Metal → Metal Parts / Metal Blocks. Each step below consumes the one before it. Good ids are unchanged: Deep Iron is `DeepAlloy` and Steel is `HighGradeSteel` (display names only, so saves load as before).

| Ladder | Step | Building (science) | Recipe |
|---|---|---|---|
| Deep metal | Deep Ore | Deep Drill (1,000; finite source), Deep Mine (15,000; vein) | gathered |
| | Deep Iron | Deep Ore Processor (1,200) | 2 Deep Ore + 1 Water + 1 Metal Part → 1, 1.5 h |
| | Steel | Steel Mill (10,000) | **2 Deep Iron** + 2 Coal + 1 Limestone → 2, 4 h (was 4 Metal Block; value 11.8 → 11.4) |
| | Alloy | Steel Mill (10,000) | 2 Steel + 1 Deep Iron → 2, 1.5 h |
| Chemistry | Crude Oil | Deep Ore Processor (1,200) | 1 Deep Ore + 3 Water → 6, 2 h |
| | Chemical | Chemical Works (9,000) | **2 Crude Oil** + 1 Extract → 2, 2 h (was 4 Badwater; value 3.12 unchanged). Chemical from brine stays: 3 Concentrated Waste + 1 Extract → 2 |
| | Polymer | Chemical Works (9,000) | 3 Crude Oil + 1 Chemical + 2 Water → 3, 3 h |
| Masonry | Sandstone, Limestone | pits (300), quarries (9,000) | gathered |
| | Brick | Stone Crusher, Cement Kiln (600) | 3 Sandstone → 8 Dirt; 4 Dirt + 1 Water → 4 Brick |
| | Cement | Cement Kiln (600) | **3 Limestone + 1 Brick** → 2, 2 h, 1 Log (crushed brick in lime mortar; was 3 Limestone + 1 Dirt, 2026-10-31: masonry is a strict ladder, Brick → Cement → Concrete, with the same Dirt per Cement) |
| | Concrete | Concrete Mixer (1,000) | 3 Sandstone + 2 Cement + 4 Water → 8 |
| Machinery | Gear | vanilla Gear Workshop (100) | 1 Plank → 1 |
| | Machine Core | Precision Machine Works (12,000) | 2 Alloy + 1 Polymer + 2 Gear + 1 Deep Iron → 1, 2 h |
| | Electronics | Precision Machine Works (12,000) | 1 Machine Core + 2 Metal Part + 1 Polymer → 1, 2 h |
| | Power Module | Precision Machine Works (12,000) | 1 Electronics + 1 Alloy + 2 Metal Part + 1 Coal → 1, 2 h |
| Water | Pure Water | Water Treatment Plant (1,800) | 10 Water + 1 Filter Media → 8 (+1 Concentrated Waste), 8 h |
| | Reactor Coolant | Water Treatment Plant (1,800; Cryocoolant from 9,000) | 4 Pure Water + 1 Filter Media + 1 Cryocoolant → 4, 4 h |
| Nuclear | Uranium Ore | Deep Ore Processor (1,200) | 2 Deep Ore + 4 Water → 1, 3 h |
| | Yellowcake | Uranium Processing Plant (300,000) | 3 Uranium Ore + 1 Chemical + 2 Water + 1 Oxygen → 2, 2 h |
| | Enriched Fuel | Uranium Processing Plant (300,000) | 2 Yellowcake + 1 Machine Core + 1 Power Module + 1 Hydrogen → 1 (+1 waste), 1 h |
| | Reactor Power Cell | Uranium Processing Plant (300,000) | 1 Enriched Fuel + 2 Power Module + 2 Electronics + 2 Cryocoolant → 1, 6 h |

Badwater keeps its uses: vanilla Extract (Centrifuge), which every Chemical recipe needs, and Badwater filtering at the Radioactive Waste Refinery. Metal Block loses Steel and gains the Deep Drill's drill bits. The Deep Drill (1,000) used to wear Steel bits that only exist from 4,500, and Steel now needs drilled ore, so the drill now wears 0.1 Metal Block per full-crew hour. The Deep Well keeps Steel bits. The Deep Mine kept them until 2026-11-03, when the deadlock audit found the same loop one step later (Steel is made from mined ore, so a mine out of steel after the Deep Ore Sources were spent could never restart): it now wears 0.3 Metal Block per full-crew hour (`docs/deadlock-audit.md` D1). Its shaft lining is 0.1 Brick per hour since the same day (was 0.1 Concrete; proposal P3, user approved): Brick needs no quarry stone, so the mine runs while the quarries are down. Concrete keeps its ongoing uses, Materials Research and the reactor's casks.

**Construction costs climb the sets.** The stage (cost tier, fixed by the science unlock) decides which goods stand in for each visible material family (`materialRule.familyGoods`, unit ratios). The material cost rule is otherwise unchanged: the value follows each building's measured material mix, a family only uses goods producible without the building itself, and the gates stay. Gear and Machine Core keep their fixed basis amounts. Where a stage names them as a family good, the family's share is added on top (Gear for early metal, Machine Core from the frontier).

| Stage (tier) | Science | Wood | Metal | Masonry | Fixed machinery |
|---|---|---|---|---|---|
| Early (T1) | ≤ 600 | 2 Plank : 1 Log | Gear | Brick, pit stone | Gear |
| Industrial (T2) | ≤ 3,000 | Plank | 2 Metal Block : 1 Deep Iron | Concrete, Brick | Gear |
| Transition (T3) | ≤ 20,000 (8,000 until 2026-11-01) | 2 Plank : 1 Treated Plank | 2 Metal Block : 1 Deep Iron : 1 Steel | Concrete, Brick | Gear |
| Frontier (T4) | ≤ 75,000 (30,000 until 2026-11-01) | Treated Plank | 4 Alloy : 1 Machine Core | Concrete, Brick | Gear |
| Endgame (T5) | above | Treated Plank | 8 Alloy : 1 Machine Core : 1 Electronics : 1 Power Module | Concrete, Brick | Machine Core |

Availability still decides per building. Deep Iron appears from 1,200 science (not on the Deep Ore Processor itself), Steel from 10,000 (not on the Steel Mill), and Electronics and Power Modules from 12,000 (4,500 and 5,000 before the 2026-11-01 science curve). Bootstrap is unchanged: the first concrete chain stays concrete-free, and no building needs a good it is needed to make (`audit_progression.mjs`: 0 failures). The audit checks a family priced in a machinery good against the others, since its value cannot be told apart from the fixed amount; late-game rule buildings are still compared with the rule exactly.

**Per-building family goods (2026-11-03).** User request: "Can we remove machine cores and alloy from the requirements to build the hospital?" `materialRule.familyGoodsOverrides` lets one named building price a family in an earlier stage's goods, with its reason: `{"Hospital": {"families": {"metal": "T3"}, "reason": "..."}}`. The Hospital (50,000, frontier) cures irradiated beavers and must stay reachable before radioactive tides (cycle 15 by default), so its metal is priced in the transition goods (2 Metal Block : 1 Deep Iron : 1 Steel) instead of 4 Alloy : 1 Machine Core. The rule is otherwise unchanged: the family's value share is the measured one, the total value is the same basis value, amounts round up to 5, and its science, tier and other families stay. Hospital: 475 Treated Plank, 20 Alloy, 5 Machine Core, 440 Concrete, 460 Brick, 180 Gear → 475 Treated Plank, 35 Metal Block, 20 Deep Iron, 20 Steel, 440 Concrete, 460 Brick, 180 Gear. No other building changes. Checks (`tools/material_costs.mjs` at load and per building, `audit_progression.mjs`): the entry has exactly `families` and `reason`, a non-empty reason, known families and tiers, a measured building that the material rule prices (`material-override-unknown`); the named tier must be an earlier stage than the building's own; every good it names must be producible without the building at its science (it never drops a good silently, unlike the stage table); the audit checks the overridden family's goods and value share in the named stage's goods, and the bootstrap and unlock-order checks apply as before.

Totals over every Deep Frontier building (81 blueprints, structures included), before → after: Metal Block 9,535 → 4,280, Steel 5,411 → 3,346 (structures and gates; no longer a T4/T5 family good), Plank 3,310 → 2,820, Treated Plank 2,897 → 3,067, Deep Iron 455 → 550, Alloy 1,770 → 1,815, Machine Core 954 → 1,279, Electronics 0 → 205, Power Module 0 → 205, Gear 6,622 → 6,782, Concrete 101,805 → 100,355, Brick 9,128 → 9,023. The embodied value of each cost stays within a few percent (a value-preserving swap rounded up to 5). Small endgame buildings rise most, because each of four metal goods has a minimum of 5: Sludge Outfall and Recovery Pump ×1.7, Reactor Charging Bay ×1.4.

**Stone budget** (`prepare_deep_frontier_map.py builtin`): unchanged at 1,213 Limestone and 1,689 Sandstone of the 1,800 in pit range. The sets swap goods inside the wood and metal families, not the stone shares.

**Finite deep ore.** Steel, Alloy, Machine Core, Electronics and Power Module now all embody deep ore, so one of each building in the whole collection needs about 24,500 Deep Ore, against the 17,000-18,000 the built-in maps hold. The map check (`finiteDeepOreMargin`) now counts the buildings up to and including the Deep Mine (15,000 since the 2026-11-01 science curve; 6,000 before), because ore is renewable after it. They need 1,450 Deep Ore (1,523 with the 5% margin; 1,363 before the curve, which now puts the 12,000 Materials Laboratory below the mine) against 18,000 in the built-in sources. Drill-bit upkeep until then takes no deep ore: the check fails if the Deep Drill's bits ever embody it.

## Mineral recovery and permanent extraction (2026-11-04)

This replaces the November 3 district-pool design. Players mine visible outcrops and haul their products.

- **Raw Deep Ore:** collected by the vanilla Scavenger Flag. The Deep Drill consumes 1 raw ore + 3 Water per two-minute cycle to produce 1 Deep Ore, at 1,000 hp. Operating supplies are 0.1 Metal Block and 0.1 Treated Plank per full-crew hour; help/status text names these goods. The Stone Crusher also converts 3 raw ore into 8 Dirt.
- **Recovery:** empty raw-ore, sandstone and limestone outcrops remain and recover 20 units in five days. The timer is saved and the source panel shows its countdown. No accumulation beyond 20 while stock remains.
- **Permanent stone:** both quarries use only vanilla structural goods to build. No Sandstone, Limestone, Brick, Cement, Concrete, Deep Iron or Steel is required for their construction. A player who spent all finite stone can still build a quarry on its seam, even in an old save where the outcrops vanished.
- **Permanent ore:** the Deep Mine no longer requires Deep Iron or its derivative Steel to build. Metal Blocks supply its structural metal value. It retains its vein requirement, science, workforce, power and water requirements.
- **Balance:** one recovered ore outcrop averages 4 raw ore/day, about 9% of a Deep Ore Processor's 42.7 ore/day at full crew for 16 hours. The Deep Mine remains the sustained supply; recovery keeps progress possible after poor spending decisions. Quarry/mine footprint-based cost value is retained by the existing material rule, with explicit bootstrap family substitutions.
- **Validation:** construction-chain tests prove permanent stone is reachable without finite sources; the deadlock audit checks every slow source has a reachable industrial replacement. Map budgets retain substantial initial reserves and reject recharge rates that replace the permanent mine. Native hauling, depleted-source save/load and recovery have their own acceptance run; consult `tools/STATUS.md` for results.

Source/map authoring: `docs/source-authoring.md`. Canonical producers: `create_vertical_slice_content.mjs`, `construction_materials.json`, `workforce_risks.json`, `building_construction_costs.json`.

## Science curve and menu order (2026-11-01)

User requests: "Did we make sure our tech progression is clear and easy and the menu items are ordered correctly to guide them for buildings from left to right?"; "remember to update the science requirements for the later stage buildings and power plants and everything. The nuclear reactor is the last one."; "Right now it is relatively low, aside from the one plant." This supersedes the [Science curve (2026-10-29)](#science-curve-2026-10-29) where they differ. Static authoring and checks only; not played in game.

### Stages

Early and industrial unlocks (up to 2,500) stay near vanilla Iron Teeth (its tree tops out at 20,000 for the Earth Repopulator, most of it under 4,000). Each later stage climbs on its own band, the order inside every stage is unchanged, and the 1,000,000 Nuclear Reactor stays the single last unlock. The 12,000 Materials Laboratory (400 science per working hour) keeps its unlock, so it is now the stepping stone at the start of the transition stage instead of a frontier building.

| Stage (cost tier) | Science | Buildings (before → after) |
|---|---|---|
| Early (T1) | ≤ 600 | unchanged |
| Industrial (T2) | ≤ 3,000 | unchanged (up to the 2,500 Smog Scrubber), plus the Grocery Store 6,000 → 3,000 (follow-up) |
| Transition (T3) | ≤ 20,000 (was ≤ 8,000) | Chemical Works 4,000 → 9,000; Sandstone and Limestone Quarry 4,000 → 9,000; Steel Mill 4,500 → 10,000; **Coal Power Plant 4,500 → 10,000**; Precision Machine Works 5,000 → 12,000; Town Plaza 5,000 → 12,000; Materials Laboratory 12,000 (unchanged); Deep Mine 6,000 → 15,000; Bathhouse 6,000 → 15,000; **Reinforced Hydro Turbine 8,000 → 20,000** |
| Frontier (T4) | ≤ 75,000 (was ≤ 30,000) | Archive Excavation 9,000 → 25,000; Observation Deck 9,500 → 27,500; Electrolysis Plant 10,000 → 30,000; **Oil Power Plant 11,000 → 35,000**; Cryogenic Liquefaction Plant 12,000 → 40,000; Cryogenic Tank Farm 12,000 → 40,000; Hospital 25,000 → 50,000; Radioactive Water Recovery Pump and Outfall 200,000 → 50,000 (follow-up); Mission Control 30,000 → 75,000; Deep Well 30,000 → 75,000 |
| Launch program (T5) | above | Rocket Assembly Hangar 50,000 → 125,000; Launch Pad 80,000 → 200,000; mission payouts 100,000 and 250,000 → 250,000 and 500,000 (follow-up) |
| Nuclear (T5) | above | Uranium Processing Plant, Radioactive Waste Vault and Radioactive Waste Export 200,000 → 300,000; Reactor Charging Bay 250,000 → 400,000 (300,000 since 2026-11-03, with the plant that makes its power cells: `docs/deadlock-audit.md` D6); Radioactive Waste Refinery 500,000 → 600,000; **Nuclear Reactor 1,000,000 (unchanged, last)** |

**Approved follow-ups (2026-11-01, user approved the four proposals of the first pass).** The Radioactive Water Recovery Pump and Outfall (ids `RadioactiveSludgeRecoveryPump`, `RadioactiveSludgeOutfall`) unlock at 50,000 with the Hospital, so tide water can be cleaned up before the nuclear stage; they need nothing nuclear (the pump draws radioactive water from the river, the outfall releases it), and their cost tier moved T5 → T4 (`lategameTier`). The rocket missions pay 250,000 and 500,000 (`rocket_program_content.mjs`), more than the 400,000 the launch unlocks cost. The Grocery Store unlocks at 3,000 (industrial): it sells Canned Fish (1,400) and vanilla staples. The concrete platforms, side platforms and the Reinforced Overhang 8x1 are back to 500 science per size unit.

The power plants climb with their output: Coal 25,000 hp at 10,000, Hydro Turbine 40,000 hp at 20,000, Oil 90,000 hp at 35,000, Reactor 1,000,000 hp at 1,000,000. The Coal Power Plant unlocks with the Steel Mill, one step after the Chemical Works and quarries (5,200 hp each, ten Large Water Wheels until then).

Steel structures keep their tier: their science formulas are 2.5 times what they were (`structural_building_content.mjs`): steel columns 10,000 + 1,250 H (11,250-17,500, so the shortest unlocks after the Steel Mill that makes its steel), steel decks 1,500 n² (13,500 and 37,500, with their leg-deck tools), steel bridges 2,000 N (16,000-30,000) and steel cantilevers 2,500 N (25,000-37,500). The concrete platforms (scaffolds) and side platforms stay at 500 × k (k = n² + legs: 4,500-14,000) and the Reinforced Overhang 8x1 at 5,000: the first pass raised them 2.5× too (11,250-35,000), and the follow-up put them back, so every size is now a transition-tier piece (the 4x4 and 5x5 platforms and the 5x5 side platform cost a third less than at T4). Bot unlocks that follow the building moved with it: science + 1,000 for the expansion buildings and the quarries, equal to the science for the Deep Mine.

Sources: `frontier_progression.json` (`implementedBuildingScienceOverrides`, `nuclearScienceRule`, hospital, grocery, planned buildings, late-game wellbeing, power plants), `create_frontier_expansion_content.mjs` rows, `create_vertical_slice_content.mjs` (Deep Mine), `construction_materials.json` (quarries), `hydro_content.json`, `deep_well_content.json`, `super_bots.json`, `radiation_content.mjs`, `structural_content.json` and the formulas, and the tier bands in `building_construction_costs.json`. The narrative hints quote the new Chemical Works, Archive Excavation and Mission Control unlocks.

### What moved with the science

- **Construction costs are held.** The T3 and T4 bands moved with the curve (T3 ≤ 20,000, T4 ≤ 75,000), and every building keeps its order against every building that makes goods, so each one keeps its tier and its material world. Canonical generation changes no construction cost except one: the **Materials Laboratory**, which stays at 12,000 and so moves from T4 to T3: 245 Treated Plank, 25 Alloy, 10 Machine Core, 1,035 Concrete, 240 Gear → 190 Plank, 95 Treated Plank, 35 Metal Block, 20 Deep Iron, 20 Steel, 690 Concrete, 160 Gear (cost factor 4 instead of 6, transition-stage goods). The follow-ups change four more costs by tier: Grocery Store (T3 → T2) 210 Plank, 105 Treated Plank, 20 Metal Block, 10 Deep Iron, 10 Steel, 105 Concrete, 80 Gear → 395 Plank, 25 Metal Block, 15 Deep Iron, 60 Concrete, 60 Gear; Radioactive Water Recovery Pump (T5 → T4) 55 Treated Plank, 10 Alloy, 10 Machine Core, 5 Electronics, 5 Power Module, 205 Concrete → 20 Treated Plank, 5 Alloy, 5 Machine Core, 75 Concrete, 15 Gear; Radioactive Water Outfall (T5 → T4) 25 Treated Plank, 5 Alloy, 10 Machine Core, 5 Electronics, 5 Power Module, 570 Concrete → 10 Treated Plank, 5 Alloy, 5 Machine Core, 200 Concrete, 15 Gear; and the 4x4 and 5x5 concrete platforms and the 5x5 side platform (T4 → T3, factor 6 → 4), e.g. Concrete Platform 5x5 (3 high) 504 Concrete, 336 Metal Block, 168 Gear → 336, 224, 112.
- **Power draws follow the existing power rule** (floor = 2,000 × (science / 2,500)^0.75, unchanged), so they rise with the science: Chemical Works 3,500 → 5,200 hp, quarries 2,800 → 5,200, Steel Mill 3,100 → 5,700, Precision Machine Works 3,400 → 6,500, Deep Mine 4,000 → 7,700, Bathhouse 3,900 → 7,700, Grocery Store 3,900 → 2,300 (at 3,000 after the follow-up; 7,700 at 15,000), Archive Excavation 5,200 → 11,000, Electrolysis Plant 6,000 → 13,000, Cryogenic Liquefaction Plant 10,000 → 16,000, Cryogenic Tank Farm 6,500 → 16,000, Hospital 11,000 → 19,000, Mission Control 13,000 → 26,000, Rocket Assembly Hangar 19,000 → 38,000, Launch Pad 27,000 → 53,000, Uranium Processing Plant 53,000 → 73,000, Radioactive Waste Refinery 106,000 → 122,000. The Deep Well and the Reactor Charging Bay stay exempt; generator outputs are unchanged. The whole launch program (cryogenic line, hangar, mission control, pad) now draws about 162,000 hp, two oil plants.
- **Map budgets** (`prepare_deep_frontier_map.py builtin`): the stone budget up to the quarries is 1,050 Limestone and 1,599 Sandstone of 1,800 (1,028 and 1,574 before the follow-ups; the Grocery Store now unlocks below the quarries); the finite deep ore up to the Deep Mine is 1,437 (1,509 with the margin; 1,363 before the curve: the laboratory now unlocks before the mine), against 17,000-18,000 in the sources. Every built-in map passes. The concrete platforms are construction pieces and do not enter the stone count.

### Science economy and time to unlock

Rates: Inventor 1 science per working hour (one worker); Numbercruncher (1,500) 10 per hour, no workers, 500 hp, so 240 a day while powered; Materials Laboratory 400 per working hour, four workers, 6,500 hp, so 6,400 a day over 16 working hours, consuming 32 Gear, 16 Concrete, 8 Metal Block and 8 Water a day (the geochemical assay is the same rate on frontier samples). Rocket missions pay 250,000 and 500,000 once (100,000 and 250,000 before the follow-up). Science is spent on each unlock, so a stage costs the sum of what the player buys in it.

| Phase | Producers assumed | Science a day | Before the curve: science, days | After the follow-ups: science, days |
|---|---|---:|---:|---:|
| Save for the Materials Laboratory | 6 Numbercrunchers | 1,440 | 12,000, 8.3 | 12,000, 8.3 |
| Rest of the transition stage (10 buildings; the Grocery Store is now industrial) | 2 laboratories + crunchers | 14,240 | 57,000, 4.0 | 121,000, 8.5 |
| Frontier (11 buildings, with the recovery pump and outfall) | 4 laboratories + crunchers | 27,040 | 148,500, 5.5 | 497,500, 18.4 |
| Launch program (2 buildings) | 6 laboratories + crunchers | 39,840 | 130,000, 3.3 | 325,000, 8.2 |
| Nuclear, the reactor's needs (plant, export, refinery, reactor), less what the missions pay (350,000 before, 750,000 after) | 8 laboratories + crunchers | 52,640 | 1,550,000, 29.4 | 1,450,000, 27.5 |
| Nuclear, every building, less the missions | same | 52,640 | 2,400,000, 45.6 | 2,150,000, 40.8 (2,050,000, 38.9 since the Reactor Charging Bay moved to 300,000 on 2026-11-03) |

From the first Numbercruncher stage to the reactor, buying every non-structure building on the way and the reactor's own needs, research takes about 71 days instead of 50 (76 in the first pass, before the larger mission payouts and the cheaper Grocery Store), at a realistic build-up of laboratories (each is 6,500 hp and four workers; eight draw 52,000 hp, one oil plant or two coal plants). The laboratory stays a fast route: it costs 12,000 and runs on early goods. The Hospital (50,000) comes about three weeks of game days after the first laboratory; the radioactive tide cannot start before cycle 15.

### Menu order

Left to right is the unlock order (`tools/validate_tool_order.mjs`, a validate_all check; `tools/tool_groups.json` `$comment`):

- inside a Deep Frontier group every tool, vanilla and other-mod claims included, follows science ascending; on a tie a tool whose products another consumes comes first, then the smaller footprint, then the lower one;
- a sub-group sits among its parent's buttons by its earliest unlock, at a place with the fewest science inversions against the vanilla and other-mod buttons, which keep their own order; Deep Frontier tools in native groups follow the same rule;
- declared related children (`tool_groups.json` `related`; player feedback 2026-11-02) stand next to each other, left to right in the declared order: Redic.NewStyles' Tubeway Stop (the visible tubeway station) then ▸Tubeways in Paths; Explosives Factory, ▸Dynamite, Tunnel in Landscaping. A declared upgrade (`upgrades`) is the same rule for the pair base, upgrade: the Reactor Charging Bay right after the vanilla Charging Station (user, 2026-11-02). The Deep Frontier children of these clusters are left out of the two rules above; every other child keeps them and takes its fewest-inversion place among the places that do not split a cluster (the Masonry and concrete group therefore moved from between Dynamite and the Tunnel to just before the Explosives Factory, one inversion either way).

The structure and quarrying generators rank their tools by science (`structural_building_content.mjs`, `create_construction_material_content.mjs`); the other generators author the order. The Radioactive Waste Vault moved from Storage to **Radioactive waste** (Recovery Pump, Outfall, Export, Vault); the Reactor Charging Bay, moved to Nuclear fuel on 2026-11-01, is back in Science beside the Charging Station as a declared upgrade. No group was added. The external mods' science is in `tool_groups.json` `externalMods`, checked against the installed loose blueprints by `validate_tool_groups.mjs` (Flywheels read with UnityPy). The power shafts sort at 25, before the Lantern that Power Lines moves into Power at 29.

| Group | Left to right (science; ▸ sub-group, vanilla or other mod in italics) |
|---|---|
| Metal | *Scavenger Flag 0, Metalsmith 150, Smelter 300*, ▸Quarries and cement 300, ▸Deep mining 1,000, *Efficient Mine 4,000*, ▸Heavy industry 9,000, ▸Rocketry 75,000, ▸Nuclear fuel 300,000 |
| Quarries and cement | Sandstone Pit 300, Limestone Pit 300, Stone Crusher 600, Cement Kiln 600, Concrete Mixer 1,000, Sandstone Quarry 9,000, Limestone Quarry 9,000 |
| Deep mining | Deep Drill 1,000, Deep Ore Processor 1,200, Deep Mine 15,000 |
| Heavy industry | Chemical Works 9,000, Steel Mill 10,000, Precision Machine Works 12,000, Electrolysis Plant 30,000, Cryogenic Liquefaction Plant 40,000 |
| Rocketry | Mission Control 75,000, Rocket Assembly Hangar 125,000, Launch Pad 200,000 |
| Nuclear fuel | Uranium Processing Plant 300,000, Radioactive Waste Refinery 600,000 |
| Food | *Gatherer Flag 0*, Fisher Flag 0, *Farmhouse 0, Fermenter 0, Oil Press 120, Hydroponic Garden 200, Food Factory 300*, Fertilizer Works 350, *Coffee Brewery 500*, Fish Hatchery 600, Greenhouse 600, Fishery Works 900, Food Packaging Works 1,400 |
| Science | *Inventor 0, Numbercruncher 1,500, Bot Part Factory 500, Bot Assembler 750, Charging Station 200*, Reactor Charging Bay 300,000 (upgrade of the Charging Station; 400,000 until 2026-11-03), *Control Tower 1,000, Grease Factory 2,000*, Technical School 2,200, Materials Laboratory 12,000, Archive Excavation 25,000 |
| Storage | *Small and Large Industrial Pile 0, Pile Module 650, Grand Underground Pile 3,500, Small and Medium Warehouse 0, Large Warehouse 250*, Modular Warehouse 400, Warehouse Module 450, *Storage Module 750, Grand Warehouse 2,500, Small Tank 0, Medium Tank 120, Large Tank 600, Tank Module 1,050, Grand Tank 3,000*, Cryogenic Tank Farm 40,000 |
| Water | *Deep Water Pump 0, Deep Badwater Pump 250, Discharge 250*, Water Treatment Plant 1,800, *Deep Mechanical Pump 2,000, Compact Mechanical Pump 4,000, Centrifuge 600, Badwater Pressurizer 4,000, Aquifer Drill 400*, ▸Radioactive waste 50,000, Deep Well 75,000 |
| Radioactive waste | Radioactive Water Recovery Pump 50,000, Radioactive Water Outfall 50,000, Radioactive Waste Export 300,000, Radioactive Waste Vault 300,000 |
| Wellbeing | *Campfire … Detailer 1,000* (vanilla order), ▸Civic services 1,000, *Motivatorium 1,200, Mud Bath 1,800*, Smog Scrubber 2,500, Town Plaza 12,000, Observation Deck 27,500 |
| Civic services | Public Health Lab 1,000, Restaurant 1,000, Grocery Store 3,000, Bathhouse 15,000, Hospital 50,000 |
| Power | ▸Water power 0, *Large Power Wheel 0*, ▸Power shafts 0, ▸Engines and power plants 160, ▸Flywheels 300, *Gravity Battery 400* |
| Water power | *Compact Water Wheel 0, Large Water Wheel 200*, Reinforced Hydro Turbine 20,000 |
| Power shafts | *Power Shaft 0, Vertical Power Shaft 40, Impermeable Power Shaft 300, Clutch 400* |
| Engines and power plants | *Geothermal Engine 160, Solar Panel 250, Steam Engine 400, Steam Plant 400*, Coal Power Plant 10,000, Oil Power Plant 35,000, Nuclear Reactor 1,000,000 |
| Flywheels | *Small 300, Small Horizontal Framed 800, Small Vertical Framed 800, Medium 1,000, Medium Horizontal and Vertical Framed 2,500, Large 5,000, Large Horizontal and Vertical Framed 10,000* (display names) |
| Paths | *Path 0, Stairs 70*, ▸Platforms 100, ▸Suspension bridges 150, *Spiral Stairs 350, Tubeway Stop 700 (Redic.NewStyles)*, ▸Tubeways 500 (related), *Gate 200, Airlock 300*, ▸Overhangs 350, ▸Concrete side platforms 4,500, ▸Concrete platforms 5,000, ▸Teleporters 5,000, ▸Steel structures 11,250 |
| Platforms, Suspension bridges, Overhangs, Tubeways, Teleporters | vanilla or mod order, already ascending |
| Concrete side platforms | 3x3 4,500, 4x4 8,000, 5x5 12,500 |
| Steel structures | Steel Column (1 high) 11,250, (2 high) 12,500, Steel Deck 3x3 13,500, Steel Deck 3x3 on Legs (1-4 high) 13,500, Steel Column (3 high) 13,750, (4 high) 15,000, Steel Truss Bridge 8x1 16,000, Steel Column (5 high) 16,250, (6 high) 17,500, Steel Truss Bridge 10x1 20,000, 12x1 24,000, Steel Cantilever 10x1 25,000, 12x1 30,000, Steel Truss Bridge 15x1 30,000, Steel Cantilever 15x1 37,500, Steel Deck 5x5 37,500, Steel Deck 5x5 on Legs (1-4 high) 37,500 |
| Concrete platforms | Reinforced Overhang 8x1 5,000, Concrete Platform 3x3 (1 high) 5,000, (2 high) 5,500, (3 high) 6,000, 4x4 (1-3 high) 8,500-9,500, 5x5 (1-3 high) 13,000-14,000 |
| Landscaping | *Dam 0, Levee 120*, ▸Floodgates 150, *Fill Valve 300, Throttling Valve 500, Impermeable Floor 200, Irrigation Barrier 400*, ▸Masonry and concrete 600, *Explosives Factory 400*, ▸Dynamite 600 (related), *Tunnel 2,000, Dirt Excavator 2,000, Terrain Block 2,000* |
| Masonry and concrete | Brick Block 600, Sandstone Masonry Block 900, Concrete Levee Block 1,200, Concrete Overflow Dam 1,500, Reinforced Dam Block 2,200 |

### Checks

- `tools/validate_tool_order.mjs` fails on a group out of science order (with the tie rule), a sub-group or Deep Frontier tool away from its fewest-inversion place, or two children sharing an order value. It fails on the data before this change (177 errors) and passes after it.
- `tools/audit_progression.mjs` adds the stage checks: the reactor unlocks above every other player building (`reactor-not-last`); each Deep Frontier power plant out-produces every generator unlocked at or before it (`power-plant-order`); each progression ladder's step is available no earlier than the step it consumes (`ladder-order`). The unlock-order check (a building before its construction goods or every recipe's inputs) is unchanged and passes: no building broke it before the curve, and the steel structures and the laboratory's cost were kept clear of it.

### Proposals

| Building | First pass | Proposal | Status | Reason |
|---|---:|---|---|---|
| Radioactive Water Recovery Pump, Outfall | 300,000 | 50,000 (with the Hospital; T4 cost) | approved and made | Radioactive tides can start at cycle 15, long before the nuclear stage; these two clean tide water and need nothing nuclear. |
| Rocket missions (payout) | 100,000 and 250,000 | 250,000 and 500,000 | approved and made | The launch unlocks (Mission Control, Hangar, Launch Pad) cost 400,000; the payouts cover them again, as the 2026-10-29 curve intended. |
| Grocery Store | 15,000 | 3,000 (T2 cost) | approved and made | It sells Canned Fish (1,400) and vanilla staples; nothing in it needs the transition stage. |
| Concrete platforms and side platforms | 11,250-35,000 | 500 × k again (4,500-14,000), T3 cost | approved and made (with the Reinforced Overhang 8x1, 5,000) | Construction pieces made of early goods. |
| Water Treatment Plant | 1,800 | keep | | Its Reactor Coolant recipe needs Cryocoolant (9,000), a later extra recipe (audit warning); Pure Water runs at its unlock. |
| Public Health Lab 1,000 / Hospital 50,000 | | keep | | The Hospital is a frontier building; Medicine comes first by design. |
| Mission Control 75,000 / Rocket Assembly Hangar 125,000 | | keep | | Mission Control comes first in the story (chapter 6 asks for it). |

## Modular Warehouse (updated 2026-11-07)

User request: early-game storage with five independently selected goods, no power, one entrance, and attachable/stackable capacity modules. All five selections belong to the core. Runtime verification is recorded in `tools/STATUS.md`.

| | Modular Warehouse (core) | Warehouse Module |
|---|---|---|
| Menu, science (stage) | Storage, after the Large Warehouse; 400 (early, T1) | right of the core; 450 (T1) |
| Size | 3x3, 2 high, door in front | 3x3, 1 high, no door |
| Storage | 600 shared across 5 slots | +600 shared across the same 5 slots when attached |
| Cost | 100 Plank, 60 Log, 15 Gear | 80 Plank, 60 Log, 5 Gear |
| Power, workers | none | none |

- **Attachment:** a finished module joins a finished core when it touches it, or an attached module, face to face (side by side on one layer, or stacked on its top); diagonal contact does not count. A module touching two networks joins the nearer core. The core holds the network's only inventory, so haulers, laborers, belts and needs use one storage point.
- **Slots:** all five are available without modules; capacity (600 + 600 per module) is shared equally, starting at 120 per slot. Each slot selects one distinct good and has the native Accept / Obtain / Supply / Empty controls. The goods button opens the existing native floating stockpile picker through `OverlayGoodSelectionController`, outside the entity panel. The game owns the picker controls, layout, updates, input, positioning and dismissal. A UI-only native Stockpile/SingleGoodAllower data adapter represents the selected slot; it never registers another world inventory or hauling destination.
- **Capacity basis:** the vanilla Large Warehouse holds 1,200 in 3x3x2 at 250 science (67 per cell, 60 Log + 80 Plank). A module holds 600 in 3x3x1 (67 per cell; `validate_modular_warehouse.mjs` fails a denser module). A core with four modules stores 3,000 (5 x 600); with nine, 5 x 1,200.
- **Costs:** the late-game size rule (both are integrated studies, tier T1) gives a 3x3 early building only 15-20 Plank, 10 Log and 5 Gear, far below the vanilla warehouses. `lategameGates` adds the rest so each costs about what the vanilla warehouses cost for its capacity, times the T1 cost factor 2 (60 Log + 80 Plank per 1,200 at vanilla rates): core +50 Log, +80 Plank, +10 Gear; module +50 Log, +65 Plank. The material rule still composes the rule part from the models (timber, iron straps priced as Gear; no brick or concrete, which do not exist at 400 science).
- **Removing a module** lowers capacity while preserving all five selections. Stock above the new shares becomes native unwanted stock and is carried to other storage. Goods never sit in a module. Deleting the core recovers its goods natively.

## Tools

| Tool | Purpose |
|---|---|
| `node tools/lategame_costs.mjs [--check\|--write]` | Prints the late-game cost rule for each integrated building. `--write` rewrites the catalog rows the rule owns; `--check` fails when a row differs from the rule. |
| `python tools/asset-pipeline/measure_building_materials.py [dataRoot]` | Measures each building's visible material mix from its exported model into `tools/building_material_mix.json` (see Material cost rule). |
| `node tools/material_costs.mjs --write\|--check [dataRoot]` | Records (or checks) the value table and producer graph of the generated data that the material cost rule uses, in `tools/material_cost_context.json`. |
| `node tools/audit_progression.mjs [dataRoot]` | Static progression audit of the generated data (vanilla Iron Teeth plus Deep Frontier). Writes `outputs/progression-audit.json` and exits 1 on any failure. |
| `node tools/validate_tool_order.mjs [dataRoot] [--print]` | Toolbar order: left to right is the unlock order (see Science curve and menu order). `--print` lists every checked group left to right. |
| `node tools/audit_item_uses.mjs` | Existing check that every new good has enough downstream uses. It does not check whether a good can be produced. It counts recipes appended to vanilla buildings, bot assembly and bot maintenance (see Second uses). |
| `node tools/validate_bot_upkeep.mjs [dataRoot]` | Static check of bot maintenance and the Reactor bot recipe (catalog, runtime records, generated data, automation declarations). |
| `node tools/validate_deadlocks.mjs [dataRoot] [--print]` | Deadlock audit beyond recipes and costs (`docs/deadlock-audit.md`): workplace upkeep, goods-consuming buildings, specialist training and food services gate each building; every good the economy uses must stay renewable without finite map stock, every required discipline teachable without itself, every Deep Frontier building able to run at its unlock, every building rebuildable without itself, and each finite map good reachable through a renewable producer; undeletable hazardous stock (radioactive waste, radioactive water, contaminated water) has a consumer from its first unit (contaminated water from the Hospital's unlock, the stage set ahead of radioactive tides), and Reactor Bots can charge from the first one. |

### Reachability model (`audit_progression.mjs`)

- **Primary goods.** A vanilla good that no vanilla recipe produces is primary (gathered, grown, pumped or scavenged). Primary goods are available at science 0.
- **Map-sourced goods.** `MAP_SOURCES` lists goods that a workplace gathers without a recipe:
  - ScrapMetal: Scavenger Flag.
  - DeepOre: Deep Drill, boring the Deep Ore Sources of its district (finite, with a slow recharge once empty). Its recipe (3 Water -> 1 Deep Ore) is not a valuation route: Deep Ore stays a gathered good at `primaryGood` until the Deep Mine's route is cheaper.
  - Sandstone and Limestone: the pits.
  - FreshFish: the Fisher Flag (shore fishing; until 2026-11-02 a mode of the Gatherer Flag).
  - ContaminatedWater: not gathered. Stored Water converts at runtime when irradiated (see [radiation.md](radiation.md)). The Radioactive Waste Refinery is the earliest source, because radiation first exists once it makes RadioactiveSludge.
- **Buildings.** A building can be built at max(its science, the availability of every construction good).
- **Recipes.** A recipe's products become available at max(its building, its ingredients, its fuel). The cheapest route wins.
- **Reported values.** For each building and good the audit reports:
  - the **gate**: the largest single unlock on that route;
  - the **cumulative** science: the sum of the distinct unlocks on that route.
- **Failures:**
  - a construction good or active recipe input that can never be produced;
  - two player tools on the same `ToolGroupId#ToolOrder`;
  - a late-game blueprint whose cost differs from the rule;
  - a late-game building whose science falls outside its tier's band;
  - a player building at or above the Nuclear Reactor's science, a Deep Frontier power plant that does not out-produce every generator unlocked at or before it, or a progression-ladder step available before the step it consumes (2026-11-01);
  - a building that unlocks before one of its construction goods, or before any of its recipes can run;
  - a bootstrap cycle: a construction good that cannot be produced without the building itself, or only by buildings unlocked after it;
  - a cost that breaks the material cost rule, a stale mix or context record, or a family the rule could not price ("concrete shown before Concrete exists");
  - two recipes of one building with the same `DisplayLocKey`: the native recipe dropdown finds the chosen recipe by it (`SingleOrDefault`) and would throw.
- **Vanilla patches.** A recipe appended to a vanilla template by a same-path patch (the Bot Assembler's IndustrialBot) is active. Its inputs must be producible; inputs that unlock after the vanilla building are warnings.
- **Warnings:**
  - recipes that no building selects;
  - consumers that need more than ten copies of the best generator unlocked by then.
  - an extra recipe whose inputs only become available above its building's science (the building fails if no recipe can run).
- **Out of scope:** production rates, workforce, actual power supply, map placement and runtime behaviour.

## Late-game construction cost rule

Applies to every building in `tools/lategame_batches.json` `integrated`. All 20 were re-authored from 3×3 prototypes into full-size studies. Data lives in `tools/building_construction_costs.json` (`lategameRule`, `lategameTier`, `lategameGates`). Size comes from the registration the blueprint is generated from, `outputs/lategame-studies/<Id>-registration.json`:

- `groundCells` = occupied cells on layer 0, i.e. the foundation slab.
- `builtCells` = every occupied cell, i.e. the built mass. Empty air above low wings does not count.
- **Foundation:** Concrete = groundCells × tier.concretePerGroundCell.
- **Superstructure:** each good = builtCells / 100 × tier.per100BuiltCells[good].
- **Rounding:** every amount rounds to the nearest multiple of 5, with a minimum of 5.
- **Tier:** fixed by the science unlock. The bands follow the implementation-plan stages.
- **Gates:** `lategameGates` adds explicit goods that prove the previous stage. The gates are DeepMine's 20 DeepAlloy, which keeps the permanent mine behind the finite drill phase; the Greenhouse's 30 Fertilizer (bed soil from the Fertilizer Works; 30 Compost until the 2026-10-30 bricks pass); and the Nuclear Reactor's 20 EnrichedFuel (first core load) and 10 RecoveredMinerals (waste refining must work before the reactor). See Second uses.

| Tier | Science | Stage | Concrete / ground cell | Per 100 built cells |
|---|---|---|---:|---|
| T1 | ≤ 600 | Productive settlement | 0 (pre-concrete) | 30 Plank, 12 Gear, 6 Metal Block |
| T2 | ≤ 3,000 | Industrial city | 0.75 | 25 Plank, 10 Gear, 8 Metal Block |
| T3 | ≤ 20,000 (8,000 until 2026-11-01) | Wonder transition | 1 | 20 Plank, 12 Gear, 12 Metal Block, 5 Treated Plank |
| T4 | ≤ 75,000 (30,000 until 2026-11-01) | Frontier | 1.5 | 15 Metal Block, 8 Gear, 8 Treated Plank, 3 Deep Alloy |
| T5 | above | Launch program and reactor | 3 | 10 High-grade Steel, 8 Alloy, 2 Machine Core, 8 Metal Block |

Each tier uses goods the chain can already make at that stage. T4 uses the frontier's own refined metal, DeepAlloy, which also gives DeepAlloy real construction uses. T5 uses the premium metals. The nuclear reactor is the largest building at 2,543 built cells and 261 ground cells, so it comes out at 1,500 units. That is 2.4 times the next building, which makes it the endgame showpiece through size alone, with no special multiplier.

| Building | Tier | Built / ground cells | Previous (prototype) | Rule |
|---|---|---:|---|---|
| FertilizerWorks | T1 | 350 / 46 | 40 Plank, 20 Gear, 15 MB | 105 Plank, 40 Gear, 20 MB |
| Greenhouse | T1 | 154 / 42 | 40 Plank, 20 Gear, 15 MB | 45 Plank, 20 Gear, 10 MB, 30 Fertilizer (gate; Compost until 2026-10-30) |
| PublicHealthLab | T2 | 318 / 56 | 40/20/15, 50 Concrete | 80 Plank, 30 Gear, 25 MB, 40 Concrete |
| FoodPackagingWorks | T2 | 306 / 55 | 40/20/15, 40 Concrete | 75 Plank, 30 Gear, 25 MB, 40 Concrete |
| WaterTreatmentPlant | T2 | 454 / 113 | 40/20/15, 80 Concrete | 115 Plank, 45 Gear, 35 MB, 85 Concrete |
| TechnicalSchool | T2 | 288 / 51 | 40/20/15, 80 Concrete | 70 Plank, 30 Gear, 25 MB, 40 Concrete |
| DeepDrill* | T2 | 591 / 79 | 40 Log, 30 Plank, 20 Gear, 10 MB, 40 Concrete | 150 Plank, 60 Gear, 45 MB, 60 Concrete |
| DeepProcessor* | T2 | 770 / 86 | 50 Plank, 20 Gear, 15 MB, 60 Concrete | 195 Plank, 75 Gear, 60 MB, 65 Concrete |
| ChemicalWorks | T3 | 416 / 77 | 40/20/15, 120 Concrete | 85 Plank, 50 Gear, 50 MB, 20 TP, 75 Concrete |
| PrecisionMachineWorks | T3 | 302 / 67 | 40/20/15, 100 Concrete | 60 Plank, 35 Gear, 35 MB, 15 TP, 65 Concrete |
| DeepMine* | T3 | 695 / 79 | 200 Log, 120 Plank, 80 Gear, 60 MB, 20 DeepAlloy, 100 Concrete | 140 Plank, 85 Gear, 85 MB, 35 TP, 80 Concrete, 20 DeepAlloy |
| UraniumProcessingPlant | T5 | 646 / 117 | 40/20/15, 160 Concrete | 65 HGS, 50 Alloy, 15 MC, 50 MB, 350 Concrete |
| RadioactiveWasteVault* | T5 | 494 / 68 | 80 Concrete, 30 TP, 50 MB | 50 HGS, 40 Alloy, 10 MC, 40 MB, 205 Concrete |
| ElectrolysisPlant | T4 | 559 / 96 | 40/20/15, 160 Concrete | 85 MB, 45 Gear, 45 TP, 15 DeepAlloy, 145 Concrete |
| CryogenicLiquefactionPlant | T4 | 533 / 84 | 40/20/15, 200 Concrete | 80 MB, 45 Gear, 45 TP, 15 DeepAlloy, 125 Concrete |
| RadioactiveWasteRefinery | T5 | 604 / 101 | 40/20/15, 200 Concrete | 60 HGS, 50 Alloy, 10 MC, 50 MB, 305 Concrete |
| MissionControl | T4 | 618 / 108 | 40/20/15, 120 Concrete | 95 MB, 50 Gear, 50 TP, 20 DeepAlloy, 160 Concrete |
| RocketAssemblyHangar | T5 | 1,033 / 113 | 100 HGS, 80 Alloy, 30 MC, 60 MB, 320 Concrete | 105 HGS, 85 Alloy, 20 MC, 85 MB, 340 Concrete |
| LaunchPad | T5 | 709 / 136 | 100 HGS, 80 Alloy, 30 MC, 60 MB, 480 Concrete | 70 HGS, 55 Alloy, 15 MC, 55 MB, 410 Concrete |
| NuclearReactor | T5 | 2,543 / 261 | 80 Alloy, 80 HGS, 20 MC, 20 TP, 300 Concrete | 255 HGS, 205 Alloy, 50 MC, 205 MB, 785 Concrete, 20 EnrichedFuel and 10 RecoveredMinerals (gates) |

\* These four take their cost from `lategameCost()` directly (`makeVault` and `create_vertical_slice_content.mjs`) instead of from catalog rows.

A registration changes whenever its art is re-registered. Rerun `node tools/lategame_costs.mjs --write` after any registration update. The audit fails while catalog or blueprint costs are stale.

Full-size buildings outside the late-game batch keep their bespoke authored costs: Restaurant, Fishery, Hatchery, Grocery, Hospital, Materials Laboratory, the concrete chain, structures and the hydro turbine.

Since 2026-10-30 the rule rows (and the authored costs) are only the basis: the material cost rule below recomposes them from what each model shows. The table above gives the size rule's earlier output, not current costs.

## Material cost rule (2026-10-30)

User request: "each building's construction materials must match what the building is visibly made of: its walls, frames and especially its roofs." Concrete is required only where the model shows concrete; plank and timber buildings cost wood, steel-plate and metal-sheet buildings cost metal goods. Later: "keep in mind the supply chain progression path" and "we don't want to require concrete on a building required to make concrete the first time around."

Every Deep Frontier building with a construction cost passes through it, except the structural modules of `tools/structural_content.json`, which are named for and priced in their material. Rule data: `tools/building_construction_costs.json` `materialRule`; code: `tools/material_costs.mjs` (`materialCost`), applied by `lategameCost(id, science)` after the size rule and before the gates, and by `buildingCost(id, cost, science)` after `scaledCost` for authored costs.

- **Measure.** `python tools/asset-pipeline/measure_building_materials.py [dataRoot]` decodes each building's exported finished model (official Timbermesh schema) and writes `tools/building_material_mix.json`: model path, sha256, triangle area per material and per family. Families come from `materialRule.materials`. Details.IronTeeth is split by atlas region: its strap strip is metal, crates and planks are wood, cloth is unpriced. Each stone tile takes the stone whose reference tile is nearest in chromaticity; all grey masonry reads as limestone. Orange plaster (Plaster_Orange.IronTeeth) is brick since the 2026-10-30 bricks pass. Glass, lamps, water, cloth, embers, instruments and rubber are unpriced. Nested native props are game models and are not measured.
- **Basis.** The building's cost before this rule: the late-game rule rows without gates, or its authored cost times its tier costFactor. Gear and MachineCore (machinery) keep their amounts. Gates are added afterwards, unchanged.
- **Value.** Each material good has an embodied value: recipe effort along the cheapest route, where a primary or map-gathered good counts 1, a liquid 0, each recipe hour 1, fuel its value / CyclesFuelLasts, and a recipe's effort is shared by its product units. The user chose raw effort, so concrete-heavy buildings need large counts. `value.scope` is `buildingWorld`: a good is valued only by the routes of the building's own world (without it, at or below its science). For a building unlocked before the quarries, Limestone comes from the pits (1.0), not the quarries (0.42). Example values at 1,000 science (bricks pass): Plank 2.25, Log 1, MetalBlock 4.2, Gear 5.25, Concrete 1.60, Brick 1.33, Dirt 0.50, TreatedPlank 6.25. At the reactor: Concrete 1.14, Brick 1.11, DeepAlloy 8.0, HighGradeSteel 11.8, Alloy 16.6, MachineCore 56.6.
- **Composition.** The material value is shared over wood, metal, concrete, brick, sandstone and limestone by the measured area. A family under 5% is folded into the others. Inside a family the goods are the tier's `familyGoods` (unit ratios; since 2026-10-31 the stage table of [Progression sets](#progression-sets-2026-10-31); since 2026-11-03 a building in `familyGoodsOverrides` takes the named earlier stage's goods for that family) that the settlement can make without this building. Each amount rounds up to a multiple of 5, so the value never falls.
- **Stone.** Masonry is priced as Sandstone or Limestone. Raw stone on the buildings that produce it (the pits and the quarries) is the deposit they work and stays unpriced (`depositFamilies`).
- **No good, no family.** A family with no producible good at the building's stage fails the audit. For concrete the failure reads "concrete shown before Concrete exists": the art must change. Fertilizer Works, Greenhouse, Fish Hatchery, Stone Crusher, Cement Kiln, Concrete Mixer and both pits show none after the roof pass.
- **Context.** `node tools/material_costs.mjs --write|--check [dataRoot]` records the value table and producer graph of the generated data in `tools/material_cost_context.json`. After a recipe or science change: measure (if models changed), `--write`, `node tools/lategame_costs.mjs --write`, regenerate.
- **Checks** (`audit_progression.mjs`): the mix records match the generated models (sha256); the context matches the generated data; every in-scope building has a mix; each cost's material goods are exactly the rule's; each family's value share equals the measured share within the rounding; plus the bootstrap check below.
- **Bootstrap.** Every good of a building's cost must be producible by the settlement without that building, from buildings unlocked at or below its science whose own costs are producible the same way (`bootstrap-cycle`). No cycle exists in the generated data; planting Concrete in the Concrete Mixer's cost trips it. The first concrete chain (pits, crusher, kiln, mixer) stays concrete-free, and the crusher and kiln stay brick-free (each shows 1% brick, folded).
- **Stone budget.** The built-in maps hold 1,800 of each stone in pit range before the quarries. Since the bricks pass the buildings up to the quarries need 1,343 Limestone and 1,535 Sandstone (`prepare_deep_frontier_map.py builtin`; 1,393 and 1,275 after the roof pass). With `global` value scope they would need 2,060 Limestone.

Totals over the 48 buildings when the rule landed: Concrete 28,815 -> 92,170 (1,925 -> 2,915 up to 4,000 science), Plank 7,370 -> 3,605, TreatedPlank 2,300 -> 3,235, MetalBlock 10,675 -> 7,525, HighGradeSteel 4,855 -> 2,495, Alloy 3,755 -> 1,865, Limestone 0 -> 300, Log 80 -> 185. The table's Now column is the generated cost after the bricks pass (brick family, kiln at 600); see [Bricks and retired goods](#bricks-and-retired-goods-2026-10-30-bricks-pass) for that change.

| Building | Science | Wood / metal / concrete / brick (/ stone) % | Before (2026-10-30, be385c5) | Now |
|---|---:|---|---|---|
| LimestonePit | 300 | 69/24/0/0/s6 | 40 Log 20 Plank | 25 Plank 15 Log 10 MetalBlock |
| SandstonePit | 300 | 79/15/0/0/s6 | 40 Log 20 Plank | 30 Plank 15 Log 5 MetalBlock |
| FertilizerWorks | 350 | 56/41/0/3 | 205 Plank 80 Gear 40 MetalBlock | 135 Plank 70 Log 65 MetalBlock 80 Gear |
| FishHatchery | 600 | 82/16/0/2/s0 | 80 Plank 40 Gear 30 MetalBlock | 95 Plank 50 Log 15 MetalBlock 40 Gear |
| Greenhouse | 600 | 10/88/0/2 | 90 Plank 35 Gear 20 MetalBlock 30 Compost | 15 Plank 10 Log 65 MetalBlock 35 Gear 30 Fertilizer |
| StoneCrusher | 600 | 54/31/0/1/s15 | 60 Plank 30 Gear 20 MetalBlock | 45 Plank 25 Log 20 MetalBlock 35 Limestone 30 Gear |
| CementKiln | 600 | 42/27/0/1/s31 | 120 Plank 60 Gear 45 MetalBlock | 50 Plank 25 Log 20 MetalBlock 95 Limestone 40 Gear |
| FisheryWorks | 900 | 78/16/2/3/s0 | 120 Plank 60 Gear 45 MetalBlock | 170 Plank 20 MetalBlock 60 Gear |
| ConcreteMixer | 1000 | 43/31/0/17/s10 | 120 Plank 60 Gear 45 MetalBlock | 90 Plank 35 MetalBlock 60 Brick 45 Limestone 60 Gear |
| DeepDrill | 1000 | 17/35/36/12 | 445 Plank 175 Gear 140 MetalBlock 180 Concrete | 145 Plank 160 MetalBlock 420 Concrete 175 Brick 175 Gear |
| PublicHealthLab | 1000 | 38/4/54/5 | 225 Plank 90 Gear 70 MetalBlock 110 Concrete | 180 Plank 360 Concrete 90 Gear |
| Restaurant | 1000 | 78/9/9/3/s0 | 120 Plank 60 Gear 45 MetalBlock 180 Concrete | 275 Plank 20 MetalBlock 50 Concrete 60 Gear |
| DeepProcessor | 1200 | 2/62/25/10 | 550 Plank 220 Gear 175 MetalBlock 165 Concrete | 340 MetalBlock 360 Concrete 180 Brick 220 Gear |
| FoodPackagingWorks | 1400 | 14/34/40/12 | 230 Plank 90 Gear 75 MetalBlock 120 Concrete | 65 Plank 85 MetalBlock 260 Concrete 95 Brick 90 Gear |
| WaterTreatmentPlant | 1800 | 19/29/45/7 | 340 Plank 135 Gear 110 MetalBlock 255 Concrete | 140 Plank 115 MetalBlock 465 Concrete 90 Brick 135 Gear |
| TechnicalSchool | 2200 | 26/8/48/18 | 210 Plank 85 Gear 70 MetalBlock 105 Concrete | 110 Plank 20 MetalBlock 285 Concrete 130 Brick 85 Gear |
| SmogScrubber | 2500 | 1/67/31/1 | 40 Plank 15 Gear 15 MetalBlock 20 Concrete | 35 MetalBlock 40 Concrete 15 Gear |
| ChemicalWorks | 4000 | 1/69/30/0 | 335 Plank 200 Gear 200 MetalBlock 85 TreatedPlank 310 Concrete | 410 MetalBlock 670 Concrete 200 Gear |
| LimestoneQuarry | 4000 | 47/13/0/10/s29 | 480 Plank 320 Gear 240 MetalBlock 240 Concrete | 425 Plank 110 TreatedPlank 110 MetalBlock 320 Brick 320 Gear |
| SandstoneQuarry | 4000 | 47/13/0/10/s29 | 480 Plank 320 Gear 240 MetalBlock 240 Concrete | 425 Plank 110 TreatedPlank 110 MetalBlock 270 Brick 320 Gear |
| CoalPowerPlant | 4500 | 3/53/30/14 | 125 Plank 75 Gear 75 MetalBlock 30 TreatedPlank 100 Concrete | 120 MetalBlock 245 Concrete 120 Brick 75 Gear |
| SteelMill | 4500 | 0/63/36/0 | 425 Plank 255 Gear 255 MetalBlock 105 TreatedPlank 450 Concrete | 485 MetalBlock 1025 Concrete 255 Gear |
| PrecisionMachineWorks | 5000 | 31/23/42/5 | 240 Plank 145 Gear 145 MetalBlock 60 TreatedPlank 255 Concrete | 155 Plank 40 TreatedPlank 105 MetalBlock 705 Concrete 145 Gear |
| TownPlaza | 5000 | 4/54/33/8 | 55 Plank 35 Gear 35 MetalBlock 15 TreatedPlank 105 Concrete | 70 MetalBlock 150 Concrete 40 Brick 35 Gear |
| Bathhouse | 6000 | 15/13/68/4 | 170 Plank 100 Gear 100 MetalBlock 45 TreatedPlank 200 Concrete | 60 Plank 15 TreatedPlank 45 MetalBlock 820 Concrete 100 Gear |
| DeepMine | 6000 | 19/38/34/9 | 545 Plank 330 Gear 330 MetalBlock 135 TreatedPlank 270 Concrete 20 DeepAlloy | 195 Plank 50 TreatedPlank 340 MetalBlock 1130 Concrete 300 Brick 330 Gear 20 DeepAlloy |
| GroceryStore | 6000 | 75/17/8/1 | 320 Plank 160 Concrete 140 MetalBlock 80 Gear | 295 Plank 75 TreatedPlank 60 MetalBlock 110 Concrete 80 Gear |
| ReinforcedHydroTurbine | 8000 | 19/22/59/0 | 640 Concrete 400 MetalBlock 240 Gear 160 TreatedPlank | 170 Plank 45 TreatedPlank 185 MetalBlock 1765 Concrete 240 Gear |
| ArchiveExcavation | 9000 | 26/12/46/16 | 500 MetalBlock 265 Gear 265 TreatedPlank 100 DeepAlloy 755 Concrete | 225 TreatedPlank 115 MetalBlock 25 DeepAlloy 2215 Concrete 780 Brick 265 Gear |
| ObservationDeck | 9500 | 8/47/41/4 | 245 MetalBlock 130 Gear 130 TreatedPlank 50 DeepAlloy 160 Concrete | 35 TreatedPlank 210 MetalBlock 45 DeepAlloy 900 Concrete 130 Gear |
| ElectrolysisPlant | 10000 | 18/37/38/7 | 505 MetalBlock 270 Gear 270 TreatedPlank 100 DeepAlloy 865 Concrete | 160 TreatedPlank 355 MetalBlock 75 DeepAlloy 1885 Concrete 370 Brick 270 Gear |
| OilPowerPlant | 11000 | 0/62/37/0 | 185 MetalBlock 100 Gear 100 TreatedPlank 35 DeepAlloy 325 Concrete 4 MachineCore | 225 MetalBlock 45 DeepAlloy 680 Concrete 100 Gear 4 MachineCore |
| CryogenicLiquefactionPlant | 12000 | 0/56/43/0 | 480 MetalBlock 255 Gear 255 TreatedPlank 95 DeepAlloy 755 Concrete | 515 MetalBlock 105 DeepAlloy 2000 Concrete 255 Gear |
| CryogenicTankFarm | 12000 | 12/34/51/3 | 420 MetalBlock 225 Gear 225 TreatedPlank 85 DeepAlloy 990 Concrete | 100 TreatedPlank 300 MetalBlock 60 DeepAlloy 2320 Concrete 225 Gear |
| MaterialsLaboratory | 12000 | 50/18/30/1 | 480 Plank 240 Gear 360 MetalBlock 720 Concrete | 280 TreatedPlank 110 MetalBlock 25 DeepAlloy 915 Concrete 240 Gear |
| Hospital | 25000 | 67/10/12/11/s0 | 720 Plank 480 Concrete 360 MetalBlock 180 Gear 120 TreatedPlank | 475 TreatedPlank 80 MetalBlock 20 DeepAlloy 470 Concrete 450 Brick 180 Gear |
| DeepWell | 30000 | 3/70/24/4 | 205 MetalBlock 155 Gear 5 TreatedPlank 20 DeepAlloy 60 Concrete 60 HighGradeSteel 10 MachineCore | 215 MetalBlock 20 DeepAlloy 70 Concrete 155 Gear 60 HighGradeSteel 10 MachineCore |
| MissionControl | 30000 | 23/10/60/7 | 555 MetalBlock 295 Gear 295 TreatedPlank 110 DeepAlloy 970 Concrete | 230 TreatedPlank 115 MetalBlock 25 DeepAlloy 3245 Concrete 370 Brick 295 Gear |
| RocketAssemblyHangar | 50000 | 14/57/15/14 | 650 HighGradeSteel 520 Alloy 130 MachineCore 520 MetalBlock 1680 Concrete | 470 TreatedPlank 410 HighGradeSteel 330 Alloy 330 MetalBlock 2670 Concrete 2525 Brick 130 MachineCore |
| LaunchPad | 80000 | 8/37/54/1 | 565 HighGradeSteel 455 Alloy 115 MachineCore 455 MetalBlock 3265 Concrete | 265 TreatedPlank 260 HighGradeSteel 210 Alloy 210 MetalBlock 9525 Concrete 115 MachineCore |
| RadioactiveSludgeOutfall | 200000 | 14/15/70/1 | 25 HighGradeSteel 20 Alloy 5 MachineCore 20 MetalBlock 240 Concrete | 25 TreatedPlank 10 HighGradeSteel 5 Alloy 5 MetalBlock 615 Concrete 5 MachineCore |
| RadioactiveSludgeRecoveryPump | 200000 | 36/36/26/2 | 25 HighGradeSteel 20 Alloy 5 MachineCore 20 MetalBlock 170 Concrete | 55 TreatedPlank 15 HighGradeSteel 10 Alloy 10 MetalBlock 215 Concrete 5 MachineCore |
| RadioactiveWasteExport | 200000 | 2/29/67/2 | 60 HighGradeSteel 50 Alloy 10 MachineCore 50 MetalBlock 720 Concrete | 30 HighGradeSteel 25 Alloy 25 MetalBlock 1585 Concrete 10 MachineCore |
| RadioactiveWasteVault | 200000 | 7/15/78/0 | 320 HighGradeSteel 255 Alloy 65 MachineCore 255 MetalBlock 910 Concrete | 120 TreatedPlank 55 HighGradeSteel 45 Alloy 45 MetalBlock 6945 Concrete 65 MachineCore |
| UraniumProcessingPlant | 200000 | 1/44/50/6 | 515 HighGradeSteel 410 Alloy 105 MachineCore 410 MetalBlock 2810 Concrete | 280 HighGradeSteel 225 Alloy 225 MetalBlock 7870 Concrete 920 Brick 105 MachineCore |
| ReactorChargingBay | 250000 | 1/80/16/2 | 15 HighGradeSteel 10 Alloy 5 MachineCore 10 MetalBlock 145 Concrete 2 ReinforcedBotFrame 2 ReactorPowerCell | 20 HighGradeSteel 15 Alloy 15 MetalBlock 85 Concrete 5 MachineCore 2 ReinforcedBotFrame 2 ReactorPowerCell |
| RadioactiveWasteRefinery | 500000 | 0/35/54/11 | 485 HighGradeSteel 385 Alloy 95 MachineCore 385 MetalBlock 2425 Concrete | 205 HighGradeSteel 165 Alloy 165 MetalBlock 7910 Concrete 1565 Brick 95 MachineCore |
| NuclearReactor | 1000000 | 1/40/59/0 | 2135 HighGradeSteel 1630 Alloy 405 MachineCore 1630 MetalBlock 6265 Concrete 20 EnrichedFuel | 1025 HighGradeSteel 740 Alloy 740 MetalBlock 34190 Concrete 405 MachineCore 20 EnrichedFuel |

## Bricks and retired goods (2026-10-30, bricks pass)

User decisions on the approved bricks proposal: one new good, Brick, on existing buildings, and seven low-value goods removed ("for every item we add, lets remove low value items from the game. We have a lot of sprawl").

### The bricks chain

| Step | Building (science) | Recipe |
|---|---|---|
| Grind brick earth | Stone Crusher (600) | 3 Sandstone -> 8 Dirt, 1 h (`BrickEarth`; vanilla `Recipe.Dirt` is the excavator's; 6 until the quarries' brick plinths, see the stone budget) |
| Fire bricks | Cement Kiln (900 -> **600**) | 4 Dirt + 1 Water -> 4 Brick, 2 h, 1 Log per cycle (`FireBricks`, "Fire bricks") |
| Fire cement | Cement Kiln | 3 Limestone + 1 **Dirt** -> 2 Cement, 2 h, 1 Log (was 1 Aggregate) |
| Mix concrete | Concrete Mixer (1,000) | 3 **Sandstone** + 2 Cement + 4 Water -> 8 Concrete, 2 h (was 3 Aggregate + 1 Cement + 2 Water -> 4, 1 h: same ratios and throughput) |

- **Order:** wood, scrap metal (vanilla), bricks (600), concrete (1,000), steel and alloys (4,500+). Brick and Cement are available at 600 science (cumulative 2,200); Concrete stays at 1,000, its cumulative science falls from 3,500 to 3,200. High-grade steel's cumulative science falls from 10,200 to 9,900.
- **Dirt** is vanilla Dirt (Pileable, vanilla industrial piles). The crusher makes it from 600 science; the vanilla Dirt Excavator (2,000) remains the stone-free source.
- **Values (raw effort, global):** Dirt 0.28, Brick 1.11, Concrete 1.14 (was 1.27: concrete no longer pays for a crushing hour). In a 1,000-science world (pit stone at 1.0): Dirt 0.50, Brick 1.33, Concrete 1.60 (was 1.75).
- **Kiln contention** is deliberate: one kiln fires bricks or cement, so players build a second kiln.

### Terrain Block

The vanilla Iron Teeth Terrain Block (4 Dirt) unlocks at **2,000** science instead of 1,000, with the vanilla Dirt Excavator, after bricks and concrete. It is a same-path partial blueprint (`BuildingSpec.ScienceCost` only) written by `tools/vanilla_tool_overrides.mjs`; `progression_data.mjs` reads the patched science and `automation_content.json` lists the patch. The Mud Bath (1,800) is unchanged.

### Brick in the material cost rule

`materialRule.families.brick` fails when unavailable ("brick shown before Brick exists"), `familyGoods.T1..T5.brick` is `{Brick: 1}`, and `Plaster_Orange.IronTeeth`, the one brick-red native surface, prices as brick (it was unpriced). Bootstrap: the crusher (1%) and kiln (1%) show brick under `minFamilyShare`, so it folds and they never cost the good their own chain makes first; no building below 600 science shows 5% or more (Fertilizer Works 3%, Fish Hatchery 2%, Greenhouse 2%). 14 buildings now cost Brick (7,275 in all): Deep Drill 140, Deep Processor 135, Food Packaging Works 70, Water Treatment Plant 75, Technical School 100, Town Plaza 40, Deep Mine 275, Archive Excavation 720, Electrolysis Plant 340, Hospital 415, Mission Control 340, Rocket Assembly Hangar 2,330, Uranium Processing Plant 850, Radioactive Waste Refinery 1,445. Their value is redistributed, so their other material goods fall a little. Totals over the 48 buildings: Concrete 92,170 -> 94,440 (cheaper concrete raises value-preserving counts), Plank 3,605 -> 3,445, TreatedPlank 3,235 -> 2,920, MetalBlock 7,525 -> 7,155, HighGradeSteel 2,495 -> 2,370, Alloy 1,865 -> 1,770, Limestone 300 -> 250, Log 185 -> 210.

**Stone budget** (`prepare_deep_frontier_map.py builtin`, every built-in map): the buildings up to the quarries need 1,535 Sandstone (was 1,275) and 1,343 Limestone (was 1,393), against 1,800 of each in pit range. Sandstone now carries more of the load (bricks, dirt and concrete rubble), and both still fit. After the first art batch (below): 1,549 Sandstone and 1,338 Limestone. The quarries' brick plinths (third batch) raised Sandstone to 1,855, over the 1,800 in pit range, so the crusher yield went from 6 to 8 dirt per 3 sandstone (the proposal's lever): now **1,723 Sandstone and 1,266 Limestone**. Brick in all costs after the third batch: 8,768 (18 buildings and the Brick Block): Concrete Mixer 60, Deep Drill 175, Deep Processor 180, Food Packaging Works 95, Water Treatment Plant 90, Technical School 130, Sandstone Quarry 270, Limestone Quarry 320, Coal Power Plant 120, Town Plaza 40, Deep Mine 300, Archive Excavation 780, Electrolysis Plant 370, Hospital 450, Mission Control 370, Rocket Assembly Hangar 2,525, Uranium Processing Plant 920, Radioactive Waste Refinery 1,565.

**Art, first batch.** Brick courses are geometry: running-bond bricks in Plaster_Orange over a recessed mortar course (`lategame_mining_parts.hall(plinth_mat=BRICK)` and `brick_block`, append-only; late-game studies use native materials only, so the mortar is Plaster_White). The Deep Drill pump house and Deep Processor blower house stand on brick plinths (Brick 140 -> 155 and 135 -> 160); the Coal Power Plant's pale concrete ground storey, engine bed and chimney base are brick (it now costs 110 Brick, Concrete 315 -> 245). The Limestone Masonry Block became the Brick Block (`BrickMasonryBlock`, 4 Brick + 1 Cement at 600 science, cost factor 2: 8 Brick and 2 Cement), keeping placed blocks through `BackwardCompatibleTemplateNames: ["LimestoneMasonryBlock.IronTeeth"]`. The limestone outcrop and seam are native cliff rock (WaterSource/UndergroundRuinsCliff) with pale limestone only on broken faces and grike walls.

**Art, second batch.** `lategame_civic_parts.brick_skin` (append-only) lays the same courses on a solid wall and leaves each door, window and lamp open: the feature is authored through `authored_box`, which returns the box of the geometry it added, and every course skips that box on the face it stands on. Brick ground storeys on the Public Health Lab (4.5% brick, under minFamilyShare, so it folds and the cost is unchanged), Technical School (Brick 100 -> 115) and Food Packaging Works (70 -> 85), and brick walls on the Water Treatment Plant's chemical house (75 -> 80).

**Art, third batch.** `factory_registration.brick_box` (append-only; the industrial palette allows the kiln tiles, so the mortar is cement dust DFIndustrial24 and the cap grey kiln masonry DFIndustrial14) replaces the Concrete Mixer's coursed grey masonry on its footings, piers and pedestals (it now costs 60 Brick, Limestone 120 -> 45) and faces the quarries' process plinth with brick on its outer sides under a grey cap (the quarries now cost 270 and 320 Brick; brick is not a deposit family, so it is priced on them).

**Art, fourth batch.** `brick_courses.py` (new; the same course dimensions) lays brick faces through a module's own box function. `grid_structure.platform(pier_material=BRICK)` and `civic_isometric_geometry.timber_column(foot=BRICK)` / `balcony_storey(foot=...)` (opt-in; defaults unchanged) turn the cast concrete footings under the Restaurant's dining-gallery posts and the Fishery Works' deck posts into brick piers on a lime mortar core. Both show under 5% brick, so their costs are unchanged; the Restaurant's remaining concrete is its cast roof slab and parapet, the Fishery's its terrace slab.

**Brick tile (2026-10-31).** In game (build 224) the modelled Plaster_Orange courses read as orange plaster, not brick (user). Brick is now a texture: `DFIndustrial06`, the retired aggregate tile (no exported model used it), is a painted running-bond tile from `tools/asset-pipeline/paint_brick_tile.py` (original procedural artwork, fixed seed; 512 px per tile like every DFIndustrial tile, 8 courses x 3 stretchers per tile, ten reds and browns, 10 px pale joints). Custom tiles are world-projected at one texture per tile, so the courses line up across faces. `reference_materials.BRICK_TILE` / `lategame_kit.BRICK` (allowed on broad surfaces through `lategame_kit.MOD_TILES`); every brick helper (`brick_courses.brick_block`, `factory_registration.brick_box`, `lategame_mining_parts` hall plinths and `brick_block`, `lategame_civic_parts.brick_skin`, `structural_geometry.brick_masonry`) lays flat brick slabs over a core with the same outer extents. Finished triangles, modelled courses -> tile: Brick Block 982 -> 38, Coal Power Plant 6,552 -> 2,490, Technical School 9,432 -> 8,018, Public Health Lab 5,412 -> 4,248, Food Packaging Works 9,228 -> 7,912, Water Treatment Plant 11,282 -> 10,910, Deep Drill 10,692 -> 9,482, Deep Processor 8,184 -> 6,946, Concrete Mixer 8,136 -> 5,272, quarries 11,593 -> 6,229, Restaurant 15,026 -> 12,234 (with the roof pass), Fishery Works 16,342 -> 15,278. Connection faces: none removed; the flat brick walls gained six (Food Packaging Works four front faces on its bay row, Water Treatment Plant two on the chemical house back). Pricing: `DFIndustrial06` is brick and `Plaster_Orange.IronTeeth` stays brick (decision 6). Brick in all costs: 8,928 (19 buildings and the Brick Block); the Public Health Lab now shows brick (50), the quarries less (200 and 240, flat faces measure less area than modelled bricks), the Coal Power Plant, Deep Drill and Deep Processor more (265, 225, 250). Stone budget: 1,673 Sandstone and 1,208 Limestone of 1,800.

**Brick tile toned; more brick (2026-10-31, build 227 feedback: "only touches of brick", "too bright red").** The tile is repainted in weathered brown-red and terracotta with grey lime mortar: in a lit swatch render beside the shipped Iron Teeth materials its mean HSV went from S .45 V .63 to S .34 V .46 (Plaster_Orange S .68 V .60, Plaster_White S .10 V .66, dark planks S .13 V .25, BaseMetal V .47). Brick is now the wall body on twelve buildings, with concrete or timber dressings kept: Public Health Lab (upper-storey infill, white -> brick), Deep Drill (engine room; `lategame_mining_parts.concrete_house(wall=...)`, opt-in), Deep Ore Processor (furnace podium walls), Food Packaging Works (main block walls and upper-floor infill), Water Treatment Plant (filter house infill and gable, chemical house), Technical School (upper storeys, clock-tower shaft, belfry and wing infill), Coal Power Plant (chimney), Steel Mill (melt-shop podium; `lategame_industry_parts.plinth(wall=...)`, opt-in), Precision Machine Works (ground storey, sawtooth gables, chimney), Deep Mine (shaft house and annex), Bathhouse (hall band, boiler room and its chimney) and Electrolysis Plant (cell house infill and gables). Concrete stays on tanks, slabs, clarifiers, the water tower and the late-game reactor, radioactive and rocket buildings; the pits, crusher, kiln and Fertilizer Works stay brick-free. Material changes only: connection faces and triangle counts unchanged, zfight 0. With the Cement ladder (Cement = 3 Limestone + 1 Brick), brick in all costs is 10,268 (21 buildings and the Brick Block; Deep Mine 620, Deep Drill 355, Coal Power Plant 305, Deep Processor 290, Precision Machine Works 210 (new), Bathhouse 190 (new), Food Packaging Works 180, Public Health Lab 155); the Steel Mill's podium shows under 5% and folds. Stone budget: 1,650 Sandstone and 1,046 Limestone of 1,800. Dirt has one use in Deep Frontier content now, brick earth for the kiln's bricks; the vanilla Iron Teeth Dirt Excavator (2,000 science, 4 Dirt per 6 h, no inputs, 200 hp) also makes it, a route the stone audit could take from 2,000 science on if the sandstone budget tightens.

## Retired goods (2026-10-30, bricks pass)

Seven goods are deleted, not kept as legacy entries. Old saves migrate natively: each removed id is in the `BackwardCompatibleIds` of a remaining good of the same storage type (`GoodService.BindGoodToItsBackwardCompatibleIds`, Timberborn.Goods 1.1.2.8), and each removed recipe in the `BackwardCompatibleIds` of the recipe that replaces it in the same building (`Manufactory.Load`, Timberborn.Workshops). A stored stack, a construction site's delivered goods and a reservation all resolve through the same lookup. The single table is `tools/content_policy.json` `migratedGoods`/`migratedRecipes`; `tools/good_migrations.mjs` feeds the generators and `tools/validate_good_migrations.mjs` checks the generated data. Runtime migration of an old save is a separate probe (see `tools/STATUS.md`).

| Removed | Saves load it as | Recipe migration | Replacement in content |
|---|---|---|---|
| Aggregate | Sandstone | crusher `Aggregate` -> `BrickEarth` | Cement takes Dirt, concrete takes Sandstone, the concrete levee block takes 1 Sandstone. Not Dirt: Dirt is Pileable and would land in box warehouses. |
| Flux | Limestone | Steel Mill `Flux` -> `HighGradeSteel` | High-grade steel takes 1 Limestone as its flux (the quarries at 4,000 come before the mill at 4,500). Electronics and the reinforced bot chassis drop it. |
| Compost | Fertilizer | Fertilizer Works `Compost` -> `Fertilizer` | Fertilizer = 1 Log + 2 Algae + 2 Water -> 2 Fertilizer, 2 h (the two old recipes added together). The Greenhouse gate is 30 Fertilizer instead of 30 Compost. |
| MedicalFood | CannedFish | Food Packaging Works -> `CannedFish` | Removed: plain Hunger 0.3 with no medical effect. Medicine keeps its Hospital and reactor-course uses. |
| EmergencyRation | CannedFish | Food Packaging Works -> `CannedFish` | Removed: a duplicate of the vanilla corn ration. |
| PackagedFood | CannedFish | Food Packaging Works -> `CannedFish` | The Technical School's flight course takes 0.5 Canned Fish per hour instead (the course's preserved field rations). The Grocery Store stocks vanilla Eggplant Rations on the same stand (its model nodes renamed). |
| ArchiveData | RecoveredArtifact | Archive Excavation `ArchiveData` -> `RecoveredArtifact` | Guidance computer = 4 Electronics + 2 Machine Core + 2 Recovered Artifact + 1 Grease; guidance telemetry = 1 Guidance Computer + 2 Recovered Artifact + 1 Metal Part (the old 2 artifacts, grease and metal part per archive data, folded in: Mission Control reads the drives directly). Human Record Caches survey on the artifact recipe and give 12 artifacts (was 6 archive data). Chapter 5 asks for 20 artifacts in total (was 10 archive data), chapter 6 for 40 artifacts in total and a Mission Control (was 30 archive data). |

The Food Packaging Works now makes only canned fish. Active Deep Frontier goods: 51 checked by the item-use audit, all with enough uses (Brick 14, Medicine 2, Canned Fish 2, Limestone 6).

## Late-game power rule (2026-10-29)

User request: the endgame buildings must need much more power ("smog scrubber only taking 200? more like 2000"). Every Deep Frontier power consumer (`MechanicalNodeSpec.PowerInput` > 0) unlocked at 2,000 science or more draws at least

    floor(science) = 2,000 × (science / 2,500)^0.75 ≈ 5.65 × science^0.75

rounded to the nearest 100 hp below 10,000 and the nearest 1,000 hp from 10,000 up, so the 2,500-science Smog Scrubber draws exactly 2,000 hp. A building draws `max(authored base, floor)`: the authored figures stay in their catalogs and generators, and every generator that writes a consumer's `PowerInput` applies `scaledPower(id, base, science)` from `tools/lategame_costs.mjs` (constants in `building_construction_costs.json` `lategameRule.power`), as authored costs go through `scaledCost`. Descriptions that state a power figure take the generated value. `tools/validate_power_rule.mjs` (a validate_all check) fails on a consumer below its floor that is not exempt, and on an exemption that names no such consumer or is no longer needed.

Exempt (`lategameRule.power.exempt`): the Deep Well (its draw follows the boost slider at runtime, 1,667 hp per step, 10,000 hp at 6×; in a drought 100,000 hp at any boost, running only on full power and at most 2×, `deep_well_content.json` `drought`) and the Reactor Charging Bay (5,000 hp, the user's explicit choice). Generators are outside the rule. Buildings below 2,000 science keep their authored draw.

| Building | Science | Floor | Before | Now |
|---|---:|---:|---:|---:|
| Technical School | 2,200 | 1,800 | 300 | 1,800 |
| Smog Scrubber | 2,500 | 2,000 | 200 | 2,000 |
| Chemical Works | 4,000 | 2,800 | 3,500 | 3,500 (authored) |
| Limestone / Sandstone Quarry | 4,000 | 2,800 | 1,500 | 2,800 |
| Steel Mill | 4,500 | 3,100 | 2,500 | 3,100 |
| Precision Machine Works | 5,000 | 3,400 | 2,200 | 3,400 |
| Bathhouse | 6,000 | 3,900 | 300 | 3,900 |
| Grocery Store | 6,000 | 3,900 | 100 | 3,900 |
| Deep Mine | 6,000 | 3,900 | 4,000 | 4,000 (authored) |
| Archive Excavation | 9,000 | 5,200 | 400 | 5,200 |
| Electrolysis Plant | 10,000 | 5,700 | 6,000 | 6,000 (authored) |
| Cryogenic Liquefaction Plant | 12,000 | 6,500 | 10,000 | 10,000 (authored) |
| Cryogenic Tank Farm | 12,000 | 6,500 | 1,000 | 6,500 |
| Materials Laboratory | 12,000 | 6,500 | 600 | 6,500 |
| Hospital | 25,000 | 11,000 | 600 | 11,000 |
| Mission Control | 30,000 | 13,000 | 1,500 | 13,000 |
| Deep Well | 30,000 | 13,000 | 1,667–10,000 (drought: 100,000) | unchanged (exempt) |
| Rocket Assembly Hangar | 50,000 | 19,000 | 12,000 | 19,000 |
| Launch Pad | 80,000 | 27,000 | 25,000 | 27,000 |
| Uranium Processing Plant | 200,000 | 53,000 | 5,000 | 53,000 |
| Reactor Charging Bay | 250,000 | 63,000 | 5,000 | 5,000 (exempt) |
| Radioactive Waste Refinery | 500,000 | 106,000 | 8,000 | 106,000 |

With the same change the generators were buffed (authored outputs, fuel unchanged): Coal Power Plant 5,000 → 25,000 hp, Oil Power Plant 20,000 → 90,000 hp, Reinforced Hydro Turbine 9,600 → 40,000 hp (rated output at its unchanged 3 m³/s and 16-layer caps; docs/hydroelectric-construction.md) and Nuclear Reactor 800,000 → 1,000,000 hp (still scaled by `1 − heat` at runtime).

## Science curve (2026-10-29)

Superseded on 2026-11-01 by [Science curve and menu order](#science-curve-and-menu-order-2026-11-01): the transition, frontier, launch and nuclear unlocks below are raised there, and the laboratory became a transition-stage building.

User decision: the late-game unlocks climb steeply towards the 1,000,000-science reactor, so players build the Materials Laboratory (400 science per working hour against the Numbercruncher's 10) as the stepping stone. The laboratory (12,000), everything below it and every building that makes the goods its recipes consume keep their science. The Materials Research recipe needs Gear, Concrete, Metal Block and Water; the Geochemical Assay needs UraniumOre, ConcentratedWaste, ReactorCoolantWater, LiquidHydrogen and LiquidOxygen; all of them are available at 12,000. Source: `frontier_progression.json` (`implementedBuildingScienceOverrides`, `nuclearScienceRule`), `create_frontier_expansion_content.mjs` (rocket rows), `radiation_content.mjs` (sludge buildings).

| Building | Before | Now |
|---|---:|---:|
| Mission Control | 14,000 | 30,000 |
| Rocket Assembly Hangar | 18,000 | 50,000 |
| Launch Pad | 20,000 | 80,000 |
| Uranium Processing Plant | 100,000 | 200,000 |
| Radioactive Waste Vault | 100,000 | 200,000 |
| Radioactive Waste Export, Sludge Outfall, Sludge Recovery Pump | 120,000 | 200,000 |
| Radioactive Waste Refinery | 120,000 | 500,000 |
| Nuclear Reactor | 1,000,000 | 1,000,000 |

Unchanged on purpose: the Hospital (25,000) cures irradiated beavers and must stay reachable before radioactive tides (cycle 15 by default); the concrete platforms and scaffolds (up to 14,000) are construction pieces, not stages. The rocket missions still award 100,000 and 250,000 science, so the launch programme pays back its 160,000 of unlocks. Tier T4 now ends at 30,000 (was 15,000) so Mission Control keeps its construction cost; no other building changes tier. The reactor's output rose from 750,000 to 800,000 hp.

## Audit findings (generated data, 2026-10-21)

The data came from a scratch-tree generation of the current sources. That generation needed one scratch-only stub, for the pending civic wall-face measurement.

### Chain completion (2026-10-21, user decisions)

The first audit found the whole late game unreachable: no building ran Flux, HighGradeSteel, Alloy, DeepCoal, DeepOil, DeepUranium or Compost, and nothing produced SulfurGas, PowerModule, Chemical, ArchiveData or RecoveredArtifact. The user scrapped the gases and kept high-grade steel. Changes made in the sources:

- **Gases removed everywhere.** Gas, Methane, SulfurGas, ToxicFumes and Radon are gone (goods, icon list, validator ids, generated outputs). HydrogenGas and OxygenGas stay; they feed the LH2/LOX rocket fuel.
  - Polymer = 3 CrudeOil + 1 Chemical + 2 Water -> 3 Polymer (3 h).
  - Yellowcake = 3 UraniumOre + 1 Chemical + 2 Water -> 2 Yellowcake (2 h), with no Radon.
- **DiningService dropped.** The good and its recipe are removed. It was a prohibited placeholder (`content_policy.json`), and no building ever ran its recipe, so no save can hold it.
- **New recipes:**
  - Chemical at ChemicalWorks: 4 Badwater + 1 Extract -> 2 Chemical (2 h).
  - PowerModule at Precision Machine Works: 1 Electronics + 1 Alloy + 2 MetalPart -> 1 PowerModule (2 h).
  - RecoveredArtifact: 1 Explosives + 2 TreatedPlank -> 1 (6 h). Charges and timber shoring open human ruins.
  - ArchiveData: 2 RecoveredArtifact + 1 Grease + 1 MetalPart -> 1 (4 h). Grease and parts restore the old data drives. Paper is Folktails-only, so it is not used.
- **Orphan recipes assigned:**
  - DeepCoal, DeepOil and DeepUranium go to the Deep Processor, the surface processor for deep ore. No separate building is needed: they are the same ore and water input as DeepAlloy.
  - Compost goes to FertilizerWorks.
- **Planned buildings** are data entries in `frontier_progression.json` `plannedBuildings`. Since the build 122 integration all three are generated from these entries and listed in `lategame_batches.json` (Archive Excavation on the BotPartFactory template). Their tiers are in `lategameTier`, and the rule prices them once a registration exists. The generator fails if a planned building names an undefined recipe.

| Planned id | Recipes / role | Footprint target | Workers | Power | Science | Tier | Menu |
|---|---|---|---:|---:|---:|---|---|
| SteelMill | Flux, HighGradeSteel, Alloy | 12x10x16 | 6 | 3,100 hp (authored 2,500; power rule) | 4,500 | T3 | Metal 40 |
| ArchiveExcavation | RecoveredArtifact, ArchiveData; proposed placement over vanilla UndergroundRuins | 10x9x10 | 4 | 5,200 hp (authored 400; power rule) | 9,000 | T4 | Science 46 |
| CryogenicTankFarm | Pipe-fed Liquid storage for LiquidHydrogen or LiquidOxygen (one selected good per farm, 2,000 capacity) | 4x4x5 | 0 | 6,500 hp (authored 1,000; power rule) | 12,000 | T4 | Storage 90 |

### Decisions applied (2026-10-21, second round)

- **Reactor waste:** `NuclearWaste` makes 1 RadioactiveWaste per 2 h cycle (0.5/h). `WasteRefining` takes 4 RadioactiveWaste + 2 Chemical + 8 Water per 8 h and gives 12 Badwater + 2 RecoveredMinerals. One refinery serves one reactor; the 1,600-slot vault holds about 133 days of waste. The ids stay; a radiation agent will turn waste into a fluid separately.
- **Greenhouse:** the fish recipe is replaced by glasshouse crops. Each uses 2 Fertilizer per 8 h cycle:
  - Eggplant: 2 Fertilizer + 4 Water -> 48.
  - Kohlrabi: 2 Fertilizer + 4 Water -> 112.
  - Coffee beans: 2 Fertilizer + 3 Water -> 24.

  Vanilla fields yield 3 eggplant per 12 days, 2 kohlrabi per 3 days and 1 coffee per 9 days per tile. The first yields beat an equal-area field of 42 ground cells by about 1.5-2x; on 2026-10-27 every product was raised 8x (inputs and cycle unchanged) so the fertilizer chain pays off, about 12-16x that field. One Fertilizer Works (2/h) supplies 8 greenhouses.
- **Archive Excavation:** free placement, no understructure, so it never competes with the vanilla Efficient Mine.
- **Concrete:** cement is 3 Limestone + 1 Aggregate (crushed sandstone) instead of Dirt (`construction_materials.json`). Concrete's gate drops from 2,000 to 1,000 science (cumulative 3,500, from 6,300).
- **Hydro turbine:** 30,000 -> 8,000 science (`hydro_content.json`). Every consumer before the reactor now needs at most three turbines.
- **Nuclear support unlocks** sit beside the reactor (`frontier_progression.json` `implementedBuildingScienceOverrides`): Uranium Processing Plant 100,000, Waste Vault 100,000, Waste Refinery 120,000. They are bought in the run-up to the 1,000,000 reactor, not as mid-game dead ends. Their science puts them in cost tier T5.
- **Technical School and Launch Pad recipes:** unchanged. Workforce and launch agents own them.
- **Gas source icons** deleted from `src/DeepFrontier/Art/Icons`, and the asset validator list is updated. The gas text in `implementation-plan.md` is rewritten.

**Current static chain** (scratch generation of the current sources, after the 2026-10-21 decisions below; `audit_progression.mjs`: 0 failures). Every ingredient and every construction good now has a producing recipe run by a generated or planned building. *Gate* is the largest single unlock on the route; *cumulative* is the summed science of the route's distinct unlocks.

| Good | Producer (recipe @ building) | Gate | Cumulative |
|---|---|---:|---:|
| Aggregate | Aggregate @ StoneCrusher | 600 | 1,300 |
| Alloy | Alloy @ SteelMill (planned) | 4,500 | 10,950 |
| ArchiveData | ArchiveData @ ArchiveExcavation (planned) | 9,000 | 18,820 |
| CannedFish | CannedFish @ FoodPackagingWorks | 1,400 | 5,800 |
| Cement | Cement @ CementKiln | 900 | 2,500 |
| Chemical | Chemical @ ChemicalWorks | 4,000 | 9,300 |
| Coal | DeepCoal @ DeepProcessor | 1,200 | 5,500 |
| Compost | Compost @ FertilizerWorks | 350 | 1,100 |
| ConcentratedWaste | PureWater @ WaterTreatmentPlant | 1,800 | 5,650 |
| Concrete | Concrete @ ConcreteMixer | 1,000 | 3,500 |
| CrudeOil | DeepOil @ DeepProcessor | 1,200 | 5,500 |
| Cryocoolant | Cryocoolant @ ChemicalWorks | 4,000 | 12,200 |
| DeepAlloy | DeepAlloy @ DeepProcessor | 1,200 | 5,650 |
| DeepOre | gathered @ DeepDrill | 1,000 | 4,300 |
| Electronics | Electronics @ PrecisionMachineWorks | 5,000 | 20,800 |
| EmergencyRation | EmergencyRation @ FoodPackagingWorks | 1,400 | 4,900 |
| EnrichedFuel | EnrichedFuel @ UraniumProcessingPlant | 100,000 | 120,800 |
| Fertilizer | Fertilizer @ FertilizerWorks | 350 | 1,100 |
| FilterMedia | FilterMedia @ WaterTreatmentPlant | 1,800 | 5,650 |
| FishOil | FishOil @ FisheryWorks | 900 | 1,300 |
| FlightLicense | FlightLicense @ MissionControl | 14,000 | 46,700 |
| Flux | Flux @ SteelMill (planned) | 4,500 | 9,600 |
| FreshFish | gathered @ FisherFlag | 0 | 0 |
| GuidanceComputer | GuidanceComputer @ MissionControl | 14,000 | 46,320 |
| HighGradeSteel | HighGradeSteel @ SteelMill (planned) | 4,500 | 10,800 |
| HydrogenGas | Electrolysis @ ElectrolysisPlant | 10,000 | 18,450 |
| IndustrialLicense | IndustrialLicense @ TechnicalSchool | 2,200 | 6,150 |
| JuvenileFish | JuvenileFish @ FishHatchery | 600 | 1,350 |
| Limestone | gathered @ LimestonePit | 300 | 300 |
| LiquidHydrogen | Liquefaction @ CryogenicLiquefactionPlant | 12,000 | 36,200 |
| LiquidOxygen | Liquefaction @ CryogenicLiquefactionPlant | 12,000 | 36,200 |
| Lubricant | retired 2026-10-30: uses moved to vanilla Grease @ GreaseFactory (2,000) | | |
| MachineCore | MachineCore @ PrecisionMachineWorks | 5,000 | 20,800 |
| MedicalFood | MedicalFood @ FoodPackagingWorks | 1,400 | 7,350 |
| Medicine | Medicine @ PublicHealthLab | 1,000 | 4,750 |
| MissionPayload | MissionPayload @ MissionControl | 14,000 | 46,320 |
| OxygenGas | Electrolysis @ ElectrolysisPlant | 10,000 | 18,450 |
| PackagedFood | PackagedFood @ FoodPackagingWorks | 1,400 | 6,100 |
| Polymer | Polymer @ ChemicalWorks | 4,000 | 11,300 |
| PowerModule | PowerModule @ PrecisionMachineWorks | 5,000 | 20,800 |
| PropulsionPackage | PropulsionPackage @ RocketAssemblyHangar | 18,000 | 38,800 |
| PureWater | PureWater @ WaterTreatmentPlant | 1,800 | 5,650 |
| RadioactiveWaste | EnrichedFuel @ UraniumProcessingPlant | 100,000 | 120,800 |
| ReactorCoolantWater | ReactorCoolantWater @ WaterTreatmentPlant | 1,800 | 5,650 |
| RecoveredArtifact | RecoveredArtifact @ ArchiveExcavation (planned) | 9,000 | 16,100 |
| RecoveredMinerals | retired 2026-10-29 | | |
| RecoveredTelemetry | GuidanceTelemetry @ MissionControl | 14,000 | 46,320 |
| RocketAirframe | RocketAirframe @ RocketAssemblyHangar | 18,000 | 38,800 |
| Sandstone | gathered @ SandstonePit | 300 | 300 |
| SpecialistLicense | SpecialistLicense @ TechnicalSchool | 5,000 | 23,300 |
| SweetBerryCake | SweetBerryCake @ Restaurant | 1,000 | 4,300 |
| UraniumOre | DeepUranium @ DeepProcessor | 1,200 | 5,500 |
| Yellowcake | Yellowcake @ UraniumProcessingPlant | 100,000 | 120,800 |

The Rocket Assembly Hangar (18,000), Launch Pad (20,000), the nuclear support buildings (100,000-120,000) and the Nuclear Reactor (1,000,000) are buildable at their own science once the Steel Mill exists. The Launch Pad's mission recipes are owned by the launch implementation and were not changed.

The current generated package has 55 new goods and the item-use audit reports zero goods below the required two distinct uses. Legacy license tokens remain save-compatibility placeholders and are excluded by policy.

### Unlock order (failures)

The audit now fails when a building unlocks before any of its construction goods, or before any of its recipes can run. A later extra recipe on a building that already works stays a warning; the Technical School's SpecialistLicense is the only one left, and the workforce agent owns it.

- **Compost** is Dirt-free: 1 Log + 1 Algae + 1 Water -> 2 Compost. Fertilizer Works and the Greenhouse now run when they unlock (Compost and Fertilizer available at 350 science).
- **Raised unlocks:**
  - masonry blocks 600 -> 900, to match cement;
  - Deep Drill 800 -> 1,000 (bots 1,800 -> 2,000), to match concrete;
  - Restaurant 800 -> 1,000, to match concrete;
  - Public Health Lab 900 -> 1,000, to match concrete.

### Menus

Superseded on 2026-11-01 by the left-to-right unlock order ([Menu order](#menu-order)).

Fixed: Nuclear Reactor Power 60 -> 250 (it collided with the Gravity Battery), Mission Control Science 50 -> 110 (it collided with the Bot Part Factory).

Coherence issues (not audit failures):

- The Metal group holds 20 Deep Frontier tools. The early concrete chain (70-76) sorts after the rockets and the launch pad (49-51).
- The Vault (Storage 61) sits between the vanilla Small and Medium Tanks.

### Power (warnings)

Fixed by the 8,000-science hydro turbine (9,600 hp then; 40,000 hp since 2026-10-29, when the power rule above also raised the consumers, so the counts below are historical). Before 8,000 science the best generator is the vanilla Large Water Wheel (540 hp): Chemical Works needs 7, Precision Machine Works 5 and the Deep Mine 8. After that, the Cryogenic Liquefaction Plant and Rocket Assembly Hangar need 2 turbines each and the Launch Pad 3. The installed Compact Water Turbine dependency (1,000 hp, 4,000 science) is not modelled by the audit.

### Recipe balance

- **Reactor waste:** fixed. 0.5 waste per hour, and one refinery per reactor.
- **Coolant demand.** One reactor needs 3 coolant per hour. That takes three Water Treatment Plants on coolant, plus three more making PureWater for them.

### Buildings without a valid purpose

| Building | Problem |
|---|---|
| Greenhouse | Fixed: eggplant, kohlrabi and coffee from Fertilizer, plus aquaponics from juvenile fish, runnable at its 600-science unlock. |
| FertilizerWorks | Fixed: runs Compost and Fertilizer; the Greenhouse consumes the Fertilizer. |
| TechnicalSchool | Makes only the prohibited license placeholders (`content_policy.json`). |
| LaunchPad | Its only recipe, GuidanceTelemetry, duplicates Mission Control. No recipe consumes RocketAirframe, PropulsionPackage, MissionPayload, LiquidHydrogen or LiquidOxygen, so no launch exists. Two workers, against 8–12 in the plan. |
| WaterTreatmentPlant | Fixed: ConcentratedWaste feeds chemical from brine and the geochemical assays. |

## Power plants (2026-10-22)

User request: bring back coal and oil power plants that are smaller and give less power than the reactor (750,000 hp then, 1,000,000 since 2026-10-29), but still enough to run the machinery. On 2026-10-29 both were buffed with unchanged fuel use: coal 5,000 → 25,000 hp, oil 20,000 → 90,000 hp. Catalog: `frontier_progression.json` `powerPlants`; generator `makePowerPlant` in `create_frontier_expansion_content.mjs`; studies `lategame_CoalPowerPlant.py` and `lategame_OilPowerPlant.py`. Static authoring only; not built or tested in game. Since 2026-10-27 both plants are workerless native Steam Engine generators (they were staffed Smelter workshops with the `CoalFiring`/`OilFiring` recipes, now removed).

| Plant | Output | Consumed per hour while generating | Footprint | Workers | Science | Cost tier |
|---|---:|---|---|---:|---:|---|
| Coal Power Plant | 25,000 hp | 1 Coal + 1 Water (inventory for 50 h: 50 of each) | 5×5, 10 layers | 0 | 4,500 | T3 |
| Oil Power Plant | 90,000 hp | 2 Crude Oil + 2 Water (inventory for 50 h: 100 of each) | 6×6, 9 layers | 0 | 11,000 | T4 (+4 Machine Core gate) |

Demand is the sum of `MechanicalNodeSpec.PowerInput` in the generated Iron Teeth blueprints (Deep Frontier and vanilla):

| Scenario | Consumers (hp) | Demand | Plants |
|---|---|---:|---|
| Steel mill line | Steel Mill 3,100, Deep Drill 1,000, Deep Ore Processor 500, Smelter 200, Gear Workshop 120, Wood Workshop 250 | 5,170 | 1 coal |
| Mid-game industrial district | the line above + Chemical Works 3,500, Precision Machine Works 3,400, quarry 2,800, Cement Kiln 300, Concrete Mixer 250, Stone Crusher 200 | 15,620 | 1 coal |
| Same, Deep Mine instead of the drill | +3,000 | 18,620 | 1 coal |
| Cryogenic fuel line | Water Treatment 500, Electrolysis 6,000, Cryogenic Liquefaction 10,000, Cryogenic Tank Farm 6,500 | 23,000 | 1 coal or 1 oil |
| Rocket factory | Rocket Assembly Hangar 19,000, Precision Machine Works 3,400, Steel Mill 3,100, Chemical Works 3,500, Deep Mine 4,000, Deep Ore Processor 500, Mission Control 13,000 | 46,500 | 2 coal or 1 oil |
| Whole launch program | cryogenic fuel line + Hangar 19,000, Mission Control 13,000, Launch Pad 27,000 | 82,000 | 1 oil |

Consumer figures follow the power rule above. The first balance kept the plan's 1:4 coal-to-oil step at 5,000/20,000 hp; the 2026-10-29 buff makes it 25,000/90,000 (about 1:3.6). One reactor equals about 11 oil plants or 40 coal plants.

Fuel chains (no new producer was needed):
- Coal: Deep Drill (1,000, finite source) or Deep Mine (6,000, permanent vein) → Deep Ore → Deep Ore Processor `DeepCoal` (1 Deep Ore + 2 Water → 3 Coal per 2 h, gate 1,200). One processor (1.5 Coal per working hour) feeds 1.5 coal plants at full load during its working hours; a plant that runs through the night as well needs more (24 Coal a day at full load). The Steel Mill and carbon filters compete for it.
- Oil: the same processor's `DeepOil` (1 Deep Ore + 3 Water → 6 Crude Oil per 2 h, doubled on 2026-10-27). There is no refinery and no refined fuel good, so the plant burns crude oil directly, competing with polymer at the Chemical Works. One processor on oil makes 3 Crude Oil per working hour, so one plant at full load (2 per hour) needs 0.67 processors during the processor's working hours; running the plant through the night as well takes 48 Crude Oil a day.

Output follows the vanilla Iron Teeth Steam Engine contract (`GoodConsumingBuildingSpec` + `GoodPoweredGeneratorSpec`, with its `PowerGeneratorSoundsSpec`, `GoodPoweredGeneratorAnimatorSpec` and `MechanicalNodeIlluminatorSpec`): no workers; native `GoodPoweredGenerator` pauses consumption while the power graph does not require power, and gives full hp while the building consumes, day and night. Fuel and water burn only while the network draws power; without either, or while paused (automation pauses it through `GoodConsumingBuilding` and `MechanicalBuilding`), output is 0. With no workers they carry no injury risk or bot upkeep. Both are smog emitters while generating (smoke and smog follow `PowerGeneratorParticleController`, SmogEmitter Activity `Generator`): coal one 12-tile disc at strength 0.55, oil two 8-tile discs at 0.3.

## Second uses (2026-10-25)

The item-use audit requires two real uses for every new good (`tools/content_policy.json`). The current generated Iron Teeth package now satisfies that gate for all 55 new goods. Every new consumer unlocks at or after the producer of each good it uses, so `audit_progression.mjs` stays at 0 failures. The audit is static authoring evidence; runtime playtesting remains a separate step.

Sources: `create_frontier_expansion_content.mjs` (recipes and building recipe lists), `building_construction_costs.json` (`lategameGates`), `research_content.json` (assay), `workforce_risks.json` (`botMaintenance`, `botAssembly`), `bot_upkeep_content.mjs` and `Scripts/Workforce/BotMaintenance.cs` (bots).

| Good | Before | New use | Consumer (science) | Good available at | Why |
|---|---|---|---|---:|---|
| Coal | none counted (Steel Mill planned) | Activated carbon filters: 1 Coal + 1 Plank → 3 FilterMedia (1 h) | Water Treatment Plant (1,800) | 1,200 | Activated carbon is a standard water filter. |
| | | Power modules: +1 Coal (graphite electrodes) | Precision Machine Works (5,000) | | Battery electrodes are graphite. |
| Flux | none counted (Steel Mill planned) | Electronics: +1 Flux (solder flux) | Precision Machine Works (5,000) | 4,500 | Soldering needs flux. |
| | | Reinforced bot chassis (below) | Precision Machine Works (5,000) | | The alloy frame is welded. |
| Compost | Fertilizer | Construction gate: 30 Compost in the Greenhouse beds | Greenhouse (600) | 350 | The beds are filled with compost. |
| JuvenileFish | FreshFish (Fishery) | Aquaponics: 1 JuvenileFish + 1 Fertilizer + 4 Water → 80 Kohlrabi + 16 FreshFish (8 h) | Greenhouse (600) | 600 | The fish grow in the bed tanks, and their waste replaces half the fertilizer of the 112-kohlrabi crop. |
| ConcentratedWaste | none | Chemical from brine: 3 ConcentratedWaste + 1 Extract → 2 Chemical (2 h) | Chemical Works (4,000) | 1,800 | Brine is the chlor-alkali feedstock. |
| | | Geochemical assays (below) | Materials Laboratory (12,000) | | A residue sample. |
| UraniumOre | Yellowcake | Geochemical assays: 1 UraniumOre + 1 ConcentratedWaste + 2 ReactorCoolantWater + 1 LiquidHydrogen + 1 LiquidOxygen → 1,600 science (4 h, 400/h, as the nameplate) | Materials Laboratory (12,000) | 1,200 | Ore assays. |
| ReactorCoolantWater | Reactor coolant | Geochemical assays | Materials Laboratory (12,000) | 1,800 | High-purity water for the analysis. |
| LiquidHydrogen, LiquidOxygen | Liquefaction | Geochemical assays | Materials Laboratory (12,000) | 36,200 | Cryogenic samples support high-energy material analysis as well as rocket missions. |
| Cryocoolant | Liquefaction | Reactor coolant conditioning: 4 PureWater + 1 FilterMedia + 1 Cryocoolant → 4 ReactorCoolantWater (4 h) | Water Treatment Plant (1,800) | 4,000 | Cryogenic coolant is required to condition the reactor's high-purity water. |
| HydrogenGas | Liquefaction | Enriched fuel: +1 HydrogenGas | Uranium Processing Plant (100,000) | 10,000 | Hydrogen reduces the oxide to fuel pellets. |
| OxygenGas | Liquefaction | Yellowcake: +1 OxygenGas | Uranium Processing Plant (100,000) | 10,000 | Oxygen is the leaching oxidant. |
| RadioactiveWaste | Waste refining | Spent fuel reprocessing: 4 RadioactiveWaste + 2 Chemical + 1 Yellowcake → 1 EnrichedFuel + 2 RadioactiveWaste (4 h) | Uranium Processing Plant (100,000) | 100,000 | Recovers fissile material. One fuel yields ten casks over its life, so reprocessing never reduces total waste. Disposal (2026-10-29): the Radioactive Waste Export dissolves 2 casks in 8 Water per hour and ships them off the map; waste refining no longer needs Chemical (4 RadioactiveWaste + 8 Water → 6 RadioactiveSludge). |
| EnrichedFuel | Reactor fuel | Construction gate: 20 EnrichedFuel, the first core load | Nuclear Reactor (1,000,000) | 100,000 | The plant must make fuel before the reactor is built. |
| RecoveredMinerals | none | Retired 2026-10-29: unproduced and unused, kept only for saves | | | The reactor gate is now 100 extra HighGradeSteel. |
| RadioactiveSludge (shown as Radioactive Water) | none (export or outfall is disposal) | Disposal only | Radioactive Waste Export, Outfall | 200,000 | Disposal at the Radioactive Waste Export (off the map) or the Outfall (into a river). Vitrification and mineral recovery were removed on 2026-10-29. |
| ContaminatedWater | Decontamination | Waste refining with contaminated water: 4 RadioactiveWaste + 8 ContaminatedWater → 6 RadioactiveSludge (8 h) | Radioactive Waste Refinery (120,000) | 120,000 | Contaminated water replaces clean process water. Its radioactivity goes into the radioactive water. The refinery also filters badwater: 10 Badwater + 1 FilterMedia → 8 Water (2 h). |
| Grease (vanilla, Grease Factory 2,000; replaced Lubricant on 2026-10-30) | Cryocoolant, ArchiveData, native bot need | Servo bot limbs (below); bot maintenance | Precision Machine Works (5,000); 16 hazardous workplaces | 2,000 | Servos and bot upkeep. |
| PowerModule | Enriched fuel | Reactor power cell: 2 per cell, for the Reactor Bot retrofit and the Reactor bot recipe (below) | Uranium Processing Plant (300,000) | 5,000 | Battery pack of a Reactor Bot. Until 2026-11-02 the recipe (then "Industrial bot") took one directly. |
| FishOil | CannedFish | Bot maintenance, as a cheaper blend | 16 hazardous workplaces | 900 | A cheap oil for bots. |

Recipes that share a product with another recipe in the same building get their own display names: activated carbon filters, chemical from brine, aquaponic kohlrabi and fish, spent fuel reprocessing, waste refining with contaminated water, and sludge vitrification. The native recipe dropdown (`ManufactoryDropdownProvider`, 1.1.2.8) finds the chosen recipe by `DisplayLocKey` with `SingleOrDefault`, so two recipes in one building with the same key would throw. `audit_progression.mjs` now fails on this (`recipe-display-key-collision`).

**Greenhouse 500 → 600 science.** This matches the Fish Hatchery, so aquaponics can run when the Greenhouse unlocks. It stays in tier T1.

### Bots

Bots already wear out 3–5× faster in heavy industry (`workforce_risks.json`). Bots now also give late-game goods real uses:

- **Late-game bot parts** at the Precision Machine Works (5,000). These are ordinary recipes for the vanilla part goods:
  - Reinforced bot chassis: 1 Alloy + 1 Polymer + 1 Flux → 2 BotChassis (4 h).
  - Servo bot limbs: 1 MachineCore + 1 Grease + 2 MetalPart → 4 BotLimb (4 h).
  - Bot cortex: 1 Electronics + 1 Polymer → 2 BotHead (4 h).

  The Bot Part Factory needs 54 worker-hours for one bot's parts. These recipes need 8.
- **Reactor bot** (recipe id `IndustrialBot`, shown as "Industrial bot" until 2026-11-02) at the vanilla Bot Assembler: 1 ReinforcedBotFrame + 1 ReactorPowerCell + 4 BotLimb + 1 BotHead → one Reactor Bot in 24 h. The native recipe takes 72 h.
  - The ingredients are the Reactor Bot retrofit parts (user decision, 2026-11-02): the reinforced bot frame (8 Steel, 4 Alloy, 1 MachineCore, 1 BotChassis) replaces the chassis and the reactor power cell (1 EnrichedFuel, 2 PowerModule, 2 Electronics, 2 Cryocoolant) is the battery pack, so the recipe asks for nothing the parts already contain. It is the retrofit path (an ordinary bot plus both parts) less the ordinary bot's chassis, three times faster. Until 2026-11-02 it took 1 BotChassis + 4 BotLimb + 1 BotHead + 1 PowerModule + 2 Steel and ran from about 12,000 science, long before the Reactor Charging Bay (400,000) that Reactor Bots need.
  - It is added by a same-path patch, `{"ManufactorySpec": {"ProductionRecipeIds#append": ["IndustrialBot"]}, "FrontierReactorBotAssemblySpec": {"RecipeId": "IndustrialBot"}}`.
  - It builds the Iron Teeth bot born as a Reactor Bot (user, 2026-11-02: the recipe's bots are the upgraded bots; `tools/super_bots.json` `upgrade`). The native `BotManufactory` spawns a bot when any assembler recipe finishes, and `BotFactory.Load` takes the faction's single template with `TemplateService.GetSingle<BotSpec>()`, so a second bot template is impossible without patching the game. Instead `ReactorBotAssembler` (Scripts/SuperBots/ReactorBotAssembly.cs) announces a Reactor Bot birth from `Manufactory.ProductionFinished` before the native handler (it subscribes in Awake, `BotManufactory` in InitializeEntity) and the new bot's `ReactorBot.InitializeEntity` takes it: the native `BotFactory.Create` instantiates and initializes the bot inside that handler, with a `CharacterBirthInit` carrying a `BotManufacturedEvent`. Ordinary-recipe bots and bots already in a save stay as they are.
  - The recipe is visible from the assembler's 750-science unlock, but it runs only once the Uranium Processing Plant (300,000) makes reactor power cells; `audit_progression.mjs` reads vanilla patches and reports this as a warning. The Reactor Charging Bay unlocks with the plant at 300,000 (400,000 until 2026-11-03, `docs/deadlock-audit.md` D6), so no Reactor Bot exists without a place to charge.
- **Bot maintenance.** `FrontierBotMaintenanceSpec` goes on all 16 open workplaces that have bot wear.
  - The building keeps a second native inventory for maintenance oil: 10 Grease and 10 FishOil. It is stocked only while a bot is assigned, so beaver crews never tie up oil.
  - A bot inside whose dose has run out takes one unit, Grease first. For 24 hours of wear, its wear multiplier is multiplied by 0.5 for Grease or 0.75 for FishOil, never below 1×. For example, the uranium plant drops from 5× to 2.5× with Grease or 3.75× with FishOil. (Lubricant until 2026-10-30, when it was merged into the vanilla Grease.)
  - The dose stays with the bot and is saved with it (`BotWear`).
  - Native `ManufactoryHaulBehaviorProvider` and `FillInputWorkplaceBehavior` fill every enabled input inventory of the building, so no new hauling code is needed.
  - Runtime: `BotMaintenance.cs` and `BotUpkeepPanels.cs`, with the dose in `BotWear.cs`.
- **Audit changes.**
  - `audit_item_uses.mjs` counts bot assembly ("Bot assembly: bots") as one destination, and maintenance oils ("Bot maintenance") as one destination for all workplaces.
  - Both audits read recipes appended to vanilla templates.
  - `tools/validate_bot_upkeep.mjs` checks the catalog, the runtime records and localization, the generated data and the automation declarations.

The meltdown agent's reactor maintenance is outage-based and consumes no goods. Grease and MachineCore already meet the policy without it.

## Source changes applied (2026-10-21)

- `create_frontier_expansion_content.mjs`: gases and DiningService removed; Chemical, PowerModule, RecoveredArtifact and ArchiveData recipes added; Polymer and Yellowcake changed; FertilizerWorks, ChemicalWorks and Precision Machine Works recipe lists extended; planned-building recipe check added; Vault cost from `lategameCost`; Reactor and Mission Control menu orders fixed.
- `create_vertical_slice_content.mjs`: DeepProcessor runs DeepAlloy, DeepCoal, DeepOil and DeepUranium; DeepDrill, DeepMine and DeepProcessor costs come from `lategameCost`.
- `create_frontier_expansion_icons.mjs` and `validate_vertical_slice_content.mjs`: removed goods dropped, new recipe ids added.
- `frontier_progression.json`: `plannedBuildings`. `building_construction_costs.json`: planned tiers.
- Stale generated files of the removed goods (Good blueprints, sprite PNGs and their meta files, Recipe.DiningService) were deleted from `src/DeepFrontier/Data`. The authored source SVGs in `src/DeepFrontier/Art/Icons` (Gas, Methane, SulfurGas, ToxicFumes, Radon, DiningService) are unreferenced and were left in place.

Still open:

- `tools/STATUS.md`: record the audit, the cost rule and the chain completion.

## Workbook rows to update

`@oai/artifact-tool` is not available to Claude Code, so the workbook was not rebuilt.

**Buildings sheet** (row, ID): set Width/Length/Height, Science unlock and Build materials from the generated blueprints and the table above.

| Row | ID | Building | Size: workbook → blueprint | Science: workbook → blueprint |
|---:|---|---|---|---|
| 3 | B002 | Fertilizer Works | 3×3×2 → 9×8×13 → 7×5×7 (compaction) → 4×3×5 (second shrink, 2026-11-01) | 180 → 350 |
| 4 | B003 | Greenhouse | 3×4×2 → 9×7×9 | 120 → 600 |
| 22 | B021 | Polymer and Chemical Works | 6×8×4 → 10×9×14 | 1,200 → 4,000 |
| 23 | B022 | Precision Machine Works | 5×6×4 → 11×9×14 | 1,100 → 5,000 |
| 24 | B023 | Water Treatment Plant | 4×5×3 → 12×11×13 | 420 → 1,800 |
| 27 | B026 | Deep Drill | 4×4×5 → 11×9×16 → 7×6×8 (compaction, 2026-10-30) → 4×4×7 (second shrink, 2026-11-01) | unchanged |
| 32 | B031 | Nuclear Reactor | 4×4×5 → 20×15×22 | unchanged |
| 33 | B032 | Uranium Processing Plant | 5×6×4 → 12×11×14 | 12,000 → 9,000 |
| 34 | B033 | Electrolysis Plant | 4×5×4 → 12×9×12 | 9,000 → 10,000 |
| 35 | B034 | Cryogenic Liquefaction Plant | 5×6×4 → 12×11×16 | 11,000 → 12,000 |
| 37 | B036 | Rocket Assembly Hangar | 8×12×8 → 12×12×14 | 15,000 → 18,000 |
| 38 | B037 | Launch Pad | 8×8×4 → 12×12×18 | 18,000 → 20,000 |
| 39 | B038 | Mission Control | 4×4×3 → 12×10×16 | 12,000 → 14,000 |
| 40 | B039 | Radioactive Waste Vault | 4×4×3 → 13×12×12 | unchanged |
| 41 | B040 | Technical School | 4×4×3 → 11×6×14 | 1,800 → 2,200 |
| 42 | B041 | Radioactive Waste Refinery | 5×6×4 → 12×11×12 | 16,000 → 12,000 |
| 43 | B042 | Deep Mine | 5×5×4 → 12×11×16 → 7×6×7 (compaction, 2026-10-30) → 5×5×6 on its vein (second shrink, 2026-11-01) | unchanged |

Other changes to the workbook:

- **Vault (row 40).** Workers 2 → 0, and its Build materials text is a placeholder.
- **Data status / Notes.** On these rows, replace "Mod draft" with "Late-game cost rule T*n* (docs/progression.md); runtime balance untested".
- **Missing Buildings rows.** Add rows for Public Health Lab, Food Packaging Works and Deep Processor.
- **ItemUses sheet.** DeepAlloy rises from 2 to 7 uses. Re-export from `outputs/item-use-audit.json` after the main generation.
- **Progression sheet.** Add a note that concrete is gated at 2,000 science by the Dirt Excavator, and that the nuclear support chain unlocks ahead of the 1,000,000-science reactor.
