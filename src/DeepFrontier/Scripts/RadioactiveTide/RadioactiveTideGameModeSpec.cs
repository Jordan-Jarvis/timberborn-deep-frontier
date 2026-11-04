using System;
using System.Collections.Immutable;
using System.Globalization;
using System.Linq;
using Timberborn.BlueprintSystem;
using Timberborn.NewGameConfigurationSystem;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // The radioactive tide settings of a game mode, the counterpart of the
  // native badtide fields of GameModeSpec (Timberborn 1.1.2.8:
  // CyclesBeforeRandomizingBadtide, ChanceForBadtide, BadtideDuration).
  //
  // Native game modes are blueprints with one GameModeSpec, a fixed record:
  // vanilla NewGameModes/GameMode.{Easy,Normal,Hard}, and any a mod adds (for
  // example zxuiji's Chill Mode, NewGameModes/GameMode.Chill). A mode's
  // tide settings follow from its own weather by one rule
  // (RadioactiveTideGameModes.Derive), so a mode Deep Frontier has never seen
  // gets them as Easy, Normal and Hard do. A mode whose blueprint carries this
  // spec as a second component uses it instead: the custom mode, which
  // RadioactiveTideNewGamePatch gives the custom tide rows' values (WithTide),
  // and any mod that wants its own values for its mode (a file at the mode's
  // blueprint path holding {"RadioactiveTideGameModeSpec": {...}}; the native
  // BlueprintFileBundleLoader merges it into that blueprint).
  //
  // The new game's GameModeSpec travels in GameSceneParameters into the Game
  // scene, where RadioactiveTideStartingValues resolves it once and the game
  // then saves its own copy, as native BadtideWeather does.
  public record RadioactiveTideGameModeSpec : ComponentSpec {
    [Serialize]
    public bool Enabled { get; init; }

    // Tides can happen in cycles after this one.
    [Serialize]
    public int CyclesWithoutTide { get; init; }

    // Chance per cycle that the cycle's hazardous season is a tide.
    [Serialize]
    public int ChancePercent { get; init; }

    // Whole days, uniform between Min and Max.
    [Serialize]
    public MinMaxSpec<int> Duration { get; init; }
  }

  // A game mode's weather as the radioactive tide rule reads it: the native
  // GameModeSpec durations in days and the badtide chance in whole percent,
  // as the native Customize screen shows it (CustomNewGameModeController
  // FloatToPercent = Mathf.RoundToInt(chance * 100), i.e. Math.Round, ties to
  // even). Integers, so a vanilla mode and its curve point give the same
  // share bit for bit.
  public readonly struct RadioactiveTideModeWeather {
    public RadioactiveTideModeWeather(int temperateMin, int temperateMax, int droughtMin, int droughtMax,
        int badtideMin, int badtideMax, int badtidePercent) {
      TemperateMin = temperateMin; TemperateMax = temperateMax;
      DroughtMin = droughtMin; DroughtMax = droughtMax;
      BadtideMin = badtideMin; BadtideMax = badtideMax;
      BadtidePercent = badtidePercent;
    }

    public int TemperateMin { get; }
    public int TemperateMax { get; }
    public int DroughtMin { get; }
    public int DroughtMax { get; }
    public int BadtideMin { get; }
    public int BadtideMax { get; }
    public int BadtidePercent { get; }

    // The weather of a game mode. Values the native Customize screen would
    // refuse (a negative duration, a shortest longer than a longest, a chance
    // outside 0-100%) are an error naming the mode.
    public static RadioactiveTideModeWeather Of(GameModeSpec gameMode, string what) {
      if (gameMode == null) throw new ArgumentNullException(nameof(gameMode));
      var temperate = Days(gameMode.TemperateWeatherDuration, "TemperateWeatherDuration", what);
      var drought = Days(gameMode.DroughtDuration, "DroughtDuration", what);
      var badtide = Days(gameMode.BadtideDuration, "BadtideDuration", what);
      float chance = gameMode.ChanceForBadtide;
      if (!(chance >= 0f && chance <= 1f))
        throw Invalid(what, $"ChanceForBadtide is {chance.ToString(CultureInfo.InvariantCulture)}, outside 0..1");
      return new RadioactiveTideModeWeather(temperate.Min, temperate.Max, drought.Min, drought.Max,
        badtide.Min, badtide.Max, (int)Math.Round(chance * 100f));
    }

    // Days of hazardous weather in an average cycle once badtides are
    // randomized: a badtide with the badtide chance, else a drought (native
    // HazardousWeatherRandomizer), each its average duration. The early-cycle
    // handicaps and the drought-only first cycles are left out.
    public double HazardDays =>
      BadtidePercent / 100.0 * (BadtideMin + BadtideMax) / 2.0
      + (100 - BadtidePercent) / 100.0 * (DroughtMin + DroughtMax) / 2.0;

    // The share of an average cycle that is hazardous: 0 without hazardous
    // weather, 1 without temperate weather.
    public double HazardShare => HazardDays / ((TemperateMin + TemperateMax) / 2.0 + HazardDays);

    // The longest hazardous season the mode can have (a badtide only if its
    // chance is above 0%, a drought only if it is below 100%).
    public int LongestHazardDays => Math.Max(BadtidePercent > 0 ? BadtideMax : 0, BadtidePercent < 100 ? DroughtMax : 0);

    public override string ToString() =>
      $"temperate {TemperateMin}-{TemperateMax} days, drought {DroughtMin}-{DroughtMax} days, badtide {BadtideMin}-{BadtideMax} days at {BadtidePercent}%";

    private static MinMaxSpec<int> Days(MinMaxSpec<int> days, string field, string what) {
      if (days == null) throw Invalid(what, $"{field} is missing");
      if (days.Min < 0 || days.Min > days.Max) throw Invalid(what, $"{field} is {days.Min}-{days.Max} days");
      return days;
    }

    private static InvalidOperationException Invalid(string what, string detail) =>
      new InvalidOperationException($"Radioactive tide: {what} has invalid weather settings ({detail}), so its radioactive tide settings "
        + "cannot be derived from them. Fix the mode, or give its blueprint a RadioactiveTideGameModeSpec.");
  }

  // One point of RadioactiveTideTuning.GameModeCurve: a native game mode's
  // weather and the radioactive tide it gets.
  public sealed class RadioactiveTideCurvePoint {
    public RadioactiveTideCurvePoint(string mode, int temperateMin, int temperateMax, int droughtMin, int droughtMax,
        int badtideMin, int badtideMax, int badtidePercent, int cyclesWithoutTide, int chancePercent, int minDurationDays, int maxDurationDays) {
      Mode = mode ?? throw new ArgumentNullException(nameof(mode));
      Weather = new RadioactiveTideModeWeather(temperateMin, temperateMax, droughtMin, droughtMax, badtideMin, badtideMax, badtidePercent);
      CyclesWithoutTide = cyclesWithoutTide; ChancePercent = chancePercent;
      MinDurationDays = minDurationDays; MaxDurationDays = maxDurationDays;
    }

    public string Mode { get; }
    public RadioactiveTideModeWeather Weather { get; }
    public int CyclesWithoutTide { get; }
    public int ChancePercent { get; }
    public int MinDurationDays { get; }
    public int MaxDurationDays { get; }
  }

  public static class RadioactiveTideGameModes {
    // A game mode's radioactive tide settings: its own RadioactiveTideGameModeSpec
    // if its blueprint carries one, else the ones its weather gives (Derive).
    // derivation is null for a mode's own spec, else how the values were
    // derived (for the log). A mode without a blueprint is an error: every
    // GameModeSpec has one (ComponentSpec's constructor creates it) until
    // Moddable Timberborn's PersistentGameModeService.Save drops it, after
    // which a custom mode's own spec could no longer be told from none.
    public static RadioactiveTideGameModeSpec For(GameModeSpec gameMode, string what, out string derivation) {
      if (gameMode == null) throw new ArgumentNullException(nameof(gameMode));
      if (gameMode.Blueprint == null)
        throw new InvalidOperationException($"Radioactive tide: {what} has no blueprint, so its radioactive tide settings cannot be read");
      var own = gameMode.GetSpec<RadioactiveTideGameModeSpec>();
      if (own != null) {
        if (own.Duration == null) throw new InvalidOperationException($"Radioactive tide: the RadioactiveTideGameModeSpec of {what} has no Duration");
        derivation = null;
        return own;
      }
      return Derive(RadioactiveTideModeWeather.Of(gameMode, what), out derivation);
    }

    // The rule (docs/radiation.md "Settings per game"):
    // - Tides are on when the mode has hazardous weather (its longest
    //   hazardous season lasts at least a day); a mode without any has none
    //   for a tide to replace.
    // - Cycles without tide, chance and shortest and longest tide are read off
    //   RadioactiveTideTuning.GameModeCurve at the mode's hazard share: linear
    //   between the two points around it, the end segment continued beyond
    //   Easy or Hard, each rounded to a whole number (halves away from zero).
    // - A tide never lasts longer than the mode's longest hazardous season
    //   (the season it replaces): the longest tide is capped there, and the
    //   shortest at the longest. Vanilla Easy meets the cap exactly (tides
    //   2-4 days, droughts 2-4 days).
    // Easy, Normal and Hard get exactly their curve points this way. A mode
    // without hazardous weather is off; its values (shown if the player
    // switches tides on in Customize) are the curve's gentlest end, share 0.
    public static RadioactiveTideGameModeSpec Derive(RadioactiveTideModeWeather weather, out string derivation) {
      var curve = Curve();
      int longest = weather.LongestHazardDays;
      bool enabled = longest >= RadioactiveTideTuning.DurationLowest;
      double share = enabled ? weather.HazardShare : 0.0;
      int k = 0;
      while (k < curve.Length - 2 && share > curve[k + 1].Weather.HazardShare) k++;
      var a = curve[k];
      var b = curve[k + 1];
      double t = (share - a.Weather.HazardShare) / (b.Weather.HazardShare - a.Weather.HazardShare);
      int cyclesWithout = Along(a.CyclesWithoutTide, b.CyclesWithoutTide, t);
      int chance = Along(a.ChancePercent, b.ChancePercent, t);
      int minDays = Along(a.MinDurationDays, b.MinDurationDays, t);
      int maxDays = Along(a.MaxDurationDays, b.MaxDurationDays, t);
      string capped = "";
      if (enabled && maxDays > longest) {
        capped = $"; longest tide capped at its longest hazardous season, {longest} day{(longest == 1 ? "" : "s")}";
        maxDays = longest;
        minDays = Math.Min(minDays, maxDays);
      }
      string points = string.Join(", ", curve.Select(p => $"{p.Mode} {Percent(p.Weather.HazardShare)}"));
      derivation = enabled
        ? $"{weather}: hazardous {Percent(share)} of a cycle ({points}){capped}"
        : $"{weather}: no hazardous weather, so no radioactive tides";
      return Create(enabled, cyclesWithout, chance, minDays, maxDays);
    }

    // A copy of the custom mode whose blueprint also holds the tide settings
    // (native Blueprint(name, specs, children) copies each spec with
    // Blueprint = the new blueprint).
    public static GameModeSpec WithTide(GameModeSpec customMode, RadioactiveTideGameModeSpec tide) {
      if (customMode == null) throw new ArgumentNullException(nameof(customMode));
      if (tide == null) throw new ArgumentNullException(nameof(tide));
      if (customMode.Blueprint == null || customMode.Blueprint.Specs.Length != 1)
        throw new InvalidOperationException("Radioactive tide: the native custom game mode is no longer a lone GameModeSpec");
      var blueprint = new Blueprint(customMode.Blueprint.Name, new ComponentSpec[] { customMode, tide }, ImmutableArray<Blueprint>.Empty);
      var copy = blueprint.GetSpec<GameModeSpec>();
      if (copy == null || copy.GetSpec<RadioactiveTideGameModeSpec>() == null)
        throw new InvalidOperationException("Radioactive tide: the custom game mode copy lost its radioactive tide settings");
      return copy;
    }

    public static RadioactiveTideGameModeSpec Create(bool enabled, int cyclesWithoutTide, int chancePercent, int minDurationDays, int maxDurationDays) =>
      new RadioactiveTideGameModeSpec {
        Enabled = enabled,
        CyclesWithoutTide = cyclesWithoutTide,
        ChancePercent = chancePercent,
        Duration = new MinMaxSpec<int> { Min = minDurationDays, Max = maxDurationDays },
      };

    // A mode's name for messages: its blueprint (GameMode.Chill), else its
    // display key; the custom mode has neither.
    public static string Name(GameModeSpec gameMode) =>
      gameMode?.Blueprint?.Name ?? gameMode?.DisplayNameLocKey ?? "custom";

    private static int Along(int a, int b, double t) => (int)Math.Round(a + t * (b - a), MidpointRounding.AwayFromZero);

    private static string Percent(double share) => (share * 100.0).ToString("0.0", CultureInfo.InvariantCulture) + "%";

    // The curve's points must rise in hazard share (each segment needs a
    // length); the content validator checks the rest.
    private static ImmutableArray<RadioactiveTideCurvePoint> Curve() {
      var curve = RadioactiveTideTuning.GameModeCurve;
      if (curve.Length < 2) throw new InvalidOperationException("Radioactive tide: RadioactiveTideTuning.GameModeCurve needs at least two points");
      for (int i = 1; i < curve.Length; i++)
        if (!(curve[i].Weather.HazardShare > curve[i - 1].Weather.HazardShare))
          throw new InvalidOperationException($"Radioactive tide: RadioactiveTideTuning.GameModeCurve point {curve[i].Mode} is not more hazardous than {curve[i - 1].Mode}");
      return curve;
    }
  }
}
