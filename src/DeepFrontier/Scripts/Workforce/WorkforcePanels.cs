#if !UNITY_EDITOR
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.GameDistricts;
using Timberborn.Localization;
using Timberborn.WorkSystem;
using TimberUi.CommonUi;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  internal sealed class IndustrialRiskPanel : BaseEntityPanelFragment<IndustrialRisk> {
    private readonly WorkforceSettings _settings;
    private readonly ILoc _loc;
    private Label _risk,_severity,_crew,_record,_bots;
    public IndustrialRiskPanel(WorkforceSettings settings, ILoc loc) {_settings=settings;_loc=loc;}
    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T("DeepFrontier.Workforce.Panel.Title"),bold:true);
      _risk=Wrapped();_severity=Wrapped();_crew=Wrapped();_record=Wrapped();_bots=Wrapped();
    }
    private Label Wrapped() {var label=panel.AddGameLabel();label.style.whiteSpace=WhiteSpace.Normal;return label;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      var spec=component.Spec;
      var tier=_loc.T($"DeepFrontier.Workforce.Danger.{spec.DangerTier}");
      _risk.text=component.InjuriesEnabled
        ?_loc.T("DeepFrontier.Workforce.Panel.InjuryRisk",tier,(component.FitChancePerHour*100f).ToString("0.##"),
          $"{_settings.Spec.StrainedRolls}/{_settings.Spec.ExhaustedRolls}")
        :_loc.T("DeepFrontier.Workforce.Panel.InjuriesDisabled",tier);
      var days=Mathf.RoundToInt(-spec.InjuryPoints/_settings.InjuryNeed.DailyDelta);
      _severity.text=_loc.T("DeepFrontier.Workforce.Panel.InjurySeverity",days,Mathf.RoundToInt(spec.FatalAccidentChance*100f));
      _crew.text=_loc.T("DeepFrontier.Workforce.Panel.Crew",component.FitWorkers,component.StrainedWorkers,component.ExhaustedWorkers);
      _record.text=_loc.T("DeepFrontier.Workforce.Panel.Record",component.Injuries,component.Fatalities);
      _bots.text=component.GetComponent<WorkplaceSpec>().DisallowOtherWorkerTypes
        ?_loc.T("DeepFrontier.Workforce.Panel.BotsNotAllowed")
        :_loc.T("DeepFrontier.Workforce.Panel.BotWear",spec.BotWearMultiplier.ToString("0.#"));
    }
  }

  internal sealed class SpecialistWorkplacePanel : BaseEntityPanelFragment<SpecialistWorkplace> {
    private readonly WorkforceSettings _settings;
    private readonly ILoc _loc;
    private Label _required,_staffing,_advice;
    public SpecialistWorkplacePanel(WorkforceSettings settings, ILoc loc) {_settings=settings;_loc=loc;}
    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T("DeepFrontier.Workforce.Specialists.Title"),bold:true);
      _required=Wrapped();_staffing=Wrapped();_advice=Wrapped();
    }
    private Label Wrapped() {var label=panel.AddGameLabel();label.style.whiteSpace=WhiteSpace.Normal;return label;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      var discipline=_settings.Discipline(component.Discipline);
      var plural=_loc.T(discipline.PluralDisplayNameLocKey);
      _required.text=_loc.T("DeepFrontier.Workforce.Specialists.Required",plural);
      var workplace=component.Workplace;
      _staffing.text=_loc.T("DeepFrontier.Workforce.Specialists.Staffing",
        $"{workplace.NumberOfAssignedWorkers}/{workplace.DesiredWorkers}",component.AvailableSpecialists,plural);
      _advice.text=_loc.T("DeepFrontier.Workforce.Specialists.Train",plural);
    }
  }

  internal sealed class SpecialistSchoolPanel : BaseEntityPanelFragment<SpecialistSchool> {
    private readonly WorkforceSettings _settings;
    private readonly SpecialistRoster _roster;
    private readonly ILoc _loc;
    private readonly List<(string discipline, Button button)> _teach=new List<(string, Button)>();
    private Label _program,_students,_remaining,_roster_;
    public SpecialistSchoolPanel(WorkforceSettings settings, SpecialistRoster roster, ILoc loc) {_settings=settings;_roster=roster;_loc=loc;}
    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T("DeepFrontier.Workforce.School.Title"),bold:true);
      _program=Wrapped();_students=Wrapped();_remaining=Wrapped();
      foreach(var discipline in _settings.Disciplines) {
        var id=discipline.Id;
        var button=panel.AddGameButton(_loc.T("DeepFrontier.Workforce.School.Teach",_loc.T(discipline.PluralDisplayNameLocKey)),
          ()=>{if(component)component.Teach(id);UpdateFragment();});
        _teach.Add((id,button));
      }
      _roster_=Wrapped();
    }
    private Label Wrapped() {var label=panel.AddGameLabel();label.style.whiteSpace=WhiteSpace.Normal;return label;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      var current=component.Discipline;
      foreach(var (discipline,button) in _teach) {
        var taught=component.Disciplines.Contains(discipline);
        button.style.display=taught?DisplayStyle.Flex:DisplayStyle.None;
        button.SetEnabled(discipline!=current);
      }
      if(current==null) {
        _program.text=_loc.T("DeepFrontier.Workforce.School.NoProgram");
        _students.text=_remaining.text="";
      } else {
        var spec=_settings.Discipline(current);
        _program.text=_loc.T("DeepFrontier.Workforce.School.Program",_loc.T(spec.PluralDisplayNameLocKey),component.StudyHours.ToString("0.#"));
        _students.text=_loc.T("DeepFrontier.Workforce.School.Students",component.Students.Count());
        var district=component.GetComponent<DistrictBuilding>().District;
        _remaining.text=district
          ?_loc.T("DeepFrontier.Workforce.School.Remaining",district.GetComponent<DistrictPopulation>().Adults
            .Select(b=>b.GetComponent<SpecialistTrait>()).Count(t=>t&&!t.Has(current)))
          :"";
      }
      _roster_.text=_loc.T("DeepFrontier.Workforce.School.Roster",string.Join(", ",
        _settings.Disciplines.Select(d=>$"{_loc.T(d.PluralDisplayNameLocKey)} {_roster.Count(d.Id)}")));
    }
  }

  internal sealed class SpecialistTraitPanel : BaseEntityPanelFragment<SpecialistTrait> {
    private readonly WorkforceSettings _settings;
    private readonly ILoc _loc;
    private Label _held,_studying;
    public SpecialistTraitPanel(WorkforceSettings settings, ILoc loc) {_settings=settings;_loc=loc;}
    protected override void InitializePanel() {
      _held=panel.AddGameLabel();_held.style.whiteSpace=WhiteSpace.Normal;
      _studying=panel.AddGameLabel();_studying.style.whiteSpace=WhiteSpace.Normal;
    }
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      panel.Visible=component.IsSpecialist||component.StudyHours.Count>0;
      _held.text=component.IsSpecialist
        ?_loc.T("DeepFrontier.Workforce.Trait.Specialist",string.Join(", ",
          component.Disciplines.Select(d=>_loc.T(_settings.Discipline(d).DisplayNameLocKey))))
        :"";
      _studying.text=component.StudyHours.Count>0
        ?_loc.T("DeepFrontier.Workforce.Trait.Training",string.Join(", ",
          component.StudyHours.Select(s=>_loc.T(_settings.Discipline(s.Key).DisplayNameLocKey)+" "+s.Value.ToString("0.#")+" h")))
        :"";
    }
  }

  internal sealed class BotWearPanel : BaseEntityPanelFragment<BotWear> {
    private readonly ILoc _loc;
    private Label _line;
    public BotWearPanel(ILoc loc) {_loc=loc;}
    protected override void InitializePanel() {_line=panel.AddGameLabel();_line.style.whiteSpace=WhiteSpace.Normal;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}
    public override void UpdateFragment() {
      if(!component)return;
      var risk=component.Risk;
      if(!risk||risk.BotWearMultiplier<=1f) {panel.Visible=false;return;}
      panel.Visible=true;
      var building=risk.GetComponent<Timberborn.EntitySystem.LabeledEntity>().DisplayName;
      _line.text=component.Wearing
        ?_loc.T("DeepFrontier.Workforce.Bot.Wearing",risk.BotWearMultiplier.ToString("0.#"),building)
        :_loc.T("DeepFrontier.Workforce.Bot.Assigned",risk.BotWearMultiplier.ToString("0.#"),building);
    }
  }

  [Context("Game")]
  public sealed class WorkforcePanelConfigurator : Configurator {
    protected override void Configure() {
      this.BindFragment<IndustrialRiskPanel>();
      this.BindFragment<SpecialistWorkplacePanel>();
      this.BindFragment<SpecialistSchoolPanel>();
      this.BindFragment<SpecialistTraitPanel>();
      this.BindFragment<BotWearPanel>();
    }
  }
}
#endif
