using System;
using Timberborn.AssetSystem;
using Timberborn.CoreUI;
using Timberborn.HazardousWeatherSystem;
using Timberborn.HazardousWeatherSystemUI;
using Timberborn.Localization;
using Timberborn.SingletonSystem;
using Timberborn.UILayoutSystem;
using UnityEngine;
using UnityEngine.UIElements;

namespace DeepFrontier.Scripts.RadioactiveTide {
  // Native weather UI for the radioactive tide (Timberborn 1.1.2.8).
  //
  // The native HazardousWeatherUIHelper only knows drought and badtide. While
  // the cycle's weather is the tide, RadioactiveTidePatches makes its getters
  // return Values(): the tide's names and three unstyled CSS classes. The
  // native DatePanel, WeatherPanel and HazardousWeatherNotificationPanel add
  // those classes exactly where they would add the badtide ones, and this
  // singleton turns them into inline styles each frame:
  // - date panel (top bar): the tide icon on `.date-panel__icon`;
  // - weather panel, in progress: the tide's own progress art on
  //   `.weather-panel__progress-background` (the elapsed part is the native
  //   fill);
  // - weather panel, approaching: a fill overlay of that art growing with the
  //   native HazardousWeatherApproachingTimer progress (the native progress
  //   bar draws a USS custom-property sprite, which inline styles cannot set);
  // - notification banner: the tide's own banner art, plus a
  //   one-line explanation under the approaching/started header.
  // Inline styles are removed as soon as the native panels drop the classes.
  internal sealed class RadioactiveTideUi : ILoadableSingleton, IUpdatableSingleton {
    private const string DatePanelName = "DatePanel";
    private const string DateIconClass = "date-panel__icon";
    private const string WeatherPanelName = "WeatherPanel";
    private const string ProgressBackgroundClass = "weather-panel__progress-background";
    private const string InProgressClass = "weather-in-progress";
    private const string ApproachingClass = "weather-approaching";
    private const string NotificationPanelName = "HazardousWeatherNotificationPanel";
    private const string OverlayName = "DeepFrontierRadioactiveTideApproachingFill";

    private readonly PanelStack _panelStack;
    private readonly IAssetLoader _assetLoader;
    private readonly ILoc _loc;
    private readonly EventBus _eventBus;
    private readonly HazardousWeatherService _hazardousWeatherService;
    private readonly HazardousWeatherApproachingTimer _approachingTimer;

    private Sprite _icon, _progress, _banner;
    private bool _primaryUiShown;
    private VisualElement _root, _datePanel, _dateIcon, _weatherPanel, _progressBackground, _overlay, _overlayImage;
    private Image _bannerBackground;
    private Label _bannerHeader, _bannerDescription;
    private bool _iconApplied, _progressApplied, _bannerApplied;

    public RadioactiveTideUi(PanelStack panelStack, IAssetLoader assetLoader, ILoc loc, EventBus eventBus,
        HazardousWeatherService hazardousWeatherService, HazardousWeatherApproachingTimer approachingTimer) {
      _panelStack = panelStack; _assetLoader = assetLoader; _loc = loc; _eventBus = eventBus;
      _hazardousWeatherService = hazardousWeatherService; _approachingTimer = approachingTimer;
    }

    // Getter values for the patched HazardousWeatherUIHelper.
    public static string Value(string getterName) => getterName switch {
      "get_NameLocKey" => RadioactiveTideLoc.Name,
      "get_ApproachingLocKey" => RadioactiveTideLoc.Approaching,
      "get_InProgressLocKey" => RadioactiveTideLoc.InProgress,
      "get_StartedNotificationLocKey" => RadioactiveTideLoc.Started,
      "get_EndedNotificationLocKey" => RadioactiveTideLoc.Ended,
      "get_InProgressClass" => RadioactiveTideTuning.WeatherPanelClass,
      "get_IconClass" => RadioactiveTideTuning.DatePanelClass,
      "get_NotificationBackgroundClass" => RadioactiveTideTuning.NotificationClass,
      _ => throw new ArgumentException($"Radioactive tide has no value for HazardousWeatherUIHelper.{getterName}"),
    };

    public static readonly string[] HelperGetters = {
      "NameLocKey", "ApproachingLocKey", "InProgressLocKey", "StartedNotificationLocKey", "EndedNotificationLocKey",
      "InProgressClass", "IconClass", "NotificationBackgroundClass",
    };

    public void Load() {
      _icon = _assetLoader.Load<Sprite>(RadioactiveTideTuning.IconSpritePath);
      _progress = _assetLoader.Load<Sprite>(RadioactiveTideTuning.ProgressSpritePath);
      _banner = _assetLoader.Load<Sprite>(RadioactiveTideTuning.NotificationSpritePath);
      _eventBus.Register(this);
    }

    // DatePanel and WeatherPanel enter the layout on this event; every
    // handler has run before the next UpdateSingleton.
    [OnEvent]
    public void OnShowPrimaryUI(ShowPrimaryUIEvent showPrimaryUIEvent) => _primaryUiShown = true;

