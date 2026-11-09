#if !UNITY_EDITOR
using System;
using System.Linq;
using Bindito.Core;
using Timberborn.CoreUI;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.GameFactionSystem;
using Timberborn.Localization;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.UILayoutSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.MapSetup {
  [Context("Game")]
  public sealed class MineralMapNoticeConfigurator : Configurator {
    protected override void Configure() => Bind<MineralMapNotice>().AsSingleton();
  }

  // Inspect the world after new-game placement, never modify an established save.
  // Empty sources still count: their native recovery timer makes them usable again.
  // Iron Teeth only (DeepFrontierFaction): the sources serve Iron Teeth buildings.
  internal sealed class MineralMapNotice : ILoadableSingleton, ISaveableSingleton, IUpdatableSingleton {
    private static readonly SingletonKey Key = new("DeepFrontier.MineralMapNotice");
    private static readonly PropertyKey<bool> ShownKey = new("Shown");
    private readonly ISpecService _specs;
    private readonly BuiltinMapSetup _setup;
    private readonly ISingletonLoader _loader;
    private readonly EntityRegistry _entities;
    private readonly TemplateNameMapper _templates;
    private readonly EventBus _events;
    private readonly DialogBoxShower _dialogs;
    private readonly ILoc _loc;
    private readonly FactionService _factions;
    private bool _shown, _ready, _checked;
    private int _frames;

    public MineralMapNotice(ISingletonLoader loader, EntityRegistry entities, TemplateNameMapper templates,
        EventBus events, DialogBoxShower dialogs, ILoc loc, ISpecService specs, BuiltinMapSetup setup, FactionService factions) {
      _loader=loader; _entities=entities; _templates=templates; _events=events; _dialogs=dialogs; _loc=loc;
      _specs=specs; _setup=setup; _factions=factions;
    }
    public void Load() {
      if(_loader.TryGetSingleton(Key,out var saved)) _shown=saved.Get(ShownKey);
      if(!_shown && DeepFrontierFaction.Applies(_factions)) _events.Register(this);
    }
    public void Save(ISingletonSaver saver) => saver.GetSingleton(Key).Set(ShownKey,_shown);
    [OnEvent]
    public void OnShowPrimaryUI(ShowPrimaryUIEvent _) { _ready=true; _events.Unregister(this); }
    public void UpdateSingleton() {
      if(_shown || _checked || !_ready || !_setup.Ready || ++_frames<2)return;
      _checked=true;
      var present=_entities.Entities.Where(e=>e.HasComponent<TemplateSpec>())
        .Select(e=>e.GetComponent<TemplateSpec>().TemplateName).ToHashSet();
      var missing=_specs.GetSingleSpec<BuiltinMapSetupSpec>().RequiredMineralTemplates
        .Where(id=>!present.Contains(id)).ToArray();
      if(missing.Length==0) { Debug.Log("[DeepFrontier MapSetup] Mineral availability: all six source types present"); return; }
      var names=missing.Select(id=> {
        if(!_templates.TryGetTemplate(id,out var template)) throw new InvalidOperationException("Missing mineral template "+id);
        return _loc.T(template.Blueprint.GetSpec<LabeledEntitySpec>().DisplayNameLocKey);
      });
      string message=_loc.T("DeepFrontier.Minerals.MissingSources",string.Join(", ",names));
      _dialogs.Create().SetMessage(message).Show();
      _shown=true;
      Debug.LogWarning("[DeepFrontier MapSetup] Missing mineral sources: "+string.Join(", ",missing)+"; one-time placement notice shown");
    }
  }
}
#endif
