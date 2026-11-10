using System;
using System.Linq;
using System.Runtime.CompilerServices;
using Timberborn.Automation;
using Timberborn.AutomationBuildings;
using Timberborn.BaseComponentSystem;
using Timberborn.CoreUI;
using Timberborn.DuplicationSystem;
using Timberborn.Persistence;
using Timberborn.WorldPersistence;
using ModdableFluids;
using UnityEngine.UIElements;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// One Weather Station mode per registered tide, next to the native Temperate, Drought and Badtide (Timberborn 1.1.2.8
  /// Timberborn.AutomationBuildings.WeatherStation); Deep Frontier's radioactive-tide mode made generic.
  /// <para>
  /// The native WeatherStationMode is a closed enum that the station saves and whose UpdateOutputState throws for any other
  /// value, so a tide is not an enum value: this decorator holds the chosen tide and saves it by tide ID under its own key.
  /// While a tide is chosen the native Mode keeps the player's previous native choice (removing the tide system leaves a
  /// working station), and the output is (the cycle's hazardous weather is that tide) and the native
  /// WithinActivationTimeHazardous, exactly as the native Drought and Badtide modes, early activation included. The tide is
  /// sampled from the cycle's weather just before the native Sample (FluidTidePatches, IFluidTideScene.CurrentCycleTide);
  /// under Moddable Weathers the cycle's weather is the adapter weather, recognised by its weather ID.
  /// </para>
  /// A station saved without this component asks the IFluidTideStationImporter providers once (another tide system's mode).
  /// </summary>
  public sealed class FluidTideWeatherStation : BaseComponent, IAwakableComponent, IPersistentEntity, IDuplicable<FluidTideWeatherStation> {
    private static readonly ComponentKey Key = new ComponentKey("ModdableFluids.WeatherStationTide");
    private static readonly PropertyKey<string> TideKey = new PropertyKey<string>("Tide");

    private readonly IFluidTideScene _tides;
    private WeatherStation _station;
    private Automator _automator;

    /// <summary>The tide this station signals instead of its native mode, or null for the native mode.</summary>
    public string SignalledTide { get; private set; }
    /// <summary>The cycle's tide at the station's last native Sample, or null.</summary>
    public string SampledTide { get; private set; }
    /// <summary>The provider whose IFluidTideStationImporter supplied the loaded choice, or null.</summary>
    public string ImportedBy { get; private set; }

    public FluidTideWeatherStation(IFluidTideScene tides) { _tides = tides; }

    public void Awake() {
      _station = GetComponent<WeatherStation>();
      _automator = GetComponent<Automator>() ?? throw new InvalidOperationException("Moddable Fluids tides: a Weather Station has no Automator");
    }

    public static FluidTideWeatherStation Of(WeatherStation station) =>
      station.GetComponent<FluidTideWeatherStation>() ?? throw new InvalidOperationException("Moddable Fluids tides: a Weather Station has no FluidTideWeatherStation decorator");

    public void SetSignalledTide(string tideId) {
      Require(tideId, "chosen");
      if (SignalledTide == tideId) return;
      SignalledTide = tideId;
      // Re-sample at once, as the native SetMode updates the output at once.
      _station.Sample();
    }

    internal void Sample(string cycleTide) => SampledTide = cycleTide;

    /// <summary>The output while a tide is signalled: the cycle's weather is that tide, within the native activation time.</summary>
    internal bool Output(bool withinActivationTimeHazardous) =>
      SignalledTide != null && SampledTide == SignalledTide && withinActivationTimeHazardous;

    internal void SetOutput(bool withinActivationTimeHazardous) => _automator.SetState(Output(withinActivationTimeHazardous));

    public void Save(IEntitySaver entitySaver) => entitySaver.GetComponent(Key).Set(TideKey, SignalledTide ?? "");

    public void Load(IEntityLoader entityLoader) {
      if (entityLoader.TryGetComponent(Key, out var loader)) {
        string tide = loader.Get(TideKey);
        SignalledTide = tide.Length == 0 ? null : tide;
        Require(SignalledTide, "saved");
        return;
      }
      SignalledTide = ModdableFluidsEntry.Host.ImportStationTide(entityLoader, out string importer);
      ImportedBy = importer;
    }

    public void DuplicateFrom(FluidTideWeatherStation source) => SetSignalledTide(source.SignalledTide);

    private void Require(string tideId, string what) {
      if (tideId != null && !_tides.Tides.TryGet(tideId, out _))
        throw new InvalidOperationException("Moddable Fluids tides: a Weather Station's " + what + " tide " + tideId + " is not registered. Enable the mod that adds it.");
    }
  }

  /// <summary>
  /// The tide buttons of the native Weather Station panel (the internal WeatherStationFragment): one native radio toggle with
  /// a button per registered tide, in ordinal order, in the same container as the native mode buttons, made with the public
  /// RadioToggleFactory.CreateLocalizable. Exactly one button is selected: a tide's while the station signals it (the native
  /// toggle selects none), else the native mode's. Clicking a native mode button returns the station to its native mode.
  /// </summary>
  internal static class FluidTideStationPanel {
    private static readonly ConditionalWeakTable<object, RadioToggle> Toggles = new ConditionalWeakTable<object, RadioToggle>();
    private static readonly ConditionalWeakTable<object, FluidTideRegistry> Registries = new ConditionalWeakTable<object, FluidTideRegistry>();

    internal static void Initialize(object fragment, FluidTideRegistry tides) {
      var container = FluidTideNative.FragmentRoot(fragment).Q<VisualElement>(FluidTideNative.StationModeContainer)
        ?? throw new InvalidOperationException("Moddable Fluids tides: the Weather Station panel has no " + FluidTideNative.StationModeContainer);
      var nativeButtons = container.Children().ToList();
      int modes = Enum.GetValues(typeof(WeatherStationMode)).Length;
      if (nativeButtons.Count != modes) throw new InvalidOperationException("Moddable Fluids tides: the Weather Station panel has " + nativeButtons.Count + " mode buttons, expected " + modes);
      var toggle = FluidTideNative.FragmentFactory(fragment).CreateLocalizable(tides.Tides.Select(t => t.DisplayNameLocKey), container);
      toggle.RadioButtonSelected += (_, index) => Shown(fragment).SetSignalledTide(tides.Tides[index].Id);
      foreach (var button in nativeButtons) button.RegisterCallback<ClickEvent>(_ => Shown(fragment).SetSignalledTide(null));
      Toggles.Add(fragment, toggle);
      Registries.Add(fragment, tides);
    }

    // After the native selection of (int)Mode; -1 selects no button.
    internal static void Update(object fragment) {
      var station = FluidTideNative.FragmentStation(fragment);
      if (station == null || !(bool)station) return;
      if (!Toggles.TryGetValue(fragment, out var toggle) || !Registries.TryGetValue(fragment, out var tides))
        throw new InvalidOperationException("Moddable Fluids tides: the Weather Station panel has no tide buttons");
      string signalled = FluidTideWeatherStation.Of(station).SignalledTide;
      if (signalled == null) { toggle.Update(-1); return; }
      FluidTideNative.FragmentModes(fragment).Update(-1);
      toggle.Update(tides.Tides.Select(t => t.Id).ToList().IndexOf(signalled));
    }

    // The station the panel shows; a mode button can only be clicked while it shows one.
    private static FluidTideWeatherStation Shown(object fragment) {
      var station = FluidTideNative.FragmentStation(fragment);
      if (station == null || !(bool)station) throw new InvalidOperationException("Moddable Fluids tides: a Weather Station mode was clicked without a selected station");
      return FluidTideWeatherStation.Of(station);
    }
  }
}
