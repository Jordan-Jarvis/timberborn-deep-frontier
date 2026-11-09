#Requires -Version 7
# Launch only the flag-gated disposable fixture, then restore the user's profile.
# The two synthetic consumer fixtures (built by build_moddable_fluids.ps1 -SyntheticFixtures and kept
# outside the Mods folder) are installed only for this run and removed afterwards, together with
# any enablement keys the game created for them: Timberborn enables a new mod by default.
param([int]$TimeoutSeconds = 360)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (Get-Process Timberborn -ErrorAction SilentlyContinue) { throw 'Close Timberborn before the disposable worker acceptance run.' }
if (-not (Test-Path (Join-Path $dev.timberbornDocuments 'Maps/Moddable Fluids Worker Fixture.timber'))) { throw 'Generate the explicit worker fixture first.' }
$output = Join-Path $root 'outputs/fluids-api-prototype'
$mods = Join-Path $dev.timberbornDocuments 'Mods'
if (-not (Test-Path -LiteralPath (Join-Path $mods 'ModdableFluids/version-1.1/Scripts/ModdableFluids.dll'))) { throw 'Build Moddable Fluids first: tools/build_moddable_fluids.ps1 -SyntheticFixtures' }
if (Test-Path -LiteralPath (Join-Path $mods 'FluidsApi')) { throw 'The pre-rename FluidsApi development package is still installed; remove it with tools/build_moddable_fluids.ps1 -RemoveLegacyPackage.' }
$fixtureIds = @('ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled')
foreach ($id in $fixtureIds) {
  if (-not (Test-Path -LiteralPath (Join-Path $output "fixture-packages/$id/version-1.1/Scripts/$id.dll"))) { throw "Missing fixture package $id; run tools/build_moddable_fluids.ps1 -SyntheticFixtures" }
  if (Test-Path -LiteralPath (Join-Path $mods $id)) { throw "$id is already in the Mods folder; it must be installed only by this launcher." }
}
$backup = Join-Path $output ('profile-' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
New-Item -ItemType Directory -Force -Path $backup | Out-Null
$profile = Join-Path $dev.timberbornDocuments 'PlayerData'
$profileFiles = @('player.data','player.data.old','player.data.backup','LoadGameModValidator.txt','Replatform.txt')
$hashes = @{}
foreach ($name in $profileFiles) {
  $path = Join-Path $profile $name
  if (Test-Path -LiteralPath $path) {
    Copy-Item -LiteralPath $path -Destination (Join-Path $backup $name)
    $hashes[$name] = (Get-FileHash -LiteralPath $path).Hash
  }
}
$prefsPath = 'HKCU:\Software\Mechanistry\Timberborn'
$ownedKeys = '^Mod(Enabled|Priority)\..*\.(ModdableFluidsSyntheticReflection|ModdableFluidsSyntheticCompiled)_h\d+$'
$prefs = Get-Item -LiteralPath $prefsPath
$flags = @{}
foreach ($name in $prefs.GetValueNames() | Where-Object { $_ -match '^ModEnabled\..*\.(DeepFrontier|ModdableFluids|ModdableFluidsSyntheticReflection|ModdableFluidsSyntheticCompiled)_h\d+$' }) {
  $flags[$name] = [int]$prefs.GetValue($name)
}
@{ playerDataHashes=$hashes; modFlags=$flags } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $backup 'original.json')
$log = Join-Path $output 'worker-game.log'
$report = Join-Path $output 'worker-report.json'
$ownedProcess = $null
$installedFixtures = @()
try {
  # Existing keys only: a mod without a key is enabled by default (ModPlayerPrefsHelper.IsModEnabled).
  foreach ($name in $flags.Keys) {
    $enabled = if ($name -match '\.(ModdableFluids|ModdableFluidsSyntheticReflection|ModdableFluidsSyntheticCompiled)_h\d+$') { 1 } else { 0 }
    Set-ItemProperty -LiteralPath $prefsPath -Name $name -Value $enabled
  }
  foreach ($id in $fixtureIds) {
    Copy-Item -LiteralPath (Join-Path $output "fixture-packages/$id") -Destination (Join-Path $mods $id) -Recurse
    $installedFixtures += $id
  }
  if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
  & (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @('-moddableFluidsWorkerAcceptance','-moddableFluidsReport',('"'+$report+'"'),'-logFile',('"'+$log+'"'))
  $ownedProcess = @(Get-Process Timberborn -ErrorAction Stop)
  if ($ownedProcess.Count -ne 1) { throw 'Expected exactly one owned acceptance game process.' }
  $ownedProcess = $ownedProcess[0]
  Write-Output "Disposable worker acceptance PID $($ownedProcess.Id). Profile backup: $backup"
  if (-not $ownedProcess.WaitForExit($TimeoutSeconds * 1000)) { throw "Disposable worker acceptance exceeded $TimeoutSeconds seconds. See $log" }
  if ($ownedProcess.ExitCode -ne 0) { throw "Acceptance game exited with $($ownedProcess.ExitCode). See $log" }
  if (-not (Test-Path -LiteralPath $report)) { throw "Acceptance did not produce its report. See $log" }
  $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
  if ($result.status -ne 'passed' -or $result.scenesAttached -ne 2 -or $result.scenesDetached -ne 2) { throw 'Worker acceptance report did not pass two scene lifecycles.' }
  $expectedFluids = 'Timberborn.Water,Timberborn.Badwater,ModdableFluidsSyntheticCompiled.Tracer,ModdableFluidsSyntheticReflection.Juice'
  foreach ($world in $result.worlds) { if (($world.fluids -join ',') -ne $expectedFluids) { throw "World $($world.scene) ran with registry $($world.fluids -join ',')" } }
  Write-Output "PASS: two real-worker scenes with the registry from both consumer routes. Report: $report"
} finally {
  # Never restore files while Unity could still write them. Stop only this test's process.
  if ($ownedProcess -and -not $ownedProcess.HasExited) {
    Stop-Process -Id $ownedProcess.Id -Force
    $ownedProcess.WaitForExit()
  }
  foreach ($id in $installedFixtures) { Remove-Item -LiteralPath (Join-Path $mods $id) -Recurse -Force }
  foreach ($id in $fixtureIds) { if (Test-Path -LiteralPath (Join-Path $mods $id)) { throw "Fixture $id is still installed." } }
  foreach ($name in $flags.Keys) { Set-ItemProperty -LiteralPath $prefsPath -Name $name -Value $flags[$name] }
  foreach ($name in (Get-Item -LiteralPath $prefsPath).GetValueNames()) {
    if ($flags.ContainsKey($name)) { continue }
    if ($name -match '^ModEnabled\..*\.ModdableFluids_h\d+$') { Set-ItemProperty -LiteralPath $prefsPath -Name $name -Value 0 }
    elseif ($name -match $ownedKeys) { Remove-ItemProperty -LiteralPath $prefsPath -Name $name }
  }
  foreach ($name in $profileFiles) {
    $path = Join-Path $profile $name
    if ($hashes.ContainsKey($name)) {
      Copy-Item -LiteralPath (Join-Path $backup $name) -Destination $path -Force
      if ((Get-FileHash -LiteralPath $path).Hash -ne $hashes[$name]) { throw "Profile restoration hash mismatch: $name" }
    } elseif (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
  }
  Write-Output 'Fixture packages removed; original Deep Frontier/API enablement and PlayerData files restored; hashes verified.'
}
