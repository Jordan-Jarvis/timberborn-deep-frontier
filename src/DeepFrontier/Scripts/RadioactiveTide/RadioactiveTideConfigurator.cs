using System;
using System.Linq;
using Bindito.Core;
using Timberborn.Debugging;
using UnityEngine;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Discovered like the mod's other per-feature configurators. The options
  // (IRadioactiveTideSettings) are bound by RadioactiveTideSettingsConfigurator
  // in the main menu and the game; the Harmony patches are applied by
  // RadioactiveTideModStarter at mod start.
  //
  // With Moddable Weathers loaded this binds nothing: Moddable Weathers
  // replaces the vanilla hazardous weather system the services below are
  // built on, and the tide is registered as a Moddable Weathers weather by
  // the optional assembly DeepFrontier.ModdableWeathers
  // (Scripts/RadioactiveTide/ModdableWeathers, its own [Context("Game")]
  // configurator). That assembly cannot live in this DLL: Timberborn calls
  // Assembly.GetTypes() unguarded on every mod assembly (ModCodeStarter,
  // Bindito ContainerDefinition.FindConfigurators, BlueprintSystem
  // SpecTypeCache), and Mono's GetTypes throws ReflectionTypeLoadException
  // for any type whose base class or interface lives in an absent assembly.
  // ModdableTimberborn's OptionalModsLoader loads it only when the
  // ModdableWeathers mod is enabled, after ModCodeStarter and before the
  // first context is configured.
  [Context("Game")]
  public sealed class RadioactiveTideConfigurator : Configurator {
    protected override void Configure() {
#if !UNITY_EDITOR
      if (RadioactiveTideModStarter.ModdableWeathersLoaded) {
        // The build packages the bridge as *.dll.ModdableWeathers.optional
        // (tools/unity/DeepFrontierBatchBuild.cs); its absence is a broken package.
        if (!AssemblyLoaded(RadioactiveTideTuning.ModdableWeathersBridgeAssembly))
          throw new InvalidOperationException($"Moddable Weathers is loaded but {RadioactiveTideTuning.ModdableWeathersBridgeAssembly} is not: the Deep Frontier package is missing its optional Scripts DLL");
        Debug.Log("[DeepFrontier] Radioactive tide runs as a Moddable Weathers weather (DeepFrontier.ModdableWeathers).");
        return;
      }
#endif
      Bind<RadioactiveTideWeather>().AsSingleton();
      Bind<RadioactiveTideService>().AsSingleton();
      Bind<RadioactiveTideUi>().AsSingleton();
      MultiBind<IDevModule>().To<RadioactiveTideDevModule>().AsSingleton();
    }

    internal static bool AssemblyLoaded(string name) =>
      AppDomain.CurrentDomain.GetAssemblies().Any(a => a.GetName().Name == name);
  }

  // Dev mode only: makes the next cycle's hazardous weather a radioactive
  // tide (used by in-game acceptance; the native "Jump to next season" then
  // reaches it without waiting for the earliest cycle).
  internal sealed class RadioactiveTideDevModule : IDevModule {
    private readonly RadioactiveTideService _tide;
    public RadioactiveTideDevModule(RadioactiveTideService tide) { _tide = tide; }

    public DevModuleDefinition GetDefinition() => new DevModuleDefinition.Builder()
      .AddMethod(DevMethod.Create("Deep Frontier: radioactive tide next cycle", _tide.ForceTideNextCycle))
      .Build();
  }
}
