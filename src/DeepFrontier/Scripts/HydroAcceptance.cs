using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.Automation;
using Timberborn.AutomationBuildings;
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
using Timberborn.Navigation;
using Timberborn.PathSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class HydroAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(args.Contains("-deepFrontierHydro")||args.Contains("-deepFrontierHydroReload"))
        Bind<HydroAcceptance>().AsSingleton();
    }
  }
  internal sealed class HydroSaveRecord {
    public StructuralEntityRecord[] Entities;
    public float Limit;
    public bool Closed,LeverOn;
  }
  internal sealed class HydroAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly INavigationService _navigation;
    private readonly INavMeshService _nav;
    private readonly IWaterService _water;
    private readonly IThreadSafeWaterMap _map;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly NonlinearAnimationManager _animation;
    private readonly IBlockService _blocks;
    private readonly List<BlockObject> _created=new();
    private readonly List<BlockObject> _outletPlug=new();
    private readonly List<object> _samples=new();
    private readonly Queue<Vector3> _destinations=new();
    private readonly bool _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierHydroReload");
    private static readonly Vector3Int Anchor=new(144,165,3);
    private const string TurbineId="ReinforcedHydroTurbine.IronTeeth";
    private static readonly string Folder=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs");
    private static readonly string RecordPath=Path.Combine(Folder,"hydro-reload-expectations.json");
    private BlockObject _building;
    private HydroTurbine _turbine;
    private Lever _lever;
    private MechanicalNode _shaft;
    private ControllableCharacter _walker;
    private Vector3 _target;
    private Transform _runner;
    private IAnimator _modelAnimator;
    private readonly float[] _audioBuffer=new float[256];
    private float _phaseRealStart,_lastAnimationTime,_playedSeconds,_referenceSeconds,_peakAudioRms;
    private Quaternion _rotorStart;
    private float _phaseStart,_lastSample,_quarterFlow,_oneFlow,_waterStart;
    private float _peakFlow,_peakPower,_blockedSettledSince;
    private int _frame,_phase,_walks;
    private bool _finished,_started,_moved,_powered;
    public HydroAcceptance(EntityRegistry entities,EntityService entityService,TemplateService templates,
      BlockObjectFactory factory,BlockValidator validator,BlockObjectValidationService validation,
      INavigationService navigation,INavMeshService nav,IWaterService water,IThreadSafeWaterMap map,
      SpeedManager speed,IDayNightCycle clock,CameraService camera,GameSaver saver,GameLoader loader,
      NonlinearAnimationManager animation,IBlockService blocks) {
      _entities=entities;_entityService=entityService;_templates=templates;_factory=factory;
      _validator=validator;_validation=validation;_navigation=navigation;_nav=nav;_water=water;
      _map=map;_speed=speed;_clock=clock;_camera=camera;_saver=saver;_loader=loader;_animation=animation;_blocks=blocks;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message)=>Debug.Log("[DeepFrontier Hydro] PASS "+message);
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&
        e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),"Fixture marker missing");
      _speed.ChangeSpeed(0);
      if(_reload) {
        var saved=JsonConvert.DeserializeObject<HydroSaveRecord>(File.ReadAllText(RecordPath));
        foreach(var record in saved.Entities) {
          var entity=_entities.Entities.Single(e=>e.GetComponent<EntityComponent>().EntityId.ToString()==record.Id);
          var block=entity.GetComponent<BlockObject>();
          Require(entity.GetComponent<TemplateSpec>().TemplateName==record.Template&&block.Coordinates==record.Coordinates,
            "Saved hydro identity/position changed");
          _created.Add(block);
        }
        BindFixture();
        Require(_turbine.DischargeLimit==saved.Limit&&_turbine.ManuallyClosed==saved.Closed&&_lever.IsOn==saved.LeverOn,
          "Saved turbine or lever setting changed");
        Require(_building.GetComponent<Automatable>().Input==_lever.GetComponent<Automator>(),
          "Saved native automation connection changed");
        Require(!_building.GetComponent<PausableBuilding>().Paused,"Saved operating turbine was paused");
        Pass("exact saved identities, positions, discharge limit, manual closure and native automation wiring restored");
      }
    }
    private BlockObjectSpec Spec(string id) {
      var template=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      return _templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var spec=Spec(id);var p=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,p),"Native placement rejected "+id+" "+p.Coordinates+" "+orientation+
        "; invalid cells "+string.Join(",",spec.GetBlocks(p).Where(b=>!_validator.BlockValidWithoutUnfinishedStackable(b))
          .Take(8).Select(b=>b.Coordinates.ToString())));
      var b=_factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),p);
      Require(_validation.IsValid(b),"Native additional placement requirements rejected "+id);
      _created.Add(b);return b;
    }
    private void Remove(BlockObject b) {_created.Remove(b);_entityService.Delete(b);}
    private void BindFixture() {
      _building=_created.Single(b=>b.GetComponent<TemplateSpec>().TemplateName==TurbineId);
      _turbine=_building.GetComponent<HydroTurbine>();
      _lever=_created.Single(b=>b.HasComponent<Lever>()).GetComponent<Lever>();
      _shaft=_created.Single(b=>b.GetComponent<TemplateSpec>().TemplateName=="PowerShaft.IronTeeth")
        .GetComponent<MechanicalNode>();
      _runner=_building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true)
        .Single(t=>t.name=="#Hydro.TurbineRunner");
      _modelAnimator=_building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<MonoBehaviour>(true)
        .OfType<IAnimator>().Single();
      Require(_building.GetComponent<BuildingSpec>().LoopingSoundName=="Gristmill"&&
        _turbine.Spec.AnimationSpeedMultiplier==4,"Turbine sound/motion revision not installed");
    }
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      if(!_reload) {
        foreach(var placement in new[]{
          (Orientation.Cw0,144,165),(Orientation.Cw90,144,171),
          (Orientation.Cw180,151,174),(Orientation.Cw270,153,165)}) {
          // Keep every rotated footprint within the fixture's existing
          // cleared pad. Rotation occurs about the anchor, not its centre.
          var trial=Create(TurbineId,placement.Item2,placement.Item3,3,placement.Item1);
          Require(trial.GetComponent<HydroTurbine>().OutputHp==0,"Dry rotated turbine generates power");
          Remove(trial);
        }
        Pass("four native rotations and dry creation/deletion register and remove water obstacles");
        Create(TurbineId,Anchor.x,Anchor.y,Anchor.z);
        // The dam joins the cap on both sides, including empty cells inside
        // the larger artwork bounding box. The powerhouse is downstream.
        for(int x=141;x<=152;x++)for(int y=160;y<=167;y++) {
          if(x!=141&&x!=152&&y!=160&&y!=167)continue;
          if(y==167&&x>=144&&x<=147)continue;
          for(int z=3;z<23;z++)Create("ReinforcedDamBlock.IronTeeth",x,y,z);
        }
        for(int x=144;x<=147;x++)for(int z=9;z<23;z++)Create("ReinforcedDamBlock.IronTeeth",x,167,z);
        Create("DoublePlatform.IronTeeth",145,168,9);Create("Platform.IronTeeth",145,168,11);
        Create("Path",145,168,12);
        Create("Stairs.IronTeeth",152,170,3,Orientation.Cw180);
        Create("Platform.IronTeeth",152,171,3);Create("Stairs.IronTeeth",152,171,4,Orientation.Cw180);
        Create("DoublePlatform.IronTeeth",152,172,3);Create("Path",152,172,5);
        // The terrace is a player-path deck (2026-10-30): the open rail gets a path on its deck cell.
        {var deck=_building.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id=="Right7");
         var inside=_building.TransformCoordinates(deck.Inside);if(!_blocks.GetPathObjectAt(inside))Create("Path",inside.x,inside.y,inside.z);}
        Create("PowerShaft.IronTeeth",152,172,3);
        Create("Platform.IronTeeth",148,174,5);Create("Platform.IronTeeth",148,174,6);
        Create("Lever.IronTeeth",153,173,3);
        BindFixture();
        _turbine.SetClosed(true);_lever.SwitchState(true);
        _building.GetComponent<Automatable>().SetInput(_lever.GetComponent<Automator>());
      }
      _camera.MoveTargetTo(new Vector3(146,6,169));_camera.SetZoomLevel(22,0);
      _camera.HorizontalAngle=130;_camera.VerticalAngle=38;
      Phase(_reload?10:0);_started=true;_speed.ChangeSpeed(3);
    }
    private void Phase(int phase) {
      _phase=phase;_phaseStart=_clock.PartialDayNumber;_peakFlow=0;_peakPower=0;
      _blockedSettledSince=-1;
      _phaseRealStart=Time.unscaledTime;_lastAnimationTime=_modelAnimator.Time;
      _playedSeconds=0;_referenceSeconds=0;_peakAudioRms=0;
      _rotorStart=_runner.localRotation;_moved=false;_powered=false;
      Debug.Log("[DeepFrontier Hydro] Phase "+phase);
    }
    private void Fill() {
      // Seed a finite, declared reservoir, never an infinite source.
      for(int x=142;x<=151;x++)for(int y=161;y<=166;y++) {
        bool casing=x>=144&&x<=147&&y>=165;
        _water.AddCleanWater(new Vector3Int(x,y,casing?5:3),casing?17:19);
      }
    }
    private float Reservoir() {
      float volume=0;
      for(int x=142;x<=151;x++)for(int y=161;y<=166;y++) {
        bool casing=x>=144&&x<=147&&y>=165;
        var p=new Vector3Int(x,y,casing?5:3);
        volume+=_map.WaterDepth(p)+_map.ColumnOverflow(p);
      }
      return volume;
    }
    private void Port(string id,bool expected) {
      // Player-path terrace deck (PlatformDeck, 2026-10-30): the rail hides exactly
      // when actual player paths stand on the deck cell and its neighbour.
      var p=_building.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id==id);
      var a=_building.TransformCoordinates(p.Inside);var b=_building.TransformCoordinates(p.Outside);
      bool connected=_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a);
      var transforms=_building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true);
      bool hidden=p.HiddenNodes.All(name=>!transforms.Single(t=>t.name==name).gameObject.activeSelf);
      bool paths=IsPlayerPath(a)&&IsPlayerPath(b);
      Require(paths==expected&&hidden==expected&&(!expected||connected),"Turbine rail/path mismatch "+id);
    }
    private bool IsPlayerPath(Vector3Int c) {
      var o=_blocks.GetPathObjectAt(c);return o&&o.IsFinished&&o.HasComponent<PathSpec>();
    }
    private void CheckConnections() {
      Require(_shaft.Graph==_building.GetComponent<MechanicalNode>().Graph,"Native shaft graph did not connect");
      Port("Right7",true);Port("Right6",false);
      Pass("shaft connects; selected railing opens; adjacent railing stays; native stairs and deck/cap platform stacks fit");
    }
    private void CheckGeneration(float minimum) {
      Require(_peakFlow>minimum&&_peakPower>10,"No measured forward flow/power: "+_peakFlow+"/"+_peakPower);
      Require(_moved,"Native turbine runner did not animate");
      Require(_powered,"Native shaft graph never received generated power during this phase");
      Require(_referenceSeconds>.05f,"Insufficient observed animation playback");
      float playbackRatio=_playedSeconds/_referenceSeconds;
      Require(Mathf.Abs(playbackRatio-4)<.25f,"Native animation playback is not 4x: "+playbackRatio);
      Require(_peakAudioRms>.00001f,"No nonzero native turbine loop output observed");
      Pass("native turbine sound emits audio; measured animation multiplier "+playbackRatio+"; peak source RMS "+_peakAudioRms);
      Pass("measured flow "+_peakFlow+" m3/s; peak "+_peakPower+" hp; actual rotor movement and shaft supply");
    }
    private AudioSource[] TurbineLoops()=>_building.GameObject.GetComponentsInChildren<AudioSource>(true)
      .Where(source=>source.loop).ToArray();
    private void CheckSilent() {
      Require(TurbineLoops().All(source=>!source.isPlaying||source.volume<=.0001f),
        "Native turbine loop did not fade to silence");
      Require(!_modelAnimator.Enabled,"Stopped turbine animator remains enabled");
      Pass("native turbine loop silent after fade; animation stopped");
    }
    private void StartWalking() {
      _walker=_entities.Entities.Where(e=>e.HasComponent<Worker>()&&e.GetComponent<Worker>().WorkerType=="Beaver")
        .Select(e=>e.GetComponent<ControllableCharacter>()).First();
      _walker.GetComponent<Worker>().Unemploy();_walker.ChangeAnimation("BeaverAdult_idle");
      _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(new Vector3Int(152,169,3)));
      // Terrace deck cells, walked as grid cells (player-path deck since 2026-10-30).
      foreach(var cell in new[]{new Vector3Int(7,7,2),new Vector3Int(4,9,2),new Vector3Int(6,5,2)})
        _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(_building.TransformCoordinates(cell)));
      _destinations.Enqueue(NavigationCoordinateSystem.GridToWorld(new Vector3Int(152,169,3)));
      NextWalk();
    }
    private void NextWalk() {
      if(_destinations.Count==0){_walker.ReleaseControl();_walker=null;return;}
      _target=_destinations.Dequeue();
      Require(_navigation.FindPathUnlimitedRange(_walker.Transform.position,_target,new List<PathCorner>(),out var distance),
        "No native route to "+_target);
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_target));
    }
    private void WriteMeasurements() {
      File.WriteAllText(Path.Combine(Folder,_reload?"hydro-reload-measurements.json":"hydro-measurements.json"),
        JsonConvert.SerializeObject(new {scope="Explicit finite-water native turbine fixture; economic and pump-loop balance separate",
          samples=_samples},Formatting.Indented));
    }
    private void Finish() {
      Require(_walks==5,"Not all five walking targets reached");
      CheckSilent();
      _turbine.SetDischargeLimit(.75f);_turbine.SetClosed(true);_lever.SwitchState(true);
      _speed.ChangeSpeed(0);_finished=true;WriteMeasurements();
      if(!_reload)File.WriteAllText(RecordPath,JsonConvert.SerializeObject(new HydroSaveRecord {
        Entities=_created.Select(b=>new StructuralEntityRecord {
          Id=b.GetComponent<EntityComponent>().EntityId.ToString(),
          Template=b.GetComponent<TemplateSpec>().TemplateName,Coordinates=b.Coordinates}).ToArray(),
        Limit=_turbine.DischargeLimit,Closed=_turbine.ManuallyClosed,LeverOn=_lever.IsOn},Formatting.Indented));
      _saver.QueueSave(new SaveReference(_reload?"Hydro turbine continuity - verified":"Hydro turbine - verified",
        _loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Hydro] ALL "+(_reload?"RELOAD":"MAIN")+" CHECKS PASSED AND SAVED"));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(!_started)return;
        float hours=(_clock.PartialDayNumber-_phaseStart)*24;
        float realSeconds=Time.unscaledTime-_phaseRealStart;
        float played=_modelAnimator.Time-_lastAnimationTime;
        _lastAnimationTime=_modelAnimator.Time;
        if(hours>.15f&&_turbine.OutputHp>0) {
          _playedSeconds+=played;
          _referenceSeconds+=Time.deltaTime*_animation.SpeedMultiplier*
            Mathf.Min(_turbine.ActualFlow/_turbine.Spec.MaxDischarge,1);
        }
        _moved|=Quaternion.Angle(_rotorStart,_runner.localRotation)>.5f;
        var node=_building.GetComponent<MechanicalNode>();
        _powered|=node.Actuals.PowerOutput>0&&node.Graph.PowerSupply>0;
        if((_clock.PartialDayNumber-_lastSample)*24>.05f) {
          _lastSample=_clock.PartialDayNumber;
          var loops=TurbineLoops();
          float audioRms=0;
          foreach(var source in loops) {
            Require(source.clip!=null&&(source.clip.name=="Environment.Buildings.Loop.Gristmill"||
              source.clip.name.StartsWith("Environment.Buildings.Loop.Gristmill.",StringComparison.Ordinal)),
              "Unexpected turbine loop clip");
            Require(source.spatialBlend==1&&source.outputAudioMixerGroup!=null,
              "Turbine audio must use native spatialization and mixer");
            source.GetOutputData(_audioBuffer,0);
            audioRms=Mathf.Max(audioRms,Mathf.Sqrt(_audioBuffer.Sum(value=>value*value)/_audioBuffer.Length));
          }
          _peakAudioRms=Mathf.Max(_peakAudioRms,audioRms);
          _samples.Add(new {phase=_phase,hours=_clock.PartialDayNumber*24,limit=_turbine.DischargeLimit,
            closed=_turbine.GateIsClosed,flow=_turbine.ActualFlow,head=_turbine.AvailableHead,
            upstream=_turbine.UpstreamHeight,downstream=_turbine.DownstreamHeight,hp=_turbine.OutputHp,
            nativeHp=node.Actuals.PowerOutput,networkHp=node.Graph.PowerSupply,
            channelFlows=_turbine.ChannelFlows.ToArray(),channelHeads=_turbine.ChannelHeads.ToArray(),
            outletDepths=_turbine.Outlets.Select(p=>_map.WaterDepth(p)).ToArray(),
            reservoir=Reservoir(),state=_turbine.State,
            animationTime=_modelAnimator.Time,animationEnabled=_modelAnimator.Enabled,
            playedSeconds=_playedSeconds,referenceSeconds=_referenceSeconds,audioRms,
            audio=loops.Select(source=>new {clip=source.clip.name,playing=source.isPlaying,
              volume=source.volume,muted=source.mute,spatialBlend=source.spatialBlend,
              mixer=source.outputAudioMixerGroup.name}).ToArray()});
          if(hours>.15f) {
            _peakFlow=Mathf.Max(_peakFlow,_turbine.ActualFlow);_peakPower=Mathf.Max(_peakPower,_turbine.OutputHp);
            float expected=Enumerable.Range(0,_turbine.Gates.Length).Sum(i=>
              Mathf.Min(_turbine.ChannelFlows[i],_turbine.Spec.MaxDischarge/_turbine.Gates.Length)*
              Mathf.Min(_turbine.ChannelHeads[i],_turbine.Spec.MaxGeneratingHead)*_turbine.Spec.HpPerFlowAndHead);
            if(!_turbine.GateIsClosed&&_turbine.Intakes.All(p=>_map.WaterDepth(p)>0))
              Require(Math.Abs(_turbine.OutputHp-expected)<.01f,"Measured flow/head power identity differs");
          }
        }
        if(_walker&&Vector3.Distance(_walker.Transform.position,_target)<.18f) {
          _walks++;Pass("actual beaver reached "+_target);NextWalk();
        }
        if(_phase==0&&hours>.25f) {
          CheckConnections();
          Require(_turbine.OutputHp==0&&_turbine.ActualFlow==0,"Dry/closed turbine generated power");
          Pass("dry turbine supplies zero hp");Fill();Phase(1);
        } else if(_phase==1&&hours>.5f) {
          _waterStart=Reservoir();
          Require(_turbine.Intakes.All(p=>_map.WaterDepth(p)>18)&&_waterStart>1090,"Closed dam lost seeded reservoir water: "+_waterStart);
          Require(_turbine.OutputHp==0&&_turbine.ActualFlow==0,"Closed full reservoir generates");
          Pass("closed concrete turbine cap retains actual native reservoir water");
          _turbine.SetDischargeLimit(.25f);_turbine.SetClosed(false);Phase(2);
        } else if(_phase==2&&hours>.5f) {
          CheckGeneration(.1f);_quarterFlow=_peakFlow;
          Require(_peakFlow<=.251f,"Quarter-rate discharge exceeds its setting: "+_peakFlow);
          _turbine.SetDischargeLimit(1);Phase(3);
        } else if(_phase==3&&hours>.5f) {
          CheckGeneration(.6f);_oneFlow=_peakFlow;
          Require(_oneFlow>_quarterFlow*2&&_oneFlow<=1.001f,"Discharge control did not scale");
          Require(Reservoir()<_waterStart-2,"Generation did not release actual reservoir water");
          _turbine.SetClosed(true);Phase(4);
        } else if(_phase==4&&hours>.4f&&realSeconds>4.5f) {
          CheckSilent();
          Require(_peakPower==0&&_peakFlow==0&&!_moved,"Closed turbine still flows, generates or rotates");
          Pass("manual closure stops measured flow, generation and rotor");
          _lever.SwitchState(false);_turbine.SetClosed(false);Phase(5);
        } else if(_phase==5&&hours>.4f&&realSeconds>4.5f) {
          CheckSilent();
          Require(_turbine.GateIsClosed&&_peakFlow==0&&_peakPower==0,"Native Off automation failed to close");
          Pass("native lever Off closes outlet");
          _lever.SwitchState(true);_turbine.SetDischargeLimit(3);Phase(6);
        } else if(_phase==6&&hours>.4f) {
          CheckGeneration(1.2f);Require(_peakFlow<=3.001f,"Three-rate discharge exceeds setting");
          // The band the 9,600 hp rating tested (8,000-9,600 hp), scaled to the rated output.
          float rated=_turbine.GetComponent<MechanicalNodeSpec>().PowerOutput;
          Require(_peakPower>=rated*8000f/9600f&&_peakPower<=rated*1.00001f,"Tall reservoir did not reach "+rated*8000f/9600f+"-"+rated+" hp: "+_peakPower);
          Require(_turbine.ChannelFlows.All(f=>f>1.4f&&f<=1.501f),"Both water lanes must share the total 3 m3/s limit");
          Require(_turbine.Outlets.All(p=>_map.WaterDepth(p)>.05f),"Visible mouth is not wet across both cells");
          Pass("high-head 3 m3/s total reaches 8–10k hp; both native outlet cells carry water");
          Pass("native lever On resumes controlled generation");
          _building.GetComponent<PausableBuilding>().Pause();Phase(12);
        } else if(_phase==12&&hours>.4f&&realSeconds>4.5f) {
          CheckSilent();
          Require(_turbine.GateIsClosed&&_peakFlow==0&&_peakPower==0&&!_moved&&
            node.Actuals.PowerOutput==0,"Native pause did not stop outlet, rotor and shaft supply");
          Pass("native Pause closes the outlet and stops actual rotor and shaft supply");
          _building.GetComponent<PausableBuilding>().Resume();Phase(13);
        } else if(_phase==13&&hours>.4f) {
          CheckGeneration(_reload?.3f:1.2f);
          Require(_peakFlow<=_turbine.DischargeLimit+.001f,"Resumed discharge exceeds saved limit");
          Pass("native Resume restores the previous limit and generation");
          if(_reload) {
            _turbine.SetDischargeLimit(3);Phase(14);return;
          }
          _turbine.SetClosed(true);
          for(int x=145;x<=146;x++)for(int z=3;z<5;z++)
            _outletPlug.Add(Create("ConcreteBlock.IronTeeth",x,171,z));
          _turbine.SetClosed(false);Phase(7);
        } else if(_phase==7&&hours>1) {
          // The finite conduit must fill and pressurize before inflow stops.
          // Require a stable zero interval rather than one favorable frame.
          if(_turbine.ActualFlow>=.005f||_turbine.OutputHp>=1) {
            _blockedSettledSince=-1;
            Require(hours<6,"Blocked outlet still generates after pressure settling: "+_turbine.ActualFlow+"/"+_turbine.OutputHp);
            return;
          }
          if(_blockedSettledSince<0)_blockedSettledSince=hours;
          if(hours-_blockedSettledSince<.25f)return;
          Pass("blocked outlet settles to zero delivered flow and zero generation");
          _turbine.SetClosed(true);foreach(var b in _outletPlug)Remove(b);_outletPlug.Clear();
          StartWalking();Phase(8);
        } else if(_phase==8&&_walker==null&&hours>.2f)Finish();
        else if(_phase==10&&hours>.3f&&realSeconds>4.5f) {
          CheckSilent();
          CheckConnections();Require(_turbine.GateIsClosed&&_turbine.OutputHp==0,"Saved closed gate did not remain closed");
          _turbine.SetClosed(false);Phase(11);
        } else if(_phase==11&&hours>.5f) {
          CheckGeneration(.3f);Require(_peakFlow<=.751f,"Saved discharge setting not enforced");
          _building.GetComponent<PausableBuilding>().Pause();Phase(12);
        } else if(_phase==14&&hours>.5f) {
          CheckGeneration(1.2f);Require(_peakFlow<=3.001f,"Full-flow presentation exceeds discharge limit");
          _turbine.SetClosed(true);StartWalking();Phase(8);
        }
        if(hours>24)throw new InvalidOperationException("Hydro fixture phase timed out: "+_phase);
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);WriteMeasurements();
        Debug.LogError("[DeepFrontier Hydro] FAILED: "+error);
      }
    }
  }
}
