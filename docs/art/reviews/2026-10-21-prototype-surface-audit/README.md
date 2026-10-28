# Twenty prototype building models: source and export audit

All twenty remaining prototype buildings were regenerated from their owning generators with native atlas UVs authored directly on their new faces. The strict check passed 50,160 UV corners and found zero visible overlap candidates at animation frame 1. The closed-component boundary audit found zero defects. The official Timbermesh exporter completed 42 files: twenty finished models, twenty construction stages, and the two drill/mine underground parts.

The first audit found 23 visible conflicts in the reactor and 34 in the cryogenic plant. Their producing canopy joins were rebuilt in `tools/asset-pipeline/generate_approved_buildings.py`: posts now terminate below headers, timber sits inside separate steel shoes, short canopies have one diagonal per side, roof end caps extend beyond the sheet ends, and wall trim ends before the shoes. The handwheel is mounted in front of the valve with a connecting axle. Shared detailed-building helpers were not edited. The other eighteen prototypes passed their first strict check.

`manifest.json` records the exact source scenes, generator/checker hashes, per-model audit results, evidence-file hashes, and all 42 output paths and hashes. Source scenes are:

- `src/DeepFrontier/Art/Source/DeepFrontierModels.blend`: `712a0f44938173b9630d3e7d1246d0155e815f70babef65e357942402d5991e8`
- `src/DeepFrontier/Art/Source/ApprovedBuildings.blend`: `bbe4f2bf2d6a04eb64840bffdcd7746d7eb91e820bacf71eee3d4131579f35f4`

These remain compact prototype designs. This pass does not establish detailed art quality, tile/hitbox alignment, runtime power or navigation, native appearance, animation playback, or save/reload. Surface overlap was tested at frame 1; the reactor/cryo source-bounds checks cover all 61 animation frames. Closed individual components do not prove watertight joins between them. Source-only generation preserved the separately owned detailed buildings and did not regenerate their icons or raster artwork.
