using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using Timberborn.Automation;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.Coordinates;
using Timberborn.EntitySystem;
using Timberborn.MapIndexSystem;
using Timberborn.MechanicalSystem;
using Timberborn.Persistence;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record HydroTurbineSpec : ComponentSpec {
    [Serialize] public ImmutableArray<Vector3Int> Intakes { get; init; }
    [Serialize] public ImmutableArray<Vector3Int> Outlets { get; init; }
    [Serialize] public ImmutableArray<Vector3Int> Gates { get; init; }
    [Serialize] public ImmutableArray<Vector3Int> SolidWaterCells { get; init; }
    [Serialize] public ImmutableArray<Vector3Int> ClosedGateCells { get; init; }
    [Serialize] public float MaxDischarge { get; init; }
    [Serialize] public float DefaultDischarge { get; init; }
    [Serialize] public float HpPerFlowAndHead { get; init; }
    [Serialize] public float MaxGeneratingHead { get; init; }
    [Serialize] public float AnimationSpeedMultiplier { get; init; }
  }

  // Native water owns volume, contamination, pressure and transit time.
  // This component registers the authored dam seal and its controllable aperture.
  internal sealed class HydroTurbine : BaseComponent, IAwakableComponent,
      IFinishedStateListener, IPersistentEntity, IPrePlacementChangeListener,
      IPostPlacementChangeListener,IAutomatableNeeder {
    private static readonly ComponentKey Key=new("DeepFrontier.HydroTurbine");
    private static readonly PropertyKey<float> DischargeKey=new("DischargeLimit");
    private static readonly PropertyKey<bool> ClosedKey=new("ManuallyClosed");
    private readonly IWaterService _water;
    private readonly HydroTurbineSimulation _simulation;
    private readonly NonlinearAnimationManager _animation;
    private readonly EventBus _events;
    private readonly HydroTurbinePlacementValidator _placement;
    private BlockObject _block;
    private MechanicalNode _node;
    private Automatable _automatable;
    private PausableBuilding _pausable;
    private IAnimator _animator;
    private Vector3Int[] _solidCells,_gateCells;
    private bool _finished,_registered,_gateClosed;
    public HydroTurbineSpec Spec { get; private set; }
    public float DischargeLimit { get; private set; }
    public bool ManuallyClosed { get; private set; }
    public Vector3Int[] Gates { get; private set; }
    public Vector3Int[] Intakes { get; private set; }
    public Vector3Int[] Outlets { get; private set; }
    public float[] ChannelFlows { get; private set; }
    public float[] ChannelHeads { get; private set; }
    public Vector3Int Forward { get; private set; }
    public float ActualFlow { get; private set; }
    public float AvailableHead { get; private set; }
    public float UpstreamHeight { get; private set; }
    public float DownstreamHeight { get; private set; }
    public float OutputHp { get; private set; }
    public string State { get; private set; }="Under construction";
    public bool GateIsClosed=>_gateClosed;
    public bool NeedsAutomatable=>true;

    public HydroTurbine(IWaterService water,HydroTurbineSimulation simulation,
      NonlinearAnimationManager animation,EventBus events,HydroTurbinePlacementValidator placement) {
      _water=water;_simulation=simulation;_animation=animation;_events=events;_placement=placement;
    }
    public void Awake() {
      Spec=GetComponent<HydroTurbineSpec>();_block=GetComponent<BlockObject>();
      _node=GetComponent<MechanicalNode>();
      _automatable=GetComponent<Automatable>();
      _pausable=GetComponent<PausableBuilding>();
      if(Spec.MaxDischarge<=0||Spec.DefaultDischarge<0||Spec.DefaultDischarge>Spec.MaxDischarge
        ||Spec.HpPerFlowAndHead<=0||Spec.MaxGeneratingHead<=0
        ||!float.IsFinite(Spec.AnimationSpeedMultiplier)||Spec.AnimationSpeedMultiplier<=0
        ||Spec.SolidWaterCells.IsDefaultOrEmpty||Spec.ClosedGateCells.IsDefaultOrEmpty
        ||Spec.SolidWaterCells.Distinct().Count()!=Spec.SolidWaterCells.Length
        ||Spec.ClosedGateCells.Distinct().Count()!=Spec.ClosedGateCells.Length
        ||Spec.SolidWaterCells.Intersect(Spec.ClosedGateCells).Any()
        ||Spec.Gates.IsDefaultOrEmpty||Spec.Intakes.IsDefaultOrEmpty||Spec.Outlets.IsDefaultOrEmpty
        ||Spec.Intakes.Length!=Spec.Gates.Length||Spec.Outlets.Length!=Spec.Gates.Length
        ||Spec.Gates.Distinct().Count()!=Spec.Gates.Length)
        throw new InvalidOperationException("Invalid authored turbine water/power contract");
      for(int i=0;i<Spec.Gates.Length;i++) {
        var gate=Spec.Gates[i];var intake=Spec.Intakes[i];var outlet=Spec.Outlets[i];
        if(!Spec.ClosedGateCells.Contains(gate)||intake.x!=gate.x||outlet.x!=gate.x
          ||intake.y>=gate.y||outlet.y<=gate.y||intake.z!=gate.z||outlet.z!=gate.z
          ||(i>0&&gate!=Spec.Gates[i-1]+Vector3Int.right))
          throw new InvalidOperationException("Turbine channels must form a contiguous authored aperture");
      }
      ChannelFlows=new float[Spec.Gates.Length];ChannelHeads=new float[Spec.Gates.Length];
      float rated=Spec.MaxDischarge*Spec.MaxGeneratingHead*Spec.HpPerFlowAndHead;
      var mechanical=GetComponent<MechanicalNodeSpec>();
      // The authored coefficient is ratedHp / (discharge x head) (833.33 hp): compare within float precision.
      if(mechanical.PowerInput!=0||Mathf.Abs(mechanical.PowerOutput-rated)>mechanical.PowerOutput*1e-5f)
        throw new InvalidOperationException("Turbine mechanical rating differs from its authored flow/head rating");
      DischargeLimit=Spec.DefaultDischarge;
      _node.SetOutputMultiplier(0);
    }
    public void SetDischargeLimit(float value) {
      if(float.IsNaN(value)||float.IsInfinity(value)||value<0||value>Spec.MaxDischarge)
        throw new ArgumentOutOfRangeException(nameof(value),"Discharge must be within the authored turbine range");
      DischargeLimit=value;
      if(_registered)ApplyGate();
    }
    public void SetClosed(bool closed) {
      ManuallyClosed=closed;
      if(_registered)ApplyGate();
    }
    public void Save(IEntitySaver saver) {
      var data=saver.GetComponent(Key);
      data.Set(DischargeKey,DischargeLimit);data.Set(ClosedKey,ManuallyClosed);
    }
    public void Load(IEntityLoader loader) {
      var data=loader.GetComponent(Key);
      SetDischargeLimit(data.Get(DischargeKey));SetClosed(data.Get(ClosedKey));
    }
    public void OnEnterFinishedState() {
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      _animator=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      _animator.Play("Default");_animator.SetTime(0);_animator.Enabled=false;
      _finished=true;_events.Register(this);
      _automatable.InputStateChanged+=OnAutomationChanged;
      _automatable.InputReconnected+=OnAutomationChanged;
      _pausable.PausedChanged+=OnPauseChanged;
      InstallWater();
    }
    public void OnExitFinishedState() {
      RemoveWater();_events.Unregister(this);
      _automatable.InputStateChanged-=OnAutomationChanged;
      _automatable.InputReconnected-=OnAutomationChanged;
      _pausable.PausedChanged-=OnPauseChanged;
      _animator.Stop();_finished=false;
      State="Under construction";
    }
    public void OnPrePlacementChanged() {if(_registered)RemoveWater();}
    public void OnPostPlacementChanged() {if(_finished)InstallWater();}
    private void OnAutomationChanged(object sender,EventArgs args) {if(_registered)ApplyGate();}
    private void OnPauseChanged(object sender,EventArgs args) {if(_registered)ApplyGate();}
    private void InstallWater() {
      if(_registered)throw new InvalidOperationException("Turbine water registration duplicated");
      if(!_placement.IsValid(_block,out var error))throw new InvalidOperationException(error);
      Gates=Spec.Gates.Select(_block.TransformCoordinates).ToArray();
      Intakes=Spec.Intakes.Select(_block.TransformCoordinates).ToArray();
      Outlets=Spec.Outlets.Select(_block.TransformCoordinates).ToArray();
      Forward=_block.TransformCoordinates(Spec.Gates[0]+Vector3Int.up)-Gates[0];
      _solidCells=Spec.SolidWaterCells.Select(_block.TransformCoordinates).ToArray();
      _gateCells=Spec.ClosedGateCells.Select(_block.TransformCoordinates).ToArray();
      foreach(var cell in _solidCells)_water.AddFullObstacle(cell);
      foreach(var gate in Gates)_water.AddDirectionLimiter(gate,_block.Orientation.ToFlowDirection());
      _registered=true;_gateClosed=false;ApplyGate();_simulation.Register(this);
    }
    private void RemoveWater() {
      if(!_registered)throw new InvalidOperationException("Turbine water registration missing");
      _simulation.Unregister(this);
      if(_gateClosed)foreach(var cell in _gateCells)_water.RemoveFullObstacle(cell);
      foreach(var cell in _solidCells)_water.RemoveFullObstacle(cell);
      foreach(var gate in Gates) {_water.RemoveInflowLimit(gate);_water.RemoveDirectionLimiter(gate);}
      _registered=false;_gateClosed=false;SetOutput(0);
    }
    private void ApplyGate() {
      bool closed=_pausable.Paused||ManuallyClosed||DischargeLimit==0||
        (_automatable.IsAutomated&&_automatable.State!=ConnectionState.On);
      if(closed!=_gateClosed) {
        foreach(var cell in _gateCells) {
          if(closed)_water.AddFullObstacle(cell);else _water.RemoveFullObstacle(cell);
        }
        _gateClosed=closed;
      }
      // The player's setting is the total aperture flow, not a per-cell limit.
      foreach(var gate in Gates)_water.SetInflowLimit(gate,closed?0:DischargeLimit/Gates.Length);
      if(closed) {ActualFlow=0;Array.Clear(ChannelFlows,0,ChannelFlows.Length);SetOutput(0);State=_pausable.Paused?"Paused":"Closed";}
    }
    internal void BeginMeasurement() {ActualFlow=0;AvailableHead=0;UpstreamHeight=0;DownstreamHeight=0;}
    internal float MeasureChannel(int i,float flow,float upstream,float downstream,bool wet) {
      ChannelFlows[i]=flow>0?flow:0;
      ChannelHeads[i]=upstream>downstream?upstream-downstream:0;
      ActualFlow+=ChannelFlows[i];AvailableHead+=ChannelFlows[i]*ChannelHeads[i];
      UpstreamHeight+=upstream/Gates.Length;DownstreamHeight+=downstream/Gates.Length;
      if(!wet)return 0;
      return Mathf.Min(ChannelFlows[i],Spec.MaxDischarge/Gates.Length)*
        Mathf.Min(ChannelHeads[i],Spec.MaxGeneratingHead)*Spec.HpPerFlowAndHead;
    }
    internal void EndMeasurement(float hp,bool intakeWet) {
      // Flow-weighted operating head; a stopped runner reports static head.
      AvailableHead=ActualFlow>0?AvailableHead/ActualFlow:Mathf.Max(UpstreamHeight-DownstreamHeight,0);
      if(_gateClosed) {ActualFlow=0;SetOutput(0);State=_pausable.Paused?"Paused":"Closed";}
      else if(!intakeWet) {SetOutput(0);State="Dry intake";}
      else if(AvailableHead<=0) {SetOutput(0);State="No forward water head";}
      else if(ActualFlow<=0) {SetOutput(0);State="No forward discharge";}
      else {SetOutput(hp);State="Generating";}
    }
    private void SetOutput(float hp) {
      OutputHp=hp;
      _node.SetOutputMultiplier(hp/GetComponent<MechanicalNodeSpec>().PowerOutput);
      RefreshAnimation();
    }
    [OnEvent] public void OnSpeedChanged(CurrentSpeedChangedEvent args)=>RefreshAnimation();
    private void RefreshAnimation() {
      if(!_finished)return;
      _animator.Enabled=OutputHp>0;
      _animator.Speed=Spec.AnimationSpeedMultiplier*_animation.SpeedMultiplier*
        Mathf.Min(ActualFlow/Spec.MaxDischarge,1);
    }
  }

  internal sealed class HydroTurbinePlacementValidator : IBlockObjectValidator {
    private readonly IBlockService _blocks;
    public HydroTurbinePlacementValidator(IBlockService blocks) {_blocks=blocks;}
    public bool IsValid(BlockObject block,out string errorMessage) {
      errorMessage=null;
      var spec=block.GetComponent<HydroTurbineSpec>();
      if(spec==null)return true;
      // Native validation runs this two or three times per preview frame.
      foreach(var local in spec.Intakes)if(!Inside(block.TransformCoordinates(local)))return Outside(out errorMessage);
      foreach(var local in spec.Outlets)if(!Inside(block.TransformCoordinates(local+Vector3Int.up)))return Outside(out errorMessage);
      return true;
    }
    private bool Inside(Vector3Int p)=>p.x>=0&&p.y>=0&&p.z>=0&&p.x<_blocks.Size.x&&p.y<_blocks.Size.y&&p.z<_blocks.Size.z;
    private static bool Outside(out string errorMessage) {
      errorMessage="The turbine needs an intake and outlet inside the map.";
      return false;
    }
  }

  // INonThreadSafeWaterService permits these reads only in singleton Tick.
  // One shared snapshot covers every turbine; no per-building full-map copies.
  internal sealed class HydroTurbineSimulation : ITickableSingleton,ILoadableSingleton {
    private readonly HashSet<HydroTurbine> _turbines=new();
    private readonly INonThreadSafeWaterService _flows;
    private readonly IThreadSafeWaterMap _map;
    private readonly MapIndexService _indices;
    private readonly ISpecService _specs;
    private float _pressureFactor;
    public HydroTurbineSimulation(INonThreadSafeWaterService flows,IThreadSafeWaterMap map,
      MapIndexService indices,ISpecService specs) {_flows=flows;_map=map;_indices=indices;_specs=specs;}
    public void Load() {
      _pressureFactor=_specs.GetSingleSpec<WaterSimulatorSpec>().OverflowPressureFactor;
      if(!float.IsFinite(_pressureFactor)||_pressureFactor<=0)
        throw new InvalidOperationException("Native water pressure factor must be positive and finite");
    }
    public void Register(HydroTurbine turbine) {
      if(!_turbines.Add(turbine))throw new InvalidOperationException("Duplicate turbine simulation registration");
    }
    public void Unregister(HydroTurbine turbine) {
      if(!_turbines.Remove(turbine))throw new InvalidOperationException("Missing turbine simulation registration");
    }
    public void Tick() {
      if(_turbines.Count==0)return;
      _flows.UpdateOutflowsData();
      foreach(var turbine in _turbines) {
        // SetInflowLimit caps the edge arriving INTO the aperture. Its
        // pressurized chamber can discharge stored water in later pulses;
        // that outgoing edge is not the controlled gate crossing.
        turbine.BeginMeasurement();float hp=0;bool wet=false;
        for(int i=0;i<turbine.Gates.Length;i++) {
          float flow=ThroughFlow(turbine.Gates[i]-turbine.Forward,turbine.Forward);
          var intake=turbine.Intakes[i];var outlet=turbine.Outlets[i];
          // Intake is in the reservoir; tail pressure is in the last conduit
          // cell. A full obstacle beyond the mouth has no water column and
          // cannot represent the back-pressure retained behind that obstacle.
          float upstream=_map.WaterHeightOrFloor(intake)+_map.ColumnOverflow(intake)*_pressureFactor;
          float downstream=_map.WaterHeightOrFloor(outlet)+_map.ColumnOverflow(outlet)*_pressureFactor;
          bool laneWet=_map.WaterDepth(intake)>0;wet|=laneWet;
          hp+=turbine.MeasureChannel(i,flow,upstream,downstream,laneWet);
        }
        turbine.EndMeasurement(hp,wet);
      }
    }
    private float ThroughFlow(Vector3Int cell,Vector3Int forward) {
      int index2D=_indices.CellToIndex(new Vector2Int(cell.x,cell.y));
      int neighbor=_indices.CellToIndex(new Vector2Int(cell.x+forward.x,cell.y+forward.y));
      for(int ordinal=0;ordinal<_map.ColumnCount(index2D);ordinal++) {
        int index3D=ordinal*_indices.VerticalStride+index2D;
        var column=_map.WaterColumns[index3D];
        if(column.Floor>cell.z||column.Ceiling<=cell.z)continue;
        var flows=_flows.ColumnOutflows(index3D);
        var primary=forward.x==1?flows.RightFlow:forward.x==-1?flows.LeftFlow:
          forward.y==1?flows.TopFlow:flows.BottomFlow;
        float result=primary.Index3D>=0&&primary.Index3D%_indices.VerticalStride==neighbor?primary.Flow:0;
        if(flows.Outflows!=null)foreach(var flow in flows.Outflows)
          if(flow.Index3D>=0&&flow.Index3D%_indices.VerticalStride==neighbor)result+=flow.Flow;
        return result;
      }
      return 0; // A closed full obstacle has no water column at the aperture.
    }
  }

  [Context("Game")]
  public sealed class HydroTurbineConfigurator : Configurator {
    protected override void Configure() {
      Bind<HydroTurbine>().AsTransient();Bind<HydroTurbineSimulation>().AsSingleton();
      Bind<HydroTurbinePlacementValidator>().AsSingleton();
      MultiBind<IBlockObjectValidator>().ToExisting<HydroTurbinePlacementValidator>();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }
    private static TemplateModule Provide() {
      var b=new TemplateModule.Builder();b.AddDecorator<HydroTurbineSpec,HydroTurbine>();return b.Build();
    }
  }
}
