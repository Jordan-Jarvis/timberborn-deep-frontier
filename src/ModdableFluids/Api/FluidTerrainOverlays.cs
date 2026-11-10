using System;
using System.Globalization;

namespace ModdableFluids {
  /// <summary>
  /// The shared terrain overlay (capability <see cref="Capability"/>): a mod tints the ground of terrain cells with its
  /// own colour, drawn by the game's own soil-contamination look on per-scene copies of the native terrain materials.
  /// The game's materials are never changed. Register an overlay from <c>IModStarter.StartMod</c> with
  /// <see cref="ModdableFluidsHost.RegisterTerrainOverlay"/>, keep the returned <see cref="FluidTerrainOverlay"/>, and write
  /// per-cell values to it on the main thread while a game scene is loaded.
  ///
  /// How a value is drawn: the overlay's <see cref="FluidTerrainOverlayCurve"/> turns it into a level byte exactly as the
  /// native <c>TerrainMaterialMap</c> stores soil contamination; where overlays meet on one cell the highest level is
  /// drawn, in the level-weighted mean of their colours. Levels follow the native update rule: a change shows during
  /// the next tick (old to new, interpolated by the native tick progress) and settles at the tick after.
  /// </summary>
  public static class FluidTerrainOverlays {
    /// <summary>Listed by a runtime that implements terrain overlays.</summary>
    public const string Capability = "ModdableFluids.Rendering.TerrainOverlays";
  }

  /// <summary>
  /// Turns an overlay value into the level the native soil-contamination look draws, the way the game maps soil
  /// contamination (<c>SoilContaminationService.GetMapSoilContamination</c>): nothing below <see cref="VisibleFrom"/>, and
  /// from there a straight line that would start at <see cref="LevelAtZero"/> for a value of 0 and reaches 1 at
  /// <see cref="Full"/>, staying 1 above it. The level is stored as the native <c>PixelData</c> stores it, byte(255 * level),
  /// truncated. Deep Frontier's irradiated soil is (0.05, 0.5, 0.1): its former IrradiatedSoilSurface.Encode, byte for byte.
  /// </summary>
  public sealed class FluidTerrainOverlayCurve {
    private readonly float _fade;
    /// <summary>The value below which the overlay does not show, in (0, <see cref="Full"/>].</summary>
    public float VisibleFrom { get; }
    /// <summary>The value at and above which the level is 1; finite and positive.</summary>
    public float Full { get; }
    /// <summary>Where the line from (0, LevelAtZero) to (Full, 1) starts, in [0, 1).</summary>
    public float LevelAtZero { get; }

    public FluidTerrainOverlayCurve(float visibleFrom, float full, float levelAtZero) {
      if (float.IsNaN(full) || float.IsInfinity(full) || full <= 0) throw new ArgumentOutOfRangeException(nameof(full), full, "Full must be finite and positive");
      if (float.IsNaN(visibleFrom) || visibleFrom <= 0 || visibleFrom > full)
        throw new ArgumentOutOfRangeException(nameof(visibleFrom), visibleFrom, "VisibleFrom must be in (0, Full]: a value of 0 never shows");
      if (float.IsNaN(levelAtZero) || levelAtZero < 0 || levelAtZero >= 1) throw new ArgumentOutOfRangeException(nameof(levelAtZero), levelAtZero, "LevelAtZero must be in [0, 1)");
      VisibleFrom = visibleFrom; Full = full; LevelAtZero = levelAtZero;
      _fade = 1f - levelAtZero;
    }

    /// <summary>The level byte of <paramref name="value"/> (finite, at least 0); 0 draws nothing.</summary>
    public byte Encode(float value) {
      if (float.IsNaN(value) || float.IsInfinity(value) || value < 0)
        throw new ArgumentOutOfRangeException(nameof(value), value, "Terrain overlay values are finite and at least 0");
      if (value < VisibleFrom) return 0;
      // The expression of the native map curve and of Deep Frontier's Encode, operation for operation (min as Mathf.Min).
      float level = 1f - _fade * (1f - (value < Full ? value : Full) / Full);
      return (byte)(255f * level);
    }

    public override string ToString() => "visible from " + VisibleFrom.ToString("R", CultureInfo.InvariantCulture) + ", full at "
      + Full.ToString("R", CultureInfo.InvariantCulture) + ", level " + LevelAtZero.ToString("R", CultureInfo.InvariantCulture) + " at 0";
  }

