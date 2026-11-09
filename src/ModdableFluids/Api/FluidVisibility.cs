using System;
using System.Globalization;

namespace ModdableFluids {
  /// <summary>
  /// How visible one extra fluid is at a given share of its column, for the shared water renderer (0.1.4,
  /// <see cref="FluidRegistration.SetVisibilityCurve"/>). Without a declared curve a fluid's visibility is its share.
  /// The declared curve is logarithmic: nothing below <see cref="FromShare"/>, <see cref="VisibilityAtFromShare"/> there,
  /// rising with the logarithm of the share to 1 at a pure column. Deep Frontier's radioactive water is (0.005, 0.12):
  /// hidden below its detection limit, 0.12 there, 1 when pure, as its own renderer drew it. The renderer multiplies the
  /// visibility by the fluid's colour alpha.
  /// </summary>
  public sealed class FluidVisibility {
    /// <summary>The share below which the fluid does not show, in (0, 1).</summary>
    public double FromShare { get; }
    /// <summary>The visibility at <see cref="FromShare"/>, in (0, 1].</summary>
    public double VisibilityAtFromShare { get; }
    internal FluidVisibility(double fromShare, double visibilityAtFromShare) { FromShare = fromShare; VisibilityAtFromShare = visibilityAtFromShare; }

    /// <summary>The visibility at <paramref name="share"/> (in [0, 1]); 1 at a pure column.</summary>
    public double At(double share) {
      if (double.IsNaN(share) || share < 0 || share > 1) throw new ArgumentOutOfRangeException(nameof(share), share, "A share is in [0, 1]");
      if (share < FromShare) return 0;
      return VisibilityAtFromShare + (1 - VisibilityAtFromShare) * (Math.Log(share / FromShare) / Math.Log(1 / FromShare));
    }

    /// <summary>The visibility of a fluid with no declared curve: its share.</summary>
    public static double Linear(double share) {
      if (double.IsNaN(share) || share < 0 || share > 1) throw new ArgumentOutOfRangeException(nameof(share), share, "A share is in [0, 1]");
      return share;
    }

    public override string ToString() => "visible from " + FromShare.ToString("R", CultureInfo.InvariantCulture) + " at "
      + VisibilityAtFromShare.ToString("R", CultureInfo.InvariantCulture) + ", log-scaled to 1";
  }
}
