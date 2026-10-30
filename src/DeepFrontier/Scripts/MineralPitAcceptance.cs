using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.Carrying;
using Timberborn.CharacterControlSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.NeedSystem;
using Timberborn.SimpleOutputBuildings;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class MineralPitAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(args.Contains("-deepFrontierMineralAcceptance")||args.Contains("-deepFrontierMineralReload"))
        Bind<MineralPitAcceptance>().AsSingleton();
    }
  }
  internal sealed class PitSaveRecord {
    public string BuildingId,DepositId;
    public int Stock,Remaining;
  }
  // Explicitly launched disposable fixture. The source trim accelerates finite
  // depletion; every retained unit must be harvested and delivered by a beaver.
  internal sealed class MineralPitAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private const int TestYield=24;
    private static readonly string[] Goods={"Sandstone","Limestone"};
    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _objects;
    private readonly IBlockService _blocks;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierMineralReload");
    private readonly BlockObject[] _pits=new BlockObject[2];
    private readonly MineralDeposit[] _deposits=new MineralDeposit[2];
    private readonly Inventory[] _inventories=new Inventory[2];
    private readonly Worker[] _workers=new Worker[2];
    private readonly Transform[] _baskets=new Transform[2];
    private readonly Vector3[] _rest=new Vector3[2],_paused=new Vector3[2];
    private readonly bool[] _moved=new bool[2],_delivered=new bool[2];
    private readonly int[] _deliveries=new int[2];
    private readonly string[] _depositIds=new string[2];
    private readonly List<ControllableCharacter> _observers=new();
    private readonly List<Inventory> _disabledDonors=new();
    private int _frame,_phase;
    private float _started,_pauseTime,_normalHours;
    private bool _finished;
    private string RecordPath=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
      "TimberbornModding","outputs","mineral-pit-reload-expectations.json");
    public MineralPitAcceptance(EntityRegistry entities,EntityService entityService,BlockObjectFactory factory,
      TemplateService templates,BlockValidator validator,BlockObjectValidationService objects,IBlockService blocks,
      SpeedManager speed,IDayNightCycle clock,WorkingHoursManager hours,CameraService camera,
      GameSaver saver,GameLoader loader) {
      _entities=entities;_entityService=entityService;_factory=factory;_templates=templates;
      _validator=validator;_objects=objects;_blocks=blocks;_speed=speed;_clock=clock;_hours=hours;
      _camera=camera;_saver=saver;_loader=loader;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message)=>Debug.Log("[DeepFrontier Mineral Pits] PASS "+message);
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()
        &&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Mineral acceptance requires the marked disposable settlement");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Create(string id,int x,int y,int z) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),Orientation.Cw0,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Native placement rejected "+id+" "+placement.Coordinates);
      var result=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_objects.IsValid(result),"Native requirements rejected "+id);
      return result;
    }
    // 2026-10-22 footprints end at the walls: SandstonePit 5x5 -> 5x4 (rear plank row gone,
    // local frame unchanged), LimestonePit 6x5 -> 5x3 (hand cart, shelter and workbench gone;
    // its new local y 0 is the former y 1). Both keep their fixture origins (159,160) and
    // (166,160): each new footprint lies inside the former one on the flat bank and each
    // ground door's Entrance (1,-1,0) stays on the y 159 road ((160,159) and (167,159)).
    // The ground they no longer cover, in each new local frame, must take a Path and a 1x1
    // decoration (the limestone pit's former right column and rear rows, its open (4,0,0)).
    private void RequireFreedCells(int i) {
      var size=_pits[i].GetComponent<BlockObjectSpec>().Size;
      // One storey since the 2026-10-30 compaction (same footprints, 3 layers).
      var expected=i==0?new Vector3Int(5,4,3):new Vector3Int(5,3,3);
      Require(size==expected,"Installed "+Goods[i]+"Pit is "+size+"; this fixture encodes "+expected);
      var cells=i==0?FreedCellProbe.Outside(0,4,0,4,size):
        new[]{new Vector3Int(4,0,0)}.Concat(FreedCellProbe.Outside(0,5,0,4,size));
      FreedCellProbe.Require(_templates,_validator,_pits[i],cells,Goods[i]+"Pit",Pass);
    }
    private void VerifyNativeRules() {
      var pathTemplate=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Path");
      var pathSpec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==pathTemplate.Blueprint);
      var platformTemplate=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Platform.IronTeeth");
      var platformSpec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==platformTemplate.Blueprint);
      for(int i=0;i<2;i++) {
        var spec=_pits[i].GetComponent<BlockObjectSpec>();
        Require(spec.Blocks.All(b=>b.Stackable==BlockStackable.None),
          "Pit roof support was overridden by another mod");
        Require(! _pits[i].HasComponent<MechanicalNode>(),
          "Unpowered pit acquired a mechanical node from another mod");
        var local=spec.GetBlocks(new Placement(Vector3Int.zero,Orientation.Cw0,FlipMode.Unflipped)).ToArray();
        Require(local.Where(b=>b.Coordinates.z==0).All(b=>b.MatterBelow==MatterBelow.Ground),
          "Pit ground requirement was overridden");
        Require(!_validator.BlocksValid(spec,new Placement(_pits[i].Coordinates+new Vector3Int(0,0,12),
          Orientation.Cw0,FlipMode.Unflipped)),"Pit can float without ground");
        foreach(var column in local.Where(b=>b.IsOccupied).GroupBy(b=>new Vector2Int(b.Coordinates.x,b.Coordinates.y))) {
          var roof=column.OrderByDescending(b=>b.Coordinates.z).First().Coordinates+_pits[i].Coordinates+Vector3Int.forward;
          var placement=new Placement(roof,Orientation.Cw0,FlipMode.Unflipped);
          Require(!_validator.BlocksValid(pathSpec,placement),"Native path accepted an unsupported pit roof");
          Require(!_validator.BlocksValid(platformSpec,placement),"Native platform accepted an unsupported pit roof");
        }
      }
      Pass("unmodified ground-only foundations, non-supporting roofs, rejected roof paths/platforms and no power nodes");
    }
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>())) {
        if(_reload&&e.HasComponent<MineralPitSpec>())
          Require(e.GetComponent<PausableBuilding>().Paused,"Saved pit pause missing before fixture preparation");
        else e.GetComponent<PausableBuilding>().Pause();
      }
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<ControllableCharacter>())) {
        var c=e.GetComponent<ControllableCharacter>();
        string idle=e.GetComponent<TemplateSpec>().TemplateName+"_idle";
        Require(c.GetAnimationNames().Contains(idle),"Native idle animation missing");
        c.ChangeAnimation(idle);c.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(c.Transform.position));
        _observers.Add(c);
      }
      if(!_reload) {
        // Remove only the two superseded prototype pits in this marked fixture.
        foreach(var e in _entities.Entities.Where(e=>e.HasComponent<MineralPitSpec>()).ToArray()) {
          var p=e.GetComponent<BlockObject>().Coordinates;
          Require(p==new Vector3Int(132,135,3)||p==new Vector3Int(136,139,3),"Unexpected pre-existing pit");
          _entityService.Delete(e);
        }
        for(int y=157;y<=159;y++)if(!_blocks.GetPathObjectAt(new Vector3Int(173,y,3)))Create("Path",173,y,3);
        for(int x=159;x<173;x++)Create("Path",x,159,3);
        for(int i=0;i<2;i++) {
          int x=159+7*i;
          _pits[i]=Create(Goods[i]+"Pit.IronTeeth",x,160,3);
          _pits[i].GetComponent<PausableBuilding>().Pause();
          RequireFreedCells(i);
          _deposits[i]=Create(Goods[i]+"Outcrop",x+1,167,3).GetComponent<MineralDeposit>();
          Require(_deposits[i].Yielder.Yield.Amount==600,"Authored finite yield changed");
          _deposits[i].Yielder.DecreaseYield(new GoodAmount(Goods[i],600-TestYield));
        }
        Pass("native pit/source placement; each ordinary 600-unit deposit explicitly trimmed to 24 for depletion test");
      } else {
        var records=JsonConvert.DeserializeObject<PitSaveRecord[]>(File.ReadAllText(RecordPath));
        Require(records.Length==2,"Invalid checkpoint");
        for(int i=0;i<2;i++) {
          _pits[i]=_entities.Entities.Single(e=>e.GetComponent<EntityComponent>().EntityId.ToString()
            ==records[i].BuildingId).GetComponent<BlockObject>();
          _deposits[i]=_entities.Entities.Single(e=>e.GetComponent<EntityComponent>().EntityId.ToString()
            ==records[i].DepositId).GetComponent<MineralDeposit>();
          Require(_pits[i].GetComponent<PausableBuilding>().Paused,"Saved pit pause missing");
          Require(_deposits[i].Yielder.Yield.Amount==records[i].Remaining,"Saved finite reserve changed");
          Require(_pits[i].GetComponent<SimpleOutputInventory>().Inventory.AmountInStock(Goods[i])
            ==records[i].Stock,"Saved output stock changed");
        }
        Pass("exact pit/deposit identities, partial finite reserves, stocks and paused states restored");
      }
      VerifyNativeRules();
      for(int i=0;i<2;i++) {
        int index=i;
        _inventories[i]=_pits[i].GetComponent<SimpleOutputInventory>().Inventory;
        _depositIds[i]=_deposits[i].GetComponent<EntityComponent>().EntityId.ToString();
        _baskets[i]=_pits[i].GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true)
          .Single(t=>t.name=="#Pit.HoistedBasket");
        _rest[i]=_baskets[i].localPosition;
        Require(_pits[i].GetComponent<MineralYielderRetriever>().TryGetYielder(_deposits[i],out var own)
          &&own==_deposits[i].Yielder,"Own mineral source rejected");
        Require(!_pits[i].GetComponent<MineralYielderRetriever>().TryGetYielder(_deposits[1-i],out _),
          "Wrong mineral source accepted");
        _inventories[i].InventoryStockChanged+=(sender,args)=>{
          if(args.GoodAmount.GoodId!=Goods[index]||args.GoodAmount.Amount<=0)return;
          _deliveries[index]++;
          Debug.Log("[DeepFrontier Mineral Pits] DELIVERY "+Goods[index]+" "+args.GoodAmount.Amount);
          if(!_reload&&_deliveries[index]==2) {
            _pits[index].GetComponent<PausableBuilding>().Pause();_delivered[index]=true;
          }
        };
      }
      foreach(var inventory in _entities.Entities.Where(e=>e.HasComponent<Inventories>())
        .SelectMany(e=>e.GetComponent<Inventories>().AllInventories)
        .Where(v=>!_inventories.Contains(v)&&v.Enabled&&v.PublicOutput
          &&(v.OutputGoods.Contains("Sandstone")||v.OutputGoods.Contains("Limestone")))) {
        inventory.Disable();_disabledDonors.Add(inventory);
      }
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      _camera.MoveTargetTo(new Vector3(165,4,163));_camera.SetZoomLevel(18,0);
      _camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      Pass("mineral-specific source selection and native model/door/hoist bindings");
    }
    private void StartWorkers() {
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver"&&!w.GetComponent<GoodCarrier>().IsCarrying).Take(2).ToArray();
      Require(workers.Length==2,"Two empty-handed beaver workers required");
      for(int i=0;i<2;i++) {
        _workers[i]=workers[i];
        var workplace=_pits[i].GetComponent<Workplace>();
        Require(workplace.DesiredWorkers>=1&&workplace.DesiredWorkers<=2,"Unexpected pit staffing");
        if(workplace.DesiredWorkers==2)workplace.DecreaseDesiredWorkers();
        Require(workers[i].GetComponent<GoodCarrier>().LiftingCapacity/8<TestYield/2,
          "Fixture worker could exhaust the shortened deposit in two trips");
        var needs=workers[i].GetComponent<NeedManager>();
        foreach(var id in new[]{"Hunger","Thirst","Sleep"})
          needs.ApplyEffect(new InstantEffect(id,needs.GetNeedSpec(id).MaximumValue-needs.GetNeedPoints(id),1));
        var character=workers[i].GetComponent<ControllableCharacter>();
        character.ReleaseControl();_observers.Remove(character);
        _pits[i].GetComponent<PausableBuilding>().Resume();
        workers[i].Unemploy();workers[i].EmployAt(workplace);
      }
      _started=_clock.PartialDayNumber;_phase=1;_speed.ChangeSpeed(3);
    }
    private void CheckConservation() {
      for(int i=0;i<2;i++) {
        int remaining=_deposits[i]?_deposits[i].Yielder.Yield.Amount:0;
        Require(!_workers[i].GetComponent<GoodCarrier>().IsCarrying,"Worker still carrying checkpoint goods");
        Require(_inventories[i].AmountInStock(Goods[i])+remaining==TestYield,
          "Finite reserve plus delivered stock must equal the explicit 24-unit test supply");
      }
    }
    private void Save() {
      CheckConservation();
      for(int i=0;i<2;i++)_pits[i].GetComponent<PausableBuilding>().Pause();
      _speed.ChangeSpeed(0);_hours.WorkedPartOfDay=_normalHours;_finished=true;
      if(!_reload) {
        var records=Enumerable.Range(0,2).Select(i=>new PitSaveRecord {
          BuildingId=_pits[i].GetComponent<EntityComponent>().EntityId.ToString(),DepositId=_depositIds[i],
          Stock=_inventories[i].AmountInStock(Goods[i]),Remaining=_deposits[i].Yielder.Yield.Amount}).ToArray();
        Require(records.All(r=>r.Stock>0&&r.Remaining>0),"Checkpoint must preserve partial deposits");
        File.WriteAllText(RecordPath,JsonConvert.SerializeObject(records,Formatting.Indented));
      }
      foreach(var donor in _disabledDonors)donor.Enable();
      foreach(var observer in _observers)observer.ReleaseControl();
      string name=_reload?"Mineral pits continuity - verified":"Mineral pits - verified";
      _saver.QueueSave(new SaveReference(name,_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Mineral Pits] "+(_reload
          ?"ALL RELOAD, GATHERING AND FINITE DEPLETION CHECKS PASSED AND SAVED"
          :"ALL PLACEMENT, GATHERING, ANIMATION AND PAUSE CHECKS PASSED AND SAVED")));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(_frame==240)StartWorkers();
        if(_frame<=240)return;
        for(int i=0;i<2;i++)if(Vector3.Distance(_rest[i],_baskets[i].localPosition)>.015f)_moved[i]=true;
        if(_frame%600==0)Debug.Log("[DeepFrontier Mineral Pits] STATUS phase="+_phase+" stock="
          +string.Join(",",Enumerable.Range(0,2).Select(i=>_inventories[i].AmountInStock(Goods[i]))));
        if(!_reload&&_phase==1&&_delivered.All(v=>v)
          &&_pits.All(p=>!p.GetComponent<MineralPitAnimation>().IsCycling)) {
          Require(_moved.All(v=>v),"A delivered load did not animate its actual basket");
          CheckConservation();
          for(int i=0;i<2;i++)_paused[i]=_baskets[i].localPosition;
          _pauseTime=Time.realtimeSinceStartup;_phase=2;
        } else if(!_reload&&_phase==2&&Time.realtimeSinceStartup-_pauseTime>2) {
          for(int i=0;i<2;i++) {
            Require(Vector3.Distance(_paused[i],_baskets[i].localPosition)<.0001f,"Paused basket still moves");
            Require(!_pits[i].GetComponent<MineralPitAnimation>().IsCycling,"Paused hoist remains enabled");
          }
          Pass("actual workers delivered both minerals; baskets moved and stopped on workplace pause; exact conservation");
          Save();
        } else if(_reload&&Enumerable.Range(0,2).All(i=>_inventories[i].AmountInStock(Goods[i])==TestYield)) {
          Require(_moved.All(v=>v),"Reloaded hoist did not animate new deliveries");
          foreach(var id in _depositIds)
            Require(!_entities.Entities.Any(e=>e.GetComponent<EntityComponent>().EntityId.ToString()==id),
              "Exhausted finite source remains registered");
          Pass("fresh-process workers exhausted both finite sources; source entities removed; all 24 units each delivered");
          Save();
        }
        Require((_clock.PartialDayNumber-_started)*24<18,"Timed out waiting for native pit work");
      } catch(Exception exception) {
        _finished=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Mineral Pits] FAILED: "+exception);
      }
    }
  }
}
