#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using HarmonyLib;
using Timberborn.GameSound;
using Timberborn.HazardousWeatherSystem;
using Timberborn.HazardousWeatherSystemUI;
using Timberborn.MapStateSystem;
using Timberborn.ModManagerScene;
using UnityEngine;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Why Harmony (Timberborn 1.1.2.8, decompiled in outputs/weather-api-1.1.2.8):
  // hazardous weather is not a registry. HazardousWeatherRandomizer and
  // HazardousWeatherService take DroughtWeather and BadtideWeather as
  // constructor arguments and choose between exactly those two; the service
  // saves only IsDrought (anything else reloads as badtide);
  // HazardousWeatherUIHelper throws "No UI for weather" for any other type,
  // and HazardousWeatherSoundPlayer throws "No start sound for weather type".
  // There is no multi-bound IHazardousWeather. Five small patches add the
  // tide; everything else (cycle length, approach timer, start/end events,
  // notifications, sky fog via the SunSpec data overlay, water-source
  // modifiers) is native behaviour driven by the tide as an IHazardousWeather.
  //
  // Every IModStarter in the mod assembly runs at mod start (ModCodeStarter).
  // Verify() resolves every native member first and throws if a game update
  // changed one, so the patches never drift silently.
  internal sealed class RadioactiveTideModStarter : IModStarter {
    internal const string HarmonyId = "DeepFrontier.RadioactiveTide";

    // Moddable Weathers replaces the vanilla hazardous weather system and
    // transpiles these vanilla methods into throws; patching them again re-runs
    // its transpiler, which fails and stops mod loading (build 122). With it
    // loaded, the vanilla tide hooks are not applied; the tide is then a
    // Moddable Weathers weather registered by the optional assembly
    // DeepFrontier.ModdableWeathers (see RadioactiveTideConfigurator).
    // ModCodeStarter loads every enabled mod's assemblies before it starts
    // any mod, so this name check is valid whatever the mod order. It only
    // compares names: this assembly never references Moddable Weathers types.
    internal static bool ModdableWeathersLoaded { get; private set; }

    public void StartMod(IModEnvironment modEnvironment) {
      ModdableWeathersLoaded = RadioactiveTideConfigurator.AssemblyLoaded(RadioactiveTideTuning.ModdableWeathersAssembly);
      if (ModdableWeathersLoaded) {
        Debug.Log("[DeepFrontier] Moddable Weathers owns hazardous weather; the vanilla radioactive tide patches are not applied.");
        return;
      }
      RadioactiveTidePatchTargets.Verify();
      RadioactiveTideNative.Verify();
      var harmony = new Harmony(HarmonyId);
      harmony.CreateClassProcessor(typeof(RadioactiveTideSelectionPatch)).Patch();
      harmony.CreateClassProcessor(typeof(RadioactiveTideRestorePatch)).Patch();
      harmony.CreateClassProcessor(typeof(RadioactiveTideUiSpecificationPatch)).Patch();
      harmony.CreateClassProcessor(typeof(RadioactiveTideUiTextPatch)).Patch();
      harmony.CreateClassProcessor(typeof(RadioactiveTideStartSoundPatch)).Patch();
      Debug.Log("[DeepFrontier] Radioactive tide weather patches applied (selection, restore, UI helper, start sound).");
    }
  }

  internal static class RadioactiveTidePatchTargets {
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    private const string SoundPlayerType = "Timberborn.HazardousWeatherSystemUI.HazardousWeatherSoundPlayer";

    public static MethodBase Randomizer() => Method(typeof(HazardousWeatherRandomizer), nameof(HazardousWeatherRandomizer.GetRandomWeatherForCycle),
      typeof(IHazardousWeather), typeof(int));
    public static MethodBase ServiceLoad() => Method(typeof(HazardousWeatherService), nameof(HazardousWeatherService.Load), typeof(void));
    public static MethodBase UiSpecification() => Method(typeof(HazardousWeatherUIHelper), "UpdateCurrentUISpecification", typeof(void));
    public static IEnumerable<MethodBase> UiGetters() => RadioactiveTideUi.HelperGetters.Select(name => {
      var getter = typeof(HazardousWeatherUIHelper).GetProperty(name, Instance)?.GetGetMethod(true);
      if (getter == null || getter.ReturnType != typeof(string)) throw Changed($"HazardousWeatherUIHelper.{name} : string");
      return (MethodBase)getter;
    }).ToList();
    public static MethodBase StartSound() {
      var type = AccessTools.TypeByName(SoundPlayerType) ?? throw Changed(SoundPlayerType);
      return Method(type, "OnHazardousWeatherStarted", typeof(void), typeof(HazardousWeatherStartedEvent));
    }

    public static void Verify() {
      Randomizer();
      ServiceLoad();
      RequireField(typeof(HazardousWeatherService), "_mapEditorMode", typeof(MapEditorMode));
      UiSpecification();
      UiGetters();
      var sound = StartSound();
      RequireField(sound.DeclaringType, "_gameUISoundController", typeof(GameUISoundController));
      if (sound.GetParameters()[0].Name != "hazardousWeatherStartedEvent") throw Changed($"{SoundPlayerType}.OnHazardousWeatherStarted(hazardousWeatherStartedEvent)");
      if (typeof(GameUISoundController).GetMethod(nameof(GameUISoundController.PlayBadtideStartedSound), Type.EmptyTypes) == null)
        throw Changed("GameUISoundController.PlayBadtideStartedSound()");
    }

    private static MethodBase Method(Type type, string name, Type returnType, params Type[] parameters) {
      var method = type.GetMethod(name, Instance, null, parameters, null);
      if (method == null || method.ReturnType != returnType)
        throw Changed($"{type.Name}.{name}({string.Join(", ", parameters.Select(p => p.Name))}) : {returnType.Name}");
      return method;
    }

    private static void RequireField(Type type, string name, Type fieldType) {
      if (type.GetField(name, Instance)?.FieldType != fieldType) throw Changed($"{type.Name}.{name} : {fieldType.Name}");
    }

    private static InvalidOperationException Changed(string member) =>
      new InvalidOperationException($"Radioactive tide: native weather API changed; expected {member} (Timberborn 1.1.2.8)");
  }

  // 1. Selection: from the player's earliest cycle, the cycle's hazardous
  //    weather may become the tide instead of the native drought/badtide.
  [HarmonyPatch]
  internal static class RadioactiveTideSelectionPatch {
    private static MethodBase TargetMethod() => RadioactiveTidePatchTargets.Randomizer();
    private static void Postfix(int cycle, ref IHazardousWeather __result) =>
      __result = RadioactiveTideService.RequireCurrent().SelectForCycle(cycle, __result);
  }

  // 2. Restore: native Load maps IsDrought=false to badtide; put a saved
  //    tide back before anything reads the weather. Native
  //    HazardousWeatherService is also bound in the map editor, where its
  //    Load does nothing and no tide service exists.
  [HarmonyPatch]
  internal static class RadioactiveTideRestorePatch {
    private static MethodBase TargetMethod() => RadioactiveTidePatchTargets.ServiceLoad();
    private static void Postfix(HazardousWeatherService __instance, MapEditorMode ____mapEditorMode) {
      if (____mapEditorMode.IsMapEditor) return;
      RadioactiveTideService.RequireCurrent().RestoreAfterNativeLoad(__instance);
    }
  }

  // 3. The native helper throws for an unknown weather; while the tide is
  //    the cycle's weather the patched getters below answer instead.
  [HarmonyPatch]
  internal static class RadioactiveTideUiSpecificationPatch {
    private static MethodBase TargetMethod() => RadioactiveTidePatchTargets.UiSpecification();
    private static bool Prefix() => !RadioactiveTideService.RequireCurrent().IsCurrentCycleTide;
  }

  // 4. Names and CSS classes for the native date, weather and notification panels.
  [HarmonyPatch]
  internal static class RadioactiveTideUiTextPatch {
    private static IEnumerable<MethodBase> TargetMethods() => RadioactiveTidePatchTargets.UiGetters();
    private static bool Prefix(MethodBase __originalMethod, ref string __result) {
      if (!RadioactiveTideService.RequireCurrent().IsCurrentCycleTide) return true;
      __result = RadioactiveTideUi.Value(__originalMethod.Name);
      return false;
    }
  }

  // 5. The native start sound player throws for an unknown weather; the tide
  //    uses the badtide alarm.
  [HarmonyPatch]
  internal static class RadioactiveTideStartSoundPatch {
    private static MethodBase TargetMethod() => RadioactiveTidePatchTargets.StartSound();
    private static bool Prefix(HazardousWeatherStartedEvent hazardousWeatherStartedEvent, GameUISoundController ____gameUISoundController) {
      if (!RadioactiveTideService.RequireCurrent().IsTide(hazardousWeatherStartedEvent.HazardousWeather)) return true;
      ____gameUISoundController.PlayBadtideStartedSound();
      return false;
    }
  }
}
#endif
