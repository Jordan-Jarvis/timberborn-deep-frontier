using System;
using System.Collections.Generic;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.Buildings;
using Timberborn.CoreUI;
using Timberborn.InputSystem;
using Timberborn.Localization;
using Timberborn.Persistence;
using Timberborn.ScienceSystem;
using Timberborn.SingletonSystem;
using Timberborn.SliderToggleSystem;
using Timberborn.TemplateSystem;
using Timberborn.TooltipSystem;
using Timberborn.UIFormatters;
using Timberborn.WorkerTypesUI;
using Timberborn.WorkSystem;
using Timberborn.WorkSystemUI;
using Timberborn.WorldPersistence;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.SuperBots {
  // The per-workplace science unlock of the Reactor Bot option (user: 3x the
  // normal bot unlock; rule in ReactorBotWorkplaceSettings.ReactorUnlockCost).
  // Kept apart from native WorkplaceUnlockingService: that service saves its
  // unlocked (template, worker type) pairs and resolves each saved type through
  // WorkerTypeService on load, so a third type saved there would stop the save
  // loading without Deep Frontier. The flow is native
  // WorkplaceUnlockingDialogService.TryToUnlockWorkerType: free while the
  // native InstantUnlock key is held, otherwise the native dialog box with a
  // confirmation, or the native "not enough Science Points" box.
  internal sealed class ReactorBotWorkplaceUnlocks : ILoadableSingleton, ISaveableSingleton {
    private static readonly SingletonKey Key=new("DeepFrontier.ReactorBotWorkplaceUnlocks");
    private static readonly ListKey<string> TemplatesKey=new("Templates");
    private static readonly string InstantUnlockKey="InstantUnlock"; // native WorkplaceUnlockingDialogService
    private static readonly string PromptLocKey="DeepFrontier.WorkerType.ReactorBot.Unlock.Prompt";
    private static readonly string CantUnlockLocKey="DeepFrontier.WorkerType.ReactorBot.Unlock.CantUnlock";

    private readonly ISingletonLoader _loader;
    private readonly TemplateNameMapper _templates;
    private readonly ScienceService _science;
    private readonly ReactorBotWorkplaceSettings _settings;
    private readonly DialogBoxShower _dialogs;
    private readonly InputService _input;
    private readonly ILoc _loc;
    private readonly HashSet<string> _unlocked=new();

    public ReactorBotWorkplaceUnlocks(ISingletonLoader loader, TemplateNameMapper templates, ScienceService science,
      ReactorBotWorkplaceSettings settings, DialogBoxShower dialogs, InputService input, ILoc loc) {
      _loader=loader;_templates=templates;_science=science;_settings=settings;_dialogs=dialogs;_input=input;_loc=loc;
    }

    // Saved template names go through the native TemplateNameMapper (renamed
    // templates), as native WorkplaceUnlockingService does; unknown ones are dropped.
    public void Load() {
      if(!_loader.TryGetSingleton(Key,out var data))return;
      foreach(var name in data.Get(TemplatesKey))
        if(_templates.TryGetTemplate(name,out var template))_unlocked.Add(template.TemplateName);
    }

    public void Save(ISingletonSaver saver) {
      if(_unlocked.Count>0)saver.GetSingleton(Key).Set(TemplatesKey,_unlocked.OrderBy(n=>n,StringComparer.Ordinal).ToList());
    }

    public bool Unlocked(ReactorBotWorkplace workplace)=>_unlocked.Contains(workplace.TemplateName);

    public int Cost(ReactorBotWorkplace workplace)=>_settings.ReactorUnlockCost(workplace.WorkplaceSpec,workplace.GetComponent<BuildingSpec>());

    public void TryUnlock(ReactorBotWorkplace workplace, Action unlocked) {
      if(Unlocked(workplace))return;
      var cost=Cost(workplace);
      if(_input.IsKeyHeld(InstantUnlockKey)) {
        _unlocked.Add(workplace.TemplateName);
        unlocked();
      } else if(cost<=_science.SciencePoints) {
        _dialogs.Create().SetMessage(_loc.T(PromptLocKey,cost)).SetConfirmButton(()=>{
          if(cost>_science.SciencePoints) {_dialogs.Create().SetLocalizedMessage(CantUnlockLocKey).Show();return;}
          _science.SubtractPoints(cost);
          _unlocked.Add(workplace.TemplateName);
          unlocked();
        }).SetDefaultCancelButton().Show();
      } else {
        _dialogs.Create().SetLocalizedMessage(CantUnlockLocKey).Show();
      }
    }
  }

  // What the patched worker-type toggles show and do for the Reactor Bot
  // option (ReactorBotWorkplacePatches). Reached through the shown entity's
  // ReactorBotWorkplace or ReactorBotDistrictDefault, only from the toggle
  // items' callbacks: native EntityPanel.Load builds the toggles while
  // singletons are still loading (SingletonLifecycleService.LoadAll: every
  // Load, then the entities, then every PostLoad), and the callbacks run when
  // a panel is shown or updated, after all of it. Nothing here needs a Load.
  internal sealed class ReactorBotWorkplaceUi {
    private static readonly string TooltipLocKey="DeepFrontier.WorkerType.ReactorBot";
    private static readonly string LockedTooltipLocKey="DeepFrontier.WorkerType.ReactorBot.Unlock.Tooltip";

    private readonly ReactorBotWorkplaceUnlocks _unlocks;
    private readonly ReactorBotWorkplaceSettings _settings;
    private readonly WorkplaceUnlockingDialogService _nativeUnlocks;
    private readonly VisualElementLoader _elements;
    private readonly ILoc _loc;
    private readonly Phrase _scienceCostPhrase=Phrase.New().FormatCompact(); // as native WorkerTypeToggle

    public ReactorBotWorkplaceUi(ReactorBotWorkplaceUnlocks unlocks, ReactorBotWorkplaceSettings settings,
      WorkplaceUnlockingDialogService nativeUnlocks, VisualElementLoader elements, ILoc loc) {
      _unlocks=unlocks;_settings=settings;_nativeUnlocks=nativeUnlocks;_elements=elements;_loc=loc;
    }

    public Color IconTint=>_settings.WorkplaceColor;
    public string DisplayName=>_loc.T(TooltipLocKey);

    public static ReactorBotWorkplace Of(BaseComponent workerType) {
      var workplace=workerType.GetComponent<ReactorBotWorkplace>();
      if(!workplace)throw new InvalidOperationException($"{workerType.Name}: no Reactor Bot workplace component");
      return workplace;
    }

    // Reactor Bot button: never unclickable (every workplace may take Reactor Bots).
    public SliderToggleState ReactorState(ReactorBotWorkplace workplace)=>
      !workplace.Unlocked?SliderToggleState.Locked:workplace.ReactorMode?SliderToggleState.Active:SliderToggleState.None;

    public TooltipContent ReactorTooltip(ReactorBotWorkplace workplace)=>workplace.Unlocked
      ?TooltipContent.Create(()=>DisplayName)
      :TooltipContent.CreateInstant(()=>LockedTooltip(workplace));

    // The native locked-workplace tooltip (native WorkerTypeToggle.GetBotLockedTooltipElement) with the Reactor Bot cost.
    private VisualElement LockedTooltip(ReactorBotWorkplace workplace) {
      var element=_elements.LoadVisualElement("Game/ScienceCostTooltip");
      element.Q<Label>("TooltipText").text=_loc.T(LockedTooltipLocKey);
      element.Q<Label>("ScienceCost").text=_loc.T(_scienceCostPhrase,_unlocks.Cost(workplace));
      return element;
    }

    public void SelectReactor(ReactorBotWorkplace workplace) {
      if(workplace.Unlocked)workplace.Enable();
      else _unlocks.TryUnlock(workplace,workplace.Enable);
    }

    // Bot button: ordinary bots only. The native unlock flow first where bots
    // are still locked; the Reactor Bot mode ends only once Bot is chosen.
    public void SelectBot(ReactorBotWorkplace workplace) {
      if(!workplace.NativeBotAllowed)return; // as native SetWorkerType (the hotkey selects disabled buttons too)
      var pair=new UnlockableWorkerType(workplace.TemplateName,WorkerTypeHelper.BotWorkerType);
      void Choose() {
        workplace.Disable();
        workplace.WorkerType.SetWorkerType(WorkerTypeHelper.BotWorkerType);
      }
      if(_nativeUnlocks.IsWorkerTypeUnlocked(pair))Choose();
      else _nativeUnlocks.TryToUnlockWorkerType(pair,Choose);
    }
  }
}
