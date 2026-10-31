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
    private Hospital _hospital; private BlockObject _building,_bed; private MechanicalNode[] _generators;
    private GoodConsumingBuilding _supplies; private Enterable _ward;
    private Worker[] _staff; private NeedManager[] _patients;
    private readonly string[] _conditions={"Injury","ChippedTeeth","BadwaterContamination"};
    private readonly HashSet<string> _treated=new();
    private readonly Dictionary<string,int> _stockAtStart=new();
    private readonly Dictionary<string,float> _observedAtEntry=new();
    private readonly Queue<Vector3Int> _targets=new();
    // A free stretch north of the fixture map's road row; everything around the hospital is
    // derived from its installed blueprint in Setup.
    private static readonly Vector3Int Origin=new(160,162,3);
    private readonly List<Vector3Int> _walk=new();
    private string _openRail,_closedRail;
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
    private BlockObject Local(string id,Vector3Int local,Orientation orientation=Orientation.Cw0) {
      var c=_building.TransformCoordinates(local);return Create(id,c.x,c.y,c.z,orientation);
    }
    private void Setup() {
      _speed.ChangeSpeed(0);
      Require(!_registry.Entities.Any(e=>e.HasComponent<Hospital>()),"Hospital fixture must start without a hospital");
      foreach(var e in _registry.Entities.Where(e=>e.HasComponent<Workplace>()&&e.HasComponent<PausableBuilding>()))e.GetComponent<PausableBuilding>().Pause();
      // The hospital stands at the fixture origin; its road, deck paths, stairs, shaft line and
      // rail seam below follow the installed blueprint (CivicFixtureGeometry), not a size literal
      // (4x9x9 since the 2026-10-30 compaction: the central pavilion, rear decks at layers 2 and 4,
      // roof garden at 6).
      _building=Create("Hospital.IronTeeth",Origin.x,Origin.y,Origin.z);_hospital=_building.GetComponent<Hospital>();
      _supplies=_building.GetComponent<GoodConsumingBuilding>();_ward=_building.GetComponent<Enterable>();
      var spec=_building.GetComponent<BlockObjectSpec>();var deck=_building.GetComponent<PlatformDeckSpec>();
      var blocks=CivicFixtureGeometry.Blocks(spec);
      var pathSpec=_templates.GetAll<BlockObjectSpec>().Single(s=>s.Blueprint==_templates.GetAll<TemplateSpec>().Single(t=>t.TemplateName=="Path").Blueprint);
      bool TakesPath(Vector3Int local)=>_validator.BlocksValid(pathSpec,new Placement(_building.TransformCoordinates(local),Orientation.Cw0,FlipMode.Unflipped));
      CivicFixtureGeometry.Place place=(id,c,o)=>Create(id,c.x,c.y,c.z,o);
      var levels=deck.Openings.Select(o=>o.Inside.z).Distinct().OrderBy(z=>z).ToArray();
      CivicFixtureGeometry.Road(place,c=>_blocks.GetPathObjectAt(c),_building.TransformCoordinates(spec.Entrance.Coordinates));
      // Player paths on every deck: every rail's deck cell and upper door step and the cells of
      // their layer that take a Path, except one roof cell that carries the full platform stack.
      var region=CivicFixtureGeometry.DeckRegion(spec,deck.Openings.Select(o=>o.Inside).Concat(deck.Doors.Select(d=>d.Exterior).Where(c=>c.z>0)),TakesPath,"Hospital");
      var tower=region.Where(c=>c.z==levels[levels.Length-1]&&deck.Openings.All(o=>o.Inside!=c)&&deck.Doors.All(d=>d.Exterior!=c)).ToArray();
      Require(tower.Length>0,"Hospital roof deck has no cell besides rail and door cells for the platform stack");
      foreach(var c in region.Where(c=>c!=tower[0]))Local("Path",c);
      Local("DoublePlatform.IronTeeth",tower[0]);Local("Platform.IronTeeth",tower[0]+new Vector3Int(0,0,2));Local("Path",tower[0]+new Vector3Int(0,0,3));
      // Ground stairs climb to the middle rear rail of the lowest deck.
      var rear=deck.Openings.Where(o=>o.Inside.z==levels[0]&&o.Outside-o.Inside==new Vector3Int(0,1,0)&&CivicFixtureGeometry.FreeColumn(blocks,o.Outside)).ToArray();
      Require(rear.Length>0,"Hospital lowest deck has no rear rail with a free column outside it for the stairs");
      var flightRail=rear[rear.Length/2];
      var flight=CivicFixtureGeometry.Flight(place,_building.TransformCoordinates(flightRail.Outside),new Vector3Int(0,1,0),Origin.z);
      // Player path on a platform stack beside the lowest deck's first side rail (open); the next
      // rail of that deck with nothing outside it stays closed.
      var seam=deck.Openings.FirstOrDefault(o=>o.Inside.z==levels[0]&&o.Outside.y==o.Inside.y&&CivicFixtureGeometry.FreeColumn(blocks,o.Outside));
      Require(seam!=null,"Hospital lowest deck has no side rail with a free column outside it");
      var shut=deck.Openings.FirstOrDefault(o=>o.Inside.z==levels[0]&&o.Outside!=seam.Outside&&o.Outside!=flightRail.Outside);
      Require(shut!=null,"Hospital lowest deck has no third rail to stay closed");
      CivicFixtureGeometry.Pad(place,_building.TransformCoordinates(seam.Outside),Origin.z);
      _openRail=seam.Id;_closedRail=shut.Id;
      // Two stacked 10,000 hp dev generators cover the 11,000 hp demand, on a shaft line out of the
      // lowest wall face clear of the stairs and the seam pad.
      var used=new HashSet<Vector2Int>(flight.Select(c=>new Vector2Int(c.x,c.y)));
      var pad=_building.TransformCoordinates(seam.Outside);used.Add(new Vector2Int(pad.x,pad.y));
      var face=CivicFixtureGeometry.ShaftFace(spec,_building.GetComponent<TransputProviderSpec>(),
        c=>{var w=_building.TransformCoordinates(c);return used.Contains(new Vector2Int(w.x,w.y));},"Hospital");
      _generators=CivicFixtureGeometry.ShaftLine(place,_building,face,2);
      // Walk (local cells; the hospital stands Cw0 unflipped): Entrance, each upper door step, the
      // seam pad, the stair foot, then the road south of the Entrance.
      var entrance=spec.Entrance.Coordinates;
      _walk.Add(entrance);_walk.AddRange(deck.Doors.Select(d=>d.Exterior).Where(c=>c.z>0));
      _walk.Add(seam.Outside);_walk.Add(flight[0]-_building.Coordinates);_walk.Add(entrance+new Vector3Int(0,-1,0));
      _bed=Create("MedicalBed.IronTeeth",166,158,3,Orientation.Cw180);
      Pass("native hospital placement, ground stairs, deck paths and full roof platform stack");
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
      var centre=_building.TransformCoordinates(_building.GetComponent<BlockObjectSpec>().Size/2);
      _camera.MoveTargetTo(new Vector3(centre.x,7,centre.y));_camera.SetZoomLevel(28,0);_camera.HorizontalAngle=25;_camera.VerticalAngle=35;
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      _speed.ChangeSpeed(1);
    }
    private void StartCare() {
      Require(_building.GetComponent<MechanicalNode>().PowerEfficiency==1,"Hospital shaft lacks full 11,000 hp");
      CheckPort(_openRail,true);CheckPort(_closedRail,false);
      foreach(var door in _building.GetComponent<PlatformDeckSpec>().Doors) {
        var a=_building.TransformCoordinates(door.Interior);var b=_building.TransformCoordinates(door.Exterior);
        Require(_nav.AreConnectedInstant(a,b)&&_nav.AreConnectedInstant(b,a),"Hospital door lacks player-path connection: "+door.Interior);
      }
      Pass("all "+_building.GetComponent<PlatformDeckSpec>().Doors.Length+" one-tile doors connect to player-built roads on their own levels");
      // The fixture's road to the district center predates blueprint regeneration; objects the
      // native loader dropped are tolerated only while this route still reaches the district.
      var center=_registry.Entities.Single(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture")
        .GetComponent<BlockObject>();
      var dropped=string.Join("; ",AcceptanceLoadingIssues.DroppedObjects.Select(d=>d.Name+" "+d.Coordinates));
      Require(AcceptanceLoadingIssues.Reported,"Fixture loading issues were not captured completely; see acceptance-loading-issues.json");
      Require(_nav.AreConnectedRoadInstant(center.PositionedEntrance.Coordinates,CivicFixtureGeometry.RoadJunction),
        "Hospital road "+CivicFixtureGeometry.RoadJunction+" does not reach the district center entrance "+center.PositionedEntrance.Coordinates+"; dropped fixture objects: "+dropped);
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
          foreach(var g in _generators)g.SetOutputMultiplier(1);_phase=3;
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
          foreach(var cell in _walk)_targets.Enqueue(cell);
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
        Capture("hospital-treating");foreach(var g in _generators)g.SetOutputMultiplier(0);
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
