using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using ModdableFluids;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace ModdableFluidsSyntheticCompiled {
  /// <summary>
  /// Development fixture for the compiled route. Its package requires Moddable Fluids: the provider type
  /// implements API interfaces, so the assembly cannot be enumerated when the API is absent.
  /// It registers only in a flagged disposable acceptance run.
  /// </summary>
  public sealed class SyntheticCompiledStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      if (!Environment.GetCommandLineArgs().Contains("-moddableFluidsWorkerAcceptance")) return;
      ModdableFluidsEntry.RegisterProvider(new TracerProvider());
      Debug.Log("[ModdableFluidsSyntheticCompiled] registered " + TracerProvider.Id + " with Moddable Fluids " + ModdableFluidsEntry.ApiVersion);
    }
  }

  public sealed class TracerProvider : IFluidProvider, IFluidSceneProvider, IFluidStateProvider {
    public const string Owner = "ModdableFluidsSyntheticCompiled";
    public const string Id = Owner + ".Tracers";
    public string ProviderId => Id;
    public string OwnerModId => Owner;
    public string MinimumApiVersion => "0.1.0";
    public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] { "ModdableFluids.Registry.Definitions", "ModdableFluids.Scene.Lifecycle", "ModdableFluids.Persistence.ProviderState" };
    public int StateSchemaVersion => 2;
    public int Activations { get; private set; }
    public int Unloads { get; private set; }
    public FluidHandle Tracer { get; private set; }
    /// <summary>Provider-owned persistent state; schema 1 stored only the release count.</summary>
    public int Releases { get; set; }
    public string LastTag { get; set; } = "";

    public void Register(FluidRegistration registration) {
      registration.AddFluid("Tracer", Owner + ".Tracer.DisplayName", .2f, .9f, .35f, .7f);
      registration.AddMetadata("Tracer", Owner + ".DetectionLimit", "0.001");
      // 0.1.4 policies only where the runtime lists them; the calls sit in their own method so an older API never JITs them.
      if (ModdableFluidsEntry.Capabilities.Contains("ModdableFluids.Policies.WaterIntakes") && ModdableFluidsEntry.Capabilities.Contains("ModdableFluids.Policies.Irrigation"))
        DeclarePolicies(registration);
    }

    [System.Runtime.CompilerServices.MethodImpl(System.Runtime.CompilerServices.MethodImplOptions.NoInlining)]
    private static void DeclarePolicies(FluidRegistration registration) {
      registration.SetWaterIntakePolicy("Tracer", .5, Owner + ".TracerDrawnAsWater", Owner + ".Tracer.IntakeRefused", Owner + ".Tracer.IntakeRefusedAlert");
      registration.SetIrrigatesLikeWater("Tracer");
    }

    public void Activate(FluidScene scene) {
      Activations++;
      Tracer = scene.Registry.GetHandle(Owner + ".Tracer");
    }

    public void Unload(FluidScene scene) { Unloads++; Tracer = default; }

    public string SaveState(FluidScene scene) => Releases.ToString(CultureInfo.InvariantCulture) + "|" + LastTag;

    public void LoadState(FluidScene scene, bool hasState, int schemaVersion, string state) {
      if (!hasState) { Releases = 0; LastTag = ""; return; }
      // Explicit owner migration: schema 1 stored "<releases>" without a tag.
      string[] parts = schemaVersion == 1 ? new[] { state, "" } : schemaVersion == 2 ? state.Split('|') : null;
      if (parts == null || parts.Length != 2 || !int.TryParse(parts[0], NumberStyles.None, CultureInfo.InvariantCulture, out int releases))
        throw new FormatException("Unreadable synthetic tracer state (schema " + schemaVersion + "): " + state);
      Releases = releases; LastTag = parts[1];
    }
  }
}
