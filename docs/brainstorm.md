# Brainstorm: Deep Frontier

## Core loop

1. Wonders unlock the Deep Frontier instead of ending the technology arc.
2. Surveyors reveal finite underground strata and hazards.
3. Drills consume power, water, lubricant, and worker access; deeper layers increase yield and risk.
4. Extracted materials feed a staged industrial chain: coal/ore -> refined metals and chemicals -> advanced machines -> nuclear and geothermal systems.
5. Waste streams matter. Badwater can be produced by specific processes, stored, treated, or accidentally released.
6. Underground settlements are space-efficient but require lighting, water, access, and evacuation routes. Gas and ventilation are optional hazard modules. Use authored lower sectors and shafts first; dynamic terrain editing is an optional research branch.

## Candidate strata and hazards

- Shallow: clay, limestone, iron, coal, groundwater.
- Mid: copper, sulfur, oil pockets, methane, unstable caverns.
- Deep: uranium-bearing rock, geothermal heat, toxic gas, high-pressure aquifers, ancient infrastructure.
- Endgame: sealed human facilities and a traceable badwater source; the mystery is revealed through recoverable logs, machines, and map changes.

## Systems to prototype

- Resource vein entity with depletion, regeneration rules, and map markers.
- Drill head, bore casing, pump, gas detector, and emergency vent.
- Authored lower-sector rooms with occupancy, lighting, and area effects; defer dynamic cave excavation until the engine path is proven.
- Optional later: fumes and gases represented as fluid-engine goods in tanks/pipes, with local pocket inventories for accumulation in low areas.
- Pipe, conveyor, tubeway, power-line, and teleporter adapters.
- Pollution ledger: every recipe declares inputs, outputs, waste, and cleanup path.
- Map expansion contract: new pre-authored sectors or map variants unlock when a settlement reaches infrastructure and survey milestones; never resize or invalidate an existing save.

## Balance principles

Make the first wonder a capability unlock, not a victory screen. Gate deep drilling behind logistics and maintenance rather than a single research click. Give every hazardous resource an early safe use and a late efficient use. Make automation reduce labor while increasing power, water, and waste-management pressure.

## Factory and automation systems

### Machine families

- **Surveying:** seismic scanner, borehole sampler, gas detector, pressure probe, vein mapper.
- **Extraction:** rotary drill, hammer drill, thermal drill, pumpjack, methane well, uranium cutter.
- **Material handling:** bucket elevator, screw conveyor, belt lift, pipe riser, pneumatic tube, freight lift, teleporter terminal.
- **Processing:** crusher, washer, separator, smelter, refinery, chemical plant, centrifuge, reactor, waste vitrifier.
- **Utilities:** boiler, turbine, flywheel bank, transformer, substation, compressor, cooling tower, oxygen plant, ventilation fan.
- **Automation:** sensor block, timer, logic gate, priority splitter, buffer controller, recipe scheduler, emergency shutoff.
- **Construction and maintenance:** machine shop, parts printer, repair bay, spare-parts depot, robotic service gantry.

Every machine should expose the same core contract: inputs, outputs, power draw, noise, failure mode, footprint, and connection ports. This lets the factory planner and automation systems reason about machines generically.

### Transport architecture

Use a layered logistics model instead of one universal transport method:

1. **Local:** beavers, carts, short belts, pipes, and tubeways.
2. **Vertical:** lifts, bucket elevators, riser belts, pipe shafts, and powered hoists.
3. **Regional:** conveyors, trains or long-haul lines if a future dependency supports them, and teleporter stations.
4. **Bulk fluids:** pipes with pressure, contamination, and leak state; gas transport is an optional late branch.
5. **High-value items:** protected containers and teleporter links with throughput limits.

Underground extraction should create a real logistics problem: the drill may be productive long before the settlement has enough lift capacity, power, and access capacity to support it. Ventilation is an optional hazard layer.

### Hazards

Gas, pressure, heat, and cave-in systems are late optional branches. Do not block the core automation loop on them; the first bounded hazard should be reactor radiation or badwater isolation.

- **Cave-ins:** unsupported excavations accumulate structural stress; supports and staged excavation reduce risk.
- **Gas:** methane, carbon monoxide, sulfur compounds, radon, and oxygen depletion; detectors should trigger alarms and automatic shutdowns.
- **Pressure:** deep water and gas pockets can rupture casings, flood shafts, or force emergency venting.
- **Heat:** geothermal zones and refineries require cooling and can damage nearby buildings.
- **Badwater:** some recipes create it deliberately; leaks contaminate water networks and soil.
- **Fire and explosion:** methane, dust, hydrogen, and refinery vapors need isolation, venting, and spark-safe equipment.
- **Radiation:** uranium processing and reactor failures create zone-based exposure, contamination, and cleanup requirements.
- **Noise and vibration:** heavy machinery reduces nearby well-being and can increase cave-in risk.
- **Supply-chain failure:** neglected maintenance should degrade throughput before causing catastrophic failure.

