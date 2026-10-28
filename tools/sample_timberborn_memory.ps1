# Samples the running Timberborn process's memory every few seconds into a CSV
# and closes the game if it exceeds a ceiling, so a runaway leak cannot push the
# machine into the page file (build 126/127 sessions reached ~21 GB and died).
#
#   powershell -File tools/sample_timberborn_memory.ps1 -Out outputs/memory-127.csv -CeilingGB 10
param(
  [Parameter(Mandatory=$true)][string]$Out,
  [double]$CeilingGB = 10,
  [int]$IntervalSeconds = 2,
  [int]$Minutes = 30
)
$ErrorActionPreference = 'Stop'
"time,privateGB,workingSetGB,virtualGB" | Set-Content -LiteralPath $Out -Encoding utf8
$deadline = (Get-Date).AddMinutes($Minutes)
while ((Get-Date) -lt $deadline) {
  $process = Get-Process -Name Timberborn -ErrorAction SilentlyContinue | Select-Object -First 1
  if ($process) {
    $private = $process.PrivateMemorySize64 / 1GB
    "{0:HH:mm:ss},{1:N2},{2:N2},{3:N2}" -f (Get-Date), $private, ($process.WorkingSet64 / 1GB), ($process.VirtualMemorySize64 / 1GB) |
      Add-Content -LiteralPath $Out -Encoding utf8
    if ($private -gt $CeilingGB) {
      Add-Content -LiteralPath $Out -Value ("{0:HH:mm:ss},CEILING {1} GB exceeded; game closed" -f (Get-Date), $CeilingGB) -Encoding utf8
      Stop-Process -Id $process.Id -Force
      break
    }
  }
  Start-Sleep -Seconds $IntervalSeconds
}
