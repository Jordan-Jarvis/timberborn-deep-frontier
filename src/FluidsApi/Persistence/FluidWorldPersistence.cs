using System;
using System.Collections.Generic;
using System.Linq;
using FluidsApi.Native.Prototype;
using FluidsApi.Transport.Prototype;

namespace FluidsApi.Persistence.Prototype {
  /// <summary>Component state restored onto the current native layout, with any projection losses.</summary>
  public sealed class FluidRestoreResult {
    private readonly FluidVolumes[] _columns;
    public int ColumnCount => _columns.Length;
    /// <summary>Saved columns copied unchanged onto an identical current column.</summary>
    public int ExactColumns { get; }
    /// <summary>Saved columns projected onto changed geometry.</summary>
    public int ProjectedColumns { get; }
    public FluidVolumes GeometryLoss { get; }
    public FluidVolumes PressureLoss { get; }
    internal FluidRestoreResult(FluidVolumes[] columns, int exact, int projected, FluidVolumes geometryLoss, FluidVolumes pressureLoss) {
      _columns = columns; ExactColumns = exact; ProjectedColumns = projected; GeometryLoss = geometryLoss; PressureLoss = pressureLoss;
    }
    /// <summary>The mixture for current layout slot <paramref name="slot"/>, in registry component order.</summary>
    public FluidVolumes GetColumn(int slot) => _columns[slot];
  }

  /// <summary>
  /// Experimental bridge between the transport session and the public save schema. Capture only at a
  /// completed-tick barrier. Restore maps saved fluids by canonical ID, copies columns whose cell,
  /// interval and capacity are unchanged bit for bit, and projects the rest with the shared geometry
  /// rules, reporting geometry and pressure losses. Applying checks every column against the native
  /// physical volume and faults the session on any mismatch; a faulted session must be discarded.
  /// </summary>
  public static class FluidWorldPersistence {
    public static FluidSaveDocument Capture(FluidRegistry registry, NativeFluidTransportSession session, int stride,
        IReadOnlyList<FluidProviderState> providerStates) {
      if (registry == null || session == null || providerStates == null) throw new ArgumentNullException("capture input");
      if (session.Phase != "Ready") throw new InvalidOperationException("Fluid state can only be saved at a completed-tick barrier; the session is in " + session.Phase);
      RequireLayout(registry, session.ComponentCount, session.BadwaterComponent);
      if (stride < 3) throw new ArgumentOutOfRangeException(nameof(stride));
      var used = new bool[registry.Count];
      var wet = new List<(FluidColumnGeometry Geometry, FluidVolumes Mixture)>();
      for (int slot = 0; slot < session.ColumnCount; slot++) {
        var geometry = session.GetGeometry(slot);
        var mixture = session.Sample(geometry.NativeIndex);
        if (mixture.TotalVolume == 0) continue;
        wet.Add((geometry, mixture));
        for (int c = 0; c < mixture.ComponentCount; c++) if (mixture.GetVolume(c) > 0) used[c] = true;
      }
      var savedIndex = new int[registry.Count];
      var ids = new List<string>(); var owners = new List<string>();
      for (int c = 0; c < registry.Count; c++) {
        savedIndex[c] = -1;
        if (!used[c]) continue;
        savedIndex[c] = ids.Count;
        ids.Add(registry.Definitions[c].Id); owners.Add(registry.Definitions[c].OwnerModId);
      }
      var x = new List<int>(); var y = new List<int>(); var floor = new List<int>(); var ceiling = new List<int>(); var capacity = new List<string>();
      var entryColumn = new List<int>(); var entryFluid = new List<int>(); var entryVolume = new List<string>();
      foreach (var (geometry, mixture) in wet) {
        int column = x.Count;
        x.Add(geometry.CellIndex % stride - 1); y.Add(geometry.CellIndex / stride - 1);
        floor.Add(geometry.Floor); ceiling.Add(geometry.Ceiling); capacity.Add(FluidSaveDocument.EncodeQuantity(geometry.Capacity));
        for (int c = 0; c < mixture.ComponentCount; c++) {
          double volume = mixture.GetVolume(c);
          if (volume == 0) continue;
          entryColumn.Add(column); entryFluid.Add(savedIndex[c]); entryVolume.Add(FluidSaveDocument.EncodeQuantity(volume));
        }
      }
      var states = providerStates.OrderBy(s => s.ProviderId, StringComparer.Ordinal).ToArray();
      return new FluidSaveDocument(FluidSaveDocument.CurrentSchemaVersion, FluidsApiHost.ApiVersion, registry.Fingerprint, ids, owners,
        x, y, floor, ceiling, capacity, entryColumn, entryFluid, entryVolume,
        states.Select(s => s.ProviderId).ToArray(), states.Select(s => s.OwnerModId).ToArray(),
        states.Select(s => s.SchemaVersion).ToArray(), states.Select(s => s.Data).ToArray());
    }

