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
#   start_fluid_worker_acceptance.ps1 -MoreFluids # an interactive session with Moddable Fluids and More Fluids only
#                                                 # (build_moddable_fluids.ps1 -MoreFluids keeps both packages); no fixture,
#                                                 # no acceptance flag. Quit the game to end it; both packages, their
#                                                 # enablement keys and the PlayerData files are then restored as below.
param([int]$TimeoutSeconds = 360, [switch]$SaveReload, [switch]$MoreFluids)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (Get-Process Timberborn -ErrorAction SilentlyContinue) { throw 'Close Timberborn before the disposable worker acceptance run.' }
if ($MoreFluids -and $SaveReload) { throw '-MoreFluids is an interactive session; it does not combine with the -SaveReload fixture.' }
# An interactive session lasts as long as the player plays: six hours unless a timeout is given.
if ($MoreFluids -and -not $PSBoundParameters.ContainsKey('TimeoutSeconds')) { $TimeoutSeconds = 6 * 3600 }
if (-not $MoreFluids -and -not (Test-Path (Join-Path $dev.timberbornDocuments 'Maps/Moddable Fluids Worker Fixture.timber'))) { throw 'Generate the explicit worker fixture first.' }
$output = Join-Path $root 'outputs/fluids-api-prototype'
$mods = Join-Path $dev.timberbornDocuments 'Mods'
if (Test-Path -LiteralPath (Join-Path $mods 'FluidsApi')) { throw 'The pre-rename FluidsApi development package is still installed; remove it with tools/build_moddable_fluids.ps1 -RemoveLegacyPackage.' }
$allPackageIds = @('ModdableFluids','ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled','MoreFluids')
$fixtureIds = if ($MoreFluids) { @('ModdableFluids','MoreFluids') } else { @('ModdableFluids','ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled') }
$saveSettlements = @('Saves','ExperimentalSaves') | ForEach-Object { Join-Path $dev.timberbornDocuments "$_/Moddable Fluids Save Acceptance" }
foreach ($settlement in $saveSettlements) { if (Test-Path -LiteralPath $settlement) { throw "$settlement already exists; the save fixture owns that settlement and must start without it." } }
foreach ($id in $fixtureIds) {
  if (-not (Test-Path -LiteralPath (Join-Path $output "packages/$id/version-1.1/Scripts/$id.dll"))) { throw "Missing kept package $id; run tools/build_moddable_fluids.ps1 $(if ($MoreFluids) { '-MoreFluids' } else { '-SyntheticFixtures' })" }
}
foreach ($id in $allPackageIds) {
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
$ownedKeys = '^Mod(Enabled|Priority)\..*\.(ModdableFluids|ModdableFluidsSyntheticReflection|ModdableFluidsSyntheticCompiled|MoreFluids)_h\d+$'
$prefs = Get-Item -LiteralPath $prefsPath
$flags = @{}
foreach ($name in $prefs.GetValueNames() | Where-Object { $_ -match '^ModEnabled\..*\.(DeepFrontier|ModdableFluids|ModdableFluidsSyntheticReflection|ModdableFluidsSyntheticCompiled|MoreFluids)_h\d+$' }) {
  $flags[$name] = [int]$prefs.GetValue($name)
}
@{ playerDataHashes=$hashes; modFlags=$flags } | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $backup 'original.json')
$log = Join-Path $output $(if ($MoreFluids) { 'more-fluids-game.log' } else { 'worker-game.log' })
$report = Join-Path $output 'worker-report.json'
$ownedProcess = $null
$installedFixtures = @()
try {
  # Existing keys only: a mod without a key is enabled by default (ModPlayerPrefsHelper.IsModEnabled).
  foreach ($name in $flags.Keys) {
    # The installed packages on; Deep Frontier (whose lockstep patches conflict with the shared transport) and any package not in this run off.
    $enabled = if ($fixtureIds | Where-Object { $name -match ('\.' + $_ + '_h\d+$') }) { 1 } else { 0 }
    Set-ItemProperty -LiteralPath $prefsPath -Name $name -Value $enabled
  }
  foreach ($id in $fixtureIds) {
    Copy-Item -LiteralPath (Join-Path $output "packages/$id") -Destination (Join-Path $mods $id) -Recurse
    $installedFixtures += $id
  }
  if (Test-Path -LiteralPath $report) { Remove-Item -LiteralPath $report }
  $gameArguments = if ($MoreFluids) { @() } else { @('-moddableFluidsWorkerAcceptance', '-moddableFluidsReport', ('"'+$report+'"')) }
  if ($SaveReload) { $gameArguments += '-moddableFluidsSaveAcceptance' }
  $launch = @(& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments ($gameArguments + @('-logFile',('"'+$log+'"'))))
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
  if ($MoreFluids) {
    Write-Output "More Fluids session ended normally. The game log ($log) holds the Moddable Fluids attach report; nothing here verifies gameplay."
    return
  }
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
  foreach ($id in $allPackageIds) { if (Test-Path -LiteralPath (Join-Path $mods $id)) { throw "Package $id is still installed." } }
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
  Write-Output "Packages removed ($($fixtureIds -join ', ')); original Deep Frontier/API enablement and PlayerData files restored; hashes verified."
}
