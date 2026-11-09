using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Linq;
using Bindito.Core;
using HarmonyLib;
using Timberborn.BlueprintSystem;
using Timberborn.CoreUI;
using Timberborn.Localization;
using Timberborn.MainMenuPanels;
using Timberborn.NewGameConfigurationSystem;
using Timberborn.SingletonSystem;
using ModdableFluids;
using ModdableFluids.Runtime.Prototype;
using UnityEngine.UIElements;

namespace ModdableFluids.Tides.Prototype {
  [Context("MainMenu")]
  public sealed class FluidTideNewGameConfigurator : Configurator {
    protected override void Configure() {
      if (!WorkerAcceptanceRun.Enabled) return;
      var host = ModdableFluidsEntry.Host;
      host.Freeze();
      if (host.Tides.Count == 0) return;
      Bind<FluidTideNewGameSettings>().AsSingleton();
    }
  }

  /// <summary>
  /// Tide rows on the native new-game screen (Timberborn 1.1.2.8 NewGameModePanel and CustomNewGameModeController),
  /// Deep Frontier's radioactive tide rows made generic. A preset needs nothing: its tide settings follow from its own
  /// weather (FluidTideModes) or its own FluidTideGameModeSpec, which the Game scene resolves the same way. For the custom
  /// mode this adds, after the native badtide rows: "Tide chance" (the shared budget), then for each registered tide in
  /// ordinal order its toggle and the rows "cycles without", "share of the tide chance" (its weight) and "duration". The
  /// rows are the native badtide rows themselves, moved from fresh copies of the native panel view (VisualElementLoader),
  /// renamed and relabelled; they clamp on focus-out with the native TextFields.InitializeIntegerField, and invalid values
  /// get the native invalid class and keep Start disabled. Customize fills them from the selected preset, as the native
  /// fields are. A postfix on CustomNewGameModeController.TryGetValidatedGameMode (the one place that both builds the
  /// custom mode and enables Start) attaches the values to the custom mode as a FluidTideGameModeSpec.
  /// The patch is installed when the main menu builds this singleton and removed when the main menu unloads.
  /// </summary>
  public sealed class FluidTideNewGameSettings : IPostLoadableSingleton, IUnloadableSingleton {
    public const string OwnerId = "ModdableFluids.TidesNewGame";
    internal const string BudgetLoc = "ModdableFluids.NewGame.TideBudget", CyclesLoc = "ModdableFluids.NewGame.TideCyclesWithout",
      WeightLoc = "ModdableFluids.NewGame.TideWeight", DurationLoc = "ModdableFluids.NewGame.TideDuration";
    private const string ModesName = "Modes", CustomizeButtonName = "CustomizeButton", NextButtonName = "NextButton";
    private const string BadtideToggleRowName = "BadtideEnabledWrapper", BadtideToggleName = "BadtideEnabled", BadtideWrapperName = "BadtideWrapper";
    private const string BadtideCyclesRowName = "CyclesBeforeRandomizingBadtideWrapper", BadtideCyclesName = "CyclesBeforeRandomizingBadtide";
    private const string BadtideChanceRowName = "ChanceForBadtideWrapper", BadtideChanceName = "ChanceForBadtide";
    private const string BadtideDurationRowName = "BadtideDurationWrapper", BadtideMinDurationName = "MinBadtideDuration", BadtideMaxDurationName = "MaxBadtideDuration";
    private const string BadtideHandicapRowName = "BadtideDurationHandicapWrapper", SettingLabelClass = "new-game-mode-panel__setting-label";
    private const string InvalidInputClass = "new-game-mode-panel__setting-input--invalid";

    private sealed class TideRows {
      internal FluidTideDefinition Tide;
      internal Toggle Enabled;
      internal VisualElement Wrapper;
      internal IntegerField CyclesWithout, Weight, MinDuration, MaxDuration;
    }

    internal static FluidTideNewGameSettings Current { get; private set; }
    private static readonly HashSet<string> LoggedDerivations = new HashSet<string>();

    private readonly NewGameModePanel _panel;
    private readonly CustomNewGameModeController _customController;
    private readonly GameModeSpecService _gameModeSpecService;
    private readonly VisualElementLoader _visualElementLoader;
    private readonly ILoc _loc;
    private readonly FluidTideRegistry _tides;
    private readonly FluidTidePatchSet _patches = new FluidTidePatchSet(OwnerId);
    private readonly List<TideRows> _rows = new List<TideRows>();
    private bool _ready, _customActive;
    private GameModeSpec _selectedPreset;
    private Button _nextButton;
    private IntegerField _budget;

