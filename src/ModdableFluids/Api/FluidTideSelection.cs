using System;
using System.Collections.Generic;

namespace ModdableFluids {
  /// <summary>
  /// The random draws a tide selection makes, with the native IRandomNumberGenerator's semantics:
  /// <see cref="CheckProbability"/> is true with the given probability (always at 1), and
  /// <see cref="Range"/> is uniform over [inclusiveMin, exclusiveMax).
  /// </summary>
  public interface IFluidTideRandom {
    bool CheckProbability(float normalizedProbability);
    int Range(int inclusiveMin, int exclusiveMax);
  }

  /// <summary>
  /// The one tide-selection rule, policy C′ (user decision 2026-11-09): installed tides split one shared hazard
  /// budget, so installing more tide mods never raises a save's tide rate above its budget, and a game with one
  /// tide behaves exactly as Deep Frontier's radioactive tide did on its own. The native drought/badtide draw runs
  /// first, unchanged; this rule then decides whether the cycle's hazardous weather becomes a tide:
  /// <list type="number">
  /// <item>Cycles before <see cref="FluidTideRules.EarliestCycle"/> keep the native weather.</item>
  /// <item>A forced tide (development only) is chosen; it must be one of the save's enabled tides.</item>
  /// <item>Global cooldown: after a tide in cycle c, cycle c + 1 keeps the native weather, whichever tide it was.</item>
  /// <item>The eligible tides are the save's enabled tides whose cycles without tide have passed. None: native weather.</item>
  /// <item>One draw with the save's budget (CheckProbability(budget / 100)). A miss keeps the native weather.</item>
  /// <item>A hit picks one of the save's enabled tides by weight: with one enabled tide no further draw; otherwise one
  /// Range(0, total enabled weight) draw walked over the enabled tides in ordinal ID order. A pick that is not eligible yet
  /// keeps the native weather.</item>
  /// </list>
  /// So each eligible tide's chance in a cycle is its own slice of the budget, budget × weight / (total weight of the
  /// enabled tides), whether or not the other tides can occur yet (user decision 1b, 2026-11-09): a tide that is not
  /// eligible leaves its slice to the native weather, and the cycle's tide chance never exceeds the budget. Once every
  /// tide is eligible the shares are those of the whole budget split by weight.
  /// Registration and load order never matter: the tides are taken in ordinal ID order whatever order they are given in.
  /// With one tide the draws are exactly Deep Frontier's (RadioactiveTideService.Choose), including the random calls.
  /// </summary>
  public static class FluidTideSelection {
    /// <summary>
    /// The ID of the tide that replaces the native weather in <paramref name="cycle"/>, or null to keep the native weather.
    /// <paramref name="lastTideCycle"/> is the cycle of the save's last tide (any tide), 0 for none.
    /// </summary>
    public static string Select(int cycle, int lastTideCycle, FluidTideSaveSettings settings, string forcedTideId, IFluidTideRandom random) {
      if (settings == null) throw new ArgumentNullException(nameof(settings));
      if (random == null) throw new ArgumentNullException(nameof(random));
      if (cycle < 1) throw new ArgumentOutOfRangeException(nameof(cycle), cycle, "Cycles start at 1");
      if (lastTideCycle < 0 || lastTideCycle >= cycle || (lastTideCycle > 0 && lastTideCycle < FluidTideRules.EarliestCycle))
        throw new ArgumentOutOfRangeException(nameof(lastTideCycle), lastTideCycle, "The last tide of the save cannot be in cycle " + lastTideCycle + " when choosing cycle " + cycle);
      if (cycle < FluidTideRules.EarliestCycle) return null;
      if (forcedTideId != null) {
        foreach (var tide in settings.Tides)
          if (tide.TideId == forcedTideId) {
            if (!tide.Enabled) throw new InvalidOperationException("Tide " + forcedTideId + " is off in this game's settings (chosen when the game was started)");
            return forcedTideId;
          }
        throw new ArgumentException("Forced tide " + forcedTideId + " has no settings in this game");
      }
      if (lastTideCycle > 0 && cycle - lastTideCycle <= FluidTideRules.CooldownCycles) return null;
      // settings.Tides is in ordinal ID order (FluidTideSaveSettings sorts it).
      var enabled = new List<FluidTideSettings>();
      int total = 0;
      bool anyEligible = false;
      foreach (var tide in settings.Tides) {
        if (!tide.Enabled) continue;
        enabled.Add(tide);
        total += tide.Weight;
        anyEligible |= cycle > tide.CyclesWithoutTide;
      }
      if (!anyEligible) return null;
      if (!random.CheckProbability(settings.BudgetPercent / 100f)) return null;
      if (enabled.Count == 1) return enabled[0].TideId;
      int roll = random.Range(0, total);
      if (roll < 0 || roll >= total) throw new InvalidOperationException("The random generator returned " + roll + " outside [0, " + total + ")");
      foreach (var tide in enabled) {
        if (roll < tide.Weight) return cycle > tide.CyclesWithoutTide ? tide.TideId : null;
        roll -= tide.Weight;
      }
      throw new InvalidOperationException("Unreachable: the weighted roll passed every eligible tide");
    }
  }
}
