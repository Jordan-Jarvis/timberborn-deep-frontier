using System;
using System.Linq;
using ModdableFluids;

namespace MoreFluids {
  /// <summary>
  /// What one More Fluids intake recipe draws from the world (pure; the harness checks it): the fluid, the volume per
  /// production cycle and the share the intake column needs. The numbers come from the fluid's registry metadata.
  /// </summary>
  public sealed class FluidIntakeRecipe {
    public FluidHandle Fluid { get; }
    public string FluidId { get; }
    /// <summary>World volume of <see cref="Fluid"/> one full production cycle removes.</summary>
    public double VolumePerCycle { get; }
    /// <summary>Of <see cref="VolumePerCycle"/>, the volume that becomes the product; the rest leaves as waste (desalination brine).</summary>
    public double ProductVolumePerCycle { get; }
    /// <summary>The intake works while the fluid's share of its column is at least this (and above zero).</summary>
    public double MinimumShare { get; }

    private FluidIntakeRecipe(FluidHandle fluid, string fluidId, double volumePerCycle, double productVolumePerCycle, double minimumShare) {
      if (!(volumePerCycle > 0) || !(productVolumePerCycle > 0) || productVolumePerCycle > volumePerCycle || minimumShare < 0 || minimumShare >= 1)
        throw new ArgumentOutOfRangeException(nameof(volumePerCycle), fluidId + ": an intake recipe draws a positive volume, at least its product, at a share in [0, 1)");
      Fluid = fluid; FluidId = fluidId; VolumePerCycle = volumePerCycle; ProductVolumePerCycle = productVolumePerCycle; MinimumShare = minimumShare;
    }

    /// <summary>Whether a column with this share of the fluid feeds the intake.</summary>
    public bool Accepts(double share) => share > 0 && share >= MinimumShare;

    /// <summary>
    /// The Fluid Extractor: the one extractable fluid (it has <see cref="MoreFluidsLiquids.ExtractorMinimumShareKey"/>) whose
    /// good is the recipe's product. <paramref name="productAmount"/> goods per cycle, each <c>VolumePerGood</c> of the fluid.
    /// </summary>
    public static FluidIntakeRecipe Extraction(FluidRegistry registry, string productGood, int productAmount) {
      if (registry == null) throw new ArgumentNullException(nameof(registry));
      RequireProduct(productGood, productAmount);
      var matches = registry.Definitions.Where(d => d.NativeRole == FluidNativeRole.Extra && d.Metadata.ContainsKey(MoreFluidsLiquids.ExtractorMinimumShareKey)
        && d.Metadata.TryGetValue(MoreFluidsLiquids.GoodKey, out string good) && good == productGood).ToArray();
      if (matches.Length != 1)
        throw new InvalidOperationException("Fluid Extractor recipe product " + productGood + " matches " + matches.Length + " extractable fluids; it needs exactly one");
      var fluid = matches[0];
      double volume = productAmount * MoreFluidsLiquids.Number(fluid, MoreFluidsLiquids.VolumePerGoodKey);
      return new FluidIntakeRecipe(registry.GetHandle(fluid.Id), fluid.Id, volume, volume, MoreFluidsLiquids.Number(fluid, MoreFluidsLiquids.ExtractorMinimumShareKey));
    }

    /// <summary>The Desalinator: saltwater into its good (Water), <c>DesalinationVolumePerWater</c> each, at any saltwater share.</summary>
    public static FluidIntakeRecipe Desalination(FluidRegistry registry, string productGood, int productAmount) {
      if (registry == null) throw new ArgumentNullException(nameof(registry));
      RequireProduct(productGood, productAmount);
      if (!registry.TryGet(MoreFluidsLiquids.Saltwater, out var salt)) throw new InvalidOperationException(MoreFluidsLiquids.Saltwater + " is not registered");
      if (!salt.Metadata.TryGetValue(MoreFluidsLiquids.GoodKey, out string good) || good != productGood)
        throw new InvalidOperationException("Desalinator recipe product " + productGood + " is not saltwater's good " + good);
      return new FluidIntakeRecipe(registry.GetHandle(salt.Id), salt.Id, productAmount * MoreFluidsLiquids.Number(salt, MoreFluidsLiquids.DesalinationVolumePerWaterKey),
        productAmount * MoreFluidsLiquids.Number(salt, MoreFluidsLiquids.VolumePerGoodKey), 0);
    }

    private static void RequireProduct(string productGood, int productAmount) {
      if (string.IsNullOrEmpty(productGood) || productAmount < 1) throw new ArgumentException("An intake recipe makes at least one of one good; got " + productAmount + " " + productGood);
    }
  }

  /// <summary>
  /// The fluid an intake has drawn but not yet used (pure; the harness checks it). Like the native
  /// <c>WaterInput.DemandCleanWaterAmount</c>, it asks for more while it holds less than three ticks' need, with one
  /// extraction request in flight at a time; production progress may use only what is stored.
  /// </summary>
  public sealed class FluidIntakeBuffer {
    /// <summary>The native <c>WaterInput.BufferMultiplier</c>.</summary>
    public const int BufferMultiplier = 3;
    public double Stored { get; private set; }
    public bool Pending { get; private set; }

    /// <summary>The volume to request now for <paramref name="neededVolume"/> this tick, or 0 when none is needed or one is in flight.</summary>
    public double Demand(double neededVolume) {
      if (double.IsNaN(neededVolume) || neededVolume < 0) throw new ArgumentOutOfRangeException(nameof(neededVolume), neededVolume, "Needed volume is non-negative");
      if (Pending || neededVolume == 0 || Stored >= neededVolume * BufferMultiplier) return 0;
      Pending = true;
      return neededVolume * BufferMultiplier;
    }

    /// <summary>The request in flight resolved with <paramref name="extracted"/> (zero when the column was refused).</summary>
    public void Resolve(double extracted) {
      if (!Pending) throw new InvalidOperationException("An intake extraction resolved with no request in flight");
      if (double.IsNaN(extracted) || double.IsInfinity(extracted) || extracted < 0) throw new ArgumentOutOfRangeException(nameof(extracted), extracted, "Extracted volume is finite and non-negative");
      Pending = false;
      Stored += extracted;
    }

    /// <summary>The production progress the stored volume allows.</summary>
    public double MaxProgress(double volumePerCycle) => volumePerCycle > 0 ? Stored / volumePerCycle
      : throw new ArgumentOutOfRangeException(nameof(volumePerCycle), volumePerCycle, "Volume per cycle is positive");

    /// <summary>Production used <paramref name="volume"/>; it never exceeds what <see cref="MaxProgress"/> allowed, up to float rounding.</summary>
    public void Consume(double volume) {
      if (double.IsNaN(volume) || volume < 0) throw new ArgumentOutOfRangeException(nameof(volume), volume, "Consumed volume is non-negative");
      if (volume > Stored + 1e-6) throw new InvalidOperationException("Production used " + volume + " fluid with only " + Stored + " stored");
      Stored = Math.Max(0, Stored - volume);
    }

    /// <summary>Restores a saved store; a request in flight is never saved (Moddable Fluids drops it, so it removed nothing).</summary>
    public void Load(double stored) {
      if (double.IsNaN(stored) || double.IsInfinity(stored) || stored < 0) throw new ArgumentOutOfRangeException(nameof(stored), stored, "A saved intake store is finite and non-negative");
      Stored = stored; Pending = false;
    }
  }
}
