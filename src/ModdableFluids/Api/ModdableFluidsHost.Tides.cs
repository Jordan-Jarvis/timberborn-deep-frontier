using System;
using System.Collections.Generic;
using System.Linq;

namespace ModdableFluids {
  /// <summary>
  /// The tide area of the host: its capability, and the freeze stages that collect, validate and commit every
  /// provider's tides with the rest of the registry. Problems are reported in the same FluidRegistryException.
  /// </summary>
  public sealed partial class ModdableFluidsHost {
    private List<PendingTide> _pendingTides;
    private FluidTideRegistry _tides;

    static partial void AddExtensionCapabilities(List<string> capabilities) {
      capabilities.Add(FluidTideRules.RegistrationCapability);
      capabilities.Add(FluidTideRules.ImportCapability);
    }

    /// <summary>The frozen tides, in ordinal ID order; empty when no provider registered one.</summary>
    public FluidTideRegistry Tides {
      get {
        lock (_gate) {
          if (_state == State.Faulted) throw _fault;
          return _tides ?? throw new InvalidOperationException("The Moddable Fluids registry is not frozen yet; tides are known once it freezes");
        }
      }
    }

    /// <summary>
    /// Asks every <see cref="IFluidTideImporter"/>, in provider order, for a save's tide state (see that interface). Returns
    /// null when none has any, else the one import with every registered tide listed and <paramref name="importerId"/> set to
    /// its provider. An importer that throws stops loading naming it; unknown tide IDs and two importers returning state stop
    /// loading with a <see cref="FluidSaveException"/>.
    /// </summary>
    public FluidTideImport ImportTides(FluidTideImportContext context, out string importerId) {
      if (context == null) throw new ArgumentNullException(nameof(context));
      importerId = null;
      List<ProviderEntry> importers;
      lock (_gate) {
        if (_state != State.Frozen) throw new InvalidOperationException("Tide state is imported after the registry froze");
        if (!ReferenceEquals(context.Tides, _tides)) throw new ArgumentException("The import context belongs to a different tide registry");
        importers = _providers.Where(e => e.Provider is IFluidTideImporter).ToList();
      }
      FluidTideImport found = null;
      ProviderEntry owner = null;
      foreach (var entry in importers) {
        string label = "Provider " + entry.Id + " (mod " + entry.Owner + ")";
        FluidTideImport import;
        try { import = ((IFluidTideImporter)entry.Provider).ImportTides(context); }
        catch (FluidSaveException) { throw; }
        catch (Exception e) { throw new InvalidOperationException(label + " failed to import this save's tide state: " + e.Message, e); }
        if (import == null) continue;
        if (owner != null)
          throw new FluidSaveException(new[] { "Providers " + owner.Id + " (mod " + owner.Owner + ") and " + entry.Id + " (mod " + entry.Owner + ") both import tide state for this save; only one may" });
        var problems = new List<string>();
        found = import.Complete(context.Tides, label, problems);
        if (found == null) throw new FluidSaveException(problems);
        owner = entry;
      }
      importerId = owner?.Id;
      return found;
    }

    partial void BeginFreezeExtensions() {
      _pendingTides = new List<PendingTide>();
    }

    // A provider whose Register failed contributes nothing, as with its fluids and source types.
    partial void CollectExtensions(ProviderEntry entry, FluidRegistration registration, bool failed) {
      if (!failed) _pendingTides.AddRange(registration.PendingTides);
    }

    partial void ValidateExtensions(IReadOnlyDictionary<string, PendingFluid> fluids, List<string> problems) {
      var ids = new Dictionary<string, PendingTide>(StringComparer.Ordinal);
      var weathers = new Dictionary<string, PendingTide>(StringComparer.Ordinal);
      foreach (var tide in _pendingTides.OrderBy(t => t.Id, StringComparer.Ordinal)) {
        if (ids.TryGetValue(tide.Id, out var first)) {
          problems.Add("Tide " + tide.Id + " is registered by both " + first.ProviderId + " and " + tide.ProviderId);
          continue;
        }
        ids.Add(tide.Id, tide);
        if (weathers.TryGetValue(tide.NativeWeatherId, out var other)) {
          problems.Add("Tides " + other.Id + " and " + tide.Id + " both use the native weather ID " + tide.NativeWeatherId);
          continue;
        }
        weathers.Add(tide.NativeWeatherId, tide);
        tide.Validate(fluids, problems);
      }
    }

    partial void CommitExtensions(FluidRegistry registry) {
      _tides = new FluidTideRegistry(_pendingTides.Select(t => new FluidTideDefinition(t)));
      _pendingTides = null;
    }
  }
}
