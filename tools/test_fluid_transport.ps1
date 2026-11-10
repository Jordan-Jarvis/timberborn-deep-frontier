#Requires -Version 7
# Run in a freshly synchronized scratch mirror. Builds the pure netstandard2.1
# prototype and invokes installed native water tasks from a .NET 8 harness.
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'gameManaged','python','node'
# Moddable Fluids' shader variants (shared water and terrain overlay) are current for the native graphs.
& $dev.node (Join-Path $PSScriptRoot 'moddable_fluids_shader_variants.mjs') --check
if ($LASTEXITCODE -ne 0) { throw 'Moddable Fluids shader variants are stale; run node tools/moddable_fluids_shader_variants.mjs' }
$project = Join-Path $PSScriptRoot 'compile-check/fluid-transport-harness/FluidTransportHarness.csproj'
$specification = Join-Path $root 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Configurations/WaterSimulator.blueprint.json'
$report = Join-Path $root 'outputs/fluids-api-prototype/transport-report.json'
& dotnet build $project --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Fluid transport prototype build failed' }
$harness = Join-Path $PSScriptRoot 'compile-check/fluid-transport-harness/bin/Release/net8.0/FluidTransportHarness.dll'
$reflectionConsumer = Join-Path $PSScriptRoot 'compile-check/fluid-synthetic-reflection/bin/Release/netstandard2.1/ModdableFluidsSyntheticReflection.dll'
& dotnet $harness $dev.gameManaged $specification $report $reflectionConsumer
if ($LASTEXITCODE -ne 0) { throw 'Fluid transport prototype assertions failed' }
$monoProject = Join-Path $PSScriptRoot 'compile-check/fluid-native-mono/ModdableFluids.NativeMonoProbe.csproj'
& dotnet build $monoProject --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Fluid native Mono probe build failed' }
$monoProbe = Join-Path $PSScriptRoot 'compile-check/fluid-native-mono/bin/Release/netstandard2.1/ModdableFluids.NativeMonoProbe.dll'
$compiledConsumer = Join-Path $PSScriptRoot 'compile-check/fluid-synthetic-compiled/bin/Release/netstandard2.1/ModdableFluidsSyntheticCompiled.dll'
& $dev.python (Join-Path $PSScriptRoot 'run_fluid_native_mono.py') $monoProbe $reflectionConsumer $compiledConsumer
if ($LASTEXITCODE -ne 0) { throw 'Fluid native Mono probe failed' }
$absenceProject = Join-Path $PSScriptRoot 'compile-check/fluid-absence-probe/ModdableFluids.AbsenceProbe.csproj'
& dotnet build $absenceProject --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Fluid API absence probe build failed' }
$absenceProbe = Join-Path $PSScriptRoot 'compile-check/fluid-absence-probe/bin/Release/netstandard2.1/ModdableFluids.AbsenceProbe.dll'
& $dev.python (Join-Path $PSScriptRoot 'run_fluid_native_mono.py') --absent $absenceProbe $reflectionConsumer $compiledConsumer
if ($LASTEXITCODE -ne 0) { throw 'Fluid API absence Mono probe failed' }
$runtimeProject = Join-Path $PSScriptRoot 'compile-check/fluid-runtime/ModdableFluids.RuntimePrototype.csproj'
& dotnet build $runtimeProject --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Fluid scene lifecycle prototype build failed' }
# Deep Frontier with DEEP_FRONTIER_MODDABLE_FLUIDS (migration groundwork; never shipped) must keep compiling.
$flaggedProject = Join-Path $PSScriptRoot 'compile-check/deep-frontier-moddable-fluids/DeepFrontierModdableFluidsCompileCheck.csproj'
& dotnet build $flaggedProject --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Deep Frontier Moddable Fluids build (flagged) failed' }
# Moddable Fluids tides (tides area): its own installed-Mono probe in a separate process.
$tidesProject = Join-Path $PSScriptRoot 'compile-check/fluid-tides/probe/ModdableFluids.TidesMonoProbe.csproj'
& dotnet build $tidesProject --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Moddable Fluids tides Mono probe build failed' }
$tidesProbe = Join-Path $PSScriptRoot 'compile-check/fluid-tides/probe/bin/Release/netstandard2.1/ModdableFluids.TidesMonoProbe.dll'
& $dev.python (Join-Path $PSScriptRoot 'compile-check/fluid-tides/run_tides_mono.py') $tidesProbe (Join-Path $root 'outputs/fluids-api-prototype/tides-mono-report.json')
if ($LASTEXITCODE -ne 0) { throw 'Moddable Fluids tides Mono probe failed' }
