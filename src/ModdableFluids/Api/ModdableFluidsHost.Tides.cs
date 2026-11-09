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
