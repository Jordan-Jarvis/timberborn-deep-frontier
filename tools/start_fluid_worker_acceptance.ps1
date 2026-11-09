#Requires -Version 7
# Launch only the flag-gated disposable fixture, then restore the user's profile.
# The Moddable Fluids package and the two synthetic consumer fixtures (built by
# build_moddable_fluids.ps1 -SyntheticFixtures and kept in outputs/fluids-api-prototype/packages)
# are installed only for this run and removed afterwards, together with any enablement keys the
# game created for them: Timberborn enables a new mod by default.
#
#   start_fluid_worker_acceptance.ps1             # two fresh disposable worlds (worker barriers, geometry, intakes)
#   start_fluid_worker_acceptance.ps1 -SaveReload # one world saved natively, reloaded and compared bit for bit;
#                                                 # the fixture deletes its settlement through the native repository
param([int]$TimeoutSeconds = 360, [switch]$SaveReload)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (Get-Process Timberborn -ErrorAction SilentlyContinue) { throw 'Close Timberborn before the disposable worker acceptance run.' }
if (-not (Test-Path (Join-Path $dev.timberbornDocuments 'Maps/Moddable Fluids Worker Fixture.timber'))) { throw 'Generate the explicit worker fixture first.' }
$output = Join-Path $root 'outputs/fluids-api-prototype'
$mods = Join-Path $dev.timberbornDocuments 'Mods'
if (Test-Path -LiteralPath (Join-Path $mods 'FluidsApi')) { throw 'The pre-rename FluidsApi development package is still installed; remove it with tools/build_moddable_fluids.ps1 -RemoveLegacyPackage.' }
$fixtureIds = @('ModdableFluids','ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled')
$saveSettlements = @('Saves','ExperimentalSaves') | ForEach-Object { Join-Path $dev.timberbornDocuments "$_/Moddable Fluids Save Acceptance" }
foreach ($settlement in $saveSettlements) { if (Test-Path -LiteralPath $settlement) { throw "$settlement already exists; the save fixture owns that settlement and must start without it." } }
foreach ($id in $fixtureIds) {
  if (-not (Test-Path -LiteralPath (Join-Path $output "packages/$id/version-1.1/Scripts/$id.dll"))) { throw "Missing kept package $id; run tools/build_moddable_fluids.ps1 -SyntheticFixtures" }
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
$ownedKeys = '^Mod(Enabled|Priority)\..*\.(ModdableFluids|ModdableFluidsSyntheticReflection|ModdableFluidsSyntheticCompiled)_h\d+$'
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
    Copy-Item -LiteralPath (Join-Path $output "packages/$id") -Destination (Join-Path $mods $id) -Recurse
    $installedFixtures += $id
  }
  if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
  $gameArguments = @('-moddableFluidsWorkerAcceptance')
  if ($SaveReload) { $gameArguments += '-moddableFluidsSaveAcceptance' }
  $launch = @(& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments ($gameArguments + @('-moddableFluidsReport',('"'+$report+'"'),'-logFile',('"'+$log+'"'))))
  $launch | Write-Output
  # Wait on the exact process the launch started. A Process object found later by name or id
  # has no handle, and .NET then cannot report its exit code once it exits (the 2026-11-09 run
  # passed but read an empty exit code). Opening .Handle while it runs keeps the code readable.
  $pids = @($launch | ForEach-Object { if ("$_" -match '^Started Timberborn\.exe \(pid (\d+)\)') { [int]$Matches[1] } })
  if ($pids.Count -ne 1) { throw 'The launch did not report exactly one Timberborn process id.' }
  $ownedProcess = Get-Process -Id $pids[0] -ErrorAction Stop
  $null = $ownedProcess.Handle
  if (@(Get-Process Timberborn -ErrorAction SilentlyContinue).Count -ne 1) { throw 'Expected exactly one Timberborn process: the owned acceptance game.' }
  Write-Output "Disposable worker acceptance PID $($ownedProcess.Id). Profile backup: $backup"
  if (-not $ownedProcess.WaitForExit($TimeoutSeconds * 1000)) { throw "Disposable worker acceptance exceeded $TimeoutSeconds seconds. See $log" }
  $ownedProcess.WaitForExit()
  $exitCode = $ownedProcess.ExitCode
  # No fallback: without an exit code the run cannot distinguish a clean quit from a crash.
  if ($null -eq $exitCode) { throw "The acceptance game's exit code is unavailable although its handle was held. See $log" }
  if ($exitCode -ne 0) { throw "Acceptance game exited with $exitCode. See $log" }
  if (-not (Test-Path -LiteralPath $report)) { throw "Acceptance did not produce its report. See $log" }
  $result = Get-Content -LiteralPath $report -Raw | ConvertFrom-Json
  if ($result.status -ne 'passed' -or $result.scenesAttached -ne 2 -or $result.scenesDetached -ne 2) { throw 'Worker acceptance report did not pass two scene lifecycles.' }
  if ($result.mode -ne $(if ($SaveReload) { 'save-reload' } else { 'worker' })) { throw "The report is for mode $($result.mode)." }
  if ($SaveReload) {
    $reloaded = $result.worlds[1]
    if (-not $reloaded.reloaded -or $reloaded.restoredDigest -ne $result.savedDigest -or -not $result.settlementDeleted) { throw 'The save/reload report does not show a bit-identical restore and a deleted settlement.' }
    foreach ($settlement in $saveSettlements) { if (Test-Path -LiteralPath $settlement) { throw "The fixture left its settlement at $settlement." } }
  }
  $expectedFluids = 'Timberborn.Water,Timberborn.Badwater,ModdableFluidsSyntheticCompiled.Tracer,ModdableFluidsSyntheticReflection.Juice'
  foreach ($world in $result.worlds) { if (($world.fluids -join ',') -ne $expectedFluids) { throw "World $($world.scene) ran with registry $($world.fluids -join ',')" } }
  Write-Output $(if ($SaveReload) { "PASS: native save and reload restored the fluid state bit for bit. Report: $report" } else { "PASS: two real-worker scenes with the registry from both consumer routes. Report: $report" })
} finally {
  # Never restore files while Unity could still write them. Stop only this test's process.
  if ($ownedProcess -and -not $ownedProcess.HasExited) {
    Stop-Process -Id $ownedProcess.Id -Force
    $ownedProcess.WaitForExit()
  }
  foreach ($id in $installedFixtures) { Remove-Item -LiteralPath (Join-Path $mods $id) -Recurse -Force }
  # A failed save run may leave the disposable settlement; it did not exist before this run.
  foreach ($settlement in $saveSettlements) { if (Test-Path -LiteralPath $settlement) { Remove-Item -LiteralPath $settlement -Recurse -Force; Write-Output "Removed the disposable settlement $settlement" } }
  foreach ($id in $fixtureIds) { if (Test-Path -LiteralPath (Join-Path $mods $id)) { throw "Fixture $id is still installed." } }
  foreach ($name in $flags.Keys) { Set-ItemProperty -LiteralPath $prefsPath -Name $name -Value $flags[$name] }
  foreach ($name in (Get-Item -LiteralPath $prefsPath).GetValueNames()) {
    if ($flags.ContainsKey($name)) { continue }
    if ($name -match $ownedKeys) { Remove-ItemProperty -LiteralPath $prefsPath -Name $name }
  }
  foreach ($name in $profileFiles) {
    $path = Join-Path $profile $name
    if ($hashes.ContainsKey($name)) {
      Copy-Item -LiteralPath (Join-Path $backup $name) -Destination $path -Force
      if ((Get-FileHash -LiteralPath $path).Hash -ne $hashes[$name]) { throw "Profile restoration hash mismatch: $name" }
    } elseif (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
  }
  Write-Output 'Moddable Fluids and fixture packages removed; original Deep Frontier/API enablement and PlayerData files restored; hashes verified.'
}
