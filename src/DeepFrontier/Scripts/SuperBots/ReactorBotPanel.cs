#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.SuperBots {
  // Bot panel fragment: state of the Reactor retrofit and the queue/cancel
  // buttons. Texts: DeepFrontier.ReactorBot.Panel.* rows written by
  // tools/super_bot_content.mjs (numbers are baked into them from the catalog).
  internal sealed class ReactorBotPanel : BaseEntityPanelFragment<ReactorBot> {
    private readonly ILoc _loc;
    private Label _state,_plating;
    private Button _queue,_cancel;
    public ReactorBotPanel(ILoc loc) {_loc=loc;}

    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T("DeepFrontier.ReactorBot.Panel.Title"),bold:true);
      _state=Wrapped();_plating=Wrapped();
      _queue=panel.AddGameButton(_loc.T("DeepFrontier.ReactorBot.Panel.Queue"),()=>{if(component)component.Queue();UpdateFragment();});
      _cancel=panel.AddGameButton(_loc.T("DeepFrontier.ReactorBot.Panel.Cancel"),()=>{if(component)component.Cancel();UpdateFragment();});
    }
    private Label Wrapped() {var label=panel.AddGameLabel();label.style.whiteSpace=WhiteSpace.Normal;return label;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}

    public override void UpdateFragment() {
      if(!component)return;
      var state=component.Current;
      _state.text=_loc.T(state switch {
        ReactorBot.State.Queued=>"DeepFrontier.ReactorBot.Panel.Queued",
        ReactorBot.State.Reactor=>"DeepFrontier.ReactorBot.Panel.Upgraded",
        _=>"DeepFrontier.ReactorBot.Panel.Ordinary"});
      _plating.text=component.IsPlated?"":_loc.T("DeepFrontier.ReactorBot.Panel.Unplated");
      _plating.style.display=component.IsPlated?DisplayStyle.None:DisplayStyle.Flex;
      _queue.style.display=state==ReactorBot.State.Ordinary?DisplayStyle.Flex:DisplayStyle.None;
      _cancel.style.display=state==ReactorBot.State.Queued?DisplayStyle.Flex:DisplayStyle.None;
    }
  }

  [Context("Game")]
  public sealed class ReactorBotPanelConfigurator : Configurator {
    protected override void Configure() {
      this.BindFragment<ReactorBotPanel>();
    }
  }
}
#endif
