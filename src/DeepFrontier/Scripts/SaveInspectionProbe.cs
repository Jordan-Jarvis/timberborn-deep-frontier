#if !UNITY_EDITOR
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using Bindito.Core;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.Buildings;
using Timberborn.BuildingsReachability;
using Timberborn.Coordinates;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.MechanicalSystem;
using Timberborn.Navigation;
using Timberborn.PathSystem;
using Timberborn.SelectionSystem;
using Timberborn.SingletonSystem;
using Timberborn.StatusSystem;
using Timberborn.TemplateSystem;
using Timberborn.WorkSystem;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts {
  // Read-only report on a loaded save copy: -deepFrontierLoadAcceptance -deepFrontierLoadSave "<copy in
  // Memory Test>" -deepFrontierSaveInspect (tools/start_memory_load.ps1 -SaveInspect). Nothing is placed,
  // changed or saved (MemoryLoadProbe saves only with -deepFrontierSaveAs, which this run never passes).
  [Context("Game")]
  public sealed class SaveInspectionProbeConfigurator : Configurator {
    protected override void Configure() {
      var args=Environment.GetCommandLineArgs();
      if(!args.Contains(SaveInspectionProbe.Flag))return;
      if(MemoryLoadProbe.SavePath()==null)throw new InvalidOperationException(SaveInspectionProbe.Flag+" requires -deepFrontierLoadAcceptance with -deepFrontierLoadSave");
      if(args.Contains(MemoryLoadProbe.SaveAsFlag))throw new InvalidOperationException(SaveInspectionProbe.Flag+" is read-only; it never runs with "+MemoryLoadProbe.SaveAsFlag);
      Bind<SaveInspectionProbe>().AsSingleton();
    }
  }

  // Per FishHatchery, FisheryWorks and Greenhouse in the save (build 176 user reports): placement,
  // visible statuses, district, entrance and doorstep, whether the entrance cell holds a Path, the
  // native path connection toward the door, road connection to each district centre's entrance,
  // single access, entrance blocked/inaccessible, the mechanical graph, and every transput with its
  // world cell, direction, target, connected node and connector socket.
  internal sealed class SaveInspectionProbe : IUpdatableSingleton {
    internal const string Flag="-deepFrontierSaveInspect";
    private const string Tag="[DeepFrontier SaveInspect]";
    private static readonly string[] Templates={"FishHatchery.IronTeeth","FisheryWorks.IronTeeth","Greenhouse.IronTeeth"};
    private readonly EntityRegistry _entities;
    private readonly IBlockService _blocks;
    private readonly IConnectionService _connections;
    private readonly INavMeshService _nav;
    private readonly WatersideSurvey _survey;
    private readonly EntitySelectionService _selection;
    private readonly Timberborn.TimeSystem.IDayNightCycle _clock;
    private readonly Timberborn.TimeSystem.SpeedManager _speed;
    private readonly Timberborn.StockpilesUI.GoodStockpilesTooltipFactory _tooltips;
    private readonly Timberborn.Goods.IGoodService _goods;
    private readonly INavigationService _navigation;
    private Restaurant _restaurant;
    private int _frame,_shotFrame;private bool _done;

    public SaveInspectionProbe(EntityRegistry entities,IBlockService blocks,IConnectionService connections,INavMeshService nav,WatersideSurvey survey,
        EntitySelectionService selection,Timberborn.TimeSystem.IDayNightCycle clock,Timberborn.TimeSystem.SpeedManager speed,
        Timberborn.StockpilesUI.GoodStockpilesTooltipFactory tooltips,Timberborn.Goods.IGoodService goods,INavigationService navigation) {
      _entities=entities;_blocks=blocks;_connections=connections;_nav=nav;_survey=survey;_selection=selection;_clock=clock;_speed=speed;_tooltips=tooltips;_goods=goods;_navigation=navigation;
    }

    private static string Xyz(Vector3Int c)=>"("+c.x+","+c.y+","+c.z+")";

    public void UpdateSingleton() {
      ++_frame;
      // Restaurant panel review: select the first restaurant after the report, capture a frame later.
      // Scroll the entity panel to the restaurant fragment's top, then its end, capturing each.
      if(_shotFrame>0&&(_frame==_shotFrame-30||_frame==_shotFrame+30)) {
        var title=UnityEngine.Object.FindObjectsOfType<UIDocument>()
          .SelectMany(d=>d.rootVisualElement.Query<Label>().ToList()).FirstOrDefault(l=>l.text=="Dining room");
        if(title==null)Debug.Log(Tag+" restaurant panel not found");
        else {
          var fragment=title.parent;
          var target=_frame==_shotFrame-30?title:fragment.Query<Label>().ToList().Last();
          for(var e=fragment;e!=null;e=e.parent)if(e is ScrollView view){view.ScrollTo(target);break;}
          if(_frame==_shotFrame-30)
            Debug.Log(Tag+" restaurant panel text: "+string.Join(" | ",fragment.Query<Label>().ToList().Select(l=>l.text).Where(t=>!string.IsNullOrEmpty(t))));
        }
      }
      if(_shotFrame>0&&(_frame==_shotFrame||_frame==_shotFrame+60)) {
        var shot=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs",
          "save-inspect-restaurant-panel-"+(_frame==_shotFrame?"top":"end")+".png");
        ScreenCapture.CaptureScreenshot(shot);Debug.Log(Tag+" restaurant panel captured "+shot);
        // After the last capture the service log runs at speed 3 (MemoryLoadProbe counts game time).
        if(_frame==_shotFrame+60)_speed.ChangeSpeed(3f);
      }
      // Passages once the queued nav-mesh changes are applied: can a beaver walk from each building's
      // entrance over roads to the other building's doorstep (native road path search)?
      if(_frame==1200) {
        Debug.Log(Tag+" passages at frame 1200");
        int both=0,oneWay=0,none=0;
        foreach(var p in BuildingPassages.Passages) {
          bool ab=_navigation.FindRoadPath(NavigationCoordinateSystem.GridToWorld(p.A.PositionedEntrance.Coordinates),NavigationCoordinateSystem.GridToWorld(p.B.PositionedEntrance.DoorstepCoordinates),out _);
          bool ba=_navigation.FindRoadPath(NavigationCoordinateSystem.GridToWorld(p.B.PositionedEntrance.Coordinates),NavigationCoordinateSystem.GridToWorld(p.A.PositionedEntrance.DoorstepCoordinates),out _);
          if(ab&&ba)both++;else if(ab||ba)oneWay++;else none++;
        }
        Debug.Log(Tag+" passages recheck: "+BuildingPassages.Passages.Count+" walkableBothWays="+both+" oneWay="+oneWay+" notWalkable="+none);
        // Per linked building, from its district centre over roads: its own entrance (native) and its doorstep (now its access).
        var centre=_entities.Entities.Select(e=>e.GetComponent<DistrictCenter>()).FirstOrDefault(d=>d);
        if(centre) {
          var from=NavigationCoordinateSystem.GridToWorld(centre.GetComponent<BlockObject>().PositionedEntrance.Coordinates);
          int kept=0,gained=0,lost=0,neither=0;
          // Hooman Stairs' top buildings instead when that mod is on (reference for the same measurement).
          var hooman=AppDomain.CurrentDomain.GetAssemblies().Select(a=>a.GetType("Calloatti.HoomanStairs.HoomanStairsRegistry")).FirstOrDefault(t=>t!=null);
          var measured=hooman!=null?((IEnumerable)hooman.GetField("TopBuildings").GetValue(null)).Cast<BlockObject>().ToList():BuildingPassages.Linked.Keys.ToList();
          Debug.Log(Tag+" passages reach measuring "+(hooman!=null?"Hooman Stairs top buildings":"Deep Frontier linked buildings")+": "+measured.Count);
          int instantDoor=0;
          foreach(var b in measured) {
            bool entrance=_navigation.FindRoadPath(from,NavigationCoordinateSystem.GridToWorld(b.PositionedEntrance.Coordinates),out _);
            bool door=_navigation.FindRoadPath(from,NavigationCoordinateSystem.GridToWorld(b.PositionedEntrance.DoorstepCoordinates),out _);
            if(_navigation.FindInstantRoadPath(from,NavigationCoordinateSystem.GridToWorld(b.PositionedEntrance.DoorstepCoordinates),out _))instantDoor++;
            if(entrance&&door)kept++;else if(door)gained++;else if(entrance){lost++;Debug.Log(Tag+" passage LOST "+b.GetComponent<TemplateSpec>()?.TemplateName+" "+Xyz(b.Coordinates));}else neither++;
            if(door&&!entrance)Debug.Log(Tag+" passage GAINED "+b.GetComponent<TemplateSpec>()?.TemplateName+" "+Xyz(b.Coordinates));
          }
          Debug.Log(Tag+" passages reach from district centre: kept="+kept+" gained="+gained+" lost="+lost+" neither="+neither+" doorstepInstant="+instantDoor);
        }
        foreach(var p in BuildingPassages.Passages.Take(8))
          Debug.Log(Tag+" passage "+p.A.GetComponent<TemplateSpec>()?.TemplateName+" "+Xyz(p.A.Coordinates)+" <-> "+p.B.GetComponent<TemplateSpec>()?.TemplateName+" "+Xyz(p.B.Coordinates)
            +" steps="+p.Path.Count+" walk="+_navigation.FindRoadPath(NavigationCoordinateSystem.GridToWorld(p.A.PositionedEntrance.Coordinates),NavigationCoordinateSystem.GridToWorld(p.B.PositionedEntrance.DoorstepCoordinates),out _));
      }
      // Power plant log every 600 frames: burning, paused for no demand, fuel stock, graph supply/demand.
      if(_frame%600==0&&_frame>=240)
        foreach(var plant in _entities.Entities.Select(e=>e.GetComponent<Timberborn.GoodConsumingBuildingSystem.GoodConsumingBuilding>()).Where(g=>g&&g.GetComponent<TemplateSpec>().TemplateName.EndsWith("PowerPlant.IronTeeth"))) {
          var node=plant.GetComponent<MechanicalNode>();var inv=plant.AllComponents.OfType<Timberborn.InventorySystem.Inventory>().FirstOrDefault(i=>i.ComponentName=="GoodConsumingBuilding");
          Debug.Log(Tag+" plant "+plant.GetComponent<TemplateSpec>().TemplateName+" consuming="+plant.IsConsuming+" paused="+plant.ConsumptionPaused
            +" stock="+(inv?string.Join(",",inv.Stock.Select(g=>g.GoodId+":"+g.Amount)):"none")
            +" graph="+(node.Graph==null?"none":node.Graph.PowerSupply+"/"+node.Graph.PowerDemand));
        }
      // Restaurant service log every 300 frames: hour, staff on duty, each recipe's batch progress, main food stock, meals.
      if(_restaurant&&_frame%100==0) {
        var chooser=_restaurant.GetComponent<RestaurantKitchenChooser>();var kitchen=_restaurant.GetComponent<Timberborn.Workshops.Manufactory>();
        Debug.Log(Tag+" restaurant hour="+_clock.HoursPassedToday.ToString("0.0")+" onDuty="+_restaurant.StaffOnDuty
          +" staff="+string.Join(",",_restaurant.Workplace.AssignedWorkers.Select(w=>w.GetComponent<Timberborn.WorkSystem.WorkerWorkingHours>().AreWorkingHours))
          +" recipe="+chooser.Cooking?.Id+" ready="+kitchen.IsReadyToProduce+" progress="+string.Join(",",kitchen.ProductionRecipes.Select(r=>r.Id+":"+chooser.Progress(r).ToString("0.00")))
          +" stock="+string.Join(",",_restaurant.Spec.Foods.Concat(_restaurant.Spec.OptionalGoods).Select(id=>id+":"+_restaurant.Inventory.AmountInStock(id)))
          +" seated="+_restaurant.GetComponent<RestaurantSeats>().SeatedDiners.Count()+" waitingGuests="+_restaurant.GetComponent<RestaurantSeats>().SeatedDiners.Count(d=>!d.Served)
          +" cooking="+_restaurant.Workplace.AssignedWorkers.Count(w=>w.GetComponent<Timberborn.BehaviorSystem.BehaviorManager>().IsRunningExecutor<Timberborn.Workshops.ProduceExecutor>())
          +" serving="+_restaurant.Workplace.AssignedWorkers.Count(w=>w.GetComponent<RestaurantWaiter>().Stage!=RestaurantOrderStage.None)
          +" meals="+_restaurant.MealsServedThisSession);
      }
      if(_done||_frame<240)return;
      _done=true;
      // Building passages (BuildingPassages.cs): count and kinds now; real road paths are checked at frame 1200.
      Debug.Log(Tag+" passages: "+BuildingPassages.Passages.Count+" linkedBuildings="+BuildingPassages.Linked.Count
        +" stacked="+BuildingPassages.Passages.Count(p=>p.Path.Any(c=>c.z!=p.Path[0].z))+" hoomanStairs="+BuildingPassagesHoomanStairs.Enabled);
      // Top-bar good tooltip (crashed on a good type without a stockpile, build 190): build it for every good.
      foreach(var id in _goods.Goods)_tooltips.Create(id);
      Debug.Log(Tag+" good tooltips built for "+_goods.Goods.Count+" goods");
      var restaurant=_entities.Entities.Select(e=>e.GetComponent<Restaurant>()).FirstOrDefault(r=>r);
      if(restaurant){_selection.SelectAndFocusOn(restaurant);_shotFrame=_frame+120;_restaurant=restaurant;}
      var save=MemoryLoadProbe.SavePath();
      var centres=_entities.Entities.Select(e=>e.GetComponent<DistrictCenter>()).Where(d=>d).ToList();
      var report=new JObject{["save"]=save,["districtCentres"]=new JArray(centres.Select(d=>d.Name+" entrance "+Xyz(d.GetComponent<BlockObject>().PositionedEntrance.Coordinates)))};
      var buildings=new JArray();
      foreach(var e in _entities.Entities.Where(e=>Templates.Contains(e.GetComponent<TemplateSpec>()?.TemplateName)).ToList()) {
        var b=e.GetComponent<BlockObject>();
        var o=new JObject{["template"]=e.GetComponent<TemplateSpec>().TemplateName,["coordinates"]=Xyz(b.Coordinates),["baseZ"]=b.BaseZ,
          ["orientation"]=b.Orientation.ToString(),["flipped"]=b.FlipMode.IsFlipped,["finished"]=b.IsFinished};
        var subject=b.GetComponent<StatusSubject>();
        o["statuses"]=new JArray(subject?subject.ActiveStatuses.Where(s=>s.IsVisible()).Select(s=>s.StatusDescription+(s.ShowFloatingIcon?" [icon]":"")):Enumerable.Empty<string>());
        var district=b.GetComponent<DistrictBuilding>();
        o["instantDistrict"]=district&&district.InstantDistrict?district.InstantDistrict.Name:null;
        if(b.HasEntrance) {
          var en=b.PositionedEntrance;
          var dir=new[]{Direction2D.Down,Direction2D.Left,Direction2D.Up,Direction2D.Right}
            .Single(d=>d.ToOffset()==new Vector3Int(en.DoorstepCoordinates.x-en.Coordinates.x,en.DoorstepCoordinates.y-en.Coordinates.y,0));
          o["entrance"]=Xyz(en.Coordinates);o["doorstep"]=Xyz(en.DoorstepCoordinates);
          o["entranceObjects"]=new JArray(_blocks.GetObjectsAt(en.Coordinates).Select(x=>x.GetComponent<TemplateSpec>()?.TemplateName));
          o["doorstepObjects"]=new JArray(_blocks.GetObjectsAt(en.DoorstepCoordinates).Select(x=>x.GetComponent<TemplateSpec>()?.TemplateName));
          o["pathConnectsTowardDoor"]=_connections.CanConnectInDirection(en.Coordinates,dir);
          o["roadToDistrictCentres"]=new JArray(centres.Select(d=>d.Name+" "+_nav.AreConnectedRoadInstant(en.Coordinates,d.GetComponent<BlockObject>().PositionedEntrance.Coordinates)));
          var reach=b.GetComponent<BlockableEntranceBuilding>();
          if(reach){o["entranceBlocked"]=reach.IsEntranceBlocked();o["entranceInaccessible"]=reach.IsEntranceInaccessible();}
          var access=b.GetComponent<BuildingAccessible>()?.Accessible;
          o["access"]=access!=null&&access.UnblockedSingleAccess.HasValue?access.UnblockedSingleAccess.Value.ToString("0.00"):"none";
          o["accessEnabled"]=access!=null&&access.Enabled;
        }
        var node=b.GetComponent<MechanicalNode>();
        if(node) {
          var g=node.Graph;
          o["graph"]=g==null?"none":"generators="+g.NumberOfGenerators+" batteryCapacity="+g.BatteryCapacity+" supply="+g.PowerSupply+" demand="+g.PowerDemand+" powered="+node.Powered;
          var connectors=b.AllComponents.FirstOrDefault(x=>x.GetType().FullName=="Timberborn.MechanicalConnectorSystem.MechanicalConnectors");
          var map=connectors?.GetType().GetField("_connectors",BindingFlags.Instance|BindingFlags.NonPublic)?.GetValue(connectors) as IDictionary;
          o["connectorTarget"]=connectors!=null;
          o["transputs"]=new JArray(node.Transputs.Select(t=>Xyz(t.Coordinates)+" "+t.Direction+" -> "+Xyz(t.Target)+
            (t.Connected?" connected to "+t.ConnectedNode.Name:"")+(map!=null&&map.Contains(t)?" socket "+(((GameObject)map[t]).activeSelf?"shown":"hidden"):"")));
          o["connectedTransputs"]=node.Transputs.Count(t=>t.Connected);
        }
        var workplace=b.GetComponent<Workplace>();
        if(workplace)o["workers"]=workplace.NumberOfAssignedWorkers+"/"+workplace.DesiredWorkers;
        var blockable=b.GetComponent<BlockableObject>();
        if(blockable) {
          o["unblocked"]=blockable.IsUnblocked;
          var blockers=typeof(BlockableObject).GetField("_blockers",BindingFlags.Instance|BindingFlags.NonPublic)?.GetValue(blockable) as IEnumerable;
          o["blockers"]=new JArray(blockers==null?new[]{"unreadable"}:blockers.Cast<object>().Select(x=>x.GetType().FullName));
        }
        var depth=b.GetComponent<WaterDepthWorkCells>();
        if(depth) {
          o["depthBlocked"]=depth.IsBlockedByDepth;
          o["workCells"]=new JArray(depth.Spec.WorkCells.Select((c,i)=>{
            var r=_survey.ReadWorkCell(b.TransformCoordinates(c));
            return Xyz(r.Cell)+" "+depth.States[i]+" open="+r.HasOpenColumn+" floor="+r.Floor+" depth="+r.Depth.ToString("0.00")+" submersion="+r.Submersion.ToString("0.00");
          }));
        }
        buildings.Add(o);
        Debug.Log(Tag+" "+o.ToString(Formatting.None));
      }
      report["buildings"]=buildings;
      var outputs=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments),"TimberbornModding","outputs");
      File.WriteAllText(Path.Combine(outputs,"save-inspect-"+Path.GetFileNameWithoutExtension(save).Replace(' ','_')+".json"),report.ToString(Formatting.Indented));
      Debug.Log(Tag+" COMPLETE "+buildings.Count+" buildings reported");
    }
  }
}
#endif
