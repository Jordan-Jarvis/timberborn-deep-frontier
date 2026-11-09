using System;
using System.Collections.Generic;
using System.Threading;
using ModdableFluids.Native.Prototype;

namespace ModdableFluids.World.Prototype {
  /// <summary>One extraction request; its result fields are written once by the change stage and read on the main thread.</summary>
  public sealed class FluidExtractionTicket : IFluidExtractionRequest {
    private int _outcome;
    private double _extracted, _share;
    private int _tick;
    internal readonly Action<IFluidExtractionRequest> Callback;
    public string RequesterId { get; }
    public int X { get; }
    public int Y { get; }
    public int Z { get; }
    public FluidHandle Fluid { get; }
    public double RequestedVolume { get; }
    public double MinimumShare { get; }
    public FluidExtractionOutcome Outcome => (FluidExtractionOutcome)Volatile.Read(ref _outcome);
    public double ExtractedVolume { get { RequireResolved(); return _extracted; } }
    public double ShareAtResolution { get { RequireResolved(); return _share; } }
    public int ResolvedTick => Outcome == FluidExtractionOutcome.Pending ? 0 : _tick;
    internal FluidExtractionTicket(string requesterId, int x, int y, int z, FluidHandle fluid, double volume, double minimumShare, Action<IFluidExtractionRequest> callback) {
      RequesterId = requesterId; X = x; Y = y; Z = z; Fluid = fluid; RequestedVolume = volume; MinimumShare = minimumShare; Callback = callback;
    }
    internal void Resolve(FluidExtractionOutcome outcome, double extracted, double share, int tick) {
      if (Outcome != FluidExtractionOutcome.Pending) throw new InvalidOperationException("Extraction request by " + RequesterId + " was resolved twice");
      _extracted = extracted; _share = share; _tick = tick;
      Volatile.Write(ref _outcome, (int)outcome);
    }
    private void RequireResolved() {
      if (Outcome == FluidExtractionOutcome.Pending) throw new InvalidOperationException("Extraction request by " + RequesterId + " at (" + X + ", " + Y + ", " + Z + ") is still pending");
    }
    public override string ToString() => RequesterId + " extracts " + RequestedVolume.ToString("R", System.Globalization.CultureInfo.InvariantCulture)
      + " at (" + X + ", " + Y + ", " + Z + "): " + Outcome;
  }

  /// <summary>
  /// Extraction requests between the main thread and the native change stage. <see cref="Request"/> and
  /// <see cref="TakeBatch"/> run on the main thread (the batch is taken when a native water tick is scheduled);
  /// <see cref="Resolve"/> runs in that tick's change job on a worker; <see cref="DeliverResolved"/> runs on the main
  /// thread after the parallel tick finished and calls each requester once, in request order.
  /// </summary>
  public sealed class FluidExtractionQueue {
    private readonly object _gate = new object();
    private readonly FluidRegistry _registry;
    private readonly int _width, _height;
    private List<FluidExtractionTicket> _queued = new List<FluidExtractionTicket>();
    private readonly List<FluidExtractionTicket> _resolved = new List<FluidExtractionTicket>();
    private bool _closed;

    public FluidExtractionQueue(FluidRegistry registry, int width, int height) {
      _registry = registry ?? throw new ArgumentNullException(nameof(registry));
      if (width < 1 || height < 1) throw new ArgumentOutOfRangeException(nameof(width), "Invalid map size");
      _width = width; _height = height;
    }

    public int Queued { get { lock (_gate) return _queued.Count; } }
    public int AwaitingDelivery { get { lock (_gate) return _resolved.Count; } }

    public FluidExtractionTicket Request(string requesterId, int x, int y, int z, FluidHandle fluid, double volume, double minimumShare, Action<IFluidExtractionRequest> resolved) {
      if (!FluidIds.TrySplit(requesterId, out _, out _)) throw new ArgumentException("Invalid extraction requester '" + requesterId + "': expected <OwnerModId>.<LocalName>");
      _registry.Get(fluid);
      if (x < 0 || x >= _width || y < 0 || y >= _height || z < 0) throw new ArgumentOutOfRangeException(nameof(x), "Extraction cell (" + x + ", " + y + ", " + z + ") lies outside the map");
      if (double.IsNaN(volume) || double.IsInfinity(volume) || volume <= 0) throw new ArgumentOutOfRangeException(nameof(volume), volume, "An extraction requests a finite positive volume");
      if (double.IsNaN(minimumShare) || minimumShare < 0 || minimumShare > 1) throw new ArgumentOutOfRangeException(nameof(minimumShare), minimumShare, "Minimum shares are in [0, 1]");
      if (resolved == null) throw new ArgumentNullException(nameof(resolved), "An extraction needs a callback that takes the extracted volume");
      var ticket = new FluidExtractionTicket(requesterId, x, y, z, fluid, volume, minimumShare, resolved);
      lock (_gate) {
        if (_closed) throw new InvalidOperationException("The fluid scene was unloaded; no extraction can be requested");
        _queued.Add(ticket);
      }
      return ticket;
    }

    /// <summary>Main thread, when a native water tick is scheduled: the requests that tick resolves.</summary>
    public FluidExtractionTicket[] TakeBatch() {
      lock (_gate) {
        if (_queued.Count == 0) return Array.Empty<FluidExtractionTicket>();
        var batch = _queued.ToArray(); _queued = new List<FluidExtractionTicket>();
        return batch;
      }
    }

    /// <summary>
    /// The change stage, after the native queued changes: resolves each request in order. <paramref name="findColumn"/>
    /// returns the native index of the open column containing (x, y, z), or false.
    /// </summary>
    public void Resolve(FluidExtractionTicket[] batch, NativeFluidTransportSession session, FindColumn findColumn) {
      if (batch == null || session == null || findColumn == null) throw new ArgumentNullException("extraction resolution input");
      int tick = session.CompletedTicks + 1;
      foreach (var ticket in batch) {
        if (!findColumn(ticket.X, ticket.Y, ticket.Z, out int nativeIndex)) { ticket.Resolve(FluidExtractionOutcome.NoColumn, 0, 0, tick); continue; }
        double extracted = session.Extract(nativeIndex, ticket.Z, ticket.Fluid.Index, ticket.RequestedVolume, ticket.MinimumShare, ticket.RequesterId, out double share);
        ticket.Resolve(share < ticket.MinimumShare ? FluidExtractionOutcome.BelowMinimumShare : FluidExtractionOutcome.Extracted, extracted, share, tick);
      }
      if (batch.Length > 0) lock (_gate) _resolved.AddRange(batch);
    }

    public delegate bool FindColumn(int x, int y, int z, out int nativeIndex);

    /// <summary>Main thread, after a parallel tick finished: calls back every resolved request once, in request order.</summary>
    public int DeliverResolved() {
      FluidExtractionTicket[] delivered;
      lock (_gate) {
        if (_resolved.Count == 0) return 0;
        delivered = _resolved.ToArray(); _resolved.Clear();
      }
      foreach (var ticket in delivered) ticket.Callback(ticket);
      return delivered.Length;
    }

    /// <summary>Scene unload: unresolved and undelivered requests are dropped without callbacks; later requests fail.</summary>
    public void Close() {
      lock (_gate) { _closed = true; _queued.Clear(); _resolved.Clear(); }
    }
  }
}
