using System;
using System.Linq;
using System.Reflection;
using System.Threading;
using Bindito.Core;
using Timberborn.Multithreading;
using Timberborn.SingletonSystem;
using Timberborn.WaterSystem;
using FluidsApi.GameBridge.Prototype;
using FluidsApi.Native.Prototype;
using UnityEngine;

namespace FluidsApi.Runtime.Prototype {
  [Context("Game")]
  public sealed class FluidsApiSceneConfigurator : Configurator {
    protected override void Configure() {
      // The prototype has no persistence yet. Only explicitly disposable acceptance
      // worlds may activate it; ordinary play leaves native water untouched.
      if (!WorkerAcceptanceRun.Enabled) return;
      Bind<FluidsApiSceneOwner>().AsSingleton();
      Bind<FluidWorkerAcceptance>().AsSingleton();
    }
  }

  public sealed class FluidsApiSceneOwner : IPostLoadableSingleton, IUnloadableSingleton {
    private readonly IWaterService _water;
    private readonly IParallelizer _parallelizer;
    public NativeTransportHooks Hooks { get; private set; }
    public int MainThreadId { get; private set; }
    public int WorkerCount => _parallelizer.NumberOfThreads;
    public FluidsApiSceneOwner(IWaterService water, IParallelizer parallelizer) { _water = water; _parallelizer = parallelizer; }
    public void PostLoad() {
      WorkerAcceptanceRun.Require(WorkerAcceptanceRun.StartingWorld, "Prototype activation requires a fresh disposable world started by its acceptance loader");
      WorkerAcceptanceRun.StartingWorld = false;
      MainThreadId = Thread.CurrentThread.ManagedThreadId;
      object simulator = Read(_water, "_waterSimulator");
      object starter = Read(simulator, "_waterSimulationTaskStarter");
      Hooks = new NativeTransportHooks(starter, 4, 1);
      Hooks.Attach(); WorkerAcceptanceRun.Attached++;
      Debug.Log("[FluidsApi] ATTACHED scene " + WorkerAcceptanceRun.Attached + "; native workers=" + WorkerCount + "; main thread=" + MainThreadId);
    }
    public void Unload() {
      if (Hooks == null) return;
      // Native singleton unload order may already have closed the parallelizer.
      // Wait is still its public main-thread barrier and checks pending work.
      _parallelizer.Wait();
      int ticks = Hooks.Session?.CompletedTicks ?? 0;
      Hooks.Dispose();
      if (Hooks.HasInstalledPatches || NativeTransportHooks.HasActiveOwner) throw new InvalidOperationException("Fluids API scene teardown left an active transport owner");
      WorkerAcceptanceRun.Detached++;
      Debug.Log("[FluidsApi] DETACHED scene " + WorkerAcceptanceRun.Detached + "; completed ticks=" + ticks);
    }
    private static object Read(object owner, string field) => (owner.GetType().GetField(field, BindingFlags.Instance | BindingFlags.NonPublic)
      ?? throw new MissingFieldException(owner.GetType().FullName, field)).GetValue(owner);
  }
}
