#if !UNITY_EDITOR
using System;
using Bindito.Core;
using DeepFrontier.Scripts.Sensors;
using Timberborn.BaseComponentSystem;
using Timberborn.CoreUI;
using Timberborn.DropdownSystem;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.SluiceIsBackContamination {
  // Measured-substance choice for the Sluice is Back! sluice, shown after the
  // mod's own sluice fragment (a top fragment, SluiceIsBack.MGameConfig). Its
  // "Contamination: x%" label is the badwater share (Sluice.Contamination);
  // this adds the radioactive share for Radiation and Any, from the same
  // source column. The dropdown is the native Dropdown with a native
  // localized EnumDropdownProvider and the same keys and texts as the
  // Contamination Sensor's choice (ContaminationSensorLoc).
  internal sealed class SluiceContaminationPanel : BaseEntityPanelFragment<SluiceContaminationSubstance> {
    private readonly ILoc _loc;
    private readonly VisualElementInitializer _initializer;
    private readonly DropdownItemsSetter _dropdownItemsSetter;
    private readonly EnumDropdownProviderFactory _dropdownProviders;
    private Dropdown _substance;
    private EnumDropdownProvider<SensedSubstance> _substanceProvider;
    private Label _reading;

    public SluiceContaminationPanel(ILoc loc, VisualElementInitializer initializer, DropdownItemsSetter dropdownItemsSetter,
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
      string text = Reading(component);
      _reading.text = text;
      _reading.style.display = text.Length > 0 ? DisplayStyle.Flex : DisplayStyle.None;
    }

    private string Reading(SluiceContaminationSubstance sluice) {
      if (sluice.Substance == SensedSubstance.Badwater) return "";
      var sample = sluice.Read(SluiceIsBackNative.SourceCoordinates(sluice.Sluice));
      return sluice.Substance switch {
        SensedSubstance.Radiation => string.Format(_loc.T(ContaminationSensorLoc.RadiationReading), Percent(sample.WaterRadiation)),
        SensedSubstance.Any => string.Format(_loc.T(ContaminationSensorLoc.AnyReading), Percent(sample.BadwaterShare), Percent(sample.WaterRadiation)),
        _ => throw new ArgumentOutOfRangeException(nameof(sluice.Substance), sluice.Substance, "Unknown sluice contamination substance"),
      };
    }

    // As the Contamination Sensor readout: finer than the mod's whole-percent
    // label, because pumps refuse radioactive water from 0.5%.
    private static string Percent(float share) => (share * 100f).ToString("0.##");
  }

  [Context("Game")]
  public sealed class SluiceContaminationPanelConfigurator : Configurator {
    protected override void Configure() {
      this.BindFragment<SluiceContaminationPanel>();
    }
  }
}
#endif
