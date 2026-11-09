using System;
using System.Collections.Generic;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.World.Prototype {
  /// <summary>The water-intake guard's decision: which extra fluids refuse a column (share at or above their refusal share).</summary>
  public static class FluidIntakeRefusal {
    /// <summary>Handle indices of the fluids whose policy refuses <paramref name="sample"/>, in registry order; empty when it is accepted.</summary>
    public static IReadOnlyList<int> Refusing(FluidRegistry registry, FluidColumnSample sample) {
      if (registry == null) throw new ArgumentNullException(nameof(registry));
      if (sample == null || sample.TotalVolume == 0) return Array.Empty<int>();
      List<int> refusing = null;
      for (int i = 0; i < registry.Count; i++) {
        var definition = registry.Definitions[i];
        if (definition.NativeRole != FluidNativeRole.Extra) continue;
        var policy = definition.WaterIntake ?? throw new InvalidOperationException("Fluid " + definition.Id + " has no water-intake policy; Moddable Fluids should not have attached");
        if (sample.GetShare(registry.GetHandle(definition.Id)) >= policy.RefuseAtShare) (refusing ?? (refusing = new List<int>())).Add(i);
      }
      return (IReadOnlyList<int>)refusing ?? Array.Empty<int>();
    }
  }

  /// <summary>
  /// The soil-moisture input: how much each native thread-safe water column's contamination rises for the native
  /// moisture tasks, from the fluids that block moisture (<see cref="FluidIrrigationPolicy"/>). A column whose
  /// geometry is the published column's takes that column's shares; a column the main thread reshaped since the
  /// published tick (a native obstacle change before the next fluid substep reconciles it) takes the shares of the
  /// published columns of its cell, weighted by how much of their wet interval it overlaps, the interval rule of
  /// geometry reconciliation. Fluids that irrigate like water add nothing.
  /// </summary>
  public sealed class FluidMoistureShadow {
    private readonly double[] _weights;
    private readonly int _verticalStride;
    /// <summary>Whether any registered fluid blocks moisture; without one, the native input is never replaced.</summary>
    public bool HasBlockingFluids { get; }

    /// <param name="maximumWaterContamination">Native <c>SoilMoistureSimulatorSpec.MaximumWaterContamination</c>: where badwater gives no moisture.</param>
    public FluidMoistureShadow(FluidRegistry registry, double maximumWaterContamination, int stride, int verticalStride) {
      if (registry == null) throw new ArgumentNullException(nameof(registry));
      if (double.IsNaN(maximumWaterContamination) || maximumWaterContamination <= 0 || maximumWaterContamination > 1)
        throw new ArgumentOutOfRangeException(nameof(maximumWaterContamination), maximumWaterContamination, "The native maximum water contamination is in (0, 1]");
      if (stride < 3 || verticalStride < stride * 3 || verticalStride % stride != 0) throw new ArgumentOutOfRangeException(nameof(stride), "Invalid native index layout");
      _verticalStride = verticalStride;
      _weights = new double[registry.Count];
      foreach (var definition in registry.Definitions) {
        if (definition.NativeRole != FluidNativeRole.Extra) continue;
        var policy = definition.Irrigation ?? throw new InvalidOperationException("Fluid " + definition.Id + " has no irrigation policy; Moddable Fluids should not have attached");
        if (policy.Effect != FluidMoistureEffect.BlocksLikeBadwater) continue;
        _weights[registry.GetHandle(definition.Id).Index] = maximumWaterContamination / policy.BlocksAtShare;
        HasBlockingFluids = true;
      }
    }

    /// <summary>The contamination a mixture adds: the sum of each blocking fluid's share times its weight.</summary>
    public double Contribution(FluidVolumes mixture) {
      if (mixture == null || mixture.ComponentCount != _weights.Length) throw new ArgumentException("Component layouts differ");
      if (mixture.TotalVolume == 0) return 0;
      double added = 0;
      for (int c = 0; c < _weights.Length; c++) if (_weights[c] > 0) added += mixture.GetShare(c) * _weights[c];
      return added;
    }

    /// <summary>The thread-safe column at native index <c>cell + ordinal * verticalStride</c>: its floor and ceiling.</summary>
    public delegate void ReadColumn(int nativeIndex, out int floor, out int ceiling);

    /// <summary>
    /// Fills <paramref name="additions"/> with (native index, contamination to add) for every thread-safe column that holds
    /// a blocking fluid, from the published tick (<paramref name="layout"/>, <paramref name="mixtures"/>). Returns the count.
    /// </summary>
    public int Compute(FluidColumnGeometry[] layout, FluidVolumes[] mixtures, Func<int, int> columnCount, ReadColumn readColumn, List<KeyValuePair<int, double>> additions) {
      if (layout == null || mixtures == null || layout.Length != mixtures.Length || columnCount == null || readColumn == null || additions == null)
        throw new ArgumentException("Invalid moisture input");
      additions.Clear();
      if (!HasBlockingFluids) return 0;
      Dictionary<int, List<int>> blockingCells = null;
      for (int slot = 0; slot < layout.Length; slot++) {
        if (Contribution(mixtures[slot]) == 0) continue;
        if (blockingCells == null) blockingCells = new Dictionary<int, List<int>>();
        if (!blockingCells.ContainsKey(layout[slot].CellIndex)) blockingCells.Add(layout[slot].CellIndex, new List<int>());
      }
      if (blockingCells == null) return 0;
      for (int slot = 0; slot < layout.Length; slot++) if (blockingCells.TryGetValue(layout[slot].CellIndex, out var slots)) slots.Add(slot);
      var cells = new List<int>(blockingCells.Keys);
      cells.Sort();
      foreach (int cell in cells) {
        var slots = blockingCells[cell];
        int count = columnCount(cell);
        for (int ordinal = 0; ordinal < count; ordinal++) {
          int nativeIndex = cell + ordinal * _verticalStride;
          readColumn(nativeIndex, out int floor, out int ceiling);
          double added = 0;
          int same = slots.FindIndex(s => layout[s].NativeIndex == nativeIndex && layout[s].Floor == floor && layout[s].Ceiling == ceiling);
          if (same >= 0) added = Contribution(mixtures[slots[same]]);
          else {
            double weighted = 0, weight = 0;
            foreach (int s in slots) {
              var old = layout[s];
              double wetTop = old.Floor + Math.Min(mixtures[s].TotalVolume, old.Ceiling - old.Floor);
              double overlap = Math.Min(wetTop, ceiling) - Math.Max(old.Floor, floor);
              if (overlap <= 0) continue;
              weighted += overlap * Contribution(mixtures[s]); weight += overlap;
            }
            if (weight > 0) added = weighted / weight;
          }
          if (added > 0) additions.Add(new KeyValuePair<int, double>(nativeIndex, added));
        }
      }
      return additions.Count;
    }
  }
}
