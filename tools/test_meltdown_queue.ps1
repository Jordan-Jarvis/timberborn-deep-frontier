#Requires -Version 7
$ErrorActionPreference = 'Stop'
$source = Get-Content -LiteralPath (Join-Path $PSScriptRoot '../src/DeepFrontier/Scripts/Meltdown/MeltdownService.cs') -Raw
# Extract the entire contiguous production queue implementation, not a rewritten
# algorithm. Native deletion contracts are checked by validate_meltdown_content.
$start = $source.IndexOf('    public void Request(ReactorCore core) {')
$end = $source.IndexOf('    private void Execute(ReactorCore core) {')
if ($start -lt 0 -or $end -le $start) { throw 'Meltdown queue method boundaries changed; update the harness' }
$methods = $source.Substring($start, $end - $start)
$project = Join-Path $PSScriptRoot 'compile-check/meltdown-queue'
New-Item -ItemType Directory -Path (Join-Path $project 'obj') -Force | Out-Null
$generated = "namespace DeepFrontier.Scripts.Meltdown { internal sealed partial class MeltdownService {`n$methods`n} }"
Set-Content -LiteralPath (Join-Path $project 'obj/MeltdownQueue.generated.cs') -Value $generated -Encoding utf8
& dotnet run --project (Join-Path $project 'MeltdownQueueHarness.csproj')
if ($LASTEXITCODE -ne 0) { throw 'Meltdown queue regression failed' }
