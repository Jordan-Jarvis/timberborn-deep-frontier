using System;
using System.Collections.Generic;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// Deep Frontier's radioactive water as a Moddable Fluids provider (migration groundwork: compiled only into the
  /// flagged DEEP_FRONTIER_MODDABLE_FLUIDS build and the harness, never into the shipped package). It registers the
  /// fluid and its two springs as source types, imports a <c>DeepFrontier.Radiation</c> version 2 or 3 save once,
  /// and applies Deep Frontier's own water rules after every completed fluid tick: decay with a 365-day half-life
  /// and the 0.5% detection cutoff for a share that stopped growing (RadiationSimulation.RunInteraction and
  /// Rescan). Both turn radioactive water into fresh water in place, as setting r lower does there. The rules are
  /// Deep Frontier's: nothing here is a Moddable Fluids default.
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

    private readonly object _gate = new object();
    private RadiationLegacyRecord _pendingImport;
    private RadiationMigrationResult _imported;
    private Dictionary<(int, int, int), double> _previous = new Dictionary<(int, int, int), double>();
    private Dictionary<(int, int, int), double> _next = new Dictionary<(int, int, int), double>();
    private double _hoursPerTick;

    public string ProviderId => Id;
    public string OwnerModId => Owner;
    public string MinimumApiVersion => "0.1.3";
    public IReadOnlyCollection<string> RequiredCapabilities { get; } = new[] {
      "ModdableFluids.Registry.Definitions", "ModdableFluids.Scene.Lifecycle", "ModdableFluids.Sources.Types", "ModdableFluids.World.Additions",
      "ModdableFluids.World.Import", "ModdableFluids.World.Rules", "ModdableFluids.World.Sampling", "ModdableFluids.World.SourceComposition" };

    /// <summary>The active scene, between Activate and Unload.</summary>
    public FluidScene Scene { get; private set; }
    public FluidHandle Radioactive => Scene?.Registry.GetHandle(FluidId) ?? throw new InvalidOperationException("No active fluid scene");

    public void Register(FluidRegistration registration) {
      // Between the radioactive shader's base colours A (0.50, 0.56, 0.04) and B (0.86, 0.92, 0.08).
      registration.AddFluid("RadioactiveWater", "DeepFrontier.RadioactiveWater.DisplayName", .68f, .74f, .06f, .85f);
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.DetectionLimit", "0.005");
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.Good", RadiationTuning.SludgeGoodId);
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.VolumePerGood", "0.2");
      registration.AddMetadata("RadioactiveWater", "DeepFrontier.WaterHalfLifeDays", "365");
      foreach (string template in SpringTemplates) {
        registration.AddSourceType(template, "DeepFrontier." + template + ".DisplayName", template, 1, SpringStrength, true, false, false);
        registration.SetSourceEmission(template, FluidId, SpringShare);
      }
    }

    public void Activate(FluidScene scene) {
      if (Scene != null) throw new InvalidOperationException("Deep Frontier radioactive water is still attached to fluid scene " + Scene.Serial);
      Scene = scene;
      lock (_gate) { _previous.Clear(); _imported = null; }
    }

    public void Unload(FluidScene scene) {
      if (!ReferenceEquals(Scene, scene)) throw new InvalidOperationException("Deep Frontier radioactive water was not attached to fluid scene " + scene?.Serial);
      Scene = null;
      lock (_gate) { _pendingImport = null; _imported = null; _previous.Clear(); _hoursPerTick = 0; }
    }

    /// <summary>
    /// Main thread, in Deep Frontier's singleton Load (before Moddable Fluids activates the scene): the scene's
    /// in-game hours per native water tick and its legacy save record, if it has one.
    /// </summary>
    public void PrepareScene(double hoursPerTick, RadiationLegacyRecord legacy) {
      if (!(hoursPerTick > 0) || double.IsInfinity(hoursPerTick)) throw new ArgumentOutOfRangeException(nameof(hoursPerTick), hoursPerTick, "Hours per tick are positive");
      lock (_gate) { _hoursPerTick = hoursPerTick; _pendingImport = legacy; _imported = null; }
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
      double hours;
      lock (_gate) hours = _hoursPerTick;
      if (!(hours > 0)) throw new InvalidOperationException("Deep Frontier did not prepare the fluid scene (hours per tick)");
      var radioactive = scene.Registry.GetHandle(FluidId);
      var water = scene.Registry.Water;
      double decay = RadiationTuning.DecayPerHour(RadiationTuning.RadiationHalfLifeDays) * hours;
      _next.Clear();
      for (int c = 0; c < columns.ColumnCount; c++) {
        double volume = columns.GetVolume(c, radioactive);
        if (!(volume > 0)) continue;
        double total = columns.TotalVolume(c);
        double share = volume / total;
        double kept = share - share * decay;
        if (kept < RadiationTuning.MinWaterRadiation) kept = 0;
        var key = (columns.X(c), columns.Y(c), columns.Floor(c));
        // The cutoff: below the detection limit and not grown since the last tick.
        if (kept < RadiationTuning.DetectionLimit && !(kept > (_previous.TryGetValue(key, out double before) ? before : 0))) kept = 0;
        double removed = kept == 0 ? volume : volume - kept * total;
        if (removed > 0) columns.Convert(c, radioactive, water, Math.Min(removed, volume));
        if (kept > 0) _next[key] = kept;
      }
      var swap = _previous; _previous = _next; _next = swap;
    }
  }
}
