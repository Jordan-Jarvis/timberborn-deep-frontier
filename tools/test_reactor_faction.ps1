#Requires -Version 7
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments'
$managed = Join-Path $dev.timberbornDocuments 'ModsBuild/TimberbornModExamples_Data/Managed'
& dotnet build (Join-Path $PSScriptRoot 'compile-check/DeepFrontierCompileCheck.csproj') -v:q
if ($LASTEXITCODE -ne 0) { throw 'Deep Frontier compile failed' }
$assembly = Join-Path $PSScriptRoot 'compile-check/bin/Debug/netstandard2.1/DeepFrontier.dll'
& dotnet run --project (Join-Path $PSScriptRoot 'compile-check/reactor-faction/ReactorFactionHarness.csproj') -- $assembly $managed
if ($LASTEXITCODE -ne 0) { throw 'Reactor Bot faction regression failed' }
