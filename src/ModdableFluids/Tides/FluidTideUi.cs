using System;
using System.Collections.Generic;
using Timberborn.AssetSystem;
using Timberborn.CoreUI;
using Timberborn.HazardousWeatherSystem;
using Timberborn.HazardousWeatherSystemUI;
using Timberborn.Localization;
using Timberborn.SingletonSystem;
using Timberborn.UILayoutSystem;
using ModdableFluids;
using UnityEngine;
using UnityEngine.UIElements;

namespace ModdableFluids.Tides.Prototype {
  /// <summary>
  /// Native weather UI for the cycle's tide (Timberborn 1.1.2.8), Deep Frontier's radioactive tide UI made generic.
  /// While a tide is the cycle's weather the patched HazardousWeatherUIHelper returns the tide's texts and three unstyled
  /// marker classes; the native DatePanel, WeatherPanel and HazardousWeatherNotificationPanel add the classes where they
  /// would add the badtide ones, and this singleton turns them into inline styles with the current tide's sprites:
  /// the date-panel icon, the weather-panel progress art (with an overlay that grows with the native approaching timer,
  /// because the native bar draws a USS custom-property sprite inline styles cannot set), and the banner art with the
  /// tide's one-line explanation under the approaching or started header. Styles are removed when the classes go.
  /// </summary>
  internal sealed class FluidTideUi : ILoadableSingleton, IUpdatableSingleton {
    private const string DatePanelName = "DatePanel", DateIconClass = "date-panel__icon";
    private const string WeatherPanelName = "WeatherPanel", ProgressBackgroundClass = "weather-panel__progress-background";
    private const string InProgressClass = "weather-in-progress", ApproachingClass = "weather-approaching";
    private const string NotificationPanelName = "HazardousWeatherNotificationPanel", OverlayName = "ModdableFluidsTideApproachingFill";

    private sealed class Art { internal Sprite Icon, Progress, Banner; }

    private readonly PanelStack _panelStack;
    private readonly IAssetLoader _assetLoader;
    private readonly ILoc _loc;
    private readonly EventBus _eventBus;
    private readonly HazardousWeatherService _hazardousWeatherService;
    private readonly HazardousWeatherApproachingTimer _approachingTimer;
    private readonly FluidTideService _tides;
    private readonly Dictionary<string, Art> _art = new Dictionary<string, Art>(StringComparer.Ordinal);

    private bool _primaryUiShown;
    private VisualElement _root, _datePanel, _dateIcon, _weatherPanel, _progressBackground, _overlay, _overlayImage;
    private Image _bannerBackground;
    private Label _bannerHeader, _bannerDescription;
    private Art _iconApplied, _progressApplied, _bannerApplied;

    public FluidTideUi(PanelStack panelStack, IAssetLoader assetLoader, ILoc loc, EventBus eventBus, HazardousWeatherService hazardousWeatherService,
        HazardousWeatherApproachingTimer approachingTimer, FluidTideService tides) {
      _panelStack = panelStack; _assetLoader = assetLoader; _loc = loc; _eventBus = eventBus;
      _hazardousWeatherService = hazardousWeatherService; _approachingTimer = approachingTimer; _tides = tides;
    }

    public void Load() {
      foreach (var tide in _tides.Tides.Tides) {
        var p = tide.Presentation;
        _art.Add(tide.Id, new Art { Icon = _assetLoader.Load<Sprite>(p.IconSprite), Progress = _assetLoader.Load<Sprite>(p.ProgressSprite), Banner = _assetLoader.Load<Sprite>(p.NotificationSprite) });
      }
      _eventBus.Register(this);
    }

    // DatePanel and WeatherPanel enter the layout on this event; every handler has run before the next UpdateSingleton.
    [OnEvent]
    public void OnShowPrimaryUI(ShowPrimaryUIEvent showPrimaryUIEvent) => _primaryUiShown = true;

    public void UpdateSingleton() {
      ResolveNotification();
      var tide = _tides.CurrentCycleTide;
      var art = tide != null ? _art[tide.Id] : null;
      UpdateBanner(tide, art);
      if (!_primaryUiShown) return;
      ResolvePrimary();
      UpdateDateIcon(art);
      UpdateWeatherPanel(art);
    }

    private VisualElement Root() => _root ??= FluidTideNative.PanelRoot(_panelStack)
      ?? throw new InvalidOperationException("Moddable Fluids tide UI: the game panel stack has no root after loading");

    private void ResolveNotification() {
      if (_bannerBackground != null) return;
      var panel = Root().Q<VisualElement>(NotificationPanelName) ?? throw Missing(NotificationPanelName);
      _bannerBackground = panel.Q<Image>("Background") ?? throw Missing(NotificationPanelName + "/Background");
      _bannerHeader = panel.Q<Label>("Header") ?? throw Missing(NotificationPanelName + "/Header");
      _bannerDescription = panel.Q<Label>("Description") ?? throw Missing(NotificationPanelName + "/Description");
    }

