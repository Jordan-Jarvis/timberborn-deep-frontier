using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;
using System.Globalization;
using System.Linq;
using System.Text;

namespace ModdableFluids {
  /// <summary>
  /// Owns provider registration, the frozen registry and scene lifecycles. The game uses the
  /// process-wide instance at <see cref="ModdableFluidsEntry.Host"/>; tests may create their own.
  /// Lifecycle: Open (providers register) → Frozen (registry built once) → scenes activate
  /// and unload one at a time. A failed freeze leaves the host Faulted with its report.
  /// </summary>
  public sealed class ModdableFluidsHost {
    public const int ApiMajor = 0, ApiMinor = 1, ApiPatch = 0;
    public static string ApiVersion => ApiMajor + "." + ApiMinor + "." + ApiPatch;

    /// <summary>Capabilities implemented by this contract, in ordinal order. Nothing unimplemented is listed.</summary>
    public static IReadOnlyList<string> Capabilities { get; } = new ReadOnlyCollection<string>(new[] {
      "ModdableFluids.Discovery.Reflection",
      "ModdableFluids.Persistence.ComponentIdentity",
      "ModdableFluids.Persistence.ProviderState",
      "ModdableFluids.Registry.Definitions",
      "ModdableFluids.Registry.Providers",
      "ModdableFluids.Scene.Lifecycle"
    }.OrderBy(c => c, StringComparer.Ordinal).ToArray());

    private enum State { Open, Frozen, Faulted }
    private readonly object _gate = new object();
    private readonly List<ProviderEntry> _providers = new List<ProviderEntry>();
    private State _state;
    private FluidRegistry _registry;
    private FluidRegistryException _fault;
    private FluidScene _scene;
    private int _sceneSerial;
    private bool _sceneStateLoaded;

    public string Phase { get { lock (_gate) return _scene != null ? "SceneActive" : _state.ToString(); } }
    public bool IsFrozen { get { lock (_gate) return _state == State.Frozen; } }
    public FluidScene ActiveScene { get { lock (_gate) return _scene; } }

    public FluidRegistry Registry {
      get {
        lock (_gate) {
          if (_state == State.Faulted) throw _fault;
          return _registry ?? throw new InvalidOperationException("The Moddable Fluids registry is not frozen yet; it freezes before the first game scene loads");
        }
      }
    }

    public void RegisterProvider(IFluidProvider provider) {
      if (provider == null) throw new ArgumentNullException(nameof(provider));
      if (provider is ReflectedFluidProvider) throw new ArgumentException("Register reflected providers with RegisterReflectedProvider");
      Add(new ProviderEntry(provider, "Compiled", provider as IFluidSceneProvider, provider as IFluidStateProvider));
    }

    /// <summary>Reflection route: binds a plain object by documented member names (see the API documentation).</summary>
    public void RegisterReflectedProvider(object provider) {
      if (provider == null) throw new ArgumentNullException(nameof(provider));
      if (provider is IFluidProvider) throw new ArgumentException(provider.GetType().FullName + " implements IFluidProvider; register it with RegisterProvider");
      var bound = new ReflectedFluidProvider(provider);
      Add(new ProviderEntry(bound, "Reflected", bound.HasScene ? bound : null, bound.HasState ? bound : null));
    }

    private void Add(ProviderEntry entry) {
      lock (_gate) {
        if (_state != State.Open)
          throw new InvalidOperationException("Moddable Fluids registrations are closed (" + _state + "): the registry froze before the first game scene. Register provider "
            + entry.Provider.ProviderId + " from IModStarter.StartMod.");
        _providers.Add(entry);
      }
    }

