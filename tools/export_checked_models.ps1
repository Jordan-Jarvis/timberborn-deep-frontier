param(
  [Parameter(Mandatory=$true)][string]$Models,
  [string]$Frames = '1',
  [switch]$Render,
  [switch]$Bake
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

# A fresh audit must succeed before the official exporter can write anything.
# No report cache, waived findings, geometry repair or depth bias is applied.
& (Join-Path $PSScriptRoot 'check_building_surfaces.ps1') -Models $Models -Frames $Frames -Render:$Render

$blender = Join-Path $root 'tools\asset-pipeline\blender-4.5.3\blender.exe'
$exportScript = Join-Path $root 'tools\asset-pipeline\export_industrial_models.py'
$exportArguments = @('-b','--python-exit-code','1','--python',$exportScript,'--','--models',$Models)
if ($Bake) { $exportArguments += '--bake' }
& $blender @exportArguments
if ($LASTEXITCODE -ne 0) { throw 'Official Timbermesh export failed.' }
