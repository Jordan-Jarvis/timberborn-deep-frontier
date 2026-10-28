param(
  [Parameter(Mandatory=$true)][string]$Models,
  [string]$Frames = '1',
  [switch]$ReportOnly,
  [switch]$Render
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$blender = Join-Path $root 'tools\asset-pipeline\blender-4.5.3\blender.exe'
$script = Join-Path $root 'tools\asset-pipeline\zfight_audit.py'
$auditArguments = @('-b','--python-exit-code','1','--python',$script,'--','--models',$Models,'--frames',$Frames)
if ($Render) { $auditArguments += '--render' }
if (-not $ReportOnly) { $auditArguments += '--fail-on-visible' }
& $blender @auditArguments
if ($LASTEXITCODE -ne 0) { throw 'Building surface audit failed. Inspect outputs/zfight before exporting; no geometry was changed.' }