    /// <summary>
    /// Validates every provider, runs their Register stage in ordinal provider order and builds the
    /// registry. The first call freezes; later calls return the same registry or rethrow the same report.
    /// </summary>
    public FluidRegistry Freeze() {
      lock (_gate) {
        if (_state == State.Frozen) return _registry;
        if (_state == State.Faulted) throw _fault;
        var problems = new List<string>();
        var accepted = new List<ProviderEntry>();
        var seen = new Dictionary<string, ProviderEntry>(StringComparer.Ordinal);
        foreach (var entry in _providers) {
          string error = ValidateProvider(entry);
          if (error != null) { problems.Add(error); continue; }
          if (seen.TryGetValue(entry.Id, out var other)) {
            problems.Add("Provider " + entry.Id + " is registered twice (" + other.Route + " and " + entry.Route + " routes, owner " + entry.Owner + ")");
            continue;
          }
          seen.Add(entry.Id, entry);
          accepted.Add(entry);
        }
        accepted.Sort((a, b) => string.CompareOrdinal(a.Id, b.Id));
        var pending = new List<PendingFluid>();
        foreach (var entry in accepted) {
          var registration = new FluidRegistration(entry.Id, entry.Owner, pending);
          int before = pending.Count;
          try { entry.Provider.Register(registration); }
          catch (Exception e) {
            pending.RemoveRange(before, pending.Count - before);
            problems.Add("Provider " + entry.Id + " (mod " + entry.Owner + ") failed during Register: " + e.GetType().Name + ": " + e.Message);
          } finally { registration.Close(); }
        }
        var byId = new Dictionary<string, PendingFluid>(StringComparer.Ordinal);
        foreach (var fluid in pending) {
          if (byId.TryGetValue(fluid.Id, out var first)) {
            problems.Add("Fluid " + fluid.Id + " is registered by both " + first.ProviderId + " and " + fluid.ProviderId + "; one owner must register a canonical fluid once");
            continue;
          }
          byId.Add(fluid.Id, fluid);
        }
        if (problems.Count > 0) {
          _fault = new FluidRegistryException(problems);
          _state = State.Faulted;
          throw _fault;
        }
        var definitions = new List<FluidDefinition> {
          BuiltIn(FluidIds.Water, "Water", "Good.Water.DisplayName", FluidNativeRole.Water),
          BuiltIn(FluidIds.Badwater, "Badwater", "Good.Badwater.DisplayName", FluidNativeRole.Badwater)
        };
        foreach (var fluid in byId.Values.OrderBy(f => f.Id, StringComparer.Ordinal))
          definitions.Add(new FluidDefinition(fluid.Id, fluid.OwnerModId, fluid.LocalName, fluid.ProviderId, fluid.DisplayNameLocKey,
            FluidNativeRole.Extra, true, fluid.Color, fluid.Metadata));
        var infos = accepted.Select(e => new FluidProviderInfo(e.Id, e.Owner, e.Provider.MinimumApiVersion, e.Route,
          e.Capabilities, e.Scene != null, e.State != null, e.State?.StateSchemaVersion ?? 0)).ToArray();
        _registry = new FluidRegistry(definitions.ToArray(), infos);
        _providers.Clear(); _providers.AddRange(accepted);
        _state = State.Frozen;
        return _registry;
      }
    }

    private static FluidDefinition BuiltIn(string id, string local, string loc, FluidNativeRole role) =>
      new FluidDefinition(id, FluidIds.BuiltInOwner, local, FluidIds.BuiltInOwner, loc, role, false, default, new SortedDictionary<string, string>(StringComparer.Ordinal));

    private static string ValidateProvider(ProviderEntry entry) {
      string id, owner;
      try { id = entry.Provider.ProviderId; owner = entry.Provider.OwnerModId; }
      catch (Exception e) { return "Provider " + entry.Provider.GetType().FullName + " failed to report its identity: " + e.Message; }
      string label = "Provider " + id + " (" + entry.Provider.GetType().FullName + ")";
      if (!FluidIds.IsModId(owner)) return label + " has an invalid owner mod ID '" + owner + "'";
      if (string.Equals(owner, FluidIds.BuiltInOwner, StringComparison.Ordinal)) return label + " uses the reserved owner '" + FluidIds.BuiltInOwner + "'";
      try { FluidIds.RequireOwned(id, owner, "provider ID"); } catch (ArgumentException e) { return label + ": " + e.Message; }
      string minimum = entry.Provider.MinimumApiVersion;
      if (!TryParseVersion(minimum, out int major, out int minor, out int patch))
        return label + " (mod " + owner + ") declares MinimumApiVersion '" + minimum + "'; expected major.minor.patch";
      bool compatible = major == ApiMajor && (ApiMajor > 0 || minor == ApiMinor) &&
        (minor < ApiMinor || (minor == ApiMinor && patch <= ApiPatch));
      if (!compatible) return label + " (mod " + owner + ") requires Moddable Fluids " + minimum + "; this runtime is " + ApiVersion;
      var capabilities = entry.Provider.RequiredCapabilities;
      if (capabilities == null) return label + " returned null RequiredCapabilities; return an empty collection for none";
      var missing = capabilities.Where(c => c == null || !Capabilities.Contains(c)).ToArray();
      if (missing.Length > 0) return label + " (mod " + owner + ") requires unsupported capabilities: " + string.Join(", ", missing.Select(c => c ?? "<null>"));
      if (capabilities.Distinct(StringComparer.Ordinal).Count() != capabilities.Count) return label + " lists a required capability twice";
      if (entry.State != null && entry.State.StateSchemaVersion < 1) return label + " declares StateSchemaVersion " + entry.State.StateSchemaVersion + "; schemas start at 1";
      entry.Id = id; entry.Owner = owner; entry.Capabilities = capabilities.OrderBy(c => c, StringComparer.Ordinal).ToArray();
      return null;
    }

