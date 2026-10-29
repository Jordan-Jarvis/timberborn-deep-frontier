#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.DeepWell {
  // Deep Well panel: the boost slider (1x..MaxBoost x, saved per building),
  // the Radioactive Tide shut-off checkbox, and the well's state, power
  // demand, drill-bit use and the source's strength.
  internal sealed class DeepWellPanel : BaseEntityPanelFragment<DeepWell> {
    private readonly ILoc _loc;
    private GameSliderInt _boost;
    private Toggle _tide;
    private Label _status;

    public DeepWellPanel(ILoc loc) { _loc = loc; }

    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T(DeepWellLoc.PanelTitle), bold: true);
      panel.AddGameLabel(_loc.T(DeepWellLoc.PanelBoost));
      _boost = panel.AddSliderInt();
      _boost.AddEndLabel(value => _loc.T(DeepWellLoc.PanelBoostValue, value));
      _boost.RegisterChange(value => { if (component) component.SetBoost(value); });
      _tide = panel.AddGamePanelToggle(_loc.T(DeepWellLoc.PanelTide),
        onValueChanged: value => { if (component) component.SetShutOffDuringTide(value); });
      _status = panel.AddGameLabel();
      _status.style.whiteSpace = WhiteSpace.Normal;
    }

    public override void ShowFragment(BaseComponent entity) {
      base.ShowFragment(entity);
      if (component) _boost.SetHorizontalSlider(new SliderValues<int>(1, component.MaxBoost, component.Boost));
      UpdateFragment();
    }

    public override void UpdateFragment() {
      if (!component) return;
      _boost.SetValueWithoutNotify(component.Boost);
      _tide.SetValueWithoutNotify(component.ShutOffDuringTide);
      var text = _loc.T(DeepWellLoc.State + component.State, component.StrengthModifier.ToString("0.0"));
      text += "\n" + _loc.T(DeepWellLoc.PanelDemand, component.PowerDemandAtBoost.ToString("N0"));
      text += "\n" + _loc.T(DeepWellLoc.PanelDrillBits, component.DrillBitsPerHour.ToString("0.00"),
        component.HoursOfDrillBits.ToString("0"));
      var source = component.Source;
      if (source) {
        text += "\n" + _loc.T(DeepWellLoc.PanelSource, source.SpecifiedStrength.ToString("0.00"), source.CurrentStrength.ToString("0.00"));
        if (component.IsSeep) text += "\n" + _loc.T(DeepWellLoc.PanelSeep);
        if (component.IsCapped) text += "\n" + _loc.T(DeepWellLoc.PanelCapped);
      }
      _status.text = text;
    }
  }

  [Context("Game")]
  public sealed class DeepWellPanelConfigurator : Configurator {
    protected override void Configure() { this.BindFragment<DeepWellPanel>(); }
  }
}
#endif
