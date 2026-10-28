using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BehaviorSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.BuildingsNavigation;
using Timberborn.Carrying;
using Timberborn.CharacterModelSystem;
using Timberborn.EntitySystem;
using Timberborn.Gathering;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MapStateSystem;
using Timberborn.Navigation;
using Timberborn.Persistence;
using Timberborn.SimpleOutputBuildings;
using Timberborn.TemplateInstantiation;
using Timberborn.WalkingSystem;
using Timberborn.WaterSystem;
using Timberborn.WorkSystem;
using Timberborn.WorldPersistence;
using Timberborn.Yielding;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record ShoreFishingSpec : ComponentSpec {
    [Serialize] public string GoodId {get;init;}
    [Serialize] public float CatchHours {get;init;}
    [Serialize] public float MinimumDepth {get;init;}
    [Serialize] public float MaximumContamination {get;init;}
    [Serialize] public float MaximumReachDown {get;init;}
  }

  // The existing flag, workforce, terrain range, carrying and output inventory
  // remain native. Fishing is an explicit player-selected job for that flag.
  internal sealed class ShoreFishing : BaseComponent,IAwakableComponent,IPersistentEntity {
    private static readonly ComponentKey Key=new("DeepFrontierShoreFishing");
    private static readonly PropertyKey<bool> ModeKey=new("FishingSelected");
    private readonly IThreadSafeWaterMap _water;
    private readonly MapSize _map;
    private BuildingTerrainRange _range;
    private Vector3Int _bank,_waterCell;
    private bool _hasSpot;
    public ShoreFishingSpec Spec {get;private set;}
    public Inventory Inventory {get;private set;}
    public bool FishingSelected {get;private set;}
    public int CaughtThisSession {get;private set;}
    public string State {get;private set;}="Gathering plants";
    public ShoreFishing(IThreadSafeWaterMap water,MapSize map) {_water=water;_map=map;}
    public void Awake() {
      Spec=GetComponent<ShoreFishingSpec>();Inventory=GetComponent<SimpleOutputInventory>().Inventory;
      _range=GetComponent<BuildingTerrainRange>();
      if(Spec.GoodId!="FreshFish" || Spec.CatchHours<=0 || Spec.MinimumDepth<=0 || Spec.MaximumContamination<0 || Spec.MaximumReachDown<=0)
        throw new InvalidOperationException("Invalid authored shore-fishing contract");
    }
    public void SelectFishing(bool selected) {FishingSelected=selected;_hasSpot=false;State=selected?"Looking for clean shoreline":"Gathering plants";}
    public void Save(IEntitySaver saver) {saver.GetComponent(Key).Set(ModeKey,FishingSelected);}
    public void Load(IEntityLoader loader) {
      // Saves predating the component have no player selection. New flags and
      // those saves start in the existing gathering job until explicitly changed.
      if(loader.TryGetComponent(Key,out var data))SelectFishing(data.Get(ModeKey));
    }
    private bool InMap(Vector3Int c) {var size=_map.TotalSize;return c.x>=0&&c.y>=0&&c.z>=0&&c.x<size.x&&c.y<size.y&&c.z<size.z;}
    public bool Suitable(Vector3Int bank,Vector3Int water) {
      if(!InMap(bank)||!InMap(water)||!_range.GetRange().Contains(bank)||_water.CellIsUnderwater(bank))return false;
      if(_water.WaterDepth(water)<Spec.MinimumDepth||_water.ColumnContamination(water)>Spec.MaximumContamination)return false;
      var height=_water.WaterHeightOrFloor(water);
      return height>=bank.z-Spec.MaximumReachDown&&height<=bank.z+.10f;
    }
    public bool TryFindSpot(Vector3 origin,out Vector3Int bank,out Vector3Int water) {
      bank=water=default;bool found=false;float best=float.PositiveInfinity;
      foreach(var cell in _range.GetRange()) {
        foreach(var offset in new[]{Vector3Int.left,Vector3Int.right,Vector3Int.up,Vector3Int.down}) {
          var probe=cell+offset+new Vector3Int(0,0,-1);
          if(!Suitable(cell,probe))continue;
          float distance=(Position(cell,probe)-origin).sqrMagnitude;
          if(distance<best) {found=true;best=distance;bank=cell;water=probe;}
        }
      }
      return found;
    }
    public static Vector3 Position(Vector3Int bank,Vector3Int water) => NavigationCoordinateSystem.GridToWorld(bank)+new Vector3(water.x-bank.x,0,water.y-bank.y)*.23f;
    public bool CanWork(Worker worker) => FishingSelected&&Inventory.Enabled&&GetComponent<BlockableObject>().IsUnblocked
      &&!GetComponent<PausableBuilding>().Paused&&worker.Workplace==GetComponent<Workplace>()&&worker.GetComponent<WorkerWorkingHours>().AreWorkingHours;
    public Decision Decide(BehaviorAgent agent) {
      var worker=agent.GetComponent<Worker>();
      if(!CanWork(worker))return Decision.ReleaseNow();
      if(agent.GetComponent<GoodCarrier>().IsCarrying)return Decision.ReleaseNow();
      if(Inventory.UnreservedCapacity(Spec.GoodId)<1) {State="Fish storage is full";return Decision.ReleaseNow();}
      if(!_hasSpot || !Suitable(_bank,_waterCell))_hasSpot=TryFindSpot(agent.Transform.position,out _bank,out _waterCell);
      var warning=GetComponent<NothingToDoInRangeStatus>();
      if(!_hasSpot) {State="No reachable clean shoreline";warning.ActivateStatus();return Decision.ReleaseNow();}
      warning.DeactivateStatus();State="Fishing from the shore";
      var walk=agent.GetComponent<WalkToPositionExecutor>();
      switch(walk.Launch(Position(_bank,_waterCell))) {
        case ExecutorStatus.Running:return Decision.ReturnWhenFinished(walk);
        case ExecutorStatus.Failure:_hasSpot=false;return Decision.ReleaseNextTick();
        case ExecutorStatus.Success:
          var catchFish=agent.GetComponent<ShoreCatchExecutor>();catchFish.Launch(this,_bank,_waterCell);return Decision.ReleaseWhenFinished(catchFish);
        default:throw new ArgumentOutOfRangeException();
      }
    }
    public void RecordCatch() {CaughtThisSession++;}
    public void RecordFishingWork() {State="Fishing from the shore";}
  }

  internal sealed class ShoreCatchExecutor : BaseComponent,IExecutor {
    private static readonly ComponentKey Key=new("DeepFrontierShoreCatch");
    private static readonly PropertyKey<ShoreFishing> FlagKey=new("Flag");
    private static readonly PropertyKey<Vector3Int> BankKey=new("Bank"),WaterKey=new("Water");
    private static readonly PropertyKey<float> HoursKey=new("RemainingHours");
    private readonly ReferenceSerializer _references;
    private ShoreFishing _flag;
    private Vector3Int _bank,_water;
    private float _remaining;
    public float RemainingHours => _remaining;
    public Vector3Int WaterCell => _water;
    public ShoreCatchExecutor(ReferenceSerializer references) {_references=references;}
    public void Launch(ShoreFishing flag,Vector3Int bank,Vector3Int water) {
      _flag=flag;_bank=bank;_water=water;_remaining=flag.Spec.CatchHours;
      GetComponent<CharacterModel>().LookToward(NavigationCoordinateSystem.GridToWorld(water));
      GetComponent<CharacterAnimator>().SetBool("Working",true);
    }
    private ExecutorStatus Finish(ExecutorStatus result) {GetComponent<CharacterAnimator>().SetBool("Working",false);return result;}
    public ExecutorStatus Tick(float hours) {
      var worker=GetComponent<Worker>();var carrier=GetComponent<GoodCarrier>();
      if(!_flag||!_flag.CanWork(worker)||!_flag.Suitable(_bank,_water)||carrier.IsCarrying
        ||Vector3.Distance(Transform.position,ShoreFishing.Position(_bank,_water))>.3f)return Finish(ExecutorStatus.Failure);
      // Use the same native working-speed multiplier as gathering. Travel and
      // delivering the catch consume additional time and do not create fish.
      GetComponent<CharacterAnimator>().SetBool("Working",true);
      GetComponent<CharacterModel>().LookToward(NavigationCoordinateSystem.GridToWorld(_water));
      _flag.RecordFishingWork();
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
      var data=saver.GetComponent(Key);data.Set(FlagKey,_flag,_references.Of<ShoreFishing>());
      data.Set(BankKey,_bank);data.Set(WaterKey,_water);data.Set(HoursKey,_remaining);
    }
    public void Load(IEntityLoader loader) {
      var data=loader.GetComponent(Key);_flag=data.Get(FlagKey,_references.Of<ShoreFishing>());
      _bank=data.Get(BankKey);_water=data.Get(WaterKey);_remaining=data.Get(HoursKey);
    }
  }

  [Context("Game")]
  public sealed class ShoreFishingConfigurator : Configurator {
    protected override void Configure() {
      Bind<ShoreFishing>().AsTransient();Bind<ShoreCatchExecutor>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();b.AddDecorator<ShoreFishingSpec,ShoreFishing>();b.AddDecorator<Worker,ShoreCatchExecutor>();return b.Build();
    }
  }

