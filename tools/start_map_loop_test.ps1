param(
  [Parameter(Mandatory=$true)][string]$Label,
  # Variant ids of tools/map_variants (one new game each, run one after another).
  [string[]]$Variants = @('plains', 'plains-hard', 'lakes', 'terraces'),
  [int]$TimeoutMinutes = 20
)
# Full-loop map proof (src/DeepFrontier/Scripts/MapLoopAcceptance.cs), one new Iron Teeth game per map
# variant through the main-menu loader (-deepFrontierLoadAcceptance -deepFrontierNewGame,
# IndustrialAcceptanceLoader.cs). The harness reads the variant's static evidence
# outputs/maps/<id>-validation.json (tools/prepare_deep_frontier_map.py build), requires the loaded map
# file to match its outputSha256, then checks that every placement survived loading, that a native
# preview accepts every listed site (after removing trees in the footprint and blasting the cells a site
# lists under "dynamite"), that dam sites hold water and that each pit's native range holds its deposits.
# Results: outputs/map-loop-<Label>-<id>.json and outputs/map-loop-<Label>-<id>.log.
# Never loads or writes a user save; the new games are discarded when the watcher closes the game.
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'A game process is already running; finish the current session before launching the map loop test.' }
if ($Label -match '[\\/:*?"<>|\s]') { throw "Label must be a plain file-name part: $Label" }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
# pwsh -File passes "a,b,c" as one string; accept both that and a real array.
$Variants = @($Variants | ForEach-Object { $_ -split ',' } | Where-Object { $_ })
$failed = @()
foreach ($id in $Variants) {
  $variantPath = Join-Path $root "tools/map_variants/$id.json"
  if (-not (Test-Path -LiteralPath $variantPath)) { throw "No variant $variantPath" }
  $variant = Get-Content -LiteralPath $variantPath -Raw | ConvertFrom-Json
  $evidence = Join-Path $root "outputs/maps/$id-validation.json"
  if (-not (Test-Path -LiteralPath $evidence)) { throw "No static evidence $evidence; run tools/prepare_deep_frontier_map.py build first" }
  $map = $variant.output.name
  $log = Join-Path $root "outputs/map-loop-$Label-$id.log"
  & (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
    '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
    '-deepFrontierLoadAcceptance','-deepFrontierNewGame',('"user:' + $map + '"'),
    '-deepFrontierMapLoop','-deepFrontierMapLoopLabel',$Label,'-logFile',('"' + $log + '"'))
  Write-Output "Requested the map loop test on $map. Log: $log"
  & (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier MapLoop\] COMPLETE' -TimeoutMinutes $TimeoutMinutes
  if ($LASTEXITCODE -ne 0) { $failed += $id }
  $json = Join-Path $root "outputs/map-loop-$Label-$id.json"
  if (Test-Path -LiteralPath $json) {
    $result = Get-Content -LiteralPath $json -Raw | ConvertFrom-Json
    Write-Output ("{0}: complete={1}, {2} checks, {3} failed" -f $id, $result.complete, $result.checks.Count, $result.failed)
    $result.checks | Where-Object status -eq 'FAIL' | ForEach-Object { '  FAIL {0} | {1}: {2}' -f $_.subject, $_.check, $_.detail }
    if ($result.failed -gt 0) { $failed += $id }
  } else { $failed += $id }
  while (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { Start-Sleep -Seconds 2 }
}
if ($failed.Count -gt 0) { Write-Output "Failed: $($failed | Select-Object -Unique)"; exit 1 }
exit 0
