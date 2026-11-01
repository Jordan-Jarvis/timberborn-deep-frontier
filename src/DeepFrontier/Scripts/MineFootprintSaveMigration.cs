#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Reflection;
using HarmonyLib;
using Timberborn.BlockSystem;
using Timberborn.Coordinates;
using Timberborn.TemplateSystem;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Second shrink pass (2026-11-01): the Deep Mine and the Sandstone and
  // Limestone Quarries became exactly 5x5, the size of the Deep Ore Vein or
  // Deep Seam they stand on, so their footprint now starts at the deposit's
  // corner. Earlier footprints (Deep Mine 10x11 and 7x6, quarries 11x7 and
  // 8x6) kept that 5x5 core at a fixed offset from their origin (local x 2..6
  // or 3..7, y 1..5). A saved mine therefore loads with its origin outside
  // the deposit, fails native validation (UnderstructureConstraintValidator:
  // every Top-only foundation must lie on the one deposit) and
  // BlockObject.AddToServiceAfterLoad would delete it with a loading issue.
  //
  // For exactly these templates, a saved placement that is not valid is
  // moved by the old core offset (rotated by its orientation; mirrored for a
  // flipped placement), and kept only if the moved placement passes the same
  // native validation, i.e. it lies exactly on its deposit. A placement that
  // is already valid (built with the 5x5 footprint) is never moved. Anything
  // that fits no known layout is left to the native deletion and its loading
  // issue, as before. BlockObjectBatchLoader adds a block object's deposit
  // first (same base z, lower occupation: Middle before Top), so the deposit
  // is in the block service when the mine is validated.
  //
  // The move uses BlockObject's own private UpdateValues (1.1.2.8:
  // coordinates, orientation, flip, positioned blocks, transform and
  // centre), the method BlockObject.Load and Reposition call, before the
  // object is added to any service.
  [HarmonyPatch(typeof(BlockObject), nameof(BlockObject.AddToServiceAfterLoad))]
  internal static class MineFootprintSaveMigration {
    // Old-local offset of the new local (0, 0): unflipped it is the old
    // core's corner; flipped it is (oldWidth - 5 - coreX0, coreY0).
    private static readonly Dictionary<string, (Vector2Int[] Unflipped, Vector2Int[] Flipped)> Moves = new() {
      // 10x11 and 7x6: core x 2..6, y 1..5.
      { "DeepMine.IronTeeth", (new[] { new Vector2Int(2, 1) }, new[] { new Vector2Int(0, 1), new Vector2Int(3, 1) }) },
      // 11x7 and 8x6: core x 3..7, y 1..5.
      { "SandstoneQuarry.IronTeeth", (new[] { new Vector2Int(3, 1) }, new[] { new Vector2Int(0, 1), new Vector2Int(3, 1) }) },
      { "LimestoneQuarry.IronTeeth", (new[] { new Vector2Int(3, 1) }, new[] { new Vector2Int(0, 1), new Vector2Int(3, 1) }) },
    };
    private static MethodInfo _updateValues;

    // Called once per process from DeepFrontierModStarter.
    internal static void Apply() {
      _updateValues = AccessTools.Method(typeof(BlockObject), "UpdateValues", new[] { typeof(Placement) })
        ?? throw new InvalidOperationException("BlockObject.UpdateValues(Placement) not found; the mine footprint save migration needs it");
      new Harmony("DeepFrontier.MineFootprintSaveMigration").CreateClassProcessor(typeof(MineFootprintSaveMigration)).Patch();
    }

    private static void Prefix(BlockObject __instance) {
      if (__instance.AddedToService) return;
      var template = __instance.GetComponent<TemplateSpec>()?.TemplateName;
      if (template == null || !Moves.TryGetValue(template, out var moves)) return;
      if (__instance.IsValid()) return;
      var original = __instance.Placement;
      foreach (var offset in original.FlipMode.IsFlipped ? moves.Flipped : moves.Unflipped) {
        var shift = original.Orientation.Transform(offset);
        var moved = new Placement(original.Coordinates + new Vector3Int(shift.x, shift.y, 0), original.Orientation, original.FlipMode);
        _updateValues.Invoke(__instance, new object[] { moved });
        if (__instance.IsValid()) {
          Debug.Log($"[DeepFrontier] Saved {template} at {original.Coordinates} ({original.Orientation}{(original.FlipMode.IsFlipped ? ", flipped" : "")}) moved to {moved.Coordinates}: the 5x5 footprint stands exactly on its deposit.");
          return;
        }
      }
      _updateValues.Invoke(__instance, new object[] { original });
      Debug.LogWarning($"[DeepFrontier] Saved {template} at {original.Coordinates} fits no known footprint over its deposit; the game will remove it.");
    }
  }
}
#endif
