using System;
using System.Collections.Generic;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Bots;
using Timberborn.Buildings;
using Timberborn.DuplicationSystem;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Illumination;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TemplateSystem;
using Timberborn.WorkerTypesUI;
using Timberborn.WorkSystem;
using Timberborn.WorkSystemUI;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts.SuperBots {
  // Reactor Bot workplaces (user 2026-11-02, Option 1 of docs/worker-types-study.md).
  //
  // The worker-type toggle reads Beaver | Bot | Reactor Bot and the three are
  // exclusive. A workplace set to Reactor Bots keeps the native worker type
  // Bot (so native assignment checks, statistics, bot outfits, the empty bot
  // slot icons and the saved type stay native) plus this saved flag:
  //   - ReactorBotStaffing fills it with Reactor Bots of its district;
  //   - the native district assigner skips it (PriorityOrderedWorkplaces
  //     postfixes, ReactorBotWorkplacePatches) and never holds Reactor Bots as
  //     unemployed (UnemployedWorkers prefix), so Bot workplaces get ordinary
  //     bots only;
  //   - every workplace can take it, beaver-only and specialist-only ones
  //     included: there the native type is set to Bot without the native
  //     allowed/unlocked checks (NativeWorkerTypeAccess), and turning the mode
  //     off puts the workplace back to a type it may natively have.
  // Saves: the native type is saved as Bot; this flag under its own key.
  // Without Deep Frontier the workplace loads as a Bot workplace where bots are
  // natively allowed and unlocked, otherwise as its default type.

  // Written by tools/reactor_bot_workplace_content.mjs as
  // Data/Configurations/DeepFrontierReactorBotWorkplaces.blueprint.json (the
  // window colour id, as native BotColorsSpec names the bot blue, and the
  // unlock rule).
  internal record FrontierReactorBotWorkplacesSpec : ComponentSpec {
    [Serialize] public string WorkplaceColorId { get; init; }
    // Reactor Bot unlock = BotUnlockMultiplier x the template's native Bot unlock cost.
    [Serialize] public int BotUnlockMultiplier { get; init; }
    // Without a native Bot unlock cost: BuildingSpec.ScienceCost + MissingBotUnlockAddend in its place.
    [Serialize] public int MissingBotUnlockAddend { get; init; }
  }

  internal sealed class ReactorBotWorkplaceSettings : ILoadableSingleton {
    private readonly ISpecService _specs;
    private readonly IlluminationService _illumination;

    public FrontierReactorBotWorkplacesSpec Spec { get; private set; }
    public Color WorkplaceColor { get; private set; }

    public ReactorBotWorkplaceSettings(ISpecService specs, IlluminationService illumination) {
      _specs=specs;_illumination=illumination;
    }

    public void Load() {
      Spec=_specs.GetSingleSpec<FrontierReactorBotWorkplacesSpec>();
      if(!(Spec.BotUnlockMultiplier>=1&&Spec.MissingBotUnlockAddend>0))
        throw new InvalidOperationException("Reactor Bot workplaces: invalid unlock rule; regenerate tools/reactor_bot_workplace_content.mjs");
      // Native FindColorById only warns on an unknown id; require the generated colour.
      if(!_specs.GetSpecs<IlluminationColorSpec>().Any(c=>c.Id==Spec.WorkplaceColorId))
        throw new InvalidOperationException($"Reactor Bot workplaces: illumination colour {Spec.WorkplaceColorId} is not generated");
      WorkplaceColor=_illumination.FindColorById(Spec.WorkplaceColorId);
    }

    // The template's native Bot unlock cost (WorkerTypeUnlockCosts), 0 without one.
    public static int BotUnlockCost(WorkplaceSpec workplace) {
      foreach(var cost in workplace.WorkerTypeUnlockCosts)
        if(cost.WorkerType==WorkerTypeHelper.BotWorkerType)return cost.ScienceCost;
      return 0;
    }

    // A workplace without a BuildingSpec has no science unlock of its own: 0.
    public int ReactorUnlockCost(WorkplaceSpec workplace, BuildingSpec building) {
      var bot=BotUnlockCost(workplace);
      var basis=bot>0?bot:(building!=null?building.ScienceCost:0)+Spec.MissingBotUnlockAddend;
      return Spec.BotUnlockMultiplier*basis;
    }
  }

  // Workplaces set to Reactor Bots (any state), for the staffing pass and the
  // native-assigner postfixes (Current: Harmony postfixes are static).
  internal sealed class ReactorBotWorkplaceRegistry : ILoadableSingleton, IUnloadableSingleton {
    public static ReactorBotWorkplaceRegistry Current { get; private set; }
    private readonly HashSet<Workplace> _workplaces=new();
    private readonly List<ReactorBotWorkplace> _all=new();

    public IReadOnlyList<ReactorBotWorkplace> All=>_all;
    public bool IsReactor(Workplace workplace)=>_workplaces.Contains(workplace);

    public void Load() {Current=this;}
    public void Unload() {if(Current==this)Current=null;}

    public void Add(ReactorBotWorkplace workplace) {
      if(_workplaces.Add(workplace.Workplace))_all.Add(workplace);
    }

    public void Remove(ReactorBotWorkplace workplace) {
      if(_workplaces.Remove(workplace.Workplace))_all.Remove(workplace);
    }
  }

  // Decorated on every WorkplaceWorkerType (every workplace).
  internal sealed class ReactorBotWorkplace : BaseComponent, IAwakableComponent, IInitializableEntity, IPersistentEntity, IDeletableEntity,
    IDuplicable<ReactorBotWorkplace>, IDuplicable {
    private static readonly ComponentKey Key=new("DeepFrontier.ReactorBotWorkplace");
    private static readonly PropertyKey<bool> EnabledKey=new("Enabled");

    private readonly ReactorBotWorkplaceRegistry _registry;
    private readonly ReactorBotWorkplaceUnlocks _unlocks;
    private readonly WorkplaceUnlockingService _nativeUnlocks;

    public WorkplaceWorkerType WorkerType { get; private set; }
    public Workplace Workplace { get; private set; }
    public WorkplacePriority Priority { get; private set; }
    public DistrictBuilding DistrictBuilding { get; private set; }
    public WorkplaceSpec WorkplaceSpec { get; private set; }
    public string TemplateName { get; private set; }
    public bool ReactorMode { get; private set; }
    public bool Unlocked=>_unlocks.Unlocked(this);
    public event EventHandler ModeChanged;

    public ReactorBotWorkplace(ReactorBotWorkplaceRegistry registry, ReactorBotWorkplaceUnlocks unlocks, WorkplaceUnlockingService nativeUnlocks) {
      _registry=registry;_unlocks=unlocks;_nativeUnlocks=nativeUnlocks;
    }

    public void Awake() {
      WorkerType=GetComponent<WorkplaceWorkerType>();
      Workplace=GetComponent<Workplace>();
      Priority=GetComponent<WorkplacePriority>();
      DistrictBuilding=GetComponent<DistrictBuilding>();
      WorkplaceSpec=GetComponent<WorkplaceSpec>();
      var template=GetComponent<TemplateSpec>();
      if(!WorkerType||!Workplace||!Priority||!DistrictBuilding||WorkplaceSpec==null||template==null)
        throw new InvalidOperationException($"{Name}: a Reactor Bot workplace needs the native workplace components");
      TemplateName=template.TemplateName;
    }

    // After loading (native state events are subscribed once the entity is
    // loaded; native Load sets the type without raising WorkerTypeChanged).
    public void InitializeEntity() {
      WorkerType.WorkerTypeChanged+=OnWorkerTypeChanged;
    }

    // Native Bot type (forced where natively disallowed or locked), flag on,
    // and every worker released so only Reactor Bots are hired.
    public void Enable() {
      if(ReactorMode)return;
      ReactorMode=true;
      _registry.Add(this);
      NativeWorkerTypeAccess.SetBot(WorkerType,Workplace);
      Workplace.UnassignAllWorkers();
      ModeChanged?.Invoke(this,EventArgs.Empty);
    }

    // Flag off and the Reactor Bots released. A Bot type the workplace may not
    // natively have (forced by Enable) goes back to the default type.
    public void Disable() {
      if(!ReactorMode)return;
      ReactorMode=false;
      _registry.Remove(this);
      Workplace.UnassignAllWorkers();
      if(WorkerType.WorkerType==WorkerTypeHelper.BotWorkerType&&!NativeBotAvailable)
        WorkerType.SetWorkerType(WorkplaceSpec.DefaultWorkerType);
      ModeChanged?.Invoke(this,EventArgs.Empty);
    }

    // Native WorkplaceWorkerType.IsWorkerTypeAllowed and IsWorkerTypeUnlocked for Bot.
    public bool NativeBeaverAllowed=>!WorkplaceSpec.DisallowOtherWorkerTypes||WorkplaceSpec.DefaultWorkerType==WorkerTypeHelper.BeaverWorkerType;
    public bool NativeBotAllowed=>!WorkplaceSpec.DisallowOtherWorkerTypes||WorkplaceSpec.DefaultWorkerType==WorkerTypeHelper.BotWorkerType;
    public bool NativeBotAvailable=>NativeBotAllowed&&_nativeUnlocks.Unlocked(new UnlockableWorkerType(TemplateName,WorkerTypeHelper.BotWorkerType));

    // Any other path that changes the native type (Beaver button, copied
    // settings, other mods) ends the Reactor Bot mode; native SetWorkerType
    // has already released the workers.
    private void OnWorkerTypeChanged(object sender, WorkerTypeChangedEventArgs e) {
      if(ReactorMode&&e.CurrentWorkerType!=WorkerTypeHelper.BotWorkerType)Disable();
    }

    public void DeleteEntity() {_registry.Remove(this);}

    public void Save(IEntitySaver entitySaver) {
      if(ReactorMode)entitySaver.GetComponent(Key).Set(EnabledKey,true);
    }

    // As native WorkplaceWorkerType.Load sets the saved type without an event:
    // the Bot type is set here directly, before Worker.InitializeEntity
    // re-employs the saved crew through Workplace.AssignWorker.
    public void Load(IEntityLoader entityLoader) {
      if(!entityLoader.TryGetComponent(Key,out var data))return; // not set to Reactor Bots, or saved before they existed
      if(!data.Get(EnabledKey))throw new InvalidOperationException($"{Name}: invalid saved Reactor Bot workplace");
      ReactorMode=true;
      _registry.Add(this);
      NativeWorkerTypeAccess.LoadBot(WorkerType);
    }

    // Native Duplicator runs WorkplaceWorkerType.DuplicateFrom first (component order).
    public void DuplicateFrom(ReactorBotWorkplace source) {
      if(!source.ReactorMode)Disable();
      else if(Unlocked)Enable();
    }
  }

  // Decorated on every DistrictDefaultWorkerType (district centres): the
  // Reactor Bot default for new workplaces. The native default is set to Bot
  // with it, so without Deep Frontier the district defaults to bots.
  internal sealed class ReactorBotDistrictDefault : BaseComponent, IAwakableComponent, IPersistentEntity,
    IDuplicable<ReactorBotDistrictDefault>, IDuplicable {
    private static readonly ComponentKey Key=new("DeepFrontier.ReactorBotDistrictDefault");
    private static readonly PropertyKey<bool> EnabledKey=new("Enabled");

    private DistrictDefaultWorkerType _native;
    private bool _enabled;

    // Only together with the native Bot default (another path may change it).
    public bool ReactorMode=>_enabled&&_native.WorkerType==WorkerTypeHelper.BotWorkerType;

    public void Awake() {
      _native=GetComponent<DistrictDefaultWorkerType>();
      if(!_native)throw new InvalidOperationException($"{Name}: a Reactor Bot district default needs the native DistrictDefaultWorkerType");
    }

    public void Set(bool enabled) {
      _enabled=enabled;
      if(enabled)_native.SetWorkerType(WorkerTypeHelper.BotWorkerType);
    }

    public void Save(IEntitySaver entitySaver) {
      if(ReactorMode)entitySaver.GetComponent(Key).Set(EnabledKey,true);
    }

    public void Load(IEntityLoader entityLoader) {
      if(!entityLoader.TryGetComponent(Key,out var data))return;
      if(!data.Get(EnabledKey))throw new InvalidOperationException($"{Name}: invalid saved Reactor Bot district default");
      _enabled=true;
    }

    public void DuplicateFrom(ReactorBotDistrictDefault source) {_enabled=source._enabled;}
  }

  // Private members of native WorkplaceWorkerType (1.1.2.8) the mode needs,
  // resolved once; ReactorBotWorkplacePatches.Verify touches them at mod start
  // so a changed game fails there.
  internal static class NativeWorkerTypeAccess {
    private const BindingFlags Instance=BindingFlags.Instance|BindingFlags.NonPublic|BindingFlags.Public;
    private static readonly MethodInfo Setter=typeof(WorkplaceWorkerType).GetProperty(nameof(WorkplaceWorkerType.WorkerType),Instance)?.GetSetMethod(true)
      ??throw new InvalidOperationException("Reactor Bot workplaces: WorkplaceWorkerType.WorkerType has no setter; recheck the 1.1.2.8 contract");
    private static readonly FieldInfo WasSet=Field("_wasSet",typeof(bool));
    // The backing field of the field-like event WorkerTypeChanged.
    private static readonly FieldInfo Changed=Field(nameof(WorkplaceWorkerType.WorkerTypeChanged),typeof(EventHandler<WorkerTypeChangedEventArgs>));

    private static FieldInfo Field(string name, Type type) {
      var field=typeof(WorkplaceWorkerType).GetField(name,Instance);
      if(field==null||field.FieldType!=type)
        throw new InvalidOperationException($"Reactor Bot workplaces: WorkplaceWorkerType.{name} ({type.Name}) not found; recheck the 1.1.2.8 contract");
      return field;
    }

    public static void Verify() {
      if(Setter==null||WasSet==null||Changed==null)throw new InvalidOperationException("Reactor Bot workplaces: WorkplaceWorkerType members missing");
    }

    // Native SetWorkerType(Bot) where bots are natively allowed and unlocked;
    // elsewhere the same steps without those checks: release the workers, set
    // the type, raise WorkerTypeChanged, mark the type as chosen.
    public static void SetBot(WorkplaceWorkerType workerType, Workplace workplace) {
      var bot=WorkerTypeHelper.BotWorkerType;
      workerType.SetWorkerType(bot);
      if(workerType.WorkerType!=bot) {
        workplace.UnassignAllWorkers();
        var previous=workerType.WorkerType;
        Setter.Invoke(workerType,new object[] {bot});
        ((EventHandler<WorkerTypeChangedEventArgs>)Changed.GetValue(workerType))?.Invoke(workerType,new WorkerTypeChangedEventArgs(previous,bot));
      }
      WasSet.SetValue(workerType,true);
    }

    // Loading: the type only, as native Load does.
    public static void LoadBot(WorkplaceWorkerType workerType)=>Setter.Invoke(workerType,new object[] {WorkerTypeHelper.BotWorkerType});
  }

  // Discovered like the mod's other per-feature configurators.
  [Context("Game")]
  public sealed class ReactorBotWorkplaceConfigurator : Configurator {
    protected override void Configure() {
      Bind<ReactorBotWorkplaceSettings>().AsSingleton();
      Bind<ReactorBotWorkplaceRegistry>().AsSingleton();
      Bind<ReactorBotWorkplaceUnlocks>().AsSingleton();
      Bind<ReactorBotWorkplaceUi>().AsSingleton();
      Bind<ReactorBotStaffing>().AsSingleton();
      Bind<ReactorBotWorkplace>().AsTransient();
      Bind<ReactorBotDistrictDefault>().AsTransient();
      Bind<ReactorBotWorker>().AsTransient();
      Bind<ReactorBotWorkplaceLight>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<WorkplaceWorkerType,ReactorBotWorkplace>();
      builder.AddDecorator<DistrictDefaultWorkerType,ReactorBotDistrictDefault>();
      builder.AddDecorator<BotSpec,ReactorBotWorker>();
      // Beside native WorkerTypeIlluminator, on the same subject.
      builder.AddDecorator<WorkplaceIlluminator,ReactorBotWorkplaceLight>();
      return builder.Build();
    }
  }
}
