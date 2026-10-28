using Bindito.Core;
using Timberborn.TemplateInstantiation;
using Timberborn.Workshops;

namespace DeepFrontier.Scripts.Narrative {
  // Story state and evidence sources. The journal UI and story dialogs are
  // bound separately by NarrativeJournalConfigurator (TimberUi, player build only).
  [Context("Game")]
  public sealed class NarrativeConfigurator : Configurator {
    protected override void Configure() {
      Bind<NarrativeObjectiveService>().AsSingleton();
      Bind<NarrativeProductionReporter>().AsTransient();
      Bind<HumanRecordCache>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<Manufactory,NarrativeProductionReporter>();
      builder.AddDecorator<HumanRecordCacheSpec,HumanRecordCache>();
      return builder.Build();
    }
  }
}
