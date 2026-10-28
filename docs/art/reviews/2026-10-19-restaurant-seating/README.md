# Restaurant seating correction

The source chair positions and Sitting anchors were corrected after the user observed guests sitting through chairs and tables, with some chairs intersecting rails. Front chairs face across the balcony, anchors sit at the modeled seat surfaces, and chair/table spacing has increased. The latest revision lowers tabletops by 0.10 tile to 0.58 above the deck in response to the user's follow-up. The animated sign now hangs outside the front deck on extended brackets, with at least 0.50 tile clearance throughout all 61 frames. Building layout, doors, native materials, plants and terrace construction areas are retained.

These are Blender renders, not in-game acceptance:

- [Front](Restaurant-front.png)
- [Front right](Restaurant-front-right.png)

`review-manifest.json` records the changed scene and its previous approved hash. `outputs/civic-integration/static-checks.json` checks actual exported marker positions and facing, all fourteen chair-to-rail clearances, the native material UV bounds, existing rail bindings and graph connectivity.

Official build 41 was installed and inspected in a fresh game process. [Seated adults and a child at the lower tables](restaurant-tables-build41.png) show clear tabletop/face separation and chairs inside the rails. [The game overview](restaurant-overview-build41.png) shows the banner hanging outside the front deck. The capture includes native thirst warnings on waiting guests and staff; service only grants effects when a meal is actually served. These captures establish the shown poses and angle, not every frame of every native animation.

The marked fixture passed real water consumption/effects, cake production, optional coffee, saved service with no duplicate meals, safe guest release during pause/power loss/off-duty periods, and resumed service. `Restaurant regression - verified` is saved and paused for inspection. The wider expansion remains unfinished; see `tools/STATUS.md`.
