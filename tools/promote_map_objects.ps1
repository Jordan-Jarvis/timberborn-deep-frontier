#Requires -Version 7
# Promote the map-object and pile-good exports (tools/map_objects.json,
# tools/asset-pipeline/build_map_objects.py) from outputs/mapobjects-integration
# into src/DeepFrontier, then verify every copy byte for byte. It generates no
# blueprints: run canonical generation (node tools/create_vertical_slice_content.mjs)
# and the expansion icons (node tools/create_frontier_expansion_icons.mjs) after it.
#
#   pwsh tools/promote_map_objects.ps1            # copy and verify
#   pwsh tools/promote_map_objects.ps1 -WhatIf    # list what would change
param([switch]$WhatIf)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$contract = Get-Content -LiteralPath (Join-Path $root 'tools/map_objects.json') -Raw | ConvertFrom-Json
$exports = Join-Path $root $contract.exportRoot
$pairs = [System.Collections.Generic.List[object]]::new()
foreach ($model in $contract.models.PSObject.Properties) {
  $relative = "$($model.Value.resource).timbermesh"
  $pairs.Add([pscustomobject]@{ From = Join-Path $exports "Data/$relative"; To = Join-Path $root "src/DeepFrontier/Data/$relative" })
}
foreach ($good in $contract.goods.PSObject.Properties | Where-Object Name -ne 'note') {
  foreach ($resource in $good.Value.primary, $good.Value.secondary) {
    $pairs.Add([pscustomobject]@{ From = Join-Path $exports "AssetBundles/Resources/$resource.timbermesh"; To = Join-Path $root "src/DeepFrontier/AssetBundles/Resources/$resource.timbermesh" })
  }
}
foreach ($pair in $pairs) {
  if (-not (Test-Path -LiteralPath $pair.From -PathType Leaf)) { throw "Missing export $($pair.From); run build_map_objects.py first" }
  $state = if (-not (Test-Path -LiteralPath $pair.To)) { 'new' } elseif ((Get-FileHash $pair.From).Hash -eq (Get-FileHash $pair.To).Hash) { 'same' } else { 'changed' }
  "{0,-8} {1}" -f $state, $pair.To.Substring($root.Length + 1)
  if ($WhatIf -or $state -eq 'same') { continue }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $pair.To) | Out-Null
  Copy-Item -LiteralPath $pair.From -Destination $pair.To -Force
  if ((Get-FileHash $pair.From).Hash -ne (Get-FileHash $pair.To).Hash) { throw "Copy verification failed: $($pair.To)" }
}
if (-not $WhatIf) { "Promoted $($pairs.Count) map-object and pile-good meshes. Next: canonical generation, then create_frontier_expansion_icons.mjs." }
