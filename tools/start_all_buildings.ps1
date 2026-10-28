param(
  [Parameter(Mandatory=$true)][string]$Label,
  # A new Iron Teeth game (settlement "Memory Test") on this map. The default, written by
  # tools/create_all_buildings_sites_map.py, is the flat, dry test map (tools/create_flat_test_map.py) plus
  # the sites of tools/all_buildings_sites.json (vein, seams, pond, radioactive pools, step, walled river
  # reach) for the twelve buildings a flat pad cannot hold. The harness clears and levels a dry pad next to
  # the starting district centre; on a map without the sites those twelve are reported SITE.
  [string]$NewGame = 'user:Deep Frontier - All Buildings Sites Test',
  [double]$CeilingGB = 13,
  [int]$TimeoutMinutes = 150
)
# All-buildings functional acceptance (src/DeepFrontier/Scripts/AllBuildingsAcceptance.cs), unattended:
# the main-menu loader starts a new game (-deepFrontierLoadAcceptance -deepFrontierNewGame,
# IndustrialAcceptanceLoader.cs); the harness places every Deep Frontier building, the vanilla
# templates Deep Frontier patches and vanilla references in batches on a levelled pad and checks
# placement, entrance, unpowered/missing-input statuses, status icon height, inventory, enterable,
# slots, workers, production, power, Timber Pipes delivery (tank -> pump -> pipe -> valve) and
# attraction visits; then one sites batch on the map's prepared sites (production on the vein and seams,
# the hatchery on the pond with its deck paths, anchored side platforms with building on top, sludge
# recovery against the world radiation balance, hydro power from flow, the vanilla pump, shower and pool).
# Results: outputs/all-buildings-<Label>.json and outputs/all-buildings-<Label>.log.
# The memory sampler closes the game above -CeilingGB; the watcher closes it when the run finishes.
# Never loads a user save.
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'A game process is already running; finish the current session before launching the all-buildings test.' }
if ($Label -match '[\\/:*?"<>|\s]') { throw "Label must be a plain file-name part: $Label" }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$log = Join-Path $root "outputs/all-buildings-$Label.log"
$csv = Join-Path $root "outputs/all-buildings-$Label-memory.csv"
$sampler = Start-Process -FilePath 'powershell' -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + (Join-Path $PSScriptRoot 'sample_timberborn_memory.ps1') + '"'),
  '-Out',('"' + $csv + '"'),'-CeilingGB',$CeilingGB,'-Minutes',($TimeoutMinutes + 10))
Write-Output "Sampler pid $($sampler.Id) -> $csv (ceiling $CeilingGB GB)"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierLoadAcceptance','-deepFrontierNewGame',('"' + $NewGame + '"'),
  '-deepFrontierAllBuildings','-deepFrontierAllBuildingsLabel',$Label,'-logFile',('"' + $log + '"'))
Write-Output "Requested the all-buildings test (new game on $NewGame). Log: $log"
& (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier AllBuildings\] COMPLETE' -TimeoutMinutes $TimeoutMinutes
$code = $LASTEXITCODE
if (-not $sampler.HasExited) { Stop-Process -Id $sampler.Id }
Get-Content -LiteralPath $csv | Select-Object -Last 3
$json = Join-Path $root "outputs/all-buildings-$Label.json"
if (Test-Path -LiteralPath $json) {
  $result = Get-Content -LiteralPath $json -Raw | ConvertFrom-Json
  $result.buildings | ForEach-Object {
    $failed = @($_.checks | Where-Object status -eq 'FAIL' | ForEach-Object check) -join '; '
    '{0,-40} {1,-8} {2}' -f $_.template, $_.verdict, $failed
  }
}
exit $code
