using System;

namespace ModdableFluids {
  /// <summary>
  /// How native water intakes treat one extra fluid (capability <c>ModdableFluids.Policies.WaterIntakes</c>, 0.1.4).
  /// Native water intakes are the entities with a native <c>WaterInput</c> (water and badwater pumps, mechanical
  /// pumps, other intake buildings) and no <see cref="IFluidCustomIntake"/> component. Moddable Fluids' one guard
  /// blocks such an intake through the native <c>BlockableObject</c>, with a status, while the share of this fluid in
  /// the intake's column (at the last completed tick) is at or above <see cref="RefuseAtShare"/>. Below it, whatever
  /// a native clean-water removal draws of this fluid becomes native clean water (Water goods at a pump, water at a
  /// mechanical pump's outlet): that is the transformation <see cref="DrawnAsWater"/>, and the drawn volume appears in
  /// the tick's <see cref="FluidLossKind.NativeRemoval"/> losses.
  /// </summary>
  public sealed class FluidWaterIntakePolicy {
    /// <summary>Intakes stop while the column's share of this fluid is at or above this value, in (0, 1].</summary>
    public double RefuseAtShare { get; }
    /// <summary>Owned ID (<c>Owner.Name</c>) of the transformation of drawn volume into native clean water, unique in the registry.</summary>
    public string DrawnAsWater { get; }
    /// <summary>Localization key of the blocked intake's status text.</summary>
    public string RefusedStatusLocKey { get; }
    /// <summary>Localization key of the blocked intake's alert text.</summary>
    public string RefusedAlertLocKey { get; }
    internal FluidWaterIntakePolicy(double refuseAtShare, string drawnAsWater, string refusedStatusLocKey, string refusedAlertLocKey) {
      RefuseAtShare = refuseAtShare; DrawnAsWater = drawnAsWater; RefusedStatusLocKey = refusedStatusLocKey; RefusedAlertLocKey = refusedAlertLocKey;
    }
    public override string ToString() => "refused at " + RefuseAtShare.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + ", drawn as water by " + DrawnAsWater;
  }

  /// <summary>What one extra fluid does to soil moisture (capability <c>ModdableFluids.Policies.Irrigation</c>, 0.1.4).</summary>
  public enum FluidMoistureEffect {
    /// <summary>Moistens soil exactly like fresh water.</summary>
    IrrigatesLikeWater = 0,
    /// <summary>Reduces moisture like badwater does, reaching none at <see cref="FluidIrrigationPolicy.BlocksAtShare"/>.</summary>
    BlocksLikeBadwater = 1
  }

  /// <summary>
  /// The soil moisture policy of one extra fluid. Moddable Fluids owns the native soil-moisture input
  /// (<c>SoilMoistureSimulationTaskStarter.StartTask</c>): the moisture tasks see a column's contamination as
  /// <c>b + sum(share_f * M / BlocksAtShare_f)</c> over fluids that block, where b is the badwater share and M the
  /// native <c>SoilMoistureSimulatorSpec.MaximumWaterContamination</c> (0.53 in 1.1.2.8), the contamination at which
  /// native badwater gives no moisture. So a fluid that blocks at 0.1 gives no moisture at a 10% share, and one that
  /// blocks at M behaves exactly like badwater. Native moisture readers treat any value at or above 1 as no moisture.
  /// </summary>
  public sealed class FluidIrrigationPolicy {
    public FluidMoistureEffect Effect { get; }
    /// <summary>In (0, 1] for <see cref="FluidMoistureEffect.BlocksLikeBadwater"/>; 0 for <see cref="FluidMoistureEffect.IrrigatesLikeWater"/>.</summary>
    public double BlocksAtShare { get; }
    internal FluidIrrigationPolicy(FluidMoistureEffect effect, double blocksAtShare) { Effect = effect; BlocksAtShare = blocksAtShare; }
    public override string ToString() => Effect == FluidMoistureEffect.IrrigatesLikeWater ? "irrigates like water"
      : "blocks moisture at " + BlocksAtShare.ToString("R", System.Globalization.CultureInfo.InvariantCulture);
  }

  /// <summary>
  /// Marks a building component as a custom fluid intake (0.1.4). Implement it on a component of an entity that also
  /// has a native <c>WaterInput</c> (for its intake pipe) but draws fluid through <see cref="IFluidExtraction"/>:
  /// Moddable Fluids' water-intake guard then leaves that entity alone. The interface has no members; the guard
  /// checks for it once, when the entity wakes.
  /// </summary>
  public interface IFluidCustomIntake { }
}
