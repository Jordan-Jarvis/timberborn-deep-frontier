using System;
using System.Linq;
using System.Reflection;
using System.Threading;
using Bindito.Core;
using Timberborn.Multithreading;
using Timberborn.SingletonSystem;
using Timberborn.WaterSystem;
using ModdableFluids;
using ModdableFluids.GameBridge.Prototype;
using ModdableFluids.Native.Prototype;
using UnityEngine;

namespace ModdableFluids.Runtime.Prototype {
  [Context("Game")]
  public sealed class ModdableFluidsSceneConfigurator : Configurator {
    protected override void Configure() {
      // The prototype has no persistence yet. Only explicitly disposable acceptance
      // worlds may activate it; ordinary play leaves native water untouched.
      if (!WorkerAcceptanceRun.Enabled) return;
      Bind<ModdableFluidsSceneOwner>().AsSingleton();
      Bind<FluidWorkerAcceptance>().AsSingleton();
    }
  }

  public sealed class ModdableFluidsSceneOwner : IPostLoadableSingleton, IUnloadableSingleton {
    private readonly IWaterService _water;
    private readonly IParallelizer _parallelizer;
    public NativeTransportHooks Hooks { get; private set; }
    public FluidRegistry Registry { get; private set; }
    public FluidScene Scene { get; private set; }
    public int MainThreadId { get; private set; }
    public int WorkerCount => _parallelizer.NumberOfThreads;
    public ModdableFluidsSceneOwner(IWaterService water, IParallelizer parallelizer) { _water = water; _parallelizer = parallelizer; }
    public void PostLoad() {
      WorkerAcceptanceRun.Require(WorkerAcceptanceRun.StartingWorld, "Prototype activation requires a fresh disposable world started by its acceptance loader");
      WorkerAcceptanceRun.StartingWorld = false;
      MainThreadId = Thread.CurrentThread.ManagedThreadId;
      // Providers registered from their IModStarter; the registry freezes once, before the first world.
      var host = ModdableFluidsEntry.Host;
      Registry = host.Freeze();
      Scene = host.ActivateScene();
      // A fresh disposable world has no saved fluid state.
      host.LoadProviderStates(Scene, null);
      object simulator = Read(_water, "_waterSimulator");
      object starter = Read(simulator, "_waterSimulationTaskStarter");
      Hooks = new NativeTransportHooks(starter, Registry.Count, FluidRegistry.BadwaterIndex);
      Hooks.Attach(); WorkerAcceptanceRun.Attached++;
      Debug.Log("[ModdableFluids] ATTACHED scene " + WorkerAcceptanceRun.Attached + "; native workers=" + WorkerCount + "; main thread=" + MainThreadId + "\n" + host.DescribeRuntime());
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
