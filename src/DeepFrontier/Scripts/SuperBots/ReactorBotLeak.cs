using System;
using System.Linq;
using Bindito.Core;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Characters;
using Timberborn.EnterableSystem;
using Timberborn.GameFactionSystem;
using Timberborn.Navigation;
using Timberborn.NeedSpecs;
using Timberborn.NeedSystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.SuperBots {
  // Reactor Bot leaks (user 2026-11-02: "If they overheat or go unmaintained
  // for too long then they can leak radioactive water on the ground").
  //
  // Conditions, read from native need states every tick:
  //   overheated:   the coolant need is in its native critical state (points at
  //                 0: the "Reactor Bot is overheating and will leak radiation" status) for longer than
  //                 OverheatHours;
  //   unmaintained: the plating need is exhausted (ReactorBot.IsPlated false:
  //                 the panel's "No plating" line) for longer than
  //                 UnmaintainedHours.
  // Lifespan wear is not a condition: every bot ages however well it is kept,
  // and an unplated Reactor Bot already wears UnplatedWearMultiplier times
  // faster. A condition's hours restart from 0 once it is fixed.
  //
  // While either has lasted past its threshold the bot leaks: one pulse at
  // once, then one every PulseHours, of VolumePerHour x PulseHours radioactive
  // water through the radiation system's own add path
  // (IRadiationService.AddRadioactiveWater), so pumps, barrels, beaver dose,
  // soil, plants, decay and the Sludge Recovery Pump treat it as any other
  // radioactive water. It stops as soon as both conditions are fixed. No
  // status or notification of its own: the native need statuses and the
  // yellow water and ground are what the player sees.
  //
  // Where: the bot's own cell (the cell RadiationExposure samples for beavers),
  // or, while it is hidden inside a building, that building's doorstep (the
  // building's blocks keep water out, so the leak runs out of the door). The
  // radiation system's TryFindOpenCell then picks the open fluid column at
  // that cell, whose floor (the ground, a platform or roof top, or the water
  // surface below the bot) takes the water natively, or the lowest open cell
  // above it if the cell itself is closed to water, the same rule waste leaks
  // and meltdowns use. A column closed all the way up takes nothing.
  //
  // Saved: the hours each condition has lasted and the time to the next pulse.
  internal record FrontierReactorBotLeakSpec : ComponentSpec {
    // The critical need whose critical state is "overheating".
    [Serialize] public string CoolantNeedId { get; init; }
    [Serialize] public float OverheatHours { get; init; }
    [Serialize] public float UnmaintainedHours { get; init; }
    // Radioactive volume (native water units; a RadioactiveSludge good is 0.2) per hour of leaking.
    [Serialize] public float VolumePerHour { get; init; }
    [Serialize] public float PulseHours { get; init; }
  }

  internal sealed class ReactorBotLeakSettings : ILoadableSingleton, IPostLoadableSingleton {
    private readonly ISpecService _specs;
    private readonly FactionNeedService _needs;
    private readonly ReactorBotSettings _bots;

    public FrontierReactorBotLeakSpec Spec { get; private set; }

    public ReactorBotLeakSettings(ISpecService specs, FactionNeedService needs, ReactorBotSettings bots) {
      _specs=specs;_needs=needs;_bots=bots;
    }

    public void Load() {
      Spec=_specs.GetSingleSpec<FrontierReactorBotLeakSpec>();
      if(string.IsNullOrEmpty(Spec.CoolantNeedId)||!Positive(Spec.OverheatHours)||!Positive(Spec.UnmaintainedHours)
         ||!Positive(Spec.VolumePerHour)||!Positive(Spec.PulseHours))
        throw new InvalidOperationException("Reactor bots: invalid leak values in the settings; regenerate tools/super_bot_content.mjs");
    }

    // Faction needs and the Reactor Bot settings are loaded by now.
    public void PostLoad() {
      if(!_bots.AppliesToFaction)return;
      if(!_bots.Spec.ReactorNeedIds.Contains(Spec.CoolantNeedId))
        throw new InvalidOperationException($"Reactor bots: leak coolant need {Spec.CoolantNeedId} is not a reactor need");
      var coolant=_needs.GetBotNeeds().SingleOrDefault(n=>n.Id==Spec.CoolantNeedId);
      if(coolant==null||!coolant.HasSpec<CriticalNeedSpec>())
        throw new InvalidOperationException($"Reactor bots: leak coolant need {Spec.CoolantNeedId} must be a critical Bot need (its critical state is the overheating status)");
    }

    private static bool Positive(float value)=>value>0f&&!float.IsInfinity(value);
  }

  internal sealed class ReactorBotLeak : TickableComponent, IAwakableComponent, IPersistentEntity {
    private static readonly ComponentKey Key=new("DeepFrontier.ReactorBotLeak");
    private static readonly PropertyKey<float> OverheatedHoursKey=new("OverheatedHours");
    private static readonly PropertyKey<float> UnplatedHoursKey=new("UnplatedHours");
    private static readonly PropertyKey<float> NextPulseHoursKey=new("NextPulseHours");

    private readonly ReactorBotLeakSettings _settings;
    private readonly IRadiationService _radiation;
    private readonly IDayNightCycle _cycle;
    private ReactorBot _bot;
    private NeedManager _needs;
    private Enterer _enterer;
    private Character _character;
    private float _overheatedHours, _unplatedHours, _nextPulseHours;

    public ReactorBotLeak(ReactorBotLeakSettings settings, IRadiationService radiation, IDayNightCycle cycle) {
      _settings=settings;_radiation=radiation;_cycle=cycle;
    }

    private FrontierReactorBotLeakSpec Spec=>_settings.Spec;
    public bool Leaking=>_overheatedHours>Spec.OverheatHours||_unplatedHours>Spec.UnmaintainedHours;

    public void Awake() {
      _bot=GetComponent<ReactorBot>();
      _needs=GetComponent<NeedManager>();
      _enterer=GetComponent<Enterer>();
      _character=GetComponent<Character>();
      if(!_bot||!_needs||!_enterer||!_character)throw new InvalidOperationException($"{Name}: a Reactor Bot leak needs ReactorBot and native NeedManager, Enterer and Character");
    }

    public override void Tick() {
      if(!_bot.IsReactor||!_character.Alive) { _overheatedHours=_unplatedHours=_nextPulseHours=0f; return; }
      float hours=_cycle.FixedDeltaTimeInHours;
      _overheatedHours=_needs.NeedIsInCriticalState(Spec.CoolantNeedId)?_overheatedHours+hours:0f;
      _unplatedHours=_bot.IsPlated?0f:_unplatedHours+hours;
      if(!Leaking) { _nextPulseHours=0f; return; }
      _nextPulseHours-=hours;
      if(_nextPulseHours>0f)return;
      _nextPulseHours+=Spec.PulseHours;
      var at=LeakOrigin();
      if(_radiation.TryFindOpenCell(new Vector2Int(at.x,at.y),at.z,out var cell))
        _radiation.AddRadioactiveWater(cell,Spec.VolumePerHour*Spec.PulseHours);
    }

    private Vector3Int LeakOrigin() {
      var building=_enterer.CurrentBuilding;
      if(building) {
        var block=building.GetComponent<BlockObject>();
        if(block.HasEntrance)return block.PositionedEntrance.DoorstepCoordinates;
      }
      return NavigationCoordinateSystem.WorldToGridInt(Transform.position);
    }

    public void Save(IEntitySaver entitySaver) {
      if(_overheatedHours==0f&&_unplatedHours==0f&&_nextPulseHours==0f)return;
      var saver=entitySaver.GetComponent(Key);
      saver.Set(OverheatedHoursKey,_overheatedHours);
      saver.Set(UnplatedHoursKey,_unplatedHours);
      saver.Set(NextPulseHoursKey,_nextPulseHours);
    }

    public void Load(IEntityLoader entityLoader) {
      if(!entityLoader.TryGetComponent(Key,out var loader))return; // not overheated or unplated, or saved before leaks existed
      _overheatedHours=loader.Get(OverheatedHoursKey);
      _unplatedHours=loader.Get(UnplatedHoursKey);
      _nextPulseHours=loader.Get(NextPulseHoursKey);
      foreach(var value in new[] {_overheatedHours,_unplatedHours,_nextPulseHours})
        if(!(value>=0f)||float.IsInfinity(value))throw new InvalidOperationException($"{Name}: saved Reactor Bot leak state is invalid");
    }
  }

  // Its own configurator: every bot's ReactorBot (ReactorBotConfigurator) gets the leak.
  [Context("Game")]
  public sealed class ReactorBotLeakConfigurator : Configurator {
    protected override void Configure() {
      Bind<ReactorBotLeakSettings>().AsSingleton();
      Bind<ReactorBotLeak>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<ReactorBot,ReactorBotLeak>();
      return builder.Build();
    }
  }
}