    /// <summary>Strict <c>major.minor.patch</c> of non-negative decimal integers.</summary>
    public static bool TryParseVersion(string text, out int major, out int minor, out int patch) {
      major = minor = patch = 0;
      if (text == null) return false;
      var parts = text.Split('.');
      if (parts.Length != 3) return false;
      var values = new int[3];
      for (int i = 0; i < 3; i++) {
        if (parts[i].Length == 0 || parts[i].Length > 9 || parts[i].Any(c => c < '0' || c > '9') || (parts[i].Length > 1 && parts[i][0] == '0')) return false;
        values[i] = int.Parse(parts[i], NumberStyles.None, CultureInfo.InvariantCulture);
      }
      major = values[0]; minor = values[1]; patch = values[2];
      return true;
    }

    /// <summary>Activates scene providers in ordinal order. A failure unloads those already activated, in reverse.</summary>
    public FluidScene ActivateScene() {
      lock (_gate) {
        var registry = Registry;
        if (_scene != null) throw new InvalidOperationException("Fluid scene " + _scene.Serial + " is still active; unload it before activating another");
        var scene = new FluidScene(registry, ++_sceneSerial) { IsActive = true };
        var activated = new List<ProviderEntry>();
        foreach (var entry in _providers.Where(e => e.Scene != null)) {
          try { entry.Scene.Activate(scene); activated.Add(entry); }
          catch (Exception e) {
            var cleanup = UnloadProviders(activated, scene);
            scene.IsActive = false;
            throw new InvalidOperationException("Provider " + entry.Id + " (mod " + entry.Owner + ") failed to activate fluid scene " + scene.Serial
              + (cleanup.Count > 0 ? "; cleanup also failed: " + string.Join("; ", cleanup) : "; already activated providers were unloaded"), e);
          }
        }
        _scene = scene; _sceneStateLoaded = false;
        return scene;
      }
    }

    /// <summary>Unloads scene providers in reverse order. Every provider is unloaded even if one throws.</summary>
    public void UnloadScene(FluidScene scene) {
      lock (_gate) {
        RequireActive(scene);
        var failures = UnloadProviders(_providers.Where(e => e.Scene != null).ToList(), scene);
        scene.IsActive = false; _scene = null; _sceneStateLoaded = false;
        if (failures.Count > 0) throw new InvalidOperationException("Fluid scene " + scene.Serial + " unloaded with provider failures: " + string.Join("; ", failures));
      }
    }

    private static List<string> UnloadProviders(List<ProviderEntry> providers, FluidScene scene) {
      var failures = new List<string>();
      for (int i = providers.Count - 1; i >= 0; i--) {
        try { providers[i].Scene.Unload(scene); }
        catch (Exception e) { failures.Add(providers[i].Id + ": " + e.GetType().Name + ": " + e.Message); }
      }
      return failures;
    }

    /// <summary>Collects state from every stateful provider, in provider order.</summary>
    public IReadOnlyList<FluidProviderState> SaveProviderStates(FluidScene scene) {
      lock (_gate) {
        RequireActive(scene);
        var states = new List<FluidProviderState>();
        foreach (var entry in _providers.Where(e => e.State != null)) {
          string data = entry.State.SaveState(scene);
          if (data == null) throw new InvalidOperationException("Provider " + entry.Id + " (mod " + entry.Owner + ") returned null state; return an empty string for no data");
          states.Add(new FluidProviderState(entry.Id, entry.Owner, entry.State.StateSchemaVersion, data));
        }
        return states;
      }
    }

