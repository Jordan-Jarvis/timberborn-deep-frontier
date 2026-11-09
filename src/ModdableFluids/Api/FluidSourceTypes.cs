using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Linq;

namespace ModdableFluids {
  /// <summary>
  /// A periodic emission profile for a custom source, such as a geyser. The strength multiplier is
  /// <see cref="DormantMultiplier"/> outside eruptions and ramps linearly over <see cref="RampHours"/>
  /// to <see cref="ActiveMultiplier"/> and back within each eruption of <see cref="ActiveHours"/>,
  /// once every <see cref="PeriodHours"/>. The schedule is a pure function of game time and a
  /// per-source phase, so it needs no saved state: the phase comes from the entity's saved GUID.
  /// </summary>
  public sealed class FluidSourceSchedule {
    public double PeriodHours { get; }
    public double ActiveHours { get; }
    public double RampHours { get; }
    public double ActiveMultiplier { get; }
    public double DormantMultiplier { get; }

    public FluidSourceSchedule(double periodHours, double activeHours, double rampHours, double activeMultiplier, double dormantMultiplier) {
      Finite(periodHours, nameof(periodHours)); Finite(activeHours, nameof(activeHours)); Finite(rampHours, nameof(rampHours));
      Finite(activeMultiplier, nameof(activeMultiplier)); Finite(dormantMultiplier, nameof(dormantMultiplier));
      if (periodHours <= 0 || periodHours > 24 * 60) throw new ArgumentOutOfRangeException(nameof(periodHours), periodHours, "A schedule period is (0, 1440] hours");
      if (activeHours <= 0 || activeHours > periodHours) throw new ArgumentOutOfRangeException(nameof(activeHours), activeHours, "An eruption lasts (0, period] hours");
      if (rampHours < 0 || 2 * rampHours > activeHours) throw new ArgumentOutOfRangeException(nameof(rampHours), rampHours, "Both ramps must fit inside the eruption");
      if (activeMultiplier < 0 || dormantMultiplier < 0) throw new ArgumentOutOfRangeException(nameof(activeMultiplier), "Multipliers are nonnegative");
      PeriodHours = periodHours; ActiveHours = activeHours; RampHours = rampHours; ActiveMultiplier = activeMultiplier; DormantMultiplier = dormantMultiplier;
    }

    /// <summary>Strength multiplier at <paramref name="gameHours"/> for a source whose cycle is shifted by <paramref name="phaseHours"/>.</summary>
    public double MultiplierAt(double gameHours, double phaseHours) {
      Finite(gameHours, nameof(gameHours)); Finite(phaseHours, nameof(phaseHours));
      double t = (gameHours + phaseHours) % PeriodHours;
      if (t < 0) t += PeriodHours;
      if (t >= ActiveHours) return DormantMultiplier;
      double rise = RampHours == 0 ? 1 : Math.Min(1, t / RampHours);
      double fall = RampHours == 0 ? 1 : Math.Min(1, (ActiveHours - t) / RampHours);
      double level = Math.Min(rise, fall);
      return DormantMultiplier + (ActiveMultiplier - DormantMultiplier) * level;
    }

    /// <summary>Mean multiplier over one period (exact for linear ramps).</summary>
    public double MeanMultiplier =>
      (DormantMultiplier * (PeriodHours - ActiveHours) + ActiveMultiplier * (ActiveHours - RampHours) + DormantMultiplier * RampHours) / PeriodHours;

    /// <summary>A stable phase in [0, period) from an entity's saved GUID, so placed sources do not erupt together.</summary>
    public double PhaseFor(Guid entityId) => BitConverter.ToUInt32(entityId.ToByteArray(), 0) / 4294967296.0 * PeriodHours;

    private static void Finite(double value, string name) {
      if (double.IsNaN(value) || double.IsInfinity(value)) throw new ArgumentOutOfRangeException(name, value, "Expected a finite value");
    }
  }

  /// <summary>
  /// A kind of fluid source. Native kinds mirror the game's own source blueprints (owner
  /// <see cref="FluidIds.BuiltInOwner"/>) and are checked against them; custom kinds are registered by
  /// mods and add a composition, a schedule, or both, on top of a native WaterSource entity. The
  /// emitted mixture is: badwater = volume x native contamination (badtide ramp included); every
  /// listed extra fluid = its share of the remaining non-bad volume; fresh water = the rest.
  /// </summary>
  public sealed class FluidSourceTypeDefinition {
    public string Id { get; }
    public string OwnerModId { get; }
    public string LocalName { get; }
    public string ProviderId { get; }
    public string DisplayNameLocKey { get; }
    /// <summary>The blueprint the type is placed from (native: the game's template name).</summary>
    public string Template { get; }
    public bool IsNative { get; }
    public int TileCount { get; }
    public float DefaultStrength { get; }
    /// <summary>Native default contamination (0 for clean sources, 1 for badwater sources).</summary>
    public float DefaultBadwaterShare { get; }
    /// <summary>Stops in droughts (native DroughtWaterStrengthModifier on every WaterSource).</summary>
    public bool FollowsDrought { get; }
    /// <summary>Turns bad during badtides (native BadtideWaterSourceContaminationController).</summary>
    public bool BadtideContamination { get; }
    /// <summary>Seep behaviour: stops while the water above it is deeper than this; null when absent.</summary>
    public double? DepthLimit { get; }
    /// <summary>Aquifer behaviour: flows only while a drill occupies it, scaled by its power efficiency.</summary>
    public bool RequiresDrill { get; }
    /// <summary>Flows only during these hazardous weathers (native HazardousWeatherWaterSourceSpec).</summary>
    public IReadOnlyList<string> ActiveOnlyInWeathers { get; }
    public bool Directional { get; }
    /// <summary>Extra fluid ID to its share of the non-bad emitted volume; empty for vanilla water/badwater.</summary>
    public IReadOnlyDictionary<string, double> EmittedFluids { get; }
    public FluidSourceSchedule Schedule { get; }
    /// <summary>Whether a registered tide may replace this type's emitted composition while it is active.</summary>
    public bool TideOverridable { get; }