    public FluidTideNewGameSettings(NewGameModePanel panel, CustomNewGameModeController customController, GameModeSpecService gameModeSpecService,
        VisualElementLoader visualElementLoader, ILoc loc) {
      _panel = panel; _customController = customController; _gameModeSpecService = gameModeSpecService; _visualElementLoader = visualElementLoader; _loc = loc;
      if (Current != null) throw new InvalidOperationException("Moddable Fluids tides: a new-game screen is already active; the previous main menu was not unloaded");
      _tides = ModdableFluidsEntry.Host.Tides;
      var target = FluidTideNative.VerifyNewGame();
      _patches.Install(new[] { target }, harmony => harmony.Patch(target, postfix: new HarmonyMethod(typeof(FluidTideNewGameSettings), nameof(Postfix))));
      Current = this;
    }

    public void PostLoad() {
      var root = FluidTideNative.NewGamePanelRoot(_panel) ?? throw Changed("NewGameModePanel has no root after Load");
      var presets = _gameModeSpecService.GetSpecsOrdered();
      foreach (var preset in presets) Resolve(preset, log: true);
      TrackPresetButtons(root, presets);
      _selectedPreset = _gameModeSpecService.GetDefaultSpec();
      AddRows(root);
      Required<Button>(root, CustomizeButtonName).RegisterCallback<ClickEvent>(_ => OnCustomize());
      _nextButton = Required<Button>(root, NextButtonName);
      Apply(Resolve(_selectedPreset, log: false));
      _ready = true;
    }

    public void Unload() {
      try { _patches.Uninstall(); }
      finally { if (Current == this) Current = null; }
    }

    // Postfix of CustomNewGameModeController.TryGetValidatedGameMode. Validated (and marked) even when a native field is
    // invalid, as the native validation marks every invalid field at once.
    private static void Postfix(ref bool __result, ref GameModeSpec gameMode) {
      var current = Current ?? throw new InvalidOperationException("Moddable Fluids tides: the custom game mode was built outside the main menu's new-game screen");
      if (!current._ready) throw new InvalidOperationException("Moddable Fluids tides: the custom game mode was built before the new-game screen finished loading");
      bool valid = current.TryGetValidated(out var settings);
      if (!__result) return;
      if (!valid) { __result = false; gameMode = null; return; }
      gameMode = WithTides(gameMode, FluidTideGameModeSpec.From(settings));
    }

    /// <summary>A copy of the custom mode whose blueprint also holds the tide settings (native Blueprint copies each spec).</summary>
    internal static GameModeSpec WithTides(GameModeSpec customMode, FluidTideGameModeSpec tides) {
      if (customMode?.Blueprint == null || customMode.Blueprint.Specs.Length != 1)
        throw new InvalidOperationException("Moddable Fluids tides: the native custom game mode is no longer a lone GameModeSpec");
      var copy = new Blueprint(customMode.Blueprint.Name, new ComponentSpec[] { customMode, tides }, ImmutableArray<Blueprint>.Empty).GetSpec<GameModeSpec>();
      if (copy?.GetSpec<FluidTideGameModeSpec>() == null) throw new InvalidOperationException("Moddable Fluids tides: the custom game mode copy lost its tide settings");
      return copy;
    }

    private FluidTideSaveSettings Resolve(GameModeSpec preset, bool log) {
      string name = _loc.T(preset.DisplayNameLocKey);
      if (preset.Blueprint == null) throw new InvalidOperationException("Moddable Fluids tides: game mode " + name + " has no blueprint, so its tide settings cannot be read");
      var weather = FluidTideSettingsStore.Weather(preset, "game mode " + name);
      var own = preset.GetSpec<FluidTideGameModeSpec>();
      if (own != null) return own.ToSettings(_tides, weather, "game mode " + name);
      var settings = FluidTideModes.Defaults(_tides, weather, out var derivations);
      if (log && LoggedDerivations.Add((preset.Blueprint.Name ?? name) + ": " + settings))
        UnityEngine.Debug.Log("[ModdableFluids] Tide settings for game mode " + name + ": " + settings + "\n  " + string.Join("\n  ", derivations));
      return settings;
    }

