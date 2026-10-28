using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using Bindito.Core;
using Newtonsoft.Json;
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
using Timberborn.Goods;
using Timberborn.Navigation;
using Timberborn.NeedSystem;
using Timberborn.SingletonSystem;
using Timberborn.Stockpiles;
using Timberborn.TimeSystem;
using Timberborn.WorkSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class GroceryContinuityAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierGroceryReload"))
        Bind<GroceryContinuityAcceptance>().AsSingleton();
    }
  }
  [Serializable] internal sealed class GroceryReloadRecord {
    public string EntityId;
    public GroceryStockRecord[] Stocks;
    public HospitalPatientRecord[] Residents;
  }
  [Serializable] internal sealed class GroceryStockRecord {
    public string Name;
    public int Amount;
  }
  internal sealed class GroceryContinuityAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private readonly EntityRegistry _entities; private readonly SpeedManager _speed;
    private readonly IDayNightCycle _clock; private readonly WorkingHoursManager _hours;
    private readonly INavigationService _navigation; private readonly INavMeshService _nav;
    private readonly GameSaver _saver; private readonly GameLoader _loader; private readonly IGoodService _goods;
    private GroceryStore _shop; private BlockObject _building; private ControllableCharacter _shopper; private NeedManager _needs;
    private int _frame,_phase,_stockBefore; private float _start,_phaseTime,_normalHours,_hungerBefore;
    private bool _finished,_entered; private Vector3 _target;
    public GroceryContinuityAcceptance(EntityRegistry entities,SpeedManager speed,IDayNightCycle clock,
      WorkingHoursManager hours,INavigationService navigation,INavMeshService nav,GameSaver saver,GameLoader loader,IGoodService goods) {
      _entities=entities;_speed=speed;_clock=clock;_hours=hours;_navigation=navigation;_nav=nav;_saver=saver;_loader=loader;_goods=goods;
    }
    private static void Require(bool value,string message) {if(!value)throw new InvalidOperationException(message);}
    private static void Pass(string message) {Debug.Log("[DeepFrontier Grocery Reload] PASS "+message);}
    private void Phase(int phase) {_phase=phase;_phaseTime=_clock.PartialDayNumber;}
    private static void SetNeed(NeedManager n,string id,float points) {n.ApplyEffect(new InstantEffect(id,points-n.GetNeedPoints(id),1));}
    public void PostLoad() {
      Require(_entities.Entities.Any(e=>e.HasComponent<NamedEntity>()&&e.GetComponent<NamedEntity>().EntityName=="Deep Frontier Acceptance Fixture"),
        "Grocery continuity requires the marked disposable settlement");
    }
    private void Setup() {
      _speed.ChangeSpeed(0);
      var saved=JsonConvert.DeserializeObject<GroceryReloadRecord>(File.ReadAllText(
        "C:/Users/Jordan/Documents/TimberbornModding/outputs/grocery-reload-expectations.json"));
      Require(saved!=null&&saved.Stocks!=null&&saved.Residents!=null,"Missing exact grocery save expectations");
      _shop=_entities.Entities.Single(e=>e.HasComponent<GroceryStore>()).GetComponent<GroceryStore>();
      _building=_shop.GetComponent<BlockObject>();
      Require(_shop.GetComponent<EntityComponent>().EntityId.ToString()==saved.EntityId,"Saved grocery identity changed");
      Require(_building.GetComponent<PausableBuilding>().Paused,"Expected paused saved grocery");
      Require(_shop.Inventory.Enabled&&_shop.Inventory.PublicInput&&!_shop.Inventory.PublicOutput&&_shop.Inventory.IsOutput,
        "Saved grocery changed its native food-access contract");
      Require(_shop.Inventory.TotalAmountInStock==saved.Stocks.Sum(g=>g.Amount),"Saved total grocery stock differs");
      foreach(var g in saved.Stocks)Require(_shop.Inventory.AmountInStock(g.Name)==g.Amount,"Saved food differs: "+g.Name);
      foreach(var resident in saved.Residents) {
        var n=_entities.Entities.Single(e=>e.EntityId.ToString()==resident.EntityId).GetComponent<NeedManager>();
        foreach(var need in resident.Needs)Require(Math.Abs(n.GetNeedPoints(need.Name)-need.Points)<.0001f,"Saved neighborhood points differ");
      }
      // Grocery Market access (GroceryAcceptance.MarketPaths/BalconyPaths): the saved door
      // approach, stair foot and balcony deck paths must reconnect after the reload.
      GroceryAcceptance.RequireMarketAccess(_building,_nav);
      Pass("fresh-process identity, pause, exact food stocks, consumer permissions, resident needs and connected door and balcony paths");
      var workers=_entities.Entities.Where(e=>e.HasComponent<Worker>()).Select(e=>e.GetComponent<Worker>())
        .Where(w=>w.WorkerType=="Beaver").ToArray();
      Require(workers.Length>=3,"Need two clerks and one test shopper");
      foreach(var w in workers) {
        w.Unemploy();var n=w.GetComponent<NeedManager>();
        foreach(var id in new[]{"Hunger","Thirst","Sleep"})SetNeed(n,id,n.GetNeedSpec(id).MaximumValue);
        foreach(var effect in _shop.GetComponent<GroceryStoreSpec>().Foods.SelectMany(id=>_goods.GetGood(id).ConsumptionEffects))
          SetNeed(n,effect.NeedId,n.GetNeedSpec(effect.NeedId).MaximumValue);
      }
      _shopper=workers[2].GetComponent<ControllableCharacter>();_needs=_shopper.GetComponent<NeedManager>();
      Require(_shopper.GetAnimationNames().Contains("BeaverAdult_idle"),"Missing adult idle animation");
      _shopper.ChangeAnimation("BeaverAdult_idle");
      _target=NavigationCoordinateSystem.GridToWorld(new Vector3Int(163,159,3));
      Require(_navigation.FindPathUnlimitedRange(_shopper.Transform.position,_target,new List<PathCorner>(),out var distance),"No saved shopper route");
      _shopper.TakeControlAndMoveTo(CoordinateSystem.WorldToGrid(_target));
      _normalHours=_hours.WorkedPartOfDay;_hours.WorkedPartOfDay=1;
      _building.GetComponent<PausableBuilding>().Resume();
      foreach(var w in workers.Take(2))w.EmployAt(_shop.GetComponent<Workplace>());
      _start=_clock.PartialDayNumber;Phase(1);_speed.ChangeSpeed(3);
    }
    public void UpdateSingleton() {
      if(_finished)return;
      try {
        if(++_frame==60)Setup();if(_frame<=60)return;
        float hours=(_clock.PartialDayNumber-_phaseTime)*24;
        if(_frame%600==0)Debug.Log($"[DeepFrontier Grocery Reload] STATUS phase={_phase}, staff={_shop.AttendingStaff}, stock={_shop.Inventory.TotalAmountInStock}, area={_shop.ProvidesNeighborhoodService}");
        if(_phase==1&&_shop.ProvidesNeighborhoodService&&Vector3.Distance(_shopper.Transform.position,_target)<.18f) {
          Pass("saved stock resumes staffed neighborhood service");
          SetNeed(_needs,"NeighborhoodGroceries",0);Phase(2);
        } else if(_phase==2&&hours>=.6f) {
          Require(_needs.GetNeedPoints("NeighborhoodGroceries")>.06f,"Reloaded service grants no real neighborhood points");
          Pass("reloaded neighborhood need grows on an actual nearby resident");
          _hours.WorkedPartOfDay=0;Phase(3);
        } else if(_phase==3&&hours>=.6f) {
          Require(_shop.AttendingStaff==0&&!_shop.ProvidesNeighborhoodService&&_shop.Inventory.Enabled,
            "Off-duty store must retain food access without staffed service");
          foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Stockpile>()))e.GetComponent<Stockpile>().Inventory.Disable();
          SetNeed(_needs,"Hunger",.3f);_hungerBefore=_needs.GetNeedPoints("Hunger");
          _stockBefore=_shop.Inventory.TotalAmountInStock;Require(_stockBefore>0,"No saved food to buy");
          _shopper.ReleaseControl();Phase(4);
          Pass("off-duty clerks stop neighborhood service while native food remains accessible");
        } else if(_phase==4) {
          if(_shopper.GetComponent<Enterer>().CurrentBuilding==_building.GetComponent<Enterable>())_entered=true;
          if(_shop.Inventory.TotalAmountInStock<_stockBefore&&_needs.GetNeedPoints("Hunger")>_hungerBefore+.2f) {
            Require(_entered,"Shopper food gain had no observed store entry");
            Pass("actual shopper ate saved food through the native consumer behavior while clerks were off duty");
            foreach(var e in _entities.Entities.Where(e=>e.HasComponent<Stockpile>()))e.GetComponent<Stockpile>().Inventory.Enable();
            _building.GetComponent<PausableBuilding>().Pause();_hours.WorkedPartOfDay=_normalHours;
            _speed.ChangeSpeed(0);_finished=true;
            _saver.QueueSave(new SaveReference("Grocery continuity - verified",_loader.LoadedSave.SettlementReference),
              ()=>Debug.Log("[DeepFrontier Grocery Reload] ALL RELOAD, SERVICE AND OFF-DUTY SHOPPING CHECKS PASSED AND SAVED"));
          }
        }
        Require(_clock.PartialDayNumber-_start<2,"Grocery continuity exceeded two simulation days");
      } catch(Exception e) {_finished=true;_speed.ChangeSpeed(0);Debug.LogError("[DeepFrontier Grocery Reload] FAILED: "+e);}
    }
  }
}
