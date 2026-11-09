using System;
using System.Linq;
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.CoreUI;
using Timberborn.DropdownSystem;
using Timberborn.EntityPanelSystem;
using Timberborn.EntityUndoSystem;
using Timberborn.GameFactionSystem;
using Timberborn.Goods;
using Timberborn.Localization;
using Timberborn.SingletonSystem;
using Timberborn.TooltipSystem;
using Timberborn.UIFormatters;
using Timberborn.UndoSystem;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.DeepOre {
  internal static class MineralDepositLoc {
    public const string RechargeNext = "DeepFrontier.MineralDeposit.Recharge.Next";
    public const string RechargeRule = "DeepFrontier.MineralDeposit.Recharge.Rule";
  }
  // The deposit's stock and its recharge shown with the game's own entity-panel views (decompiled
  // 1.1.2.8):
  // - the stock: the native RuinFragment layout (good icon, name and amount remaining), as a ruin
  //   shows its scrap;
  // - the recharge: the native ResourceYieldFragment layout as GatherableFragment fills it for a
  //   bush regrowing its yield: the calendar-cycle icon, the recharge time, the progress and the
  //   amount it brings back; greyed (the native resource-yield--inactive class, progress hidden)
  //   while the deposit still holds ore. A line under it gives the days left while it recharges.
  // Nothing here depends on another singleton's Load.
  internal sealed class DeepOreStockView {
    public VisualElement Root { get; }
    private readonly Label _remaining, _name;
    private readonly Image _icon;

    public DeepOreStockView(VisualElementLoader loader) {
      Root = loader.LoadVisualElement("Game/EntityPanel/RuinFragment");
      _remaining = Root.Q<Label>("GoodRemaining");
      _name = Root.Q<Label>("GoodName");
      _icon = Root.Q<Image>("GoodIcon");
    }

    public void Show(string name, Sprite icon, int amount) {
      _name.text = name;
      _icon.sprite = icon;
      _remaining.text = amount.ToString();
    }
  }

  internal sealed class DeepOreRechargeView {
    private const string CalendarCycleClass = "resource-yield__icon--calendar-cycle";
    private const string InactiveClass = "resource-yield--inactive";
    private readonly ILoc _loc;
    private readonly Label _progress, _time, _amount, _next;
    private readonly Image _icon;
    private readonly Phrase _timePhrase = Phrase.New().FormatDays<float>("F0");
    private readonly Phrase _progressPhrase = Phrase.New().FormatPercentFloored();
    private string _rule = "";
    public VisualElement Root { get; }

    public DeepOreRechargeView(VisualElementLoader loader, ITooltipRegistrar tooltips, ILoc loc) {
      _loc = loc;
      Root = loader.LoadVisualElement("Game/EntityPanel/ResourceYieldFragment");
      _progress = Root.Q<Label>("ProgressText");
      _time = Root.Q<Label>("GrowthTime");
      _amount = Root.Q<Label>("YieldAmount");
      _icon = Root.Q<Image>("YieldIcon");
      Root.Q<VisualElement>("Calendar").AddToClassList(CalendarCycleClass);
      _next = new Label();
      _next.AddToClassList("entity-panel__text");
      Root.Add(_next);
      tooltips.Register(Root, () => _rule);
    }

    public void Show(MineralDeposit deposit, Sprite icon) {
      var spec = deposit.Spec;
      _time.text = _loc.T(_timePhrase, spec.RechargeTimeInDays);
      _amount.text = spec.RechargeAmount.ToString();
      _icon.sprite = icon;
      _rule = _loc.T(MineralDepositLoc.RechargeRule, spec.RechargeAmount, spec.RechargeTimeInDays.ToString("0.#"));
      bool recharging = deposit.IsRecharging;
      _progress.text = _loc.T(_progressPhrase, deposit.RechargeProgress);
      _progress.ToggleDisplayStyle(recharging);
      Root.EnableInClassList(InactiveClass, !recharging);
      _next.text = recharging ? _loc.T(MineralDepositLoc.RechargeNext, spec.RechargeAmount, deposit.RechargeDaysLeft.ToString("0.0")) : "";
      _next.ToggleDisplayStyle(recharging);
    }
  }

  // Deep Ore Source: its stock and recharge.
  internal sealed class MineralDepositFragment : IEntityPanelFragment {
    private readonly VisualElementLoader _loader;
    private readonly ITooltipRegistrar _tooltips;
    private readonly IGoodService _goods;
    private readonly ILoc _loc;
    private readonly FactionService _factions;
    private VisualElement _root;
    private DeepOreStockView _stock;
    private DeepOreRechargeView _recharge;
    private MineralDeposit _deposit;
    private GoodSpec _good;

    public MineralDepositFragment(VisualElementLoader loader, ITooltipRegistrar tooltips, IGoodService goods, ILoc loc,
        FactionService factions) {
      _loader = loader; _tooltips = tooltips; _goods = goods; _loc = loc; _factions = factions;
    }

    public VisualElement InitializeFragment() {
      _root = new VisualElement();
      _stock = new DeepOreStockView(_loader);
      _recharge = new DeepOreRechargeView(_loader, _tooltips, _loc);
      _root.Add(_stock.Root);
      _root.Add(_recharge.Root);
      _root.ToggleDisplayStyle(visible: false);
      return _root;
    }

    public void ShowFragment(BaseComponent entity) {
      _deposit = entity.GetComponent<MineralDeposit>();
      if (!_deposit) return;
      // Iron Teeth goods (DeepFrontierFaction); a map placed with these
      // objects and played by another faction has no such goods to show.
      if (!DeepFrontierFaction.Applies(_factions)) { _deposit = null; return; }
      _good = _goods.GetGood(_deposit.Spec.GoodId);
      UpdateFragment();
      _root.ToggleDisplayStyle(visible: true);
    }

    public void ClearFragment() {
      _deposit = null;
      _good = null;
      _root.ToggleDisplayStyle(visible: false);
    }

    public void UpdateFragment() {
      if (!_deposit) return;
      _stock.Show(_good.PluralDisplayName.Value, _good.IconSmall.Value, _deposit.Amount);
      _recharge.Show(_deposit, _good.IconSmall.Value);
    }
  }

  // Shared stock/recovery panel for the three visible mineral outcrops.
  [Context("Game")]
  public sealed class DeepOrePanelConfigurator : Configurator {
    protected override void Configure() {
      Bind<MineralDepositFragment>().AsSingleton();
      MultiBind<EntityPanelModule>().ToProvider<EntityPanelModuleProvider>().AsSingleton();
    }

    // Where the native GatherableFragment sits (GatheringUIConfigurator).
    private sealed class EntityPanelModuleProvider : IProvider<EntityPanelModule> {
      private readonly MineralDepositFragment _deposit;
      public EntityPanelModuleProvider(MineralDepositFragment deposit) { _deposit = deposit; }

      public EntityPanelModule Get() {
        var builder = new EntityPanelModule.Builder();
        builder.AddMiddleFragment(_deposit);
        return builder.Build();
      }
    }
  }

  // Map editor: the deposit's amount, in the native fixed stockpile fragment's layout (its amount
  // field; the good is fixed, so the good dropdown is hidden), with native undo as
  // FixedStockpileFragment records it.
  internal sealed class MineralDepositAmountFragment : IEntityPanelFragment, ILoadableSingleton {
    private readonly EventBus _eventBus;
    private readonly VisualElementLoader _loader;
    private readonly EntityChangeRecorderFactory _changeRecorders;
    private VisualElement _root;
    private IntegerField _amount;
    private MineralDeposit _deposit;

    public MineralDepositAmountFragment(EventBus eventBus, VisualElementLoader loader, EntityChangeRecorderFactory changeRecorders) {
      _eventBus = eventBus; _loader = loader; _changeRecorders = changeRecorders;
    }

    public void Load() { _eventBus.Register(this); }

    public VisualElement InitializeFragment() {
      _root = _loader.LoadVisualElement("MapEditor/EntityPanel/FixedStockpileFragment");
      _root.Q<Dropdown>("Goods").ToggleDisplayStyle(false);
      _amount = _root.Q<IntegerField>("Amount");
      _amount.isDelayed = true;
      _amount.RegisterValueChangedCallback(OnAmountChanged);
      _root.ToggleDisplayStyle(visible: false);
      return _root;
    }

    public void ShowFragment(BaseComponent entity) {
      _deposit = entity.GetComponent<MineralDeposit>();
      if (!_deposit) return;
      _amount.SetValueWithoutNotify(_deposit.Amount);
      _root.ToggleDisplayStyle(visible: true);
    }

    public void ClearFragment() {
      _deposit = null;
      _root.ToggleDisplayStyle(visible: false);
    }

    public void UpdateFragment() { }

    [OnEvent]
    public void OnUndoStateChanged(UndoStateChangedEvent undoStateChangedEvent) {
      if (_deposit) _amount.SetValueWithoutNotify(_deposit.Amount);
    }

    private void OnAmountChanged(ChangeEvent<int> changeEvent) {
      if (!_deposit) return;
      int amount = Math.Clamp(changeEvent.newValue, 0, _deposit.Spec.Capacity);
      using (_changeRecorders.CreateChangeRecorder(_deposit)) _deposit.SetAmount(amount);
      _amount.SetValueWithoutNotify(amount);
    }
  }

  [Context("MapEditor")]
  public sealed class DeepOreMapEditorPanelConfigurator : Configurator {
    protected override void Configure() {
      Bind<MineralDepositAmountFragment>().AsSingleton();
      MultiBind<EntityPanelModule>().ToProvider<EntityPanelModuleProvider>().AsSingleton();
    }

    // Where the native FixedStockpileFragment sits (MapEditorStockpilesUIConfigurator).
    private sealed class EntityPanelModuleProvider : IProvider<EntityPanelModule> {
      private readonly MineralDepositAmountFragment _amount;
      public EntityPanelModuleProvider(MineralDepositAmountFragment amount) { _amount = amount; }

      public EntityPanelModule Get() {
        var builder = new EntityPanelModule.Builder();
        builder.AddBottomFragment(_amount);
        return builder.Build();
      }
    }
  }
}