    private void ResolvePrimary() {
      if (_datePanel != null) return;
      _datePanel = Root().Q<VisualElement>(DatePanelName) ?? throw Missing(DatePanelName);
      _dateIcon = _datePanel.Q<VisualElement>(className: DateIconClass) ?? throw Missing(DatePanelName + "/." + DateIconClass);
      _weatherPanel = Root().Q<VisualElement>(WeatherPanelName) ?? throw Missing(WeatherPanelName);
      _progressBackground = _weatherPanel.Q<VisualElement>(className: ProgressBackgroundClass) ?? throw Missing(WeatherPanelName + "/." + ProgressBackgroundClass);
      _overlay = new VisualElement { name = OverlayName, pickingMode = PickingMode.Ignore };
      _overlay.style.position = Position.Absolute;
      _overlay.style.left = 0; _overlay.style.top = 0; _overlay.style.bottom = 0;
      _overlay.style.overflow = Overflow.Hidden;
      _overlay.style.display = DisplayStyle.None;
      _overlayImage = new VisualElement { pickingMode = PickingMode.Ignore };
      _overlayImage.style.position = Position.Absolute;
      _overlayImage.style.left = 0; _overlayImage.style.top = 0; _overlayImage.style.bottom = 0;
      _overlay.Add(_overlayImage);
      _progressBackground.Add(_overlay);
    }

    private void UpdateDateIcon(Art art) {
      var show = _datePanel.ClassListContains(FluidTideService.DatePanelClass) ? Required(art ?? _iconApplied, DatePanelName) : null;
      if (show == _iconApplied) return;
      _dateIcon.style.backgroundImage = show != null ? new StyleBackground(show.Icon) : new StyleBackground(StyleKeyword.Null);
      _iconApplied = show;
    }

    private void UpdateWeatherPanel(Art art) {
      bool tide = _weatherPanel.ClassListContains(FluidTideService.WeatherPanelClass);
      var inProgress = tide && _weatherPanel.ClassListContains(InProgressClass) ? Required(art ?? _progressApplied, WeatherPanelName) : null;
      if (inProgress != _progressApplied) {
        _progressBackground.style.backgroundImage = inProgress != null ? new StyleBackground(inProgress.Progress) : new StyleBackground(StyleKeyword.Null);
        _progressApplied = inProgress;
      }
      bool approaching = tide && _weatherPanel.ClassListContains(ApproachingClass);
      _overlay.style.display = approaching ? DisplayStyle.Flex : DisplayStyle.None;
      if (!approaching) return;
      _overlayImage.style.backgroundImage = new StyleBackground(Required(art, WeatherPanelName).Progress);
      float width = _progressBackground.layout.width;
      if (float.IsNaN(width)) return;   // not laid out yet this frame
      _overlayImage.style.width = width;
      _overlay.style.width = Length.Percent(100f * Mathf.Clamp01(_approachingTimer.GetProgress()));
    }

    private void UpdateBanner(FluidTideDefinition tide, Art art) {
      var show = _bannerBackground.ClassListContains(FluidTideService.NotificationClass) ? Required(art ?? _bannerApplied, NotificationPanelName) : null;
      if (show != _bannerApplied) {
        _bannerBackground.style.backgroundImage = show != null ? new StyleBackground(show.Banner) : new StyleBackground(StyleKeyword.Null);
        _bannerApplied = show;
      }
      if (show == null || tide == null) return;
      // The native panel shows hazardous headers without a description.
      var p = tide.Presentation;
      string header = _bannerHeader.text;
      string description = header == _loc.T(p.ApproachingLocKey) ? _loc.T(p.ApproachingDescriptionLocKey, _hazardousWeatherService.HazardousWeatherDuration)
        : header == _loc.T(p.StartedLocKey) ? _loc.T(p.StartedDescriptionLocKey) : null;
      if (description == null || _bannerDescription.text == description) return;
      _bannerDescription.text = description;
      _bannerDescription.style.display = DisplayStyle.Flex;
    }

    // A marker class is added only while the helper answers for a tide. One the native panel still shows after the next
    // cycle's weather was chosen keeps the art of the tide that set it.
    private static Art Required(Art art, string panel) =>
      art ?? throw new InvalidOperationException("Moddable Fluids tide UI: " + panel + " shows a tide marker while the cycle's weather is no tide");

    private static InvalidOperationException Missing(string element) =>
      new InvalidOperationException("Moddable Fluids tide UI: native element " + element + " not found (Timberborn " + FluidTideNative.GameVersion + " layout changed)");
  }
}
