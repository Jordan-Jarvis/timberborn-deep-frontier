using DeepFrontier.Scripts.Radiation;
using ModdableFluids;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// Irradiated ground in the Moddable Fluids build (migration groundwork, never in the shipped package): Deep Frontier's
  /// soil tint as a Moddable Fluids terrain overlay (capability <c>ModdableFluids.Rendering.TerrainOverlays</c>) instead
  /// of its own terrain shader variant on the native terrain materials. The curve is IrradiatedSoilSurface.Encode's
  /// (RadiationShading.cs): nothing below <see cref="MinRenderedSoil"/>, where plants die
  /// (RadiationTuning.IrradiatedGroundThreshold), then a native-like map value from <see cref="MinMapValue"/> at 0 to 1 at
  /// <see cref="FullSoil"/>; the harness compares these constants and Encode's source text with RadiationShading.cs and
  /// checks the encoding byte for byte. The colour is IrradiatedSoilSurface.SoilColor, passed by the game glue.
  /// </summary>
  public static class IrradiatedSoilOverlay {
    public const string Id = DeepFrontierRadioactiveWater.Owner + ".IrradiatedSoil";
    // IrradiatedSoilSurface.MinRenderedSoil, FullSoil and MinMapValue.
    public const float MinRenderedSoil = RadiationTuning.IrradiatedGroundThreshold;
    public const float FullSoil = 0.5f;
    public const float MinMapValue = 0.1f;

    public static FluidTerrainOverlayCurve Curve() => new FluidTerrainOverlayCurve(MinRenderedSoil, FullSoil, MinMapValue);

    /// <summary>Registers the overlay at mod start; <paramref name="color"/> is the material colour Deep Frontier's variant was given.</summary>
    public static FluidTerrainOverlay Register(ModdableFluidsHost host, FluidTerrainOverlayColor color) =>
      host.RegisterTerrainOverlay(Id, DeepFrontierRadioactiveWater.Owner, color, Curve());
  }
}
