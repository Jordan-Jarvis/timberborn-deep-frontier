# Deep Ore source authoring

Deep ore comes from two map objects: finite Deep Ore Sources, which Deep Drills bore, and permanent Deep Ore Veins under Deep Mines. Neither scans terrain or patches the game's mine targeting.

## Deep Ore Source

A Deep Ore Source is a deposit (`DeepOreDepositSpec`, `src/DeepFrontier/Scripts/DeepOre/DeepOreDeposit.cs`), not a stockpile. Only the Deep Drills of its district take from it: no hauler, district supply, pipe or storage mod can.

- **Amount.** Up to 10,000 Deep Ore (`Capacity`). A newly placed source holds 10,000, as the map editor fills a new fixed stockpile to its capacity. The map editor panel has an amount field (the native fixed-stockpile layout without its good list), with undo. The new-game setup of the built-in maps sets each source's amount from `tools/map_variants` (8,500 on most maps).
- **District.** The source has an entrance: connect it to the drill's district with a path.
- **Recharge.** Once empty, the source regains 20 Deep Ore after 5 days and holds no more than that until drilled empty again, as a bush regrows its yield after it is gathered. The timer is the native time trigger and is saved with the source. It never runs in the map editor. The numbers and their reasons are in `docs/progression.md` ("Deep Ore Source recharge").

## Deep Drill

The drill's recipe is 3 Water -> 1 Deep Ore per two-minute cycle (1,000 hp, Metal Block drill bits). The cycle's ore comes out of a Deep Ore Source in the drill's district, the nearest by road first, then the one holding most (`DeepDrillSpec`, `src/DeepFrontier/Scripts/DeepOre/DeepDrill.cs`). The drill stops when no source in its district holds ore. Its panel then shows the soonest recharge, and its status reads "Deep Ore Sources recharging", or "No Deep Ore Source in the district" when there is none. The ore it makes leaves through its output like any product: haulers, belts or tubeways.

## Author a map

1. Open the map in the Map Editor with Deep Frontier enabled.
2. Place a Deep Ore Source from the map objects group, with its entrance on reachable ground.
3. Set its amount in its panel. For a built-in map variant, set the placement's `good` (`DeepOre`) and `amount` in `tools/map_variants/<map>.json` instead.
4. Save the map and start a new colony from it.

`tools/prepare_deep_frontier_map.py` checks every built-in variant:
- the drillable sources must hold the deep ore of one of each building up to the Deep Mine, plus 5%, without counting the recharge;
- the recharge must stay a trickle (`deepOreRechargeMinDays`).

See `docs/maps.md`.

## Permanent source

The permanent path follows vanilla's finite scrap versus mine distinction:

1. Place a `DeepOreVein` map-editor understructure. The vein never runs out.
2. Unlock and build `DeepMine.IronTeeth` on it. The placement contract requires the vein, so the permanent recipe is not a free surface resource.
3. Supply the mine with 12 Water per two-minute cycle and its power; each cycle makes 4 Deep Ore indefinitely.

The drill phase is cheaper and earlier and bootstraps the first Deep Iron chain. The mine is deliberately expensive (footprint, workers, science, construction materials, water and power) and is the real supply: the recharge of emptied sources keeps a colony that missed it limping along, nothing more.

## Saves from before the deposit (2026-11-03)

Until 2026-11-03 the source was a native fixed stockpile that haulers emptied into the drill.

- A source saved then loads its stockpile's Deep Ore as its amount; this also covers map files built then.
- An emptied old source starts recharging.
- A drill saved mid-cycle keeps that cycle's ore.
