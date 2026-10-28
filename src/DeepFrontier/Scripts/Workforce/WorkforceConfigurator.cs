using Bindito.Core;
using Timberborn.Beavers;
using Timberborn.Bots;
using Timberborn.TemplateInstantiation;

namespace DeepFrontier.Scripts {
  // Discovered like the mod's other per-feature configurators.
  [Context("Game")]
  public sealed class WorkforceConfigurator : Configurator {
    protected override void Configure() {
      Bind<WorkforceSettings>().AsSingleton();
      Bind<SpecialistRoster>().AsSingleton();
      Bind<SpecialistStaffing>().AsSingleton();
      Bind<IndustrialRisk>().AsTransient();
      Bind<BotWear>().AsTransient();
      Bind<SpecialistTrait>().AsTransient();
      Bind<SpecialistWorkplace>().AsTransient();
      Bind<SpecialistSchool>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<FrontierWorkforceRiskSpec,IndustrialRisk>();
      builder.AddDecorator<FrontierSpecialistWorkplaceSpec,SpecialistWorkplace>();
      builder.AddDecorator<FrontierSpecialistSchoolSpec,SpecialistSchool>();
      builder.AddDecorator<AdultSpec,SpecialistTrait>();
      builder.AddDecorator<BotSpec,BotWear>();
      return builder.Build();
    }
  }
}
