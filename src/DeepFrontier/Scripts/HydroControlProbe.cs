using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.MapIndexSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterBuildings;
using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class HydroControlProbeConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierHydroProbe"))
        Bind<HydroControlProbe>().AsSingleton();
    }
  }
  // Explicit disposable API experiment. It does not add a turbine or generator.
  internal sealed class HydroControlProbe : IPostLoadableSingleton,IUpdatableSingleton,ITickableSingleton {
    private readonly EntityRegistry _entities;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly IWaterService _water;
    private readonly IThreadSafeWaterMap _map;
    private readonly INonThreadSafeWaterService _flows;
    private readonly MapIndexService _indices;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly CameraService _camera;
    private readonly List<object> _samples=new();
    private static readonly Vector3Int ValveCell=new(145,165,4);
    private static readonly Vector3Int Intake=new(145,166,4);
    private static readonly Vector3Int Outlet=new(145,164,4);
    private ThrottlingValve _valve;
    private int _frame,_phase;
    private float _phaseStart,_lastSample;
    private readonly float[] _maximumDischarge=new float[4];
    private bool _finished,_ready;
    public HydroControlProbe(EntityRegistry entities,TemplateService templates,BlockObjectFactory factory,
      BlockValidator validator,IWaterService water,IThreadSafeWaterMap map,
      INonThreadSafeWaterService flows,MapIndexService indices,SpeedManager speed,
      IDayNightCycle clock,CameraService camera) {
      _entities=entities;_templates=templates;_factory=factory;_validator=validator;
      _water=water;_map=map;_flows=flows;_indices=indices;_speed=speed;_clock=clock;_camera=camera;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&
        e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),"Fixture marker missing");
      _speed.ChangeSpeed(0);
    }
    private BlockObject Create(string id,Vector3Int position,Orientation orientation) {
      var t=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==t.Blueprint);
      var p=new Placement(position,orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,p),"Native hydro probe placement rejected "+id+" "+position);
      return _factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),p);
    }
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      // Seven-by-seven sealed reservoir; 5×5 interior, eight-layer walls.
      for(int x=142;x<=148;x++)for(int y=165;y<=171;y++) {
        Create("ConcreteBlock.IronTeeth",new Vector3Int(x,y,3),Orientation.Cw0);
        bool edge=x==142||x==148||y==165||y==171;
        if(edge)for(int z=4;z<12;z++) {
          var p=new Vector3Int(x,y,z);
          // Cw180 admits flow toward -Y. Cw0 points into this reservoir.
          if(p==ValveCell)_valve=Create("ThrottlingValve.IronTeeth",p,Orientation.Cw180).GetComponent<ThrottlingValve>();
          else Create("ReinforcedDamBlock.IronTeeth",p,Orientation.Cw0);
        }
        else _water.AddCleanWater(new Vector3Int(x,y,4),6);
      }
      _valve.ToggleSynchronization(false);
      Require(_valve.GetComponent<BlockObject>().Orientation.ToFlowDirection()==FlowDirection.Bottom,
        "Probe valve must discharge toward its outside -Y cell");
      _valve.SetOutflowLimitEnabled(true);_valve.SetOutflowLimit(0);
      _camera.MoveTargetTo(new Vector3(145,6,167));_camera.SetZoomLevel(21,0);
      _camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _phaseStart=_clock.PartialDayNumber;_lastSample=_phaseStart;_speed.ChangeSpeed(3);
      _ready=true;
      Debug.Log("[DeepFrontier Hydro Probe] Native valve, concrete reservoir and 150 units of test water created");
    }
    private object Sample() {
      // Singleton-Tick-only diagnostic snapshot. Native TickOnlyArray rejects
      // UpdateSingleton access; never take a full-world copy per building.
      _flows.UpdateOutflowsData();
      int index2D=_indices.CellToIndex(new Vector2Int(ValveCell.x,ValveCell.y));
      var columns=new List<object>();
      float discharge=0;
      for(int i=0;i<_map.ColumnCount(index2D);i++) {
        int index3D=i*_indices.VerticalStride+index2D;
        var column=_map.WaterColumns[index3D];
        if(column.Floor>ValveCell.z||column.Ceiling<=ValveCell.z)continue;
        var flows=_flows.ColumnOutflows(index3D);
        int outletIndex=_indices.CellToIndex(new Vector2Int(Outlet.x,Outlet.y));
        if(flows.BottomFlow.Index3D>=0&&flows.BottomFlow.Index3D%_indices.VerticalStride==outletIndex)
          discharge+=flows.BottomFlow.Flow;
        if(flows.Outflows!=null)foreach(var flow in flows.Outflows)
          if(flow.Index3D>=0&&flow.Index3D%_indices.VerticalStride==outletIndex)discharge+=flow.Flow;
        columns.Add(new {
          floor=column.Floor,ceiling=column.Ceiling,
          bottom=flows.BottomFlow,top=flows.TopFlow,left=flows.LeftFlow,right=flows.RightFlow,
          additional=flows.Outflows,
        });
      }
      float reservoir=0;
      for(int x=143;x<=147;x++)for(int y=166;y<=170;y++)
        reservoir+=_map.WaterDepth(new Vector3Int(x,y,4))+_map.ColumnOverflow(new Vector3Int(x,y,4));
      var vector=_map.WaterFlowDirection(ValveCell);
      if((_clock.PartialDayNumber-_phaseStart)*24>.15f)
        _maximumDischarge[_phase]=Mathf.Max(_maximumDischarge[_phase],discharge);
      return new {phase=_phase,hours=_clock.PartialDayNumber*24,
        requested=_valve.OutflowLimit,currentLimit=_valve.CurrentOutflowLimit,
        intakeSurface=_map.WaterHeightOrFloor(Intake),outletSurface=_map.WaterHeightOrFloor(Outlet),
        intakeOverflow=_map.ColumnOverflow(Intake),outletOverflow=_map.ColumnOverflow(Outlet),
        reservoirVolume=reservoir,discharge,flowX=vector.x,flowY=vector.y,columns};
    }
    private void Finish() {
      _speed.ChangeSpeed(0);_finished=true;
      var path=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),
        "TimberbornModding","outputs","hydro-control-probe.json");
      File.WriteAllText(path,JsonConvert.SerializeObject(new {
        scope="Native valve API measurement only; no turbine generation or balance acceptance",
        maximumSettledDischarge=_maximumDischarge,samples=_samples},Formatting.Indented));
      Debug.Log("[DeepFrontier Hydro Probe] MEASUREMENTS SAVED: "+path);
      Require(_maximumDischarge[1]>.02f,"Open quarter-rate phase passed no measurable water");
      Require(_maximumDischarge[2]>_maximumDischarge[1]*2,
        "Larger requested discharge did not produce a larger measured through-flow");
      Require(_maximumDischarge[3]<.005f,"Closed final phase still passed water");
      Debug.Log("[DeepFrontier Hydro Probe] CLOSED AND OPEN DISCHARGE CHECKS PASSED");
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
      } catch(Exception error) {Fail(error);}
    }
    public void Tick() {
      if(_finished||!_ready)return;
      try {
        var now=_clock.PartialDayNumber;
        if((now-_lastSample)*24>.05f) {
          _lastSample=now;_samples.Add(Sample());
        }
        if((now-_phaseStart)*24<.5f)return;
        if(_phase==0) {
          Require(_map.WaterDepth(Intake)>5.9f,"Closed reservoir lost test water");
          _valve.SetOutflowLimit(.25f);
        } else if(_phase==1)_valve.SetOutflowLimit(1);
        else if(_phase==2)_valve.SetOutflowLimit(0);
        else {Finish();return;}
        _phase++;_phaseStart=now;
        Debug.Log("[DeepFrontier Hydro Probe] Phase "+_phase+" requested "+_valve.OutflowLimit+" m3/s");
      } catch(Exception error) {Fail(error);}
    }
    private void Fail(Exception error) {
      _finished=true;_speed.ChangeSpeed(0);
      Debug.LogError("[DeepFrontier Hydro Probe] FAILED: "+error);
    }
  }
}
