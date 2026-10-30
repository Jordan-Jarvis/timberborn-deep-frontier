# Changelog

## Unreleased

### Smaller buildings (compaction pass)
- **Cement Kiln** is 5x3, 4 high (was 7x5, 6 high): a closed feed house, the rotary drum under a lean-to roof on stone blocks, the stone firebox with its fire and chimney. The open timber trestle and raised drum deck are gone.
- **Concrete Mixer** is 4x3, 3 high (was 7x5, 7 high): the hoppers sit on the operator room's roof, the drum stands on low concrete piers, the water tank on a concrete pedestal. The tall timber feed tower and tank tower are gone.
- **Deep Drill** is 7x6, 8 high (was 11x9, 16 high): a boarded drilling tower on a solid concrete engine room, open at the front so the hoist shows. The open lattice derrick, the pier substructure, the pipe ramp, the pipe rack and the separate power house are gone. Same cost, power, crew and drill-bit upkeep.
- **Deep Mine** is 7x6, 7 high (was 10x11, 16 high): a compact plated headframe on a low concrete shaft house, both skips riding in its open front under twin sheaves; the winding drum and flywheel turn on the deck, the skips tip into an ore bin and an ore tub runs out along a short track. The open lattice headframe, drum shed, engine house, stilted ore bin with its tipple and the bath house are gone. Same cost, power, crew and upkeep; it still stands over its Deep Ore Vein; a mine that was placed flipped needs re-placing over its vein.
- **Limestone and Sandstone Quarry** are 8x6, 5 high (was 11x7, 9 high): a boarded headframe over the shaft with its sheave, a flat-roofed winding house with the drum, and the sorting line on a stone plinth. The ladder mast and lattice tower are gone. Old quarries keep their place over the seam.
- **Sandstone and Limestone Pit** have one storey under a flat roof (3 high, was 4); the hoist jib is lower. The flat roof can carry platforms.
- **Stone Crusher** stays 4x4 but is 3 high (was 5): its workshop is one layer under the machine floor, and the roll and hopper roofs are flat.
- **Old saves:** both keep their origin and entrance; freed tiles become empty ground. Reconnect a pipe at the mixer's water inlet (now on the tank pedestal) and its power line. A placed Deep Drill keeps its origin and entrance too (a flipped one's entrance moves 4 tiles); reconnect its shafts and pipes to the new walls.

### Smaller late-game buildings (compaction pass: power, nuclear, rocketry)

- **Coal Power Plant** is 4x4, 6 high (was 5x5, 10 high). The boiler house has a flat roof with the coal bunker on it, and the chimney is shorter. Same cost and output.
- **Oil Power Plant** is 5x4, 6 high (was 6x6, 9 high). The turbine hall has a flat roof with the two fin-fan coolers on it; the barrel vault and the cooler frame over the tanks are gone. Same cost and output.
- **Old saves:** both plants keep their origin and entrance; a flipped plant's entrance moves one tile. Reconnect shafts and pipes to the new walls.

### Smaller civic buildings (compaction pass)
- **Restaurant** is 5 high (was 9) on the same 9x7 footprint: one layer per storey, both dining balconies with all their tables and chairs, a flat timber-decked roof level with the roof terrace, the sign swinging from a gantry on the roof. The gabled roof, dormers and lantern are gone.
- **Hospital** is just its central pavilion: 4x9, 9 high (was 12x9). The two ward wings are gone; the pavilion, its doors, rear decks and roof garden are unchanged. Same cost, power, crew and 30 beds.
- **Grocery Store** is 5 high (was 8) on the same 9x6 footprint: one layer per storey, the balcony one layer up (one stair reaches it), the gable roof and lit monitor kept.
- **Old saves:** the Restaurant and Grocery keep their place and entrance, but paths, stairs and platforms on their old balconies need re-placing. Re-place an old Hospital: its remaining pavilion now sits on the old west wing's tiles.

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
