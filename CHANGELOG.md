# Changelog

## Unreleased

### Bricks: a new step between metal and concrete
- **New good: Brick.** The Stone Crusher now grinds sandstone into vanilla dirt (brick earth, 3 sandstone into 6 dirt per hour), and the Cement Kiln fires 4 dirt and 1 water into 4 bricks every 2 hours, burning a log per batch.
- **The Cement Kiln unlocks at 600 science** (was 900), with the crusher, so bricks get their own window before concrete (1,000). The kiln also got cheaper.
- **Cement** is limestone and dirt again (was limestone and aggregate). **Concrete** takes sandstone directly: 3 sandstone, 2 cement and 4 water make 8 concrete every 2 hours, the same ratios as before.
- **Buildings that show brick now cost bricks.** The orange brick plaster on buildings is priced as Brick, so 14 buildings from the Deep Drill to the Rocket Assembly Hangar take bricks instead of part of their other materials. The crusher and kiln never need bricks to build.
- The kiln takes water for bricks, so it now accepts Timber Pipes on its flat walls.
- The vanilla **Terrain Block** unlocks at 2,000 science with the Dirt Excavator (was 1,000), so cheap crusher dirt doesn't open it early. The Mud Bath is unchanged.
- The built-in maps' starting stone still covers everything up to the quarries: 1,535 sandstone and 1,343 limestone of the 1,800 each.

### Fewer goods (seven removed)
- **Aggregate:** concrete uses sandstone, cement uses dirt and the concrete levee block takes 1 sandstone.
- **Flux:** high-grade steel uses limestone as its flux. Electronics and reinforced bot chassis no longer need it.
- **Compost:** the Fertilizer Works makes fertilizer in one step (1 log, 2 algae and 2 water make 2 fertilizer in 2 hours). The Greenhouse needs 30 fertilizer to build (was 30 compost).
- **Medical Food, Emergency Ration and Packaged Food:** the Food Packaging Works makes canned fish. The Technical School's flight course uses canned fish, and the Grocery Store stocks eggplant rations in place of packaged food.
- **Archive Data:** Mission Control reads the recovered artifacts' data drives directly: guidance computers take 2 artifacts and 1 grease, telemetry 2 artifacts and 1 metal part. Human Record Caches give 12 artifacts. Story chapters 5 and 6 ask for 20 and 40 recovered artifacts.
- **Old saves:** stored goods load as their replacement (Aggregate as sandstone, Flux as limestone, Compost as fertilizer, the three foods as canned fish, Archive Data as recovered artifacts), and workshops set to a removed recipe switch to its replacement.

## 0.7.1 (2026-10-30)

### Fixes
- No crash when a game loads without Flywheels installed. 0.7.0's build-menu group for Flywheels tried to load Flywheels' icon even when that mod is missing; the group now only exists when Flywheels is installed. It holds all nine flywheels directly, without the three sub-groups per type.

### Maps re-planned for the smaller buildings
- Every built-in map's sites were searched again for the compacted footprints (Deep Mine and Deep Drill 7x6, quarries 8x6, Nuclear Reactor 14x11).
- **Beaverome** now has two Deep Mine sites, two Deep Drill sites with a Deep Ore Source each (17,000 deep ore), the Deep Processor, Steel Mill, Mission Control and Launch Pad. It is no longer EXTREMELY difficult; it shows the shorter notice of what it can't provide (quarries, reactor, some plants and civic buildings, renewable scrap).
- **Diorama** gets two Deep Mine sites and most of the deep industry; **Cliffside** gets the Limestone Quarry, the Launch Pad, five Human Record Caches and the full rocket chain. Both stay EXTREMELY difficult because they are small.
- **Reactor sites** on Canyon, Craters, Hollows, Mountain Range, Oasis, Pillars, Spillage and Thousand Islands. Only Beaverome, Cliffside and Diorama have none now (was 11 maps).
- Meander, Waterfalls, Pillars and Thousand Islands get the plants they had no room for.
- The small-map threshold follows the smaller sites: 5,966 tiles (was 11,176). Diorama and Cliffside are still the only small maps.
- The four Deep Frontier map files (Plains, Plains Hard, Lakes, Terraces) keep their placements and sites.

## 0.7.0 (2026-10-30)

### Tidier build menu (player feedback)
- **Paths:** platforms, suspension bridges, overhangs and tubeways each get a sub-group. So do Teleporter Station's teleporter and ring, when that mod is installed. The Paths bar goes from about 30 buttons to 14, so opening a sub-group no longer pushes the bar off the screen.
- **Power:** new sub-groups:
  - Water power: both water wheels and the Reinforced Hydro Turbine.
  - Power shafts: the three shafts and the clutch.
  - Engines and power plants: steam engine, New Styles' steam plant, geothermal engine, Solar Panel when installed, and the coal, oil and nuclear plants.
  - With Flywheels installed, a Flywheels sub-group with one sub-group per type: inline, horizontal framed, vertical framed.
