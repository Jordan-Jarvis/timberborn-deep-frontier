using System;

namespace ModdableFluids {
  /// <summary>
  /// Canonical, case-sensitive identifiers. A fluid ID is its owning mod's manifest ID,
  /// a dot, and a local name: <c>DeepFrontier.RadioactiveWater</c>. Mod IDs may contain
  /// dots (<c>eMka.ModSettings</c>); local names may not, so the last dot separates them.
  /// Identifiers are validated as authored and never normalized, trimmed or aliased.
  /// </summary>
  public static class FluidIds {
    /// <summary>Reserved owner of the game's own fluids. No mod may register under it.</summary>
    public const string BuiltInOwner = "Timberborn";
    public const string Water = "Timberborn.Water";
    public const string Badwater = "Timberborn.Badwater";

    /// <summary>Segments of letters, digits, '_' or '-', separated by single dots.</summary>
    public static bool IsModId(string value) {
      if (string.IsNullOrEmpty(value) || value[0] == '.' || value[value.Length - 1] == '.') return false;
      for (int i = 0; i < value.Length; i++) {
        char c = value[i];
        if (c == '.') { if (value[i - 1] == '.') return false; continue; }
        if (!IsAsciiLetterOrDigit(c) && c != '_' && c != '-') return false;
      }
      return true;
    }

    /// <summary>An ASCII letter followed by letters, digits or '_'; no dots.</summary>
    public static bool IsLocalName(string value) {
      if (string.IsNullOrEmpty(value) || !IsAsciiLetter(value[0])) return false;
      for (int i = 1; i < value.Length; i++) if (!IsAsciiLetterOrDigit(value[i]) && value[i] != '_') return false;
      return true;
    }

    public static bool TrySplit(string id, out string ownerModId, out string localName) {
      ownerModId = null; localName = null;
      if (id == null) return false;
      int dot = id.LastIndexOf('.');
      if (dot <= 0) return false;
      string owner = id.Substring(0, dot), local = id.Substring(dot + 1);
      if (!IsModId(owner) || !IsLocalName(local)) return false;
      ownerModId = owner; localName = local;
      return true;
    }

    public static string Compose(string ownerModId, string localName) {
      RequireModId(ownerModId, "owner mod ID");
      RequireLocalName(localName, "local name");
      return ownerModId + "." + localName;
    }

    public static void RequireModId(string value, string role) {
      if (!IsModId(value)) throw new ArgumentException("Invalid " + role + " '" + value + "': expected a manifest ID made of letters, digits, '_' or '-' separated by single dots");
    }

    public static void RequireLocalName(string value, string role) {
      if (!IsLocalName(value)) throw new ArgumentException("Invalid " + role + " '" + value + "': expected an ASCII letter followed by letters, digits or '_'");
    }

    /// <summary>Requires <paramref name="id"/> to be a valid ID inside <paramref name="ownerModId"/>'s namespace.</summary>
    public static void RequireOwned(string id, string ownerModId, string role) {
      RequireModId(ownerModId, "owner mod ID");
      if (!TrySplit(id, out string owner, out _)) throw new ArgumentException("Invalid " + role + " '" + id + "': expected <OwnerModId>.<LocalName>");
      if (!string.Equals(owner, ownerModId, StringComparison.Ordinal))
        throw new ArgumentException(role + " '" + id + "' is outside its owner's namespace '" + ownerModId + ".'");
    }

    private static bool IsAsciiLetter(char c) => (c >= 'A' && c <= 'Z') || (c >= 'a' && c <= 'z');
    private static bool IsAsciiLetterOrDigit(char c) => IsAsciiLetter(c) || (c >= '0' && c <= '9');
  }
}
