using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Reflection;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace ModdableFluidsSyntheticReflection {
  /// <summary>
  /// Development fixture written like a third-party integration with no compiled reference to
  /// Moddable Fluids. It registers only in a flagged disposable acceptance run.
  /// </summary>
  public sealed class SyntheticReflectionStarter : IModStarter {
    public void StartMod(IModEnvironment modEnvironment) {
      if (!Environment.GetCommandLineArgs().Contains("-moddableFluidsWorkerAcceptance")) return;
      Debug.Log("[ModdableFluidsSyntheticReflection] " + SyntheticReflectionDiscovery.Register(AppDomain.CurrentDomain.GetAssemblies(), new JuiceProvider()));
    }
  }

  /// <summary>The documented reflection route: find one ModdableFluids assembly, check version and capabilities, register.</summary>
  public static class SyntheticReflectionDiscovery {
    public const string Absent = "Moddable Fluids absent; no synthetic reflection fluid registered";

    public static string Register(IEnumerable<Assembly> loaded, object provider) {
      var api = loaded.Where(a => a.GetName().Name == "ModdableFluids").ToArray();
      // This package lists Moddable Fluids as optional, so its absence is a supported outcome.
      if (api.Length == 0) return Absent;
      if (api.Length > 1) throw new InvalidOperationException("Expected one loaded ModdableFluids assembly, found " + api.Length);
      var entry = api[0].GetType("ModdableFluids.ModdableFluidsEntry", true);
      string version = (string)Get(entry, "ApiVersion");
      var parts = version.Split('.');
      if (parts.Length != 3 || parts[0] != "0" || parts[1] != "1")
        throw new InvalidOperationException("Synthetic reflection fixture supports Moddable Fluids 0.1.x, found " + version);
      var capabilities = new HashSet<string>((IEnumerable<string>)Get(entry, "Capabilities"), StringComparer.Ordinal);
      foreach (string required in JuiceProvider.Required)
        if (!capabilities.Contains(required)) throw new InvalidOperationException("Moddable Fluids " + version + " lacks " + required);
      // Optional features are used only when the runtime lists them (0.1.4 policies).
      ((JuiceProvider)provider).DeclarePolicies = capabilities.Contains("ModdableFluids.Policies.WaterIntakes") && capabilities.Contains("ModdableFluids.Policies.Irrigation");
      var register = entry.GetMethod("RegisterReflectedProvider", BindingFlags.Public | BindingFlags.Static, null, new[] { typeof(object) }, null)
        ?? throw new MissingMethodException("ModdableFluids.ModdableFluidsEntry.RegisterReflectedProvider(object)");
      Invoke(register, null, provider);
      return "registered " + ((JuiceProvider)provider).ProviderId + " with Moddable Fluids " + version;
    }

    private static object Get(Type type, string property) =>
      (type.GetProperty(property, BindingFlags.Public | BindingFlags.Static) ?? throw new MissingMemberException(type.FullName, property)).GetValue(null);

    internal static object Invoke(MethodInfo method, object target, params object[] arguments) {
      try { return method.Invoke(target, arguments); }
      catch (TargetInvocationException e) when (e.InnerException != null) {
        System.Runtime.ExceptionServices.ExceptionDispatchInfo.Capture(e.InnerException).Throw();
        throw;
      }
    }
  }

  /// <summary>A plain provider bound by documented member names. Context parameters are typed object.</summary>
  public sealed class JuiceProvider {
    public const string Owner = "ModdableFluidsSyntheticReflection";
    internal static readonly string[] Required = { "ModdableFluids.Discovery.Reflection", "ModdableFluids.Persistence.ProviderState", "ModdableFluids.Scene.Lifecycle" };
    public string ProviderId => Owner + ".Juice";
    public string OwnerModId => Owner;
    public string MinimumApiVersion => "0.1.0";
    public string[] RequiredCapabilities => (string[])Required.Clone();
    public int StateSchemaVersion => 1;
    public int Activations { get; private set; }
    public int Unloads { get; private set; }
    public int LastSceneSerial { get; private set; }
    /// <summary>Provider-owned persistent counter, saved with the world fluid state.</summary>
    public int Pressings { get; set; }
    /// <summary>Set by discovery when the runtime lists the water-intake and irrigation policy capabilities.</summary>
    public bool DeclarePolicies { get; set; }

    public void Register(object registration) {
      var type = registration.GetType();
      SyntheticReflectionDiscovery.Invoke(type.GetMethod("AddFluid"), registration, "Juice", Owner + ".Juice.DisplayName", .95f, .55f, .1f, .85f);
      SyntheticReflectionDiscovery.Invoke(type.GetMethod("AddMetadata"), registration, "Juice", Owner + ".Sweetness", "7");
      if (!DeclarePolicies) return;
      // Juice stops water intakes from half the column and blocks moisture at the same share (exercises the moisture input).
      SyntheticReflectionDiscovery.Invoke(type.GetMethod("SetWaterIntakePolicy"), registration, "Juice", .5, Owner + ".JuiceDrawnAsWater",
        Owner + ".Juice.IntakeRefused", Owner + ".Juice.IntakeRefusedAlert");
      SyntheticReflectionDiscovery.Invoke(type.GetMethod("SetBlocksMoisture"), registration, "Juice", .5);
    }

    public void Activate(object scene) {
      Activations++;
      LastSceneSerial = (int)scene.GetType().GetProperty("Serial").GetValue(scene);
    }

    public void Unload(object scene) => Unloads++;

    public string SaveState(object scene) => "pressings=" + Pressings.ToString(CultureInfo.InvariantCulture);

    public void LoadState(object scene, bool hasState, int schemaVersion, string state) {
      if (!hasState) { Pressings = 0; return; }
      if (schemaVersion != 1 || state == null || !state.StartsWith("pressings=", StringComparison.Ordinal) ||
          !int.TryParse(state.Substring("pressings=".Length), NumberStyles.None, CultureInfo.InvariantCulture, out int pressings))
        throw new FormatException("Unreadable synthetic juice state (schema " + schemaVersion + "): " + state);
      Pressings = pressings;
    }
  }
}
