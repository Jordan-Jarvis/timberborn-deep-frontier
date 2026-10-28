# Height layers for the industrial buildings

The user required actual game height quantization on 2026-10-19. Functional levels are now explicit source constants in `tools/asset-pipeline/industrial_levels.py`. They are chosen before building geometry; there is no rounding, automatic scaling or bounds repair during export.

## Verified units

Installed Timberborn 1.1.2.8 `CoordinateSystem.GridToWorld` returns `(x,z,y)` with no scale factor. `GridToWorldCentered` adds half a cell horizontally and no vertical offset. The official Timbermesh exporter maps Blender `(-x,z,-y)` into Unity coordinates. Therefore **one Blender Z unit is one game height layer**. Evidence: `outputs/navigation-api-1.1.2.8/CoordinateSystem.cs` and the official exporter `node_builder.py`.

| Building | Structural walking floors | Player-built vanilla access | Declared vertical envelope |
| --- | --- | --- | --- |
| Crusher | 2 | 0 → 1 → 2 | 5 layers |
| Kiln | 2 | Front/rear approaches, each 0 → 1 → 2 | 6 layers |
| Quarry | 1, 3, 5, 7 | Entrance 0 → 1 | 9 layers |

Integral stair flights are removed at the user's request. Cleared approach bays accept player-built vanilla stairs; adaptive rails guard their upper exits. Quarry ladders remain in the mast at unit layers 1 → 2 → 3 → 4 → 5 → 6 → 7, with galleries at 3, 5 and 7. The declared envelopes are source limits checked against actual bounds, not solid rectangular collision volumes.

The user explicitly clarified the same **0 / 1 / 2** arrangement for both kiln and crusher: the doorway starts at layer 0, the little roof above the door begins at layer 1, and the actual surface where beavers walk is at height 2. Railings rise above that layer-2 walking surface. The porch roof is pitched artwork in the layer-1 band, with its front beam underside at height 1; it is not an extra path deck. `FACTORY_ENTRANCE`, `FACTORY_PORCH_ROOF`, and each building's deck constant drive these positions. Native entrance/grid bindings remain to be exported.

For the quarry, preserve every existing entrance and the existing layout. Its front operator doorway is at layer 0; its existing deck-level doorways stay at layer 1. The user explicitly prohibited adding, removing or relocating doors during this height correction. Only the front doorway, threshold and adjacent wall/support bottom elevations change; the canopy, X/Y positions, door dimensions and all deck entrances remain as modeled. `QUARRY_ENTRANCE=0` also drives its authored idle anchor.

## Authoring rules

- Structural support surfaces, path connections and ladder/stair endpoints use whole height layers. Native path surface thickness and character foot offsets remain separate from the structural floor datum.
- A native-style straight stair rises one layer across one horizontal cell. Each authored layer has eight small visual treads. The stair helper rejects fractional endpoints or a different slope. Multi-cell flights still require explicit native edges and a verified height provider during integration.
- Roof pitches, timber thicknesses, rail heights, machinery, pipes, doors and window frames retain detailed fractional dimensions. Only an explicitly designated support surface becomes stackable; a roof's visual peak does not create a stacking surface.
- Machinery is attached rigidly to the chosen deck without stretching drums, rollers or other parts. `MountedMachinery` uses an explicit assembly reference plane and matching pivot placement. Lower walls, piers, ceilings, discharge chutes and stairs are authored separately from the whole-layer constants. This is source assembly placement, not inferred normalization of mesh bounds.
- Height manifests are emitted beside the scenes. Validation checks every rail run's floor against the declared layer set, physical floor/headroom along intended routes, source animation, and the declared upper envelope. Invalid authoring stops with an error.
- Horizontal grid origin, occupied cells, entrance/hauling cells, power and external transport ports, collision and adaptive railing openings must agree before export. Do not round existing X/Y artwork coordinates into a route graph. Height alignment alone does not establish native pathing.

The prior crusher 1.50 and kiln 1.29 deck datums are retained solely as local machinery reference frames so accepted detailed assemblies keep their proportions. Their new physical work decks are both at Z=2. The quarry's prior long decorative stair was rebuilt as a one-layer, one-cell flight ending at its actual apron edge.

The installed gameplay blueprints and workbook have not yet been given these new model footprints. Update all of those together after the complete horizontal layout and collision/support occupations are authored. Current pictures remain Blender reviews. Native movement, district reach, standing idle workers, hauling, rotations and save/reload still require an official build and a fresh game process.
