#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.CoreUI;
using Timberborn.DropdownSystem;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.Sensors {
  // Measured-substance choice for the native Contamination Sensor, a top
  // fragment shown directly after the native sensor fragment (native
  // AutomationBuildingsUI adds ContaminationSensorFragment as a top fragment
  // too). The native fragment's "Measurement" and slider marker already show
  // the selected substance's reading (ContaminationSensor.SampledContamination);
  // this adds the radioactive share for Radiation and Any. The dropdown is the
  // native Dropdown with a native localized EnumDropdownProvider, as the
  // native fragment builds its comparison-mode dropdown.
  internal sealed class ContaminationSensorSubstancePanel : BaseEntityPanelFragment<ContaminationSensorSubstance> {
    private readonly ILoc _loc;
    private readonly VisualElementInitializer _initializer;
    private readonly DropdownItemsSetter _dropdownItemsSetter;
    private readonly EnumDropdownProviderFactory _dropdownProviders;
    private Dropdown _substance;
    private EnumDropdownProvider<SensedSubstance> _substanceProvider;
    private Label _reading;

    public ContaminationSensorSubstancePanel(ILoc loc, VisualElementInitializer initializer, DropdownItemsSetter dropdownItemsSetter,
        EnumDropdownProviderFactory dropdownProviders) {
      _loc = loc;
      _initializer = initializer;
      _dropdownItemsSetter = dropdownItemsSetter;
      _dropdownProviders = dropdownProviders;
    }

    protected override void InitializePanel() {
      _substance = new Dropdown();
      _substance.OverrideLabelLocKey(ContaminationSensorLoc.Substance);
      panel.Add(_substance);
      _initializer.InitializeVisualElement(_substance);
      _substanceProvider = _dropdownProviders.CreateLocalized(() => component.Substance, value => component.SetSubstance(value),
        ContaminationSensorLoc.SubstancePrefix);
      _reading = panel.AddGameLabel();
    }

    public override void ShowFragment(BaseComponent entity) {
      base.ShowFragment(entity);
      if (!component) return;
      _dropdownItemsSetter.SetItems(_substance, _substanceProvider);
      UpdateFragment();
    }

    public override void UpdateFragment() {
      if (!component) return;
      string text = component.Sensor.SampledContamination.HasValue ? Reading(component) : "";
      _reading.text = text;
      _reading.style.display = text.Length > 0 ? DisplayStyle.Flex : DisplayStyle.None;
    }

    private string Reading(ContaminationSensorSubstance sensor) => sensor.Substance switch {
      SensedSubstance.Badwater => "",
      SensedSubstance.Radiation => string.Format(_loc.T(ContaminationSensorLoc.RadiationReading), Percent(sensor.MeasuredRadioactiveShare)),
      SensedSubstance.Any => string.Format(_loc.T(ContaminationSensorLoc.AnyReading), Percent(sensor.MeasuredBadwaterShare),
        Percent(sensor.MeasuredRadioactiveShare)),
      _ => throw new System.ArgumentOutOfRangeException(nameof(sensor.Substance), sensor.Substance, "Unknown contamination sensor substance"),
    };

    // Finer than the native whole-percent readout: pumps refuse radioactive
    // water from 0.5% (RadiationTuning.DetectionLimit; below it the share reads 0).
    private static string Percent(float share) => (share * 100f).ToString("0.##");
  }

  [Context("Game")]
  public sealed class ContaminationSensorPanelConfigurator : Configurator {
    protected override void Configure() {
      this.BindFragment<ContaminationSensorSubstancePanel>();
    }
  }
}
#endif
