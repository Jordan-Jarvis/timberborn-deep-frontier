using System;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.Goods;
using Timberborn.MechanicalSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterBuildings;
using Timberborn.WaterContaminationBuildings;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Explicit disposable-fixture continuation. Never registered in normal play.
  [Context("Game")]
  public sealed class AquacultureContinuityAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierAquacultureContinuity"))
        Bind<AquacultureContinuityAcceptance>().AsSingleton();
    }
  }

  internal sealed class AquacultureContinuityAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private BlockObject _fishery,_hatchery;
    private Manufactory _fish,_nursery;
    private WorkshopReservoir _reservoir;
    private MechanicalNode _generator;
    private int _frame,_phase,_phaseProducts,_fishBatches,_juvenileBatches;
    private float _phaseTime,_progress,_wheelTime,_normalOutput;
    private bool _finished;
    public AquacultureContinuityAcceptance(EntityRegistry entities,SpeedManager speed,IDayNightCycle clock,CameraService camera,GameSaver saver,GameLoader loader) {
      _entities=entities;_speed=speed;_clock=clock;_camera=camera;_saver=saver;_loader=loader;
    }
    public void PostLoad() {
      if(!_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"))
        throw new InvalidOperationException("Aquaculture continuation requires the marked disposable settlement");
    }
    private BlockObject Find(string id) => _entities.Entities.Single(e=>e.HasComponent<TemplateSpec>()&&e.GetComponent<TemplateSpec>().TemplateName==id).GetComponent<BlockObject>();
    private void Phase(int phase) {_phase=phase;_phaseTime=_clock.PartialDayNumber;_phaseProducts=_fishBatches;}
    private bool HasFinished(string id,Vector3Int coordinates) => _entities.Entities.Any(e=>e.HasComponent<TemplateSpec>()&&e.GetComponent<TemplateSpec>().TemplateName==id
      &&e.GetComponent<BlockObject>().Coordinates==coordinates&&e.GetComponent<BlockObject>().IsFinished);
    // The fixture loads "Hatchery acceptance - verified", saved by the hatchery
    // acceptance right after it placed these objects. Native
    // BlockObjectBatchLoader deletes a loaded object whose support is not yet
    // added, so each deck path and the platform stack on the dock slab must
    // still exist after this fresh-process load.
    private void RequireSavedHatcheryDeck() {
      var missing=FisheryAcceptance.HatcheryPathCells().Select(c=>_hatchery.TransformCoordinates(c)).Where(c=>!HasFinished("Path",c)).ToList();
      foreach(var (id,z) in new[]{("DoublePlatform.IronTeeth",3),("Platform.IronTeeth",5),("Path",6)})
        if(!HasFinished(id,new Vector3Int(189,162,z)))missing.Add(new Vector3Int(189,162,z));
      if(missing.Count>0)throw new InvalidOperationException("Reload deleted hatchery deck objects at "+string.Join(", ",missing));
      Debug.Log("[DeepFrontier Continuity] PASS all "+FisheryAcceptance.HatcheryPathCells().Count+" hatchery deck/bank paths and the dock platform stack survived the fresh-process reload");
    }
    private void Setup() {
      _speed.ChangeSpeed(0);
      _fishery=Find("FisheryWorks.IronTeeth");_hatchery=Find("FishHatchery.IronTeeth");
      _fish=_fishery.GetComponent<Manufactory>();_nursery=_hatchery.GetComponent<Manufactory>();_reservoir=_fishery.GetComponent<WorkshopReservoir>();
      // The saved generator at the end of the Fishery's shaft line (from its installed shaft face).
      var generator=FisheryAcceptance.ShaftLine(_fishery).Generator;
      _generator=_entities.Entities.Single(e=>e.HasComponent<BlockObject>()&&e.GetComponent<BlockObject>().Coordinates==generator
        &&e.GetComponent<TemplateSpec>().TemplateName=="DevPowerGenerator").GetComponent<MechanicalNode>();
      _normalOutput=_generator.OutputMultiplier;
      if(_normalOutput<=0)throw new InvalidOperationException("Saved power fixture has no output");
      if(!_fishery.GetComponent<PausableBuilding>().Paused||!_hatchery.GetComponent<PausableBuilding>().Paused)
        throw new InvalidOperationException("Expected both saved workshops paused");
      if(_nursery.CurrentRecipe.Id!="JuvenileFish"||_nursery.Inventory.AmountInStock("JuvenileFish")!=2||_nursery.Inventory.AmountInStock("FreshFish")!=1||_nursery.Inventory.AmountInStock("Algae")!=1||_nursery.Inventory.AmountInStock("Water")!=30)
        throw new InvalidOperationException("Native hatchery recipe or saved stock changed");
      var waterSite=_hatchery.GetComponent<WaterDepthWorkCells>();
      if(_hatchery.TransformCoordinates(waterSite.Spec.WorkCells[0])!=new Vector3Int(188,161,2)||waterSite.IsBlockedByDepth||_hatchery.GetComponent<ContaminationBlockableBuilding>().IsBlocked)
        throw new InvalidOperationException("Saved hatchery water coordinate or contamination state changed");
      RequireSavedHatcheryDeck();
      var header=_hatchery.GetComponent<WorkshopReservoir>();
      if(header.StoredAmount!=30||!header.SurfacesVisible||header.Flowing)throw new InvalidOperationException("Hatchery saved header tank state changed");
      if(_reservoir.StoredAmount!=45||!_reservoir.SurfacesVisible||_reservoir.Flowing||_reservoir.WheelsEnabled)
        throw new InvalidOperationException("Saved paused Fishery water state changed");
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<ShoreFishing>()))e.GetComponent<PausableBuilding>().Pause();
      _fish.ProductionFinished+=(sender,args)=>{_fishBatches++;Debug.Log("[DeepFrontier Continuity] FISH BATCH "+_fishBatches);};
      _nursery.ProductionFinished+=(sender,args)=>{_juvenileBatches++;Debug.Log("[DeepFrontier Continuity] HATCHERY BATCH "+_juvenileBatches);};
      _camera.MoveTargetTo(new Vector3(166,7,164));_camera.SetZoomLevel(20,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      Debug.Log("[DeepFrontier Continuity] PASS saved hatchery stock/recipe/water coordinate and paused Fishery reservoirs");
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        ++_frame;
        if(_frame==60)Setup();
        if(_frame==180) {
          var folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding/docs/art/reviews/2026-10-19-fishery-waterfront");
          ScreenCapture.CaptureScreenshot(Path.Combine(folder,"fishery-decks-reloaded.png"));
          _hatchery.GetComponent<PausableBuilding>().Resume();
          // Native Pause itself is a BlockableObject blocker. Evaluate the
          // aggregate water/site gate only after removing that saved pause.
          if(!_hatchery.GetComponent<BlockableObject>().IsUnblocked)
            throw new InvalidOperationException("Reloaded hatchery remains blocked after resuming in clean water");
          Debug.Log("[DeepFrontier Continuity] PASS resumed hatchery clean-water site gate");
          Phase(1);_speed.ChangeSpeed(3);
        }
        if(_frame<=180)return;
        float hours=(_clock.PartialDayNumber-_phaseTime)*24;
        if(hours>36)throw new InvalidOperationException("Aquaculture continuity phase timed out: "+_phase);
        if(_phase==1&&_juvenileBatches>0) {
          Debug.Log("[DeepFrontier Continuity] PASS hatchery resumed real juvenile production after fresh process reload");
          _hatchery.GetComponent<PausableBuilding>().Pause();
          _fishery.GetComponent<PausableBuilding>().Resume();
          foreach(var w in _fishery.GetComponent<Workplace>().AssignedWorkers.ToArray())w.Unemploy();
          foreach(var w in _entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").Take(3)) {
            w.Unemploy();w.EmployAt(_fishery.GetComponent<Workplace>());
          }
          Phase(2);
        } else if(_phase==2&&_reservoir.Flowing) {
          _generator.SetOutputMultiplier(0);Phase(3);
        } else if(_phase==3&&hours>=.25f) {
          if(_fishery.GetComponent<MechanicalNode>().Graph.PowerSupply!=0||_fish.IsReadyToProduce||_reservoir.Flowing||_reservoir.WheelsEnabled)
            throw new InvalidOperationException("Unpowered fishery remains productive or visibly circulates");
          _progress=_fish.ProductionProgress;_wheelTime=_reservoir.WheelTimes.Single();Phase(4);
        } else if(_phase==4&&hours>=.5f) {
          if(_fish.ProductionProgress!=_progress||_fishBatches!=_phaseProducts||_reservoir.WheelTimes.Single()!=_wheelTime||_reservoir.Flowing)
            throw new InvalidOperationException("Unpowered Fishery progressed or animated");
          Debug.Log("[DeepFrontier Continuity] PASS zero shaft power stops production, cascade and native wheel");
          _generator.SetOutputMultiplier(_normalOutput);Phase(5);
        } else if(_phase==5&&_fishBatches>_phaseProducts) {
          Debug.Log("[DeepFrontier Continuity] PASS restored shaft power completes the interrupted batch");Phase(6);
        } else if(_phase==6&&!_fish.HasAllIngredients&&_fish.ProcessedGoods.Count==0&&!_reservoir.Flowing&&!_reservoir.WheelsEnabled) {
          _progress=_fish.ProductionProgress;_wheelTime=_reservoir.WheelTimes.Single();Phase(7);
        } else if(_phase==7&&hours>=.5f) {
          if(_fish.HasAllIngredients||_fish.ProductionProgress!=_progress||_fishBatches!=_phaseProducts||_reservoir.Flowing||_reservoir.WheelsEnabled||_reservoir.WheelTimes.Single()!=_wheelTime)
            throw new InvalidOperationException("Missing-ingredient Fishery progressed or animated");
          Debug.Log("[DeepFrontier Continuity] PASS exhausted real inputs stop production, cascade and native wheel");
          _fish.Inventory.GiveExisting(new GoodAmount("JuvenileFish",2));_fish.Inventory.GiveExisting(new GoodAmount("Algae",2));Phase(8);
        } else if(_phase==8&&_fishBatches>_phaseProducts) {
          Debug.Log("[DeepFrontier Continuity] PASS replenished ingredients resume real fish production");
          _fishery.GetComponent<PausableBuilding>().Pause();_speed.ChangeSpeed(0);_finished=true;
          _saver.QueueSave(new SaveReference("Aquaculture continuity - verified",_loader.LoadedSave.SettlementReference),()=>Debug.Log("[DeepFrontier Continuity] ALL RELOAD, POWER AND INPUT CHECKS PASSED AND SAVED"));
        }
        if(_frame%1800==0)Debug.Log($"[DeepFrontier Continuity] phase={_phase}, elapsedHours={hours}, hatcheryBatches={_juvenileBatches}, fishBatches={_fishBatches}, progress={_fish.ProductionProgress}, water={_reservoir.StoredAmount}");
      } catch(Exception e) {_finished=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Continuity] FAILED: "+e);}
    }
  }
}