    private bool TryGetValidated(out FluidTideSaveSettings settings) {
      settings = null;
      if (!Validate()) return false;
      settings = new FluidTideSaveSettings(_budget.value, _rows.Select(r => new FluidTideSettings(r.Tide.Id, r.Enabled.value, r.Weight.value,
        r.CyclesWithout.value, r.MinDuration.value, r.MaxDuration.value)));
      return true;
    }

    // Native NewGameModePanel.Load adds one mode button per spec of GetSpecsOrdered, in that order, labelled with its name.
    private void TrackPresetButtons(VisualElement root, ImmutableArray<GameModeSpec> presets) {
      var buttons = Required<VisualElement>(root, ModesName).Query<Button>().ToList();
      if (buttons.Count != presets.Length) throw Changed("the new-game screen shows " + buttons.Count + " mode buttons for " + presets.Length + " game modes");
      for (int i = 0; i < presets.Length; i++) {
        var preset = presets[i];
        if (buttons[i].text != _loc.T(preset.DisplayNameLocKey)) throw Changed("mode button " + i + " reads '" + buttons[i].text + "', expected '" + _loc.T(preset.DisplayNameLocKey) + "'");
        buttons[i].RegisterCallback<ClickEvent>(_ => { _selectedPreset = preset; _customActive = false; });
      }
    }

    private void AddRows(VisualElement root) {
      var nativeBadtide = Required<VisualElement>(root, BadtideWrapperName);
      var parent = nativeBadtide.parent;
      int index = parent.IndexOf(nativeBadtide) + 1;
      var budgetCopy = _visualElementLoader.LoadVisualElement(FluidTideNative.NewGamePanelView);
      var budgetRow = Take(budgetCopy, BadtideChanceRowName, "ModdableFluidsTideBudgetWrapper");
      Relabel(budgetRow, _loc.T(BudgetLoc));
      _budget = Rename<IntegerField>(budgetRow, BadtideChanceName, "ModdableFluidsTideBudget");
      TextFields.InitializeIntegerField(_budget, FluidTideRules.BudgetPercentLowest, FluidTideRules.BudgetPercentLowest, FluidTideRules.BudgetPercentHighest, _ => OnChanged());
      parent.Insert(index++, budgetRow);
      foreach (var tide in _tides.Tides) {
        string key = tide.LocalName, name = _loc.T(tide.DisplayNameLocKey);
        var copy = _visualElementLoader.LoadVisualElement(FluidTideNative.NewGamePanelView);
        var rows = new TideRows { Tide = tide };
        var toggleRow = Take(copy, BadtideToggleRowName, "ModdableFluidsTide" + key + "EnabledWrapper");
        rows.Enabled = Rename<Toggle>(toggleRow, BadtideToggleName, "ModdableFluidsTide" + key + "Enabled");
        Relabel(toggleRow, name);
        rows.Wrapper = Take(copy, BadtideWrapperName, "ModdableFluidsTide" + key + "Wrapper");
        Required<VisualElement>(rows.Wrapper, BadtideHandicapRowName).RemoveFromHierarchy();
        var cyclesRow = Rename<VisualElement>(rows.Wrapper, BadtideCyclesRowName, "ModdableFluidsTide" + key + "CyclesWrapper");
        var weightRow = Rename<VisualElement>(rows.Wrapper, BadtideChanceRowName, "ModdableFluidsTide" + key + "WeightWrapper");
        var durationRow = Rename<VisualElement>(rows.Wrapper, BadtideDurationRowName, "ModdableFluidsTide" + key + "DurationWrapper");
        if (rows.Wrapper.childCount != 3 || rows.Wrapper[0] != cyclesRow || rows.Wrapper[1] != weightRow || rows.Wrapper[2] != durationRow)
          throw Changed("the badtide rows are no longer cycles, chance, duration and handicap");
        Relabel(cyclesRow, _loc.T(CyclesLoc, name));
        Relabel(weightRow, _loc.T(WeightLoc, name));
        Relabel(durationRow, _loc.T(DurationLoc, name));
        rows.CyclesWithout = Rename<IntegerField>(cyclesRow, BadtideCyclesName, "ModdableFluidsTide" + key + "Cycles");
        rows.Weight = Rename<IntegerField>(weightRow, BadtideChanceName, "ModdableFluidsTide" + key + "Weight");
        rows.MinDuration = Rename<IntegerField>(durationRow, BadtideMinDurationName, "ModdableFluidsTide" + key + "MinDuration");
        rows.MaxDuration = Rename<IntegerField>(durationRow, BadtideMaxDurationName, "ModdableFluidsTide" + key + "MaxDuration");
        // Registered once; the native controller re-registers its own fields on every Initialize, these never need it.
        TextFields.InitializeIntegerField(rows.CyclesWithout, FluidTideRules.CyclesWithoutTideLowest, FluidTideRules.CyclesWithoutTideLowest, FluidTideRules.CyclesWithoutTideHighest, _ => OnChanged());
        TextFields.InitializeIntegerField(rows.Weight, FluidTideRules.WeightLowest, FluidTideRules.WeightLowest, FluidTideRules.WeightHighest, _ => OnChanged());
        TextFields.InitializeIntegerField(rows.MinDuration, FluidTideRules.DurationLowest, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest, _ => OnChanged());
        TextFields.InitializeIntegerField(rows.MaxDuration, FluidTideRules.DurationLowest, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest, _ => OnChanged());
        rows.Enabled.RegisterValueChangedCallback(_ => OnChanged());
        parent.Insert(index++, toggleRow);
        parent.Insert(index++, rows.Wrapper);
        _rows.Add(rows);
      }
    }

