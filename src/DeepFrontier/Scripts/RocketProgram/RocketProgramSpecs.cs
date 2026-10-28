using System.Collections.Immutable;
using Timberborn.BlueprintSystem;
using Timberborn.NeedSpecs;

namespace DeepFrontier.Scripts {
  // One launch mission. Its rocket and fuel are the ingredients of a native
  // recipe (RecipeId) on the Launch Pad's Manufactory: native haulers stage the
  // goods, the native recipe selector chooses the mission, and the recipe's
  // cycle is the powered preparation window. Ingredients are consumed when
  // preparation starts (the rocket is stacked on the pad).
  internal record RocketMissionSpec {
    [Serialize] public string Id { get; init; }
    [Serialize] public string RecipeId { get; init; }
    // Empty for the first mission; otherwise the mission that must succeed first.
    [Serialize] public string PrerequisiteMissionId { get; init; }
    [Serialize] public float BaseFailureChance { get; init; }
    [Serialize] public int ScienceReward { get; init; }
    // Permanent Awe effect around the pad after this mission succeeds (native
    // wonder need pattern), applied while the pad is on a powered grid.
    [Serialize] public ContinuousEffectSpec LegacyEffect { get; init; }
    [Serialize] public int LegacyWellbeing { get; init; }
    [Serialize] public string DisplayNameLocKey { get; init; }
    [Serialize] public string DescriptionLocKey { get; init; }
    [Serialize] public string SuccessLocKey { get; init; }
    [Serialize] public string FailureLocKey { get; init; }
    // The final mission ends the story through native wonder completion.
    [Serialize] public bool CompletesStory { get; init; }
  }

  internal record RocketLaunchPadSpec : ComponentSpec {
    [Serialize] public ImmutableArray<RocketMissionSpec> Missions { get; init; }
    [Serialize] public float MissionControlFailureReduction { get; init; }
    [Serialize] public float HeritageFailureReductionPerLaunch { get; init; }
    [Serialize] public float MaxHeritageFailureReduction { get; init; }
    [Serialize] public float MinimumFailureChance { get; init; }
    // Preparation holds just below completion until the pad's grid delivers
    // full power; liftoff happens only at full launch power.
    [Serialize] public float LaunchHoldProgress { get; init; }
    [Serialize] public float FlightHours { get; init; }
    // Fraction of the flight at which a failing rocket is lost.
    [Serialize] public float FailurePointFraction { get; init; }
    [Serialize] public float RefurbishmentHours { get; init; }
    // Tiles around the pad that receive completed missions' legacy wellbeing
    // while the pad is on a powered grid (pause/automation do not matter).
    [Serialize] public int LegacyRadius { get; init; }
  }

  // Optional until the Launch Pad art exports the named nodes; the generator
  // adds it only when the art study declares them.
  internal record RocketLaunchVisualSpec : ComponentSpec {
    [Serialize] public string RocketNode { get; init; }
    [Serialize] public string ExhaustNode { get; init; }
    [Serialize] public float AscentHeight { get; init; }
  }

  // Marks Mission Control: an operating, staffed one lowers launch risk.
  internal record RocketMissionControlSpec : ComponentSpec;
}
