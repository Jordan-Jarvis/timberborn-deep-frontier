using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

namespace ModdableFluids {
  /// <summary>
  /// Terrain overlays (<see cref="FluidTerrainOverlays"/>): registered while providers register, closed with them when the
  /// registry freezes, and attached to one game scene's surface at a time.
  /// </summary>
  public sealed partial class ModdableFluidsHost {
    private readonly List<FluidTerrainOverlay> _terrainOverlays = new List<FluidTerrainOverlay>();
    private IReadOnlyList<FluidTerrainOverlay> _frozenTerrainOverlays;
    private IFluidTerrainOverlaySink _terrainSink;

    /// <summary>
    /// Registers terrain overlay <paramref name="id"/> (<c>&lt;OwnerModId&gt;.&lt;LocalName&gt;</c>) for every game scene of
    /// this process. Call it from <c>IModStarter.StartMod</c>: registrations close when the registry freezes, before the
    /// first game scene. Keep the returned overlay to write its values.
    /// </summary>
    public FluidTerrainOverlay RegisterTerrainOverlay(string id, string ownerModId, FluidTerrainOverlayColor color, FluidTerrainOverlayCurve curve) {
      if (curve == null) throw new ArgumentNullException(nameof(curve));
      FluidIds.RequireOwned(id, ownerModId, "terrain overlay ID");
      if (string.Equals(ownerModId, FluidIds.BuiltInOwner, StringComparison.Ordinal)) throw new ArgumentException("Terrain overlay " + id + " uses the reserved owner '" + FluidIds.BuiltInOwner + "'");
      lock (_gate) {
        if (_state != State.Open)
          throw new InvalidOperationException("Moddable Fluids registrations are closed (" + _state + "): the registry froze before the first game scene. Register terrain overlay "
            + id + " from IModStarter.StartMod.");
        if (_terrainOverlays.Any(o => string.Equals(o.Id, id, StringComparison.Ordinal))) throw new ArgumentException("Terrain overlay " + id + " is registered twice");
        var overlay = new FluidTerrainOverlay(id, ownerModId, color, curve);
        _terrainOverlays.Add(overlay);
        return overlay;
      }
    }

    /// <summary>The registered terrain overlays in ordinal ID order (their <see cref="FluidTerrainOverlay.Index"/>), once the registry froze.</summary>
    public IReadOnlyList<FluidTerrainOverlay> TerrainOverlays { get { lock (_gate) return FrozenTerrainOverlays(); } }

    /// <summary>Whether a game scene's terrain overlay surface is attached.</summary>
    public bool TerrainOverlaysAttached { get { lock (_gate) return _terrainSink != null; } }

    /// <summary>Attaches one game scene's surface: every overlay writes to it until <see cref="DetachTerrainOverlays"/>.</summary>
    public void AttachTerrainOverlays(IFluidTerrainOverlaySink sink) {
      if (sink == null) throw new ArgumentNullException(nameof(sink));
      lock (_gate) {
        var overlays = FrozenTerrainOverlays();
        if (_terrainSink != null) throw new InvalidOperationException("A terrain overlay surface is still attached; detach it before attaching another scene's");
        _terrainSink = sink;
        foreach (var overlay in overlays) overlay.Attach(sink);
      }
    }

    /// <summary>Detaches the scene's surface attached with <see cref="AttachTerrainOverlays"/>; overlays cannot be written until the next scene.</summary>
    public void DetachTerrainOverlays(IFluidTerrainOverlaySink sink) {
      lock (_gate) {
        if (sink == null || !ReferenceEquals(sink, _terrainSink)) throw new InvalidOperationException("Expected the attached terrain overlay surface");
        foreach (var overlay in _frozenTerrainOverlays) overlay.Detach();
        _terrainSink = null;
      }
    }

    // Under _gate. The order, and so each overlay's index, is fixed on the first read after the freeze.
    private IReadOnlyList<FluidTerrainOverlay> FrozenTerrainOverlays() {
      if (_state == State.Faulted) throw _fault;
      if (_state != State.Frozen) throw new InvalidOperationException("Terrain overlays are listed once the Moddable Fluids registry froze, before the first game scene loads");
      if (_frozenTerrainOverlays == null) {
        var ordered = _terrainOverlays.OrderBy(o => o.Id, StringComparer.Ordinal).ToArray();
        for (int i = 0; i < ordered.Length; i++) ordered[i].Freeze(i);
        _frozenTerrainOverlays = new ReadOnlyCollection<FluidTerrainOverlay>(ordered);
      }
      return _frozenTerrainOverlays;
    }
  }
}
