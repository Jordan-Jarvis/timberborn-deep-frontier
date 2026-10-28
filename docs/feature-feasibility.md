# Deep Frontier feasibility pass (Timberborn 1.1)

This pass separates features that fit the supported building/recipe/mod API from features that would require a new terrain or fluid simulation. The project should ship the high-confidence pieces first and keep the risky pieces behind explicit adapters.

## Taller worlds and copied maps

The current 1.1 tool to use is [Map Transformer](https://steamcommunity.com/sharedfiles/filedetails/?id=3798650616), which is marked for Update 1.1 and requires Moddable Timberborn. It can resize map height, add bottom dirt, preserve water while transforming, and work in the map editor or on a paused save. It creates a transformed save and warns that the current session may crash; the author also recommends a backup and says custom terrain height still requires the mod when playing.

Use it as a **map-authoring tool**, not as a runtime dependency for expanding the world during ordinary play:

1. Copy a vanilla `.timber` map to a new Deep Frontier source file. Never transform the only copy.
2. Open the copy in the map editor with Map Transformer enabled.
3. Add a modest number of bottom dirt layers to create vertical budget beneath the surface, then raise the terrain/total height only as far as the map can render reliably.
4. Carve one or two authored lower sectors, shafts, and low pockets in the editor. Place the starting colony and all lower-sector entrances deliberately.
5. Save the transformed map, reload the generated save, save it again, and test it with the development dependency profile.

For the first map, target a conservative extra 8 terrain layers and a total height around 40 rather than jumping straight to extreme 64 or 96-layer maps. The map should be playable without the editor tool after authoring only if its custom terrain height is not reset; published maps that depend on a custom terrain height must list Map Transformer and its Moddable Timberborn dependency. A taller map gives us authored vertical space; it does not provide procedural caves, runtime terrain resizing, or automatic building placement.

## Feature matrix

| Feature | Feasibility | First implementation | Boundary or fallback | First slice |
|---|---|---|---|---|
| Copied, taller world | High as authoring | Duplicate a vanilla map, transform height, then hand-author lower sectors | Backups are mandatory; custom terrain height keeps a mod dependency; do not resize during normal play | One 8-layer lower sector and one shaft |
| Runtime map expansion | Low | Unlock pre-authored sectors with Survey Stations | Defer save transformation and runtime terrain edits to a reverse-engineering branch | Survey milestone reveals an existing room |
| Underground rooms and shafts | Medium-high | Ordinary buildings, paths, platforms, airlocks, and vertical logistics inside authored chambers | No generic cave generator or “dig anywhere” system in v1 | One room with a lift, pipe riser, and power riser |
| Underground settlement | Medium-high | Standard housing, workplaces, food, water, and district services placed in a lower sector | Lighting, pathing, district range, and service reach need playtesting; no special subterranean citizen simulation | Ten-beaver outpost |
| Custom buildings, goods, and recipes | High | Add standard specs/blueprints and recipe chains | Custom UI and novel entity behavior require code; keep each new good tied to a visible use | Deep ore to alloy |
| Surface agriculture, fertilizer, advanced food | High | Workplace and recipe additions using vanilla goods flow | Keep one or two inputs per tier so the surface remains readable | Compost, fertilizer, greenhouse, bakery |
| Hospitals, restaurants, grocery stores, parks | High for service buildings | Well-Being buildings with standard visitors, workers, storage, and recipes | New needs/status effects are a separate code feature; first pass can improve existing needs and supply chains | Clinic, grocery, restaurant |
| Fish farming | Medium-high | Water-dependent workplace plus a Fish good and hatchery recipe | Start with inventory-based production; delay individual fish entities and complex migration | Pond to fresh fish |
| Conveyor-only factories | High with Conveyor Belts v2 | Fixed input/output ports, belt lifts, splitters, and large power loads | Detect the belt package; retain hauling fallback for non-required lines | One belt-fed alloy line |
| Timber Pipes and Pump to Tank | High with dependencies | Pipe ports, tanks, pumps, and fluid recipes; use the existing [Pump to Tank mod](https://steamcommunity.com/workshop/filedetails/?id=3681283725) rather than reimplementing it | Core slice uses water, oil, badwater, and chemicals; custom gas goods are optional research | Water or oil tank-to-machine loop |
| Solar, Power Lines, Flywheels | High with dependencies | Register ordinary consumers and generators against the existing network | Extract exact package profiles and treat flywheel behavior as an adapter; do not create a second power system | Solar panel, flywheel, one substation |
| Coal, oil, ore veins | Medium | Pre-authored finite stockpiles bootstrap the colony; permanent vein understructures feed sustainable extractor recipes | Runtime terrain-cell scanning, natural vein depletion, and arbitrary mine placement require code; use explicit source markers and understructure-gated permanent mines first | One finite stockpile plus one permanent Deep Ore vein |
| Deep drilling | Medium-high | Mine/Aquifer-Drill-style workplace with power, workers, drill heads, and a selected source node | Do not promise generic drilling into any terrain block in v1 | One drill at one authored vein |
| Gas, fumes, radon, methane | Optional later | Named custom goods plus explicit per-pocket inventories only if the hazard branch earns its complexity | Avoid full diffusion, buoyancy, pressure, and world-fluid simulation; do not block factory progression on this module | Deferred after industrial chain |
| Hazards and contamination | Optional later | Area alarm, machine shutoff, contaminated input, and recovery recipes for selected late hazards | Defer lethal exposure, physics, and a global hazard solver; reactor radiation remains the first bounded hazard | Reactor radiation or badwater isolation |
| Oil refining, polymers, nuclear chain | Medium-high | Linear recipe chains with power demand, waste goods, and unlock gates | Represent radiation as an area state and byproduct; no heat or maintenance simulation | Refinery plus one waste outlet |
| Radioactive waste custody and reprocessing | Medium-high | Persistent sealed good; locked storage; Radioactive Waste Refinery converts waste into badwater and recovered minerals | No manual deletion or demolition while waste is present; migrate stranded waste to an emergency vault | Reactor to locked vault to badwater refinery |
| Specialist workforce and education | Medium-high | Colony-level training capacity from School, Technical School, Engineering Academy, and Mission Control Academy; one-time commissioning licenses for advanced sites | Avoid hard-locking named beavers to jobs in v1; ordinary worker allocation remains intact, and bots can fill unlocked specialist capacity | Technical School commissions one reactor and one cryogenic plant |
| Badwater source mystery | High as content, medium as systems | Archive buildings, map objects, science milestones, and scripted objectives | If a novel quest/event API is unavailable, use staged unlocks and visible evidence items | Human Archive chain |
| General heat and maintenance | High to omit | Power, inputs, storage, workers, hazards, and waste are the operating constraints | Do not add hidden universal upkeep; reactor coolant failure is a bounded special-case hazard | All factories use the same clear failure states |

## Recommendation

Use Map Transformer to create a **single purpose-built Deep Frontier map** from a copied vanilla map, then keep the actual mod focused on buildings, recipes, logistics adapters, resource nodes, and progression. The underground should be a set of authored spaces that become useful over time, not a promise that the game will generate or resize a cave network at runtime. Gas pockets and scrubbers are an optional branch after the core factory loop is stable. This gives the project a stable save format and leaves reverse engineering focused on source-node selection and dependency adapters first.

Education should gate access to complexity without turning every workplace into a fragile private assignment system. In the first implementation, a School produces basic training capacity, a Technical School produces industrial capacity, an Engineering Academy produces specialist capacity, and Mission Control produces flight capacity. Advanced buildings consume a one-time commissioning license when they are activated, then draw from the corresponding trained-capacity pool. The building panel should name the missing certificate or capacity and show the next training building the player can construct. This keeps the intended “learn before operate” progression while preserving the game’s ordinary worker allocation and avoiding colony-wide deadlocks.

