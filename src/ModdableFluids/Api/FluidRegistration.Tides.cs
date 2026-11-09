using System;
using System.Collections.Generic;
using System.Linq;

namespace ModdableFluids {
  /// <summary>
  /// Tide registration (capability <c>ModdableFluids.Tides.Registration</c>). Every method takes primitives only,
  /// so reflected providers can call it too. A tide is complete when it has values for Easy, Normal and Hard, a
  /// source emission, texts, art and a start sound; the registry freeze reports every missing part at once.
  /// </summary>
  public sealed partial class FluidRegistration {
    private readonly List<PendingTide> _tides = new List<PendingTide>();
    internal IReadOnlyList<PendingTide> PendingTides => _tides;

    /// <summary>
    /// Registers tide <c>OwnerModId.localName</c>. <paramref name="nativeWeatherId"/> is the hazardous weather ID the
    /// game stores in its weather history and looks up in SunSpec fog lists (the mod's content adds a
    /// HazardousWeatherFogs entry for it to every day stage); it must be unique and not a native weather.
    /// </summary>
    public void AddTide(string localName, string nativeWeatherId, string displayNameLocKey, string descriptionLocKey) {
      RequireOpen();
      FluidIds.RequireLocalName(localName, "tide local name of provider " + ProviderId);
      string id = OwnerModId + "." + localName;
      if (!FluidIds.IsModId(nativeWeatherId))
        throw new ArgumentException("Tide " + id + " needs a native weather ID of letters, digits, '_' or '-' in dot-separated segments; got '" + nativeWeatherId + "'");
      if (nativeWeatherId == FluidTideRules.NativeDroughtWeatherId || nativeWeatherId == FluidTideRules.NativeBadtideWeatherId)
        throw new ArgumentException("Tide " + id + " cannot use the native weather ID " + nativeWeatherId);
      RequireText(displayNameLocKey, id, "a display name localization key");
      RequireText(descriptionLocKey, id, "a description localization key");
      if (_tides.Any(t => t.Id == id)) throw new ArgumentException("Provider " + ProviderId + " registered tide " + id + " twice");
      if (_tides.Any(t => t.NativeWeatherId == nativeWeatherId)) throw new ArgumentException("Provider " + ProviderId + " gave two tides the weather ID " + nativeWeatherId);
      _tides.Add(new PendingTide(id, OwnerModId, localName, ProviderId, nativeWeatherId, displayNameLocKey, descriptionLocKey));
    }

    /// <summary>
    /// The tide's values for one vanilla preset (<c>Easy</c>, <c>Normal</c> or <c>Hard</c>): its chance per eligible cycle
    /// (also its default weight in the shared budget), the cycles without it, and its whole-day duration range.
    /// </summary>
    public void SetTideMode(string tideLocalName, string mode, int chancePercent, int cyclesWithoutTide, int minDurationDays, int maxDurationDays) {
      RequireOpen();
      var tide = OwnTide(tideLocalName);
      if (!FluidTideRules.Modes.Contains(mode)) throw new ArgumentException("Tide " + tide.Id + ": game mode '" + mode + "' is not Easy, Normal or Hard");
      if (tide.Modes.ContainsKey(mode)) throw new ArgumentException("Tide " + tide.Id + " was given two sets of " + mode + " values");
      try { tide.Modes.Add(mode, new FluidTideModeValues(chancePercent, cyclesWithoutTide, minDurationDays, maxDurationDays)); }
      catch (ArgumentException e) { throw new ArgumentException("Tide " + tide.Id + " " + mode + ": " + e.Message, e); }
    }

