# Build/install only the separate Fluids API development package with the official Mod Builder.
#
#   build_fluids_api.ps1                     # FluidsApi only (flag-gated: binds nothing without -fluidsApiWorkerAcceptance)
#   build_fluids_api.ps1 -SyntheticFixtures  # also the two synthetic consumer fixtures
#
# Timberborn enables a newly installed mod by default (ModPlayerPrefsHelper.IsModEnabled
# returns true without a saved key), and the compiled fixture cannot even be enumerated
# without Fluids API. The fixtures are therefore moved out of the Mods folder right after
# the official build, into outputs/fluids-api-prototype/fixture-packages/<Id>, and only
# tools/start_fluid_worker_acceptance.ps1 installs them for a run and removes them after.
param([switch]$SyntheticFixtures)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'unity','workshopContent','timberbornDocuments'
if (Get-Process Timberborn -ErrorAction SilentlyContinue) { throw 'Close Timberborn before replacing the Fluids API package; the game loads every enabled mod DLL at startup.' }
if (Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object ExecutablePath -eq $dev.unity) { throw 'Close the Unity authoring editor (or wait for another official build) before the Fluids API build.' }
$project = Join-Path $root 'vendor/timberborn-modding'
$source = Join-Path $root 'src/FluidsApi'
$mods = [System.IO.Path]::GetFullPath((Join-Path $dev.timberbornDocuments 'Mods'))
$output = Join-Path $root 'outputs/fluids-api-prototype'
$managed = Join-Path $dev.timberbornDocuments 'ModsBuild/TimberbornModExamples_Data/Managed'
function Package([string]$id) {
  $path = [System.IO.Path]::GetFullPath((Join-Path $mods "$id/version-1.1"))
  if (-not $path.StartsWith($mods + [System.IO.Path]::DirectorySeparatorChar, [StringComparison]::OrdinalIgnoreCase)) { throw "Build target for $id escapes the Mods folder." }
  $path
}
function Stage([string]$modName, [string]$manifest, [object[]]$assemblies) {
  $stage = Join-Path $project "Assets/Mods/$modName"
  New-Item -ItemType Directory -Force -Path $stage | Out-Null
  Copy-Item -LiteralPath $manifest -Destination $stage -Force
  foreach ($assembly in $assemblies) {
    $target = Join-Path $stage ('Scripts/' + $assembly.Folder)
    New-Item -ItemType Directory -Force -Path $target | Out-Null
    Copy-Item -LiteralPath $assembly.Asmdef -Destination $target -Force
    foreach ($folder in $assembly.Sources) {
      $destination = Join-Path $target (Split-Path $folder -Leaf)
      New-Item -ItemType Directory -Force -Path $destination | Out-Null
      $activeNames = @(Get-ChildItem $folder -Filter '*.cs' -File | Select-Object -ExpandProperty Name)
      foreach ($old in Get-ChildItem -LiteralPath $destination -File -Filter '*.cs') {
        if ($old.Name -notin $activeNames) { Remove-Item -LiteralPath $old.FullName -Force }
      }
      foreach ($file in Get-ChildItem $folder -Filter '*.cs' -File) { Copy-Item -LiteralPath $file.FullName -Destination $destination -Force }
    }
  }
}
function Verify([string]$id, [string]$installed, [string]$manifest, [string[]]$expected) {
  if ((Get-Content (Join-Path $installed 'manifest.json') -Raw | ConvertFrom-Json).Id -ne $id) { throw "Unexpected installed identity for $id" }
  if ((Get-FileHash -LiteralPath (Join-Path $installed 'manifest.json')).Hash -ne (Get-FileHash -LiteralPath $manifest).Hash) { throw "Installed $id manifest differs from the authored source." }
  $files = @(Get-ChildItem -LiteralPath (Join-Path $installed 'Scripts') -File)
  if (@($files | Where-Object Name -notin $expected).Count -ne 0 -or $files.Count -ne $expected.Count) { throw "$id must contain exactly $($expected -join ', '), without embedded dependencies." }
  $hashes = @{}
  foreach ($name in $expected) {
    $actual = (Get-FileHash -LiteralPath (Join-Path $installed ('Scripts/' + $name))).Hash
    if ($actual -ne (Get-FileHash -LiteralPath (Join-Path $managed $name)).Hash) { throw "Official $id package differs from its compiled output: $name" }
    $hashes[$name] = $actual
  }
  $hashes
}

