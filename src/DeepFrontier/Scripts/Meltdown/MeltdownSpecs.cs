using System.Collections.Immutable;
using Timberborn.BlueprintSystem;
using Timberborn.Goods;

namespace DeepFrontier.Scripts.Meltdown {
  // Reactor meltdown and radioactive waste leaks. Every value is authored in
  // tools/meltdown_content.mjs and written onto the NuclearReactor, the
  // RadioactiveWasteVault and the RadioactiveWasteRefinery blueprints; nothing
  // here has a default. tools/validate_meltdown_content.mjs checks that the
  // property names below match the authored spec keys exactly.

  // NuclearReactor (ReactorCore). Heat is a 0..1 fraction of meltdown.
  internal record ReactorMeltdownSpec : ComponentSpec {
    // Coolant is the reactor recipe's own ingredient; "dry" means less than
    // one cycle's amount in stock, so the next cycle cannot start.
    [Serialize] public string CoolantGoodId { get; init; }
    [Serialize] public float CoolantReserveWarningHours { get; init; }
    // Operators actually working (native Workshop.NumberOfWorkersWorking).
    [Serialize] public int MinOperators { get; init; }
    // Maintenance falls due after this many running hours and is done by any
    // stretch of MaintenanceOutageHours without production.
    [Serialize] public float MaintenanceIntervalHours { get; init; }
    [Serialize] public float MaintenanceWarningHours { get; init; }
    [Serialize] public float MaintenanceOutageHours { get; init; }
    // Repair materials the maintenance stop consumes from the reactor's own
    // inventory (each must be a reactor recipe ingredient with room for the
    // amount); without them the stop does not complete.
    [Serialize] public ImmutableArray<GoodAmountSpec> MaintenanceGoods { get; init; }
    // Heat balance per game hour: each heating cause (a dry core, and while
    // running a short crew or overdue maintenance) adds HeatPerFaultPerHour;
    // otherwise a core with coolant, or a paused one, cools at CoolingPerHour.
    [Serialize] public float HeatPerFaultPerHour { get; init; }
    [Serialize] public float CoolingPerHour { get; init; }
    // Thresholds: RestartHeat < WarningHeat < FaultHeatLimit < 1 (meltdown).
    // Crew and maintenance faults heat the core only below FaultHeatLimit; a
    // dry core past it posts the meltdown-imminent alert. RestartHeat gates
    // the restart after a player SCRAM.
    [Serialize] public float WarningHeat { get; init; }
    [Serialize] public float FaultHeatLimit { get; init; }
    [Serialize] public float RestartHeat { get; init; }
    // Meltdown release (IRadiationService units: one sludge good = 0.2).
    [Serialize] public float MeltdownInstantSludge { get; init; }
    [Serialize] public float MeltdownSourceSludgePerHour { get; init; }
    [Serialize] public float MeltdownSourceHours { get; init; }
    // Radii are in tiles beyond the reactor footprint (Chebyshev distance).
    [Serialize] public int MeltdownRadius { get; init; }
    [Serialize] public float MeltdownFootprintSoilRadiation { get; init; }
    [Serialize] public float MeltdownEdgeSoilRadiation { get; init; }
    [Serialize] public float MeltdownFootprintWaterRadiation { get; init; }
    [Serialize] public float MeltdownEdgeWaterRadiation { get; init; }
    [Serialize] public int MeltdownKillRadius { get; init; }
    [Serialize] public int MeltdownIrradiationRadius { get; init; }
    // Added to RadiationExposure dose; above 1 so the beaver is irradiated on
    // its next exposure tick after that tick's small dose decay.
    [Serialize] public float MeltdownIrradiationDose { get; init; }
  }

  // RadioactiveWasteVault (Trigger StorageFull: Stockpile) and
  // RadioactiveWasteRefinery (Trigger OutputBlocked: Manufactory product).
  internal record WasteLeakSpec : ComponentSpec {
    [Serialize] public string GoodId { get; init; }
    [Serialize] public string Trigger { get; init; }
    [Serialize] public float WarningFillFraction { get; init; }
    [Serialize] public float LeakIntervalHours { get; init; }
    [Serialize] public int GoodsPerLeak { get; init; }
    [Serialize] public float SludgeVolumePerGood { get; init; }
    [Serialize] public float SoilRadiationPerLeak { get; init; }
    [Serialize] public int SoilRadius { get; init; }
  }

  internal static class WasteLeakTriggers {
    public const string StorageFull = "StorageFull";
    public const string OutputBlocked = "OutputBlocked";
  }

  // Status sprites. Vanilla 1.1.2.8 status icons (Sprites/StatusIcons/<name>,
  // names found in the native status code: NoPowerStatus, NoStorageStatus,
  // LackOfResourcesStatus, NoUnemployed, BuildingBlockedByContamination) used
  // as explicit placeholders until reactor/leak icons are authored.
  internal static class MeltdownSprites {
    public const string Overheating = "BuildingBlockedByContamination";
    public const string Scram = "NoPower";
    public const string CoolantDry = "LackOfResources";
    public const string CoolantLow = "LackOfResources";
    public const string WasteFull = "NoStorage";
    public const string Crew = "NoUnemployed";
    public const string Maintenance = "NothingToDo";
    public const string LeakWarning = "NoStorage";
    public const string Leaking = "BuildingBlockedByContamination";
  }
}
