# This machine's Timberborn and tool paths, written by tools/setup_dev.py.
#   . (Join-Path $PSScriptRoot 'DevEnvironment.ps1'); $dev = Get-DevEnvironment 'node','python'
# Get-DevEnvironment throws when tools/dev-environment.json or a requested entry
# is missing; it never guesses a path.
function Get-DevEnvironment([string[]]$Required = @()) {
  $config = Join-Path $PSScriptRoot 'dev-environment.json'
  if (-not (Test-Path -LiteralPath $config -PathType Leaf)) {
    throw 'tools/dev-environment.json is missing: run "python tools/setup_dev.py" first.'
  }
  $dev = Get-Content -LiteralPath $config -Raw | ConvertFrom-Json
  foreach ($key in $Required) {
    if (-not $dev.$key) { throw "`"$key`" is not set in tools/dev-environment.json: re-run `"python tools/setup_dev.py`"." }
  }
  return $dev
}
