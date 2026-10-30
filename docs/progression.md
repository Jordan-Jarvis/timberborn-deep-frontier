# Progression and construction balance

Status 2026-10-21. These are the rules for unlock order, construction cost and chain reachability, with the static audit that checks them. They are authored balance plus static checks. None of this has been played or tested in game. `tools/STATUS.md` holds the runtime verification state.

## Tools

| Tool | Purpose |
|---|---|
| `node tools/lategame_costs.mjs [--check\|--write]` | Prints the late-game cost rule for each integrated building. `--write` rewrites the catalog rows the rule owns; `--check` fails when a row differs from the rule. |
| `node tools/audit_progression.mjs [dataRoot]` | Static progression audit of the generated data (vanilla Iron Teeth plus Deep Frontier). Writes `outputs/progression-audit.json` and exits 1 on any failure. |
| `node tools/audit_item_uses.mjs` | Existing check that every new good has enough downstream uses. It does not check whether a good can be produced. It counts recipes appended to vanilla buildings, bot assembly and bot maintenance (see Second uses). |
| `node tools/validate_bot_upkeep.mjs [dataRoot]` | Static check of bot maintenance and the industrial bot (catalog, runtime records, generated data, automation declarations). |

### Reachability model (`audit_progression.mjs`)

- **Primary goods.** A vanilla good that no vanilla recipe produces is primary (gathered, grown, pumped or scavenged). Primary goods are available at science 0.
- **Map-sourced goods.** `MAP_SOURCES` lists goods that a workplace gathers without a recipe:
  - ScrapMetal: Scavenger Flag.
  - DeepOre: Deep Drill on the finite DeepOreSource marker.
  - Sandstone and Limestone: the pits.
  - FreshFish: shore fishing at the Gatherer Flag.
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
  - a building that unlocks before one of its construction goods, or before any of its recipes can run;
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
- **Gates:** `lategameGates` adds explicit goods that prove the previous stage. The gates are DeepMine's 20 DeepAlloy, which keeps the permanent mine behind the finite drill phase; the Greenhouse's 30 Compost (bed soil from the Fertilizer Works); and the Nuclear Reactor's 20 EnrichedFuel (first core load) and 10 RecoveredMinerals (waste refining must work before the reactor). See Second uses.

| Tier | Science | Stage | Concrete / ground cell | Per 100 built cells |
|---|---|---|---:|---|
| T1 | ≤ 600 | Productive settlement | 0 (pre-concrete) | 30 Plank, 12 Gear, 6 Metal Block |
| T2 | ≤ 3,000 | Industrial city | 0.75 | 25 Plank, 10 Gear, 8 Metal Block |
| T3 | ≤ 8,000 | Wonder transition | 1 | 20 Plank, 12 Gear, 12 Metal Block, 5 Treated Plank |
| T4 | ≤ 30,000 | Frontier | 1.5 | 15 Metal Block, 8 Gear, 8 Treated Plank, 3 Deep Alloy |
| T5 | above | Launch program and reactor | 3 | 10 High-grade Steel, 8 Alloy, 2 Machine Core, 8 Metal Block |

Each tier uses goods the chain can already make at that stage. T4 uses the frontier's own refined metal, DeepAlloy, which also gives DeepAlloy real construction uses. T5 uses the premium metals. The nuclear reactor is the largest building at 2,543 built cells and 261 ground cells, so it comes out at 1,500 units. That is 2.4 times the next building, which makes it the endgame showpiece through size alone, with no special multiplier.

| Building | Tier | Built / ground cells | Previous (prototype) | Rule |
|---|---|---:|---|---|
| FertilizerWorks | T1 | 350 / 46 | 40 Plank, 20 Gear, 15 MB | 105 Plank, 40 Gear, 20 MB |
| Greenhouse | T1 | 154 / 42 | 40 Plank, 20 Gear, 15 MB | 45 Plank, 20 Gear, 10 MB, 30 Compost (gate) |
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

## Late-game power rule (2026-10-29)

User request: the endgame buildings must need much more power ("smog scrubber only taking 200? more like 2000"). Every Deep Frontier power consumer (`MechanicalNodeSpec.PowerInput` > 0) unlocked at 2,000 science or more draws at least

    floor(science) = 2,000 × (science / 2,500)^0.75 ≈ 5.65 × science^0.75

