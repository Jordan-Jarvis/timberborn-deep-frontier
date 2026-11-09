# Static checks of the Unity build tooling (docs/unity-build-performance.md), without running Unity:
#   - tools/unity/*.cs (batch builds and ModShaderVariantStripping) compile with the official Mod Builder sources
#     against this machine's Unity editor assemblies (tools/compile-check/unity-build-tools);
#   - the build scripts parse;
#   - tools/UnityProcess.ps1 starts a harmless process tree (cmd.exe starting ping.exe at once): parent and child run
#     at below-normal priority on the reduced affinity mask, and the exit code comes back;
#   - tools/UnityBundleCache.ps1 on a temporary project: fingerprint stability and change detection, store, reuse,
#     install, corruption and stale-input refusals, and the stripping summary of a Unity log.
# Run with PowerShell 7 (validate_all check unity-build-tools); it repeats the process, parse and cache checks in
# Windows PowerShell 5.1, which runs tools/build_deep_frontier.ps1.
param([switch]$Nested)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
. (Join-Path $PSScriptRoot 'UnityProcess.ps1')
. (Join-Path $PSScriptRoot 'UnityBundleCache.ps1')
$shell = "PowerShell $($PSVersionTable.PSVersion)"
function Assert-True([bool]$Condition, [string]$Message) { if (-not $Condition) { throw "$shell`: $Message" } }
function Assert-Throws([scriptblock]$Block, [string]$Pattern, [string]$Message) {
  $thrown = $null
  try { & $Block } catch { $thrown = $_.Exception.Message }
  Assert-True ($null -ne $thrown -and $thrown -match $Pattern) "$Message (got: $thrown)"
}

if (-not $Nested) {
  if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'Run tools/test_unity_build_tools.ps1 with PowerShell 7.' }
  $unity = (Get-DevEnvironment 'unity').unity
  $editorData = Join-Path (Split-Path -Parent $unity) 'Data'
  & dotnet build (Join-Path $PSScriptRoot 'compile-check/unity-build-tools/UnityBuildTools.csproj') --nologo -v q "-p:UnityEditorData=$editorData"
  if ($LASTEXITCODE -ne 0) { throw 'tools/unity/*.cs do not compile against the Unity editor assemblies.' }
  Write-Output 'Compile: tools/unity/*.cs with the official Mod Builder sources against the Unity editor assemblies.'
}

# Parse: every script that dot-sources or runs these helpers.
$scripts = @('UnityProcess.ps1', 'UnityBundleCache.ps1', 'run_unity.ps1', 'build_deep_frontier.ps1', 'stage_deep_frontier.ps1',
  'build_moddable_fluids.ps1', 'open_deep_frontier_builder.ps1', 'test_unity_build_tools.ps1')
if (-not $Nested) { $scripts += @('build_deep_frontier_moddable_fluids.ps1', 'verify_deep_frontier_package.ps1', 'verify_moddable_fluids_package.ps1') }
foreach ($name in $scripts) {
  $tokens = $null; $errors = $null
  [void][Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $name), [ref]$tokens, [ref]$errors)
  Assert-True ($errors.Count -eq 0) "$name does not parse: $($errors | Select-Object -First 1)"
}
Write-Output "$shell parses $($scripts.Count) scripts."

