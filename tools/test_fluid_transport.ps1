#Requires -Version 7
# Run in a freshly synchronized scratch mirror. Builds the pure netstandard2.1
# prototype and invokes installed native water tasks from a .NET 8 harness.
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'gameManaged','python'
$project = Join-Path $PSScriptRoot 'compile-check/fluid-transport-harness/FluidTransportHarness.csproj'
$specification = Join-Path $root 'vendor/timberborn-modding/Assets/Tools/ImportedAssets/Editor/Resources/Configurations/WaterSimulator.blueprint.json'
$report = Join-Path $root 'outputs/fluids-api-prototype/transport-report.json'
& dotnet build $project --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Fluid transport prototype build failed' }
$harness = Join-Path $PSScriptRoot 'compile-check/fluid-transport-harness/bin/Release/net8.0/FluidTransportHarness.dll'
& dotnet $harness $dev.gameManaged $specification $report
if ($LASTEXITCODE -ne 0) { throw 'Fluid transport prototype assertions failed' }
$monoProject = Join-Path $PSScriptRoot 'compile-check/fluid-native-mono/FluidsApi.NativeMonoProbe.csproj'
& dotnet build $monoProject --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Fluid native Mono probe build failed' }
$monoProbe = Join-Path $PSScriptRoot 'compile-check/fluid-native-mono/bin/Release/netstandard2.1/FluidsApi.NativeMonoProbe.dll'
& $dev.python (Join-Path $PSScriptRoot 'run_fluid_native_mono.py') $monoProbe
if ($LASTEXITCODE -ne 0) { throw 'Fluid native Mono probe failed' }
$runtimeProject = Join-Path $PSScriptRoot 'compile-check/fluid-runtime/FluidsApi.RuntimePrototype.csproj'
& dotnet build $runtimeProject --configuration Release --nologo
if ($LASTEXITCODE -ne 0) { throw 'Fluid scene lifecycle prototype build failed' }
