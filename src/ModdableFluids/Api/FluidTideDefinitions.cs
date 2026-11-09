using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;

namespace ModdableFluids {
  /// <summary>
  /// Fixed rules shared by every registered tide (capability <c>ModdableFluids.Tides.Registration</c>).
  /// The ranges are those of the native new-game screen's rows and of Deep Frontier's radioactive tide.
  /// </summary>
  public static class FluidTideRules {
    public const string RegistrationCapability = "ModdableFluids.Tides.Registration";
    /// <summary>Cycle 1's weather is chosen while the game loads; a tide can come from cycle 2.</summary>
    public const int EarliestCycle = 2;
    /// <summary>Global cooldown: no tide in the cycle right after any tide.</summary>
    public const int CooldownCycles = 1;
    public const int ChancePercentLowest = 1, ChancePercentHighest = 100;
    public const int WeightLowest = 1, WeightHighest = 100;
    public const int BudgetPercentLowest = 1, BudgetPercentHighest = 100;
    public const int CyclesWithoutTideLowest = 1, CyclesWithoutTideHighest = 99;
    public const int DurationLowest = 1, DurationHighest = 30;
    /// <summary>The three vanilla presets a tide defines its values for; other modes derive theirs (<see cref="FluidTideModes"/>).</summary>
    public const string Easy = "Easy", Normal = "Normal", Hard = "Hard";
    public static IReadOnlyList<string> Modes { get; } = new ReadOnlyCollection<string>(new[] { Easy, Normal, Hard });
    /// <summary>Native start sounds a tide may play (GameUISoundController.PlayBadtideStartedSound / PlayDroughtStartedSound).</summary>
    public const string BadtideSound = "Badtide", DroughtSound = "Drought";
    /// <summary>Native hazardous weather IDs (DroughtWeather.Id, BadtideWeather.Id); no tide may use them.</summary>
    public const string NativeDroughtWeatherId = "DroughtWeather", NativeBadtideWeatherId = "BadtideWeather";

    internal static void Require(int value, int lowest, int highest, string what) {
      if (value < lowest || value > highest) throw new ArgumentOutOfRangeException(what, value, what + " is " + value + "; allowed " + lowest + ".." + highest);
    }
  }

  /// <summary>One tide's values for one vanilla preset: its chance (also its default weight), cycles without it and duration.</summary>
  public sealed class FluidTideModeValues {
    public int ChancePercent { get; }
    /// <summary>The tide can happen in cycles after this one.</summary>
    public int CyclesWithoutTide { get; }
    public int MinDurationDays { get; }
    public int MaxDurationDays { get; }
    public FluidTideModeValues(int chancePercent, int cyclesWithoutTide, int minDurationDays, int maxDurationDays) {
      FluidTideRules.Require(chancePercent, FluidTideRules.ChancePercentLowest, FluidTideRules.ChancePercentHighest, "tide chance (%)");
      FluidTideRules.Require(cyclesWithoutTide, FluidTideRules.CyclesWithoutTideLowest, FluidTideRules.CyclesWithoutTideHighest, "cycles without tide");
      FluidTideRules.Require(minDurationDays, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest, "shortest tide (days)");
      FluidTideRules.Require(maxDurationDays, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest, "longest tide (days)");
      if (minDurationDays > maxDurationDays) throw new ArgumentException("The shortest tide (" + minDurationDays + " days) is longer than the longest (" + maxDurationDays + " days)");
      ChancePercent = chancePercent; CyclesWithoutTide = cyclesWithoutTide; MinDurationDays = minDurationDays; MaxDurationDays = maxDurationDays;
    }
    public override string ToString() => ChancePercent + "%, from cycle " + (CyclesWithoutTide + 1) + ", " + MinDurationDays + "-" + MaxDurationDays + " days";
  }

