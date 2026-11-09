# Build/install only the separate Moddable Fluids development package with the official Mod Builder.
#
#   build_moddable_fluids.ps1                     # ModdableFluids only (flag-gated: binds nothing without -moddableFluidsWorkerAcceptance)
#   build_moddable_fluids.ps1 -SyntheticFixtures  # also the two synthetic consumer fixtures
#   build_moddable_fluids.ps1 -MoreFluids         # also the More Fluids package: its code (public API and game only) and its
#                                                 # Data (blueprints, models, icons, sprites, localization) as authored
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
#
# Unity runs through tools/UnityProcess.ps1 (below-normal priority, two logical processors left free). The API's
# shader bundles are built only when their inputs changed since the last verified build; otherwise that build's
# bundles are installed and Unity builds the code alone (tools/UnityBundleCache.ps1, docs/unity-build-performance.md).
param([switch]$SyntheticFixtures, [switch]$MoreFluids, [switch]$RemoveLegacyPackage)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
. (Join-Path $PSScriptRoot 'UnityProcess.ps1')
. (Join-Path $PSScriptRoot 'UnityBundleCache.ps1')
$dev = Get-DevEnvironment 'unity','workshopContent','timberbornDocuments','python'
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
  @{Folder='Runtime';Asmdef=(Join-Path $source 'Authoring/ModdableFluids.RuntimePrototype.asmdef');Sources=@((Join-Path $source 'Runtime'),(Join-Path $source 'Tides'))}
)
if (Test-Path -LiteralPath (Join-Path $mods 'ModdableFluids')) { throw 'ModdableFluids is installed in the Mods folder; packages must only be present during an acceptance run. Remove it first.' }
Stage 'ModdableFluids' (Join-Path $source 'manifest.json') $api
# Shared-rendering shader variants (tools/moddable_fluids_shader_variants.mjs) go into the API's bundles.
& (Get-DevEnvironment 'node').node (Join-Path $PSScriptRoot 'moddable_fluids_shader_variants.mjs') --check
if ($LASTEXITCODE -ne 0) { throw 'Moddable Fluids shader variants are stale; run node tools/moddable_fluids_shader_variants.mjs' }
# Synchronised file by file, keeping Unity's .meta files (the GUIDs the bundles' object ids derive from), so unchanged
# bundle inputs keep their fingerprint (tools/UnityBundleCache.ps1); staged files without a source go with their .meta.
$stagedBundles = Join-Path $project 'Assets/Mods/ModdableFluids/AssetBundles'
$sourceBundles = Join-Path $source 'AssetBundles'
New-Item -ItemType Directory -Force -Path $stagedBundles | Out-Null
Copy-Item -Path (Join-Path $sourceBundles '*') -Destination $stagedBundles -Recurse -Force
$stagedBundlesFull = (Resolve-Path -LiteralPath $stagedBundles).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
foreach ($file in Get-ChildItem -LiteralPath $stagedBundles -File -Recurse) {
  $relative = $file.FullName.Substring($stagedBundlesFull.Length + 1)
  $origin = if ($file.Extension -eq '.meta') { $relative.Substring(0, $relative.Length - 5) } else { $relative }
  if (-not (Test-Path -LiteralPath (Join-Path $sourceBundles $origin))) { Remove-Item -LiteralPath $file.FullName -Force; Write-Output "Removed stale staged Moddable Fluids bundle file: $relative" }
}
Get-ChildItem -LiteralPath $stagedBundles -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending |
  Where-Object { -not (Test-Path -LiteralPath (Join-Path $sourceBundles $_.FullName.Substring($stagedBundlesFull.Length + 1))) } |
  ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force }
