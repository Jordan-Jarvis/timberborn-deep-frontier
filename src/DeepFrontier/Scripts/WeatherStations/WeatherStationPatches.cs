#if !UNITY_EDITOR
using System;
using System.Linq;
using System.Reflection;
using System.Runtime.CompilerServices;
using DeepFrontier.Scripts.RadioactiveTide;
using HarmonyLib;
using Timberborn.Automation;
using Timberborn.AutomationBuildings;
using Timberborn.AutomationBuildingsUI;
using Timberborn.CoreUI;
using Timberborn.HazardousWeatherSystem;
using Timberborn.ModManagerScene;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.WeatherStations {
  // Why patches (Timberborn 1.1.2.8, decompiled Timberborn.AutomationBuildings
  // and Timberborn.AutomationBuildingsUI):
  // - WeatherStation.Sample() samples the cycle day, the hazardous start day
  //   and `_hazardousWeatherService.CurrentCycleHazardousWeather is
  //   DroughtWeather / BadtideWeather`, then calls the private
  //   UpdateOutputState(), which is
  //   _automator.SetState(Mode switch { Temperate => ..., Drought =>
  //     _sampledIsDrought && WithinActivationTimeHazardous, Badtide => ...,
  //     _ => throw });
  //   The mode is a closed enum with no spec, provider or binding.
  //   WeatherStationSamplePatch (prefix, never skips) samples the tide from the
  //   same service just before the native sample; WeatherStationOutputPatch
  //   (prefix) sets the tide output with the native
  //   WithinActivationTimeHazardous and skips the native switch only while the
  //   station's Radioactive Tide mode is on. One SetState per update, as
  //   native, so linked buildings never see an intermediate state.
  // - WeatherStationFragment builds its mode buttons with
  //   RadioToggleFactory.CreateLocalizable<WeatherStationMode>("Weather.",
  //   ModeRadioToggleContainer) and selects (int)Mode each UpdateFragment. The
  //   postfixes add a fourth native radio button ("Radioactive tide", the
  //   public RadioToggleFactory.CreateLocalizable) to the same container and
  //   keep exactly one button selected; clicking a native mode button turns
  //   the tide mode off (a ClickEvent callback on the native buttons, after
  //   the native one).
  //
  // Every IModStarter in the mod assembly runs at mod start. Verify() resolves
  // every native member the patches rely on and throws if a game update
  // changed one.
  internal sealed class WeatherStationModStarter : IModStarter {
    internal const string HarmonyId = "DeepFrontier.WeatherStation";

    public void StartMod(IModEnvironment modEnvironment) {
      WeatherStationNative.Verify();
      var harmony = new Harmony(HarmonyId);
      harmony.CreateClassProcessor(typeof(WeatherStationSamplePatch)).Patch();
      harmony.CreateClassProcessor(typeof(WeatherStationOutputPatch)).Patch();
      harmony.CreateClassProcessor(typeof(WeatherStationFragmentInitializePatch)).Patch();
      harmony.CreateClassProcessor(typeof(WeatherStationFragmentUpdatePatch)).Patch();
      Debug.Log("[DeepFrontier] Weather Station radioactive tide mode patches applied (sample, output, panel).");
    }
  }

  internal static class WeatherStationNative {
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
    internal const string ModeContainerName = "ModeRadioToggleContainer";
    private static readonly string[] NativeModes = { "Temperate", "Drought", "Badtide" };

    private static Func<WeatherStation, bool> _withinActivationTimeHazardous;
    private static AccessTools.FieldRef<WeatherStationFragment, WeatherStation> _fragmentStation;

    public static MethodInfo Sample() => Method(typeof(WeatherStation), nameof(WeatherStation.Sample), typeof(void));
    public static MethodInfo UpdateOutputState() => Method(typeof(WeatherStation), "UpdateOutputState", typeof(void));
    public static MethodInfo InitializeFragment() => Method(typeof(WeatherStationFragment), nameof(WeatherStationFragment.InitializeFragment), typeof(VisualElement));
    public static MethodInfo UpdateFragment() => Method(typeof(WeatherStationFragment), nameof(WeatherStationFragment.UpdateFragment), typeof(void));

    public static bool WithinActivationTimeHazardous(WeatherStation station) => _withinActivationTimeHazardous(station);
    public static WeatherStation FragmentStation(WeatherStationFragment fragment) => _fragmentStation(fragment);

    public static void Verify() {
      var station = typeof(WeatherStation);
      var names = Enum.GetNames(typeof(WeatherStationMode));
      if (!names.SequenceEqual(NativeModes)) throw Changed($"WeatherStationMode {{ {string.Join(", ", NativeModes)} }}, found {{ {string.Join(", ", names)} }}");

      var sample = Sample();
      var update = UpdateOutputState();
      if (update.IsPublic) throw Changed("WeatherStation.UpdateOutputState() private");
      // A method Mono inlines into its callers would bypass the patch.
      foreach (var target in new[] { sample, update })
        if (NativeIl.Inlinable(target)) throw Changed($"WeatherStation.{target.Name} larger than the Mono inline limit (IL {NativeIl.Size(target)} bytes)");
      var currentWeather = typeof(HazardousWeatherService).GetProperty(nameof(HazardousWeatherService.CurrentCycleHazardousWeather))?.GetGetMethod();
      if (currentWeather?.ReturnType != typeof(IHazardousWeather)) throw Changed("HazardousWeatherService.CurrentCycleHazardousWeather : IHazardousWeather");
      RequireCalls(sample, currentWeather, update);
      RequireCalls(update, typeof(Automator).GetMethod(nameof(Automator.SetState), new[] { typeof(bool) }));
      RequireField(station, "_hazardousWeatherService", typeof(HazardousWeatherService));
      RequireField(station, "_automator", typeof(Automator));
      var within = station.GetProperty("WithinActivationTimeHazardous", Instance);
      if (within?.PropertyType != typeof(bool) || within.GetGetMethod(true) == null) throw Changed("WeatherStation.WithinActivationTimeHazardous : bool");
      RequireCalls(update, within.GetGetMethod(true));
      _withinActivationTimeHazardous = AccessTools.MethodDelegate<Func<WeatherStation, bool>>(within.GetGetMethod(true));
      if (typeof(IHazardousWeather).GetProperty(nameof(IHazardousWeather.Id))?.PropertyType != typeof(string)) throw Changed("IHazardousWeather.Id : string");

      var fragment = typeof(WeatherStationFragment);
      var initialize = InitializeFragment();
      var refresh = UpdateFragment();
      if (!NativeIl.LoadsString(initialize, ModeContainerName)) throw Changed($"WeatherStationFragment.InitializeFragment builds the mode buttons in \"{ModeContainerName}\"");
      var createLocalizable = typeof(RadioToggleFactory).GetMethods(BindingFlags.Instance | BindingFlags.Public)
        .SingleOrDefault(m => m.Name == nameof(RadioToggleFactory.CreateLocalizable) && m.IsGenericMethodDefinition);
      if (createLocalizable == null) throw Changed("RadioToggleFactory.CreateLocalizable<T>(string, VisualElement)");
      RequireCalls(initialize, createLocalizable.MakeGenericMethod(typeof(WeatherStationMode)));
      var plain = typeof(RadioToggleFactory).GetMethod(nameof(RadioToggleFactory.CreateLocalizable), new[] { typeof(System.Collections.Generic.IEnumerable<string>), typeof(VisualElement) });
      if (plain?.ReturnType != typeof(RadioToggle)) throw Changed("RadioToggleFactory.CreateLocalizable(IEnumerable<string>, VisualElement) : RadioToggle");
      var select = typeof(RadioToggle).GetMethod(nameof(RadioToggle.Update), new[] { typeof(int) });
      RequireCalls(refresh, select);
      if (typeof(RadioToggle).GetEvent(nameof(RadioToggle.RadioButtonSelected))?.EventHandlerType != typeof(EventHandler<int>))
        throw Changed("RadioToggle.RadioButtonSelected : EventHandler<int>");
      RequireField(fragment, "_root", typeof(VisualElement));
      RequireField(fragment, "_radioToggleFactory", typeof(RadioToggleFactory));
      RequireField(fragment, "_modeRadioToggle", typeof(RadioToggle));
      RequireField(fragment, "_weatherStation", typeof(WeatherStation));
      _fragmentStation = AccessTools.FieldRefAccess<WeatherStationFragment, WeatherStation>("_weatherStation");
    }

    private static void RequireCalls(MethodBase caller, params MethodBase[] callees) {
      foreach (var callee in callees)
        if (!NativeIl.Calls(caller, callee)) throw Changed($"{caller.DeclaringType?.Name}.{caller.Name} calls {callee?.DeclaringType?.Name}.{callee?.Name}");
    }

    private static MethodInfo Method(Type type, string name, Type returnType) {
      var method = type.GetMethod(name, Instance, null, Type.EmptyTypes, null);
      if (method == null || method.ReturnType != returnType) throw Changed($"{type.Name}.{name}() : {returnType.Name}");
      return method;
    }

    private static void RequireField(Type type, string name, Type fieldType) {
      if (type.GetField(name, Instance)?.FieldType != fieldType) throw Changed($"{type.Name}.{name} : {fieldType.Name}");
    }

    private static InvalidOperationException Changed(string member) =>
      new InvalidOperationException($"Weather Station radioactive tide mode: native API changed; expected {member} (Timberborn 1.1.2.8)");
  }

  internal static class WeatherStationTide {
    public static WeatherStationRadioactiveTide Of(WeatherStation station) {
      var tide = station.GetComponent<WeatherStationRadioactiveTide>();
      if (!tide) throw new InvalidOperationException($"Weather Station {station.Name} has no WeatherStationRadioactiveTide decorator");
      return tide;
    }
  }

  [HarmonyPatch]
  internal static class WeatherStationSamplePatch {
    private static MethodBase TargetMethod() => WeatherStationNative.Sample();

    private static void Prefix(WeatherStation __instance, HazardousWeatherService ____hazardousWeatherService) {
      WeatherStationTide.Of(__instance).Sample(____hazardousWeatherService.CurrentCycleHazardousWeather);
    }
  }

  [HarmonyPatch]
  internal static class WeatherStationOutputPatch {
    private static MethodBase TargetMethod() => WeatherStationNative.UpdateOutputState();

    // false skips the native mode switch: only while the tide mode is on.
    private static bool Prefix(WeatherStation __instance, Automator ____automator) {
      var tide = WeatherStationTide.Of(__instance);
      if (!tide.SignalsRadioactiveTide) return true;
      ____automator.SetState(tide.SampledIsRadioactiveTide && WeatherStationNative.WithinActivationTimeHazardous(__instance));
      return false;
    }
  }

  // The fourth radio button of the (singleton) native fragment.
  internal static class WeatherStationPanel {
    private static readonly ConditionalWeakTable<WeatherStationFragment, RadioToggle> TideButtons = new();

    public static void Add(WeatherStationFragment fragment, RadioToggle tide) => TideButtons.Add(fragment, tide);

    public static RadioToggle TideButton(WeatherStationFragment fragment) =>
      TideButtons.TryGetValue(fragment, out var tide) ? tide : throw new InvalidOperationException("Weather Station panel has no Radioactive tide button");

    // The station the panel shows; a mode button can only be clicked while it shows one.
    public static WeatherStationRadioactiveTide Shown(WeatherStationFragment fragment) {
      var station = WeatherStationNative.FragmentStation(fragment);
      if (!station) throw new InvalidOperationException("Weather Station panel mode clicked without a selected station");
      return WeatherStationTide.Of(station);
    }
  }

  [HarmonyPatch]
  internal static class WeatherStationFragmentInitializePatch {
    private static MethodBase TargetMethod() => WeatherStationNative.InitializeFragment();

    private static void Postfix(WeatherStationFragment __instance, VisualElement ____root, RadioToggleFactory ____radioToggleFactory) {
      var container = ____root.Q<VisualElement>(WeatherStationNative.ModeContainerName)
        ?? throw new InvalidOperationException($"Weather Station panel has no {WeatherStationNative.ModeContainerName}");
      var nativeButtons = container.Children().ToList();
      int modes = Enum.GetValues(typeof(WeatherStationMode)).Length;
      if (nativeButtons.Count != modes) throw new InvalidOperationException($"Weather Station panel has {nativeButtons.Count} mode buttons, expected {modes}");
      var tide = ____radioToggleFactory.CreateLocalizable(new[] { RadioactiveTideLoc.Name }, container);
      tide.RadioButtonSelected += (_, _) => WeatherStationPanel.Shown(__instance).SetSignalsRadioactiveTide(true);
      foreach (var button in nativeButtons)
        button.RegisterCallback<ClickEvent>(_ => WeatherStationPanel.Shown(__instance).SetSignalsRadioactiveTide(false));
      WeatherStationPanel.Add(__instance, tide);
    }
  }

  [HarmonyPatch]
  internal static class WeatherStationFragmentUpdatePatch {
    private static MethodBase TargetMethod() => WeatherStationNative.UpdateFragment();

    // Runs after the native selection of (int)Mode; -1 selects no button.
    private static void Postfix(WeatherStationFragment __instance, WeatherStation ____weatherStation, RadioToggle ____modeRadioToggle) {
      if (!____weatherStation) return;
      var tideButton = WeatherStationPanel.TideButton(__instance);
      if (WeatherStationTide.Of(____weatherStation).SignalsRadioactiveTide) {
        ____modeRadioToggle.Update(-1);
        tideButton.Update(0);
      } else {
        tideButton.Update(-1);
      }
    }
  }
}
#endif
