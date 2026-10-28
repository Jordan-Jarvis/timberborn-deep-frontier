using System;
using Bindito.Core;
using DeepFrontier.Scripts.Radiation;
using Timberborn.AutomationBuildings;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.Common;
using Timberborn.DuplicationSystem;
using Timberborn.EntitySystem;
using Timberborn.Persistence;
using Timberborn.TemplateInstantiation;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.Sensors {
  // What the native Contamination Sensor measures. Badwater is the native
  // behaviour and the default, so sensors saved before this option existed
  // read exactly as before.
  public enum SensedSubstance {
    Badwater,
    Radiation,
    Any,
  }

  // Decorated onto every native ContaminationSensor (Timberborn 1.1.2.8,
  // Timberborn.AutomationBuildings). The native sensor keeps its threshold,
  // comparison mode, save keys, panel and automation output; only its measured
  // value is substituted (ContaminationSensorPatches.cs, a postfix on the
  // private ContaminationSensor.GetContamination(floor)):
  //   Badwater  native ColumnContamination, unchanged
  //   Radiation radioactive share r of the measured column (IRadiationService.Sample)
  //   Any       badwater + radioactive share (one fluid: b + r <= 1)
  // each rounded to the native ContaminationSensor.Precision, so the native
  // SampledContamination, panel readout, slider marker and Mode.Evaluate
  // against the native threshold all apply to the selected substance.
  //
  // Saved games apply their radiation on the first frame after every PostLoad
  // (IRadiationService.SavedStatePending), but AutomationRunner.PostLoad
  // samples every sensor before that. The sensor therefore saves the radioactive
  // share of its column, sampled at save time with the radiation it is saved
  // with, and measures with it until the saved radiation is applied, so the
  // reloaded output equals the saved one.
  internal sealed class ContaminationSensorSubstance : BaseComponent, IAwakableComponent, IInitializableEntity, IPersistentEntity,
      IDuplicable<ContaminationSensorSubstance> {
    private static readonly ComponentKey Key = new("DeepFrontier.ContaminationSensorSubstance");
    private static readonly PropertyKey<SensedSubstance> SubstanceKey = new("Substance");
    private static readonly PropertyKey<float> RadioactiveShareKey = new("RadioactiveShare");

    private readonly IRadiationService _radiation;
    private readonly IThreadSafeWaterMap _waterMap;
    private ContaminationSensor _sensor;
    private Vector3Int _coordinates;
    private bool _initialized;
    private float? _savedRadioactiveShare;

    public SensedSubstance Substance { get; private set; }
    public ContaminationSensor Sensor => _sensor;
    // Unrounded shares of the last measurement (Radiation and Any only).
    public float MeasuredBadwaterShare { get; private set; }
    public float MeasuredRadioactiveShare { get; private set; }

    public ContaminationSensorSubstance(IRadiationService radiation, IThreadSafeWaterMap waterMap) {
      _radiation = radiation;
      _waterMap = waterMap;
    }

    public void Awake() {
      _sensor = GetComponent<ContaminationSensor>();
    }

    // Same cell as native ContaminationSensor.InitializeEntity.
    public void InitializeEntity() {
      _coordinates = GetComponent<BlockObject>().TransformCoordinates(GetComponent<ContaminationSensorSpec>().SensorCoordinates);
      _initialized = true;
    }

    public void SetSubstance(SensedSubstance substance) {
      RequireDefined(substance);
      if (Substance == substance) return;
      Substance = substance;
      // Re-sample at once, as native SetThreshold/SetMode update the output at once.
      if (_initialized) _sensor.Sample();
    }

    // The native measurement of the column whose floor contains `cell`, with
    // the native rounded badwater share; returns the value the sensor compares.
    internal float Measure(Vector3Int cell, float nativeBadwater) {
      if (Substance == SensedSubstance.Badwater) return nativeBadwater;
      MeasuredBadwaterShare = _waterMap.ColumnContamination(cell);
      MeasuredRadioactiveShare = RadioactiveShareAt(cell);
      float value = Substance == SensedSubstance.Radiation ? MeasuredRadioactiveShare : MeasuredBadwaterShare + MeasuredRadioactiveShare;
      return Numbers.RoundToPrecision(value, ContaminationSensor.Precision);
    }

    private float RadioactiveShareAt(Vector3Int cell) {
      if (!_radiation.SavedStatePending) {
        _savedRadioactiveShare = null;
        return _radiation.Sample(cell).WaterRadiation;
      }
      return _savedRadioactiveShare ?? throw new InvalidOperationException(
        $"Contamination sensor at {_coordinates} measures {Substance} over water, but was saved without the radioactive share of that water");
    }

    public void Save(IEntitySaver entitySaver) {
      var saver = entitySaver.GetComponent(Key);
      saver.Set(SubstanceKey, Substance);
      if (Substance != SensedSubstance.Badwater && _waterMap.TryGetColumnFloor(_coordinates, out int floor))
        saver.Set(RadioactiveShareKey, RadioactiveShareAt(new Vector3Int(_coordinates.x, _coordinates.y, floor)));
    }

    public void Load(IEntityLoader entityLoader) {
      // Saved before the option existed: the native badwater sensor.
      if (!entityLoader.TryGetComponent(Key, out var loader)) return;
      var substance = loader.Get(SubstanceKey);
      RequireDefined(substance);
      Substance = substance;
      if (loader.Has(RadioactiveShareKey)) _savedRadioactiveShare = loader.Get(RadioactiveShareKey);
    }

    public void DuplicateFrom(ContaminationSensorSubstance source) => SetSubstance(source.Substance);

    private static void RequireDefined(SensedSubstance substance) {
      if (!Enum.IsDefined(typeof(SensedSubstance), substance))
        throw new ArgumentOutOfRangeException(nameof(substance), substance, "Unknown contamination sensor substance");
    }
  }

  // Public: the Stream Gauge readout and the optional Sluice is Back! bridge
  // (DeepFrontier.SluiceIsBack) show the same choice and readouts.
  public static class ContaminationSensorLoc {
    public const string Substance = "DeepFrontier.ContaminationSensor.Substance";
    // + SensedSubstance name (native EnumDropdownProviderFactory.CreateLocalized).
    public const string SubstancePrefix = "DeepFrontier.ContaminationSensor.Substance.";
    public const string RadiationReading = "DeepFrontier.ContaminationSensor.Reading.Radiation";
    public const string AnyReading = "DeepFrontier.ContaminationSensor.Reading.Any";
  }

  // Discovered like the mod's other per-feature configurators. Native
  // AutomationBuildingsConfigurator is [Context("Game")] only, as is this.
  [Context("Game")]
  public sealed class ContaminationSensorConfigurator : Configurator {
    protected override void Configure() {
      Bind<ContaminationSensorSubstance>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<ContaminationSensor, ContaminationSensorSubstance>();
      return builder.Build();
    }
  }
}
