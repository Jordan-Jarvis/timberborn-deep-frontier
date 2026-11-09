using System;

namespace ModdableFluids.Transport.Prototype {
  /// <summary>Experimental immutable component volumes, in physical native water units.</summary>
  /// <remarks>Component positions are supplied by the caller, not persistent fluid IDs.</remarks>
  public sealed class FluidVolumes {
    private readonly double[] _volumes;
    public int ComponentCount => _volumes.Length;
    public double TotalVolume { get; }

    public FluidVolumes(double[] volumes) {
      if (volumes == null) throw new ArgumentNullException(nameof(volumes));
      if (volumes.Length < 2) throw new ArgumentException("Include fresh water and badwater components", nameof(volumes));
      _volumes = (double[])volumes.Clone();
      double total = 0;
      for (int i = 0; i < volumes.Length; i++) {
        RequireQuantity(volumes[i], "component " + i);
        total += volumes[i];
      }
      RequireQuantity(total, "total volume");
      TotalVolume = total;
    }

    public double GetVolume(int component) => _volumes[component];
    public double GetShare(int component) => TotalVolume == 0 ? 0 : _volumes[component] / TotalVolume;
    public double[] CopyVolumes() => (double[])_volumes.Clone();

    internal static void RequireQuantity(double value, string name) {
      if (double.IsNaN(value) || double.IsInfinity(value) || value < 0)
        throw new ArgumentOutOfRangeException(name, value, "Expected a finite nonnegative quantity");
    }
  }

  /// <summary>A measured transfer; destination -1 discharges outside the tracked domain.</summary>
  public readonly struct FluidTransfer {
    public int Source { get; }
    public int Destination { get; }
    public double Volume { get; }
    public FluidTransfer(int source, int destination, double volume) {
      Source = source; Destination = destination; Volume = volume;
    }
  }

  /// <summary>One eligible unordered pair of columns exchanging mixture by diffusion.</summary>
  public readonly struct FluidDiffusionLink {
    public int First { get; }
    public int Second { get; }
    public FluidDiffusionLink(int first, int second) { First = first; Second = second; }
  }

  public sealed class FluidStepResult {
    private readonly FluidVolumes[] _columns;
    private readonly FluidVolumes[] _evaporated;
    private readonly FluidVolumes[] _discharged;
    public int ColumnCount => _columns.Length;
    public FluidVolumes Discharged { get; }
    internal FluidStepResult(FluidVolumes[] columns, FluidVolumes[] evaporated, FluidVolumes discharged, FluidVolumes[] dischargedByColumn) {
      _columns = columns; _evaporated = evaporated; Discharged = discharged; _discharged = dischargedByColumn;
    }
    public FluidVolumes GetColumn(int column) => _columns[column];
    public FluidVolumes GetEvaporated(int column) => _evaporated[column];
    /// <summary>What column <paramref name="column"/> discharged off the map, or null when it discharged nothing.</summary>
    public FluidVolumes GetDischarged(int column) => _discharged[column];
  }

  public sealed class FluidRemovalResult {
    public FluidVolumes Remaining { get; }
    public FluidVolumes Removed { get; }
    internal FluidRemovalResult(FluidVolumes remaining, FluidVolumes removed) { Remaining = remaining; Removed = removed; }
  }
}
