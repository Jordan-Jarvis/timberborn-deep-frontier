using System.Collections.Immutable;
using Timberborn.BlueprintSystem;

namespace DeepFrontier.Scripts.Narrative {
  // The colony's story: exactly one blueprint (Configurations/DeepFrontierNarrative)
  // carries it; written by tools/narrative_content.mjs. Every value is required
  // and validated by NarrativeObjectiveService.Load; nothing is defaulted.
  internal record NarrativeSettingsSpec : ComponentSpec {
    // The story runs only in settlements of this faction (Deep Frontier is Iron Teeth only).
    [Serialize] public string FactionId { get; init; }
    // Rocket mission whose success is the final chapter (RocketMissionSpec.CompletesStory).
    [Serialize] public string EndingMissionId { get; init; }
    // Main chapters, completed strictly in order.
    [Serialize] public ImmutableArray<NarrativeStageSpec> Stages { get; init; }
    // Optional discoveries, completed in any order; they never gate chapters.
    [Serialize] public ImmutableArray<NarrativeStageSpec> Discoveries { get; init; }
    // What the final launch carries; chosen during the Choice chapter.
    [Serialize] public ImmutableArray<NarrativeEndingSpec> Endings { get; init; }
  }

  internal record NarrativeStageSpec {
    [Serialize] public string Id { get; init; }
    [Serialize] public string TitleLocKey { get; init; }
    [Serialize] public string ObjectiveLocKey { get; init; }
    // Empty for discoveries.
    [Serialize] public string HintLocKey { get; init; }
    [Serialize] public ImmutableArray<string> StoryLocKeys { get; init; }
    [Serialize] public int ScienceReward { get; init; }
    // "" (none), "Choice" (the chapter that records the ending choice) or
    // "Epilogue" (the final chapter, which appends the chosen ending).
    [Serialize] public string EndingText { get; init; }
    // All must be met.
    [Serialize] public ImmutableArray<NarrativeRequirementSpec> Requirements { get; init; }
  }

  // Kinds (Targets are alternatives; Amount is the total over them):
  // - BuildingFinished: template names; met once any target has ever been finished (Amount 1).
  // - GoodProduced: good ids; cumulative amount produced by native recipes and cache surveys.
  // - RecipeCompleted: recipe ids; cumulative completed production cycles.
  // - MissionCompleted: one rocket mission id (Amount 1).
  // - EndingChosen: every ending id (Amount 1); met once the colony has chosen.
  // - CachesSurveyed: no targets; Human Record Caches surveyed so far.
  internal record NarrativeRequirementSpec {
    [Serialize] public string Kind { get; init; }
    [Serialize] public ImmutableArray<string> Targets { get; init; }
    [Serialize] public int Amount { get; init; }
    [Serialize] public string LabelLocKey { get; init; }
    // BuildingFinished only: one story line per target, told for the first
    // target the colony finished. Empty otherwise.
    [Serialize] public ImmutableArray<string> VariantLocKeys { get; init; }
  }

  internal record NarrativeEndingSpec {
    [Serialize] public string Id { get; init; }
    [Serialize] public string TitleLocKey { get; init; }
    [Serialize] public string DescriptionLocKey { get; init; }
    [Serialize] public ImmutableArray<string> EpilogueLocKeys { get; init; }
  }

  // Human Record Cache map object (clone of the vanilla MediumRelic). A finished
  // workshop that runs SurveyRecipeId with an occupied cell within SurveyRadius
  // cells surveys it while its workers work; after SurveyHours it hands
  // RewardAmount RewardGoodId to that workshop's output as storage allows.
  internal record HumanRecordCacheSpec : ComponentSpec {
    [Serialize] public string SurveyRecipeId { get; init; }
    [Serialize] public int SurveyRadius { get; init; }
    [Serialize] public float SurveyHours { get; init; }
    [Serialize] public string RewardGoodId { get; init; }
    [Serialize] public int RewardAmount { get; init; }
  }
}
