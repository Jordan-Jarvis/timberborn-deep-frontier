# Persistent, incremental scratch mirror of this repository for isolated
# generation and validation (agents must never generate into the real Data).
#
#   pwsh tools/scratch_mirror.ps1 -Name radiation      # prints the mirror root
#
# The mirror lives at %USERPROFILE%\dfs\<Name>: a short path outside AppData,
# which the desktop app redirects into a long package path (the deep session
# temp folders broke four validators on the 260-character path limit). It is
# reused across runs: robocopy /MIR copies only files whose size or time
# changed and removes files deleted here, so a re-sync takes seconds instead of
# a multi-GB copy. Scratch-only edits are discarded by the next sync.
#
# Read-only inputs are directory junctions to the real folders, never copies:
# vendor (8 GB of vanilla reference data), the Blender scenes in
# src/DeepFrontier/Art/Source (12 GB; generators only read and hash them), the
# art review records and images in docs/art (750 MB; validators read them),
# node_modules and the bundled Blender. Nothing that runs in a mirror may write into them: run
# Blender saves and exports in the real repository (tools/asset-pipeline/blender_low.sh).
param(
  [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9_-]+$')][string]$Name
)
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$mirror = Join-Path $env:USERPROFILE "dfs\$Name"
New-Item -ItemType Directory -Force -Path $mirror | Out-Null

function Sync([string]$relative, [string[]]$excludeDirs = @(), [string[]]$excludeFiles = @()) {
  $source = Join-Path $root $relative
  $target = Join-Path $mirror $relative
  $arguments = @($source, $target, '/MIR', '/FFT', '/R:1', '/W:1', '/NFL', '/NDL', '/NJH', '/NJS', '/NP', '/MT:8')
  if ($excludeDirs.Count) { $arguments += '/XD'; $arguments += $excludeDirs }
  if ($excludeFiles.Count) { $arguments += '/XF'; $arguments += $excludeFiles }
  & robocopy @arguments | Out-Null
  # robocopy: 0-7 success (bit flags for copied/extra/mismatched), 8+ failure.
  if ($LASTEXITCODE -ge 8) { throw "robocopy failed ($LASTEXITCODE) for $relative" }
}

function Link([string]$relative) {
  $target = Join-Path $mirror $relative
  $source = Join-Path $root $relative
  $item = Get-Item -LiteralPath $target -Force -ErrorAction SilentlyContinue
  if ($item -and $item.LinkType -eq 'Junction' -and $item.Target -contains $source) { return }
  if ($item) { throw "$target exists and is not a junction to $source; remove it first" }
  New-Item -ItemType Directory -Force -Path (Split-Path -Parent $target) | Out-Null
  New-Item -ItemType Junction -Path $target -Target $source | Out-Null
}

Link 'vendor'
Link 'node_modules'
Link 'tools\asset-pipeline\blender-4.5.3'
Link 'src\DeepFrontier\Art\Source'
# Junctioned folders are excluded on both sides so robocopy neither copies nor
# deletes through them.
Sync 'src' @((Join-Path $root 'src\DeepFrontier\Art\Source'), (Join-Path $mirror 'src\DeepFrontier\Art\Source'))
# Blender is a junction; robocopy must not mirror (or delete) through it.
Sync 'tools' @((Join-Path $root 'tools\asset-pipeline\blender-4.5.3'), (Join-Path $mirror 'tools\asset-pipeline\blender-4.5.3'))
Link 'docs\art'
Sync 'docs' @((Join-Path $root 'docs\art'), (Join-Path $mirror 'docs\art'))
# Generation and validators read registrations, exports and manifests under
# outputs; Blender scenes, logs and review renders are not inputs.
Sync 'outputs' @('zfight', 'zfight-baseline-*', 'alignment-audit', 'review-sheets', 'review-*', 'validate-all', 'catalog-shell-review', 'bin', 'obj') @('*.blend', '*.blend1', '*.log')
foreach ($file in Get-ChildItem -LiteralPath $root -File) {
  Copy-Item -LiteralPath $file.FullName -Destination $mirror -Force
}
Write-Output $mirror