rounded to the nearest 100 hp below 10,000 and the nearest 1,000 hp from 10,000 up, so the 2,500-science Smog Scrubber draws exactly 2,000 hp. A building draws `max(authored base, floor)`: the authored figures stay in their catalogs and generators, and every generator that writes a consumer's `PowerInput` applies `scaledPower(id, base, science)` from `tools/lategame_costs.mjs` (constants in `building_construction_costs.json` `lategameRule.power`), as authored costs go through `scaledCost`. Descriptions that state a power figure take the generated value. `tools/validate_power_rule.mjs` (a validate_all check) fails on a consumer below its floor that is not exempt, and on an exemption that names no such consumer or is no longer needed.

Exempt (`lategameRule.power.exempt`): the Deep Well (its draw follows the boost slider at runtime, 1,667 hp per step, 10,000 hp at 6×) and the Reactor Charging Bay (5,000 hp, the user's explicit choice). Generators are outside the rule. Buildings below 2,000 science keep their authored draw.

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
| Deep Well | 30,000 | 13,000 | 1,667–10,000 | unchanged (exempt) |
| Rocket Assembly Hangar | 50,000 | 19,000 | 12,000 | 19,000 |
| Launch Pad | 80,000 | 27,000 | 25,000 | 27,000 |
| Uranium Processing Plant | 200,000 | 53,000 | 5,000 | 53,000 |
| Reactor Charging Bay | 250,000 | 63,000 | 5,000 | 5,000 (exempt) |
| Radioactive Waste Refinery | 500,000 | 106,000 | 8,000 | 106,000 |

With the same change the generators were buffed (authored outputs, fuel unchanged): Coal Power Plant 5,000 → 25,000 hp, Oil Power Plant 20,000 → 90,000 hp, Reinforced Hydro Turbine 9,600 → 40,000 hp (rated output at its unchanged 3 m³/s and 16-layer caps; docs/hydroelectric-construction.md) and Nuclear Reactor 800,000 → 1,000,000 hp (still scaled by `1 − heat` at runtime).

## Science curve (2026-10-29)

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
| CryogenicTankFarm | Pipe-fed Liquid storage for LiquidHydrogen or LiquidOxygen (one selected good per farm, 2,000 capacity) | 10x10x8 | 0 | 6,500 hp (authored 1,000; power rule) | 12,000 | T4 | Storage 90 |

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
| FreshFish | gathered @ GathererFlag | 0 | 0 |
| GuidanceComputer | GuidanceComputer @ MissionControl | 14,000 | 46,320 |
| HighGradeSteel | HighGradeSteel @ SteelMill (planned) | 4,500 | 10,800 |
| HydrogenGas | Electrolysis @ ElectrolysisPlant | 10,000 | 18,450 |
| IndustrialLicense | IndustrialLicense @ TechnicalSchool | 2,200 | 6,150 |
| JuvenileFish | JuvenileFish @ FishHatchery | 600 | 1,350 |
| Limestone | gathered @ LimestonePit | 300 | 300 |
| LiquidHydrogen | Liquefaction @ CryogenicLiquefactionPlant | 12,000 | 36,200 |
| LiquidOxygen | Liquefaction @ CryogenicLiquefactionPlant | 12,000 | 36,200 |
| Lubricant | Lubricant @ ChemicalWorks | 4,000 | 11,200 |
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
- Oil: the same processor's `DeepOil` (1 Deep Ore + 3 Water → 6 Crude Oil per 2 h, doubled on 2026-10-27). There is no refinery and no refined fuel good, so the plant burns crude oil directly, competing with polymer and lubricant at the Chemical Works. One processor on oil makes 3 Crude Oil per working hour, so one plant at full load (2 per hour) needs 0.67 processors during the processor's working hours; running the plant through the night as well takes 48 Crude Oil a day.

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
| Lubricant | Cryocoolant | Servo bot limbs (below); bot maintenance | Precision Machine Works (5,000); 16 hazardous workplaces | 4,000 | Servos and bot upkeep. |
| PowerModule | Enriched fuel | Industrial bot battery pack (below) | vanilla Bot Assembler (750) | 5,000 | Battery for the fast-built bot. |
| FishOil (already two uses) | CannedFish, Lubricant | Bot maintenance, as a cheaper blend | 16 hazardous workplaces | 900 | A cheap oil for bots. |

Recipes that share a product with another recipe in the same building get their own display names: activated carbon filters, chemical from brine, aquaponic kohlrabi and fish, spent fuel reprocessing, waste refining with contaminated water, and sludge vitrification. The native recipe dropdown (`ManufactoryDropdownProvider`, 1.1.2.8) finds the chosen recipe by `DisplayLocKey` with `SingleOrDefault`, so two recipes in one building with the same key would throw. `audit_progression.mjs` now fails on this (`recipe-display-key-collision`).

**Greenhouse 500 → 600 science.** This matches the Fish Hatchery, so aquaponics can run when the Greenhouse unlocks. It stays in tier T1.

### Bots

Bots already wear out 3–5× faster in heavy industry (`workforce_risks.json`). Bots now also give late-game goods real uses:

- **Late-game bot parts** at the Precision Machine Works (5,000). These are ordinary recipes for the vanilla part goods:
  - Reinforced bot chassis: 1 Alloy + 1 Polymer + 1 Flux → 2 BotChassis (4 h).
  - Servo bot limbs: 1 MachineCore + 1 Lubricant + 2 MetalPart → 4 BotLimb (4 h).
  - Bot cortex: 1 Electronics + 1 Polymer → 2 BotHead (4 h).

  The Bot Part Factory needs 54 worker-hours for one bot's parts. These recipes need 8.
- **Industrial bot** at the vanilla Bot Assembler: 1 BotChassis + 4 BotLimb + 1 BotHead + 1 PowerModule → one bot in 24 h. The native recipe takes 72 h.
  - It is added by a same-path patch, `{"ManufactorySpec": {"ProductionRecipeIds#append": ["IndustrialBot"]}}`.
  - It builds the same Iron Teeth bot. The native `BotManufactory` spawns a bot when any assembler recipe finishes, and `BotFactory.Load` takes the faction's single template with `TemplateService.GetSingle<BotSpec>()`. A second bot template is therefore impossible without patching the game. A faster recipe for the same bot is the clean route, and vanilla bots stay untouched.
  - Known caveat: the recipe is visible from the assembler's 750-science unlock, but the PowerModule only exists from 5,000. `audit_progression.mjs` reads vanilla patches now and reports this as a warning.
- **Bot maintenance.** `FrontierBotMaintenanceSpec` goes on all 16 open workplaces that have bot wear.
  - The building keeps a second native inventory for maintenance oil: 10 Lubricant and 10 FishOil. It is stocked only while a bot is assigned, so beaver crews never tie up oil.
  - A bot inside whose dose has run out takes one unit, Lubricant first. For 24 hours of wear, its wear multiplier is multiplied by 0.5 for Lubricant or 0.75 for FishOil, never below 1×. For example, the uranium plant drops from 5× to 2.5× with Lubricant or 3.75× with FishOil.
  - The dose stays with the bot and is saved with it (`BotWear`).
  - Native `ManufactoryHaulBehaviorProvider` and `FillInputWorkplaceBehavior` fill every enabled input inventory of the building, so no new hauling code is needed.
  - Runtime: `BotMaintenance.cs` and `BotUpkeepPanels.cs`, with the dose in `BotWear.cs`.
- **Audit changes.**
  - `audit_item_uses.mjs` counts bot assembly ("Bot assembly: bots") as one destination, and maintenance oils ("Bot maintenance") as one destination for all workplaces.
  - Both audits read recipes appended to vanilla templates.
  - `tools/validate_bot_upkeep.mjs` checks the catalog, the runtime records and localization, the generated data and the automation declarations.

The meltdown agent's reactor maintenance is outage-based and consumes no goods. Lubricant and MachineCore already meet the policy without it.

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
| 3 | B002 | Fertilizer Works | 3×3×2 → 9×8×13 | 180 → 350 |
| 4 | B003 | Greenhouse | 3×4×2 → 9×7×9 | 120 → 600 |
| 22 | B021 | Polymer and Chemical Works | 6×8×4 → 10×9×14 | 1,200 → 4,000 |
| 23 | B022 | Precision Machine Works | 5×6×4 → 11×9×14 | 1,100 → 5,000 |
| 24 | B023 | Water Treatment Plant | 4×5×3 → 12×11×13 | 420 → 1,800 |
| 27 | B026 | Deep Drill | 4×4×5 → 11×9×16 | unchanged |
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
| 43 | B042 | Deep Mine | 5×5×4 → 12×11×16 | unchanged |

Other changes to the workbook:

- **Vault (row 40).** Workers 2 → 0, and its Build materials text is a placeholder.
- **Data status / Notes.** On these rows, replace "Mod draft" with "Late-game cost rule T*n* (docs/progression.md); runtime balance untested".
- **Missing Buildings rows.** Add rows for Public Health Lab, Food Packaging Works and Deep Processor.
- **ItemUses sheet.** DeepAlloy rises from 2 to 7 uses. Re-export from `outputs/item-use-audit.json` after the main generation.
- **Progression sheet.** Add a note that concrete is gated at 2,000 science by the Dirt Excavator, and that the nuclear support chain unlocks ahead of the 1,000,000-science reactor.
