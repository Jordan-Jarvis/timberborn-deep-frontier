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
  /// <item>One draw with the cycle's tide chance p (below). A miss keeps the native weather.</item>
  /// <item>A hit picks one eligible tide by weight: with one eligible tide no further draw; otherwise one
  /// Range(0, total eligible weight) draw walked over the eligible tides in ordinal ID order.</item>
  /// </list>
  /// The cycle's tide chance (user decisions 1b and 1c, 2026-11-09), with B the budget, W and m the total and the largest
  /// weight of the save's enabled tides, and We and me those of the eligible ones:
  /// p = B × min(We / W, me / m).
  /// <list type="bullet">
  /// <item>Every enabled tide eligible: p = B exactly (CheckProbability(budget / 100f)), the budget split by weight.</item>
  /// <item>Otherwise each eligible tide gets at most its own slice B × w / W (1b), and the cycle at most B × me / m (1c): with
  /// the default weights (each tide's chance) and budget (the largest chance) that is the largest chance among the eligible
  /// tides, so no cycle is harder than the hardest eligible tide would be alone. A budget the player raised scales the cap
  /// with it.</item>
  /// </list>
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
      var eligible = new List<FluidTideSettings>();
      int enabled = 0, total = 0, largest = 0, eligibleTotal = 0, eligibleLargest = 0;
      foreach (var tide in settings.Tides) {
        if (!tide.Enabled) continue;
        enabled++; total += tide.Weight; largest = Math.Max(largest, tide.Weight);
        if (cycle <= tide.CyclesWithoutTide) continue;
        eligible.Add(tide); eligibleTotal += tide.Weight; eligibleLargest = Math.Max(eligibleLargest, tide.Weight);
      }
      if (eligible.Count == 0) return null;
      // Every enabled tide eligible: exactly the budget, as Deep Frontier's single tide drew it.
      float chance = eligible.Count == enabled ? settings.BudgetPercent / 100f
        : (float)(settings.BudgetPercent * (double)Math.Min((long)eligibleTotal * largest, (long)eligibleLargest * total) / (100.0 * total * largest));
      if (!random.CheckProbability(chance)) return null;
      if (eligible.Count == 1) return eligible[0].TideId;
      int roll = random.Range(0, eligibleTotal);
      if (roll < 0 || roll >= eligibleTotal) throw new InvalidOperationException("The random generator returned " + roll + " outside [0, " + eligibleTotal + ")");
      foreach (var tide in eligible) {
        if (roll < tide.Weight) return tide.TideId;
        roll -= tide.Weight;
      }
      throw new InvalidOperationException("Unreachable: the weighted roll passed every eligible tide");
    }
  }
}
