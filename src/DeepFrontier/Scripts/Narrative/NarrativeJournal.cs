#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.CoreUI;
using Timberborn.EntityPanelSystem;
using Timberborn.Goods;
using Timberborn.Localization;
using Timberborn.SingletonSystem;
using Timberborn.UILayoutSystem;
using TimberUi.CommonUi;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.Narrative {
  // Frontier Journal: a small top-left panel (current chapter and its next
  // unmet objective) that opens the journal window, the queued story dialogs
  // for completed chapters and discoveries, and the ending choice.
  // Story dialogs use the native DialogBoxShower (as the rocket program does)
  // and wait until no other panel or dialog is open, so a rocket's own mission
  // dialog is read before the journal's chapter that follows it.
  internal sealed class NarrativePresenter : ILoadableSingleton, IUpdatableSingleton {
    private const int TopLeftOrder=4;
    private const float RefreshSeconds=.5f;
    private readonly NarrativeObjectiveService _narrative;
    private readonly UILayout _layout;
    private readonly EventBus _events;
    private readonly DialogBoxShower _dialogs;
    private readonly VisualElementInitializer _initializer;
    private readonly PanelStack _panels;
    private readonly ILoc _loc;
    private readonly Queue<Action> _queue=new();
    private bool _anyPanelShown;
    private VisualElement _widget;
    private Label _widgetTitle,_widgetLine;
    private float _nextRefresh;

    public NarrativePresenter(NarrativeObjectiveService narrative,UILayout layout,EventBus events,DialogBoxShower dialogs,
      VisualElementInitializer initializer,PanelStack panels,ILoc loc) {
      _narrative=narrative;_layout=layout;_events=events;_dialogs=dialogs;_initializer=initializer;_panels=panels;_loc=loc;
    }

    public void Load() {
      _events.Register(this);
      _narrative.Completed+=completion=>_queue.Enqueue(()=>ShowStory(completion));
      _narrative.ChoiceRequested+=()=>_queue.Enqueue(ShowChoice);
    }

    [OnEvent]
    public void OnShowPrimaryUI(ShowPrimaryUIEvent showPrimaryUIEvent) {
      if(!_narrative.Active)return;
      if(_widget==null)BuildWidget();
      _layout.AddTopLeft(_widget,TopLeftOrder);
      RefreshWidget();
    }

    [OnEvent] public void OnPanelShown(PanelShownEvent shown)=>_anyPanelShown=true;
    [OnEvent] public void OnPanelHidden(PanelHiddenEvent hidden)=>_anyPanelShown=hidden.AnyPanelShown;

    public void UpdateSingleton() {
      if(!_narrative.Active)return;
      if(!_anyPanelShown&&_queue.Count>0)_queue.Dequeue()();
      if(_widget!=null&&Time.unscaledTime>=_nextRefresh) {
        _nextRefresh=Time.unscaledTime+RefreshSeconds;
        RefreshWidget();
      }
    }

    // ---- text ----
    private int ChapterCount=>_narrative.Spec.Stages.Length;
    private string Title(NarrativeStageSpec stage)=>_loc.T(stage.TitleLocKey);

    private string ProgressLine(NarrativeRequirementSpec r)=>_narrative.IsMet(r)
      ?_loc.T("Narrative.Journal.ProgressDone",_loc.T(r.LabelLocKey))
      :_loc.T("Narrative.Journal.Progress",_loc.T(r.LabelLocKey),Math.Min(_narrative.Progress(r),r.Amount),r.Amount);

    // Body of a completed chapter or discovery: the variant line for the
    // colony's own first step, the story and, where authored, the ending.
    private string StoryText(NarrativeStageSpec stage) {
      var parts=new List<string>();
      var variant=_narrative.VariantLocKey(stage);
      if(variant!=null)parts.Add(_loc.T(variant));
      parts.AddRange(stage.StoryLocKeys.Select(key=>_loc.T(key)));
      var ending=_narrative.ChosenEnding;
      if(ending!=null&&stage.EndingText==NarrativeObjectiveService.ChoiceText)
        parts.Add(_loc.T("Narrative.Dialog.Decision",_loc.T(ending.TitleLocKey))+"\n"+_loc.T(ending.DescriptionLocKey));
      if(ending!=null&&stage.EndingText==NarrativeObjectiveService.EpilogueText) {
        parts.Add($"<b>{_loc.T(ending.TitleLocKey)}</b>");
        parts.AddRange(ending.EpilogueLocKeys.Select(key=>_loc.T(key)));
      }
      return string.Join("\n\n",parts);
    }

    private void ShowStory(NarrativeCompletion completion) {
      var stage=completion.Stage;
      var header=completion.IsDiscovery?_loc.T("Narrative.Dialog.Discovery")
        :_loc.T("Narrative.Dialog.Chapter",completion.ChapterNumber,ChapterCount);
      var message=$"{header}\n<b>{Title(stage)}</b>\n\n{StoryText(stage)}";
      if(stage.ScienceReward>0)message+="\n\n"+_loc.T("Narrative.Dialog.Reward",stage.ScienceReward);
      _dialogs.Create().SetMessage(message).Show();
    }

    // ---- top-left panel ----
    private void BuildWidget() {
      _widget=new VisualElement();
      _widget.style.maxWidth=300;
      var fragment=_widget.AddFragment();
      _widgetTitle=fragment.AddGameLabel(bold:true);
      _widgetLine=fragment.AddGameLabel();
      _widgetLine.style.whiteSpace=WhiteSpace.Normal;
      fragment.AddGameButton(_loc.T("Narrative.Journal.Open"),OpenJournal);
      _initializer.InitializeVisualElement(_widget);
    }

    private void RefreshWidget() {
      var current=_narrative.CurrentStage;
      if(current==null) {
        _widgetTitle.text=_loc.T("Narrative.Journal.WidgetComplete");
        _widgetLine.text="";
        return;
      }
      _widgetTitle.text=_loc.T("Narrative.Journal.Widget",_narrative.CompletedStageIds.Count,ChapterCount);
      var next=current.Requirements.FirstOrDefault(r=>!_narrative.IsMet(r));
      _widgetLine.text=Title(current)+(next!=null?"\n"+ProgressLine(next):"");
    }

    // ---- journal window ----
    private static Label Text(VisualElement parent,string text,bool bold=false) {
      var label=parent.AddGameLabel(text,bold:bold);
      label.style.whiteSpace=WhiteSpace.Normal;
      label.style.marginBottom=4;
      return label;
    }

    private void OpenJournal() {
      var box=new DialogBoxElement();
      box.SetTitle(_loc.T("Narrative.Journal.Title"));
      box.AddCloseButton();
      box.SetDialogPercentSize(.45f,.7f);
      var content=box.Content;
      var current=_narrative.CurrentStage;
      if(current!=null) {
        Text(content,_loc.T("Narrative.Journal.Current",_narrative.CompletedStageIds.Count+1,ChapterCount,Title(current)),bold:true);
        Text(content,_loc.T(current.ObjectiveLocKey));
        foreach(var r in current.Requirements)Text(content,ProgressLine(r));
        Text(content,_loc.T("Narrative.Journal.Hint",_loc.T(current.HintLocKey)));
        if(_narrative.AwaitingChoice)AddChoices(content,box);
      } else {
        Text(content,_loc.T("Narrative.Journal.AllComplete"),bold:true);
      }
      var ending=_narrative.ChosenEnding;
      if(ending!=null)Text(content,_loc.T("Narrative.Journal.Chosen",_loc.T(ending.TitleLocKey)));

      Text(content,_loc.T("Narrative.Journal.Chronicle"),bold:true);
      var completed=_narrative.CompletedStageIds;
      if(completed.Count==0)Text(content,_loc.T("Narrative.Journal.NoChronicle"));
      for(int i=completed.Count-1;i>=0;i--)
        AddEntry(content,_loc.T("Narrative.Journal.ChapterEntry",i+1,Title(_narrative.Spec.Stages[i])),_narrative.Spec.Stages[i]);

      var discoveries=_narrative.Spec.Discoveries;
      Text(content,_loc.T("Narrative.Journal.Discoveries",_narrative.CompletedDiscoveryIds.Count,discoveries.Length),bold:true);
      foreach(var discovery in discoveries) {
        if(_narrative.IsDiscovered(discovery))AddEntry(content,Title(discovery),discovery);
        else Text(content,_loc.T("Narrative.Journal.DiscoveryPending",_loc.T(discovery.ObjectiveLocKey)));
      }
      box.Show(_initializer,_panels);
    }

    private void AddEntry(VisualElement parent,string title,NarrativeStageSpec stage) {
      var entry=parent.AddCollapsiblePanel(title,expand:false);
      Text(entry.Container,StoryText(stage));
    }

    private void AddChoices(VisualElement parent,DialogBoxElement box) {
      Text(parent,_loc.T("Narrative.Journal.ChooseIntro"),bold:true);
      foreach(var ending in _narrative.Spec.Endings) {
        var id=ending.Id;
        Text(parent,_loc.T(ending.TitleLocKey),bold:true);
        Text(parent,_loc.T(ending.DescriptionLocKey));
        parent.AddMenuButton(_loc.T("Narrative.Journal.ChooseButton",_loc.T(ending.TitleLocKey)),()=>{
          box.Close();
          _narrative.ChooseEnding(id);
        },stretched:true);
      }
    }

    private void ShowChoice() {
      if(!_narrative.AwaitingChoice)return;
      var box=new DialogBoxElement();
      box.SetTitle(_loc.T("Narrative.Choice.Title"));
      box.AddCloseButton();
      box.SetDialogPercentSize(.4f,.6f);
      Text(box.Content,_loc.T(_narrative.CurrentStage.ObjectiveLocKey));
      AddChoices(box.Content,box);
      box.Content.AddMenuButton(_loc.T("Narrative.Choice.Later"),box.Close,stretched:true);
      box.Show(_initializer,_panels);
    }
  }

  // Survey state of a Human Record Cache.
  internal sealed class HumanRecordCachePanel : BaseEntityPanelFragment<HumanRecordCache> {
    private readonly ILoc _loc;
    private readonly IGoodService _goods;
    private Label _state,_reward;
    public HumanRecordCachePanel(ILoc loc,IGoodService goods) {_loc=loc;_goods=goods;}

    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T("Narrative.Cache.Title"),bold:true);
      _state=Wrapped();_reward=Wrapped();
    }
    private Label Wrapped() {var label=panel.AddGameLabel();label.style.whiteSpace=WhiteSpace.Normal;return label;}
    public override void ShowFragment(BaseComponent entity) {base.ShowFragment(entity);UpdateFragment();}

    public override void UpdateFragment() {
      if(!component)return;
      var cache=component;
      _state.text=cache.State switch {
        HumanRecordCacheState.Surveyed=>_loc.T("Narrative.Cache.Surveyed"),
        HumanRecordCacheState.NoSurveyor=>_loc.T("Narrative.Cache.NoSurveyor",cache.Spec.SurveyRadius),
        HumanRecordCacheState.Idle=>_loc.T("Narrative.Cache.Idle"),
        HumanRecordCacheState.Surveying=>_loc.T("Narrative.Cache.Surveying",Mathf.FloorToInt(cache.SurveyFraction*100f)),
        HumanRecordCacheState.WaitingForStorage=>_loc.T("Narrative.Cache.WaitingForStorage",cache.Delivered,cache.Spec.RewardAmount),
        _=>cache.State.ToString(),
      };
      _reward.text=cache.Surveyed?"":_loc.T("Narrative.Cache.Reward",cache.Spec.RewardAmount,
        _goods.GetGood(cache.Spec.RewardGoodId).PluralDisplayName.Value);
    }
  }

  [Context("Game")]
  public sealed class NarrativeJournalConfigurator : Configurator {
    protected override void Configure() {
      Bind<NarrativePresenter>().AsSingleton();
      this.BindFragment<HumanRecordCachePanel>();
    }
  }
}
#endif
