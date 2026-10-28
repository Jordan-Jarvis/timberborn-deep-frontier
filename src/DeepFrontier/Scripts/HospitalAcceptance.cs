using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.Attractions;
using Timberborn.BehaviorSystem;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.CameraSystem;
using Timberborn.CharacterControlSystem;
using Timberborn.ConstructionSites;
using Timberborn.Coordinates;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.EntityNaming;
using Timberborn.EntitySystem;
using Timberborn.GameSaveRepositorySystem;
using Timberborn.GameSaveRuntimeSystem;
using Timberborn.GoodConsumingBuildingSystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.NeedSystem;
using Timberborn.SingletonSystem;
using Timberborn.TemplateSystem;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class HospitalAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierHospitalAcceptance"))
        Bind<HospitalAcceptance>().AsSingleton();
    }
  }
  internal sealed class HospitalAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _registry; private readonly BlockObjectFactory _factory;
    private readonly TemplateService _templates; private readonly BlockValidator _validator;
    private readonly BlockObjectValidationService _objects; private readonly IBlockService _blocks;
    private readonly SpeedManager _speed; private readonly CameraService _camera;
    private readonly GameSaver _saver; private readonly GameLoader _loader; private readonly IDayNightCycle _clock;
    private readonly WorkingHoursManager _hours; private readonly INavMeshService _nav; private readonly INavigationService _navigation;
    private Hospital _hospital; private BlockObject _building,_bed; private MechanicalNode _generator;
    private GoodConsumingBuilding _supplies; private Enterable _ward;
    private Worker[] _staff; private NeedManager[] _patients;
    private readonly string[] _conditions={"Injury","ChippedTeeth","BadwaterContamination"};
    private readonly HashSet<string> _treated=new();
    private readonly Dictionary<string,int> _stockAtStart=new();
    private readonly Dictionary<string,float> _observedAtEntry=new();
    private readonly Queue<Vector3Int> _targets=new();
    private ControllableCharacter _walker; private Vector3 _walkWorld; private Vector3Int _target;
    private int _frame,_phase,_phaseFrame; private bool _failed,_saved; private float _start,_phaseTime,_normalHours;
    private float _sampleTime,_sampleInjury,_bedRate,_fullStaffTime,_arrivalTime;
    public HospitalAcceptance(EntityRegistry registry,BlockObjectFactory factory,TemplateService templates,
      BlockValidator validator,BlockObjectValidationService objects,IBlockService blocks,SpeedManager speed,
      CameraService camera,GameSaver saver,GameLoader loader,IDayNightCycle clock,WorkingHoursManager hours,
      INavMeshService nav,INavigationService navigation) {
      _registry=registry;_factory=factory;_templates=templates;_validator=validator;_objects=objects;_blocks=blocks;
      _speed=speed;_camera=camera;_saver=saver;_loader=loader;_clock=clock;_hours=hours;_nav=nav;_navigation=navigation;
    }
    public void PostLoad() {
      if(!_registry.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"))
        throw new InvalidOperationException("Hospital acceptance requires the marked disposable settlement");
    }
    private void Require(bool condition,string message) {if(!condition)throw new InvalidOperationException(message);}
    private void Pass(string message) {Debug.Log("[DeepFrontier Hospital] PASS "+message);}
    private BlockObject Create(string id,int x,int y,int z,Orientation orientation=Orientation.Cw0) {
      var t=_templates.GetAll<TemplateSpec>().Single(s=>s.TemplateName==id);
      var spec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==t.Blueprint);
      var placement=new Placement(new Vector3Int(x,y,z),orientation,FlipMode.Unflipped);
      Require(_validator.BlocksValid(spec,placement),"Native placement rejected "+id+" "+placement.Coordinates);
      var b=_factory.CreateFinished(new EntitySetup.Builder(t.Blueprint).AddInitComponent(new FinishedConstructionSiteInit()),placement);
      Require(_objects.IsValid(b),"Native requirements rejected "+id);
      Debug.Log("[DeepFrontier Hospital] PLACED "+id+" "+placement.Coordinates);return b;
    }
    private void Setup() {
      _speed.ChangeSpeed(0);
      Require(!_registry.Entities.Any(e=>e.HasComponent<Hospital>()),"Hospital fixture must start without a hospital");
      foreach(var e in _registry.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))e.GetComponent<PausableBuilding>().Pause();
      // 12x9 hospital (2026-10-22: the two front planter/canopy rows left the footprint, so
      // local y 0 is the old local y 2). Placing at y 162 keeps every hall, door, opening and
      // roof cell at its old world cell; the freed rows are world y 160..161.
      // Every world cell below encodes that layout; read the installed blueprint first so
      // a stale or newer footprint fails here with its real size instead of drifting.
      var installed=_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Hospital.IronTeeth").Blueprint;
      var size=installed.GetSpec<BlockObjectSpec>().Size;
      var deck=installed.HasSpec<PlatformDeckSpec>()?installed.GetSpec<PlatformDeckSpec>():null;
      var openings=deck==null?new string[0]:deck.Openings.Select(o=>o.Id).ToArray();
      Require(size==new Vector3Int(12,9,9)&&openings.Contains("WestFrontLeft")&&openings.Contains("WestFront1")&&deck.Doors.Length==6
        &&installed.GetSpec<BlockObjectSpec>().Entrance.Coordinates==new Vector3Int(6,-1,0),
        "Installed Hospital is "+size.x+"x"+size.y+"x"+size.z+" with "+(deck==null?0:deck.Doors.Length)+" doors and openings ["+
        string.Join(",",openings)+"]; this fixture's roads, ports and walking targets encode the 12x9x9 six-door layout "+
        "(WestFrontLeft/WestFront1, entrance (6,-1,0)). Regenerate the Hospital or update the fixture geometry.");
      Pass("installed Hospital blueprint is the 12x9x9 six-door layout this fixture encodes");
      _building=Create("Hospital.IronTeeth",160,162,3);_hospital=_building.GetComponent<Hospital>();
      _supplies=_building.GetComponent<GoodConsumingBuilding>();_ward=_building.GetComponent<Enterable>();
      // Freed ground, checked before the fixture builds on it: the rear barrel/supply cells
      // inside the bounds (validate_freed_cells.py) and the two former front rows.
      FreedCellProbe.Require(_templates,_validator,_building,
        new[]{new Vector3Int(1,8,0),new Vector3Int(10,8,0),new Vector3Int(11,8,0)}.Concat(FreedCellProbe.Rect(0,11,-2,-1)),
        "Hospital",Pass);
      for(int y=157;y<=159;y++)if(!_blocks.GetPathObjectAt(new Vector3Int(173,y,3)))Create("Path",173,y,3);
      for(int x=159;x<173;x++)Create("Path",x,159,3);
      Create("Path",166,160,3);Create("Path",166,161,3);
      var deckPaths=new HashSet<Vector3Int>();
      for(int x=0;x<=3;x++)deckPaths.Add(new Vector3Int(x,0,2));
      for(int x=8;x<=11;x++)deckPaths.Add(new Vector3Int(x,0,2));
      for(int x=0;x<=11;x++)deckPaths.Add(new Vector3Int(x,8,2));
      for(int x=3;x<=8;x++)deckPaths.Add(new Vector3Int(x,8,4));
      for(int x=4;x<=7;x++)for(int y=5;y<=7;y++)deckPaths.Add(new Vector3Int(x,y,6));
      foreach(var cell in deckPaths)Create("Path",160+cell.x,162+cell.y,3+cell.z);
      Create("PowerShaft.IronTeeth",159,165,3);_generator=Create("DevPowerGenerator",158,165,3).GetComponent<MechanicalNode>();
      Create("DoublePlatform.IronTeeth",164,167,9);Create("Platform.IronTeeth",164,167,11);Create("Path",164,167,12);
      Create("Stairs.IronTeeth",160,160,3,Orientation.Cw180);
      Create("Platform.IronTeeth",160,161,3);Create("Stairs.IronTeeth",160,161,4,Orientation.Cw180);
      // Player path beside the west front balcony's end rail (WestFrontLeft).
      Create("DoublePlatform.IronTeeth",159,162,3);Create("Path",159,162,5);
      _bed=Create("MedicalBed.IronTeeth",166,158,3,Orientation.Cw180);
      Pass("native hospital placement, ground stairs and full roof platform stack");
      Require(_ward.NumberOfEnterersInside==0,"Empty unstaffed hospital already contains patients");
      for(int i=0;i<30;i++){Require(_ward.CanReserveSlot,"Patient capacity ended before thirty");_ward.ReserveSlot();}
      Require(!_ward.CanReserveSlot,"Hospital allowed a thirty-first patient reservation");
      for(int i=0;i<30;i++)_ward.UnreserveSlot();
      Pass("thirty native patient reservations, then full; reservations released");
      Require(!_building.GetComponent<Attraction>().IsUsable,"Empty hospital accepted treatment");
      foreach(var good in _supplies.ConsumedGoods) {
        int amount=(int)Math.Ceiling(good.GoodPerHour*24);
        _supplies.Inventory.GiveExisting(new GoodAmount(good.GoodId,amount));_stockAtStart.Add(good.GoodId,amount);
      }
      // Admitted patients stay until cured and eat from the patient pantry (HospitalPantry).
      var pantry=_hospital.Pantry;
      Require(!pantry.CanFeed,"Patient meals reported before any food was stocked");
      Require(_building.GetComponentsAllocating<Inventory>().Count(i=>i.Enabled)==1&&pantry.Inventory==_supplies.Inventory,"Hospital must keep exactly one enabled native inventory, shared by supplies and patient meals");
      int water=pantry.WaterInStock;
      foreach(var food in pantry.Foods)pantry.Inventory.GiveExisting(new GoodAmount(food,10));
      pantry.Inventory.GiveExisting(new GoodAmount(pantry.WaterGoodId,60));
      Require(pantry.CanFeed&&pantry.FoodInStock==10*pantry.Foods.Count&&pantry.WaterInStock==water+60,"Native hospital inventory did not accept patient food and water");
      Require(_building.GetComponent<Attraction>().Effects.All(e=>e.SatisfyToMaxValue),"Hospital effects must keep patients admitted until cured");
      Pass("patient pantry stocked: "+pantry.Foods.Count+" faction foods and water; every treatment keeps patients until cured");
      _camera.MoveTargetTo(new Vector3(166,7,166));_camera.SetZoomLevel(28,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      _speed.ChangeSpeed(1);
    }
    private void StartCare() {
      Require(_building.GetComponent<MechanicalNode>().PowerEfficiency==1,"Hospital shaft lacks full 600 hp");
      CheckPort("WestFrontLeft",true);CheckPort("WestFront1",false);
      foreach(var door in _building.GetComponent<PlatformDeckSpec>().Doors) {
        var a=_building.TransformCoordinates(door.Interior);var b=_building.TransformCoordinates(door.Exterior);
        Require(_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a),"Hospital door lacks player-path connection: "+door.Interior);
      }
      Pass("all six one-tile doors connect to player-built roads on their own levels");
      // The fixture's road to the district center predates blueprint regeneration; objects the
      // native loader dropped are tolerated only while this route still reaches the district.
      var center=_registry.Entities.Single(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture")
        .GetComponent<BlockObject>();
      var dropped=string.Join("; ",AcceptanceLoadingIssues.DroppedObjects.Select(d=>d.Name+" "+d.Coordinates));
      Require(AcceptanceLoadingIssues.Reported,"Fixture loading issues were not captured completely; see acceptance-loading-issues.json");
      Require(_nav.AreConnectedRoadInstant(center.PositionedEntrance.Coordinates,new Vector3Int(173,159,3)),
        "Hospital road (173,159,3) does not reach the district center entrance "+center.PositionedEntrance.Coordinates+"; dropped fixture objects: "+dropped);
      Pass("hospital road reaches the district center"+(dropped.Length>0?"; tolerated dropped fixture objects: "+dropped:"; fixture loaded cleanly"));
      var workers=_registry.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").ToArray();
      Require(workers.Length>=9,"Hospital fixture needs six staff and three adult patients");
      foreach(var w in workers)w.Unemploy();
      _staff=workers.Take(6).ToArray();_patients=workers.Skip(6).Take(3).Select(w=>w.GetComponent<NeedManager>()).ToArray();
      _building.GetComponent<PausableBuilding>().Pause();
      foreach(var w in _staff) {
        var n=w.GetComponent<NeedManager>();
        foreach(var id in _conditions)SetNeed(n,id,0);
        foreach(var id in new[]{"Hunger","Thirst","Sleep"})SetNeed(n,id,n.GetNeedSpec(id).MaximumValue);
      }
      for(int i=0;i<_patients.Length;i++) {
        foreach(var id in _conditions)SetNeed(_patients[i],id,0);
      }
      SetNeed(_patients[0],"Injury",-.6f);
      _start=_clock.PartialDayNumber;_phase=7;_speed.ChangeSpeed(3);
      Pass("full native shaft supply; first measuring the native Medical Bed control");
    }
    private static void SetNeed(NeedManager n,string id,float value) {
      n.ApplyEffect(new InstantEffect(id,value-n.GetNeedPoints(id),1));
    }
    public void UpdateSingleton() {
      if(_failed||_saved)return;
      try {
        ++_frame;if(_frame==60)Setup();if(_frame==240)StartCare();
        if(_frame==270)Capture("hospital-native");
        if(_frame<=240)return;
        if(_frame%600==0)Debug.Log($"[DeepFrontier Hospital] STATUS phase={_phase}, staff={_hospital.AttendingStaff}, patients={_ward.NumberOfEnterersInside}, care={_hospital.CanUse}, supplied={_supplies.CanUse}, area={_hospital.ProvidesNeighborhoodCare}, treated={string.Join(",",_treated)}");
        if(_phase==1)CheckCare();
        else if(_phase==7) {
          if(_patients[0].GetComponent<Enterer>().CurrentBuilding!=_bed.GetComponent<Enterable>()) {_sampleTime=0;_arrivalTime=0;}
          else if(_arrivalTime==0)_arrivalTime=_clock.PartialDayNumber;
          else if((_clock.PartialDayNumber-_arrivalTime)*24<.6f) {}
          else if(_sampleTime==0) {_sampleTime=_clock.PartialDayNumber;_sampleInjury=_patients[0].GetNeedPoints("Injury");}
          else if((_clock.PartialDayNumber-_sampleTime)*24>=1f) {
            _bedRate=(_patients[0].GetNeedPoints("Injury")-_sampleInjury)/((_clock.PartialDayNumber-_sampleTime)*24);
            Require(Math.Abs(_bedRate-(.015f+.1f/24)/2)<.001f,"Steady Medical Bed control differs from its native repeat-visit cadence: "+_bedRate);
            Pass("measured native Medical Bed recovery="+_bedRate+"/hour");
            _bed.GetComponent<PausableBuilding>().Pause();SetNeed(_patients[0],"Injury",0);
            _building.GetComponent<PausableBuilding>().Resume();
            foreach(var w in _staff) {w.Unemploy();w.EmployAt(_building.GetComponent<Workplace>());}
            _sampleTime=0;_arrivalTime=0;_phase=8;
          }
        } else if(_phase==8) {
          if(_hospital.AttendingStaff!=6)_fullStaffTime=0;
          else if(_fullStaffTime==0)_fullStaffTime=_clock.PartialDayNumber;
          else if((_clock.PartialDayNumber-_fullStaffTime)*24>=.6f) {
            // Build 146 regression: the ward must admit with no patient meals in stock.
            var pantry=_hospital.Pantry;var held=pantry.Foods.Select(id=>new GoodAmount(id,pantry.Inventory.UnreservedAmountInStock(id))).Where(g=>g.Amount>0).ToList();
            foreach(var g in held)pantry.Inventory.TakeExisting(g);
            Require(pantry.Enabled&&pantry.FoodInStock==0&&!pantry.MealsShort&&_hospital.CanUse&&_building.GetComponent<Attraction>().IsUsable,
              "Staffed, powered, supplied Hospital must admit before its first meal delivery");
            foreach(var g in held)pantry.Inventory.GiveExisting(g);
            Pass("staffed, powered, supplied ward is open with an empty food stock");
            for(int i=0;i<_patients.Length;i++)SetNeed(_patients[i],_conditions[i],-.6f);
            _phase=1;
            Pass("six staff stably attending before separate injury, teeth and contamination cases begin");
          }
        }
        else if(_phase==2&&(_clock.PartialDayNumber-_phaseTime)*24>=.6f) {
          Require(!_hospital.CanUse&&!_hospital.ProvidesNeighborhoodCare,"Unpowered hospital still offers care");
          Require(!_building.GetComponent<Attraction>().IsUsable&&!_supplies.IsConsuming,"Unpowered treatment or supplies remain active");
          Pass("zero shaft power disables treatment, supplies and neighborhood care");
          _generator.SetOutputMultiplier(1);_phase=3;
        } else if(_phase==3&&_hospital.CanUse&&_hospital.ProvidesNeighborhoodCare) {
          Pass("care and neighborhood effect resume with power");
          _hours.WorkedPartOfDay=0;_phaseTime=_clock.PartialDayNumber;_phase=4;
        } else if(_phase==4&&(_clock.PartialDayNumber-_phaseTime)*24>=.6f) {
          Require(_hospital.CanUse&&!_hospital.Attended&&!_hospital.ProvidesNeighborhoodCare,"Off-duty hospital must keep its ward open on call while attendance and neighborhood care stop");
          Pass("off-duty crew stays on call: ward open, attendance and neighborhood care stop");
          _hours.WorkedPartOfDay=1;_phase=5;
        } else if(_phase==5&&_hospital.CanUse&&_hospital.ProvidesNeighborhoodCare) {
          _walker=_staff[0].GetComponent<ControllableCharacter>();
          _building.GetComponent<PausableBuilding>().Pause();_walker.GetComponent<Worker>().Unemploy();
          foreach(var cell in new[]{new Vector3Int(6,0,0),new Vector3Int(2,1,2),new Vector3Int(0,8,2),
            new Vector3Int(6,7,4),new Vector3Int(6,4,6),new Vector3Int(4,7,6),
            new Vector3Int(0,0,2),new Vector3Int(11,0,2),new Vector3Int(9,1,2),new Vector3Int(0,-3,0)})_targets.Enqueue(cell);
          _phase=6;NextTarget();
        } else if(_phase==6&&Vector3.Distance(_walker.Transform.position,_walkWorld)<.18f) {
          Pass("actual beaver reached "+_target);
          if(_targets.Count>0)NextTarget();
          else {
            _walker.ReleaseControl();_hours.WorkedPartOfDay=_normalHours;
            _speed.ChangeSpeed(0);_saved=true;Capture("hospital-care-and-access");
            _saver.QueueSave(new SaveReference("Hospital acceptance - verified",_loader.LoadedSave.SettlementReference),
              ()=>Debug.Log("[DeepFrontier Hospital] ALL CARE, STAFF, POWER, CAPACITY AND ACCESS CHECKS PASSED AND SAVED"));
          }
        }
        Require(_clock.PartialDayNumber-_start<4,"Hospital acceptance exceeded four simulation days");
      } catch(Exception e) {_failed=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Hospital] FAILED: "+e);}
    }
    private void CheckCare() {
      for(int i=0;i<_patients.Length;i++) {
        var n=_patients[i];string id=_conditions[i];
        if(n.GetComponent<Enterer>().CurrentBuilding!=_ward)continue;
        float points=n.GetNeedPoints(id);
        if(!_observedAtEntry.ContainsKey(id)) {
          _observedAtEntry.Add(id,points);Pass("patient entered native ward for "+id);
          // The long contamination stay proves in-place meals: start it hungry and thirsty.
          if(id=="BadwaterContamination") {SetNeed(n,"Hunger",.2f);SetNeed(n,"Thirst",.2f);}
        }
        if(points-_observedAtEntry[id]>.012f&&_treated.Add(id))Pass("actual native recovery for "+id);
        if(id=="BadwaterContamination"&&!_treated.Contains("Fed")&&n.GetNeedPoints("Hunger")>.45f&&n.GetNeedPoints("Thirst")>.45f) {
          _treated.Add("Fed");Pass("admitted patient fed and watered in the ward from the patient pantry");
        }
      }
      // Admitted until cured: a patient seen in the ward never leaves with its condition untreated.
      for(int i=0;i<_patients.Length;i++) {
        string id=_conditions[i];var n=_patients[i];
        if(_observedAtEntry.ContainsKey(id)&&n.GetComponent<Enterer>().CurrentBuilding!=_ward)
          Require(n.NeedPointsToMax(id)<=.001f,"Patient left the ward before "+id+" was cured: "+n.GetNeedPoints(id));
      }
      if(_hospital.AttendingStaff==6&&_patients[0].GetComponent<Enterer>().CurrentBuilding==_ward) {
        if(_arrivalTime==0)_arrivalTime=_clock.PartialDayNumber;
        else if((_clock.PartialDayNumber-_arrivalTime)*24<.6f) {}
        else if(_sampleTime==0) {_sampleTime=_clock.PartialDayNumber;_sampleInjury=_patients[0].GetNeedPoints("Injury");}
        else if((_clock.PartialDayNumber-_sampleTime)*24>=1f&&!_treated.Contains("Rate")) {
          float elapsed=(_clock.PartialDayNumber-_sampleTime)*24;
          float rate=(_patients[0].GetNeedPoints("Injury")-_sampleInjury)/elapsed;
          Debug.Log("[DeepFrontier Hospital] RATE sample hours="+elapsed+", staff="+_hospital.AttendingStaff+
            ", power="+_building.GetComponent<MechanicalNode>().PowerEfficiency+", injury="+rate+", bed="+_bedRate);
          Require(Math.Abs(rate/_bedRate-1.8f)<.08f,"Measured injury rate differs from 1.8x Medical Bed: "+rate+" vs "+_bedRate);
          var effects=new List<ContinuousEffect>();_building.GetComponent<Attraction>().GetEfficiencyAdjustedEffects(effects);
          var expectedNeeds=new[]{"Injury","ChippedTeeth","BadwaterContamination","Irradiation"};
          Require(effects.Count==4&&expectedNeeds.All(id=>effects.Count(e=>e.NeedId==id)==1),
            "Native hospital treatment effects differ: "+string.Join(",",effects.Select(e=>e.NeedId+"="+e.PointsPerHour)));
          // Irradiation is treated at its authored rate scaled by the same native efficiency as Injury.
          var authored=_building.GetComponent<Attraction>().Effects;
          float injuryScale=effects.Single(e=>e.NeedId=="Injury").PointsPerHour/authored.Single(e=>e.NeedId=="Injury").PointsPerHour;
          var irradiation=effects.Single(e=>e.NeedId=="Irradiation");
          float irradiationAuthored=authored.Single(e=>e.NeedId=="Irradiation").PointsPerHour;
          Require(irradiationAuthored>0&&irradiation.PointsPerHour>0&&Math.Abs(irradiation.PointsPerHour/irradiationAuthored-injuryScale)<.0001f,
            "Irradiation treatment rate "+irradiation.PointsPerHour+"/h does not follow the authored "+irradiationAuthored+"/h at efficiency "+injuryScale);
          Pass("four native treatment effects; Irradiation "+irradiation.PointsPerHour+"/hour (authored "+irradiationAuthored+"/hour x efficiency "+injuryScale+")");
          _treated.Add("Rate");Pass("measured full-staff injury recovery="+rate+"/hour; measured Medical Bed="+_bedRate+"/hour; ratio="+rate/_bedRate);
          Require(_staff.All(w=>w.GetComponent<Enterer>().CurrentBuilding!=_ward),"Staff consume patient places");
          Pass("six attending workers consume none of the thirty patient places");
        }
      } else if(!_treated.Contains("Rate")) {_sampleTime=0;_arrivalTime=0;}
      if(_treated.Count==5&&_hospital.ProvidesNeighborhoodCare) {
        foreach(var id in _stockAtStart.Keys)Require(_supplies.Inventory.AmountInStock(id)<_stockAtStart[id],"Operating hospital did not consume "+id);
        Pass("native medicine, water and extract consumption; neighborhood service active");
        Capture("hospital-treating");_generator.SetOutputMultiplier(0);
        _phaseTime=_clock.PartialDayNumber;_phase=2;
      }
    }
    private void CheckPort(string id,bool expected) {
      var p=_building.GetComponent<PlatformDeckSpec>().Openings.Single(p=>p.Id==id);
      var a=_building.TransformCoordinates(p.Inside);var b=_building.TransformCoordinates(p.Outside);
      bool connected=_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a);
      var nodes=_building.GetComponent<BuildingModel>().FinishedModel.GetComponentsInChildren<Transform>(true);
      bool hidden=p.HiddenNodes.All(n=>!nodes.Single(t=>t.name==n).gameObject.activeSelf);
      Require(connected==expected&&hidden==expected,"Hospital route/rail mismatch "+id);Pass("rail "+id+" open="+expected);
    }
    private void NextTarget() {
      _target=_targets.Dequeue();
      _walkWorld=NavigationCoordinateSystem.GridToWorld(_building.TransformCoordinates(_target));
      Require(_navigation.FindPathUnlimitedRange(_walker.Transform.position,_walkWorld,new List<PathCorner>(),out var distance),"No native route to "+_target);
      _walker.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_walkWorld));
      Debug.Log("[DeepFrontier Hospital] WALK "+_target+" distance="+distance);
    }
    private static void Capture(string name) {
      const string folder="C:/Users/Jordan/Documents/TimberbornModding/docs/art/reviews/2026-10-21-hospital-wings-runtime";
      Directory.CreateDirectory(folder);ScreenCapture.CaptureScreenshot(Path.Combine(folder,name+".png"));
    }
  }
}
