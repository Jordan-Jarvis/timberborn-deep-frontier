using System;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BonusSystem;
using Timberborn.CharacterModelSystem;
using Timberborn.Characters;
using Timberborn.EntitySystem;
using Timberborn.NeedSystem;
using Timberborn.Persistence;
using Timberborn.Rendering;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.SuperBots {
  // In-place Reactor Bot upgrade, decorated on every bot (BotSpec). The bot
  // keeps its template, name and identity; this saved state decides which of
  // its needs are on and applies the buffs and the skin.
  //
  //   Ordinary: vanilla needs only (reactor and retrofit needs disabled).
  //   Queued:   the retrofit needs are enabled at 0. Native NeederRootBehavior
  //             (before WorkerRootBehavior) sends the bot to storage for each
  //             part, whose ConsumptionEffects fill its need; when all are
  //             full the bot becomes a Reactor Bot.
  //   Reactor:  replaced vanilla needs (Energy) disabled, reactor needs on.
  //             A bot the Bot Assembler finishes from the Reactor Bot recipe
  //             (ReactorBotAssembler) is born in this state, its reactor
  //             needs full, as a finished retrofit leaves it.
  //
  // Skin (ReactorBotSkin): neon-yellow glowing eyes and joint seams, and dark
  // plating while the plating need is favourable (the vanilla light body,
  // still glowing, while unplated), set on the body material through the native
  // CharacterMaterialModifier. A colour-named bot keeps its native CitizenTint
  // on top. The native illumination colour (MaterialColorer) is set to the
  // eye colour as vanilla BotIlluminationController sets the bot's; the
  // BotURP body material does not read it.
  //
  // Need switches follow native ContaminationNeedEnabler (ResetNeed then
  // DisableNeed in InitializeEntity); Need.Enabled is not saved, so they are
  // reapplied on every load. Need points are saved natively.
  internal sealed class ReactorBot : BaseComponent, IAwakableComponent, IInitializableEntity, IPersistentEntity {
    internal enum State { Ordinary, Queued, Reactor }

    private static readonly string CarryingCapacityBonusId="CarryingCapacity"; // native GoodCarrier bonus id
    private static readonly ComponentKey Key=new("DeepFrontier.ReactorBot");
    private static readonly PropertyKey<string> StateKey=new("State");

    private readonly ReactorBotSettings _settings;
    private readonly MaterialColorer _materialColorer;
    private readonly ReactorBotAssemblyLine _assembly;
    private readonly ReactorBotSkin _skin;
    private NeedManager _needs;
    private BonusManager _bonuses;
    private CharacterMaterialModifier _material;
    private CharacterAnimator _animator;
    private ReactorBotSkin.Textures _textures;
    private bool _buffed;

    public State Current { get; private set; }
    public bool IsReactor=>Current==State.Reactor;
    public bool IsPlated=>!IsReactor||_needs.NeedIsFavorable(Spec.PlatingNeedId);
    public float SpeedMultiplier=>IsReactor?Spec.SpeedMultiplier:1f;
    private FrontierReactorBotSettingsSpec Spec=>_settings.Spec;

    public ReactorBot(ReactorBotSettings settings, MaterialColorer materialColorer, ReactorBotAssemblyLine assembly, ReactorBotSkin skin) {
      _settings=settings;_materialColorer=materialColorer;_assembly=assembly;_skin=skin;
    }

    public void Awake() {
      _needs=GetComponent<NeedManager>();
      _bonuses=GetComponent<BonusManager>();
      _material=GetComponent<CharacterMaterialModifier>();
      _animator=GetComponent<CharacterAnimator>();
      if(!_needs||!_bonuses||!_material||!_animator)throw new InvalidOperationException($"{Name}: a Reactor Bot needs native NeedManager, BonusManager, CharacterMaterialModifier and CharacterAnimator");
      _needs.NeedChangedIsFavorable+=OnNeedChangedIsFavorable;
      _needs.NeedChangedCriticalState+=OnNeedChangedCriticalState;
    }

    // A newborn bot has no saved state; one born from the Reactor Bot recipe
    // starts as a Reactor Bot with its reactor needs reset to full. On load
    // the saved state and need points stand.
    public void InitializeEntity() {
      var assembled=_assembly.TakeBirth(this);
      if(assembled)Current=State.Reactor;
      ApplyNeeds(resetEnabled:assembled);
      if(IsReactor)ApplyUpgrade();
    }

    public void Queue() {
      if(Current!=State.Ordinary)throw new InvalidOperationException($"{Name}: only an ordinary bot can be queued for a retrofit ({Current})");
      Current=State.Queued;
      foreach(var id in Spec.RetrofitNeedIds) {
        _needs.ResetNeed(id);
        _needs.EnableNeed(id);
      }
    }

    public void Cancel() {
      if(Current!=State.Queued)throw new InvalidOperationException($"{Name}: no retrofit is queued ({Current})");
      Current=State.Ordinary;
      // Parts already fitted are lost with the cancelled retrofit.
      foreach(var id in Spec.RetrofitNeedIds)Disable(id);
    }

    // Wear multiplier the deterioration patch applies on top of native and
    // workplace wear (1 unless the plating need is exhausted).
    public float PlatingWearMultiplier=>IsPlated?1f:Spec.UnplatedWearMultiplier;
    public float LifespanMultiplier=>IsReactor?Spec.LifespanMultiplier:1f;

    // Dark plating while plated, the vanilla body while unplated (on upgrade
    // and when the plating need changes); the glow stays either way.
    private void ApplyPlating()=>_material.SetTexture(ReactorBotSkin.BaseMapId,IsPlated?_textures.Plated:_textures.Unplated);

    private void OnNeedChangedIsFavorable(object sender, NeedChangedIsFavorableEventArgs e) {
      if(IsReactor&&e.NeedSpec.Id==Spec.PlatingNeedId) { ApplyPlating(); return; }
      if(Current!=State.Queued||!Spec.RetrofitNeedIds.Contains(e.NeedSpec.Id))return;
      foreach(var id in Spec.RetrofitNeedIds)if(!_needs.NeedIsFavorable(id))return;
      Current=State.Reactor;
      ApplyNeeds(resetEnabled:true);
      ApplyUpgrade();
    }

    // The vanilla template's CriticalNeedStateAnimationSpec drives this bool
    // from Energy only; mirror the charge need onto it.
    private void OnNeedChangedCriticalState(object sender, NeedChangedCriticalStateEventArgs e) {
      if(IsReactor&&e.NeedSpec.Id==Spec.ChargeNeedId)_animator.SetBool(Spec.NoChargeAnimation,e.IsInCriticalState);
    }

    // resetEnabled: freshly enabled reactor needs start full (on upgrade);
    // on load they keep their saved points.
    private void ApplyNeeds(bool resetEnabled) {
      foreach(var id in Spec.ReactorNeedIds) {
        if(!IsReactor) { Disable(id); continue; }
        if(resetEnabled)_needs.ResetNeed(id);
        _needs.EnableNeed(id);
      }
      foreach(var id in Spec.ReplacedNeedIds) {
        if(IsReactor)Disable(id);
        else _needs.EnableNeed(id);
      }
      foreach(var id in Spec.RetrofitNeedIds) {
        if(Current==State.Queued)_needs.EnableNeed(id);
        else Disable(id);
      }
    }

    private void Disable(string id) {
      if(!_needs.HasNeed(id))throw new InvalidOperationException($"{Name}: bot has no need {id}; check the Iron Teeth NeedCollection");
      _needs.ResetNeed(id);
      _needs.DisableNeed(id);
    }

    private void ApplyUpgrade() {
      if(!_buffed) {
        _bonuses.AddBonus(CarryingCapacityBonusId,Spec.CarryingCapacityBonus);
        _buffed=true;
      }
      _materialColorer.SetLightingColor(this,_settings.IlluminationColor);
      _materialColorer.EnableLighting(this);
      if(_textures==null) {
        // The body renderer native CharacterMaterialModifier edits (its Awake takes the same one) and its mesh.
        var body=GetComponentInChildren<Renderer>(includeInactive:true);
        var filter=body.GetComponent<MeshFilter>();
        if(!filter)throw new InvalidOperationException($"{Name}: the bot body renderer {body.name} has no MeshFilter");
        _textures=_skin.For(body.sharedMaterial,filter.sharedMesh);
        _material.SetTexture(ReactorBotSkin.EmissionMapId,_textures.Emission);
      }
      ApplyPlating();
    }

    public void Save(IEntitySaver saver) {
      if(Current==State.Ordinary)return;
      saver.GetComponent(Key).Set(StateKey,Current.ToString());
    }

    public void Load(IEntityLoader loader) {
      if(!loader.TryGetComponent(Key,out var data))return; // ordinary, or saved before Reactor Bots existed
      var saved=data.Get(StateKey);
      if(!Enum.TryParse(saved,out State state)||state==State.Ordinary)throw new InvalidOperationException($"{Name}: invalid saved Reactor Bot state {saved}");
      Current=state;
    }
  }
}
