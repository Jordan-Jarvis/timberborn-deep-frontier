namespace DeepFrontier.Scripts.Meltdown {
  // Localization keys. The English rows are authored in
  // tools/meltdown_content.mjs and appended to Localizations/enUS.csv by
  // canonical generation; tools/validate_meltdown_content.mjs checks that every
  // key here (WasteLeak suffixes for both triggers) has a row.
  internal static class MeltdownLoc {
    public const string StatusOverheating = "DeepFrontier.Meltdown.Status.Overheating";
    public const string StatusOverheatingShort = "DeepFrontier.Meltdown.Status.Overheating.Short";
    public const string StatusScram = "DeepFrontier.Meltdown.Status.Scram";
    public const string StatusScramShort = "DeepFrontier.Meltdown.Status.Scram.Short";
    public const string StatusCoolantDry = "DeepFrontier.Meltdown.Status.CoolantDry";
    public const string StatusCoolantDryShort = "DeepFrontier.Meltdown.Status.CoolantDry.Short";
    public const string StatusWasteFull = "DeepFrontier.Meltdown.Status.WasteFull";
    public const string StatusWasteFullShort = "DeepFrontier.Meltdown.Status.WasteFull.Short";
    public const string StatusCoolantLow = "DeepFrontier.Meltdown.Status.CoolantLow";
    public const string StatusCrew = "DeepFrontier.Meltdown.Status.Crew";
    public const string StatusMaintenanceDue = "DeepFrontier.Meltdown.Status.MaintenanceDue";
    public const string StatusMaintenanceOverdue = "DeepFrontier.Meltdown.Status.MaintenanceOverdue";

    public const string NotificationWarning = "DeepFrontier.Meltdown.Notification.Warning";
    public const string NotificationCoolantDry = "DeepFrontier.Meltdown.Notification.CoolantDry";
    public const string NotificationWasteFull = "DeepFrontier.Meltdown.Notification.WasteFull";
    public const string NotificationImminent = "DeepFrontier.Meltdown.Notification.Imminent";
    public const string NotificationMaintenanceOverdue = "DeepFrontier.Meltdown.Notification.MaintenanceOverdue";
    public const string NotificationMaintenanceDone = "DeepFrontier.Meltdown.Notification.MaintenanceDone";
    public const string NotificationMeltdown = "DeepFrontier.Meltdown.Notification.Meltdown";
    public const string DialogTitle = "DeepFrontier.Meltdown.Dialog.Title";
    public const string DialogCasualties = "DeepFrontier.Meltdown.Dialog.Casualties";
    public const string DialogContamination = "DeepFrontier.Meltdown.Dialog.Contamination";
    public const string DialogShowSite = "DeepFrontier.Meltdown.Dialog.ShowSite";
    public const string DeathMessage = "DeepFrontier.Meltdown.DeathMessage";

    public const string CauseCoolant = "DeepFrontier.Meltdown.Cause.Coolant";
    public const string CauseCrew = "DeepFrontier.Meltdown.Cause.Crew";
    public const string CauseWaste = "DeepFrontier.Meltdown.Cause.Waste";
    public const string CauseMaintenance = "DeepFrontier.Meltdown.Cause.Maintenance";

    public const string PanelTitle = "DeepFrontier.Meltdown.Panel.Title";
    public const string PanelHeat = "DeepFrontier.Meltdown.Panel.Heat";
    public const string PanelThresholds = "DeepFrontier.Meltdown.Panel.Thresholds";
    public const string PanelRising = "DeepFrontier.Meltdown.Panel.Rising";
    public const string PanelFalling = "DeepFrontier.Meltdown.Panel.Falling";
    public const string PanelOutput = "DeepFrontier.Meltdown.Panel.Output";
    public const string PanelEtaMeltdown = "DeepFrontier.Meltdown.Panel.EtaMeltdown";
    public const string PanelEtaLimit = "DeepFrontier.Meltdown.Panel.EtaLimit";
    public const string PanelEtaCool = "DeepFrontier.Meltdown.Panel.EtaCool";
    public const string PanelEtaRestart = "DeepFrontier.Meltdown.Panel.EtaRestart";
    public const string PanelStateUnderConstruction = "DeepFrontier.Meltdown.Panel.State.UnderConstruction";
    public const string PanelStateColdShutdown = "DeepFrontier.Meltdown.Panel.State.ColdShutdown";
    public const string PanelStateRunning = "DeepFrontier.Meltdown.Panel.State.Running";
    public const string PanelStateScram = "DeepFrontier.Meltdown.Panel.State.Scram";
    public const string PanelStateIdle = "DeepFrontier.Meltdown.Panel.State.Idle";
    public const string PanelStateMeltingDown = "DeepFrontier.Meltdown.Panel.State.MeltingDown";
    public const string PanelDryCore = "DeepFrontier.Meltdown.Panel.DryCore";
    public const string PanelCoolant = "DeepFrontier.Meltdown.Panel.Coolant";
    public const string PanelWaste = "DeepFrontier.Meltdown.Panel.Waste";
    public const string PanelCrew = "DeepFrontier.Meltdown.Panel.Crew";
    public const string PanelMaintenanceDue = "DeepFrontier.Meltdown.Panel.MaintenanceDue";
    public const string PanelMaintenanceOverdue = "DeepFrontier.Meltdown.Panel.MaintenanceOverdue";
    public const string PanelRules = "DeepFrontier.Meltdown.Panel.Rules";
    public const string PanelConsequences = "DeepFrontier.Meltdown.Panel.Consequences";
    public const string PanelScramButton = "DeepFrontier.Meltdown.Panel.ScramButton";
    public const string PanelRestartButton = "DeepFrontier.Meltdown.Panel.RestartButton";
    public const string PanelRestartBlocked = "DeepFrontier.Meltdown.Panel.RestartBlocked";

    // WasteLeak keys are "DeepFrontier.WasteLeak.<Trigger>" + suffix.
    public const string LeakStatusWarning = ".Status.Warning";
    public const string LeakStatusLeaking = ".Status.Leaking";
    public const string LeakStatusLeakingShort = ".Status.Leaking.Short";
    public const string LeakNotificationWarning = ".Notification.Warning";
    public const string LeakNotificationFull = ".Notification.Full";
    public const string LeakNotificationLeak = ".Notification.Leak";
    public const string LeakPanelRules = ".Panel.Rules";
    public const string LeakPanelTitle = "DeepFrontier.WasteLeak.Panel.Title";
    public const string LeakPanelFill = "DeepFrontier.WasteLeak.Panel.Fill";
    public const string LeakPanelContained = "DeepFrontier.WasteLeak.Panel.Contained";
    public const string LeakPanelWarning = "DeepFrontier.WasteLeak.Panel.Warning";
    public const string LeakPanelFull = "DeepFrontier.WasteLeak.Panel.Full";
    public const string LeakPanelSealed = "DeepFrontier.WasteLeak.Panel.Sealed";
    public const string LeakPanelHistory = "DeepFrontier.WasteLeak.Panel.History";
  }
}
