using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;

namespace ModdableFluids {
  /// <summary>
  /// A game mode's weather as the tide rule reads it: the native GameModeSpec durations in days and the
  /// badtide chance in whole percent (as the native Customize screen shows it). A mode with badtides or droughts
  /// switched off stores zeros for them, as the native custom mode does.
  /// </summary>
  public sealed class FluidTideModeWeather {
    public int TemperateMin { get; }
    public int TemperateMax { get; }
    public int DroughtMin { get; }
    public int DroughtMax { get; }
    public int BadtideMin { get; }
    public int BadtideMax { get; }
    public int BadtidePercent { get; }

    public FluidTideModeWeather(int temperateMin, int temperateMax, int droughtMin, int droughtMax, int badtideMin, int badtideMax, int badtidePercent) {
      if (temperateMin < 0 || temperateMin > temperateMax || droughtMin < 0 || droughtMin > droughtMax || badtideMin < 0 || badtideMin > badtideMax)
        throw new ArgumentException("Invalid game mode weather: " + Describe(temperateMin, temperateMax, droughtMin, droughtMax, badtideMin, badtideMax, badtidePercent));
      if (badtidePercent < 0 || badtidePercent > 100) throw new ArgumentOutOfRangeException(nameof(badtidePercent), badtidePercent, "A badtide chance is 0..100%");
      TemperateMin = temperateMin; TemperateMax = temperateMax; DroughtMin = droughtMin; DroughtMax = droughtMax;
      BadtideMin = badtideMin; BadtideMax = badtideMax; BadtidePercent = badtidePercent;
    }

    /// <summary>Timberborn 1.1.2.8 NewGameModes/GameMode.Easy, .Normal and .Hard (the harness checks them against the blueprints).</summary>
    public static FluidTideModeWeather VanillaEasy { get; } = new FluidTideModeWeather(16, 19, 2, 4, 1, 3, 40);
    public static FluidTideModeWeather VanillaNormal { get; } = new FluidTideModeWeather(13, 17, 5, 9, 4, 8, 40);
    public static FluidTideModeWeather VanillaHard { get; } = new FluidTideModeWeather(5, 8, 15, 30, 15, 30, 40);

    /// <summary>Average hazardous days once badtides are randomized: a badtide with its chance, else a drought.</summary>
    public double HazardDays => BadtidePercent / 100.0 * (BadtideMin + BadtideMax) / 2.0 + (100 - BadtidePercent) / 100.0 * (DroughtMin + DroughtMax) / 2.0;
    /// <summary>The hazardous share of an average cycle: 0 without hazardous weather, 1 without temperate weather.</summary>
    public double HazardShare => HazardDays / ((TemperateMin + TemperateMax) / 2.0 + HazardDays);
    /// <summary>The longest hazardous season the mode can have (a badtide only above 0%, a drought only below 100%).</summary>
    public int LongestHazardDays => Math.Max(BadtidePercent > 0 ? BadtideMax : 0, BadtidePercent < 100 ? DroughtMax : 0);

    public override string ToString() => Describe(TemperateMin, TemperateMax, DroughtMin, DroughtMax, BadtideMin, BadtideMax, BadtidePercent);
    private static string Describe(int tMin, int tMax, int dMin, int dMax, int bMin, int bMax, int percent) =>
      "temperate " + tMin + "-" + tMax + " days, drought " + dMin + "-" + dMax + " days, badtide " + bMin + "-" + bMax + " days at " + percent + "%";
  }

  /// <summary>One tide's settings in one save: whether it can happen, its weight in the shared budget, cycles without it and duration.</summary>
  public sealed class FluidTideSettings {
    public string TideId { get; }
    public bool Enabled { get; }
    public int Weight { get; }
    public int CyclesWithoutTide { get; }
    public int MinDurationDays { get; }
    public int MaxDurationDays { get; }

    /// <summary>Only an enabled tide's values must be in range, as the native custom mode skips a switched-off badtide.</summary>
    public FluidTideSettings(string tideId, bool enabled, int weight, int cyclesWithoutTide, int minDurationDays, int maxDurationDays) {
      if (string.IsNullOrEmpty(tideId)) throw new ArgumentException("Tide settings need the tide's ID");
      if (enabled) {
        FluidTideRules.Require(weight, FluidTideRules.WeightLowest, FluidTideRules.WeightHighest, tideId + " weight");
        FluidTideRules.Require(cyclesWithoutTide, FluidTideRules.CyclesWithoutTideLowest, FluidTideRules.CyclesWithoutTideHighest, tideId + " cycles without tide");
        FluidTideRules.Require(minDurationDays, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest, tideId + " shortest tide (days)");
        FluidTideRules.Require(maxDurationDays, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest, tideId + " longest tide (days)");
        if (minDurationDays > maxDurationDays)
          throw new ArgumentException(tideId + ": the shortest tide (" + minDurationDays + " days) is longer than the longest (" + maxDurationDays + " days)");
      }
      TideId = tideId; Enabled = enabled; Weight = weight; CyclesWithoutTide = cyclesWithoutTide; MinDurationDays = minDurationDays; MaxDurationDays = maxDurationDays;
    }

