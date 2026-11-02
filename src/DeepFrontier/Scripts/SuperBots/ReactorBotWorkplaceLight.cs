using System;
using Timberborn.BaseComponentSystem;
using Timberborn.EntitySystem;
using Timberborn.Illumination;

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
  // Rule: the worker-type modes are exclusive, so only Reactor Bots work at a
  // workplace set to Reactor Bots (ReactorBotWorkplace) and Reactor Bots work
  // nowhere else. This light, decorated on every WorkplaceIlluminator, sets the
  // Reactor Bot colour at priority 30 while the workplace is set to Reactor
  // Bots and clears it otherwise; the lights still go on and off natively
  // (while a worker, here a Reactor Bot, is working). Above the bot blue, below
  // a player's custom colour. Nothing is saved: the mode is.
  internal sealed class ReactorBotWorkplaceLight : BaseComponent, IAwakableComponent, IInitializableEntity {
    // Checked against the native priorities by tools/validate_reactor_bot_workplaces.mjs.
    internal const int ColorizerPriority=30;

    private readonly ReactorBotWorkplaceSettings _settings;
    private ReactorBotWorkplace _workplace;
    private IlluminatorColorizer _colorizer;

    public ReactorBotWorkplaceLight(ReactorBotWorkplaceSettings settings) {
      _settings=settings;
    }

    public void Awake() {
      _workplace=GetComponent<ReactorBotWorkplace>();
      var illuminator=GetComponent<Illuminator>();
      if(!_workplace||!illuminator)throw new InvalidOperationException($"{Name}: a Reactor Bot workplace light needs the Reactor Bot workplace and the native Illuminator of its WorkplaceIlluminator");
      _colorizer=illuminator.CreateColorizer(ColorizerPriority);
    }

    // After loading: the loaded or duplicated mode, then its changes.
    public void InitializeEntity() {
      Apply();
      _workplace.ModeChanged+=(_,_)=>Apply();
    }

    private void Apply() {
      if(_workplace.ReactorMode)_colorizer.SetColor(_settings.WorkplaceColor);
      else _colorizer.ClearColor();
    }
  }
}
