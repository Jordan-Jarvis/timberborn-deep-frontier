$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$blender = Join-Path $root 'tools/asset-pipeline/blender-4.5.3/blender.exe'
& $blender --background --factory-startup --python-exit-code 1 --python (Join-Path $root 'tools/asset-pipeline/check_prototype_surfaces.py')
if ($LASTEXITCODE -ne 0) { throw 'Prototype surfaces failed; no assets exported.' }
& $blender --background --factory-startup --python-exit-code 1 --python (Join-Path $root 'tools/asset-pipeline/export_deep_frontier_assets.py')
if ($LASTEXITCODE -ne 0) { throw 'Official export failed for DeepFrontierModels prototypes.' }
& $blender --background --factory-startup --python-exit-code 1 --python (Join-Path $root 'tools/asset-pipeline/export_approved_prototypes.py')
if ($LASTEXITCODE -ne 0) { throw 'Official export failed for reactor/cryo prototypes.' }
