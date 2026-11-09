using System;
using System.Collections.Generic;
using System.Linq;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>A timed radioactive water source (AddContinuousSource), as RadiationSimulation saves it.</summary>
  public sealed class RadiationSourceRecord {
    public int Id { get; }
    public Vector3Int Cell { get; }
    public float VolumePerHour { get; }
    public float RemainingHours { get; set; }
    public RadiationSourceRecord(int id, Vector3Int cell, float volumePerHour, float remainingHours) {
      Id = id; Cell = cell; VolumePerHour = volumePerHour; RemainingHours = remainingHours;
    }
  }

  /// <summary>
  /// The <c>DeepFrontier.Radiation</c> singleton as RadiationSimulation writes it (versions 2 and 3): cells are
  /// (x, y, column floor). Kept verbatim until the first fluid substep imports its water, so a save made before
  /// then writes it back unchanged.
  /// </summary>
  public sealed class RadiationLegacyRecord {
    public const int SludgeVersion = 2, LastVersion = 3;
    public int Version { get; }
    public bool Snapshot { get; }
    public IReadOnlyList<Vector3Int> Cells { get; }
    public IReadOnlyList<float> WaterRadiation { get; }
    public IReadOnlyList<float> Soil { get; }
    /// <summary>Version 2 only; null for version 3.</summary>
    public IReadOnlyList<float> Sludge { get; }
    public IReadOnlyList<RadiationSourceRecord> Sources { get; }
    public int NextSourceId { get; }
    public float HourAccumulator { get; }

    public RadiationLegacyRecord(int version, bool snapshot, IList<Vector3Int> cells, IList<float> waterRadiation, IList<float> soil, IList<float> sludge,
        IList<RadiationSourceRecord> sources, int nextSourceId, float hourAccumulator) {
      if (version != SludgeVersion && version != LastVersion)
        throw new InvalidOperationException("Unsupported radiation save version " + version + " (supported: " + SludgeVersion + " converted, " + LastVersion + ")");
      int n = cells.Count;
      if (waterRadiation.Count != n || soil.Count != n || (version == SludgeVersion ? sludge == null || sludge.Count != n : sludge != null))
        throw new InvalidOperationException("Radiation save lists have different lengths");
      if (sources.Any(s => s.Id >= nextSourceId)) throw new InvalidOperationException("Saved radiation source id is not below NextSourceId");
      Version = version; Snapshot = snapshot; Cells = cells.ToArray(); WaterRadiation = waterRadiation.ToArray(); Soil = soil.ToArray();
      Sludge = sludge?.ToArray(); Sources = sources.ToArray(); NextSourceId = nextSourceId; HourAccumulator = hourAccumulator;
    }
  }

  /// <summary>
  /// Version 4 of <c>DeepFrontier.Radiation</c>, written by the Moddable Fluids build: the water is saved by
  /// Moddable Fluids, so Deep Frontier keeps soil by (x, y, column floor), timed sources, its hour counter, and the
  /// requests no fluid tick has applied yet (soil additions, and radioactive water added before the first fluid tick).
  /// </summary>
  public sealed class RadiationFacadeRecord {
    public const int Version = 4;
    public IReadOnlyList<Vector3Int> SoilCells { get; }
    public IReadOnlyList<float> Soil { get; }
    public IReadOnlyList<RadiationSourceRecord> Sources { get; }
    public int NextSourceId { get; }
    public float HourAccumulator { get; }
    public IReadOnlyList<(Vector3Int Cell, float Amount)> PendingSoil { get; }
    public IReadOnlyList<(Vector3Int Cell, float Volume)> EarlyWater { get; }
    public RadiationFacadeRecord(IList<Vector3Int> soilCells, IList<float> soil, IList<RadiationSourceRecord> sources, int nextSourceId, float hourAccumulator,
        IList<(Vector3Int, float)> pendingSoil, IList<(Vector3Int, float)> earlyWater) {
      if (soil.Count != soilCells.Count) throw new InvalidOperationException("Radiation soil save lists have different lengths");
      if (soil.Any(s => !(s > 0) || s > 1)) throw new InvalidOperationException("Saved soil radiation is within (0, 1]");
      if (soilCells.Distinct().Count() != soilCells.Count) throw new InvalidOperationException("Saved soil radiation lists a cell twice");
      if (sources.Any(s => s.Id >= nextSourceId)) throw new InvalidOperationException("Saved radiation source id is not below NextSourceId");
      if (!(hourAccumulator >= 0) || float.IsInfinity(hourAccumulator)) throw new InvalidOperationException("Saved radiation hour counter " + hourAccumulator + " is invalid");
      if (pendingSoil.Concat(earlyWater).Any(p => !(p.Item2 > 0) || float.IsInfinity(p.Item2))) throw new InvalidOperationException("Saved pending radiation amounts are positive and finite");
      SoilCells = soilCells.ToArray(); Soil = soil.ToArray(); Sources = sources.ToArray(); NextSourceId = nextSourceId; HourAccumulator = hourAccumulator;
      PendingSoil = pendingSoil.ToArray(); EarlyWater = earlyWater.ToArray();
    }

    /// <summary>The facade's state at a completed tick: the last published soil pass, sources and unapplied requests.</summary>
    public static RadiationFacadeRecord Capture(ModdableFluidsRadiationService facade) {
      var pass = facade.Soil.Published;
      var cells = pass.Soil.Keys.OrderBy(c => c.y).ThenBy(c => c.x).ThenBy(c => c.z).ToArray();
      return new RadiationFacadeRecord(cells, cells.Select(c => pass.Soil[c]).ToArray(),
        facade.Sources.Select(s => new RadiationSourceRecord(s.Id, s.Cell, s.VolumePerHour, s.RemainingHours)).ToArray(), facade.NextSourceId, pass.HourAccumulator,
        facade.Soil.PendingRequests.Select(r => (r.Cell, r.Amount)).ToArray(), facade.EarlyAdditions.Select(r => (r.Cell, r.Volume)).ToArray());
    }

    /// <summary>Loads this record into a facade whose soil field has not run a pass (singleton Load).</summary>
    public void Restore(ModdableFluidsRadiationService facade) {
      facade.Soil.Load(SoilCells, Soil, HourAccumulator, lenient: false);
      facade.LoadSources(Sources, NextSourceId);
      foreach (var (cell, amount) in PendingSoil) facade.Soil.RequestSoil(cell, amount);
      facade.LoadEarlyAdditions(EarlyWater);
    }
  }
}
