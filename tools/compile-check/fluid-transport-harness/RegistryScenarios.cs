using System.Reflection;
using System.Runtime.Loader;
using ModdableFluids;

/// <summary>Public registry, provider, lifecycle and discovery contract (ModdableFluids 0.1).</summary>
internal static class RegistryScenarios {
  internal sealed record Fluid(string Local, string Loc, float R = .5f, float G = .5f, float B = .5f, float A = 1f, (string Key, string Value)[]? Metadata = null);

  internal class PlainProvider : IFluidProvider {
    private readonly Fluid[] _fluids;
    private readonly List<string> _log;
    public string ProviderId { get; }
    public string OwnerModId { get; }
    public string MinimumApiVersion { get; init; } = "0.1.0";
    public IReadOnlyCollection<string> RequiredCapabilities { get; init; } = new[] { "ModdableFluids.Registry.Definitions" };
    public Action<FluidRegistration>? Extra { get; init; }
    public FluidRegistration? Kept { get; private set; }
    public PlainProvider(string id, string owner, List<string> log, params Fluid[] fluids) { ProviderId = id; OwnerModId = owner; _log = log; _fluids = fluids; }
    public void Register(FluidRegistration registration) {
      _log.Add("register " + ProviderId); Kept = registration;
      foreach (var f in _fluids) {
        registration.AddFluid(f.Local, f.Loc, f.R, f.G, f.B, f.A);
        foreach (var (key, value) in f.Metadata ?? Array.Empty<(string, string)>()) registration.AddMetadata(f.Local, key, value);
      }
      Extra?.Invoke(registration);
    }
  }

  internal class SceneProvider : PlainProvider, IFluidSceneProvider {
    public bool FailActivate { get; init; }
    public bool FailUnload { get; init; }
    private readonly List<string> _log;
    public SceneProvider(string id, string owner, List<string> log, params Fluid[] fluids) : base(id, owner, log, fluids) { _log = log; }
    public void Activate(FluidScene scene) { _log.Add("activate " + ProviderId + " " + scene.Serial); if (FailActivate) throw new InvalidOperationException("activate failed for " + ProviderId); }
    public void Unload(FluidScene scene) { _log.Add("unload " + ProviderId + " " + scene.Serial); if (FailUnload) throw new InvalidOperationException("unload failed for " + ProviderId); }
  }

  internal sealed class StateProvider : SceneProvider, IFluidStateProvider {
    public int StateSchemaVersion { get; init; } = 1;
    public string State { get; set; } = "";
    public (bool HasState, int Schema, string? State)? Loaded { get; private set; }
    public StateProvider(string id, string owner, List<string> log, params Fluid[] fluids) : base(id, owner, log, fluids) { }
    public string SaveState(FluidScene scene) => State;
    public void LoadState(FluidScene scene, bool hasState, int schemaVersion, string state) => Loaded = (hasState, schemaVersion, state);
  }