Hazards should be readable and preventable. The player should be able to see the cause, receive a warning, and build a mitigation path before a disaster occurs.

### Factory planning and control

- Add machine groups, production priorities, and recipe quotas.
- Let players set stock targets and overflow destinations.
- Add dashboards for throughput, queue time, power, heat, waste, and maintenance.
- Support circuit-like control: gas detector -> shutoff valve; tank level -> pump; flywheel charge -> machine schedule; badwater sensor -> isolation gate.
- Use buffers deliberately. A full downstream buffer should slow or stop upstream machines instead of silently deleting output.
- Model bottlenecks explicitly so a player can improve one lift, pipe, belt, or machine without rebuilding the entire factory.

### Underground-to-surface progression

Start with manual hauling and a simple shaft. Progress through:

1. rope lift and timber supports;
2. powered hoist and bucket elevator;
3. vertical conveyor and pipe riser;
4. multi-level freight lift with loading bays;
5. automated shaft control with sensors and priority routing;
6. teleporter or high-capacity transfer station for late-game materials.

Each tier should solve a specific throughput or safety problem and consume different resources, so the transport game remains meaningful after the first wonder.

### Production-chain examples

- Coal -> coke oven -> steel -> machine parts -> drills and lifts.
- Crude oil -> distillation -> fuel, polymers, lubricant, and badwater byproducts.
- Sulfur + water -> acid -> ore leaching -> refined metals and contaminated water.
- Uranium ore -> milling -> yellowcake -> fuel fabrication -> reactor power and radioactive waste.
- Geothermal brine -> heat exchanger -> steam turbine -> mineral concentrate and hot brine.
- Biomass -> gasifier -> syngas -> chemicals, with tar and badwater requiring cleanup.

### Save, failure, and performance constraints

- Every machine, buffer, hazard, and underground sector needs deterministic save/load state.
- Use event-driven updates for sensors and logistics where possible; avoid per-frame scans across every belt item.
- Cap factory simulation detail at distance and aggregate flows when the camera is far away.
- Make failures recoverable: isolate, repair, purge, rebuild, or abandon a sector.
- Keep the base mod playable without optional transport dependencies, then add adapters for the named mods.

## Above-ground progression and natural colony arc

The expansion should extend Timberborn's existing progression rather than jump straight from wonders to nuclear industry. The base game already centers survival on water, food, crops, housing, power, transport, automation, well-being, and monuments. Version 1.1 adds statistics, new watertight buildings, attractions, monuments, and workwear, so the mod should use those systems as its foundation.

### Stage 1: survival and dependable agriculture

Add crop rotation, composting, mulch, basic irrigation controls, seed storage, farm tools, and simple fertilizers made from waste, algae, or compost. These should improve yield and drought resilience without making early farming obsolete. New foods should begin as modest variety bonuses rather than instant high-efficiency meals.

### Stage 2: settlement quality and food variety

Add kitchens, bakeries, preserves, smokehouses, oil presses, herbalists, dairies or plant-protein kitchens, and beverage production. Recipes should consume different crops so the player is rewarded for diversified farming. Tie advanced food to existing Nutrition and Well-Being needs rather than adding an unrelated happiness meter.

Add above-ground amenities that make industrial districts livable: bathhouses, dining halls, markets, schools, clinics, parks, music venues, workshops, viewing platforms, and seasonal festivals. Industrialization should create a reason to invest in worker housing, decoration, walkability, and services.

### Stage 3: farm and factory integration

Introduce fertilizer plants, irrigation pumps, greenhouses, seed laboratories, crop dryers, grain mills, oil refineries, food factories, and cold storage. Fertilizer should have tradeoffs: higher output, water or power demand, soil depletion if overused, and possible badwater or chemical waste. Let farm output feed factories and let factory waste return to agriculture through safe treatment loops.

Use production statistics to expose throughput, labor, power, water, crop yield, spoilage, and waste. This makes automation valuable before the underground phase begins.

### Stage 4: advanced surface infrastructure

Add district-scale utilities: substations, water-treatment plants, food distribution hubs, warehouses with filters, freight elevators, overhead conveyors, loading bays, and automated delivery routes. The player's first large factory should be possible entirely above ground, with underground extraction becoming a later expansion rather than the first major industrial challenge.

