param(
  [Parameter(Mandatory=$true)][string]$Model,
  [Parameter(Mandatory=$true)][string]$Components,
  [switch]$Initialize
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$blender = Join-Path $root 'tools/asset-pipeline/blender-4.5.3/blender.exe'
$script = Join-Path $root 'tools/asset-pipeline/rebuild_components.py'
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss-fff'
$report = Join-Path $root "outputs/component-rebuilds/$Model-$stamp.json"
$arguments = @('-b','--python-exit-code','1','--python',$script,'--',
  '--model',$Model,'--components',$Components,'--report',$report)
if ($Initialize) { $arguments += '--initialize' }
& $blender @arguments
if ($LASTEXITCODE -ne 0) { throw 'Selected component rebuild failed; source was not saved.' }
