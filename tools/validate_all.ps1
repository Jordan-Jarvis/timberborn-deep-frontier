#Requires -Version 7
# Runs every static validator for the active data, in order, and prints a PASS/FAIL table
# with the first error line of each failure. Exit code 1 when any check fails.
# It generates no content: run generators and exports first. Some validators write their
# own evidence reports under outputs/, and audit_item_uses.mjs rewrites
# outputs/item-use-audit.json and docs/item-use-audit.md as it always does.
# Full output of each check: outputs/validate-all/<id>.log.
#
#   pwsh tools/validate_all.ps1                     # everything
#   pwsh tools/validate_all.ps1 -List               # ids, in run order
#   pwsh tools/validate_all.ps1 -Only exports-pit,model-bindings
#   pwsh tools/validate_all.ps1 -SkipBlender        # omit the saved-scene source checks
param(
  [string[]]$Only,
  [switch]$SkipBlender,
  [switch]$List
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$node = 'C:\Users\Jordan\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$python = 'C:\Users\Jordan\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$blender = Join-Path $root 'tools\asset-pipeline\blender-4.5.3\blender.exe'
$logDir = Join-Path $root 'outputs\validate-all'
$source = Join-Path $root 'src\DeepFrontier\Art\Source'

$checks = [System.Collections.Generic.List[object]]::new()
# Pre runs first inside the check (an applicability assertion); Block replaces Exe.
function Add-Check([string]$Id, [string]$Kind, [string]$Exe, [string[]]$Arguments, [scriptblock]$Block, [scriptblock]$Pre, [switch]$ReportOnly) {
  $checks.Add([pscustomobject]@{ Id = $Id; Kind = $Kind; Exe = $Exe; Arguments = $Arguments; Block = $Block; Pre = $Pre; ReportOnly = [bool]$ReportOnly })
}

# 1. Promotion preconditions (the non-generating checks of promote_style_exports.ps1).
Add-Check 'promote-clearance' 'json' -Block {
  $routes = Get-Content -LiteralPath (Join-Path $root 'outputs/industrial-integration/route-clearance-diagnostics.json') -Raw | ConvertFrom-Json
  foreach ($route in $routes) { if ($route.issues.Count -ne 0) { throw "Route obstruction in $($route.model)" } }
  $openings = Get-Content -LiteralPath (Join-Path $root 'outputs/industrial-integration/opening-clearance-diagnostics.json') -Raw | ConvertFrom-Json
  foreach ($model in $openings) {
    foreach ($port in $model.ports) { if ($port.issueCount -ne 0) { throw "Opening obstruction in $($model.model)/$($port.port)" } }
  }
  "Route and opening clearance diagnostics: $(@($routes).Count) routes, $(@($openings).Count) models, no issues."
}

# 2. Exported Timbermesh payloads and their blueprint bindings (every validate_*_exports.py).
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $root 'tools/asset-pipeline') -Filter 'validate_*_exports.py' | Sort-Object Name) {
  $name = $file.BaseName -replace '^validate_', '' -replace '_exports$', ''
  Add-Check "exports-$name" 'python' $python @($file.FullName)
}

# 3. Saved source scenes (Blender, read-only). Commands match tools/validate_style_sources.ps1;
#    civic walk checks cover the CIVIC_ACCESS models whose scene is an active catalog source.
if (-not $SkipBlender) {
  foreach ($name in 'research', 'hydro') {
    Add-Check "sources-$name" 'blender' $blender @('-b', '-t', '6', '--python-exit-code', '1', '-P', (Join-Path $root "tools/asset-pipeline/validate_${name}_source.py"))
  }
  Add-Check 'sources-structural' 'blender' $blender @('-b', '-t', '6', '--python-exit-code', '1', '-P', (Join-Path $root 'tools/asset-pipeline/validate_structural_sources.py'))
  Add-Check 'sources-mixer' 'blender' $blender @('-b', '-t', '6', '--python-exit-code', '1', '-P', (Join-Path $root 'tools/asset-pipeline/validate_mixer_source.py'),
    '--', '--scene', (Join-Path $source 'ConcreteMixer-ReferenceStudy.blend'), '--report', (Join-Path $root 'outputs/style-source-mixer.json'))
  Add-Check 'sources-pits' 'blender' $blender @('-b', '-t', '6', '--python-exit-code', '1', '-P', (Join-Path $root 'tools/asset-pipeline/validate_pit_sources.py'),
    '--', '--source-dir', $source, '--report', (Join-Path $root 'outputs/style-source-pits.json'))
  $civic = 'FishHatchery', 'FisheryWorks', 'Hospital', 'Restaurant'
  Add-Check 'sources-civic' 'blender' $blender @('-b', '-t', '6', '--python-exit-code', '1', '-P', (Join-Path $root 'tools/asset-pipeline/validate_civic_sources.py'),
    '--', '--models', ($civic -join ',')) -Pre {
    $catalogScenes = (Get-Content -LiteralPath (Join-Path $root 'tools/building_asset_catalog.json') -Raw | ConvertFrom-Json).buildings.sourceScene
    foreach ($ident in $civic) {
      if ("src/DeepFrontier/Art/Source/$ident-ReferenceStudy.blend" -notin $catalogScenes) {
        throw "$ident-ReferenceStudy.blend is no longer an active catalog source; update the civic source list in validate_all.ps1"
      }
    }
  }
}

