param([Parameter(Mandatory=$true)][int]$Build)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
. (Join-Path $PSScriptRoot 'UnityBundleCache.ps1')
$dev = Get-DevEnvironment 'python'
$data = Join-Path $root 'src\DeepFrontier\Data'
$installed = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\Mods\DeepFrontier\version-1.1'
$checked = [Collections.Generic.List[object]]::new()
function Compare-Artifact([string]$Source,[string]$Target,[string]$Label) {
  $sourceHash = (Get-FileHash -LiteralPath $Source -Algorithm SHA256).Hash
  $targetHash = (Get-FileHash -LiteralPath $Target -Algorithm SHA256).Hash
  if ($sourceHash -ne $targetHash) { throw "Installed artifact differs: $Label" }
  $checked.Add([pscustomobject]@{ file=$Label; sha256=$sourceHash })
}
foreach ($file in Get-ChildItem -LiteralPath $data -File -Recurse | Where-Object Extension -ne '.meta') {
  $relative = [IO.Path]::GetRelativePath($data,$file.FullName)
  Compare-Artifact $file.FullName (Join-Path $installed $relative) $relative
}
Compare-Artifact (Join-Path $root 'src\DeepFrontier\manifest.json') (Join-Path $installed 'manifest.json') 'manifest.json'
# Match DllFilesCopier's final player-build artifact, not Unity's transient Bee cache.
$officialDll = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ModsBuild\TimberbornModExamples_Data\Managed\DeepFrontier.dll'
Compare-Artifact $officialDll (Join-Path $installed 'Scripts\DeepFrontier.dll') 'Scripts\DeepFrontier.dll'
# The Moddable Weathers bridge ships only in Moddable Timberborn's optional form
# (tools/unity/DeepFrontierBatchBuild.cs PackageOptionalAssembly); a plain .dll
# would break loading whenever Moddable Weathers is absent.
$bridgeDll = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ModsBuild\TimberbornModExamples_Data\Managed\DeepFrontier.ModdableWeathers.dll'
Compare-Artifact $bridgeDll (Join-Path $installed 'Scripts\DeepFrontier.ModdableWeathers.dll.ModdableWeathers.optional') 'Scripts\DeepFrontier.ModdableWeathers.dll.ModdableWeathers.optional'
if (Test-Path -LiteralPath (Join-Path $installed 'Scripts\DeepFrontier.ModdableWeathers.dll')) { throw 'The Moddable Weathers bridge must not be installed as a plain DLL.' }
# The Sluice is Back! bridge likewise (Scripts/SluiceIsBack): optional form only.
$sluiceDll = Join-Path ([Environment]::GetFolderPath('MyDocuments')) 'Timberborn\ModsBuild\TimberbornModExamples_Data\Managed\DeepFrontier.SluiceIsBack.dll'
Compare-Artifact $sluiceDll (Join-Path $installed 'Scripts\DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional') 'Scripts\DeepFrontier.SluiceIsBack.dll.SluiceIsBack.optional'
if (Test-Path -LiteralPath (Join-Path $installed 'Scripts\DeepFrontier.SluiceIsBack.dll')) { throw 'The Sluice is Back! bridge must not be installed as a plain DLL.' }
# Nothing else is installed: authored data (with the builder's .meta.json beside imported
# assets), the manifest, Scripts and AssetBundles. Extra files are leftovers of older builds.
$authored = [Collections.Generic.HashSet[string]]::new([StringComparer]::OrdinalIgnoreCase)
foreach ($file in Get-ChildItem -LiteralPath $data -File -Recurse) { $null = $authored.Add([IO.Path]::GetRelativePath($data,$file.FullName)) }
$stale = @(Get-ChildItem -LiteralPath $installed -File -Recurse | ForEach-Object { [IO.Path]::GetRelativePath($installed,$_.FullName) } | Where-Object {
  $_ -ne 'manifest.json' -and -not $_.StartsWith('Scripts\') -and -not $_.StartsWith('AssetBundles\') -and
  -not $authored.Contains($_) -and -not ($_.EndsWith('.meta.json') -and $authored.Contains($_.Substring(0, $_.Length - 10)))
})
if ($stale.Count) { throw "Installed files not in the authored package (left from older builds): $($stale -join ', ')" }
foreach($dependency in @('TimberUi.dll','0Harmony.dll','ModdableRecipes.dll','ConveyorBelt.dll','ConveyorBelt.Algorithm.dll','ModdableTimberborn.dll','ModSettings.Core.dll','ModSettings.Common.dll','TimberPipes.dll','PowerLines.dll','ModdableWeathers.dll','SluiceIsBack.dll')) {
  if (Test-Path -LiteralPath (Join-Path $installed "Scripts\$dependency")) { throw 'Dependency DLLs must remain in their own mod packages.' }
}
# Every GoodVisualization mesh (AssetRef<Mesh>) must be a Mesh in the built bundle;
# build 167 shipped the pile meshes as BinaryData GameObjects and every load failed.
# Both platform bundles ship: the game loads deepfrontier_win on Windows and deepfrontier_mac
# on macOS, and a missing one fails every bundled asset there.
$bundles = [Collections.Generic.List[object]]::new()
foreach ($platform in 'win', 'mac') {
  $bundle = Join-Path $installed "AssetBundles\deepfrontier_$platform"
  if (-not (Test-Path -LiteralPath $bundle -PathType Leaf)) { throw "The installed package has no $platform asset bundle ($bundle)." }
  & $dev.python (Join-Path $root 'tools\asset-pipeline\validate_goodmesh_exports.py') --data $data --bundle $bundle --platform $platform
  if ($LASTEXITCODE -ne 0) { throw "The installed $platform bundle failed platform, material or stockpile-mesh validation." }
  $bundles.Add([pscustomobject]@{ platform=$platform; bytes=(Get-Item -LiteralPath $bundle).Length; sha256=(Get-FileHash -LiteralPath $bundle -Algorithm SHA256).Hash })
}
# Exactly the shader variants the game draws (tools/unity/ModShaderVariantStripping.cs, docs/unity-build-performance.md).
& $dev.python (Join-Path $root 'tools\asset-pipeline\check_bundle_shaders.py') --win (Join-Path $installed 'AssetBundles\deepfrontier_win') --mac (Join-Path $installed 'AssetBundles\deepfrontier_mac') `
  --expect 'DeepFrontier/IrradiatedTerrainURP' 'DeepFrontier/RadioactiveWaterURP_Opaque' 'DeepFrontier/RadioactiveWaterURP_Transparent'
if ($LASTEXITCODE -ne 0) { throw 'The installed bundles do not hold exactly the shader variants the game can draw.' }
# The installed AssetBundles folder is byte for byte the one the last verified build cached with its inputs'
# fingerprint (tools/UnityBundleCache.ps1): built then, or reused by a code-only build since.
$bundleRecord = Assert-BundlesMatchCache -Entry (Get-BundleCacheEntry -Root $root -Mod 'DeepFrontier' -Variant 'default') -Directory (Join-Path $installed 'AssetBundles')
$report = [pscustomobject]@{ bundles=$bundles; bundleFingerprint=$bundleRecord.fingerprint; bundlesBuiltAt=$bundleRecord.storedAt; build=$Build; checkedAt=(Get-Date -Format o); status='all-authored-files-match-installed-package'; count=$checked.Count; files=$checked }
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $root "outputs\restaurant-package-verification$Build.json") -Encoding utf8
Write-Output "Build ${Build}: $($checked.Count) authored data/manifest/DLL hashes match the official installed package."
