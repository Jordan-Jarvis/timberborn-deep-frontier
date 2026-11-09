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
  // "Reactor bot" recipe, id IndustrialBot, tools/workforce_risks.json botAssembly; written on
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
      _manufactory.ProductionFinished+=BeforeBotManufactory; // native-safety: awake-subscription (handler order before BotManufactory's InitializeEntity subscription; ProductionFinished is never raised while loading)
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

  // The Reactor Bot birth announced by an assembler (or by the dev-mode
  // Reactor Bot generator, ReactorBotGeneratorTool), taken by the bot it
  // creates. Everything happens inside one call: ProductionFinished for an
  // assembler, BotFactory.Create for the generator.
  internal sealed class ReactorBotAssemblyLine {
    private object _source;
    private string _sourceName;
    // An assembler's bot carries the native CharacterBirthInit with a
    // BotManufacturedEvent (BotManufactory); the generator's has no birth init
    // (native BotFactory.Create(position), as BotGeneratorTool spawns bots).
    private bool _manufactured;
    private bool _taken;

    public void Expect(BaseComponent assembler)=>Begin(assembler,assembler.Name,manufactured:true);

    public void ExpectSpawn(object generator, string name)=>Begin(generator,name,manufactured:false);

    private void Begin(object source, string name, bool manufactured) {
      if(_source!=null)throw new InvalidOperationException($"{name}: {_sourceName}'s Reactor Bot birth is still pending");
      _source=source;_sourceName=name;_manufactured=manufactured;_taken=false;
    }

    // True for the bot created while a Reactor Bot birth is pending; that bot
    // starts as a Reactor Bot.
    public bool TakeBirth(BaseComponent bot) {
      if(_source==null)return false;
      var born=bot.TryGetComponent<CharacterBirthInit>(out var birth);
      if(_manufactured) {
        if(!born||birth.EventToPost is not BotManufacturedEvent)return false;
      } else if(born)return false;
      if(_taken)throw new InvalidOperationException($"{_sourceName} created a second bot from one Reactor Bot birth");
      _taken=true;
      return true;
    }

    public void Settle(object source) {
      if(_source!=source)return;
      var taken=_taken;
      var name=_sourceName;
      _source=null;_sourceName=null;_taken=false;
      if(!taken)throw new InvalidOperationException($"{name}: no bot took the Reactor Bot birth (Timberborn 1.1.2.8 contract changed)");
    }
  }
}