    public void UpdateSingleton() {
      ResolveNotification();
      UpdateBanner();
      if (!_primaryUiShown) return;
      ResolvePrimary();
      UpdateDateIcon();
      UpdateWeatherPanel();
    }

    private VisualElement Root() {
      if (_root != null) return _root;
      _root = RadioactiveTideNative.PanelRoot(_panelStack)
        ?? throw new InvalidOperationException("Radioactive tide UI: the game panel stack has no root after loading");
      return _root;
    }

    private void ResolveNotification() {
      if (_bannerBackground != null) return;
      var panel = Root().Q<VisualElement>(NotificationPanelName) ?? throw Missing(NotificationPanelName);
      _bannerBackground = panel.Q<Image>("Background") ?? throw Missing($"{NotificationPanelName}/Background");
      _bannerHeader = panel.Q<Label>("Header") ?? throw Missing($"{NotificationPanelName}/Header");
      _bannerDescription = panel.Q<Label>("Description") ?? throw Missing($"{NotificationPanelName}/Description");
    }

    private void ResolvePrimary() {
      if (_datePanel != null) return;
      _datePanel = Root().Q<VisualElement>(DatePanelName) ?? throw Missing(DatePanelName);
      _dateIcon = _datePanel.Q<VisualElement>(className: DateIconClass) ?? throw Missing($"{DatePanelName}/.{DateIconClass}");
      _weatherPanel = Root().Q<VisualElement>(WeatherPanelName) ?? throw Missing(WeatherPanelName);
      _progressBackground = _weatherPanel.Q<VisualElement>(className: ProgressBackgroundClass) ?? throw Missing($"{WeatherPanelName}/.{ProgressBackgroundClass}");
      _overlay = new VisualElement { name = OverlayName, pickingMode = PickingMode.Ignore };
      _overlay.style.position = Position.Absolute;
      _overlay.style.left = 0; _overlay.style.top = 0; _overlay.style.bottom = 0;
      _overlay.style.overflow = Overflow.Hidden;
      _overlay.style.display = DisplayStyle.None;
      _overlayImage = new VisualElement { pickingMode = PickingMode.Ignore };
      _overlayImage.style.position = Position.Absolute;
      _overlayImage.style.left = 0; _overlayImage.style.top = 0; _overlayImage.style.bottom = 0;
      _overlayImage.style.backgroundImage = new StyleBackground(_progress);
      _overlay.Add(_overlayImage);
      _progressBackground.Add(_overlay);
    }

    private void UpdateDateIcon() {
      bool show = _datePanel.ClassListContains(RadioactiveTideTuning.DatePanelClass);
      if (show == _iconApplied) return;
      _dateIcon.style.backgroundImage = show ? new StyleBackground(_icon) : new StyleBackground(StyleKeyword.Null);
      _iconApplied = show;
    }

    private void UpdateWeatherPanel() {
      bool tide = _weatherPanel.ClassListContains(RadioactiveTideTuning.WeatherPanelClass);
      bool inProgress = tide && _weatherPanel.ClassListContains(InProgressClass);
      if (inProgress != _progressApplied) {
        _progressBackground.style.backgroundImage = inProgress ? new StyleBackground(_progress) : new StyleBackground(StyleKeyword.Null);
        _progressApplied = inProgress;
      }
      bool approaching = tide && _weatherPanel.ClassListContains(ApproachingClass);
      _overlay.style.display = approaching ? DisplayStyle.Flex : DisplayStyle.None;
      if (!approaching) return;
      float width = _progressBackground.layout.width;
      if (float.IsNaN(width)) return;   // not laid out yet this frame
      _overlayImage.style.width = width;
      _overlay.style.width = Length.Percent(100f * Mathf.Clamp01(_approachingTimer.GetProgress()));
    }

    private void UpdateBanner() {
      bool show = _bannerBackground.ClassListContains(RadioactiveTideTuning.NotificationClass);
      if (show != _bannerApplied) {
        _bannerBackground.style.backgroundImage = show ? new StyleBackground(_banner) : new StyleBackground(StyleKeyword.Null);
        _bannerApplied = show;
      }
      if (!show) return;
      // The native panel shows hazardous headers without a description.
      string header = _bannerHeader.text;
      string description = header == _loc.T(RadioactiveTideLoc.Approaching)
        ? _loc.T(RadioactiveTideLoc.ApproachingDescription, _hazardousWeatherService.HazardousWeatherDuration)
        : header == _loc.T(RadioactiveTideLoc.Started) ? _loc.T(RadioactiveTideLoc.StartedDescription) : null;
      if (description == null || _bannerDescription.text == description) return;
      _bannerDescription.text = description;
      _bannerDescription.style.display = DisplayStyle.Flex;
    }

    private static InvalidOperationException Missing(string element) =>
      new InvalidOperationException($"Radioactive tide UI: native element {element} not found (Timberborn 1.1.2.8 layout changed)");
  }
}