### Stage 5: wonders as industrial unlocks

Wonders should unlock new capabilities instead of ending the progression. Each wonder can specialize:

- Agricultural wonder: controlled climate, advanced seed genetics, and high-efficiency fertilizer.
- Industrial wonder: advanced alloys, machine tools, robotics, and high-capacity logistics.
- Social wonder: large-scale education, healthcare, arts, and settlement-wide well-being bonuses.
- Environmental wonder: water purification, badwater treatment, soil restoration, and climate stabilization.
- Exploration wonder: surveying, deep drilling, map expansion, and the human-history arc.

Only after these surface systems are mature should the player need deep drilling, underground settlements, nuclear materials, and the source of badwater.

### Design rule

Every new building should answer one of three questions: does it make the colony more resilient, does it create a more interesting production decision, or does it improve the quality of life of the beavers who operate the system? If it does none of those, it should not be added yet.

## Megafactories and conveyor-only production

A small number of landmark factories should require conveyor logistics for every solid input and output. They are intentionally too large and too hungry for ordinary hauling to be practical. Their purpose is to make the player design a dedicated industrial district.

### Rules for conveyor-only buildings

- Solid inputs must arrive through conveyor ports; workers cannot hand-carry them into the building.
- Solid outputs leave through conveyor ports; internal storage is limited to a short startup buffer.
- Fluids use dedicated pipe ports with pressure and flow limits.
- Power demand is high enough to require substations, flywheels, or dedicated generators.
- Noise, vibration, waste, and maintenance create a reason to place the factory away from housing.
- The building exposes throughput, queue time, input starvation, output blocking, and power quality in the statistics panel.
- A failed belt, full output buffer, or unstable power grid should reduce production gracefully before causing a shutdown.

### Candidate landmark factories

- **Arc Furnace Complex:** iron, coal, flux, and electricity into high-grade steel, alloys, and slag.
- **Polymer and Chemical Works:** crude oil, water, sulfur, and power into polymers, lubricants, resins, and contaminated wastewater.
- **Precision Machine Works:** refined metals, polymers, gears, and science into machine parts, robotics components, and drill heads.
- **Food Synthesis Plant:** grains, oils, algae, sugar, and power into high-density rations, medical foods, and long-shelf-life emergency stores.
- **Fertilizer and Soil Lab:** compost, ammonia, phosphates, water, and electricity into crop fertilizer, seed treatments, and soil restorers.
- **Isotope Processing Plant:** uranium ore, coolant, chemicals, and extreme power into reactor fuel, medical isotopes, and radioactive waste.
- **Megawatt Storage Works:** advanced metals, batteries, and power into grid-scale storage modules for droughtproof industry.

### Valuable outputs and their consequences

Each megafactory should create at least one product that changes the colony's capabilities, not just a more efficient version of an existing good. Examples include:

- High-grade alloys that unlock deep drilling and heavy lifts.
- Polymer seals that prevent pipe leaks and enable high-pressure systems.
- Machine cores that unlock autonomous factories and robotic maintenance.
- Medical foods and treatments that improve health and work uptime.
- Soil restorers that reclaim depleted or contaminated farmland.
- Reactor fuel that supports enormous power production but creates radioactive waste.
- Grid storage modules that stabilize industrial power through droughts.

The valuable output must be constrained by a real bottleneck: rare inputs, enormous electricity demand, cooling water, hazardous waste, belt throughput, worker access, or a specialized workforce. The goal is a strategic factory district, not a universal upgrade that makes every earlier building irrelevant.

### District design challenge

A megafactory district should need:

- Receiving yards and belt splitters
- Large warehouses and buffer silos
- Dedicated substations and flywheel banks
- Water treatment and waste handling
- Maintenance access and worker facilities and storage
- Worker housing, food, healthcare, and recreation nearby
- Isolation gates for fires, gas leaks, badwater, or radiation

This makes the factory a colony-scale project that visibly changes the surface skyline before the player ever reaches the deepest strata.

### Complexity rule

Do not make heat a universal simulation layer. Megafactories should be difficult because of belt throughput, power demand, input quality, staffing and waste. Reserve heat or explosion mechanics for a small number of optional late-game machines where the payoff is worth the extra complexity.


### Scope rule

Factories do not need a universal maintenance or durability simulation. If a machine is starved of inputs, power, workers, or storage space, it throttles or pauses. This keeps the challenge legible and preserves complexity for logistics and production planning.


