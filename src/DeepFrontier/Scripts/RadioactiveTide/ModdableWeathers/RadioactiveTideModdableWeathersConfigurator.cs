#if !UNITY_EDITOR
using Bindito.Core;
using ModdableWeathers.Helpers;
using Timberborn.Debugging;

namespace DeepFrontier.RadioactiveTideModdableWeathers {
  // The radioactive tide as a Moddable Weathers 11.0.0 hazardous weather.
  //
  // This is the optional assembly DeepFrontier.ModdableWeathers. It must
  // ship as Scripts/DeepFrontier.ModdableWeathers.dll.ModdableWeathers.optional
  // so that only ModdableTimberborn's OptionalModsLoader loads it, and only
  // when the ModdableWeathers mod is enabled (ModdableTimberborn 11.1.3,
  // OptionalMods/OptionalModsLoader.cs: files "*.dll.<ModId>.optional").
  // As a plain .dll, ModCodeStarter would load it without Moddable Weathers
  // and its unguarded Assembly.GetTypes() would throw for the types below,
  // which derive from Moddable Weathers types.
  //
  // Registration uses Moddable Weathers' own binding extension, as its
  // built-in weathers and Skyblight Weather do (ModdableWeathers
  // Helpers/ModdableWeatherBindingExtensions.BindWeather<T, TSettings>):
  // the weather is multi-bound as IModdableWeather and its settings as
  // IModdableWeatherSettings. Moddable Weathers then
  // - lists it in ModdableWeatherRegistry.HazardousWeathers and rolls it in
  //   WeatherGenerator for hazardous cycle stages (GetChance/GetDuration);
  // - saves the chosen stages in WeatherHistoryRegistry and calls Start on
  //   load or day change and End when the stage ends;
  // - saves the settings per save in ModdableWeatherSettingsService and
  //   shows them in its Weather Settings dialog;
  // - draws the name, icon, banner, sky fog and start sound from the
  //   ModdableWeatherSpec blueprint ModdableWeatherSpecs/RadioactiveTideWeather
  //   (written by tools/radioactive_tide_content.mjs).
  // The vanilla path in DeepFrontier.Scripts.RadioactiveTide binds nothing
  // while Moddable Weathers is loaded (RadioactiveTideConfigurator).
  [Context("Game")]
  public sealed class RadioactiveTideModdableWeathersConfigurator : Configurator {
    protected override void Configure() {
      this.BindWeather<RadioactiveTideModdableWeather, RadioactiveTideModdableWeatherSettings>();
      Bind<RadioactiveTideModdableEmitter>().AsSingleton();
      MultiBind<IDevModule>().To<RadioactiveTideModdableDevModule>().AsSingleton();
    }
  }
}
#endif
