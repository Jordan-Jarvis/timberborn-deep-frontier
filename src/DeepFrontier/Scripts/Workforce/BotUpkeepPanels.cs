#if !UNITY_EDITOR
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // Texts: DeepFrontier.BotUpkeep.* rows written by tools/bot_upkeep_content.mjs.
  internal sealed class BotMaintenancePanel : BaseEntityPanelFragment<BotMaintenance> {
    private readonly ILoc _loc;
    private readonly IGoodService _goods;
    private Label _bots,_goodsLine,_dose;
    public BotMaintenancePanel(ILoc loc, IGoodService goods) {_loc=loc;_goods=goods;}
    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T("DeepFrontier.BotUpkeep.Panel.Title"),bold:true);
      _bots=Wrapped();_goodsLine=Wrapped();_dose=Wrapped();
    }
    private Label Wrapped() {var label=panel.AddGameLabel();label.style.whiteSpace=WhiteSpace.Normal;return label;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      _bots.text=component.AssignedBots>0
        ?_loc.T("DeepFrontier.BotUpkeep.Panel.Bots",component.AssignedBots,component.ServicedBots)
        :_loc.T("DeepFrontier.BotUpkeep.Panel.NoBots");
      _goodsLine.text=string.Join("\n",component.Spec.Goods.Select(g=>_loc.T("DeepFrontier.BotUpkeep.Panel.Good",
        _goods.GetGood(g.GoodId).PluralDisplayName.Value,component.Inventory.AmountInStock(g.GoodId),
        component.ServicedMultiplier(g).ToString("0.#"))));
      _dose.text=_loc.T("DeepFrontier.BotUpkeep.Panel.Dose",component.Spec.ServiceHours.ToString("0.#"),
        component.Risk.BotWearMultiplier.ToString("0.#"));
    }
  }

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
      this.BindFragment<BotMaintenancePanel>();
      this.BindFragment<BotServicePanel>();
    }
  }
}
#endif
