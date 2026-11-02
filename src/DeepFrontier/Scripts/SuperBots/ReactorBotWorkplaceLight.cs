using System;
using System.Collections.Generic;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.Illumination;
using Timberborn.SingletonSystem;
using Timberborn.TemplateInstantiation;
using Timberborn.TickSystem;
using Timberborn.WorkSystem;
using Timberborn.WorkSystemUI;
using UnityEngine;

namespace DeepFrontier.Scripts.SuperBots {
  // Neon green workplace windows while Reactor Bots work there (user
  // 2026-11-02). Native mechanism (decompiled 1.1.2.8, Timberborn.WorkSystemUI):
  // a workplace with WorkplaceIlluminatorSpec gets WorkplaceIlluminator, which
  // turns its Illuminator on while Workplace.AnyWorkerHasJobRunning, and
  // WorkerTypeIlluminator, which sets the bot blue (BotColors, IlluminationColor.Bot)
  // through a priority-20 IlluminatorColorizer while the workplace's worker
  // type is Bot. Illuminator shows the colour of its highest-priority colorizer
  // (DefaultIlluminatorColor 10, TubeIlluminator 40, the player's own colour
  // CustomizableIlluminator 100).
  //
  // Rule: this light, decorated on every WorkplaceIlluminator, sets the Reactor
  // Bot colour at priority 30 while at least one Reactor Bot assigned to the
  // workplace has its job running (the native lights-on test, Worker.JobRunning,
  // narrowed to Reactor Bots), and clears it otherwise, which leaves the native
  // bot blue. A mixed crew shows green while a Reactor Bot is among those
  // working. Beaver workplaces never have bots (Workplace.AssignWorker throws on
  // a worker-type mismatch). A player's custom light colour still wins.
  //
  // Ticks late (ILateTickable): after the entity's WorkplaceIlluminator, so the
  // tick that switches the lights on also sets the colour. Nothing is saved:
  // assignments are replayed on load (Worker.InitializeEntity -> AssignWorker
  // raises WorkerAssigned after every entity's Awake), and the colour follows
  // on the first tick.
  internal sealed class ReactorBotWorkplaceLight : TickableComponent, IAwakableComponent, ILateTickable {
    // Checked against the native priorities by tools/validate_reactor_bot_workplace_light.mjs.
    internal const int ColorizerPriority=30;

    private readonly ReactorBotColors _colors;
    private readonly List<(Worker Worker, ReactorBot Bot)> _bots=new();
    private IlluminatorColorizer _colorizer;
    private bool _green;

    public ReactorBotWorkplaceLight(ReactorBotColors colors) {
      _colors=colors;
    }

    public void Awake() {
      var workplace=GetComponent<Workplace>();
      var illuminator=GetComponent<Illuminator>();
      if(!workplace||!illuminator)throw new InvalidOperationException($"{Name}: a Reactor Bot workplace light needs the native Workplace and Illuminator of its WorkplaceIlluminator");
      _colorizer=illuminator.CreateColorizer(ColorizerPriority);
      workplace.WorkerAssigned+=OnWorkerAssigned;
      workplace.WorkerUnassigned+=OnWorkerUnassigned;
    }

    public override void Tick() {
      var green=false;
      for(var i=0;i<_bots.Count&&!green;i++)green=_bots[i].Bot.IsReactor&&_bots[i].Worker.JobRunning;
      if(green==_green)return;
      _green=green;
      if(green)_colorizer.SetColor(_colors.WorkplaceColor);
      else _colorizer.ClearColor();
    }

    // Every bot carries ReactorBot (decorated on BotSpec); beavers do not.
    private void OnWorkerAssigned(object sender, WorkerChangedEventArgs e) {
      var bot=e.Worker.GetComponent<ReactorBot>();
      if(bot)_bots.Add((e.Worker,bot));
    }

    private void OnWorkerUnassigned(object sender, WorkerChangedEventArgs e) {
      _bots.RemoveAll(b=>b.Worker==e.Worker);
    }
  }

  // The Reactor Bot workplace colour id (written by
  // tools/reactor_bot_workplace_light_content.mjs as
  // Data/Configurations/DeepFrontierReactorBotColors.blueprint.json), as native
  // BotColorsSpec names the bot blue.
  internal record FrontierReactorBotColorsSpec : ComponentSpec {
    [Serialize] public string WorkplaceColorId { get; init; }
  }

  // As native BotColors: the colour is looked up once through IlluminationService.
  internal sealed class ReactorBotColors : ILoadableSingleton {
    private readonly ISpecService _specs;
    private readonly IlluminationService _illumination;

    public Color WorkplaceColor { get; private set; }

    public ReactorBotColors(ISpecService specs, IlluminationService illumination) {
      _specs=specs;_illumination=illumination;
    }

    public void Load() {
      var spec=_specs.GetSingleSpec<FrontierReactorBotColorsSpec>();
      // Native FindColorById only warns on an unknown id; require the generated colour.
      if(!_specs.GetSpecs<IlluminationColorSpec>().Any(c=>c.Id==spec.WorkplaceColorId))
        throw new InvalidOperationException($"Reactor Bot workplace light: illumination colour {spec.WorkplaceColorId} is not generated");
      WorkplaceColor=_illumination.FindColorById(spec.WorkplaceColorId);
    }
  }

  // Discovered like the mod's other per-feature configurators.
  [Context("Game")]
  public sealed class ReactorBotWorkplaceLightConfigurator : Configurator {
    protected override void Configure() {
      Bind<ReactorBotColors>().AsSingleton();
      Bind<ReactorBotWorkplaceLight>().AsTransient();
      MultiBind<TemplateModule>().ToProvider(Provide).AsSingleton();
    }

    // Beside native WorkerTypeIlluminator, on the same subject.
    private static TemplateModule Provide() {
      var builder=new TemplateModule.Builder();
      builder.AddDecorator<WorkplaceIlluminator,ReactorBotWorkplaceLight>();
      return builder.Build();
    }
  }
}
