using System;
using System.Collections.Immutable;
using System.Linq;
using System.Reflection;
using Timberborn.CoreUI;
using Timberborn.GameSceneLoading;
using Timberborn.Localization;
using Timberborn.MainMenuPanels;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.SingletonSystem;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Radioactive tide rows on the native new-game screen (Timberborn 1.1.2.8,
  // Timberborn.MainMenuPanels NewGameModePanel + CustomNewGameModeController,
  // UI/Views/MainMenu/NewGameModePanel.uxml).
  //
  // Native flow: the panel lists one button per GameModeSpec blueprint
  // (GameModeSpecService.GetSpecsOrdered: Easy, Normal, Hard) and starts the
  // game with the selected preset's GameModeSpec. "Customize" fills the
  // custom fields from the selected preset (CustomNewGameModeController.
  // Initialize) and the game then starts with the GameModeSpec those fields
  // build (TryGetValidatedGameMode). Each preset carries a
  // RadioactiveTideGameModeSpec (Data/NewGameModes), so a preset needs nothing
  // from this class.
  //
  // For the custom mode this class adds a "Radioactive tides" toggle and the
  // rows "Cycles without radioactive tide", "Radioactive tide chance" and
  // "Radioactive tide duration" right after the native badtide rows, filled
  // from the selected preset when "Customize" is pressed, as the native
  // fields are. The rows are the native badtide rows themselves: a second
  // copy of the native panel view is loaded through the native
  // VisualElementLoader (which localizes it and sets up its text fields and
  // sounds) and its badtide toggle, cycles, chance and duration rows are
  // moved over, renamed and relabelled. Fields clamp on focus-out with the
  // native TextFields.InitializeIntegerField; a duration whose shortest
  // exceeds its longest is marked with the native invalid-input class and
  // keeps the native Start button disabled.
  //
  // RadioactiveTideNewGamePatch (a postfix on the native
  // CustomNewGameModeController.TryGetValidatedGameMode) asks TryGetValidated
  // for the values and attaches them to the custom GameModeSpec.
  public sealed class RadioactiveTideNewGameSettings : IPostLoadableSingleton, IUnloadableSingleton {
    private const string ModesName = "Modes";
    private const string CustomizeButtonName = "CustomizeButton";
    private const string NextButtonName = "NextButton";
    private const string BadtideToggleRowName = "BadtideEnabledWrapper";
    private const string BadtideToggleName = "BadtideEnabled";
    private const string BadtideWrapperName = "BadtideWrapper";
    private const string BadtideCyclesRowName = "CyclesBeforeRandomizingBadtideWrapper";
    private const string BadtideCyclesName = "CyclesBeforeRandomizingBadtide";
    private const string BadtideChanceRowName = "ChanceForBadtideWrapper";
    private const string BadtideChanceName = "ChanceForBadtide";
    private const string BadtideDurationRowName = "BadtideDurationWrapper";
    private const string BadtideMinDurationName = "MinBadtideDuration";
    private const string BadtideMaxDurationName = "MaxBadtideDuration";
    private const string BadtideHandicapRowName = "BadtideDurationHandicapWrapper";
    private const string SettingLabelClass = "new-game-mode-panel__setting-label";
    // CustomNewGameModeController.InvalidInputClass.
    private const string InvalidInputClass = "new-game-mode-panel__setting-input--invalid";

    // The main menu's instance, for RadioactiveTideNewGamePatch.
    internal static RadioactiveTideNewGameSettings Current { get; private set; }

    private readonly NewGameModePanel _panel;
    private readonly CustomNewGameModeController _customController;
    private readonly GameModeSpecService _gameModeSpecService;
    private readonly VisualElementLoader _visualElementLoader;
    private readonly ILoc _loc;

    private GameModeSpec _selectedPreset;
    private bool _customActive;
    private Button _nextButton;
    private Toggle _enabled;
    private VisualElement _wrapper;
    private IntegerField _cyclesWithout;
    private IntegerField _chance;
    private IntegerField _minDuration;
    private IntegerField _maxDuration;

    public RadioactiveTideNewGameSettings(NewGameModePanel panel, CustomNewGameModeController customController,
        GameModeSpecService gameModeSpecService, VisualElementLoader visualElementLoader, ILoc loc) {
      _panel = panel; _customController = customController; _gameModeSpecService = gameModeSpecService;
      _visualElementLoader = visualElementLoader; _loc = loc;
    }

    internal static RadioactiveTideNewGameSettings RequireCurrent() =>
      Current ?? throw new InvalidOperationException("Radioactive tide: the native custom game mode was built outside the main menu's new-game screen");

    // After NewGameModePanel.Load has built the panel and its mode buttons.
    public void PostLoad() {
      if (Current != null) throw new InvalidOperationException("Radioactive tide: a new-game screen is already active; the previous main menu was not unloaded");
      var root = RadioactiveTideNewGameNative.PanelRoot(_panel)
        ?? throw new InvalidOperationException("Radioactive tide: NewGameModePanel has no root after Load");
      ImmutableArray<GameModeSpec> presets = _gameModeSpecService.GetSpecsOrdered();
      foreach (var preset in presets) RadioactiveTideGameModes.Require(preset, $"game mode {_loc.T(preset.DisplayNameLocKey)}");
      TrackPresetButtons(root, presets);
      _selectedPreset = _gameModeSpecService.GetDefaultSpec();
      AddRows(root);
      Required<Button>(root, CustomizeButtonName).RegisterCallback<ClickEvent>(_ => OnCustomize());
      _nextButton = Required<Button>(root, NextButtonName);
      Apply(RadioactiveTideGameModes.Require(_selectedPreset, "the default game mode"));
      Current = this;
    }

    public void Unload() {
      if (Current == this) Current = null;
    }

    // The custom mode's tide values, or false (fields marked) when they are
    // not valid. Called by the native custom controller's validation, which
    // decides whether the Start button is enabled.
    internal bool TryGetValidated(out RadioactiveTideGameModeSpec spec) {
      if (!Validate()) { spec = null; return false; }
      spec = RadioactiveTideGameModes.Create(_enabled.value, _cyclesWithout.value, _chance.value, _minDuration.value, _maxDuration.value);
      return true;
    }

    // Native NewGameModePanel.Load adds one mode button per spec of
    // GetSpecsOrdered, in that order, labelled with its display name.
    private void TrackPresetButtons(VisualElement root, ImmutableArray<GameModeSpec> presets) {
      var buttons = Required<VisualElement>(root, ModesName).Query<Button>().ToList();
      if (buttons.Count != presets.Length)
        throw Changed($"the new-game screen shows {buttons.Count} mode buttons for {presets.Length} game modes");
      for (int i = 0; i < presets.Length; i++) {
        var preset = presets[i];
        if (buttons[i].text != _loc.T(preset.DisplayNameLocKey))
          throw Changed($"mode button {i} reads '{buttons[i].text}', expected '{_loc.T(preset.DisplayNameLocKey)}'");
        buttons[i].RegisterCallback<ClickEvent>(_ => { _selectedPreset = preset; _customActive = false; });
      }
    }

    private void AddRows(VisualElement root) {
      var nativeBadtide = Required<VisualElement>(root, BadtideWrapperName);
      var copy = _visualElementLoader.LoadVisualElement(RadioactiveTideNewGameNative.PanelView);

      var toggleRow = Take(copy, BadtideToggleRowName, "RadioactiveTideEnabledWrapper");
      _enabled = Rename<Toggle>(toggleRow, BadtideToggleName, "RadioactiveTideEnabled");
      Relabel(toggleRow, RadioactiveTideLoc.SettingEnabled);

      _wrapper = Take(copy, BadtideWrapperName, "RadioactiveTideWrapper");
      Required<VisualElement>(_wrapper, BadtideHandicapRowName).RemoveFromHierarchy();
      var cyclesRow = Rename<VisualElement>(_wrapper, BadtideCyclesRowName, "CyclesWithoutRadioactiveTideWrapper");
      var chanceRow = Rename<VisualElement>(_wrapper, BadtideChanceRowName, "RadioactiveTideChanceWrapper");
      var durationRow = Rename<VisualElement>(_wrapper, BadtideDurationRowName, "RadioactiveTideDurationWrapper");
      if (_wrapper.childCount != 3 || _wrapper[0] != cyclesRow || _wrapper[1] != chanceRow || _wrapper[2] != durationRow)
        throw Changed("the badtide rows are no longer cycles, chance, duration and handicap");
      Relabel(cyclesRow, RadioactiveTideLoc.NewGameCyclesWithout);
      Relabel(chanceRow, RadioactiveTideLoc.NewGameChance);
      Relabel(durationRow, RadioactiveTideLoc.NewGameDuration);
      _cyclesWithout = Rename<IntegerField>(cyclesRow, BadtideCyclesName, "CyclesWithoutRadioactiveTide");
      _chance = Rename<IntegerField>(chanceRow, BadtideChanceName, "RadioactiveTideChance");
      _minDuration = Rename<IntegerField>(durationRow, BadtideMinDurationName, "MinRadioactiveTideDuration");
      _maxDuration = Rename<IntegerField>(durationRow, BadtideMaxDurationName, "MaxRadioactiveTideDuration");

      // Registered once; the native controller registers its fields again on
      // every Initialize, these never need it.
      TextFields.InitializeIntegerField(_cyclesWithout, RadioactiveTideTuning.CyclesWithoutTideLowest,
        RadioactiveTideTuning.CyclesWithoutTideLowest, RadioactiveTideTuning.CyclesWithoutTideHighest, _ => OnChanged());
      TextFields.InitializeIntegerField(_chance, RadioactiveTideTuning.ChancePercentLowest,
        RadioactiveTideTuning.ChancePercentLowest, RadioactiveTideTuning.ChancePercentHighest, _ => OnChanged());
      TextFields.InitializeIntegerField(_minDuration, RadioactiveTideTuning.DurationLowest,
        RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest, _ => OnChanged());
      TextFields.InitializeIntegerField(_maxDuration, RadioactiveTideTuning.DurationLowest,
        RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest, _ => OnChanged());
      _enabled.RegisterValueChangedCallback(_ => OnChanged());

      var parent = nativeBadtide.parent;
      int index = parent.IndexOf(nativeBadtide);
      parent.Insert(index + 1, toggleRow);
      parent.Insert(index + 2, _wrapper);
    }

    // Native OnCustomizeButtonClicked (registered first, so it runs first)
    // has filled the native fields from the selected preset.
    private void OnCustomize() {
      _customActive = true;
      Apply(RadioactiveTideGameModes.Require(_selectedPreset, $"game mode {_loc.T(_selectedPreset.DisplayNameLocKey)}"));
      OnChanged();
    }

    private void Apply(RadioactiveTideGameModeSpec spec) {
      if (spec.Duration == null) throw new InvalidOperationException("Radioactive tide: a game mode's RadioactiveTideGameModeSpec has no Duration");
      _enabled.SetValueWithoutNotify(spec.Enabled);
      _cyclesWithout.SetValueWithoutNotify(spec.CyclesWithoutTide);
      _chance.SetValueWithoutNotify(spec.ChancePercent);
      _minDuration.SetValueWithoutNotify(spec.Duration.Min);
      _maxDuration.SetValueWithoutNotify(spec.Duration.Max);
      _wrapper.ToggleDisplayStyle(spec.Enabled);
      Validate();
    }

    // As native OnGameModeChanged: validate, show the rows of an enabled
    // tide, and re-evaluate the Start button (native UpdateNextButton =
    // SetEnabled(TryGetValidatedGameMode), which includes these rows).
    private void OnChanged() {
      _wrapper.ToggleDisplayStyle(_enabled.value);
      Validate();
      if (_customActive) _nextButton.SetEnabled(_customController.TryGetValidatedGameMode(out _));
    }

    // Like native ValidateGameMode, a switched-off section is not checked.
    private bool Validate() {
      foreach (var field in new[] { _cyclesWithout, _chance, _minDuration, _maxDuration }) field.RemoveFromClassList(InvalidInputClass);
      if (!_enabled.value) return true;
      bool valid = InRange(_cyclesWithout, RadioactiveTideTuning.CyclesWithoutTideLowest, RadioactiveTideTuning.CyclesWithoutTideHighest);
      valid &= InRange(_chance, RadioactiveTideTuning.ChancePercentLowest, RadioactiveTideTuning.ChancePercentHighest);
      valid &= InRange(_minDuration, RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest);
      valid &= InRange(_maxDuration, RadioactiveTideTuning.DurationLowest, RadioactiveTideTuning.DurationHighest);
      if (_minDuration.value > _maxDuration.value) {
        _minDuration.AddToClassList(InvalidInputClass);
        _maxDuration.AddToClassList(InvalidInputClass);
        valid = false;
      }
      return valid;
    }

    private static bool InRange(IntegerField field, int lowest, int highest) {
      if (field.value >= lowest && field.value <= highest) return true;
      field.AddToClassList(InvalidInputClass);
      return false;
    }

    private void Relabel(VisualElement row, string locKey) {
      var label = row.Q<Label>(className: SettingLabelClass) ?? throw Changed($"row {row.name} has no {SettingLabelClass} label");
      label.text = _loc.T(locKey);
    }

    private static VisualElement Take(VisualElement copy, string nativeName, string newName) {
      var element = Rename<VisualElement>(copy, nativeName, newName);
      element.RemoveFromHierarchy();
      return element;
    }

    private static T Rename<T>(VisualElement parent, string nativeName, string newName) where T : VisualElement {
      var element = Required<T>(parent, nativeName);
      element.name = newName;
      return element;
    }

    private static T Required<T>(VisualElement parent, string name) where T : VisualElement =>
      parent.Q<T>(name) ?? throw Changed($"no {typeof(T).Name} named {name}");

    private static InvalidOperationException Changed(string detail) =>
      new InvalidOperationException($"Radioactive tide: the native new-game screen changed ({detail}; Timberborn 1.1.2.8 UI/Views/{RadioactiveTideNewGameNative.PanelView})");
  }

  // The native new-game members the radioactive tide relies on (Timberborn
  // 1.1.2.8), checked at mod start by RadioactiveTideNewGameModStarter before
  // it patches: a game update that changes them throws there instead of
  // drifting.
  // - NewGameModePanel._root is private; it is the only route to the panel's
  //   elements (GetPanel() also marks the panel visible and refreshes its
  //   summary for a faction and map not chosen yet).
  // - Every custom game starts through the patched method: StartNewGame and
  //   UpdateNextButton call the panel's TryGetValidatedGameMode, which asks
  //   CustomNewGameModeController.TryGetValidatedGameMode, whose GetGameMode
  //   builds the custom GameModeSpec; StartNewGame hands it to
  //   GameSceneLoader.StartNewGame.
  // - OnCustomizeButtonClicked fills the custom fields through
  //   CustomNewGameModeController.Initialize; Load loads the panel view.
  public static class RadioactiveTideNewGameNative {
    public const string PanelView = "MainMenu/NewGameModePanel";
    private const BindingFlags Instance = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic;
    private static FieldInfo _root;

    public static MethodInfo CustomTryGetValidatedGameMode() {
      var method = typeof(CustomNewGameModeController).GetMethod(nameof(CustomNewGameModeController.TryGetValidatedGameMode), Instance, null,
        new[] { typeof(GameModeSpec).MakeByRefType() }, null);
      if (method == null || method.ReturnType != typeof(bool) || !method.IsPublic || !method.GetParameters()[0].IsOut || method.GetParameters()[0].Name != "gameMode")
        throw Changed("CustomNewGameModeController.TryGetValidatedGameMode(out GameModeSpec gameMode) : bool");
      return method;
    }

    public static void Verify() {
      PanelRootField();
      var custom = CustomTryGetValidatedGameMode();
      if (NativeIl.Inlinable(custom)) throw Changed("CustomNewGameModeController.TryGetValidatedGameMode became small enough to inline");
      var getGameMode = Method(typeof(CustomNewGameModeController), "GetGameMode", typeof(GameModeSpec));
      if (!NativeIl.Calls(custom, getGameMode)) throw Changed("CustomNewGameModeController.TryGetValidatedGameMode no longer builds the mode with GetGameMode");
      var panelTry = Method(typeof(NewGameModePanel), "TryGetValidatedGameMode", typeof(bool), typeof(GameModeSpec).MakeByRefType());
      if (!NativeIl.Calls(panelTry, custom)) throw Changed("NewGameModePanel.TryGetValidatedGameMode no longer asks CustomNewGameModeController");
      var start = Method(typeof(NewGameModePanel), "StartNewGame", typeof(void));
      var sceneStart = Method(typeof(GameSceneLoader), nameof(GameSceneLoader.StartNewGame), typeof(void), typeof(NewGameConfiguration));
      if (!NativeIl.Calls(start, panelTry) || !NativeIl.Calls(start, sceneStart))
        throw Changed("NewGameModePanel.StartNewGame no longer starts the validated mode through GameSceneLoader.StartNewGame");
      if (!NativeIl.Calls(Method(typeof(NewGameModePanel), "UpdateNextButton", typeof(void)), panelTry))
        throw Changed("NewGameModePanel.UpdateNextButton no longer enables Start from TryGetValidatedGameMode");
      var initialize = Method(typeof(CustomNewGameModeController), nameof(CustomNewGameModeController.Initialize), typeof(void),
        typeof(VisualElement), typeof(GameModeSpec), typeof(Action));
      if (!NativeIl.Calls(Method(typeof(NewGameModePanel), "OnCustomizeButtonClicked", typeof(void)), initialize))
        throw Changed("NewGameModePanel.OnCustomizeButtonClicked no longer fills the custom fields from the preset");
      if (!NativeIl.LoadsString(Method(typeof(NewGameModePanel), nameof(NewGameModePanel.Load), typeof(void)), PanelView))
        throw Changed($"NewGameModePanel.Load no longer loads {PanelView}");
    }

    public static VisualElement PanelRoot(NewGameModePanel panel) {
      if (panel == null) throw new ArgumentNullException(nameof(panel));
      return (VisualElement)PanelRootField().GetValue(panel);
    }

    private static FieldInfo PanelRootField() {
      if (_root != null) return _root;
      var field = typeof(NewGameModePanel).GetField("_root", Instance);
      if (field?.FieldType != typeof(VisualElement)) throw Changed("NewGameModePanel._root : VisualElement");
      return _root = field;
    }

    private static MethodInfo Method(Type type, string name, Type returnType, params Type[] parameters) {
      var method = type.GetMethod(name, Instance, null, parameters, null);
      if (method == null || method.ReturnType != returnType)
        throw Changed($"{type.Name}.{name}({string.Join(", ", parameters.Select(p => p.Name))}) : {returnType.Name}");
      return method;
    }

    private static InvalidOperationException Changed(string member) =>
      new InvalidOperationException($"Radioactive tide: native new-game API changed; expected {member} (Timberborn 1.1.2.8)");
  }
}
