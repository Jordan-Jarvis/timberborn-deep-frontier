using Timberborn.BaseComponentSystem;
using Timberborn.BlockSystem;
using Timberborn.EntitySystem;
using Timberborn.MechanicalSystem;
using Timberborn.WorkSystem;

namespace DeepFrontier.Scripts {
  // Finished Mission Control buildings are enumerated through the native
  // EntityComponentRegistry. "Operating" means flight control is actually
  // manned: finished, unblocked (not paused or automation-blocked), on a
  // powered grid and with at least one assigned worker.
  internal sealed class RocketMissionControl : BaseComponent, IAwakableComponent,
      IFinishedStateListener, IRegisteredComponent {
    private MechanicalNode _power;
    private Workplace _workplace;

    public bool IsOperating=>Enabled&&_power.ActiveAndPowered&&_workplace.NumberOfAssignedWorkers>0;

    public void Awake() {
      _power=GetComponent<MechanicalNode>();_workplace=GetComponent<Workplace>();
      if(!_power||!_workplace)
        throw new System.InvalidOperationException("Mission Control requires a powered workplace");
      DisableComponent();
    }
    public void OnEnterFinishedState()=>EnableComponent();
    public void OnExitFinishedState()=>DisableComponent();
  }
}