    // Native OnCustomizeButtonClicked (registered first, so it runs first) has filled the native fields from the preset.
    private void OnCustomize() {
      _customActive = true;
      Apply(Resolve(_selectedPreset, log: false));
      OnChanged();
    }

    private void Apply(FluidTideSaveSettings settings) {
      _budget.SetValueWithoutNotify(settings.BudgetPercent);
      foreach (var rows in _rows) {
        var tide = settings.Get(rows.Tide.Id);
        rows.Enabled.SetValueWithoutNotify(tide.Enabled);
        rows.CyclesWithout.SetValueWithoutNotify(tide.CyclesWithoutTide);
        rows.Weight.SetValueWithoutNotify(tide.Weight);
        rows.MinDuration.SetValueWithoutNotify(tide.MinDurationDays);
        rows.MaxDuration.SetValueWithoutNotify(tide.MaxDurationDays);
        rows.Wrapper.ToggleDisplayStyle(tide.Enabled);
      }
      Validate();
    }

    // As native OnGameModeChanged: validate, show an enabled tide's rows and re-evaluate Start (native UpdateNextButton).
    private void OnChanged() {
      foreach (var rows in _rows) rows.Wrapper.ToggleDisplayStyle(rows.Enabled.value);
      Validate();
      if (_customActive) _nextButton.SetEnabled(_customController.TryGetValidatedGameMode(out _));
    }

    // Like native ValidateGameMode, a switched-off tide is not checked.
    private bool Validate() {
      _budget.RemoveFromClassList(InvalidInputClass);
      bool valid = InRange(_budget, FluidTideRules.BudgetPercentLowest, FluidTideRules.BudgetPercentHighest);
      foreach (var rows in _rows) {
        foreach (var field in new[] { rows.CyclesWithout, rows.Weight, rows.MinDuration, rows.MaxDuration }) field.RemoveFromClassList(InvalidInputClass);
        if (!rows.Enabled.value) continue;
        valid &= InRange(rows.CyclesWithout, FluidTideRules.CyclesWithoutTideLowest, FluidTideRules.CyclesWithoutTideHighest);
        valid &= InRange(rows.Weight, FluidTideRules.WeightLowest, FluidTideRules.WeightHighest);
        valid &= InRange(rows.MinDuration, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest);
        valid &= InRange(rows.MaxDuration, FluidTideRules.DurationLowest, FluidTideRules.DurationHighest);
        if (rows.MinDuration.value > rows.MaxDuration.value) {
          rows.MinDuration.AddToClassList(InvalidInputClass);
          rows.MaxDuration.AddToClassList(InvalidInputClass);
          valid = false;
        }
      }
      return valid;
    }

    private static bool InRange(IntegerField field, int lowest, int highest) {
      if (field.value >= lowest && field.value <= highest) return true;
      field.AddToClassList(InvalidInputClass);
      return false;
    }

    private static void Relabel(VisualElement row, string text) =>
      (row.Q<Label>(className: SettingLabelClass) ?? throw Changed("row " + row.name + " has no " + SettingLabelClass + " label")).text = text;

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
      parent.Q<T>(name) ?? throw Changed("no " + typeof(T).Name + " named " + name);

    private static InvalidOperationException Changed(string detail) =>
      new InvalidOperationException("Moddable Fluids tides: the native new-game screen changed (" + detail + "; Timberborn " + FluidTideNative.GameVersion + " UI/Views/" + FluidTideNative.NewGamePanelView + ")");
  }
}
