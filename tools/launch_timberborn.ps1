# Unattended Timberborn launch for the marked acceptance launchers (tools/start_*.ps1).
#
# Starts Timberborn.exe directly with the Steam app id in its environment instead of
# Steam.exe -applaunch, and always passes the native -skipModManager argument:
# - Timberborn.ModManagerSceneUI.ModManagerScenePanel.Awake shows the "Mods" screen (OK
#   button) whenever mods are installed, unless the command line has skipModManager; it
#   then loads the enabled mods exactly as the OK button does. This screen runs before any
#   mod code is loaded, so the mod cannot dismiss it.
# - Timberborn.SteamStoreSystem.SteamManager calls SteamAPI.RestartAppIfNecessary(1062090);
#   with SteamAppId set it connects to the running Steam client instead of relaunching.
# See docs/acceptance-runs.md for the procedure and the observed evidence.
param(
  # Game arguments after the executable, including '-logFile' and the quoted log path.
  [Parameter(Mandatory=$true)][string[]]$Arguments
)
$ErrorActionPreference = 'Stop'
$appId = '1062090'
. (Join-Path $PSScriptRoot 'DevEnvironment.ps1')
$game = (Get-DevEnvironment 'gameRoot').gameRoot
$exe = Join-Path $game 'Timberborn.exe'
if (-not (Test-Path -LiteralPath $exe)) { throw "Timberborn.exe not found at $exe" }
if (Get-Process -Name Timberborn -ErrorAction SilentlyContinue) { throw 'The previous Timberborn process must exit first.' }
if (-not (Get-Process -Name steam -ErrorAction SilentlyContinue)) {
  throw 'Steam must be running: the direct launch connects to the running Steam client.'
}
if ($Arguments -contains '-skipModManager') { throw 'Pass game arguments only; -skipModManager is added here.' }
$logIndex = [array]::IndexOf($Arguments, '-logFile')
if ($logIndex -lt 0 -or $logIndex -eq $Arguments.Count - 1) { throw 'Acceptance launches must pass -logFile and its quoted path.' }
$log = $Arguments[$logIndex + 1].Trim('"')
# Unity truncates the -logFile at startup anyway; removing it first lets
# watch_acceptance_log.ps1 treat any log it finds as this launch's.
if (Test-Path -LiteralPath $log) { Remove-Item -LiteralPath $log; Write-Output "Removed the previous $log" }
$previous = @{ SteamAppId = $env:SteamAppId; SteamGameId = $env:SteamGameId }
try {
  $env:SteamAppId = $appId
  $env:SteamGameId = $appId
  $process = Start-Process -FilePath $exe -WorkingDirectory $game -ArgumentList (@('-skipModManager') + $Arguments) -PassThru
} finally {
  $env:SteamAppId = $previous.SteamAppId
  $env:SteamGameId = $previous.SteamGameId
}
Write-Output "Started Timberborn.exe (pid $($process.Id)) with -skipModManager and SteamAppId $appId."