  /// <summary>A reflected provider with no API types in its signatures.</summary>
  public sealed class PlainReflected {
    public string ProviderId => "ExampleCreator.Juices";
    public string OwnerModId => "ExampleCreator";
    public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => new[] { "ModdableFluids.Discovery.Reflection" };
    public int StateSchemaVersion => 3;
    public List<string> Log { get; } = new();
    public string Saved { get; set; } = "orchard";
    public void Register(object registration) {
      var add = registration.GetType().GetMethod("AddFluid")!;
      add.Invoke(registration, new object[] { "Juice", "ExampleCreator.Juice.DisplayName", .9f, .5f, .1f, .8f });
    }
    public void Activate(object scene) => Log.Add("activate");
    public void Unload(object scene) => Log.Add("unload");
    public string SaveState(object scene) => Saved;
    public void LoadState(object scene, bool hasState, int schemaVersion, string state) => Log.Add($"load {hasState} {schemaVersion} {state}");
  }
  public sealed class ReflectedActivateOnly {
    public string ProviderId => "ExampleCreator.Partial"; public string OwnerModId => "ExampleCreator"; public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => Array.Empty<string>();
    public void Register(object registration) { }
    public void Activate(object scene) { }
  }
  public sealed class ReflectedPartialState {
    public string ProviderId => "ExampleCreator.PartialState"; public string OwnerModId => "ExampleCreator"; public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => Array.Empty<string>();
    public int StateSchemaVersion => 1;
    public void Register(object registration) { }
    public string SaveState(object scene) => "";
  }
  public sealed class ReflectedOverloaded {
    public string ProviderId => "ExampleCreator.Overloaded"; public string OwnerModId => "ExampleCreator"; public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => Array.Empty<string>();
    public void Register(object registration) { }
    public void Register(string registration) { }
  }
  public sealed class ReflectedWrongCapabilities {
    public string ProviderId => "ExampleCreator.Wrong"; public string OwnerModId => "ExampleCreator"; public string MinimumApiVersion => "0.1.0";
    public List<string> RequiredCapabilities => new();
    public void Register(object registration) { }
  }
  public sealed class ReflectedWrongReturn {
    public string ProviderId => "ExampleCreator.Return"; public string OwnerModId => "ExampleCreator"; public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => Array.Empty<string>();
    public int Register(object registration) => 0;
  }
  public sealed class ReflectedMissingOwner {
    public string ProviderId => "ExampleCreator.NoOwner"; public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => Array.Empty<string>();
    public void Register(object registration) { }
  }
  public sealed class ReflectedThrows {
    public string ProviderId => "ExampleCreator.Throws"; public string OwnerModId => "ExampleCreator"; public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => Array.Empty<string>();
    public void Register(object registration) => throw new FormatException("orchard data unreadable");
  }

