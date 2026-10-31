# Construction materials

Target: Timberborn 1.1.2.8, Iron Teeth. The canonical authored values are in `tools/construction_materials.json`; `create_construction_material_content.mjs` generates the blueprints from that catalog. These are mod balance values, not vanilla statistics.

## Player progression

Build a Sandstone Pit beside sandstone outcrops and a Limestone Pit beside limestone outcrops. Workers gather these finite deposits using the game's normal range, carrying, reservation and output-inventory behavior. Each authored outcrop contains 600 stone. The resource is saved by the native Yielder and is removed when exhausted.

Build a Stone Crusher and a Cement Kiln (both 600 science) using vanilla construction materials. **Bricks come first (2026-10-30, user decision):** the crusher grinds sandstone into vanilla Dirt (brick earth), and the kiln moulds and fires dirt and water into Brick, burning logs as ordinary recipe fuel; there is no heat simulation. Bricks are the material of the 600 to 1,000 science window and stay in use afterwards: every building whose model shows brick (Plaster_Orange.IronTeeth) costs Brick under the material cost rule. The same kiln fires cement from limestone and dirt (real cement raw meal is limestone and clay), and the Concrete Mixer (1,000 science) mixes sandstone rubble, cement and water into concrete. One kiln either fires bricks or cement, so a growing colony builds a second kiln.

The crusher's dirt is the same vanilla Dirt the 2,000-science Dirt Excavator digs; it stores in the vanilla industrial piles (Pileable). The vanilla Terrain Block, which costs 4 Dirt, now unlocks at 2,000 science with the excavator instead of 1,000, so cheap crusher dirt does not open it early (same-path partial blueprint, `tools/vanilla_tool_overrides.mjs`). The vanilla Mud Bath (1,800) is unchanged.

Use the first concrete to build permanent quarries on marked deep seams. Both sandstone and limestone remain available indefinitely at the cost of water, power, workers and a larger investment. A quarry cannot be placed freely on ordinary ground: the native mine understructure constraint requires its matching seam.

Concrete then supplies advanced construction, including the waste vault. The vault's existing 80-concrete cost remains; this chain supplies the missing material rather than removing that requirement. Waste custody itself is still a separate unfinished mechanic.

## Buildings

Dimensions below are width × depth × height. Grid blueprints use X/Y/Z in that order. All buildings output 0 hp. The crusher, kiln, mixer and quarries have supported walking decks where clear cells accept native platforms. Machinery and roofs do not automatically provide support. Native support and collision determine placement, with no arbitrary layer limit. The crusher, kiln and mixer can stand on suitable stackable supports. Pits require ground, and quarries require a matching seam.

| Building | Dimensions | Workers | Demand (hp) | Science / bot science | Construction cost |
| --- | --- | ---: | ---: | --- | --- |
| Sandstone Pit | 5 × 5 × 4 | 2 | 0 | 300 / 1,000 | 30 planks, 15 logs, 5 metal blocks |
| Limestone Pit | 6 × 5 × 4 | 2 | 0 | 300 / 1,000 | 25 planks, 15 logs, 10 metal blocks |
| Sandstone Quarry | 11 × 10 × 9 | 4 | 1,500 | 4,000 / 5,000 | 505 planks, 130 treated planks, 130 metal blocks, 320 gears |
| Limestone Quarry | 11 × 10 × 9 | 4 | 1,500 | 4,000 / 5,000 | 505 planks, 130 treated planks, 130 metal blocks, 320 gears |
| Stone Crusher | 6 × 7 × 5 | 2 | 200 | 600 / 1,600 | 45 planks, 25 logs, 20 metal blocks, 35 limestone, 30 gears |
| Cement Kiln | 9 × 9 × 6 | 2 | 300 | 600 / 1,600 | 50 planks, 25 logs, 20 metal blocks, 95 limestone, 40 gears |
| Concrete Mixer | 8 × 6 × 7 | 2 | 250 | 1,000 / 2,000 | 90 planks, 35 metal blocks, 120 limestone, 60 gears |

