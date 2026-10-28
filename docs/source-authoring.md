# Deep Ore source authoring

The current source path uses supported stockpile, manufactory, and understructure contracts. It does not scan terrain or patch the game's private mine-targeting code.

## Author a deposit

1. Open the copied Deep Frontier map in the Map Editor with Deep Frontier enabled.
2. Choose the Deep Ore Source object from the Map Editor objects group.
3. Place it in the lower sector or basin where the resource should be exposed.
4. Set its stored good to `DeepOre` and fill it with up to 4,000 units. A 1,000–2,000 unit deposit is a useful first playtest size.
5. Save the map and start a new colony from that map.

The source marker is a finite stockpile. A Deep Drill consumes one Deep Ore and three Water per cycle, draws 1,000 hp, and outputs one Deep Ore to its normal output inventory. The input quantity therefore leaves the source stockpile, while the extracted unit can be moved by haulers, Conveyor Belts v2, or Powered Tubeway to storage and the Deep Ore Processor.

The processor consumes two Deep Ore and one Water per cycle, draws 500 hp, and produces one Deep Alloy. Both machines retain ordinary hauler logistics as the fallback path. Timber Pipes, Pump to Tank, Power Lines, and conveyor endpoints are integration work after this authoring loop passes a real save/reload test.

## Permanent source path

The permanent path deliberately follows vanilla's finite scrap versus mine distinction:

1. Place a `DeepOreVein` map-editor understructure in the lower sector while authoring the map. The vein has no stockpile capacity and never runs out.
2. Unlock and build `DeepMine.IronTeeth` on that vein. The placement contract requires the `DeepOreVein` understructure, so the permanent recipe is not a free surface resource.
3. Supply the mine with 12 Water per two-minute cycle and 4,000 hp. Each completed cycle emits 4 Deep Ore indefinitely.
4. Use belts, tubeways, power lines, or the installed pump/tank chain to move the mine's output and water. The mine does not require finite Deep Ore input.

The finite drill remains useful because it is cheaper, appears earlier, and can bootstrap the first Deep Alloy chain. The permanent mine is deliberately expensive in footprint, workers, science, construction materials, water, and power so it becomes the sustainable branch rather than an automatic replacement on the first cycle.

The implementation uses the verified vanilla understructure mechanism. Runtime vein discovery and automatic vein depletion are intentionally out of scope: the map author places the vein, and normal understructure placement rules enforce the mine location.

## Prototype limitation

The source marker currently behaves as an authored stockpile rather than a terrain vein entity. This is intentional: it makes the first resource loop playable with the 1.1 data contracts and keeps saves portable. A later runtime adapter can replace the stockpile input with explicit node selection and depletion without changing the Deep Ore good, processor recipe, or player-facing progression.
