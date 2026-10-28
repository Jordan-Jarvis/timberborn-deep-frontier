param(
  [switch]$SkipGeneration,
  [switch]$SkipExport,
  [switch]$SkipValidation
)

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$blender = Join-Path $PSScriptRoot 'blender-4.5.3\blender.exe'
$generator = Join-Path $PSScriptRoot 'generate_deep_frontier_assets.py'
$iconGenerator = Join-Path $PSScriptRoot '..\create_frontier_expansion_icons.mjs'
$contentGenerator = Join-Path $PSScriptRoot '..\create_vertical_slice_content.mjs'
$exporter = Join-Path $PSScriptRoot 'export_deep_frontier_assets.py'
$validator = Join-Path $PSScriptRoot 'validate_deep_frontier_assets.mjs'
$animationValidator = Join-Path $PSScriptRoot 'validate_deep_frontier_animations.py'
. (Join-Path $PSScriptRoot '..\DevEnvironment.ps1')
$dev = Get-DevEnvironment 'node','python'
$node = $dev.node
$output = Join-Path $root 'outputs'

if (-not (Test-Path $blender)) {
  throw "Blender was not found at $blender. Extract the pinned portable package first."
}
if (-not (Test-Path $node)) {
  throw "Bundled Node.js was not found at $node."
}
$python = $dev.python
if (-not (Test-Path $python)) {
  throw "Bundled Python was not found at $python."
}

New-Item -ItemType Directory -Force (Join-Path $root 'outputs') | Out-Null
if (-not $SkipGeneration) {
  & $node $contentGenerator
  if ($LASTEXITCODE -ne 0) { throw "Deep Frontier content generation failed with exit code $LASTEXITCODE." }
  & $node $iconGenerator
  if ($LASTEXITCODE -ne 0) { throw "Expansion icon generation failed with exit code $LASTEXITCODE." }
  & $node (Join-Path $root 'tools\create_restaurant_icons.mjs')
  if ($LASTEXITCODE -ne 0) { throw "Authored civic icon generation failed with exit code $LASTEXITCODE." }
  & $node (Join-Path $root 'tools\create_construction_icons.mjs')
  if ($LASTEXITCODE -ne 0) { throw "Authored construction icon generation failed with exit code $LASTEXITCODE." }
  & $blender --background --factory-startup --python-exit-code 1 --python $generator --log-file (Join-Path $output 'blender_generate_assets.log')
  if ($LASTEXITCODE -ne 0) { throw "Blender asset generation failed with exit code $LASTEXITCODE." }
}
if (-not $SkipExport) {
  & $blender --background --factory-startup --python-exit-code 1 --python $exporter --log-file (Join-Path $output 'blender_export_assets.log')
  if ($LASTEXITCODE -ne 0) { throw "Timbermesh export failed with exit code $LASTEXITCODE." }
  & $blender --background --factory-startup --python-exit-code 1 --python (Join-Path $PSScriptRoot 'generate_approved_buildings.py')
  if ($LASTEXITCODE -ne 0) { throw "Approved building asset generation failed with exit code $LASTEXITCODE." }
}
if (-not $SkipValidation) {
  & $node $validator
  if ($LASTEXITCODE -ne 0) { throw "Deep Frontier asset validation failed with exit code $LASTEXITCODE." }
  & $python $animationValidator
  if ($LASTEXITCODE -ne 0) { throw "Deep Frontier animation validation failed with exit code $LASTEXITCODE." }
  & $python (Join-Path $PSScriptRoot 'validate_model_bindings.py')
  if ($LASTEXITCODE -ne 0) { throw "Deep Frontier model bindings failed with exit code $LASTEXITCODE." }
}

Write-Output 'Deep Frontier asset pipeline completed.'