    internal FluidSourceTypeDefinition(string id, string owner, string local, string provider, string loc, string template, bool native, int tiles,
        float strength, float bad, bool drought, bool badtide, double? depthLimit, bool drill, string[] weathers, bool directional,
        SortedDictionary<string, double> emitted, FluidSourceSchedule schedule, bool tideOverridable) {
      Id = id; OwnerModId = owner; LocalName = local; ProviderId = provider; DisplayNameLocKey = loc; Template = template; IsNative = native;
      TileCount = tiles; DefaultStrength = strength; DefaultBadwaterShare = bad; FollowsDrought = drought; BadtideContamination = badtide;
      DepthLimit = depthLimit; RequiresDrill = drill; ActiveOnlyInWeathers = new ReadOnlyCollection<string>(weathers); Directional = directional;
      EmittedFluids = new ReadOnlyDictionary<string, double>(new SortedDictionary<string, double>(emitted, StringComparer.Ordinal));
      Schedule = schedule; TideOverridable = tideOverridable;
    }

    public override string ToString() => Id + " (" + (IsNative ? "native " : "custom ") + Template + ")";
  }

  /// <summary>
  /// The game's own source kinds in Timberborn 1.1.2.8 (MapEditor/Water and Buildings/Water blueprints).
  /// Every WaterSource gets the native drought modifier and activator, so all of them follow droughts
  /// unless a Badwater Pressurizer (WaterSourceDischarger) sits on the source. The harness checks this
  /// table against Blueprints.zip; a game update that changes or adds a source kind fails there.
  /// </summary>
  public static class NativeFluidSourceTypes {
    public const string WaterSource = "Timberborn.WaterSource";
    public const string BadwaterSource = "Timberborn.BadwaterSource";
    public const string WaterSeep = "Timberborn.WaterSeep";
    public const string BadwaterSeep = "Timberborn.BadwaterSeep";
    public const string Aquifer = "Timberborn.Aquifer";
    public const string BadtideDrain = "Timberborn.BadtideDrain";
    public const string DevWaterSource = "Timberborn.DevWaterSource";

    internal static FluidSourceTypeDefinition[] Create() => new[] {
      Native("WaterSource", 1, 1f, 0f, true, null, false, new string[0], false),
      Native("BadwaterSource", 9, 3f, 1f, false, null, false, new string[0], false),
      Native("WaterSeep", 4, 1f, 0f, true, .8, false, new string[0], false),
      Native("BadwaterSeep", 4, 1f, 1f, true, .8, false, new string[0], false),
      Native("Aquifer", 1, 1f, 0f, true, null, true, new string[0], false),
      Native("BadtideDrain", 1, 1f, 1f, false, null, false, new[] { "BadtideWeather" }, true),
      Native("DevWaterSource", 1, 1f, 0f, true, null, false, new string[0], false),
    };

    private static FluidSourceTypeDefinition Native(string template, int tiles, float strength, float bad, bool badtide, double? depth, bool drill, string[] weathers, bool directional) =>
      new FluidSourceTypeDefinition(FluidIds.BuiltInOwner + "." + template, FluidIds.BuiltInOwner, template, FluidIds.BuiltInOwner,
        template == "DevWaterSource" ? "Building.WaterSource.DisplayName" : "Building." + template + ".DisplayName", template, true, tiles, strength, bad, true, badtide, depth, drill, weathers, directional,
        new SortedDictionary<string, double>(StringComparer.Ordinal), null, true);
  }

  internal sealed class PendingSourceType {
    internal readonly string Id, OwnerModId, LocalName, ProviderId, DisplayNameLocKey, Template;
    internal readonly int TileCount;
    internal readonly float DefaultStrength;
    internal readonly bool FollowsDrought, BadtideContamination, TideOverridable;
    internal readonly SortedDictionary<string, double> Emitted = new SortedDictionary<string, double>(StringComparer.Ordinal);
    internal FluidSourceSchedule Schedule;
    internal PendingSourceType(string id, string owner, string local, string provider, string loc, string template, int tiles, float strength,
        bool drought, bool badtide, bool overridable) {
      Id = id; OwnerModId = owner; LocalName = local; ProviderId = provider; DisplayNameLocKey = loc; Template = template; TileCount = tiles;
      DefaultStrength = strength; FollowsDrought = drought; BadtideContamination = badtide; TideOverridable = overridable;
    }
  }
}