## Civic life and modern colony services

The colony should gradually develop recognizable civic life. These buildings should feed into existing Well-Being, housing, workforce, food, and logistics systems without creating a separate happiness simulation.

### Healthcare progression

- **First-aid hut:** treats minor injuries and improves recovery time.
- **Clinic:** handles routine care, medicine, and basic public health.
- **Hospital:** requires medicines, clean water, trained workers, and reliable power; improves survival and reduces lost work time.
- **Specialist hospital:** treats radiation, badwater exposure, industrial accidents, or severe disease once those systems exist.
- **Public health laboratory:** produces vaccines, water tests, crop-safety reports, and outbreak-prevention supplies.

Healthcare should matter through straightforward effects: fewer sick days, faster recovery, healthier population growth, and better resilience during disasters.

### Food and retail progression

- **Market stall:** distributes food variety locally.
- **Grocery store:** accepts packaged foods, preserves, drinks, and household goods; reduces the distance beavers travel for supplies.
- **Bakery and café:** turn grains, oils, fruit, and sweeteners into high-value food and social needs.
- **Restaurant:** consumes several food categories and beverages, creates a strong social and nutrition benefit, and needs regular deliveries.
- **Food court or market hall:** serves dense urban districts and becomes a major consumer of factory output.

Restaurants should not replace ordinary food storage. They should be optional quality-of-life buildings that reward a diversified supply chain.

### Recreation and public space

- **Neighborhood park:** trees, shade, paths, benches, and simple decorations.
- **Playground and sports field:** support youth, leisure, and community life.
- **Public pool or bathhouse:** consumes water and power but provides strong well-being.
- **Theater, cinema, museum, or concert hall:** consumes paper, textiles, electricity, or cultural goods.
- **Botanical garden:** uses advanced irrigation and rare plants to create a high-tier attraction.
- **Civic plaza:** combines decorations, services, and events into a central public district.

Parks should also improve the feel of the city visually. They can make dense industrial districts livable when placed between factories and housing.

### Services and consumer logistics

Modern services create a second logistics layer beyond industrial production:

- Packaged food and medicines move through warehouses and grocery stores.
- Restaurants request specific ingredients instead of generic food.
- Hospitals consume medicine, clean water, and specialized supplies.
- Parks and civic buildings need trees, flowers, decorations, lighting, and water.
- Schools and laboratories consume paper, books, tools, and power.
- Retail districts use market hubs, delivery routes, storage limits, and worker access.

The player should be able to build an industrial colony, a comfortable town, or a dense modern city with different tradeoffs. Civic buildings should make the surface worth developing even after extraction and factory capacity are solved.

## Aquaculture and fish farming

Fish farming adds a new food branch built around water infrastructure. It should begin as a modest midgame option and grow into an industrial food chain later.

### Progression

- **Fish pond:** stocked with juvenile fish; produces fish slowly and benefits from clean water.
- **Hatchery:** breeds juvenile fish from adult fish, grain, algae, or specialized feed.
- **Feed mill:** converts grain, algae, insects, or crop byproducts into fish feed.
- **Fishery works:** processes fish into fresh fish, smoked fish, dried fish, canned fish, and fish oil.
- **Aquaculture complex:** large connected ponds or tanks with automated feeding and high output.

### Products

- Fresh fish: a new food variety and protein source.
- Smoked or dried fish: longer-lasting food for drought and badtide preparation.
- Canned fish: high-value food for grocery stores, restaurants, and hospitals.
- Fish oil: ingredient for advanced food, medicine, lubricants, or chemical recipes.
- Fish meal: fertilizer or animal-feed substitute, if later livestock or additional food chains are added.

### Simple constraints

Keep the system readable: ponds need water, fish need feed, and overcrowding reduces output. Dirty or contaminated water should reduce production or make the pond unsafe, giving water treatment and pipe routing a meaningful role. Avoid detailed oxygen, disease, or temperature simulation unless a later design specifically needs it.

Fish farming should compete with other water uses. A colony may choose to use a reservoir for irrigation, drinking water, power, aquaculture, or a combination of those through separate intakes and treatment systems.

### Civic integration

Fish becomes especially valuable when grocery stores, restaurants, food courts, hospitals, and emergency ration programs request it. This makes aquaculture part of the modern surface economy rather than just another isolated food recipe.

## Balance notation

Power values use Timberborn's rotary mechanical unit, horsepower (hp). New values should be compared with vanilla anchors before implementation. Keep science points and construction goods as separate gates: science signals capability, while material and infrastructure requirements prove that the colony is ready.
