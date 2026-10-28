#if !UNITY_EDITOR
using System;
using System.Linq;
using DeepFrontier.Scripts.Radiation;
using DeepFrontier.Scripts.RadioactiveTide;
using ModdableWeathers.Cycles;
using ModdableWeathers.Historical;
using Timberborn.Debugging;
using Timberborn.GameCycleSystem;
using Timberborn.TickSystem;

namespace DeepFrontier.RadioactiveTideModdableWeathers {
  // Emission under Moddable Weathers, the counterpart of
  // RadioactiveTideService.Tick on the vanilla path: while the tide's stage
  // is active, SourceRadioactiveShare (100%) of the non-bad
  // water every enabled native source adds is radioactive (one-fluid model,
  // IRadiationService.SetSourceRadioactiveShare); otherwise the share is 0.
  // CurrentStrength already includes the native and Moddable Weathers water
  // strength modifiers, so a source that stops flowing releases nothing.
  // No Moddable Weathers modifier lists the tide as a compatible weather, so
  // sources are neither dried nor turned bad during it.
  public sealed class RadioactiveTideModdableEmitter : ITickableSingleton {
    private readonly RadioactiveTideModdableWeather _weather;
    private readonly IRadiationService _radiation;

    public RadioactiveTideModdableEmitter(RadioactiveTideModdableWeather weather, IRadiationService radiation) {
      _weather = weather; _radiation = radiation;
    }

    public void Tick() =>
      _radiation.SetSourceRadioactiveShare(_weather.Active ? RadioactiveTideTuning.SourceRadioactiveShare : 0f);
  }

  // Dev mode only: regenerates the next cycle with a radioactive tide in its
  // first hazardous stage, ignoring the earliest cycle, the chance and the
  // cooldown. It clears and regenerates the future cycle exactly as Moddable
  // Weathers does after its Weather Settings dialog closes
  // (WeatherSettingsDialogShower.ShowDialogAsync), then refreshes the
  // current/next cycle references. Throws if the regenerated cycle has no
  // tide (for example, no hazardous stage in the cycle-stage settings).
  internal sealed class RadioactiveTideModdableDevModule : IDevModule {
    private readonly RadioactiveTideModdableWeather _weather;
    private readonly WeatherHistoryRegistry _historyRegistry;
    private readonly WeatherHistoryService _history;
    private readonly WeatherGenerator _generator;
    private readonly GameCycleService _gameCycleService;

    public RadioactiveTideModdableDevModule(RadioactiveTideModdableWeather weather, WeatherHistoryRegistry historyRegistry,
        WeatherHistoryService history, WeatherGenerator generator, GameCycleService gameCycleService) {
      _weather = weather; _historyRegistry = historyRegistry; _history = history; _generator = generator; _gameCycleService = gameCycleService;
    }

    public DevModuleDefinition GetDefinition() => new DevModuleDefinition.Builder()
      .AddMethod(DevMethod.Create("Deep Frontier: radioactive tide next cycle", ForceTideNextCycle))
      .Build();

    private void ForceTideNextCycle() {
      int cycle = _gameCycleService.Cycle;
      _weather.ForceForCycle(cycle + 1);
      try {
        _historyRegistry.ClearFutureEntries(cycle);
        _generator.EnsureWeatherGenerated(cycle);
      } finally {
        _weather.ForceForCycle(0);
      }
      _history.UpdateReferences(cycle, true);
      if (!_history.GetWeatherCycle(cycle + 1).Stages.Any(s => s.Weather == _weather))
        throw new InvalidOperationException($"Radioactive tide: cycle {cycle + 1} was regenerated without a hazardous stage for the tide");
    }
  }
}
#endif
