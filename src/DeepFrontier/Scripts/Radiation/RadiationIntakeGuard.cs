using System.Collections.Generic;
using Timberborn.BaseComponentSystem;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.EntitySystem;
using Timberborn.Localization;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.WaterBuildings;

namespace DeepFrontier.Scripts.Radiation {
  // Decorated onto every native WaterInput (water and badwater pumps,
  // mechanical pumps, showers). Unlike badwater, which native pumps filter,
  // any radioactive share at or above the detection limit in the intake's
  // column blocks the building through the native BlockableObject: workshops
  // stop, WaterMover stops and the building shows "Radiation detected". It
  // resumes below the clear limit. The sludge recovery pump is meant to pump
  // radioactive water, so the guard stays inert there. The entity panel shows
  // the intake water's fresh / bad / radioactive shares.
  internal sealed class RadiationIntakeGuard : TickableComponent, IAwakableComponent, IInitializableEntity, IFinishedStateListener,
      IEntityDescriber {
    private const int DescriptionOrder = 130;
    private readonly RadiationSimulation _radiation;
    private readonly ILoc _loc;
    private WaterInput _waterInput;
    private BlockableObject _blockable;
    private StatusToggle _status;
    private bool _inert, _blocked, _finished;

    public bool IsBlockedByRadiation => _blocked;

    public RadiationIntakeGuard(RadiationSimulation radiation, ILoc loc) { _radiation = radiation; _loc = loc; }

    public void Awake() {
      _inert = GetComponent<RadioactiveSludgeIntake>() != null;
      _waterInput = GetComponent<WaterInput>();
      _blockable = GetComponent<BlockableObject>();
      if (!_inert && _blockable == null)
        throw new System.InvalidOperationException("RadiationIntakeGuard requires the native BlockableObject on water intake buildings");
      _status = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon(RadiationSprites.PumpBlocked,
        _loc.T(RadiationLoc.PumpBlocked), _loc.T(RadiationLoc.PumpBlockedShort));
      DisableComponent();
    }

    public void InitializeEntity() {
      if (!_inert) GetComponent<StatusSubject>().RegisterStatus(_status);
    }

    public void OnEnterFinishedState() {
      _finished = true;
      if (_inert) return;
      EnableComponent();
      Evaluate();
    }

    public void OnExitFinishedState() {
      _finished = false;
      DisableComponent();
      SetBlocked(false);
    }

    public override void Tick() => Evaluate();

    private void Evaluate() {
      float radiation = _radiation.ColumnRadiation(_waterInput.Coordinates);
      // One threshold, no hysteresis: below DetectionLimit the share reads 0
      // (RadiationTuning.Detected) and the late tick removes it once it stops rising.
      SetBlocked(radiation >= RadiationTuning.DetectionLimit);
    }

    private void SetBlocked(bool blocked) {
      if (blocked == _blocked) return;
      _blocked = blocked;
      if (blocked) { _blockable.Block(this); _status.Activate(); }
      else { _blockable.Unblock(this); _status.Deactivate(); }
    }

    public IEnumerable<EntityDescription> DescribeEntity() {
      if (!_finished) yield break;
      var sample = _radiation.Sample(_waterInput.Coordinates);
      if (!sample.HasColumn || !sample.Submerged) yield break;
      yield return EntityDescription.CreateTextSection(_loc.T(RadiationLoc.WaterShares,
        Percent(sample.FreshShare), Percent(sample.BadwaterShare), Percent(sample.WaterRadiation)), DescriptionOrder);
    }

    private static string Percent(float share) => (share * 100f).ToString("0.#");
  }
}
