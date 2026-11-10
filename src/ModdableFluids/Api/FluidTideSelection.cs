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
      var e = new Eligibility(cycle, settings);
      if (e.Tides.Count == 0) return null;
      // Every enabled tide eligible: exactly the budget, as Deep Frontier's single tide drew it.
      float chance = e.Tides.Count == e.Enabled ? settings.BudgetPercent / 100f
        : (float)(settings.BudgetPercent * (double)Math.Min((long)e.We * e.M, (long)e.Me * e.W) / (100.0 * e.W * e.M));
      if (!random.CheckProbability(chance)) return null;
      if (e.Tides.Count == 1) return e.Tides[0].TideId;
      int roll = random.Range(0, e.We);
      if (roll < 0 || roll >= e.We) throw new InvalidOperationException("The random generator returned " + roll + " outside [0, " + e.We + ")");
      foreach (var tide in e.Tides) {
        if (roll < tide.Weight) return tide.TideId;
        roll -= tide.Weight;
      }
      throw new InvalidOperationException("Unreachable: the weighted roll passed every eligible tide");
    }

    /// <summary>
    /// The same rule as integer weights for one hazardous stage of Moddable Weathers (WeatherGenerator.DecideWeather draws
    /// a stage's weather in proportion to the integer GetChance of every enabled hazardous weather; 0 leaves one out).
    /// <paramref name="otherWeight"/> O is the summed weight of the stage's other (non-tide) enabled hazardous weathers.
    /// Returns one weight per entry of <paramref name="settings"/>.Tides (ordinal ID order), 0 for a tide that cannot occur.
    /// <list type="bullet">
    /// <item>Eligibility is <see cref="Select"/>'s: cycle, forced tide, global cooldown, on/off, cycles without. Under Moddable
    /// Weathers a cycle may have several hazardous stages; <paramref name="lastTideCycle"/> equal to
    /// <paramref name="cycle"/> means a tide in an earlier stage of this cycle, and then no tide (at most one per cycle).</item>
    /// <item>With the cycle's tide chance p = Pn / Pd (as Select), the tides together get K, the integer nearest to
    /// X = O × p / (1 − p) (halves up), at least one per eligible tide, so that K / (O + K) ≈ p.</item>
    /// <item>K is split over the eligible tides by weight with the largest-remainder (Hamilton) method, ties to the earlier
    /// tide in ordinal order; a tide whose share rounds to 0 gets 1 from the tide with the largest share (the earlier on a
    /// tie), so every eligible tide can occur.</item>
    /// <item>p = 1 (budget 100% and every enabled tide eligible): K = int.MaxValue − O; the other weathers keep O / (2³¹ − 1).</item>
    /// <item>O = 0 (no other hazardous weather can occur in the stage): the weights are the tides' own, so a tide is certain
    /// and picked as Select picks it.</item>
    /// <item>A forced tide (development) gets int.MaxValue − O and every other tide 0; it ignores cycles without, the budget
    /// and the cooldown, and is refused in a cycle that already has a tide.</item>
    /// </list>
    /// Error (docs/fluids-tides.md, "Integer weights"): with X ≥ n − ½ for n eligible tides, |K − X| ≤ ½, so the stage's
    /// tide chance K / (O + K) is within (1 − p)² / (2O − (1 − p)) of p, and each tide's chance within
    /// |kᵢ − K·wᵢ/We| / (O + K) of its exact split of K / (O + K) (under one weight unit, two when a share is below one unit).
    /// O + K never exceeds int.MaxValue (Moddable Weathers sums the weights as an int); larger weights are refused.
    /// </summary>
    public static int[] StageWeights(int cycle, int lastTideCycle, FluidTideSaveSettings settings, string forcedTideId, long otherWeight) {
      if (settings == null) throw new ArgumentNullException(nameof(settings));
      if (cycle < 1) throw new ArgumentOutOfRangeException(nameof(cycle), cycle, "Cycles start at 1");
      if (lastTideCycle < 0 || lastTideCycle > cycle || (lastTideCycle > 0 && lastTideCycle < FluidTideRules.EarliestCycle))
        throw new ArgumentOutOfRangeException(nameof(lastTideCycle), lastTideCycle, "The last tide cannot be in cycle " + lastTideCycle + " when weighing cycle " + cycle);
      if (otherWeight < 0 || otherWeight >= int.MaxValue)
        throw new ArgumentOutOfRangeException(nameof(otherWeight), otherWeight, "The other hazardous weathers' summed weight must be in [0, " + int.MaxValue + ")");
      var weights = new int[settings.Tides.Count];
      if (cycle < FluidTideRules.EarliestCycle) return weights;
      if (forcedTideId != null) {
        if (lastTideCycle == cycle) throw new InvalidOperationException("Tide " + forcedTideId + " was forced into cycle " + cycle + ", which already has a tide");
        for (int i = 0; i < settings.Tides.Count; i++)
          if (settings.Tides[i].TideId == forcedTideId) {
            if (!settings.Tides[i].Enabled) throw new InvalidOperationException("Tide " + forcedTideId + " is off in this game's settings (chosen when the game was started)");
            weights[i] = (int)(int.MaxValue - otherWeight);
            return weights;
          }
        throw new ArgumentException("Forced tide " + forcedTideId + " has no settings in this game");
      }
      if (lastTideCycle > 0 && cycle - lastTideCycle <= FluidTideRules.CooldownCycles) return weights;
      var e = new Eligibility(cycle, settings);
      int n = e.Tides.Count;
      if (n == 0) return weights;
      var index = new int[n];
      for (int i = 0, j = 0; i < settings.Tides.Count; i++) if (j < n && ReferenceEquals(settings.Tides[i], e.Tides[j])) index[j++] = i;
      if (otherWeight == 0) {
        for (int j = 0; j < n; j++) weights[index[j]] = e.Tides[j].Weight;
        return weights;
      }
      // p = Pn / Pd exactly (Select's chance before its float conversion).
      long pn = checked(settings.BudgetPercent * Math.Min((long)e.We * e.M, (long)e.Me * e.W));
      long pd = checked(100L * e.W * e.M);
      long k;
      if (pn == pd) k = int.MaxValue - otherWeight;
      else {
        // The integer nearest to X = O·pn / (pd − pn), halves up: floor((2·O·pn + (pd − pn)) / (2·(pd − pn))).
        long gap = pd - pn;
        k = checked(2 * otherWeight * pn + gap) / checked(2 * gap);
        if (k < n) k = n;
      }
      if (k < n || otherWeight + k > int.MaxValue)
        throw new InvalidOperationException("Moddable Fluids tides: the hazardous weathers' weights (" + otherWeight + " for the others, " + k
          + " for the tides) exceed Moddable Weathers' integer roll (" + int.MaxValue + ")");
      var shares = new long[n];
      var remainders = new long[n];
      long given = 0;
      for (int j = 0; j < n; j++) {
        long scaled = checked(k * e.Tides[j].Weight);
        shares[j] = scaled / e.We; remainders[j] = scaled % e.We; given += shares[j];
      }
      // Largest remainders first; on a tie the earlier tide in ordinal order.
      var order = new int[n];
      for (int j = 0; j < n; j++) order[j] = j;
      Array.Sort(order, (a, b) => remainders[a] != remainders[b] ? remainders[b].CompareTo(remainders[a]) : a.CompareTo(b));
      for (long left = k - given, j = 0; left > 0; left--, j++) shares[order[j]]++;
      for (int j = 0; j < n; j++) {
        if (shares[j] > 0) continue;
        int donor = 0;
        for (int d = 1; d < n; d++) if (shares[d] > shares[donor]) donor = d;
        shares[donor]--; shares[j]++;
      }
      for (int j = 0; j < n; j++) weights[index[j]] = (int)shares[j];
      return weights;
    }

    /// <summary>The save's enabled tides, and those of them the cycle may have, in ordinal ID order.</summary>
    private sealed class Eligibility {
      /// <summary>The eligible tides.</summary>
      internal readonly List<FluidTideSettings> Tides = new List<FluidTideSettings>();
      /// <summary>Enabled tides: their count, total weight W and largest weight M.</summary>
      internal readonly int Enabled, W, M;
      /// <summary>Eligible tides: total weight We and largest weight Me.</summary>
      internal readonly int We, Me;

      internal Eligibility(int cycle, FluidTideSaveSettings settings) {
        // settings.Tides is in ordinal ID order (FluidTideSaveSettings sorts it).
        foreach (var tide in settings.Tides) {
          if (!tide.Enabled) continue;
          Enabled++; W += tide.Weight; M = Math.Max(M, tide.Weight);
          if (cycle <= tide.CyclesWithoutTide) continue;
          Tides.Add(tide); We += tide.Weight; Me = Math.Max(Me, tide.Weight);
        }
      }
    }
  }
}
