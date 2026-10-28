#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using HarmonyLib;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.ModManagerScene;
using Timberborn.SingletonSystem;
using UnityEngine;
using UnityEngine.Profiling;

namespace DeepFrontier.Scripts {
  // Explicit diagnostic only (-deepFrontierMemoryTrace). Normal play patches nothing.
  //
  // - Every Deep Frontier lifecycle method (singleton Load/PostLoad/Unload, ticks,
  //   updates, entity initialization, parallel task Run) and every Deep Frontier Harmony
  //   prefix/postfix is wrapped: it records the method each thread is in, and Load/PostLoad
  //   (and the first calls of everything else) log process private bytes, the Mono heap
  //   and the Unity allocator totals before and after.
  // - A background thread samples private bytes every 200 ms and logs every 5 s, and at
  //   once with every thread's current method when private bytes moved by 256 MB.
  internal sealed class MemoryTraceModStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      if (Environment.GetCommandLineArgs().Contains(MemoryTrace.Flag)) MemoryTrace.Start();
    }
  }

  internal static class MemoryTrace {
    internal const string Flag = "-deepFrontierMemoryTrace";
    private const string Tag = "[DeepFrontier MemoryTrace]";
    private const long MB = 1024 * 1024;
    private const long JumpBytes = 256 * MB;
    private const long LoggedDeltaBytes = 16 * MB;
    private const int MeasuredCalls = 3;
    private const int Slots = 128;

    private static readonly HashSet<string> Lifecycle = new HashSet<string> {
      "Load", "PostLoad", "Unload", "UpdateSingleton", "LateUpdateSingleton", "Tick", "StartParallelTick", "Awake", "Start",
      "InitializeEntity", "PostInitializeEntity", "DeleteEntity", "OnEnterFinishedState", "OnExitFinishedState", "Run", "Save",
    };
    // Singleton Load/PostLoad/Unload: measured on every call.
    private static readonly HashSet<MethodBase> AlwaysMeasured = new HashSet<MethodBase>();
    private static readonly string[] Phases = new string[Slots];
    private static readonly string[] ThreadNames = new string[Slots];
    private static readonly Dictionary<MethodBase, int[]> Calls = new Dictionary<MethodBase, int[]>();
    [ThreadStatic] private static int _slot;
    private static int _nextSlot, _mainThread;
    private static readonly DateTime Started = DateTime.UtcNow;

    internal struct Snapshot {
      public string Previous;
      public bool Measured;
      public long Private, Mono, Unity, Graphics;
    }

    private static Harmony _harmony;
    private static HarmonyMethod _prefix, _postfix;

    internal static void Start() {
      _mainThread = Thread.CurrentThread.ManagedThreadId;
      _harmony = new Harmony("DeepFrontier.MemoryTrace");
      _prefix = new HarmonyMethod(typeof(MemoryTrace).GetMethod(nameof(Prefix), BindingFlags.Static | BindingFlags.NonPublic));
      _postfix = new HarmonyMethod(typeof(MemoryTrace).GetMethod(nameof(Postfix), BindingFlags.Static | BindingFlags.NonPublic));
      Debug.Log($"{Tag} wrapped {Wrap(Targets())} Deep Frontier methods");
      // Every scene's singleton lifecycle, and (wrapped when it starts) every singleton's
      // Load/PostLoad of every assembly, native and mods.
      var lifecycle = typeof(SingletonLifecycleService);
      Wrap(new[] { "LoadAll", "LoadSingletons", "LoadNonSingletons", "PostLoadSingletons", "PostLoadNonSingletons" }
        .Select(name => (MethodBase)AccessTools.Method(lifecycle, name)));
      _harmony.Patch(AccessTools.Method(lifecycle, "LoadSingletons"),
        new HarmonyMethod(typeof(MemoryTrace).GetMethod(nameof(WrapSingletons), BindingFlags.Static | BindingFlags.NonPublic)));
      // Every building tool preview (BottomBarPanel.Load creates one per placeable template).
      _harmony.Patch(AccessTools.Method(typeof(PreviewFactory), nameof(PreviewFactory.Create)),
        new HarmonyMethod(typeof(MemoryTrace).GetMethod(nameof(PreviewPrefix), BindingFlags.Static | BindingFlags.NonPublic)),
        new HarmonyMethod(typeof(MemoryTrace).GetMethod(nameof(PreviewPostfix), BindingFlags.Static | BindingFlags.NonPublic)));
      Log("mod start", null);
      new Thread(Watch) { IsBackground = true, Name = "DeepFrontier.MemoryTrace" }.Start();
    }

    private static int Wrap(IEnumerable<MethodBase> methods) {
      int patched = 0;
      var failed = new List<string>();
      foreach (var method in methods) {
        lock (Calls) {
          if (Calls.ContainsKey(method)) continue;
          Calls[method] = new int[1];
          if (IsSingletonLifecycle(method)) AlwaysMeasured.Add(method);
        }
        try { _harmony.Patch(method, _prefix, _postfix); patched++; } catch (Exception e) { failed.Add($"{Name(method)} ({e.GetType().Name}: {e.Message})"); }
      }
      if (failed.Count > 0) Debug.Log($"{Tag} not patchable: {string.Join("; ", failed)}");
      return patched;
    }

    // Prefix of SingletonLifecycleService.LoadSingletons: wraps every singleton's Load and PostLoad.
    private static void WrapSingletons(SingletonLifecycleService __instance) {
      var repository = (ISingletonRepository)AccessTools.Field(typeof(SingletonLifecycleService), "_singletonRepository").GetValue(__instance);
      var methods = new List<MethodBase>();
      foreach (var (contract, name) in new[] { (typeof(ILoadableSingleton), "Load"), (typeof(IPostLoadableSingleton), "PostLoad") }) {
        var singletons = (System.Collections.IEnumerable)typeof(ISingletonRepository).GetMethod(nameof(ISingletonRepository.GetSingletons))
          .MakeGenericMethod(contract).Invoke(repository, null);
        foreach (var singleton in singletons) {
          var map = singleton.GetType().GetInterfaceMap(contract);
          var method = map.TargetMethods[0];
          if (!method.IsAbstract && method.GetMethodBody() != null && !method.DeclaringType.ContainsGenericParameters) methods.Add(method);
        }
      }
      Debug.Log($"{Tag} wrapped {Wrap(methods.Distinct())} more singleton Load/PostLoad methods of this scene ({methods.Count} calls)");
      WrapDetails();
      Log("LoadSingletons start", null);
    }

    private static IEnumerable<MethodBase> Targets() {
      foreach (var type in typeof(MemoryTrace).Assembly.GetTypes()) {
        if (type.IsInterface || type.ContainsGenericParameters || type == typeof(MemoryTrace) || type == typeof(MemoryTraceModStarter)) continue;
        bool harmonyPatch = type.GetCustomAttributes(typeof(HarmonyPatch), true).Length > 0
          || (type.DeclaringType != null && type.DeclaringType.GetCustomAttributes(typeof(HarmonyPatch), true).Length > 0);
        foreach (var method in type.GetMethods(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly)) {
          if (method.IsAbstract || method.ContainsGenericParameters || method.GetMethodBody() == null) continue;
          bool patchMethod = method.IsStatic && (method.Name == "Prefix" || method.Name == "Postfix") && (harmonyPatch || type.Name.Contains("Patch"));
          bool lifecycle = !method.IsStatic && Lifecycle.Contains(method.Name);
          if (patchMethod || lifecycle) yield return method;
        }
      }
    }

    private static bool IsSingletonLifecycle(MethodBase method) {
      var type = method.DeclaringType;
      return type == typeof(SingletonLifecycleService) || method.GetParameters().Length == 0 && (
        (method.Name.EndsWith("Load") && typeof(ILoadableSingleton).IsAssignableFrom(type)) ||
        (method.Name.EndsWith("PostLoad") && typeof(IPostLoadableSingleton).IsAssignableFrom(type)) ||
        (method.Name.EndsWith("Unload") && typeof(IUnloadableSingleton).IsAssignableFrom(type)));
    }

    private static string Name(MethodBase method) => (method.DeclaringType?.Name ?? "?") + "." + method.Name;

    private static int Slot() {
      if (_slot == 0) {
        int slot = Interlocked.Increment(ref _nextSlot);
        _slot = slot < Slots ? slot : Slots - 1;
        var thread = Thread.CurrentThread;
        ThreadNames[_slot] = thread.ManagedThreadId == _mainThread ? "main" : (thread.Name ?? "thread") + "#" + thread.ManagedThreadId;
      }
      return _slot;
    }

    private static void Prefix(MethodBase __originalMethod, out Snapshot __state) {
      int slot = Slot();
      __state = new Snapshot { Previous = Phases[slot] };
      Phases[slot] = Name(__originalMethod);
      int calls;
      bool always;
      lock (Calls) { calls = ++Calls[__originalMethod][0]; always = AlwaysMeasured.Contains(__originalMethod); }
      if (always || calls <= MeasuredCalls) {
        __state.Measured = true;
        __state.Private = PrivateBytes();
        if (Thread.CurrentThread.ManagedThreadId == _mainThread) { __state.Mono = GC.GetTotalMemory(false); __state.Unity = Profiler.GetTotalAllocatedMemoryLong(); }
      }
    }

    private static void Postfix(MethodBase __originalMethod, Snapshot __state) {
      int slot = Slot();
      Phases[slot] = __state.Previous ?? "(native, after " + Name(__originalMethod) + ")";
      if (!__state.Measured) return;
      long privateBytes = PrivateBytes();
      bool main = Thread.CurrentThread.ManagedThreadId == _mainThread;
      long mono = main ? GC.GetTotalMemory(false) : 0, unity = main ? Profiler.GetTotalAllocatedMemoryLong() : 0;
      bool ours = __originalMethod.DeclaringType?.Assembly == typeof(MemoryTrace).Assembly || __originalMethod.DeclaringType == typeof(SingletonLifecycleService);
      if (!ours && Math.Abs(privateBytes - __state.Private) < LoggedDeltaBytes) return;
      Debug.Log($"{Tag} {Name(__originalMethod)} [{ThreadNames[slot]}] private {__state.Private / MB}->{privateBytes / MB} MB ({(privateBytes - __state.Private) / MB:+#;-#;0})"
        + (main ? $", mono {__state.Mono / MB}->{mono / MB} MB, unity allocated {__state.Unity / MB}->{unity / MB} MB" : ""));
    }

    // Model import and template instantiation steps, logged with the preview being created.
    private static bool _detailsWrapped;
    private static string _currentPreview;

    private static void WrapDetails() {
      if (_detailsWrapped) return;
      _detailsWrapped = true;
      var targets = new List<MethodBase>();
      void Add(Type type, string name) {
        foreach (var method in type.GetMethods(BindingFlags.Instance | BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly))
          if (method.Name == name && !method.IsAbstract && method.GetMethodBody() != null && !method.ContainsGenericParameters) targets.Add(method);
      }
      Add(typeof(Timberborn.Timbermesh.TimbermeshImporter), "CreateMeshes");
      Add(typeof(Timberborn.Timbermesh.TimbermeshImporter), "PostprocessModel");
      Add(typeof(Timberborn.Timbermesh.TimbermeshReader), "ReadFromStream");
      Add(typeof(Timberborn.TemplateInstantiation.TemplateInstantiator), "Instantiate");
      Add(typeof(BlockObject), "MarkAsPreviewAndInitialize");
      foreach (var assembly in AppDomain.CurrentDomain.GetAssemblies()) {
        Type[] types;
        try { types = assembly.GetTypes(); } catch (ReflectionTypeLoadException e) { types = e.Types.Where(t => t != null).ToArray(); }
        foreach (var type in types)
          if (!type.IsInterface && !type.IsAbstract && typeof(Timberborn.Timbermesh.IModelPostprocessor).IsAssignableFrom(type)) Add(type, "Postprocess");
      }
      var prefix = new HarmonyMethod(typeof(MemoryTrace).GetMethod(nameof(DetailPrefix), BindingFlags.Static | BindingFlags.NonPublic));
      var postfix = new HarmonyMethod(typeof(MemoryTrace).GetMethod(nameof(DetailPostfix), BindingFlags.Static | BindingFlags.NonPublic));
      var names = new List<string>();
      foreach (var method in targets) {
        try { _harmony.Patch(method, prefix, postfix); names.Add(Name(method)); } catch (Exception e) { Debug.Log($"{Tag} not patchable: {Name(method)} ({e.Message})"); }
      }
      Debug.Log($"{Tag} detail methods: {string.Join(", ", names)}");
    }

    private static void DetailPrefix(out Snapshot __state) {
      bool main = Thread.CurrentThread.ManagedThreadId == _mainThread;
      __state = new Snapshot { Measured = main, Private = PrivateBytes() };
      if (main) { __state.Mono = GC.GetTotalMemory(false); __state.Unity = Profiler.GetTotalAllocatedMemoryLong(); }
    }

    private static void DetailPostfix(MethodBase __originalMethod, Snapshot __state) {
      if (!__state.Measured || _currentPreview == null) return;
      long privateBytes = PrivateBytes(), mono = GC.GetTotalMemory(false), unity = Profiler.GetTotalAllocatedMemoryLong();
      if (privateBytes - __state.Private < 4 * MB && unity - __state.Unity < 4 * MB) return;
      Debug.Log($"{Tag}   {_currentPreview} {Name(__originalMethod)}: private {(privateBytes - __state.Private) / MB:+#;-#;0} MB, "
        + $"mono {(mono - __state.Mono) / MB:+#;-#;0}, unity allocated {(unity - __state.Unity) / MB:+#;-#;0}");
    }

    private static long _previewTotal;
    private static int _previews;

    private static void PreviewPrefix(PlaceableBlockObjectSpec template, out Snapshot __state) {
      _currentPreview = template.Blueprint.Name;
      __state = new Snapshot { Private = PrivateBytes(), Mono = GC.GetTotalMemory(false), Unity = Profiler.GetTotalAllocatedMemoryLong(),
        Graphics = Profiler.GetAllocatedMemoryForGraphicsDriver() };
    }

    private static void PreviewPostfix(Snapshot __state, Preview __result) {
      long privateBytes = PrivateBytes(), mono = GC.GetTotalMemory(false), unity = Profiler.GetTotalAllocatedMemoryLong(),
        graphics = Profiler.GetAllocatedMemoryForGraphicsDriver();
      _previewTotal += privateBytes - __state.Private; _previews++;
      _currentPreview = null;
      Debug.Log($"{Tag} preview {__result.GameObject.name}: private {(privateBytes - __state.Private) / MB:+#;-#;0} MB, mono {(mono - __state.Mono) / MB:+#;-#;0}, "
        + $"unity allocated {(unity - __state.Unity) / MB:+#;-#;0}, graphics driver {(graphics - __state.Graphics) / MB:+#;-#;0} MB; "
        + $"{_previews} previews, {_previewTotal / MB} MB in previews so far; released {PrefabMeshRelease.ReleasedMeshes} meshes, {PrefabMeshRelease.ReleasedVertices / 1000}k vertices, shared {PrefabMeshRelease.SharedMeshes}, {PrefabMeshRelease.Collections} collections");
    }

    // Main thread only (Unity profiler API).
    internal static void Log(string what, string phase) {
      Debug.Log($"{Tag} {what}: private {PrivateBytes() / MB} MB, mono heap {Profiler.GetMonoHeapSizeLong() / MB} MB (used {GC.GetTotalMemory(false) / MB}), "
        + $"unity allocated {Profiler.GetTotalAllocatedMemoryLong() / MB} MB, reserved {Profiler.GetTotalReservedMemoryLong() / MB} MB, "
        + $"graphics driver {Profiler.GetAllocatedMemoryForGraphicsDriver() / MB} MB" + (phase != null ? ", " + phase : ""));
    }

    private static void Watch() {
      long logged = PrivateBytes(), peak = logged;
      DateTime lastLog = DateTime.UtcNow;
      while (true) {
        Thread.Sleep(200);
        long now = PrivateBytes();
        if (now > peak) peak = now;
        bool jump = Math.Abs(now - logged) >= JumpBytes;
        if (!jump && (DateTime.UtcNow - lastLog).TotalSeconds < 5) continue;
        var phases = new List<string>();
        for (int i = 1; i < Slots; i++) if (Phases[i] != null) phases.Add(ThreadNames[i] + ": " + Phases[i]);
        Debug.Log($"{Tag} {(jump ? "JUMP" : "sample")} t={(DateTime.UtcNow - Started).TotalSeconds:F1}s private {logged / MB}->{now / MB} MB (peak {peak / MB}), "
          + $"in [{string.Join(" | ", phases)}]");
        logged = now; lastLog = DateTime.UtcNow;
      }
    }

    internal static long PrivateBytes() => ProcessMemory.PrivateBytes();
  }
}
#endif