    /// <summary>
    /// Delivers saved provider state once per scene. <paramref name="saved"/> is null when the save has
    /// no Moddable Fluids data. State for an unknown, stateless or newer provider stops loading with the cause.
    /// </summary>
    public void LoadProviderStates(FluidScene scene, IReadOnlyList<FluidProviderState> saved) {
      lock (_gate) {
        RequireActive(scene);
        if (_sceneStateLoaded) throw new InvalidOperationException("Provider state was already loaded for fluid scene " + scene.Serial);
        var byId = new Dictionary<string, FluidProviderState>(StringComparer.Ordinal);
        var problems = new List<string>();
        foreach (var state in saved ?? Array.Empty<FluidProviderState>()) {
          if (byId.ContainsKey(state.ProviderId)) { problems.Add("The save stores provider " + state.ProviderId + " twice"); continue; }
          byId.Add(state.ProviderId, state);
          var entry = _providers.SingleOrDefault(e => e.Id == state.ProviderId);
          if (entry == null) problems.Add("The save needs provider " + state.ProviderId + " from mod " + state.OwnerModId + ", which is not loaded");
          else if (entry.State == null) problems.Add("Provider " + state.ProviderId + " (mod " + entry.Owner + ") no longer stores state, but this save holds schema " + state.SchemaVersion);
          else if (entry.Owner != state.OwnerModId) problems.Add("Provider " + state.ProviderId + " moved from mod " + state.OwnerModId + " to " + entry.Owner);
          else if (state.SchemaVersion > entry.State.StateSchemaVersion)
            problems.Add("Provider " + state.ProviderId + " (mod " + entry.Owner + ") state schema " + state.SchemaVersion + " is newer than the installed " + entry.State.StateSchemaVersion + "; update that mod");
        }
        if (problems.Count > 0) throw new FluidSaveException(problems);
        foreach (var entry in _providers.Where(e => e.State != null)) {
          if (byId.TryGetValue(entry.Id, out var state)) entry.State.LoadState(scene, true, state.SchemaVersion, state.Data);
          else entry.State.LoadState(scene, false, 0, null);
        }
        _sceneStateLoaded = true;
      }
    }

    private void RequireActive(FluidScene scene) {
      if (scene == null || !ReferenceEquals(scene, _scene) || !scene.IsActive) throw new InvalidOperationException("Expected the active fluid scene");
    }

    /// <summary>Plain-text runtime report for logs and support requests.</summary>
    public string DescribeRuntime() {
      lock (_gate) {
        var text = new StringBuilder();
        text.Append("Moddable Fluids ").Append(ApiVersion).Append(" (contract ").Append(ApiMajor).Append(") phase ").Append(Phase).Append('\n');
        text.Append("Capabilities: ").Append(string.Join(", ", Capabilities)).Append('\n');
        if (_state == State.Faulted) text.Append("FAULT: ").Append(_fault.Message).Append('\n');
        if (_registry != null) {
          text.Append("Registry ").Append(_registry.Fingerprint).Append(", ").Append(_registry.Count).Append(" fluids\n");
          for (int i = 0; i < _registry.Count; i++) {
            var d = _registry.Definitions[i];
            text.Append("  [").Append(i).Append("] ").Append(d.Id).Append(" role=").Append(d.NativeRole).Append(" owner=").Append(d.OwnerModId)
              .Append(" provider=").Append(d.ProviderId).Append('\n');
          }
          foreach (var p in _registry.Providers)
            text.Append("  provider ").Append(p.ProviderId).Append(" owner=").Append(p.OwnerModId).Append(" route=").Append(p.Route)
              .Append(" minimum=").Append(p.MinimumApiVersion).Append(" scene=").Append(p.HasSceneLifecycle).Append(" state=")
              .Append(p.HasState ? p.StateSchemaVersion.ToString(CultureInfo.InvariantCulture) : "none").Append('\n');
        } else {
          foreach (var entry in _providers) text.Append("  pending provider ").Append(entry.Provider.GetType().FullName).Append(" route=").Append(entry.Route).Append('\n');
        }
        if (_scene != null) text.Append("Active scene ").Append(_scene.Serial).Append('\n');
        return text.ToString();
      }
    }

    private sealed class ProviderEntry {
      internal readonly IFluidProvider Provider;
      internal readonly string Route;
      internal readonly IFluidSceneProvider Scene;
      internal readonly IFluidStateProvider State;
      internal string Id, Owner;
      internal string[] Capabilities;
      internal ProviderEntry(IFluidProvider provider, string route, IFluidSceneProvider scene, IFluidStateProvider state) {
        Provider = provider; Route = route; Scene = scene; State = state;
      }
    }
  }
}
