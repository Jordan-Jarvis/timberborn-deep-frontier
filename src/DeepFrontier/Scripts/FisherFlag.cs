using System;
using System.Collections.Generic;
using Bindito.Core;
using DeepFrontier.Scripts.Radiation;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlueprintSystem;
using Timberborn.BuildingRange;
using Timberborn.Buildings;
using Timberborn.BuildingsNavigation;
using Timberborn.Carrying;
using Timberborn.CharacterModelSystem;
using Timberborn.Emptying;
using Timberborn.Goods;
using Timberborn.Hauling;
using Timberborn.InventorySystem;
using Timberborn.LaborSystem;
using Timberborn.MapStateSystem;
using Timberborn.Navigation;
using Timberborn.Persistence;
using Timberborn.SimpleOutputBuildings;
using Timberborn.SimpleOutputBuildingsUI;
using Timberborn.TemplateInstantiation;
using Timberborn.WalkingSystem;
using Timberborn.WaterSystem;
using Timberborn.WorkSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Fisher Flag (2026-11-02): an independent source of fresh fish. Players
  // could not find the old "Catch fish" mode hidden in the Gatherer Flag panel,
  // so fishing is its own small flag beside the Gatherer Flag, built and
  // staffed the same way. The fisher walks to a dry bank in the flag's native
  // terrain range, faces clean water that is deep enough, and catches one
  // fresh fish per CatchHours of work; haulers take the catch from the flag's
  // native output inventory.
  internal record FisherFlagSpec : ComponentSpec {
    [Serialize] public string GoodId {get;init;}
    [Serialize] public float CatchHours {get;init;}
    [Serialize] public float MinimumDepth {get;init;}
    [Serialize] public float MaximumContamination {get;init;}
    [Serialize] public float MaximumReachDown {get;init;}
  }

  // The shore rule and the catch inventory. The native Workplace, BuildingTerrainRange,
  // SimpleOutputInventory, hauling and emptying stay as on the Gatherer Flag.
  internal sealed class FisherFlag : BaseComponent,IAwakableComponent,IAllowedGoodProvider {
    private readonly IThreadSafeWaterMap _water;
    private readonly MapSize _map;
    private readonly IRadiationService _radiation;
    private BuildingTerrainRange _range;
    private FisherFlagSpec _spec;
    // SimpleOutputInventoryInitializer asks for the allowed goods before Awake.
    public FisherFlagSpec Spec => _spec ??= GetComponent<FisherFlagSpec>();
    public Inventory Inventory {get;private set;}
    public int CaughtThisSession {get;private set;}
    public FisherFlag(IThreadSafeWaterMap water,MapSize map,IRadiationService radiation) {_water=water;_map=map;_radiation=radiation;}
    public void Awake() {
      if(Spec.GoodId!="FreshFish" || Spec.CatchHours<=0 || Spec.MinimumDepth<=0 || Spec.MaximumContamination<0 || Spec.MaximumReachDown<=0)
        throw new InvalidOperationException("Invalid authored Fisher Flag contract");
      Inventory=GetComponent<SimpleOutputInventory>().Inventory;
      _range=GetComponent<BuildingTerrainRange>();
    }
    public IEnumerable<string> GetAllowedGoods() {yield return Spec.GoodId;}
    private bool InMap(Vector3Int c) {var size=_map.TotalSize;return c.x>=0&&c.y>=0&&c.z>=0&&c.x<size.x&&c.y<size.y&&c.z<size.z;}
    // A dry bank cell in range beside water one layer down: clean (badwater share at most
    // MaximumContamination, no detectable radiation, the pumps' rule), at least MinimumDepth
    // deep, its surface between MaximumReachDown below the bank and 0.1 above it.
    public bool Suitable(Vector3Int bank,Vector3Int water) {
      if(!InMap(bank)||!InMap(water)||!_range.GetRange().Contains(bank)||_water.CellIsUnderwater(bank))return false;
      if(_water.WaterDepth(water)<Spec.MinimumDepth||_water.ColumnContamination(water)>Spec.MaximumContamination)return false;
      if(_radiation.IsColumnContaminated(water))return false;
      var height=_water.WaterHeightOrFloor(water);
      return height>=bank.z-Spec.MaximumReachDown&&height<=bank.z+.10f;
    }
    public bool TryFindSpot(Vector3 origin,out Vector3Int bank,out Vector3Int water) {
      bank=water=default;bool found=false;float best=float.PositiveInfinity;
      foreach(var cell in _range.GetRange()) {
        foreach(var offset in Neighbours) {
          var probe=cell+offset+new Vector3Int(0,0,-1);
          if(!Suitable(cell,probe))continue;
          float distance=(Position(cell,probe)-origin).sqrMagnitude;
          if(distance<best) {found=true;best=distance;bank=cell;water=probe;}
        }
      }
      return found;
    }
    private static readonly Vector3Int[] Neighbours={Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down};
    public static Vector3 Position(Vector3Int bank,Vector3Int water) => NavigationCoordinateSystem.GridToWorld(bank)+new Vector3(water.x-bank.x,0,water.y-bank.y)*.23f;
    public bool CanWork(Worker worker) => Inventory.Enabled&&GetComponent<BlockableObject>().IsUnblocked
      &&!GetComponent<PausableBuilding>().Paused&&worker.Workplace==GetComponent<Workplace>()&&worker.GetComponent<WorkerWorkingHours>().AreWorkingHours;
    public void RecordCatch() {CaughtThisSession++;}
  }

  // The flag's job, in the native workplace behavior order of the Gatherer Flag
  // (GatheringConfigurator): remove unwanted stock, fish, empty output, labor, wait.
  // With no suitable bank in range (dry, too shallow, badwater, radiation, too far
  // below the bank) the worker gets the native "Nothing to do in range" status, the
  // NothingToDoInRangeStatus that every Workplace carries and that the Gatherer
  // Flag's YieldStatus switches the same way.
  internal sealed class FisherWorkplaceBehavior : WorkplaceBehavior,IAwakableComponent {
    private FisherFlag _flag;
    private NothingToDoInRangeStatus _nothingToDo;
    private Vector3Int _bank,_waterCell;
    private bool _hasSpot;
    public void Awake() {_flag=GetComponent<FisherFlag>();_nothingToDo=GetComponent<NothingToDoInRangeStatus>();}
    public override Decision Decide(BehaviorAgent agent) {
      var worker=agent.GetComponent<Worker>();
      if(!_flag.CanWork(worker)||agent.GetComponent<GoodCarrier>().IsCarrying)return Decision.ReleaseNow();
      if(_flag.Inventory.UnreservedCapacity(_flag.Spec.GoodId)<1)return Decision.ReleaseNow();
      if(!_hasSpot||!_flag.Suitable(_bank,_waterCell))_hasSpot=_flag.TryFindSpot(agent.Transform.position,out _bank,out _waterCell);
      if(!_hasSpot) {_nothingToDo.ActivateStatus();return Decision.ReleaseNow();}
      _nothingToDo.DeactivateStatus();
      var walk=agent.GetComponent<WalkToPositionExecutor>();
      switch(walk.Launch(FisherFlag.Position(_bank,_waterCell))) {
        case ExecutorStatus.Running:return Decision.ReturnWhenFinished(walk);
        case ExecutorStatus.Failure:_hasSpot=false;return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:
          var catchFish=agent.GetComponent<FisherCatchExecutor>();catchFish.Launch(_flag,_bank,_waterCell);return Decision.ReleaseWhenFinished(catchFish);
        default:throw new ArgumentOutOfRangeException();
      }
    }
  }

  internal sealed class FisherCatchExecutor : BaseComponent,IExecutor {
    private static readonly ComponentKey Key=new("DeepFrontierFisherCatch");
    private static readonly PropertyKey<FisherFlag> FlagKey=new("Flag");
    private static readonly PropertyKey<Vector3Int> BankKey=new("Bank"),WaterKey=new("Water");
    private static readonly PropertyKey<float> HoursKey=new("RemainingHours");
    private readonly ReferenceSerializer _references;
    private FisherFlag _flag;
    private Vector3Int _bank,_water;
    private float _remaining;
    public float RemainingHours => _remaining;
    public Vector3Int WaterCell => _water;
    public FisherCatchExecutor(ReferenceSerializer references) {_references=references;}
    public void Launch(FisherFlag flag,Vector3Int bank,Vector3Int water) {
      _flag=flag;_bank=bank;_water=water;_remaining=flag.Spec.CatchHours;
      GetComponent<CharacterModel>().LookToward(NavigationCoordinateSystem.GridToWorld(water));
      GetComponent<CharacterAnimator>().SetBool("Working",true);
    }
    private ExecutorStatus Finish(ExecutorStatus result) {GetComponent<CharacterAnimator>().SetBool("Working",false);return result;}
    public ExecutorStatus Tick(float hours) {
      var worker=GetComponent<Worker>();var carrier=GetComponent<GoodCarrier>();
      if(!_flag||!_flag.CanWork(worker)||!_flag.Suitable(_bank,_water)||carrier.IsCarrying
        ||Vector3.Distance(Transform.position,FisherFlag.Position(_bank,_water))>.3f)return Finish(ExecutorStatus.Failure);
      // The native working-speed multiplier, as in gathering. Walking and
      // delivering the catch take extra time and make no fish.
      GetComponent<CharacterAnimator>().SetBool("Working",true);
      GetComponent<CharacterModel>().LookToward(NavigationCoordinateSystem.GridToWorld(_water));
      _remaining-=hours*worker.WorkingSpeedMultiplier;
      if(_remaining>0)return ExecutorStatus.Running;
      var fish=new GoodAmount(_flag.Spec.GoodId,1);
      if(!_flag.Inventory.HasUnreservedCapacity(fish))return Finish(ExecutorStatus.Failure);
      GetComponent<GoodReserver>().ReserveCapacity(_flag.Inventory,fish);
      carrier.PutGoodsInHands(new CarriedGood(fish,CarriedGoodType.Uncountable));
      _flag.RecordCatch();
      return Finish(ExecutorStatus.Success);
    }
    public void Save(IEntitySaver saver) {
      var data=saver.GetComponent(Key);data.Set(FlagKey,_flag,_references.Of<FisherFlag>());
      data.Set(BankKey,_bank);data.Set(WaterKey,_water);data.Set(HoursKey,_remaining);
    }
    public void Load(IEntityLoader loader) {
      var data=loader.GetComponent(Key);_flag=data.Get(FlagKey,_references.Of<FisherFlag>());
      _bank=data.Get(BankKey);_water=data.Get(WaterKey);_remaining=data.Get(HoursKey);
    }
  }

  // The Gatherer Flag's native decorators (GatheringConfigurator, GatheringUIConfigurator),
  // with the fishing behavior in place of GatherWorkplaceBehavior. Saves from before the
  // Fisher Flag: the Gatherer Flag no longer reads its old "DeepFrontierShoreFishing" entry
  // (the entity loader only reads the keys a component asks for), so such a flag gathers
  // again; a fish left in its stock is native unwanted stock that its worker carries off;
  // a beaver saved in the old "ShoreCatchExecutor" resumes with no executor, because
  // BehaviorManager.DeserializeExecutor finds none of that name on the agent.
  [Context("Game")]
  public sealed class FisherFlagConfigurator : Configurator {
    protected override void Configure() {
      Bind<FisherFlag>().AsTransient();Bind<FisherWorkplaceBehavior>().AsTransient();Bind<FisherCatchExecutor>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();
      b.AddDecorator<FisherFlagSpec,FisherFlag>();
      b.AddDecorator<FisherFlag,BuildingWithTerrainRange>();
      b.AddDecorator<FisherFlag,SimpleOutputInventoryFragmentEnabler>();
      b.AddDecorator<FisherFlag,AutoEmptiable>();
      b.AddDecorator<FisherFlag,Emptiable>();
      b.AddDecorator<FisherFlag,HaulCandidate>();
      b.AddDecorator<FisherFlag,SimpleOutputInventoryHaulBehaviorProvider>();
      b.AddDecorator<FisherFlag,RemoveUnwantedStockWorkplaceBehavior>();
      b.AddDecorator<FisherFlag,FisherWorkplaceBehavior>();
      b.AddDecorator<FisherFlag,EmptyOutputWorkplaceBehavior>();
      b.AddDecorator<FisherFlag,EmptyInventoriesWorkplaceBehavior>();
      b.AddDecorator<FisherFlag,LaborWorkplaceBehavior>();
      b.AddDecorator<FisherFlag,WaitInsideIdlyWorkplaceBehavior>();
      b.AddDecorator<Worker,FisherCatchExecutor>();
      return b.Build();
    }
  }
}
