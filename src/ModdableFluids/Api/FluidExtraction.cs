using System;

namespace ModdableFluids {
  /// <summary>How an extraction request ended.</summary>
  public enum FluidExtractionOutcome {
    /// <summary>Not resolved yet.</summary>
    Pending = 0,
    /// <summary>Resolved: <see cref="IFluidExtractionRequest.ExtractedVolume"/> left the column (it can be zero when the column held none).</summary>
    Extracted = 1,
    /// <summary>The cell had no open column at the change stage; nothing was removed.</summary>
    NoColumn = 2,
    /// <summary>The fluid's share of the column was below the request's minimum share at the change stage; nothing was removed.</summary>
    BelowMinimumShare = 3
  }

  /// <summary>One extraction request and, once resolved, what it actually drew. Read it on the main thread.</summary>
  public interface IFluidExtractionRequest {
    /// <summary>Owned ID (<c>Owner.Name</c>) of the requester, reported with the tick's extraction losses.</summary>
    string RequesterId { get; }
    int X { get; }
    int Y { get; }
    int Z { get; }
    FluidHandle Fluid { get; }
    double RequestedVolume { get; }
    double MinimumShare { get; }
    FluidExtractionOutcome Outcome { get; }
    /// <summary>The volume of <see cref="Fluid"/> removed: at most the request and at most what the column held.</summary>
    double ExtractedVolume { get; }
    /// <summary>The fluid's share of the column just before the extraction; 0 for <see cref="FluidExtractionOutcome.NoColumn"/>.</summary>
    double ShareAtResolution { get; }
    /// <summary>The completed native water tick that resolved the request (0 while pending).</summary>
    int ResolvedTick { get; }
  }

  /// <summary>
  /// Component-selective removal for custom intakes (capability <c>ModdableFluids.World.Extraction</c>, 0.1.4), reached
  /// through <see cref="FluidScene.Extraction"/>. A request is made on the main thread, like a native water change. The
  /// requests made before a native water tick is scheduled are resolved in that tick's change stage, after the native
  /// queued changes, in request order: each removes up to its volume of its one fluid from the open column containing
  /// (x, y, z), and nothing else, so the column's other fluids stay. A request whose cell has no open column, or whose
  /// fluid share is below its minimum share there, removes nothing. The result is delivered once, on the main thread,
  /// after that parallel tick finished and before any save is written (at the next singleton tick, or when a save forces
  /// the tick to finish), so a building can store it in its own save data. Requests still queued when a save is
  /// written are not saved: they removed nothing, and the requester asks again after loading. The scene's unload
  /// drops unresolved requests without calling them back.
  /// </summary>
  public interface IFluidExtraction {
    /// <param name="requesterId">Owned ID of the requester, such as <c>MoreFluids.FluidExtractor</c>.</param>
    /// <param name="volume">Finite and positive.</param>
    /// <param name="minimumShare">In [0, 1]: the share of <paramref name="fluid"/> the column needs at the change stage.</param>
    /// <param name="resolved">Called once on the main thread with the resolved request; it must take the extracted volume.</param>
    IFluidExtractionRequest RequestExtraction(string requesterId, int x, int y, int z, FluidHandle fluid, double volume, double minimumShare,
      Action<IFluidExtractionRequest> resolved);
  }
}