  /// <summary>
  /// What the native weather panels, banner and alarm show for a tide. Loc keys follow the native
  /// HazardousWeatherUIHelper getters; the two descriptions are the line under the banner header.
  /// Sprites are asset paths loaded with the game's asset loader.
  /// </summary>
  public sealed class FluidTidePresentation {
    public string ApproachingLocKey { get; }
    public string InProgressLocKey { get; }
    public string StartedLocKey { get; }
    public string EndedLocKey { get; }
    public string ApproachingDescriptionLocKey { get; }
    public string StartedDescriptionLocKey { get; }
    public string IconSprite { get; }
    public string ProgressSprite { get; }
    public string NotificationSprite { get; }
    /// <summary><see cref="FluidTideRules.BadtideSound"/> or <see cref="FluidTideRules.DroughtSound"/>.</summary>
    public string StartSound { get; }
    internal FluidTidePresentation(string approaching, string inProgress, string started, string ended, string approachingDescription, string startedDescription,
        string icon, string progress, string notification, string sound) {
      ApproachingLocKey = approaching; InProgressLocKey = inProgress; StartedLocKey = started; EndedLocKey = ended;
      ApproachingDescriptionLocKey = approachingDescription; StartedDescriptionLocKey = startedDescription;
      IconSprite = icon; ProgressSprite = progress; NotificationSprite = notification; StartSound = sound;
    }
  }

  /// <summary>
  /// A registered tide: a hazardous weather that, while it is the cycle's weather and in progress, makes every
  /// tide-overridable source emit <see cref="SourceEmission"/> (shares of its non-bad volume) at
  /// <see cref="SourceStrengthMultiplier"/> times its strength. Every installed tide shares one hazard budget
  /// per save (<see cref="FluidTideSelection"/>).
  /// </summary>
  public sealed class FluidTideDefinition {
    public string Id { get; }
    public string OwnerModId { get; }
    public string LocalName { get; }
    public string ProviderId { get; }
    /// <summary>
    /// The IHazardousWeather.Id the game stores in its weather history and looks up in every day stage's
    /// SunSpec HazardousWeatherFogs (content must add the fog entries) and in HazardousWeatherWaterSourceSpec lists.
    /// </summary>
    public string NativeWeatherId { get; }
    public string DisplayNameLocKey { get; }
    public string DescriptionLocKey { get; }
    /// <summary>Values for <see cref="FluidTideRules.Easy"/>, <see cref="FluidTideRules.Normal"/> and <see cref="FluidTideRules.Hard"/>.</summary>
    public IReadOnlyDictionary<string, FluidTideModeValues> Modes { get; }
    /// <summary>Extra fluid ID to its share of a tide-overridable source's non-bad emitted volume; ordinal order.</summary>
    public IReadOnlyDictionary<string, double> SourceEmission { get; }
    /// <summary>Multiplies the native strength of every tide-overridable source while the tide is in progress; in (0, 1].</summary>
    public double SourceStrengthMultiplier { get; }
    public FluidTidePresentation Presentation { get; }

    internal FluidTideDefinition(PendingTide pending) {
      Id = pending.Id; OwnerModId = pending.OwnerModId; LocalName = pending.LocalName; ProviderId = pending.ProviderId;
      NativeWeatherId = pending.NativeWeatherId; DisplayNameLocKey = pending.DisplayNameLocKey; DescriptionLocKey = pending.DescriptionLocKey;
      Modes = new ReadOnlyDictionary<string, FluidTideModeValues>(new SortedDictionary<string, FluidTideModeValues>(pending.Modes, StringComparer.Ordinal));
      SourceEmission = new ReadOnlyDictionary<string, double>(new SortedDictionary<string, double>(pending.Emission, StringComparer.Ordinal));
      SourceStrengthMultiplier = pending.StrengthMultiplier;
      Presentation = new FluidTidePresentation(pending.Texts[0], pending.Texts[1], pending.Texts[2], pending.Texts[3], pending.Texts[4], pending.Texts[5],
        pending.Art[0], pending.Art[1], pending.Art[2], pending.StartSound);
    }

    public FluidTideModeValues GetMode(string mode) =>
      Modes.TryGetValue(mode ?? "", out var values) ? values : throw new ArgumentException("Tide " + Id + " has no values for game mode '" + mode + "'");

    public override string ToString() => Id + " (weather " + NativeWeatherId + ")";
  }

