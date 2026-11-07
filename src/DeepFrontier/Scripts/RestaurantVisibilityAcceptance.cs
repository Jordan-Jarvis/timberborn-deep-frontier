#if !UNITY_EDITOR
using System;
using System.IO;
using System.Linq;
using Bindito.Core;
using Timberborn.Buildings;
using Timberborn.BuildingsUI;
using Timberborn.Debugging;
using Timberborn.EnterableSystem;
using Timberborn.EntitySystem;
using Timberborn.SingletonSystem;
using Timberborn.SlotSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  [Context("Game")]
  public sealed class RestaurantVisibilityAcceptanceConfigurator : Configurator {
    protected override void Configure() {
      if(Environment.GetCommandLineArgs().Contains("-deepFrontierRestaurantVisibilityAcceptance"))
        Bind<RestaurantVisibilityAcceptance>().AsSingleton();
    }
  }

  // Replays the actual native debug command on an explicitly named disposable
  // copy of the crash report's starting save. Never saves the test mutations.
  internal sealed class RestaurantVisibilityAcceptance : IPostLoadableSingleton,IUpdatableSingleton {
    private const string Tag="[DeepFrontier RestaurantVisibility] ";
    private readonly EntityRegistry _entities;
    private readonly EntityComponentRegistry _components;
    private readonly TransformSlotFactory _factory;
    private Restaurant _restaurant;
    private DevMethod _toggle;
    private int _frame,_arrivals,_chargingArrivals,_mealsAtHide;
    private Enterable[] _chargers;
    private float _hiddenAt;
    private bool _restored;
    public RestaurantVisibilityAcceptance(EntityRegistry entities,EntityComponentRegistry components,TransformSlotFactory factory) {
      _entities=entities;_components=components;_factory=factory;
    }
    private static void Require(bool value,string message) {
      if(!value)throw new InvalidOperationException(Tag+message);
    }
    public void PostLoad() {
      Require(Path.GetFileName(MemoryLoadProbe.SavePath())=="restaurant-visibility-repro-copy.timber",
        "Requires the explicitly named disposable restaurant save");
      Require(!Environment.GetCommandLineArgs().Contains(MemoryLoadProbe.SaveAsFlag),"Test must not save mutations");
    }
    public void UpdateSingleton() {
      if(++_frame<60 || _restored)return;
      if(_frame==60) {
        _restaurant=_entities.Entities.Select(e=>e.GetComponent<Restaurant>()).Single(r=>r);
        var seats=_restaurant.GetComponent<RestaurantSeats>();
        var manager=_restaurant.GetComponent<SlotManager>();
        var visitors=_restaurant.Visitors;
        Require(_restaurant.Enabled&&manager.SlotsCount==_restaurant.Spec.Seats.Length,"Finished restaurant seats did not load");
        var diner=seats.SeatedDiners.First(d=>d.Served);
        var entered=diner.GetComponent<Enterer>();
        float servedAt=diner.ServedAt;
        int count=visitors.NumberOfEnterersInside;
        var transform=seats.SeatTransform(_restaurant.Spec.Seats[0].Name);
        var native=_factory.Create(transform,new TransformSlotSpec {
          SlotKeyword="Seat",Animation="Sitting",Inanimate=false,RandomizeYRotation=false,WaterSlot=false });
        _toggle=new BuildingsModelToggler(_components).GetDefinition().Methods.Single();
        Require(native.IsAvailable,"Expected visible models at test start");
        var model=_restaurant.GetComponent<BuildingModel>().FinishedModel;
        model.SetActive(false);
        Require(!native.IsAvailable,"Negative control: original SetActive must disable native seat availability");
        model.SetActive(true);
        var renderers=model.GetComponentsInChildren<Renderer>(true);
        var renderState=renderers.Select(r=>r.forceRenderingOff).ToArray();
        Require(renderers.Length>0,"No restaurant renderers to hide");
        for(int cycle=0;cycle<3;cycle++) {
          _toggle.Invoke();
          Require(native.IsAvailable&&model.activeSelf,"Debug command disabled native restaurant slots");
          Require(renderers.All(r=>r.forceRenderingOff),"Debug command did not hide restaurant renderers");
          entered.Exit();diner.BeginVisit(_restaurant);entered.Enter(visitors);diner.MarkServed(servedAt);
          Require(entered.CurrentBuilding==visitors&&visitors.NumberOfEnterersInside==count,"Hidden native re-entry changed occupancy");
          Require(seats.SeatedDiners.Count()==count&&seats.SeatedDiners.Distinct().Count()==count,"Missing or duplicate seat assignment");
          Require(seats.DinerAt(seats.SeatOf(diner))==diner,"Re-entering diner has no native seat");
          _toggle.Invoke();
          Require(native.IsAvailable&&manager.SlotsCount==_restaurant.Spec.Seats.Length,"Show changed capacity or seat transform");
          Require(renderers.Select(r=>r.forceRenderingOff).SequenceEqual(renderState),"Show did not restore original rendering state");
        }
        Debug.Log(Tag+"PASS three native hide/show cycles, hidden entry/exit, unique seats, unchanged capacity and restored rendering; original SetActive fails availability control");
        _toggle.Invoke();
        _mealsAtHide=_restaurant.MealsServedThisSession;
        visitors.EntererAdded+=OnArrival;
        _chargers=_entities.Entities.Where(e=>e.Name.StartsWith("ChargingStation.IronTeeth",StringComparison.Ordinal))
          .Select(e=>e.GetComponent<Enterable>()).Where(e=>e).ToArray();
        Require(_chargers.Length>0,"No native charging stations in test save");
        foreach(var charger in _chargers)charger.EntererAdded+=OnChargingArrival;
        _hiddenAt=Time.unscaledTime;
      }
      if(Time.unscaledTime-_hiddenAt<60f)return;
      _restaurant.Visitors.EntererAdded-=OnArrival;
      foreach(var charger in _chargers)charger.EntererAdded-=OnChargingArrival;
      _toggle.Invoke();_restored=true;
      Require(_restaurant.GetComponent<BuildingModel>().FinishedModel.activeSelf,"Models not restored");
      Require(_arrivals>0,"No naturally walking guests arrived during hidden simulation");
      Require(_chargingArrivals>0,"No bots entered charging stations during hidden simulation");
      Require(_restaurant.MealsServedThisSession>_mealsAtHide,"No meals served during hidden simulation");
      Debug.Log(Tag+$"COMPLETE native debug toggle, hidden guest entry and service passed; {_arrivals} natural arrivals, {_chargingArrivals} charging arrivals, {_restaurant.MealsServedThisSession-_mealsAtHide} meals while hidden; models restored; no save written");
    }
    private void OnArrival(object sender,EntererAddedEventArgs args) { _arrivals++; }
    private void OnChargingArrival(object sender,EntererAddedEventArgs args) { _chargingArrivals++; }
  }
}
#endif
