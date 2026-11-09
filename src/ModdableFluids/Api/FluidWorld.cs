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
    /// <summary>Whether fluid state has been published: false until the scene's first native water substep.</summary>
    bool HasState { get; }
    /// <summary>The open column at map cell (x, y) whose interval contains height z.</summary>
    bool TrySample(int x, int y, int z, out FluidColumnSample sample);
    /// <summary>Every open column at map cell (x, y), lowest floor first (dry columns included).</summary>
    IReadOnlyList<FluidColumnSample> SampleCell(int x, int y);
    /// <summary>Total volume of one fluid over every column, at the last completed tick.</summary>
    double TotalVolume(FluidHandle fluid);
    /// <summary>Requests <paramref name="volume"/> of <paramref name="fluid"/> in the open column containing (x, y, z).</summary>
    void QueueAddition(int x, int y, int z, FluidHandle fluid, double volume);
    /// <summary>Sets (or with null clears) <paramref name="ownerId"/>'s override of tide-overridable source emissions.</summary>
    void SetSourceComposition(string ownerId, IReadOnlyDictionary<string, double> composition);
  }

  /// <summary>One open native column as the first fluid substep of a world sees it.</summary>
  public sealed class FluidNativeColumn {
    public int X { get; }
    public int Y { get; }
    public int Floor { get; }
    public int Ceiling { get; }
    public double Capacity { get; }
    /// <summary>Physical stored volume (native depth plus overflow).</summary>
    public double Volume { get; }
    /// <summary>Native contamination, the badwater share of <see cref="Volume"/>.</summary>
    public double BadwaterShare { get; }
    public FluidNativeColumn(int x, int y, int floor, int ceiling, double capacity, double volume, double badwaterShare) {
      if (ceiling <= floor || double.IsNaN(capacity) || capacity < ceiling - floor || double.IsNaN(volume) || double.IsInfinity(volume) || volume < 0
          || double.IsNaN(badwaterShare) || badwaterShare < 0 || badwaterShare > 1)
        throw new ArgumentOutOfRangeException(nameof(volume), "Native column (" + x + ", " + y + ", " + floor + "-" + ceiling + ") has invalid geometry, volume or contamination");
      X = x; Y = y; Floor = floor; Ceiling = ceiling; Capacity = capacity; Volume = volume; BadwaterShare = badwaterShare;
    }
  }

  /// <summary>
  /// Optional provider interface (capability <c>ModdableFluids.World.Import</c>, compiled providers only): turns
  /// another save format into the world fluid state once. Moddable Fluids asks every importer when a world's
  /// save has no <c>ModdableFluids.World</c> entry, during the first native water substep on a native worker
  /// thread, so an importer must only compute from data it read earlier (for example in its own singleton's
  /// Load). Return null when the save holds nothing for this importer. If two importers return a document the
  /// load stops naming both; the document is validated and restored like a saved one, so any disagreement
  /// with the native water fails that tick.
  /// </summary>
  public interface IFluidWorldImporter {
    FluidSaveDocument ImportWorld(FluidScene scene, IReadOnlyList<FluidNativeColumn> columns);
  }

  /// <summary>
  /// Optional provider interface (capability <c>ModdableFluids.World.Rules</c>, compiled providers only): the
  /// provider's own per-tick fluid rules, such as decay. <see cref="ApplyRules"/> runs after every completed
  /// native water tick, on the native worker thread, before the tick is published to readers; providers run
  /// in provider order. Rules can only convert volume between fluids inside one column, so native water depth
  /// and contamination are never changed. An exception fails the tick with the provider named.
  /// </summary>
  public interface IFluidColumnRules {
    void ApplyRules(FluidScene scene, IFluidColumnEditor columns);
  }

  /// <summary>The columns of a completed tick, editable by volume-preserving conversions.</summary>
  public interface IFluidColumnEditor {
    int ColumnCount { get; }
    /// <summary>Completed native water ticks, counting this one.</summary>
    int CompletedTicks { get; }
    int X(int column);
    int Y(int column);
    int Floor(int column);
    int Ceiling(int column);
    double GetVolume(int column, FluidHandle fluid);
    double TotalVolume(int column);
    /// <summary>
    /// Turns <paramref name="volume"/> of <paramref name="from"/> into <paramref name="to"/> in one column.
    /// Badwater is native contamination and cannot be converted; the volume must be positive and at most what
    /// the column holds of <paramref name="from"/>.
    /// </summary>
    void Convert(int column, FluidHandle from, FluidHandle to, double volume);
  }
}
