using System;
using System.Linq;
using System.Reflection;
using System.Threading;
using Bindito.Core;
using Timberborn.MapIndexSystem;
using Timberborn.Multithreading;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;
using ModdableFluids;
using ModdableFluids.GameBridge.Prototype;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Persistence.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  [Context("Game")]
  public sealed class ModdableFluidsSceneConfigurator : Configurator {
    protected override void Configure() {
      // Only explicitly disposable acceptance worlds may activate the prototype;
      // ordinary play leaves native water untouched.
      if (!WorkerAcceptanceRun.Enabled) return;
      Bind<ModdableFluidsSceneOwner>().AsSingleton();
      Bind<FluidWorkerAcceptance>().AsSingleton();
    }
  }

  /// <summary>
  /// One game scene's fluid owner: registry scene, native transport attachment and world save.
  /// Load reads the <c>ModdableFluids.World</c> singleton; PostLoad validates its fluid IDs against the
  /// frozen registry on the main thread, delivers provider state and attaches the transport. The
  /// component state is restored in the first native substep, before geometry reconciliation, and
  /// any disagreement with native water fails that tick. Save runs after the native saver finished
  /// the tick (GameSaver.Save calls Ticker.FinishFullTick), so the session must be at a completed
  /// tick; otherwise the save fails with the reason instead of recording a partial state.
  /// </summary>
  public sealed class ModdableFluidsSceneOwner : ILoadableSingleton, IPostLoadableSingleton, ISaveableSingleton, IUnloadableSingleton {
    private readonly IWaterService _water;
    private readonly IParallelizer _parallelizer;
    private readonly ISingletonLoader _singletons;
    private readonly MapIndexService _index;
    private FluidWorldSaveFormat.Loaded _loaded;
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
    public string LastSaveDigest { get; private set; }
    public int Stride => _index.Stride;
    public int Height => _index.TerrainSize.y;

    public ModdableFluidsSceneOwner(IWaterService water, IParallelizer parallelizer, ISingletonLoader singletons, MapIndexService index) {
      _water = water; _parallelizer = parallelizer; _singletons = singletons; _index = index;
    }

    public void Load() {
      if (_singletons.TryGetSingleton(FluidWorldSaveFormat.Key, out var loader)) _loaded = FluidWorldSaveFormat.Read(loader);
    }

    public void PostLoad() {
      WorkerAcceptanceRun.Require(WorkerAcceptanceRun.StartingWorld, "Prototype activation requires a disposable world started by its acceptance loader");
      WorkerAcceptanceRun.StartingWorld = false;
      if (_index.Stride != _index.TerrainSize.x + 2) throw new InvalidOperationException("Moddable Fluids expects the native padded map index layout of 1.1.2.8");
      MainThreadId = Thread.CurrentThread.ManagedThreadId;
      // Providers registered from their IModStarter; the registry freezes once, before the first world.
      var host = ModdableFluidsEntry.Host;
      Registry = host.Freeze();
      // Missing or moved fluids stop loading here, on the main thread, naming their mods.
      LoadedDocument?.ResolveFluidSlots(Registry);
      Scene = host.ActivateScene();
      host.LoadProviderStates(Scene, _loaded?.ProviderStates);
      object simulator = Read(_water, "_waterSimulator");
      object starter = Read(simulator, "_waterSimulationTaskStarter");
      Hooks = new NativeTransportHooks(starter, Registry.Count, FluidRegistry.BadwaterIndex);
      Hooks.SessionCreated = OnSessionCreated;
      Hooks.Attach(); WorkerAcceptanceRun.Attached++;
      Debug.Log("[ModdableFluids] ATTACHED scene " + WorkerAcceptanceRun.Attached + "; native workers=" + WorkerCount + "; main thread=" + MainThreadId
        + "; saved fluid state=" + (LoadedDocument != null ? LoadedDocument.ColumnCount + " columns" : _loaded != null ? "native only" : "none") + "\n" + host.DescribeRuntime());
    }

    private void OnSessionCreated(NativeFluidTransportSession session) {
      if (LoadedDocument != null) {
        var layout = Enumerable.Range(0, session.ColumnCount).Select(session.GetGeometry).ToArray();
        Restored = FluidWorldPersistence.Restore(LoadedDocument, Registry, layout, Stride, Height);
        FluidWorldPersistence.Apply(session, Registry, Restored, Stride);
      }
      SessionCreated?.Invoke(session);
    }

    public void Save(ISingletonSaver singletonSaver) {
      var host = ModdableFluidsEntry.Host;
      var states = host.SaveProviderStates(Scene);
      var saver = singletonSaver.GetSingleton(FluidWorldSaveFormat.Key);
      var session = Hooks.Session;
      FluidSaveDocument document;
      if (session == null) {
        // No fluid tick has run since load: the saved components are unchanged.
        if (LoadedDocument == null) { FluidWorldSaveFormat.WriteNativeOnly(saver, states); LastSaveDigest = null; return; }
        document = FluidWorldSaveFormat.WithProviderStates(LoadedDocument, states);
      } else {
        if (session.Phase != "Ready")
          throw new InvalidOperationException("Moddable Fluids saves only at a completed water tick; the fluid session is " + session.Phase
            + ". A save during a failed or unfinished tick cannot record fluid state.");
        document = FluidWorldPersistence.Capture(Registry, session, Stride, states);
      }
      FluidWorldSaveFormat.Write(saver, document);
      LastSaveDigest = FluidWorldSaveFormat.ContentDigest(document);
    }

    public void Unload() {
      if (Scene == null) return;
      if (Hooks == null) { ModdableFluidsEntry.Host.UnloadScene(Scene); return; }
      // Native singleton unload order may already have closed the parallelizer.
      // Wait is still its public main-thread barrier and checks pending work.
      _parallelizer.Wait();
      int ticks = Hooks.Session?.CompletedTicks ?? 0;
      Hooks.Dispose();
      ModdableFluidsEntry.Host.UnloadScene(Scene);
      if (Hooks.HasInstalledPatches || NativeTransportHooks.HasActiveOwner || ModdableFluidsEntry.Host.ActiveScene != null)
        throw new InvalidOperationException("Moddable Fluids scene teardown left an active transport owner or provider scene");
      WorkerAcceptanceRun.Detached++;
      Debug.Log("[ModdableFluids] DETACHED scene " + WorkerAcceptanceRun.Detached + "; completed ticks=" + ticks);
    }
    private static object Read(object owner, string field) => (owner.GetType().GetField(field, BindingFlags.Instance | BindingFlags.NonPublic)
      ?? throw new MissingFieldException(owner.GetType().FullName, field)).GetValue(owner);
  }
}
