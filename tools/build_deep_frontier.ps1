# -ModdableFluids: a disposable test package with DEEP_FRONTIER_MODDABLE_FLUIDS, kept out of Mods
# (tools/build_deep_frontier_moddable_fluids.ps1). Without it this script is the default build.
# Unity runs through tools/UnityProcess.ps1 (below-normal priority, two logical processors left free). The asset
# bundles are built only when their inputs changed since the last verified build; otherwise that build's bundles
# are installed and Unity builds the code alone (tools/UnityBundleCache.ps1, docs/unity-build-performance.md).
param([switch]$ModdableFluids)
$ErrorActionPreference = 'Stop'
if ($ModdableFluids) {
  . (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
  & (Get-DevEnvironment 'pwsh').pwsh -NoProfile -File (Join-Path $PSScriptRoot 'build_deep_frontier_moddable_fluids.ps1')
  if ($LASTEXITCODE -ne 0) { throw "The flagged Deep Frontier test build failed ($LASTEXITCODE)." }
  return
}
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$project = Join-Path $root 'vendor\timberborn-modding'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
. (Join-Path $PSScriptRoot 'UnityProcess.ps1')
. (Join-Path $PSScriptRoot 'UnityBundleCache.ps1')
$dev = Get-DevEnvironment 'unity', 'python', 'timberbornDocuments'
$unity = $dev.unity
$log = Join-Path $root 'outputs\unity_official_build.log'

if (Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object ExecutablePath -eq $unity) {
  throw 'Close the authoring project in Unity before running the batch build.'
}
if (-not (Test-Path -LiteralPath $unity -PathType Leaf)) {
  throw "The required Unity editor is missing: $unity"
}
& (Join-Path $PSScriptRoot 'stage_deep_frontier.ps1')
$cache = Get-BundleCacheEntry -Root $root -Mod 'DeepFrontier' -Variant 'default'
$inputs = Get-BundleInputs -Project $project -Mod 'DeepFrontier' -Variant 'default' -Unity $unity
$reuse = Test-BundleCacheHit -Entry $cache -Inputs $inputs
# The official Mod Builder adds and overwrites installed files but never removes one, so a
# blueprint, recipe or sprite deleted from src stayed installed (and uploaded) from older
# builds. Start from an empty version folder; workshop_data.json and the thumbnail sit one
# level up and stay. A running game holding the DLL makes this fail before Unity starts.
$installed = Join-Path $dev.timberbornDocuments 'Mods\DeepFrontier\version-1.1'
if (Test-Path -LiteralPath $installed) { Remove-Item -LiteralPath $installed -Recurse -Force }
$process = Start-UnityProcess -FilePath $unity -Hidden -ArgumentList @(
  '-batchmode', '-nographics', '-quit',
  # No names: Unity skips its API updater for every assembly. The game's and the mods' DLLs are built for this editor,
  # and on a new project the single-threaded updater otherwise spends over 30 minutes on the 518 game assemblies.
  '-disable-assembly-updater',
  '-projectPath', ('"' + $project + '"'),
  '-executeMethod', 'Timberborn.ModdingTools.ModBuilding.DeepFrontierBatchBuild.Build',
  '-modBundles', $(if ($reuse) { 'reuse' } else { 'build' }),
  '-logFile', ('"' + $log + '"')
)
# Wait for the editor's result. Its shared Roslyn compiler can remain alive
# after a failed compile; waiting for the entire process tree never completes.
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "Official Mod Builder failed ($($process.ExitCode)). See $log" }
Write-Output 'Shader variant stripping (tools/unity/ModShaderVariantStripping.cs):'
Get-ShaderStrippingSummary $log
$bundles = Join-Path $installed 'AssetBundles'
if ($reuse) {
  Assert-BundleInputsUnchanged -Entry $cache -Before $inputs -After (Get-BundleInputs -Project $project -Mod 'DeepFrontier' -Variant 'default' -Unity $unity)
  Install-CachedBundles -Entry $cache -Destination $bundles
  Write-Output "Installed the cached asset bundles of the last verified build ($cache)."
} else {
  # The bundle checks of tools/verify_deep_frontier_package.ps1, before the bundles are cached.
  foreach ($platform in 'win', 'mac') {
    & $dev.python (Join-Path $root 'tools\asset-pipeline\validate_goodmesh_exports.py') --data (Join-Path $root 'src\DeepFrontier\Data') --bundle (Join-Path $bundles "deepfrontier_$platform") --platform $platform
    if ($LASTEXITCODE -ne 0) { throw "The built $platform bundle failed platform, material or stockpile-mesh validation." }
  }
  & $dev.python (Join-Path $root 'tools\asset-pipeline\check_bundle_shaders.py') --win (Join-Path $bundles 'deepfrontier_win') --mac (Join-Path $bundles 'deepfrontier_mac') `
    --expect 'DeepFrontier/IrradiatedTerrainURP' 'DeepFrontier/RadioactiveWaterURP_Opaque' 'DeepFrontier/RadioactiveWaterURP_Transparent'
  if ($LASTEXITCODE -ne 0) { throw 'The built bundles do not hold exactly the shader variants the game can draw (tools/asset-pipeline/check_bundle_shaders.py).' }
  Save-BundleCache -Entry $cache -Inputs (Get-BundleInputs -Project $project -Mod 'DeepFrontier' -Variant 'default' -Unity $unity) -Source $bundles
}
Write-Output "Official Mod Builder finished. Log: $log"
