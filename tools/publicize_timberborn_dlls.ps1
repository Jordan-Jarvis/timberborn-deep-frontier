param(
  [string]$DllDirectory = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\vendor\timberborn-modding')).Path 'Assets\Plugins\Timberborn')
)

$ErrorActionPreference = 'Stop'
$packageCache = Join-Path $PSScriptRoot '..\vendor\timberborn-modding\Library\PackageCache'
$cecilPath = Get-ChildItem -Path $packageCache -Filter 'Mono.Cecil.dll' -Recurse -ErrorAction SilentlyContinue |
  Where-Object { $_.Directory.Name -like 'com.unity.nuget.mono-cecil@*' } | Select-Object -First 1 -ExpandProperty FullName
if (-not $cecilPath) {
  throw "Mono.Cecil was not found in $packageCache. Open vendor/timberborn-modding in Unity once (tools/setup_dev.py does this) so it resolves its packages."
}

Add-Type -Path $cecilPath
$resolver = New-Object Mono.Cecil.DefaultAssemblyResolver
$resolver.AddSearchDirectory($DllDirectory)
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$gameManaged = (Get-DevEnvironment 'gameManaged').gameManaged
if (Test-Path $gameManaged) { $resolver.AddSearchDirectory($gameManaged) }
$reader = New-Object Mono.Cecil.ReaderParameters
$reader.AssemblyResolver = $resolver

function Test-CompilerGenerated($member) {
  return [bool]($member.CustomAttributes | Where-Object {
    $_.AttributeType.FullName -eq 'System.Runtime.CompilerServices.CompilerGeneratedAttribute'
  })
}

function Publicize-Type($type) {
  if (-not (Test-CompilerGenerated $type)) {
    if ($type.IsNested) { $type.IsNestedPublic = $true } else { $type.IsPublic = $true }
    foreach ($method in $type.Methods) {
      if (-not (Test-CompilerGenerated $method)) { $method.IsPublic = $true }
    }
    foreach ($property in $type.Properties) {
      # Unity/C# records generate an EqualityContract override whose original
      # accessibility must remain protected; the official importer preserves it.
      if ($property.Name -ne 'EqualityContract') {
        if ($property.GetMethod) { $property.GetMethod.IsPublic = $true }
        if ($property.SetMethod) { $property.SetMethod.IsPublic = $true }
      }
    }
    foreach ($field in $type.Fields) {
      if (-not (Test-CompilerGenerated $field)) { $field.IsPublic = $true }
    }
    foreach ($nested in $type.NestedTypes) { Publicize-Type $nested }
  }
}

$count = 0
foreach ($path in Get-ChildItem -LiteralPath $DllDirectory -Filter 'Timberborn.*.dll' -File) {
  $tmp = "$($path.FullName).publicized.tmp"
  $assembly = [Mono.Cecil.AssemblyDefinition]::ReadAssembly($path.FullName, $reader)
  foreach ($type in $assembly.MainModule.Types) { Publicize-Type $type }
  $assembly.Write($tmp)
  $assembly.Dispose()
  Move-Item -LiteralPath $tmp -Destination $path.FullName -Force
  $count++
}

Write-Output "Publicized $count Timberborn assemblies in $DllDirectory"
