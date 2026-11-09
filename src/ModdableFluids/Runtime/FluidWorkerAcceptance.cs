using System;
using System.Collections;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.CoreUI;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.GameSceneLoading;
using Timberborn.MainMenuSceneLoading;
using Timberborn.MapIndexSystem;
using Timberborn.MapRepositorySystem;
using Timberborn.Modding;
using Timberborn.SettlementNameSystem;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using ModdableFluids;
using ModdableFluids.GameBridge.Prototype;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Persistence.Prototype;
using ModdableFluids.Transport.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  internal static class WorkerAcceptanceRun {
    internal const string Flag = "-moddableFluidsWorkerAcceptance";
    /// <summary>With the worker flag: one world saved natively, then reloaded and compared bit for bit.</summary>
    internal const string SaveFlag = "-moddableFluidsSaveAcceptance";
    internal const string Map = "Moddable Fluids Worker Fixture";
    internal const string SaveName = "Moddable Fluids save acceptance";
    internal static bool Enabled => Environment.GetCommandLineArgs().Contains(Flag);
    internal static bool SaveMode => Environment.GetCommandLineArgs().Contains(SaveFlag);
    internal static string Settlement => SaveMode ? "Moddable Fluids Save Acceptance" : "Moddable Fluids Worker Acceptance";
    internal static int Attached, Detached;
    internal static bool StartingWorld, Reloading;
    internal static SaveReference SavedReference;
    internal static string SavedDigest;
    internal static string[] SavedProviderStates;
    internal static readonly List<object> Worlds = new List<object>();
    internal static string ReportPath {
      get {
        var args = Environment.GetCommandLineArgs(); int index = Array.IndexOf(args, "-moddableFluidsReport");
        if (index < 0 || index + 1 == args.Length) throw new InvalidOperationException("Worker acceptance requires -moddableFluidsReport <absolute path>");
        return Path.GetFullPath(args[index + 1]);
      }
    }
    internal static void Require(bool value, string message) { if (!value) throw new InvalidOperationException("[ModdableFluids Acceptance] " + message); }
  }

  [Context("MainMenu")]
  public sealed class FluidAcceptanceMenuConfigurator : Configurator {
    protected override void Configure() { if (WorkerAcceptanceRun.Enabled) Bind<FluidAcceptanceMenu>().AsSingleton(); }
  }
  public sealed class FluidAcceptanceMenu : IUpdatableSingleton {
    private readonly GameSceneLoader _loader;
    private readonly MapRepository _maps;
    private readonly ModRepository _mods;
    private readonly GameSaveRepository _saves;
    private int _frame;
    public FluidAcceptanceMenu(GameSceneLoader loader, MapRepository maps, ModRepository mods, GameSaveRepository saves) {
      _loader = loader; _maps = maps; _mods = mods; _saves = saves;
    }
    public void UpdateSingleton() {
      if (++_frame != 30) return;
      WorkerAcceptanceRun.Require(!NativeTransportHooks.HasActiveOwner && WorkerAcceptanceRun.Attached == WorkerAcceptanceRun.Detached, "Main menu retained a game-scene transport owner");
      WorkerAcceptanceRun.Require(WorkerAcceptanceRun.Attached == 0 || ModdableFluidsEntry.Host.ActiveScene == null, "Main menu retained an active provider scene");
      if (WorkerAcceptanceRun.SaveMode && WorkerAcceptanceRun.Worlds.Count == 1) {
        WorkerAcceptanceRun.Require(WorkerAcceptanceRun.SavedReference != null && WorkerAcceptanceRun.SavedDigest != null, "The first world finished without its native save");
        Debug.Log("[ModdableFluids Acceptance] Reloading " + WorkerAcceptanceRun.SavedReference);
        WorkerAcceptanceRun.StartingWorld = true; WorkerAcceptanceRun.Reloading = true;
        _loader.StartSaveGameInstantly(WorkerAcceptanceRun.SavedReference);
        return;
      }
      bool settlementDeleted = false;
      if (WorkerAcceptanceRun.SaveMode && WorkerAcceptanceRun.Worlds.Count == 2) {
        // The disposable settlement's saves are removed through the native repository.
        var settlement = WorkerAcceptanceRun.SavedReference.SettlementReference;
        _saves.DeleteSettlement(settlement);
        WorkerAcceptanceRun.Require(!Directory.Exists(_saves.SettlementReferenceIntoDirectoryName(settlement)), "The disposable settlement's saves were not deleted");
        settlementDeleted = true;
      }
      if (WorkerAcceptanceRun.Worlds.Count < (WorkerAcceptanceRun.SaveMode ? 1 : 2)) {
        WorkerAcceptanceRun.Require(_maps.GetUserMapNames().Contains(WorkerAcceptanceRun.Map), "Missing the explicitly named disposable worker fixture map");
        Debug.Log("[ModdableFluids Acceptance] Starting disposable world " + (WorkerAcceptanceRun.Worlds.Count + 1));
        WorkerAcceptanceRun.StartingWorld = true;
        _loader.StartNewGameInstantly("IronTeeth", MapFileReference.FromUserFolder(WorkerAcceptanceRun.Map), WorkerAcceptanceRun.Settlement);
        return;
      }
      // Keep the development package disabled for the user's next ordinary launch.
      var ownMod = _mods.EnabledMods.Single(mod => mod.Manifest.Id == "ModdableFluids");
      ModPlayerPrefsHelper.ToggleMod(false, ownMod); PlayerPrefs.Save();
      string report = WorkerAcceptanceRun.ReportPath;
      Directory.CreateDirectory(Path.GetDirectoryName(report));
      File.WriteAllText(report, JsonConvert.SerializeObject(new { status = "passed", mode = WorkerAcceptanceRun.SaveMode ? "save-reload" : "worker",
        scenesAttached = WorkerAcceptanceRun.Attached, scenesDetached = WorkerAcceptanceRun.Detached, worlds = WorkerAcceptanceRun.Worlds,
        savedDigest = WorkerAcceptanceRun.SavedDigest, settlementDeleted, prototypeDisabled = true,
        apiRuntime = ModdableFluidsEntry.DescribeRuntime() }, Formatting.Indented));
      Debug.Log("[ModdableFluids Acceptance] COMPLETE " + (WorkerAcceptanceRun.SaveMode ? "native save and reload" : "two disposable worlds") + ". Report: " + report);
      Application.Quit();
    }
  }

  public sealed class FluidWorkerAcceptance : IPostLoadableSingleton, ITickableSingleton, IUpdatableSingleton, IUnloadableSingleton {
    private readonly ModdableFluidsSceneOwner _owner;
    private readonly IWaterService _water;
    private readonly IWaterRemovalService _removals;
    private readonly ITickableSingletonService _ticks;
    private readonly MapIndexService _index;
    private readonly SpeedManager _speed;
    private readonly MainMenuSceneLoader _menu;
    private readonly PanelStack _panels;
    private readonly GameSaver _saver;
    private readonly SettlementReferenceService _settlements;
    private string _restoredDigest;
    private bool _sourceRegistered, _saveQueued;
    private readonly ConcurrentDictionary<int, byte> _workerIds = new ConcurrentDictionary<int, byte>();
    private readonly TestSource _source = new TestSource();
    private readonly Vector3Int _pool = new Vector3Int(8, 8, 3);
    private int _tick, _frames, _initialColumns, _maxColumns, _checks, _pumpRequests;
    private bool _returnToMenu, _finished, _pendingRemoval;
    private double _expectedRemoval, _previousRemoved, _nativeRemoved, _lastRemoved;
    // Transport indices include the native one-cell border, unlike MapIndexService.
    // This fixture always samples the lower reservoir (vertical ordinal zero).
    private int PoolIndex => (_pool.y + 1) * (_index.TerrainSize.x + 2) + _pool.x + 1;
    public FluidWorkerAcceptance(ModdableFluidsSceneOwner owner, IWaterService water, IWaterRemovalService removals,
        ITickableSingletonService ticks, MapIndexService index, SpeedManager speed, MainMenuSceneLoader menu, PanelStack panels,
        GameSaver saver, SettlementReferenceService settlements) {
      _owner = owner; _water = water; _removals = removals; _ticks = ticks; _index = index; _speed = speed; _menu = menu; _panels = panels;
      _saver = saver; _settlements = settlements;
    }
    private void Check(bool condition, string name) { _checks++; WorkerAcceptanceRun.Require(condition, name); }
    public void PostLoad() {
      Check(_index.TerrainSize.x == 32 && _index.TerrainSize.y == 32, "Worker acceptance requires the generated 32 by 32 fixture");
      // Both synthetic consumer packages must have registered: one by reflection, one compiled.
      var registry = _owner.Registry;
      Check(registry.Definitions.Select(d => d.Id).SequenceEqual(new[] { FluidIds.Water, FluidIds.Badwater, "ModdableFluidsSyntheticCompiled.Tracer", "ModdableFluidsSyntheticReflection.Juice" }),
        "Worker acceptance requires the two synthetic fixture packages; registry: " + string.Join(", ", registry.Definitions.Select(d => d.Id)));
      Check(_owner.Scene.Serial == WorkerAcceptanceRun.Attached, "Provider scene serial differs from the attached scene count");
      int components = registry.Count;
      FluidVolumes Even(double volume) => new FluidVolumes(Enumerable.Repeat(volume / components, components).ToArray());
      Check(WorkerAcceptanceRun.Reloading == (_owner.LoadedDocument != null), WorkerAcceptanceRun.Reloading
        ? "The reloaded world has no saved fluid state" : "A fresh disposable world loaded saved fluid state");
      _owner.SessionCreated = session => {
        _workerIds.TryAdd(Thread.CurrentThread.ManagedThreadId, 0);
        WorkerAcceptanceRun.Require(session.CompletedTicks == 0, "A new scene inherited previous fluid ticks");
        // Runs after the owner restored the saved state: recapture it before the first tick advances.
        if (WorkerAcceptanceRun.Reloading)
          _restoredDigest = FluidWorldSaveFormat.ContentDigest(FluidWorldPersistence.Capture(_owner.Registry, session, _owner.Stride, Array.Empty<FluidProviderState>()));
      };
      _owner.Hooks.ResolveSource = (source, native, volume) => {
        _workerIds.TryAdd(Thread.CurrentThread.ManagedThreadId, 0);
        WorkerAcceptanceRun.Require(ReferenceEquals(source, _source), "Unexpected emitter in the disposable dry map");
        return Even(volume);
      };
      _owner.Hooks.ResolveAddition = (change, native, volume, bad) => {
        _workerIds.TryAdd(Thread.CurrentThread.ManagedThreadId, 0);
        if (native == PoolIndex) return Even(volume);
        var vanilla = new double[components]; vanilla[FluidRegistry.WaterIndex] = volume * (1 - bad); vanilla[FluidRegistry.BadwaterIndex] = volume * bad;
        return new FluidVolumes(vanilla);
      };
    }
    public void UpdateSingleton() {
      if (_returnToMenu) { _returnToMenu = false; _menu.OpenMainMenu(); return; }
      _frames++;
      if (_frames < 60) {
        var stack = (IEnumerable)(typeof(PanelStack).GetField("_stack", BindingFlags.NonPublic | BindingFlags.Instance)
          ?? throw new MissingFieldException("PanelStack._stack")).GetValue(_panels);
        var top = stack.Cast<object>().FirstOrDefault();
        if (top != null) {
          var controller = (IPanelController)top.GetType().GetProperty("PanelController").GetValue(top);
          controller.OnUICancelled(); Debug.Log("[ModdableFluids Acceptance] Dismissed startup panel " + controller.GetType().FullName);
        }
      }
      if (!_finished) _speed.ChangeSpeed(1);
    }
    public void Tick() {
      if (_finished) return;
      Check(_ticks.ParalleTicklIsFinished, "Acceptance sampling occurred before the native parallel barrier");
      _tick++;
      var session = _owner.Hooks.Session;
      if (WorkerAcceptanceRun.Reloading) { TickReloaded(session); return; }
      if (_tick == 1) {
        // Queue a sealed lower reservoir. The next native Tick applies the real
        // obstacles and grows its buffers when the horizontal ceiling splits it.
        foreach (var edge in new[] { new Vector2Int(7,8), new Vector2Int(9,8), new Vector2Int(8,7), new Vector2Int(8,9) })
          for (int z = 3; z <= 7; z++) _water.AddFullObstacle(new Vector3Int(edge.x, edge.y, z));
        _water.AddHorizontalObstacle(new Vector3Int(8,8,4));
        return;
      }
      if (session == null) return;
      Check(session.Phase == "Ready", "Real worker jobs left an incomplete fluid tick");
      if (_initialColumns == 0) _initialColumns = session.ColumnCount;
      _maxColumns = Math.Max(_maxColumns, session.ColumnCount);
      if (_tick == 3) {
        _water.RegisterWaterSource(_source); _sourceRegistered = true;
        _water.AddCleanWater(_pool, .75f);
      }
      if (_tick == 12) _water.AddHorizontalObstacle(new Vector3Int(8,8,5));
      if (_tick == 16) _water.RemoveHorizontalObstacle(new Vector3Int(8,8,5));
      if (_tick == 30) {
        Check(session.PressureLoss.TotalVolume > 0, "Sealed real-worker reservoir never reached pressure capacity");
        _source.Strength = 0;
      }
      if (_pendingRemoval) {
        var removed = _removals.GetWaterChangeUnsafe(_pool);
        // Evaporation precedes queued intakes. Near empty, the actual amount may
        // be smaller than the pre-step availability; it must match the ledger.
        Check(removed.CleanWaterChange >= 0 && removed.CleanWaterChange <= _expectedRemoval + 2e-6, "Native intake exceeded its physical request/availability");
        Check(removed.ContaminatedWaterChange == 0, "Non-bad intake removed badwater");
        _nativeRemoved += removed.CleanWaterChange;
        double cumulative = session.Removed.TotalVolume - session.Removed.GetVolume(1);
        Check(Math.Abs(cumulative - _previousRemoved - removed.CleanWaterChange) < 2e-6, "Native intake result differs from the component removal ledger");
        _pendingRemoval = false;
      }
      if (_tick >= 34 && _tick <= 43) {
        var mixture = session.Sample(PoolIndex);
        _expectedRemoval = Math.Min(.5, mixture.TotalVolume - mixture.GetVolume(1));
        _previousRemoved = session.Removed.TotalVolume - session.Removed.GetVolume(1);
        _water.RemoveCleanWater(_pool, .5f); _pendingRemoval = true; _pumpRequests++;
      }
      if (_tick == 46) _water.RemoveHorizontalObstacle(new Vector3Int(8,8,4));
      if (_tick < 52) return;
      Check(_owner.WorkerCount > 0 && _workerIds.Count > 0 && !_workerIds.ContainsKey(_owner.MainThreadId), "Fluid callbacks did not run on actual native worker threads");
      Check(_maxColumns > _initialColumns, "Native column growth/resizing was not exercised");
      Check(_nativeRemoved > 0 && _pumpRequests == 10, "Native pump acceptance did not execute its ten requests");
      for (int component = 0; component < _owner.Registry.Count; component++) {
        double remaining = 0;
        for (int slot = 0; slot < session.ColumnCount; slot++) remaining += session.Sample(session.GetGeometry(slot).NativeIndex).GetVolume(component);
        double accounted = remaining + session.Removed.GetVolume(component) + session.Evaporated.GetVolume(component) + session.Discharged.GetVolume(component)
          + session.PressureLoss.GetVolume(component) + session.GeometryLoss.GetVolume(component);
        Check(Math.Abs(accounted - session.Added.GetVolume(component)) < 1e-7, "Real worker component conservation failed for " + component);
      }
      _lastRemoved = session.Removed.TotalVolume;
      WorkerAcceptanceRun.Worlds.Add(new { scene = WorkerAcceptanceRun.Attached, nativeTicks = session.CompletedTicks, checks = _checks,
        workers = _owner.WorkerCount, mainThread = _owner.MainThreadId, callbackThreads = _workerIds.Keys.OrderBy(v=>v).ToArray(),
        initialColumns = _initialColumns, maximumColumns = _maxColumns, pressureLoss = session.PressureLoss.TotalVolume,
        nativePumpRemoved = _nativeRemoved, componentPumpRemoved = _lastRemoved, maxRepresentationDifference = session.MaxRepresentationDifference,
        registryFingerprint = _owner.Registry.Fingerprint, fluids = _owner.Registry.Definitions.Select(d => d.Id).ToArray(), providerScene = _owner.Scene.Serial });
      Debug.Log("[ModdableFluids Acceptance] WORLD PASS " + WorkerAcceptanceRun.Worlds.Count + "; ticks=" + session.CompletedTicks + "; callbacks=" + string.Join(",", _workerIds.Keys));
      _finished = true; _speed.ChangeSpeed(0);
      if (!WorkerAcceptanceRun.SaveMode) { _returnToMenu = true; return; }
      // Native save of this disposable world. GameSaver finishes the tick first; the owner then
      // captures the fluid document and records its digest, which the reloaded world must match.
      var states = ProviderStates();
      var reference = new SaveReference(WorkerAcceptanceRun.SaveName, _settlements.SettlementReference);
      _saveQueued = true;
      _saver.QueueSave(reference, () => {
        Check(_owner.LastSaveDigest != null, "The native save did not capture fluid state");
        WorkerAcceptanceRun.SavedReference = reference; WorkerAcceptanceRun.SavedDigest = _owner.LastSaveDigest; WorkerAcceptanceRun.SavedProviderStates = states;
        Debug.Log("[ModdableFluids Acceptance] SAVED " + reference + "; fluid digest " + _owner.LastSaveDigest);
        _returnToMenu = true;
      });
    }
    private string[] ProviderStates() =>
      ModdableFluidsEntry.Host.SaveProviderStates(_owner.Scene).Select(s => s.ProviderId + "|" + s.SchemaVersion + "|" + s.Data).ToArray();
    private void TickReloaded(NativeFluidTransportSession session) {
      if (session == null) return;
      Check(session.Phase == "Ready", "Real worker jobs left an incomplete fluid tick after reload");
      if (_tick < 6) return;
      var restored = _owner.Restored;
      Check(restored != null && _restoredDigest != null, "The reloaded world never restored its fluid state");
      Check(_restoredDigest == WorkerAcceptanceRun.SavedDigest, "Reloaded fluid state differs from the saved state: " + _restoredDigest + " versus " + WorkerAcceptanceRun.SavedDigest);
      Check(restored.ExactColumns == _owner.LoadedDocument.ColumnCount && restored.ProjectedColumns == 0, "Unchanged geometry was not restored exactly");
      Check(ProviderStates().SequenceEqual(WorkerAcceptanceRun.SavedProviderStates), "Provider state changed across the native save and reload");
      for (int component = 0; component < _owner.Registry.Count; component++) {
        double baseline = 0, remaining = 0;
        for (int slot = 0; slot < restored.ColumnCount; slot++) baseline += restored.GetColumn(slot).GetVolume(component);
        for (int slot = 0; slot < session.ColumnCount; slot++) remaining += session.Sample(session.GetGeometry(slot).NativeIndex).GetVolume(component);
        double accounted = remaining + session.Removed.GetVolume(component) + session.Evaporated.GetVolume(component) + session.Discharged.GetVolume(component)
          + session.PressureLoss.GetVolume(component) + session.GeometryLoss.GetVolume(component);
        Check(Math.Abs(accounted - baseline - session.Added.GetVolume(component)) < 1e-7, "Reloaded component conservation failed for " + component);
      }
      Check(_workerIds.Count > 0 && !_workerIds.ContainsKey(_owner.MainThreadId), "Reloaded fluid callbacks did not run on native worker threads");
      WorkerAcceptanceRun.Worlds.Add(new { scene = WorkerAcceptanceRun.Attached, reloaded = true, nativeTicks = session.CompletedTicks, checks = _checks,
        restoredColumns = restored.ExactColumns, restoredDigest = _restoredDigest, providerStates = WorkerAcceptanceRun.SavedProviderStates,
        maxRepresentationDifference = session.MaxRepresentationDifference, registryFingerprint = _owner.Registry.Fingerprint,
        fluids = _owner.Registry.Definitions.Select(d => d.Id).ToArray(), providerScene = _owner.Scene.Serial });
      Debug.Log("[ModdableFluids Acceptance] RELOAD PASS; " + restored.ExactColumns + " columns restored bit for bit; digest " + _restoredDigest);
      WorkerAcceptanceRun.Reloading = false;
      _finished = true; _speed.ChangeSpeed(0); _returnToMenu = true;
    }
    public void Unload() {
      if (_sourceRegistered) _water.UnregisterWaterSource(_source);
      WorkerAcceptanceRun.Require(!_saveQueued || WorkerAcceptanceRun.SavedReference != null, "The scene unloaded before its queued native save completed");
    }
    private sealed class TestSource : IWaterSource {
      internal float Strength = .4f;
      public ImmutableArray<Vector3Int> Coordinates => ImmutableArray.Create(new Vector3Int(8,8,3));
      public float SpecifiedStrength => Strength;
      public float CurrentStrength => Strength;
      public float Contamination => .25f;
      public void SetSpecifiedStrength(float strength) => throw new NotSupportedException("Acceptance emitter is controlled by its fixture");
    }
  }
}
