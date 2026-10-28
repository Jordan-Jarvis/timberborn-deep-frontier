# Deep Frontier implementation plan

The [2026-10-19 civic/progression revision](civic-progression-revision.md) supersedes earlier service-token and low late-game science proposals below: worker-served multi-food dining, 30-patient hospital care, a stocked neighborhood grocery, wellbeing/education readiness, aluminum, advanced research and new structural blocks/overhangs/bridges/scaffolds. Nuclear research is **1,000,000 science**. New ordinary industrial goods require at least two useful destinations (target three to five); edible foods and rocket-specific final-goal parts may have one. The [item audit](item-use-audit.md) reports the current implementation gaps separately from plans.

Concrete is now an authored construction chain with sandstone/limestone pits, permanent quarries, a crusher, kiln and mixer. Exact values, prerequisites, native API use and remaining runtime tests are maintained in [construction-materials.md](construction-materials.md). Its source catalog is `tools/construction_materials.json`; concrete is obtainable before nuclear construction.

The [reinforced dam and turbine contract](hydroelectric-construction.md) adds concrete levees, overflow dams, reinforced concrete/metal blocks and controlled dam-base generation. Turbines use actual world-water discharge in m³/s and head, with native flow controls and hp output. Advanced building foundations require concrete while the starter concrete chain remains self-bootstrapping.

Target: Timberborn 1.1.2.8, Iron Teeth, with the pinned foundation mods in `tools/installed_dependency_manifests_1_1.json`.

The [current API/Workshop audit](modding-api-audit.md) maps features to exact installed interfaces. Use native attractions for seated dining, Moddable Timberborn for additional enterable/work effects, TimberUi for panels, and evaluate the already installed Scientific Projects + Moddable Recipes for certification/recipe progression. These are integration decisions; runtime completion is recorded in `tools/STATUS.md`.

This document turns the design workbook into an implementation order. The first release should feel like a natural industrial era after the vanilla wonders: more food and civic life on the surface, then automation, authored lower sectors, resource extraction, and the human-history mystery. Gas and fume mechanics are scrapped (user decision, 2026-10-21); see "Scrapped gas and fume branch" below. The foundation mods declared in the manifest are required. Missing dependencies must produce an explicit error; no normalization or fallback behavior is permitted.

## Product boundary

The first release uses one purpose-built map derived from a copied vanilla `.timber` map. Map Transformer is used once during authoring to add a modest lower Z budget. The mod then adds buildings, goods, recipes, progression, logistics adapters, authored resource nodes, and factory progression. Runtime terrain expansion, dig-anywhere caves, gas and fume mechanics, general heat, and maintenance are outside the mod; reactor coolant safety is the one bounded exception.

The player should always be able to answer three questions:

1. What new colony need does this unlock solve?
2. What input, power, worker, storage, and transport chain does it require?
3. What visible project points to the next stage?

The final mystery and the rocket program are reachable through several industrial strategies. Nuclear power accelerates compact, reliable production; it is not a mandatory key for the story ending.

## Architecture

### Data layer

Use the official Timberborn modding project for Unity assets, import, packaging, and example structure. Keep ordinary content in namespaced JSON blueprints:

- `GoodSpec` for new solids, liquids, waste, and fluid proxy goods.
- `BuildingSpec` for workplaces, machines, storage, services, ports, and power nodes.
- `RecipeSpec` for production, extraction, treatment, and power-output recipes.
- `TemplateCollectionSpec` for faction and building-group membership.
- `RangedEffectBuildingSpec` or `ContinuousEffectBuildingSpec` only where an ordinary visitor or area effect is insufficient.

Each Deep Frontier ID should be namespaced, such as `DeepFrontier.DeepDrill` and `DeepFrontier.HighGradeSteel`. Every building row must retain the workbook fields for dimensions, footprint, height, workers, science, bot unlock, materials, stackability, power demand, power output, ports, inputs, outputs, waste, placement, and player cue.

### Runtime layer

