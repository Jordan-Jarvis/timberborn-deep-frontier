#Requires -Version 7
# One interactive game with the flagged Deep Frontier test package on Moddable Fluids, for the in-game gates in
# docs/deep-frontier-fluids-migration.md. Nothing it installs stays installed, and the user's files come back byte
# for byte:
#
#   start_deep_frontier_moddable_fluids.ps1                      # Moddable Fluids + flagged Deep Frontier
#   start_deep_frontier_moddable_fluids.ps1 -MoreFluids          # also More Fluids (its tides share the budget)
#   start_deep_frontier_moddable_fluids.ps1 -SaveCopies a.timber,b.timber
#                                                                # copies of saves to load, in a test settlement
#   start_deep_frontier_moddable_fluids.ps1 -ModdableWeathers    # keep Moddable Weathers on: the tides run as its
#                                                                # weathers through Moddable Fluids' optional adapter
#
# Before the game starts it copies aside, with SHA-256 hashes of every file:
# - the installed (shipped) Mods/DeepFrontier, which the test package replaces for the run;
# - Saves and ExperimentalSaves (autosaves rotate, and a flagged save cannot be read by the shipped build);
# - the PlayerData files, as start_fluid_worker_acceptance.ps1 does;
# - every ModEnabled/ModPriority preference value, with its registry type.
# It then installs Moddable Fluids (and More Fluids) from outputs/fluids-api-prototype/packages and the test package from
# outputs/deep-frontier-moddable-fluids/package, and enables them. Moddable Weathers is switched off for the run, so the
# tides run on the native weather (the binding most gates describe); -ModdableWeathers keeps it and its required mods
# (Moddable Timberborn, TimberUi, Harmony) on instead, so Moddable Fluids' optional adapter runs the tides as Moddable
# Weathers weathers, for example to load a save played with the shipped Deep Frontier and Moddable Weathers. The game
# shows its startup dialogs; click through them. Quit the game to end the run.
#
# Afterwards (also after a crash or a stopped run) it removes the test packages, restores Mods/DeepFrontier, puts
# every preference value back with its type and deletes the ones the game created, restores PlayerData, and returns
# Saves and ExperimentalSaves to their backed-up state: files the run created or changed are first moved or copied
# into the run folder (outputs/deep-frontier-moddable-fluids/runs/<time>/evidence), so its saves stay available
# as evidence. Steam's steam_autocloud.vdf is left as Steam keeps it. Every restore is hash-verified; a mismatch
# stops with the run folder named, which then also holds the backups and a restore-pending marker.
param([switch]$MoreFluids, [switch]$ModdableWeathers, [string[]]$SaveCopies = @(), [int]$TimeoutSeconds = 6 * 3600)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$documents = $dev.timberbornDocuments
$mods = Join-Path $documents 'Mods'
$output = Join-Path $root 'outputs/deep-frontier-moddable-fluids'
$testPackage = Join-Path $output 'package/DeepFrontier'
$apiPackages = Join-Path $root 'outputs/fluids-api-prototype/packages'
$testSettlement = 'Deep Frontier Moddable Fluids Test'
$saveFolders = @('Saves', 'ExperimentalSaves')
$prefsPath = 'Software\Mechanistry\Timberborn'
$prefsPattern = '^Mod(Enabled|Priority)\.'

