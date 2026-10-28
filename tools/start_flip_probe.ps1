param(
  [Parameter(Mandatory=$true)][string]$Label,
  # A new Iron Teeth game (settlement "Memory Test") on this map; the probe levels a dry slot next to the
  # starting district centre and carves the hatchery's bank itself.
  [string]$NewGame = 'user:Deep Frontier - All Buildings Sites Test',
  [double]$CeilingGB = 13,
  [int]$TimeoutMinutes = 90
)
# Flipped-placement probe (src/DeepFrontier/Scripts/FlipPlacementProbe.cs), unattended after the launch
# dialogs: FishHatchery, FisheryWorks and Greenhouse in all 4 rotations, unflipped and flipped. Per
# placement: the native cursor pick on the hatchery's bank, native preview, a plain Path on the entrance
# and a road to the district centre (path connection toward the door, district, no Unconnected status,
# access), a native PowerShaft on every horizontal and Top transput face (graph join and connector
# socket), and a beaver employed there reaching the building.
# Results: outputs/flip-probe-<Label>.json and outputs/flip-probe-<Label>.log. Never loads a user save.
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'A game process is already running; finish the current session before launching the flip probe.' }
if ($Label -match '[\\/:*?"<>|\s]') { throw "Label must be a plain file-name part: $Label" }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$log = Join-Path $root "outputs/flip-probe-$Label.log"
$csv = Join-Path $root "outputs/flip-probe-$Label-memory.csv"
$sampler = Start-Process -FilePath 'powershell' -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + (Join-Path $PSScriptRoot 'sample_timberborn_memory.ps1') + '"'),
  '-Out',('"' + $csv + '"'),'-CeilingGB',$CeilingGB,'-Minutes',($TimeoutMinutes + 10))
Write-Output "Sampler pid $($sampler.Id) -> $csv (ceiling $CeilingGB GB)"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @(
  '-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierLoadAcceptance','-deepFrontierNewGame',('"' + $NewGame + '"'),
  '-deepFrontierFlipProbe','-deepFrontierFlipProbeLabel',$Label,'-logFile',('"' + $log + '"'))
Write-Output "Requested the flip probe (new game on $NewGame). Log: $log"
& (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier FlipProbe\] COMPLETE' -TimeoutMinutes $TimeoutMinutes
$code = $LASTEXITCODE
if (-not $sampler.HasExited) { Stop-Process -Id $sampler.Id }
Get-Content -LiteralPath $csv | Select-Object -Last 3
$json = Join-Path $root "outputs/flip-probe-$Label.json"
if (Test-Path -LiteralPath $json) {
  $result = Get-Content -LiteralPath $json -Raw | ConvertFrom-Json
  $result.cases | ForEach-Object {
    $failed = @($_.checks | Where-Object status -eq 'FAIL' | ForEach-Object check) -join '; '
    '{0,-36} {1,-6} {2}' -f $_.case, $_.verdict, $failed
  }
}
exit $code
