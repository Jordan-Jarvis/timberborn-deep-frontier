using System;
#if !UNITY_EDITOR
using HarmonyLib;
#endif
using Timberborn.BlockSystem;

namespace DeepFrontier.Scripts {
  // Save/load order for block objects that carry stackable cells below their
  // BaseZ layer: FishHatchery's deck slabs (local z=0, BaseZ 1) and the
  // concrete side platforms' decks.
  //
  // Native 1.1.2.8 BlockObjectBatchLoader.AddToServices adds every loaded
  // block object ordered by CoordinatesAtBaseZ.z, then by GetHighestOccupation
  // (the highest occupation class on the local BaseZ layer: None 0, Floor 1,
  // Path 2, Bottom 3, Middle 4, Corners 5, Top 6). BlockObject
  // .AddToServiceAfterLoad deletes any object whose MatterBelow is unmet at
  // that moment, and StackableBlockService only sees objects already added.
  // A path, shaft or platform built on the hatchery deck stands one layer
  // above a slab that lies below the hatchery's BaseZ layer, so it shares the
  // hatchery's sort layer; the hatchery's 'All' headhouse blocks on that layer
  // rank 6, so every deck object was validated before its support existed and
  // deleted on each load.
  //
  // Blueprint data cannot express the order. The preview picker places
  // origin = cursor - BaseZ and the loader sorts at origin + BaseZ, so the
  // sort layer is the bank layer the player points at for any BaseZ that
  // keeps the bank anchoring. Ranking below Path would need a BaseZ layer of
  // only Floor/None cells (no enclosed headhouse), and Floor still ties with
  // native ImpermeableFloor. No native blueprint has stackable cells below
  // BaseZ, so this gap only exists for this mod's content.
  //
  // Such an object is ranked below every native occupation class, so it is
  // added first within its layer. That is always valid for it: every
  // foundation block (solid MatterBelow) sits at or below the BaseZ layer, so
  // it rests on terrain or on cells of lower layers, which the loader has
  // already added. Objects with a foundation above BaseZ keep native order.
  // The hatchery generator and validate_hatchery_exports.py require the
  // hatchery to keep that condition; the side platforms (cleat at BaseZ) meet
  // it too.
#if !UNITY_EDITOR
  [HarmonyPatch(typeof(BlockObjectBatchLoader),nameof(BlockObjectBatchLoader.GetHighestOccupation))]
#endif
  internal static class StackableBaseLoadOrder {
    internal const string HarmonyId="DeepFrontier.StackableBaseLoadOrder";
    // Below native Floor (1) and None (0).
    internal const int SupportFirst=-1;

    internal static bool LoadsFirst(BlockObject blockObject) {
      int baseZ=blockObject.BaseZ;
      bool carriesStackableBelowBase=false;
      foreach(var block in blockObject.Blocks.GetAllBlocks()) {
        int z=block.Coordinates.z;
        if(block.IsFoundationBlock&&z>baseZ)return false;
        if(z<baseZ&&block.Stackable.IsStackable())carriesStackableBelowBase=true;
      }
      return carriesStackableBelowBase;
    }

#if !UNITY_EDITOR
    private static bool _patched;

    // Called once per process from DeepFrontierModStarter, before any game
    // scene loads entities.
    internal static void Apply() {
      if(_patched)return;
      var method=AccessTools.Method(typeof(BlockObjectBatchLoader),nameof(BlockObjectBatchLoader.GetHighestOccupation),new[]{typeof(BlockObject)});
      if(method==null||!method.IsStatic||method.ReturnType!=typeof(int))
        throw new InvalidOperationException("Timberborn 1.1.2.8 static BlockObjectBatchLoader.GetHighestOccupation(BlockObject) : int changed");
      new Harmony(HarmonyId).CreateClassProcessor(typeof(StackableBaseLoadOrder)).Patch();
      _patched=true;
    }

    private static void Postfix(BlockObject blockObject,ref int __result) {
      if(LoadsFirst(blockObject))__result=SupportFirst;
    }
#endif
  }
}