# 4. Blueprint visual bindings against the authored Timbermesh nodes.
Add-Check 'model-bindings' 'python' $python @((Join-Path $root 'tools/asset-pipeline/validate_model_bindings.py'))

# 5. Content and manifest validators (every tools/validate_*.mjs).
foreach ($file in Get-ChildItem -LiteralPath (Join-Path $root 'tools') -Filter 'validate_*.mjs' | Sort-Object Name) {
  Add-Check ($file.BaseName -replace '^validate_', '') 'node' $node @($file.FullName)
}

# 6. Audits.
Add-Check 'audit-progression' 'node' $node @((Join-Path $root 'tools/audit_progression.mjs'))
Add-Check 'audit-item-uses' 'node' $node @((Join-Path $root 'tools/audit_item_uses.mjs')) -ReportOnly
Add-Check 'audit-building-assets' 'python' $python @((Join-Path $root 'tools/audit_building_assets.py'), '--require-mirroring')

if ($List) { $checks | ForEach-Object { '{0,-28} {1}{2}' -f $_.Id, $_.Kind, $(if ($_.ReportOnly) { ' (report only)' } else { '' }) }; return }
if ($Only) {
  $unknown = $Only | Where-Object { $_ -notin $checks.Id }
  if ($unknown) { throw "Unknown check id(s): $($unknown -join ', '). Use -List." }
  $checks = [System.Collections.Generic.List[object]]@($checks | Where-Object { $_.Id -in $Only })
}

# The exception or failure line itself: a Python/Node exception line ("ValueError: ...",
# "AssertionError [ERR_ASSERTION]: ..."), else the first unindented FAIL/failed/error line.
function Get-FirstError([string]$text) {
  $lines = @($text -split "`r?`n" | Where-Object { $_.Trim() })
  $hit = $lines | Where-Object { $_ -match '^[\w.]*(Error|Exception)\b' } | Select-Object -First 1
  if (-not $hit) { $hit = $lines | Where-Object { $_ -match '^\S.*(FAIL|failed|[Ee]rror|Exception)' -and $_ -notmatch '^Traceback' } | Select-Object -First 1 }
  if (-not $hit) { $hit = $lines | Select-Object -Last 1 }
  # A header such as "... validation failed (30):" continues with its first item.
  $index = [array]::IndexOf($lines, $hit)
  if ($hit.TrimEnd().EndsWith(':') -and $index + 1 -lt $lines.Count) { $hit = $hit.TrimEnd() + ' ' + $lines[$index + 1].Trim() }
  if ($hit.Length -gt 160) { $hit = $hit.Substring(0, 157) + '...' }
  return $hit
}

New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$results = [System.Collections.Generic.List[object]]::new()
Push-Location -LiteralPath $root
try {
  foreach ($check in $checks) {
    $log = Join-Path $logDir "$($check.Id).log"
    $watch = [Diagnostics.Stopwatch]::StartNew()
    $code = 0
    try {
      if ($check.Pre) { & $check.Pre }
      if ($check.Block) { $text = (& $check.Block | Out-String) }
      else {
        $text = (& $check.Exe @($check.Arguments) 2>&1 | Out-String)
        $code = $LASTEXITCODE
      }
    } catch {
      $text = "$($_.Exception.Message)`n$($_.ScriptStackTrace)"
      $code = 1
    }
    $watch.Stop()
    Set-Content -LiteralPath $log -Value $text -Encoding utf8
    $status = if ($code -ne 0) { 'FAIL' } elseif ($check.ReportOnly) { 'REPORT' } else { 'PASS' }
    $detail = ''
    if ($status -eq 'FAIL') { $detail = Get-FirstError $text }
    elseif ($check.Id -eq 'audit-item-uses') {
      $report = $text | ConvertFrom-Json
      $detail = "$(@($report.failures).Count) of $($report.checked) new goods need redesign or more uses (releaseReady=$($report.releaseReady))"
    }
    $results.Add([pscustomobject]@{ Check = $check.Id; Status = $status; Seconds = [math]::Round($watch.Elapsed.TotalSeconds, 1); Detail = $detail })
    Write-Host ('{0,-6} {1,-28} {2,6:0.0}s {3}' -f $status, $check.Id, $watch.Elapsed.TotalSeconds, $detail)
  }
} finally {
  Pop-Location
}

$failed = @($results | Where-Object Status -eq 'FAIL')
''
$results | Format-Table -AutoSize -Wrap | Out-String -Width 220
"{0} checks: {1} passed, {2} failed, {3} report-only. Logs: {4}" -f $results.Count, @($results | Where-Object Status -eq 'PASS').Count, $failed.Count, @($results | Where-Object Status -eq 'REPORT').Count, $logDir
exit ([int]($failed.Count -ne 0))
