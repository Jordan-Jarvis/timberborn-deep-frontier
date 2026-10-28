#if !UNITY_EDITOR
using Bindito.Core;
using Timberborn.BaseComponentSystem;
using Timberborn.Goods;
using Timberborn.Localization;
using TimberUi.CommonUi;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.Meltdown {
  // Reactor entity panel: core heat with its trend and time to the next
  // threshold, each cause with its live value, what a meltdown does, the
  // SCRAM / restart buttons and the auto-restart choice.
  internal sealed class ReactorCorePanel : BaseEntityPanelFragment<ReactorCore> {
    private readonly ILoc _loc;
    private readonly IGoodService _goods;
    private Label _heat, _state, _eta, _causes, _restartHint, _rules;
    private Button _scram, _restart;
    private Toggle _autoRestart;

    public ReactorCorePanel(ILoc loc, IGoodService goods) { _loc = loc; _goods = goods; }

    private string F(string key, params object[] args) => string.Format(_loc.T(key), args);
    private static int Pct(float value) => ReactorCore.Pct(value);
    private static int Hours(float value) => ReactorCore.Hours(value);

    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T(MeltdownLoc.PanelTitle), bold: true);
      _heat = Wrapped(); _state = Wrapped(); _eta = Wrapped(); _causes = Wrapped();
      _scram = panel.AddGameButton(_loc.T(MeltdownLoc.PanelScramButton), () => {
        if (component && component.CanScram) component.ManualScram();
        UpdateFragment();
      }, stretched: true);
      _restart = panel.AddGameButton(_loc.T(MeltdownLoc.PanelRestartButton), () => {
        if (component && component.CanRestart) component.Restart();
        UpdateFragment();
      }, stretched: true);
      _restartHint = Wrapped();
      _autoRestart = panel.AddGamePanelToggle(_loc.T(MeltdownLoc.PanelAutoRestart),
        onValueChanged: value => { if (component) component.SetAutoRestart(value); });
      _rules = Wrapped();
    }

    private Label Wrapped() { var label = panel.AddGameLabel(); label.style.whiteSpace = WhiteSpace.Normal; return label; }

    public override void ShowFragment(BaseComponent entity) { base.ShowFragment(entity); UpdateFragment(); }

    public override void UpdateFragment() {
      if (!component) return;
      var core = component;
      var s = core.Spec;
      float rate = core.HeatRatePerHour;
      string trend = rate > 0f ? F(MeltdownLoc.PanelRising, (rate * 100f).ToString("0.#"))
        : rate < 0f && core.Heat > 0f ? F(MeltdownLoc.PanelFalling, (-rate * 100f).ToString("0.#")) : "";
      _heat.text = F(MeltdownLoc.PanelHeat, Pct(core.Heat), trend) + "\n" + F(MeltdownLoc.PanelThresholds, Pct(s.WarningHeat), Pct(s.ScramHeat));
      _state.text = StateText(core) + "\n" + (core.DecayHoursLeft > 0f
        ? F(MeltdownLoc.PanelDecayHeat, Hours(core.DecayHoursLeft)) : _loc.T(MeltdownLoc.PanelNoDecayHeat));
      _eta.text = EtaText(core);
      var coolantName = _goods.GetGood(s.CoolantGoodId).PluralDisplayName.Value;
      _causes.text = F(MeltdownLoc.PanelCoolant, coolantName, core.CoolantStock, core.CoolantPerCycle, Hours(core.CoolantReserveHours))
        + "\n" + F(MeltdownLoc.PanelCrew, core.OperatorsOnDuty, s.MinOperators)
        + "\n" + (core.MaintenanceOverdue
          ? F(MeltdownLoc.PanelMaintenanceOverdue, Hours(s.MaintenanceOutageHours), Mathf.FloorToInt(core.IdleHours))
          : F(MeltdownLoc.PanelMaintenanceDue, Hours(core.RunHoursUntilMaintenance), Hours(s.MaintenanceOutageHours)));
      bool tripped = core.Scram != ReactorScram.None;
      _scram.style.display = tripped ? DisplayStyle.None : DisplayStyle.Flex;
      _scram.SetEnabled(core.CanScram);
      _restart.style.display = tripped ? DisplayStyle.Flex : DisplayStyle.None;
      _restart.SetEnabled(core.CanRestart);
      _restartHint.text = tripped && !core.CanRestart ? F(MeltdownLoc.PanelRestartBlocked, Pct(s.RestartHeat)) : "";
      _autoRestart.SetValueWithoutNotify(core.AutoRestart);
      _rules.text = F(MeltdownLoc.PanelRules, (s.HeatPerFaultPerHour * 100f).ToString("0.#"), s.MinOperators,
          Hours(s.MaintenanceOutageHours), Hours(s.MaintenanceIntervalHours), Pct(s.ScramHeat), Hours(s.DecayHeatHours))
        + "\n" + F(MeltdownLoc.PanelConsequences, s.MeltdownKillRadius, s.MeltdownIrradiationRadius,
          Mathf.CeilToInt(s.MeltdownSourceHours / 24f), s.MeltdownRadius);
    }

    private string StateText(ReactorCore core) => core.Mode switch {
      ReactorMode.UnderConstruction => _loc.T(MeltdownLoc.PanelStateUnderConstruction),
      ReactorMode.ColdShutdown => _loc.T(MeltdownLoc.PanelStateColdShutdown),
      ReactorMode.Running => _loc.T(MeltdownLoc.PanelStateRunning),
      ReactorMode.Scrammed => core.Scram == ReactorScram.Manual ? _loc.T(MeltdownLoc.PanelStateScramManual) : _loc.T(MeltdownLoc.PanelStateScram),
      ReactorMode.Idle => _loc.T(MeltdownLoc.PanelStateIdle),
      ReactorMode.MeltingDown => _loc.T(MeltdownLoc.PanelStateMeltingDown),
      _ => core.Mode.ToString(),
    };

    // Time to the next threshold at the current rate. Running rates apply
    // only while the reactor runs; decay heat stops after DecayHoursLeft.
    private string EtaText(ReactorCore core) {
      var s = core.Spec;
      float rate = core.HeatRatePerHour, heat = core.Heat;
      if (rate > 0f) {
        if (core.Mode == ReactorMode.Running && heat < s.ScramHeat) return F(MeltdownLoc.PanelEtaScram, Hours((s.ScramHeat - heat) / rate));
        float toMeltdown = (1f - heat) / rate;
        if (core.Mode != ReactorMode.Running && toMeltdown > core.DecayHoursLeft)
          return F(MeltdownLoc.PanelEtaPeak, Pct(heat + rate * core.DecayHoursLeft), Hours(core.DecayHoursLeft));
        return F(MeltdownLoc.PanelEtaMeltdown, Hours(toMeltdown));
      }
      if (rate < 0f && core.Scram != ReactorScram.None && heat > s.RestartHeat)
        return F(MeltdownLoc.PanelEtaRestart, Hours((heat - s.RestartHeat) / -rate));
      return "";
    }
  }

  // Vault / refinery panel: fill against capacity, time to the next leak and
  // what a leak does.
  internal sealed class WasteLeakPanel : BaseEntityPanelFragment<WasteLeak> {
    private readonly ILoc _loc;
    private readonly IGoodService _goods;
    private Label _fill, _state, _rules, _history;

    public WasteLeakPanel(ILoc loc, IGoodService goods) { _loc = loc; _goods = goods; }

    private string F(string key, params object[] args) => string.Format(_loc.T(key), args);

    protected override void InitializePanel() {
      panel.AddGameLabel(_loc.T(MeltdownLoc.LeakPanelTitle), bold: true);
      _fill = Wrapped(); _state = Wrapped(); _rules = Wrapped(); _history = Wrapped();
    }

    private Label Wrapped() { var label = panel.AddGameLabel(); label.style.whiteSpace = WhiteSpace.Normal; return label; }

    public override void ShowFragment(BaseComponent entity) { base.ShowFragment(entity); UpdateFragment(); }

    public override void UpdateFragment() {
      if (!component) return;
      var leak = component;
      var s = leak.Spec;
      var goodName = _goods.GetGood(s.GoodId).PluralDisplayName.Value;
      _fill.text = F(MeltdownLoc.LeakPanelFill, goodName, leak.Stock, leak.Capacity, ReactorCore.Pct(leak.Fill));
      _state.text = leak.State switch {
        WasteLeakState.Contained => F(MeltdownLoc.LeakPanelContained, ReactorCore.Pct(s.WarningFillFraction)),
        WasteLeakState.Warning => _loc.T(MeltdownLoc.LeakPanelWarning),
        WasteLeakState.Full => F(MeltdownLoc.LeakPanelFull, ReactorCore.Hours(leak.HoursUntilLeak)),
        WasteLeakState.Sealed => _loc.T(MeltdownLoc.LeakPanelSealed),
        _ => "",
      };
      _rules.text = F($"DeepFrontier.WasteLeak.{s.Trigger}{MeltdownLoc.LeakPanelRules}", s.GoodsPerLeak,
        ReactorCore.Hours(s.LeakIntervalHours), s.SoilRadius);
      _history.text = leak.Leaks == 0 ? "" : F(MeltdownLoc.LeakPanelHistory, leak.Leaks, leak.GoodsLeaked, goodName);
    }
  }

  [Context("Game")]
  public sealed class MeltdownPanelConfigurator : Configurator {
    protected override void Configure() {
      this.BindFragment<ReactorCorePanel>();
      this.BindFragment<WasteLeakPanel>();
    }
  }
}
#endif
