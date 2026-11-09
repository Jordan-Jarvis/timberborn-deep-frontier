using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;

namespace ModdableFluids {
  /// <summary>
  /// A compiled provider. Register it from <c>IModStarter.StartMod</c> with
  /// <see cref="ModdableFluidsEntry.RegisterProvider"/>. Its <see cref="Register"/> runs once when the
  /// registry freezes, in ordinal <see cref="ProviderId"/> order, never in registration order.
  /// Optional behaviour uses separate interfaces (<see cref="IFluidSceneProvider"/>,
  /// <see cref="IFluidStateProvider"/>), so this interface does not change when stages are added.
  /// </summary>
  public interface IFluidProvider {
    /// <summary><c>&lt;OwnerModId&gt;.&lt;LocalName&gt;</c>, unique across all providers.</summary>
    string ProviderId { get; }
    /// <summary>The owning mod's manifest ID. Only this mod's namespace can be registered.</summary>
    string OwnerModId { get; }
    /// <summary>Exact <c>major.minor.patch</c> of the oldest compatible API.</summary>
    string MinimumApiVersion { get; }
    /// <summary>Capabilities this provider needs; an unsupported entry rejects it before simulation starts.</summary>
    IReadOnlyCollection<string> RequiredCapabilities { get; }
    void Register(FluidRegistration registration);
  }

  /// <summary>Per game scene: <see cref="Activate"/> in provider order, <see cref="Unload"/> in reverse.</summary>
  public interface IFluidSceneProvider {
    void Activate(FluidScene scene);
    void Unload(FluidScene scene);
  }

  /// <summary>
  /// Provider-owned save data, stored with the world fluid state under the provider's ID.
  /// <see cref="LoadState"/> runs once per scene after every provider activated, with
  /// <c>hasState</c> false when the save holds nothing for this provider. A save written by a
  /// newer schema than <see cref="StateSchemaVersion"/> stops loading; older schemas are passed
  /// to the provider for its own explicit migration.
  /// </summary>
  public interface IFluidStateProvider {
    int StateSchemaVersion { get; }
    string SaveState(FluidScene scene);
    void LoadState(FluidScene scene, bool hasState, int schemaVersion, string state);
  }

  /// <summary>Registration-stage context; valid only during the provider's Register call.</summary>
  public sealed partial class FluidRegistration {
    private readonly List<PendingFluid> _fluids;
    private readonly List<PendingSourceType> _sources;
    private bool _closed;
    public string ProviderId { get; }
    public string OwnerModId { get; }
    internal FluidRegistration(string providerId, string ownerModId, List<PendingFluid> fluids, List<PendingSourceType> sources) {
      ProviderId = providerId; OwnerModId = ownerModId; _fluids = fluids; _sources = sources;
    }

    /// <summary>
    /// Registers source type <c>OwnerModId.localName</c>, placed from blueprint <paramref name="template"/>, which must
    /// carry a native WaterSourceSpec with the same tile count and default strength (checked in game). Capability
    /// <c>ModdableFluids.Sources.Types</c>. Every behaviour is explicit: nothing is inherited from a native kind.
    /// </summary>
    public void AddSourceType(string localName, string displayNameLocKey, string template, int tileCount, float defaultStrength,
        bool followsDrought, bool badtideContamination, bool tideOverridable) {
      RequireOpen();
      FluidIds.RequireLocalName(localName, "source type local name of provider " + ProviderId);
      string id = OwnerModId + "." + localName;
      if (string.IsNullOrWhiteSpace(displayNameLocKey)) throw new ArgumentException("Source type " + id + " needs a display name localization key");
      if (string.IsNullOrWhiteSpace(template)) throw new ArgumentException("Source type " + id + " needs its blueprint template name");
      if (tileCount < 1 || tileCount > 64) throw new ArgumentOutOfRangeException(nameof(tileCount), tileCount, "Source type " + id + " covers 1 to 64 tiles");
      if (float.IsNaN(defaultStrength) || float.IsInfinity(defaultStrength) || defaultStrength <= 0 || defaultStrength > 8f * tileCount)
        throw new ArgumentOutOfRangeException(nameof(defaultStrength), defaultStrength, "Source type " + id + " default strength must be in (0, 8 x tiles], the native limit");
      if (_sources.Any(s => s.Id == id)) throw new ArgumentException("Provider " + ProviderId + " registered source type " + id + " twice");
      _sources.Add(new PendingSourceType(id, OwnerModId, localName, ProviderId, displayNameLocKey, template, tileCount, defaultStrength,
        followsDrought, badtideContamination, tideOverridable));
    }

