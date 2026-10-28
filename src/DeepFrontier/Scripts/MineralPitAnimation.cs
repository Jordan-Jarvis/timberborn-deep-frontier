using System;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.Common;
using Timberborn.InventorySystem;
using Timberborn.SimpleOutputBuildings;
using Timberborn.SingletonSystem;
using Timberborn.TickSystem;
using Timberborn.TimbermeshAnimations;
using Timberborn.TimeSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  internal record MineralPitAnimationSpec : ComponentSpec {}

  // Cosmetic hand-hoist cycle after real harvested stone reaches the native
  // output inventory. Gathering, quantities and reservations stay native.
  internal sealed class MineralPitAnimation : TickableComponent,
      IAwakableComponent, IFinishedStateListener {
    private readonly NonlinearAnimationManager _animation;
    private readonly EventBus _events;
    private Inventory _inventory;
    private IAnimator _animator;
    private PausableBuilding _pausable;
    private string _good;
    private bool _active;
    public bool IsCycling=>_active&&_animator.Enabled;
    public int DeliveryCyclesStarted { get; private set; }

    public MineralPitAnimation(NonlinearAnimationManager animation,EventBus events) {
      _animation=animation;_events=events;
    }
    public void Awake() {
      _good=GetComponent<MineralPitSpec>().GoodId;
      _pausable=GetComponent<PausableBuilding>();
      DisableComponent();
    }
    public void OnEnterFinishedState() {
      var finished=GameObject.FindChildIfNameNotEmpty(GetComponent<BuildingModelSpec>().FinishedModelName);
      _animator=finished.GetComponentsInChildren<MonoBehaviour>(true).OfType<IAnimator>().Single();
      _animator.Play("Default",false);_animator.SetTime(0);_animator.Enabled=false;
      _inventory=GetComponent<SimpleOutputInventory>().Inventory;
      _inventory.InventoryStockChanged+=OnStockChanged;
      _events.Register(this);
      EnableComponent();
    }
    public void OnExitFinishedState() {
      _inventory.InventoryStockChanged-=OnStockChanged;
      _events.Unregister(this);_active=false;_animator.Enabled=false;
      DisableComponent();
    }
    private void OnStockChanged(object sender,InventoryStockChangedEventArgs args) {
      if(args.GoodAmount.GoodId!=_good||args.GoodAmount.Amount<=0||_active)return;
      _animator.Play("Default",false);_animator.SetTime(0);_active=true;
      DeliveryCyclesStarted++;Refresh();
    }
    public override void Tick() {
      if(_active&&_animator.PlayingFinished)_active=false;
      Refresh();
    }
    [OnEvent] public void OnSpeedChanged(CurrentSpeedChangedEvent args)=>Refresh();
    private void Refresh() {
      _animator.Enabled=_active&&!_pausable.Paused;
      _animator.Speed=_animation.SpeedMultiplier;
    }
  }
}
