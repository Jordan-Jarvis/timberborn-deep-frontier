using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.BlueprintSystem;
using Timberborn.MechanicalSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.Workshops;

namespace DeepFrontier.Scripts {
  internal record WorkshopPoweredGeneratorSpec : ComponentSpec { }

  // Optional component on the same building that scales the full output
  // (0..1): the reactor's core heat (Meltdown/ReactorCore).
  internal interface IGeneratorOutputFactor {
    float OutputFactor { get; }
  }

  // Recipe inventories and progress stay native; this component only connects
  // productive workshop activity to the native mechanical network's output.
  //
  // Pilot output (all-buildings test, build 154/155): these plants clone the vanilla Smelter and
  // keep its MechanicalBuildingSpec (it lists them in the native Power batch-control tab). Native
  // ProduceExecutor.Launch (Timberborn 1.1.2.8) refuses to start production while
  // MechanicalBuilding.ActiveAndPowered is false, i.e. while the graph has no supply; with output
  // gated on production, a plant whose graph carries any demand and no other generator could never
  // start (the Oil plant with a charging station never ran). While the plant is staffed and its
  // recipe is ready, it therefore offers PilotOutputHp so the graph counts as supplied and the
  // worker can start; full output follows as soon as it works.
  internal sealed class WorkshopPoweredGenerator : TickableComponent,
      IAwakableComponent, IFinishedStateListener {
    private MechanicalNode _node;
    private Workshop _workshop;
    private Manufactory _manufactory;
    private Timberborn.WorkSystem.Workplace _workplace;
    private IGeneratorOutputFactor _factor;
    private float _pilot;
    private const int PilotOutputHp = 1;

    public void Awake() {
      _node = GetComponent<MechanicalNode>();
      _workshop = GetComponent<Workshop>();
      _manufactory = GetComponent<Manufactory>();
      _workplace = GetComponent<Timberborn.WorkSystem.Workplace>();
      _factor = GetComponent<IGeneratorOutputFactor>();
      int nominal = GetComponent<MechanicalNodeSpec>().PowerOutput;
      if (nominal <= 0 || !_workplace) throw new System.InvalidOperationException($"{Name}: WorkshopPoweredGenerator needs a positive PowerOutput and the native Workplace");
      _pilot = (float)PilotOutputHp / nominal;
      DisableComponent();
    }

    public void OnEnterFinishedState() {
      _node.SetOutputMultiplier(0f);
      EnableComponent();
    }

    public void OnExitFinishedState() {
      _node.SetOutputMultiplier(0f);
      DisableComponent();
    }

    public override void Tick() {
      bool ready = _manufactory.IsReadyToProduce;
      _node.SetOutputMultiplier(_workshop.CurrentlyWorking && ready ? (_factor != null ? _factor.OutputFactor : 1f)
          : ready && _workplace.NumberOfAssignedWorkers > 0 ? _pilot : 0f);
    }
  }

  [Context("Game")]
  public sealed class WorkshopPoweredGeneratorConfigurator : Configurator {
    protected override void Configure() {
      Bind<WorkshopPoweredGenerator>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(ProvideTemplateModule).AsSingleton();
    }

    private static TemplateModule ProvideTemplateModule() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<WorkshopPoweredGeneratorSpec, WorkshopPoweredGenerator>();
      return builder.Build();
    }
  }
}
