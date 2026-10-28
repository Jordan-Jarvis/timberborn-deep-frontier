using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.EntitySystem;
using Timberborn.Yielding;

namespace DeepFrontier.Scripts {
  // The native Yielder owns quantities, reservations, extraction time and saving.
  internal record MineralDepositSpec : ComponentSpec, IYielderDecorable, IOrderableYielder {
    [Serialize] public YielderSpec Yielder { get; init; }
    public bool PersistYield => true;
    public int Order => 0;
  }

  internal sealed class MineralDeposit : BaseComponent, IAwakableComponent, IInitializableEntity {
    private readonly EntityService _entityService;
    public Yielder Yielder { get; private set; }

    public MineralDeposit(EntityService entityService) { _entityService = entityService; }

    public void Awake() {
      Yielder = GetComponent<Yielder>();
    }

    public void InitializeEntity() {
      Yielder.Enable();
      Yielder.YieldDecreased += OnYieldDecreased;
    }

    private void OnYieldDecreased(object sender, System.EventArgs args) {
      if (Yielder.IsYieldRemoved) _entityService.Delete(this);
    }
  }

  internal record MineralPitSpec : ComponentSpec {
    [Serialize] public string GoodId { get; init; }
  }

  internal sealed class MineralYielderRetriever : BaseComponent, IYielderRetriever {
    public bool TryGetYielder(BaseComponent component, out Yielder yielder) {
      var deposit = component.GetComponent<MineralDeposit>();
      if (deposit != null && deposit.Yielder.YielderSpec.Yield.Id == GetComponent<MineralPitSpec>().GoodId) {
        yielder = deposit.Yielder;
        return true;
      }
      yielder = null;
      return false;
    }
  }
}
