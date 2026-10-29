using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Linq;
using Bindito.Core;
using Timberborn.BlockObjectModelSystem;
using Timberborn.BlockObjectTools;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Coordinates;
using Timberborn.SelectionSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.ToolSystem;
using UnityEngine;
using Debug = UnityEngine.Debug;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class PreviewCostAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierPreviewCost"))
        Bind<PreviewCostAcceptance>().AsSingleton();
    }
  }

  // Explicit measurement launch (-deepFrontierPreviewCost, tools/start_preview_cost.ps1).
  // For each building it drives the exact native placement path the build tool
  // runs every frame (PreviewFactory + PreviewPlacer.ShowPreviews at one
  // buildable placement) and times it, then times its parts the same way the
  // native code calls them: the IPreviewServiceMember round trip (preview
  // blocks, preview navmesh, districts), highlighting (Highlighter
  // UnhighlightAllPrimary + HighlightPrimary), block validation and the model
  // updaters. Native previews only: nothing is placed, saved or removed, and
  // the game stays paused. Vanilla references give the baseline.
  internal sealed class PreviewCostAcceptance : IPostLoadableSingleton, IUpdatableSingleton {
    private static readonly string[] DeepFrontier={
      "ArchiveExcavation","Bathhouse","CementKiln","CoalPowerPlant","OilPowerPlant","ChemicalWorks","ConcreteBlock","ConcreteMixer",
      "ConcreteOverflowDam","ConcreteOverhang8x1","ConcreteScaffold5x5H3","ConcreteSidePlatform5x5",
      "CryogenicLiquefactionPlant","CryogenicTankFarm","DeepDrill","DeepMine","DeepProcessor",
      "ElectrolysisPlant","FertilizerWorks","FishHatchery","FisheryWorks","FoodPackagingWorks",
      "Greenhouse","GroceryStore","Hospital","LaunchPad","LimestonePit","LimestoneQuarry",
      "MaterialsLaboratory","MissionControl","NuclearReactor","ObservationDeck","PrecisionMachineWorks",
      "PublicHealthLab","RadioactiveSludgeOutfall","RadioactiveSludgeRecoveryPump","RadioactiveWasteExport",
      "RadioactiveWasteRefinery","RadioactiveWasteVault","ReinforcedDamBlock","ReinforcedHydroTurbine",
      "Restaurant","RocketAssemblyHangar","SandstonePit","SmogScrubber","SteelBridge15x1","SteelCantilever15x1",
      "SteelColumnH6","SteelDeck5x5","SteelMill","StoneCrusher",
      "TechnicalSchool","TownPlaza","UraniumProcessingPlant","WaterTreatmentPlant"
    };
    private static readonly string[] First={
      "NuclearReactor","LaunchPad","RocketAssemblyHangar","SteelMill","CoalPowerPlant","OilPowerPlant"
    };
    private static readonly string[] Vanilla={
      "Smelter","LargeTank","MudBath","DistrictCenter","HydroponicGarden","Motivatorium","EarthRepopulator"
    };
    private const int ShowSamples=20,MoveSamples=30,PartRepeats=10,SiteStep=3,SweepPlacements=6;
    private const float RestWindowSeconds=0.6f;
    // Per building: native (all caches off) still and moving, then shipped
    // still, moving, and holding still after moving (the deferred navmesh
    // swap lands in that window). Moving = a different buildable placement
    // every frame, as a dragged mouse gives.
    private enum Phase { NativeStill, NativeMoving, ShippedStill, ShippedMoving, ShippedRest, Done }
    private static readonly string[] PhaseNames={"nativeStill","nativeMoving","shippedStill","shippedMoving","shippedRest"};
    private readonly TemplateService _templates;
    private readonly PreviewFactory _previewFactory;
    private readonly PreviewShower _previewShower;
    private readonly BlockObjectValidationService _validation;
    private readonly Highlighter _highlighter;
    private readonly ISpecService _specs;
    private readonly ITerrainService _terrain;
    private readonly EventBus _events;
    private readonly SpeedManager _speed;
    private readonly List<string> _queue=new();
    private readonly List<double>[] _samples={new(),new(),new(),new(),new()};
    private readonly List<Placement> _sweep=new();
    private Phase _phase;
    private int _frame;
    private float _restStart,_shippedStart;
    private long _rebuilds,_kept,_deferred,_generated,_reused,_worldChanges;
    private readonly List<IPreviewServiceMember> _members=new();
    private readonly List<string> _summary=new();
    private Color _buildable;
    private string _name;
    private Preview _preview;
    private PreviewPlacer _placer;
    private Placement _placement;
    private bool _ready,_finished;

    public PreviewCostAcceptance(TemplateService templates,PreviewFactory previewFactory,PreviewShower previewShower,
        BlockObjectValidationService validation,Highlighter highlighter,ISpecService specs,ITerrainService terrain,
        EventBus events,SpeedManager speed) {
      _templates=templates;_previewFactory=previewFactory;_previewShower=previewShower;_validation=validation;
      _highlighter=highlighter;_specs=specs;_terrain=terrain;_events=events;_speed=speed;
    }

    public void PostLoad() {
      _speed.ChangeSpeed(0);
      _buildable=_specs.GetSingleSpec<PreviewShowerSpec>().BuildablePreview;
      // The heaviest previews first, then the vanilla baseline, then the rest.
      _queue.AddRange(First.Select(n=>"df:"+n));
      _queue.AddRange(Vanilla.Select(n=>"vanilla:"+n));
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierPreviewCostAll"))
        _queue.AddRange(DeepFrontier.Except(First).Select(n=>"df:"+n));
      _ready=true;
      Debug.Log($"[DeepFrontier PreviewCost] START buildings={_queue.Count} showSamples={ShowSamples} partRepeats={PartRepeats}");
    }

    public void UpdateSingleton() {
      if(!_ready||_finished)return;
      try {
        if(_preview==null) {
          if(_queue.Count==0) {Finish();return;}
          Begin(_queue[0]);_queue.RemoveAt(0);
        } else if(_phase==Phase.Done) {
          Report();End();
        } else {
          Step();
        }
      } catch(Exception error) {
        _finished=true;
        Debug.LogError("[DeepFrontier PreviewCost] FAILED at "+_name+": "+error);
      }
    }

    private void Begin(string entry) {
      _name=entry;
      string template=entry.Substring(entry.IndexOf(':')+1)+".IronTeeth";
      var blueprint=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==template).Blueprint;
      var placeable=_templates.GetAll<PlaceableBlockObjectSpec>().Single(p=>p.Blueprint==blueprint);
      _preview=_previewFactory.Create(placeable);
      var preview=_preview;
      _placer=new PreviewPlacer(_previewShower,_validation,false,new Lazy<Preview[]>(()=>new[]{preview}));
      foreach(var list in _samples)list.Clear();
      _sweep.Clear();_phase=Phase.NativeStill;_frame=0;
      if(!FindSite(_preview.BlockObject,out _placement)) {
        Debug.LogWarning("[DeepFrontier PreviewCost] NO-SITE "+_name+": no buildable placement found on this map; skipped");
        _summary.Add(_name+" no-site");
        End();
        return;
      }
      FindSweep(_preview.BlockObject);
      SwitchCache(false,_placement);
      if(!_preview.GameObject.activeSelf||!_preview.PreviewState.IsBuildable)
        throw new InvalidOperationException("The found placement did not show a buildable preview");
    }

    // One native ShowPreviews per frame, as the build tool does.
    private void Step() {
      bool moving=_phase==Phase.NativeMoving||_phase==Phase.ShippedMoving;
      if(moving&&_sweep.Count<2) {Advance();return;}
      Placement placement;
      if(_phase==Phase.NativeStill||_phase==Phase.ShippedStill)placement=_placement;
      else if(_phase==Phase.ShippedRest)placement=_sweep.Count>=2?_sweep[(MoveSamples-1)%_sweep.Count]:_placement;
      else placement=_sweep[_frame%_sweep.Count];
      var watch=Stopwatch.StartNew();
      _placer.ShowPreviews(new[]{placement});
      _samples[(int)_phase].Add(watch.Elapsed.TotalMilliseconds);
      _frame++;
      bool done;
      if(_phase==Phase.NativeStill||_phase==Phase.ShippedStill)done=_frame>=ShowSamples;
      else if(_phase==Phase.ShippedRest)done=Time.unscaledTime-_restStart>=RestWindowSeconds&&_frame>=5;
      else done=_frame>=MoveSamples;
      if(done)Advance();
    }

    private void Advance() {
      _phase++;_frame=0;
      if(_phase==Phase.ShippedStill) {
        SwitchCache(true,_placement);
        _shippedStart=Time.unscaledTime;
      } else if(_phase==Phase.ShippedRest) {
        _restStart=Time.unscaledTime;
      }
    }

    // Other buildable placements a few cells around the found site. The
    // moving phases end on a sweep placement other than the base one, so the
    // rest phase holds a placement whose navmesh list is not applied yet.
    private void FindSweep(BlockObject block) {
      var spec=block.GetComponent<BlockObjectSpec>();
      _sweep.Add(_placement);
      var size=_terrain.Size;
      for(int r=1;r<=6&&_sweep.Count<SweepPlacements;r++)
        for(int dx=-r;dx<=r&&_sweep.Count<SweepPlacements;dx++)
          for(int dy=-r;dy<=r&&_sweep.Count<SweepPlacements;dy++) {
            if(Math.Max(Math.Abs(dx),Math.Abs(dy))!=r)continue;
            int x=_placement.Coordinates.x+dx,y=_placement.Coordinates.y+dy;
            if(x<1||y<1||x+spec.Size.x>=size.x||y+spec.Size.y>=size.y)continue;
            int ground=_terrain.GetTerrainHeightBelow(new Vector3Int(x,y,size.z-1));
            for(int z=ground-spec.BaseZ-1;z<=ground-spec.BaseZ+1;z++) {
              var candidate=new Placement(new Vector3Int(x,y,z),Orientation.Cw0,new FlipMode(false));
              block.Reposition(candidate);
              if(block.IsValid()) {_sweep.Add(candidate);break;}
            }
          }
      if(_sweep.Count>=2&&(MoveSamples-1)%_sweep.Count==0)_sweep.Add(_sweep[1]);
      block.Reposition(_placement);
    }

    // The cache may only switch while no preview is in the preview services.
    private void SwitchCache(bool enabled,Placement placement) {
      _placer.HideAllPreviews();
#if !UNITY_EDITOR
      PreviewNavMesh.PreviewNavMeshCache.SetEnabledForMeasurement(enabled);
      _rebuilds=PreviewNavMesh.PreviewNavMeshCache.Rebuilds;_kept=PreviewNavMesh.PreviewNavMeshCache.KeptApplied;
      _deferred=PreviewNavMesh.PreviewNavMeshCache.DeferredMoves;
      _generated=PreviewNavMesh.PreviewAccessCache.Generated;_reused=PreviewNavMesh.PreviewAccessCache.Reused;
      _worldChanges=PreviewNavMesh.PreviewAccessCache.WorldChanges;
#endif
      _placer.ShowPreviews(new[]{placement});
    }

    // Native validity at Cw0 on a coarse grid over the map, at terrain height.
    private bool FindSite(BlockObject block,out Placement placement) {
      var spec=block.GetComponent<BlockObjectSpec>();
      var size=_terrain.Size;
      for(int y=1;y+spec.Size.y<size.y;y+=SiteStep)
        for(int x=1;x+spec.Size.x<size.x;x+=SiteStep) {
          int ground=_terrain.GetTerrainHeightBelow(new Vector3Int(x,y,size.z-1));
          for(int z=ground-spec.BaseZ-1;z<=ground-spec.BaseZ+1;z++) {
            var candidate=new Placement(new Vector3Int(x,y,z),Orientation.Cw0,new FlipMode(false));
            block.Reposition(candidate);
            if(block.IsValid()) {placement=candidate;return true;}
          }
        }
      placement=default;
      return false;
    }

    private void Report() {
      var block=_preview.BlockObject;
      var renderers=_preview.GameObject.GetComponentsInChildren<MeshRenderer>(true);
      int slots=renderers.Sum(r=>r.sharedMaterials.Length);
      var blocks=block.PositionedBlocks.GetAllBlocks();
      int occupied=blocks.Count(b=>b.IsOccupied);
      var parts=new List<string>();
      _preview.GetComponents(_members);
      foreach(var member in _members) {
        parts.Add($"{member.GetType().Name}={Median(PartRepeats,()=>{member.RemoveFromPreviewService();member.AddToPreviewService();}):0.000}");
      }
      _members.Clear();
      double highlight=Median(PartRepeats,()=>{_highlighter.UnhighlightAllPrimary();_highlighter.HighlightPrimary(_preview,_buildable);});
      _highlighter.UnhighlightAllPrimary();
      var single=new List<Timberborn.BaseComponentSystem.BaseComponent>{_preview};
      double valid=Median(PartRepeats,()=>{block.IsValid();_validation.AreValid(single,out _);});
      var model=_preview.GetComponent<BlockObjectModelController>();
      double models=Median(PartRepeats,model.UpdateModel);
      // Preview.Show calls every IPreviewSelectionListener.OnPreviewSelect each
      // frame; each is timed alone. PreviewDistrictAdder adds a preview district
      // per call and needs the services round trip in between, so it is skipped.
      var listeners=new List<IPreviewSelectionListener>();
      _preview.GetComponents(listeners);
      var selects=new List<string>();
      foreach(var listener in listeners) {
        if(listener.GetType().Name=="PreviewDistrictAdder")continue;
        selects.Add($"{listener.GetType().Name}={Median(PartRepeats,listener.OnPreviewSelect):0.000}");
      }
      long rebuilds=0,kept=0,deferred=0,generated=0,reused=0,worldChanges=0;
#if !UNITY_EDITOR
      rebuilds=PreviewNavMesh.PreviewNavMeshCache.Rebuilds-_rebuilds;kept=PreviewNavMesh.PreviewNavMeshCache.KeptApplied-_kept;
      deferred=PreviewNavMesh.PreviewNavMeshCache.DeferredMoves-_deferred;
      generated=PreviewNavMesh.PreviewAccessCache.Generated-_generated;reused=PreviewNavMesh.PreviewAccessCache.Reused-_reused;
      worldChanges=PreviewNavMesh.PreviewAccessCache.WorldChanges-_worldChanges;
#endif
      float seconds=Mathf.Max(Time.unscaledTime-_shippedStart,0.001f);
      var phases=new List<string>();
      for(int i=0;i<_samples.Length;i++) {
        var list=_samples[i];
        if(list.Count==0) {phases.Add(PhaseNames[i]+"=n/a");continue;}
        list.Sort();
        phases.Add($"{PhaseNames[i]} median={list[list.Count/2]:0.000} max={list[list.Count-1]:0.000} n={list.Count}");
      }
      string line=$"{_name} blocks={blocks.Length} occupied={occupied} renderers={renderers.Length} slots={slots} sweep={_sweep.Count} | "+
        string.Join(" | ",phases)+$" (ms) | shipped: {rebuilds} list rebuilds, {kept} kept, {deferred} deferred moves, {generated} access generations, {reused} reused, "+
        $"{worldChanges} world changes in {seconds:0.0}s | "+
        $"services[{string.Join(" ",parts)}] highlight={highlight:0.000} validate={valid:0.000} "+
        $"modelUpdaters={models:0.000} onPreviewSelect[{string.Join(" ",selects)}] (ms)";
      _summary.Add(line);
      Debug.Log("[DeepFrontier PreviewCost] "+line);
    }

    private void End() {
      if(_placer!=null)_placer.HideAllPreviews();
      // BuildingWithRangePreviewUpdater keeps its preview registered until a tool exits.
      _events.Post(new ToolExitedEvent(null));
      if(_preview!=null)UnityEngine.Object.Destroy(_preview.GameObject);
      _preview=null;_placer=null;
    }

    private void Finish() {
      _finished=true;
      Debug.Log("[DeepFrontier PreviewCost] ALL MEASURED buildings="+_summary.Count+"\n"+string.Join("\n",_summary));
    }

    private static double Median(int repeats,Action action) {
      var samples=new double[repeats];
      for(int i=0;i<repeats;i++) {
        var watch=Stopwatch.StartNew();action();samples[i]=watch.Elapsed.TotalMilliseconds;
      }
      Array.Sort(samples);
      return samples[repeats/2];
    }
  }
}
