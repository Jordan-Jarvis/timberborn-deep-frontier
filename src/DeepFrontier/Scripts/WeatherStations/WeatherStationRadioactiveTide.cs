using Bindito.Core;
using DeepFrontier.Scripts.RadioactiveTide;
using Timberborn.AutomationBuildings;
using Timberborn.BaseComponentSystem;
using Timberborn.DuplicationSystem;
using Timberborn.HazardousWeatherSystem;
using Timberborn.Persistence;
using Timberborn.TemplateInstantiation;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts.WeatherStations {
  // The Radioactive Tide as a fourth Weather Station mode, next to the native
  // Temperate, Drought and Badtide (Timberborn 1.1.2.8,
  // Timberborn.AutomationBuildings.WeatherStation).
  //
  // The native WeatherStationMode enum is saved by the native station and its
  // UpdateOutputState throws for any value outside it, so the tide is not an
  // enum value: this decorator holds the choice and saves it under its own
  // key. While it is on, the native Mode keeps the player's previous native
  // choice (so removing the mod leaves a working station) and the output is
  //   (cycle's hazardous weather is the tide) && native WithinActivationTimeHazardous
  // exactly as the native Drought and Badtide modes are
  //   (cycle's hazardous weather is X) && WithinActivationTimeHazardous,
  // with the native early activation (hours before the hazardous stage).
  // WeatherStationPatches.cs samples the tide with the native Sample() and
  // substitutes the output in the native UpdateOutputState.
  //
  // The tide is recognised by its weather id on the native
  // HazardousWeatherService.CurrentCycleHazardousWeather, which the station
  // itself reads. That covers both tide paths:
  // - vanilla: RadioactiveTideService selects RadioactiveTideWeather as the
  //   cycle's hazardous weather at the cycle start;
  // - Moddable Weathers: its replacement HazardousWeatherService returns the
  //   current or next hazardous stage's weather of this cycle, and
  //   RadioactiveTideModdableWeather is an IHazardousWeather with the same id.
  // Neither path makes the native Drought or Badtide modes fire during a tide.
  internal sealed class WeatherStationRadioactiveTide : BaseComponent, IAwakableComponent, IPersistentEntity,
      IDuplicable<WeatherStationRadioactiveTide> {
    private static readonly ComponentKey Key = new("DeepFrontier.WeatherStationRadioactiveTide");
    private static readonly PropertyKey<bool> SignalsKey = new("SignalsRadioactiveTide");

    private WeatherStation _station;

    // True: the station signals for the Radioactive Tide instead of its native mode.
    public bool SignalsRadioactiveTide { get; private set; }
    // The tide test of the station's last native Sample().
    public bool SampledIsRadioactiveTide { get; private set; }
    public WeatherStation Station => _station;

    public void Awake() {
      _station = GetComponent<WeatherStation>();
    }

    public void SetSignalsRadioactiveTide(bool value) {
      if (SignalsRadioactiveTide == value) return;
      SignalsRadioactiveTide = value;
      // Re-sample at once, as native SetMode updates the output at once.
      _station.Sample();
    }

    // Called with the native station's HazardousWeatherService value just
    // before the native Sample() reads it (WeatherStationSamplePatch).
    internal void Sample(IHazardousWeather currentCycleHazardousWeather) {
      SampledIsRadioactiveTide = currentCycleHazardousWeather != null && currentCycleHazardousWeather.Id == RadioactiveTideTuning.WeatherId;
    }

    public void Save(IEntitySaver entitySaver) {
      entitySaver.GetComponent(Key).Set(SignalsKey, SignalsRadioactiveTide);
    }

    public void Load(IEntityLoader entityLoader) {
      // Saved before the option existed: the native station.
      if (!entityLoader.TryGetComponent(Key, out var loader)) return;
      SignalsRadioactiveTide = loader.Get(SignalsKey);
    }

    public void DuplicateFrom(WeatherStationRadioactiveTide source) => SetSignalsRadioactiveTide(source.SignalsRadioactiveTide);
  }

  // Native AutomationBuildingsConfigurator is [Context("Game")] only, as is
  // this. Bound on both tide paths (vanilla and Moddable Weathers): the
  // station reads only the native HazardousWeatherService.
  [Context("Game")]
  public sealed class WeatherStationRadioactiveTideConfigurator : Configurator {
    protected override void Configure() {
      Bind<WeatherStationRadioactiveTide>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<WeatherStation, WeatherStationRadioactiveTide>();
      return builder.Build();
    }
  }
}
