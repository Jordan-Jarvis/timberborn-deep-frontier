using System.Collections.Generic;
using System.Globalization;
using Timberborn.BaseComponentSystem;
using Timberborn.BeaverContaminationSystem;
using Timberborn.Beavers;
using Timberborn.CharacterModelSystem;
using Timberborn.Characters;
using Timberborn.Effects;
using Timberborn.EntityPanelSystem;
using Timberborn.EntitySystem;
using Timberborn.GameFactionSystem;
using Timberborn.Localization;
using Timberborn.MortalSystem;
using Timberborn.NeedSystem;
using Timberborn.StatusSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WalkingSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.Radiation {
  // The Radioactive Zombie: a beaver whose native "Irradiation" need is active
  // (RadiationExposure sets it to -1 at dose 1; the Hospital's attraction
  // effect cures it). The need is the zombie state, so it is saved, loaded and
  // carried from kit to adult by native NeedManager. Decorated on BeaverSpec;
  // bots have no BeaverSpec and are never zombies.
  //
  // From the need blueprint (tools/radiation_content.mjs): no work
  // (NeedPreventingWorkSpec), wellbeing -12, the critical-need status icon and
  // a MovementSpeed penalty below native BadwaterContamination's.
  //
  // From this component, all applied and removed with the need's active state
  // (NeedManager.NeedChangedActiveState):
  // - Twice the hunger and thirst. Native NeedSpec decay has no per-beaver
  //   multiplier, so each tick applies a native ContinuousEffect of
  //   ZombieNeedDecayMultiplier x DailyDelta to Hunger and Thirst. Native
  //   Need.Update skips its own decay in an update after Need.Apply, so the
  //   effect replaces the native decay instead of adding to it: the rate is
  //   exactly 2x and starvation and dehydration come exactly twice as fast.
  // - The look: the native CharacterTint (the beaver shader's _TintColor /
  //   _TintEnabled, which native CitizenTint drives from colour names) in the
  //   radiation tint yellow, kept over CitizenTint by RadioactiveZombieTint.
  // - The walk: exactly the two animator inputs a native badwater-contaminated
  //   beaver gets (Timberborn 1.1.2.8). ContaminableAnimator sets "Contaminated";
  //   RunningStateUpdater forces RunningProhibited for Contaminable.IsContaminated.
  //   The animator plays the last exactly matching state (TimbermeshAnimator-
  //   Controller.FindBestMatchState), and only "Contaminated walking" requires
  //   Walking + RunningProhibited + Contaminated; with RunningProhibited false
  //   the plain "Running" state (no Contaminated condition) matches instead.
  //   The zombie therefore sets "Contaminated" and prohibits running through a
  //   native WalkingEnforcerToggle (the mechanism carrying, ziplines and
  //   character control use; RunningStateUpdater ORs it into RunningProhibited),
  //   not through its low speed, which only held while the MovementSpeed bonus
  //   stayed below RunningStateUpdaterSpec.WalkingSpeedThreshold. The clip speed
  //   is the state's Speed x WalkingSpeed, and MovementAnimator sets WalkingSpeed
  //   to the actual path speed, so the slower zombie keeps the native cycle
  //   (cadence x0.25/x0.30 of a contaminated beaver's, feet matched). Native
  //   ContaminableAnimator also writes "Contaminated" on badwater contamination
  //   changes, so a zombie re-asserts it each tick (the controller ignores an
  //   unchanged value) and a cured beaver gets the native contamination value back.
  // - The beaver panel: a badge subtitle "<age> · Radioactive Zombie" with the
  //   native contaminated avatar, and a description line with the untreated
  //   time left before radiation sickness kills it (RadiationExposure's
  //   unchanged 8-day clock); an alert once less than ZombieDyingAlertHours
  //   remain while the clock runs.
  internal sealed class RadioactiveZombie : TickableComponent, IAwakableComponent, IInitializableEntity, IPostInitializableEntity,
      IEntityDescriber, IEntityBadge {
    internal const string ContaminatedAnimatorParameter = "Contaminated";
    private const int DescriptionOrder = 140;
    private const int BadgePriority = 20;                 // native BeaverEntityBadge: 10

    private readonly ILoc _loc;
    private readonly IDayNightCycle _dayNightCycle;
    private readonly IEntityPanel _entityPanel;
    private readonly FactionService _factionService;
    private readonly List<IEntityBadge> _badges = new List<IEntityBadge>();
    private NeedManager _needs;
    private RadiationExposure _exposure;
    private CharacterTint _tint;
    private CharacterAnimator _animator;
    private Contaminable _contaminable;
    private Mortal _mortal;
    private EntityComponent _entity;
    private StatusToggle _dyingStatus;
    private WalkingEnforcerToggle _walkingToggle;
    private ContinuousEffect _hungerDecay, _thirstDecay;
    private bool _isChild, _zombie, _decayReady, _dyingShown, _shownPaused;
    private int _shownTenths = -1;

    public bool IsZombie => _zombie;

    public RadioactiveZombie(ILoc loc, IDayNightCycle dayNightCycle, IEntityPanel entityPanel, FactionService factionService) {
      _loc = loc; _dayNightCycle = dayNightCycle; _entityPanel = entityPanel; _factionService = factionService;
    }

    public void Awake() {
      _needs = GetComponent<NeedManager>();
      _exposure = GetComponent<RadiationExposure>();
      _tint = GetComponent<CharacterTint>();
      _animator = GetComponent<CharacterAnimator>();
      _contaminable = GetComponent<Contaminable>();
      _mortal = GetComponent<Mortal>();
      _entity = GetComponent<EntityComponent>();
      if (_needs == null || _exposure == null || _tint == null || _animator == null || _contaminable == null || _mortal == null || _entity == null)
        throw new System.InvalidOperationException("RadioactiveZombie requires NeedManager, RadiationExposure, CharacterTint, CharacterAnimator, Contaminable, Mortal and EntityComponent on beavers");
      var walkingEnforcer = GetComponent<WalkingEnforcer>();
      if (walkingEnforcer == null) throw new System.InvalidOperationException("RadioactiveZombie requires the native WalkingEnforcer on beavers");
      _walkingToggle = walkingEnforcer.GetWalkingEnforcerToggle();
      _isChild = GetComponent<Child>() != null;
      _dyingStatus = StatusToggle.CreateNormalStatusWithAlertAndFloatingIcon(RadiationSprites.ZombieDying,
        _loc.T(RadiationLoc.ZombieDying), _loc.T(RadiationLoc.ZombieDyingShort));
      // NeedManager.Load and InfluenceByChildhood report the loaded or
      // inherited need state through this event.
      _needs.NeedChangedActiveState += (_, e) => { if (e.NeedSpec.Id == RadiationTuning.NeedId) Sync(); };
      DisableComponent();
    }

    public void InitializeEntity() {
      if (!_animator.HasParameter(ContaminatedAnimatorParameter))
        throw new System.InvalidOperationException($"Beaver animator has no native '{ContaminatedAnimatorParameter}' parameter");
      _hungerDecay = ZombieDecay(RadiationTuning.HungerNeedId);
      _thirstDecay = ZombieDecay(RadiationTuning.ThirstNeedId);
      _decayReady = true;
      var subject = GetComponent<StatusSubject>();
      if (subject == null) throw new System.InvalidOperationException("RadioactiveZombie requires the native StatusSubject on beavers");
      subject.RegisterStatus(_dyingStatus);
    }

    public void PostInitializeEntity() => Sync();

    // Need.Apply scales effect points by NeedSpec.Effectiveness; dividing by it
    // keeps the applied rate at exactly ZombieNeedDecayMultiplier x DailyDelta.
    private ContinuousEffect ZombieDecay(string needId) {
      var spec = _needs.GetNeedSpec(needId);
      if (spec == null) throw new System.InvalidOperationException($"Beaver need '{needId}' is missing");
      if (!(spec.DailyDelta < 0f) || !(spec.Effectiveness > 0f))
        throw new System.InvalidOperationException($"Beaver need '{needId}' must decay (DailyDelta {spec.DailyDelta}) with positive Effectiveness ({spec.Effectiveness})");
      return new ContinuousEffect(needId, RadiationTuning.ZombieNeedDecayMultiplier * spec.DailyDelta / 24f / spec.Effectiveness);
    }

    private void Sync() {
      bool zombie = _needs.NeedIsActive(RadiationTuning.NeedId);
      if (zombie == _zombie) return;
      _zombie = zombie;
      if (zombie) {
        ReapplyTint();
        _animator.SetBool(ContaminatedAnimatorParameter, true);
        _walkingToggle.EnableForcedWalking();
        EnableComponent();
      } else {
        DisableComponent();
        SetDyingStatus(false);
        _walkingToggle.DisableForcedWalking();
        _animator.SetBool(ContaminatedAnimatorParameter, _contaminable.IsContaminated);
#if !UNITY_EDITOR
        RadioactiveZombieTint.RestoreNative(this);
#endif
      }
      _shownTenths = -1;
      _entityPanel.ReloadDescription(_entity);
    }

    // Called on becoming a zombie and after every native CitizenTint update.
    internal void ReapplyTint() {
      if (_zombie) _tint.SetTint(RadiationMaterials.WaterTintColor);
    }

    // Enabled only while a zombie.
    public override void Tick() {
      if (_mortal.Dead || _exposure.IsDying) return;
      if (!_decayReady) throw new System.InvalidOperationException("RadioactiveZombie ticked before InitializeEntity");
      float hours = _dayNightCycle.FixedDeltaTimeInHours;
      _needs.ApplyEffect(_hungerDecay, hours);
      _needs.ApplyEffect(_thirstDecay, hours);
      _animator.SetBool(ContaminatedAnimatorParameter, true);
      float hoursLeft = _exposure.UntreatedHoursLeft;
      bool paused = _exposure.SicknessClockPaused;
      SetDyingStatus(!paused && hoursLeft < RadiationTuning.ZombieDyingAlertHours);
      int tenths = Tenths(hoursLeft);
      if (tenths != _shownTenths || paused != _shownPaused) {
        _shownTenths = tenths;
        _shownPaused = paused;
        _entityPanel.ReloadDescription(_entity);
      }
    }

    private void SetDyingStatus(bool shown) {
      if (shown == _dyingShown) return;
      _dyingShown = shown;
      if (shown) _dyingStatus.Activate(); else _dyingStatus.Deactivate();
    }

    // Untreated days left in tenths, rounded down (never overstates the time).
    private static int Tenths(float hoursLeft) => hoursLeft > 0f ? Mathf.FloorToInt(hoursLeft / 2.4f) : 0;

    public IEnumerable<EntityDescription> DescribeEntity() {
      if (!_zombie || _mortal.Dead) yield break;
      string days = (Tenths(_exposure.UntreatedHoursLeft) / 10f).ToString("0.0", CultureInfo.InvariantCulture);
      string key = _exposure.SicknessClockPaused ? RadiationLoc.ZombieCountdownPaused : RadiationLoc.ZombieCountdown;
      yield return EntityDescription.CreateTextSection(_loc.T(key, days), DescriptionOrder);
      yield return EntityDescription.CreateTextSection(_loc.T(RadiationLoc.ZombieFlavor), DescriptionOrder + 1);
    }

    public bool EntityBadgeEnabled => _zombie && !_mortal.Dead;

    public int EntityBadgePriority => BadgePriority;

    public string GetEntitySubtitle() => _loc.T(RadiationLoc.ZombieSubtitle, NativeBadge().GetEntitySubtitle());

    public ClickableSubtitle GetEntityClickableSubtitle() => NativeBadge().GetEntityClickableSubtitle();

    public Sprite GetEntityAvatar() {
      var faction = _factionService.Current;
      return (_isChild ? faction.ContaminatedChildAvatar : faction.ContaminatedAdultAvatar).Asset;
    }

    // The highest-priority other badge (native BeaverEntityBadge): age and
    // district link stay native.
    private IEntityBadge NativeBadge() {
      _badges.Clear();
      GetComponents(_badges);
      IEntityBadge best = null;
      int priority = int.MinValue;
      foreach (var badge in _badges) {
        if (ReferenceEquals(badge, this) || !badge.EntityBadgeEnabled || badge.EntityBadgePriority <= priority) continue;
        best = badge;
        priority = badge.EntityBadgePriority;
      }
      _badges.Clear();
      if (best == null) throw new System.InvalidOperationException("Radioactive zombie has no native entity badge to extend");
      return best;
    }
  }
}
