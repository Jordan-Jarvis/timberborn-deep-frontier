# Reinforced hydroelectric turbine study

Build 105 shared-reservoir review: [two turbines passing contaminated water](Turbine-basins105-badwater.jpg). The same accepted models operate at independent 0.75/1.5 m³/s limits, supplying 2,400/4,800 native hp. Full-column water/contamination accounting, reverse pressure and drought checks passed; no art or hydraulic tuning changed. The enclosing terrain and concrete wall are a disposable test fixture. Report: `outputs/hydro-basins-verification105.json`.

Build 103 sound/motion review: [paused native outlet view](Turbine-native-reload103-outlet.jpg). Geometry and materials are unchanged from 101. Fresh-process acceptance measured four-times animation playback, native spatial mechanical audio, Pause/closure silence and resumed operation at 0.75 and 3 m³/s; peak native output was 9,600 hp. The later manual review had a lower reservoir head after drawdown. The game was left paused. Exact measurements and save/reload evidence are in `outputs/hydro-continuity103.json` and `outputs/hydro-reload-measurements103.json`.

Current revision: [two-cell front](two-cell/ReinforcedHydroTurbine-front.png) and [two-cell rear](two-cell/ReinforcedHydroTurbine-rear.png). The casing is four tiles wide with a two-tile clear opening; the powerhouse moves one tile sideways. This aligns the visibly wide mouth with two real native water lanes. New registration is 8×10×7, with 21 support cells. Source `ReinforcedHydroTurbine-ReferenceStudy.blend` SHA256: `db8808854daaf3335fd8161fdc930a53c4b4b2622e21182f6ca0bbfaaa1cd04f`. Both animation loops, 164 walking-clearance samples, 32 cap-support samples and native UVs passed. Export SHA256: `5219490bae96f4c4fca0197ae2acc5a089bcd89e798f97577478f0b4c1c8ad5c`. Native main 100 passed both wet water lanes, 3 m³/s total, 9,600 native shaft hp and stable shutdown under outlet blockage. The final mouth now extends to its six-tile physical water-wall boundary, removing the invisible wall extension seen beyond the earlier casing. Fresh-process reload 101 passed all 709 saved identities, controls, wiring, renewed generation, animation, Pause/Resume and five walking destinations. The final UI review showed 3.000 m³/s, 15.19 layers of head and 9,113 native hp. [Current outlet view](Turbine-native-reload101-outlet.jpg) · [Current power panel](Turbine-native-reload101-power.jpg). [Earlier main 100 screenshot](Turbine-native-main100.jpg).

The [original concept](<../../concepts/Reinforced Hydro Turbine v1.png>) supplies the two isometric views. No top-down plan or footprint count is used.

The first Blender study has a continuous arched water conduit, intake grille, visible downstream runner, six-layer concrete cap, enclosed Iron Teeth workshop, generator housing, pressure instruments and a layer-two service terrace. The workshop door opens onto that terrace; stairs will be player-built. The shaft coupling and runner have separate 121-frame animation loops. Rail panels are separate nodes for the existing adaptive-rail system.

[Front render](ReinforcedHydroTurbine-front.png) · [Rear render](ReinforcedHydroTurbine-rear.png)

That first source is preserved as `src/DeepFrontier/Art/Source/ReinforcedHydroTurbine-ReferenceStudy-v1.blend`, SHA256 `d293976bba3de084112eaa56a2ab600fd27f550826a6d6076f475e4a6fcaab53`. Authoring source: `tools/asset-pipeline/hydro_isometric_geometry.py`.

The first render exposed labels on fittings because the native `Details.IronTeeth` sheet contains crate and sack decorations, not brass. The hardware now explicitly uses `BaseMetal.IronTeeth`, including the helper-generated handwheel, gauge rims, fasteners and rail caps. No existing building was regenerated. A raised service hatch was also made flush with the walking surface.

Saved-source validation passed 164 route samples with a 0.2 body radius and 1.1 headroom, 24 support samples on the cap, 149,136 bounded native UV corners, and all 121 frames of both loops. The runner remains within the conduit. Report: `outputs/hydro-source-checks.json`; script: `tools/asset-pipeline/validate_hydro_source.py`.

The first arrangement put the workshop across the intended dam wall. The downstream revision translates that complete assembly four layers along the conduit axis, preserving its scale and details while leaving both sides of the cap open for adjoining dam blocks.

[Earlier downstream front render](downstream/ReinforcedHydroTurbine-front.png) · [Earlier downstream rear render](downstream/ReinforcedHydroTurbine-rear.png)

That source is now preserved as `outputs/ReinforcedHydroTurbine-before-two-cell.blend`, SHA256 `ff29c317edf0c6932428c83b52c30aa414d2d708fceb20fdd84f9ab39ec31580`. Its registration was 7×10×7; the dam cap supports construction at layer 6 and the service terrace at layer 2.

Official Timbermesh export contains 105 nodes, two 121-frame tracks, thirteen walking cells and fourteen adaptive rail openings. Export SHA256: `e276a197a663dbd760683507c76722182eef82e533766c50d429dad8ece5f6a3`. Official build 97 installed all 468 matching package files. All 47 authored template model bindings passed.

The renders above are Blender views. The conduit intentionally contains no decorative water mesh; operating water comes from the native world simulation.

[Daylight in-game view, main 97](Turbine-native-main97.jpg) · [Control panel, main 96](Turbine-native-main96-panel.jpg)

Main 97 passed four rotations, native shafts, stairs, deck/cap platforms, selective rails, retained reservoir water, measured 0.25/1/3 m³/s discharge, rotor motion, manual closure, lever Off/On, native Pause/Resume, blocked-outlet cessation and five actual walking destinations. The test deliberately places and demolishes trial turbines; the loose piles around the outlet are native demolition rubble, not authored decorations. The native save is preserved as `outputs/hydro-verified-build97.timber`. Fresh-process reload 97 restored every recorded identity, control and wire, then passed measured operation, Pause/Resume and the same five walking destinations. [Reload screenshot](Turbine-native-reload97.jpg). Broader hydraulic and balance coverage remains pending; see `tools/STATUS.md` and `docs/hydroelectric-construction.md`.
