using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.EntitySystem;
using Timberborn.Goods;
using Timberborn.InventorySystem;
using Timberborn.Localization;
using Timberborn.SingletonSystem;
using Timberborn.StatusSystem;
using Timberborn.Stockpiles;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;

namespace DeepFrontier.Scripts.Radiation {
  // Stored Water becomes undrinkable ContaminatedWater when the storage is
  // irradiated: any of its occupied cells is submerged in water whose
  // radioactive share is at or above the detection limit, or the storage
  // already holds ContaminatedWater (mixed from pipes or haulers). ContaminatedWater has no consumption effects, so
  // the native InventoryNeedBehavior never offers it as a drink.
  //
  // Only unreserved Water converts; units reserved by a beaver already walking
  // to drink or haul are converted on a later pass once released. A tank whose
  // single allowed good was Water switches to ContaminatedWater once it holds
  // no Water, so haulers stop treating its contents as unwanted stock.
  public sealed class RadiationStorageService : ITickableSingleton, ILateTickable {
    private readonly EntityComponentRegistry _registry;
    private readonly RadiationSimulation _radiation;
    private readonly IDayNightCycle _dayNightCycle;
    private float _hours;

    public RadiationStorageService(EntityComponentRegistry registry, RadiationSimulation radiation, IDayNightCycle dayNightCycle) {
      _registry = registry; _radiation = radiation; _dayNightCycle = dayNightCycle;
    }

    public void Tick() {
      _hours += _dayNightCycle.FixedDeltaTimeInHours;
      if (_hours < RadiationTuning.StorageCheckIntervalHours) return;
      _hours = 0f;
      foreach (var stockpile in _registry.GetEnabled<Stockpile>()) Process(stockpile);
    }

    private void Process(Stockpile stockpile) {
      var inventory = stockpile.Inventory;
      var status = stockpile.GetComponent<IrradiatedStorageStatus>();
      if (inventory == null || status == null) return;
      bool holdsWater = inventory.AmountInStock(RadiationTuning.WaterGoodId) > 0;
      bool holdsContaminated = inventory.AmountInStock(RadiationTuning.ContaminatedWaterGoodId) > 0;
      if (holdsWater && (holdsContaminated || IsIrradiated(stockpile.GetComponent<BlockObject>()))) {
        int amount = inventory.UnreservedAmountInStock(RadiationTuning.WaterGoodId);
        if (amount > 0) {
          inventory.TakeExisting(new GoodAmount(RadiationTuning.WaterGoodId, amount));
          inventory.GiveExistingIgnoringCapacity(new GoodAmount(RadiationTuning.ContaminatedWaterGoodId, amount));
          holdsContaminated = true;
        }
      }
      // Checked on every pass, not only on a pass that converted: Water that
      // was reserved during the conversion is drunk or hauled away later, and
      // the tank must then switch (SingleGoodAllower.AllowedAmount is 0 for
      // Water while other goods are stocked, so a Water tank holding only
      // ContaminatedWater would accept nothing and count it as unwanted).
      var allower = stockpile.GetComponent<SingleGoodAllower>();
      if (holdsContaminated && allower != null && allower.AllowedGood == RadiationTuning.WaterGoodId
          && inventory.AmountInStock(RadiationTuning.WaterGoodId) == 0) {
        allower.Allow(RadiationTuning.ContaminatedWaterGoodId);
      }
      status.SetActive(holdsContaminated);
    }

    private bool IsIrradiated(BlockObject block) {
      if (block == null || !block.IsFinished) return false;
      return block.PositionedBlocks.GetOccupiedCoordinates().Any(cell => {
        var sample = _radiation.Sample(cell);
        return sample.Submerged && sample.WaterRadiation >= RadiationTuning.DetectionLimit;
      });
    }
  }

  // Status shown on storage that holds irradiated water.
  internal sealed class IrradiatedStorageStatus : BaseComponent, IAwakableComponent, IInitializableEntity {
    private readonly ILoc _loc;
    private StatusToggle _status;

    public IrradiatedStorageStatus(ILoc loc) { _loc = loc; }

    public void Awake() {
      _status = StatusToggle.CreateNormalStatusWithFloatingIcon(RadiationSprites.StorageIrradiated, _loc.T(RadiationLoc.StorageIrradiated));
    }

    public void InitializeEntity() => GetComponent<StatusSubject>().RegisterStatus(_status);

    public void SetActive(bool active) {
      if (active == _status.IsActive) return;
      if (active) _status.Activate(); else _status.Deactivate();
    }
  }
}
