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

### Nuclear Reactor
- **Falling power:** output now falls as the core heats instead of the reactor shutting itself down. Half the core heat means half the power, down to nothing at a meltdown. There is no automatic emergency shutdown any more; the manual SCRAM button remains.
- **Slow cooling:** the core cools exactly as slowly as it heats, 2.5% per hour. A reactor that lacks cooling more than half the time therefore keeps gaining heat and eventually melts down, even if it gets coolant 45% of the time.
- **Full waste heats the core:** a full store of Radioactive Waste or Radioactive Sludge in the reactor now heats the core just like running out of coolant, as long as it stays full.
- **Running or stopped:** a hot core with no coolant, or with full waste, keeps heating whether it is running, idle or shut down by SCRAM.
- **Safe stops:**
  - Pausing the reactor, or switching it off by automation, is still a safe cold shutdown. It cools at the same slow rate.
  - A short crew or overdue maintenance heats the core only up to 85%, so on its own it costs power but never causes a meltdown.
- **Panel:** the reactor panel shows current power output, waste and sludge storage, and the time to a meltdown or to cooling down.

### Radiation
- Warehouses, piles and tanks holding radioactive waste, radioactive sludge or contaminated water can no longer be deleted until they are emptied. Before, deleting one threw the waste away.

### Interface
- Deep Frontier's buildings sit in nine toolbar sub-groups: deep mining, quarries and cement, heavy industry, nuclear fuel, rocketry, concrete scaffolds, concrete side platforms, radioactive waste and civic services.

### Performance
- **Lighter building models:** 43 models are lighter. The mod's finished models drop from about 906,000 to 632,000 triangles in total, and no building exceeds 20,000 (ordinary buildings 12,000). Large buildings were up to 37,000 before. This means less memory, faster loading and smoother placement previews. Footprints, entrances, chimneys and animations are unchanged.
- **New connection spots:** some late-game surfaces are now flat, so a few late-game buildings accept power shafts and pipes in new places. Most of these are on the Nuclear Reactor. No existing connection spot or buildable roof tile was removed.
- **Power networks:** splitting a power network no longer slows down with the network's size. Before, deleting, pausing or flooding one building on a very large network could freeze the game. This mattered most with mods that turn every building into a power shaft.