Start the code assembly through the standard mod entry point used by the official sample: `IModStarter.StartMod(IModEnvironment)`. Register services through the game `Configurator` and Bindito dependency injection. Use `BottomBarModule` and `EntityPanelModule` only for small, readable controls such as reactor coolant state and source-node information.

The runtime services are:

| Service | Responsibility | First implementation |
|---|---|---|
| `DependencyProbe` | Validate required mod IDs, versions, and capabilities | The foundation mods are declared requirements in `manifest.json`. Missing or incompatible required packages fail visibly. Keep their DLLs external to Deep Frontier. |
| `ProgressionGateService` | Science, material, bot, survey, and evidence gates | Native building science/material gates; Scientific Projects and Moddable Recipes are the preferred candidates for one-time certification and explicit recipe unlocks. Their all-recipes-locked and migration constraints are recorded in the API audit. |
| `TrainingService` | Persistent individual education and advanced-job eligibility | Follow the later civic revision: train actual workers, check readiness at safe work boundaries and show unmet requirements. Basic recovery jobs and reactor safety remain exempt. |
| `SourceNodeService` | Authored coal, oil, ore, uranium, and archive locations | Track explicit map entities or authored node markers. Do not scan every terrain cell. |
| `ExtractionService` | Deep Drill, Pumpjack, mine, and finite source output | Use native persistent Yielders for finite deposits and explicit understructure placement with renewable recipes for permanent seams. Both paths must have a reachable bootstrap. |
| `AreaEffectService` | Optional warning, exposure, machine shutoff, and recovery state | Add only for bounded late hazards or reactor radiation; do not build a global per-tile hazard solver. |
| `PowerAdapter` | Generators, consumers, storage, and power status | Use the vanilla mechanical network and the documented ModdableTimberborn mechanical-system hooks. Do not create a second power system. |
| `TransportAdapters` | Belts, pipes, tubeways, lines, pumps, and teleporters | Validate required dependency versions and register their supported endpoints. Ordinary hauling is an authored early-tier transport choice; conveyor-only factories require their conveyor connection. |
| `NarrativeObjectiveService` | Archive evidence and endgame stages | Prefer staged unlocks, map objects, and evidence goods. Treat a novel quest API as optional research. |
| `RocketProgramService` | Rocket parts, cryogenic fuel, launch sequencing, and mission completion | Track a small number of explicit work orders and launch states; do not simulate orbital physics. |
| `WasteCustodyService` | Persistent radioactive waste, storage locks and refinery routing | Block manual waste deletion and demolition of occupied waste storage. Preserve native inventories and show the reason. Any development-save migration must be explicit; do not silently relocate waste. |
| `StateMigrationService` | Versioned Deep Frontier state | Store only small, versioned source and objective state. Avoid private save-format patches in v1. |

The documented ModdableTimberborn surfaces we will use are spec and template modifiers, building settings, entity tracking, game stats, areas, extra hauler targets, and mechanical-system changes. Game stats can report map dimensions; they do not provide a supported runtime terrain-expansion service. Map Transformer therefore remains an authoring dependency, not a gameplay API.

### Dependency adapters

The installed foundation set is treated as capability providers:

| Dependency | Adapter contract |
|---|---|
| Pump to Tank | Reuse its verified Water/Badwater tank-to-tank behavior. Custom oil/chemical transport uses Timber Pipes' registered Liquid-good inventory contract; do not assume Pump to Tank supports arbitrary goods. |
| Timber Pipes | Expose liquid ports, risers, headlift requirements, network isolation, and outfalls. Core slice uses water, oil, badwater, chemicals, and the rocket-fuel liquids (hydrogen and oxygen gas, liquid hydrogen and liquid oxygen as Liquid goods). |
| Conveyor Belts v2 | Expose solid input/output ports, lifts, splitters, mergers, and belt power demand. A conveyor-only building must stop and explain a missing connection. |
| Powered Tubeway | Treat power transmission through Tubeways as an optional network capability. It is never required for a recipe to exist. |
| Power Lines | Support pylons and beams through their verified mechanical connection contract. Native shafts remain an explicit player construction choice. |
| Flywheels | Detect storage and discharge behavior; do not assume capacity or decay until the installed blueprint profile is extracted. |
| Northforge Solar Panel | Treat the installed 100 hp Iron Teeth producer as an optional generator. |
| Expanded Storage | Use exact storage filters and capacities when present; allow module stacking only through the package's own `BlockObject` rule. |
| Wormhole and Ring Teleporter Stations | Reserve for rare goods, emergency workforce movement, and late logistics. Bulk materials still use belts and pipes. |
| Map Transformer | Author the transformed map before play. Do not call it from normal gameplay. |

