using System;
using ModdableFluids;
using ModdableWeathers.Historical;
using ModdableWeathers.Weathers;

namespace ModdableFluids.Tides.ModdableWeathersAdapter {
  /// <summary>
  /// One registered tide as a Moddable Weathers hazardous weather (Moddable Weathers 11.0.0). Its <see cref="Id"/> is the
  /// tide's native weather ID, so Moddable Weathers' history, its panels and sound (the ModdableWeatherSpec blueprint the
  /// content mod ships under that ID), a save played without Moddable Weathers (whose native history Moddable Weathers
  /// converts) and the Weather Station all name it the same way.
  /// <list type="bullet">
  /// <item><b>Binding.</b> Moddable Weathers binds weathers by type (ModdableWeatherBindingExtensions.BindWeather&lt;T&gt;),
  /// and the tides are known only at run time, so this is a fixed set of <see cref="Classes"/> sealed classes,
  /// FluidTideWeather0 … FluidTideWeather7; the first N are bound for N registered tides, class i taking the i-th tide in
  /// ordinal ID order. More tides than classes are refused when the scene is configured.</item>
  /// <item><b>Weight.</b> GetChance returns the tide's integer weight for the stage from the C′ rule
  /// (FluidTideSelection.StageWeights), computed once per stage for all tides by the adapter service.</item>
  /// <item><b>Duration.</b> Whole days, uniform over the save's shortest to longest tide, as the native binding draws them;
  /// Moddable Weathers then applies its stage length multiplier.</item>
  /// <item><b>Settings.</b> On/off and every value come from <c>ModdableFluids.TideSettings</c> (the new-game screen's tide
  /// rows), not from Moddable Weathers' Weather Settings dialog, which lists this weather without settings.</item>
  /// </list>
  /// </summary>
  public abstract class FluidTideModdableWeather : ModdableWeatherBase, IModdableHazardousWeather {
    /// <summary>How many tides the adapter can bind (FluidTideWeather0 … FluidTideWeather7).</summary>
    public const int Classes = 8;

    private readonly ModdableWeatherSpecService _specs;
    private readonly FluidTideModdableWeathersService _service;

    /// <summary>The tide's position in ordinal ID order (FluidTideRegistry.Tides), and the class number.</summary>
    public int Index { get; }
    public FluidTideDefinition Tide { get; }

    protected FluidTideModdableWeather(int index, ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(specs) {
      _specs = specs ?? throw new ArgumentNullException(nameof(specs));
      _service = service ?? throw new ArgumentNullException(nameof(service));
      Index = index;
      Tide = service.Attach(this);
    }

    public override string Id => Tide.NativeWeatherId;
    /// <summary>The save's on/off for this tide; Moddable Weathers neither weighs nor lists a disabled weather as possible.</summary>
    public override bool Enabled => _service.Settings.Get(Tide.Id).Enabled;

    /// <summary>Reads the tide's ModdableWeatherSpec (Moddable Weathers' base Load); a missing spec is named, not a KeyNotFoundException.</summary>
    public override void Load() {
      if (!_specs.SpecsById.ContainsKey(Id))
        throw new InvalidOperationException("Moddable Fluids tides: Moddable Weathers has no ModdableWeatherSpec '" + Id + "' for tide " + Tide.Id
          + ". The mod that registers it (provider " + Tide.ProviderId + ") ships ModdableWeatherSpecs/" + Id + ".blueprint.json for Moddable Weathers.");
      base.Load();
      if (Spec.DisplayLoc != Tide.DisplayNameLocKey)
        throw new InvalidOperationException("Moddable Fluids tides: the ModdableWeatherSpec '" + Id + "' names its weather " + Spec.DisplayLoc + ", but tide " + Tide.Id
          + " is registered as " + Tide.DisplayNameLocKey + "; its mod must give both the same name key");
    }

    public override int GetChance(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) =>
      _service.WeightOf(this, stageDecision, cycleDecision);

    public override int GetDuration(WeatherCycleStageDecision stageDecision, WeatherCycleDecision cycleDecision, WeatherHistoryService history) =>
      _service.DrawDuration(Tide);

    public override string ToString() => Id + " (Moddable Fluids tide " + Tide.Id + ")";
  }

  public sealed class FluidTideWeather0 : FluidTideModdableWeather { public FluidTideWeather0(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(0, specs, service) { } }
  public sealed class FluidTideWeather1 : FluidTideModdableWeather { public FluidTideWeather1(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(1, specs, service) { } }
  public sealed class FluidTideWeather2 : FluidTideModdableWeather { public FluidTideWeather2(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(2, specs, service) { } }
  public sealed class FluidTideWeather3 : FluidTideModdableWeather { public FluidTideWeather3(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(3, specs, service) { } }
  public sealed class FluidTideWeather4 : FluidTideModdableWeather { public FluidTideWeather4(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(4, specs, service) { } }
  public sealed class FluidTideWeather5 : FluidTideModdableWeather { public FluidTideWeather5(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(5, specs, service) { } }
  public sealed class FluidTideWeather6 : FluidTideModdableWeather { public FluidTideWeather6(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(6, specs, service) { } }
  public sealed class FluidTideWeather7 : FluidTideModdableWeather { public FluidTideWeather7(ModdableWeatherSpecService specs, FluidTideModdableWeathersService service) : base(7, specs, service) { } }
}
