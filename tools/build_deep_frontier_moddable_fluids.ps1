#Requires -Version 7
# A disposable Deep Frontier test package built with DEEP_FRONTIER_MODDABLE_FLUIDS
# (docs/deep-frontier-fluids-migration.md, "Switch-over plan"). Run through
#   pwsh tools/build_deep_frontier.ps1 -ModdableFluids
# The default build (no switch) is unchanged.
#
# It uses the official Mod Builder exactly as the default build does (stage_deep_frontier.ps1, then
# DeepFrontierBatchBuild.Build), with these differences in the staged authoring copy only:
# - src/DeepFrontier/ModdableFluids is staged into Scripts/ModdableFluids (the DeepFrontier assembly);
# - the staged DeepFrontier.asmdef defines DEEP_FRONTIER_MODDABLE_FLUIDS for that assembly alone (versionDefines on
#   the Unity editor version, which every editor satisfies) and references the ModdableFluids assembly definition.
#   build_moddable_fluids.ps1 stages Moddable Fluids' API as source into the same Unity project, as More Fluids also
#   compiles against it; a precompiled ModdableFluids.dll there would collide with that assembly definition. This
#   script therefore requires the staged API to be src/ModdableFluids/Api and its compiled ModdableFluids.dll to be
#   byte-identical to the official Moddable Fluids package's, before and after the build;
# - the staged manifest requires ModdableFluids (the official package's version) and drops ModdableWeathers, which
#   Moddable Fluids refuses together with tides; the Moddable Weathers bridge is left out of the package;
# - Moddable Fluids draws the water and the irradiated ground (its shared water renderer and terrain overlay, on
#   per-scene copies of the native materials), so all three of Deep Frontier's shader variants
#   (RadioactiveWaterURP_Opaque/_Transparent, IrradiatedTerrainURP) are set aside with their .meta files for the build
#   and left out of the bundles; only RadiationRenderer loads them, and RadiationConfigurator binds it only without the
#   flag. They are restored byte for byte afterwards.
# Unity runs through tools/UnityProcess.ps1, and the bundles are rebuilt only when this variant's bundle inputs
# changed since its last verified build (tools/UnityBundleCache.ps1, variant moddable-fluids).
#
# The official builder writes only into Mods/DeepFrontier/version-1.1. The installed (shipped) Deep Frontier package
# and the builder's Managed DeepFrontier*.dll are copied aside first, hashed, and restored byte for byte afterwards
# (also when the build fails); a restore that does not match stops with the backup's location. The flagged package is
# verified and moved to outputs/deep-frontier-moddable-fluids/package/DeepFrontier; it never stays installed.
# tools/start_deep_frontier_moddable_fluids.ps1 installs it for one interactive run.
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
. (Join-Path $PSScriptRoot 'UnityProcess.ps1')
. (Join-Path $PSScriptRoot 'UnityBundleCache.ps1')
$dev = Get-DevEnvironment 'unity', 'timberbornDocuments', 'python'
$project = Join-Path $root 'vendor/timberborn-modding'
$source = Join-Path $root 'src/DeepFrontier'
$staged = Join-Path $project 'Assets/Mods/DeepFrontier'
$mods = Join-Path $dev.timberbornDocuments 'Mods'
$installedRoot = Join-Path $mods 'DeepFrontier'
$managed = Join-Path $dev.timberbornDocuments 'ModsBuild/TimberbornModExamples_Data/Managed'
$output = Join-Path $root 'outputs/deep-frontier-moddable-fluids'
$backup = Join-Path $output 'installed-backup'
$packageRoot = Join-Path $output 'package/DeepFrontier'
$package = Join-Path $packageRoot 'version-1.1'
$log = Join-Path $output 'official-build.log'
$mfPackage = Join-Path $root 'outputs/fluids-api-prototype/packages/ModdableFluids/version-1.1'
$mfDll = Join-Path $mfPackage 'Scripts/ModdableFluids.dll'
$flaggedTypes = @('DeepFrontier.ModdableFluidsMigration.ModdableFluidsBankLayer', 'DeepFrontier.ModdableFluidsMigration.DeepFrontierFluidsModStarter')
# Left out of this package: Moddable Fluids draws the water and the irradiated ground.
$stagedShaders = Join-Path $staged 'AssetBundles/Resources/Shaders/DeepFrontier'
$leftOutShaders = @('RadioactiveWaterURP_Opaque.shadergraph', 'RadioactiveWaterURP_Transparent.shadergraph', 'IrradiatedTerrainURP.shadergraph')
$setAside = Join-Path $backup 'Shaders'
$setAsideTree = [ordered]@{}
$cache = Get-BundleCacheEntry -Root $root -Mod 'DeepFrontier' -Variant 'moddable-fluids'

