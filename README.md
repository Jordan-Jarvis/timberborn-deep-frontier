# Deep Frontier

An industrial frontier expansion for the **Iron Teeth** in [Timberborn](https://mechanistry.com/timberborn) 1.1.2.8. Dig into deep ore below the map, pour concrete, smelt steel, run coal, oil and nuclear power, keep beavers fed and healthy, and push to a rocket launch, while managing radiation, smog and workplace injuries.

- **64 buildings, 55 goods, 75 recipes**, built on the official Timberborn modding tools to match the game's look and placement rules.
- Deep ore mining, construction materials (quarries, cement, concrete, masonry), heavy industry, a rocket program.
- Power: reinforced hydro turbine, workerless coal and oil plants, a nuclear reactor with meltdown risk.
- Radiation: radioactive waste, contaminated water and goods, and a Radioactive Tide weather event.
- Civic life: a restaurant with table service and Fine Dining, a grocery store, a hospital and public health lab, a bathhouse, town plaza and observation deck.
- Smog, workforce injuries and bot upkeep.
- Building passages: touching buildings share their insides, stacked or side by side. This replaces the Hooman Stairs mod, which is incompatible.

The player-facing Workshop description is in [workshop/description.bbcode](workshop/description.bbcode).

## Playing

Subscribe on the Steam Workshop together with the required mods listed in [src/DeepFrontier/manifest.json](src/DeepFrontier/manifest.json). Iron Teeth only.

## Repository layout

| Path | Contents |
| --- | --- |
| `src/DeepFrontier/` | The mod: `manifest.json`, C# `Scripts/` (main assembly plus optional Moddable Weathers and Sluice is Back! bridges), `Data/` blueprints, localization and meshes, `AssetBundles/` sources, `Editor/` Unity helpers. |
| `src/DeepFrontier/Art/` | Source art: Blender scenes (`Source/*.blend`, saved compressed with textures unpacked), concepts, icons and textures. |
| `tools/` | Content generators (`*_content.mjs`), validators (`validate_*.mjs/py`, `validate_all.ps1`), the build and launch scripts, the asset pipeline and the C# compile checks (`tools/compile-check`). |
| `tools/STATUS.md` | Build-by-build record of what was implemented and what was verified in game. |
| `docs/` | Design and implementation notes (progression, radiation, meltdown, maps, asset pipeline and more) and art review renders. |
| `outputs/` | Deep Frontier model exports and studies that the content generators read (`reference-studies`, `lategame-*`, `*-integration`, `connection-faces`). Everything else the tools write here (logs, reports, screenshots) is ignored. |
| `workshop/` | Steam Workshop description and thumbnail. |


## Building from source

Windows only. You need:

- Timberborn 1.1.2.8 (Steam) with the required mods subscribed (the build references their DLLs from the Workshop folder).
- Unity 6000.5.11f1 and the official modding project cloned to `vendor/timberborn-modding` (from Mechanistry's [timberborn-modding](https://github.com/mechanistry/timberborn-modding) repository, last built against commit `cc50d47`; not included here).
- .NET SDK 8, Node.js, Python 3 and PowerShell 7. The scripts currently use fixed paths for Node, Python and PowerShell 7; see `AGENTS.md`.
- For model work only: Blender 4.5.3 portable in `tools/asset-pipeline/blender-4.5.3` with the Timbermesh exporter, and the game textures (see "Local-only game references"). Save scenes with Blender's Compress option and textures unpacked; `tools/asset-pipeline/unpack_blend_textures.py` does both for any scene that packs images again.

Typical loop:

```bash
pwsh tools/promote_style_exports.ps1          # regenerate blueprints into src/DeepFrontier/Data
node tools/aquaculture_workbook.mjs
pwsh tools/validate_all.ps1 -SkipBlender      # static checks (logs in outputs/validate-all)
dotnet build tools/compile-check/DeepFrontierCompileCheck.csproj
powershell -File tools/build_deep_frontier.ps1   # official Mod Builder; installs to Documents\Timberborn\Mods\DeepFrontier
pwsh tools/verify_deep_frontier_package.ps1 -Build <n>
```

`tools/start_memory_load.ps1 -SaveInspect` loads a save copy unattended for in-game checks, and `-Showcase` takes Workshop screenshots. Both load copies from the "Memory Test" settlement, whose autosaves they rotate.

## Local-only game references

Some generators and validators also read references taken from your own Timberborn install. They belong to Mechanistry, so they are not in this repository; create them locally after installing the game:

| Folder | Used by | Create with |
| --- | --- | --- |
| `src/DeepFrontier/Art/GameTextures` | the Blender scenes' game textures (wood, plaster, metal, water...); the list is `Art/GameTextures.json` | `python tools/asset-pipeline/extract_game_textures.py` |
| `outputs/vanilla-icons` | icon generators, the Radioactive Tide banner (`tools/radioactive_tide_content.mjs`) | `python tools/asset-pipeline/export_vanilla_icon_references.py` |
| `outputs/native-civic-assets` | native model and material previews for the civic buildings | `python tools/asset-pipeline/extract_native_models.py`, `export_native_civic_materials.py`, `export_native_civic_inspection.py`, `read_native_civic_models.py` |
| `outputs/workforce-api-1.1.2.8/original` | optional API checks in `tools/validate_workforce_risks.mjs` (skipped when absent) | decompile the listed game assemblies with ILSpy (`ilspycmd`) |

The extraction scripts read `Timberborn_Data/resources.assets` with UnityPy (`tools/asset-pipeline/unitypy`) and never ship anything: the mod references the game's own resources at runtime.

## Working rules

Use the official tools and public dependency interfaces first. Fix the producing source instead of adding normalization or fallback logic. Do not redistribute third-party mod binaries. See `AGENTS.md`.

## License

Code (scripts, tools, blueprint data and localization) is MIT; art (models, meshes, textures, icons, renders, asset bundles) is all rights reserved. See [LICENSE](LICENSE).