    public static FluidRestoreResult Restore(FluidSaveDocument document, FluidRegistry registry, FluidColumnGeometry[] currentLayout, int stride, int height) {
      if (document == null || registry == null || currentLayout == null) throw new ArgumentNullException("restore input");
      int width = stride - 2;
      if (width < 1 || height < 1) throw new ArgumentOutOfRangeException(nameof(stride), "Invalid native map size");
      int[] slots = document.ResolveFluidSlots(registry);
      int components = registry.Count;
      var saved = new FluidColumnGeometry[document.ColumnCount];
      var mixtures = new double[document.ColumnCount][];
      for (int k = 0; k < saved.Length; k++) {
        if (document.ColumnX[k] >= width || document.ColumnY[k] >= height)
          throw new FluidSaveException(new[] { "Saved fluid column (" + document.ColumnX[k] + ", " + document.ColumnY[k] + ") lies outside the " + width + " by " + height + " map" });
        int cell = (document.ColumnY[k] + 1) * stride + document.ColumnX[k] + 1;
        saved[k] = new FluidColumnGeometry(k, cell, document.ColumnFloor[k], document.ColumnCeiling[k], document.GetCapacity(k));
        mixtures[k] = new double[components];
      }
      for (int e = 0; e < document.EntryColumn.Count; e++) mixtures[document.EntryColumn[e]][slots[document.EntryFluid[e]]] = document.GetVolume(e);
      var result = new FluidVolumes[currentLayout.Length];
      var empty = new FluidVolumes(new double[components]);
      var byInterval = new Dictionary<(int Cell, int Floor, int Ceiling), int>();
      for (int i = 0; i < currentLayout.Length; i++) byInterval.Add((currentLayout[i].CellIndex, currentLayout[i].Floor, currentLayout[i].Ceiling), i);
      // Exact copies only where one saved column maps onto an identical current column that no other
      // saved column overlaps; everything else goes through the shared projection together.
      var overlapping = new int[currentLayout.Length];
      var byCell = currentLayout.Select((g, i) => (g, i)).GroupBy(v => v.g.CellIndex).ToDictionary(g => g.Key, g => g.ToArray());
      foreach (var old in saved)
        if (byCell.TryGetValue(old.CellIndex, out var targets))
          foreach (var (g, i) in targets) if (old.Floor < g.Ceiling && g.Floor < old.Ceiling) overlapping[i]++;
      var projectedOld = new List<int>();
      var exactTargets = new HashSet<int>();
      for (int k = 0; k < saved.Length; k++) {
        if (byInterval.TryGetValue((saved[k].CellIndex, saved[k].Floor, saved[k].Ceiling), out int target) && overlapping[target] == 1 &&
            BitConverter.DoubleToInt64Bits(currentLayout[target].Capacity) == BitConverter.DoubleToInt64Bits(saved[k].Capacity)) {
          result[target] = new FluidVolumes(mixtures[k]);
          exactTargets.Add(target);
        } else projectedOld.Add(k);
      }
      var geometryLoss = empty; var pressureLoss = empty;
      if (projectedOld.Count > 0) {
        var newSlots = Enumerable.Range(0, currentLayout.Length).Where(i => !exactTargets.Contains(i)).ToArray();
        var remapped = FluidGeometryTransport.Remap(projectedOld.Select(k => saved[k]).ToArray(),
          projectedOld.Select(k => new FluidVolumes(mixtures[k])).ToArray(), newSlots.Select(i => currentLayout[i]).ToArray(), components);
        for (int n = 0; n < newSlots.Length; n++) result[newSlots[n]] = remapped.GetColumn(n);
        geometryLoss = remapped.GeometryLoss; pressureLoss = remapped.PressureLoss;
      }
      for (int i = 0; i < result.Length; i++) if (result[i] == null) result[i] = empty;
      return new FluidRestoreResult(result, exactTargets.Count, projectedOld.Count, geometryLoss, pressureLoss);
    }

    /// <summary>Seeds every current column. Any disagreement with native water faults the session.</summary>
    public static void Apply(NativeFluidTransportSession session, FluidRegistry registry, FluidRestoreResult restored, int stride) {
      if (session == null || registry == null || restored == null) throw new ArgumentNullException("apply input");
      RequireLayout(registry, session.ComponentCount, session.BadwaterComponent);
      if (restored.ColumnCount != session.ColumnCount) throw new ArgumentException("Restored layout differs from the session's native layout");
      for (int slot = 0; slot < session.ColumnCount; slot++) {
        var geometry = session.GetGeometry(slot);
        try { session.SeedComposition(geometry.NativeIndex, restored.GetColumn(slot)); }
        catch (Exception e) when (e is InvalidOperationException || e is ArgumentException) {
          session.AbortTick();
          throw new FluidSaveException(new[] { "Saved fluid state disagrees with native water at (" + (geometry.CellIndex % stride - 1) + ", "
            + (geometry.CellIndex / stride - 1) + ", floor " + geometry.Floor + "): " + e.Message + ". The fluid session was discarded." });
        }
      }
    }

    private static void RequireLayout(FluidRegistry registry, int components, int badwater) {
      if (components != registry.Count || badwater != FluidRegistry.BadwaterIndex)
        throw new InvalidOperationException("The transport session layout (" + components + " components, badwater " + badwater
          + ") does not match registry " + registry.Fingerprint.Substring(0, 12) + " (" + registry.Count + " components, badwater " + FluidRegistry.BadwaterIndex + ")");
    }
  }
}