# ---------------------------------------------------------------- refusals (nothing changed yet)
if (Get-Process Timberborn -ErrorAction SilentlyContinue) { throw 'Close Timberborn first: the build replaces Mods/DeepFrontier for its duration.' }
if (Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object ExecutablePath -eq $dev.unity) { throw 'Close the authoring project in Unity (or wait for another official build) first.' }
if (-not (Test-Path -LiteralPath $dev.unity -PathType Leaf)) { throw "The required Unity editor is missing: $($dev.unity)" }
if (Test-Path -LiteralPath $backup) {
  throw "$backup exists: an earlier flagged build did not finish its restore. Compare it with Mods/DeepFrontier, restore what is needed by hand, then delete it."
}
if (-not (Test-Path -LiteralPath $mfDll -PathType Leaf) -or (Get-Content -LiteralPath (Join-Path $mfPackage 'manifest.json') -Raw | ConvertFrom-Json).Id -ne 'ModdableFluids') {
  throw "The official Moddable Fluids package is missing ($mfPackage); run tools/build_moddable_fluids.ps1 first."
}
$mfVersion = (Get-Content -LiteralPath (Join-Path $mfPackage 'manifest.json') -Raw | ConvertFrom-Json).Version
# build_moddable_fluids.ps1 stages each source folder inside its assembly folder: Scripts/Api/ModdableFluids.asmdef, Scripts/Api/Api/*.cs.
$stagedApi = Join-Path $project 'Assets/Mods/ModdableFluids/Scripts/Api/Api'
$sourceApi = Join-Path $root 'src/ModdableFluids/Api'
function SourceHashes([string]$folder) {
  $hashes = [ordered]@{}
  foreach ($file in Get-ChildItem -LiteralPath $folder -Filter '*.cs' -File | Sort-Object Name) { $hashes[$file.Name] = (Get-FileHash -LiteralPath $file.FullName).Hash }
  $hashes
}
function SameMap($a, $b) { ($a | ConvertTo-Json -Depth 3 -Compress) -eq ($b | ConvertTo-Json -Depth 3 -Compress) }
if (-not (Test-Path -LiteralPath $stagedApi) -or -not (SameMap (SourceHashes $stagedApi) (SourceHashes $sourceApi))) {
  throw "The Unity project's staged Moddable Fluids API ($stagedApi) is not src/ModdableFluids/Api; run tools/build_moddable_fluids.ps1 so the API and its package match the source."
}
if ((Get-FileHash -LiteralPath (Join-Path $managed 'ModdableFluids.dll')).Hash -ne (Get-FileHash -LiteralPath $mfDll).Hash) {
  throw "The builder's ModdableFluids.dll differs from the official package's ($mfDll); rebuild Moddable Fluids with tools/build_moddable_fluids.ps1 first."
}

# Every file under a folder (relative path to SHA-256), for the byte-for-byte restore checks.
function Tree([string]$folder) {
  $hashes = [ordered]@{}
  if (-not (Test-Path -LiteralPath $folder)) { return $hashes }
  $full = (Resolve-Path -LiteralPath $folder).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
  foreach ($file in Get-ChildItem -LiteralPath $folder -File -Recurse -Force | Sort-Object FullName) {
    $hashes[$file.FullName.Substring($full.Length + 1)] = (Get-FileHash -LiteralPath $file.FullName).Hash
  }
  $hashes
}
Add-Type -AssemblyName System.Reflection.Metadata
function AssemblyFacts([string]$path) {
  $stream = [IO.File]::OpenRead($path)
  try {
    $reader = [System.Reflection.Metadata.PEReaderExtensions]::GetMetadataReader([System.Reflection.PortableExecutable.PEReader]::new($stream))
    $references = @(foreach ($handle in $reader.AssemblyReferences) { $r = $reader.GetAssemblyReference($handle); [pscustomobject]@{ Name = $reader.GetString($r.Name); Version = $r.Version } })
    $types = @(foreach ($handle in $reader.TypeDefinitions) { $t = $reader.GetTypeDefinition($handle); $reader.GetString($t.Namespace) + '.' + $reader.GetString($t.Name) })
    [pscustomobject]@{ References = $references; Types = $types }
  } finally { $stream.Dispose() }
}

