using System;

namespace ModdableFluids {
  /// <summary>Why volume left the fluid world during a tick (capability <c>ModdableFluids.World.Losses</c>, 0.1.4).</summary>
  public enum FluidLossKind {
    /// <summary>Native evaporation from a column, both substeps together.</summary>
    Evaporation = 0,
    /// <summary>Flow off the map edge from a column.</summary>
    Discharge = 1,
    /// <summary>
    /// Volume above a column's pressure capacity: after transport, a blocked source emission (only its own fluid),
    /// a queued addition, or columns merged by a geometry change (on the new column).
    /// </summary>
    Pressure = 2,
    /// <summary>
    /// A native queued removal at a cell (<c>IWaterService.RemoveCleanWater</c>/<c>RemoveContaminatedWater</c>: pumps,
    /// intakes, mechanical pumps, other mods). Extra fluids drawn by a clean-water removal become native clean water;
    /// each fluid's <see cref="FluidWaterIntakePolicy.DrawnAsWater"/> names that transformation.
    /// </summary>
    NativeRemoval = 3,
    /// <summary>A native source with negative strength at a cell.</summary>
    SourceWithdrawal = 4,
    /// <summary>A Moddable Fluids extraction request (<see cref="IFluidExtraction"/>); <see cref="FluidLoss.RequesterId"/> names the requester.</summary>
    Extraction = 5,
    /// <summary>Water deleted by a geometry change (a solid placed in it, a column shrunk or removed), by the old column's (x, y, floor).</summary>
    Geometry = 6,
    /// <summary>
    /// A queued addition (<see cref="IFluidWorld.QueueAddition"/> or native clean water) whose cell had no open column at
    /// the change stage. The native game drops such a change, so this volume never entered the world.
    /// </summary>
    DroppedAddition = 7
  }

  /// <summary>
  /// One entry of a completed tick's losses: the volume of every fluid that left one place for one reason, summed over
  /// the tick. Entries are unique per kind, place and requester, and ordered by kind, then y, x, z and requester.
  /// A tick's losses run from the geometry reconciliation at its start to its native change stage.
  /// </summary>
  public sealed class FluidLoss {
    private readonly FluidRegistry _registry;
    private readonly double[] _volumes;
    public FluidLossKind Kind { get; }
    /// <summary>Unpadded map cell.</summary>
    public int X { get; }
    public int Y { get; }
    /// <summary>
    /// The column's floor for column losses (evaporation, discharge, pressure) and for geometry losses (the old
    /// column's floor); the requested cell's height for removals, withdrawals, extractions and dropped additions.
    /// </summary>
    public int Z { get; }
    /// <summary>The editor's column (layout slot) this happened in, or -1 for geometry losses and dropped additions.</summary>
    public int Column { get; }
    /// <summary>The extraction requester for <see cref="FluidLossKind.Extraction"/>; null otherwise.</summary>
    public string RequesterId { get; }
    public double TotalVolume { get; }

    public FluidLoss(FluidRegistry registry, FluidLossKind kind, int x, int y, int z, int column, string requesterId, double[] volumes) {
      _registry = registry ?? throw new ArgumentNullException(nameof(registry));
      if (volumes == null || volumes.Length != registry.Count) throw new ArgumentException("A fluid loss holds one volume per registered fluid");
      if (!Enum.IsDefined(typeof(FluidLossKind), kind)) throw new ArgumentOutOfRangeException(nameof(kind), kind, "Unknown fluid loss kind");
      if ((kind == FluidLossKind.Extraction) != (requesterId != null)) throw new ArgumentException("Only extraction losses name a requester, and they always do");
      if ((kind == FluidLossKind.Geometry || kind == FluidLossKind.DroppedAddition) != (column == -1) || column < -1)
        throw new ArgumentOutOfRangeException(nameof(column), column, kind + " losses " + (column == -1 ? "need" : "have no") + " a current column");
      _volumes = (double[])volumes.Clone();
      double total = 0;
      foreach (double v in _volumes) {
        if (double.IsNaN(v) || double.IsInfinity(v) || v < 0) throw new ArgumentOutOfRangeException(nameof(volumes), v, "Lost volumes are finite and non-negative");
        total += v;
      }
      Kind = kind; X = x; Y = y; Z = z; Column = column; RequesterId = requesterId; TotalVolume = total;
    }

    public double GetVolume(FluidHandle fluid) { _registry.Get(fluid); return _volumes[fluid.Index]; }
    public override string ToString() => Kind + " at (" + X + ", " + Y + ", " + Z + ")" + (RequesterId != null ? " by " + RequesterId : "")
      + ": " + TotalVolume.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
  }
}
