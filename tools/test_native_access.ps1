#Requires -Version 7
# Compiled access to game members that are not public (docs/native-safety-audit.md, "Compiled access").
#
# Deep Frontier compiles against publicized reference assemblies (ModsBuildManaged), so its C# can name private
# and internal game members directly. Mono binds such a reference only when the method using it first runs, so a
# game update that renames one fails mid-game. This builds the main and optional assemblies (incremental), runs
# tools/compile-check/native-access against the SHIPPED game assemblies and the pinned dependency DLLs, and fails
# when:
#   - any reference is missing from the installed game or dependency (the game changed under the compiled code);
#   - a non-public reference is not in tools/native_access_baseline.json (new compiled access must be audited);
#   - a baseline entry is no longer referenced (the baseline stays exact).
# References a subclass may make (protected members) and Deep Frontier's own InternalsVisibleTo are not
# publicizer-dependent and are not listed. Report: outputs/native-access/report.json.
#
#   pwsh tools/test_native_access.ps1                    # check
#   pwsh tools/test_native_access.ps1 -WriteBaseline     # rewrite the baseline after auditing the change
param([switch]$WriteBaseline)
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'gameManaged', 'workshopContent'
$compile = Join-Path $PSScriptRoot 'compile-check'
$projects = @(
  'DeepFrontierCompileCheck.csproj',
  'power-lines/DeepFrontierPowerLinesCompile.csproj',
  'moddable-weathers/DeepFrontierModdableWeathersCompile.csproj',
  'sluice-is-back/DeepFrontierSluiceIsBackCompile.csproj')
foreach ($project in $projects) {
  & dotnet build (Join-Path $compile $project) -v:q -nologo | Out-Null
  if ($LASTEXITCODE -ne 0) { throw "compile failed: $project" }
}
$inputs = @(
  'bin/Debug/netstandard2.1/DeepFrontier.dll',
  'power-lines/bin/Debug/netstandard2.1/DeepFrontier.PowerLines.dll',
  'moddable-weathers/bin/Debug/netstandard2.1/DeepFrontier.ModdableWeathers.dll',
  'sluice-is-back/bin/Debug/netstandard2.1/DeepFrontier.SluiceIsBack.dll') | ForEach-Object { Join-Path $compile $_ }
$workshop = $dev.workshopContent
# The version-1.1 copies the compile checks build against (Workshop items keep one copy per game version).
$pinned = @(
  '3639961044/version-1.1/ModdableRecipes.dll',
  '3630523180/version-1.1/ModdableWeathers.dll',
  '3677643870/version-1.1/SluiceIsBack.dll',
  '3430626620/version-1.1/TimberUi.dll') | ForEach-Object { '--assembly'; Join-Path $workshop $_ }
$out = Join-Path $PSScriptRoot '../outputs/native-access/report.json'
& dotnet run --project (Join-Path $compile 'native-access') -- @inputs --managed $dev.gameManaged --workshop $workshop @pinned --out $out
$code = $LASTEXITCODE
$report = Get-Content -LiteralPath $out -Raw | ConvertFrom-Json
if ($code -ne 0 -or @($report.missing).Count -gt 0) { throw "$(@($report.missing).Count) compiled references are missing from the installed game or dependencies (see $out)" }
if (@($report.unresolvedAssemblies).Count -gt 0) { throw "unresolved assemblies: $(@($report.unresolvedAssemblies).assembly -join ', ')" }

$key = { param($e) "$($e.assembly)|$($e.type)|$($e.member)|$($e.kind)" }
$current = @($report.nonPublic | Where-Object { -not $_.fromSubclass -and -not $_.internalsVisibleTo } | ForEach-Object { & $key $_ }) | Sort-Object -Unique
$baselinePath = Join-Path $PSScriptRoot 'native_access_baseline.json'
if ($WriteBaseline) {
  [ordered]@{
    note = 'Compiled references to non-public game members (publicized reference assemblies), audited in docs/native-safety-audit.md. Written by tools/test_native_access.ps1 -WriteBaseline.'
    references = $current
  } | ConvertTo-Json | Set-Content -LiteralPath $baselinePath -Encoding utf8NoBOM
  "Baseline written: $($current.Count) references."
  return
}
$baseline = @((Get-Content -LiteralPath $baselinePath -Raw | ConvertFrom-Json).references)
$new = @($current | Where-Object { $_ -notin $baseline })
$stale = @($baseline | Where-Object { $_ -notin $current })
if ($new.Count -gt 0 -or $stale.Count -gt 0) {
  $new | ForEach-Object { "NEW (audit it, then -WriteBaseline): $_" }
  $stale | ForEach-Object { "STALE (no longer referenced; -WriteBaseline): $_" }
  throw "native access differs from the audited baseline: $($new.Count) new, $($stale.Count) stale"
}
"Native access: $($current.Count) audited non-public references, none missing from the installed game (report: $out)."
