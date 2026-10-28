#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using TimberUi.CommonUi;
using UnityEngine.UIElements;
namespace DeepFrontier.Scripts {
  internal sealed class ShoreFishingPanel : BaseEntityPanelFragment<ShoreFishing> {
    private Toggle _mode;private Label _status;
    protected override void InitializePanel() {
      panel.AddGameLabel("Shore fishing",bold:true);
      _mode=panel.AddGamePanelToggle("Catch fish",onValueChanged:value=>{if(component)component.SelectFishing(value);});
      _status=panel.AddGameLabel();_status.style.whiteSpace=WhiteSpace.Normal;
    }
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;_mode.SetValueWithoutNotify(component.FishingSelected);
      _status.text=$"{component.State}\n1 fish per {component.Spec.CatchHours} base working hours, plus travel. Requires reachable clean water; droughts and contamination stop fishing.";
    }
  }
  [Context("Game")]
  public sealed class ShoreFishingPanelConfigurator : Configurator {
    protected override void Configure() {this.BindFragment<ShoreFishingPanel>();}
  }
}
#endif
