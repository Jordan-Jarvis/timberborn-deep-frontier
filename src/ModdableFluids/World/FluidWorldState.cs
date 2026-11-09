using System;
using System.Collections.Generic;
using System.Linq;
using ModdableFluids.Native.Prototype;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.World.Prototype {
  /// <summary>
  /// The thread-safe core of the world fluid service. <see cref="Publish"/> copies the session's layout and
  /// (immutable) mixtures at a completed-tick barrier and swaps them in atomically, so readers on any thread
  /// sample a whole tick. The addition ledger pairs each requested fluid addition with the native water change
  /// that carries its volume (same cell, same float volume, first in first out). One owner at a time may
  /// override tide-overridable source emissions.
  /// </summary>
  public sealed class FluidWorldState {
    private sealed class Snapshot {
      internal readonly FluidColumnGeometry[] Layout;
      internal readonly FluidVolumes[] Mixtures;
      internal readonly Dictionary<int, int[]> ByCell;
      internal readonly int Ticks;
      internal Snapshot(FluidColumnGeometry[] layout, FluidVolumes[] mixtures, int ticks) {
        Layout = layout; Mixtures = mixtures; Ticks = ticks;
        ByCell = Enumerable.Range(0, layout.Length).GroupBy(i => layout[i].CellIndex).ToDictionary(g => g.Key, g => g.ToArray());
      }
    }
    private readonly object _gate = new object();
    private readonly Dictionary<(int, int, int), Queue<(float Volume, int Component)>> _pending = new Dictionary<(int, int, int), Queue<(float, int)>>();
    private volatile Snapshot _snapshot;
    private string _compositionOwner;
    private IReadOnlyDictionary<string, double> _composition;
    public FluidRegistry Registry { get; }
    public int Stride { get; }
    public int CompletedTicks => _snapshot?.Ticks ?? 0;
    public bool HasSnapshot => _snapshot != null;

    public FluidWorldState(FluidRegistry registry, int stride) {
      Registry = registry ?? throw new ArgumentNullException(nameof(registry));
      if (stride < 3) throw new ArgumentOutOfRangeException(nameof(stride));
      Stride = stride;
    }

    /// <summary>Publishes the session at a completed tick (its Ready phase). Mixtures are immutable; only arrays are copied.</summary>
    public void Publish(NativeFluidTransportSession session) {
      if (session == null) throw new ArgumentNullException(nameof(session));
      if (session.Phase != "Ready") throw new InvalidOperationException("Fluid state is published only at a completed tick; the session is " + session.Phase);
      if (session.ComponentCount != Registry.Count) throw new InvalidOperationException("The session layout differs from the registry");
      var layout = new FluidColumnGeometry[session.ColumnCount];
      var mixtures = new FluidVolumes[session.ColumnCount];
      for (int i = 0; i < layout.Length; i++) { layout[i] = session.GetGeometry(i); mixtures[i] = session.Sample(layout[i].NativeIndex); }
      _snapshot = new Snapshot(layout, mixtures, session.CompletedTicks);
    }

    public bool TrySample(int x, int y, int z, out FluidColumnSample sample) {
      sample = null;
      var snapshot = _snapshot ?? throw new InvalidOperationException("No completed fluid tick has been published yet");
      if (!snapshot.ByCell.TryGetValue((y + 1) * Stride + x + 1, out var slots)) return false;
      foreach (int slot in slots) {
        var geometry = snapshot.Layout[slot];
        if (z < geometry.Floor || z >= geometry.Ceiling) continue;
        sample = new FluidColumnSample(geometry.Floor, geometry.Ceiling, snapshot.Mixtures[slot].CopyVolumes());
        return true;
      }
      return false;
    }

    /// <summary>Every open column at (x, y), lowest floor first; empty outside the map or where the cell is solid.</summary>
    public IReadOnlyList<FluidColumnSample> SampleCell(int x, int y) {
      var snapshot = _snapshot ?? throw new InvalidOperationException("No completed fluid tick has been published yet");
      if (x < 0 || x >= Stride - 2 || y < 0 || !snapshot.ByCell.TryGetValue((y + 1) * Stride + x + 1, out var slots)) return Array.Empty<FluidColumnSample>();
      return slots.OrderBy(slot => snapshot.Layout[slot].Floor)
        .Select(slot => new FluidColumnSample(snapshot.Layout[slot].Floor, snapshot.Layout[slot].Ceiling, snapshot.Mixtures[slot].CopyVolumes())).ToArray();
    }

    public double TotalVolume(FluidHandle fluid) {
      Registry.Get(fluid);
      var snapshot = _snapshot ?? throw new InvalidOperationException("No completed fluid tick has been published yet");
      double total = 0;
      foreach (var mixture in snapshot.Mixtures) total += mixture.GetVolume(fluid.Index);
      return total;
    }

    /// <summary>Records a requested addition before its native water change is queued (main thread).</summary>
    public void RecordAddition(int x, int y, int z, FluidHandle fluid, double volume) {
      var definition = Registry.Get(fluid);
      if (definition.NativeRole == FluidNativeRole.Badwater) throw new ArgumentException("Badwater additions use the native contaminated-water change");
      if (double.IsNaN(volume) || double.IsInfinity(volume) || volume <= 0) throw new ArgumentOutOfRangeException(nameof(volume), volume, "Additions are finite and positive");
      lock (_gate) {
        if (!_pending.TryGetValue((x, y, z), out var queue)) _pending.Add((x, y, z), queue = new Queue<(float, int)>());
        queue.Enqueue(((float)volume, fluid.Index));
      }
    }

    public int PendingAdditions { get { lock (_gate) return _pending.Values.Sum(q => q.Count); } }

    /// <summary>
    /// The mixture for a native clean-water addition at (x, y, z): a recorded addition of the same float volume,
    /// oldest first, or false for an ordinary native addition.
    /// </summary>
    public bool TryResolveAddition(int x, int y, int z, double nativeVolume, out FluidVolumes mixture) {
      mixture = null;
      lock (_gate) {
        if (!_pending.TryGetValue((x, y, z), out var queue) || queue.Count == 0 || queue.Peek().Volume != (float)nativeVolume) return false;
        var (_, component) = queue.Dequeue();
        if (queue.Count == 0) _pending.Remove((x, y, z));
        var values = new double[Registry.Count];
        values[component] = nativeVolume;
        mixture = new FluidVolumes(values);
        return true;
      }
    }

    /// <summary>Sets or clears (null) an owner's source composition override; a second owner is a visible conflict.</summary>
    public void SetSourceComposition(string ownerId, IReadOnlyDictionary<string, double> composition) {
      if (string.IsNullOrWhiteSpace(ownerId)) throw new ArgumentException("A source composition needs its owner");
      lock (_gate) {
        if (composition == null) {
          if (_compositionOwner == ownerId) { _compositionOwner = null; _composition = null; }
          return;
        }
        if (_compositionOwner != null && _compositionOwner != ownerId)
          throw new InvalidOperationException("Source composition is already overridden by " + _compositionOwner + "; " + ownerId + " cannot override it at the same time");
        double total = 0;
        foreach (var pair in composition.OrderBy(p => p.Key, StringComparer.Ordinal)) {
          if (!Registry.TryGet(pair.Key, out var fluid) || fluid.NativeRole != FluidNativeRole.Extra) throw new ArgumentException(ownerId + " overrides sources with " + pair.Key + ", which is not a registered extra fluid");
          if (double.IsNaN(pair.Value) || pair.Value <= 0 || pair.Value > 1) throw new ArgumentOutOfRangeException(nameof(composition), pair.Value, "Shares are in (0, 1]");
          total += pair.Value;
        }
        if (total > 1) throw new ArgumentException(ownerId + "'s source composition totals above one");
        _compositionOwner = ownerId;
        _composition = new Dictionary<string, double>(composition.ToDictionary(p => p.Key, p => p.Value), StringComparer.Ordinal);
      }
    }

    public IReadOnlyDictionary<string, double> ActiveSourceComposition { get { lock (_gate) return _composition; } }
  }
}
