using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
using Timberborn.Attractions;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CharacterControlSystem;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.Navigation;
using Timberborn.NeedSystem;
using Timberborn.SingletonSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class HospitalContinuityAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierHospitalReload"))
        Bind<HospitalContinuityAcceptance>().AsSingleton();
    }
  }
  // Only the explicitly launched, marked disposable fixture reads this record.
  // Its expected values are extracted from the prior native save, not invented.
  [Serializable] internal sealed class HospitalReloadRecord {
    public string EntityId;
    public int Medicine,Water,Extract;
    public float SupplyHours;
    public HospitalPatientRecord[] Patients;
  }
  [Serializable] internal sealed class HospitalPatientRecord {
    public string EntityId;
    public HospitalNeedRecord[] Needs;
  }
  [Serializable] internal sealed class HospitalNeedRecord {
    public string Name;
    public float Points;
  }
  internal sealed class HospitalContinuityAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities; private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock; private readonly WorkingHoursManager _hours;
    private readonly INavigationService _navigation; private readonly GameSaver _saver; private readonly GameLoader _loader;
    private Hospital _hospital; private BlockObject _building; private Workplace _workplace;
    private GoodConsumingBuilding _supplies; private ControllableCharacter _observer; private NeedManager _needs;
    private Worker[] _staff;
    private int _frame,_phase; private float _start,_phaseTime,_baseline,_normalHours,_stableSince,_arrivalTime;
    private bool _finished; private Vector3 _target;
    private readonly string[] _conditions={"Injury","ChippedTeeth","BadwaterContamination"};
    public HospitalContinuityAcceptance(EntityRegistry entities,SpeedManager speed,IDayNightCycle clock,
      WorkingHoursManager hours,INavigationService navigation,GameSaver saver,GameLoader loader) {
      _entities=entities;_speed=speed;_clock=clock;_hours=hours;_navigation=navigation;_saver=saver;_loader=loader;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message) {Debug.Log("[DeepFrontier Hospital Reload] PASS "+message);}
    private void Phase(int phase) {_phase=phase;_phaseTime=_clock.PartialDayNumber;}
    private static void SetNeed(NeedManager n,string id,float points) {
      n.ApplyEffect(new InstantEffect(id,points-n.GetNeedPoints(id),1));
    }
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Hospital continuity requires the marked disposable settlement");
    }
    private void Setup() {
      _speed.ChangeSpeed(0);
      var expected=JsonConvert.DeserializeObject<HospitalReloadRecord>(File.ReadAllText(
        "C:/Users/Jordan/Documents/TimberbornModding/outputs/hospital-reload-expectations.json"));
      Require(expected!=null&&expected.Patients!=null&&expected.Patients.Length>=3,"Missing exact native save expectations");
      _hospital=_entities.Entities.Single(e=>e.HasComponent<Hospital>()).GetComponent<Hospital>();
      _building=_hospital.GetComponent<BlockObject>();_workplace=_hospital.GetComponent<Workplace>();
      _supplies=_hospital.GetComponent<GoodConsumingBuilding>();
      Require(_hospital.GetComponent<EntityComponent>().EntityId.ToString()==expected.EntityId,"Saved hospital identity changed");
      Require(_building.GetComponent<PausableBuilding>().Paused,"Expected paused native hospital save");
      Require(_supplies.Inventory.AmountInStock("Medicine")==expected.Medicine
        &&_supplies.Inventory.AmountInStock("Water")==expected.Water
        &&_supplies.Inventory.AmountInStock("Extract")==expected.Extract,"Native hospital stocks changed after reload");
      Require(Math.Abs(_supplies.HoursUntilNoSupply()-expected.SupplyHours)<.0001f,"Fractional native supply duration changed after reload");
      foreach(var p in expected.Patients) {
        var n=_entities.Entities.Single(e=>e.EntityId.ToString()==p.EntityId).GetComponent<NeedManager>();
        Require(p.Needs!=null&&p.Needs.Length>0,"Patient record must contain saved needs");
        foreach(var need in p.Needs)Require(Math.Abs(n.GetNeedPoints(need.Name)-need.Points)<.0001f,"Saved patient need changed: "+need.Name);
      }
      Pass("fresh-process identity, pause, medicine/water/extract, fractional supplies and saved patient needs");
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").ToArray();
      Require(workers.Length>=7,"Continuity needs six staff and one neighborhood observer");
      foreach(var w in workers)w.Unemploy();
      _staff=workers.Take(6).ToArray();_observer=workers[6].GetComponent<ControllableCharacter>();_needs=_observer.GetComponent<NeedManager>();
      Require(_observer.GetAnimationNames().Contains("BeaverAdult_idle"),"Native adult idle animation is missing");
      _observer.ChangeAnimation("BeaverAdult_idle");
      foreach(var w in workers.Take(7)) {
        var n=w.GetComponent<NeedManager>();
        foreach(var id in _conditions)SetNeed(n,id,0);
        foreach(var id in new[]{"Hunger","Thirst","Sleep"})SetNeed(n,id,n.GetNeedSpec(id).MaximumValue);
      }
      _building.GetComponent<PausableBuilding>().Resume();
      foreach(var w in _staff)w.EmployAt(_workplace);
      MoveObserver(new Vector3Int(173,159,3));
      _start=_clock.PartialDayNumber;Phase(1);_speed.ChangeSpeed(3);
    }
    private void MoveObserver(Vector3Int coordinates) {
      _target=NavigationCoordinateSystem.GridToWorld(coordinates);
      Require(_navigation.FindPathUnlimitedRange(_observer.Transform.position,_target,new List<PathCorner>(),out var distance),"No observer route to "+coordinates);
      _observer.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_target));
      Debug.Log("[DeepFrontier Hospital Reload] WALK "+coordinates+" distance="+distance);
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();
        if(_frame<=60)return;
        float hours=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_frame%600==0)Debug.Log($"[DeepFrontier Hospital Reload] STATUS phase={_phase}, staff={_hospital.AttendingStaff}, supplies={_supplies.HoursUntilNoSupply()}, area={_hospital.ProvidesNeighborhoodCare}");
        if(_phase==1&&_hospital.ProvidesNeighborhoodCare&&Vector3.Distance(_observer.Transform.position,_target)<.18f) {
          SetNeed(_needs,"PublicHealthcare",0);_baseline=0;Phase(2);
        } else if(_phase==2&&hours>=.6f) {
          float gained=_needs.GetNeedPoints("PublicHealthcare")-_baseline;
          Require(gained>.06f,"Nearby beaver did not receive actual PublicHealthcare points");
          Pass("actual neighborhood need gained "+gained+" while inside range");
          MoveObserver(new Vector3Int(173,149,3));Phase(3);
        } else if(_phase==3&&Vector3.Distance(_observer.Transform.position,_target)<.18f) {
          _baseline=_needs.GetNeedPoints("PublicHealthcare");Phase(4);
        } else if(_phase==4&&hours>=.6f) {
          Require(_needs.GetNeedPoints("PublicHealthcare")<_baseline-.005f,"Outside observer still receives neighborhood benefit");
          Pass("actual neighborhood need decays outside radius");
          MoveObserver(new Vector3Int(173,159,3));
          int stock=_supplies.Inventory.AmountInStock("Medicine");
          Require(stock==_supplies.Inventory.UnreservedAmountInStock("Medicine"),"Medicine depletion fixture encountered reserved stock");
          _supplies.Inventory.TakeConsumed(new GoodAmount("Medicine",stock));Phase(5);
        } else if(_phase==5&&hours>=1f) {
          Require(!_supplies.CanUse&&!_supplies.IsConsuming&&!_hospital.ProvidesNeighborhoodCare
            &&!_building.GetComponent<Attraction>().IsUsable,"Missing medicine did not stop native treatment and area care");
          if(Vector3.Distance(_observer.Transform.position,_target)>=.18f)return;
          _baseline=_needs.GetNeedPoints("PublicHealthcare");Phase(6);
        } else if(_phase==6&&hours>=.6f) {
          Require(_needs.GetNeedPoints("PublicHealthcare")<=_baseline,"Unstocked hospital grants neighborhood points");
          Pass("exhausted real medicine and its fractional buffer stop treatment, consumption and neighborhood benefit");
          _supplies.Inventory.GiveExisting(new GoodAmount("Medicine",8));Phase(7);
        } else if(_phase==7&&_hospital.ProvidesNeighborhoodCare&&_building.GetComponent<Attraction>().IsUsable) {
          _baseline=_needs.GetNeedPoints("PublicHealthcare");Phase(8);
        } else if(_phase==8&&hours>=.6f) {
          Require(_needs.GetNeedPoints("PublicHealthcare")>_baseline+.06f,"Replenished care did not restore neighborhood benefit");
          Pass("replenished medicine restores actual care and nearby need gain");
          Require(_workplace.DesiredWorkers==6,"Expected six worker slots before partial-staff check");
          for(int i=0;i<3;i++)_workplace.DecreaseDesiredWorkers();
          Phase(9);
        } else if(_phase==9) {
          if(_hospital.AttendingStaff!=3)_stableSince=0;
          else if(_stableSince==0)_stableSince=_clock.PartialDayNumber;
          else if((_clock.PartialDayNumber-_stableSince)*24>=.6f) {
            Require(_hospital.Efficiency==.5f,"Three staff do not provide half treatment efficiency");
            SetNeed(_needs,"Injury",-.3f);_observer.ReleaseControl();Phase(10);
          }
        } else if(_phase==10) {
          if(_hospital.AttendingStaff!=3||_observer.GetComponent<Enterer>().CurrentBuilding!=_building.GetComponent<Enterable>())_arrivalTime=0;
          else if(_arrivalTime==0)_arrivalTime=_clock.PartialDayNumber;
          else if((_clock.PartialDayNumber-_arrivalTime)*24>=.6f) {_baseline=_needs.GetNeedPoints("Injury");Phase(11);}
        } else if(_phase==11&&hours>=1f) {
          Require(_hospital.AttendingStaff==3,"Staff attendance changed during the partial-staff rate sample");
          float rate=(_needs.GetNeedPoints("Injury")-_baseline)/hours;
          Require(Math.Abs(rate-.009666667f)<.001f,"Partial-staff steady injury recovery differs: "+rate);
          Pass("actual three-staff injury treatment="+rate+"/hour; staffing does not consume patient capacity");
          _building.GetComponent<PausableBuilding>().Pause();_hours.WorkedPartOfDay=_normalHours;
          _speed.ChangeSpeed(0);_finished=true;
          _saver.QueueSave(new SaveReference("Hospital continuity - verified",_loader.LoadedSave.SettlementReference),
            ()=>Debug.Log("[DeepFrontier Hospital Reload] ALL RELOAD, NEIGHBORHOOD, SUPPLY AND PARTIAL-STAFF CHECKS PASSED AND SAVED"));
        }
        Require(_clock.PartialDayNumber-_start<3,"Hospital continuity exceeded three simulation days");
      } catch(Exception e) {_finished=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Hospital Reload] FAILED: "+e);}
    }
  }
}
