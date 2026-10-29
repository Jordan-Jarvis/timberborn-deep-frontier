param(
  [Parameter(Mandatory=$true)][string]$Label,
  # Save copy to load; it must lie in ExperimentalSaves\Memory Test (MemoryLoadProbe/IndustrialAcceptanceLoader).
  [Parameter(Mandatory=$true)][string]$Save,
  [double]$CeilingGB = 15
)
# Frame-time profile of a save copy with mods loaded, unattended (Scripts/Performance/FrameProfileProbe.cs):
# the main-menu loader starts the game (-deepFrontierLoadAcceptance -deepFrontierLoadSave), the probe runs
# it at speed 3 for a 20 s warm-up and 60 s of sampling, then writes the native per-system tick report
# (native -metrics switch) to outputs\frame-profile-<Label>.csv and every frame time to
# outputs\frame-profile-<Label>-frames.csv. MemoryLoadProbe only unpauses a paused game;
# -deepFrontierRunSeconds keeps it from pausing first. The watcher closes the game on COMPLETE.
$ErrorActionPreference = 'Stop'
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$testDir = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ExperimentalSaves\Memory Test'
$Save = [IO.Path]::GetFullPath($Save)
if ((Split-Path -Parent $Save) -ne $testDir) { throw "Only copies in $testDir are loaded: $Save" }
if (-not (Test-Path -LiteralPath $Save -PathType Leaf)) { throw "No save at $Save" }
$log = Join-Path $root "outputs\frame-profile-$Label.log"
$csv = Join-Path $root "outputs\frame-profile-$Label-memory.csv"
$report = Join-Path $root "outputs\frame-profile-$Label"
$sampler = Start-Process -FilePath 'powershell' -WindowStyle Hidden -PassThru -ArgumentList @(
  '-NoProfile','-ExecutionPolicy','Bypass','-File',('"' + (Join-Path $PSScriptRoot 'sample_timberborn_memory.ps1') + '"'),
  '-Out',('"' + $csv + '"'),'-CeilingGB',$CeilingGB,'-Minutes','25')
Write-Output "Sampler pid $($sampler.Id) -> $csv (ceiling $CeilingGB GB)"
& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @('-force-d3d11','-screen-fullscreen','0','-screen-width','1920','-screen-height','1080',
  '-deepFrontierLoadAcceptance','-deepFrontierLoadSave',('"' + $Save + '"'),'-deepFrontierRunSeconds','1000000',
  '-metrics','-deepFrontierFrameProfile',('"' + $report + '"'),'-logFile',('"' + $log + '"'))
Write-Output "Frame profile of $Save. Log: $log"
& (Join-Path $PSScriptRoot 'watch_acceptance_log.ps1') -Log $log -Done '^\[DeepFrontier FrameProfile\] COMPLETE' -TimeoutMinutes 20
$code = $LASTEXITCODE
if (-not $sampler.HasExited) { Stop-Process -Id $sampler.Id }
Get-Content -LiteralPath $csv | Select-Object -Last 3
exit $code
