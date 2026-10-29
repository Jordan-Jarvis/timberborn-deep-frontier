using System.Collections.Immutable;
using Timberborn.BlueprintSystem;
using Timberborn.NeedApplication;

namespace DeepFrontier.Scripts {
  // Workforce risks (industrial injuries, bot wear, specialist-only crews).
  // Every value is authored in tools/workforce_risks.json and written by
  // tools/workforce_risk_content.mjs; nothing here has a default. Spec names
  // carry the Frontier prefix so they cannot collide with other mods' specs.

  // Singleton: Data/Configurations/DeepFrontierWorkforce.blueprint.json.
  internal record FrontierWorkforceSettingsSpec : ComponentSpec {
    // Native probability group whose Low/Medium/High chances are rolled
    // through EffectProbabilityService.CanApply, which also applies the
    // game mode's InjuryChance (Easy 0.3, Normal/Hard 1.0).
    [Serialize] public string ProbabilityGroupId { get; init; }
    // Copies of the native group's chances, for panel text only. The static
    // validator checks them against vanilla Configurations/ProbabilityGroups.
    [Serialize] public float NativeLowChance { get; init; }
    [Serialize] public float NativeMediumChance { get; init; }
    [Serialize] public float NativeHighChance { get; init; }
    [Serialize] public string InjuryNeedId { get; init; }
    [Serialize] public string FatigueNeedId { get; init; }
    // Tired: fatigue need points below this (but not yet critical).
    [Serialize] public float StrainedBelowFatiguePoints { get; init; }
    [Serialize] public int StrainedBelowWellbeing { get; init; }
    [Serialize] public int ExhaustedBelowWellbeing { get; init; }
    [Serialize] public int StrainedRolls { get; init; }
    [Serialize] public int ExhaustedRolls { get; init; }
    [Serialize] public ImmutableArray<FrontierSpecialistDisciplineSpec> Disciplines { get; init; }
  }

  internal record FrontierSpecialistDisciplineSpec {
    [Serialize] public string Id { get; init; }
    [Serialize] public string DisplayNameLocKey { get; init; }
    [Serialize] public string PluralDisplayNameLocKey { get; init; }
  }

  // Heavy-industry workplace: hourly-style injury rolls and bot wear.
  internal record FrontierWorkforceRiskSpec : ComponentSpec {
    [Serialize] public string DangerTier { get; init; }
    [Serialize] public EffectProbability Probability { get; init; }
    [Serialize] public float RollIntervalHours { get; init; }
    [Serialize] public float InjuryPoints { get; init; }
    [Serialize] public float FatalAccidentChance { get; init; }
    // 1 on beaver-only buildings (no bots can work there).
    [Serialize] public float BotWearMultiplier { get; init; }
  }

  // Workplace that only beavers trained in Discipline may staff.
  internal record FrontierSpecialistWorkplaceSpec : ComponentSpec {
    [Serialize] public string Discipline { get; init; }
  }

  // Technical School: a staff-free goods-consuming attraction that teaches
  // one of these disciplines, chosen in its panel (SpecialistSchool).
  internal record FrontierSpecialistSchoolSpec : ComponentSpec {
    [Serialize] public ImmutableArray<FrontierSpecialistProgramSpec> Programs { get; init; }
  }

  internal record FrontierSpecialistProgramSpec {
    [Serialize] public string Discipline { get; init; }
    // Hours inside a school teaching the discipline that make a graduate.
    [Serialize] public float StudyHours { get; init; }
    // Goods the school uses up per hour while anyone studies the discipline.
    [Serialize] public ImmutableArray<FrontierSchoolSupplySpec> Supplies { get; init; }
  }

  internal record FrontierSchoolSupplySpec {
    [Serialize] public string GoodId { get; init; }
    [Serialize] public float GoodPerHour { get; init; }
  }
}
