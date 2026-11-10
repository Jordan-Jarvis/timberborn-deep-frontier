#Requires -Version 7
# Verify the kept official packages (outputs/fluids-api-prototype/packages) without changing them:
# manifest and DLL set, official-output hashes, then the installed-Mono probes run against copies of
# the official API DLLs (API present) and of the fixture DLLs alone (API absent). Run from the real
# checkout after tools/build_moddable_fluids.ps1 -SyntheticFixtures. It also requires that none of the
# packages is installed: they belong in the Mods folder only during an acceptance run.
# The tides' Moddable Weathers adapter must be the optional file Scripts/ModdableFluids.ModdableWeathers.dll.ModdableWeathers.optional
# (never a plain DLL), the only package assembly referencing Moddable Weathers, Moddable Timberborn or TimberUi; its
# installed-Mono probe runs against the official copies with the installed Workshop Moddable Weathers 11.0.0.
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
. (Join-Path $PSScriptRoot 'UnityBundleCache.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments','python'
Add-Type -AssemblyName System.Reflection.Metadata
$output = Join-Path $root 'outputs/fluids-api-prototype'
$installed = Join-Path $output 'packages/ModdableFluids/version-1.1'
foreach ($id in @('ModdableFluids','ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled')) {
  if (Test-Path -LiteralPath (Join-Path $dev.timberbornDocuments "Mods/$id")) { throw "$id is installed in the Mods folder outside an acceptance run." }
}
$package = Get-Content (Join-Path $output 'package-report.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $installed 'manifest.json')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $root 'src/ModdableFluids/manifest.json')).Hash) { throw 'Kept package manifest differs from the authored source.' }
$apiNames = @('ModdableFluids.dll','ModdableFluids.TransportPrototype.dll','ModdableFluids.GamePrototype.dll','ModdableFluids.RuntimePrototype.dll')
$adapterName = 'ModdableFluids.ModdableWeathers.dll.ModdableWeathers.optional'
$files = @(Get-ChildItem -LiteralPath (Join-Path $installed 'Scripts') -File)
if ($files.Count -ne $apiNames.Count + 1 -or @($files | Where-Object Name -notin ($apiNames + $adapterName)).Count -ne 0) {
  throw "The package must hold exactly the four Moddable Fluids assemblies and $adapterName (no plain ModdableFluids.ModdableWeathers.dll)." }
foreach ($name in $apiNames + $adapterName) {
  if ((Get-FileHash -LiteralPath (Join-Path $installed "Scripts/$name")).Hash -ne $package.assemblies.$name) { throw "Kept $name differs from the recorded official build." }
}
# Only the optional adapter references the Workshop mods; it references Moddable Weathers and the Runtime assembly.
function Get-AssemblyReferences([string]$path) {
  $stream = [IO.File]::OpenRead($path)
  try {
    $reader = [System.Reflection.Metadata.PEReaderExtensions]::GetMetadataReader([System.Reflection.PortableExecutable.PEReader]::new($stream))
    @(foreach ($handle in $reader.AssemblyReferences) { $reader.GetString($reader.GetAssemblyReference($handle).Name) })
  } finally { $stream.Dispose() }
}
$workshopAssemblies = @('ModdableWeathers','ModdableTimberborn','TimberUi')
foreach ($name in $apiNames) {
  $foreign = @(Get-AssemblyReferences (Join-Path $installed "Scripts/$name") | Where-Object { $_ -in $workshopAssemblies })
  if ($foreign.Count -ne 0) { throw "$name references $($foreign -join ', '); only the optional Moddable Weathers adapter may." }
}
$adapterReferences = Get-AssemblyReferences (Join-Path $installed "Scripts/$adapterName")
if ($adapterReferences -notcontains 'ModdableWeathers' -or $adapterReferences -notcontains 'ModdableFluids.RuntimePrototype') { throw "$adapterName does not reference ModdableWeathers and ModdableFluids.RuntimePrototype." }
foreach ($platform in 'win','mac') {
  if ((Get-FileHash -LiteralPath (Join-Path $installed "AssetBundles/moddablefluids_$platform")).Hash -ne $package.assemblies."moddablefluids_$platform") { throw "Kept $platform shader bundle differs from the recorded official build." }
}
# Exactly the shader variants the game draws (tools/unity/ModShaderVariantStripping.cs, docs/unity-build-performance.md).
& $dev.python (Join-Path $root 'tools/asset-pipeline/check_bundle_shaders.py') --win (Join-Path $installed 'AssetBundles/moddablefluids_win') `
  --mac (Join-Path $installed 'AssetBundles/moddablefluids_mac') --expect 'ModdableFluids/FluidWaterURP_Opaque' 'ModdableFluids/FluidWaterURP_Transparent' 'ModdableFluids/FluidTerrainURP'
if ($LASTEXITCODE -ne 0) { throw 'The kept shader bundles do not hold exactly the variants the game can draw.' }
# The kept AssetBundles folder is byte for byte the cached one of the fingerprint the build recorded (tools/UnityBundleCache.ps1).
$bundleRecord = Assert-BundlesMatchCache -Entry (Get-BundleCacheEntry -Root $root -Mod 'ModdableFluids' -Variant 'default') -Directory (Join-Path $installed 'AssetBundles')
if ($package.bundles.fingerprint -ne $bundleRecord.fingerprint) { throw "package-report.json records bundle fingerprint $($package.bundles.fingerprint); the cache holds $($bundleRecord.fingerprint)." }
$fixtures = @('ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled')
$fixtureDlls = @()
foreach ($id in $fixtures) {
  $dll = Join-Path $output "packages/$id/version-1.1/Scripts/$id.dll"
  if ((Get-FileHash -LiteralPath $dll).Hash -ne $package.fixtures.$id.assemblies."$id.dll") { throw "Kept fixture $id differs from the recorded official build." }
  $fixtureDlls += $dll
}
foreach ($project in @('fluid-native-mono/ModdableFluids.NativeMonoProbe.csproj','fluid-absence-probe/ModdableFluids.AbsenceProbe.csproj',
    'fluid-moddable-weathers/probe/ModdableFluids.ModdableWeathersMonoProbe.csproj')) {
  & dotnet build (Join-Path $PSScriptRoot "compile-check/$project") --configuration Release --nologo
  if ($LASTEXITCODE -ne 0) { throw "Probe build failed: $project" }
}
# API present: the probe binds to copies of the installed DLLs by assembly name.
$present = Join-Path $output 'package-probe'
if (Test-Path -LiteralPath $present) { Remove-Item -LiteralPath $present -Recurse -Force }
New-Item -ItemType Directory -Force -Path $present | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'compile-check/fluid-native-mono/bin/Release/netstandard2.1/ModdableFluids.NativeMonoProbe.dll') -Destination $present
foreach ($name in $apiNames) { Copy-Item -LiteralPath (Join-Path $installed "Scripts/$name") -Destination $present }
& $dev.python (Join-Path $PSScriptRoot 'run_fluid_native_mono.py') (Join-Path $present 'ModdableFluids.NativeMonoProbe.dll') $fixtureDlls[0] $fixtureDlls[1]
if ($LASTEXITCODE -ne 0) { throw 'Installed-package Mono probe failed' }
Copy-Item -LiteralPath (Join-Path $output 'mono-report.json') -Destination (Join-Path $output 'package-mono-report.json') -Force
# API absent: only the absence probe and the official fixture DLLs.
$absent = Join-Path $output 'package-absence-probe'
if (Test-Path -LiteralPath $absent) { Remove-Item -LiteralPath $absent -Recurse -Force }
New-Item -ItemType Directory -Force -Path $absent | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'compile-check/fluid-absence-probe/bin/Release/netstandard2.1/ModdableFluids.AbsenceProbe.dll') -Destination $absent
& $dev.python (Join-Path $PSScriptRoot 'run_fluid_native_mono.py') --absent (Join-Path $absent 'ModdableFluids.AbsenceProbe.dll') $fixtureDlls[0] $fixtureDlls[1]
if ($LASTEXITCODE -ne 0) { throw 'Fixture absence Mono probe failed' }
Copy-Item -LiteralPath (Join-Path $output 'mono-absence-report.json') -Destination (Join-Path $output 'package-absence-report.json') -Force
# The Moddable Weathers adapter: its probe binds to copies of the official API DLLs and of the optional adapter (as a DLL).
$adapterProbe = Join-Path $output 'package-moddable-weathers-probe'
if (Test-Path -LiteralPath $adapterProbe) { Remove-Item -LiteralPath $adapterProbe -Recurse -Force }
New-Item -ItemType Directory -Force -Path $adapterProbe | Out-Null
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'compile-check/fluid-moddable-weathers/probe/bin/Release/netstandard2.1/ModdableFluids.ModdableWeathersMonoProbe.dll') -Destination $adapterProbe
foreach ($name in $apiNames) { Copy-Item -LiteralPath (Join-Path $installed "Scripts/$name") -Destination $adapterProbe }
Copy-Item -LiteralPath (Join-Path $installed "Scripts/$adapterName") -Destination (Join-Path $adapterProbe 'ModdableFluids.ModdableWeathers.dll')
& $dev.python (Join-Path $PSScriptRoot 'compile-check/fluid-moddable-weathers/run_moddable_weathers_mono.py') (Join-Path $adapterProbe 'ModdableFluids.ModdableWeathersMonoProbe.dll') `
  (Join-Path $output 'package-moddable-weathers-report.json')
if ($LASTEXITCODE -ne 0) { throw 'Installed-package Moddable Weathers adapter Mono probe failed' }
Write-Output 'PASS: kept Moddable Fluids and fixture packages, none installed, installed-Mono present, absent and Moddable Weathers adapter probes.'
