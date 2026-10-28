# Sandstone and limestone pits

Both models follow the front and rear **isometric** pit illustrations in
[the mining reference](../../concepts/01-mining-and-sources-concept-v1.png).
Top views and printed dimensions were excluded.

The sandstone yard has a sorting grate and a stone-catching tray. Limestone
uses a loaded cart and a separate workbench canopy. Both have an enclosed
store room, ground-level arched entrance, framed windows, braced hand winch,
moving basket, sheaves, cable and native barrel. Wood, roof and structural
metal use the shipped Iron Teeth materials. There are no character meshes.

- [Sandstone front](SandstonePit-front.png)
- [Sandstone opposite angle](SandstonePit-front-right.png)
- [Sandstone rear](SandstonePit-rear.png)
- [Limestone front](LimestonePit-front.png)
- [Limestone opposite angle](LimestonePit-front-right.png)
- [Limestone rear](LimestonePit-rear.png)

The first render was revised to lower the roof and hoist, expose the stone bin,
replace a slab beneath the grate with a real catch tray and individual stones,
and remove the multicolored detail texture from the cable.

[Source validation](source-validation.json) checked 50 door-approach samples per
model, native atlas UVs and all 121 animation frames. The basket rises 0.35 units;
its cable remains attached and no basket/static mesh intersections were found.
These are source-art checks; native evidence is recorded below.

Canonical sources are `SandstonePit-ReferenceStudy.blend` and
`LimestonePit-ReferenceStudy.blend` in `src/DeepFrontier/Art/Source`.
Geometry comes from `tools/asset-pipeline/pit_isometric_geometry.py`.
The game registration follows the completed artwork: 5×5×4 and
6×5×4, respectively, with no mesh scaling.

The official export preserves seven nodes, three animation tracks and all 121
frames. The native barrel remains an external game asset. Build 85 passed native
placement, both workers' harvesting/delivery, mineral selection, actual basket
movement and stationary paused hoists. Both shortened test deposits saved with
22 remaining and two stone delivered. Fresh-process reload 85 restored those
exact identities, reserves and stocks, then delivered the remaining 22 units
of each mineral and removed both exhausted source entities. Both captured
saves passed exact stock/yield conservation.
Existing cramped prototype pit placements need rebuilding for these larger footprints.

[Native game view, build 85](Pits-native-build85.jpg)

Build 85 loaded optional placement and universal power modifiers. Their effects
made the non-supporting pit roof appear Solid and added power connections.
Both were disabled for main/reload 86. Those runs passed effective ground-only
placement, rejection of floating pits and roof platforms/paths, and absence
of a power node, followed by the same harvesting, animation and exact
save/reload/depletion checks.

[Correct native panel and placement profile, build 86](Pits-native-isolated-build86.jpg)
