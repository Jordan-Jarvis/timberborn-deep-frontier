using System.Collections.Immutable;
using Timberborn.BlueprintSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Global smog tuning: exactly one blueprint (Configurations/DeepFrontierSmog)
  // carries it; written by tools/smog_building_content.mjs from
  // tools/smog_content.json. Every value is required and validated by
  // SmogService.Load; nothing is defaulted.
  internal record SmogSettingsSpec : ComponentSpec {
    // Intensity (0..1) at or above which light smog applies: the Smog need,
    // the growth slowdown, panel lines and highlights.
    [Serialize] public float LightThreshold { get; init; }
    // Intensity at or above which the HeavySmog need also applies.
    [Serialize] public float HeavyThreshold { get; init; }
    [Serialize] public string LightNeedId { get; init; }
    [Serialize] public string HeavyNeedId { get; init; }
    // Need points lost per hour at intensity 1 (scaled by intensity).
    [Serialize] public float ExposurePointsPerHour { get; init; }
    // Growth slowdown = min(Max, AtThreshold + PerIntensity * (I - LightThreshold)).
    [Serialize] public float GrowthSlowdownAtThreshold { get; init; }
    [Serialize] public float GrowthSlowdownPerIntensity { get; init; }
    [Serialize] public float GrowthSlowdownMax { get; init; }
    // Greenery: every living tree (bush) within GreeneryRadius cells removes
    // this fraction of the smog in a cell, scaled by its growth; capped.
    [Serialize] public float TreeReduction { get; init; }
    [Serialize] public float BushReduction { get; init; }
    [Serialize] public float GreeneryRadius { get; init; }
    [Serialize] public float GreeneryMaxReduction { get; init; }
    // Combined scrubber reduction cap (scrubbers combine as 1 - prod(1 - k)).
    [Serialize] public float ScrubberMaxReduction { get; init; }
    // Plumes drift downwind by up to this many cells at full wind strength.
    [Serialize] public float WindDriftCells { get; init; }
    // A source keeps full strength out to CoreFraction * Radius, then falls
    // linearly to EdgeFactor * Strength at Radius and stops (hard edge).
    [Serialize] public float CoreFraction { get; init; }
    [Serialize] public float EdgeFactor { get; init; }
    [Serialize] public float FieldIntervalHours { get; init; }
    [Serialize] public float GrowthIntervalHours { get; init; }
  }

  // One smoke flue mouth. Position is the mouth in the building's local grid
  // frame (x, y across the footprint, z up), the artwork coordinates recorded
  // in the study registration (smokeEmitters).
  internal record SmogSourceSpec {
    [Serialize] public Vector3 Position { get; init; }
    [Serialize] public float Radius { get; init; }
    [Serialize] public float Strength { get; init; }
  }

  // A polluting building. Activity mirrors the particle controller that runs
  // the same flue's smoke: "Workshop" (WorkshopParticleController: while the
  // workshop works), "Generator" (PowerGeneratorParticleController: while the
  // generator's MechanicalNode is ActiveAndPowered with OutputMultiplier > 0)
  // or "Occupied" (EnterableParticleController: while anyone is inside).
  internal record SmogEmitterSpec : ComponentSpec {
    [Serialize] public string Activity { get; init; }
    [Serialize] public ImmutableArray<SmogSourceSpec> Sources { get; init; }
  }

  // Smog Scrubber: while finished, unblocked and powered, removes Reduction of
  // the smog in every cell within Radius of its footprint centre.
  internal record SmogScrubberSpec : ComponentSpec {
    [Serialize] public float Radius { get; init; }
    [Serialize] public float Reduction { get; init; }
  }
}
