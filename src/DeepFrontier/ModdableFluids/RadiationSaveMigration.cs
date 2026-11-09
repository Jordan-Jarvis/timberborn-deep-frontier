using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using ModdableFluids;

namespace DeepFrontier.ModdableFluidsMigration {
  public sealed class RadiationMigrationResult {
    public FluidSaveDocument Document { get; }
    /// <summary>Version 2 sludge to add as radioactive water on the first tick: (x, y, floor, volume).</summary>
    public IReadOnlyList<(int X, int Y, int Floor, double Volume)> SludgeAdditions { get; }
    /// <summary>Radioactive volume below Deep Frontier's 0.5% detection limit, removed as that rule does.</summary>
    public double CutoffVolume { get; }
    /// <summary>Exception-save cells without a matching column, or capped above 1 - b, dropped as Deep Frontier's lenient snapshot load does.</summary>
    public IReadOnlyList<string> SnapshotCorrections { get; }
    internal RadiationMigrationResult(FluidSaveDocument document, List<(int, int, int, double)> sludge, double cutoff, List<string> corrections) {
      Document = document; SludgeAdditions = sludge; CutoffVolume = cutoff; SnapshotCorrections = corrections;
    }
  }

  /// <summary>
  /// Reads the <c>DeepFrontier.Radiation</c> singleton (versions 2 and 3) into the Moddable Fluids world save, once.
  /// Radioactive volume = the saved share x the column's physical volume (version 2: share x (1 - b), its sludge
  /// queued as radioactive additions), badwater = native contamination, fresh water = the rest. Deep Frontier's
  /// own load rules are kept (RadiationSimulation.ApplyLoaded): shares below its 0.5% detection limit read as
  /// zero, and an exception snapshot (LastCompletedTickSnapshot) drops cells whose column moved and caps r at
  /// 1 - b, each reported. A normal save with either problem stops loading. Soil, sources and counters stay with
  /// Deep Frontier. Computed in double precision from the saved floats.
  /// </summary>
  public static class RadiationSaveMigration {
    public static RadiationMigrationResult Import(FluidRegistry registry, RadiationLegacyRecord record, IReadOnlyList<FluidNativeColumn> columns,
        IReadOnlyList<FluidProviderState> providerStates) {
      if (registry == null || record == null || columns == null || providerStates == null) throw new ArgumentNullException("migration input");
      int version = record.Version, n = record.Cells.Count;
      bool snapshot = record.Snapshot;
      double limit = RadiationTuning.DetectionLimit;
      var radioactive = registry.GetHandle(DeepFrontierRadioactiveWater.FluidId);
      var byCell = new Dictionary<(int, int, int), int>();
      for (int c = 0; c < columns.Count; c++) byCell.Add((columns[c].X, columns[c].Y, columns[c].Floor), c);
      var share = new double[columns.Count];
      var problems = new List<string>(); var corrections = new List<string>(); var additions = new List<(int, int, int, double)>();
      double cutoff = 0;
      for (int k = 0; k < n; k++) {
        var at = record.Cells[k];
        string cell = "(" + at.x + ", " + at.y + ", " + at.z + ")";
        if (version == RadiationLegacyRecord.SludgeVersion && record.Sludge[k] > 0) additions.Add((at.x, at.y, at.z, record.Sludge[k]));
        float saved = record.WaterRadiation[k];
        if (float.IsNaN(saved) || saved < 0 || saved > 1) { problems.Add("Saved radiation " + saved.ToString("R", CultureInfo.InvariantCulture) + " at " + cell + " is not a share"); continue; }
        if (saved == 0) continue;
        if (!byCell.TryGetValue((at.x, at.y, at.z), out int column)) {
          if (snapshot) { corrections.Add("dropped " + cell + ": no column with that floor"); continue; }
          problems.Add("Saved radiation at " + cell + " has no native column with that floor"); continue;
        }
        double bad = columns[column].BadwaterShare;
        double r = version == RadiationLegacyRecord.SludgeVersion ? saved * (1 - bad) : saved;
        if (r < limit) { cutoff += r * columns[column].Volume; continue; }
        if (r + bad > 1 + RadiationTuning.ShareTolerance) {
          if (!snapshot) { problems.Add("Saved radiation " + r.ToString("R", CultureInfo.InvariantCulture) + " at " + cell + " plus badwater exceeds the column"); continue; }
          corrections.Add("capped " + cell + " at 1 - b");
          if (1 - bad < limit) { cutoff += Math.Max(0, 1 - bad) * columns[column].Volume; continue; }
          r = 1 - bad;
        }
        share[column] = Math.Min(r, 1 - bad);
      }
      if (problems.Count > 0) throw new FluidSaveException(problems);
      // The saved table lists only fluids with volume, as FluidWorldPersistence.Capture does.
      var wet = Enumerable.Range(0, columns.Count).Where(c => columns[c].Volume > 0).ToArray();
      bool anyBad = wet.Any(c => columns[c].BadwaterShare > 0), anyRadioactive = wet.Any(c => share[c] > 0);
      bool anyWater = wet.Any(c => 1 - columns[c].BadwaterShare - share[c] > 0);
      var ids = new List<string>(); var owners = new List<string>(); var slot = new Dictionary<int, int>();
      void Use(bool used, FluidHandle handle) { if (!used) return; var d = registry.Get(handle); slot[handle.Index] = ids.Count; ids.Add(d.Id); owners.Add(d.OwnerModId); }
      Use(anyWater, registry.Water); Use(anyBad, registry.Badwater); Use(anyRadioactive, radioactive);
      var x = new List<int>(); var y = new List<int>(); var floor = new List<int>(); var ceiling = new List<int>(); var capacity = new List<string>();
      var entryColumn = new List<int>(); var entryFluid = new List<int>(); var entryVolume = new List<string>();
      foreach (int c in wet) {
        var col = columns[c];
        int index = x.Count;
        x.Add(col.X); y.Add(col.Y); floor.Add(col.Floor); ceiling.Add(col.Ceiling); capacity.Add(FluidSaveDocument.EncodeQuantity(col.Capacity));
        void Entry(FluidHandle handle, double volume) {
          if (volume <= 0) return;
          entryColumn.Add(index); entryFluid.Add(slot[handle.Index]); entryVolume.Add(FluidSaveDocument.EncodeQuantity(volume));
        }
        // Each component from its own share, so none is a difference of near-equal volumes.
        Entry(registry.Water, col.Volume * (1 - col.BadwaterShare - share[c]));
        Entry(registry.Badwater, col.Volume * col.BadwaterShare);
        Entry(radioactive, col.Volume * share[c]);
      }
      var states = providerStates.OrderBy(s => s.ProviderId, StringComparer.Ordinal).ToArray();
      var document = new FluidSaveDocument(FluidSaveDocument.CurrentSchemaVersion, ModdableFluidsHost.ApiVersion, registry.Fingerprint, ids, owners,
        x, y, floor, ceiling, capacity, entryColumn, entryFluid, entryVolume,
        states.Select(s => s.ProviderId).ToArray(), states.Select(s => s.OwnerModId).ToArray(), states.Select(s => s.SchemaVersion).ToArray(), states.Select(s => s.Data).ToArray());
      return new RadiationMigrationResult(document, additions, cutoff, corrections);
    }
  }
}
