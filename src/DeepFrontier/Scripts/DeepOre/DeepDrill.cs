using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Buildings;
using Timberborn.EntitySystem;
using Timberborn.GameDistricts;
using Timberborn.Localization;
using Timberborn.Persistence;
using Timberborn.StatusSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.Workshops;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts.DeepOre {
  // The Deep Drill's draw on the Deep Ore Sources of its district (docs/source-authoring.md). Its
  // recipe turns water into deep ore (Recipe.DeepOre: 3 Water -> 1 DeepOre); each cycle's ore comes
  // out of a deposit, as each cycle of the native Dirt Excavator takes a terrain voxel
  // (Timberborn.Terraforming.Drill on Manufactory.ProductionFinished) and a native water pump draws
  // its water from the world (WaterInputManufactoryLimiter).
  //
  // As a native IManufactoryLimiter (Manufactory collects them in Awake):
  // - MaxProductionProgressChange takes the cycle's units from a deposit before the cycle's first
  //   progress, as the Manufactory takes its ingredients then, and keeps them (saved) until the cycle
  //   finishes; 0 when no deposit can give them, so no progress is made without ore;
  // - ProductionEfficiency is 0 while no cycle ore is held and no deposit of the district holds
  //   enough, so Manufactory.IsReadyToProduce is false and the workers stop.
  // The deposit is the district's nearest by road, as the native DistrictInventoryPicker picks the
  // closest inventory with stock (Accessible.FindRoadPath); between equally near ones, the one
  // holding most. Statuses: every deposit of the district is empty and recharging; or there is none.
  internal record DeepDrillSpec : ComponentSpec {
    // The good it bores out of Deep Ore Sources (DeepOreDepositSpec.GoodId); each cycle takes the
    // recipe's product amount of it.
    [Serialize] public string GoodId { get; init; }
  }

  internal static class DeepOreLoc {
    public const string StatusRecharging = "DeepFrontier.DeepDrill.Status.Recharging";
    public const string StatusNoSource = "DeepFrontier.DeepDrill.Status.NoSource";
    public const string StatusNoSourceShort = "DeepFrontier.DeepDrill.Status.NoSource.Short";
    public const string PanelDistrictOre = "DeepFrontier.DeepDrill.Panel.DistrictOre";
    public const string PanelNoSource = "DeepFrontier.DeepDrill.Panel.NoSource";
    public const string RechargeNext = "DeepFrontier.DeepOre.Recharge.Next";
    public const string RechargeRule = "DeepFrontier.DeepOre.Recharge.Rule";
  }

  internal sealed class DeepDrill : TickableComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener,
      IPersistentEntity, IManufactoryLimiter {
    private static readonly ComponentKey Key = new("DeepFrontier.DeepDrill");
    private static readonly PropertyKey<bool> CycleOreKey = new("CycleOreDrawn");
    private const float SameDistance = 0.01f;
    private readonly EntityComponentRegistry _registry;
    private readonly ILoc _loc;
    private DeepDrillSpec _spec;
    private Manufactory _manufactory;
    private DistrictBuilding _districtBuilding;
    private BuildingAccessible _accessible;
    private BlockableObject _blockable;
    private BlockObject _blockObject;
    private StatusToggle _rechargingStatus, _noSourceStatus;
    private bool _finished;
    // Saved before 2026-11-03 (no DeepDrill component): resolved in InitializeEntity, after the
    // Manufactory loaded its progress.
    private bool _savedBeforeDeposits;

    public DeepDrill(EntityComponentRegistry registry, ILoc loc) { _registry = registry; _loc = loc; }

    public DeepDrillSpec Spec => _spec;
    // The current cycle's units are already out of a deposit.
    public bool CycleOreDrawn { get; private set; }
    public bool HasDistrict => _districtBuilding.District;

    public void Awake() {
      _spec = GetComponent<DeepDrillSpec>();
      if (string.IsNullOrEmpty(_spec.GoodId)) throw new InvalidOperationException($"{Name}: DeepDrillSpec needs a GoodId");
      _manufactory = GetComponent<Manufactory>();
      _districtBuilding = GetComponent<DistrictBuilding>();
      _accessible = GetComponent<BuildingAccessible>();
      _blockable = GetComponent<BlockableObject>();
      _blockObject = GetComponent<BlockObject>();
      if (!_manufactory || !_districtBuilding || !_accessible || !_blockable || !_blockObject)
        throw new InvalidOperationException($"{Name}: a Deep Drill needs a native Manufactory, BuildingAccessible (DistrictBuilding), BlockableObject and BlockObject");
      DisableComponent();
    }

    public void InitializeEntity() {
      foreach (var recipe in _manufactory.ProductionRecipes) {
        if (recipe.Ingredients.Any(i => i.Id == _spec.GoodId) || recipe.Products.Count(p => p.Id == _spec.GoodId && p.Amount > 0) != 1)
          throw new InvalidOperationException($"{Name}: recipe {recipe.Id} must produce {_spec.GoodId} and not consume it; the deposit supplies it");
      }
      // The old recipe took its DeepOre (hauled from the source) at the cycle's first progress.
      if (_savedBeforeDeposits) CycleOreDrawn = _manufactory.ProductionProgress > 0f;
      _manufactory.ProductionFinished += OnProductionFinished;
      if (_blockObject.IsPreview) return;
      _rechargingStatus = StatusToggle.CreateNormalStatusWithFloatingIcon("Empty", _loc.T(DeepOreLoc.StatusRecharging));
      _noSourceStatus = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon("NothingToDo",
        _loc.T(DeepOreLoc.StatusNoSource), _loc.T(DeepOreLoc.StatusNoSourceShort));
      var subject = GetComponent<StatusSubject>();
      subject.RegisterStatus(_rechargingStatus);
      subject.RegisterStatus(_noSourceStatus);
    }

    public void OnEnterFinishedState() { _finished = true; EnableComponent(); Tick(); }

    public void OnExitFinishedState() {
      _finished = false;
      _rechargingStatus?.Deactivate();
      _noSourceStatus?.Deactivate();
      DisableComponent();
    }

    public void Save(IEntitySaver entitySaver) {
      entitySaver.GetComponent(Key).Set(CycleOreKey, CycleOreDrawn);
    }

    public void Load(IEntityLoader entityLoader) {
      if (entityLoader.TryGetComponent(Key, out var loader)) CycleOreDrawn = loader.Get(CycleOreKey);
      else _savedBeforeDeposits = true;
    }

    // Deposits of this drill's district holding its good (none while it has no district).
    public IEnumerable<DeepOreDeposit> Deposits() {
      var district = _districtBuilding.District;
      if (!district) yield break;
      foreach (var deposit in _registry.GetEnabled<DeepOreDeposit>())
        if (deposit.Spec.GoodId == _spec.GoodId && deposit.District == district) yield return deposit;
    }

    public int UnitsPerCycle => _manufactory.CurrentRecipe.Products.Single(p => p.Id == _spec.GoodId).Amount;

    private bool DistrictHasOre() {
      int units = UnitsPerCycle;
      foreach (var deposit in Deposits()) if (deposit.Amount >= units) return true;
      return false;
    }

    public float ProductionEfficiency() => CycleOreDrawn || DistrictHasOre() ? 1f : 0f;

    public float MaxProductionProgressChange(float expectedProductionProgressChange) {
      if (CycleOreDrawn) return expectedProductionProgressChange;
      var deposit = NearestWithOre(UnitsPerCycle);
      if (!deposit || !deposit.TryTake(UnitsPerCycle)) return 0f;
      CycleOreDrawn = true;
      return expectedProductionProgressChange;
    }

    private DeepOreDeposit NearestWithOre(int units) {
      DeepOreDeposit best = null;
      float bestDistance = float.MaxValue;
      var start = _accessible.Accessible;
      foreach (var deposit in Deposits()) {
        if (deposit.Amount < units || !start.FindRoadPath(deposit.Accessible.Accessible, out float distance)) continue;
        if (!best || distance < bestDistance - SameDistance || (distance <= bestDistance + SameDistance && deposit.Amount > best.Amount)) {
          best = deposit;
          bestDistance = distance;
        }
      }
      return best;
    }

    private void OnProductionFinished(object sender, EventArgs e) {
      CycleOreDrawn = false;
    }

    public override void Tick() {
      bool waiting = _finished && _blockable.IsUnblocked && _manufactory.HasCurrentRecipe && HasDistrict && !CycleOreDrawn && !DistrictHasOre();
      bool anyDeposit = waiting && Deposits().Any();
      if (waiting && anyDeposit) _rechargingStatus.Activate(); else _rechargingStatus.Deactivate();
      if (waiting && !anyDeposit) _noSourceStatus.Activate(); else _noSourceStatus.Deactivate();
    }
  }

  [Context("Game")]
  public sealed class DeepDrillConfigurator : Configurator {
    protected override void Configure() {
      Bind<DeepDrill>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<DeepDrillSpec, DeepDrill>();
      return builder.Build();
    }
  }
}
