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
using Timberborn.MechanicalSystem;
using Timberborn.MapIndexSystem;
using Timberborn.Navigation;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class StructuralAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(args.Contains("-deepFrontierStructures")||args.Contains("-deepFrontierStructuresReload"))
        Bind<StructuralAcceptance>().AsSingleton();
    }
  }
  internal sealed class StructuralEntityRecord {
    public string Id,Template;
    public Vector3Int Coordinates;
  }
  internal sealed class StructuralSaveRecord {
    public StructuralEntityRecord[] Entities;
  }
  internal sealed class StructuralWaterRecord {
    public float WaterDepth;
  }
  // Explicit disposable fixture. Every placement and route uses native services.
  internal sealed class StructuralAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private static readonly string[] Models={"SandstoneMasonryBlock","BrickMasonryBlock","ConcreteBlock",
      "ReinforcedDamBlock","ConcreteOverflowDam","ConcreteOverhang8x1","ConcreteScaffold3x3"};
    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly INavigationService _navigation;
    private readonly IWaterService _water;
    private readonly IThreadSafeWaterMap _waterMap;
    private readonly IFlowLimiterService _flowLimits;
    private readonly MapIndexService _indices;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly List<BlockObject> _created=new();
    private readonly Queue<Vector3Int> _destinations=new();
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierStructuresReload");
    private static readonly Vector3Int Basin=new(143,170,4);
    private static readonly Vector3Int ControlBasin=new(149,170,4);
    private readonly List<BlockObject> _spillWalls=new();
    private ControllableCharacter _walker;
    private Vector3 _target;
    private int _frame,_phase,_walks;
    private float _phaseStart;
    private bool _finished;
    private string RecordPath=>Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
      "TimberbornModding","outputs","structural-reload-expectations.json");
    public StructuralAcceptance(EntityRegistry entities,EntityService entityService,TemplateService templates,
      BlockObjectFactory factory,BlockValidator validator,BlockObjectValidationService validation,
      INavigationService navigation,IWaterService water,IThreadSafeWaterMap waterMap,IFlowLimiterService flowLimits,MapIndexService indices,SpeedManager speed,
      IDayNightCycle clock,CameraService camera,GameSaver saver,GameLoader loader) {
      _entities=entities;_entityService=entityService;_templates=templates;_factory=factory;
      _validator=validator;_validation=validation;_navigation=navigation;_water=water;_waterMap=waterMap;
      _flowLimits=flowLimits;_indices=indices;_speed=speed;_clock=clock;_camera=camera;_saver=saver;_loader=loader;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message)=>Debug.Log("[DeepFrontier Structures] PASS "+message);
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&
        e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),"Disposable fixture marker missing");
      _speed.ChangeSpeed(0);
      if(_reload) {
        var saved=JsonConvert.DeserializeObject<StructuralSaveRecord>(File.ReadAllText(RecordPath));
        foreach(var record in saved.Entities) {
          var entity=_entities.Entities.Single(e=>e.GetComponent<EntityComponent>().EntityId.ToString()==record.Id);
          var block=entity.GetComponent<BlockObject>();
          Require(entity.GetComponent<TemplateSpec>().TemplateName==record.Template&&block.Coordinates==record.Coordinates,
            "Saved structural identity/coordinates changed");
          _created.Add(block);
        }
        // The capture tool reads the completed native save. A render-thread
        // water snapshot taken before QueueSave can precede the saved physics.
        var waterRecord=JsonConvert.DeserializeObject<StructuralWaterRecord>(File.ReadAllText(
          Path.Combine(Path.GetDirectoryName(RecordPath),"structural-water-checkpoint.json")));
        float restoredDepth=_waterMap.WaterDepth(Basin);
        Require(Math.Abs(restoredDepth-waterRecord.WaterDepth)<.000001f,
          "Saved basin water changed before simulation: restored="+restoredDepth+" saved="+waterRecord.WaterDepth);
        Pass("exact structural identities, positions and retained basin water restored");
      }
    }
    private BlockObjectSpec Spec(string id) {
      var t=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      return _templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==t.Blueprint);
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var spec=Spec(id);var p=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,p),"Native placement rejected "+id+" "+p.Coordinates+" "+orientation);
      var result=_factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),p);
      Require(_validation.IsValid(result),"Native object requirements rejected "+id);
      _created.Add(result);return result;
    }
    private void Remove(BlockObject block) {_created.Remove(block);_entityService.Delete(block);}
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      foreach(var id in Models) {
        Require(!_validator.BlocksValid(Spec(id+".IronTeeth"),
          new Placement(new Vector3Int(148,165,20),Orientation.Cw0,FlipMode.Unflipped)),
          "Unsupported structure floats: "+id);
      }
      if(!_reload) {
        foreach(var id in Models)foreach(var orientation in new[]{Orientation.Cw0,Orientation.Cw90,Orientation.Cw180,Orientation.Cw270}) {
          var trial=Create(id+".IronTeeth",148,165,3,orientation);
          Require(!trial.HasComponent<MechanicalNode>(),"Passive structure acquired power from an override");
          Remove(trial);
        }
        Pass("seven native templates in all four rotations; unsupported floating placement rejected; no passive power nodes");
        for(int z=3;z<15;z++)Create(Models[(z-3)%4]+".IronTeeth",145,164,z);
        Create("Platform.IronTeeth",145,164,15);
        Create("Path",145,164,16);
        Create("ConcreteScaffold3x3.IronTeeth",148,162,3);
        for(int y=162;y<=164;y++)Create("Path",149,y,3);
        Create("PowerShaft.IronTeeth",150,163,3);
        Create("Tubeway.IronTeeth",148,163,3);
        // Native stair flight climbs four layers to the scaffold deck.
        Create("Stairs.IronTeeth",147,158,3,Orientation.Cw180);
        Create("Platform.IronTeeth",147,159,3);Create("Stairs.IronTeeth",147,159,4,Orientation.Cw180);
        Create("DoublePlatform.IronTeeth",147,160,3);Create("Stairs.IronTeeth",147,160,5,Orientation.Cw180);
        Create("DoublePlatform.IronTeeth",147,161,3);Create("Platform.IronTeeth",147,161,5);
        Create("Stairs.IronTeeth",147,161,6,Orientation.Cw180);
        Create("TriplePlatform.IronTeeth",147,162,3);Create("Platform.IronTeeth",147,162,6);
        Create("Path",147,162,7);
        for(int x=148;x<=150;x++)Create("Path",x,162,7);
        for(int y=163;y<=164;y++)Create("Path",149,y,7);
        Create("Path",150,164,7);
        Create("DoublePlatform.IronTeeth",148,164,7);Create("Platform.IronTeeth",148,164,9);
        Create("Path",148,164,10);
        for(int z=3;z<6;z++)Create("ConcreteBlock.IronTeeth",151,164,z);
        Create("ConcreteOverhang8x1.IronTeeth",151,164,6);
        for(int y=164;y<172;y++)Create("Path",151,y,7);
        Create("PowerShaft.IronTeeth",151,166,3);Create("Tubeway.IronTeeth",151,167,3);
        foreach(var center in new[]{Basin,ControlBasin}) {
          for(int x=center.x-2;x<=center.x+2;x++)for(int y=center.y-2;y<=center.y+2;y++) {
            bool edge=Math.Abs(x-center.x)==2||Math.Abs(y-center.y)==2;
            Create("ConcreteBlock.IronTeeth",x,y,3);
            if(edge) {
              var wall=Create((x==center.x-2?"ReinforcedDamBlock":"ConcreteBlock")+".IronTeeth",x,y,4);
              if(x==center.x&&y==center.y-2)_spillWalls.Add(wall);
            } else _water.AddCleanWater(new Vector3Int(x,y,4),.9f);
          }
        }
        Pass("12-layer masonry tower; native stairs, deck platforms, eight-tile overhang and clear shaft/tubeway bays placed");
      }
      _camera.MoveTargetTo(new Vector3(148,7,166));_camera.SetZoomLevel(18,0);
      _camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _phaseStart=_clock.PartialDayNumber;_phase=_reload?2:0;_speed.ChangeSpeed(3);
    }
    private void StartWalking() {
      _walker=_entities.Entities.Where(e=>e.HasComponent<Worker>()&&e.GetComponent<Worker>().WorkerType=="Beaver")
        .Select(e=>e.GetComponent<ControllableCharacter>()).First();
      _walker.GetComponent<Worker>().Unemploy();
      Require(_walker.GetAnimationNames().Contains("BeaverAdult_idle"),"Adult animation missing");
      _walker.ChangeAnimation("BeaverAdult_idle");
      foreach(var p in new[]{new Vector3Int(149,162,3),new Vector3Int(149,164,3),
        new Vector3Int(148,162,7),new Vector3Int(149,164,7),new Vector3Int(151,171,7),
        new Vector3Int(147,157,3)})_destinations.Enqueue(p);
      NextWalk();
    }
    private void NextWalk() {
      if(_destinations.Count==0) {_walker.ReleaseControl();_walker=null;return;}
      _target=NavigationCoordinateSystem.GridToWorld(_destinations.Dequeue());
      Require(_navigation.FindPathUnlimitedRange(_walker.Transform.position,_target,new List<PathCorner>(),out var distance),
        "No native route to "+_target);
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_target));
    }
    private void Finish() {
      var record=new StructuralSaveRecord {Entities=_created.Select(b=>new StructuralEntityRecord {
        Id=b.GetComponent<EntityComponent>().EntityId.ToString(),Template=b.GetComponent<TemplateSpec>().TemplateName,
        Coordinates=b.Coordinates}).ToArray()};
      if(!_reload)File.WriteAllText(RecordPath,JsonConvert.SerializeObject(record,Formatting.Indented));
      _finished=true;_speed.ChangeSpeed(0);
      string name=_reload?"Structures continuity - verified":"Structures - verified";
      _saver.QueueSave(new SaveReference(name,_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Structures] ALL "+(_reload?"RELOAD":"PLACEMENT")+", WATER AND WALKING CHECKS PASSED AND SAVED"));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(_frame<240)return;
        float hours=(_clock.PartialDayNumber-_phaseStart)*24;
        if(_phase==0&&hours>.5f) {
          float depth=_waterMap.WaterDepth(Basin);
          Require(depth>.85f&&depth<=.901f,"Solid concrete/reinforced walls did not retain the test water: "+depth);
          Require(_waterMap.WaterDepth(ControlBasin)>.85f,"Native control basin did not retain its initial water");
          foreach(var wall in _spillWalls)Remove(wall);
          Create("ConcreteOverflowDam.IronTeeth",143,168,4);
          Create("Dam.IronTeeth",149,168,4);
          Pass("solid concrete and reinforced walls retain actual native water");
          _phase=1;_phaseStart=_clock.PartialDayNumber;
        } else if(_phase==1&&hours>2) {
          float depth=_waterMap.WaterDepth(Basin);
          float controlDepth=_waterMap.WaterDepth(ControlBasin);
          Debug.Log("[DeepFrontier Structures] Overflow samples: concrete="+depth+" native="+controlDepth+
            " concreteSurface="+_waterMap.WaterHeightOrFloor(Basin)+
            " nativeSurface="+_waterMap.WaterHeightOrFloor(ControlBasin));
          // Native arrays include a border margin. Use the native index service.
          Require(_flowLimits.HeightLimits[_indices.CoordinatesToIndex3D(new Vector3Int(143,168,4))]==.65f,
            "Concrete crest is absent from native water limits");
          Require(_flowLimits.HeightLimits[_indices.CoordinatesToIndex3D(new Vector3Int(149,168,4))]==.65f,
            "Vanilla control crest is absent from native water limits");
          Require(depth>=0&&depth<.69f,"Overflow dam did not release the excess test water: "+depth);
          Require(Math.Abs(depth-controlDepth)<.025f,"Concrete spill behavior differs from the native dam control");
          Pass("concrete overflow matches the vanilla dam in both actual crest registration and transient reservoir drawdown");
          foreach(var center in new[]{Basin,ControlBasin})
            for(int x=center.x-1;x<=center.x+1;x++)for(int y=center.y-1;y<=center.y+1;y++)
              _water.AddCleanWater(new Vector3Int(x,y,4),.35f);
          _phase=4;_phaseStart=_clock.PartialDayNumber;
        } else if(_phase==4&&hours>1) {
          float depth=_waterMap.WaterDepth(Basin),controlDepth=_waterMap.WaterDepth(ControlBasin);
          Require(depth>.30f&&depth<.55f,"Below-crest pool did not retain its added water: "+depth+" native="+controlDepth);
          Require(Math.Abs(depth-controlDepth)<.025f,"Below-crest retention differs from native control");
          Pass("settled below-crest pool retains water with native dam parity: concrete="+depth+" native="+controlDepth);
          _phase=2;_phaseStart=_clock.PartialDayNumber;
        } else if(_phase==2) {StartWalking();_phase=3;_phaseStart=_clock.PartialDayNumber;}
        if(_walker&&Vector3.Distance(_walker.Transform.position,_target)<.18f) {
          _walks++;Pass("actual beaver reached "+_target);NextWalk();
        }
        if(_phase==3&&_walks==6)Finish();
        Require(hours<36,"Structural fixture exceeded phase time limit");
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);
        if(_walker)_walker.ReleaseControl();
        Debug.LogError("[DeepFrontier Structures] FAILED: "+error);
      }
    }
  }
}
