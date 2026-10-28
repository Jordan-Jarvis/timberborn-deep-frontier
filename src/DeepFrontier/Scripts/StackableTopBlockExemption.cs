#if !UNITY_EDITOR
using System;
using System.Collections.Generic;
using HarmonyLib;
using Timberborn.BlockingSystem;
using Timberborn.BlockSystem;
using Timberborn.Common;
using UnityEngine;

namespace DeepFrontier.Scripts {
  // Native FinishedBlockObjectBelowBlocker (solar panels and most finished
  // buildings) blocks every BlockableObject under its foundation. A blocked
  // Workplace is never understaffed, so no beaver is assigned, and nothing
  // shows a status. Vanilla never offers a buildable top on a working
  // building, but Deep Frontier's decks and roofs are Stackable by design
  // (power and platforms on every flat face): a solar panel on the hatchery
  // deck stopped the hatchery (user save leg Day 20-11, build 178).
  //
  // The prefix replaces the private fill: an object below is skipped where its
  // own block at that cell is stackable, i.e. its blueprint invites building
  // there. Every other object below is blocked exactly as before.
  [HarmonyPatch(typeof(BlockObjectBelowBlocker),"FillBlockableObjectsBelow")]
  internal static class StackableTopBlockExemption {
    private const string HarmonyId="DeepFrontier.StackableTopBlockExemption";
    private static AccessTools.FieldRef<BlockObjectBelowBlocker,IBlockService> _blockService;
    private static AccessTools.FieldRef<BlockObjectBelowBlocker,BlockObject> _blockObject;
    private static AccessTools.FieldRef<BlockObjectBelowBlocker,List<BlockableObject>> _below;
    private static bool _patched;

    // Called once per process from DeepFrontierModStarter.
    internal static void Apply() {
      if(_patched)return;
      var fill=AccessTools.Method(typeof(BlockObjectBelowBlocker),"FillBlockableObjectsBelow",Type.EmptyTypes);
      if(fill==null||fill.IsStatic||fill.ReturnType!=typeof(void))
        throw new InvalidOperationException("Timberborn 1.1.2.8 BlockObjectBelowBlocker.FillBlockableObjectsBelow() changed");
      _blockService=AccessTools.FieldRefAccess<BlockObjectBelowBlocker,IBlockService>("_blockService");
      _blockObject=AccessTools.FieldRefAccess<BlockObjectBelowBlocker,BlockObject>("_blockObject");
      _below=AccessTools.FieldRefAccess<BlockObjectBelowBlocker,List<BlockableObject>>("_blockableObjectsBelow");
      new Harmony(HarmonyId).CreateClassProcessor(typeof(StackableTopBlockExemption)).Patch();
      _patched=true;
    }

    private static bool Prefix(BlockObjectBelowBlocker __instance) {
      var blocks=_blockService(__instance);
      var below=_below(__instance);
      foreach(Vector3Int foundation in _blockObject(__instance).PositionedBlocks.GetFoundationCoordinates()) {
        var cell=foundation.Below();
        foreach(var blockable in blocks.GetObjectsWithComponentAt<BlockableObject>(cell)) {
          var lower=blockable.GetComponent<BlockObject>();
          if(lower!=null&&lower.PositionedBlocks.HasStackableBlockAt(cell))continue;
          below.Add(blockable);
        }
      }
      return false;
    }
  }
}
#endif
