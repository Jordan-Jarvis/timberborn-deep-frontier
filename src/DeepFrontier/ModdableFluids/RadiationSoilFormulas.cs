using System;
using DeepFrontier.Scripts.Radiation;
using UnityEngine;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// RadiationSoil's soil-water formulas for the Moddable Fluids build. The bodies of <see cref="SoilWaterExchange"/>,
  /// <see cref="Rinse"/> and <see cref="KernelContamination"/> and both constants are copied from
  /// src/DeepFrontier/Scripts/Radiation/RadiationSoil.cs without a change; the fluid harness compares the source text
  /// of each against RadiationSoil.cs, so the two copies cannot drift apart. RadiationSoil itself cannot be compiled
  /// here (it reads the native soil simulation), and the shipped file keeps its own copy.
  /// </summary>
  public static class RadiationSoilFormulas {
    public const float VolumePerSoil = 1f / RadiationTuning.SoilPerDepositedVolume;
    public const float RinseShareCap = 0.5f * RadiationTuning.DetectionLimit;

    // Rinsing under clean water: the soil falls at the native rate whatever
    // the depth. The water takes the washed radioactive volume up to
    // RinseShareCap (below DetectionLimit, so rinse water never reads
    // radioactive); the rest counts as diluted below the cutoff and is gone,
    // as the cutoff removes it from flowing water anyway. Returns the soil
    // change (negative) and the new share.
    public static float Rinse(float s, float r, float b, float d, float maxWash, out float share) {
      if (!(d > 0f)) throw new ArgumentOutOfRangeException(nameof(d), d, "Only ground under water is rinsed");
      if (RadiationTuning.Detected(r) != 0f) throw new ArgumentOutOfRangeException(nameof(r), r, "Rinsing needs clean water (a share below DetectionLimit)");
      float washed = Mathf.Min(s, maxWash);
      float room = Mathf.Max(0f, Mathf.Min(RinseShareCap - r, 1f - b - r)) * d;
      share = r + Mathf.Min(washed * VolumePerSoil, room) / d;
      return -washed;
    }

    // Soil change (positive: the ground takes radiation from the water) for
    // soil s under water with radioactive share r, badwater share b and
    // effective depth d. Never crosses the equilibrium s = min(1, F x r)
    // (F = WaterToSoilFactor) after the exchange, never exceeds the rates,
    // never takes more radioactive water than there is, and keeps b + r <= 1.
    public static float SoilWaterExchange(float s, float r, float b, float d, float maxRise, float maxWash) {
      if (!(d > 0f)) throw new ArgumentOutOfRangeException(nameof(d), d, "Soil exchanges radiation only with standing water");
      const float F = RadiationTuning.WaterToSoilFactor;
      float a = VolumePerSoil / d;                 // share change per unit of soil radiation
      // A share below DetectionLimit reads 0: the ground does not take it up,
      // but it still counts toward the washout equilibrium below.
      float target = Mathf.Min(1f, RadiationTuning.Detected(r) * F);
      if (s < target) {
        // Equilibrium after the exchange: saturated (1) while the water keeps
        // F x r' >= 1, else F x (r - a x delta) = s + delta.
        float equilibrium = (r - (1f - s) * a) * F >= 1f ? 1f - s : (r * F - s) / (1f + F * a);
        return Mathf.Min(maxRise, equilibrium);
      }
      if (s > target) {
        // s > F x r here, so the equilibrium is unsaturated: s - w = F x (r + a x w).
        float equilibrium = (s - r * F) / (1f + F * a);
        float headroom = (1f - b - r) / a;         // b + r' <= 1
        float washed = Mathf.Min(maxWash, Mathf.Min(equilibrium, headroom));
        return washed > 0f ? -washed : 0f;
      }
      return 0f;
    }

    // Water contamination the native soil kernel turns into the existing soil
    // target: (c - min) x scaler = min(1, WaterToSoilFactor x r) for r > 0.
    public static float KernelContamination(float r, float minimumWaterContamination, float contaminationScaler) =>
      minimumWaterContamination + Mathf.Min(1f, r * RadiationTuning.WaterToSoilFactor) / contaminationScaler;
  }
}
