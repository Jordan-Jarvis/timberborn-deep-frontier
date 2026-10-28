using Timberborn.BaseComponentSystem;
using Timberborn.Characters;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.Localization;
using Timberborn.MortalSystem;
using Timberborn.Navigation;
using Timberborn.NeedSystem;
using Timberborn.Persistence;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;
using Timberborn.WorldPersistence;

namespace DeepFrontier.Scripts.Radiation {
  // Beaver radiation exposure and radiation sickness.
  //
  // Exposure: outside buildings, a beaver accumulates dose from the cell it
  // stands in: radioactive water it wades in (scaled by the radioactive share;
  // r = 1 is as harmful as sludge was) and irradiated ground (scaled by soil
  // radiation). At dose 1
  // the "Irradiation" need drops to its minimum (-1), like native badwater
  // Contaminable.Contaminate(), and the beaver becomes a Radioactive Zombie
  // (RadioactiveZombie.cs): wellbeing penalty, slower movement than a
  // badwater-contaminated beaver and refusal to work (need blueprint), twice
  // the hunger and thirst, the yellow look. Dose decays slowly while clean.
  //
  // Treatment: the Hospital's native attraction effect restores the need over
  // 10 days of care (tools/radiation_content.mjs authors the rate from the
  // measured repeat-visit duty). Re-exposure resets the course.
  //
  // Sickness: an irradiated beaver that has not been inside a Hospital for
  // more than CareGraceHours accrues untreated time; LethalUntreatedHours of
  // untreated time kills it. Hospital stays pause (do not reset) the clock.
  // The clock counts hours only: the zombie's doubled hunger and thirst do not
  // shorten it (they can still starve or dehydrate it natively, twice as fast).
  //
  // Growing up: the game replaces a kit with a new adult entity. Native
  // NeedManager.InfluenceByChildhood copies the Irradiation need; this copies
  // the dose and the sickness clock the same way (cf. native
  // ContaminationIncubator.InfluenceByChildhood), so an irradiated kit keeps
  // its untreated time instead of starting a fresh 8 days.
  internal sealed class RadiationExposure : TickableComponent, IAwakableComponent, IPersistentEntity, IChildhoodInfluenced {
    private static readonly ComponentKey ExposureKey = new ComponentKey("DeepFrontier.RadiationExposure");
    private static readonly PropertyKey<float> DoseKey = new PropertyKey<float>("Dose");
    private static readonly PropertyKey<float> UntreatedHoursKey = new PropertyKey<float>("UntreatedHours");
    private static readonly PropertyKey<float> LastCareHourKey = new PropertyKey<float>("LastCareHour");

    private readonly RadiationSimulation _radiation;
    private readonly IDayNightCycle _dayNightCycle;
    private readonly ILoc _loc;
    private NeedManager _needs;
    private Enterer _enterer;
    private Mortal _mortal;
    private IWaterResistor _waterResistor;
    private float _dose, _untreatedHours, _lastCareHour;
    private bool _dying, _needChecked;

    public float Dose => _dose;
    public float UntreatedHours => _untreatedHours;
    public bool IsIrradiated => _needs.NeedIsActive(RadiationTuning.NeedId);
    public bool IsDying => _dying;
    // Untreated time left before radiation sickness kills the beaver.
    public float UntreatedHoursLeft => RadiationTuning.LethalUntreatedHours - _untreatedHours;
    // True while the last Hospital stay (or the onset) is within the care
    // grace period, so UpdateSickness adds no untreated time.
    public bool SicknessClockPaused => IsIrradiated && _dayNightCycle.PartialDayNumber * 24f - _lastCareHour <= RadiationTuning.CareGraceHours;

    public RadiationExposure(RadiationSimulation radiation, IDayNightCycle dayNightCycle, ILoc loc) {
      _radiation = radiation; _dayNightCycle = dayNightCycle; _loc = loc;
    }

    public void Awake() {
      _needs = GetComponent<NeedManager>();
      _enterer = GetComponent<Enterer>();
      _mortal = GetComponent<Mortal>();
      _waterResistor = GetComponent<IWaterResistor>();
      if (_needs == null || _enterer == null || _mortal == null)
        throw new System.InvalidOperationException("RadiationExposure requires NeedManager, Enterer and Mortal on beavers");
    }

