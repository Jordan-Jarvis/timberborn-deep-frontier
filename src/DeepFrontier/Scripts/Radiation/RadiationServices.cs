using Timberborn.WaterSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Services the radiation buildings use besides IRadiationService (and the
  // public IIrradiatedGround and IRadiationWaterCells in IRadiationService.cs).
  // Consumers inject these instead of the concrete RadiationSimulation, so the
  // Moddable Fluids build (DEEP_FRONTIER_MODDABLE_FLUIDS) can serve them from
  // its facade. RadiationSimulation implements each one by forwarding to the
  // method its consumers called before.

  // Sludge recovery intakes: the radioactive volume their pumping actually
  // removed at the intake cell is credited to them once per tick
  // (RadioactiveSludgeIntake.OnRadioactiveRemoved, main thread).
  internal interface IRadioactiveIntakes {
    void RegisterIntake(Vector3Int cell, RadioactiveSludgeIntake intake);
    void UnregisterIntake(Vector3Int cell, RadioactiveSludgeIntake intake);
  }

  // Radioactive Springs: native water sources whose non-bad water is
  // RadioactiveWaterSourceSpec.RadioactiveShare radioactive.
  internal interface IRadioactiveSprings {
    void RegisterSpring(IWaterSource source, float share);
    void UnregisterSpring(IWaterSource source);
  }
}
