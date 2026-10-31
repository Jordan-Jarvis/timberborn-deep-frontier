using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.CharacterControlSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class MixerAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierMixerAcceptance")
        ||Environment.GetCommandLineArgs().Contains("-deepFrontierMixerReload"))
        Bind<MixerAcceptance>().AsSingleton();
    }
  }
  internal sealed class MixerSaveRecord {
    public string EntityId;
    public Dictionary<string,int> Stock;
    public float Progress;
  }
  internal sealed class MixerAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities; private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates; private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _objects; private readonly IBlockService _blocks;
    private readonly INavMeshService _nav; private readonly INavigationService _navigation;
    private readonly SpeedManager _speed; private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours; private readonly CameraService _camera;
    private readonly GameSaver _saver; private readonly GameLoader _loader;
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierMixerReload");
    private readonly Queue<Vector3> _destinations=new();
    private readonly List<Inventory> _disabledDonors=new();
    // The installed mixer recipe's goods and amounts per batch (Concrete since
    // the 2026-10-30 bricks pass: sandstone rubble, cement and water).
    private RecipeSpec _recipe;
    private readonly Dictionary<string,int> _consumed=new();
    private string[] InputGoods=>_recipe.Ingredients.Select(g=>g.Id).ToArray();
    private string[] Solids=>InputGoods.Where(g=>g!="Water").ToArray();
    private string[] Goods=>InputGoods.Concat(_recipe.Products.Select(g=>g.Id)).ToArray();
    private int Per(string good)=>_recipe.Ingredients.Single(g=>g.Id==good).Amount;
    private int WaterCapacity=>_recipe.GetCapacity(new GoodAmount("Water",Per("Water")));
    private bool ConsumedBatches(int batches)=>InputGoods.All(g=>_consumed[g]==Per(g)*batches);
    private BlockObject _building; private Manufactory _machine; private MechanicalNode _generator;
    private Transform _drum; private Quaternion _firstRotation,_stoppedRotation;
    private ControllableCharacter _walker; private Vector3 _walkTarget;
    private const int Walks=3;
    private int _frame,_phase,_batches,_walks; private float _phaseTime,_normalHours,_stoppedProgress;
    private bool _finished,_motionObserved;
    private string RecordPath=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
      "TimberbornModding","outputs","mixer-reload-expectations.json");
    public MixerAcceptance(EntityRegistry entities,BlockObjectFactory factory,TemplateService templates,
      BlockValidator validator,BlockObjectValidationService objects,IBlockService blocks,
      INavMeshService nav,INavigationService navigation,SpeedManager speed,IDayNightCycle clock,
      WorkingHoursManager hours,CameraService camera,GameSaver saver,GameLoader loader) {
      _entities=entities;_factory=factory;_templates=templates;_validator=validator;_objects=objects;
      _blocks=blocks;_nav=nav;_navigation=navigation;_speed=speed;_clock=clock;_hours=hours;
      _camera=camera;_saver=saver;_loader=loader;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message) {Debug.Log("[DeepFrontier Mixer] PASS "+message);}
    private void Phase(int value) {_phase=value;_phaseTime=_clock.PartialDayNumber;}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()
        &&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Mixer acceptance requires the marked disposable settlement");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Native placement rejected "+id+" "+placement.Coordinates);
      var result=_factory.CreateFinished(new EntitySetup.Builder(template.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_objects.IsValid(result),"Native building requirements rejected "+id);
      return result;
    }
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>())) {
        if(_reload&&e.GetComponent<TemplateSpec>().TemplateName=="ConcreteMixer.IronTeeth")
          Require(e.GetComponent<PausableBuilding>().Paused,"Saved mixer pause did not persist");
        else e.GetComponent<PausableBuilding>().Pause();
      }
      if(_reload) {
        _building=_entities.Entities.Single(e=>e.HasComponent<TemplateSpec>()
          &&e.GetComponent<TemplateSpec>().TemplateName=="ConcreteMixer.IronTeeth").GetComponent<BlockObject>();
        var generatorCell=PowerCell(2);
        _generator=_entities.Entities.Where(e=>e.HasComponent<BlockObject>())
          .Select(e=>e.GetComponent<BlockObject>()).Single(b=>b.Coordinates==generatorCell
            &&b.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator").GetComponent<MechanicalNode>();
      } else {
        Require(!_entities.Entities.Any(e=>e.HasComponent<TemplateSpec>()
          &&e.GetComponent<TemplateSpec>().TemplateName=="ConcreteMixer.IronTeeth"),"Fixture already contains a mixer");
        _building=Create("ConcreteMixer.IronTeeth",159,160,3);
        _building.GetComponent<PausableBuilding>().Pause();
        // The fixture follows the installed mixer blueprint, not a size literal
        // (compact 4x3x3 since 2026-10-30, same origin and entrance). Freed
        // ground, checked before the fixture builds beside it: the open ground
        // cells inside the bounds and the former 8x6 footprint (local frame
        // unchanged since then) outside them (outputs/freed-cells.json).
        var spec=_building.GetComponent<BlockObjectSpec>();
        var size=spec.Size;
        var localBlocks=spec.GetBlocks(new Placement(Vector3Int.zero,Orientation.Cw0,FlipMode.Unflipped)).ToArray();
        var openGround=localBlocks.Where(b=>b.Coordinates.z==0&&!b.IsOccupied).Select(b=>b.Coordinates).ToArray();
        FreedCellProbe.Require(_templates,_validator,_building,
          openGround.Concat(FreedCellProbe.Outside(0,7,0,5,size)),"ConcreteMixer",Pass);
        var entrance=_building.PositionedEntrance.Coordinates;
        Require(entrance.y==159&&entrance.z==3,"Mixer entrance "+entrance+" is not on the fixture's y 159 road");
        for(int y=157;y<=159;y++)if(!_blocks.GetPathObjectAt(new Vector3Int(173,y,3)))Create("Path",173,y,3);
        for(int x=159;x<173;x++)Create("Path",x,159,3);
        // The ground door's native Entrance is the road cell in front of it,
        // local (1,-1,0); the doorstep behind the face is occupied. The
        // machine has no walkable decks or rails since 2026-10-21.
        for(int y=156;y<=159;y++)Create("Path",158,y,3);
        Create("Path",159,156,3);
        // Shafts meet authored walls only: build beside the first transput's
        // first horizontal face.
        var shaftCell=PowerCell(1);var generatorCell=PowerCell(2);
        Create("PowerShaft.IronTeeth",shaftCell.x,shaftCell.y,shaftCell.z);
        _generator=Create("DevPowerGenerator",generatorCell.x,generatorCell.y,generatorCell.z).GetComponent<MechanicalNode>();
        var pathSpec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint
          ==_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Path").Blueprint);
        // An enclosed room: every floor-occupying ground cell rejects a path.
        var room=localBlocks.Where(b=>b.Coordinates.z==0&&b.Occupation.Intersects(BlockOccupations.Floor)).Select(b=>b.Coordinates).ToArray();
        Require(room.Length>0,"Installed mixer has no floor-occupying ground cell");
        foreach(var local in room)
          Require(!_validator.BlocksValid(pathSpec,new Placement(_building.TransformCoordinates(local),Orientation.Cw0,FlipMode.Unflipped)),
            "Enclosed mixer room incorrectly accepts a path at "+local);
        Pass("native placement, ground-door entrance path, wall-face shaft and enclosed-room collision");
      }
      _machine=_building.GetComponent<Manufactory>();
      _recipe=_machine.ProductionRecipes.Single();
      foreach(var good in InputGoods)_consumed[good]=0;
      // Other accepted factories retain real output stock in this settlement.
      // Isolate this seeded consumption test at its supply source, so normal
      // haulers cannot replenish its solid inputs during exhaustion or saving.
      foreach(var inventory in _entities.Entities.Where(e=>e.HasComponent<Inventories>())
        .SelectMany(e=>e.GetComponent<Inventories>().AllInventories)
        .Where(i=>i!=_machine.Inventory&&i.Enabled&&i.PublicOutput
          &&Solids.Any(g=>i.OutputGoods.Contains(g)))) {
        inventory.Disable();_disabledDonors.Add(inventory);
      }
      _drum=_building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true)
        .Single(t=>t.name=="#Mixer.Drum");
      _firstRotation=_drum.localRotation;
      _machine.ProductionFinished+=(sender,args)=>{_batches++;Debug.Log("[DeepFrontier Mixer] BATCH "+_batches);};
      _machine.Inventory.InventoryStockChanged+=(sender,args)=>{
        if(args.StockChangeType==Timberborn.InventorySystem.StockChangeType.Consumed
          &&args.GoodAmount.Amount<0&&_consumed.ContainsKey(args.GoodAmount.GoodId))
          _consumed[args.GoodAmount.GoodId]-=args.GoodAmount.Amount;
      };
      _camera.MoveTargetTo(new Vector3(163,6,163));_camera.SetZoomLevel(15,0);
      _camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
    }
    private void Water(int amount) {
      var inv=_machine.Inventory;int current=inv.AmountInStock("Water");
      if(current>0)inv.TakeExisting(new GoodAmount("Water",current));
      if(amount>0)inv.GiveExisting(new GoodAmount("Water",amount));
      CheckWater(amount);
    }
    private void CheckWater(int amount) {
      var spec=_building.GetComponent<WorkshopReservoirSpec>();
      var visual=_building.GetComponent<WorkshopReservoir>();
      Require(spec.Capacity==WaterCapacity&&visual.StoredAmount==amount&&visual.SurfacesVisible==(amount>0),
        "Mixer header stock/visibility mismatch");
      Require(visual.SurfaceHeights.Count==1,"Expected one native mixer tank surface");
      var surface=spec.Surfaces.Single();
      float expected=surface.EmptyHeight+(surface.FullHeight-surface.EmptyHeight)*amount/(float)WaterCapacity;
      Require(Math.Abs(visual.SurfaceHeights.Single()-expected)<.00001f,"Mixer header level mismatch");
    }
    private Vector3Int PowerCell(int distance) {
      var transput=_building.GetComponent<TransputProviderSpec>().Transputs[0];
      foreach(var d in transput.Directions.ToString().Split(',').Select(x=>x.Trim())) {
        var step=d=="Left"?Vector3Int.left:d=="Right"?Vector3Int.right:d=="Down"?Vector3Int.down:d=="Up"?Vector3Int.up:Vector3Int.zero;
        if(step!=Vector3Int.zero)return _building.TransformCoordinates(transput.Coordinates+step*distance);
      }
      throw new InvalidOperationException("Mixer Transputs[0] has no horizontal face: "+transput.Directions);
    }
    private void Inputs(int batches) {
      foreach(var good in InputGoods)_machine.Inventory.GiveExisting(new GoodAmount(good,Per(good)*batches));
    }
    private void Start() {
      var power=_building.GetComponent<MechanicalNode>();
      Require(power.Graph==_generator.Graph&&power.Graph.PowerSupply>0,"Mixer shaft does not join its generator");
      Require(_building.GetComponent<MechanicalNodeSpec>().PowerInput==250,"Mixer nameplate demand changed");
      Require(_building.HasEntrance,"Mixer has no native entrance");
      var entrance=_building.PositionedEntrance.Coordinates;
      Require(entrance==_building.TransformCoordinates(new Vector3Int(1,-1,0)),"Mixer entrance is not the path cell in front of the door");
      Require(_blocks.GetPathObjectAt(entrance)
        &&_nav.AreConnectedInstant(entrance,entrance+Vector3Int.right)
        &&_nav.AreConnectedInstant(entrance+Vector3Int.right,entrance),
        "Mixer ground-door entrance lacks its connected native path");
      Pass("shaft graph supplies the 250 hp mixer; the ground-door entrance is on the connected road");
      if(_reload) {
        var record=JsonConvert.DeserializeObject<MixerSaveRecord>(File.ReadAllText(RecordPath));
        Require(_building.GetComponent<EntityComponent>().EntityId.ToString()==record.EntityId,"Mixer identity changed across reload");
        Require(_building.GetComponent<PausableBuilding>().Paused,"Mixer pause did not persist");
        foreach(var good in Goods)Require(_machine.Inventory.AmountInStock(good)==record.Stock[good],"Saved stock differs: "+good);
        Require(Math.Abs(_machine.ProductionProgress-record.Progress)<.00001f,"Saved production progress differs");
        CheckWater(record.Stock["Water"]);
        Pass("fresh process restored exact mixer identity, stock, progress, supports and water surface");
      } else {
        Water(0);Water(WaterCapacity/2);Water(WaterCapacity);Water(0);
        Pass($"native header tank follows 0/{WaterCapacity/2}/{WaterCapacity}/0 Water without a duplicate inventory");
        Require(_machine.Inventory.IsEmpty,"New mixer has unexpected stock");
        Inputs(2);
      }
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").Take(3).ToArray();
      Require(workers.Length==3,"Mixer fixture requires two workers and one walker");
      foreach(var worker in workers)worker.Unemploy();
      _building.GetComponent<PausableBuilding>().Resume();
      for(int i=0;i<2;i++)workers[i].EmployAt(_building.GetComponent<Workplace>());
      _walker=workers[2].GetComponent<ControllableCharacter>();
      Require(_walker.GetAnimationNames().Contains("BeaverAdult_idle"),"Native walker idle animation missing");
      _walker.ChangeAnimation("BeaverAdult_idle");
      // Ground walks only: door entrance, along the road, back to the door.
      _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(entrance));
      _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(new Vector3Int(172,159,3)));
      _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(entrance));
      NextWalk();Phase(_reload?7:1);_speed.ChangeSpeed(3);
    }
    private void NextWalk() {
      if(_destinations.Count==0){_walker.ReleaseControl();_walker=null;return;}
      _walkTarget=_destinations.Dequeue();
      Require(_navigation.FindPathUnlimitedRange(_walker.Transform.position,_walkTarget,new List<PathCorner>(),out var distance),
        "No native walking route to "+_walkTarget);
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_walkTarget));
    }
    private void Finish() {
      Require(_walks==Walks,"Mixer traversal did not reach every destination");
      _building.GetComponent<PausableBuilding>().Pause();
      _hours.WorkedPartOfDay=_normalHours;
      _speed.ChangeSpeed(0);_finished=true;
      if(!_reload) {
        Require(InputGoods.All(g=>_machine.Inventory.AmountInStock(g)==0),
          "The controlled three-batch supply was unexpectedly replenished");
        Inputs(2);
        var record=new MixerSaveRecord {EntityId=_building.GetComponent<EntityComponent>().EntityId.ToString(),
          Stock=Goods.ToDictionary(g=>g,g=>_machine.Inventory.AmountInStock(g)),Progress=_machine.ProductionProgress};
        File.WriteAllText(RecordPath,JsonConvert.SerializeObject(record,Formatting.Indented));
      }
      foreach(var donor in _disabledDonors)donor.Enable();
      _disabledDonors.Clear();
      CheckWater(_machine.Inventory.AmountInStock("Water"));
      var folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        "TimberbornModding","docs","art","reviews","2026-10-20-mixer");
      Directory.CreateDirectory(folder);
      ScreenCapture.CaptureScreenshot(Path.Combine(folder,_reload?"mixer-native-reload.png":"mixer-native.png"));
      _saver.QueueSave(new SaveReference(_reload?"Mixer continuity - verified":"Mixer acceptance - verified",
        _loader.LoadedSave.SettlementReference),()=>Debug.Log("[DeepFrontier Mixer] "
          +(_reload?"ALL RELOAD AND PRODUCTION CHECKS PASSED AND SAVED":"ALL PLACEMENT, WALKING, ANIMATION AND PRODUCTION CHECKS PASSED AND SAVED")));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(_frame==240)Start();
        if(_frame<=240)return;
        if(_walker&&Vector3.Distance(_walker.Transform.position,_walkTarget)<.18f) {
          _walks++;Pass("actual beaver reached "+_walkTarget);NextWalk();
        }
        if(Quaternion.Angle(_drum.localRotation,_firstRotation)>.1f)_motionObserved=true;
        float hours=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_frame%600==0)Debug.Log("[DeepFrontier Mixer] STATUS phase="+_phase+", batches="+_batches
          +", progress="+_machine.ProductionProgress+", walks="+_walks);
        if(_phase==1&&_machine.ProductionProgress>.2f) {
          Require(_motionObserved,"Mixer drum did not animate during production");
          Require(_building.GetComponent<MechanicalNode>().PowerEfficiency==1,"Mixer lacks full 250 hp");
          _generator.SetOutputMultiplier(0);Phase(2);
        } else if(_phase==2&&hours>.1f) {
          _stoppedProgress=_machine.ProductionProgress;_stoppedRotation=_drum.localRotation;Phase(3);
        } else if(_phase==3&&hours>.3f) {
          Require(Math.Abs(_machine.ProductionProgress-_stoppedProgress)<.00001f,"Unpowered mixer continued production");
          Require(Quaternion.Angle(_drum.localRotation,_stoppedRotation)<.01f,"Unpowered mixer drum continued moving");
          _generator.SetOutputMultiplier(1);Pass("power loss stops recipe progress and actual drum motion");Phase(4);
        } else if(_phase==4&&_batches==2) {
          Require(ConsumedBatches(2),"Two-batch input accounting differs");
          Phase(5);Pass("two native batches consumed "+string.Join(", ",InputGoods.Select(g=>Per(g)*2+" "+g)));
        } else if(_phase==5&&hours>.4f) {
          Require(_batches==2&&!_machine.IsReadyToProduce,"Mixer produces without ingredients");
          CheckWater(0);Inputs(1);Phase(6);
          Pass("input exhaustion stops work and empties the visible header tank");
        } else if(_phase==6&&_batches==3&&_walks==Walks) {
          Require(ConsumedBatches(3),"Three-batch input accounting differs");
          Pass("replenishment resumes production; three batches made "+_recipe.Products.Sum(g=>g.Amount)*3+" Concrete");Finish();
        } else if(_phase==7&&_batches>=1&&_walks==Walks) {
          Require(_motionObserved&&_consumed["Water"]>0,"Reload did not resume actual water-consuming production");
          Pass("saved inputs produced another native batch with advancing drum and matching water surface");Finish();
        }
        Require(hours<36,"Mixer test exceeded its per-phase time limit");
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        foreach(var donor in _disabledDonors)donor.Enable();
        _disabledDonors.Clear();
        Debug.LogError("[DeepFrontier Mixer] FAILED: "+error);
      }
    }
  }
}
