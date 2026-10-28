param(
  [string]$DllDirectory = (Join-Path (Resolve-Path (Join-Path $PSScriptRoot '..\vendor\timberborn-modding')).Path 'Assets\Plugins\Timberborn')
)

$ErrorActionPreference = 'Stop'
$cecilPath = 'C:\Users\Jordan\Documents\TimberbornModding\vendor\timberborn-modding\Library\PackageCache\com.unity.nuget.mono-cecil@ecb9724e46ff\Mono.Cecil.dll'
if (-not (Test-Path $cecilPath)) {
  throw "Mono.Cecil was not found at $cecilPath. Run bootstrap_unity_timberborn_assets.ps1 first."
}

Add-Type -Path $cecilPath
$resolver = New-Object Mono.Cecil.DefaultAssemblyResolver
$resolver.AddSearchDirectory($DllDirectory)
$gameManaged = 'C:\Program Files (x86)\Steam\steamapps\common\Timberborn\Timberborn_Data\Managed'
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
