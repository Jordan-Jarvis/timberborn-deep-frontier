using System;
using System.IO;
using System.Linq;
using System.Collections.Generic;
using Bindito.Core;
using Timberborn.BehaviorSystem;
using Timberborn.BlockSystem;
using Timberborn.BlockingSystem;
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
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.PathSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WaterBuildings;
using Timberborn.WaterContaminationBuildings;
using Timberborn.WorkSystem;
using Timberborn.Workshops;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class FisheryAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierFisheryAcceptance")||Environment.GetCommandLineArgs().Contains("-deepFrontierFisheryReload")||Environment.GetCommandLineArgs().Contains("-deepFrontierAquacultureBootstrap")||Environment.GetCommandLineArgs().Contains("-deepFrontierHatcheryAcceptance"))
        Bind<FisheryAcceptance>().AsSingleton();
    }
  }
  internal sealed class FisheryAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _registry;private readonly BlockObjectFactory _factory;private readonly TemplateService _templates;
    private readonly BlockValidator _validator;private readonly BlockObjectValidationService _objects;private readonly IBlockService _blocks;
    private readonly ITerrainService _terrain;private readonly IWaterService _water;private readonly IThreadSafeWaterMap _waterMap;
    private readonly SpeedManager _speed;private readonly CameraService _camera;private readonly GameSaver _saver;private readonly GameLoader _loader;
    private readonly IDayNightCycle _clock;
    private readonly INavMeshService _nav;private readonly INavigationService _navigation;
    // Fixture terrain shared by every run: the level bank at z 3, the road column x 173 and
    // the road row y 159 south of the Fishery. Everything placed against the Fishery follows
    // its installed blueprint (entrance, shaft face, deck openings and doors).
    private const int Ground=3,RoadX=173,RoadY=159;
    private static readonly Orientation[] Rotations={Orientation.Cw0,Orientation.Cw90,Orientation.Cw180,Orientation.Cw270};
    // World cells, walked in order.
    private ControllableCharacter _walker;private readonly Queue<Vector3Int> _walkTargets=new();private Vector3Int _walkTarget;private Vector3 _walkWorld;
    private BlockObject _building;private Manufactory _manufactory;private WorkshopReservoir _reservoir;private ShoreFishing _flag;
    private int _frame,_products,_deposited,_pauseFrame;private bool _failed,_reload,_bootstrap,_sawFlow,_saved,_pausedCheck;
    private float _startTime,_wheelTime;
    private int _shorePhase,_shoreFrame,_catchBefore;
    private BlockObject _hatchery;
    private BlockObject _walkBuilding;
    private Manufactory _hatcheryProduction;
    private int _hatcheryBatches;
    private int _hatcheryCreatedFrame;
    private bool _hatcheryOnly;
    private float _dryProgress;
    public FisheryAcceptance(EntityRegistry registry,BlockObjectFactory factory,TemplateService templates,BlockValidator validator,BlockObjectValidationService objects,IBlockService blocks,ITerrainService terrain,IWaterService water,IThreadSafeWaterMap waterMap,SpeedManager speed,CameraService camera,GameSaver saver,GameLoader loader,IDayNightCycle clock,INavMeshService nav,INavigationService navigation) {
      _registry=registry;_factory=factory;_templates=templates;_validator=validator;_objects=objects;_blocks=blocks;_terrain=terrain;_water=water;
      _nav=nav;_navigation=navigation;_waterMap=waterMap;_speed=speed;_camera=camera;_saver=saver;_loader=loader;_clock=clock;
    }
    public void PostLoad() {
      if(!_registry.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"))
        throw new InvalidOperationException("Fishery test requires the marked disposable settlement");
      _hatcheryOnly=Environment.GetCommandLineArgs().Contains("-deepFrontierHatcheryAcceptance");
      _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierFisheryReload")||_hatcheryOnly;
      _bootstrap=Environment.GetCommandLineArgs().Contains("-deepFrontierAquacultureBootstrap");
    }
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      if(!_validator.BlocksValid(spec,placement))throw new InvalidOperationException("Invalid native fixture placement: "+id+" at "+placement.Coordinates);
      var setup=new EntitySetup.Builder(template.Blueprint).AddInitComponent(new FinishedConstructionSiteInit());
      var result=_factory.CreateFinished(setup,placement);
      if(!_objects.IsValid(result))throw new InvalidOperationException("Native object requirements failed: "+id);
      Debug.Log("[DeepFrontier Fishery] PLACED "+id+" "+placement.Coordinates);return result;
    }
    private void Setup() {
      _speed.ChangeSpeed(0);
      if(_reload) {
        _building=_registry.Entities.Where(e=>e.HasComponent<TemplateSpec>()&&e.GetComponent<TemplateSpec>().TemplateName=="FisheryWorks.IronTeeth").Single().GetComponent<BlockObject>();
        _flag=_registry.Entities.Where(e=>e.HasComponent<ShoreFishing>()).Single().GetComponent<ShoreFishing>();
        if(!_flag.FishingSelected||!_building.GetComponent<PausableBuilding>().Paused)throw new InvalidOperationException("Saved fishing selection/factory pause changed");
      } else {
        foreach(var e in _registry.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))e.GetComponent<PausableBuilding>().Pause();
        // Fishery Works at (159,162,3), Cw0 unflipped. The fixture follows the installed
        // blueprint, not a size literal (11x8x4 since the 2026-10-30 compaction): ordinary
        // player paths join its native Entrance (the path cell in front of the ground door,
        // tools/native_entrance.mjs) to the road row; nothing else gives ground access.
        _building=Create("FisheryWorks.IronTeeth",159,162,3);_building.GetComponent<PausableBuilding>().Pause();
        // Freed ground, checked before the fixture builds on it: the rear supply cells inside
        // the bounds (validate_freed_cells.py), the two former front rows and the right column.
        FreedCellProbe.Require(_templates,_validator,_building,
          FreedCellProbe.Rect(5,7,7,7).Concat(FreedCellProbe.Rect(0,11,-2,-1)).Concat(FreedCellProbe.Rect(11,11,0,7)),
          "FisheryWorks",message=>Debug.Log("[DeepFrontier Fishery] PASS "+message));
        var entrance=_building.PositionedEntrance.Coordinates;
        if(entrance.z!=Ground||entrance.y<=RoadY||entrance.x>=RoadX)
          throw new InvalidOperationException("Fishery Entrance "+entrance+" is not on the bank north of the road row y "+RoadY+" and west of the road column x "+RoadX);
        var approach=GalleryStairs().Approach;
        for(int y=157;y<=170;y++)if(!_blocks.GetPathObjectAt(new Vector3Int(RoadX,y,Ground)))Create("Path",RoadX,y,Ground);
        for(int x=Math.Min(entrance.x,approach.x);x<RoadX;x++)Create("Path",x,RoadY,Ground);
        for(int y=RoadY+1;y<=entrance.y;y++)Create("Path",entrance.x,y,Ground);
        for(int x=174;x<=188;x++)Create("Path",x,170,Ground);
        var line=ShaftLine(_building);
        Create("PowerShaft.IronTeeth",line.Shaft.x,line.Shaft.y,line.Shaft.z);Create("DevPowerGenerator",line.Generator.x,line.Generator.y,line.Generator.z);
        // A native platform stack on the first free warehouse-terrace deck cell.
        var stack=_building.TransformCoordinates(TerraceBuildCells()[0]);
        Create("DoublePlatform.IronTeeth",stack.x,stack.y,stack.z);Create("Platform.IronTeeth",stack.x,stack.y,stack.z+2);Create("Path",stack.x,stack.y,stack.z+3);
        Debug.Log("[DeepFrontier Fishery] PASS native terrace platform stack");
        // A native water-filled pond in the disposable fixture. Its banks and
        // four-by-four bed are outside the earlier quarry's occupied footprint.
        for(int x=189;x<=192;x++)for(int y=166;y<=169;y++) {
          if(_terrain.GetTerrainHeight(new Vector3Int(x,y,0))!=3)throw new InvalidOperationException("Expected unmodified level test bank");
          _terrain.UnsetTerrain(new Vector3Int(x,y,2),1);
          _water.AddCleanWater(new Vector3Int(x,y,2),.8f);
        }
        _flag=Create("GathererFlag.IronTeeth",188,171,3).GetComponent<ShoreFishing>();
        if(_flag.FishingSelected)throw new InvalidOperationException("New gatherer must keep native gathering until fishing is selected");
        _flag.SelectFishing(true);
      }
      _manufactory=_building.GetComponent<Manufactory>();_reservoir=_building.GetComponent<WorkshopReservoir>();
      if(!_reload)_manufactory.SetRecipe(_manufactory.ProductionRecipes.Single(r=>r.Id=="FreshFish"));
      _manufactory.ProductionFinished+=(sender,args)=>{_products++;Debug.Log("[DeepFrontier Fishery] PRODUCED "+_manufactory.CurrentRecipe.Id);};
      _flag.Inventory.InventoryStockChanged+=(sender,args)=>{
        if(args.GoodAmount.GoodId=="FreshFish"&&args.GoodAmount.Amount>0){_deposited+=args.GoodAmount.Amount;Debug.Log("[DeepFrontier Fishery] FISH DEPOSITED "+args.GoodAmount.Amount);}
      };
      _camera.MoveTargetTo(new Vector3(166,7,164));_camera.SetZoomLevel(20,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      if(_reload) {_camera.MoveTargetTo(new Vector3(189,3,169));_camera.SetZoomLevel(12,0);}
      if(!_reload)_speed.ChangeSpeed(1);
    }
    public void UpdateSingleton() {
      if(_failed||_saved)return;
      try {
        ++_frame;if(_frame==60)Setup();
        if(_frame==240) {
          var power=_building.GetComponent<MechanicalNode>();
          if(power.Graph.PowerSupply<80)throw new InvalidOperationException("Fishery shaft supply not connected");
          Debug.Log("[DeepFrontier Fishery] PASS shaft supply="+power.Graph.PowerSupply+" hp");
          if(_reload) {
            VerifyWater(45);
            var active=_flag.GetComponent<Workplace>().AssignedWorkers.Any(w=>w.GetComponent<BehaviorManager>().IsRunningExecutor<ShoreCatchExecutor>());
            if(!active)throw new InvalidOperationException("Reload fixture lacks saved active catch");
            Debug.Log("[DeepFrontier Fishery] PASS saved reservoir surface heights, fishing selection and active catch");
            if(_hatcheryOnly) {SetupHatchery();_shorePhase=11;_shoreFrame=_frame;}
            _speed.ChangeSpeed(3);_startTime=_clock.PartialDayNumber;
          } else SetWater(0);
        }
        if(_hatcheryCreatedFrame>0&&_frame==_hatcheryCreatedFrame+120)AssignHatcheryWorkers();
        if(!_reload) {
          if(_frame==270)Capture("fishery-empty");
          if(_frame==300)SetWater(45);
          if(_frame==330)Capture("fishery-half");
          if(_frame==360)SetWater(90);
          if(_frame==390)Capture("fishery-full");
          if(_frame==420)StartProduction();
          if(_frame>420&&!_bootstrap&&_reservoir.Flowing&&!_pausedCheck&&_pauseFrame==0) {
            _wheelTime=_reservoir.WheelTimes.Single();_pauseFrame=_frame+60;
          }
          if(_pauseFrame>0&&_frame==_pauseFrame) {
            if(!_reservoir.Flowing||_reservoir.WheelTimes.Single()==_wheelTime)throw new InvalidOperationException("Native wheel time did not advance during water circulation");
            _sawFlow=true;Debug.Log("[DeepFrontier Fishery] PASS native wheel animation advances during real workshop production");
            Capture("fishery-working");_building.GetComponent<PausableBuilding>().Pause();_wheelTime=_reservoir.WheelTimes.Single();
          }
          if(_pauseFrame>0&&_frame==_pauseFrame+120) {
            if(_reservoir.Flowing||_reservoir.WheelsEnabled||_reservoir.WheelTimes.Single()!=_wheelTime)throw new InvalidOperationException("Paused fishery still circulates water");
            _pausedCheck=true;Debug.Log("[DeepFrontier Fishery] PASS pause stops cascade and wheel");_building.GetComponent<PausableBuilding>().Resume();
          }
          if(_frame>420&&!_bootstrap&&_products>0&&_deposited>0&&_sawFlow&&_pausedCheck
            &&_flag.GetComponent<Workplace>().AssignedWorkers.Any(w=>w.GetComponent<BehaviorManager>().IsRunningExecutor<ShoreCatchExecutor>())) {
            _building.GetComponent<PausableBuilding>().Pause();SetWater(45);_speed.ChangeSpeed(0);_saved=true;
            _saver.QueueSave(new SaveReference("Fishery acceptance - verified",_loader.LoadedSave.SettlementReference),()=>Debug.Log("[DeepFrontier Fishery] SAVED VERIFIED FISHERY AND ACTIVE FISHING FIXTURE"));
          }
        } else if(_frame>240&&(_hatcheryOnly||_deposited>0))CheckShoreInterruptions();
        if(_bootstrap&&_frame>420&&_products>0&&_hatcheryBatches>0&&_deposited>0) {
          _building.GetComponent<PausableBuilding>().Pause();_hatchery.GetComponent<PausableBuilding>().Pause();_flag.GetComponent<PausableBuilding>().Pause();
          _speed.ChangeSpeed(0);_saved=true;
          Debug.Log("[DeepFrontier Fishery] PASS unseeded fish chain: real shore catch, native delivery, hatchery breeding, native juvenile hauling and Fishery production; only vanilla feed/water and fixture power were supplied");
          _saver.QueueSave(new SaveReference("Aquaculture bootstrap - verified",_loader.LoadedSave.SettlementReference),()=>Debug.Log("[DeepFrontier Fishery] UNSEEDED AQUACULTURE BOOTSTRAP PASSED AND SAVED"));
        }
        if(_frame>420&&_frame%600==0) {
          Debug.Log($"[DeepFrontier Fishery] STATUS products={_products}, catches={_flag.CaughtThisSession}, delivered={_deposited}, fishing={_flag.State}, workers={_flag.GetComponent<Workplace>().NumberOfAssignedWorkers}, flow={_reservoir.Flowing}, water={_reservoir.StoredAmount}, progress={_manufactory.ProductionProgress}");
          if(_hatchery)Debug.Log($"[DeepFrontier Fishery] HATCHERY phase={_shorePhase}, workers={_hatchery.GetComponent<Workplace>().NumberOfAssignedWorkers}, working={_hatchery.GetComponent<Workshop>().NumberOfWorkersWorking}, ready={_hatcheryProduction.IsReadyToProduce}, progress={_hatcheryProduction.ProductionProgress}, batches={_hatcheryBatches}");
        }
        if(_frame>420&&_clock.PartialDayNumber-_startTime>(_reload?4:2))throw new InvalidOperationException("Fishery/fishing fixture exceeded its simulated-day allowance without completing");
      } catch(Exception e) {_failed=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Fishery] FAILED: "+e);}
    }
    private bool CatchActive() => _flag.GetComponent<Workplace>().AssignedWorkers.Any(w=>w.GetComponent<BehaviorManager>().IsRunningExecutor<ShoreCatchExecutor>());
    private void Pond(Action<Vector3Int> action) {
      for(int x=189;x<=192;x++)for(int y=166;y<=169;y++)action(new Vector3Int(x,y,2));
    }
    private void CheckShoreInterruptions() {
      if(_shorePhase==0) {
        Debug.Log("[DeepFrontier Fishery] RELOAD PASS: saved catch completed and delivered through native carrying");
        Capture("fishing-reload");_shorePhase=1;
      }
      if(_shorePhase==1&&CatchActive()) {
        _catchBefore=_flag.CaughtThisSession;Pond(c=>_water.AddContaminatedWater(c,.05f));_shorePhase=2;_shoreFrame=_frame;
      } else if(_shorePhase==2&&_frame>=_shoreFrame+120) {
        if(_flag.TryFindSpot(_flag.Transform.position,out _,out _)||CatchActive()||_flag.CaughtThisSession!=_catchBefore)
          throw new InvalidOperationException("Contamination failed to interrupt the catch without producing fish");
        Debug.Log("[DeepFrontier Fishery] PASS contaminated pond interrupts active catch with no fish");
        Capture("fishing-contaminated");
        Pond(c=>{float depth=_waterMap.WaterDepth(c),bad=_waterMap.ColumnContamination(c);_water.RemoveCleanWater(c,depth*(1-bad));_water.RemoveContaminatedWater(c,depth*bad);});
        _shorePhase=3;_shoreFrame=_frame;
      } else if(_shorePhase==3&&_frame>=_shoreFrame+120) {
        if(_flag.TryFindSpot(_flag.Transform.position,out _,out _)||CatchActive()||_flag.CaughtThisSession!=_catchBefore)
          throw new InvalidOperationException("Dry pond accepted by fishing job");
        bool dry=true;Pond(c=>{if(_waterMap.WaterDepth(c)>=.5f)dry=false;});
        if(!dry)throw new InvalidOperationException("Native test pond did not drain");
        Debug.Log("[DeepFrontier Fishery] PASS drained pond prevents fishing");
        Pond(c=>_water.AddCleanWater(c,.8f));_shorePhase=4;
      } else if(_shorePhase==4&&CatchActive()) {
        Debug.Log("[DeepFrontier Fishery] PASS clean refilled pond resumes fishing");
        _flag.SelectFishing(false);_shorePhase=5;_shoreFrame=_frame;
      } else if(_shorePhase==5&&_frame>=_shoreFrame+120) {
        if(CatchActive()||_flag.CaughtThisSession!=_catchBefore)throw new InvalidOperationException("Switching back to gathering did not cancel the catch");
        Debug.Log("[DeepFrontier Fishery] PASS switching job cancels catch without fish");
        _flag.SelectFishing(true);_shorePhase=6;
      } else if(_shorePhase==6&&CatchActive()) {
        _flag.GetComponent<PausableBuilding>().Pause();_shorePhase=7;_shoreFrame=_frame;
      } else if(_shorePhase==7&&_frame>=_shoreFrame+120) {
        if(CatchActive()||_flag.CaughtThisSession!=_catchBefore)throw new InvalidOperationException("Pausing flag did not cancel catch");
        Debug.Log("[DeepFrontier Fishery] PASS paused flag cancels catch without fish");
        _flag.GetComponent<PausableBuilding>().Resume();_shorePhase=8;
      } else if(_shorePhase==8&&CatchActive()) {
        var fisher=_flag.GetComponent<Workplace>().AssignedWorkers.Single();
        var catchFish=fisher.GetComponent<ShoreCatchExecutor>();
        if(catchFish.RemainingHours>=3)return;
        var model=fisher.GetComponent<Timberborn.CharacterModelSystem.CharacterModel>();
        var target=NavigationCoordinateSystem.GridToWorld(catchFish.WaterCell);
        target.y=model.Position.y;
        var direction=(target-model.Position).normalized;
        if(Vector3.Dot(fisher.GetComponent<Timberborn.CharacterModelSystem.CharacterModel>().Model.forward,direction)<.99f)
          throw new InvalidOperationException("Fisher model is not facing the fixture pond");
        Debug.Log("[DeepFrontier Fishery] PASS visible fisher model faces the water");Capture("fishing-regression");
        SetupAccess();
        // Player-path decks (2026-10-30): an opening's rail hides only between
        // two actual player paths, so the open rails get a path on their deck cell.
        foreach(var id in new[]{"FishFront8","FishRoofLeft6"}) {
          var inside=_building.TransformCoordinates(_building.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id==id).Inside);
          if(!_blocks.GetPathObjectAt(inside))Create("Path",inside.x,inside.y,inside.z);
        }
        _shorePhase=9;
      } else if(_shorePhase==9&&_frame>=_shoreFrame+120) {
        CheckPort("FishFront8",true);CheckPort("FishRoofLeft6",true);CheckPort("FishRoofLeft5",false);
        var worker=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).First(w=>w.WorkerType=="Beaver"&&w.Workplace!=_flag.GetComponent<Workplace>());
        worker.Unemploy();_walker=worker.GetComponent<ControllableCharacter>();_walker.ChangeAnimation("BeaverAdult_idle");
        _walkBuilding=_building;
        // From the road below the gallery stairs onto the gallery, through both upper doors
        // and the hall to the warehouse terrace, then down to the road in front of the Entrance.
        var deck=_building.GetComponent<PlatformDeckSpec>();
        var front=Opening("FishFront8");var access=GalleryStairs();
        var galleryDoor=deck.Doors.Single(d=>d.Exterior==front.Inside);
        var terraceDoor=deck.Doors.Single(d=>d.Exterior!=front.Inside);
        var entrance=_building.PositionedEntrance.Coordinates;
        foreach(var cell in new[]{new Vector3Int(access.Approach.x,RoadY,Ground),_building.TransformCoordinates(front.Inside),_building.TransformCoordinates(galleryDoor.Interior),
          _building.TransformCoordinates(terraceDoor.Interior),_building.TransformCoordinates(Opening("FishRoofLeft6").Inside),new Vector3Int(entrance.x,RoadY,Ground)})
          _walkTargets.Enqueue(cell);
        _camera.MoveTargetTo(new Vector3(166,7,164));_camera.SetZoomLevel(20,0);_shorePhase=10;NextTarget();
      } else if(_shorePhase==10&&Vector3.Distance(_walker.Transform.position,_walkWorld)<.18f) {
        Debug.Log("[DeepFrontier Fishery] PASS actual beaver reached "+_walkTarget);
        if(_walkTargets.Count>0)NextTarget();
        else {
          _walker.ReleaseControl();Capture("fishery-access-regression");
          SetupHatchery();_shorePhase=11;_shoreFrame=_frame;
        }
      } else if(_shorePhase>=11)CheckHatchery();
    }
    private void SetupHatchery(bool seedFish=true) {
      // Exact empty bank surveyed in Reservoir acceptance - verified. The
      // nursery sits beside the quarry, with a separate six-row water bed under
      // its compact 7x7 deck (2026-10-26; 8x8 with perimeter docks before).
      HatcheryPond(c=>{
        if(_terrain.GetTerrainHeight(new Vector3Int(c.x,c.y,0))!=3)throw new InvalidOperationException("Hatchery bed requires the surveyed unmodified bank");
        _terrain.UnsetTerrain(c,1);_water.AddCleanWater(c,.8f);
      });
      for(int x=189;x<=193;x++)Create("Path",x,170,3);
      for(int y=169;y>=164;y--)Create("Path",193,y,3);
      // The deck no longer reaches the bank row (the walkway beside the
      // headhouse is gone): the bank row and its door join the network on the
      // west, and the rear railing opening behind the centre dock on the north.
      for(int y=155;y<=169;y++)Create("Path",186,y,3);
      // The only access: an ordinary player path on the native Entrance (1,-1,1), the bank cell in
      // front of the door, world (188,155) (tools/native_entrance.mjs). No path on the door cell.
      Create("Path",187,155,3);Create("Path",188,155,3);
      for(int x=189;x<=193;x++)Create("Path",x,163,3);
      _hatchery=Create("FishHatchery.IronTeeth",187,156,2);
      if(!_hatchery.HasComponent<PlatformDeckSpec>()||_hatchery.HasComponent<BuildingWalkwaySpec>())
        throw new InvalidOperationException("Hatchery deck must use player paths, not built-in outdoor routes");
      // Only the door cell needs ground (tools/waterside_sites.json groundCells);
      // on this straight fixture bank every bank post finds the bed at depth 0
      // (no post shown) and each of the four deck piles reaches the pond bed.
      var foundation=_hatchery.PositionedBlocks.GetFoundationCoordinates().ToList();
      var supports=_hatchery.GetComponent<AdaptiveSupports>();
      // AdaptiveSupportsSpec.Columns: the four deck piles, then the six bank posts.
      if(foundation.Count!=1||foundation[0]!=_hatchery.TransformCoordinates(new Vector3Int(1,0,1))||supports.Probes.Count!=10||!supports.AllColumnsSupported
         ||supports.Probes.Take(4).Any(p=>p.Depth<1)||supports.Probes.Skip(4).Any(p=>p.Depth!=0))
        throw new InvalidOperationException($"Hatchery foundation/support contract changed: {foundation.Count} foundation cells, post depths {string.Join(",",supports.Probes.Select(p=>p.Depth))}");
      Debug.Log("[DeepFrontier Fishery] PASS hatchery stands on its door cell; posts "+string.Join(",",supports.Probes.Select(p=>p.Depth)));
      RequireHatcheryPlacement("Path",new Vector3Int(1,2,1),false,"enclosed headhouse");
      RequireHatcheryPlacement("Path",new Vector3Int(1,5,1),false,"open nursery pen");
      RequireHatcheryPlacement("Path",new Vector3Int(4,3,1),false,"retained canopy post");
      RequireHatcheryPlacement("PowerShaft.IronTeeth",new Vector3Int(0,3,1),true,"front walkway shaft");
      RequireHatcheryPlacement("Platform.IronTeeth",new Vector3Int(0,0,1),true,"floor-only bank apron");
      RequireHatcheryPlacement("DoublePlatform.IronTeeth",new Vector3Int(2,6,1),true,"centre dock end");
      // Ground freed by the 2026-10-22 pass (validate_freed_cells.py): bank-row cells that held
      // barrels and sacks (native Floor now), in the compact grid.
      FreedCellProbe.Require(_templates,_validator,_hatchery,
        new[]{new Vector3Int(2,0,1),new Vector3Int(3,0,1),new Vector3Int(6,0,1)},
        "FishHatchery",message=>Debug.Log("[DeepFrontier Fishery] PASS "+message));
      // Right canopy wall socket (6,1,1) -> shaft outside it at (194,157,3); the
      // generator stays west of x=195, where the pipe test clears its own pad.
      Create("PowerShaft.IronTeeth",194,157,3);Create("DevPowerGenerator",194,156,3);
      // A shaft under the centre dock end and a native platform stack above it,
      // over the end path (paths pass under platform legs).
      Create("PowerShaft.IronTeeth",189,162,2);
      Create("DoublePlatform.IronTeeth",189,162,3);Create("Platform.IronTeeth",189,162,5);Create("Path",189,162,6);
      foreach(var cell in HatcheryPathCells().OrderBy(c=>c.y).ThenBy(c=>c.x)) {
        var world=_hatchery.TransformCoordinates(cell);Create("Path",world.x,world.y,world.z);
      }
      Debug.Log("[DeepFrontier Fishery] PASS hatchery player-path placement, blocked room/pen, shaft underneath and native platform stack above dock");
      RequireHatcheryDeckLoadOrder(HatcheryPathCells().Count(c=>c.y>0)+1);
      _hatcheryProduction=_hatchery.GetComponent<Manufactory>();
      var supplies=seedFish?new[]{new GoodAmount("FreshFish",2),new GoodAmount("Algae",2),new GoodAmount("Water",4)}:
        new[]{new GoodAmount("Algae",4),new GoodAmount("Water",8)};
      foreach(var good in supplies)_hatcheryProduction.Inventory.GiveExisting(good);
      _hatcheryProduction.ProductionFinished+=(sender,args)=>{_hatcheryBatches++;Debug.Log("[DeepFrontier Fishery] HATCHERY PRODUCED JuvenileFish");};
      _hatcheryCreatedFrame=_frame;
      _camera.MoveTargetTo(new Vector3(191,4,160));_camera.SetZoomLevel(18,0);_startTime=_clock.PartialDayNumber;
    }
    // Player paths placed by the hatchery fixture, local cells at bank height.
    // Row y=0 stands on the bank; every other cell stands on a deck slab below
    // the hatchery's BaseZ layer. AquacultureContinuityAcceptance requires
    // them all to survive a fresh-process reload of the saved fixture.
    // Compact 7x7 deck (2026-10-26): the bank row beside the door, the front
    // walkway behind the headhouse and the centre dock between the pens.
    internal static HashSet<Vector3Int> HatcheryPathCells() {
      var paths=new HashSet<Vector3Int>();
      // The door cell (1,0,1) stays unpaved: the hatchery is reached from its Entrance in front of it.
      paths.Add(new Vector3Int(0,0,1));paths.Add(new Vector3Int(2,0,1));
      for(int x=0;x<=3;x++)paths.Add(new Vector3Int(x,3,1));
      for(int y=4;y<=6;y++)paths.Add(new Vector3Int(2,y,1));
      return paths;
    }
    // Native BlockObjectBatchLoader adds saved objects ordered by
    // (CoordinatesAtBaseZ.z, GetHighestOccupation) and deletes any whose
    // MatterBelow is unmet when it is added. Every object resting on a
    // hatchery deck slab must therefore sort strictly after the hatchery.
    private void RequireHatcheryDeckLoadOrder(int expectedDeckObjects) {
      int hatcheryZ=_hatchery.CoordinatesAtBaseZ.z,hatcheryRank=BlockObjectBatchLoader.GetHighestOccupation(_hatchery);
      if(hatcheryRank!=StackableBaseLoadOrder.SupportFirst)
        throw new InvalidOperationException("Hatchery is not ranked first in its native load layer (StackableBaseLoadOrder inactive): "+hatcheryRank);
      var deck=new List<BlockObject>();
      foreach(var other in _registry.Entities.Where(e=>e.HasComponent<BlockObject>()).Select(e=>e.GetComponent<BlockObject>())) {
        if(other==_hatchery)continue;
        bool onDeck=other.PositionedBlocks.GetFoundationBlocks().Any(f=>
          _hatchery.PositionedBlocks.TryGetBlock(f.Coordinates-new Vector3Int(0,0,1),out var slab)&&slab.Stackable.IsStackable());
        if(!onDeck)continue;
        int z=other.CoordinatesAtBaseZ.z,rank=BlockObjectBatchLoader.GetHighestOccupation(other);
        if(z<hatcheryZ||(z==hatcheryZ&&rank<=hatcheryRank))
          throw new InvalidOperationException($"{other.Name} at {other.Coordinates} loads before the hatchery deck it stands on: ({z},{rank}) vs ({hatcheryZ},{hatcheryRank})");
        deck.Add(other);
      }
      if(deck.Count!=expectedDeckObjects)
        throw new InvalidOperationException($"Expected {expectedDeckObjects} objects on hatchery deck slabs, found {deck.Count}");
      Debug.Log($"[DeepFrontier Fishery] PASS native load order: hatchery ({hatcheryZ},{hatcheryRank}) is added before all {deck.Count} deck paths/platforms standing on its slabs");
    }
    private void AssignHatcheryWorkers() {
      // Water edits and navmesh changes are queued by native services. Let
      // those updates run before invoking the normal workplace contract.
      if(!_hatchery.GetComponent<BlockableObject>().IsUnblocked)throw new InvalidOperationException("New hatchery remained blocked after native water/site updates");
      var accessible=_hatchery.GetComponent<BuildingAccessible>();
      var access=accessible.CalculateAccessFromLocalAccess();
      if(Vector3.Distance(access,new Vector3(188.5f,3,157f))>.0001f)throw new InvalidOperationException("Hatchery workshop final access is outside its bank-height arch: "+access);
      // Reachable through the plain path on its Entrance (188,155) alone.
      var entrance=_hatchery.PositionedEntrance.Coordinates;
      if(entrance!=new Vector3Int(188,155,3)||!_blocks.GetPathObjectAt(entrance))
        throw new InvalidOperationException("Hatchery Entrance "+entrance+" is not the bank cell (188,155,3) in front of the door with a player path");
      if(_blocks.GetPathObjectAt(_hatchery.TransformCoordinates(new Vector3Int(1,0,1))))
        throw new InvalidOperationException("The hatchery door cell carries a path; the fixture must reach it from the Entrance only");
      var district=_hatchery.GetComponent<Timberborn.GameDistricts.DistrictBuilding>();
      if(!accessible.Accessible.UnblockedSingleAccess.HasValue||!district.District)
        throw new InvalidOperationException("Hatchery not reachable through the plain path on its Entrance: access "+accessible.Accessible.UnblockedSingleAccess+
          ", district "+(district.District?"assigned":"none"));
      Debug.Log("[DeepFrontier Fishery] PASS hatchery reachable through an ordinary player path on its Entrance "+entrance+" (door cell unpaved)");
      var workers=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver"&&w.Workplace!=_flag.GetComponent<Workplace>()&&w.Workplace!=_building.GetComponent<Workplace>()).Take(2).ToArray();
      if(workers.Length!=2)throw new InvalidOperationException("Hatchery fixture requires two available adult workers");
      foreach(var worker in workers){worker.Unemploy();worker.EmployAt(_hatchery.GetComponent<Workplace>());}
      Debug.Log("[DeepFrontier Fishery] PASS hatchery native site unblocked before assigning workers");
    }
    private void HatcheryPond(Action<Vector3Int> action) {
      for(int x=187;x<=193;x++)for(int y=157;y<=162;y++)action(new Vector3Int(x,y,2));
    }
    private void DrainPond() {
      HatcheryPond(c=>{float depth=_waterMap.WaterDepth(c),bad=_waterMap.ColumnContamination(c);_water.RemoveCleanWater(c,depth*(1-bad));_water.RemoveContaminatedWater(c,depth*bad);});
    }
    private void CheckHatchery() {
      if(_frame<_shoreFrame+120)return;
      var waterBuilding=_hatchery.GetComponent<WaterDepthWorkCells>();
      var blocker=_hatchery.GetComponent<BlockableObject>();
      var pollution=_hatchery.GetComponent<ContaminationBlockableBuilding>();
      if(_shorePhase==11) {
        if(_hatchery.TransformCoordinates(waterBuilding.Spec.WorkCells[0])!=new Vector3Int(188,161,2)||waterBuilding.IsBlockedByDepth||!blocker.IsUnblocked||pollution.IsBlocked)
          throw new InvalidOperationException("Hatchery native pool water requirement did not accept clean water under rear nursery");
        if(_hatchery.GetComponent<MechanicalNode>().Graph.PowerSupply<55)throw new InvalidOperationException("Hatchery shaft has no supply");
        Debug.Log("[DeepFrontier Fishery] PASS hatchery clean water below nursery and native shaft supply");
        if(Math.Abs(_hatchery.Transform.position.y-3)>.0001f)throw new InvalidOperationException("Hatchery BaseZ moved its bank-level deck");
        foreach(int x in new[]{0,1,2}) {
          var cell=_hatchery.TransformCoordinates(new Vector3Int(x,0,1));
          var occupation=_hatchery.PositionedBlocks.GetBlock(cell).Occupation;
          if(!occupation.Intersects(BlockOccupations.Floor)||occupation.Intersects(BlockOccupations.Path))
            throw new InvalidOperationException("Bank apron is not native Floor-only occupation");
          var path=_blocks.GetPathObjectAt(cell);
          var nodes=path.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true);
          var variants=new[]{"0000","0010","0011","0111","1010","1111"};
          int roof=variants.Count(v=>nodes.Single(t=>t.name=="RoofPath"+v).gameObject.activeSelf);
          int dirt=variants.Count(v=>nodes.Single(t=>t.name=="DirtPath"+v).gameObject.activeSelf);
          if(roof!=1||dirt!=0)throw new InvalidOperationException("Bank apron path did not select the native roof model above its timber surface");
        }
        Debug.Log("[DeepFrontier Fishery] PASS native Floor-only bank aprons retain player paths and select visible roof path models");
        CheckHatcheryPort("NurseryBack2",true);CheckHatcheryPort("NurseryLeft3",true);CheckHatcheryPort("NurseryRight5",false);
        foreach(int amount in new[]{0,30,60,4})SetHatcheryWater(amount);
        Capture("hatchery-clean-water");DrainPond();_shorePhase=12;_shoreFrame=_frame;
      } else if(_shorePhase==12) {
        if(blocker.IsUnblocked)throw new InvalidOperationException("Dry hatchery is not blocked by native pool requirement");
        _dryProgress=_hatcheryProduction.ProductionProgress;_shorePhase=13;_shoreFrame=_frame;
      } else if(_shorePhase==13) {
        if(blocker.IsUnblocked||_hatcheryProduction.ProductionProgress!=_dryProgress)throw new InvalidOperationException("Dry hatchery continued breeding");
        Debug.Log("[DeepFrontier Fishery] PASS dry hatchery blocks breeding");Capture("hatchery-dry");
        HatcheryPond(c=>{_water.AddCleanWater(c,.7f);_water.AddContaminatedWater(c,.1f);});_shorePhase=14;_shoreFrame=_frame;
      } else if(_shorePhase==14) {
        if(!pollution.IsBlocked||blocker.IsUnblocked)throw new InvalidOperationException("Native pool contamination protection did not block hatchery");
        Debug.Log("[DeepFrontier Fishery] PASS badwater blocks hatchery through native contamination component");
        DrainPond();_shorePhase=15;_shoreFrame=_frame;
      } else if(_shorePhase==15) {
        HatcheryPond(c=>_water.AddCleanWater(c,.8f));_shorePhase=16;_shoreFrame=_frame;
      } else if(_shorePhase==16) {
        if(!blocker.IsUnblocked||pollution.IsBlocked)throw new InvalidOperationException("Clean refilling did not restore hatchery");
        if(_hatcheryBatches<1)return;
        Debug.Log("[DeepFrontier Fishery] PASS clean refilled hatchery resumes and breeds real juveniles");
        var worker=_hatchery.GetComponent<Workplace>().AssignedWorkers.First();
        _hatchery.GetComponent<PausableBuilding>().Pause();worker.Unemploy();
        _walker=worker.GetComponent<ControllableCharacter>();_walker.ChangeAnimation("BeaverAdult_idle");_walkBuilding=_hatchery;
        foreach(var cell in new[]{new Vector3Int(2,6,1),new Vector3Int(3,3,1),new Vector3Int(0,3,1),new Vector3Int(2,4,1),new Vector3Int(0,0,1),new Vector3Int(1,1,1)})_walkTargets.Enqueue(_hatchery.TransformCoordinates(cell));
        _shorePhase=17;NextTarget();
      } else if(_shorePhase==17&&Vector3.Distance(_walker.Transform.position,_walkWorld)<.18f) {
        Debug.Log("[DeepFrontier Fishery] PASS actual beaver reached hatchery dock/door "+_walkTarget);
        if(_walkTargets.Count>0)NextTarget();
        else {
          _walker.ReleaseControl();SetHatcheryWater(30);_speed.ChangeSpeed(0);_shorePhase=18;_shoreFrame=_frame;
          _camera.MoveTargetTo(new Vector3(191,4,160));_camera.SetZoomLevel(18,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
        }
      } else if(_shorePhase==18) {
        _saved=true;Capture("hatchery-production");
        string saveName=_hatcheryOnly?"Hatchery acceptance - verified":"Fishery regression - verified";
        string result=_hatcheryOnly?"ALL HATCHERY WATER, POWER, RESERVOIR, STACKING AND WALKING CHECKS PASSED AND SAVED":"ALL SHORE, ACCESS AND HATCHERY REGRESSIONS PASSED AND SAVED";
        _saver.QueueSave(new SaveReference(saveName,_loader.LoadedSave.SettlementReference),()=>Debug.Log("[DeepFrontier Fishery] "+result));
      }
    }
    private void SetHatcheryWater(int amount) {
      var inventory=_hatcheryProduction.Inventory;
      int previous=inventory.AmountInStock("Water");if(previous>0)inventory.TakeExisting(new GoodAmount("Water",previous));
      if(amount>0)inventory.GiveExisting(new GoodAmount("Water",amount));
      var spec=_hatchery.GetComponent<WorkshopReservoirSpec>();var visual=_hatchery.GetComponent<WorkshopReservoir>();
      if(spec.Capacity!=60||spec.Surfaces.Length!=1||visual.StoredAmount!=amount||visual.SurfacesVisible!=(amount>0))throw new InvalidOperationException("Hatchery native header tank stock/visibility mismatch");
      var surface=spec.Surfaces.Single();float expected=surface.EmptyHeight+(surface.FullHeight-surface.EmptyHeight)*amount/60f;
      if(Math.Abs(visual.SurfaceHeights.Single()-expected)>.00001f)throw new InvalidOperationException("Hatchery native header tank fill height mismatch");
      Debug.Log("[DeepFrontier Fishery] PASS hatchery native header tank "+amount+"/60");
    }
    private void SetupAccess() {
      // Native stairs from the road row up to the FishFront8 gallery opening, and a
      // platform stack carrying a path at both open openings' outside cells.
      var access=GalleryStairs();
      for(int y=RoadY+1;y<=access.Approach.y;y++)Create("Path",access.Approach.x,y,Ground);
      foreach(var (cell,climb) in access.Stairs) {
        for(int z=Ground;z<cell.z;z++)Create("Platform.IronTeeth",cell.x,cell.y,z);
        Create("Stairs.IronTeeth",cell.x,cell.y,cell.z,climb);
      }
      foreach(var id in new[]{"FishFront8","FishRoofLeft6"}) {
        var outside=_building.TransformCoordinates(Opening(id).Outside);
        for(int z=Ground;z<outside.z;z++)Create("Platform.IronTeeth",outside.x,outside.y,z);
        Create("Path",outside.x,outside.y,outside.z);
      }
      // The terrace supports native construction: a platform and path on the next free deck
      // cell (the saved stack now fills the first), clear of the door and the opening cells.
      var platform=_building.TransformCoordinates(TerraceBuildCells()[0]);
      Create("Platform.IronTeeth",platform.x,platform.y,platform.z);Create("Path",platform.x,platform.y,platform.z+1);
      foreach(var e in _registry.Entities.Where(e=>e.HasComponent<WorkshopReservoirSpec>()&&e.GetComponent<WorkshopReservoirSpec>().Capacity==16)) {
        if(!e.GetComponent<PausableBuilding>().Paused)throw new InvalidOperationException("Quarry regression requires paused fixture");
        var spec=e.GetComponent<WorkshopReservoirSpec>();var visual=e.GetComponent<WorkshopReservoir>();var inventory=e.GetComponent<Manufactory>().Inventory;
        foreach(var amount in new[]{0,8,16,8}) {
          int old=inventory.AmountInStock("Water");if(old>0)inventory.TakeExisting(new GoodAmount("Water",old));if(amount>0)inventory.GiveExisting(new GoodAmount("Water",amount));
          if(visual.StoredAmount!=amount||visual.SurfacesVisible!=(amount>0))throw new InvalidOperationException("Quarry reservoir regression");
          for(int i=0;i<spec.Surfaces.Length;i++)if(Math.Abs(visual.SurfaceHeights[i]-(spec.Surfaces[i].EmptyHeight+(spec.Surfaces[i].FullHeight-spec.Surfaces[i].EmptyHeight)*amount/16f))>.00001f)throw new InvalidOperationException("Quarry height regression");
        }
        Debug.Log("[DeepFrontier Fishery] PASS quarry water regression "+e.GetComponent<TemplateSpec>().TemplateName);
      }
      _shoreFrame=_frame;
    }
    private void CheckPort(string id,bool expected) => CheckPort(id,expected,_building);
    private WalkwayOpeningSpec Opening(string id)=>_building.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id==id);
    // The Fishery's shaft line: a vanilla shaft on its first transput face (which must face
    // Left, the fixture's west side) and the developer generator beyond it. Shared with
    // AquacultureContinuityAcceptance, which finds the saved generator here.
    internal static (Vector3Int Shaft,Vector3Int Generator) ShaftLine(BlockObject fishery) {
      var face=fishery.GetComponent<TransputProviderSpec>().Transputs[0];
      if(!face.Directions.ToString().Split(',').Select(d=>d.Trim()).Contains("Left"))
        throw new InvalidOperationException("Fishery's first shaft face "+face.Coordinates+" "+face.Directions+" does not face Left, where this fixture's shaft line runs");
      var shaft=fishery.TransformCoordinates(face.Coordinates)+new Vector3Int(-1,0,0);
      return (shaft,shaft+new Vector3Int(-1,0,0));
    }
    // Stairs up to the FishFront8 opening's outside cell from the road row: one native stair
    // per layer, each on native platforms, climbing toward the building (native Stairs climb
    // toward their local Down side, as in AllBuildingsAcceptance), then the ground approach
    // cell at their foot. The opening must face the road row (south).
    private (List<(Vector3Int Cell,Orientation Climb)> Stairs,Vector3Int Approach) GalleryStairs() {
      var front=Opening("FishFront8");
      var outside=_building.TransformCoordinates(front.Outside);var step=outside-_building.TransformCoordinates(front.Inside);
      int height=outside.z-Ground;
      if(step!=new Vector3Int(0,-1,0)||height<1)
        throw new InvalidOperationException("FishFront8 steps "+step+" to "+outside+"; this fixture's stairs need a raised opening facing the road row (south)");
      var climb=Rotations.Single(o=>o.Transform(Direction2D.Down).ToOffset()==-step);
      var stairs=Enumerable.Range(1,height).Select(k=>(outside+step*k-new Vector3Int(0,0,k),climb)).ToList();
      var approach=outside+step*(height+1);approach.z=Ground;
      if(approach.y<=RoadY)throw new InvalidOperationException("FishFront8 stairs at "+outside+" reach past the road row y "+RoadY);
      return (stairs,approach);
    }
    // Free warehouse-terrace deck cells (local) that take a native Platform, flooded from the
    // terrace door's exterior over the building's own bounds; minus the door exterior and the
    // openings' inside cells, ordered by row then column.
    private List<Vector3Int> TerraceBuildCells() {
      var deck=_building.GetComponent<PlatformDeckSpec>();
      var door=deck.Doors.Single(d=>d.Exterior!=Opening("FishFront8").Inside).Exterior;
      var size=_building.GetComponent<BlockObjectSpec>().Size;
      var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Platform.IronTeeth");
      var platform=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      bool Deck(Vector3Int c)=>c.x>=0&&c.y>=0&&c.x<size.x&&c.y<size.y
        &&_validator.BlocksValid(platform,new Placement(_building.TransformCoordinates(c),Orientation.Cw0,FlipMode.Unflipped));
      if(!Deck(door))throw new InvalidOperationException("Fishery terrace door exterior "+door+" is not a free deck cell");
      var cells=new HashSet<Vector3Int>{door};var open=new Queue<Vector3Int>(cells);
      while(open.Count>0) {
        var c=open.Dequeue();
        foreach(var n in new[]{c+Vector3Int.right,c+Vector3Int.left,c+Vector3Int.up,c+Vector3Int.down})
          if(!cells.Contains(n)&&Deck(n)){cells.Add(n);open.Enqueue(n);}
      }
      var reserved=new HashSet<Vector3Int>(deck.Openings.Select(p=>p.Inside)){door};
      var result=cells.Where(c=>!reserved.Contains(c)).OrderBy(c=>c.y).ThenBy(c=>c.x).ToList();
      if(result.Count==0)throw new InvalidOperationException("Fishery terrace offers no free deck cell besides its door and openings for this fixture's platforms");
      return result;
    }
    private void RequireHatcheryPlacement(string id,Vector3Int cell,bool expected,string purpose) {
      var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(_hatchery.TransformCoordinates(cell),Orientation.Cw0,FlipMode.Unflipped);
      if(_validator.BlocksValid(spec,placement)!=expected)
        throw new InvalidOperationException("Hatchery native placement mismatch for "+purpose+": "+id+" "+cell);
    }
    private void CheckHatcheryPort(string id,bool expectedOpen) {
      var p=_hatchery.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id==id);
      var a=_hatchery.TransformCoordinates(p.Inside);var b=_hatchery.TransformCoordinates(p.Outside);
      var inside=_blocks.GetPathObjectAt(a);var outside=_blocks.GetPathObjectAt(b);
      if(!inside||!inside.IsFinished||!inside.HasComponent<PathSpec>())throw new InvalidOperationException("Hatchery rail test has no actual player path inside "+id);
      bool neighboringPath=outside&&outside.IsFinished&&outside.HasComponent<PathSpec>();
      bool connected=_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a);
      var nodes=_hatchery.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true);
      bool hidden=p.HiddenNodes.All(name=>!nodes.Single(t=>t.name==name).gameObject.activeSelf);
      if(neighboringPath!=expectedOpen||hidden!=expectedOpen||(expectedOpen&&!connected))
        throw new InvalidOperationException("Hatchery player-path rail mismatch: "+id+", path="+neighboringPath+", hidden="+hidden+", floorConnected="+connected);
      Debug.Log("[DeepFrontier Fishery] PASS hatchery decorative rail "+id+" actual outside path="+neighboringPath+", hidden="+hidden);
    }
    // Player-path deck rail (PlatformDeck, 2026-10-30): hidden exactly when actual
    // player paths stand on both the deck cell and the neighbouring cell.
    private void CheckPort(string id,bool expected,BlockObject building) {
      var p=building.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id==id);
      var a=building.TransformCoordinates(p.Inside);var b=building.TransformCoordinates(p.Outside);
      bool paths=IsPlayerPath(a)&&IsPlayerPath(b);
      bool connected=_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a);
      var nodes=building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true);
      bool hidden=p.HiddenNodes.All(name=>!nodes.Single(t=>t.name==name).gameObject.activeSelf);
      if(paths!=expected||hidden!=expected||(expected&&!connected))throw new InvalidOperationException("Fishery rail/route mismatch: "+id);
      Debug.Log("[DeepFrontier Fishery] PASS rail "+id+": paths="+paths+", connected="+connected+", hidden="+hidden);
    }
    private bool IsPlayerPath(Vector3Int c){var o=_blocks.GetPathObjectAt(c);return o&&o.IsFinished&&o.HasComponent<PathSpec>();}
    private void NextTarget() {
      _walkTarget=_walkTargets.Dequeue();
      // Both buildings are player-path decks (2026-10-30): every target is a world grid cell.
      _walkWorld=NavigationCoordinateSystem.GridToWorld(_walkTarget);
      var corners=new List<PathCorner>();
      if(!_navigation.FindPathUnlimitedRange(_walker.Transform.position,_walkWorld,corners,out var distance))throw new InvalidOperationException("No native route to fishery target "+_walkTarget);
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_walkWorld));
      Debug.Log("[DeepFrontier Fishery] WALK target="+_walkTarget+", native distance="+distance);
    }
    private void StartProduction() {
      _manufactory.SetRecipe(_manufactory.ProductionRecipes.Single(r=>r.Id=="FreshFish"));
      if(_bootstrap) {StartBootstrap();return;}
      _manufactory.Inventory.GiveExisting(new GoodAmount("JuvenileFish",4));_manufactory.Inventory.GiveExisting(new GoodAmount("Algae",4));
      _building.GetComponent<PausableBuilding>().Resume();
      var workers=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").ToArray();
      foreach(var w in workers)w.Unemploy();
      workers[0].EmployAt(_flag.GetComponent<Workplace>());
      foreach(var worker in workers.Skip(1).Take(3))worker.EmployAt(_building.GetComponent<Workplace>());
      if(!_flag.TryFindSpot(workers[0].Transform.position,out var bank,out var water))throw new InvalidOperationException("Fixture must expose a reachable clean-water shoreline");
      if(_flag.Suitable(bank,bank))throw new InvalidOperationException("Dry ground accepted as fish habitat");
      Debug.Log("[DeepFrontier Fishery] PASS clean shoreline="+bank+", water="+water+"; dry bank rejected");
      _startTime=_clock.PartialDayNumber;_speed.ChangeSpeed(3);
    }
    private void StartBootstrap() {
      var workers=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").ToArray();
      if(workers.Length<6)throw new InvalidOperationException("Bootstrap fixture needs six adult workers");
      foreach(var worker in workers)worker.Unemploy();
      workers[0].EmployAt(_flag.GetComponent<Workplace>());
      SetupHatchery(seedFish:false);
      if(_flag.Inventory.AmountInStock("FreshFish")!=0||_manufactory.Inventory.AmountInStock("FreshFish")!=0||_manufactory.Inventory.AmountInStock("JuvenileFish")!=0||_hatcheryProduction.Inventory.AmountInStock("FreshFish")!=0||_hatcheryProduction.Inventory.AmountInStock("JuvenileFish")!=0)
        throw new InvalidOperationException("Bootstrap must begin without fish or juveniles");
      _manufactory.Inventory.GiveExisting(new GoodAmount("Algae",8));
      _building.GetComponent<PausableBuilding>().Resume();
      foreach(var worker in workers.Skip(3).Take(3))worker.EmployAt(_building.GetComponent<Workplace>());
      _camera.MoveTargetTo(new Vector3(176,6,165));_camera.SetZoomLevel(34,0);
      Debug.Log("[DeepFrontier Fishery] BOOTSTRAP begins with zero FreshFish/JuvenileFish; supplied only native Algae/Water and developer shaft power");
      _startTime=_clock.PartialDayNumber;_speed.ChangeSpeed(3);
    }
    private void SetWater(int amount) {
      var inventory=_manufactory.Inventory;int old=inventory.AmountInStock("Water");
      if(old>0)inventory.TakeExisting(new GoodAmount("Water",old));
      if(amount>0)inventory.GiveExisting(new GoodAmount("Water",amount));VerifyWater(amount);
    }
    private void VerifyWater(int amount) {
      var spec=_building.GetComponent<WorkshopReservoirSpec>();
      if(spec.Capacity!=90||spec.Surfaces.Length==0||_reservoir.StoredAmount!=amount||_reservoir.SurfacesVisible!=(amount>0))throw new InvalidOperationException("Fishery water surface/stock mismatch");
      for(int i=0;i<spec.Surfaces.Length;i++) {
        var s=spec.Surfaces[i];float expected=s.EmptyHeight+(s.FullHeight-s.EmptyHeight)*amount/90f;
        if(Math.Abs(_reservoir.SurfaceHeights[i]-expected)>.00001f)throw new InvalidOperationException("Fishery liquid height mismatch: "+s.Node);
      }
      Debug.Log("[DeepFrontier Fishery] PASS "+spec.Surfaces.Length+" native-material water surfaces: "+amount+"/90");
    }
    private static void Capture(string name) {
      var folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding/docs/art/reviews/2026-10-19-fishery-runtime");
      Directory.CreateDirectory(folder);ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
    }
  }
}
