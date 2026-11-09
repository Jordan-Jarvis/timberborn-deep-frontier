using System;
using System.Collections.Generic;
using System.Linq;

namespace ModdableFluids {
  /// <summary>
  /// Optional provider interface (capability <c>ModdableFluids.Tides.Import</c>, compiled providers only): reads one save's
  /// tide state and settings from another tide system, once. Moddable Fluids asks every importer, in provider order, when a
  /// loaded save (not a new game) has neither <c>ModdableFluids.Tides</c> nor <c>ModdableFluids.TideSettings</c>, before
  /// the tide service resolves its settings or restores the cycle's weather. Return null when the save holds nothing for
  /// this importer. The result is validated like a saved state; if two importers return one, the load stops naming both.
  /// The next save writes Moddable Fluids' own keys, so a save is imported at most once.
  /// </summary>
  public interface IFluidTideImporter {
    FluidTideImport ImportTides(FluidTideImportContext context);
  }

  /// <summary>What an importer is given. The native services are passed as objects so this assembly stays free of game types.</summary>
  public sealed class FluidTideImportContext {
    public FluidTideRegistry Tides { get; }
    /// <summary>The save's <c>Timberborn.WorldPersistence.ISingletonLoader</c>: the importer reads its own singletons from it.</summary>
    public object NativeSingletonLoader { get; }
    /// <summary>The game's <c>Timberborn.SettingsSystem.ISettings</c> (player settings, where older mod settings were stored).</summary>
    public object NativeSettings { get; }

    public FluidTideImportContext(FluidTideRegistry tides, object nativeSingletonLoader, object nativeSettings) {
      Tides = tides ?? throw new ArgumentNullException(nameof(tides));
      NativeSingletonLoader = nativeSingletonLoader ?? throw new ArgumentNullException(nameof(nativeSingletonLoader));
      NativeSettings = nativeSettings;
    }
  }

  /// <summary>
  /// One save's tide state and settings read from another format. The state follows the rules of a saved state: no last
  /// tide means cycle 0, no ID and no duration; a last tide is in cycle <see cref="FluidTideRules.EarliestCycle"/> or later
  /// and lasted at least a day; the current cycle's tide, if any, is the last tide. Tides the import does not list are off
  /// in the save, as for a tide registered after a save was made.
  /// </summary>
  public sealed class FluidTideImport {
    public string CurrentCycleTideId { get; }
    public int LastTideCycle { get; }
    public string LastTideId { get; }
    public int LastTideDuration { get; }
    /// <summary>The budget and the listed tides (after <see cref="ModdableFluidsHost.ImportTides"/>: every registered tide).</summary>
    public FluidTideSaveSettings Settings { get; }

    public FluidTideImport(string currentCycleTideId, int lastTideCycle, string lastTideId, int lastTideDuration, int budgetPercent, IEnumerable<FluidTideSettings> tides)
      : this(currentCycleTideId, lastTideCycle, lastTideId, lastTideDuration, new FluidTideSaveSettings(budgetPercent, tides)) { }

    private FluidTideImport(string current, int lastCycle, string lastId, int lastDuration, FluidTideSaveSettings settings) {
      if (lastCycle < 0 || lastDuration < 0) throw new ArgumentOutOfRangeException("lastTideCycle", "An imported tide cycle and duration are not negative");
      if (lastCycle == 0 && (lastId != null || lastDuration != 0 || current != null))
        throw new ArgumentException("An imported state without a last tide (cycle 0) has no tide ID, duration or current tide");
      if (lastCycle > 0 && (lastId == null || lastCycle < FluidTideRules.EarliestCycle || lastDuration < FluidTideRules.DurationLowest))
        throw new ArgumentException("An imported last tide in cycle " + lastCycle + " lasting " + lastDuration + " days (" + (lastId ?? "no ID") + ") is impossible");
      if (current != null && current != lastId) throw new ArgumentException("The imported current tide " + current + " is not the last tide " + lastId);
      CurrentCycleTideId = current; LastTideCycle = lastCycle; LastTideId = lastId; LastTideDuration = lastDuration; Settings = settings;
    }

    /// <summary>This import with every registered tide listed (unlisted ones off), after checking every ID against the registry.</summary>
    internal FluidTideImport Complete(FluidTideRegistry tides, string importer, List<string> problems) {
      foreach (var id in new[] { CurrentCycleTideId, LastTideId }.Where(id => id != null).Distinct())
        if (!tides.TryGet(id, out _)) problems.Add(importer + " imported the tide " + id + ", which no installed mod registers");
      foreach (var tide in Settings.Tides)
        if (!tides.TryGet(tide.TideId, out _)) problems.Add(importer + " imported settings for the tide " + tide.TideId + ", which no installed mod registers");
      if (problems.Count > 0) return null;
      var unlisted = tides.Tides.Where(t => Settings.Tides.All(s => s.TideId != t.Id)).Select(t => new FluidTideSettings(t.Id, false, 0, 0, 0, 0));
      return new FluidTideImport(CurrentCycleTideId, LastTideCycle, LastTideId, LastTideDuration, new FluidTideSaveSettings(Settings.BudgetPercent, Settings.Tides.Concat(unlisted)));
    }

    public override string ToString() =>
      (CurrentCycleTideId != null ? "current " + CurrentCycleTideId + ", " : "") + (LastTideId != null ? "last " + LastTideId + " in cycle " + LastTideCycle + " for " + LastTideDuration + " days" : "no tide yet")
      + "; " + Settings;
  }
}
