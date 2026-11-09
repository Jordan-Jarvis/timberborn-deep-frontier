using System;
using System.Collections.Generic;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// Deep Frontier's radioactive water as a Moddable Fluids provider (migration groundwork: compiled only into the
  /// flagged DEEP_FRONTIER_MODDABLE_FLUIDS build and the harness, never into the shipped package). It registers the
  /// fluid and its two springs as source types, imports a <c>DeepFrontier.Radiation</c> version 2 or 3 save once,
  /// and applies Deep Frontier's own water and soil rules after every completed fluid tick (<see cref="RadiationSoilField"/>:
  /// decay, the soil-water exchange, the 0.5% cutoff, deposition of lost radioactive water, soil spread). The rules
  /// are Deep Frontier's: nothing here is a Moddable Fluids default.
  /// </summary>
  public sealed class DeepFrontierRadioactiveWater : IFluidProvider, IFluidSceneProvider, IFluidWorldImporter, IFluidColumnRules {
    public const string Owner = "DeepFrontier";
    public const string Id = Owner + ".Radiation";
    public const string FluidId = Owner + ".RadioactiveWater";
    /// <summary>The springs' native strength: RadioactiveSpring and RadioactiveSpringSource blueprints.</summary>
    public const float SpringStrength = 0.026041666666666668f;
    public static readonly string[] SpringTemplates = { "RadioactiveSpring", "RadioactiveSpringSource" };
    /// <summary>The springs' radioactive share of their non-bad water (RadioactiveWaterSourceSpec.RadioactiveShare in both blueprints).</summary>
    public const float SpringShare = 1f;
    /// <summary>
    /// Radioactive water blocks soil moisture exactly like badwater: RadiationSoil's moisture shadow showed the native
    /// moisture tasks b + r. Moddable Fluids shows them b + share x M / this, so this is M, the native
    /// SoilMoistureSimulatorSpec.MaximumWaterContamination of 1.1.2.8 (checked against the game in ModdableFluidsBankLayer).
    /// </summary>
    public const float MoistureBlockShare = 0.53f;
    /// <summary>What a native pump draws of radioactive water below the refusal share becomes clean water (as in the one-fluid build).</summary>
    public const string DrawnAsWater = Owner + ".RadioactiveWaterDrawnAsWater";

    private readonly object _gate = new object();
    private RadiationLegacyRecord _pendingImport;
    private RadiationMigrationResult _imported;
    private RadiationSoilField _field;
    private readonly RadioactiveTideRegistration _tide;

    /// <param name="tide">The radioactive tide to register (the game passes it; harness scenarios may leave it out).</param>
    public DeepFrontierRadioactiveWater(RadioactiveTideRegistration tide = null) {
      _tide = tide;
      var capabilities = new List<string> {
        "ModdableFluids.Policies.Irrigation", "ModdableFluids.Policies.WaterIntakes", "ModdableFluids.Registry.Definitions", "ModdableFluids.Scene.Lifecycle",
        "ModdableFluids.Sources.Types", "ModdableFluids.World.Additions", "ModdableFluids.World.Import", "ModdableFluids.World.Losses", "ModdableFluids.World.Rules",
        "ModdableFluids.World.Sampling" };
      if (tide != null) capabilities.Add(FluidTideRules.RegistrationCapability);
      RequiredCapabilities = capabilities;
    }

    public string ProviderId => Id;
    public string OwnerModId => Owner;
    public string MinimumApiVersion => "0.1.3";
    public IReadOnlyCollection<string> RequiredCapabilities { get; }
    public bool RegistersTide => _tide != null;

    /// <summary>The active scene, between Activate and Unload.</summary>
    public FluidScene Scene { get; private set; }
    public FluidHandle Radioactive => Scene?.Registry.GetHandle(FluidId) ?? throw new InvalidOperationException("No active fluid scene");

    public void Register(FluidRegistration registration) {
      // Between the radioactive shader's base colours A (0.50, 0.56, 0.04) and B (0.86, 0.92, 0.08).
      // The good of the same name is this water in a barrel ("Radioactive water").
      registration.AddFluid("RadioactiveWater", "Good." + RadiationTuning.SludgeGoodId + ".DisplayName", .68f, .74f, .06f, .85f);
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.DetectionLimit", "0.005");
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.Good", RadiationTuning.SludgeGoodId);
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.VolumePerGood", "0.2");
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.WaterHalfLifeDays", "365");
      // RadiationIntakeGuard: native pumps stop at the detection limit and draw less as clean water.
      registration.SetWaterIntakePolicy("RadioactiveWater", RadiationTuning.DetectionLimit, DrawnAsWater, RadiationLoc.PumpBlocked, RadiationLoc.PumpBlockedShort);
      registration.SetBlocksMoisture("RadioactiveWater", MoistureBlockShare);
      foreach (string template in SpringTemplates) {
        registration.AddSourceType(template, "Building." + template + ".DisplayName", template, 1, SpringStrength, true, false, false);
        registration.SetSourceEmission(template, FluidId, SpringShare);
      }
      _tide?.Register(registration);
    }

    public void Activate(FluidScene scene) {
      if (Scene != null) throw new InvalidOperationException("Deep Frontier radioactive water is still attached to fluid scene " + Scene.Serial);
      Scene = scene;
      lock (_gate) _imported = null;
    }

    public void Unload(FluidScene scene) {
      if (!ReferenceEquals(Scene, scene)) throw new InvalidOperationException("Deep Frontier radioactive water was not attached to fluid scene " + scene?.Serial);
      Scene = null;
      lock (_gate) { _pendingImport = null; _imported = null; _field = null; }
    }

    /// <summary>
    /// Main thread, in Deep Frontier's singleton Load (before Moddable Fluids activates the scene): the scene's soil
    /// field (which knows the hours per native water tick) and its legacy save record, if it has one.
    /// </summary>
    public void PrepareScene(RadiationSoilField field, RadiationLegacyRecord legacy) {
      lock (_gate) { _field = field ?? throw new ArgumentNullException(nameof(field)); _pendingImport = legacy; _imported = null; }
    }

    /// <summary>Whether a legacy record still waits for the first fluid substep to import it.</summary>
    public bool ImportPending { get { lock (_gate) return _pendingImport != null; } }

    /// <summary>The legacy record not yet imported (saved again unchanged if the world is saved before its first fluid tick).</summary>
    public RadiationLegacyRecord PendingRecord { get { lock (_gate) return _pendingImport; } }

    /// <summary>Main thread: the import result once, after the first fluid substep imported it.</summary>
    public RadiationMigrationResult TakeImportResult() {
      lock (_gate) { var result = _imported; _imported = null; return result; }
    }

    // Native worker thread, first substep of a world without Moddable Fluids data.
    public FluidSaveDocument ImportWorld(FluidScene scene, IReadOnlyList<FluidNativeColumn> columns) {
      lock (_gate) {
        if (!ReferenceEquals(scene, Scene)) throw new InvalidOperationException("Import for an inactive fluid scene");
        if (_pendingImport == null) return null;
        var record = _pendingImport;
        _imported = RadiationSaveMigration.Import(scene.Registry, record, columns, Array.Empty<FluidProviderState>());
        _pendingImport = null;
        return _imported.Document;
      }
    }

    // Native worker thread, after every completed fluid tick.
    public void ApplyRules(FluidScene scene, IFluidColumnEditor columns) {
      RadiationSoilField field;
      lock (_gate) field = _field;
      if (field == null) throw new InvalidOperationException("Deep Frontier did not prepare the fluid scene (its soil field)");
      field.ApplyRules(columns, scene.Registry.GetHandle(FluidId), scene.Registry.Water);
    }
  }
}