# The tide system's texts (new-game rows, refusals) ship as the package's localization.
$tideLocalization = Join-Path $source 'Tides/Localizations/enUS.csv'
$stagedLocalizations = Join-Path $project 'Assets/Mods/ModdableFluids/Data/Localizations'
New-Item -ItemType Directory -Force -Path $stagedLocalizations | Out-Null
Copy-Item -LiteralPath $tideLocalization -Destination $stagedLocalizations -Force
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
$moreFluidsData = Join-Path $moreFluidsSource 'Data'
# Every model, icon and sprite More Fluids references, as Data-relative paths with their file extension. Blueprints
# name models and icons; the tide sprites are named in code (MoreFluidsLiquids.Tide), so they are listed here, as in the
# harness art list (tools/compile-check/fluid-transport-harness/HarnessExtensions.MoreFluids.cs).
function MoreFluidsArt {
  $paths = [System.Collections.Generic.SortedSet[string]]::new([StringComparer]::Ordinal)
  foreach ($file in Get-ChildItem -LiteralPath $moreFluidsData -Filter '*.blueprint.json' -File -Recurse) {
    foreach ($match in [regex]::Matches((Get-Content -LiteralPath $file.FullName -Raw), '"(Model|Icon)":\s*"((Buildings/Water|MapEditor/Objects)/MoreFluids[^"]+)"')) {
      [void]$paths.Add($match.Groups[2].Value + $(if ($match.Groups[1].Value -eq 'Model') { '.timbermesh' } else { '.png' }))
    }
  }
  foreach ($tide in 'Coffee','Salt') { foreach ($part in 'Icon','Progress','Notification') { [void]$paths.Add("Sprites/Weather/MoreFluids${tide}Tide$part.png") } }
  foreach ($path in @($paths)) { if ($path.EndsWith('.png')) { [void]$paths.Add($path + '.meta.json') } }
  @($paths)
}
# The authored Data, file by file (Data-relative path to SHA-256); Unity's .meta files are not part of it. The official
# AssetsCopier copies Data's contents into the package root, so a package is read from its root without the top-level
# names in $exclude (its manifest and Scripts).
function DataHashes([string]$folder, [string[]]$exclude = @()) {
  $hashes = [ordered]@{}
  $full = (Resolve-Path -LiteralPath $folder).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
  foreach ($file in Get-ChildItem -LiteralPath $folder -File -Recurse | Where-Object Extension -ne '.meta' | Sort-Object FullName) {
    $relative = $file.FullName.Substring($full.Length + 1).Replace([IO.Path]::DirectorySeparatorChar, '/')
    if ($relative.Split('/')[0] -in $exclude) { continue }
    $hashes[$relative] = (Get-FileHash -LiteralPath $file.FullName).Hash
  }
  $hashes
}
if ($MoreFluids) {
  if (Test-Path -LiteralPath (Join-Path $mods 'MoreFluids')) { throw 'MoreFluids is installed in the Mods folder; packages must only be present during an acceptance run. Remove it first.' }
  # More Fluids uses only native materials: it has no Unity assets, so the official build makes no bundle for it.
  if (Test-Path -LiteralPath (Join-Path $moreFluidsSource 'AssetBundles')) { throw 'src/MoreFluids/AssetBundles exists: build its bundles in ModdableFluidsBatchBuild before packaging More Fluids.' }
  $missingArt = @(MoreFluidsArt | Where-Object { -not (Test-Path -LiteralPath (Join-Path $moreFluidsData $_) -PathType Leaf) })
  if ($missingArt.Count -ne 0) { throw "More Fluids references art that is not in src/MoreFluids/Data yet:`n  " + ($missingArt -join "`n  ") }
  foreach ($meta in Get-ChildItem -LiteralPath $moreFluidsData -Filter '*.png.meta.json' -File -Recurse) {
    if ((Get-Content -LiteralPath $meta.FullName -Raw).Trim() -ne '{"isSprite":true}') { throw "$($meta.FullName) must be {""isSprite"":true}" }
  }
  Stage 'MoreFluids' (Join-Path $moreFluidsSource 'manifest.json') @(@{Folder='Code';Asmdef=(Join-Path $moreFluidsSource 'Scripts/MoreFluids.asmdef');Sources=@((Join-Path $moreFluidsSource 'Scripts'))})
  # Data as authored: copy every file, then delete staged files (and their Unity .meta) that no longer have a source.
  $stagedData = Join-Path $project 'Assets/Mods/MoreFluids/Data'
  New-Item -ItemType Directory -Force -Path $stagedData | Out-Null
  Copy-Item -Path (Join-Path $moreFluidsData '*') -Destination $stagedData -Recurse -Force
  $stagedFull = (Resolve-Path -LiteralPath $stagedData).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
  foreach ($file in Get-ChildItem -LiteralPath $stagedData -File -Recurse) {
    $relative = $file.FullName.Substring($stagedFull.Length + 1)
    $origin = if ($file.Extension -eq '.meta') { $relative.Substring(0, $relative.Length - 5) } else { $relative }
    if (-not (Test-Path -LiteralPath (Join-Path $moreFluidsData $origin))) { Remove-Item -LiteralPath $file.FullName -Force; Write-Output "Removed stale staged More Fluids file: $relative" }
  }
  Get-ChildItem -LiteralPath $stagedData -Directory -Recurse | Sort-Object { $_.FullName.Length } -Descending |
    Where-Object { -not (Test-Path -LiteralPath (Join-Path $moreFluidsData $_.FullName.Substring($stagedFull.Length + 1))) } |
    ForEach-Object { Remove-Item -LiteralPath $_.FullName -Recurse -Force; if (Test-Path -LiteralPath "$($_.FullName).meta") { Remove-Item -LiteralPath "$($_.FullName).meta" -Force } }
}
$dependencies = Join-Path $project 'Assets/Plugins/ModDependencies'
New-Item -ItemType Directory -Force -Path $dependencies | Out-Null
Copy-Item -LiteralPath (Join-Path $dev.workshopContent '3284904751/0Harmony.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/0Harmony.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/ModdableFluidsBatchBuild.cs') -Destination (Join-Path $project 'Assets/Tools/Editor/Scripts/ModBuilding') -Force
# Strips variants of our own shaders that the game never draws (docs/unity-build-performance.md).
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/ModShaderVariantStripping.cs') -Destination (Join-Path $project 'Assets/Tools/Editor/Scripts/ModBuilding') -Force
# The Mod Builder's throwaway player builds (used only for their DLLs) compile no shader under Assets/Mods.
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/PlayerBuildShaderStripping.cs') -Destination (Join-Path $project 'Assets/Tools/Editor/Scripts/ModBuilding') -Force
$log = Join-Path $output 'official-build.log'
New-Item -ItemType Directory -Force -Path $output | Out-Null
$method = if ($SyntheticFixtures -and $MoreFluids) { 'BuildWithSyntheticFixturesAndMoreFluids' } elseif ($SyntheticFixtures) { 'BuildWithSyntheticFixtures' } elseif ($MoreFluids) { 'BuildWithMoreFluids' } else { 'Build' }
$cache = Get-BundleCacheEntry -Root $root -Mod 'ModdableFluids' -Variant 'default'
$inputs = Get-BundleInputs -Project $project -Mod 'ModdableFluids' -Variant 'default' -Unity $dev.unity
$reuse = Test-BundleCacheHit -Entry $cache -Inputs $inputs
$process = Start-UnityProcess -FilePath $dev.unity -Hidden -ArgumentList @(
  '-batchmode','-nographics','-quit','-disable-assembly-updater','-projectPath',('"'+$project+'"'),
  '-executeMethod',"Timberborn.ModdingTools.ModBuilding.ModdableFluidsBatchBuild.$method",
  '-modBundles',$(if ($reuse) { 'reuse' } else { 'build' }),'-logFile',('"'+$log+'"'))