#if !UNITY_EDITOR
  // Native gathering only has resource-entity yielders. These three specific
  // entry contracts extend that job and its inventory to free water fishing.
  [HarmonyLib.HarmonyPatch(typeof(YieldRemovingBuilding),nameof(YieldRemovingBuilding.GetAllowedGoods))]
  internal static class ShoreFishingAllowedGoods {
    private static void Postfix(YieldRemovingBuilding __instance,ref IEnumerable<string> __result) {
      if(__instance.GetComponent<ShoreFishingSpec>()!=null)__result=__result.Append("FreshFish");
    }
  }
  [HarmonyLib.HarmonyPatch(typeof(InRangeYielderGoodAllower),nameof(InRangeYielderGoodAllower.AllowedAmount))]
  internal static class ShoreFishingAllowance {
    private static bool Prefix(InRangeYielderGoodAllower __instance,string goodId,ref int __result) {
      if(goodId!="FreshFish"||__instance.GetComponent<ShoreFishingSpec>()==null)return true;
      __result=int.MaxValue;return false;
    }
  }
  [HarmonyLib.HarmonyPatch(typeof(GatherWorkplaceBehavior),nameof(GatherWorkplaceBehavior.Decide))]
  internal static class ShoreFishingJob {
    private static bool Prefix(GatherWorkplaceBehavior __instance,BehaviorAgent agent,ref Decision __result) {
      var fishing=__instance.GetComponent<ShoreFishing>();
      if(!fishing||!fishing.FishingSelected)return true;
      __result=fishing.Decide(agent);return false;
    }
  }
#endif
}
