using System.Collections.Immutable;
using Timberborn.BlueprintSystem;

namespace DeepFrontier.Scripts.Cryogenics {
  // Powered cryogenic storage on a native liquid Stockpile (written by
  // tools/cryogenic_content.mjs; every value is required and validated by
  // CryogenicTank.Awake, nothing is defaulted).
  //
  // The native Stockpile inventory stays the store and the player picks the
  // stored good with the native single-good selection. Goods lists the goods
  // this farm may hold (one at a time); any other selection accepts nothing.
  // While the building is finished, unblocked and powered
  // (MechanicalBuilding.ActiveAndPowered) the selected good is accepted from
  // haulers and Timber Pipes. Otherwise intake closes at once; after
  // BufferHours without power the tank vents VentPerHourOnPowerLoss units per
  // hour until power returns. Pause and automation Off block the same
  // BlockableObject and therefore count as power loss.
  internal record CryogenicTankSpec : ComponentSpec {
    [Serialize] public ImmutableArray<string> Goods { get; init; }
    [Serialize] public float VentPerHourOnPowerLoss { get; init; }
    [Serialize] public float BufferHours { get; init; }
  }
}