  internal static void Run(Action<bool, string> check, Action<string, Action> scenario, string managed, string reflectionConsumerPath, Dictionary<string, object> observations) {
    void Rejects<T>(Action action, string name, string? mustMention = null) where T : Exception {
      Exception? caught = null;
      try { action(); } catch (Exception e) { caught = e; }
      check(caught is T, name + $": expected {typeof(T).Name}, got {caught?.GetType().Name ?? "no exception"} {caught?.Message}");
      if (mustMention != null) check(caught!.Message.Contains(mustMention, StringComparison.Ordinal), name + ": message lacks '" + mustMention + "': " + caught.Message);
    }

    scenario("fluid and mod IDs are validated as authored, never normalized", () => {
      foreach (string id in new[] { "DeepFrontier", "eMka.ModSettings", "Lapantouflemagic.1x1x2Storage", "KnatteAnka.waterextention", "Timberborn.IgorZ.TimberCommons", "Mod-Name_2" })
        check(FluidIds.IsModId(id), "Real mod ID rejected: " + id);
      foreach (string id in new[] { "", ".", "a..b", ".a", "a.", "a b", "Juice!", "Säft", " DeepFrontier", "DeepFrontier " })
        check(!FluidIds.IsModId(id), "Invalid mod ID accepted: '" + id + "'");
      foreach (string local in new[] { "Juice", "RadioactiveWater", "water_2", "x" }) check(FluidIds.IsLocalName(local), "Local name rejected: " + local);
      foreach (string local in new[] { "", "2Juice", "Juice.Box", "_Juice", "Ju ice", "Juice-1" }) check(!FluidIds.IsLocalName(local), "Invalid local name accepted: " + local);
      check(FluidIds.TrySplit("eMka.ModSettings.Coffee", out var owner, out var name) && owner == "eMka.ModSettings" && name == "Coffee", "Dotted owner split");
      check(!FluidIds.TrySplit("Coffee", out _, out _) && !FluidIds.TrySplit("MoreFluids.", out _, out _), "Malformed IDs split");
      check(FluidIds.Compose("MoreFluids", "Coffee") == "MoreFluids.Coffee", "Compose");
      Rejects<ArgumentException>(() => FluidIds.RequireOwned("MoreFluids.Coffee", "DeepFrontier", "fluid"), "Foreign namespace");
      Rejects<ArgumentException>(() => FluidIds.RequireOwned("morefluids.Coffee", "MoreFluids", "fluid"), "Case-folded owner accepted");
    });

    ModdableFluidsHost Host(List<string> log, IEnumerable<object> providers) {
      var host = new ModdableFluidsHost();
      foreach (var provider in providers) {
        if (provider is IFluidProvider compiled) host.RegisterProvider(compiled); else host.RegisterReflectedProvider(provider);
      }
      return host;
    }
    IEnumerable<object> Standard(List<string> log) => new object[] {
      new SceneProvider("MoreFluids.Drinks", "MoreFluids", log, new Fluid("Coffee", "MoreFluids.Coffee.DisplayName", .3f, .2f, .1f, .9f, new[] { ("MoreFluids.Caffeine", "2") })),
      new PlainProvider("DeepFrontier.Radiation", "DeepFrontier", log, new Fluid("RadioactiveWater", "DeepFrontier.RadioactiveWater.DisplayName", .7f, 1f, .1f, .8f)),
      new PlainReflected(),
      new PlainProvider("MoreFluids.Sea", "MoreFluids", log, new Fluid("Saltwater", "MoreFluids.Saltwater.DisplayName", .2f, .4f, .8f, .6f), new Fluid("Brine", "MoreFluids.Brine.DisplayName"))
    };

    scenario("registry handles and fingerprints do not depend on registration order", () => {
      var logA = new List<string>(); var logB = new List<string>();
      var a = Host(logA, Standard(logA)).Freeze();
      var b = Host(logB, Standard(logB).Reverse()).Freeze();
      check(a.Fingerprint == b.Fingerprint && a.Fingerprint.Length == 64, "Fingerprint depends on registration order");
      string[] expected = { FluidIds.Water, FluidIds.Badwater, "DeepFrontier.RadioactiveWater", "ExampleCreator.Juice", "MoreFluids.Brine", "MoreFluids.Coffee", "MoreFluids.Saltwater" };
      check(a.Definitions.Select(d => d.Id).SequenceEqual(expected) && b.Definitions.Select(d => d.Id).SequenceEqual(expected), "Handle order is not built-ins then ordinal IDs");
      for (int i = 0; i < expected.Length; i++) check(a.GetHandle(expected[i]).Index == i && b.GetHandle(expected[i]).Index == i, "Handle index differs for " + expected[i]);
      string[] registerOrder = { "register DeepFrontier.Radiation", "register MoreFluids.Drinks", "register MoreFluids.Sea" };
      check(logA.SequenceEqual(registerOrder) && logB.SequenceEqual(registerOrder), "Register stage did not run in ordinal provider order: " + string.Join(", ", logB));
      check(a.Water.Index == FluidRegistry.WaterIndex && a.Badwater.Index == FluidRegistry.BadwaterIndex, "Built-in slots");
      var water = a.Get(a.Water);
      check(water.NativeRole == FluidNativeRole.Water && !water.HasColor && water.OwnerModId == "Timberborn", "Built-in water definition");
      var coffee = a.Get(a.GetHandle("MoreFluids.Coffee"));
      check(coffee.NativeRole == FluidNativeRole.Extra && coffee.HasColor && coffee.Color.Equals(new FluidColor(.3f, .2f, .1f, .9f)) &&
        coffee.ProviderId == "MoreFluids.Drinks" && coffee.Metadata["MoreFluids.Caffeine"] == "2", "Extra definition contents");
      check(a.Get(a.GetHandle("ExampleCreator.Juice")).ProviderId == "ExampleCreator.Juices", "Reflected registration");
      check(a.Providers.Select(p => p.ProviderId).SequenceEqual(new[] { "DeepFrontier.Radiation", "ExampleCreator.Juices", "MoreFluids.Drinks", "MoreFluids.Sea" }), "Provider info order");
      check(a.Providers.Single(p => p.ProviderId == "ExampleCreator.Juices") is { Route: "Reflected", HasSceneLifecycle: true, HasState: true, StateSchemaVersion: 3 }, "Reflected provider info");
      Rejects<ArgumentException>(() => new ModdableFluidsHost().Freeze().Get(a.Water), "Handle from a registry with different content");
      Rejects<ArgumentException>(() => a.GetHandle("MoreFluids.Tea"), "Unknown fluid handle");
      observations["registryFingerprint"] = a.Fingerprint;
      observations["registryFluids"] = a.Count;
    });

    scenario("freezing reports every invalid provider and definition together", () => {
      var log = new List<string>();
      var host = Host(log, new object[] {
        new PlainProvider("MoreFluids.Drinks", "MoreFluids", log, new Fluid("Coffee", "MoreFluids.Coffee.DisplayName")),
        new PlainProvider("OtherPack.Drinks", "OtherPack", log, new Fluid("Coffee", "OtherPack.Coffee.DisplayName")),
        new PlainProvider("MoreFluids.Again", "MoreFluids", log, new Fluid("Coffee", "MoreFluids.Coffee.DisplayName")),
        new PlainProvider("Timberborn.Water", "Timberborn", log, new Fluid("Water", "Good.Water.DisplayName")),
        new PlainProvider("Thief.Drinks", "MoreFluids", log),
        new PlainProvider("Old.Provider", "Old", log) { MinimumApiVersion = "0.1" },
        new PlainProvider("Future.Major", "Future", log) { MinimumApiVersion = "1.0.0" },
        new PlainProvider("Future.Minor", "Future", log) { MinimumApiVersion = "0.2.0" },
        new PlainProvider("Future.Patch", "Future", log) { MinimumApiVersion = "0.1.5" },
        new PlainProvider("Needs.Rendering", "Needs", log) { RequiredCapabilities = new[] { "ModdableFluids.Rendering" } },
        new PlainProvider("Twice.Provider", "Twice", log), new PlainProvider("Twice.Provider", "Twice", log),
        new PlainProvider("Bad.Colour", "Bad", log, new Fluid("Glow", "Bad.Glow", 1.5f)),
        new PlainProvider("Bad.Loc", "Bad", log, new Fluid("Blank", " ")),
        new PlainProvider("Bad.Metadata", "Bad", log, new Fluid("Tagged", "Bad.Tagged", Metadata: new[] { ("MoreFluids.Sweetness", "1") })),
        new ReflectedThrows()
      });
      FluidRegistryException? report = null;
      try { host.Freeze(); } catch (FluidRegistryException e) { report = e; }
      check(report != null, "Invalid registrations froze");
      var problems = report!.Problems;
      string[] mentions = { "Fluid MoreFluids.Coffee is registered by both", "reserved owner 'Timberborn'", "Thief.Drinks", "'0.1'", "requires Moddable Fluids 1.0.0", "requires Moddable Fluids 0.2.0",
        "requires Moddable Fluids 0.1.5", "ModdableFluids.Rendering", "Twice.Provider is registered twice", "Bad.Colour", "Bad.Loc", "Bad.Metadata", "ExampleCreator.Throws (mod ExampleCreator) failed during Register: FormatException: orchard data unreadable" };
      foreach (string mention in mentions) check(problems.Any(p => p.Contains(mention, StringComparison.Ordinal)), "Problem report lacks " + mention + ":\n" + report.Message);
      check(problems.Count == 13, "Expected 13 problems, got " + problems.Count + ":\n" + report.Message);
      check(problems.Count(p => p.Contains("registered by both")) == 1, "The duplicate fluid was reported more than once");
      Rejects<FluidRegistryException>(() => host.Freeze(), "Faulted host froze on retry");
      Rejects<FluidRegistryException>(() => _ = host.Registry, "Faulted registry readable");
      Rejects<InvalidOperationException>(() => host.RegisterProvider(new PlainProvider("Late.Provider", "Late", log)), "Registration after a fault");
      check(host.DescribeRuntime().Contains("FAULT:", StringComparison.Ordinal), "Diagnostic report hides the fault");
      observations["registryRejectedProblems"] = problems.Count;
    });

    scenario("registration closes at freeze and contexts expire after their stage", () => {
      var log = new List<string>();
      var keeper = new PlainProvider("Keep.Provider", "Keep", log, new Fluid("Kept", "Keep.Kept"));
      var host = new ModdableFluidsHost();
      host.RegisterProvider(keeper);
      Rejects<InvalidOperationException>(() => _ = host.Registry, "Registry readable before freeze");
      var registry = host.Freeze();
      check(ReferenceEquals(registry, host.Freeze()) && host.IsFrozen, "Freeze is not idempotent");
      Rejects<InvalidOperationException>(() => keeper.Kept!.AddFluid("Later", "Keep.Later", 0, 0, 0, 0), "Registration context used after Register returned");
      Rejects<InvalidOperationException>(() => host.RegisterProvider(new PlainProvider("Late.Provider", "Late", log)), "Registration after freeze", "IModStarter.StartMod");
      Rejects<ArgumentException>(() => host.RegisterReflectedProvider(keeper), "Compiled provider on the reflected route");
      check(registry.Count == 3 && registry.TryGet("Keep.Kept", out _), "Frozen registry contents");
    });

    scenario("reflected providers bind documented members with exact signatures", () => {
      var host = new ModdableFluidsHost();
      var plain = new PlainReflected();
      host.RegisterReflectedProvider(plain);
      foreach (var (bad, name) in new (object, string)[] { (new ReflectedActivateOnly(), "Activate without Unload"), (new ReflectedPartialState(), "partial state group"),
          (new ReflectedOverloaded(), "overloaded Register"), (new ReflectedWrongCapabilities(), "List<string> capabilities"), (new ReflectedWrongReturn(), "Register returning int"),
          (new ReflectedMissingOwner(), "missing OwnerModId") })
        Rejects<ArgumentException>(() => host.RegisterReflectedProvider(bad), "Reflected " + name);
      var registry = host.Freeze();
      var scene = host.ActivateScene();
      host.LoadProviderStates(scene, new[] { new FluidProviderState("ExampleCreator.Juices", "ExampleCreator", 2, "grove") });
      var saved = host.SaveProviderStates(scene);
      host.UnloadScene(scene);
      check(plain.Log.SequenceEqual(new[] { "activate", "load True 2 grove", "unload" }), "Reflected lifecycle: " + string.Join(", ", plain.Log));
      check(saved.Single() is { ProviderId: "ExampleCreator.Juices", SchemaVersion: 3, Data: "orchard" }, "Reflected state save");
      check(registry.TryGet("ExampleCreator.Juice", out var juice) && juice.Color.Equals(new FluidColor(.9f, .5f, .1f, .8f)), "Reflected definition");
    });

    scenario("scene lifecycle activates in order, rolls back failures and always unloads", () => {
      var log = new List<string>();
      var host = Host(log, new object[] {
        new SceneProvider("Order.C", "Order", log), new SceneProvider("Order.A", "Order", log), new PlainProvider("Order.B", "Order", log),
        new SceneProvider("Order.D", "Order", log) { FailUnload = true }
      });
      host.Freeze(); log.Clear();
      var first = host.ActivateScene();
      Rejects<InvalidOperationException>(() => host.ActivateScene(), "Second active scene");
      Rejects<InvalidOperationException>(() => host.UnloadScene(first), "Unload with a failing provider", "Order.D");
      check(log.SequenceEqual(new[] { "activate Order.A 1", "activate Order.C 1", "activate Order.D 1", "unload Order.D 1", "unload Order.C 1", "unload Order.A 1" }),
        "Scene order: " + string.Join(", ", log));
      Rejects<InvalidOperationException>(() => _ = first.Registry, "Registry through an unloaded scene");
      check(host.ActiveScene == null && !first.IsActive, "Failed unload left the scene active");

      var failLog = new List<string>();
      var failing = Host(failLog, new object[] { new SceneProvider("Fail.A", "Fail", failLog), new SceneProvider("Fail.B", "Fail", failLog) { FailActivate = true }, new SceneProvider("Fail.C", "Fail", failLog) });
      failing.Freeze(); failLog.Clear();
      Rejects<InvalidOperationException>(() => failing.ActivateScene(), "Failing activation", "Fail.B");
      check(failLog.SequenceEqual(new[] { "activate Fail.A 1", "activate Fail.B 1", "unload Fail.A 1" }), "Rollback order: " + string.Join(", ", failLog));
      check(failing.ActiveScene == null, "Failed activation left an active scene");
    });

    scenario("provider state round trips and missing or newer providers stop loading", () => {
      var log = new List<string>();
      StateProvider Stateful(string state) => new("State.Keeper", "State", log, new Fluid("Kept", "State.Kept")) { StateSchemaVersion = 2, State = state };
      var saving = new ModdableFluidsHost(); var keeper = Stateful("alpha|7"); saving.RegisterProvider(keeper); saving.RegisterProvider(new StateProvider("State.Empty", "State", log));
      saving.Freeze();
      var scene = saving.ActivateScene(); saving.LoadProviderStates(scene, null);
      check(keeper.Loaded is { HasState: false, Schema: 0, State: null }, "New game state delivery");
      Rejects<InvalidOperationException>(() => saving.LoadProviderStates(scene, null), "Provider state loaded twice");
      var saved = saving.SaveProviderStates(scene);
      saving.UnloadScene(scene);
      check(saved.Select(s => s.ProviderId).SequenceEqual(new[] { "State.Empty", "State.Keeper" }) && saved[1].Data == "alpha|7" && saved[0].Data == "", "Saved provider states");

      var loading = new ModdableFluidsHost(); var reloaded = Stateful(""); loading.RegisterProvider(new StateProvider("State.Empty", "State", log)); loading.RegisterProvider(reloaded);
      loading.Freeze(); var next = loading.ActivateScene(); loading.LoadProviderStates(next, saved);
      check(reloaded.Loaded is { HasState: true, Schema: 2, State: "alpha|7" }, "Provider state round trip");
      loading.UnloadScene(next);

      void Fails(ModdableFluidsHost host, IReadOnlyList<FluidProviderState> states, string mention) {
        host.Freeze(); var s = host.ActivateScene();
        Rejects<FluidSaveException>(() => host.LoadProviderStates(s, states), "State load " + mention, mention);
        host.UnloadScene(s);
      }
      Fails(new ModdableFluidsHost(), saved, "needs provider State.Empty from mod State");
      var newer = new ModdableFluidsHost(); newer.RegisterProvider(new StateProvider("State.Keeper", "State", log) { StateSchemaVersion = 1 }); newer.RegisterProvider(new StateProvider("State.Empty", "State", log));
      Fails(newer, saved, "schema 2 is newer than the installed 1");
      var stateless = new ModdableFluidsHost(); stateless.RegisterProvider(new SceneProvider("State.Keeper", "State", log)); stateless.RegisterProvider(new StateProvider("State.Empty", "State", log));
      Fails(stateless, saved, "no longer stores state");
      Rejects<ArgumentOutOfRangeException>(() => new FluidProviderState("State.Keeper", "State", 0, ""), "Schema zero");
      Rejects<ArgumentException>(() => new FluidProviderState("Other.Keeper", "State", 1, ""), "State outside the owner namespace");
    });

    scenario("optional consumers load with the API present and fail only where documented when it is absent", () => {
      string compiledPath = Path.Combine(AppContext.BaseDirectory, "ModdableFluidsSyntheticCompiled.dll");
      Assembly? Game(AssemblyLoadContext context, AssemblyName name) {
        string path = Path.Combine(managed, name.Name + ".dll");
        return File.Exists(path) ? context.LoadFromAssemblyPath(path) : null;
      }
      AssemblyLoadContext.Default.Resolving += Game;
      try {
      // Present: the reflection consumer finds the API, checks capabilities and registers through the entry point.
      var reflection = Assembly.LoadFrom(reflectionConsumerPath);
      check(!reflection.GetReferencedAssemblies().Any(a => a.Name == "ModdableFluids"), "Reflection consumer has a compiled API reference");
      check(reflection.GetTypes().Length >= 3, "Reflection consumer type enumeration");
      var compiled = Assembly.LoadFrom(compiledPath);
      check(compiled.GetTypes().Any(t => typeof(IFluidProvider).IsAssignableFrom(t)), "Compiled consumer type enumeration with the API present");
      var discovery = reflection.GetType("ModdableFluidsSyntheticReflection.SyntheticReflectionDiscovery", true)!;
      var provider = Activator.CreateInstance(reflection.GetType("ModdableFluidsSyntheticReflection.JuiceProvider", true)!)!;
      var register = discovery.GetMethod("Register")!;
      string result = (string)register.Invoke(null, new[] { AppDomain.CurrentDomain.GetAssemblies(), provider })!;
      check(result.StartsWith("registered ModdableFluidsSyntheticReflection.Juice with Moddable Fluids 0.1.4", StringComparison.Ordinal), "Reflection discovery: " + result);
      ModdableFluidsEntry.RegisterProvider((IFluidProvider)Activator.CreateInstance(compiled.GetType("ModdableFluidsSyntheticCompiled.TracerProvider", true)!)!);
      var registry = ModdableFluidsEntry.Host.Freeze();
      check(registry.Definitions.Select(d => d.Id).SequenceEqual(new[] { FluidIds.Water, FluidIds.Badwater, "ModdableFluidsSyntheticCompiled.Tracer", "ModdableFluidsSyntheticReflection.Juice" }),
        "Process-wide registry through both consumer routes");
      check(registry.Get(registry.GetHandle("ModdableFluidsSyntheticReflection.Juice")).Metadata["ModdableFluidsSyntheticReflection.Sweetness"] == "7", "Reflected metadata");
      var scene = ModdableFluidsEntry.Host.ActivateScene();
      ModdableFluidsEntry.Host.LoadProviderStates(scene, null);
      ModdableFluidsEntry.Host.UnloadScene(scene);
      check((int)provider.GetType().GetProperty("Activations")!.GetValue(provider)! == 1 && (int)provider.GetType().GetProperty("Unloads")!.GetValue(provider)! == 1, "Reflection consumer lifecycle");
      observations["processRegistry"] = ModdableFluidsEntry.DescribeRuntime();

      // Absent: a context where ModdableFluids cannot load, like a game install without the API.
      var absent = new AbsentApiContext();
      try {
        var lonelyReflection = absent.LoadFromStream(new MemoryStream(File.ReadAllBytes(reflectionConsumerPath)));
        check(lonelyReflection.GetTypes().Length >= 3, "Reflection consumer enumeration without the API");
        var lonelyDiscovery = lonelyReflection.GetType("ModdableFluidsSyntheticReflection.SyntheticReflectionDiscovery", true)!;
        var lonelyProvider = Activator.CreateInstance(lonelyReflection.GetType("ModdableFluidsSyntheticReflection.JuiceProvider", true)!)!;
        string absentResult = (string)lonelyDiscovery.GetMethod("Register")!.Invoke(null, new[] { new[] { lonelyReflection }, lonelyProvider })!;
        check(absentResult == (string)lonelyDiscovery.GetField("Absent")!.GetValue(null)!, "Absent API outcome: " + absentResult);
        var lonelyCompiled = absent.LoadFromStream(new MemoryStream(File.ReadAllBytes(compiledPath)));
        ReflectionTypeLoadException? failure = null;
        try { lonelyCompiled.GetTypes(); } catch (ReflectionTypeLoadException e) { failure = e; }
        check(failure != null && failure.LoaderExceptions.Any(e => e?.Message.Contains("ModdableFluids", StringComparison.Ordinal) == true),
          "Compiled consumer enumerated without the API; its package must require Moddable Fluids");
        observations["absentApiCompiledConsumer"] = failure?.LoaderExceptions.FirstOrDefault()?.Message ?? "";
      } finally { absent.Unload(); }
      } finally { AssemblyLoadContext.Default.Resolving -= Game; }
    });

    scenario("discovery entry reports version and capabilities and refuses duplicate copies", () => {
      check(ModdableFluidsEntry.ApiVersion == "0.1.4" && ModdableFluidsEntry.ContractMajor == 0, "API version");
      check(typeof(ModdableFluidsEntry).Assembly.GetName().Version == new Version(0, 1, 4, 0), "Assembly version matches the contract version");
      // Core capabilities here; each feature area (tides) checks its own in its scenario file.
      var core = new[] { "ModdableFluids.Discovery.Reflection", "ModdableFluids.Persistence.ComponentIdentity", "ModdableFluids.Persistence.ProviderState",
        "ModdableFluids.Policies.Irrigation", "ModdableFluids.Policies.WaterIntakes",
        "ModdableFluids.Registry.Definitions", "ModdableFluids.Registry.Providers", "ModdableFluids.Rendering.TerrainOverlays", "ModdableFluids.Scene.Lifecycle", "ModdableFluids.Sources.Types",
        "ModdableFluids.World.Additions", "ModdableFluids.World.Extraction", "ModdableFluids.World.Import", "ModdableFluids.World.Losses", "ModdableFluids.World.Rules",
        "ModdableFluids.World.Sampling", "ModdableFluids.World.SourceComposition" };
      check(ModdableFluidsEntry.Capabilities.SequenceEqual(ModdableFluidsEntry.Capabilities.OrderBy(c => c, StringComparer.Ordinal))
        && ModdableFluidsEntry.Capabilities.Distinct().Count() == ModdableFluidsEntry.Capabilities.Count
        && core.All(ModdableFluidsEntry.Capabilities.Contains) && ModdableFluidsEntry.Capabilities.All(c => c.StartsWith("ModdableFluids.", StringComparison.Ordinal)), "Capability list");
      // Shared water rendering has no capability of its own; the terrain overlay is the one rendering capability.
      check(!ModdableFluidsEntry.Capabilities.Any(c => (c.Contains("Rendering") && c != FluidTerrainOverlays.Capability) || c.Contains("Transport")), "Unimplemented capability advertised");
      ModdableFluidsEntry.RequireSingleLoadedCopy(AppDomain.CurrentDomain.GetAssemblies());
      check(typeof(ModdableFluidsEntry).FullName == ModdableFluidsEntry.EntryTypeName && typeof(ModdableFluidsEntry).Assembly.GetName().Name == ModdableFluidsEntry.AssemblyName, "Documented entry names");
      var second = new AssemblyLoadContext("second Moddable Fluids copy", isCollectible: true);
      try {
        var copy = second.LoadFromStream(new MemoryStream(File.ReadAllBytes(typeof(ModdableFluidsEntry).Assembly.Location)));
        check(copy != typeof(ModdableFluidsEntry).Assembly, "Second copy was not separate");
        Rejects<InvalidOperationException>(() => ModdableFluidsEntry.RequireSingleLoadedCopy(AppDomain.CurrentDomain.GetAssemblies()), "Duplicate API copies", "loaded 2 times");
        observations["duplicateCopiesReport"] = string.Join(", ", ModdableFluidsEntry.DescribeLoadedCopies(AppDomain.CurrentDomain.GetAssemblies()));
      } finally { second.Unload(); }
      foreach (var type in typeof(ModdableFluidsEntry).Assembly.GetTypes().Where(t => !t.Name.StartsWith("<", StringComparison.Ordinal))) check(type.Namespace == "ModdableFluids", "Unexpected namespace in the public assembly: " + type.FullName);
      check(typeof(ModdableFluidsEntry).Assembly.GetReferencedAssemblies().All(a => a.Name == "netstandard"), "The public assembly references more than netstandard");
    });
  }

  /// <summary>Resolves game assemblies but never Moddable Fluids, so the API is genuinely missing.</summary>
  private sealed class AbsentApiContext : AssemblyLoadContext {
    internal AbsentApiContext() : base("API absent", isCollectible: true) { }
    protected override Assembly? Load(AssemblyName name) {
      if (name.Name == "ModdableFluids") throw new FileNotFoundException("ModdableFluids is not installed", "ModdableFluids.dll");
      return null;
    }
  }
}
