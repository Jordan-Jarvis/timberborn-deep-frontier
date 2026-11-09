using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using ModdableFluids.Transport.Prototype;

namespace ModdableFluids.Sources.Prototype {
  /// <summary>
  /// What a source blueprint declares through native specs: WaterSourceSpec (tiles, DefaultStrength),
  /// WaterSourceContaminationSpec (DefaultContamination), BadtideWaterSourceContaminationControllerSpec,
  /// WaterDepthStrengthModifierSpec (DepthLimit), UndergroundWaterSourceSpec,
  /// HazardousWeatherWaterSourceSpec (ActiveInHazardousWeather) and DirectionalWaterSourceSpec. The game
  /// adds the drought modifier and activator to every WaterSource, so they are not part of the signature.
  /// </summary>
  public sealed class NativeSourceSignature {
    public string Template { get; }
    public int TileCount { get; }
    public float DefaultStrength { get; }
    public float DefaultContamination { get; }
    public bool BadtideContamination { get; }
    public double? DepthLimit { get; }
    public bool Underground { get; }
    public IReadOnlyList<string> ActiveInWeathers { get; }
    public bool Directional { get; }
    public NativeSourceSignature(string template, int tileCount, float defaultStrength, float defaultContamination, bool badtideContamination,
        double? depthLimit, bool underground, IReadOnlyList<string> activeInWeathers, bool directional) {
      if (string.IsNullOrEmpty(template)) throw new ArgumentException("A native source signature needs its template name");
      Template = template; TileCount = tileCount; DefaultStrength = defaultStrength; DefaultContamination = defaultContamination;
      BadtideContamination = badtideContamination; DepthLimit = depthLimit; Underground = underground;
      ActiveInWeathers = (activeInWeathers ?? throw new ArgumentNullException(nameof(activeInWeathers))).ToArray(); Directional = directional;
    }
  }

  /// <summary>Maps native source blueprints to registered source types and reports every disagreement.</summary>
  public static class NativeSourceClassifier {
    /// <summary>
    /// The type registered for the blueprint, after checking that the blueprint still declares what the
    /// type says. Returns false with the reason when no type claims the template; throws when a type
    /// claims it but the native data changed (a game update), naming every differing value.
    /// </summary>
    public static bool TryClassify(FluidRegistry registry, NativeSourceSignature signature, out FluidSourceTypeDefinition type, out string reason) {
      if (registry == null || signature == null) throw new ArgumentNullException("classification input");
      reason = null;
      if (!registry.TryGetSourceTypeByTemplate(signature.Template, out type)) {
        reason = "No source type claims blueprint " + signature.Template;
        return false;
      }
      var differences = new List<string>();
      void Compare(string name, object expected, object actual) {
        if (!Equals(expected, actual)) differences.Add(name + " " + Format(actual) + " (type says " + Format(expected) + ")");
      }
      Compare("tiles", type.TileCount, signature.TileCount);
      Compare("default strength", type.DefaultStrength, signature.DefaultStrength);
      if (type.IsNative) Compare("default contamination", type.DefaultBadwaterShare, signature.DefaultContamination);
      Compare("badtide contamination", type.BadtideContamination, signature.BadtideContamination);
      if (type.IsNative) {
        Compare("depth limit", type.DepthLimit, signature.DepthLimit);
        Compare("underground", type.RequiresDrill, signature.Underground);
        Compare("hazardous weathers", string.Join(",", type.ActiveOnlyInWeathers), string.Join(",", signature.ActiveInWeathers));
        Compare("directional", type.Directional, signature.Directional);
      }
      if (differences.Count > 0)
        throw new InvalidOperationException("Blueprint " + signature.Template + " no longer matches source type " + type.Id + ": " + string.Join("; ", differences)
          + ". The game's source data changed; update the source type table.");
      return true;
    }

    private static string Format(object value) => value is double d ? d.ToString("R", CultureInfo.InvariantCulture)
      : value is float f ? f.ToString("R", CultureInfo.InvariantCulture) : value == null ? "none" : value.ToString();
  }

  /// <summary>The mixture a source emits and its schedule multiplier, for the transport's source stage.</summary>
  public static class FluidSourceEmission {
    /// <summary>
    /// Badwater = volume x native contamination (which already includes the badtide ramp); each extra fluid =
    /// its share of the rest; fresh water = the rest of the non-bad volume. An active tide's composition replaces
    /// the type's own only when the type is tide-overridable. Nothing is rescaled: shares above one were
    /// rejected at registration, and invalid inputs throw.
    /// </summary>
    public static FluidVolumes Compose(FluidRegistry registry, FluidSourceTypeDefinition type, double volume, double nativeBadShare,
        IReadOnlyDictionary<string, double> activeTideComposition) {
      if (registry == null || type == null) throw new ArgumentNullException("emission input");
      if (double.IsNaN(volume) || double.IsInfinity(volume) || volume < 0) throw new ArgumentOutOfRangeException(nameof(volume), volume, "Emission volume must be finite and nonnegative");
      if (double.IsNaN(nativeBadShare) || nativeBadShare < 0 || nativeBadShare > 1) throw new ArgumentOutOfRangeException(nameof(nativeBadShare), nativeBadShare, "Native contamination must be in [0, 1]");
      var shares = activeTideComposition != null && type.TideOverridable ? activeTideComposition : type.EmittedFluids;
      var values = new double[registry.Count];
      double bad = volume * nativeBadShare, nonBad = volume - bad, extraShare = 0;
      values[FluidRegistry.BadwaterIndex] = bad;
      foreach (var pair in shares.OrderBy(p => p.Key, StringComparer.Ordinal)) {
        if (!registry.TryGet(pair.Key, out var fluid) || fluid.NativeRole != FluidNativeRole.Extra)
          throw new ArgumentException("Source " + type.Id + " emits " + pair.Key + ", which is not a registered extra fluid");
        if (double.IsNaN(pair.Value) || pair.Value <= 0 || pair.Value > 1) throw new ArgumentOutOfRangeException(nameof(activeTideComposition), pair.Value, "Emission shares are in (0, 1]");
        values[registry.GetHandle(pair.Key).Index] = nonBad * pair.Value;
        extraShare += pair.Value;
      }
      if (extraShare > 1) throw new ArgumentException("Emission shares for " + type.Id + " total " + extraShare.ToString("R", CultureInfo.InvariantCulture) + ", above 1");
      // Fresh water from its own share, not by subtracting near-equal volumes. Registration sums the same
      // shares in the same ordinal order, so a registered composition never exceeds one.
      values[FluidRegistry.WaterIndex] = nonBad * (1 - extraShare);
      return new FluidVolumes(values);
    }

    /// <summary>The schedule multiplier for one placed source (1 when the type has no schedule).</summary>
    public static double StrengthMultiplier(FluidSourceTypeDefinition type, double gameHours, Guid entityId) {
      if (type == null) throw new ArgumentNullException(nameof(type));
      return type.Schedule == null ? 1 : type.Schedule.MultiplierAt(gameHours, type.Schedule.PhaseFor(entityId));
    }
  }
}
