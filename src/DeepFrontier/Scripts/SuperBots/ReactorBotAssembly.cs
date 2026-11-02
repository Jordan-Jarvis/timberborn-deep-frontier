using System;
using System.Linq;
using Timberborn.BaseComponentSystem;
using Timberborn.BlueprintSystem;
using Timberborn.BotUpkeep;
using Timberborn.CharactersGame;
using Timberborn.EntitySystem;
using Timberborn.Workshops;

namespace DeepFrontier.Scripts.SuperBots {
  // A Bot Assembler recipe whose bot comes out as a Reactor Bot (the
  // Industrial bot recipe, tools/workforce_risks.json botAssembly; written on
  // the vanilla assembler's same-path patch by tools/bot_upkeep_content.mjs).
  internal record FrontierReactorBotAssemblySpec : ComponentSpec {
    [Serialize] public string RecipeId { get; init; }
  }

  // Native contract (Timberborn 1.1.2.8, decompiled Timberborn.BotUpkeep and
  // Timberborn.Workshops / EntitySystem):
  // - BotManufactory subscribes to Manufactory.ProductionFinished in
  //   InitializeEntity; its handler calls BotFactory.Create, which
  //   instantiates the single BotSpec template through
  //   EntityService.Instantiate with a CharacterBirthInit carrying a
  //   BotManufacturedEvent, and initializes it (PreInitialize, Initialize,
  //   PostInitialize) before returning.
  // - Manufactory.FinishProduction raises ProductionFinished with
  //   CurrentRecipe still the recipe that just finished.
  // So the assembler's recipe is known while the native handler creates the
  // bot. This component subscribes in Awake (before any InitializeEntity, so
  // its handler runs before BotManufactory's) to announce a Reactor Bot birth,
  // and again in PostInitializeEntity (after BotManufactory's) to require that
  // the bot took it.
  internal sealed class ReactorBotAssembler : BaseComponent, IAwakableComponent, IPostInitializableEntity {
    private readonly ReactorBotAssemblyLine _line;
    private Manufactory _manufactory;
    private string _recipeId;

    public ReactorBotAssembler(ReactorBotAssemblyLine line) {_line=line;}

    public void Awake() {
      _recipeId=GetComponent<FrontierReactorBotAssemblySpec>().RecipeId;
      _manufactory=GetComponent<Manufactory>();
      if(string.IsNullOrEmpty(_recipeId)||!_manufactory)throw new InvalidOperationException($"{Name}: a Reactor Bot assembly recipe needs a recipe id and a native Manufactory");
      _manufactory.ProductionFinished+=BeforeBotManufactory;
    }

    public void PostInitializeEntity() {
      if(!_manufactory.ProductionRecipes.Any(r=>r.Id==_recipeId))throw new InvalidOperationException($"{Name} does not run the Reactor Bot recipe {_recipeId}");
      _manufactory.ProductionFinished+=AfterBotManufactory;
    }

    private void BeforeBotManufactory(object sender, EventArgs e) {
      if(_manufactory.CurrentRecipe.Id==_recipeId)_line.Expect(this);
    }

    private void AfterBotManufactory(object sender, EventArgs e)=>_line.Settle(this);
  }

  // The Reactor Bot birth announced by an assembler, taken by the bot it
  // creates. Everything happens inside one ProductionFinished call.
  internal sealed class ReactorBotAssemblyLine {
    private BaseComponent _assembler;
    private bool _taken;

    public void Expect(BaseComponent assembler) {
      if(_assembler)throw new InvalidOperationException($"{assembler.Name}: {_assembler.Name}'s Reactor Bot birth is still pending");
      _assembler=assembler;_taken=false;
    }

    // True for the bot the native BotManufactory creates while a Reactor Bot
    // birth is pending; that bot starts as a Reactor Bot.
    public bool TakeBirth(BaseComponent bot) {
      if(!_assembler||!bot.TryGetComponent<CharacterBirthInit>(out var birth)||birth.EventToPost is not BotManufacturedEvent)return false;
      if(_taken)throw new InvalidOperationException($"{_assembler.Name} created a second bot from one Reactor Bot recipe");
      _taken=true;
      return true;
    }

    public void Settle(BaseComponent assembler) {
      if(_assembler!=assembler)return;
      var taken=_taken;
      _assembler=null;_taken=false;
      if(!taken)throw new InvalidOperationException($"{assembler.Name}: the native BotManufactory created no bot for the Reactor Bot recipe (Timberborn 1.1.2.8 contract changed)");
    }
  }
}
