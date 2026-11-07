using System;
using System.Collections.Generic;

namespace FluidsApi.Transport.Prototype {
  public readonly struct FluidColumnGeometry {
    public int NativeIndex { get; }
    public int CellIndex { get; }
    public int Floor { get; }
    public int Ceiling { get; }
    public double Capacity { get; }
    public FluidColumnGeometry(int nativeIndex, int cellIndex, int floor, int ceiling, double capacity) {
      if (nativeIndex < 0 || cellIndex < 0 || floor < 0 || ceiling < floor) throw new ArgumentException("Invalid native column geometry");
      FluidVolumes.RequireQuantity(capacity, nameof(capacity));
      if (capacity < ceiling - floor) throw new ArgumentException("Capacity is smaller than the open column");
      NativeIndex = nativeIndex; CellIndex = cellIndex; Floor = floor; Ceiling = ceiling; Capacity = capacity;
    }
  }

  public sealed class FluidGeometryResult {
    private readonly FluidVolumes[] _columns;
    public FluidVolumes GeometryLoss { get; }
    public FluidVolumes PressureLoss { get; }
    internal FluidGeometryResult(FluidVolumes[] columns, FluidVolumes geometryLoss, FluidVolumes pressureLoss) {
      _columns = columns; GeometryLoss = geometryLoss; PressureLoss = pressureLoss;
    }
    public FluidVolumes GetColumn(int slot) => _columns[slot];
  }

  public static class FluidGeometryTransport {
    /// <summary>
    /// Projects old wet intervals into new openings. Solids remove their occupied water.
    /// Pressure storage belongs to the lowest surviving overlapping opening. Merges retain
    /// all parent overflow before applying the new column's explicit pressure capacity.
    /// </summary>
    public static FluidGeometryResult Remap(FluidColumnGeometry[] before, FluidVolumes[] mixtures,
        FluidColumnGeometry[] after, int componentCount) {
      Validate(before); Validate(after);
      if (mixtures == null || mixtures.Length != before.Length || componentCount < 2) throw new ArgumentException("Geometry and mixture layouts differ");
      var next = new double[after.Length][];
      for (int n = 0; n < next.Length; n++) next[n] = new double[componentCount];
      var lost = new double[componentCount];
      var pressureLost = new FluidVolumes(new double[componentCount]);
      var byCell = new Dictionary<int, List<int>>();
      for (int n = 0; n < after.Length; n++) {
        if (!byCell.TryGetValue(after[n].CellIndex, out var indices)) { indices = new List<int>(); byCell.Add(after[n].CellIndex, indices); }
        indices.Add(n);
      }
      for (int o = 0; o < before.Length; o++) {
        var old = before[o]; var mixture = mixtures[o];
        if (mixture == null || mixture.ComponentCount != componentCount ||
            mixture.TotalVolume - old.Capacity > 4 * componentCount * 2.2204460492503131e-16 * Math.Max(mixture.TotalVolume, old.Capacity))
          throw new ArgumentException("Invalid old column mixture");
        double depth = Math.Min(mixture.TotalVolume, old.Ceiling - old.Floor);
        double overflow = mixture.TotalVolume - depth;
        var assigned = new List<KeyValuePair<int, double>>();
        double retained = 0;
        int pressureDestination = -1;
        if (!byCell.TryGetValue(old.CellIndex, out var targets)) targets = new List<int>();
        foreach (int n in targets) {
          var target = after[n];
          if (old.CellIndex != target.CellIndex || old.Floor >= target.Ceiling || target.Floor >= old.Ceiling) continue;
          if (pressureDestination < 0 || target.Floor < after[pressureDestination].Floor) pressureDestination = n;
          double overlap = Math.Min(depth, target.Ceiling - old.Floor) - Math.Max(0, target.Floor - old.Floor);
          if (overlap > 0) { assigned.Add(new KeyValuePair<int, double>(n, overlap)); retained += overlap; }
        }
        if (pressureDestination >= 0 && overflow > 0) { assigned.Add(new KeyValuePair<int, double>(pressureDestination, overflow)); retained += overflow; }
        if (retained > mixture.TotalVolume) throw new InvalidOperationException("Geometry remap allocated more than the donor volume");
        double lostFraction = mixture.TotalVolume > 0 ? (mixture.TotalVolume - retained) / mixture.TotalVolume : 0;
        for (int c = 0; c < componentCount; c++) {
          lost[c] += mixture.GetVolume(c) * lostFraction;
          foreach (var allocation in assigned) next[allocation.Key][c] += mixture.GetVolume(c) * (allocation.Value / mixture.TotalVolume);
        }
      }
      var result = new FluidVolumes[after.Length];
      for (int n = 0; n < after.Length; n++) {
        var mixture = new FluidVolumes(next[n]);
        var capped = FluidTransportPrototype.LimitCapacity(mixture, after[n].Capacity);
        result[n] = capped.Remaining;
        pressureLost = FluidTransportPrototype.Add(pressureLost, capped.Removed);
      }
      return new FluidGeometryResult(result, new FluidVolumes(lost), pressureLost);
    }

    private static void Validate(FluidColumnGeometry[] columns) {
      if (columns == null) throw new ArgumentNullException(nameof(columns));
      var nativeIndices = new HashSet<int>();
      var byCell = new Dictionary<int, List<FluidColumnGeometry>>();
      foreach (var column in columns) {
        if (!nativeIndices.Add(column.NativeIndex)) throw new ArgumentException("Duplicate native column index");
        if (!byCell.TryGetValue(column.CellIndex, out var previous)) { previous = new List<FluidColumnGeometry>(); byCell.Add(column.CellIndex, previous); }
        foreach (var old in previous) if (column.Floor < old.Ceiling && old.Floor < column.Ceiling) throw new ArgumentException("Overlapping open columns");
        previous.Add(column);
      }
    }
  }
}