    /// <summary>Makes <paramref name="share"/> of the source's non-bad emitted volume the registered extra fluid <paramref name="fluidId"/>.</summary>
    public void SetSourceEmission(string sourceLocalName, string fluidId, double share) {
      RequireOpen();
      var source = OwnSource(sourceLocalName);
      if (double.IsNaN(share) || share <= 0 || share > 1) throw new ArgumentOutOfRangeException(nameof(share), share, "Source type " + source.Id + " emission shares are in (0, 1]");
      if (fluidId == null || source.Emitted.ContainsKey(fluidId)) throw new ArgumentException("Source type " + source.Id + " lists fluid " + fluidId + " twice or as null");
      source.Emitted.Add(fluidId, share);
    }

    /// <summary>Gives the source a periodic emission profile (see <see cref="FluidSourceSchedule"/>).</summary>
    public void SetSourceSchedule(string sourceLocalName, double periodHours, double activeHours, double rampHours, double activeMultiplier, double dormantMultiplier) {
      RequireOpen();
      var source = OwnSource(sourceLocalName);
      if (source.Schedule != null) throw new ArgumentException("Source type " + source.Id + " was given two schedules");
      try { source.Schedule = new FluidSourceSchedule(periodHours, activeHours, rampHours, activeMultiplier, dormantMultiplier); }
      catch (ArgumentOutOfRangeException e) { throw new ArgumentException("Source type " + source.Id + ": " + e.Message, e); }
    }

    private PendingSourceType OwnSource(string localName) =>
      _sources.SingleOrDefault(s => s.ProviderId == ProviderId && s.LocalName == localName)
        ?? throw new ArgumentException("Provider " + ProviderId + " has not registered source type " + OwnerModId + "." + localName);

    /// <summary>Registers <c>OwnerModId.localName</c>. Uses primitives only so reflected providers can call it.</summary>
    public void AddFluid(string localName, string displayNameLocKey, float red, float green, float blue, float alpha) {
      RequireOpen();
      FluidIds.RequireLocalName(localName, "fluid local name of provider " + ProviderId);
      string id = OwnerModId + "." + localName;
      if (string.IsNullOrWhiteSpace(displayNameLocKey)) throw new ArgumentException("Fluid " + id + " (provider " + ProviderId + ") needs a display name localization key");
      FluidColor color;
      try { color = new FluidColor(red, green, blue, alpha); }
      catch (ArgumentOutOfRangeException e) { throw new ArgumentException("Fluid " + id + " (provider " + ProviderId + "): " + e.Message, e); }
      if (_fluids.Any(f => f.ProviderId == ProviderId && f.Id == id)) throw new ArgumentException("Provider " + ProviderId + " registered " + id + " twice");
      _fluids.Add(new PendingFluid(id, OwnerModId, localName, ProviderId, displayNameLocKey, color));
    }

    /// <summary>Adds a namespaced property (<c>OwnerModId.Name</c>) to a fluid this provider registered.</summary>
    public void AddMetadata(string localName, string key, string value) {
      RequireOpen();
      string id = OwnerModId + "." + localName;
      var fluid = _fluids.SingleOrDefault(f => f.ProviderId == ProviderId && f.Id == id)
        ?? throw new ArgumentException("Provider " + ProviderId + " adds metadata to " + id + ", which it has not registered");
      FluidIds.RequireOwned(key, OwnerModId, "metadata key on " + id);
      if (value == null) throw new ArgumentNullException(nameof(value), "Metadata " + key + " on " + id + " needs a value");
      if (fluid.Metadata.ContainsKey(key)) throw new ArgumentException("Metadata " + key + " on " + id + " was set twice");
      fluid.Metadata.Add(key, value);
    }

