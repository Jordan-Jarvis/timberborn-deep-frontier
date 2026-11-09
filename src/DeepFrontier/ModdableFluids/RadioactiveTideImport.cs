using System;
using ModdableFluids;

namespace DeepFrontier.ModdableFluidsMigration {
  /// <summary>
  /// The singleton <c>DeepFrontier.RadioactiveTide</c> as RadioactiveTideService saved it, with its load checks
  /// (EnsureLoaded). Its <c>SludgeEmittedThisTide</c> is not carried over: it was only ever saved.
  /// </summary>
  public sealed class RadioactiveTideSavedState {
    public bool CurrentCycleIsTide { get; }
    public int LastTideCycle { get; }
    public int LastTideDuration { get; }

    public RadioactiveTideSavedState(bool currentCycleIsTide, int lastTideCycle, int lastTideDuration) {
      if (lastTideCycle < 0 || lastTideDuration < 0)
        throw new InvalidOperationException("Saved radioactive tide state is invalid (cycle " + lastTideCycle + ", duration " + lastTideDuration + ")");
      if (lastTideCycle == 0 && (lastTideDuration != 0 || currentCycleIsTide))
        throw new InvalidOperationException("Saved radioactive tide state has a tide without a cycle");
      if (lastTideCycle > 0 && (lastTideCycle < FluidTideRules.EarliestCycle || lastTideDuration < FluidTideRules.DurationLowest))
        throw new InvalidOperationException("Saved radioactive tide in cycle " + lastTideCycle + " lasting " + lastTideDuration + " days is impossible");
      CurrentCycleIsTide = currentCycleIsTide; LastTideCycle = lastTideCycle; LastTideDuration = lastTideDuration;
    }
  }

  /// <summary>
  /// A Deep Frontier save's radioactive tide as Moddable Fluids tide state (IFluidTideImporter, asked once for a loaded
  /// save without Moddable Fluids tide state). The settings are the save's own copy, or for a save from 0.8.3 and older
  /// the former mod settings (RadioactiveTideStartingValues.ForLoadedSave, the shipped rule).
  /// <list type="bullet">
  /// <item>State: a current tide is the last tide, <see cref="RadioactiveTideRegistration.TideId"/>, with its cycle and duration;
  /// no tide yet is cycle 0.</item>
  /// <item>Settings: budget = weight = the save's chance, so with Deep Frontier's tide alone the C′ draws are
  /// RadioactiveTideService.Choose's. A tide that is off is not range-checked (as Deep Frontier never checked it); the
  /// budget then draws nothing, because no listed tide is on and unlisted tides are off, and it is the lowest valid
  /// budget (1) rather than a value that may be out of range.</item>
  /// </list>
  /// </summary>
  public static class RadioactiveTideImport {
    public static FluidTideImport Map(RadioactiveTideSavedState state, bool enabled, int cyclesWithoutTide, int chancePercent, int minDurationDays, int maxDurationDays) {
      string id = RadioactiveTideRegistration.TideId;
      bool hasTide = state != null && state.LastTideCycle > 0;
      var settings = new FluidTideSettings(id, enabled, chancePercent, cyclesWithoutTide, minDurationDays, maxDurationDays);
      return new FluidTideImport(hasTide && state.CurrentCycleIsTide ? id : null, hasTide ? state.LastTideCycle : 0, hasTide ? id : null,
        hasTide ? state.LastTideDuration : 0, enabled ? chancePercent : FluidTideRules.BudgetPercentLowest, new[] { settings });
    }
  }
}
