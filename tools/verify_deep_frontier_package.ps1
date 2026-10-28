param([Parameter(Mandatory=$true)][int]$Build)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
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
& $dev.python (Join-Path $root 'tools\asset-pipeline\validate_goodmesh_exports.py') --data $data --bundle (Join-Path $installed 'AssetBundles\deepfrontier_win')
if ($LASTEXITCODE -ne 0) { throw 'A GoodVisualization mesh is not a Mesh in the installed bundle.' }
$report = [pscustomobject]@{ build=$Build; checkedAt=(Get-Date -Format o); status='all-authored-files-match-installed-package'; count=$checked.Count; files=$checked }
$report | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $root "outputs\restaurant-package-verification$Build.json") -Encoding utf8
Write-Output "Build ${Build}: $($checked.Count) authored data/manifest/DLL hashes match the official installed package."
