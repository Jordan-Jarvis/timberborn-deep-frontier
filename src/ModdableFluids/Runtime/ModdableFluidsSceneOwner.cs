using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using System.Threading;
using Bindito.Core;
using Timberborn.MapIndexSystem;
using Timberborn.Multithreading;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;
using ModdableFluids;
using ModdableFluids.GameBridge.Prototype;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Persistence.Prototype;
using ModdableFluids.Transport.Prototype;
using ModdableFluids.World.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  [Context("Game")]
  public sealed class ModdableFluidsSceneConfigurator : Configurator {
    protected override void Configure() {
      // Providers registered from their IModStarter; the registry freezes once, before the first world, and a
      // rejected registration stops this scene here with every problem named.
      var registry = ModdableFluidsEntry.Host.Freeze();
      // Terrain overlays (registered with the providers) are drawn whether or not a mod registered a fluid; with none,
      // the native terrain stays completely untouched.
      if (ModdableFluidsEntry.Host.TerrainOverlays.Count > 0) {
        var terrain = FluidTerrainRendering.CheckContract();
        if (terrain.Count > 0)
          throw new InvalidOperationException("Moddable Fluids cannot draw terrain overlays in this game (expected Timberborn 1.1.2.8). Changed native contract:\n- " + string.Join("\n- ", terrain));
        Bind<FluidTerrainRendering>().AsSingleton();
      }
      // With no fluid besides water and badwater nothing else is bound: native water stays completely untouched.
      // The worker-acceptance fixture stays behind its flag (its synthetic fluids register only with it).
      if (!WorkerAcceptanceRun.Enabled && !registry.HasExtraFluids) return;
      // The native members the intake guard and the moisture input compile against, before either is bound.
      var changed = FluidWaterIntakeGuard.CheckContract().Concat(FluidMoistureInput.CheckContract()).Concat(FluidPlacedSource.CheckContract()).ToArray();
      if (changed.Length > 0)
        throw new InvalidOperationException("Moddable Fluids cannot attach to this game (expected Timberborn 1.1.2.8). Changed native contract:\n- " + string.Join("\n- ", changed));
      Bind<FluidMoistureInput>().AsSingleton();
      // Before any entity wakes: every placed water source is classified by its blueprint into this table.
      Bind<FluidPlacedSources>().AsSingleton();
      Bind<FluidPlacedSource>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(FluidPlacedSource.Module).AsSingleton();
      Bind<ModdableFluidsSceneOwner>().AsSingleton();
      // After the owner: it needs the frozen registry and the session the owner attaches.
      Bind<FluidWaterRendering>().AsSingleton();
      Bind<FluidWaterIntakeGuard>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(FluidWaterIntakeGuard.Module).AsSingleton();
      if (WorkerAcceptanceRun.Enabled) Bind<FluidWorkerAcceptance>().AsSingleton();
    }
  }

  /// <summary>
  /// One game scene's fluid owner: registry scene, native transport attachment, world save and extraction results.
  /// It is bound in every game scene where a mod registered a fluid (ordinary play), and in the flagged worker
  /// fixture. Load reads the <c>ModdableFluids.World</c> singleton; PostLoad checks everything that can refuse
  /// before changing anything (every fluid's policies, the native contracts, other mods' patches on what Moddable
  /// Fluids replaces), then delivers provider state and attaches the transport. The component state is restored in
  /// the first native substep, before geometry reconciliation, and any disagreement with native water fails that
  /// tick. Save runs after the native saver finished the tick (GameSaver.Save calls Ticker.FinishFullTick), so the
  /// session must be at a completed tick; the native exception saver (which can arrive mid-tick) instead writes the
  /// last published completed tick, marked so its load takes native water as authoritative.
  /// </summary>
  public sealed class ModdableFluidsSceneOwner : ILoadableSingleton, IPostLoadableSingleton, ISaveableSingleton, ITickableSingleton, IUnloadableSingleton {
    private readonly IWaterService _water;
    private readonly IParallelizer _parallelizer;
    private readonly ISingletonLoader _singletons;
    private readonly MapIndexService _index;
    private readonly ITickableSingletonService _ticks;
    private readonly TickOnlyArrayService _tickOnlyArrays;
    private readonly FieldInfo _forceAllowAccess;
    private readonly FluidMoistureInput _moisture;
    private readonly FluidPlacedSources _sources;
    private FluidWorldSaveFormat.Loaded _loaded;
    private bool _subscribed;
    public NativeTransportHooks Hooks { get; private set; }
    public FluidRegistry Registry { get; private set; }
    public FluidScene Scene { get; private set; }
    public int MainThreadId { get; private set; }
    public int WorkerCount => _parallelizer.NumberOfThreads;
    /// <summary>Runs on the native worker thread after any saved state was restored.</summary>
    public Action<NativeFluidTransportSession> SessionCreated { get; set; }
    public FluidSaveDocument LoadedDocument => _loaded?.Document;
    public bool LoadedFluidState => _loaded != null;
    public FluidRestoreResult Restored { get; private set; }
    /// <summary>What loading an exception-save snapshot changed (null unless the save was one).</summary>
    public FluidSnapshotAdjustment SnapshotAdjustment { get; private set; }
    /// <summary>The fluid state an importer supplied for a save without Moddable Fluids data, if any.</summary>
    public FluidSaveDocument ImportedDocument { get; private set; }
    public string LastSaveDigest { get; private set; }
    /// <summary>Whether the last save was a native exception save, written from the last published tick.</summary>
    public bool LastSaveWasSnapshot { get; private set; }
    public int Stride => _index.Stride;
    public int Height => _index.TerrainSize.y;
    /// <summary>The scene's world fluid service (sampling, additions, source composition, extraction).</summary>
    public ModdableFluidsWorld World { get; private set; }
    /// <summary>The native soil-moisture input owner (installed only when a fluid blocks moisture).</summary>
    public FluidMoistureInput Moisture => _moisture;

    public ModdableFluidsSceneOwner(IWaterService water, IParallelizer parallelizer, ISingletonLoader singletons, MapIndexService index,
        ITickableSingletonService ticks, TickOnlyArrayService tickOnlyArrays, FluidMoistureInput moisture, FluidPlacedSources sources) {
      _sources = sources;
      _water = water; _parallelizer = parallelizer; _singletons = singletons; _index = index; _ticks = ticks; _tickOnlyArrays = tickOnlyArrays; _moisture = moisture;
      // The native exception saver (GameSceneExceptionStateSaver.CreateExceptionSave) marks itself only through this
      // private field (TickOnlyArrayService.ForceAllowAccess, then GameSaver.SaveWithoutFinishingTick).
      _forceAllowAccess = typeof(TickOnlyArrayService).GetField("_forceAllowAccess", BindingFlags.Instance | BindingFlags.NonPublic);
      if (_forceAllowAccess == null || _forceAllowAccess.FieldType != typeof(bool))
        throw new InvalidOperationException("Moddable Fluids cannot tell an exception save from a normal save: native TickOnlyArrayService._forceAllowAccess (bool) changed (expected Timberborn 1.1.2.8)");
    }

    public void Load() {
      if (_singletons.TryGetSingleton(FluidWorldSaveFormat.Key, out var loader)) _loaded = FluidWorldSaveFormat.Read(loader);
    }

    public void PostLoad() {
      if (WorkerAcceptanceRun.Enabled) {
        WorkerAcceptanceRun.Require(WorkerAcceptanceRun.StartingWorld, "Prototype activation requires a disposable world started by its acceptance loader");
        WorkerAcceptanceRun.StartingWorld = false;
      }
      if (_index.Stride != _index.TerrainSize.x + 2) throw new InvalidOperationException("Moddable Fluids expects the native padded map index layout of 1.1.2.8");
      MainThreadId = Thread.CurrentThread.ManagedThreadId;
      var host = ModdableFluidsEntry.Host;
      Registry = host.Freeze();
      // Everything that can refuse, before anything changes.
      var undeclared = Registry.UndeclaredPolicies();
      if (undeclared.Count > 0)
        throw new InvalidOperationException("Moddable Fluids cannot carry these fluids in a game: every fluid needs a water-intake policy and an irrigation policy, declared by its mod.\n- "
          + string.Join("\n- ", undeclared));
      // Missing or moved fluids stop loading here, on the main thread, naming their mods.
      LoadedDocument?.ResolveFluidSlots(Registry);
      object simulator = Read(_water, "_waterSimulator");
      object starter = Read(simulator, "_waterSimulationTaskStarter");
      var hooks = new NativeTransportHooks(starter, Registry.Count, FluidRegistry.BadwaterIndex);
      var conflicts = hooks.ForeignPatches().Concat(_moisture.Prepare(Registry)).ToArray();
      if (conflicts.Length > 0) {
        hooks.Dispose();
        throw new InvalidOperationException("Moddable Fluids replaces these native methods for the registered fluids ("
          + string.Join(", ", Registry.Definitions.Where(d => d.NativeRole == FluidNativeRole.Extra).Select(d => d.Id))
          + "), and another mod patches them; both cannot run, so the game stops before the simulation starts:\n- " + string.Join("\n- ", conflicts));
      }
      Hooks = hooks;
      World = new ModdableFluidsWorld(Registry, Stride, Height, _water, MainThreadId, _sources);
      Scene = host.ActivateScene(World);
      host.LoadProviderStates(Scene, _loaded?.ProviderStates);
      Hooks.SessionCreated = OnSessionCreated;
      Hooks.TickCompleted = OnTickCompleted;
      Hooks.ResolveAddition = World.ResolveAddition;
      Hooks.ResolveSource = World.ResolveSource;
      Hooks.Extractions = World.Extractions;
      Hooks.Attach();
      _moisture.Install(World.State);
      // A save forces the parallel tick to finish (Ticker.FinishFullTick): deliver extraction results before it writes.
      _ticks.ForcedParallelTickFinished += OnForcedParallelTickFinished; _subscribed = true;
      if (WorkerAcceptanceRun.Enabled) WorkerAcceptanceRun.Attached++;
      Debug.Log("[ModdableFluids] ATTACHED" + (WorkerAcceptanceRun.Enabled ? " acceptance scene " + WorkerAcceptanceRun.Attached : "") + "; native workers=" + WorkerCount + "; main thread=" + MainThreadId
        + "; moisture input " + (_moisture.Installed ? "owned" : "untouched (no fluid blocks moisture)")
        + "; saved fluid state=" + (LoadedDocument != null ? LoadedDocument.ColumnCount + " columns" + (_loaded.Snapshot ? " (exception-save snapshot)" : "")
          : _loaded == null ? "none" : _loaded.ImportPending ? "native only, import pending" : "native only") + "\n" + host.DescribeRuntime());
    }

    private void OnSessionCreated(NativeFluidTransportSession session) {
      var layout = Enumerable.Range(0, session.ColumnCount).Select(session.GetGeometry).ToArray();
      // A save without Moddable Fluids data (an older or another mod's format) may be imported, once.
      if (_loaded == null || _loaded.ImportPending) ImportedDocument = ModdableFluidsEntry.Host.ImportWorld(Scene, layout.Select(g => NativeColumn(session, g)).ToArray());
      var document = LoadedDocument ?? ImportedDocument;
      if (document != null) {
        Restored = FluidWorldPersistence.Restore(document, Registry, layout, Stride, Height);
        if (_loaded != null && _loaded.Snapshot) {
          SnapshotAdjustment = FluidWorldPersistence.ApplySnapshot(session, Registry, Restored, Stride);
          Debug.LogWarning("[ModdableFluids] Loaded an exception save: the last completed fluid tick, with native water authoritative. "
            + SnapshotAdjustment.AdjustedColumns.Count + " column(s) adjusted to native water"
            + (SnapshotAdjustment.AdjustedColumns.Count > 0 ? " (" + string.Join(", ", SnapshotAdjustment.AdjustedColumns.Take(20)) + (SnapshotAdjustment.AdjustedColumns.Count > 20 ? ", ..." : "") + ")" : "")
            + "; absolute change per fluid: " + string.Join(", ", Enumerable.Range(0, Registry.Count).Select(c => Registry.Definitions[c].Id + " "
              + SnapshotAdjustment.AbsoluteDifference.GetVolume(c).ToString("R", System.Globalization.CultureInfo.InvariantCulture))));
        } else FluidWorldPersistence.Apply(session, Registry, Restored, Stride);
      }
      World.State.Publish(session);
      SessionCreated?.Invoke(session);
    }

    private FluidNativeColumn NativeColumn(NativeFluidTransportSession session, FluidColumnGeometry geometry) {
      var mixture = session.Sample(geometry.NativeIndex);
      return new FluidNativeColumn(geometry.CellIndex % Stride - 1, geometry.CellIndex / Stride - 1, geometry.Floor, geometry.Ceiling,
        geometry.Capacity, mixture.TotalVolume, mixture.GetShare(FluidRegistry.BadwaterIndex));
    }

    // Worker thread, at the completed-tick barrier: provider rules (with the tick's losses), then publication to readers.
    private void OnTickCompleted(NativeFluidTransportSession session) {
      var editor = new FluidColumnEditor(session, Registry, Stride);
      try { ModdableFluidsEntry.Host.ApplyColumnRules(Scene, editor); }
      finally { editor.Close(); }
      World.State.Publish(session);
    }

    // Main thread, singleton tick (after the previous parallel tick finished): extraction results.
    public void Tick() => World?.Extractions.DeliverResolved();

    private void OnForcedParallelTickFinished(object sender, EventArgs e) => World?.Extractions.DeliverResolved();

    public void Save(ISingletonSaver singletonSaver) {
      // A scene that failed before its provider scene existed has nothing of Moddable Fluids to save.
      if (Scene == null) return;
      bool exceptionSave = (bool)_forceAllowAccess.GetValue(_tickOnlyArrays);
      var host = ModdableFluidsEntry.Host;
      var states = host.SaveProviderStates(Scene);
      var saver = singletonSaver.GetSingleton(FluidWorldSaveFormat.Key);
      var session = Hooks?.Session;
      FluidSaveDocument document;
      LastSaveWasSnapshot = false;
      if (session != null && exceptionSave && World.State.TryGetPublished(out var layout, out var mixtures, out _)) {
        // The native exception saver can arrive while workers still run (or abandoned) a fluid tick: write the last
        // completed tick that was published, rules included. Its load takes native water as authoritative.
        document = FluidWorldPersistence.Capture(Registry, layout, mixtures, Stride, states);
        FluidWorldSaveFormat.Write(saver, document, snapshot: true);
        LastSaveDigest = FluidWorldSaveFormat.ContentDigest(document); LastSaveWasSnapshot = true;
        return;
      }
      if (session == null || (exceptionSave && !World.State.HasSnapshot)) {
        // No fluid tick has run since load (or none completed before the exception): the saved components are unchanged.
        // Before the first substep the importers have not run: mark the save so the next load imports.
        if (LoadedDocument == null) {
          FluidWorldSaveFormat.WriteNativeOnly(saver, states, (_loaded == null || _loaded.ImportPending) && host.HasImporters);
          LastSaveDigest = null; return;
        }
        document = FluidWorldSaveFormat.WithProviderStates(LoadedDocument, states);
        FluidWorldSaveFormat.Write(saver, document, snapshot: _loaded.Snapshot);
        LastSaveDigest = FluidWorldSaveFormat.ContentDigest(document);
        return;
      }
      if (session.Phase != "Ready")
        throw new InvalidOperationException("Moddable Fluids saves only at a completed water tick; the fluid session is " + session.Phase
          + ". A save during a failed or unfinished tick cannot record fluid state.");
      document = FluidWorldPersistence.Capture(Registry, session, Stride, states);
      FluidWorldSaveFormat.Write(saver, document);
      LastSaveDigest = FluidWorldSaveFormat.ContentDigest(document);
    }

    public void Unload() {
      if (_subscribed) { _ticks.ForcedParallelTickFinished -= OnForcedParallelTickFinished; _subscribed = false; }
      if (Scene == null) { Hooks?.Dispose(); _moisture.Uninstall(); return; }
      World?.Extractions.Close();
      if (Hooks == null) { _moisture.Uninstall(); ModdableFluidsEntry.Host.UnloadScene(Scene); return; }
      // Native singleton unload order may already have closed the parallelizer.
      // Wait is still its public main-thread barrier and checks pending work.
      _parallelizer.Wait();
      int ticks = Hooks.Session?.CompletedTicks ?? 0;
      Hooks.Dispose();
      _moisture.Uninstall();
      ModdableFluidsEntry.Host.UnloadScene(Scene);
      if (Hooks.HasInstalledPatches || NativeTransportHooks.HasActiveOwner || _moisture.HasOwnedPatch || FluidMoistureInput.HasActiveOwner || ModdableFluidsEntry.Host.ActiveScene != null)
        throw new InvalidOperationException("Moddable Fluids scene teardown left an active transport owner, moisture patch or provider scene");
      if (WorkerAcceptanceRun.Enabled) WorkerAcceptanceRun.Detached++;
      Debug.Log("[ModdableFluids] DETACHED" + (WorkerAcceptanceRun.Enabled ? " acceptance scene " + WorkerAcceptanceRun.Detached : "") + "; completed ticks=" + ticks);
    }
    private static object Read(object owner, string field) => (owner.GetType().GetField(field, BindingFlags.Instance | BindingFlags.NonPublic)
      ?? throw new MissingFieldException(owner.GetType().FullName, field)).GetValue(owner);
  }
}