Construction costs are the generated ones (2026-10-30). They follow the material cost rule in [progression.md](progression.md#material-cost-rule-2026-10-30): the authored catalog value times its tier factor, recomposed from what each model shows. Masonry is priced as limestone or sandstone; the pits and quarries leave the stone they work unpriced, and no building of the first concrete chain costs concrete or bricks. The kiln moved from cost tier T2 (factor 3) to T1 (factor 2) with its science. Dimensions, workers and power in this table predate the compaction pass.

These dimensions describe current authored registrations. The detailed pit replacements passed source/export checks and native harvesting, hoist animation, pause and exact save/reload/depletion in build 85. Their roofed storerooms and hand hoists follow the mining sheet's isometric views. The 85 profile included global placement/power overrides; support-rule acceptance is being repeated with those disabled. The mixer reference revision passed native placement, production and fresh-process reload in build 79; its previous 3×3×3 prototype is retired. See `tools/STATUS.md` for installed build evidence. Sparse structural occupancy and the separately supported walking decks permit appropriate native paths, platforms and shafts; the table's outer dimensions do not mean every enclosed grid cell is solid.

## Recipes and throughput

| Machine | Cycle (game hours) | Inputs | Outputs | Fuel |
| --- | ---: | --- | --- | --- |
| Sandstone Quarry | 2 | 4 water | 8 sandstone | None |
| Limestone Quarry | 2 | 4 water | 8 limestone | None |
| Stone Crusher (Grind brick earth) | 1 | 3 sandstone | 6 dirt | None |
| Cement Kiln (Fire bricks) | 2 | 4 dirt, 1 water | 4 bricks | 1 log per cycle |
| Cement Kiln (Fire cement) | 2 | 3 limestone, 1 dirt | 2 cement | 1 log per cycle |
| Concrete Mixer | 2 | 3 sandstone, 2 cement, 4 water | 8 concrete | None |

These are recipe durations at nominal productivity, not guaranteed observed rates. Worker productivity, working hours, power and hauling affect actual output. A fully supplied kiln on cement produces enough binder for one continuously operating mixer. One crusher (6 dirt per hour) supplies three kilns on bricks (2 dirt per hour each) or many on cement (0.5 dirt per hour each), so the player adds kilns before duplicating the crusher. Concrete takes sandstone directly, with the same 1.5 sandstone per 4 concrete that the retired aggregate step used. The crusher/kiln/mixer line has a combined nameplate demand of 750 hp. Adding both quarries raises connected nameplate demand to 3,750 hp; idle loads follow native workshop behavior. This is deliberately below the nuclear tier.

One mixer nominally needs 1.75 sandstone (1.5 as rubble, 0.25 as the kiln's dirt), 1.5 limestone, 0.5 log and 2 water per production hour, excluding quarry water. A brick kiln needs 1 sandstone (as 2 dirt), 0.5 log and 0.5 water per hour for 2 bricks. Each quarry outputs 4 stone/hour and consumes 2 water/hour while active. A 600-stone outcrop of each mineral supplies about 1,370 concrete before the sandstone runs out (limestone lasts to 1,600), or 1,200 bricks from the sandstone alone, provided all other inputs are available.

## Map and transport requirements

Map authors must place both finite outcrop types and both permanent seam types. The new entries are registered in the map editor's object group. Existing vanilla maps do not automatically acquire these entities. `outputs/Deep Frontier - Concrete Test.timber` is a Plains copy authored through the official map editor with all four sources near the starting plateau; it is also installed in `Documents/Timberborn/Maps`. Its outcrops serialize 600 units each. Individual production and continuity fixtures have passed as recorded below; an unseeded end-to-end colony remains to test. Sources are explicit geology; no terrain scanning or runtime map resizing is introduced.

The five mod goods (Sandstone, Limestone, Brick, Cement, Concrete) are solids stored as boxes, with normal carrying weights; Dirt is the vanilla Pileable good. Native input/output inventories are implemented. Mixer intake (then Aggregate and Cement), Concrete output and piped Water passed actual transfer and reload in build 81; the mixer now takes Sandstone instead of Aggregate, which is not yet retested in game. The kiln now also takes water for bricks, so it gains Timber Pipe ports on its flat faces (connection rule). Power Lines supplied the same circuit in builds 82/83, with measured combined demand of 312 hp for the mixer, six belts and pump. Other factory ports and rotations remain separate checks. None of the concrete recipes is conveyor-only, so the first industrial line has a normal early hauling route by design.

## Foundations and water infrastructure

`tools/structural_content.json` now authors sandstone/limestone masonry, a concrete levee block (4 concrete and 1 sandstone ballast since Aggregate was retired), an eight-tile reinforced overhang, a 3×3 four-layer scaffold, a metal-reinforced dam block and a concrete overflow dam. Their original models and ivory icons are reviewed under `docs/art/reviews/2026-10-20-structures`. The solid modules use the native one-layer Levee seal; the overflow dam uses the native 0.65-layer Dam sill. Open overhangs/scaffolds have no water obstacle. Source/export checks passed; native acceptance is recorded separately in STATUS.

`tools/building_construction_costs.json` replaces generic expansion-building costs with explicit entries. Advanced production, research, restaurant and rocket facilities now require concrete: initial amounts range from 40 for Food Packaging Works to 480 for the Launch Pad; the reactor requires 300. Hospital/grocery retain their canonical 80/40 concrete costs in `frontier_progression.json`. Deep Drill, Deep Processor and permanent Deep Mine require 40/60/100 concrete in their producing generator. These are initial balance values. Both pits and the crusher/kiln/mixer require no concrete, and the finite-to-permanent construction graph still passes.

Controlled dam-base generation is specified in [hydroelectric-construction.md](hydroelectric-construction.md). Its turbine art, component and in-game water/power tests remain to implement.

## Retired goods (2026-10-30)

Aggregate was removed with the bricks pass. Saves map stored Aggregate to Sandstone and a crusher saved on the Aggregate recipe to Grind brick earth through native `BackwardCompatibleIds` (`tools/content_policy.json` `migratedGoods`/`migratedRecipes`). Sandstone, not Dirt: Dirt is Pileable and would land in box warehouses. Flux, the Steel Mill's single-recipe intermediate, maps to Limestone, which high-grade steel now takes as its flux. See [progression.md](progression.md#retired-goods-2026-10-30-bricks-pass) for the other five removals.

## Implementation and verification

`MineralDepositSpec` implements the native `IYielderDecorable` contract with persistent yield. A small component enables that yield and deletes the exhausted source. `MineralPitSpec` selects one mineral. Each mineral has its own native resource group, shared by its source and pit, so gathering tooltips match the selector. Native scavenger work, hauling, range, removal strategy and reservations handle extraction. The pit also registers the native `YieldStatus` and output-inventory panel components that vanilla registers in `RuinsUIConfigurator`; work depends on the former. The spec decorators follow the official ShantySpeaker configurator pattern. No Harmony patch or separate inventory/save format is needed for this chain.

Permanent quarries use `EfficientMine` understructure placement and normal `ManufactorySpec` recipes. Processing buildings use audited Smelter factory components, with their inherited mesh-specific effects removed at authoring time. Native `RecipeSpec.Fuel` provides kiln fuel consumption. The official Mod Builder compiles, packages and installs all output.

Original Blender models contain UV maps, material slots, construction stages and moving components. All seven construction buildings, five goods and four map sources now use ivory outline SVG icons, following the approved native UI style. Their 128px and 32px review is in `docs/art/reviews/2026-10-20-mixer/construction-ivory-icons.png`; installed build status is recorded separately. Blender source axes match the official exporter at authoring time. Exported clips require in-game animation validation.

The static validator checks active-faction goods, every mod building's construction costs, collection registration, source constraints, hp direction, geometry, asset references, and concrete reachability including construction gates. It verifies that removing the cement recipe prevents concrete, and that the chain can continue with permanent sources after finite sources run out. Native crusher/kiln/quarry production, access and reload passed builds 15/17; the rebuilt mixer passed build 79. Mixer conveyor inputs/output and piped Water passed build 81, including power/valve interruptions, exact conservation and saved queues followed by further production. Both finite mineral types passed depletion and exact native continuity in build 86 using explicitly shortened 24-unit test sources; normal authored sources retain 600 units. Both global build/power overrides were disabled, and effective Ground/None support, rejection of floating pits and roof paths/platforms, and absence of power nodes passed in main and reload. Other factory layouts and wider transport coverage remain. See `tools/STATUS.md` for exact observed results.

## Runtime acceptance sequence

Use an isolated Iron Teeth test settlement on a copy of Plains authored with both outcrops and both seams. Native developer tools may supply baseline goods and finish test construction; they must not create the concrete used as evidence of production.

1. Place and save each source in the official map editor; reload it and confirm location, model and initial yield.
2. Connect each pit to the district. Confirm workers return only its designated stone and the matching deposit quantity falls. Reload the save and verify the remaining quantity is preserved.
3. Operate crusher, kiln and mixer with their declared inputs and adequate power. Observe dirt, bricks, cement and concrete in native output inventories, including log consumption at the kiln. Withhold each required input and power in turn and confirm production stops rather than generating goods freely.
4. Place each quarry over its matching seam; reject ordinary terrain and the wrong seam. Confirm water-powered extraction continues without consuming the source entity. Save and reload with quarries operating.
5. Confirm model alignment, entrance access, construction art and animation, then check belt transfer of the five solids and pipe transfer of factory water against the installed foundation mods.
6. Spend produced concrete on a permanent quarry or other authored construction cost. Record observed inventories and save paths separately from static reachability results.