# ---------------------------------------------------------------- refusals (nothing changed yet)
if (Get-Process Timberborn -ErrorAction SilentlyContinue) { throw 'Close Timberborn before the Moddable Fluids gate run.' }
$pending = @(Get-ChildItem -LiteralPath (Join-Path $output 'runs') -Filter 'restore-pending' -File -Recurse -ErrorAction SilentlyContinue)
if ($pending.Count -ne 0) { throw "An earlier run did not finish its restore: $($pending.DirectoryName -join ', '). Restore from its backup by hand, then delete its restore-pending file." }
if (-not (Test-Path -LiteralPath (Join-Path $testPackage 'version-1.1/Scripts/DeepFrontier.dll')) -or -not (Test-Path -LiteralPath (Join-Path $output 'package-report.json'))) {
  throw "Missing the flagged Deep Frontier test package at $testPackage; build it with tools/build_deep_frontier.ps1 -ModdableFluids."
}
$packageIds = @('ModdableFluids') + $(if ($MoreFluids) { @('MoreFluids') } else { @() })
foreach ($id in $packageIds) {
  if (-not (Test-Path -LiteralPath (Join-Path $apiPackages "$id/version-1.1/Scripts/$id.dll"))) { throw "Missing kept package $id; run tools/build_moddable_fluids.ps1$(if ($MoreFluids) { ' -MoreFluids' })." }
}
foreach ($id in @('ModdableFluids', 'MoreFluids', 'ModdableFluidsSyntheticReflection', 'ModdableFluidsSyntheticCompiled')) {
  if (Test-Path -LiteralPath (Join-Path $mods $id)) { throw "$id is already in the Mods folder; it must be installed only by a launcher." }
}
$required = (Get-Content -LiteralPath (Join-Path $testPackage 'version-1.1/manifest.json') -Raw | ConvertFrom-Json).RequiredMods | Where-Object Id -eq 'ModdableFluids'
$apiVersion = (Get-Content -LiteralPath (Join-Path $apiPackages 'ModdableFluids/version-1.1/manifest.json') -Raw | ConvertFrom-Json).Version
if (-not $required -or $required.MinimumVersion -ne $apiVersion) { throw "The test package was built against Moddable Fluids $($required.MinimumVersion), the kept package is $apiVersion; rebuild the test package." }
foreach ($copy in $SaveCopies) { if (-not (Test-Path -LiteralPath $copy -PathType Leaf) -or [IO.Path]::GetExtension($copy) -ne '.timber') { throw "Not a save file: $copy" } }
$settlementPath = Join-Path $documents "Saves/$testSettlement"
if (Test-Path -LiteralPath $settlementPath) { throw "$settlementPath exists; this launcher creates that settlement for the save copies and moves it out afterwards." }
# Moddable Weathers stays off unless -ModdableWeathers. The launch skips the mod screen, so a Moddable Weathers that is
# enabled only by default (no preference value yet) cannot be switched off for the run here.
$workshop = (Get-DevEnvironment 'workshopContent').workshopContent
$weathersInstalled = (Test-Path -LiteralPath (Join-Path $mods 'ModdableWeathers')) -or (Test-Path -LiteralPath (Join-Path $workshop '3630523180'))
$probe = [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($prefsPath)
if (-not $probe) { throw "HKCU\$prefsPath is missing; start Timberborn once normally first." }
$weathersKey = @($probe.GetValueNames() | Where-Object { $_ -match '^ModEnabled\..*\.ModdableWeathers_h\d+$' })
$probe.Dispose()
# Moddable Weathers and the mods it requires (Moddable Timberborn, which requires TimberUi and Harmony).
$weathersChain = '\.(ModdableWeathers|ModdableTimberborn|TimberUi|Harmony)_h\d+$'
if ($ModdableWeathers) {
  if (-not $weathersInstalled) { throw '-ModdableWeathers: Moddable Weathers is not installed (Workshop item 3630523180 or Mods/ModdableWeathers).' }
  $adapter = Join-Path $apiPackages 'ModdableFluids/version-1.1/Scripts/ModdableFluids.ModdableWeathers.dll.ModdableWeathers.optional'
  if (-not (Test-Path -LiteralPath $adapter)) { throw "-ModdableWeathers: the kept Moddable Fluids package has no Moddable Weathers adapter ($adapter); rebuild it with tools/build_moddable_fluids.ps1." }
} elseif ($weathersInstalled -and $weathersKey.Count -eq 0) {
  throw 'Moddable Weathers is installed without a preference value (enabled by default), and the launch skips the mod screen. Switch it off and on once in the game''s mod screen so the value exists, then rerun; the launcher disables it for the run and puts the value back afterwards. To run with Moddable Weathers, pass -ModdableWeathers.'
}

function Tree([string]$folder, [string[]]$skip = @()) {
  $hashes = [ordered]@{}
  if (-not (Test-Path -LiteralPath $folder)) { return $hashes }
  $full = (Resolve-Path -LiteralPath $folder).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
  foreach ($file in Get-ChildItem -LiteralPath $folder -File -Recurse -Force | Sort-Object FullName) {
    $relative = $file.FullName.Substring($full.Length + 1)
    if ($relative -in $skip) { continue }
    $hashes[$relative] = (Get-FileHash -LiteralPath $file.FullName).Hash
  }
  $hashes
}
function SameMap($a, $b) { ($a | ConvertTo-Json -Depth 3 -Compress) -eq ($b | ConvertTo-Json -Depth 3 -Compress) }
function Prefs { [Microsoft.Win32.Registry]::CurrentUser.OpenSubKey($prefsPath, $true) ?? $(throw "HKCU\$prefsPath is missing; start Timberborn once normally first.") }

# ---------------------------------------------------------------- backup
$run = Join-Path $output ('runs/' + (Get-Date -Format 'yyyyMMdd-HHmmss-fff'))
$backup = Join-Path $run 'backup'
$evidence = Join-Path $run 'evidence'
New-Item -ItemType Directory -Force -Path $backup, $evidence | Out-Null
Set-Content -LiteralPath (Join-Path $run 'restore-pending') -Value 'This run has not finished restoring the files under backup.'
$installedRoot = Join-Path $mods 'DeepFrontier'
$installedExisted = Test-Path -LiteralPath $installedRoot
$installedTree = Tree $installedRoot
if ($installedExisted) {
  Copy-Item -LiteralPath $installedRoot -Destination (Join-Path $backup 'DeepFrontier') -Recurse
  if (-not (SameMap (Tree (Join-Path $backup 'DeepFrontier')) $installedTree)) { throw "The backup of $installedRoot does not match it; nothing was changed. See $run." }
}
$saveTrees = @{}
$saveDirectories = @{}
foreach ($folder in $saveFolders) {
  $path = Join-Path $documents $folder
  $saveTrees[$folder] = Tree $path @('steam_autocloud.vdf')
  $saveDirectories[$folder] = @(if (Test-Path -LiteralPath $path) {
    $full = (Resolve-Path -LiteralPath $path).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
    Get-ChildItem -LiteralPath $path -Directory -Recurse -Force | ForEach-Object { $_.FullName.Substring($full.Length + 1) } })
  if (Test-Path -LiteralPath $path) {
    Copy-Item -LiteralPath $path -Destination (Join-Path $backup $folder) -Recurse
    if (-not (SameMap (Tree (Join-Path $backup $folder) @('steam_autocloud.vdf')) $saveTrees[$folder])) { throw "The backup of $path does not match it; nothing was changed. See $run." }
  }
}
$profile = Join-Path $documents 'PlayerData'
$profileFiles = @('player.data', 'player.data.old', 'player.data.backup', 'LoadGameModValidator.txt', 'Replatform.txt')
$profileHashes = @{}
foreach ($name in $profileFiles) {
  $path = Join-Path $profile $name
  if (Test-Path -LiteralPath $path) { Copy-Item -LiteralPath $path -Destination (Join-Path $backup $name); $profileHashes[$name] = (Get-FileHash -LiteralPath $path).Hash }
}
$prefs = Prefs
$values = [ordered]@{}
foreach ($name in $prefs.GetValueNames() | Where-Object { $_ -match $prefsPattern } | Sort-Object) {
  $values[$name] = [pscustomobject]@{ Kind = $prefs.GetValueKind($name); Value = $prefs.GetValue($name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames) }
}
$prefs.Dispose()
[ordered]@{ installedExisted = $installedExisted; installed = $installedTree; saves = $saveTrees; playerData = $profileHashes
  preferences = @($values.Keys | ForEach-Object { [ordered]@{ name = $_; kind = "$($values[$_].Kind)"; value = $(if ($values[$_].Value -is [byte[]]) { [Convert]::ToBase64String($values[$_].Value) } else { $values[$_].Value }) } }) } |
  ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $backup 'original.json')
