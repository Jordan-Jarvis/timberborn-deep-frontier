using System;
using System.Collections.Generic;

namespace ModdableFluids {
  /// <summary>One open column at a completed tick: its interval, physical volume and component volumes.</summary>
  public sealed class FluidColumnSample {
    private readonly double[] _volumes;
    public int Floor { get; }
    public int Ceiling { get; }
    /// <summary>Physical stored volume (native depth plus overflow).</summary>
    public double TotalVolume { get; }
    public FluidColumnSample(int floor, int ceiling, double[] volumes) {
      if (volumes == null) throw new ArgumentNullException(nameof(volumes));
      Floor = floor; Ceiling = ceiling; _volumes = (double[])volumes.Clone();
      double total = 0;
      foreach (double v in _volumes) total += v;
      TotalVolume = total;
    }
    public double GetVolume(FluidHandle fluid) => _volumes[fluid.Index];
    public double GetShare(FluidHandle fluid) => TotalVolume == 0 ? 0 : _volumes[fluid.Index] / TotalVolume;
    /// <summary>Whether the water surface lies above height <paramref name="z"/> (depth counted from the floor).</summary>
    public bool Covers(int z) => TotalVolume > 0 && z >= Floor && z < Floor + TotalVolume;
  }

  /// <summary>
  /// The world fluid service (capabilities <c>ModdableFluids.World.Sampling</c>, <c>.Additions</c> and
  /// <c>.SourceComposition</c>). Sampling reads the state published at the last completed tick, so it is safe
  /// from any game thread and never sees a half-finished tick. Additions are requests: each becomes a native
  /// water change carrying the named fluid and takes effect at the next native water-change stage. A source
  /// composition override replaces what tide-overridable source types emit (a tide); only one owner may hold
  /// one at a time, and a second owner fails instead of winning by load order.
  /// </summary>
  public interface IFluidWorld {
    FluidRegistry Registry { get; }
    /// <summary>Completed native water ticks since the scene attached.</summary>
    int CompletedTicks { get; }
    /// <summary>The open column at map cell (x, y) whose interval contains height z.</summary>
    bool TrySample(int x, int y, int z, out FluidColumnSample sample);
    /// <summary>Total volume of one fluid over every column, at the last completed tick.</summary>
    double TotalVolume(FluidHandle fluid);
    /// <summary>Requests <paramref name="volume"/> of <paramref name="fluid"/> in the open column containing (x, y, z).</summary>
    void QueueAddition(int x, int y, int z, FluidHandle fluid, double volume);
    /// <summary>Sets (or with null clears) <paramref name="ownerId"/>'s override of tide-overridable source emissions.</summary>
    void SetSourceComposition(string ownerId, IReadOnlyDictionary<string, double> composition);
  }
}