# From here on the builder may have installed packages into Mods. Any failure moves every package this build
# produces out of Mods (into outputs/fluids-api-prototype/failed-build/<time>) before rethrowing, so nothing stays installed.
$builtIds = @('ModdableFluids') + $(if ($SyntheticFixtures) { $fixtures | ForEach-Object { $_.Id } } else { @() }) + $(if ($MoreFluids) { @('MoreFluids') } else { @() })
function Evacuate {
  $failed = Join-Path $output ('failed-build/' + (Get-Date -Format 'yyyyMMdd-HHmmss'))
  foreach ($id in $builtIds) {
    $left = Join-Path $mods $id
    if (-not (Test-Path -LiteralPath $left)) { continue }
    $manifestPath = @(Get-ChildItem -LiteralPath $left -Filter 'manifest.json' -Recurse -File | Select-Object -First 1)
    if ($manifestPath.Count -ne 1 -or (Get-Content -LiteralPath $manifestPath[0].FullName -Raw | ConvertFrom-Json).Id -ne $id) { Write-Warning "$left is not this build's $id package; left in place."; continue }
    New-Item -ItemType Directory -Force -Path $failed | Out-Null
    Move-Item -LiteralPath $left -Destination (Join-Path $failed $id)
    if (Test-Path -LiteralPath $left) { Write-Warning "$id is STILL installed at $left; remove it by hand." } else { Write-Warning "Moved the failed build's $id out of Mods to $failed" }
  }
}
try {
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "Official Moddable Fluids build failed. See $log" }
Write-Output 'Shader variant stripping (tools/unity/ModShaderVariantStripping.cs):'
Get-ShaderStrippingSummary $log
$installed = Package 'ModdableFluids'
$builtInputs = Get-BundleInputs -Project $project -Mod 'ModdableFluids' -Variant 'default' -Unity $dev.unity
if ($reuse) {
  Assert-BundleInputsUnchanged -Entry $cache -Before $inputs -After $builtInputs
  Install-CachedBundles -Entry $cache -Destination (Join-Path $installed 'AssetBundles')
}
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
& $dev.python (Join-Path $root 'tools/asset-pipeline/check_bundle_shaders.py') --win (Join-Path $installed 'AssetBundles/moddablefluids_win') `
  --mac (Join-Path $installed 'AssetBundles/moddablefluids_mac') --expect 'ModdableFluids/FluidWaterURP_Opaque' 'ModdableFluids/FluidWaterURP_Transparent'
if ($LASTEXITCODE -ne 0) { throw 'The shader bundles do not hold exactly the variants the game can draw (tools/asset-pipeline/check_bundle_shaders.py).' }
$packagedLocalization = @(Get-ChildItem -LiteralPath $installed -Recurse -File -Filter 'enUS.csv' | Where-Object { $_.Directory.Name -eq 'Localizations' })
if ($packagedLocalization.Count -ne 1 -or (Get-FileHash -LiteralPath $packagedLocalization[0].FullName).Hash -ne (Get-FileHash -LiteralPath $tideLocalization).Hash) {
  throw 'The official Moddable Fluids package must hold exactly the tide localization src/ModdableFluids/Tides/Localizations/enUS.csv.' }
$apiHashes['Localizations/enUS.csv'] = (Get-FileHash -LiteralPath $tideLocalization).Hash
$report = [ordered]@{ status='passed'; package=(Keep 'ModdableFluids'); version=$version; assemblies=$apiHashes }
$keptBundles = Join-Path $report.package 'version-1.1/AssetBundles'
if ($SyntheticFixtures) {
  $report.fixtures = [ordered]@{}
  foreach ($fixture in $fixtures) {
    $hashes = Verify $fixture.Id (Package $fixture.Id) (Join-Path $fixture.Folder 'manifest.json') @($fixture.Id + '.dll')
    $report.fixtures[$fixture.Id] = [ordered]@{ package=(Keep $fixture.Id); assemblies=$hashes }
  }
}
if ($MoreFluids) {
  $moreFluidsPackage = Package 'MoreFluids'
  $hashes = Verify 'MoreFluids' $moreFluidsPackage (Join-Path $moreFluidsSource 'manifest.json') @('MoreFluids.dll')
  # The package root holds exactly the authored Data (art included) beside its manifest and Scripts.
  $expectedData = DataHashes $moreFluidsData
  $packagedData = DataHashes $moreFluidsPackage @('manifest.json','Scripts')
  $differences = @(@($expectedData.Keys) + @($packagedData.Keys) | Sort-Object -Unique | Where-Object { $expectedData[$_] -ne $packagedData[$_] })
  if ($differences.Count -ne 0) { throw "Official More Fluids package Data differs from src/MoreFluids/Data:`n  " + ($differences -join "`n  ") }
  $allowed = @('manifest.json','Scripts') + @(Get-ChildItem -LiteralPath $moreFluidsData | Select-Object -ExpandProperty Name)
  $extra = @(Get-ChildItem -LiteralPath $moreFluidsPackage | Where-Object Name -notin $allowed)
  if ($extra.Count -ne 0) { throw "Official More Fluids package holds more than its manifest, Scripts and Data: $($extra.Name -join ', ')" }
  $report.moreFluids = [ordered]@{ package=(Keep 'MoreFluids'); assemblies=$hashes; dataFiles=$expectedData.Count; art=@(MoreFluidsArt).Count }
}
# Verified: a fresh build's bundles are cached; the kept package's bundles are the cached ones either way.
if (-not $reuse) { Save-BundleCache -Entry $cache -Inputs $builtInputs -Source $keptBundles }
$bundleRecord = Assert-BundlesMatchCache -Entry $cache -Directory $keptBundles -Inputs $builtInputs
$report.bundles = [ordered]@{ reused=[bool]$reuse; fingerprint=$bundleRecord.fingerprint; cache=$cache }
$report | ConvertTo-Json -Depth 4 | Set-Content (Join-Path $output 'package-report.json')
} catch { Evacuate; throw }
Write-Output "Official Moddable Fluids packages verified and kept out of the Mods folder under $(Join-Path $output 'packages'). Log: $log"
