$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'node','python'
$node = $dev.node
$python = $dev.python
Set-Location -LiteralPath $root

# Run only after the canonical source scenes, manifests and official mesh
# exports are complete. Diagnose geometry before installing any candidate.
# Static checks live in tools/validate_all.ps1 (logs: outputs/validate-all/<id>.log).
$validateAll = Join-Path $PSScriptRoot 'validate_all.ps1'
& $validateAll -Only promote-clearance
if ($LASTEXITCODE -ne 0) { throw 'Route or opening clearance diagnostics report an obstruction' }

# The canonical generator owns active blueprints and matching civic meshes.
# Complete faction goods registration before candidate recipe validation.
& $node tools/create_vertical_slice_content.mjs
if ($LASTEXITCODE -ne 0) { throw 'Canonical content generation failed' }

foreach ($name in @('research', 'hydro', 'structural')) {
  & $node "tools/${name}_building_content.mjs"
  if ($LASTEXITCODE -ne 0) { throw "$name candidate blueprint generation failed" }
  & $python "tools/asset-pipeline/validate_${name}_exports.py" *> "outputs/style-export-$name.json"
  if ($LASTEXITCODE -ne 0) { throw "$name candidate export validation failed" }
}

# A candidate file is registered only when the canonical blueprint in its
# target folder references it by its exact resource path.
function Assert-Registered([string]$relative, [string]$field) {
  $resource = ($relative -replace '\\', '/') -replace '\.(timbermesh|png)$', ''
  $folder = Split-Path -Parent (Join-Path $root "src/DeepFrontier/Data/$relative")
  $blueprint = Join-Path $folder ((Split-Path -Leaf $folder) + '.IronTeeth.blueprint.json')
  if (-not (Test-Path -LiteralPath $blueprint -PathType Leaf)) { throw "No canonical blueprint registers $relative" }
  $text = Get-Content -LiteralPath $blueprint -Raw
  if ($text -notmatch ('"' + $field + '"\s*:\s*"' + [regex]::Escape($resource) + '"')) {
    throw "Canonical blueprint $blueprint does not reference $resource"
  }
}

foreach ($name in @('research', 'hydro', 'structural')) {
  $source = (Resolve-Path "outputs/$name-integration/Data").Path
  $meshes = @(Get-ChildItem -LiteralPath $source -Filter '*.timbermesh' -File -Recurse)
  # Structural: 18 templates (7 original structures, 8 concrete platform variants, 3 side platforms), two meshes each.
  $expected = if ($name -eq 'structural') { 36 } else { 2 }
  if ($meshes.Count -ne $expected) { throw "Unexpected candidate mesh count in $name" }
  foreach ($mesh in $meshes) {
    $relative = [IO.Path]::GetRelativePath($source, $mesh.FullName)
    Assert-Registered $relative 'Model'
    $target = Join-Path $root "src/DeepFrontier/Data/$relative"
    Copy-Item -LiteralPath $mesh.FullName -Destination $target -Force
  }
}

# Structural UI icons come from tools/create_structural_icons.mjs.
$structural = (Resolve-Path 'outputs/structural-integration/Data').Path
$icons = @(Get-ChildItem -LiteralPath $structural -Filter 'Icon.png' -File -Recurse)
if ($icons.Count -ne 18) { throw 'Unexpected structural candidate icon count' }
foreach ($icon in $icons) {
  $relative = [IO.Path]::GetRelativePath($structural, $icon.FullName)
  Assert-Registered $relative 'Icon'
  $target = Join-Path $root "src/DeepFrontier/Data/$relative"
  Copy-Item -LiteralPath $icon.FullName -Destination $target -Force
  Copy-Item -LiteralPath ($icon.FullName + '.meta.json') -Destination ($target + '.meta.json') -Force
}

# The same post-promotion checks as before; `pwsh tools/validate_all.ps1` runs every validator.
& $validateAll -Only exports-industrial, exports-pit, exports-civic, exports-hospital, exports-grocery, exports-fishery, exports-hatchery,
  model-bindings, deep_frontier_manifest, vertical_slice_content, construction_materials, restaurant_content
if ($LASTEXITCODE -ne 0) { throw 'Post-promotion validation failed; see the validate_all table above' }
Write-Output 'Detailed style exports promoted; generated data and model binding checks passed. Native game acceptance remains separate.'
