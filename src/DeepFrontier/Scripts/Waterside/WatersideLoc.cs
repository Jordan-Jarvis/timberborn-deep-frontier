using System.Globalization;

namespace DeepFrontier.Scripts {
  // Localization keys used by the waterside components. English source text
  // is WATERSIDE_ROWS in tools/fishery_building_content.mjs (ID, Text,
  // Comment); canonical generation appends it to Data/Localizations/enUS.csv.
  internal static class WatersideLoc {
    public const string SupportTooDeep="DeepFrontier.Waterside.SupportTooDeep";
    public const string SupportOutsideMap="DeepFrontier.Waterside.SupportOutsideMap";
    public const string WorkCellsTooShallow="DeepFrontier.Waterside.WorkCellsTooShallow";
    public const string WorkCellsTooDeep="DeepFrontier.Waterside.WorkCellsTooDeep";
    public const string StatusWaterTooDeep="DeepFrontier.Waterside.Status.WaterTooDeep";
    public const string StatusWaterTooDeepShort="DeepFrontier.Waterside.Status.WaterTooDeep.Short";

    public static string Meters(float value)=>value.ToString("0.##",CultureInfo.InvariantCulture);
  }
}
