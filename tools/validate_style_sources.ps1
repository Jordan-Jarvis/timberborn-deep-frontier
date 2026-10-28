$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
Set-Location -LiteralPath $root
$blender = Join-Path $root 'tools/asset-pipeline/blender-4.5.3/blender.exe'
foreach ($name in @('research', 'hydro', 'structural')) {
  $script = if ($name -eq 'structural') { 'validate_structural_sources.py' } else { "validate_${name}_source.py" }
  & $blender -b -t 6 --python-exit-code 1 -P (Join-Path $root "tools/asset-pipeline/$script") *> (Join-Path $root "outputs/style-source-$name.log")
  if ($LASTEXITCODE -ne 0) { throw "Source validation failed: $name" }
  Write-Output "Source validation passed: $name"
}
& $blender -b -t 6 --python-exit-code 1 -P tools/asset-pipeline/validate_mixer_source.py -- --scene (Join-Path $root 'src/DeepFrontier/Art/Source/ConcreteMixer-ReferenceStudy.blend') --report (Join-Path $root 'outputs/style-source-mixer.json') *> outputs/style-source-mixer.log
if ($LASTEXITCODE -ne 0) { throw 'Mixer source validation failed' }
& $blender -b -t 6 --python-exit-code 1 -P tools/asset-pipeline/validate_pit_sources.py -- --source-dir (Join-Path $root 'src/DeepFrontier/Art/Source') --report (Join-Path $root 'outputs/style-source-pits.json') *> outputs/style-source-pits.log
if ($LASTEXITCODE -ne 0) { throw 'Pit source validation failed' }
Write-Output 'All selected source checks passed; civic route checks ran during rendering.'
