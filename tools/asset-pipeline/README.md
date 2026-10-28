# Deep Frontier asset CLI

Reviewed buildings have their own source scenes and export commands. Follow `docs/asset-pipeline.md` and `tools/STATUS.md` for the current owner and installed verification. The generic prototype pipeline below does not rebuild or replace the reviewed crusher, kiln, quarries, mixer, restaurant, hospital, grocery, Fishery or hatchery.

This folder is a self-contained Windows asset toolchain for Timberborn 1.1:

- `blender-4.5.3\blender.exe` — pinned portable Blender CLI.
- `timbermesh-plugin\timbermesh_blender_plugin` — official Timbermesh Blender exporter.
- `generate_deep_frontier_assets.py` — creates the remaining prototype source collections and initial material assets.
- `export_deep_frontier_assets.py` — exports its explicitly owned prototype collections to Timbermesh files under `src\DeepFrontier\Data`.
- `render_reference_studies.py` — builds detailed reference scenes and angled review renders from the individual geometry modules.
- `export_industrial_models.py` — exports the reviewed industrial scenes using their explicit layouts.
- `validate_deep_frontier_assets.mjs` — checks the source scene, icons, textures, and model exports.
- `validate_deep_frontier_animations.py` — checks that every finished model contains the exported looping Timbermesh node animation.
- `prepare_deep_frontier_materials.py` — prepares authored texture maps for Unity material authoring.

From the repository root:

```powershell
.\tools\asset-pipeline\build_deep_frontier_assets.ps1
```

For prototype iteration, use `-SkipGeneration`, `-SkipExport`, or `-SkipValidation`. Open the official builder with `tools/open_deep_frontier_builder.ps1`. Unity's **Deep Frontier > Create Materials** authors custom prototype materials; **Timberborn > Show Mod Builder** compiles and packages the mod. Reviewed models use the native Iron Teeth palette and original native prop references. Exact source, export and gameplay checks remain separate in `tools/STATUS.md`.
