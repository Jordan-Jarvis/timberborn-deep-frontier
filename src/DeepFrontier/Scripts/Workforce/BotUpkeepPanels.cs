#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // Second fragment on the bot, beside the workforce BotWearPanel.
  internal sealed class BotServicePanel : BaseEntityPanelFragment<BotWear> {
    private readonly ILoc _loc;
    private readonly IGoodService _goods;
    private Label _line;
    public BotServicePanel(ILoc loc, IGoodService goods) {_loc=loc;_goods=goods;}
    protected override void InitializePanel() {_line=panel.AddGameLabel();_line.style.whiteSpace=WhiteSpace.Normal;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      var risk=component.Risk;
      if(!risk||!risk.GetComponent<BotMaintenance>()) {panel.Visible=false;return;}
      panel.Visible=true;
      _line.text=component.IsServiced
        ?_loc.T("DeepFrontier.BotUpkeep.Bot.Serviced",_goods.GetGood(component.ServiceGood).PluralDisplayName.Value,
          BotWear.Serviced(risk.BotWearMultiplier,component.ServiceWearFactor).ToString("0.#"),component.ServiceHoursLeft.ToString("0"))
        :_loc.T("DeepFrontier.BotUpkeep.Bot.Unserviced",risk.GetComponent<LabeledEntity>().DisplayName);
    }
  }

  [Context("Game")]
  public sealed class BotUpkeepPanelConfigurator : Configurator {
    protected override void Configure() {
      this.BindFragment<BotServicePanel>();
    }
  }
}
#endif