All adapters must pass three profiles: supported required dependencies present, a missing requirement with an explicit load error, and a save that already contains connected networks. Never replace an unavailable dependency with different behavior.

## Machine and hazard contracts

Every machine has a simple operational state: `Operational`, `NoPower`, `NoInput`, `OutputBlocked`, `Unsafe`, or `NoWorkers`. The state must be visible in the building panel. No hidden maintenance meter or universal heat system is added.

The nuclear reactor adds three explicit safety states on top of that contract: `CoolantWarning`, `EmergencyShutdown`, and `Meltdown`. Coolant is a continuous operating input, not a one-time construction cost. The reactor keeps a bounded water buffer so a short pipe or pump interruption is recoverable, but an empty buffer while the reactor is operating triggers a visible meltdown event, contaminated outputs, and a recovery lock. This is a reactor-specific safety mechanic, not a general heat simulation.

Power fields are separate:

- **Power demand (hp):** consumed while a recipe or machine operates.
- **Power output (hp):** supplied to the mechanical network.
- **Power role:** Consumer, Generator, Passive / transport, or Review when a dependency genuinely exposes both sides.

Recipe demand mirrors the machine load for line balancing. It is not added a second time to colony totals.

### Scrapped gas and fume branch

Gas, Methane, Sulfur Gas, Toxic Fumes and Radon, gas pockets, detectors and scrubbers are scrapped (user decision, 2026-10-21). Their goods, icons and recipes are removed. Chemistry runs on native inputs instead: Chemical comes from badwater and extract at the Chemical Works, and both Polymer and Yellowcake take Chemical in place of Sulfur Gas, with no gas byproducts. Hydrogen Gas and Oxygen Gas stay. They are ordinary `Liquid` goods between the Electrolysis Plant and the Cryogenic Liquefaction Plant, in separate pipe networks, and carry no hazard simulation. Do not reintroduce a gas proxy or pocket service without a new user decision.

The first content slice is now implemented with the official 1.1 blueprint contracts: `DeepOre` and `DeepAlloy` goods, finite and permanent Deep Ore recipes, a powered `DeepDrill`, a powered `DeepMine`, a powered `DeepProcessor`, a finite `DeepOreSource` marker, and a permanent `DeepOreVein` understructure. The drill consumes one `DeepOre` from the authored source stockpile plus water and outputs the extracted unit to the normal production chain. The mine consumes only water and power, produces four Deep Ore per cycle indefinitely, and is constrained to the authored vein. Custom runtime terrain scanning is not required for this path.

Custom art is part of the same source slice. New Blender collections are exported through the Timbermesh CLI into the mod's `Data` tree; see `docs/asset-pipeline.md` for the reproducible model, icon, texture, and validation command.

## Progression and balance

Current unlock and construction rules, the late-game cost formula and the static reachability audit (`tools/audit_progression.mjs`) are in [progression.md](progression.md).

The workbook is the balancing source of truth. Vanilla 1.1 values establish the footprint, science, material, worker, and hp scale. Deep Frontier should add one major bottleneck per stage rather than raising every number at once.