- **Landscaping:** Dynamite (single, double, triple), Floodgates, and Deep Frontier's masonry and concrete blocks each get a sub-group.
- **Storage:** sorted by type, then by size: piles, then warehouses, then tanks. With Expanded Storage installed, its buildings slot in by size. The Radioactive Waste Vault comes last among the warehouses and the Cryogenic Tank Farm last among the tanks.
- A sub-group for an optional mod's tools appears only when that mod is installed. Without the mod, nothing changes and nothing breaks. Vanilla and other mods' buildings keep their own blueprints; only their place in the menu changes.

### Deep Well in droughts; vanilla Grease replaces Lubricant
- **Deep Well in droughts** (player feedback: it was too strong): in a drought the well now runs only on its full 100,000 hp, at any boost, and drives its source at most 2× (6× otherwise). Short of full power it stops and the source dries up like any other. Outside droughts nothing changes (1,667 hp per boost step, 10,000 hp at 6×). Seeps still become steady sources while it runs, the radioactive-tide shut-off and the drill bits are unchanged, and the building description and panel state the drought rule.
- **Grease replaces Lubricant:** Deep Frontier's Lubricant is merged into the vanilla Iron Teeth Grease, made at the Grease Factory from Extract and Canola Oil. Cryocoolant and Servo bot limbs now take Grease, and bots in heavy industry take Grease (best) or Fish Oil for maintenance. The Chemical Works' Lubricant recipe is gone.
- **Old saves:** Lubricant stays defined so saves holding it still load, but nothing makes or uses it any more. Haulers clear it out of workplaces; empty it from storage. A Chemical Works set to make Lubricant loads with no recipe: pick another.

### Fixes
- Loading a second game in the same session (load a save, return to the main menu, start a new game or load another save) no longer crashes with "expected native shader ... found Hidden/InternalErrorShader". Water and terrain are returned to their native look whenever a game ends.
- The error report's game save no longer fails when a crash happens while a new game is still loading.
- **Deep Mine:** the ore bin's top no longer shows see-through gaps between the ore lumps.

### Construction costs follow materials
- Every building now costs what it is visibly made of. Timber and plank buildings cost planks (logs too before 600 science, treated planks later), steel and sheet-metal buildings cost metal blocks, deep alloy, high-grade steel or alloy by stage, and concrete is needed only where the building shows concrete. Masonry costs limestone or sandstone. Gears and machine cores stay as they were, and no building got cheaper.
- A building never costs a good that can only be made with that building, or with one unlocked after it: the first concrete chain (pits, crusher, kiln, mixer) needs no concrete. The pits and quarries do not pay for the stone they quarry.
- Concrete-heavy late buildings now need far more concrete (the Nuclear Reactor 32,285, the Launch Pad 9,040), and less steel and alloy. Before the quarries, the buildings still fit in the 1,800 limestone and sandstone that every built-in map holds near its pits.

### Fewer required mods
- **No crash without the optional mods.** Deep Frontier now loads, starts a new game and loads a save with only its required mods. Without Power Lines the game used to crash while loading mods ("Could not load file or assembly 'PowerLines'"), and three buildings carried a Power Lines spec that the game cannot load without that mod.
- Seven mods are no longer required: Power Lines, Pump to Tank, Flywheels, Teleporter Station, Solar Panel (northforge), Expanded Storage and Powered Tubeway. Deep Frontier still integrates with the ones it uses, and only while they are enabled:
  - **Power Lines:** cable attachment points on the Concrete Mixer, Reinforced Hydro Turbine and Materials Laboratory, and the vanilla power shafts stay in the build menu.
  - **Expanded Storage:** its Pile Module shows Deep Ore and Deep Alloy piles again.
  - **Moddable Weathers** and **Sluice is Back!** stay optional, as before.
  - Pump to Tank, Flywheels, Teleporter Station, Solar Panel and Powered Tubeway need nothing from Deep Frontier and work alongside it.
- **One Tubeway Station in the build menu:** the vanilla station is hidden in favour of New Building Styles' Tubeway Station. Placed vanilla stations keep working, and dev mode still shows both.