# ---------------------------------------------------------------- backup
New-Item -ItemType Directory -Force -Path $output | Out-Null
$installedTree = Tree $installedRoot
$installedExisted = Test-Path -LiteralPath $installedRoot
$managedNames = @(Get-ChildItem -LiteralPath $managed -Filter 'DeepFrontier*.dll' -File | Select-Object -ExpandProperty Name)
$managedTree = [ordered]@{}
foreach ($name in $managedNames) { $managedTree[$name] = (Get-FileHash -LiteralPath (Join-Path $managed $name)).Hash }
New-Item -ItemType Directory -Force -Path (Join-Path $backup 'ModsBuild') | Out-Null
if ($installedExisted) {
  Copy-Item -LiteralPath $installedRoot -Destination (Join-Path $backup 'DeepFrontier') -Recurse
  if (-not (SameMap (Tree (Join-Path $backup 'DeepFrontier')) $installedTree)) { throw "The backup of $installedRoot does not match it; nothing was built. Delete $backup and retry." }
}
foreach ($name in $managedNames) { Copy-Item -LiteralPath (Join-Path $managed $name) -Destination (Join-Path $backup "ModsBuild/$name") }
[ordered]@{ installedExisted = $installedExisted; installed = $installedTree; managed = $managedTree } | ConvertTo-Json -Depth 4 |
  Set-Content -LiteralPath (Join-Path $backup 'original.json')
Write-Output "Backed up the installed Deep Frontier package ($($installedTree.Count) files) and $($managedNames.Count) builder DLLs to $backup"

