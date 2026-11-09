using System;
using System.Collections.Generic;
using System.Linq;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.Native.Prototype {
  /// <summary>One completed tick's loss entry, in padded native cell coordinates (see <see cref="FluidLoss"/> for the public form).</summary>
  public sealed class FluidLossRecord {
    public FluidLossKind Kind { get; }
    /// <summary>Padded 2D cell index: (y + 1) * stride + x + 1.</summary>
    public int CellIndex { get; }
    public int Z { get; }
    /// <summary>Layout slot during the tick, or -1 (geometry losses, dropped additions).</summary>
    public int Slot { get; }
    public string RequesterId { get; }
    public FluidVolumes Volumes { get; }
    internal FluidLossRecord(FluidLossKind kind, int cellIndex, int z, int slot, string requesterId, FluidVolumes volumes) {
      Kind = kind; CellIndex = cellIndex; Z = z; Slot = slot; RequesterId = requesterId; Volumes = volumes;
    }
  }

  /// <summary>
  /// Accumulates one tick's losses by kind, cell, height, slot and requester. Zero losses make no entry. A completed
  /// ledger is ordered by kind, cell index (y, then x), height and requester, so reports do not depend on the order
  /// of native operations within a stage.
  /// </summary>
  internal sealed class FluidLossLedger {
    private readonly Dictionary<(FluidLossKind Kind, int Cell, int Z, int Slot, string Requester), double[]> _entries =
      new Dictionary<(FluidLossKind, int, int, int, string), double[]>();
    private readonly int _components;
    internal FluidLossLedger(int components) { _components = components; }

    internal void Add(FluidLossKind kind, int cellIndex, int z, int slot, string requester, FluidVolumes volumes) {
      if (volumes == null || volumes.ComponentCount != _components) throw new ArgumentException("Component layouts differ");
      if (volumes.TotalVolume == 0) return;
      var key = (kind, cellIndex, z, slot, requester);
      if (!_entries.TryGetValue(key, out var sum)) _entries.Add(key, sum = new double[_components]);
      for (int c = 0; c < _components; c++) sum[c] += volumes.GetVolume(c);
    }

    internal FluidLossRecord[] Complete() => _entries
      .OrderBy(e => (int)e.Key.Kind).ThenBy(e => e.Key.Cell).ThenBy(e => e.Key.Z).ThenBy(e => e.Key.Requester ?? "", StringComparer.Ordinal)
      .Select(e => new FluidLossRecord(e.Key.Kind, e.Key.Cell, e.Key.Z, e.Key.Slot, e.Key.Requester, new FluidVolumes(e.Value))).ToArray();
  }
}