### Smaller buildings: concrete chain and quarries
- **Cement Kiln** is 5x3, 4 high (was 7x5, 6 high): a closed feed house, the rotary drum under a lean-to roof on stone blocks, the stone firebox with its fire and chimney. The open timber trestle and raised drum deck are gone.
- **Concrete Mixer** is 4x3, 3 high (was 7x5, 7 high): the hoppers sit on the operator room's roof, the drum stands on low concrete piers, the water tank on a concrete pedestal. The tall timber feed tower and tank tower are gone.
- **Stone Crusher** stays 4x4 but is 3 high (was 5): its workshop is one layer under the machine floor, and the roll and hopper roofs are flat.
- **Sandstone and Limestone Pit** have one storey under a flat roof (3 high, was 4); the hoist jib is lower. The flat roof can carry platforms.
- **Limestone and Sandstone Quarry** are 8x6, 5 high (was 11x7, 9 high): a boarded headframe over the shaft with its sheave, a flat-roofed winding house with the drum, and the sorting line on a stone plinth. The ladder mast and lattice tower are gone. Old quarries keep their place over the seam.
- **No clutter on buildable tiles:** the kiln's front tiles beside the porch are open ground, the mixer's wet tray sits in its concrete base, and the quarry's plinth top and winding-house roof can carry platforms.
- **Old saves:** placed Cement Kilns and Concrete Mixers keep their origin and entrance; freed tiles become empty ground. Reconnect a pipe at the mixer's water inlet (now on the tank pedestal) and its power line.

