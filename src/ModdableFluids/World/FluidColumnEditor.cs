using System;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.World.Prototype {
  /// <summary>
  /// The <see cref="IFluidColumnEditor"/> handed to provider rules for one completed tick. It addresses
  /// layout slots of the session and is closed when the rules return, so a provider cannot keep it.
  /// </summary>
  public sealed class FluidColumnEditor : IFluidColumnEditor {
    private readonly NativeFluidTransportSession _session;
    private readonly FluidRegistry _registry;
    private readonly int _stride;
    private bool _closed;
    public FluidColumnEditor(NativeFluidTransportSession session, FluidRegistry registry, int stride) {
      _session = session ?? throw new ArgumentNullException(nameof(session));
      _registry = registry ?? throw new ArgumentNullException(nameof(registry));
      if (session.ComponentCount != registry.Count) throw new InvalidOperationException("The session layout differs from the registry");
      if (stride < 3) throw new ArgumentOutOfRangeException(nameof(stride));
      _stride = stride;
    }
    public int ColumnCount { get { Open(); return _session.ColumnCount; } }
    public int CompletedTicks { get { Open(); return _session.CompletedTicks; } }
    public int X(int column) => Geometry(column).CellIndex % _stride - 1;
    public int Y(int column) => Geometry(column).CellIndex / _stride - 1;
    public int Floor(int column) => Geometry(column).Floor;
    public int Ceiling(int column) => Geometry(column).Ceiling;
    public double GetVolume(int column, FluidHandle fluid) => _session.Sample(Geometry(column).NativeIndex).GetVolume(Index(fluid));
    public double TotalVolume(int column) => _session.Sample(Geometry(column).NativeIndex).TotalVolume;
    public void Convert(int column, FluidHandle from, FluidHandle to, double volume) {
      Geometry(column);
      _session.ConvertComponent(column, Index(from), Index(to), volume);
    }
    public void Close() => _closed = true;
    private int Index(FluidHandle fluid) { _registry.Get(fluid); return fluid.Index; }
    private FluidColumnGeometry Geometry(int column) {
      Open();
      if (column < 0 || column >= _session.ColumnCount) throw new ArgumentOutOfRangeException(nameof(column), column, "No such column");
      return _session.GetGeometry(column);
    }
    private void Open() { if (_closed) throw new InvalidOperationException("A fluid column editor is valid only while the rules run"); }
  }
}