    public override string ToString() => Enabled
      ? TideId + ": weight " + Weight + ", from cycle " + (CyclesWithoutTide + 1) + ", " + MinDurationDays + "-" + MaxDurationDays + " days"
      : TideId + ": off";
  }

  /// <summary>
  /// One save's tide settings: the shared hazard budget (percent of eligible cycles that become a tide) and every
  /// tide's settings in ordinal tide-ID order. Chosen when the game starts and saved with it.
  /// </summary>
  public sealed class FluidTideSaveSettings {
    public int BudgetPercent { get; }
    public IReadOnlyList<FluidTideSettings> Tides { get; }

    public FluidTideSaveSettings(int budgetPercent, IEnumerable<FluidTideSettings> tides) {
      FluidTideRules.Require(budgetPercent, FluidTideRules.BudgetPercentLowest, FluidTideRules.BudgetPercentHighest, "tide budget (%)");
      if (tides == null) throw new ArgumentNullException(nameof(tides));
      var ordered = tides.ToArray();
      if (ordered.Any(t => t == null)) throw new ArgumentException("Tide settings contain null");
      Array.Sort(ordered, (a, b) => string.CompareOrdinal(a.TideId, b.TideId));
      for (int i = 1; i < ordered.Length; i++)
        if (ordered[i].TideId == ordered[i - 1].TideId) throw new ArgumentException("Tide " + ordered[i].TideId + " has two settings");
      BudgetPercent = budgetPercent;
      Tides = new ReadOnlyCollection<FluidTideSettings>(ordered);
    }

    public FluidTideSettings Get(string tideId) =>
      Tides.SingleOrDefault(t => t.TideId == tideId) ?? throw new ArgumentException("These tide settings have no entry for " + tideId);

    public override string ToString() => "budget " + BudgetPercent + "%; " + (Tides.Count == 0 ? "no tides" : string.Join("; ", Tides));
  }

  /// <summary>
  /// Per-mode tide values. A tide defines its values for the vanilla Easy, Normal and Hard presets; every
  /// other mode (a mod's preset, the custom mode before it is edited) derives them from its own weather by
  /// Deep Frontier's rule (docs/radiation.md, "Settings per game"), generalised to any tide:
  /// <list type="bullet">
  /// <item>A mode without hazardous weather (its longest hazardous season is under a day) has the tide off.</item>
  /// <item>Chance, cycles without and shortest and longest tide are read off the tide's three points at the mode's
  /// hazard share: linear between the two points around it, the end segment continued beyond Easy or Hard, each
  /// rounded to a whole number (halves away from zero). Easy, Normal and Hard get exactly their own points.</item>
  /// <item>A tide never lasts longer than the mode's longest hazardous season (the season it replaces).</item>
  /// </list>
  /// Registration checks that the curve stays inside the allowed ranges for every share in [0, 1], so the rule
  /// needs no clamping. The defaults of a save: each tide's weight is its chance, and the shared budget is the
  /// largest chance among the installed tides.
  /// </summary>
  public static class FluidTideModes {
    private static readonly FluidTideModeWeather[] Anchors = { FluidTideModeWeather.VanillaEasy, FluidTideModeWeather.VanillaNormal, FluidTideModeWeather.VanillaHard };

    /// <summary>The tide's values for a mode with this weather (the vanilla presets' own weather gives their points exactly).</summary>
    public static FluidTideSettings Derive(FluidTideDefinition tide, FluidTideModeWeather weather, out int chancePercent, out string derivation) {
      if (tide == null) throw new ArgumentNullException(nameof(tide));
      if (weather == null) throw new ArgumentNullException(nameof(weather));
      int longest = weather.LongestHazardDays;
      bool enabled = longest >= FluidTideRules.DurationLowest;
      double share = enabled ? weather.HazardShare : 0.0;
      var values = Curve(FluidTideRules.Modes.Select(tide.GetMode).ToArray(), share);
      int minDays = values[2], maxDays = values[3];
      string capped = "";
      if (enabled && maxDays > longest) {
        capped = "; longest tide capped at its longest hazardous season, " + longest + " day" + (longest == 1 ? "" : "s");
        maxDays = longest;
        minDays = Math.Min(minDays, maxDays);
      }
      chancePercent = values[0];
      string points = string.Join(", ", FluidTideRules.Modes.Select((m, i) => m + " " + Percent(Anchors[i].HazardShare)));
      derivation = enabled ? weather + ": hazardous " + Percent(share) + " of a cycle (" + points + ")" + capped
        : weather + ": no hazardous weather, so no " + tide.Id;
      return new FluidTideSettings(tide.Id, enabled, values[0], values[1], minDays, maxDays);
    }

