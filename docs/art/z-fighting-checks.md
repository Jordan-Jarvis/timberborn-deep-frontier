# Building surface overlap checks

The Blender geometry detector in `tools/asset-pipeline/zfight_audit.py` locates near-coplanar, overlapping surfaces in the saved detailed building scenes. It includes evaluated modifiers, the requested animation pose and native preview prop meshes. It writes exact object/face/material records and an optional grey render with red overlap regions. It never modifies or saves the source model.

## Use

Run from the project directory in PowerShell:

```powershell
# Diagnose a building and produce a marked image.
./tools/check_building_surfaces.ps1 -Models Restaurant -Render -ReportOnly

# Check multiple poses of moving geometry; fail on visible candidates.
./tools/check_building_surfaces.ps1 -Models FisheryWorks -Frames '1,31,61' -Render

# Fresh strict check, followed by the official exporter only if it passes.
./tools/export_checked_models.ps1 -Models Restaurant -Render
```

`-Models` takes exact comma-separated source names, for example `Restaurant,Hospital,StoneCrusher`. A missing scene, missing UVs, unbound material or nonpositive tolerance raises an error. The standard checker fails when it finds potentially visible conflicts; `-ReportOnly` explicitly produces diagnostics without export. The checked export command has no bypass switch. It invokes the existing official Timbermesh exporter after a successful check; packaging still uses the official Mod Builder.

Results are written to `outputs/zfight/<Model>-frame<Frame>.json` and `.md`; `-Render` also writes `.png`. JSON records the source scene SHA256, detector SHA256, tolerances, measured separation, overlap polygons, evaluated Blender face IDs and sampled visibility. Face IDs refer to that exact evaluated scene/pose, not a later rebuild. Pair counts are triangle overlaps, **not counts of distinct visible defects**.

Correct the producing helpers or the individual authored parts, regenerate the scene, and rerun. Timber-to-timber joints need intentional boundaries; panels and trim need deliberately distinct surface planes. Do not use shader depth offsets, silent mesh cleanup, coordinate normalization or automatic repair to conceal an overlap. Preserve the approved shape and native grid contracts while correcting the joinery.

## Detection and limits

- A spatial AABB/normal index includes exactly coincident triangles. Blender's `BVHTree.overlap` failed the coincident-plane test and is not used for candidate discovery.
- Near-parallel, same-facing triangles are projected into a local plane and clipped to measure positive overlap area. Shared edges alone are excluded.
- Defaults: separation at most **0.0005 model units**, overlap at least **0.0005 square units**, parallel angle within **0.05 degrees**. These are detection tolerances, not automatic geometry changes.
- Material identity and interpolated UVs separate identical-appearance duplicates from competing surfaces. The identical category does not inspect every possible shader input, custom normal or vertex-color difference.
- Outward ray samples split potentially visible conflicts from buried joints. Visibility is an approximation; thin covers, transparency and uncommon view directions can require manual inspection. The geometry test assumes ordinary back-face culling.
- A marked surface is a geometric risk, not proof of GPU flicker. Depth precision, camera distance, shader behavior and runtime-created objects still need an in-game check. Player Paths, neighboring buildings and runtime-only assemblies are not present in the isolated reference scene. Animation is tested only at the requested frames.
- Red overlays exist only in the temporary diagnostic render. Source `.blend` files, game assets, materials and export geometry are untouched.

## Verification

The nine synthetic cases cover coincident different materials, shifted UVs with the same material, identical material/UV duplicates, close separated planes, clearly separated planes, shared edges, partial overlap, an angled roof and a buried joint. All passed; see `outputs/zfight/detector-tests.json`.

```powershell
./tools/asset-pipeline/blender-4.5.3/blender.exe -b --python-exit-code 1 --python tools/asset-pipeline/test_zfight_audit.py
```

The [report index](../../outputs/zfight/index.md) records the latest completed detailed-scene scan. Source edits invalidate its older hashes until the affected scenes are checked again. The original eighteen-flagged baseline is preserved in `outputs/zfight-baseline-2026-10-20/`. Run `tools/asset-pipeline/summarize_surface_audits.py` to regenerate the index; it rejects reports whose source or detector hash is stale. Fresh reports only link diagnostic images produced by that same run. This is source geometry evidence, not a statement that every camera angle, animation pose or runtime assembly is visually clean.

The checked export's rejection test used the historical Restaurant source and preserved the SHA256 hashes of its existing game scene and official Timbermesh (`outputs/zfight/checked-export-test.json`). A separate strict SandstoneMasonryBlock frame-two check passed. The earlier `validate_restaurant_surfaces.py` only checked broad plaster/wood facade rectangles and did not cover all frame joints, trim, roofs and deck surfaces; use the general detector for the repaired sources.

## Missing surfaces and floating windows

Zero overlap candidates does not prove a closed exterior. The restaurant still had roof-sheet slots, missing curbs, joined-room strips and an uncapped vestibule after an earlier overlap pass. Explicit coverage probes now check declared opaque walls and roofs, including oblique seams and evaluated modifier output. Deliberately open galleries, pools and machine mouths are separate architectural cases.

`test_catalog_surfaces.py` tests the authored catalog surface contracts; the restaurant and hospital also have full-scene checks. `audit_window_mounts.py` casts toward opaque backing with every window assembly and its reveal excluded. It reports missing backing or an unsupported stand-off; it never moves an asset. The shared native-window helper accepts an explicitly authored wall-plane anchor and builds a physical reveal while retaining original native triangles and atlas coordinates.

Use all three kinds of evidence—coverage, mounting contact and overlap—then inspect front/rear isometric views and the exported model in game. None is a substitute for the others.

## Ground and plank contact (2026-10-21)

An isolated building audit cannot see the terrain beneath it. Inspect the actual native terrain and path models before setting the wearing surface of a ground apron. `inspect_native_ground_clearance.py` reads installed 1.1.2.8 terrain through its exact ResourceManager/BinaryData mappings and the official Timbermesh stream format. The 100 terrain assemblies include 67 with horizontal upward faces. Their highest horizontal top is 0.01 units above the cell datum (`environment/land/0udu-a`); other terrain vertices include cliff sides extending higher and are not a flat-floor clearance contract. Results are in `outputs/native-ground-clearance.json`.

The two pit aprons previously had plank tops exactly at ground Z=0. Their selected `Apron` components now author tops at 0.020, preserving buried board bottoms, joists and doorway registration. Hatchery's two bank-apron components use a 0.016 backing and 0.020 plank top above the bank floor, so board gaps do not expose competing ground surfaces. Its submerged model origin is accounted for explicitly. These are physical source dimensions, not shader offsets or adjusted building/path layers.

Native DirtPath surfaces are only about 0.00030 above ground and would be buried by a raised wooden apron. A pathable physical floor follows the shipped ImpermeableFloor contract: `Floor` occupation without `Path`, plus `PathModelTypeEnforcerSpec` selecting `Roof`. The six native RoofPath variants have upward surfaces starting at 0.20000003, above the authored planks. Apply this only to actual pathable floor cells; occupied workshop yards are not player decks. Source/assembled clearance and official exports are evidence of geometry and bindings. Native placement, path rendering and camera-dependent depth behavior still require an in-game check.