    /// <summary>
    /// While the tide is in progress, <paramref name="share"/> of every tide-overridable source's non-bad emitted volume is
    /// the registered extra fluid <paramref name="fluidId"/> (the badwater part stays badwater). Shares total at most 1.
    /// </summary>
    public void SetTideSourceEmission(string tideLocalName, string fluidId, double share) {
      RequireOpen();
      var tide = OwnTide(tideLocalName);
      if (double.IsNaN(share) || share <= 0 || share > 1) throw new ArgumentOutOfRangeException(nameof(share), share, "Tide " + tide.Id + " emission shares are in (0, 1]");
      if (fluidId == null || tide.Emission.ContainsKey(fluidId)) throw new ArgumentException("Tide " + tide.Id + " lists fluid " + fluidId + " twice or as null");
      tide.Emission.Add(fluidId, share);
    }

    /// <summary>
    /// While the tide is in progress, every tide-overridable source runs at <paramref name="multiplier"/> times its native
    /// strength, through a native water strength modifier. In (0, 1]: a larger strength would meet the game's silent cap.
    /// Without this call the strength is unchanged.
    /// </summary>
    public void SetTideSourceStrength(string tideLocalName, double multiplier) {
      RequireOpen();
      var tide = OwnTide(tideLocalName);
      if (tide.StrengthSet) throw new ArgumentException("Tide " + tide.Id + " was given two strength multipliers");
      if (double.IsNaN(multiplier) || multiplier <= 0 || multiplier > 1)
        throw new ArgumentOutOfRangeException(nameof(multiplier), multiplier, "Tide " + tide.Id + " strength multiplier is in (0, 1]");
      tide.StrengthMultiplier = multiplier; tide.StrengthSet = true;
    }

    /// <summary>
    /// Localization keys for the native weather panels and banner (the HazardousWeatherUIHelper getters), and the two lines
    /// shown under the banner header while the tide approaches and when it starts. The approaching description may use
    /// {0} for the tide's duration in days.
    /// </summary>
    public void SetTideTexts(string tideLocalName, string approachingLocKey, string inProgressLocKey, string startedLocKey, string endedLocKey,
        string approachingDescriptionLocKey, string startedDescriptionLocKey) {
      RequireOpen();
      var tide = OwnTide(tideLocalName);
      if (tide.Texts != null) throw new ArgumentException("Tide " + tide.Id + " was given texts twice");
      var texts = new[] { approachingLocKey, inProgressLocKey, startedLocKey, endedLocKey, approachingDescriptionLocKey, startedDescriptionLocKey };
      foreach (var text in texts) RequireText(text, tide.Id, "six notification localization keys");
      tide.Texts = texts;
    }

    /// <summary>Sprite asset paths: the date-panel icon, the weather-panel progress art and the banner background.</summary>
    public void SetTideArt(string tideLocalName, string iconSprite, string progressSprite, string notificationSprite) {
      RequireOpen();
      var tide = OwnTide(tideLocalName);
      if (tide.Art != null) throw new ArgumentException("Tide " + tide.Id + " was given art twice");
      var art = new[] { iconSprite, progressSprite, notificationSprite };
      foreach (var sprite in art) RequireText(sprite, tide.Id, "three sprite asset paths");
      tide.Art = art;
    }

    /// <summary>The native alarm the tide plays when it starts: <c>Badtide</c> or <c>Drought</c>.</summary>
    public void SetTideStartSound(string tideLocalName, string nativeSound) {
      RequireOpen();
      var tide = OwnTide(tideLocalName);
      if (tide.StartSound != null) throw new ArgumentException("Tide " + tide.Id + " was given two start sounds");
      if (nativeSound != FluidTideRules.BadtideSound && nativeSound != FluidTideRules.DroughtSound)
        throw new ArgumentException("Tide " + tide.Id + " start sound '" + nativeSound + "' is not Badtide or Drought");
      tide.StartSound = nativeSound;
    }

    private PendingTide OwnTide(string localName) =>
      _tides.SingleOrDefault(t => t.LocalName == localName)
        ?? throw new ArgumentException("Provider " + ProviderId + " has not registered tide " + OwnerModId + "." + localName);

    private static void RequireText(string value, string id, string what) {
      if (string.IsNullOrWhiteSpace(value)) throw new ArgumentException("Tide " + id + " needs " + what);
    }
  }
}
