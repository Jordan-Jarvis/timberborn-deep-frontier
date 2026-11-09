using Bindito.Core;
using Timberborn.Beavers;
using Timberborn.BlockSystem;
using Timberborn.NaturalResources;
using Timberborn.Planting;
using Timberborn.Stockpiles;
using Timberborn.TemplateInstantiation;
using Timberborn.WaterBuildings;

namespace DeepFrontier.Scripts.Radiation {
  // Discovered like the mod's other per-feature configurators.
  [Context("Game")]
  public sealed class RadiationConfigurator : Configurator {
    protected override void Configure() {
#if DEEP_FRONTIER_MODDABLE_FLUIDS
      // Moddable Fluids carries and renders the water; the facade serves the radiation services
      // (docs/deep-frontier-fluids-migration.md).
      Bind<DeepFrontier.ModdableFluidsMigration.ModdableFluidsBankLayer>().AsSingleton();
      Bind<DeepFrontier.ModdableFluidsMigration.ModdableFluidsRadiation>().AsSingleton();
      Bind<IRadiationService>().ToExisting<DeepFrontier.ModdableFluidsMigration.ModdableFluidsRadiation>();
      Bind<IIrradiatedGround>().ToExisting<DeepFrontier.ModdableFluidsMigration.ModdableFluidsRadiation>();
      Bind<IRadiationWaterCells>().ToExisting<DeepFrontier.ModdableFluidsMigration.ModdableFluidsRadiation>();
      Bind<IRadioactiveIntakes>().ToExisting<DeepFrontier.ModdableFluidsMigration.ModdableFluidsRadiation>();
      Bind<IRadioactiveSprings>().ToExisting<DeepFrontier.ModdableFluidsMigration.ModdableFluidsRadiation>();
#else
      Bind<RadiationSoil>().AsSingleton();
      Bind<RadiationSimulation>().AsSingleton();
      Bind<IRadiationService>().ToExisting<RadiationSimulation>();
      Bind<IIrradiatedGround>().ToExisting<RadiationSimulation>();
      Bind<IRadiationWaterCells>().ToExisting<RadiationSimulation>();
      Bind<IRadioactiveIntakes>().ToExisting<RadiationSimulation>();
      Bind<IRadioactiveSprings>().ToExisting<RadiationSimulation>();
      Bind<RadiationRenderer>().AsSingleton();
#endif
      Bind<RadiationStorageService>().AsSingleton();
      Bind<MapEdgeSiteValidator>().AsSingleton();
      MultiBind<IBlockObjectValidator>().ToExisting<MapEdgeSiteValidator>();
      Bind<RadiationIntakeGuard>().AsTransient();
      Bind<RadiationExposure>().AsTransient();
      Bind<RadioactiveZombie>().AsTransient();
      Bind<IrradiatedStorageStatus>().AsTransient();
      Bind<HazardousStorageDeletionBlocker>().AsTransient();
      Bind<RadioactiveSludgeOutfall>().AsTransient();
      Bind<RadioactiveSludgeIntake>().AsTransient();
      Bind<MapEdgeSite>().AsTransient();
      Bind<IrradiatedPlantWarning>().AsTransient();
      Bind<IrradiatedGroundDeath>().AsTransient();
      Bind<IrradiatedPlantingSpots>().AsTransient();
      MultiBind<ISpawnValidator>().To<IrradiatedGroundSpawnValidator>().AsSingleton();
      Bind<RadioactiveWaterSource>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder = new TemplateModule.Builder();
      builder.AddDecorator<WaterInput, RadiationIntakeGuard>();
      builder.AddDecorator<BeaverSpec, RadiationExposure>();
      builder.AddDecorator<BeaverSpec, RadioactiveZombie>();
      builder.AddDecorator<Stockpile, IrradiatedStorageStatus>();
      builder.AddDecorator<Stockpile, HazardousStorageDeletionBlocker>();
      builder.AddDecorator<RadioactiveSludgeOutfallSpec, RadioactiveSludgeOutfall>();
      builder.AddDecorator<RadioactiveSludgeIntakeSpec, RadioactiveSludgeIntake>();
      builder.AddDecorator<MapEdgeSiteSpec, MapEdgeSite>();
      builder.AddDecorator<PlantableSpec, IrradiatedPlantWarning>();
      builder.AddDecorator<NaturalResourceSpec, IrradiatedGroundDeath>();
      // Planters skip irradiated ground (IrradiatedPlantingSpots.cs); native
      // PlantingSpotFinder is decorated on PlantablePrioritizer too.
      builder.AddDecorator<PlantablePrioritizer, IrradiatedPlantingSpots>();
      builder.AddDecorator<RadioactiveWaterSourceSpec, RadioactiveWaterSource>();
      return builder.Build();
    }
  }
}
