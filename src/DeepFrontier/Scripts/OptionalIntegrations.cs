using System;
using System.Linq;
using System.Runtime.CompilerServices;
using Bindito.Core;

// The Power Lines acceptance harnesses moved with their Power Lines references into the optional
// assembly and still use this assembly's internal fixture types.
[assembly: InternalsVisibleTo("DeepFrontier.PowerLines")]

namespace DeepFrontier.Scripts {
  // Mods Deep Frontier integrates with but does not require (manifest OptionalMods).
  //
  // Code that uses an optional mod's types lives in its own assembly, DeepFrontier.<ModId>
  // (Scripts/<folder>/DeepFrontier.<ModId>.asmdef), packaged as
  // Scripts/DeepFrontier.<ModId>.dll.<ModId>.optional (tools/unity/DeepFrontierBatchBuild.cs).
  // Moddable Timberborn's OptionalModsLoader loads it only while that mod is enabled. This
  // assembly may not use those types: Timberborn calls Assembly.GetTypes() unguarded on every mod
  // assembly, and Bindito resolves constructor parameter types, so a type here that names an absent
  // assembly breaks mod start or the context that binds it. tools/validate_mod_dependencies.mjs
  // enforces the split from the manifest and the asmdefs.
  //
  // Blueprint content for an optional mod is conditional too: a partial blueprint of another mod's
  // template is a native *.optional.blueprint.json (merged only when the base exists), and a spec
  // of an optional mod on a Deep Frontier template is added by that mod's optional assembly
  // (Scripts/PowerLines/PowerLineConnectionPoints.cs).
  internal static class OptionalIntegrations {
    // Power Lines 11.1.1 (Workshop 3766893705): its assembly, and Deep Frontier's bridge for it.
    internal const string PowerLinesAssembly = "PowerLines";
    internal const string PowerLinesBridgeAssembly = "DeepFrontier.PowerLines";
    // Acceptance harnesses in the bridge (FactoryTransportAcceptance, LategameAcceptance).
    internal static readonly string[] PowerLinesAcceptanceFlags = {
      "-deepFrontierFactoryTransport", "-deepFrontierFactoryTransportReload",
      "-deepFrontierFactoryPowerLines", "-deepFrontierFactoryPowerLinesReload",
      "-deepFrontierLategame", "-deepFrontierLategameReload",
    };

    internal static bool AssemblyLoaded(string name) =>
      AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == name);
  }

  // Fails a broken package or an impossible test launch before anything else runs.
  [Context("MainMenu")]
  [Context("Game")]
  [Context("MapEditor")]
  public sealed class OptionalIntegrationsConfigurator : Configurator {
    protected override void Configure() {
#if !UNITY_EDITOR
      bool powerLines = OptionalIntegrations.AssemblyLoaded(OptionalIntegrations.PowerLinesAssembly);
      if (powerLines && !OptionalIntegrations.AssemblyLoaded(OptionalIntegrations.PowerLinesBridgeAssembly))
        throw new InvalidOperationException($"Power Lines is loaded but {OptionalIntegrations.PowerLinesBridgeAssembly} is not: the Deep Frontier package is missing its optional Scripts DLL");
      var flag = Environment.GetCommandLineArgs().FirstOrDefault(arg => OptionalIntegrations.PowerLinesAcceptanceFlags.Contains(arg));
      if (!powerLines && flag != null)
        throw new InvalidOperationException($"{flag} runs a Power Lines acceptance harness, which loads only with the Power Lines mod enabled");
#endif
    }
  }
}