$built = $false
$problems = [Collections.Generic.List[string]]::new()
$report = $null
$buildError = $null
try {
  # ------------------------------------------------------------ flagged staging
  & (Join-Path $PSScriptRoot 'stage_deep_frontier.ps1')
  $stagedFlagged = Join-Path $staged 'Scripts/ModdableFluids'
  New-Item -ItemType Directory -Force -Path $stagedFlagged | Out-Null
  foreach ($file in Get-ChildItem -LiteralPath (Join-Path $source 'ModdableFluids') -Filter '*.cs' -File) { Copy-Item -LiteralPath $file.FullName -Destination $stagedFlagged -Force }
  $asmdef = Get-Content -LiteralPath (Join-Path $source 'Scripts/DeepFrontier.asmdef') -Raw | ConvertFrom-Json
  if ($asmdef.name -ne 'DeepFrontier' -or $asmdef.PSObject.Properties.Name -contains 'references' -or $asmdef.PSObject.Properties.Name -contains 'versionDefines') {
    throw 'src/DeepFrontier/Scripts/DeepFrontier.asmdef changed shape; update the flagged variant in this script.'
  }
  $asmdef | Add-Member -MemberType NoteProperty -Name references -Value @('ModdableFluids')
  $asmdef | Add-Member -MemberType NoteProperty -Name versionDefines -Value @([ordered]@{ name = 'Unity'; expression = '2021.3'; define = 'DEEP_FRONTIER_MODDABLE_FLUIDS' })
  $asmdef | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $staged 'Scripts/DeepFrontier.asmdef') -Encoding utf8NoBOM
  $manifest = Get-Content -LiteralPath (Join-Path $source 'manifest.json') -Raw | ConvertFrom-Json
  if (@($manifest.RequiredMods | Where-Object Id -eq 'ModdableFluids').Count -ne 0) { throw 'src/DeepFrontier/manifest.json already requires ModdableFluids; this test build is for the switch-over.' }
  $manifest.Name = $manifest.Name + ' (Moddable Fluids test build)'
  $manifest.RequiredMods = @($manifest.RequiredMods) + @([pscustomobject]@{ Id = 'ModdableFluids'; MinimumVersion = $mfVersion })
  $manifest.OptionalMods = @($manifest.OptionalMods | Where-Object Id -ne 'ModdableWeathers')
  $manifestVariant = Join-Path $output 'manifest.json'
  $manifest | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $manifestVariant -Encoding utf8NoBOM
  Copy-Item -LiteralPath $manifestVariant -Destination (Join-Path $staged 'manifest.json') -Force
  # Deep Frontier's shader variants with their .meta files (GUIDs), restored byte for byte in the finally block.
  New-Item -ItemType Directory -Force -Path $setAside | Out-Null
  foreach ($name in $leftOutShaders | ForEach-Object { $_, "$_.meta" }) {
    $path = Join-Path $stagedShaders $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
      if ($name.EndsWith('.meta')) { continue }
      throw "$path is not staged; tools/stage_deep_frontier.ps1 stages it from src."
    }
    $hash = (Get-FileHash -LiteralPath $path).Hash
    Move-Item -LiteralPath $path -Destination (Join-Path $setAside $name)
    $setAsideTree[$name] = $hash
  }
  $leftShaders = @(Get-ChildItem -LiteralPath $stagedShaders -Filter '*.shadergraph' -File)
  if ($leftShaders.Count -ne 0) { throw "Deep Frontier shader graphs are still staged for the flagged bundles: $($leftShaders.Name -join ', ')" }
  Write-Output "Staged the flagged variant: Scripts/ModdableFluids, DEEP_FRONTIER_MODDABLE_FLUIDS on the DeepFrontier assembly, manifest requiring ModdableFluids $mfVersion, no Deep Frontier shader variant"
  $inputs = Get-BundleInputs -Project $project -Mod 'DeepFrontier' -Variant 'moddable-fluids' -Unity $dev.unity
  $reuse = Test-BundleCacheHit -Entry $cache -Inputs $inputs

  # ------------------------------------------------------------ official build (as build_deep_frontier.ps1)
  $installedVersion = Join-Path $installedRoot 'version-1.1'
  if (Test-Path -LiteralPath $installedVersion) { Remove-Item -LiteralPath $installedVersion -Recurse -Force }
  $process = Start-UnityProcess -FilePath $dev.unity -Hidden -ArgumentList @(
    '-batchmode', '-nographics', '-quit', '-disable-assembly-updater',
    '-projectPath', ('"' + $project + '"'),
    '-executeMethod', 'Timberborn.ModdingTools.ModBuilding.DeepFrontierBatchBuild.Build',
    '-modBundles', $(if ($reuse) { 'reuse' } else { 'build' }),
    '-logFile', ('"' + $log + '"'))
  $process.WaitForExit()
  if ($process.ExitCode -ne 0) { throw "Official Mod Builder failed ($($process.ExitCode)). See $log" }
  Write-Output 'Shader variant stripping (tools/unity/ModShaderVariantStripping.cs):'
  Get-ShaderStrippingSummary $log
  # The flagged staging is restored only in the finally block: these are the inputs the bundles were built from.
  $builtInputs = Get-BundleInputs -Project $project -Mod 'DeepFrontier' -Variant 'moddable-fluids' -Unity $dev.unity
  if ($reuse) { Assert-BundleInputsUnchanged -Entry $cache -Before $inputs -After $builtInputs }

  # ------------------------------------------------------------ move out and verify
  if (Test-Path -LiteralPath $packageRoot) { Remove-Item -LiteralPath $packageRoot -Recurse -Force }
  New-Item -ItemType Directory -Force -Path $packageRoot | Out-Null
  Move-Item -LiteralPath $installedVersion -Destination $package
  # The bridge for Moddable Weathers, which this manifest no longer lists (Moddable Fluids refuses it with tides).
  $bridge = Join-Path $package 'Scripts/DeepFrontier.ModdableWeathers.dll.ModdableWeathers.optional'
  if (Test-Path -LiteralPath $bridge) { Remove-Item -LiteralPath $bridge }
  $packagedManifest = Get-Content -LiteralPath (Join-Path $package 'manifest.json') -Raw | ConvertFrom-Json
  if ((Get-FileHash -LiteralPath (Join-Path $package 'manifest.json')).Hash -ne (Get-FileHash -LiteralPath $manifestVariant).Hash) { throw 'The packaged manifest is not the staged variant.' }
  if ($packagedManifest.Id -ne 'DeepFrontier' -or @($packagedManifest.RequiredMods | Where-Object { $_.Id -eq 'ModdableFluids' -and $_.MinimumVersion -eq $mfVersion }).Count -ne 1 -or
      @($packagedManifest.OptionalMods | Where-Object Id -eq 'ModdableWeathers').Count -ne 0) { throw 'The packaged manifest must require ModdableFluids and leave out ModdableWeathers.' }
  $scripts = Join-Path $package 'Scripts'
  $embedded = @(Get-ChildItem -LiteralPath $scripts -File | Where-Object { $_.Name -like 'ModdableFluids*' -or $_.Name -like '*.ModdableWeathers.*' })
  if ($embedded.Count -ne 0) { throw "The package must not carry Moddable Fluids or the Moddable Weathers bridge: $($embedded.Name -join ', ')" }
  $dll = Join-Path $scripts 'DeepFrontier.dll'
  if ((Get-FileHash -LiteralPath $dll).Hash -ne (Get-FileHash -LiteralPath (Join-Path $managed 'DeepFrontier.dll')).Hash) { throw 'The packaged DeepFrontier.dll is not the official build output.' }
  $facts = AssemblyFacts $dll
  $apiName = [Reflection.AssemblyName]::GetAssemblyName($mfDll)
  $apiReference = @($facts.References | Where-Object Name -eq 'ModdableFluids')
  if ($apiReference.Count -ne 1 -or $apiReference[0].Version -ne $apiName.Version) { throw "DeepFrontier.dll must reference ModdableFluids $($apiName.Version) (the official package)." }
  $missing = @($flaggedTypes | Where-Object { $facts.Types -notcontains $_ })
  if ($missing.Count -ne 0) { throw "DeepFrontier.dll was not compiled with DEEP_FRONTIER_MODDABLE_FLUIDS (missing $($missing -join ', '))." }
  if ((Get-FileHash -LiteralPath (Join-Path $managed 'ModdableFluids.dll')).Hash -ne (Get-FileHash -LiteralPath $mfDll).Hash) {
    throw 'The build compiled a ModdableFluids.dll that differs from the official package; the test package would not match the API it is installed with.'
  }
  if ($reuse) { Install-CachedBundles -Entry $cache -Destination (Join-Path $package 'AssetBundles') }
  foreach ($platform in 'win', 'mac') {
    $bundle = Join-Path $package "AssetBundles/deepfrontier_$platform"
    if (-not (Test-Path -LiteralPath $bundle -PathType Leaf) -or (Get-Item -LiteralPath $bundle).Length -eq 0) { throw "The package has no $platform asset bundle." }
  }
  # The bundles hold no shader of Deep Frontier's (or Moddable Fluids'): Moddable Fluids draws the water and the irradiated ground.
  & $dev.python (Join-Path $root 'tools/asset-pipeline/check_bundle_shaders.py') --win (Join-Path $package 'AssetBundles/deepfrontier_win') `
    --mac (Join-Path $package 'AssetBundles/deepfrontier_mac') --expect
  if ($LASTEXITCODE -ne 0) { throw 'The flagged bundles must hold no Deep Frontier shader variant (tools/asset-pipeline/check_bundle_shaders.py).' }
  $data = Join-Path $source 'Data'
  $dataFull = (Resolve-Path -LiteralPath $data).Path.TrimEnd([IO.Path]::DirectorySeparatorChar)
  $dataFiles = 0
  foreach ($file in Get-ChildItem -LiteralPath $data -File -Recurse | Where-Object Extension -ne '.meta') {
    $relative = $file.FullName.Substring($dataFull.Length + 1)
    $packed = Join-Path $package $relative
    if (-not (Test-Path -LiteralPath $packed -PathType Leaf) -or (Get-FileHash -LiteralPath $packed).Hash -ne (Get-FileHash -LiteralPath $file.FullName).Hash) { throw "Packaged data differs from src: $relative" }
    $dataFiles++
  }
  $thumbnail = Join-Path (Join-Path $backup 'DeepFrontier') 'thumbnail.png'
  if (Test-Path -LiteralPath $thumbnail) { Copy-Item -LiteralPath $thumbnail -Destination $packageRoot }
  # Verified: a fresh build's bundles are cached for this variant; the package's bundles are the cached ones either way.
  if (-not $reuse) { Save-BundleCache -Entry $cache -Inputs $builtInputs -Source (Join-Path $package 'AssetBundles') }
  $bundleRecord = Assert-BundlesMatchCache -Entry $cache -Directory (Join-Path $package 'AssetBundles') -Inputs $builtInputs
  $report = [ordered]@{
    status = 'passed'; builtAt = (Get-Date -Format o); package = $packageRoot; manifest = $packagedManifest
    deepFrontierDll = (Get-FileHash -LiteralPath $dll).Hash; moddableFluidsDll = (Get-FileHash -LiteralPath $mfDll).Hash; moddableFluidsVersion = $mfVersion
    referencesModdableFluids = "$($apiReference[0].Version)"; flaggedTypes = $flaggedTypes; dataFiles = $dataFiles
    scripts = @(Get-ChildItem -LiteralPath $scripts -File | ForEach-Object { [ordered]@{ name = $_.Name; sha256 = (Get-FileHash -LiteralPath $_.FullName).Hash } })
    bundles = [ordered]@{ reused = [bool]$reuse; fingerprint = $bundleRecord.fingerprint; cache = $cache; files = $bundleRecord.bundles; leftOut = $leftOutShaders }
  }
  $built = $true
} catch {
  $buildError = $_
  throw
} finally {
  # 1. Nothing of the flagged build stays in Mods: its version folder was moved out, or is removed here.
  try {
    $leftover = Join-Path $installedRoot 'version-1.1'
    if (Test-Path -LiteralPath $installedRoot) { Remove-Item -LiteralPath $installedRoot -Recurse -Force }
    if (Test-Path -LiteralPath $leftover) { throw "$leftover could not be removed." }
  } catch { $problems.Add("Removing the build from Mods: $($_.Exception.Message)") }
  # 2. The installed package, byte for byte.
  try {
    if ($installedExisted) {
      Copy-Item -LiteralPath (Join-Path $backup 'DeepFrontier') -Destination $installedRoot -Recurse
      if (-not (SameMap (Tree $installedRoot) $installedTree)) { throw "the restored files differ from the originals" }
    }
  } catch { $problems.Add("Restoring $installedRoot from $backup/DeepFrontier: $($_.Exception.Message)") }
  # 3. The builder's Managed DeepFrontier DLLs (verify_deep_frontier_package.ps1 compares them with the installed package).
  try {
    foreach ($file in Get-ChildItem -LiteralPath $managed -Filter 'DeepFrontier*.dll' -File) {
      if (-not $managedTree.Contains($file.Name)) { Remove-Item -LiteralPath $file.FullName }
    }
    foreach ($name in $managedNames) {
      Copy-Item -LiteralPath (Join-Path $backup "ModsBuild/$name") -Destination (Join-Path $managed $name) -Force
      if ((Get-FileHash -LiteralPath (Join-Path $managed $name)).Hash -ne $managedTree[$name]) { throw "$name differs after the restore" }
    }
  } catch { $problems.Add("Restoring the builder's Managed DLLs from $backup/ModsBuild: $($_.Exception.Message)") }
  # 4. Deep Frontier's shader variants with their original .meta files (GUIDs), so the default bundles' inputs are what
  #    they were.
  try {
    foreach ($name in $setAsideTree.Keys) {
      Move-Item -LiteralPath (Join-Path $setAside $name) -Destination (Join-Path $stagedShaders $name) -Force
      if ((Get-FileHash -LiteralPath (Join-Path $stagedShaders $name)).Hash -ne $setAsideTree[$name]) { throw "$name differs after the restore" }
    }
  } catch { $problems.Add("Restoring Deep Frontier's shader variants from $setAside into $($stagedShaders): $($_.Exception.Message)") }
  # 5. The default staging, so the next default build starts from src as always.
  try {
    & (Join-Path $PSScriptRoot 'stage_deep_frontier.ps1') | Out-Null
    if (Test-Path -LiteralPath (Join-Path $staged 'Scripts/ModdableFluids')) { throw 'Scripts/ModdableFluids is still staged' }
    foreach ($pair in @(@('Scripts/DeepFrontier.asmdef', 'Scripts/DeepFrontier.asmdef'), @('manifest.json', 'manifest.json'))) {
      if ((Get-FileHash -LiteralPath (Join-Path $staged $pair[0])).Hash -ne (Get-FileHash -LiteralPath (Join-Path $source $pair[1])).Hash) { throw "staged $($pair[0]) is not the source" }
    }
    foreach ($name in $setAsideTree.Keys) {
      if ((Get-FileHash -LiteralPath (Join-Path $stagedShaders $name)).Hash -ne $setAsideTree[$name]) { throw "staged $name is not the original" }
    }
  } catch { $problems.Add("Restoring the default staging (rerun tools/stage_deep_frontier.ps1): $($_.Exception.Message)") }
  if ($problems.Count -ne 0) {
    throw "The flagged build's restore FAILED; the backup stays at $backup.`n  " + ($problems -join "`n  ") + $(if ($buildError) { "`nThe build itself failed first: $($buildError.Exception.Message)" } else { '' })
  }
  Remove-Item -LiteralPath $backup -Recurse -Force
  Write-Output "Restored the installed Deep Frontier package and the builder's DLLs byte for byte; default staging restored."
}
if ($built) {
  $report | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $output 'package-report.json')
  Write-Output "Flagged Deep Frontier test package verified and kept out of Mods at $packageRoot. Log: $log"
}
