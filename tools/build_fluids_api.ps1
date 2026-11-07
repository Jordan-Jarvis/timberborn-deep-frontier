# Build/install only the separate development package with the official Mod Builder.
param()
$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$dev = Get-DevEnvironment 'unity','workshopContent','timberbornDocuments'
if (Get-CimInstance Win32_Process -Filter "Name='Timberborn.exe'" | Where-Object { $_.CommandLine -match '(^|\s)-fluidsApiWorkerAcceptance(\s|$)' }) {
  throw 'Close the active Fluids API acceptance process before replacing its package.'
}
if (Get-CimInstance Win32_Process -Filter "Name='Unity.exe'" | Where-Object ExecutablePath -eq $dev.unity) { throw 'Close the Unity authoring editor before the prototype build.' }
$project = Join-Path $root 'vendor/timberborn-modding'
$source = Join-Path $root 'src/FluidsApi'
$stage = Join-Path $project 'Assets/Mods/FluidsApi'
$installed = [System.IO.Path]::GetFullPath((Join-Path $dev.timberbornDocuments 'Mods/FluidsApi/version-1.1'))
$intended = [System.IO.Path]::GetFullPath((Join-Path $dev.timberbornDocuments 'Mods/FluidsApi')) + [System.IO.Path]::DirectorySeparatorChar
if (-not $installed.StartsWith($intended, [StringComparison]::OrdinalIgnoreCase)) { throw 'Prototype build target escapes its dedicated mod directory.' }
New-Item -ItemType Directory -Force -Path $stage | Out-Null
Copy-Item -LiteralPath (Join-Path $source 'manifest.json') -Destination $stage -Force
foreach ($assembly in @(
  @{Folder='Core';Name='FluidsApi.TransportPrototype';Sources=@('Transport','Native')},
  @{Folder='GameBridge';Name='FluidsApi.GamePrototype';Sources=@('GameBridge')},
  @{Folder='Runtime';Name='FluidsApi.RuntimePrototype';Sources=@('Runtime')}
)) {
  $target = Join-Path $stage ('Scripts/' + $assembly.Folder)
  New-Item -ItemType Directory -Force -Path $target | Out-Null
  Copy-Item -LiteralPath (Join-Path $source ('Authoring/' + $assembly.Name + '.asmdef')) -Destination $target -Force
  foreach ($folder in $assembly.Sources) {
    $destination = Join-Path $target $folder
    New-Item -ItemType Directory -Force -Path $destination | Out-Null
    $activeNames = @(Get-ChildItem (Join-Path $source $folder) -Filter '*.cs' -File | Select-Object -ExpandProperty Name)
    foreach ($old in Get-ChildItem -LiteralPath $destination -File -Filter '*.cs') {
      if ($old.Name -notin $activeNames) { Remove-Item -LiteralPath $old.FullName -Force }
    }
    foreach ($file in Get-ChildItem (Join-Path $source $folder) -Filter '*.cs' -File) { Copy-Item -LiteralPath $file.FullName -Destination $destination -Force }
  }
}
$dependencies = Join-Path $project 'Assets/Plugins/ModDependencies'
New-Item -ItemType Directory -Force -Path $dependencies | Out-Null
Copy-Item -LiteralPath (Join-Path $dev.workshopContent '3284904751/0Harmony.dll') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/0Harmony.dll.meta') -Destination $dependencies -Force
Copy-Item -LiteralPath (Join-Path $PSScriptRoot 'unity/FluidsApiBatchBuild.cs') -Destination (Join-Path $project 'Assets/Tools/Editor/Scripts/ModBuilding') -Force
$log = Join-Path $root 'outputs/fluids-api-prototype/official-build.log'
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
$process = Start-Process -FilePath $dev.unity -WindowStyle Hidden -PassThru -ArgumentList @(
  '-batchmode','-nographics','-quit','-disable-assembly-updater','-projectPath',('"'+$project+'"'),
  '-executeMethod','Timberborn.ModdingTools.ModBuilding.FluidsApiBatchBuild.Build','-logFile',('"'+$log+'"'))
$process.WaitForExit()
if ($process.ExitCode -ne 0) { throw "Official Fluids API build failed. See $log" }
$manifest = Get-Content (Join-Path $installed 'manifest.json') -Raw | ConvertFrom-Json
if ($manifest.Id -ne 'FluidsApi') { throw 'Unexpected installed prototype identity' }
$packageFiles = @(Get-ChildItem -LiteralPath (Join-Path $installed 'Scripts') -File)
$expected = @('FluidsApi.TransportPrototype.dll','FluidsApi.GamePrototype.dll','FluidsApi.RuntimePrototype.dll')
if (@($packageFiles | Where-Object Name -notin $expected).Count -ne 0 -or $packageFiles.Count -ne 3) { throw 'Prototype must contain exactly its three assemblies, without embedded dependencies.' }
$managed = Join-Path $dev.timberbornDocuments 'ModsBuild/TimberbornModExamples_Data/Managed'
$hashes = @{}
foreach ($name in $expected) {
  $actual = (Get-FileHash -LiteralPath (Join-Path $installed ('Scripts/' + $name))).Hash
  if ($actual -ne (Get-FileHash -LiteralPath (Join-Path $managed $name)).Hash) { throw "Official package differs from its compiled output: $name" }
  $hashes[$name] = $actual
}
if ((Get-FileHash -LiteralPath (Join-Path $installed 'manifest.json')).Hash -ne (Get-FileHash -LiteralPath (Join-Path $source 'manifest.json')).Hash) { throw 'Installed manifest differs from the authored source.' }
@{ status='passed'; installed=$installed; assemblies=$hashes; version=$manifest.Version } | ConvertTo-Json -Depth 3 | Set-Content (Join-Path (Split-Path $log) 'package-report.json')
Write-Output "Official prototype installed at $installed. Log: $log"