    // Prompt dose from a reactor meltdown (Meltdown/MeltdownService.cs). It
    // accumulates like environmental exposure; dose >= 1 after the next tick's
    // decay irradiates the beaver with the usual care grace period.
    internal void AddDose(float dose) {
      if (!(dose > 0f) || float.IsInfinity(dose))
        throw new System.ArgumentOutOfRangeException(nameof(dose), dose, "Must be a positive finite dose");
      _dose += dose;
    }

    public override void Tick() {
      if (_dying) return;
      if (!_needChecked) {
        // NeedManager builds its needs in its own Awake; check on first tick.
        if (!_needs.HasNeed(RadiationTuning.NeedId))
          throw new System.InvalidOperationException($"Beaver need '{RadiationTuning.NeedId}' is missing from the active need collection");
        _needChecked = true;
      }
      float hours = _dayNightCycle.FixedDeltaTimeInHours;
      var building = _enterer.CurrentBuilding;
      if (building == null && !(_waterResistor?.IsWaterResistant ?? false)) {
        var cell = NavigationCoordinateSystem.WorldToGridInt(Transform.position);
        _dose += ExposureRate(_radiation.Sample(cell)) * hours;
      }
      _dose -= RadiationTuning.ExposureDecayPerHour * hours;
      if (_dose < 0f) _dose = 0f;
      if (_dose >= 1f) {
        _dose = 0f;
        if (!IsIrradiated) { _lastCareHour = _dayNightCycle.PartialDayNumber * 24f; _untreatedHours = 0f; }
        _needs.ApplyEffect(new InstantEffect(RadiationTuning.NeedId, float.MinValue, 1));
      }
      UpdateSickness(building, hours);
    }

    private static float ExposureRate(in RadiationSample sample) {
      if (!sample.HasColumn) return 0f;
      float rate = 0f;
      if (sample.Submerged) rate += sample.WaterRadiation * RadiationTuning.ExposurePerWaterRadiationPerHour;
      if (sample.SoilRadiation >= RadiationTuning.SoilExposureThreshold)
        rate += sample.SoilRadiation * RadiationTuning.ExposurePerSoilRadiationPerHour;
      return rate;
    }

    private void UpdateSickness(Enterable building, float hours) {
      if (!IsIrradiated) { _untreatedHours = 0f; return; }
      float now = _dayNightCycle.PartialDayNumber * 24f;
      if (building != null && building.GetComponent<Hospital>() != null) _lastCareHour = now;
      if (now - _lastCareHour > RadiationTuning.CareGraceHours) _untreatedHours += hours;
      if (_untreatedHours >= RadiationTuning.LethalUntreatedHours) {
        _dying = true;
        _mortal.DieTragicallyAsSoonAsPossible(_loc.T(RadiationLoc.DeathMessage, GetComponent<Character>().FirstName));
      }
    }

    // Called from Character.PreInitializeEntity of the new adult (after Awake,
    // before its first tick) with the kit it replaces.
    public void InfluenceByChildhood(Character child) {
      var childExposure = child.GetComponent<RadiationExposure>();
      if (childExposure == null) throw new System.InvalidOperationException("Kit has no RadiationExposure (decorated on BeaverSpec)");
      _dose = childExposure._dose;
      _untreatedHours = childExposure._untreatedHours;
      _lastCareHour = childExposure._lastCareHour;
    }

    public void Save(IEntitySaver entitySaver) {
      if (_dose <= 0f && _untreatedHours <= 0f && _lastCareHour <= 0f) return;
      var saver = entitySaver.GetComponent(ExposureKey);
      saver.Set(DoseKey, _dose);
      saver.Set(UntreatedHoursKey, _untreatedHours);
      saver.Set(LastCareHourKey, _lastCareHour);
    }

    public void Load(IEntityLoader entityLoader) {
      if (!entityLoader.TryGetComponent(ExposureKey, out var loader)) return;
      _dose = loader.Get(DoseKey);
      _untreatedHours = loader.Get(UntreatedHoursKey);
      _lastCareHour = loader.Get(LastCareHourKey);
    }
  }
}