  /// <summary>
  /// An overlay's colour: the factors the native soil-contamination texture (the veins the game draws on contaminated
  /// soil) is multiplied by, given as a material colour, the way <c>Material.SetColor</c> takes the native material's
  /// Contamination Color. In the game's gamma colour space the shader multiplies by these values as they are; a linear
  /// project would linearise them as SetColor does. Channels may exceed 1 (the veins are dark); each is finite and in
  /// [0, <see cref="MaximumChannel"/>].
  /// </summary>
  public readonly struct FluidTerrainOverlayColor : IEquatable<FluidTerrainOverlayColor> {
    /// <summary>Headroom of the half-float colour map the runtime blends overlays in.</summary>
    public const float MaximumChannel = 64f;
    public float Red { get; }
    public float Green { get; }
    public float Blue { get; }
    public FluidTerrainOverlayColor(float red, float green, float blue) {
      Require(red, nameof(red)); Require(green, nameof(green)); Require(blue, nameof(blue));
      Red = red; Green = green; Blue = blue;
    }
    private static void Require(float value, string name) {
      if (float.IsNaN(value) || float.IsInfinity(value) || value < 0 || value > MaximumChannel)
        throw new ArgumentOutOfRangeException(name, value, "Terrain overlay colour channels must be finite values in [0, " + MaximumChannel.ToString(CultureInfo.InvariantCulture) + "]");
    }
    public bool Equals(FluidTerrainOverlayColor other) => Red == other.Red && Green == other.Green && Blue == other.Blue;
    public override bool Equals(object obj) => obj is FluidTerrainOverlayColor other && Equals(other);
    public override int GetHashCode() => (Red.GetHashCode() * 31 + Green.GetHashCode()) * 31 + Blue.GetHashCode();
    public override string ToString() => "(" + Red.ToString("R", CultureInfo.InvariantCulture) + ", " + Green.ToString("R", CultureInfo.InvariantCulture) + ", "
      + Blue.ToString("R", CultureInfo.InvariantCulture) + ")";
  }

  /// <summary>
  /// One registered terrain overlay. Its values exist only while a game scene with terrain overlays is loaded
  /// (<see cref="IsAttached"/>); each scene starts with every cell at 0, and the provider writes what it wants drawn,
  /// for example from its singleton's first update or tick after loading. Write on the main thread only.
  /// </summary>
  public sealed class FluidTerrainOverlay {
    private volatile IFluidTerrainOverlaySink _sink;
    public string Id { get; }
    public string OwnerModId { get; }
    public FluidTerrainOverlayColor Color { get; }
    public FluidTerrainOverlayCurve Curve { get; }
    /// <summary>The overlay's slot among the registered overlays (ordinal ID order), fixed when the registry froze; -1 before.</summary>
    public int Index { get; private set; } = -1;
    /// <summary>Whether a game scene's terrain overlay surface is loaded.</summary>
    public bool IsAttached => _sink != null;
    /// <summary>The terrain size of the loaded scene (native <c>TerrainService.Size</c>).</summary>
    public int Width => Sink.Width;
    public int Height => Sink.Height;
    /// <summary>Terrain layers: a cell's z is the floor its ground surface is drawn at, from 0 to Depth - 1.</summary>
    public int Depth => Sink.Depth;

    internal FluidTerrainOverlay(string id, string ownerModId, FluidTerrainOverlayColor color, FluidTerrainOverlayCurve curve) {
      Id = id; OwnerModId = ownerModId; Color = color; Curve = curve;
    }

    private IFluidTerrainOverlaySink Sink => _sink ?? throw new InvalidOperationException("Terrain overlay " + Id + " has no loaded game scene to draw on");

    /// <summary>
    /// Sets the overlay's value at the ground surface of terrain cell (<paramref name="x"/>, <paramref name="y"/>) drawn at
    /// floor <paramref name="z"/>. The level (<see cref="Curve"/>) is what is drawn; a value whose level did not change
    /// changes nothing. Main thread, while <see cref="IsAttached"/>.
    /// </summary>
    public void Set(int x, int y, int z, float value) => Sink.SetLevel(Index, x, y, z, Curve.Encode(value));

    /// <summary>The level now stored at the cell (what the next tick draws).</summary>
    public byte GetLevel(int x, int y, int z) => Sink.GetLevel(Index, x, y, z);

    internal void Freeze(int index) { Index = index; }
    internal void Attach(IFluidTerrainOverlaySink sink) { _sink = sink; }
    internal void Detach() { _sink = null; }

    public override string ToString() => Id + " (mod " + OwnerModId + "): colour " + Color + ", " + Curve;
  }

  /// <summary>
  /// One game scene's terrain overlay surface, implemented by the Moddable Fluids runtime and attached through
  /// <see cref="ModdableFluidsHost.AttachTerrainOverlays"/>. Providers write through <see cref="FluidTerrainOverlay"/>.
  /// </summary>
  public interface IFluidTerrainOverlaySink {
    int Width { get; }
    int Height { get; }
    int Depth { get; }
    /// <summary>Stores overlay <paramref name="overlay"/>'s level byte at a cell; refuses a cell outside the terrain or another thread.</summary>
    void SetLevel(int overlay, int x, int y, int z, byte level);
    byte GetLevel(int overlay, int x, int y, int z);
  }
}
