using System;
using System.Collections.Generic;
using System.Collections.ObjectModel;

namespace ModdableFluids {
  /// <summary>How the native single-body water column represents a component.</summary>
  public enum FluidNativeRole {
    /// <summary>The game's fresh water. Volume left after badwater and every extra component.</summary>
    Water = 0,
    /// <summary>The game's badwater, published to the native contamination share.</summary>
    Badwater = 1,
    /// <summary>A registered extra component carried inside the native non-bad volume.</summary>
    Extra = 2
  }

  /// <summary>Linear RGBA in [0, 1]. Stored for the shared renderer, which is not part of contract 0.1.</summary>
  public readonly struct FluidColor : IEquatable<FluidColor> {
    public float Red { get; }
    public float Green { get; }
    public float Blue { get; }
    public float Alpha { get; }
    public FluidColor(float red, float green, float blue, float alpha) {
      Require(red, nameof(red)); Require(green, nameof(green)); Require(blue, nameof(blue)); Require(alpha, nameof(alpha));
      Red = red; Green = green; Blue = blue; Alpha = alpha;
    }
    private static void Require(float value, string name) {
      if (float.IsNaN(value) || float.IsInfinity(value) || value < 0 || value > 1)
        throw new ArgumentOutOfRangeException(name, value, "Fluid colour channels must be finite values in [0, 1]");
    }
    public bool Equals(FluidColor other) => Red == other.Red && Green == other.Green && Blue == other.Blue && Alpha == other.Alpha;
    public override bool Equals(object obj) => obj is FluidColor other && Equals(other);
    public override int GetHashCode() => ((Red.GetHashCode() * 31 + Green.GetHashCode()) * 31 + Blue.GetHashCode()) * 31 + Alpha.GetHashCode();
    public override string ToString() => "(" + Red.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + ", " +
      Green.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + ", " + Blue.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + ", " +
      Alpha.ToString("R", System.Globalization.CultureInfo.InvariantCulture) + ")";
  }

  /// <summary>An immutable registered fluid. Identity is <see cref="Id"/>; display names never merge fluids.</summary>
  public sealed class FluidDefinition {
    public string Id { get; }
    public string OwnerModId { get; }
    public string LocalName { get; }
    /// <summary>The provider that registered it, or <see cref="FluidIds.BuiltInOwner"/> for the game's fluids.</summary>
    public string ProviderId { get; }
    public string DisplayNameLocKey { get; }
    public FluidNativeRole NativeRole { get; }
    /// <summary>False for the game's fluids, whose appearance stays with the native water shader.</summary>
    public bool HasColor { get; }
    public FluidColor Color { get; }
    /// <summary>Namespaced custom properties (<c>Owner.Key</c>), ordinal key order.</summary>
    public IReadOnlyDictionary<string, string> Metadata { get; }
    /// <summary>How native water intakes treat this extra fluid (0.1.4); null for the game's fluids and while undeclared.</summary>
    public FluidWaterIntakePolicy WaterIntake { get; }
    /// <summary>What this extra fluid does to soil moisture (0.1.4); null for the game's fluids and while undeclared.</summary>
    public FluidIrrigationPolicy Irrigation { get; }
    /// <summary>The shared renderer's visibility curve (0.1.4); null means the visibility is the share.</summary>
    public FluidVisibility Visibility { get; }

    internal FluidDefinition(string id, string ownerModId, string localName, string providerId, string displayNameLocKey,
        FluidNativeRole role, bool hasColor, FluidColor color, SortedDictionary<string, string> metadata,
        FluidWaterIntakePolicy waterIntake = null, FluidIrrigationPolicy irrigation = null, FluidVisibility visibility = null) {
      Id = id; OwnerModId = ownerModId; LocalName = localName; ProviderId = providerId; DisplayNameLocKey = displayNameLocKey;
      NativeRole = role; HasColor = hasColor; Color = color; WaterIntake = waterIntake; Irrigation = irrigation; Visibility = visibility;
      Metadata = new ReadOnlyDictionary<string, string>(new SortedDictionary<string, string>(metadata, StringComparer.Ordinal));
    }

    public override string ToString() => Id + " (" + NativeRole + ", owner " + OwnerModId + ")";
  }
}