  /// <summary>The frozen set of tides, in ordinal ID order (<see cref="ModdableFluidsHost.Tides"/>).</summary>
  public sealed class FluidTideRegistry {
    private readonly Dictionary<string, FluidTideDefinition> _byId = new Dictionary<string, FluidTideDefinition>(StringComparer.Ordinal);
    private readonly Dictionary<string, FluidTideDefinition> _byWeather = new Dictionary<string, FluidTideDefinition>(StringComparer.Ordinal);
    public IReadOnlyList<FluidTideDefinition> Tides { get; }
    public int Count => Tides.Count;

    internal FluidTideRegistry(IEnumerable<FluidTideDefinition> tides) {
      var ordered = tides.OrderBy(t => t.Id, StringComparer.Ordinal).ToArray();
      foreach (var tide in ordered) { _byId.Add(tide.Id, tide); _byWeather.Add(tide.NativeWeatherId, tide); }
      Tides = new ReadOnlyCollection<FluidTideDefinition>(ordered);
    }

    public bool TryGet(string id, out FluidTideDefinition tide) { tide = null; return id != null && _byId.TryGetValue(id, out tide); }
    public FluidTideDefinition Get(string id) => TryGet(id, out var tide) ? tide : throw new ArgumentException("Tide '" + id + "' is not registered");
    /// <summary>The tide whose native weather ID is <paramref name="weatherId"/>, as stored in the native weather history.</summary>
    public bool TryGetByWeather(string weatherId, out FluidTideDefinition tide) { tide = null; return weatherId != null && _byWeather.TryGetValue(weatherId, out tide); }
  }

  internal sealed class PendingTide {
    internal readonly string Id, OwnerModId, LocalName, ProviderId, NativeWeatherId, DisplayNameLocKey, DescriptionLocKey;
    internal readonly SortedDictionary<string, FluidTideModeValues> Modes = new SortedDictionary<string, FluidTideModeValues>(StringComparer.Ordinal);
    internal readonly SortedDictionary<string, double> Emission = new SortedDictionary<string, double>(StringComparer.Ordinal);
    internal double StrengthMultiplier = 1;
    internal bool StrengthSet;
    internal string[] Texts, Art;
    internal string StartSound;
    internal PendingTide(string id, string owner, string local, string provider, string weather, string name, string description) {
      Id = id; OwnerModId = owner; LocalName = local; ProviderId = provider; NativeWeatherId = weather; DisplayNameLocKey = name; DescriptionLocKey = description;
    }

    /// <summary>Everything that can be checked without other providers' registrations.</summary>
    internal void Validate(IReadOnlyDictionary<string, PendingFluid> fluids, List<string> problems) {
      string label = "Tide " + Id + " (provider " + ProviderId + ")";
      var missing = FluidTideRules.Modes.Where(m => !Modes.ContainsKey(m)).ToArray();
      if (missing.Length > 0) problems.Add(label + " has no values for game mode(s) " + string.Join(", ", missing) + "; call SetTideMode for Easy, Normal and Hard");
      if (Texts == null) problems.Add(label + " has no notification texts; call SetTideTexts");
      if (Art == null) problems.Add(label + " has no weather art; call SetTideArt");
      if (StartSound == null) problems.Add(label + " has no start sound; call SetTideStartSound");
      if (Emission.Count == 0) problems.Add(label + " changes no source emission; call SetTideSourceEmission");
      double total = 0;
      foreach (var pair in Emission) {
        if (!fluids.ContainsKey(pair.Key)) problems.Add(label + " makes sources emit " + pair.Key + ", which is not a registered extra fluid");
        total += pair.Value;
      }
      // Summed in ordinal order, as the source emission composer sums an active override.
      if (total > 1) problems.Add(label + " source emission shares total " + total.ToString("R", CultureInfo.InvariantCulture) + ", above 1");
      if (missing.Length == 0) {
        try { FluidTideModes.RequireCurveInRange(this); }
        catch (ArgumentException e) { problems.Add(label + ": " + e.Message); }
      }
    }
  }
}