    internal void Close() => _closed = true;
    private void RequireOpen() {
      if (_closed) throw new InvalidOperationException("Provider " + ProviderId + " used its registration context after Register returned");
    }
  }

  internal sealed class PendingFluid {
    internal readonly string Id, OwnerModId, LocalName, ProviderId, DisplayNameLocKey;
    internal readonly FluidColor Color;
    internal readonly SortedDictionary<string, string> Metadata = new SortedDictionary<string, string>(StringComparer.Ordinal);
    internal PendingFluid(string id, string owner, string local, string provider, string loc, FluidColor color) {
      Id = id; OwnerModId = owner; LocalName = local; ProviderId = provider; DisplayNameLocKey = loc; Color = color;
    }
  }

  /// <summary>One activated game scene. Invalid after the host unloads it.</summary>
  public sealed class FluidScene {
    private readonly FluidRegistry _registry;
    public int Serial { get; }
    public bool IsActive { get; internal set; }
    public FluidRegistry Registry {
      get {
        if (!IsActive) throw new InvalidOperationException("Fluid scene " + Serial + " is no longer active");
        return _registry;
      }
    }
    /// <summary>The scene's world fluid service; a scene activated without native transport (tests) has none.</summary>
    public IFluidWorld World {
      get {
        if (!IsActive) throw new InvalidOperationException("Fluid scene " + Serial + " is no longer active");
        return _world ?? throw new InvalidOperationException("Fluid scene " + Serial + " has no world service: it was activated without native water transport");
      }
    }
    public bool HasWorld => _world != null;
    private readonly IFluidWorld _world;
    internal FluidScene(FluidRegistry registry, int serial, IFluidWorld world) { _registry = registry; Serial = serial; _world = world; }
  }

  /// <summary>
  /// Binds a provider that has no compiled reference to this assembly. Members are found by
  /// documented name and exact signature; context parameters may be typed <c>object</c>.
  /// Required: string properties ProviderId, OwnerModId, MinimumApiVersion; string[] property
  /// RequiredCapabilities; void Register(object). Optional pairs/groups: void Activate(object)
  /// with void Unload(object); int property StateSchemaVersion with string SaveState(object)
  /// and void LoadState(object, bool, int, string). A partial group is rejected.
  /// </summary>
  internal sealed class ReflectedFluidProvider : IFluidProvider, IFluidSceneProvider, IFluidStateProvider {
    private const BindingFlags Public = BindingFlags.Public | BindingFlags.Instance;
    private readonly object _target;
    private readonly MethodInfo _register, _activate, _unload, _save, _load;
    public string ProviderId { get; }
    public string OwnerModId { get; }
    public string MinimumApiVersion { get; }
    public IReadOnlyCollection<string> RequiredCapabilities { get; }
    public int StateSchemaVersion { get; }
    internal bool HasScene => _activate != null;
    internal bool HasState => _save != null;

