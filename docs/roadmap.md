# Roadmap

## Milestone 0: environment

- [x] Official tools and Mod Manager source cloned.
- [x] Unity editor version identified: 6000.5.11f1.
- [x] Game build identified: 1.1.2.8.
- [x] Ghidra downloaded and extracted.
- [x] Create the namespaced Deep Frontier mod shell, manifest, assembly definition, and standard `IModStarter`/Configurator entry point.
- [ ] Install Unity 6000.5.11f1 through Unity Hub.
- [ ] Create a copied Deep Frontier source map with Map Transformer, add a conservative lower-sector Z budget, and validate save/load before placing mod content.
- [x] Capture dependency package IDs/versions in `tools/installed_dependency_manifests_1_1.json`.
- [ ] Create a clean development mod profile and verify the pinned dependency set together.

## Milestone 1: vertical slice

- [x] Stage the Deep Frontier shell into the official Unity project and import the first vertical-slice blueprints cleanly in Unity.
- [x] Add one authored Deep Ore source marker, Deep Ore good, and powered Deep Drill building.
- [x] Make the first source loop playable with a finite authored Deep Ore stockpile; document the Map Editor authoring path.
- [x] Add an indefinite Deep Ore vein and Deep Mine branch constrained by the vanilla understructure system.
- [x] Add Deep Alloy good, recipe, and powered surface processor.
- [x] Add new Deep Frontier Blender geometry, icon art, texture sources, and Timbermesh exports.
- [ ] Verify the staged mod loads in-game and the two buildings appear in the Iron Teeth build menu.
- [ ] Add one authored lower sector, shaft, and vertical material route.
- [ ] Connect one pipe, conveyor, and power adapter to a surface processor.
- [ ] Test save/load and missing-dependency behavior.

## Milestone 2: industrial chain

- [ ] Coal, oil, sulfur, copper, and uranium recipes.
- [ ] Waste/badwater outputs and treatment.
- [ ] Machine starvation, shutdown, and recovery states driven by inputs, power, storage, and optional hazards; no universal maintenance simulation.
- [ ] Add the nuclear branch as a compact 50,000–100,000 hp industrial power option, with constant coolant, bounded meltdown risk, locked waste custody, badwater conversion, and radiation pockets.

## Milestone 3: exploration narrative

- [ ] Survey milestones and unlock pre-authored lower sectors or map variants; keep runtime map resizing experimental.
- [ ] Human facility discoveries and badwater provenance.
- [ ] Cryogenic water splitting, hydrogen/oxygen liquefaction, rocket components, launch complex, and mission work orders.
- [ ] Endgame scenario, launch missions, and world-state progression.

The detailed implementation order, API boundaries, balance targets, nuclear design, rocket chain, and player routes are in [implementation-plan.md](implementation-plan.md).
