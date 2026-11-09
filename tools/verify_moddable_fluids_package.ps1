#Requires -Version 7
# Verify the kept official packages (outputs/fluids-api-prototype/packages) without changing them:
# manifest and DLL set, official-output hashes, then the installed-Mono probes run against copies of
# the official API DLLs (API present) and of the fixture DLLs alone (API absent). Run from the real
# checkout after tools/build_moddable_fluids.ps1 -SyntheticFixtures. It also requires that none of the
# packages is installed: they belong in the Mods folder only during an acceptance run.
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'timberbornDocuments','python'
$output = Join-Path $root 'outputs/fluids-api-prototype'
$installed = Join-Path $output 'packages/ModdableFluids/version-1.1'
foreach ($id in @('ModdableFluids','ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled')) {
  if (Test-Path -LiteralPath (Join-Path $dev.timberbornDocuments "Mods/$id")) { throw "$id is installed in the Mods folder outside an acceptance run." }
}
$package = Get-Content (Join-Path $output 'package-report.json') -Raw | ConvertFrom-Json
if ((Get-FileHash -LiteralPath (Join-Path $installed 'manifest.json')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $root 'src/ModdableFluids/manifest.json')).Hash) { throw 'Kept package manifest differs from the authored source.' }
$apiNames = @('ModdableFluids.dll','ModdableFluids.TransportPrototype.dll','ModdableFluids.GamePrototype.dll','ModdableFluids.RuntimePrototype.dll')
$files = @(Get-ChildItem -LiteralPath (Join-Path $installed 'Scripts') -File)
if ($files.Count -ne $apiNames.Count -or @($files | Where-Object Name -notin $apiNames).Count -ne 0) { throw 'The package must hold exactly the four Moddable Fluids assemblies.' }
foreach ($name in $apiNames) {
  if ((Get-FileHash -LiteralPath (Join-Path $installed "Scripts/$name")).Hash -ne $package.assemblies.$name) { throw "Kept $name differs from the recorded official build." }
}
$fixtures = @('ModdableFluidsSyntheticReflection','ModdableFluidsSyntheticCompiled')
$fixtureDlls = @()
foreach ($id in $fixtures) {
  $dll = Join-Path $output "packages/$id/version-1.1/Scripts/$id.dll"
  if ((Get-FileHash -LiteralPath $dll).Hash -ne $package.fixtures.$id.assemblies."$id.dll") { throw "Kept fixture $id differs from the recorded official build." }
  $fixtureDlls += $dll
}
foreach ($project in @('fluid-native-mono/ModdableFluids.NativeMonoProbe.csproj','fluid-absence-probe/ModdableFluids.AbsenceProbe.csproj')) {
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
Write-Output 'PASS: kept Moddable Fluids and fixture packages, none installed, installed-Mono present and absent probes.'
