#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Collections.Immutable;
using System.Runtime.CompilerServices;
using HarmonyLib;
using Timberborn.BlockSystem;
using UnityEngine;

namespace DeepFrontier.Scripts.PreviewNavMesh {
  // Extension gap (Timberborn 1.1.2.8, decompiled): PositionedBlocks.TryGetBlock,
  // HasBlockAt and HasStackableBlockAt scan the whole block array for one
  // coordinate. A Nuclear Reactor has 6,600 blocks. While its preview is shown,
  // BlockObjectAccessGenerator.IsAccessBlockedBySelf calls TryGetBlock for every
  // column and level it tests for builder access (tens of thousands of calls
  // per regeneration, ~1 s; measured in PreviewCostAcceptance), and the block
  // validators and stackable checks call GetBlock on large neighbours.
  //
  // PositionedBlocks is immutable (one readonly ImmutableArray, set in the
  // private constructor), so a per-instance coordinate -> first index map gives
  // exactly the native first match: TryGetBlock returns the block at the first
  // index with equal coordinates, HasBlockAt is "map contains". Native
  // positioning gives unique coordinates; if an instance ever had duplicates,
  // HasStackableBlockAt ("any block there is stackable") keeps the native scan.
  // Arrays shorter than IndexedLength keep the native scan (no gain).
  internal static class PositionedBlocksIndex {
    private sealed class Index {
      public readonly Dictionary<Vector3Int,int> FirstAt=new();
      public bool Unique=true;
    }

    private const int IndexedLength=64;
    private static readonly ConditionalWeakTable<PositionedBlocks,Index> Indexes=new();
    private static readonly ConditionalWeakTable<PositionedBlocks,Index>.CreateValueCallback Build=BuildIndex;
    private static AccessTools.FieldRef<PositionedBlocks,ImmutableArray<Block>> _all;
    private static bool _enabled=true;

    // 1.1.2.8: every method of PositionedBlocks and its iterators.
    private const string TypeIl="1290a3afda847ee3ca6bb88eca13959a0e53f860f355e00acbd5593eb4f8d241";

    public static void Patch() {
      var digest=PreviewAccessCache.TypeDigest(typeof(PositionedBlocks));
      if(digest!=TypeIl)throw new InvalidOperationException("[DeepFrontier PositionedBlocksIndex] PositionedBlocks differs from 1.1.2.8 (IL digest "+digest+")");
      var field=AccessTools.Field(typeof(PositionedBlocks),"_all");
      if(field==null||field.FieldType!=typeof(ImmutableArray<Block>)||!field.IsInitOnly)
        throw new InvalidOperationException("[DeepFrontier PositionedBlocksIndex] PositionedBlocks._all changed");
      _all=AccessTools.FieldRefAccess<PositionedBlocks,ImmutableArray<Block>>("_all");
      var harmony=new Harmony("DeepFrontier.PositionedBlocksIndex");
      harmony.Patch(AccessTools.Method(typeof(PositionedBlocks),nameof(PositionedBlocks.TryGetBlock)),
        prefix:new HarmonyMethod(typeof(PositionedBlocksIndex),nameof(TryGetBlockPrefix)));
      harmony.Patch(AccessTools.Method(typeof(PositionedBlocks),nameof(PositionedBlocks.HasBlockAt)),
        prefix:new HarmonyMethod(typeof(PositionedBlocksIndex),nameof(HasBlockAtPrefix)));
      harmony.Patch(AccessTools.Method(typeof(PositionedBlocks),nameof(PositionedBlocks.HasStackableBlockAt)),
        prefix:new HarmonyMethod(typeof(PositionedBlocksIndex),nameof(HasStackableBlockAtPrefix)));
    }

    // Measurement only (PreviewCostAcceptance): native scans.
    internal static void SetEnabledForMeasurement(bool enabled) {_enabled=enabled;}

    private static Index BuildIndex(PositionedBlocks blocks) {
      var all=_all(blocks);
      var index=new Index();
      for(int i=0;i<all.Length;i++) {
        if(!index.FirstAt.ContainsKey(all[i].Coordinates))index.FirstAt.Add(all[i].Coordinates,i);
        else index.Unique=false;
      }
      return index;
    }

    private static bool TryGetBlockPrefix(PositionedBlocks __instance,Vector3Int coordinates,ref Block result,ref bool __result) {
      if(!_enabled)return true;
      var all=_all(__instance);
      if(all.Length<IndexedLength)return true;
      if(Indexes.GetValue(__instance,Build).FirstAt.TryGetValue(coordinates,out int i)) {
        result=all[i];__result=true;
      } else {
        result=default;__result=false;
      }
      return false;
    }

    private static bool HasBlockAtPrefix(PositionedBlocks __instance,Vector3Int coordinates,ref bool __result) {
      if(!_enabled)return true;
      if(_all(__instance).Length<IndexedLength)return true;
      __result=Indexes.GetValue(__instance,Build).FirstAt.ContainsKey(coordinates);
      return false;
    }

    private static bool HasStackableBlockAtPrefix(PositionedBlocks __instance,Vector3Int coordinates,ref bool __result) {
      if(!_enabled)return true;
      var all=_all(__instance);
      if(all.Length<IndexedLength)return true;
      var index=Indexes.GetValue(__instance,Build);
      if(!index.Unique)return true;
      __result=index.FirstAt.TryGetValue(coordinates,out int i)&&all[i].Stackable.IsStackable();
      return false;
    }
  }
}
#endif
