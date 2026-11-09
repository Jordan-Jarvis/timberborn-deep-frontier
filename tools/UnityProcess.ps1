# Starts the Unity editor for this repository's scripts: every Unity launch goes through Start-UnityProcess.
#   . (Join-Path $PSScriptRoot 'UnityProcess.ps1')
#   $process = Start-UnityProcess -FilePath $unity -ArgumentList @('-batchmode', ...) -Hidden
#   $process.WaitForExit(); $process.ExitCode
# A cold shader compile once saturated every core for over half an hour and froze the machine. The editor is
# therefore created suspended, at below-normal priority and with an affinity mask that leaves this session's two
# lowest logical processors free (with SMT, one whole physical core), and only then resumed. Child processes inherit
# a below-normal priority class and the affinity mask, so every shader compiler, Bee and compiler server the editor
# starts runs the same way from its first instruction. tools/test_unity_build_tools.ps1 checks this with a
# harmless process tree. Works in Windows PowerShell 5.1 and PowerShell 7.

if (-not ('UnityProcessLauncher' -as [type])) {
  Add-Type -TypeDefinition @'
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Text;

public static class UnityProcessLauncher {
  [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Unicode)]
  private struct StartupInfo {
    public int cb; public string lpReserved; public string lpDesktop; public string lpTitle;
    public int dwX, dwY, dwXSize, dwYSize, dwXCountChars, dwYCountChars, dwFillAttribute, dwFlags;
    public short wShowWindow, cbReserved2;
    public IntPtr lpReserved2, hStdInput, hStdOutput, hStdError;
  }

  [StructLayout(LayoutKind.Sequential)]
  private struct ProcessInformation { public IntPtr hProcess, hThread; public int dwProcessId, dwThreadId; }

  [DllImport("kernel32.dll", SetLastError = true, CharSet = CharSet.Unicode)]
  private static extern bool CreateProcess(string application, StringBuilder commandLine, IntPtr processAttributes,
    IntPtr threadAttributes, bool inheritHandles, uint flags, IntPtr environment, string directory,
    ref StartupInfo startupInfo, out ProcessInformation processInformation);
  [DllImport("kernel32.dll", SetLastError = true)] private static extern bool SetProcessAffinityMask(IntPtr process, UIntPtr mask);
  [DllImport("kernel32.dll", SetLastError = true)] private static extern uint ResumeThread(IntPtr thread);
  [DllImport("kernel32.dll", SetLastError = true)] private static extern bool TerminateProcess(IntPtr process, uint exitCode);
  [DllImport("kernel32.dll", SetLastError = true)] private static extern bool CloseHandle(IntPtr handle);

  private const uint CreateSuspended = 0x00000004, BelowNormalPriorityClass = 0x00004000;
  private const int StartfUseShowWindow = 0x00000001;

  // commandLine is the complete argument string after the quoted executable, exactly as Start-Process joins it.
  public static Process Start(string file, string commandLine, ulong affinity, bool hidden, string directory) {
    var startup = new StartupInfo();
    startup.cb = Marshal.SizeOf(typeof(StartupInfo));
    if (hidden) { startup.dwFlags = StartfUseShowWindow; startup.wShowWindow = 0; }
    var command = new StringBuilder("\"" + file + "\" " + commandLine);
    ProcessInformation info;
    if (!CreateProcess(file, command, IntPtr.Zero, IntPtr.Zero, false, CreateSuspended | BelowNormalPriorityClass,
        IntPtr.Zero, directory, ref startup, out info))
      throw new Win32Exception(Marshal.GetLastWin32Error(), "CreateProcess failed for " + file);
    try {
      if (!SetProcessAffinityMask(info.hProcess, new UIntPtr(affinity)))
        throw new Win32Exception(Marshal.GetLastWin32Error(), "SetProcessAffinityMask failed for " + file);
      Process process = Process.GetProcessById(info.dwProcessId);
      // The Process object opens its own handle while the process is suspended, so WaitForExit and ExitCode work.
      IntPtr own = process.Handle;
      if (ResumeThread(info.hThread) == uint.MaxValue)
        throw new Win32Exception(Marshal.GetLastWin32Error(), "ResumeThread failed for " + file);
      return process;
    } catch {
      TerminateProcess(info.hProcess, 1);
      throw;
    } finally {
      CloseHandle(info.hThread);
      CloseHandle(info.hProcess);
    }
  }
}
'@
}

# This session's logical processors without its two lowest.
function Get-UnityAffinityMask {
  $available = [UInt64][Diagnostics.Process]::GetCurrentProcess().ProcessorAffinity.ToInt64()
  $mask = [UInt64]0
  $free = 0
  for ($bit = 0; $bit -lt 64; $bit++) {
    $processor = [UInt64]1 -shl $bit
    if (($available -band $processor) -eq 0) { continue }
    if ($free -lt 2) { $free++ } else { $mask = $mask -bor $processor }
  }
  if ($mask -eq 0) { throw ('Unity needs more than two logical processors so that two stay free (this session has mask 0x{0:X}).' -f $available) }
  return $mask
}

function Start-UnityProcess {
  param(
    [Parameter(Mandatory = $true)][string]$FilePath,
    [Parameter(Mandatory = $true)][string[]]$ArgumentList,
    [switch]$Hidden
  )
  if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) { throw "The Unity editor is missing: $FilePath" }
  $directory = (Get-Location -PSProvider FileSystem).ProviderPath
  $mask = Get-UnityAffinityMask
  return [UnityProcessLauncher]::Start($FilePath, ($ArgumentList -join ' '), $mask, [bool]$Hidden, $directory)
}