    /// <summary>
    /// A save's defaults for a mode: every tide derived as above with its chance as its weight, and the budget the
    /// largest chance among the installed tides. Null when no tide is installed.
    /// </summary>
    public static FluidTideSaveSettings Defaults(FluidTideRegistry tides, FluidTideModeWeather weather, out IReadOnlyList<string> derivations) {
      if (tides == null) throw new ArgumentNullException(nameof(tides));
      var list = new List<string>();
      derivations = list;
      if (tides.Count == 0) return null;
      int budget = 0;
      var settings = new List<FluidTideSettings>();
      foreach (var tide in tides.Tides) {
        settings.Add(Derive(tide, weather, out int chance, out string derivation));
        list.Add(tide.Id + ": " + derivation);
        budget = Math.Max(budget, chance);
      }
      return new FluidTideSaveSettings(budget, settings);
    }

    /// <summary>
    /// A save's settings with the registered tides it does not list added (user decision 3b, 2026-11-09): each starts at
    /// its defaults for the save's mode weather (on when the mode has hazardous weather, weight = its chance), and the
    /// budget becomes the larger of the save's budget and the largest chance of an added tide that is on. So the save never
    /// gets a larger budget than its own or than the added content's own default. Tides it lists keep their settings.
    /// </summary>
    public static FluidTideSaveSettings AddMissing(FluidTideSaveSettings saved, FluidTideRegistry tides, FluidTideModeWeather weather, out IReadOnlyList<string> added) {
      if (saved == null) throw new ArgumentNullException(nameof(saved));
      if (tides == null) throw new ArgumentNullException(nameof(tides));
      if (weather == null) throw new ArgumentNullException(nameof(weather));
      var notes = new List<string>();
      added = notes;
      int budget = saved.BudgetPercent;
      var settings = new List<FluidTideSettings>(saved.Tides);
      foreach (var tide in tides.Tides) {
        if (saved.Tides.Any(t => t.TideId == tide.Id)) continue;
        var derived = Derive(tide, weather, out int chance, out string derivation);
        settings.Add(derived);
        if (derived.Enabled) budget = Math.Max(budget, chance);
        notes.Add(tide.Id + " was not in this save's settings: added " + derived + " (" + derivation + ")");
      }
      if (notes.Count > 0 && budget != saved.BudgetPercent) notes.Add("budget raised from " + saved.BudgetPercent + "% to " + budget + "%, the largest added chance");
      return new FluidTideSaveSettings(budget, settings);
    }

    /// <summary>The vanilla preset whose weather this is, or null (a mod's preset or a custom mode).</summary>
    public static string VanillaMode(FluidTideModeWeather weather) {
      if (weather == null) throw new ArgumentNullException(nameof(weather));
      for (int i = 0; i < Anchors.Length; i++) if (Same(Anchors[i], weather)) return FluidTideRules.Modes[i];
      return null;
    }

    /// <summary>Registration check: the tide's curve stays inside the allowed ranges for every hazard share in [0, 1].</summary>
    internal static void RequireCurveInRange(PendingTide tide) {
      var points = FluidTideRules.Modes.Select(m => tide.Modes[m]).ToArray();
      // Each segment is linear and rounding is monotonic, so the extremes are at the ends and the points.
      foreach (double share in new[] { 0.0, 1.0 }.Concat(Anchors.Select(a => a.HazardShare))) {
        var v = Curve(points, share);
        string at = " at hazard share " + Percent(share);
        if (v[0] < FluidTideRules.ChancePercentLowest || v[0] > FluidTideRules.ChancePercentHighest) throw new ArgumentException("the chance curve reaches " + v[0] + "%" + at);
        if (v[1] < FluidTideRules.CyclesWithoutTideLowest || v[1] > FluidTideRules.CyclesWithoutTideHighest) throw new ArgumentException("the cycles-without curve reaches " + v[1] + at);
        if (v[2] < FluidTideRules.DurationLowest || v[3] > FluidTideRules.DurationHighest || v[2] > v[3])
          throw new ArgumentException("the duration curve reaches " + v[2] + "-" + v[3] + " days" + at);
      }
    }

    private static int[] Curve(FluidTideModeValues[] points, double share) {
      int k = 0;
      while (k < Anchors.Length - 2 && share > Anchors[k + 1].HazardShare) k++;
      var a = points[k];
      var b = points[k + 1];
      double t = (share - Anchors[k].HazardShare) / (Anchors[k + 1].HazardShare - Anchors[k].HazardShare);
      return new[] {
        Along(a.ChancePercent, b.ChancePercent, t), Along(a.CyclesWithoutTide, b.CyclesWithoutTide, t),
        Along(a.MinDurationDays, b.MinDurationDays, t), Along(a.MaxDurationDays, b.MaxDurationDays, t)
      };
    }

    private static int Along(int a, int b, double t) => (int)Math.Round(a + t * (b - a), MidpointRounding.AwayFromZero);
    private static bool Same(FluidTideModeWeather a, FluidTideModeWeather b) =>
      a.TemperateMin == b.TemperateMin && a.TemperateMax == b.TemperateMax && a.DroughtMin == b.DroughtMin && a.DroughtMax == b.DroughtMax
      && a.BadtideMin == b.BadtideMin && a.BadtideMax == b.BadtideMax && a.BadtidePercent == b.BadtidePercent;
    private static string Percent(double share) => (share * 100.0).ToString("0.0", CultureInfo.InvariantCulture) + "%";
  }
}