| Stage | Colony scale | Main additions | Starting balance target |
|---|---:|---|---|
| Survival | 10–30 beavers | Compost, fertilizer, basic storage, park, first clinic | Mostly manual hauling; machines at 0–100 hp; one or two new inputs per chain. |
| Productive settlement | 30–80 | Greenhouse, bakery, fish pond, grocery, water treatment | 20–150 hp consumers; science roughly 300–1,500; surface materials remain dominant. |
| Industrial city | 80–180 | Conveyors, hospital, restaurant, alloy, treatment works, substations | 100–550 hp consumers; factories need belts, storage, workers, and waste outlets. |
| Wonder transition | 180–350 | Polymer, machine cores, oil, long-distance power, teleporter stations | 350–900 hp consumers; science roughly 5,000–15,000; transport becomes the visible bottleneck. |
| Frontier and mystery | 350+ | Authored lower sectors, deep drilling, uranium, nuclear branch, archives | 1,000–10,000 hp consumers per major machine; a nuclear reactor targets 50,000–100,000 hp output in a compact 4x4 footprint. |
| Launch program | 500+ | Rocket components, cryogenic fuels, launch complex, orbital missions | 6,000–25,000 hp electrolysis, liquefaction, assembly, and launch loads; every launch consumes a complete material and fuel chain. |

Balance rules:

1. A large output must require a large footprint, stable inputs, workers or bots, storage, transport, power, and waste handling.
2. Every new good must have a visible use within one stage. Avoid dead-end materials.
3. A dependency improves logistics; it does not silently remove the science or material gate for a Deep Frontier machine.
4. A non-nuclear colony can reach the narrative ending. The tradeoff is more generators, more land, more storage, or lower throughput.
5. A nuclear colony can be compact and reliable, but it must still solve fuel, coolant, waste, transport, and hazard isolation.
6. Generator output scales nonlinearly by fuel tier: approximately 500 hp wood, 5,000 hp coal, 20,000 hp oil (implemented 2026-10-22, docs/progression.md "Power plants"), and the nuclear reactor above them. Each tier must add a new logistics or hazard obligation rather than only increasing a number.

## Education and specialist workforce

Advanced machines require education for the individual worker, following the user's later civic revision in `tools/frontier_progression.json`. A colony certificate alone does not satisfy that requirement. Preserve native employment, work and save systems; inspect their exact extension points before adding eligibility checks. This system is still proposed.

The proposed tiers are:

| Certification | Produced by | Enables | Cost model |
|---|---|---|---|
| Basic Training | School | Entry to advanced study | Persistent worker qualification; basic survival jobs stay available |
| Industrial Training | Technical School or Training Academy | Arc Furnace, Chemical Works, machine-core production, heavy conveyors | Persistent worker qualification |
| Specialist Training | Engineering Academy | Deep Drill, uranium processing, reactor production, cryogenic plants | Persistent worker qualification; cooling and shutdown remain unconditional |
| Flight Training | Mission Control Academy | Rocket Assembly Hangar, launch preparation, mission control | Persistent qualification for the launch crew |

Implementation requirements:

- Schools use ordinary supplies and time to train actual beavers. Persist earned qualifications on those beavers, never as tradable license goods.
- Recheck education and wellbeing at safe work boundaries. Falling wellbeing does not erase education or make a worker abandon a dangerous reactor operation.
- Building panels report the actual qualification and current/required wellbeing. Thresholds need drought-recovery testing before enabling them.
- Food, water, civic care, basic power, basic research/training, and nuclear cooling/shutdown are exempt from wellbeing gates.
- Bot access retains its native science unlock and needs an explicit advanced-job qualification policy; do not assume bots bypass training.

Existing prototype `IndustrialLicense`, `SpecialistLicense` and `FlightLicense` goods are obsolete development content. Remove them through an explicit development-save transition when the replacement is implemented. The item-use audit must not count those token recipes as completed education.

## Why nuclear power exists

Nuclear power is the compact high-density branch. It exists because the late factories and rocket program should demand more power than a few wood or coal generators can conveniently provide. The target is a **75,000 hp reactor**, with a playtest band of **50,000–100,000 hp**, a compact 4x4 footprint, six specialist workers or bots, a high science gate, enriched fuel, continuous coolant water, and radioactive waste.

The generator curve is deliberately nonlinear:

