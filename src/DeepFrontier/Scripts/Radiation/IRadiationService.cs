using System;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // Public contract of the radiation system for other Deep Frontier systems
  // (reactor meltdown, waste leaks, radioactive tide). Coordinates are grid
  // (x, y, z = height). Volumes are native water units; one RadioactiveSludge
  // good is 0.2 units of radioactive volume.
  //
  // One fluid: the native water in every column is fresh + bad + radioactive,
  // summing to 1. The badwater share is native WaterColumn.Contamination; the
  // radioactive share r is kept by RadiationSimulation and moved by the native
  // contamination kernels. Radioactive volume = r * water volume.
  //
  // Threading: call on the main thread. Every mutation is applied through the
  // native water paths (WaterChangeService) or in the simulation's late tick.
  public interface IRadiationService {
    // Adds radioactiveVolume of pure radioactive water (r = 1) to the column
    // containing `cell` through the native water add path (applied with the
    // native water changes of the next parallel tick). Throws if the cell is
    // not inside an open column; use TryFindOpenCell.
    void AddRadioactiveWater(Vector3Int cell, float radioactiveVolume);

    // A saved emitter (e.g. a breached reactor) adding volumePerHour of
    // radioactive water to `cell` for durationHours of game time.
    int AddContinuousSource(Vector3Int cell, float volumePerHour, float durationHours);
    void RemoveContinuousSource(int id);

    // Raises soil radiation (0..1) of the ground under the column containing
    // `cell` by `amount`, capped at 1.
    void AddSoilRadiation(Vector3Int cell, float amount);

    // Radioactive share of the non-bad water every native water source adds
    // (0 = off). Set each tick by the radioactive tide. Radioactive Springs
    // always add r = 1.
    void SetSourceRadioactiveShare(float share);

    // Native water volume a source of strength 1 adds per game hour.
    float WaterPerStrengthHour { get; }

    // Finds the lowest open fluid cell at (xy) whose column contains or lies
    // above height z. Returns false when the whole column is closed.
    bool TryFindOpenCell(Vector2Int xy, int z, out Vector3Int cell);

    RadiationSample Sample(Vector3Int cell);

    // Combined 0..1 hazard: max(radioactive share where submerged, soil * SoilHazardWeight).
    float GetRadiation(Vector3Int cell);

    // True when the column's radioactive share is at or above DetectionLimit. Pumps use this.
    // Sample and GetRadiation report a share below DetectionLimit as 0.
    bool IsColumnContaminated(Vector3Int cell);

    // Radioactive volume in all water (sum of r * depth).
    float TotalWaterRadiation { get; }

    // True from a save's Load until the first frame applies the saved radiation
    // (after every PostLoad); Sample() reports no radiation until then.
    bool SavedStatePending { get; }
  }

  public readonly struct RadiationSample {
    public readonly bool HasColumn;
    public readonly float WaterRadiation;   // radioactive share r of the column water
    public readonly float BadwaterShare;    // native contamination b
    public readonly bool Submerged;         // native water surface is above the cell floor
    public readonly float SoilRadiation;    // 0..1, ground under the column

    public float FreshShare => 1f - BadwaterShare - WaterRadiation;

    public RadiationSample(bool hasColumn, float waterRadiation, float badwaterShare, bool submerged, float soilRadiation) {
      HasColumn = hasColumn; WaterRadiation = waterRadiation; BadwaterShare = badwaterShare; Submerged = submerged; SoilRadiation = soilRadiation;
    }
  }

  // Authored tuning, read by tools/validate_radiation_content.mjs.
  public static class RadiationTuning {
    public const string SludgeGoodId = "RadioactiveSludge";
    public const string ContaminatedWaterGoodId = "ContaminatedWater";
    public const string RadioactiveWasteGoodId = "RadioactiveWaste";
    public const string WaterGoodId = "Water";
    // Storage holding any of these cannot be deleted (HazardousStorageDeletionBlocker).
    public static readonly string[] HazardousStockGoodIds = { RadioactiveWasteGoodId, SludgeGoodId, ContaminatedWaterGoodId };
    public const string NeedId = "Irradiation";
    public const float VolumePerGood = 0.2f;              // radioactive volume per RadioactiveSludge good

    // Radioactive water.
    public const float RadiationHalfLifeDays = 365f;
    // The one radiation threshold (design decision 2026-10-22: "if it is below
    // 0.5 percent then it is gone"). A column whose final share falls below it
    // is set to 0 in the late tick (RadiationSimulation.Rescan), and every
    // reader sees a share below it as 0 (Detected): Sample, GetRadiation,
    // IsColumnContaminated, pumps (refuse at or above, resume once it reads 0),
    // barrels, beaver dose, soil targets, moisture, sensors and the water tint.
    public const float DetectionLimit = 0.005f;
    public static float Detected(float share) => share >= DetectionLimit ? share : 0f;
    public const float MinWaterRadiation = 1e-6f;
    // b + r may exceed 1 by float rounding only; RadiationMixing throws past it.
    public const float ShareTolerance = 1e-5f;

    // Soil.
    public const float SoilRiseFromWaterPerHour = 0.05f;
    public const float WaterToSoilFactor = 4f;
    public const float SoilPerDepositedVolume = 10f;       // radioactive volume left by evaporation or lost water
    public const float SoilHalfLifeDays = 120f;
    public const float SoilSpreadPerHour = 0.002f;
    public const float MinSoilRadiation = 1e-4f;
    public const float SoilHazardWeight = 0.5f;

    // Irradiated ground: soil radiation (or the bank layer) at or above this
    // shows the yellow-green ground tint and kills any plant on it at once
    // (user rule 2026-10-22: "irradiated ground should kill plants immediately").
    public const float IrradiatedGroundThreshold = 0.05f;

    // Beavers. Wading in r = 1 water is as harmful as standing in sludge was.
    public const float ExposurePerWaterRadiationPerHour = 60f;
    public const float ExposurePerSoilRadiationPerHour = 0.25f;
    public const float SoilExposureThreshold = 0.05f;
    public const float ExposureDecayPerHour = 0.5f / 24f;
    public const float LethalUntreatedHours = 8f * 24f;
    public const float CareGraceHours = 12f;
    public const float TreatmentDays = 10f;               // authored into the Hospital effect by tools/radiation_content.mjs

    // Hauling (user 2026-10-29): a beaver carrying radioactive goods has a
    // small chance per carrying hour of being irradiated outright (a 15-minute
    // haul of waste is about 0.5%). Bots are not beavers and are unaffected.
    public const float HaulingIrradiationPerHour = 0.02f;            // waste casks, radioactive water
    public const float ContaminatedHaulingIrradiationPerHour = 0.005f;
    public static float HaulingIrradiationRate(string goodId) =>
      goodId == RadioactiveWasteGoodId || goodId == SludgeGoodId ? HaulingIrradiationPerHour
      : goodId == ContaminatedWaterGoodId ? ContaminatedHaulingIrradiationPerHour : 0f;

    // Radioactive zombie (the irradiated state, RadioactiveZombie.cs). Its
    // movement penalty is the Irradiation need's PunitiveNeedSpec (authored by
    // tools/radiation_content.mjs, slower than native BadwaterContamination).
    public const string HungerNeedId = "Hunger";
    public const string ThirstNeedId = "Thirst";
    public const float ZombieNeedDecayMultiplier = 2f;    // Hunger and Thirst drop at twice their native DailyDelta
    public const float ZombieDyingAlertHours = 2f * 24f;  // alert below this much untreated time left

    // Storage.
    public const float StorageCheckIntervalHours = 1f;

    // Simulation bookkeeping.
    public const int RangeMargin = 3;
    public const int GeometrySyncMargin = 6;

    public static float DecayPerHour(float halfLifeDays) => (float)(Math.Log(2.0) / (halfLifeDays * 24.0));
  }

  internal static class RadiationLoc {
    public const string PumpBlocked = "DeepFrontier.Radiation.Status.PumpBlocked";
    public const string PumpBlockedShort = "DeepFrontier.Radiation.Status.PumpBlocked.Short";
    public const string StorageIrradiated = "DeepFrontier.Radiation.Status.StorageIrradiated";
    public const string HaulingIrradiated = "DeepFrontier.Radiation.Notification.HaulingIrradiated";
    public const string HazardousStockDeletion = "DeepFrontier.Radiation.DeletionBlocker.HazardousStock";
    public const string NoRadiation = "DeepFrontier.Radiation.Status.NoRadiation";
    public const string OutletBlocked = "DeepFrontier.Radiation.Status.OutletBlocked";
    public const string NotAtMapEdge = "DeepFrontier.Radiation.Placement.NotAtMapEdge";
    public const string DeathMessage = "DeepFrontier.Radiation.DeathMessage";
    public const string PlantingWarning = "DeepFrontier.Radiation.Planting.Warning";
    public const string WaterShares = "DeepFrontier.Radiation.WaterShares";
    public const string ZombieSubtitle = "DeepFrontier.Radiation.Zombie.Subtitle";
    public const string ZombieCountdown = "DeepFrontier.Radiation.Zombie.Countdown";
    public const string ZombieCountdownPaused = "DeepFrontier.Radiation.Zombie.CountdownPaused";
    public const string ZombieFlavor = "DeepFrontier.Radiation.Zombie.Flavor";
    public const string ZombieDying = "DeepFrontier.Radiation.Zombie.Dying";
    public const string ZombieDyingShort = "DeepFrontier.Radiation.Zombie.Dying.Short";
  }

  // Vanilla 1.1.2.8 sprites used as explicit placeholders until the radiation
  // icons are authored.
  internal static class RadiationSprites {
    public const string PumpBlocked = "BuildingBlockedByContamination";
    public const string StorageIrradiated = "BuildingBlockedByContamination";
    public const string NoRadiation = "NothingToDo";
    public const string OutletBlocked = "NothingToDo";
    public const string ZombieDying = "Injury";
  }
}