### Smaller buildings: deep industry
- **Deep Drill** is 7x6, 8 high (was 11x9, 16 high): a boarded drilling tower on a solid concrete engine room, open at the front so the hoist shows. The open lattice derrick, the pier substructure, the pipe ramp, the pipe rack, the separate power house and the mud tanks are gone; the stacks rise up the engine room's walls. Same cost, power, crew and drill-bit upkeep.
- **Deep Mine** is 7x6, 7 high (was 10x11, 16 high): a compact plated headframe on a low concrete shaft house, both skips riding in its open front under twin sheaves; the winding drum and flywheel turn on the deck, the skips tip into an ore bin on the deck, and the ground in front stays buildable. The open lattice headframe, drum shed, engine house, stilted ore bin with its tipple and the bath house are gone. Same cost, power, crew and upkeep; it still stands over its Deep Ore Vein; a mine that was placed flipped needs re-placing over its vein.
- **Deep Ore Processor** is 7x6, 8 high (was 11x10, 14 high): the blast furnace stands on a low hearth podium and is charged by a compact skip hoist instead of the long lattice skip bridge; a flat-roofed casting bay and blower house. Same cost, power, crew and recipes.
- **Steel Mill** is 8x6, 8 high (was 12x10, 15 high): a flat-roofed melt shop with its electrode penthouse, the rolling line and teeming bay under flat open roofs. The open crane bay and its travelling ladle crane, the bunkers and the cooling bed are gone. Same cost, power, crew and recipes.
- **Archive Excavation** is 7x6, 6 high (was 10x9, 11 high): a flat-roofed archive hall, stack tower and catalogue wing beside the dig and its tripod derrick, with a flat-roofed sieving shed. Same cost, power, crew and recipes. Human Record Caches can now be surveyed from 7 tiles away (was 4), so every cache the larger excavation reached, on the built-in maps and in existing saves, stays in range.
- **Old saves:** a placed Deep Drill keeps its origin and entrance (a flipped one's entrance moves 4 tiles); reconnect its shafts and pipes to the new walls.

### Smaller buildings: chemical, cryogenic and process plants
- **Chemical Works** is 5x5, 8 high (was 10x9, 14 high): one solid two-storey reactor hall with a flat roof carrying the fin-fan cooler and the flare, three agitated reactors along its side and the fractionating column with one ring platform. The lattice flare tower, pipe-rack catwalk, cooler piers and product sphere are gone; the front of the roof can carry platforms. Same cost, power and crew.
- **Precision Machine Works** is 9x5, 7 high (was 11x9, 14 high): the long sawtooth machine hall with its open belt bay, a flat-roofed gate office with the air receiver, and the crane yard where the travelling crane runs on a solid runway wall beside a six-layer brick chimney. The yard's steel columns, the receiver frame and the forge lean-to are gone. Same cost, power and crew.
- **Electrolysis Plant** is 8x5, 6 high (was 12x9, 12 high): the two telescoping gas holders in plain round guide frames beside a flat-roofed two-storey cell hall with a glazed lantern, two transformers and the water intake behind it. The bus-bar gantry, open cell gallery and scrubber drums are gone. Its door is now on the front edge of the tile column the old access path used: re-path or re-place existing Electrolysis Plants. Same cost, power and crew.
- **Cryogenic Liquefaction Plant** is 8x6, 9 high (was 12x11, 16 high): the frost-white cold box tower with its banded column, the two Horton spheres, a flat-roofed two-storey compressor house carrying the cooler fans and the open engine bed. The cooler deck on piers, the pipe rack, the loading bay and the product tank are gone. Its entrance is now the tile in front of the old door. Same cost, power and crew.
- **Cryogenic Tank Farm** is 7x6, 7 high (was 11x10, 11 high): the domed LOX tank with its spiral stair, two hydrogen bullets in the bund, a flat-roofed control hut, the compressor, vaporizers and manifold along the front. The pipe rack and the bullet platform are gone. Its two pipe sockets moved to the front-edge cells (5,0) and (6,0): reconnect pipes on placed tank farms. Same cost, capacity and power.
- **Water Treatment Plant** is 9x5, 7 high (was 12x11, 13 high): the water tower on a solid concrete shaft, two round clarifiers with their scraper bridges, a filter house under a teal plank gable, a flat-roofed chemical house with the chlorine tower and an open pump shed under corrugated metal. The lattice trestle and both digesters are gone. Its door is now on the front edge of the old access column and the coolant outlet is on the front of the tower: re-path existing plants and reconnect their coolant pipe. Same cost, power and crew.
- **Fertilizer Works** is 7x5, 7 high (was 9x6, 13 high): three stave silos on steel drums, a closed bucket elevator, a flat timber-roofed composting hall and the rotary drier. It shows no concrete any more (it unlocks before concrete): timber ground storeys, steel silo drums and a steel firebox. The lattice elevator tower and the barrel vault are gone. Same cost, power and crew.
- **Food Packaging Works** is 7x5, 7 high (was 10x7, 12 high): the steel cannery under a flat corrugated-metal roof and glazed monitor, the retorts, the boilers and a hip-roofed boiler house with a shorter stack, and a timber-roofed warehouse over a short conveyor bridge. The gable, turbine ventilators, feed-water tank and tall stack are gone. Same cost, power and crew.

### Smaller buildings: power, nuclear and rocketry
- **Coal Power Plant** is 4x4, 6 high (was 5x5, 10 high). The boiler house has a pitched corrugated-metal roof, and the chimney rises from the ground; the coal bunker and the roof deck are gone. Same cost and output.
- **Oil Power Plant** is 5x4, 6 high (was 6x6, 9 high). The turbine hall has a pitched metal roof, the boiler tower a riveted steel roof you can build on with its twin stacks rising from the ground, and the fin-fan cooler unit stands on the tank bund. The barrel vault and the cooler frame are gone. Same cost and output.
- **Reinforced Hydro Turbine** is 6 high (was 7) on the same 8x10 footprint: the workshop on the terrace is one storey under a lower teal plank gable, with no dormer or roof vent. The dam, gates, water flow and terrace walkway are unchanged.
- **Uranium Processing Plant** is 8x7, 8 high (was 12x11, 14 high). The centrifuge row stands under a flat canopy beside the hall, whose clerestory monitor and fuel vault have riveted steel-plate roofs you can build on. The steel gantry, catwalks, drum dock, roof fan and roof duct are gone; the scrubber column and stack rise from the ground. Same cost, power and crew; a flipped plant's entrance moves 4 tiles.
- **Nuclear Reactor** is 14x11, 11 high (was 20x15, 22 high): the containment dome and twin cooling towers stay, the turbine hall has a riveted steel-plate roof you can build on with no roof vents, and the feed tanks stand on the feed house; the galleries, lattice water tower, vent stack and steel trestles are gone. The coolant pipe inlet is where it was. Same cost, output and crew; a flipped reactor's entrance moves 6 tiles. The Meander and Pressure maps' reactor sites moved 6 tiles to stay within reach of water.
- **Radioactive Waste Refinery** is 9x7, 7 high (was 12x11, 12 high): the vitrification hall has a pitched metal roof with orange gables, the cask crane is a short riveted box girder on a concrete pier in the pond and a pedestal on the hot cells, and the stack rises from the ground. The lattice gantry, filter house and roof vents are gone. Its entrance is now the tile in front of the old doorway; a flipped refinery's entrance moves 3 tiles. Same cost, power and crew.
- **Radioactive Waste Vault** is 8x7, 6 high (was 9x10, 12 high): two berm courses, a lower dome closed by a concrete crown (the turning lantern ventilator is gone), shorter vent towers and a gatehouse under a teal plank gable. Same cost.
- **Smaller radiation buildings:** the Radioactive Waste Export is 3 high (was 4) with a flat roof you can build on; the Sludge Outfall (3 high, was 4) and Sludge Recovery Pump (3 high, was 5) keep lower plank roofs, and the pump's roof cowl is gone; the Smog Scrubber is 5 high (was 6) without its ring catwalk; the Deep Well is 4 high (was 5); the Reactor Charging Bay's roof fan is gone. Same footprints, cost and power.
- **Rocket Assembly Hangar** is 7x8, 9 high (was 8x9, 14 high): the barrel vault stays, lower, over a bay that holds the 0.8-scale rocket stage; the workshop has a flat timber-decked roof you can build on, and its forge flue rises from the ground in the workshop wall. The ridge walkway, work platforms, roof vents and roof stack are gone. Same cost, power and crew; a flipped hangar's entrance moves 1 tile.
- **Launch Pad** is 10x9, 12 high (was 12x12, 18 high): a closed service tower instead of the open lattice gantry, a one-layer pad and a 0.8-scale rocket; the pump house has a plank gable. Same cost, power and crew; a flipped pad's entrance moves 2 tiles.
- **Mission Control** is 8x7, 9 high (was 12x10, 16 high): the control tower with its glazed cab, the telescope dome and the radio dish stay, beside a two-storey hall under a teal plank gable. The lattice masts and their aerial are gone. Its entrance is now the tile in front of the old doorway; a flipped Mission Control's entrance moves 4 tiles. Same cost, power and crew.
- **Old saves:** every one of these buildings keeps its origin; freed tiles become empty ground. Reconnect shafts and pipes to the new walls; anything built on a roof that is now pitched or lower must be rebuilt.

### Smaller buildings: civic and science
- **Restaurant** is 5 high (was 9) on the same 9x7 footprint: one layer per storey, both dining balconies with all their tables and chairs, a flat timber-decked roof level with the roof terrace, the sign swinging from a gantry on the front parapet. The gabled roof, dormers and lantern are gone.
- **Hospital** is just its central pavilion: 4x9, 9 high (was 12x9). The two ward wings are gone; the pavilion, its doors, rear decks and roof garden are unchanged. Same cost, power, crew and 30 beds.
- **Grocery Store** is 5 high (was 8) on the same 9x6 footprint: one layer per storey, the balcony one layer up (one stair reaches it), the gable roof and lit monitor kept.
- **Fish Hatchery** is 3 high (was 5) on the same 7x7 footprint: the headhouse and pump canopy are one layer under flat roofs.
- **Fishery Works** is 4 high (was 7) on the same 11x8 footprint: one layer per storey, galleries and the warehouse roof terrace one layer up, the long roof kept but lower; the rear water tanks (pipe inlet) stand under the rear gallery.
- **Materials Laboratory** is 5 high (was 9) on the same 10x8 footprint: one-layer cast bases, the terrace one layer up, the records office under a flat roof, the sawtooth testing hall, tower and press lower. Same cost, power and crew.
- **Public Health Lab** is 6x4, 4 high (was 8x6, 12 high): two one-layer storeys under a teal plank gabled roof, with the weathervane and anemometer on its ridge. The mansard, observation lantern, tall tower and ventilation shaft are gone. Same cost, power and workers; a flipped lab's entrance moves 2 tiles.
- **Technical School** is 8x4, 7 high (was 11x5, 14 high): the clock tower stays, half as tall, beside a two-storey block under a teal plank gable and a one-storey engine house with a timber roof deck you can build on, and the working beam engine in front. The right wing, hipped roofs and chimneys are gone. Same cost, power and seats; a flipped school's entrance moves 3 tiles.
- **Town Plaza** is 7x8, 4 high (was 9x9, 6 high): the same fountain and visitor places, a lower bandstand with the flags on its podium, and no flagpoles or plinths taking tiles of the paving, which you can build on. Same cost and capacity; a flipped plaza shifts 2 tiles.
- **Greenhouse** is 9x3, 5 high (was 9x5, 9 high): the glazed pavilion and dome stay, lower, with one-storey glazed wings; the boiler house, stack and pump sit behind the right wing. Same cost, power and worker; placed greenhouses keep their entrance, flipped ones too.
- **Bathhouse** is 7x5, 5 high (was 9x7, 11 high): the cross-vaulted bath hall with its thermal windows on a smaller hall, one-storey changing rooms and boiler room with flat roofs, the plunge pool in front. Same cost, power, water and 12 bathers. The water inlet moved to the back of the boiler room; reconnect its pipe. A flipped bathhouse's entrance moves 2 tiles.
- **Observation Deck** is 10 high (was 16), same 6x6: the deck sits at layer 7 on a solid concrete corbel instead of open trusses, the stairhead and ticket kiosk have flat roofs you can build on. Same cost and 20 visitors.
- **No clutter on open tiles:** the Restaurant's sign gantry stands on its front parapet, so the whole roof is buildable; the crate, basket and sack in front of the Grocery's stall wing are gone.
- **Old saves:** the Restaurant and Grocery keep their place and entrance. Paths, stairs and platforms on the old decks, balconies and terraces of these buildings need re-placing. Re-place an old Hospital: its remaining pavilion now sits on the old west wing's tiles. Reconnect a pipe to the Fishery Works' tank inlet one tile in from where it was.

### Roofs and decks
- **Flat roofs you can build on, roof variety, no roof vents, no concrete before concrete:**
  - The Restaurant's and quarries' last blocked flat roof tiles, and those beside the kiln and drill stacks, now take platforms.
  - The Deep Mine's lamp house and the Archive's hall have real plank gables. The Deep Drill, Deep Ore Processor, Steel Mill, quarry winding house and Limestone Pit get steel plate or painted sheet roofs; the Deep Mine annex and the Archive catalogue wing get timber decks.
  - Roof flues and stacks are gone from the Restaurant, Hospital, Fishery Works, Grocery and Materials Laboratory (the Restaurant and Laboratory no longer make smog). The Deep Drill, Deep Mine and Archive chimneys rise up their walls.
  - The Stone Crusher, Concrete Mixer, both pits and the Fish Hatchery no longer show concrete: stone flagstones and coursed masonry, timber and steel instead.
- **Roof variety, no roof vents** on Chemical Works, Precision Machine Works, Electrolysis Plant, Cryogenic Liquefaction Plant and Cryogenic Tank Farm: corrugated-metal, steel-plate and timber flat roofs (placeable) mixed with teal plank gables and the sawtooth; every roof ventilator, cowl and vent lantern on them is gone.
- **Flat timber and metal roofs** on Chemical Works, Precision Machine Works, Cryogenic Liquefaction Plant and Water Treatment Plant are laid as separate boards and sheets instead of one stretched texture.
- **Roofs on the civic buildings:** the Public Health Lab and the Technical School have real teal plank gabled roofs, the Observation Deck's stairhead a teal pyramid roof and its kiosk a plank gable. The remaining flat roofs are timber or metal decks you can build on. No roof vents: the lab's ventilation shaft, the bathhouse lantern and the greenhouse ridge vents are gone, and chimneys rise from walls. The Greenhouse no longer shows concrete.
- **Fishery Works galleries, Materials Laboratory terrace and Reinforced Hydro Turbine terrace are player-path decks:** every flat roof tile on them can carry paths, platforms and buildings, like the Restaurant and Hospital balconies. Lay paths over them to reach the upper doors; their rails open where your paths cross.

## 0.6.0 (2026-10-29)

Changes since 0.5.0, the first Workshop release.

### Technical School
- **Self-study:** beavers now study at the Technical School in their free time instead of being taught by staff. Every adult tries to get educated, and a beaver can learn every profession. For example, three schools can teach all three professions.
- **Choosing the profession:** each school teaches one profession; pick it with the "Teach" buttons. A beaver graduates after 16 study hours for Metallurgy, 24 for Flight or 32 for Nuclear.
- **Supplies:** each profession consumes its own supplies per hour while someone studies it:
  - Metallurgy: Metal Block, Deep Alloy and Corn Ration.
  - Nuclear: Electronics, Yellowcake and Medicine.
  - Flight: Electronics, Recovered Telemetry and Packaged Food.
- **Seats:** the school seats 12 students. Selecting a school with students inside no longer crashes the game.
- **Panels:** the school panel shows the students inside, the adults still to learn the profession and the colony's specialists. The beaver panel lists the professions a beaver holds and its study progress.
- **Old saves:** a school saved as a staffed workshop loads with empty supplies.

### Balance
- **Much heavier construction costs.** Every Deep Frontier building costs 2 to 8 times as much, by its science tier:

  | Science unlock | Factor |
  |---|---|
  | up to 600 | ×2 |
  | up to 3,000 | ×3 |
  | up to 8,000 | ×4 |
  | up to 30,000 | ×6 |
  | above 30,000 | ×8 |

  The Nuclear Reactor now takes about 12,000 goods, more than double the vanilla Earth Repopulator's 5,500. Other examples: Launch Pad about 4,900, Hospital about 1,900, Deep Drill about 940. Large concrete and steel works now pay off.
- **Late-game science** now climbs steeply towards the reactor:

  | Building | Science |
  |---|---|
  | Mission Control | 30,000 |
  | Rocket Assembly Hangar | 50,000 |
  | Launch Pad | 80,000 |
  | Uranium Processing Plant, Waste Vault and the three sludge buildings | 200,000 |
  | Waste Refinery | 500,000 |
  | Nuclear Reactor | 1,000,000 |

  The Materials Laboratory (12,000) and the Hospital (25,000) are unchanged.
- **Power plants:**

  | Plant | Before | Now |
  |---|---|---|
  | Coal Power Plant | 5,000 hp | 25,000 hp |
  | Reinforced Hydro Turbine (full flow and head) | 9,600 hp | 40,000 hp |
  | Oil Power Plant | 20,000 hp | 90,000 hp |
  | Nuclear Reactor | 750,000 hp | 1,000,000 hp |

  Fuel use is unchanged.
- **Late buildings need much more power.** From 2,000 science up, a building draws at least about 5.65 × science^0.75 hp; buildings that already drew more keep their value. Examples: Smog Scrubber 2,000 hp (was 200), Technical School 1,800, Steel Mill 3,100, Hospital 11,000, Mission Control 13,000, Rocket Assembly Hangar 19,000, Launch Pad 27,000, Uranium Processing Plant 53,000 and Radioactive Waste Refinery 106,000. The Deep Well (power follows its boost slider) and the Reactor Charging Bay (5,000 hp) are exempt.
- **Smog Scrubber:** radius 20 tiles, up from 7, and it now removes all smog within that radius instead of 75%.
- **Drill bits:** the Deep Drill now wears out 0.1 High-Grade Steel an hour while it produces. The Deep Mine wears out 0.1 High-Grade Steel plus 0.1 Concrete (shaft lining) an hour. Each building keeps up to 15 of each, delivered by haulers, and stops with "Waiting for drill bits" when it runs out. A smaller crew uses less; a paused building none. The building panel shows the stock and how long it lasts.

### Nuclear Reactor
- **Falling power:** output now falls as the core heats instead of the reactor shutting itself down. Half the core heat means half the power, down to nothing at a meltdown. There is no automatic emergency shutdown any more; the manual SCRAM button remains.
- **Slow cooling:** the core cools exactly as slowly as it heats, 2.5% per hour. A reactor that lacks cooling more than half the time therefore keeps gaining heat and eventually melts down, even if it gets coolant 45% of the time.
- **Full waste heats the core:** a full store of Radioactive Waste or Radioactive Water in the reactor now heats the core just like running out of coolant, as long as it stays full.
- **Running or stopped:** a hot core with no coolant, or with full waste, keeps heating whether it is running, idle or shut down by SCRAM.
- **Safe stops:**
  - Pausing the reactor, or switching it off by automation, is still a safe cold shutdown. It cools at the same slow rate.
  - A short crew or overdue maintenance heats the core only up to 85%, so on its own it costs power but never causes a meltdown.
- **Panel:** the reactor panel shows current power output, waste and sludge storage, and the time to a meltdown or to cooling down.
- **Steel and concrete upkeep:** each reactor cycle seals its spent fuel in a cask of 1 High-Grade Steel and 2 Concrete. Each maintenance stop uses 20 High-Grade Steel and 40 Concrete from the reactor's stock; without them, maintenance waits.

### Radioactive waste
- **Simpler disposal:** the Radioactive Waste Export now dissolves spent-fuel casks in water and ships them off the map: 2 casks and 8 Water per hour. One building now disposes of casks, Radioactive Water and Contaminated Water, and the Waste Vault is just a buffer.
- **Waste Refinery:**
  - It no longer needs Chemical: 4 casks + 8 Water → 6 Radioactive Water.
  - It now also filters badwater: 10 Badwater + 1 Filter Media → 8 Water.
  - Vitrification (turning sludge back into casks) and mineral recovery are removed.
- **Recovered Minerals are retired:** nothing makes or uses them now. The reactor's 10 minerals in its build cost became 100 extra High-Grade Steel.
- **Renamed:** Radioactive Sludge is now **Radioactive Water**, since it is the same fluid the radioactive tide brings. The Sludge Outfall and Sludge Recovery Pump are now the Radioactive Water Outfall and Radioactive Water Recovery Pump. Existing saves keep their stock.

### Radiation
- **Hauling hazard:** a beaver carrying radioactive goods now has a small chance of being irradiated and needing hospital care. The chance is 2% per hour of carrying for Radioactive Waste or Radioactive Water (about 0.5% for a 15-minute haul) and 0.5% for Contaminated Water. Bots are immune, so they are the safe haulers for waste.
- Warehouses, piles and tanks holding radioactive waste, radioactive sludge or contaminated water can no longer be deleted until they are emptied. Before, deleting one threw the waste away.

### New buildings
- **Deep Well** (30,000 science, Water group): a small powered drill (1×2 tiles) that straddles a water source. Its leg stands on the ground beside the source and its drill head hangs over it. It works on ordinary sources, Water Seeps and badwater sources, and needs no workers.
  - **Boost:** a slider from 1× to 6× multiplies the source's flow, up to the game's limit of 8 per source cell. Power draw follows the slider, from 1,667 hp at 1× to 10,000 hp at 6×.
  - **Seeps and droughts:** a boosted seep no longer stops in deep water, and a boosted source keeps flowing through droughts.
  - **Drill bits:** it uses 0.05 High-Grade Steel per hour per boost step, delivered by haulers, and stops boosting without them.
  - **Radioactive tide:** a per-building checkbox (on by default) shuts the source off completely during a tide.
  - Fully waterproof.
- **Steel structures** (new "Steel structures" toolbar group under Paths), built from High-Grade Steel and Concrete:
  - Steel cantilevers 10, 12 and 15 tiles long, anchored on 1, 2 and 3 tiles.
  - Steel truss bridges spanning gaps of exactly 8, 10, 12 or 15 tiles; only the near end needs support.
  - Steel columns 1 to 6 high that stack. 3×3 and 5×5 steel decks rest on four corner columns, so the corners can stand at different ground heights.

### Maps
- **Every built-in map now works with Deep Frontier.** When you start a new game on any of the 19 built-in maps, Deep Frontier places that map's resources once at the start: deep ore veins and sources, limestone and sandstone outcrops, a limestone seam and Human Record Caches. Loading a save never places them again.
- **Taller build height:** these new games also get a 66-layer build height (vanilla 33), kept through Map Transformer, so the tall late-game buildings fit. The terrain itself is unchanged.
- **Three maps are EXTREMELY difficult.** Diorama and Cliffside are far smaller than the Deep Frontier late game needs. Beaverome is large, but it has no room for a Deep Mine and no deep ore at all; any map without a Deep Mine site gets the same warning. A warning appears when you start one of them, listing what the map can't provide.
- **Maps that can't host everything:** many built-in maps have no site for some late-game buildings; for example, 11 maps have no room for the Nuclear Reactor. A short notice at the start of a new game lists what that map can't provide.
- **Fuller Deep Ore Sources:** a Deep Ore Source now holds up to 10,000 deep ore (was 4,000). Every map with Deep Drill sites has 17,000 or 18,000 deep ore in its sources (was 4,000 to 6,000). That is enough to build one of each building with a little to spare; the rocket launches still need the Deep Mines.
- The Deep Frontier map files (Plains, Plains Hard, Lakes, Terraces) are rebuilt with the fuller sources: 18,000 deep ore on Plains and Plains Hard, 17,000 on Lakes and Terraces. Their layout is unchanged. Plains Hard's radioactive spring is only on that map file, not on built-in Plains.

### Reactor Bots
- **Retrofit:** any bot can be upgraded in place to a **Reactor Bot**, keeping its name. Press "Retrofit to Reactor Bot" on its panel. It then fetches a Reinforced Bot Frame (Precision Machine Works) and a Reactor Power Cell (Uranium Processing Plant) from storage and is upgraded once it has both.
- **Buffs:** a Reactor Bot carries 5× as much, moves 4× as fast, lasts 10× as long (700 days) and needs charging only a quarter as often (about every 7 days).
- **Look:** gunmetal plating and an amber glow.
- **Upkeep per bot:**
  - **Coolant:** 1 Reactor Coolant Water (or 0.5 Cryocoolant) a day.
  - **Plating:** 0.2 High-Grade Steel (or 0.1 Alloy) a day. Without it the bot wears out 5× faster.
- **Reactor Charging Bay** (250,000 science, beside the Charging Station): charges two Reactor Bots at once, draws 5,000 hp and burns a little Enriched Fuel while charging. Ordinary bots keep using ordinary charging stations.

### Interface
- Deep Frontier's buildings sit in nine toolbar sub-groups: deep mining, quarries and cement, heavy industry, nuclear fuel, rocketry, concrete scaffolds, concrete side platforms, radioactive waste and civic services.

### Performance
- **Lighter building models:** 43 models are lighter. The mod's finished models drop from about 906,000 to 632,000 triangles in total, and no building exceeds 20,000 (ordinary buildings 12,000). Large buildings were up to 37,000 before. This means less memory, faster loading and smoother placement previews. Footprints, entrances, chimneys and animations are unchanged.
- **New connection spots:** some late-game surfaces are now flat, so a few late-game buildings accept power shafts and pipes in new places. Most of these are on the Nuclear Reactor. No existing connection spot or buildable roof tile was removed.
- **Power networks:** splitting a power network no longer slows down with the network's size. Before, deleting, pausing or flooding one building on a very large network could freeze the game. This mattered most with mods that turn every building into a power shaft.
