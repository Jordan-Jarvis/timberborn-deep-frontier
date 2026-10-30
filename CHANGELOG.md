# Changelog

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
- **Nuclear reactor:** 800,000 hp, up from 750,000.
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
