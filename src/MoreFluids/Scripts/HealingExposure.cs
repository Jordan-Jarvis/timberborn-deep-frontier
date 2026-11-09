using System;
using ModdableFluids;
using Timberborn.BaseComponentSystem;
using Timberborn.Effects;
using Timberborn.EnterableSystem;
using Timberborn.Navigation;
using Timberborn.NeedSystem;
using Timberborn.TickSystem;
using Timberborn.TimeSystem;
using Timberborn.WaterSystem;

namespace MoreFluids {
  /// <summary>
  /// Healing water exposure, after Deep Frontier's <c>RadiationExposure</c>: outside buildings, a beaver standing in a
  /// column whose healing-water share is at least <see cref="HealingDose.MinimumShare"/> recovers the vanilla
  /// <c>Injury</c> and <c>BadwaterContamination</c> needs at their daily rates, through the native continuous effect.
  /// Nothing is stored: the effect is instantaneous, read from the last completed fluid tick.
  /// </summary>
  internal sealed class HealingExposure : TickableComponent, IAwakableComponent {
    private readonly MoreFluidsScene _fluids;
    private readonly IDayNightCycle _dayNightCycle;
    private NeedManager _needs;
    private Enterer _enterer;
    private IWaterResistor _waterResistor;
    private HealingDose _dose;

    public HealingExposure(MoreFluidsScene fluids, IDayNightCycle dayNightCycle) { _fluids = fluids; _dayNightCycle = dayNightCycle; }

    public void Awake() {
      _needs = GetComponent<NeedManager>();
      _enterer = GetComponent<Enterer>();
      _waterResistor = GetComponent<IWaterResistor>();
      if (_needs == null || _enterer == null) throw new InvalidOperationException("HealingExposure requires NeedManager and Enterer on beavers");
    }

    public override void Tick() {
      if (_enterer.CurrentBuilding != null || (_waterResistor?.IsWaterResistant ?? false)) return;
      var world = _fluids.Scene.World;
      if (!world.HasState) return;   // before the scene's first fluid tick there is no column to stand in
      _dose ??= HealingDose.From(_fluids.Fluid(MoreFluidsLiquids.HealingWater), _fluids.Handle(MoreFluidsLiquids.HealingWater));
      var cell = NavigationCoordinateSystem.WorldToGridInt(Transform.position);
      if (!world.TrySample(cell.x, cell.y, cell.z, out var column) || !_dose.Heals(column, cell.z)) return;
      float hours = _dayNightCycle.FixedDeltaTimeInHours;
      foreach (var effect in _dose.Effects)
        if (_needs.HasNeed(effect.NeedId)) _needs.ApplyEffect(effect, hours);
    }
  }

  /// <summary>Healing water's exposure numbers, read once from its registry metadata.</summary>
  public sealed class HealingDose {
    public const string InjuryNeed = "Injury", ContaminationNeed = "BadwaterContamination";
    public FluidHandle Fluid { get; }
    public double MinimumShare { get; }
    public ContinuousEffect[] Effects { get; }
    /// <summary>The same effects as need ID and points per day.</summary>
    public (string NeedId, double PointsPerDay)[] Rates { get; }

    private HealingDose(FluidHandle fluid, double minimumShare, double injuryPerDay, double contaminationPerDay) {
      Fluid = fluid; MinimumShare = minimumShare;
      Rates = new[] { (InjuryNeed, injuryPerDay), (ContaminationNeed, contaminationPerDay) };
      Effects = new[] { new ContinuousEffect(InjuryNeed, (float)(injuryPerDay / 24)), new ContinuousEffect(ContaminationNeed, (float)(contaminationPerDay / 24)) };
    }

    public static HealingDose From(FluidDefinition healing, FluidHandle handle) => new HealingDose(handle,
      MoreFluidsLiquids.Number(healing, MoreFluidsLiquids.ExposureMinimumShareKey),
      MoreFluidsLiquids.Number(healing, MoreFluidsLiquids.InjuryRecoveryPerDayKey),
      MoreFluidsLiquids.Number(healing, MoreFluidsLiquids.BadwaterContaminationRecoveryPerDayKey));

    /// <summary>Whether a beaver whose feet are at height <paramref name="z"/> stands in water of the column at or above the threshold.</summary>
    public bool Heals(FluidColumnSample column, int z) => column.Covers(z) && column.GetShare(Fluid) >= MinimumShare;
  }
}