| Fuel tier | Target output | Main obligation |
|---|---:|---|
| Wood | 500 hp | Reliable wood and water supply |
| Coal | 5,000 hp (Coal Power Plant, 5×5) | Coal from the Deep Ore Processor, water and heavy smog (no workers; burns only while the network draws power) |
| Oil | 20,000 hp (Oil Power Plant, 6×6) | Crude oil from the Deep Ore Processor, water and smog (no workers; burns only while the network draws power) |
| Nuclear | 50,000–100,000 hp | Enriched fuel, constant coolant, sealed waste, and meltdown risk |

A 75,000 hp reactor should support a serious district: several 2,500 hp arc-furnace lines, chemical works, deep drills, conveyor trunks, cryogenic plants, and a short launch preparation window. It should not make power irrelevant; the bottlenecks become water throughput, fuel production, waste custody, specialist capacity, and the physical ability to distribute that power.

The nuclear chain is:

`Uranium Ore → Yellowcake → Enriched Fuel → Reactor → Radioactive Waste → Badwater`

The reactor consumes coolant continuously. A six-hour internal water buffer makes a short pump or pipe failure recoverable. At low buffer, the reactor throttles and alarms; at an empty buffer, it enters emergency shutdown. If the player fails to restore coolant before the safety window expires, the reactor enters a bounded meltdown state that produces contaminated water, extra radioactive waste, and a temporary area hazard. There is no global heat simulation, but coolant failure has a concrete, visible consequence.

Radioactive waste is persistent. It cannot be manually deleted, and a warehouse or vault containing it cannot be demolished until the waste is moved or processed. The `Radioactive Waste Refinery` converts waste, chemicals, and water into badwater and recovered minerals. Badwater then requires ordinary treatment, storage, transport, or controlled discharge. If a save or dependency failure would otherwise strand the good, the migration layer moves it into a locked emergency vault rather than deleting it.

Nuclear research should require deep drilling, chemical processing, specialist education, advanced power, and a meaningful evidence or science milestone. It is a reward for a mature industrial system and a way to compress production districts, not an early shortcut. A renewable colony can still reach the launch program, but it needs more land, more generators, more storage, and more power-line capacity.

## Rocket program and the final wonders

The final wonders should be a launch program rather than a single building that grants a permanent victory bonus. Standard vanilla wonders mark the transition into the industrial frontier. The launch program is the final project that asks the colony to coordinate every major system: food and workers, refined materials, conveyors, pipes, power, storage, science, and waste.

The first implementation uses explicit work orders instead of a new construction simulation:

| Work order | Inputs | Output / purpose | Main pressure |
|---|---|---|---|
| Structural Airframe | High-grade Steel, Alloy, Treated Glass, Polymer | Rocket body and tank sections | Heavy conveyor throughput and large refined-material inventory |
| Propulsion Package | Alloy, Machine Cores, Polymer, Precision Parts | Engines and turbopumps | High power, precision manufacturing, and scarce machine cores |
| Avionics and Guidance | Electronics, Machine Cores, Archive Data | Guidance computer and flight systems | Science, archive evidence, and high-value goods |
| Water Purification | Water, Filter Media | Pure Water for electrolysis | Treatment capacity and clean-water demand |
| Electrolysis | Pure Water, power | Hydrogen Gas and Oxygen Gas | Large continuous hp demand and water throughput |
| Cryogenic Liquefaction | Hydrogen Gas, Oxygen Gas, Cryocoolant, power | Liquid Hydrogen and Liquid Oxygen | High hp, isolated pipe networks, and cryogenic storage |
| Cryogenic Storage | Liquid Hydrogen, Liquid Oxygen, power | Launch-ready fuel inventory | Dedicated tanks and a clear power-loss failure state |
| Launch Preparation | Complete rocket, liquid fuels, guidance, power | Armed rocket | Assembly footprint, workers, safety clearance, and launch power |

