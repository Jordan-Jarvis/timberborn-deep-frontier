using System;
using System.IO;
using System.Linq;
using System.Runtime.InteropServices;
using Bindito.Core;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.MapRepositorySystem;
using Timberborn.SingletonSystem;
using Timberborn.TimeSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit test launch only (-deepFrontierLoadAcceptance plus one of):
  //   -deepFrontierLoadSave "<full path of a .timber>"   load that exact save (it must lie in the
  //       native save repository; tools/start_memory_load.ps1 loads only copies in "Memory Test")
  //   -deepFrontierNewGame "user:<map>"|"builtin:<map>"   start an Iron Teeth new game on that map
  //       (settlement "Memory Test")
  // optionally with -deepFrontierSaveAs "<save name>" (saved into "Memory Test" at the end).
  // The main-menu IndustrialAcceptanceLoader starts the game. In the game scene this probe runs
  // it at speed 1 for RunSeconds of unpaused game time, logging process private bytes, then
  // logs COMPLETE. Normal play binds nothing.
  [Context("Game")]
  public sealed class MemoryLoadProbeConfigurator : Configurator {
    protected override void Configure() {
      if (MemoryLoadProbe.SavePath() != null || MemoryLoadProbe.NewGameMap() != null) Bind<MemoryLoadProbe>().AsSingleton();
    }
  }

  public sealed class MemoryLoadProbe : IUpdatableSingleton {
    internal const string Flag = "-deepFrontierLoadSave";
    internal const string NewGameFlag = "-deepFrontierNewGame";
    internal const string SaveAsFlag = "-deepFrontierSaveAs";
    internal const string TestSettlement = "Memory Test";
    private const string Tag = "[DeepFrontier MemoryLoad]";
    internal const string RunSecondsFlag = "-deepFrontierRunSeconds";
    // Game seconds to run (default 180); -deepFrontierRunSeconds N runs longer, e.g. a restaurant day.
    private static readonly float RunSeconds = RunSecondsArgument();
    private static float RunSecondsArgument() {
      var args = Environment.GetCommandLineArgs();
      int i = Array.IndexOf(args, RunSecondsFlag);
      if (i < 0) return 180f;
      if (i + 1 >= args.Length || !float.TryParse(args[i + 1], System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out var seconds) || !(seconds > 0f))
        throw new InvalidOperationException(RunSecondsFlag + " needs a positive number of game seconds");
      return seconds;
    }
    private const float StallSeconds = 120f;
    private const long MB = 1024 * 1024;
    private readonly SpeedManager _speed;
    private readonly GameSaver _saver;
    private readonly GameSaveRepository _saves;
    private int _frame;
    private float _gameSeconds, _nextLog, _stalled;
    private long _peak;
    private bool _finished;

    public MemoryLoadProbe(SpeedManager speed, GameSaver saver, GameSaveRepository saves) { _speed = speed; _saver = saver; _saves = saves; }

    // The value after a test flag, or null without the flag. Requires the acceptance launch
    // flag, so the panel dismisser and loader are bound with it.
    private static string Argument(string flag) {
      var args = Environment.GetCommandLineArgs();
      int index = Array.IndexOf(args, flag);
      if (index < 0) return null;
      if (!args.Contains("-deepFrontierLoadAcceptance")) throw new InvalidOperationException($"{flag} requires -deepFrontierLoadAcceptance");
      if (index == args.Length - 1) throw new InvalidOperationException($"{flag} must be followed by its value");
      return args[index + 1].Trim('"');
    }

    internal static string SavePath() => Argument(Flag) is string path ? Path.GetFullPath(path) : null;
    internal static string NewGameMap() => Argument(NewGameFlag);

    internal static SaveReference Find(GameSaveRepository saves, string path) {
      if (!File.Exists(path)) throw new FileNotFoundException($"{Flag}: no save at {path}", path);
      var matches = saves.GetAllSaves().Where(save => string.Equals(Path.GetFullPath(Path.Combine(saves.DefaultSaveDirectory,
        saves.SettlementReferenceIntoDirectoryName(save.SettlementReference), saves.SaveNameToFileName(save))), path,
        StringComparison.OrdinalIgnoreCase)).ToList();
      if (matches.Count != 1)
        throw new InvalidOperationException($"{Flag}: {path} matches {matches.Count} saves in the native repository {saves.DefaultSaveDirectory}");
      return matches[0];
    }

    internal static MapFileReference Map(MapRepository maps, string value) {
      if (value.StartsWith("user:", StringComparison.Ordinal)) {
        string name = value.Substring(5);
        if (!maps.GetUserMapNames().Contains(name)) throw new InvalidOperationException($"{NewGameFlag}: no user map named {name}");
        return MapFileReference.FromUserFolder(name);
      }
      if (value.StartsWith("builtin:", StringComparison.Ordinal)) {
        string name = value.Substring(8);
        if (!maps.GetBuiltinMapNames().Contains(name))
          throw new InvalidOperationException($"{NewGameFlag}: no built-in map named {name} (have {string.Join(", ", maps.GetBuiltinMapNames())})");
        return MapFileReference.FromResource(name);
      }
      throw new InvalidOperationException($"{NewGameFlag} takes user:<map> or builtin:<map>, not {value}");
    }

    public void UpdateSingleton() {
      if (_finished) return;
      long privateBytes = PrivateBytes();
      if (privateBytes > _peak) _peak = privateBytes;
      // Startup panels are dismissed before frame 60 (AcceptanceStartupPanels).
      if (++_frame == 60) Debug.Log($"{Tag} loaded; private {privateBytes / MB} MB; running {RunSeconds} s of game time at speed 1");
      if (_frame < 60) return;
      if (_speed.CurrentSpeed <= 0f) {
        _speed.ChangeSpeed(1f);
        _stalled += Time.unscaledDeltaTime;
        if (_stalled > StallSeconds) {
          _finished = true;
          Debug.LogError($"{Tag} FAILED the game stayed paused for {StallSeconds} s (a panel or the starting-location choice holds it); private {privateBytes / MB} MB, peak {_peak / MB} MB");
        }
        return;
      }
      _stalled = 0f;
      _gameSeconds += Time.unscaledDeltaTime * _speed.CurrentSpeed;
      if (_gameSeconds >= _nextLog) {
        Debug.Log($"{Tag} t={_gameSeconds:F0}s private {privateBytes / MB} MB (peak {_peak / MB} MB)");
        _nextLog += 10f;
      }
      if (_gameSeconds < RunSeconds) return;
      _finished = true;
      _speed.ChangeSpeed(0f);
      string result = $"{RunSeconds} s of game time; private {privateBytes / MB} MB, peak {_peak / MB} MB";
      if (Argument(SaveAsFlag) is string saveName) {
        var save = new SaveReference(saveName, _saves.DirectoryNameIntoSettlementReference(TestSettlement));
        _saver.QueueSave(save, () => Debug.Log($"{Tag} COMPLETE {result}; saved {save}"));
      } else {
        Debug.Log($"{Tag} COMPLETE {result}");
      }
    }

    private static long PrivateBytes() => ProcessMemory.PrivateBytes();
  }

  // Process private bytes (commit charge), as Task Manager and tools/sample_timberborn_memory.ps1 read it.
  internal static class ProcessMemory {
    [StructLayout(LayoutKind.Sequential)]
    private struct ProcessMemoryCountersEx {
      public uint cb, PageFaultCount;
      public UIntPtr PeakWorkingSetSize, WorkingSetSize, QuotaPeakPagedPoolUsage, QuotaPagedPoolUsage, QuotaPeakNonPagedPoolUsage,
        QuotaNonPagedPoolUsage, PagefileUsage, PeakPagefileUsage, PrivateUsage;
    }

    [DllImport("kernel32.dll")] private static extern IntPtr GetCurrentProcess();
    [DllImport("kernel32.dll", SetLastError = true)] private static extern bool K32GetProcessMemoryInfo(IntPtr process, out ProcessMemoryCountersEx counters, uint size);

    internal static long PrivateBytes() {
      if (!K32GetProcessMemoryInfo(GetCurrentProcess(), out var counters, (uint)Marshal.SizeOf<ProcessMemoryCountersEx>()))
        throw new InvalidOperationException("K32GetProcessMemoryInfo failed: " + Marshal.GetLastWin32Error());
      return (long)counters.PrivateUsage.ToUInt64();
    }
  }
}
