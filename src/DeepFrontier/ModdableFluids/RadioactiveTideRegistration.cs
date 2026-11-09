using System;
using System.Collections.Generic;
using System.Linq;
using ModdableFluids;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// Deep Frontier's radioactive tide as a Moddable Fluids tide (the flagged build passes it to
  /// <see cref="DeepFrontierRadioactiveWater"/>, built from RadioactiveTideTuning). The native weather ID stays
  /// <c>RadioactiveTideWeather</c>, so the saved weather history and the SunSpec fog entries keep working. Moddable
  /// Fluids' tide service then selects it (policy C′: with Deep Frontier's tide alone, the budget and weight are its
  /// chance and the draws are RadioactiveTideService.Choose's), restores it, shows it and owns the source emission
  /// while it is in progress. Deep Frontier installs none of its own tide patches in that build.
  /// </summary>
  public sealed class RadioactiveTideRegistration {
    public const string LocalName = "RadioactiveTide";
    public const string TideId = DeepFrontierRadioactiveWater.Owner + "." + LocalName;
    public string WeatherId { get; }
    public string NameLocKey { get; }
    public string DescriptionLocKey { get; }
    /// <summary>Easy, Normal and Hard: chance percent, cycles without tide, shortest and longest tide in days.</summary>
    public IReadOnlyList<(string Mode, int ChancePercent, int CyclesWithoutTide, int MinDays, int MaxDays)> Modes { get; }
    /// <summary>The radioactive share of every tide-overridable source's non-bad volume while the tide is in progress.</summary>
    public double SourceShare { get; }
    /// <summary>Approaching, in progress, started, ended, approaching description, started description.</summary>
    public IReadOnlyList<string> Texts { get; }
    /// <summary>Date-panel icon, weather-panel progress and banner sprites.</summary>
    public IReadOnlyList<string> Art { get; }
    public string StartSound { get; }

    public RadioactiveTideRegistration(string weatherId, string nameLocKey, string descriptionLocKey,
        IEnumerable<(string Mode, int ChancePercent, int CyclesWithoutTide, int MinDays, int MaxDays)> modes, double sourceShare,
        IReadOnlyList<string> texts, IReadOnlyList<string> art, string startSound) {
      WeatherId = weatherId; NameLocKey = nameLocKey; DescriptionLocKey = descriptionLocKey;
      Modes = (modes ?? throw new ArgumentNullException(nameof(modes))).ToArray();
      if (texts == null || texts.Count != 6) throw new ArgumentException("A tide has six notification texts");
      if (art == null || art.Count != 3) throw new ArgumentException("A tide has three sprites");
      SourceShare = sourceShare; Texts = texts.ToArray(); Art = art.ToArray(); StartSound = startSound;
    }

    // Moddable Fluids validates every value at the registry freeze and names this provider in any problem.
    internal void Register(FluidRegistration registration) {
      registration.AddTide(LocalName, WeatherId, NameLocKey, DescriptionLocKey);
      foreach (var (mode, chance, cyclesWithout, min, max) in Modes) registration.SetTideMode(LocalName, mode, chance, cyclesWithout, min, max);
      registration.SetTideSourceEmission(LocalName, DeepFrontierRadioactiveWater.FluidId, SourceShare);
      registration.SetTideTexts(LocalName, Texts[0], Texts[1], Texts[2], Texts[3], Texts[4], Texts[5]);
      registration.SetTideArt(LocalName, Art[0], Art[1], Art[2]);
      registration.SetTideStartSound(LocalName, StartSound);
    }
  }
}
