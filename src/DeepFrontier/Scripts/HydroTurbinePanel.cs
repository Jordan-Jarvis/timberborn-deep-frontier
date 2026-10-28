#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  internal sealed class HydroTurbinePanel : BaseEntityPanelFragment<HydroTurbine> {
    private GameSlider _limit;
    private Toggle _closed;
    private Label _status;
    protected override void InitializePanel() {
      panel.AddGameLabel("Dam turbine",bold:true);
      panel.AddGameLabel("Discharge limit");
      _limit=panel.AddSlider();
      _limit.Slider.showInputField=true;
      _limit.AddEndLabel("m³/s");
      _limit.RegisterChange(value=>{if(component)component.SetDischargeLimit(value);});
      _closed=panel.AddGamePanelToggle("Close outlet",
        onValueChanged:value=>{if(component)component.SetClosed(value);});
      _status=panel.AddGameLabel();_status.style.whiteSpace=WhiteSpace.Normal;
    }
    public override void ShowFragment(BaseComponent entity) {
      base.ShowFragment(entity);
      if(component)_limit.SetHorizontalSlider(new SliderValues<float>(0,
        component.Spec.MaxDischarge,component.DischargeLimit));
      UpdateFragment();
    }
    public override void UpdateFragment() {
      if(!component)return;
      _limit.SetValueWithoutNotify(component.DischargeLimit);
      _closed.SetValueWithoutNotify(component.ManuallyClosed);
      _status.text=$"{component.State}\nMeasured total flow: {component.ActualFlow:0.000} m³/s"+
        $"\nUpstream water level: {component.UpstreamHeight:0.00} layers"+
        $"\nOutlet pressure level: {component.DownstreamHeight:0.00} layers"+
        $"\nAvailable head: {component.AvailableHead:0.00} layers";
    }
  }
  [Context("Game")]
  public sealed class HydroTurbinePanelConfigurator : Configurator {
    protected override void Configure() {this.BindFragment<HydroTurbinePanel>();}
  }
}
#endif
