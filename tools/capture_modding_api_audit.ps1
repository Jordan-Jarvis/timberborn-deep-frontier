$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$workshopRoot = 'C:\Program Files (x86)\Steam\steamapps\workshop\content\1062090'
$packageIds = @('3578009707', '3430626620', '3612110827', '3283831040',
    '3639961044', '3442389397', '3337906807', '3434034047', '3416879061',
    '3801726769', '3815376360', '3766893705', '3286476486')
$packages = foreach ($id in $packageIds) {
    $packageRoot = Join-Path $workshopRoot "$id\version-1.1"
    $manifestPath = Join-Path $packageRoot 'manifest.json'
    $manifest = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
    $dlls = @(Get-ChildItem -LiteralPath $packageRoot -Filter '*.dll' -Recurse -File | Sort-Object FullName)
    if ($dlls.Count -eq 0) { throw "No DLLs in $packageRoot" }
    [ordered]@{
        workshopId = $id
        workshopUrl = "https://steamcommunity.com/sharedfiles/filedetails/?id=$id"
        packageDirectory = $packageRoot
        manifest = $manifest
        manifestSha256 = (Get-FileHash -LiteralPath $manifestPath -Algorithm SHA256).Hash
        dlls = @($dlls | ForEach-Object {
            [ordered]@{
                path = [IO.Path]::GetRelativePath($packageRoot, $_.FullName)
                sha256 = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
            }
        })
    }
}
$sourceRoot = Join-Path $projectRoot 'vendor\datvm-timberborn-mods'
$sourceCommit = & git -C $sourceRoot rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify downloaded source revision' }
$capture = [ordered]@{
    capturedAt = (Get-Date).ToString('o')
    gameVersion = '1.1.2.8'
    scope = 'Installed files and declared manifests; installation does not imply enabled or integration-tested.'
    downloadedSource = [ordered]@{
        repository = 'https://github.com/datvm/TimberbornMods'
        commit = $sourceCommit
        path = $sourceRoot
        license = 'MIT; retained in source checkout'
        authority = 'Author documentation/examples. Installed DLLs are the authority for exact callable signatures.'
    }
    packages = @($packages)
}
$capture | ConvertTo-Json -Depth 12 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'modding_api_audit_1_1.json') -Encoding utf8

$hoomanRoot = Join-Path $projectRoot 'vendor\hooman-stairs-package\extracted\Hooman Stairs\Version-1.1'
$hoomanDll = @(Get-ChildItem -LiteralPath $hoomanRoot -Filter 'hoomanstairs.dll' -Recurse -File)
if ($hoomanDll.Count -ne 1) { throw 'Expected one Hooman Stairs assembly' }
$hoomanCommit = & git -C (Join-Path $projectRoot 'vendor\hooman-stairs') rev-parse HEAD
if ($LASTEXITCODE -ne 0) { throw 'Cannot identify Hooman source revision' }
[ordered]@{
    capturedAt = (Get-Date).ToString('o')
    workshopId = '3682012904'
    workshopUrl = 'https://steamcommunity.com/sharedfiles/filedetails/?id=3682012904'
    status = 'Downloaded for inspection; not installed, enabled or required by Deep Frontier'
    manifest = Get-Content -LiteralPath (Join-Path $hoomanRoot 'manifest.json') -Raw | ConvertFrom-Json
    workshopRequiredItems = @('Harmony', 'Vertical Nav Mesh (3631491885)')
    dependencyDifference = 'Workshop additionally lists Vertical Nav Mesh. Preserve the package MinVersion field as authored; do not silently rewrite it to MinimumVersion.'
    downloadUrl = 'https://raw.githubusercontent.com/calloatti/ModZips/main/Hooman%20Stairs_2.0.2.zip'
    zipSha256 = (Get-FileHash -LiteralPath (Join-Path $projectRoot 'vendor\hooman-stairs-package\Hooman Stairs_2.0.2.zip') -Algorithm SHA256).Hash
    dllSha256 = (Get-FileHash -LiteralPath $hoomanDll[0].FullName -Algorithm SHA256).Hash
    repository = 'https://github.com/calloatti/Hooman-Stairs'
    sourceCommit = $hoomanCommit
    evidence = 'outputs/hooman-stairs-2.0.2/hoomanstairs.decompiled.cs'
} | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'hooman_stairs_dependency_1_1.json') -Encoding utf8
Write-Output "Captured $($packages.Count) installed API/transport packages and the downloaded Hooman Stairs candidate."
