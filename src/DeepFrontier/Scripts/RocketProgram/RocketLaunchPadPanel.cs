#if !UNITY_EDITOR
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.Goods;
using Timberborn.Localization;
using Timberborn.Workshops;
using TimberUi.CommonUi;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // Mission selection itself is the native recipe selector of the workshop
  // panel; this fragment explains the program, the selected mission's rocket
  // and fuel, the launch odds and what success or failure means.
  internal sealed class RocketLaunchPadPanel : BaseEntityPanelFragment<RocketLaunchPad> {
    private readonly RocketProgramService _program;
    private readonly RecipeSpecService _recipes;
    private readonly IGoodService _goods;
    private readonly ILoc _loc;
    private Label _missions,_state,_rocket,_odds,_stakes,_reward,_legacy,_last;
    public RocketLaunchPadPanel(RocketProgramService program,RecipeSpecService recipes,IGoodService goods,ILoc loc) {
      _program=program;_recipes=recipes;_goods=goods;_loc=loc;
    }
    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T("RocketProgram.Panel.Title"),bold:true);
      _missions=Wrapped();_state=Wrapped();_rocket=Wrapped();_odds=Wrapped();_stakes=Wrapped();_reward=Wrapped();_legacy=Wrapped();_last=Wrapped();
    }
    private Label Wrapped() {var label=panel.AddGameLabel();label.style.whiteSpace=WhiteSpace.Normal;return label;}
    private static int Pct(float value)=>Mathf.RoundToInt(value*100f);
    private string Name(RocketMissionSpec mission)=>_loc.T(mission.DisplayNameLocKey);
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}

    public override void UpdateFragment() {
      if(!component)return;
      var pad=component;
      _missions.text=string.Join("\n",pad.Missions.Select(m=>_program.IsCompleted(m.Id)
        ?_loc.T("RocketProgram.Panel.MissionCompleted",Name(m))
        :pad.IsLocked(m)?_loc.T("RocketProgram.Panel.MissionLocked",Name(m),Name(pad.Missions.Single(p=>p.Id==m.PrerequisiteMissionId)))
        :_loc.T("RocketProgram.Panel.MissionAvailable",Name(m))));
      var mission=pad.CurrentMission;
      var stage=pad.Stage;
      _state.text=stage switch {
        RocketPadStage.UnderConstruction=>_loc.T("RocketProgram.Stage.UnderConstruction"),
        RocketPadStage.NoMission=>_loc.T("RocketProgram.Stage.NoMission"),
        RocketPadStage.Telemetry=>_loc.T("RocketProgram.Stage.Telemetry"),
        RocketPadStage.InFlight=>_loc.T("RocketProgram.Stage.InFlight",Name(pad.FlightMission)),
        RocketPadStage.Refurbishing=>_loc.T("RocketProgram.Stage.Refurbishing",Mathf.CeilToInt(pad.RefurbishHoursLeft)),
        RocketPadStage.Blocked=>_loc.T("RocketProgram.Stage.Blocked"),
        RocketPadStage.MissionCompleted=>_loc.T("RocketProgram.Stage.MissionCompleted"),
        RocketPadStage.MissionInFlightElsewhere=>_loc.T("RocketProgram.Stage.MissionInFlightElsewhere"),
        RocketPadStage.MissionLocked=>_loc.T("RocketProgram.Stage.MissionLocked"),
        RocketPadStage.Staging=>_loc.T("RocketProgram.Stage.Staging"),
        RocketPadStage.Preparing=>_loc.T("RocketProgram.Stage.Preparing",Pct(pad.Manufactory.ProductionProgress)),
        RocketPadStage.HoldingForPower=>_loc.T("RocketProgram.Stage.HoldingForPower",Pct(pad.Manufactory.ProductionProgress)),
        _=>stage.ToString(),
      };
      if(mission==null) {
        _rocket.text=_odds.text=_stakes.text=_reward.text="";
      } else {
        var recipe=_recipes.GetRecipe(mission.RecipeId);
        _rocket.text=_loc.T(mission.DescriptionLocKey)+"\n"+(pad.RocketStacked
          ?_loc.T("RocketProgram.Panel.RocketStacked")
          :string.Join("\n",recipe.Ingredients.Select(i=>$"{_goods.GetGood(i.Id).PluralDisplayName.Value}: {pad.Manufactory.Inventory.AmountInStock(i.Id)} / {i.Amount}")));
        _odds.text=_loc.T("RocketProgram.Panel.Odds",Pct(pad.FailureChance(mission)),Pct(mission.BaseFailureChance))
          +"\n"+_loc.T("RocketProgram.Panel.OddsMissionControl",Pct(pad.MissionControlReduction),Pct(pad.Spec.MissionControlFailureReduction))
          +"\n"+_loc.T("RocketProgram.Panel.OddsHeritage",Pct(pad.HeritageReduction),_program.LaunchAttempts)
          +"\n"+_loc.T("RocketProgram.Panel.OddsFloor",Pct(pad.Spec.MinimumFailureChance));
        _stakes.text=_loc.T("RocketProgram.Panel.Stakes",Mathf.RoundToInt(pad.Spec.RefurbishmentHours));
        _reward.text=_loc.T("RocketProgram.Reward",mission.ScienceReward,mission.LegacyWellbeing,
          pad.Spec.LegacyRadius)
          +(mission.CompletesStory?"\n"+_loc.T("RocketProgram.Panel.FinalMission"):"");
      }
      _legacy.text=pad.AppliedLegacy.Count==0?""
        :_loc.T(pad.LegacyPowered?"RocketProgram.Panel.LegacyActive":"RocketProgram.Panel.LegacyUnpowered",
          pad.AppliedLegacy.Count,pad.Spec.LegacyRadius);
      _last.text=_program.LaunchAttempts==0?_loc.T("RocketProgram.Panel.NoLaunches")
        :_loc.T(_program.LastSucceeded?"RocketProgram.Panel.LastSuccess":"RocketProgram.Panel.LastFailure",
          Name(pad.Missions.Single(m=>m.Id==_program.LastMission)),Pct(_program.LastFailureChance));
    }
  }
  [Context("Game")]
  public sealed class RocketLaunchPadPanelConfigurator : Configurator {
    protected override void Configure() {this.BindFragment<RocketLaunchPadPanel>();}
  }
}
#endif
