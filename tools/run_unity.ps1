# Runs the Unity editor through tools/UnityProcess.ps1 for callers outside PowerShell (tools/setup_dev.py) and waits
# for it; the exit code is the editor's.
#   powershell -NoProfile -ExecutionPolicy Bypass -File tools/run_unity.ps1 <Unity.exe> -batchmode -quit -projectPath <path> ...
# Every argument after the editor goes to Unity as given; one with a space is quoted.
$ErrorActionPreference = 'Stop'
if ($args.Count -lt 2) { throw 'Usage: run_unity.ps1 <Unity.exe> <Unity arguments>' }
. (Join-Path $PSScriptRoot 'UnityProcess.ps1')
$unityArguments = foreach ($argument in $args[1..($args.Count - 1)]) {
  $text = [string]$argument
  if ($text.Contains('"')) { throw "A Unity argument holds a double quote: $text" }
  if ($text -match '\s') { '"' + $text + '"' } else { $text }
}
$process = Start-UnityProcess -FilePath ([string]$args[0]) -ArgumentList @($unityArguments) -Hidden
$process.WaitForExit()
exit $process.ExitCode