    internal ReflectedFluidProvider(object target) {
      _target = target ?? throw new ArgumentNullException(nameof(target));
      var type = target.GetType();
      string name = type.FullName;
      ProviderId = (string)Property(type, "ProviderId", typeof(string), true).GetValue(target);
      OwnerModId = (string)Property(type, "OwnerModId", typeof(string), true).GetValue(target);
      MinimumApiVersion = (string)Property(type, "MinimumApiVersion", typeof(string), true).GetValue(target);
      var capabilities = (string[])Property(type, "RequiredCapabilities", typeof(string[]), true).GetValue(target)
        ?? throw new ArgumentException(name + ".RequiredCapabilities returned null; return an empty array for none");
      RequiredCapabilities = (string[])capabilities.Clone();
      _register = Method(type, "Register", typeof(void), true, typeof(FluidRegistration));
      _activate = Method(type, "Activate", typeof(void), false, typeof(FluidScene));
      _unload = Method(type, "Unload", typeof(void), false, typeof(FluidScene));
      if ((_activate == null) != (_unload == null)) throw new ArgumentException(name + " must declare both Activate(object) and Unload(object), or neither");
      var schema = Property(type, "StateSchemaVersion", typeof(int), false);
      _save = Method(type, "SaveState", typeof(string), false, typeof(FluidScene));
      _load = Method(type, "LoadState", typeof(void), false, typeof(FluidScene), typeof(bool), typeof(int), typeof(string));
      int present = (schema != null ? 1 : 0) + (_save != null ? 1 : 0) + (_load != null ? 1 : 0);
      if (present != 0 && present != 3) throw new ArgumentException(name + " must declare StateSchemaVersion, SaveState(object) and LoadState(object, bool, int, string) together, or none of them");
      if (schema != null) StateSchemaVersion = (int)schema.GetValue(target);
    }

    private static PropertyInfo Property(Type type, string name, Type expected, bool required) {
      var matches = type.GetProperties(Public).Where(p => p.Name == name).ToArray();
      if (matches.Length == 0) {
        if (required) throw new ArgumentException(type.FullName + " lacks the required public property " + expected.Name + " " + name);
        return null;
      }
      var property = matches[0];
      if (matches.Length != 1 || property.PropertyType != expected || property.GetIndexParameters().Length != 0 || property.GetGetMethod() == null)
        throw new ArgumentException(type.FullName + "." + name + " must be one readable public property of type " + expected.Name);
      return property;
    }

    private static MethodInfo Method(Type type, string name, Type returns, bool required, params Type[] parameters) {
      var matches = type.GetMethods(Public).Where(m => m.Name == name).ToArray();
      if (matches.Length == 0) {
        if (required) throw new ArgumentException(type.FullName + " lacks the required public method " + name);
        return null;
      }
      if (matches.Length != 1) throw new ArgumentException(type.FullName + "." + name + " is overloaded; reflected providers need one unambiguous method");
      var method = matches[0];
      var actual = method.GetParameters();
      bool matchesSignature = method.ReturnType == returns && !method.IsGenericMethodDefinition && actual.Length == parameters.Length;
      for (int i = 0; matchesSignature && i < actual.Length; i++) {
        var p = actual[i].ParameterType;
        // The API context may be received as object, so the provider needs no compiled reference.
        matchesSignature = i == 0 ? p == parameters[0] || p == typeof(object) : p == parameters[i];
        if (actual[i].IsOut || p.IsByRef) matchesSignature = false;
      }
      if (!matchesSignature)
        throw new ArgumentException(type.FullName + "." + name + " must be " + returns.Name + " " + name + "(" + string.Join(", ", parameters.Select((p, i) => i == 0 ? "object" : p.Name)) + ")");
      return method;
    }

    public void Register(FluidRegistration registration) => Invoke(_register, registration);
    public void Activate(FluidScene scene) => Invoke(_activate, scene);
    public void Unload(FluidScene scene) => Invoke(_unload, scene);
    public string SaveState(FluidScene scene) => (string)Invoke(_save, scene);
    public void LoadState(FluidScene scene, bool hasState, int schemaVersion, string state) => Invoke(_load, scene, hasState, schemaVersion, state);

    private object Invoke(MethodInfo method, params object[] arguments) {
      try { return method.Invoke(_target, arguments); }
      catch (TargetInvocationException e) when (e.InnerException != null) {
        // Preserve the provider's own exception as the visible cause.
        System.Runtime.ExceptionServices.ExceptionDispatchInfo.Capture(e.InnerException).Throw();
        throw;
      }
    }
  }
}