Write-Output "Backed up Mods/DeepFrontier ($($installedTree.Count) files), $($saveFolders -join ' and '), PlayerData and $($values.Count) mod preference values to $backup"

$log = Join-Path $run 'game.log'
$ownedProcess = $null
$problems = [Collections.Generic.List[string]]::new()
$runError = $null
try {
  # ------------------------------------------------------------ install for this run
  if ($installedExisted) { Remove-Item -LiteralPath $installedRoot -Recurse -Force }
  Copy-Item -LiteralPath $testPackage -Destination $installedRoot -Recurse
  foreach ($id in $packageIds) { Copy-Item -LiteralPath (Join-Path $apiPackages $id) -Destination (Join-Path $mods $id) -Recurse }
  # A mod without a key is enabled by default (ModPlayerPrefsHelper.IsModEnabled); existing keys are set for the run.
  $prefs = Prefs
  try {
    foreach ($name in $values.Keys | Where-Object { $_ -match '^ModEnabled\.' }) {
      # Local mods are keyed by folder and id (ModEnabled.Local.<folder>.<id>); only the folders this run installs.
      if ($name -match ('^ModEnabled\.Local\.(' + ((@('DeepFrontier') + $packageIds) -join '|') + ')\.\1_h\d+$')) { $prefs.SetValue($name, 1, [Microsoft.Win32.RegistryValueKind]::DWord) }
      elseif ($ModdableWeathers -and $name -match $weathersChain) { $prefs.SetValue($name, 1, [Microsoft.Win32.RegistryValueKind]::DWord) }
      elseif ($name -match '\.ModdableWeathers_h\d+$') { $prefs.SetValue($name, 0, [Microsoft.Win32.RegistryValueKind]::DWord) }
    }
  } finally { $prefs.Dispose() }
  if ($SaveCopies.Count -ne 0) {
    New-Item -ItemType Directory -Force -Path $settlementPath | Out-Null
    foreach ($copy in $SaveCopies) { Copy-Item -LiteralPath $copy -Destination $settlementPath }
    Write-Output "Copied $($SaveCopies.Count) save(s) into the settlement '$testSettlement'; load them from there."
  }

  # ------------------------------------------------------------ the game (interactive)
  $launch = @(& (Join-Path $PSScriptRoot 'launch_timberborn.ps1') -Arguments @('-logFile', ('"' + $log + '"')))
  $launch | Write-Output
  # Wait on the exact process the launch started; holding its handle keeps the exit code readable.
  $pids = @($launch | ForEach-Object { if ("$_" -match '^Started Timberborn\.exe \(pid (\d+)\)') { [int]$Matches[1] } })
  if ($pids.Count -ne 1) { throw 'The launch did not report exactly one Timberborn process id.' }
  $ownedProcess = Get-Process -Id $pids[0] -ErrorAction Stop
  $null = $ownedProcess.Handle
  Write-Output "Timberborn PID $($ownedProcess.Id) with the flagged Deep Frontier test package. Click through the startup dialogs; quit the game to end the run. Run folder: $run"
  if (-not $ownedProcess.WaitForExit($TimeoutSeconds * 1000)) { throw "The run exceeded $TimeoutSeconds seconds. See $log" }
  $ownedProcess.WaitForExit()
  $exitCode = $ownedProcess.ExitCode
  if ($null -eq $exitCode) { throw "The game's exit code is unavailable although its handle was held. See $log" }
  if ($exitCode -ne 0) { throw "The game exited with $exitCode. See $log" }
  Write-Output "The game exited normally. Its log ($log) holds the Moddable Fluids attach report and Deep Frontier's registration lines."
} catch {
  $runError = $_
  throw
} finally {
  if ($ownedProcess -and -not $ownedProcess.HasExited) { Stop-Process -Id $ownedProcess.Id -Force; $ownedProcess.WaitForExit() }
  # 1. Test packages out, the installed Deep Frontier back.
  try {
    foreach ($id in $packageIds) { if (Test-Path -LiteralPath (Join-Path $mods $id)) { Remove-Item -LiteralPath (Join-Path $mods $id) -Recurse -Force } }
    if (Test-Path -LiteralPath $installedRoot) { Remove-Item -LiteralPath $installedRoot -Recurse -Force }
    if ($installedExisted) {
      Copy-Item -LiteralPath (Join-Path $backup 'DeepFrontier') -Destination $installedRoot -Recurse
      if (-not (SameMap (Tree $installedRoot) $installedTree)) { throw 'the restored files differ from the originals' }
    }
    foreach ($id in $packageIds) { if (Test-Path -LiteralPath (Join-Path $mods $id)) { throw "$id is still installed" } }
  } catch { $problems.Add("Mods: $($_.Exception.Message)") }
  # 2. Preferences: every backed-up value with its type; values the run created are deleted.
  try {
    $prefs = Prefs
    try {
      foreach ($name in $prefs.GetValueNames() | Where-Object { $_ -match $prefsPattern -and -not $values.Contains($_) }) { $prefs.DeleteValue($name) }
      foreach ($name in $values.Keys) { $prefs.SetValue($name, $values[$name].Value, $values[$name].Kind) }
      foreach ($name in $values.Keys) {
        $now = $prefs.GetValue($name, $null, [Microsoft.Win32.RegistryValueOptions]::DoNotExpandEnvironmentNames)
        if ($prefs.GetValueKind($name) -ne $values[$name].Kind -or (($now | ConvertTo-Json -Compress) -ne ($values[$name].Value | ConvertTo-Json -Compress))) { throw "$name differs after the restore" }
      }
    } finally { $prefs.Dispose() }
  } catch { $problems.Add("Preferences: $($_.Exception.Message)") }
  # 3. PlayerData.
  try {
    foreach ($name in $profileFiles) {
      $path = Join-Path $profile $name
      if ($profileHashes.ContainsKey($name)) {
        Copy-Item -LiteralPath (Join-Path $backup $name) -Destination $path -Force
        if ((Get-FileHash -LiteralPath $path).Hash -ne $profileHashes[$name]) { throw "$name differs after the restore" }
      } elseif (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path }
    }
  } catch { $problems.Add("PlayerData: $($_.Exception.Message)") }
  # 4. Saves: what the run made or changed goes to the evidence folder, then the backed-up state comes back.
  foreach ($folder in $saveFolders) {
    try {
      $path = Join-Path $documents $folder
      $original = $saveTrees[$folder]
      $now = Tree $path @('steam_autocloud.vdf')
      foreach ($relative in $now.Keys) {
        if ($original.Contains($relative) -and $original[$relative] -eq $now[$relative]) { continue }
        $target = Join-Path $evidence "$folder/$relative"
        New-Item -ItemType Directory -Force -Path (Split-Path $target) | Out-Null
        if ($original.Contains($relative)) { Copy-Item -LiteralPath (Join-Path $path $relative) -Destination $target -Force }
        else { Move-Item -LiteralPath (Join-Path $path $relative) -Destination $target -Force }
      }
      foreach ($relative in $original.Keys) {
        $live = Join-Path $path $relative
        if ((Test-Path -LiteralPath $live) -and (Get-FileHash -LiteralPath $live).Hash -eq $original[$relative]) { continue }
        New-Item -ItemType Directory -Force -Path (Split-Path $live) | Out-Null
        Copy-Item -LiteralPath (Join-Path $backup "$folder/$relative") -Destination $live -Force
      }
      if (Test-Path -LiteralPath $path) {
        # Folders the run created (its settlements) are empty now; folders that existed before stay.
        $full = (Resolve-Path -LiteralPath $path).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
        Get-ChildItem -LiteralPath $path -Directory -Recurse -Force | Sort-Object { $_.FullName.Length } -Descending |
          Where-Object { $_.FullName.Substring($full.Length + 1) -notin $saveDirectories[$folder] -and @(Get-ChildItem -LiteralPath $_.FullName -Force).Count -eq 0 } |
          ForEach-Object { Remove-Item -LiteralPath $_.FullName }
      }
      if (-not (SameMap (Tree $path @('steam_autocloud.vdf')) $original)) { throw 'the restored files differ from the originals' }
    } catch { $problems.Add("${folder}: $($_.Exception.Message)") }
  }
  if ($problems.Count -ne 0) {
    throw "The run's restore FAILED; backups and the restore-pending marker stay in $run.`n  " + ($problems -join "`n  ") + $(if ($runError) { "`nThe run itself failed first: $($runError.Exception.Message)" } else { '' })
  }
  Remove-Item -LiteralPath $backup -Recurse -Force
  Remove-Item -LiteralPath (Join-Path $run 'restore-pending')
  $kept = @(Get-ChildItem -LiteralPath $evidence -File -Recurse)
  Write-Output "Restored Mods/DeepFrontier, preferences, PlayerData, $($saveFolders -join ' and ') (hashes verified); test packages removed. $($kept.Count) save file(s) the run made or changed are in $evidence."
}