Cryogenic fuel is intentionally a complete production chain. Water is purified, split, cooled, liquefied, stored, and finally consumed by a launch. Hydrogen and oxygen must use separate pipe networks and separate tanks; a mixed network is invalid and should fail visibly. Cryogenic tanks do not introduce a general heat system. They require power to accept and hold launch fuel; if power is lost, the tank stops accepting fuel and can vent a bounded amount after its buffer is exhausted.

The first launch balance target is:

- Launch Complex: 8x12 or 10x12, conveyor-fed solids, pipe-fed cryogenic fuel, 8–12 workers or bots.
- Electrolysis Plant: about 6,000 hp while operating.
- Cryogenic Liquefaction Plant: about 10,000 hp while operating.
- Cryogenic Tank: about 1,000 hp per active tank.
- Launch sequence: about 25,000 hp for a short, visible preparation window.
- Per-launch materials: roughly 600–900 refined structural units, 80–140 Machine Cores or equivalent precision parts, 150–300 Polymer, and a large electronics/guidance package. These are initial ranges for playtesting, not final package facts.
- Per-launch fuel: enough Liquid Hydrogen and Liquid Oxygen to make the cryogenic chain matter over several in-game days, rather than a single instant recipe.

The launch complex should have three mission tiers:

1. **Orbital Observatory:** the first launch reveals human orbital records and provides the next evidence about the badwater source.
2. **Recovery Probe:** a second launch retrieves a rare data package or material recipe and expands the industrial endgame.
3. **Long-Range Beacon or Ark:** the final launch completes the colony's chosen ending. It can transmit a signal, preserve the archive, or prepare a future settlement without requiring a beaver to leave the map.

Each mission consumes a complete rocket and fuel load. A launch is therefore a colony-scale decision, not a repeatable free reward. The story ending checks mission evidence and colony capability; it does not check `HasNuclearReactor`.

## Player stories

### The civic builder

The colony begins with farms, compost, fertilizer, a greenhouse, and better food. A clinic, grocery store, restaurant, and parks improve well-being and create demand for reliable food and clean water. This player uses water wheels, steam, solar, and Flywheels instead of nuclear. The colony reaches the Human Archive through civic growth and evidence production, then builds an Orbital Observatory with a larger renewable power district and more storage instead of a reactor.

### The automation engineer

The player makes conveyors and storage the first major investment after basic food. Arc furnaces, alloy, machine cores, Power Lines, and Flywheels create a compact industrial district. Nuclear research then supports two furnace lines, chemical processing, cryogenic fuel production, and deep drilling from one reliable power district. The endgame route is efficient and dense, but fuel and waste logistics become the price of that density. This player is most likely to complete the Recovery Probe and Long-Range Beacon missions.

### The underground prospector

The player stabilizes the surface, builds a survey station, opens an authored lower sector, and connects it with a lift, pipes, and power. A Deep Drill brings up deep ore, which the Deep Processor turns into coal, crude oil, uranium ore and deep alloy. This route reaches the mystery by exploring source sites and recovering evidence, then decides whether uranium is worth the nuclear branch or whether a larger renewable grid is safer.

### The badwater remediator

The player treats badwater as an industrial input. Treatment works, filter media, clean water, chemical recovery, and controlled waste outlets allow a large surface city without nuclear power. The colony earns archive evidence by tracing contamination and rebuilding human treatment infrastructure, then uses purified water and a large mixed renewable grid for a Beacon launch. This route has lower peak power but turns pollution into a source of materials and story clues.

These stories share the same core gates—food, water, workers, science, materials, storage, and transport—but emphasize different bottlenecks. All can reach the launch program; the practical difference is whether the colony pays with land and storage, or with uranium processing and waste isolation.

## Implementation milestones

### Shared building walkways

All intended decks must be traversable, and railings must adapt to valid adjoining paths. Keep rail nodes, grid routes, collision and support bindings consistent at source. See [building-walkways.md](building-walkways.md) for verified native APIs. Industrial and civic blueprints now activate the reusable walkway system, with actual walking, selective rail openings, vanilla stairs, supported platforms and save/reload verified for several buildings. `tools/STATUS.md` identifies the tested layouts. Remaining rotations and cross-building seams need their own tests.

