using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.Automation;
using Timberborn.AutomationBuildings;
using Timberborn.GameSound;
using Timberborn.HazardousWeatherSystem;
using Timberborn.HazardousWeatherSystemUI;
using Timberborn.MainMenuPanels;
using Timberborn.CoreUI;
using Timberborn.GameSceneLoading;
using Timberborn.NewGameConfigurationSystem;
using UnityEngine.UIElements;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// Every native member the tide adapter relies on (Timberborn 1.1.2.8), resolved and checked before any patch is
  /// installed. Hazardous weather is closed in the game: HazardousWeatherRandomizer and HazardousWeatherService know
  /// only drought and badtide, the service saves only IsDrought, HazardousWeatherUIHelper throws "No UI for weather"
  /// and the internal HazardousWeatherSoundPlayer throws for any other weather. A changed member throws here, at the
  /// start of the scene, naming it, instead of failing later or drifting.
  /// </summary>
  internal static class FluidTideNative {
    internal const string GameVersion = "1.1.2.8";
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
    private const string SoundPlayerType = "Timberborn.HazardousWeatherSystemUI.HazardousWeatherSoundPlayer";
    internal const string NewGamePanelView = "MainMenu/NewGameModePanel";
    /// <summary>Mono inlines methods whose IL is at most this long; a patched method must be longer.</summary>
    private const int MonoInlineLimit = 20;

    internal static readonly string[] HelperGetters = {
      "NameLocKey", "ApproachingLocKey", "InProgressLocKey", "StartedNotificationLocKey", "EndedNotificationLocKey",
      "InProgressClass", "IconClass", "NotificationBackgroundClass",
    };

    internal static MethodInfo Randomizer() => Method(typeof(HazardousWeatherRandomizer), nameof(HazardousWeatherRandomizer.GetRandomWeatherForCycle), typeof(IHazardousWeather), typeof(int));
    internal static MethodInfo ServiceLoad() => Method(typeof(HazardousWeatherService), nameof(HazardousWeatherService.Load), typeof(void));
    internal static MethodInfo UiSpecification() => Method(typeof(HazardousWeatherUIHelper), "UpdateCurrentUISpecification", typeof(void));
    internal static MethodInfo[] UiGetters() => HelperGetters.Select(name => {
      var getter = typeof(HazardousWeatherUIHelper).GetProperty(name, Instance)?.GetGetMethod(true);
      if (getter == null || getter.ReturnType != typeof(string)) throw Changed("HazardousWeatherUIHelper." + name + " : string");
      return getter;
    }).ToArray();
    internal static MethodInfo StartSound() {
      var type = AccessTools.TypeByName(SoundPlayerType) ?? throw Changed(SoundPlayerType);
      return Method(type, "OnHazardousWeatherStarted", typeof(void), typeof(HazardousWeatherStartedEvent));
    }
    // Weather Station (Timberborn.AutomationBuildings): the mode is a closed enum, sampled with `is DroughtWeather / BadtideWeather`.
    internal const string StationModeContainer = "ModeRadioToggleContainer";
    private const string FragmentType = "Timberborn.AutomationBuildingsUI.WeatherStationFragment, Timberborn.AutomationBuildingsUI";
    internal static MethodInfo StationSample() => Method(typeof(WeatherStation), nameof(WeatherStation.Sample), typeof(void));
    internal static MethodInfo StationUpdateOutput() => Method(typeof(WeatherStation), "UpdateOutputState", typeof(void));
    internal static Type StationFragment() => Type.GetType(FragmentType) ?? throw Changed(FragmentType);
    internal static MethodInfo FragmentInitialize() => Method(StationFragment(), "InitializeFragment", typeof(VisualElement));
    internal static MethodInfo FragmentUpdate() => Method(StationFragment(), "UpdateFragment", typeof(void));

    // The station's private WithinActivationTimeHazardous (native early activation included) and the fragment's fields.
    private static Func<WeatherStation, bool> _withinHazardous;
    private static FieldInfo _fragmentRoot, _fragmentFactory, _fragmentModes, _fragmentStation;
    internal static bool WithinActivationTimeHazardous(WeatherStation station) => (_withinHazardous ?? throw Changed("a verified WeatherStation contract"))(station);
    internal static VisualElement FragmentRoot(object fragment) => (VisualElement)_fragmentRoot.GetValue(fragment);
    internal static RadioToggleFactory FragmentFactory(object fragment) => (RadioToggleFactory)_fragmentFactory.GetValue(fragment);
    internal static RadioToggle FragmentModes(object fragment) => (RadioToggle)_fragmentModes.GetValue(fragment);
    internal static WeatherStation FragmentStation(object fragment) => (WeatherStation)_fragmentStation.GetValue(fragment);

    private static MethodInfo[] VerifyStation() {
      var names = Enum.GetNames(typeof(WeatherStationMode));
      if (!names.SequenceEqual(new[] { "Temperate", "Drought", "Badtide" })) throw Changed("WeatherStationMode { Temperate, Drought, Badtide }, found { " + string.Join(", ", names) + " }");
      var sample = StationSample();
      var update = StationUpdateOutput();
      if (update.IsPublic) throw Changed("WeatherStation.UpdateOutputState() private");
      var currentWeather = typeof(HazardousWeatherService).GetProperty(nameof(HazardousWeatherService.CurrentCycleHazardousWeather))?.GetGetMethod();
      if (currentWeather == null || !Calls(sample, currentWeather) || !Calls(sample, update)) throw Changed("WeatherStation.Sample reading the cycle's hazardous weather, then calling UpdateOutputState");
      var setState = typeof(Automator).GetMethod(nameof(Automator.SetState), new[] { typeof(bool) });
      var within = typeof(WeatherStation).GetProperty("WithinActivationTimeHazardous", Instance)?.GetGetMethod(true);
      if (setState == null || within == null || within.ReturnType != typeof(bool) || !Calls(update, setState) || !Calls(update, within))
        throw Changed("WeatherStation.UpdateOutputState setting Automator.SetState(bool) from WithinActivationTimeHazardous : bool");
      _withinHazardous = (Func<WeatherStation, bool>)Delegate.CreateDelegate(typeof(Func<WeatherStation, bool>), within);
      var fragment = StationFragment();
      var initialize = FragmentInitialize();
      var refresh = FragmentUpdate();
      if (!LoadsString(initialize, StationModeContainer)) throw Changed("WeatherStationFragment.InitializeFragment building its mode buttons in " + StationModeContainer);
      var generic = typeof(RadioToggleFactory).GetMethods(BindingFlags.Instance | BindingFlags.Public)
        .SingleOrDefault(m => m.Name == nameof(RadioToggleFactory.CreateLocalizable) && m.IsGenericMethodDefinition);
      if (generic == null || !Calls(initialize, generic.MakeGenericMethod(typeof(WeatherStationMode)))) throw Changed("WeatherStationFragment.InitializeFragment calling RadioToggleFactory.CreateLocalizable<WeatherStationMode>");
      var plain = typeof(RadioToggleFactory).GetMethod(nameof(RadioToggleFactory.CreateLocalizable), new[] { typeof(IEnumerable<string>), typeof(VisualElement) });
      if (plain?.ReturnType != typeof(RadioToggle)) throw Changed("RadioToggleFactory.CreateLocalizable(IEnumerable<string>, VisualElement) : RadioToggle");
      if (!Calls(refresh, typeof(RadioToggle).GetMethod(nameof(RadioToggle.Update), new[] { typeof(int) }))) throw Changed("WeatherStationFragment.UpdateFragment selecting with RadioToggle.Update(int)");
      if (typeof(RadioToggle).GetEvent(nameof(RadioToggle.RadioButtonSelected))?.EventHandlerType != typeof(EventHandler<int>)) throw Changed("RadioToggle.RadioButtonSelected : EventHandler<int>");
      _fragmentRoot = Field(fragment, "_root", typeof(VisualElement));
      _fragmentFactory = Field(fragment, "_radioToggleFactory", typeof(RadioToggleFactory));
      _fragmentModes = Field(fragment, "_modeRadioToggle", typeof(RadioToggle));
      _fragmentStation = Field(fragment, "_weatherStation", typeof(WeatherStation));
      return new[] { sample, update, initialize, refresh };
    }

    internal static MethodInfo CustomTryGetValidatedGameMode() {
      var method = Method(typeof(CustomNewGameModeController), nameof(CustomNewGameModeController.TryGetValidatedGameMode), typeof(bool), typeof(GameModeSpec).MakeByRefType());
      var parameter = method.GetParameters()[0];
      if (!method.IsPublic || !parameter.IsOut || parameter.Name != "gameMode") throw Changed("CustomNewGameModeController.TryGetValidatedGameMode(out GameModeSpec gameMode) : bool");
      return method;
    }

    /// <summary>The Game scene's patch targets, after checking the call paths they rely on.</summary>
    internal static MethodInfo[] VerifyGame() {
      var randomizer = Randomizer();
      var load = ServiceLoad();
      var setForCycle = Method(typeof(HazardousWeatherService), nameof(HazardousWeatherService.SetForCycle), typeof(void), typeof(int));
      if (!Calls(setForCycle, randomizer)) throw Changed("HazardousWeatherService.SetForCycle choosing the cycle's weather with HazardousWeatherRandomizer.GetRandomWeatherForCycle");
      if (!Calls(setForCycle, Method(typeof(IHazardousWeather), nameof(IHazardousWeather.GetDurationAtCycle), typeof(int), typeof(int))))
        throw Changed("HazardousWeatherService.SetForCycle drawing the duration with IHazardousWeather.GetDurationAtCycle");
      WeatherSetter();
      var specification = UiSpecification();
      var getters = UiGetters();
      var sound = StartSound();
      if (sound.GetParameters()[0].Name != "hazardousWeatherStartedEvent") throw Changed(SoundPlayerType + ".OnHazardousWeatherStarted(hazardousWeatherStartedEvent)");
      foreach (var name in new[] { nameof(GameUISoundController.PlayBadtideStartedSound), nameof(GameUISoundController.PlayDroughtStartedSound) })
        if (typeof(GameUISoundController).GetMethod(name, Type.EmptyTypes)?.ReturnType != typeof(void)) throw Changed("GameUISoundController." + name + "()");
      PanelRootField();
      var targets = new[] { randomizer, load, specification, sound }.Concat(VerifyStation()).ToArray();
      foreach (var target in targets) RequireNotInlinable(target);
      return targets.Concat(getters).ToArray();
    }

    /// <summary>The Weather Station targets alone (the Moddable Weathers binding), after the same checks as <see cref="VerifyGame"/>.</summary>
    internal static MethodInfo[] VerifyStationGame() {
      var targets = VerifyStation();
      foreach (var target in targets) RequireNotInlinable(target);
      return targets;
    }

    /// <summary>The main menu's patch target, after checking that every custom game starts through it.</summary>
    internal static MethodInfo VerifyNewGame() {
      NewGamePanelRootField();
      var custom = CustomTryGetValidatedGameMode();
      RequireNotInlinable(custom);
      if (!Calls(custom, Method(typeof(CustomNewGameModeController), "GetGameMode", typeof(GameModeSpec))))
        throw Changed("CustomNewGameModeController.TryGetValidatedGameMode building the mode with GetGameMode");
      var panelTry = Method(typeof(NewGameModePanel), "TryGetValidatedGameMode", typeof(bool), typeof(GameModeSpec).MakeByRefType());
      if (!Calls(panelTry, custom)) throw Changed("NewGameModePanel.TryGetValidatedGameMode asking CustomNewGameModeController");
      var start = Method(typeof(NewGameModePanel), "StartNewGame", typeof(void));
      var sceneStart = Method(typeof(GameSceneLoader), nameof(GameSceneLoader.StartNewGame), typeof(void), typeof(NewGameConfiguration));
      if (!Calls(start, panelTry) || !Calls(start, sceneStart)) throw Changed("NewGameModePanel.StartNewGame starting the validated mode through GameSceneLoader.StartNewGame");
      if (!Calls(Method(typeof(NewGameModePanel), "UpdateNextButton", typeof(void)), panelTry)) throw Changed("NewGameModePanel.UpdateNextButton enabling Start from TryGetValidatedGameMode");
      var initialize = Method(typeof(CustomNewGameModeController), nameof(CustomNewGameModeController.Initialize), typeof(void), typeof(VisualElement), typeof(GameModeSpec), typeof(Action));
      if (!Calls(Method(typeof(NewGameModePanel), "OnCustomizeButtonClicked", typeof(void)), initialize)) throw Changed("NewGameModePanel.OnCustomizeButtonClicked filling the custom fields from the preset");
      if (!LoadsString(Method(typeof(NewGameModePanel), nameof(NewGameModePanel.Load), typeof(void)), NewGamePanelView)) throw Changed("NewGameModePanel.Load loading " + NewGamePanelView);
      return custom;
    }

    // HazardousWeatherService.CurrentCycleHazardousWeather has a private setter; native Load restores only drought or badtide.
    private static MethodInfo _weatherSetter;
    internal static void SetCurrentWeather(HazardousWeatherService service, IHazardousWeather weather) {
      WeatherSetter().Invoke(service, new object[] { weather });
      if (service.CurrentCycleHazardousWeather != weather) throw new InvalidOperationException("Moddable Fluids tides: HazardousWeatherService did not accept the restored weather " + weather.Id);
    }
    private static MethodInfo WeatherSetter() {
      if (_weatherSetter != null) return _weatherSetter;
      var property = typeof(HazardousWeatherService).GetProperty(nameof(HazardousWeatherService.CurrentCycleHazardousWeather), Instance);
      var setter = property?.GetSetMethod(true);
      if (property?.PropertyType != typeof(IHazardousWeather) || setter == null || setter.GetParameters().Length != 1)
        throw Changed("HazardousWeatherService.CurrentCycleHazardousWeather { get; private set; } : IHazardousWeather");
      return _weatherSetter = setter;
    }

    // PanelStack._root and NewGameModePanel._root are private: the only routes to the native panels' elements.
    private static FieldInfo _panelRoot, _newGameRoot;
    internal static VisualElement PanelRoot(PanelStack panelStack) => (VisualElement)PanelRootField().GetValue(panelStack ?? throw new ArgumentNullException(nameof(panelStack)));
    internal static VisualElement NewGamePanelRoot(NewGameModePanel panel) => (VisualElement)NewGamePanelRootField().GetValue(panel ?? throw new ArgumentNullException(nameof(panel)));
    private static FieldInfo PanelRootField() => _panelRoot ??= Field(typeof(PanelStack), "_root", typeof(VisualElement));
    private static FieldInfo NewGamePanelRootField() => _newGameRoot ??= Field(typeof(NewGameModePanel), "_root", typeof(VisualElement));

    /// <summary>
    /// Another mod's patch on a method this adapter patches would compete with it, and the last one applied would win
    /// silently (for example Deep Frontier's shipped radioactive tide, or Moddable Weathers' transpilers). Refuse,
    /// naming each owner.
    /// </summary>
    internal static void RequireNoForeignPatches(IEnumerable<MethodBase> targets, string ownerId) {
      var conflicts = new List<string>();
      foreach (var method in targets) {
        var owners = Harmony.GetPatchInfo(method)?.Owners.Where(owner => owner != ownerId).Distinct().ToArray();
        if (owners != null && owners.Length > 0) conflicts.Add(method.DeclaringType.Name + "." + method.Name + " is patched by " + string.Join(", ", owners));
      }
      if (conflicts.Count > 0)
        throw new InvalidOperationException("Moddable Fluids tides own the native hazardous weather selection, restore, UI and new-game mode, and cannot run with these patches, "
          + "which would compete with them:\n- " + string.Join("\n- ", conflicts)
          + "\nDisable the mod that owns them (a tide of its own must register through Moddable Fluids instead).");
    }

    internal static bool OwnsAny(IEnumerable<MethodBase> targets, string ownerId) => targets.Any(m => Harmony.GetPatchInfo(m)?.Owners.Contains(ownerId) == true);

    private static void RequireNotInlinable(MethodBase method) {
      int size = method.GetMethodBody()?.GetILAsByteArray()?.Length ?? 0;
      if (size <= MonoInlineLimit) throw Changed(method.DeclaringType.Name + "." + method.Name + " longer than Mono's inline limit (now " + size + " bytes of IL)");
    }

    private static MethodInfo Method(Type type, string name, Type returnType, params Type[] parameters) {
      var method = type.GetMethod(name, Instance, null, parameters, null);
      if (method == null || method.ReturnType != returnType)
        throw Changed(type.Name + "." + name + "(" + string.Join(", ", parameters.Select(p => p.Name)) + ") : " + returnType.Name);
      return method;
    }

    private static FieldInfo Field(Type type, string name, Type fieldType) {
      var field = type.GetField(name, Instance);
      if (field?.FieldType != fieldType) throw Changed(type.Name + "." + name + " : " + fieldType.Name);
      return field;
    }

    private static bool Calls(MethodBase caller, MethodBase callee) {
      var il = caller.GetMethodBody()?.GetILAsByteArray() ?? throw Changed(caller.DeclaringType.Name + "." + caller.Name + " with an IL body");
      for (int i = 0; i + 4 < il.Length; i++) {
        // call, callvirt, newobj with a MethodDef, MemberRef or MethodSpec token.
        if (il[i] != 0x28 && il[i] != 0x6F && il[i] != 0x73) continue;
        int token = BitConverter.ToInt32(il, i + 1);
        int table = token >> 24;
        if (table != 0x06 && table != 0x0A && table != 0x2B) continue;
        MethodBase method;
        try { method = caller.Module.ResolveMethod(token, caller.DeclaringType?.GetGenericArguments(), caller.IsGenericMethod ? caller.GetGenericArguments() : null); }
        catch (ArgumentException) { continue; }
        if (method.Module == callee.Module && method.MetadataToken == callee.MetadataToken) return true;
      }
      return false;
    }

    private static bool LoadsString(MethodBase caller, string literal) {
      var il = caller.GetMethodBody()?.GetILAsByteArray() ?? throw Changed(caller.DeclaringType.Name + "." + caller.Name + " with an IL body");
      for (int i = 0; i + 4 < il.Length; i++) {
        if (il[i] != 0x72) continue;
        int token = BitConverter.ToInt32(il, i + 1);
        if (token >> 24 != 0x70) continue;
        try { if (caller.Module.ResolveString(token) == literal) return true; } catch (ArgumentException) { }
      }
      return false;
    }

    internal static InvalidOperationException Changed(string member) =>
      new InvalidOperationException("Moddable Fluids tides: the game's native weather API changed; expected " + member + " (Timberborn " + GameVersion + ")");
  }

  /// <summary>
  /// One Harmony owner's patches for one scene: installed after the contract check and the foreign-owner check,
  /// removed on scene unload. A second install while the first is still in place is refused.
  /// </summary>
  internal sealed class FluidTidePatchSet {
    private readonly Harmony _harmony;
    private readonly string _ownerId;
    private readonly List<MethodBase> _targets = new List<MethodBase>();
    private bool _installed;

    internal FluidTidePatchSet(string ownerId) { _ownerId = ownerId; _harmony = new Harmony(ownerId); }

    internal void Install(IReadOnlyList<MethodBase> targets, Action<Harmony> apply) {
      if (_installed || FluidTideNative.OwnsAny(targets, _ownerId))
        throw new InvalidOperationException("Moddable Fluids tides: patches of " + _ownerId + " are still installed from an earlier scene that did not unload");
      FluidTideNative.RequireNoForeignPatches(targets, _ownerId);
      _targets.AddRange(targets);
      _installed = true;
      try { apply(_harmony); }
      catch { Uninstall(); throw; }
    }

    internal void Uninstall() {
      if (!_installed) return;
      foreach (var target in _targets) _harmony.Unpatch(target, HarmonyPatchType.All, _ownerId);
      _installed = false;
      if (FluidTideNative.OwnsAny(_targets, _ownerId)) throw new InvalidOperationException("Moddable Fluids tides: " + _ownerId + " patches remained after unpatching");
      _targets.Clear();
    }

    internal bool Installed => _installed;
  }
}
