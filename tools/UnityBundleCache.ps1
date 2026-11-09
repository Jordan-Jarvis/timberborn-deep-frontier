# Asset bundle reuse for the official builds (tools/build_deep_frontier.ps1, its -ModdableFluids variant and
# tools/build_moddable_fluids.ps1); docs/unity-build-performance.md. A cold shader compile of the bundles costs well
# over an hour of CPU time, so bundles are built only when one of their inputs changed:
#   . (Join-Path $PSScriptRoot 'UnityBundleCache.ps1')
#   $entry = Get-BundleCacheEntry -Root $root -Mod DeepFrontier -Variant default
#   $inputs = Get-BundleInputs -Project $project -Mod DeepFrontier -Variant default -Unity $unity   # after staging
#   $reuse = Test-BundleCacheHit -Entry $entry -Inputs $inputs      # Unity: -modBundles reuse|build
#   reuse: Assert-BundleInputsUnchanged -Entry $entry -Before $inputs -After (Get-BundleInputs ...)   # after Unity
#          Install-CachedBundles -Entry $entry -Destination <package>/AssetBundles
#   build: verify the bundles, then Save-BundleCache -Entry $entry -Inputs (Get-BundleInputs ...) -Source <package>/AssetBundles
#   verify scripts: Assert-BundlesMatchCache -Entry $entry -Directory <package>/AssetBundles [-Inputs (Get-BundleInputs ...)]
# The fingerprint covers every file the official bundle build reads or that changes the bytes it writes: the staged
# mod's AssetBundles folder with Unity's .meta files (GUIDs), the mod's staged Editor scripts (Deep Frontier's
# "Create Materials" step), the official tools and imported game assets with the staged batch builds and the shader
# stripping (Assets/Tools), the game assemblies whose scripts bundled objects use (Assets/Plugins/Timberborn), the
# render pipeline assets and project settings, the package versions, the Unity editor version and its Windows and
# macOS build support (every bundle is built for both: <mod>_win and <mod>_mac). The cache keeps the AssetBundles
# folder exactly as the official builder wrote it, both platforms' bundles and manifests, in
# outputs/unity-bundle-cache/<Mod>/<Variant> (fingerprint.json, inputs.tsv: one "path<TAB>SHA-256" line per input),
# written only after a verified build. Works in Windows PowerShell 5.1 and PowerShell 7.

# Unity's build support for the two bundle targets (StandaloneWindows64, StandaloneOSX), under Editor/Data/PlaybackEngines.
$script:BundleTargetSupport = @(
  'windowsstandalonesupport/UnityEditor.WindowsStandalone.Extensions.dll', 'windowsstandalonesupport/modules.asset',
  'MacStandaloneSupport/UnityEditor.OSXStandalone.Extensions.dll', 'MacStandaloneSupport/modules.asset'
)

$script:BundleInputRoots = @(
  'Assets/Rendering', 'Assets/Rendering.meta', 'Assets/Tools', 'Assets/Tools.meta',
  'Assets/Plugins/Timberborn', 'Assets/Plugins/Timberborn.meta',
  'ProjectSettings/GraphicsSettings.asset', 'ProjectSettings/QualitySettings.asset', 'ProjectSettings/ProjectSettings.asset',
  'ProjectSettings/EditorSettings.asset', 'ProjectSettings/ShaderGraphSettings.asset', 'ProjectSettings/URPProjectSettings.asset',
  'ProjectSettings/ProjectVersion.txt', 'Packages/manifest.json', 'Packages/packages-lock.json'
)

function Get-BundleFileHash([string]$Path) {
  $stream = [IO.File]::OpenRead($Path)
  try {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return [BitConverter]::ToString($sha.ComputeHash($stream)).Replace('-', '') } finally { $sha.Dispose() }
  } finally { $stream.Dispose() }
}

function Get-BundleCacheEntry([string]$Root, [string]$Mod, [string]$Variant) {
  if ($Mod -notmatch '^[A-Za-z0-9]+$' -or $Variant -notmatch '^[a-z0-9-]+$') { throw "Invalid bundle cache key $Mod/$Variant" }
  return (Join-Path $Root "outputs\unity-bundle-cache\$Mod\$Variant")
}

