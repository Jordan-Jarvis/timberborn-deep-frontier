using System.Collections.Generic;
using Bindito.Core;
using Timberborn.Bots;
using Timberborn.BottomBarSystem;
using Timberborn.Coordinates;
using Timberborn.CursorToolSystem;
using Timberborn.InputSystem;
using Timberborn.SingletonSystem;
using Timberborn.ToolButtonSystem;
using Timberborn.ToolSystem;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.SuperBots {
  // Dev mode: spawn Reactor Bots (user 2026-11-02), beside the native bot
  // generator. Native pattern (decompiled 1.1.2.8, Timberborn.BotsUI):
  // BotGeneratorTool is an IDevModeTool that, on a click outside the UI, calls
  // BotFactory.Create(position) once (ten times with the SpawnManyCharacters
  // key held) on the picked tile; BotGeneratorButton puts it in the bottom
  // bar's left section (order 80) as a red groupless tool button with the
  // Sprites/BottomBar/BotGeneratorTool image. ToolButton shows dev-mode tools
  // only in dev mode.
  //
  // This tool does the same, and each bot is born as a Reactor Bot through the
  // path the Bot Assembler's Reactor bot recipe uses: the birth is announced
  // on ReactorBotAssemblyLine, the native factory creates and initializes the
  // ordinary bot, ReactorBot.InitializeEntity takes the birth (Reactor state,
  // reactor needs full), and Settle requires that it did. Reactor Bots are
  // Iron Teeth only (ReactorBot.Applies): another faction's click spawns nothing.
  internal sealed class ReactorBotGeneratorTool : IDevModeTool, ITool, IInputProcessor {
    private static readonly string CursorKey="BeaverAvatarCursor"; // native BotGeneratorTool
    private static readonly string SpawnManyCharactersKey="SpawnManyCharacters"; // native BotGeneratorTool
    private static readonly int ManyBotsToAdd=10; // native BotGeneratorTool

    private readonly BotFactory _botFactory;
    private readonly ReactorBotAssemblyLine _line;
    private readonly ReactorBotSettings _settings;
    private readonly InputService _inputService;
    private readonly CursorService _cursorService;
    private readonly CursorCoordinatesPicker _cursorCoordinatesPicker;

    public bool IsDevMode=>true;

    public ReactorBotGeneratorTool(BotFactory botFactory, ReactorBotAssemblyLine line, ReactorBotSettings settings, InputService inputService,
      CursorService cursorService, CursorCoordinatesPicker cursorCoordinatesPicker) {
      _botFactory=botFactory;_line=line;_settings=settings;_inputService=inputService;_cursorService=cursorService;_cursorCoordinatesPicker=cursorCoordinatesPicker;
    }

    public bool ProcessInput() {
      if(_inputService.MainMouseButtonDown&&!_inputService.MouseOverUI) {
        PlaceBots(_inputService.IsKeyHeld(SpawnManyCharactersKey)?ManyBotsToAdd:1);
        return true;
      }
      return false;
    }

    public void Enter() {
      _cursorService.SetCursor(CursorKey);
      _inputService.AddInputProcessor(this);
    }

    public void Exit() {
      _cursorService.ResetCursor();
      _inputService.RemoveInputProcessor(this);
    }

    private void PlaceBots(int count) {
      if(!_settings.AppliesToFaction) {
        Debug.LogWarning("[DeepFrontier] Reactor Bot generator: Reactor Bots are Iron Teeth only; no bot spawned");
        return;
      }
      var picked=_cursorCoordinatesPicker.Pick();
      if(!picked.HasValue)return;
      var position=CoordinateSystem.GridToWorldCentered(picked.Value.TileCoordinates);
      for(var i=0;i<count;i++) {
        _line.ExpectSpawn(this,"Reactor Bot generator");
        _botFactory.Create(position);
        _line.Settle(this);
      }
    }
  }

  // The tool's bottom-bar button: the native bot generator image, tinted with
  // the Reactor Bot window colour. The bottom bar collects its elements while
  // singletons are still loading (SingletonLifecycleService.LoadAll: every
  // Load, then every PostLoad), so the tint, which needs the loaded colour, is
  // applied in PostLoad.
  internal sealed class ReactorBotGeneratorButton : IBottomBarElementsProvider, IPostLoadableSingleton {
    private static readonly string ToolImageKey="BotGeneratorTool"; // native BotGeneratorButton

    private readonly ReactorBotGeneratorTool _tool;
    private readonly ToolButtonFactory _toolButtonFactory;
    private readonly ReactorBotWorkplaceSettings _settings;
    private VisualElement _image;
    private bool _postLoaded;

    public ReactorBotGeneratorButton(ReactorBotGeneratorTool tool, ToolButtonFactory toolButtonFactory, ReactorBotWorkplaceSettings settings) {
      _tool=tool;_toolButtonFactory=toolButtonFactory;_settings=settings;
    }

    public IEnumerable<BottomBarElement> GetElements() {
      var button=_toolButtonFactory.CreateGrouplessRed(_tool,ToolImageKey);
      _image=button.Root.Q<VisualElement>("ToolImage");
      if(_postLoaded)Tint();
      yield return BottomBarElement.CreateSingleLevel(button.Root);
    }

    public void PostLoad() {
      _postLoaded=true;
      if(_image!=null)Tint();
    }

    private void Tint()=>_image.style.unityBackgroundImageTintColor=new StyleColor(_settings.WorkplaceColor);
  }

  [Context("Game")]
  public sealed class ReactorBotGeneratorConfigurator : Configurator {
    private sealed class BottomBarModuleProvider : IProvider<BottomBarModule> {
      private readonly ReactorBotGeneratorButton _button;
      public BottomBarModuleProvider(ReactorBotGeneratorButton button) {_button=button;}
      public BottomBarModule Get() {
        var builder=new BottomBarModule.Builder();
        builder.AddLeftSectionElement(_button,81); // right after the native bot generator (80)
        return builder.Build();
      }
    }

    protected override void Configure() {
      Bind<ReactorBotGeneratorTool>().AsSingleton();
      Bind<ReactorBotGeneratorButton>().AsSingleton();
      MultiBind<BottomBarModule>().ToProvider<BottomBarModuleProvider>().AsSingleton();
    }
  }
}