$api = @(
  @{Folder='Api';Asmdef=(Join-Path $source 'Authoring/FluidsApi.asmdef');Sources=@((Join-Path $source 'Api'))},
  @{Folder='Core';Asmdef=(Join-Path $source 'Authoring/FluidsApi.TransportPrototype.asmdef');Sources=@((Join-Path $source 'Transport'),(Join-Path $source 'Native'),(Join-Path $source 'Persistence'))},
  @{Folder='GameBridge';Asmdef=(Join-Path $source 'Authoring/FluidsApi.GamePrototype.asmdef');Sources=@((Join-Path $source 'GameBridge'))},
  @{Folder='Runtime';Asmdef=(Join-Path $source 'Authoring/FluidsApi.RuntimePrototype.asmdef');Sources=@((Join-Path $source 'Runtime'))}
)
Stage 'FluidsApi' (Join-Path $source 'manifest.json') $api
$fixtures = @(
  @{Id='FluidsApiSyntheticReflection';Folder=(Join-Path $source 'Examples/SyntheticReflection')},
  @{Id='FluidsApiSyntheticCompiled';Folder=(Join-Path $source 'Examples/SyntheticCompiled')}
)
if ($SyntheticFixtures) {
  foreach ($fixture in $fixtures) {
    if (Test-Path -LiteralPath (Join-Path $mods $fixture.Id)) { throw "$($fixture.Id) is installed in the Mods folder; the fixtures must only be present during an acceptance run. Remove it first." }
    Stage $fixture.Id (Join-Path $fixture.Folder 'manifest.json') @(@{Folder='Code';Asmdef=(Join-Path $fixture.Folder ($fixture.Id + '.asmdef'));Sources=@($fixture.Folder)})
  }
}
$dependencies = Join-Path $project 'Assets/Plugins/ModDependencies'
New-Item -ItemType Directory -Force -Path $dependencies | Out-Null
Copy-Item -LiteralPath (Join-Path $dev.workshopContent '3284904751/0Harmony.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/0Harmony.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/FluidsApiBatchBuild.cs') -Destination (Join-Path $project 'Assets/Tools/Editor/Scripts/ModBuilding') -Force
$log = Join-Path $output 'official-build.log'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$method = if ($SyntheticFixtures) { 'BuildWithSyntheticFixtures' } else { 'Build' }
$process = Start-Process -FilePath $dev.unity -WindowStyle Hidden -PassThru -ArgumentList @(
  '-batchmode','-nographics','-quit','-disable-assembly-updater','-projectPath',('"'+$project+'"'),
  '-executeMethod',"Timberborn.ModdingTools.ModBuilding.FluidsApiBatchBuild.$method",'-logFile',('"'+$log+'"'))
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "Official Fluids API build failed. See $log" }
$installed = Package 'FluidsApi'
$report = [ordered]@{ status='passed'; installed=$installed; version=(Get-Content (Join-Path $installed 'manifest.json') -Raw | ConvertFrom-Json).Version
  assemblies=(Verify 'FluidsApi' $installed (Join-Path $source 'manifest.json') @('FluidsApi.dll','FluidsApi.TransportPrototype.dll','FluidsApi.GamePrototype.dll','FluidsApi.RuntimePrototype.dll')) }
if ($SyntheticFixtures) {
  $report.fixtures = [ordered]@{}
  foreach ($fixture in $fixtures) {
    $built = Package $fixture.Id
    $hashes = Verify $fixture.Id $built (Join-Path $fixture.Folder 'manifest.json') @($fixture.Id + '.dll')
    $kept = Join-Path $output ('fixture-packages/' + $fixture.Id)
    if (Test-Path -LiteralPath $kept) { Remove-Item -LiteralPath $kept -Recurse -Force }
    New-Item -ItemType Directory -Force -Path (Split-Path $kept) | Out-Null
    Move-Item -LiteralPath (Join-Path $mods $fixture.Id) -Destination $kept
    if (Test-Path -LiteralPath (Join-Path $mods $fixture.Id)) { throw "$($fixture.Id) is still installed after the build." }
    $report.fixtures[$fixture.Id] = [ordered]@{ package=$kept; assemblies=$hashes }
  }
}
$report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $output 'package-report.json')
Write-Output "Official Fluids API package installed at $installed (flag-gated). Log: $log"
if ($SyntheticFixtures) { Write-Output "Synthetic fixture packages kept out of the Mods folder under $(Join-Path $output 'fixture-packages')." }
