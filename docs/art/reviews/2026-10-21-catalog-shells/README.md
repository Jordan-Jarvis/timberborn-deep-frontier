# Catalog exterior repair review — 2026-10-21

These are exact-source Blender reviews. The manifest records the canonical saved scene and SHA-256 for every model, image hashes, current overlap reports, and the source/audit code hashes. The original scenes remain in `src/DeepFrontier/Art/Source`.

All 18 listed scenes passed the current visible-overlap check. The 11 architectural scenes below were reviewed from both isometric directions. Separate declared-surface tests covered 26 contracts and 1,088,252 samples; window backing tests covered 176 windows and 880 samples. Both reported zero findings.

| Model | Front | Rear | Review |
|---|---|---|---|
| GroceryStore | [Front](GroceryStore-front.png) | [Rear](GroceryStore-rear.png) | Closed walls and attached windows. Terrace has wall-mounted cantilevers instead of dangling outer posts; terrace footprint preserved. |
| FisheryWorks | [Front](FisheryWorks-front.png) | [Rear](FisheryWorks-rear.png) | Closed hall and warehouse shells; rear net drapes and open water equipment are intentional. |
| FishHatchery | [Front](FishHatchery-front.png) | [Rear](FishHatchery-rear.png) | Closed nursery cabin; side windows fit the forward wall bays below collars. Water baskets and channels remain open. |
| ReinforcedHydroTurbine | [Front](ReinforcedHydroTurbine-front.png) | [Rear](ReinforcedHydroTurbine-rear.png) | Closed dam/conduit shell and attached workshop windows. Both conduit mouths remain intentionally open; rear review uses temporary fill lighting. |
| MaterialsLaboratory | [Front](MaterialsLaboratory-front.png) | [Rear](MaterialsLaboratory-rear.png) | Closed asymmetrical laboratory shells, attached windows and roof bearings. Heavy external bracing across window fields is retained. |
| StoneCrusher | [Front](StoneCrusher-front.png) | [Rear](StoneCrusher-rear.png) | Closed operator workshop and entry porch; open upper crusher machinery is intentional. |
| CementKiln | [Front](CementKiln-front.png) | [Rear](CementKiln-rear.png) | Closed operator walls and porch beneath the kiln canopy; rotary processing equipment remains visible. |
| MineralQuarry | [Front](MineralQuarry-front.png) | [Rear](MineralQuarry-rear.png) | Closed workshops, ground cabin and rear control room; open hoist frame and transfer equipment are intentional. |
| ConcreteMixer | [Front](ConcreteMixer-front.png) | [Rear](ConcreteMixer-rear.png) | Closed operator room and porch; exposed mixing machinery and underside structure are intentional. |
| SandstonePit | [Front](SandstonePit-front.png) | [Rear](SandstonePit-rear.png) | Closed sloping cabin walls, front header and roof bearing; attached native windows. |
| LimestonePit | [Front](LimestonePit-front.png) | [Rear](LimestonePit-rear.png) | Closed sloping cabin walls, front header and roof bearing; attached native windows. |

The seven structural models have fresh source-bound overlap reports in this folder, but this review does not claim a new visual render pass for them: SandstoneMasonryBlock, LimestoneMasonryBlock, ConcreteBlock, ConcreteOverhang8x1, ConcreteScaffold3x3, ReinforcedDamBlock, ConcreteOverflowDam.

Open machinery, scaffold space, water baskets and conduit mouths are intentional. Occluded overlap candidates remain recorded; zero visible candidates is not a blanket claim that all geometry overlaps were removed.

This evidence does not certify native shaders, beaver paths, platform placement, hitboxes or gear connections. The broader catalog includes prototypes whose detailed art and tile-grid redesign remain a separate tracked task.
