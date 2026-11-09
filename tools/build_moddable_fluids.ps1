# Build/install only the separate Moddable Fluids development package with the official Mod Builder.
#
#   build_moddable_fluids.ps1                     # ModdableFluids only (flag-gated: binds nothing without -moddableFluidsWorkerAcceptance)
#   build_moddable_fluids.ps1 -SyntheticFixtures  # also the two synthetic consumer fixtures
#   build_moddable_fluids.ps1 -MoreFluids         # also the More Fluids package (public API only, provisional data)
#
# Timberborn enables a newly installed mod by default (ModPlayerPrefsHelper.IsModEnabled
# returns true without a saved key), and the compiled fixture cannot even be enumerated
# without Moddable Fluids. Nothing stays installed: right after the official build every
# package, the API included, is verified and moved out of the Mods folder into
# outputs/fluids-api-prototype/packages/<Id>. Only tools/start_fluid_worker_acceptance.ps1
# installs them, for one run, and removes them after. The official Mod Builder shares one
# Unity project with the Deep Frontier build; never run the two at once.
#
#   build_moddable_fluids.ps1 -RemoveLegacyPackage   # also delete the pre-rename "FluidsApi" development
#                                                    # package and its staged authoring copies (2026-11-09 rename)
# The build refuses to run while that legacy package is installed: it carries the old flag and
# assembly names, so it would load beside the renamed package without being detected as a copy.
param([switch]$SyntheticFixtures, [switch]$MoreFluids, [switch]$RemoveLegacyPackage)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'unity','workshopContent','timberbornDocuments'
if (Get-Process Timberborn -ErrorAction SilentlyContinue) { throw 'Close Timberborn before replacing the Moddable Fluids package; the game loads every enabled mod DLL at startup.' }
if (Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object ExecutablePath -eq $dev.unity) { throw 'Close the Unity authoring editor (or wait for another official build) before the Moddable Fluids build.' }
$project = Join-Path $root 'vendor/timberborn-modding'
$source = Join-Path $root 'src/ModdableFluids'
$mods = [System.IO.Path]::GetFullPath((Join-Path $dev.timberbornDocuments 'Mods'))
$output = Join-Path $root 'outputs/fluids-api-prototype'
$managed = Join-Path $dev.timberbornDocuments 'ModsBuild/TimberbornModExamples_Data/Managed'
# Pre-rename development package and staging (mod id FluidsApi, fixtures FluidsApiSynthetic*).
$legacyIds = @('FluidsApi','FluidsApiSyntheticReflection','FluidsApiSyntheticCompiled')
foreach ($id in $legacyIds) {
  $installedLegacy = Join-Path $mods $id
  $stagedLegacy = Join-Path $project "Assets/Mods/$id"
  foreach ($legacy in @($installedLegacy, $stagedLegacy)) {
    if (-not (Test-Path -LiteralPath $legacy)) { continue }
    $manifestPath = @(Get-ChildItem -LiteralPath $legacy -Filter 'manifest.json' -Recurse -File | Select-Object -First 1)
    if ($manifestPath.Count -ne 1 -or (Get-Content -LiteralPath $manifestPath[0].FullName -Raw | ConvertFrom-Json).Id -ne $id) { throw "$legacy is not the pre-rename $id package; not touching it." }
    if (-not $RemoveLegacyPackage) { throw "The pre-rename $id package is still present at $legacy. Rerun with -RemoveLegacyPackage to delete it (and Assets/Mods/$id staging)." }
    Remove-Item -LiteralPath $legacy -Recurse -Force
    Write-Output "Removed pre-rename $id at $legacy"
  }
  if (Test-Path -LiteralPath "$stagedLegacy.meta") { Remove-Item -LiteralPath "$stagedLegacy.meta" -Force }
}
if ($RemoveLegacyPackage) {
  $prefsPath = 'HKCU:\Software\Mechanistry\Timberborn'
  foreach ($name in (Get-Item -LiteralPath $prefsPath).GetValueNames() | Where-Object { $_ -match '^Mod(Enabled|Priority)\..*\.(FluidsApi|FluidsApiSyntheticReflection|FluidsApiSyntheticCompiled)_h\d+$' }) {
    Remove-ItemProperty -LiteralPath $prefsPath -Name $name
    Write-Output "Removed pre-rename preference $name"
  }
}
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
  @{Folder='Api';Asmdef=(Join-Path $source 'Authoring/ModdableFluids.asmdef');Sources=@((Join-Path $source 'Api'))},
  @{Folder='Core';Asmdef=(Join-Path $source 'Authoring/ModdableFluids.TransportPrototype.asmdef');Sources=@((Join-Path $source 'Transport'),(Join-Path $source 'Native'),(Join-Path $source 'Persistence'),(Join-Path $source 'Rendering'),(Join-Path $source 'Sources'),(Join-Path $source 'World'))},
  @{Folder='GameBridge';Asmdef=(Join-Path $source 'Authoring/ModdableFluids.GamePrototype.asmdef');Sources=@((Join-Path $source 'GameBridge'))},
  @{Folder='Runtime';Asmdef=(Join-Path $source 'Authoring/ModdableFluids.RuntimePrototype.asmdef');Sources=@((Join-Path $source 'Runtime'))}
)
if (Test-Path -LiteralPath (Join-Path $mods 'ModdableFluids')) { throw 'ModdableFluids is installed in the Mods folder; packages must only be present during an acceptance run. Remove it first.' }
Stage 'ModdableFluids' (Join-Path $source 'manifest.json') $api
# Shared-rendering shader variants (tools/moddable_fluids_shader_variants.mjs) go into the API's bundles.
& (Get-DevEnvironment 'node').node (Join-Path $PSScriptRoot 'moddable_fluids_shader_variants.mjs') --check
if ($LASTEXITCODE -ne 0) { throw 'Moddable Fluids shader variants are stale; run node tools/moddable_fluids_shader_variants.mjs' }
$stagedBundles = Join-Path $project 'Assets/Mods/ModdableFluids/AssetBundles'
if (Test-Path -LiteralPath $stagedBundles) { Remove-Item -LiteralPath $stagedBundles -Recurse -Force }
Copy-Item -LiteralPath (Join-Path $source 'AssetBundles') -Destination $stagedBundles -Recurse
$fixtures = @(
  @{Id='ModdableFluidsSyntheticReflection';Folder=(Join-Path $source 'Examples/SyntheticReflection')},
  @{Id='ModdableFluidsSyntheticCompiled';Folder=(Join-Path $source 'Examples/SyntheticCompiled')}
)
if ($SyntheticFixtures) {
  foreach ($fixture in $fixtures) {
    if (Test-Path -LiteralPath (Join-Path $mods $fixture.Id)) { throw "$($fixture.Id) is installed in the Mods folder; packages must only be present during an acceptance run. Remove it first." }
    Stage $fixture.Id (Join-Path $fixture.Folder 'manifest.json') @(@{Folder='Code';Asmdef=(Join-Path $fixture.Folder ($fixture.Id + '.asmdef'));Sources=@($fixture.Folder)})
  }
}
$moreFluidsSource = Join-Path $root 'src/MoreFluids'
if ($MoreFluids) {
  if (Test-Path -LiteralPath (Join-Path $mods 'MoreFluids')) { throw 'MoreFluids is installed in the Mods folder; packages must only be present during an acceptance run. Remove it first.' }
  Stage 'MoreFluids' (Join-Path $moreFluidsSource 'manifest.json') @(@{Folder='Code';Asmdef=(Join-Path $moreFluidsSource 'Scripts/MoreFluids.asmdef');Sources=@((Join-Path $moreFluidsSource 'Scripts'))})
}
$dependencies = Join-Path $project 'Assets/Plugins/ModDependencies'
New-Item -ItemType Directory -Force -Path $dependencies | Out-Null
Copy-Item -LiteralPath (Join-Path $dev.workshopContent '3284904751/0Harmony.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/0Harmony.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/ModdableFluidsBatchBuild.cs') -Destination (Join-Path $project 'Assets/Tools/Editor/Scripts/ModBuilding') -Force
$log = Join-Path $output 'official-build.log'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$method = if ($SyntheticFixtures -and $MoreFluids) { 'BuildWithSyntheticFixturesAndMoreFluids' } elseif ($SyntheticFixtures) { 'BuildWithSyntheticFixtures' } elseif ($MoreFluids) { 'BuildWithMoreFluids' } else { 'Build' }
$process = Start-Process -FilePath $dev.unity -WindowStyle Hidden -PassThru -ArgumentList @(
  '-batchmode','-nographics','-quit','-disable-assembly-updater','-projectPath',('"'+$project+'"'),
  '-executeMethod',"Timberborn.ModdingTools.ModBuilding.ModdableFluidsBatchBuild.$method",'-logFile',('"'+$log+'"'))
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "Official Moddable Fluids build failed. See $log" }
$installed = Package 'ModdableFluids'
function Keep([string]$id) {
  $kept = Join-Path $output ('packages/' + $id)
  if (Test-Path -LiteralPath $kept) { Remove-Item -LiteralPath $kept -Recurse -Force }
  New-Item -ItemType Directory -Force -Path (Split-Path $kept) | Out-Null
  Move-Item -LiteralPath (Join-Path $mods $id) -Destination $kept
  if (Test-Path -LiteralPath (Join-Path $mods $id)) { throw "$id is still installed after the build." }
  $kept
}
$version = (Get-Content (Join-Path $installed 'manifest.json') -Raw | ConvertFrom-Json).Version
$apiHashes = Verify 'ModdableFluids' $installed (Join-Path $source 'manifest.json') @('ModdableFluids.dll','ModdableFluids.TransportPrototype.dll','ModdableFluids.GamePrototype.dll','ModdableFluids.RuntimePrototype.dll')
foreach ($platform in 'win','mac') {
  $bundle = Join-Path $installed "AssetBundles/moddablefluids_$platform"
  if (-not (Test-Path -LiteralPath $bundle) -or (Get-Item -LiteralPath $bundle).Length -eq 0) { throw "The official build produced no $platform shader bundle." }
  $apiHashes["moddablefluids_$platform"] = (Get-FileHash -LiteralPath $bundle).Hash
}
$report = [ordered]@{ status='passed'; package=(Keep 'ModdableFluids'); version=$version; assemblies=$apiHashes }
if ($SyntheticFixtures) {
  $report.fixtures = [ordered]@{}
  foreach ($fixture in $fixtures) {
    $hashes = Verify $fixture.Id (Package $fixture.Id) (Join-Path $fixture.Folder 'manifest.json') @($fixture.Id + '.dll')
    $report.fixtures[$fixture.Id] = [ordered]@{ package=(Keep $fixture.Id); assemblies=$hashes }
  }
}
if ($MoreFluids) {
  $hashes = Verify 'MoreFluids' (Package 'MoreFluids') (Join-Path $moreFluidsSource 'manifest.json') @('MoreFluids.dll')
  $report.moreFluids = [ordered]@{ package=(Keep 'MoreFluids'); assemblies=$hashes }
}
$report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $output 'package-report.json')
Write-Output "Official Moddable Fluids packages verified and kept out of the Mods folder under $(Join-Path $output 'packages'). Log: $log"
