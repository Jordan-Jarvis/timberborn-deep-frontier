using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.MapIndexSystem;
using Timberborn.MechanicalSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TerrainSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class HydroBasinAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierHydroBasins"))
        Bind<HydroBasinAcceptance>().AsSingleton();
    }
  }

  // Disposable, explicitly selected settlement only. No changes to ordinary gameplay.
  internal sealed class HydroBasinAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities;
    private readonly EntityService _entityService;
    private readonly TemplateService _templates;
    private readonly BlockObjectFactory _factory;
    private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _validation;
    private readonly ITerrainService _terrain;
    private readonly IWaterService _water;
    private readonly IThreadSafeWaterMap _map;
    private readonly IThreadSafeWaterEvaporationMap _evaporation;
    private readonly MapIndexService _indices;
    private readonly ISpecService _specs;
    private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock;
    private readonly CameraService _camera;
    private readonly GameSaver _saver;
    private readonly GameLoader _loader;
    private readonly List<BlockObject> _created=new();
    private readonly List<HydroTurbine> _turbines=new();
    private readonly List<object> _samples=new();
    private readonly List<object> _windows=new();
    private readonly List<string> _checks=new();
    private WaterSimulatorSpec _waterSpec;
    private const int MinX=210,MaxX=238,MinY=140,MaxY=166,Divider=148;
    private static readonly int[] Anchors={213,224};
    private static readonly string Folder=Path.Combine(
      Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs");
    private sealed class Basin {
      public double Total,Upper,Lower,Contaminated,LowerContaminated,Evaporation,UpperEvaporation;
      public int WetColumns;
    }
    private Basin _previous,_baseline;
    private double _lastTime,_phaseTime,_evaporated,_upperEvaporated,_through;
    private float _previousFlow;
    private readonly float[] _peakFlows=new float[2],_peakHp=new float[2];
    private int _frame,_phase;
    private bool _started,_finished,_measuring;
    private double Now=>(_clock.PartialDayNumber*_clock.DayLengthInSeconds);
    public HydroBasinAcceptance(EntityRegistry entities,EntityService entityService,TemplateService templates,
      BlockObjectFactory factory,BlockValidator validator,BlockObjectValidationService validation,
      ITerrainService terrain,IWaterService water,IThreadSafeWaterMap map,
      IThreadSafeWaterEvaporationMap evaporation,MapIndexService indices,ISpecService specs,
      SpeedManager speed,IDayNightCycle clock,CameraService camera,GameSaver saver,GameLoader loader) {
      _entities=entities;_entityService=entityService;_templates=templates;_factory=factory;
      _validator=validator;_validation=validation;_terrain=terrain;_water=water;_map=map;
      _evaporation=evaporation;_indices=indices;_specs=specs;_speed=speed;_clock=clock;
      _camera=camera;_saver=saver;_loader=loader;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private void Pass(string message) {_checks.Add(message);Debug.Log("[DeepFrontier Hydro Basins] PASS "+message);}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&
        e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),"Disposable fixture marker missing");
      _speed.ChangeSpeed(0);
      _waterSpec=_specs.GetSingleSpec<WaterSimulatorSpec>();
    }
    private BlockObject Create(string id,int x,int y,int z) {
      var template=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==template.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),Orientation.Cw0,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Invalid basin placement: "+id+" "+placement.Coordinates);
      var block=_factory.CreateFinished(new EntitySetup.Builder(spec.Blueprint)
        .AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_validation.IsValid(block),"Additional native placement restriction: "+id);
      _created.Add(block);return block;
    }
    private void Setup() {
      foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))
        e.GetComponent<PausableBuilding>().Pause();
      var occupants=_entities.Entities.Where(e=>e.HasComponent<BlockObject>()).Where(e=> {
        var p=e.GetComponent<BlockObject>().Coordinates;
        return p.x>=MinX&&p.x<=MaxX&&p.y>=MinY&&p.y<=MaxY;
      }).ToArray();
      var removable=new[]{"Pine","Birch","Oak","Blockage"};
      Require(occupants.All(e=>removable.Contains(e.GetComponent<TemplateSpec>().TemplateName)),
        "Basin pad contains a building or unexpected object; inspect before changing it");
      foreach(var e in occupants)_entityService.Delete(e);
      for(int x=MinX;x<=MaxX;x++)for(int y=MinY;y<=MaxY;y++) {
        var surfaces=_terrain.GetAllHeightsInCell(new Vector2Int(x,y)).Where(p=>p.z>3)
          .OrderByDescending(p=>p.z).ToArray();
        foreach(var top in surfaces)_terrain.UnsetTerrain(new Vector3Int(x,y,top.z-1),top.z-3);
        int height=_terrain.GetTerrainHeight(new Vector3Int(x,y,0));
        if(height<3)_terrain.SetTerrain(new Vector3Int(x,y,height),3-height);
        Require(_terrain.GetTerrainHeight(new Vector3Int(x,y,0))==3&&
          !Enumerable.Range(3,_terrain.Size.z-3).Any(z=>_terrain.Underground(new Vector3Int(x,y,z))),
          "Native basin floor preparation failed");
        if(x==MinX||x==MaxX||y==MinY||y==MaxY)_terrain.SetTerrain(new Vector3Int(x,y,3),20);
      }
      foreach(int x in Anchors) {
        var building=Create("ReinforcedHydroTurbine.IronTeeth",x,146,3);
        var turbine=building.GetComponent<HydroTurbine>();
        turbine.SetClosed(true);_turbines.Add(turbine);
        Create("PowerShaft.IronTeeth",x+8,153,3);
      }
      for(int x=MinX+1;x<MaxX;x++) {
        int bottom=Anchors.Any(a=>x>=a&&x<a+4)?9:3;
        for(int z=bottom;z<23;z++)Create("ReinforcedDamBlock.IronTeeth",x,Divider,z);
      }
      _turbines[0].SetDischargeLimit(.75f);_turbines[1].SetDischargeLimit(1.5f);
      _camera.MoveTargetTo(new Vector3(224,9,151));_camera.SetZoomLevel(36,0);
      _camera.HorizontalAngle=145;_camera.VerticalAngle=43;
      _started=true;Phase(0);_speed.ChangeSpeed(3);
      Pass("two native turbines with independent 0.75 and 1.5 m3/s limits in sealed finite basins");
    }
    private IEnumerable<(Vector3Int Cell,int Index)> Columns() {
      for(int x=MinX;x<=MaxX;x++)for(int y=MinY;y<=MaxY;y++) {
        int index=_indices.CellToIndex(new Vector2Int(x,y));
        for(int ordinal=0;ordinal<_map.ColumnCount(index);ordinal++) {
          int index3D=index+ordinal*_indices.VerticalStride;
          yield return (new Vector3Int(x,y,_map.WaterColumns[index3D].Floor),index3D);
        }
      }
    }
    private Basin ReadBasin() {
      var result=new Basin();
      foreach(var entry in Columns()) {
        var c=_map.WaterColumns[entry.Index];double volume=c.WaterDepth+c.Overflow;
        double evaporation=volume>0?((c.WaterDepth<_waterSpec.FastEvaporationDepthThreshold?
          _waterSpec.FastEvaporationSpeed:_waterSpec.NormalEvaporationSpeed)*_evaporation.EvaporationModifiers[entry.Index]):0;
        result.Total+=volume;result.Contaminated+=volume*c.Contamination;result.Evaporation+=evaporation;
        if(volume>0)result.WetColumns++;
        if(entry.Cell.y<=Divider) {result.Upper+=volume;result.UpperEvaporation+=evaporation;}
        else {result.Lower+=volume;result.LowerContaminated+=volume*c.Contamination;}
      }
      return result;
    }
    private void Drain() {
      foreach(var entry in Columns()) {
        var c=_map.WaterColumns[entry.Index];float volume=c.WaterDepth+c.Overflow;
        if(volume<=0)continue;
        _water.RemoveCleanWater(entry.Cell,volume*(1-c.Contamination));
        _water.RemoveContaminatedWater(entry.Cell,volume*c.Contamination);
      }
    }
    private void Fill(float upperHeight,float lowerHeight,float contamination) {
      foreach(var entry in Columns()) {
        var c=_map.WaterColumns[entry.Index];
        float surface=entry.Cell.y<=Divider?upperHeight:lowerHeight;
        float depth=Mathf.Min(surface,c.Ceiling)-c.Floor;
        if(depth<=0)continue;
        if(contamination<1)_water.AddCleanWater(entry.Cell,depth*(1-contamination));
        if(contamination>0)_water.AddContaminatedWater(entry.Cell,depth*contamination);
      }
    }
    private void Close(bool closed) {foreach(var turbine in _turbines)turbine.SetClosed(closed);}
    private void Phase(int phase) {
      _phase=phase;_phaseTime=Now;_lastTime=Now;_previous=ReadBasin();
      _measuring=false;Array.Clear(_peakFlows,0,2);Array.Clear(_peakHp,0,2);
      Debug.Log("[DeepFrontier Hydro Basins] Phase "+phase);
    }
    private void StartWindow(int phase) {
      Phase(phase);_measuring=true;_baseline=_previous;_evaporated=0;_upperEvaporated=0;_through=0;
      _previousFlow=_turbines.Sum(t=>t.ActualFlow);
    }
    private void EndWindow(Basin basin,float contamination) {
      double volumeError=basin.Total+_evaporated-_baseline.Total;
      double transferError=_baseline.Upper-basin.Upper-_upperEvaporated-_through;
      double contaminationError=basin.Contaminated+_evaporated*contamination-_baseline.Contaminated;
      _windows.Add(new {phase=_phase,start=_baseline,end=basin,evaporated=_evaporated,
        upperEvaporated=_upperEvaporated,integratedGateVolume=_through,volumeError,transferError,contaminationError,
        peakFlows=_peakFlows.ToArray(),peakHp=_peakHp.ToArray()});
      Require(Math.Abs(volumeError)<.5,"Water conservation differs from native evaporation by "+volumeError);
      // Samples span completed native ticks; gate integration may straddle one physics tick.
      Require(Math.Abs(transferError)<2,"Combined measured gate flow differs from upper-basin drawdown by "+transferError);
      Require(Math.Abs(contaminationError)<1,"Contamination inventory drift exceeds evaporation allowance: "+contaminationError);
      Require(_peakFlows[0]>.7f&&_peakFlows[1]>1.4f&&_peakHp.All(hp=>hp>100),
        "Both independently limited turbines must actually generate");
      Require(basin.Lower-_baseline.Lower>30,"No substantial downstream water delivered");
      if(contamination>0)Require(Math.Abs(basin.LowerContaminated/basin.Lower-contamination)<.015,
        "Turbines changed downstream contamination concentration");
      Pass((contamination>0?"contaminated":"clean")+" shared-reservoir volume and gate accounting; volume error "+
        volumeError+", transfer error "+transferError+", contamination error "+contaminationError);
      _measuring=false;
    }
    private void Write() {
      File.WriteAllText(Path.Combine(Folder,"hydro-basins-measurements.json"),JsonConvert.SerializeObject(new {
        scope="Two turbines, sealed finite water, native evaporation, contaminated transfer, reverse head and drought. Pump energy separate.",
        checks=_checks,windows=_windows,samples=_samples},Formatting.Indented));
    }
    private void Finish() {
      Close(true);_finished=true;_speed.ChangeSpeed(0);Write();
      File.WriteAllText(Path.Combine(Folder,"hydro-basins-entities.json"),JsonConvert.SerializeObject(
        _created.Select(b=>new StructuralEntityRecord {Id=b.GetComponent<EntityComponent>().EntityId.ToString(),
          Template=b.GetComponent<TemplateSpec>().TemplateName,Coordinates=b.Coordinates}),Formatting.Indented));
      _saver.QueueSave(new SaveReference("Hydro basins - verified",_loader.LoadedSave.SettlementReference),
        ()=>Debug.Log("[DeepFrontier Hydro Basins] ALL CHECKS PASSED AND SAVED"));
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(!_started||Now==_lastTime)return;
        double now=Now,dt=now-_lastTime;var basin=ReadBasin();
        if(_measuring) {
          _evaporated+=(_previous.Evaporation+basin.Evaporation)*.5*dt;
          _upperEvaporated+=(_previous.UpperEvaporation+basin.UpperEvaporation)*.5*dt;
          float flow=_turbines.Sum(t=>t.ActualFlow);_through+=(_previousFlow+flow)*.5*dt;_previousFlow=flow;
        }
        _lastTime=now;_previous=basin;
        for(int i=0;i<2;i++) {
          var turbine=_turbines[i];
          _peakFlows[i]=Mathf.Max(_peakFlows[i],turbine.ActualFlow);_peakHp[i]=Mathf.Max(_peakHp[i],turbine.OutputHp);
          Require(turbine.ActualFlow<=turbine.DischargeLimit+.001f,"A turbine exceeded its independent total flow limit");
        }
        _samples.Add(new {phase=_phase,seconds=now,basin,turbines=_turbines.Select(t=>new {
          limit=t.DischargeLimit,flow=t.ActualFlow,head=t.AvailableHead,upstream=t.UpstreamHeight,
          downstream=t.DownstreamHeight,hp=t.OutputHp,nativeHp=t.GetComponent<MechanicalNode>().Actuals.PowerOutput,
          state=t.State,closed=t.GateIsClosed,channels=t.ChannelFlows.ToArray(),
          intakeContamination=t.Intakes.Select(p=>_map.ColumnContamination(p)).ToArray(),
          outletContamination=t.Outlets.Select(p=>_map.ColumnContamination(p)).ToArray()}).ToArray()});
        double hours=(now-_phaseTime)*24/_clock.DayLengthInSeconds;
        if(_phase==0&&hours>.2) {Require(basin.Total<.01,"Prepared basin unexpectedly wet");Fill(20,3,0);Phase(1);}
        else if(_phase==1&&hours>.5) {Require(basin.Upper>1000&&basin.Lower<.1,"Closed gates leaked initial fill");Close(false);StartWindow(2);}
        else if(_phase==2&&hours>2) {EndWindow(basin,0);Close(true);Drain();Phase(3);}
        else if(_phase==3&&hours>.2) {
          if(basin.Total>.001) {Drain();Require(hours<2,"Drain did not empty test basins");}
          else {Fill(20,3,.5f);Phase(4);}
        }
        else if(_phase==4&&hours>.5) {Close(false);StartWindow(5);}
        else if(_phase==5&&hours>2) {EndWindow(basin,.5f);Close(true);Drain();Phase(6);}
        else if(_phase==6&&hours>.2) {
          if(basin.Total>.001) {Drain();Require(hours<2,"Reverse-head preparation did not drain");}
          else {Fill(9,13,0);Phase(7);}
        }
        else if(_phase==7&&hours>.7) {Close(false);Phase(8);}
        else if(_phase==8&&hours>1) {
          Require(_turbines.All(t=>t.DownstreamHeight>t.UpstreamHeight+1&&t.OutputHp==0&&
            t.GetComponent<MechanicalNode>().Actuals.PowerOutput==0),"Reverse head produced power or did not establish reverse pressure");
          Require(_peakHp.All(hp=>hp==0),"Reverse-head transient generated fictional power");
          Pass("higher downstream water gives zero measured generation on both native nodes");
          Close(true);Drain();Phase(9);
        }
        else if(_phase==9&&hours>.2) {
          if(basin.Total>.001) {Drain();Require(hours<2,"Drought preparation did not drain");}
          else {Close(false);Phase(10);}
        }
        else if(_phase==10&&hours>.5) {
          Require(basin.Total<.001&&_peakHp.All(hp=>hp==0)&&
            _turbines.All(t=>t.State=="Dry intake"&&t.GetComponent<MechanicalNode>().Actuals.PowerOutput==0),
            "Dry turbines generated power or misreported drought");
          Pass("both empty intakes remain dry with zero native shaft output");
          Close(true);Fill(20,3,0);Phase(11);
        }
        else if(_phase==11&&hours>.5)Finish();
        if(hours>4)throw new InvalidOperationException("Basin phase timed out: "+_phase);
      } catch(Exception error) {
        _finished=true;_speed.ChangeSpeed(0);Write();Debug.LogError("[DeepFrontier Hydro Basins] FAILED: "+error);
      }
    }
  }
}
