#Requires -Version 7
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments'
# .NET enforces visibility across assemblies; use the official publicized game
# assemblies, whose task bodies are unchanged. The shipped game runs on Mono.
$managed = Join-Path $dev.timberbornDocuments 'ModsBuild/TimberbornModExamples_Data/Managed'
$compile = Join-Path $PSScriptRoot 'compile-check/DeepFrontierCompileCheck.csproj'
& dotnet build $compile -v:q
if ($LASTEXITCODE -ne 0) { throw 'Deep Frontier compile failed' }
$assembly = Join-Path $PSScriptRoot 'compile-check/bin/Debug/netstandard2.1/DeepFrontier.dll'
& dotnet run --project (Join-Path $PSScriptRoot 'compile-check/radiation-mixing/RadiationMixingHarness.csproj') -- $assembly $managed
if ($LASTEXITCODE -ne 0) { throw 'Radiation mixing regression failed' }