# The bundle inputs of a staged mod: relative path (with /) to SHA-256, and the fingerprint over all of them.
function Get-BundleInputs([string]$Project, [string]$Mod, [string]$Variant, [string]$Unity) {
  $projectFull = (Resolve-Path -LiteralPath $Project).Path.TrimEnd('\', '/')
  $bundleRoot = Join-Path $projectFull "Assets\Mods\$Mod\AssetBundles"
  if (-not (Test-Path -LiteralPath $bundleRoot -PathType Container)) { throw "$Mod has no staged AssetBundles folder ($bundleRoot)." }
  if (-not (Test-Path -LiteralPath $Unity -PathType Leaf)) { throw "The Unity editor is missing: $Unity" }
  $roots = @("Assets/Mods/$Mod/AssetBundles", "Assets/Mods/$Mod/AssetBundles.meta", "Assets/Mods/$Mod/Editor", "Assets/Mods/$Mod/Editor.meta") + $script:BundleInputRoots
  $paths = [Collections.Generic.List[string]]::new()
  foreach ($relative in $roots) {
    $full = Join-Path $projectFull ($relative.Replace('/', '\'))
    if (Test-Path -LiteralPath $full -PathType Leaf) { $paths.Add($full) }
    elseif (Test-Path -LiteralPath $full -PathType Container) {
      foreach ($file in Get-ChildItem -LiteralPath $full -File -Recurse -Force) { $paths.Add($file.FullName) }
    }
  }
  $files = [Collections.Generic.SortedDictionary[string, string]]::new([StringComparer]::Ordinal)
  foreach ($path in $paths) { $files[$path.Substring($projectFull.Length + 1).Replace('\', '/')] = Get-BundleFileHash $path }
  $unityVersion = (Get-Item -LiteralPath $Unity).VersionInfo.ProductVersion
  $engines = Join-Path (Split-Path -Parent $Unity) 'Data\PlaybackEngines'
  foreach ($relative in $script:BundleTargetSupport) {
    $path = Join-Path $engines ($relative.Replace('/', '\'))
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { throw "The bundles need Unity's Windows and macOS build support: $path is missing." }
    $files["unity:PlaybackEngines/$relative"] = Get-BundleFileHash $path
  }
  $text = [Text.StringBuilder]::new()
  [void]$text.Append("format 1`nmod $Mod`nvariant $Variant`nunity $unityVersion`n")
  foreach ($pair in $files.GetEnumerator()) { [void]$text.Append("$($pair.Key)`t$($pair.Value)`n") }
  $sha = [Security.Cryptography.SHA256]::Create()
  try { $fingerprint = [BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($text.ToString()))).Replace('-', '') } finally { $sha.Dispose() }
  $map = [ordered]@{}
  foreach ($pair in $files.GetEnumerator()) { $map[$pair.Key] = $pair.Value }
  return [pscustomobject]@{ mod = $Mod; variant = $Variant; unity = $unityVersion; fingerprint = $fingerprint; files = $map }
}

function Read-BundleCacheRecord([string]$Entry) {
  $path = Join-Path $Entry 'fingerprint.json'
  if (-not (Test-Path -LiteralPath $path -PathType Leaf)) { return $null }
  $record = Get-Content -LiteralPath $path -Raw | ConvertFrom-Json
  $files = [ordered]@{}
  foreach ($line in [IO.File]::ReadAllLines((Join-Path $Entry 'inputs.tsv'))) {
    $fields = $line.Split("`t")
    if ($fields.Count -ne 2) { throw "Malformed line in $Entry\inputs.tsv: $line" }
    $files[$fields[0]] = $fields[1]
  }
  $record | Add-Member -MemberType NoteProperty -Name files -Value $files
  return $record
}

function Get-RecordMap($Object) {
  $map = @{}
  if ($null -ne $Object) {
    if ($Object -is [Collections.IDictionary]) { foreach ($key in $Object.Keys) { $map[$key] = $Object[$key] } }
    else { foreach ($property in $Object.PSObject.Properties) { $map[$property.Name] = $property.Value } }
  }
  return $map
}

# Added, removed and changed inputs between two fingerprints, at most $Limit lines.
function Get-BundleInputChanges($Before, $After, [int]$Limit = 20) {
  $old = Get-RecordMap $Before.files
  $new = Get-RecordMap $After.files
  $changes = [Collections.Generic.List[string]]::new()
  if ($Before.unity -ne $After.unity) { $changes.Add("Unity $($Before.unity) -> $($After.unity)") }
  $keys = [Collections.Generic.SortedSet[string]]::new([StringComparer]::Ordinal)
  foreach ($key in @($old.Keys) + @($new.Keys)) { [void]$keys.Add($key) }
  foreach ($key in $keys) {
    if (-not $new.ContainsKey($key)) { $changes.Add("removed $key") }
    elseif (-not $old.ContainsKey($key)) { $changes.Add("added $key") }
    elseif ($old[$key] -ne $new[$key]) { $changes.Add("changed $key") }
  }
  if ($changes.Count -gt $Limit) { return @($changes | Select-Object -First $Limit) + "... and $($changes.Count - $Limit) more" }
  return @($changes)
}

# Every cached bundle file is present with its recorded hash, and nothing else is cached.
function Assert-BundleCacheIntact([string]$Entry, $Record) {
  $cached = Join-Path $Entry 'AssetBundles'
  $bundles = Get-RecordMap $Record.bundles
  if ($bundles.Count -eq 0) { throw "The bundle cache record $Entry\fingerprint.json lists no bundles; delete $Entry." }
  if (-not (Test-Path -LiteralPath $cached -PathType Container)) { throw "The bundle cache $Entry has no AssetBundles folder; delete $Entry." }
  $present = @(Get-ChildItem -LiteralPath $cached -Force)
  foreach ($item in $present) {
    if ($item.PSIsContainer -or -not $bundles.ContainsKey($item.Name)) { throw "The bundle cache $cached holds $($item.Name), which its record does not list; delete $Entry." }
  }
  foreach ($name in $bundles.Keys) {
    $path = Join-Path $cached $name
    if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-BundleFileHash $path) -ne $bundles[$name]) {
      throw "The cached bundle $path is missing or differs from its record; delete $Entry."
    }
  }
}

# True when the last verified build's bundles were built from exactly these inputs; says why otherwise.
function Test-BundleCacheHit([string]$Entry, $Inputs) {
  $record = Read-BundleCacheRecord $Entry
  if ($null -eq $record) {
    Write-Host "Asset bundles: no verified build of $($Inputs.mod) ($($Inputs.variant)) is cached; building them."
    return $false
  }
  if ($record.mod -ne $Inputs.mod -or $record.variant -ne $Inputs.variant) { throw "$Entry holds $($record.mod)/$($record.variant), not $($Inputs.mod)/$($Inputs.variant); delete it." }
  if ($record.fingerprint -ne $Inputs.fingerprint) {
    Write-Host "Asset bundles: their inputs changed since the last verified build; building them:"
    foreach ($line in Get-BundleInputChanges $record $Inputs) { Write-Host "  $line" }
    return $false
  }
  Assert-BundleCacheIntact $Entry $record
  Write-Host "Asset bundles: inputs unchanged since the verified build of $($record.storedAt) (fingerprint $($Inputs.fingerprint.Substring(0, 12))); reusing its bundles, building code only."
  return $true
}

# The cached AssetBundles folder into a package the official builder wrote without bundles.
function Install-CachedBundles([string]$Entry, [string]$Destination) {
  $record = Read-BundleCacheRecord $Entry
  if ($null -eq $record) { throw "No cached bundles at $Entry." }
  Assert-BundleCacheIntact $Entry $record
  if (Test-Path -LiteralPath $Destination) { throw "$Destination exists, but the official builder was told not to build bundles." }
  New-Item -ItemType Directory -Force -Path $Destination | Out-Null
  $bundles = Get-RecordMap $record.bundles
  foreach ($name in $bundles.Keys) {
    Copy-Item -LiteralPath (Join-Path (Join-Path $Entry 'AssetBundles') $name) -Destination (Join-Path $Destination $name)
    if ((Get-BundleFileHash (Join-Path $Destination $name)) -ne $bundles[$name]) { throw "Installing the cached $name into $Destination changed it." }
  }
}

# A reuse build ran Unity on the inputs it fingerprinted: if Unity changed one (an editor step re-authored an asset),
# the reused bundles may be stale. The cache entry is dropped so that the next build rebuilds them.
function Assert-BundleInputsUnchanged([string]$Entry, $Before, $After) {
  if ($Before.fingerprint -eq $After.fingerprint) { return }
  $changes = (Get-BundleInputChanges $Before $After) -join "`n  "
  if (Test-Path -LiteralPath $Entry) { Remove-Item -LiteralPath $Entry -Recurse -Force }
  throw "Unity changed bundle inputs during this code-only build, so the reused bundles may be stale:`n  $changes`nThe cache entry $Entry was removed; run the build again to rebuild the bundles."
}

# Stores a verified build's AssetBundles folder with the inputs it was built from, replacing the entry.
function Save-BundleCache([string]$Entry, $Inputs, [string]$Source) {
  $items = @(Get-ChildItem -LiteralPath $Source -Force)
  if ($items.Count -eq 0 -or @($items | Where-Object PSIsContainer).Count -ne 0) { throw "$Source must hold the bundle files only." }
  $staging = "$Entry.new"
  if (Test-Path -LiteralPath $staging) { Remove-Item -LiteralPath $staging -Recurse -Force }
  New-Item -ItemType Directory -Force -Path (Join-Path $staging 'AssetBundles') | Out-Null
  $bundles = [ordered]@{}
  foreach ($item in $items | Sort-Object Name) {
    $hash = Get-BundleFileHash $item.FullName
    $copy = Join-Path (Join-Path $staging 'AssetBundles') $item.Name
    Copy-Item -LiteralPath $item.FullName -Destination $copy
    if ((Get-BundleFileHash $copy) -ne $hash) { throw "Copying $($item.FullName) into the bundle cache changed it." }
    $bundles[$item.Name] = $hash
  }
  $record = [ordered]@{
    mod = $Inputs.mod; variant = $Inputs.variant; unity = $Inputs.unity; fingerprint = $Inputs.fingerprint
    storedAt = (Get-Date -Format o); inputCount = $Inputs.files.Count; bundles = $bundles
  }
  $utf8 = [Text.UTF8Encoding]::new($false)
  [IO.File]::WriteAllText((Join-Path $staging 'fingerprint.json'), ($record | ConvertTo-Json -Depth 3), $utf8)
  $lines = foreach ($key in $Inputs.files.Keys) { "$key`t$($Inputs.files[$key])" }
  [IO.File]::WriteAllLines((Join-Path $staging 'inputs.tsv'), [string[]]@($lines), $utf8)
  if (Test-Path -LiteralPath $Entry) { Remove-Item -LiteralPath $Entry -Recurse -Force }
  Move-Item -LiteralPath $staging -Destination $Entry
  Write-Host "Asset bundles: cached this verified build's bundles at $Entry (fingerprint $($Inputs.fingerprint.Substring(0, 12)))."
}

# For the verify scripts: the package's AssetBundles folder is byte for byte the cached one, and (with -Inputs) the
# cache was built from the current inputs. Returns the cache record.
function Assert-BundlesMatchCache([string]$Entry, [string]$Directory, $Inputs) {
  $record = Read-BundleCacheRecord $Entry
  if ($null -eq $record) { throw "No verified bundles are cached at $Entry; rebuild the package." }
  Assert-BundleCacheIntact $Entry $record
  $bundles = Get-RecordMap $record.bundles
  $present = @(Get-ChildItem -LiteralPath $Directory -Force)
  if ($present.Count -ne $bundles.Count -or @($present | Where-Object { $_.PSIsContainer -or -not $bundles.ContainsKey($_.Name) }).Count -ne 0) {
    throw "$Directory holds $(@($present.Name) -join ', '); the cached build holds $(@($bundles.Keys) -join ', ')."
  }
  foreach ($name in $bundles.Keys) {
    if ((Get-BundleFileHash (Join-Path $Directory $name)) -ne $bundles[$name]) { throw "$Directory\$name is not the cached bundle of fingerprint $($record.fingerprint)." }
  }
  if ($null -ne $Inputs -and $Inputs.fingerprint -ne $record.fingerprint) {
    throw "The bundle inputs changed since the cached bundles were built; rebuild the package:`n  " + ((Get-BundleInputChanges $record $Inputs) -join "`n  ")
  }
  return $record
}

# Per shader and graphics API, the variants ModShaderVariantStripping saw and kept (tools/unity), from a Unity log.
# A player build and the bundle build for the same API log identical lines; each distinct line counts once.
function Get-ShaderStrippingSummary([string]$Log) {
  $pattern = '^\[ModShaderVariantStripping\] (?<shader>\S+) \| .+ \| (?<stage>\S+) \| (?<api>\S+): (?<before>\d+) -> (?<after>\d+)'
  $totals = [ordered]@{}
  $seen = @{}
  foreach ($line in Get-Content -LiteralPath $Log) {
    if ($line -notmatch $pattern -or $seen.ContainsKey($line)) { continue }
    $seen[$line] = $true
    $key = "$($Matches.shader) ($($Matches.api))"
    if (-not $totals.Contains($key)) { $totals[$key] = @(0, 0) }
    $totals[$key] = @(($totals[$key][0] + [int]$Matches.before), ($totals[$key][1] + [int]$Matches.after))
  }
  foreach ($key in $totals.Keys) { "  $key`: $($totals[$key][0]) -> $($totals[$key][1]) variants" }
}