### Milestone 0: project and dependency shell

- Create the namespaced mod assembly and manifest.
- Load one `GoodSpec`, one `BuildingSpec`, and one `RecipeSpec`.
- Start through `IModStarter` and register a small game-context configurator.
- Probe all foundation mod IDs without taking hard references.
- Acceptance: the mod loads with its declared dependency profile; missing required packages produce an explicit load requirement instead of hidden substitutes.

### Milestone 1: vertical slice

- Use one transformed test map with one lower sector.
- Add Deep Drill, Deep Ore, one authored source node, and one surface processor.
- Add one belt endpoint, one pipe loop, and one power connection.
- Acceptance: drill output reaches the surface processor through the declared dependency APIs; missing or incompatible required dependencies fail explicitly; save/reload preserves source and machine state.

### Milestone 2: surface progression

- Add compost, fertilizer, greenhouse, fish pond, bakery, clinic, grocery, restaurant, park, and the first School.
- Connect each building to an existing need, food chain, or production bottleneck.
- Acceptance: a new player can discover the next building from needs, storage, or production feedback.

### Milestone 3: industrial logistics

- Add alloy, polymer, treatment, machine core, substations, and fixed factory ports.
- Add Technical School or Training Academy with persistent individual Industrial Training.
- Validate Conveyor Belts v2, Timber Pipes, Power Lines, Powered Tubeway, Pump to Tank, and Flywheels one adapter at a time.
- Acceptance: required dependency endpoints, inventories, queues and network connections survive save/reload, with clear interruption behavior when power or inputs are unavailable.

### Milestone 4: frontier and nuclear branch

- Add oil, coal, uranium, fuel processing, reactor, locked waste storage, waste refinery, reactor radiation states, and archive evidence.
- Add Specialist Training capacity and explicit Reactor, Cryogenic, and Launch workforce gates.
- Test the 50,000–100,000 hp reactor band against the heavy industrial package and coolant throughput.
- Acceptance: one compact reactor supports a meaningful district, cannot erase water/fuel/waste bottlenecks, enters emergency shutdown when coolant is missing, and produces a bounded meltdown state if the safety buffer is exhausted.

### Milestone 5: rocket program

- Add Structural Airframe, Propulsion Package, Avionics and Guidance, Pure Water, Hydrogen Gas, Oxygen Gas, Cryocoolant, Liquid Hydrogen, Liquid Oxygen, cryogenic tanks, Launch Complex, and Mission Control.
- Add three explicit launch work orders with separate evidence rewards.
- Test the launch sequence with nuclear power, renewable power plus storage, and a mixed grid.
- Acceptance: electrolysis, liquefaction, cryogenic storage, assembly, and launch consume visible high-power loads; every launch consumes materials, workers, power, and fuel; a failed launch preparation leaves recoverable inputs; no launch requires a global heat or maintenance simulation.

### Milestone 6: narrative completion

- Add human archive buildings, evidence goods, staged objectives, and final source reveal.
- Acceptance: all four player stories can reach at least one final mission with different power and logistics mixes.

## Verification and reverse engineering

Use ordinary JSON and documented services first. Harmony 2.4.1 is pinned in the development profile because several 1.1 foundation mods already require it, but Deep Frontier should add a Harmony patch only after a test demonstrates that a required adapter cannot be built through public data or supported hooks. Keep each patch in a named adapter with an explicit compatibility check; reject unsupported versions rather than silently changing behavior. Use a .NET decompiler for managed game/dependency assemblies and Ghidra when native-code inspection is needed. The first inspection targets are exact dependency blueprints, transport connection behavior, custom-fluid acceptance, and save-state behavior. Runtime terrain expansion remains a research branch until the content-based version is stable.

The completion gate for each milestone is a playable save, a dependency-present/absent test, a power and throughput check against the workbook, and a reload test. No feature is considered complete because its building appears in the menu; it must produce, consume, transport, gate, and fail in a way the player can understand.