# Process tree: the child starts at once, so it shows what the editor's first children inherit.
$mask = Get-UnityAffinityMask
$cmd = Join-Path $env:SystemRoot 'System32\cmd.exe'
$parent = Start-UnityProcess -FilePath $cmd -ArgumentList @('/d', '/c', '"ping -n 4 127.0.0.1 >nul & exit 7"') -Hidden
$child = $null
$deadline = (Get-Date).AddSeconds(10)
while ($null -eq $child -and (Get-Date) -lt $deadline) {
  $child = Get-CimInstance Win32_Process -Filter "ParentProcessId=$($parent.Id) AND Name='PING.EXE'"
  if ($null -eq $child) { Start-Sleep -Milliseconds 50 }
}
Assert-True ($null -ne $child) 'cmd.exe started no ping.exe'
$childProcess = Get-Process -Id $child.ProcessId
foreach ($process in @($parent, $childProcess)) {
  Assert-True ($process.PriorityClass -eq [Diagnostics.ProcessPriorityClass]::BelowNormal) "$($process.ProcessName) runs at $($process.PriorityClass)"
  Assert-True ([UInt64]$process.ProcessorAffinity.ToInt64() -eq $mask) ("{0} has affinity 0x{1:X}, expected 0x{2:X}" -f $process.ProcessName, $process.ProcessorAffinity.ToInt64(), $mask)
}
$parent.WaitForExit()
Assert-True ($parent.ExitCode -eq 7) "the exit code came back as $($parent.ExitCode)"
Write-Output ("{0}: cmd.exe and its ping.exe ran at BelowNormal on affinity 0x{1:X} of 0x{2:X}; exit code 7 returned." -f $shell, $mask, [Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity.ToInt64())

# Bundle cache on a temporary project and outputs folder.
$temp = Join-Path ([IO.Path]::GetTempPath()) ('unity-build-tools-' + [Guid]::NewGuid().ToString('N'))
try {
  $project = Join-Path $temp 'project'
  function Write-TestFile([string]$Relative, [string]$Text) {
    $path = Join-Path $project $Relative
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path) | Out-Null
    [IO.File]::WriteAllText($path, $Text)
  }
  Write-TestFile 'Assets/Mods/TestMod/AssetBundles/Resources/Shaders/Water.shadergraph' 'graph'
  Write-TestFile 'Assets/Mods/TestMod/AssetBundles/Resources/Shaders/Water.shadergraph.meta' 'guid: 1'
  Write-TestFile 'Assets/Mods/TestMod/AssetBundles.meta' 'guid: 0'
  Write-TestFile 'Assets/Mods/TestMod/Scripts/Code.cs' 'code'
  Write-TestFile 'Assets/Tools/Editor/Scripts/ModBuilding/ModShaderVariantStripping.cs' 'strip'
  Write-TestFile 'ProjectSettings/GraphicsSettings.asset' 'graphics'
  Write-TestFile 'Packages/packages-lock.json' '{}'
  # A stand-in editor folder: an executable with version information, and Windows and macOS build support.
  $editor = Join-Path $temp 'Unity/Editor'
  New-Item -ItemType Directory -Force -Path $editor | Out-Null
  $fakeUnity = Join-Path $editor 'Unity.exe'
  Copy-Item -LiteralPath $cmd -Destination $fakeUnity
  foreach ($relative in 'windowsstandalonesupport/UnityEditor.WindowsStandalone.Extensions.dll', 'windowsstandalonesupport/modules.asset',
      'MacStandaloneSupport/UnityEditor.OSXStandalone.Extensions.dll', 'MacStandaloneSupport/modules.asset') {
    $path = Join-Path $editor "Data/PlaybackEngines/$relative"
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $path) | Out-Null
    [IO.File]::WriteAllText($path, $relative)
  }
  $first = Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity
  $again = Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity
  Assert-True ($first.fingerprint -eq $again.fingerprint) 'the fingerprint of unchanged inputs changed'
  Assert-True ($first.files.Count -eq 10) "expected 10 bundle inputs (scripts excluded), got $($first.files.Count): $(@($first.files.Keys) -join ', ')"
  Assert-True ((Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'moddable-fluids' -Unity $fakeUnity).fingerprint -ne $first.fingerprint) 'variants share a fingerprint'
  Write-TestFile 'Assets/Mods/TestMod/Scripts/Code.cs' 'other code'
  Assert-True ((Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity).fingerprint -eq $first.fingerprint) 'a script change changed the bundle fingerprint'
  Write-TestFile 'Assets/Mods/TestMod/AssetBundles/Resources/Shaders/Water.shadergraph.meta' 'guid: 2'
  $metaChanged = Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity
  Assert-True ($metaChanged.fingerprint -ne $first.fingerprint) 'a .meta change kept the fingerprint'
  Assert-True (@(Get-BundleInputChanges $first $metaChanged) -contains 'changed Assets/Mods/TestMod/AssetBundles/Resources/Shaders/Water.shadergraph.meta') 'the .meta change is not listed'
  Write-TestFile 'Assets/Mods/TestMod/AssetBundles/Resources/Shaders/Water.shadergraph.meta' 'guid: 1'
  Write-TestFile 'ProjectSettings/GraphicsSettings.asset' 'graphics changed'
  Assert-True ((Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity).fingerprint -ne $first.fingerprint) 'a graphics settings change kept the fingerprint'
  Write-TestFile 'ProjectSettings/GraphicsSettings.asset' 'graphics'
  $macSupport = Join-Path $editor 'Data/PlaybackEngines/MacStandaloneSupport/UnityEditor.OSXStandalone.Extensions.dll'
  [IO.File]::WriteAllText($macSupport, 'updated macOS build support')
  Assert-True ((Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity).fingerprint -ne $first.fingerprint) 'a macOS build support change kept the fingerprint'
  Remove-Item -LiteralPath $macSupport
  Assert-Throws { Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity } 'macOS build support' 'missing macOS build support was not refused'
  [IO.File]::WriteAllText($macSupport, 'MacStandaloneSupport/UnityEditor.OSXStandalone.Extensions.dll')
  Assert-True ((Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity).fingerprint -eq $first.fingerprint) 'restoring the inputs did not restore the fingerprint'
  # PlayerBuildShaderStripping acts only in the throwaway player build: not a bundle input.
  Write-TestFile 'Assets/Tools/Editor/Scripts/ModBuilding/PlayerBuildShaderStripping.cs' 'player build'
  Write-TestFile 'Assets/Tools/Editor/Scripts/ModBuilding/PlayerBuildShaderStripping.cs.meta' 'guid: 3'
  $withPlayer = Get-BundleInputs -Project $project -Mod 'TestMod' -Variant 'default' -Unity $fakeUnity
  Assert-True ($withPlayer.fingerprint -eq $first.fingerprint -and $withPlayer.files.Count -eq $first.files.Count) 'PlayerBuildShaderStripping.cs changed the bundle fingerprint'

  $entry = Get-BundleCacheEntry -Root $temp -Mod 'TestMod' -Variant 'default'
  Assert-True (-not (Test-BundleCacheHit -Entry $entry -Inputs $first 6>$null)) 'an empty cache reported a hit'
  $built = Join-Path $temp 'package/AssetBundles'
  New-Item -ItemType Directory -Force -Path $built | Out-Null
  foreach ($name in 'testmod_win', 'testmod_win.manifest', 'testmod_mac', 'testmod_mac.manifest') { [IO.File]::WriteAllText((Join-Path $built $name), "bundle $name") }
  Save-BundleCache -Entry $entry -Inputs $first -Source $built 6>$null
  Assert-True (Test-BundleCacheHit -Entry $entry -Inputs $first 6>$null) 'the stored build is not reused'
  Assert-True (-not (Test-BundleCacheHit -Entry $entry -Inputs $metaChanged 6>$null)) 'changed inputs reused the stored bundles'
  $installedBundles = Join-Path $temp 'installed/AssetBundles'
  Install-CachedBundles -Entry $entry -Destination $installedBundles
  $record = Assert-BundlesMatchCache -Entry $entry -Directory $installedBundles -Inputs $first
  Assert-True ($record.fingerprint -eq $first.fingerprint -and $record.files.Count -eq $first.files.Count) 'the record does not hold the stored inputs'
  Assert-Throws { Install-CachedBundles -Entry $entry -Destination $installedBundles } 'exists' 'installing over existing bundles was not refused'
  Assert-Throws { Assert-BundlesMatchCache -Entry $entry -Directory $installedBundles -Inputs $metaChanged } 'inputs changed' 'stale inputs passed verification'
  [IO.File]::WriteAllText((Join-Path $installedBundles 'testmod_win'), 'other bytes')
  Assert-Throws { Assert-BundlesMatchCache -Entry $entry -Directory $installedBundles } 'is not the cached bundle' 'a different installed bundle passed verification'
  [IO.File]::WriteAllText((Join-Path $installedBundles 'extra'), 'x')
  Assert-Throws { Assert-BundlesMatchCache -Entry $entry -Directory $installedBundles } 'holds' 'an extra installed file passed verification'
  [IO.File]::WriteAllText((Join-Path $entry 'AssetBundles/testmod_mac'), 'corrupt')
  Assert-Throws { Test-BundleCacheHit -Entry $entry -Inputs $first 6>$null } 'differs from its record' 'a corrupt cache was reused'
  Save-BundleCache -Entry $entry -Inputs $first -Source $built 6>$null
  Assert-Throws { Assert-BundleInputsUnchanged -Entry $entry -Before $first -After $metaChanged } 'changed bundle inputs' 'changed inputs during a reuse build passed'
  Assert-True (-not (Test-Path -LiteralPath $entry)) 'the stale cache entry was kept'
  Assert-BundleInputsUnchanged -Entry $entry -Before $first -After $again

  $log = Join-Path $temp 'unity.log'
  [IO.File]::WriteAllLines($log, [string[]]@(
    '[ModShaderVariantStripping] DeepFrontier/IrradiatedTerrainURP | ForwardLit (UniversalForward) | Fragment | D3D: 256 -> 192',
    '[ModShaderVariantStripping] DeepFrontier/IrradiatedTerrainURP | ForwardLit (UniversalForward) | Fragment | D3D: 256 -> 192',
    '[ModShaderVariantStripping] DeepFrontier/IrradiatedTerrainURP | Universal 2D (Universal2D) | Vertex | D3D: 16 -> 0 (pass drawn only by the 2D renderer)',
    '[ModShaderVariantStripping] DeepFrontier/IrradiatedTerrainURP | ForwardLit (UniversalForward) | Fragment | Metal: 256 -> 192',
    '[PlayerBuildShaderStripping] player build: stripped 1136 variants of mod shaders (3: a, b, c)',
    'unrelated line'))
  $summary = @(Get-ShaderStrippingSummary $log)
  Assert-True ($summary.Count -eq 3 -and $summary[0] -eq '  DeepFrontier/IrradiatedTerrainURP (D3D): 272 -> 192 variants' -and $summary[1] -eq '  DeepFrontier/IrradiatedTerrainURP (Metal): 256 -> 192 variants' -and
    $summary[2] -eq '  [PlayerBuildShaderStripping] player build: stripped 1136 variants of mod shaders (3: a, b, c)') "stripping summary: $($summary -join ' / ')"
} finally {
  if (Test-Path -LiteralPath $temp) { Remove-Item -LiteralPath $temp -Recurse -Force }
}
Write-Output "$shell`: bundle cache fingerprint, store, reuse, install and refusals behave; stripping summary parsed."

if (-not $Nested) {
  & (Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe') -NoProfile -ExecutionPolicy Bypass -File $PSCommandPath -Nested
  if ($LASTEXITCODE -ne 0) { throw 'The Windows PowerShell 5.1 pass failed.' }
  Write-Output 'PASS: Unity build tooling (compile, parse, process priority and affinity, bundle cache) in PowerShell 7 and Windows PowerShell 5.1.'
}
