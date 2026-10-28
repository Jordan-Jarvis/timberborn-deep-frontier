using System;
using System.Reflection;
using Timberborn.CoreUI;
using Timberborn.HazardousWeatherSystem;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // The two non-public native members the tide needs outside its Harmony
  // patches (Timberborn 1.1.2.8):
  // - HazardousWeatherService.CurrentCycleHazardousWeather has a private
  //   setter. Native Save writes only IsDrought, so a loaded tide must be put
  //   back after native Load (RadioactiveTideService.RestoreAfterNativeLoad).
  // - PanelStack._root is the game UI document root, the only route to the
  //   native date, weather and notification panels (all internal classes).
  // Both are resolved once and checked; a changed game version throws
  // instead of drifting. Verify() runs at mod start (RadioactiveTidePatches).
  internal static class RadioactiveTideNative {
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    private static MethodInfo _weatherSetter;
    private static FieldInfo _panelRoot;

    public static void Verify() {
      WeatherSetter();
      PanelRootField();
    }

    public static void SetCurrentWeather(HazardousWeatherService service, IHazardousWeather weather) {
      if (service == null || weather == null) throw new ArgumentNullException(service == null ? nameof(service) : nameof(weather));
      WeatherSetter().Invoke(service, new object[] { weather });
      if (service.CurrentCycleHazardousWeather != weather)
        throw new InvalidOperationException("Radioactive tide: HazardousWeatherService.CurrentCycleHazardousWeather did not accept the restored weather");
    }

    // Null until UILayout.Load initialises the panel stack.
    public static VisualElement PanelRoot(PanelStack panelStack) {
      if (panelStack == null) throw new ArgumentNullException(nameof(panelStack));
      return (VisualElement)PanelRootField().GetValue(panelStack);
    }

    private static MethodInfo WeatherSetter() {
      if (_weatherSetter != null) return _weatherSetter;
      var property = typeof(HazardousWeatherService).GetProperty(nameof(HazardousWeatherService.CurrentCycleHazardousWeather), Instance);
      var setter = property?.GetSetMethod(true);
      var parameters = setter?.GetParameters();
      if (property?.PropertyType != typeof(IHazardousWeather) || parameters == null || parameters.Length != 1)
        throw new InvalidOperationException("Radioactive tide: native API changed; expected HazardousWeatherService.CurrentCycleHazardousWeather { get; private set; } : IHazardousWeather (Timberborn 1.1.2.8)");
      return _weatherSetter = setter;
    }

    private static FieldInfo PanelRootField() {
      if (_panelRoot != null) return _panelRoot;
      var field = typeof(PanelStack).GetField("_root", Instance);
      if (field?.FieldType != typeof(VisualElement))
        throw new InvalidOperationException("Radioactive tide: native API changed; expected PanelStack._root : VisualElement (Timberborn 1.1.2.8)");
      return _panelRoot = field;
    }
  }
}
