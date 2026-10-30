using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.ConstructionSites;
using Timberborn.CharacterControlSystem;
using Timberborn.Coordinates;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.SingletonSystem;
using Timberborn.SimulationSystem;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.Workshops;
using Timberborn.WorkSystem;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Opt-in acceptance fixture. Requires BOTH an explicit launch argument and
  // the uniquely named district in a disposable copy of the concrete test save.
  [Context("Game")]
  public sealed class IndustrialAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if (Environment.GetCommandLineArgs().Contains("-deepFrontierWalkwayAcceptance")
          || Environment.GetCommandLineArgs().Contains("-deepFrontierWalkwayReload"))
        Bind<IndustrialAcceptance>().AsSingleton();
    }
  }

  public sealed class IndustrialAcceptance : IUpdatableSingleton, IPostLoadableSingleton {
    private readonly EntityRegistry _registry;
    private readonly EntityService _entities;
    private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates;
    private readonly ITerrainService _terrain;
    private readonly INavMeshService _nav;
    private readonly IBlockService _blocks;
    private readonly INavigationService _pathfinding;
    private readonly BlockValidator _blockValidator;
    private readonly BlockObjectValidationService _objectValidator;
    private readonly SpeedManager _speed;
    private readonly SimulationController _simulation;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly CameraService _camera;
    private bool _saved;
    private readonly List<BlockObject> _factories = new List<BlockObject>();
    private readonly List<(BlockObject Factory,BlockObject Shaft,BlockObject Generator)> _powerTests=new List<(BlockObject,BlockObject,BlockObject)>();
    private int _frame;
    private bool _active;
    private bool _failed;
    private bool _reload;
    private readonly HashSet<string> _produced = new HashSet<string>();
    private readonly Queue<(string Label,Vector3 World)> _walkTargets=new Queue<(string,Vector3)>();
    private ControllableCharacter _walker;
    private (string Label,Vector3 World) _walkTarget;

    public IndustrialAcceptance(EntityRegistry registry, EntityService entities,
        BlockObjectFactory factory, TemplateService templates, ITerrainService terrain,
        INavMeshService nav, IBlockService blocks, INavigationService pathfinding,
        BlockValidator blockValidator,BlockObjectValidationService objectValidator,SpeedManager speed,SimulationController simulation,GameSaver saver,GameLoader loader,CameraService camera) {
      _registry=registry; _entities=entities; _factory=factory; _templates=templates;
      _terrain=terrain; _nav=nav; _blocks=blocks; _pathfinding=pathfinding;
      _blockValidator=blockValidator;_objectValidator=objectValidator;
      _speed=speed;
      _simulation=simulation;
      _saver=saver;_loader=loader;
      _camera=camera;
    }
    public void PostLoad() {
      _active = _registry.Entities.Any(e => e.HasComponent<NamedEntity>()
          && e.GetComponent<NamedEntity>().EntityName == "Deep Frontier Acceptance Fixture");
      if (!_active) throw new InvalidOperationException("Acceptance launch requires the explicitly marked disposable fixture save.");
      _reload=Environment.GetCommandLineArgs().Contains("-deepFrontierWalkwayReload");
    }
    public void UpdateSingleton() {
      if (!_active || _failed) return;
      ++_frame;
      try {
        if (_frame==60) Setup();
        if (_reload) {
          if (_frame==240) { Audit("save/reload"); Debug.Log("[DeepFrontier Acceptance] RELOAD DOOR CHECKS COMPLETE"); }
          return;
        }
        // The machines have no walkable decks or rails since 2026-10-21: the
        // checks cover ground-door routes, power, production and traversal.
        if (_frame==240) { Audit("connected"); Debug.Log("[DeepFrontier Acceptance] GROUND DOOR ROUTE CHECKS COMPLETE; production and visual traversal are separate checks."); }
        if (_frame==600) SetupProduction();
        if (_frame==720) { CheckPower(); SetupTraversal(); }
        if (_frame>=720 && _frame%30==0) CheckTraversal();
        if(_frame==900) ReviewView(new Vector3(153,5,147),20);
        if(_frame==930) CaptureReview("crusher-native-materials");
        if(_frame==1200) ReviewView(new Vector3(167,5,147),23);
        if(_frame==1230) CaptureReview("kiln-native-materials");
        if(_frame==1500) ReviewView(new Vector3(181,7,148),28);
        if(_frame==1530) CaptureReview("quarry-native-materials");
        if (_frame>600 && _frame%1800==0) ReportProduction();
        if(_frame>720 && !_saved && _produced.Count==4 && !_walker && _walkTargets.Count==0) {
          _saved=true;
          _saver.QueueSave(new SaveReference("Industrial acceptance - verified",_loader.LoadedSave.SettlementReference),
            ()=>Debug.Log("[DeepFrontier Acceptance] SAVED VERIFIED FIXTURE through native GameSaver"));
        }
      } catch (Exception e) {
        _failed=true;
        Debug.LogError("[DeepFrontier Acceptance] FAILED at frame "+_frame+": "+e);
      }
    }
    private void ReviewView(Vector3 target,float distance) {
      _camera.MoveTargetTo(target);_camera.SetZoomLevel(distance,0);
      _camera.HorizontalAngle=35;_camera.VerticalAngle=40;
    }
    private void CaptureReview(string name) {
      string folder=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding/docs/art/reviews/2026-10-19-native-material-fix");
      Directory.CreateDirectory(folder);
      ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
      Debug.Log("[DeepFrontier Acceptance] CAPTURED "+name);
    }
    private BlockObject Create(string name,int x,int y,int z,Orientation orientation=Orientation.Cw0,bool finished=true) {
      var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==name);
      var setup=new EntitySetup.Builder(template.Blueprint);
      if (finished && _templates.GetAll<BuildingSpec>().Any(s=>s.Blueprint==template.Blueprint)) setup.AddInitComponent(new FinishedConstructionSiteInit());
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      // The native collision validator must run BEFORE registration: calling
      // BlockObject.IsValid after creation collides with the object itself.
      if(!_blockValidator.BlocksValid(spec,placement))
        throw new InvalidOperationException($"Native placement rejected {name} at {placement.Coordinates}; invalid blocks: "+string.Join(",",spec.GetBlocks(placement).Where(b=>!_blockValidator.BlockValidWithoutUnfinishedStackable(b)).Take(8).Select(b=>b.Coordinates.ToString())));
      var result=finished?_factory.CreateFinished(setup,placement):_factory.CreateUnfinished(setup,placement);
      if(!_objectValidator.IsValid(result))throw new InvalidOperationException($"Native object requirements rejected {name} at {result.Coordinates}");
      Debug.Log($"[DeepFrontier Acceptance] Placed {name} at {result.Coordinates}, placement and object requirements valid");
      return result;
    }
    private void Setup() {
      // The game starts paused. Native regular navigation is processed by
      // simulation ticks; run the marked fixture before testing its routes.
      _speed.ChangeSpeed(1);
      _camera.MoveTargetTo(new Vector3(166,5,150));
      _camera.SetZoomLevel(35,0);_camera.HorizontalAngle=35;_camera.VerticalAngle=45;
      if (_reload) {
        foreach(var c in Origins)
          _factories.Add(_registry.Entities.Where(e=>e.HasComponent<TemplateSpec>()&&IsIndustrial(e.GetComponent<TemplateSpec>().TemplateName)).Select(e=>e.GetComponent<BlockObject>()).Single(b=>b.Coordinates==c));
        return;
      }
      if (_registry.Entities.Any(e=>e.HasComponent<TemplateSpec>()&&IsIndustrial(e.GetComponent<TemplateSpec>().TemplateName)))
        throw new InvalidOperationException("Initial fixture must not contain industrial buildings. Use a fresh fixture for mutation tests.");
      // Use the same native reset as the developer Water simulation: Reset all
      // button. This disposable workshop test isolates navigation/production
      // from the river that the enlarged pad crosses. Normal worlds are untouched.
      foreach(var entity in _registry.Entities.Where(e=>e.HasComponent<IWaterSource>()))
        entity.GetComponent<IWaterSource>().SetSpecifiedStrength(0);
      _simulation.ResetSimulation();
      // Only this marked disposable fixture is altered. Use the game's public
      // terrain and construction APIs so normal placement constraints execute.
      var toDelete=_registry.Entities.Where(e=>e.HasComponent<BlockObject>()).Where(e=>{
        var c=e.GetComponent<BlockObject>().Coordinates;return c.x>=140&&c.x<195&&c.y>=134&&c.y<175;
      }).ToArray();
      foreach(var e in toDelete)_entities.Delete(e);
      for(int y=134;y<175;y++)for(int x=140;x<195;x++)LevelCell(x,y);
      // The original map contains disconnected overhead terrain, so the pad
      // must clear every solid segment, not only the surface above voxel zero.
      for(int x=132;x<140;x++)LevelCell(x,142);
      for(int y=140;y<142;y++)LevelCell(132,y);
      RequireInstalledFootprints();
      _factories.Add(CreateFactory("StoneCrusher.IronTeeth",0));
      _factories.Add(CreateFactory("StoneCrusher.IronTeeth",1));
      _factories.Add(CreateFactory("CementKiln.IronTeeth",2));
      Create("SandstoneSeam",179,146,3);
      _factories.Add(CreateFactory("SandstoneQuarry.IronTeeth",3));
      Create("LimestoneSeam",179,159,3);
      _factories.Add(CreateFactory("LimestoneQuarry.IronTeeth",4));
      _factories.Add(CreateFactory("StoneCrusher.IronTeeth",5,Orientation.Cw90));
      // Ordinary district road and the existing ground-door approaches.
      for(int x=145;x<186;x++)Create("Path",x,142,3);
      foreach(var c in new[]{new Vector3Int(150,143,3),new Vector3Int(150,144,3),new Vector3Int(156,143,3),new Vector3Int(156,144,3),new Vector3Int(167,143,3),new Vector3Int(177,143,3),new Vector3Int(177,144,3)})Create("Path",c.x,c.y,c.z);
      CheckSolidRooms();
      Debug.Log("[DeepFrontier Acceptance] Fixture setup complete.");
    }
    // 2026-10-22 footprints end at the walls: StoneCrusher 6x7 -> 4x4 (new local = old - (1,2)),
    // CementKiln 9x9 -> 7x5 (old - (1,1)), quarries 11x10 -> 11x7 (old - (0,2)). Each origin
    // below is the former origin plus that offset (rotated for the Cw90 crusher), so every
    // machine, ground-door Entrance, approach path and seam keeps its former world cell and the
    // new footprint lies inside the former one on the levelled pad. Former origins:
    // (148,143) (154,143) (163,143) (176,143) (176,156) (148,156) Cw90.
    private static readonly Vector3Int[] Origins={new(149,145,3),new(155,145,3),new(164,144,3),
      new(176,145,3),new(176,158,3),new(150,155,3)};
    // Former footprint in the new local frame (xMin,xMax,yMin,yMax) and the open ground cells
    // inside the new bounds (tools/validate_freed_cells.mjs, outputs/freed-cells.json).
    private static readonly Dictionary<string,(int,int,int,int,Vector3Int[])> Freed=new() {
      {"StoneCrusher.IronTeeth",(-1,4,-2,4,new Vector3Int[0])},
      // Compact 5x3x4 kiln (2026-10-30, same origin and entrance): no open
      // ground cell inside its bounds; the former 7x5 cells outside it are freed.
      {"CementKiln.IronTeeth",(-1,7,-1,7,new Vector3Int[0])},
      // Compact 8x6x5 quarries (2026-10-30, same origin, entrance and seam
      // cells): every ground cell inside the bounds is occupied.
      {"SandstoneQuarry.IronTeeth",(0,10,-2,7,new Vector3Int[0])},
      {"LimestoneQuarry.IronTeeth",(0,10,-2,7,new Vector3Int[0])}};
    private void RequireInstalledFootprints() {
      foreach(var (id,size,entrance) in new[]{("StoneCrusher.IronTeeth",new Vector3Int(4,4,5),new Vector3Int(1,-1,0)),
        ("CementKiln.IronTeeth",new Vector3Int(5,3,4),new Vector3Int(3,-1,0)),
        ("SandstoneQuarry.IronTeeth",new Vector3Int(8,6,5),new Vector3Int(1,-1,0)),
        ("LimestoneQuarry.IronTeeth",new Vector3Int(8,6,5),new Vector3Int(1,-1,0))}) {
        var spec=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==id).Blueprint.GetSpec<BlockObjectSpec>();
        if(spec.Size!=size||spec.Entrance.Coordinates!=entrance)
          throw new InvalidOperationException($"Installed {id} is {spec.Size} with entrance {spec.Entrance.Coordinates}; this fixture's origins, approach paths and walk targets encode {size} with entrance {entrance}.");
      }
    }
    private BlockObject CreateFactory(string name,int index,Orientation orientation=Orientation.Cw0) {
      var c=Origins[index];var b=Create(name,c.x,c.y,c.z,orientation);
      var (xMin,xMax,yMin,yMax,inside)=Freed[name];
      var size=b.GetComponent<BlockObjectSpec>().Size;
      FreedCellProbe.Require(_templates,_blockValidator,b,inside.Concat(FreedCellProbe.Outside(xMin,xMax,yMin,yMax,size)),
        $"{name} #{index}",message=>Debug.Log("[DeepFrontier Acceptance] PASS FREED CELLS "+message));
      return b;
    }
    private BlockObject CreateLocal(BlockObject b,string name,Vector3Int cell,Orientation orientation=Orientation.Cw0) {
      var c=b.TransformCoordinates(cell);return Create(name,c.x,c.y,c.z,orientation);
    }
    private static bool IsIndustrial(string name)=>name=="StoneCrusher.IronTeeth"||name=="CementKiln.IronTeeth"||name.EndsWith("Quarry.IronTeeth");
    private void CheckSolidRooms() {
      // Occupied rooms reject native paths (no hidden walkable cells).
      var path=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Path");
      var spec=_templates.GetAll<BlockObjectSpec>().Single(o=>o.Blueprint==path.Blueprint);
      // The same occupied cells as before the 2026-10-22 footprint pass, in the new local frames.
      foreach(var test in new[]{(0,new Vector3Int(2,1,0)),(2,new Vector3Int(3,2,0)),(3,new Vector3Int(1,3,1))}) {
        var b=_factories[test.Item1];var c=b.TransformCoordinates(test.Item2);
        if(_blockValidator.BlocksValid(spec,new Placement(c,Orientation.Cw0,FlipMode.Unflipped)))
          throw new InvalidOperationException($"Occupied room incorrectly accepts a path: {b.Name} {test.Item2}");
        Debug.Log($"[DeepFrontier Acceptance] PASS SOLID ROOM REJECTS PATH {b.Name} at {test.Item2}");
      }
    }
    private void LevelCell(int x,int y) {
      var surfaces=_terrain.GetAllHeightsInCell(new Vector2Int(x,y)).Where(c=>c.z>3).OrderByDescending(c=>c.z).ToArray();
      foreach(var top in surfaces)_terrain.UnsetTerrain(new Vector3Int(x,y,top.z-1),top.z-3);
      int height=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
      if(height<3)_terrain.SetTerrain(new Vector3Int(x,y,height),3-height);
      if(_terrain.GetTerrainHeight(new Vector3Int(x,y,0))!=3 || Enumerable.Range(3,_terrain.Size.z-3).Any(z=>_terrain.Underground(new Vector3Int(x,y,z))))
        throw new InvalidOperationException($"Fixture terrain is not a clear level pad at {x},{y}");
    }
    private static Vector3Int FirstHorizontal(string directions) {
      foreach(var d in directions.Split(',').Select(x=>x.Trim())) {
        if(d=="Left")return Vector3Int.left;
        if(d=="Right")return Vector3Int.right;
        if(d=="Down")return Vector3Int.down;
        if(d=="Up")return Vector3Int.up;
      }
      throw new InvalidOperationException($"Transput has no horizontal face: {directions}");
    }
    private void SetupProduction() {
      // Native developer generators isolate the workshop test from a separate
      // power-plant test. Only recipe INPUTS are seeded; products must be made.
      foreach(var index in new[]{0,2,3,4}) {
        var building=_factories[index];
        var transput=building.GetComponent<TransputProviderSpec>().Transputs[0];
        // Shafts meet authored walls only: build beside the first transput's
        // first horizontal face (a Left face wherever the building has one).
        var step=FirstHorizontal(transput.Directions.ToString());
        var shaft=CreateLocal(building,"PowerShaft.IronTeeth",transput.Coordinates+step);
        var generator=CreateLocal(building,"DevPowerGenerator",transput.Coordinates+step*2);
        _powerTests.Add((building,shaft,generator));
        var manufactory=building.GetComponent<Manufactory>();
        var recipe=manufactory.CurrentRecipe;
        foreach(var good in recipe.Ingredients)manufactory.Inventory.GiveExisting(new GoodAmount(good.Id,good.Amount*2));
        if(recipe.ConsumesFuel)manufactory.Inventory.GiveExisting(new GoodAmount(recipe.Fuel,2));
        string name=building.GetComponent<TemplateSpec>().TemplateName;
        manufactory.ProductionFinished+=(sender,args)=>{
          _produced.Add(name);
          Debug.Log($"[DeepFrontier Acceptance] PRODUCED {name}: "+string.Join(", ",recipe.Products.Select(g=>$"{g.Id}={manufactory.Inventory.AmountInStock(g.Id)}")));
          if(_produced.Count==4)Debug.Log("[DeepFrontier Acceptance] ALL FOUR NATIVE WORKSHOPS PRODUCED");
        };
      }
      // Join the fixture road to the existing district entrance and the second
      // quarry, using actual native paths and their normal placement checks.
      for(int x=132;x<145;x++)Create("Path",x,142,3);
      for(int y=139;y<142;y++)if(!_blocks.GetPathObjectAt(new Vector3Int(132,y,3)))Create("Path",132,y,3);
      for(int y=143;y<157;y++)Create("Path",173,y,3);
      for(int x=174;x<178;x++)Create("Path",x,155,3);
      Create("Path",177,156,3);
      Create("Path",177,157,3);
      var workers=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").Take(4).ToArray();
      if(workers.Length!=4)throw new InvalidOperationException("Production fixture requires four adult beaver workers.");
      for(int i=0;i<workers.Length;i++) {
        var worker=workers[i];if(worker.Employed)worker.Workplace.UnassignWorker(worker);
        var workplace=_factories[new[]{0,2,3,4}[i]].GetComponent<Workplace>();
        if(workplace.Understaffed)workplace.AssignWorker(worker);
      }
      ReportProduction();
    }
    private void CheckPower() {
      foreach(var test in _powerTests) {
        var factory=test.Factory.GetComponent<MechanicalNode>();
        var shaft=test.Shaft.GetComponent<MechanicalNode>();var generator=test.Generator.GetComponent<MechanicalNode>();
        if(!factory.Transputs.Any(t=>t.ConnectedNode==shaft)||factory.Graph!=shaft.Graph||factory.Graph!=generator.Graph||factory.Graph.PowerSupply<=0)
          throw new InvalidOperationException($"Native generator -> shaft -> factory connection failed: {test.Factory.Name}");
        Debug.Log($"[DeepFrontier Acceptance] PASS SHAFT POWER {test.Factory.Name}: supply={factory.Graph.PowerSupply} hp, efficiency={factory.PowerEfficiency}");
      }
    }
    private void ReportProduction() {
      foreach(var index in new[]{0,2,3,4}) {
        var b=_factories[index];var m=b.GetComponent<Manufactory>();var p=b.GetComponent<MechanicalNode>();var w=b.GetComponent<Workplace>();
        Debug.Log($"[DeepFrontier Acceptance] WORKSHOP {b.Name}: registered={b.AddedToService}, requirements={_objectValidator.IsValid(b)}, workers={w.NumberOfAssignedWorkers}, job={w.AnyWorkerHasJobRunning()}, ready={m.IsReadyToProduce}, progress={m.ProductionProgress}, power={p.PowerEfficiency}, stock={string.Join(",",m.CurrentRecipe.Products.Select(g=>$"{g.Id}={m.Inventory.AmountInStock(g.Id)}"))}");
      }
    }
    private void SetupTraversal() {
      var worker=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>()).Where(w=>w.WorkerType=="Beaver").Skip(4).First();
      if(worker.Employed)worker.Workplace.UnassignWorker(worker);
      _walker=worker.GetComponent<ControllableCharacter>();
      if(!_walker.GetAnimationNames().Contains("BeaverAdult_idle"))throw new InvalidOperationException("Native BeaverAdult_idle clip is required for the traversal fixture.");
      _walker.ChangeAnimation("BeaverAdult_idle");
      // Ground-door entrance path cells only: nobody walks on the machines.
      AddNativeWalkTarget(0,new Vector3Int(1,-1,0),"crusher ground door entrance");
      AddNativeWalkTarget(1,new Vector3Int(1,-1,0),"second crusher ground door entrance");
      AddNativeWalkTarget(2,new Vector3Int(3,-1,0),"kiln ground door entrance");
      AddNativeWalkTarget(3,new Vector3Int(1,-1,0),"quarry ground door entrance");
      NextWalkTarget();
    }
    private void AddNativeWalkTarget(int index,Vector3Int cell,string label) {
      _walkTargets.Enqueue((label,NavigationCoordinateSystem.GridToWorld(_factories[index].TransformCoordinates(cell))));
    }
    private void NextWalkTarget() {
      if(_walkTargets.Count==0) {
        _walker.ReleaseControl();_walker=null;
        Debug.Log("[DeepFrontier Acceptance] ALL NATIVE BEAVER TRAVERSAL TARGETS REACHED");
        return;
      }
      _walkTarget=_walkTargets.Dequeue();
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_walkTarget.World));
      Debug.Log($"[DeepFrontier Acceptance] WALK TO {_walkTarget.Label}: {_walkTarget.World}");
    }
    private void CheckTraversal() {
      if(!_walker)return;
      if(Vector3.Distance(_walker.Transform.position,_walkTarget.World)<.18f) {
        Debug.Log($"[DeepFrontier Acceptance] PASS BEAVER WALK {_walkTarget.Label}: {_walker.Transform.position}");
        NextWalkTarget();
      } else if(_frame%1800==0)Debug.Log($"[DeepFrontier Acceptance] WALKING {_walkTarget.Label}: {_walker.Transform.position}, target={_walkTarget.World}");
    }
    private void Audit(string phase) {
      // Native route from the district road to each ground door's Entrance
      // path cell. Nobody walks on the machines, so there are no deck routes.
      var failures=new List<Exception>();
      foreach(var building in _factories) {
        var ident=building.GetComponent<TemplateSpec>().TemplateName;
        if(!building.HasEntrance)throw new InvalidOperationException($"{ident} has no native entrance");
        var door=building.PositionedEntrance.Coordinates;
        Debug.Log($"[DeepFrontier Acceptance] {building.Name}: finished={building.IsFinished}, registered={building.AddedToService}, requirements={_objectValidator.IsValid(building)}, entrance={door}");
        // The rotated crusher has no approach path in this fixture.
        if(building.Orientation!=Orientation.Cw0)continue;
        var start=NavigationCoordinateSystem.GridToWorld(new Vector3Int(door.x,142,3));
        var end=NavigationCoordinateSystem.GridToWorld(door);
        var corners=new List<PathCorner>();
        if(!_pathfinding.FindPathUnlimitedRange(start,end,corners,out var distance)) {
          var error=new InvalidOperationException($"{phase}: no native route from the road to the ground door of {building.Name}");
          failures.Add(error);Debug.LogError("[DeepFrontier Acceptance] "+error.Message);
        } else Debug.Log($"[DeepFrontier Acceptance] PASS {phase} DOOR ROUTE {building.Name}: {corners.Count} corners, distance={distance}");
      }
      if(failures.Count>0)throw new AggregateException("Industrial ground-door acceptance failed",failures);
    }
  }
}
